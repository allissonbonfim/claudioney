"""Rotas públicas (site do participante). Prefixo /v1/public."""

from __future__ import annotations

import mimetypes
import re
import time
import zipfile
from collections import deque
from collections.abc import Iterator
from datetime import timedelta
from urllib.parse import quote

import numpy as np
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flash import imaging, security
from flash.api.deps import client_ip, get_open_event, get_tenant, limiter
from flash.channels.base import CHANNEL_WEB
from flash.config import get_settings
from flash.db import ConsentLog, Event, Feedback, Photo, Search, SearchResult, Tenant, get_session
from flash.faces import get_engine
from flash.faces.selfie import analyze_selfie
from flash.index.vector import get_index
from flash.search.service import RateLimited, run_search
from flash.sources import source_for
from flash.storage import get_store

router = APIRouter(prefix="/v1/public", tags=["public"])

TERMS_VERSION = "2026-10"
_DEVICE_RE = re.compile(r"^[A-Za-z0-9_\-]{16,64}$")


# --------------------------------------------------------------------------- tenant / eventos
@router.get("/tenant")
def tenant_info(tenant: Tenant = Depends(get_tenant)):
    cfg = tenant.config
    return {
        "slug": tenant.slug,
        "name": tenant.name,
        "brand": cfg.get("brand", {}),
        "texts": cfg.get("texts", {}),
        "terms_url": cfg.get("terms_url"),
        "terms_version": TERMS_VERSION,
    }


def _event_card(session: Session, e: Event) -> dict:
    n = session.scalar(
        select(func.count())
        .select_from(Photo)
        .where(Photo.event_id == e.id, Photo.visible.is_(True), Photo.status == "indexed")
    )
    return {
        "slug": e.slug,
        "name": e.name,
        "status": e.status,
        "starts_on": e.starts_on,
        "ends_on": e.ends_on,
        "requires_code": bool(e.access_code_hash),
        "has_minors": e.has_minors,
        "photos": n or 0,
        "description": e.config.get("description"),
    }


@router.get("/events")
def list_events(tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)):
    events = session.scalars(
        select(Event)
        .where(Event.tenant_id == tenant.id, Event.status.in_(("open", "indexing")))
        .order_by(Event.created_at.desc())
    ).all()
    return [_event_card(session, e) for e in events]


@router.get("/events/{slug}")
def event_info(event: Event = Depends(get_open_event), session: Session = Depends(get_session)):
    return _event_card(session, event)


class AccessBody(BaseModel):
    code: str = Field(min_length=1, max_length=64)


@router.post("/events/{slug}/access")
def event_access(body: AccessBody, request: Request, event: Event = Depends(get_open_event)):
    if not event.access_code_hash:
        return {"token": None}
    if not limiter.check(f"code:{client_ip(request)}:{event.id}", 8, 600):
        raise HTTPException(429, "Muitas tentativas. Aguarde alguns minutos.")
    if not security.check_code(body.code, event.access_code_hash):
        raise HTTPException(403, "Código inválido")
    ttl = timedelta(hours=get_settings().session_ttl_hours)
    token = security.make_token("access", ttl, t=event.tenant_id, e=event.id)
    return {"token": token}


def _require_access(event: Event, authorization: str | None) -> None:
    if not event.access_code_hash:
        return
    token = (authorization or "").removeprefix("Bearer ").strip()
    try:
        claims = security.read_token(token, "access")
    except security.TokenError:
        raise HTTPException(401, "Informe o código do evento") from None
    if claims.get("e") != event.id:
        raise HTTPException(401, "Informe o código do evento")


# --------------------------------------------------------------------------- busca
@router.post("/events/{slug}/search")
def search(
    request: Request,
    event: Event = Depends(get_open_event),
    session: Session = Depends(get_session),
    selfie: list[UploadFile] = File(...),
    consent: bool = Form(False),
    terms_version: str = Form(TERMS_VERSION),
    x_device_id: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    settings = get_settings()
    if not consent:
        raise HTTPException(400, "É preciso aceitar os termos para buscar suas fotos.")
    if not x_device_id or not _DEVICE_RE.match(x_device_id):
        raise HTTPException(400, "Dispositivo não identificado")
    _require_access(event, authorization)
    if not limiter.check(f"search-ip:{client_ip(request)}", 30, 60):
        raise HTTPException(429, "Muitas buscas em pouco tempo.")
    if not 1 <= len(selfie) <= 3:
        raise HTTPException(400, "Envie de 1 a 3 selfies")

    engine = get_engine(event.engine)
    vectors, qualities = [], []
    for i, upload in enumerate(selfie):
        raw = upload.file.read(settings.max_upload_bytes + 1)  # só em memória, nunca em disco
        if len(raw) > settings.max_upload_bytes:
            raise HTTPException(413, "Imagem muito grande (máx. 10 MB)")
        try:
            img, _, _ = imaging.decode(raw, 1280)
        except imaging.InvalidImageError:
            raise HTTPException(
                422,
                {
                    "reason": "invalid_image",
                    "message": "Não consegui abrir essa imagem.",
                    "index": i,
                },
            ) from None
        result = analyze_selfie(engine, imaging.to_bgr(img))
        if result.ok:
            vectors.append(result.embedding)
            qualities.append(result.quality)
        elif not vectors and i == len(selfie) - 1:
            raise HTTPException(
                422, {"reason": result.reason, "message": result.message, "index": i}
            )
    if not vectors:
        raise HTTPException(
            422, {"reason": "no_face", "message": "Não encontramos um rosto.", "index": 0}
        )

    subject = security.subject_ref(x_device_id)
    already = session.scalar(
        select(func.count())
        .select_from(ConsentLog)
        .where(
            ConsentLog.event_id == event.id,
            ConsentLog.subject_ref == subject,
            ConsentLog.terms_version == terms_version,
        )
    )
    if not already:
        session.add(
            ConsentLog(
                tenant_id=event.tenant_id,
                event_id=event.id,
                subject_ref=subject,
                channel=CHANNEL_WEB,
                terms_version=terms_version,
            )
        )
    limit = settings.searches_per_day if event.has_minors else settings.searches_per_day * 5
    try:
        outcome = run_search(
            session,
            event,
            np.stack(vectors),
            subject=subject,
            channel=CHANNEL_WEB,
            quality=float(np.mean(qualities)),
            daily_limit=limit,
        )
    except RateLimited:
        raise HTTPException(429, "Você atingiu o limite de buscas de hoje. Tente amanhã.") from None

    ttl = timedelta(days=settings.gallery_ttl_days)
    token = security.make_token("gal", ttl, t=event.tenant_id, e=event.id, s=outcome.search_id)
    return {
        "search_id": outcome.search_id,
        "counts": {"certain": len(outcome.certain), "maybe": len(outcome.maybe)},
        "gallery_token": token,
        "latency_ms": outcome.latency_ms,
    }


# --------------------------------------------------------------------------- galeria
def _gallery(token: str, session: Session) -> tuple[Search, Event]:
    try:
        claims = security.read_token(token, "gal")
    except security.TokenError:
        raise HTTPException(401, "Link inválido ou expirado") from None
    search_row = session.get(Search, claims["s"])
    event = session.get(Event, claims["e"])
    if search_row is None or event is None or event.status == "archived":
        raise HTTPException(404, "Galeria não encontrada")
    return search_row, event


def _photo_in_gallery(session: Session, search_id: str, photo_id: str) -> Photo:
    row = session.scalar(
        select(Photo)
        .join(SearchResult, SearchResult.photo_id == Photo.id)
        .where(SearchResult.search_id == search_id, Photo.id == photo_id, Photo.visible.is_(True))
    )
    if row is None:
        raise HTTPException(404, "Foto não encontrada")
    return row


def _photo_json(token: str, p: Photo, tier: str) -> dict:
    base = f"/v1/public/galleries/{token}/photos/{p.id}"
    return {
        "id": p.id,
        "name": p.name,
        "tier": tier,
        "taken_at": p.taken_at.isoformat() if p.taken_at else None,
        "facets": {k: v for k, v in p.facets.items() if k != "pasta"},
        "width": p.width,
        "height": p.height,
        "thumb": f"{base}/thumb",
        "preview": f"{base}/preview",
        "original": f"{base}/original",
    }


@router.get("/galleries/{token}")
def gallery(
    token: str,
    tier: str = "certain",
    offset: int = 0,
    limit: int = 60,
    session: Session = Depends(get_session),
):
    if tier not in ("certain", "maybe"):
        raise HTTPException(400, "tier inválido")
    search_row, event = _gallery(token, session)
    limit = max(1, min(limit, 200))
    rows = session.execute(
        select(Photo, SearchResult.tier)
        .join(SearchResult, SearchResult.photo_id == Photo.id)
        .where(
            SearchResult.search_id == search_row.id,
            SearchResult.tier == tier,
            Photo.visible.is_(True),
        )
        .order_by(SearchResult.rank)
        .offset(max(offset, 0))
        .limit(limit)
    ).all()
    counts = {
        t: session.scalar(
            select(func.count())
            .select_from(SearchResult)
            .join(Photo, Photo.id == SearchResult.photo_id)
            .where(
                SearchResult.search_id == search_row.id,
                SearchResult.tier == t,
                Photo.visible.is_(True),
            )
        )
        or 0
        for t in ("certain", "maybe")
    }
    return {
        "event": {"slug": event.slug, "name": event.name},
        "counts": counts,
        "tier": tier,
        "offset": offset,
        "items": [_photo_json(token, p, t) for p, t in rows],
    }


@router.get("/galleries/{token}/photos/{photo_id}/{kind}")
def photo_file(token: str, photo_id: str, kind: str, session: Session = Depends(get_session)):
    if kind not in ("thumb", "preview", "original"):
        raise HTTPException(404)
    search_row, event = _gallery(token, session)
    photo = _photo_in_gallery(session, search_row.id, photo_id)
    if kind == "original":
        source = source_for(event)
        ctype = mimetypes.guess_type(photo.name)[0] or "application/octet-stream"
        disp = f"attachment; filename*=UTF-8''{quote(photo.name)}"
        return StreamingResponse(
            source.stream(photo.source_id),
            media_type=ctype,
            headers={"Content-Disposition": disp, "Cache-Control": "private, max-age=3600"},
        )
    path = get_store().path(event.tenant_id, event.id, photo.id, kind)
    if path is None:
        raise HTTPException(404, "Arquivo ainda não disponível")
    return FileResponse(
        path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"}
    )


class _Sink:
    """Destino não-seekable para o ZipFile: acumula bytes e os entrega aos poucos."""

    def __init__(self) -> None:
        self.chunks: deque[bytes] = deque()
        self._pos = 0

    def write(self, b) -> int:
        self.chunks.append(bytes(b))
        self._pos += len(b)
        return len(b)

    def tell(self) -> int:
        return self._pos

    def flush(self) -> None:
        pass

    def drain(self) -> Iterator[bytes]:
        while self.chunks:
            yield self.chunks.popleft()


def _zip_stream(event: Event, photos: list[Photo]) -> Iterator[bytes]:
    source = source_for(event)
    sink = _Sink()
    used: set[str] = set()
    with zipfile.ZipFile(sink, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
        for p in photos:
            name = p.name
            if name in used:
                name = f"{p.id[:6]}_{name}"
            used.add(name)
            with zf.open(
                zipfile.ZipInfo(name, time.localtime()[:6]), "w", force_zip64=True
            ) as dest:
                for chunk in source.stream(p.source_id):
                    dest.write(chunk)
                    yield from sink.drain()
            yield from sink.drain()
    yield from sink.drain()


@router.get("/galleries/{token}/zip")
def gallery_zip(
    token: str,
    tier: str = "certain",
    ids: str | None = None,
    session: Session = Depends(get_session),
):
    search_row, event = _gallery(token, session)
    q = (
        select(Photo)
        .join(SearchResult, SearchResult.photo_id == Photo.id)
        .where(SearchResult.search_id == search_row.id, Photo.visible.is_(True))
        .order_by(SearchResult.rank)
    )
    if ids:
        wanted = [i for i in ids.split(",") if i][:300]
        q = q.where(Photo.id.in_(wanted))
    elif tier in ("certain", "maybe"):
        q = q.where(SearchResult.tier == tier)
    photos = list(session.scalars(q))
    if not photos:
        raise HTTPException(404, "Nenhuma foto para baixar")
    filename = quote(f"fotos-{event.slug}.zip")
    return StreamingResponse(
        _zip_stream(event, photos),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


class FeedbackBody(BaseModel):
    kind: str = Field(pattern="^(not_me|remove)$")


@router.post("/galleries/{token}/photos/{photo_id}/feedback")
def feedback(
    token: str, photo_id: str, body: FeedbackBody, session: Session = Depends(get_session)
):
    search_row, event = _gallery(token, session)
    photo = _photo_in_gallery(session, search_row.id, photo_id)
    session.add(
        Feedback(
            tenant_id=event.tenant_id,
            event_id=event.id,
            photo_id=photo.id,
            search_id=search_row.id,
            kind=body.kind,
        )
    )
    if body.kind == "remove":  # RN8: oculta já; a decisão final é humana
        from flash.api.admin import set_photo_visibility

        set_photo_visibility(session, photo, False)
        get_index().invalidate(event.id)
    return {"ok": True}
