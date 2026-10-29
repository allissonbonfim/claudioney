"""Rotas administrativas (operador / cliente). Prefixo /v1/admin, protegidas por token."""

from __future__ import annotations

import mimetypes
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from flash import security
from flash.api.deps import require_admin
from flash.db import Event, Face, Feedback, Photo, Search, Tenant, get_session, utcnow
from flash.index.vector import get_index
from flash.ingest.pipeline import event_progress, scan_event
from flash.storage import get_store

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])

SLUG = r"^[a-z0-9][a-z0-9\-]{1,78}$"


def set_photo_visibility(session: Session, photo: Photo, visible: bool) -> None:
    photo.visible = visible
    session.execute(update(Face).where(Face.photo_id == photo.id).values(visible=visible))


# --------------------------------------------------------------------------- clientes
class TenantBody(BaseModel):
    slug: str = Field(pattern=SLUG)
    name: str = Field(min_length=2, max_length=200)
    config: dict = {}


@router.post("/tenants", status_code=201)
def create_tenant(body: TenantBody, session: Session = Depends(get_session)):
    if session.scalar(select(Tenant).where(Tenant.slug == body.slug)):
        raise HTTPException(409, "Slug já existe")
    t = Tenant(slug=body.slug, name=body.name, config=body.config)
    session.add(t)
    session.flush()
    return {"id": t.id, "slug": t.slug}


@router.get("/tenants")
def list_tenants(session: Session = Depends(get_session)):
    return [{"id": t.id, "slug": t.slug, "name": t.name} for t in session.scalars(select(Tenant))]


@router.patch("/tenants/{slug}")
def update_tenant(slug: str, config: dict, session: Session = Depends(get_session)):
    t = session.scalar(select(Tenant).where(Tenant.slug == slug))
    if t is None:
        raise HTTPException(404)
    t.config = {**t.config, **config}
    return {"ok": True}


# --------------------------------------------------------------------------- eventos
class EventBody(BaseModel):
    tenant_slug: str
    slug: str = Field(pattern=SLUG)
    name: str = Field(min_length=2, max_length=200)
    source_type: str = Field(pattern="^(drive|local)$")
    source_ref: str = Field(min_length=1, max_length=500)
    engine: str = "sface"
    has_minors: bool = True
    access_code: str | None = Field(default=None, max_length=64)
    starts_on: str | None = None
    ends_on: str | None = None
    config: dict = {}


class EventPatch(BaseModel):
    name: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|indexing|open|closed|archived)$")
    has_minors: bool | None = None
    access_code: str | None = None  # "" remove o código
    config: dict | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)


def _event_json(e: Event) -> dict:
    return {
        "id": e.id,
        "slug": e.slug,
        "name": e.name,
        "status": e.status,
        "source_type": e.source_type,
        "source_ref": e.source_ref,
        "engine": e.engine,
        "has_minors": e.has_minors,
        "requires_code": bool(e.access_code_hash),
        "starts_on": e.starts_on,
        "ends_on": e.ends_on,
        "config": e.config,
        "retention_until": e.retention_until,
    }


@router.post("/events", status_code=201)
def create_event(body: EventBody, session: Session = Depends(get_session)):
    tenant = session.scalar(select(Tenant).where(Tenant.slug == body.tenant_slug))
    if tenant is None:
        raise HTTPException(404, "Cliente não encontrado")
    if session.scalar(select(Event).where(Event.tenant_id == tenant.id, Event.slug == body.slug)):
        raise HTTPException(409, "Slug de evento já existe")
    e = Event(
        tenant_id=tenant.id,
        slug=body.slug,
        name=body.name,
        source_type=body.source_type,
        source_ref=body.source_ref,
        engine=body.engine,
        has_minors=body.has_minors,
        access_code_hash=security.hash_code(body.access_code) if body.access_code else None,
        starts_on=body.starts_on,
        ends_on=body.ends_on,
        config=body.config,
    )
    session.add(e)
    session.flush()
    return _event_json(e)


@router.get("/events")
def list_events(tenant: str | None = None, session: Session = Depends(get_session)):
    q = select(Event).order_by(Event.created_at.desc())
    if tenant:
        q = q.join(Tenant, Tenant.id == Event.tenant_id).where(Tenant.slug == tenant)
    return [_event_json(e) for e in session.scalars(q)]


def _event(session: Session, event_id: str) -> Event:
    e = session.get(Event, event_id)
    if e is None:
        raise HTTPException(404, "Evento não encontrado")
    return e


@router.get("/events/{event_id}")
def get_event(event_id: str, session: Session = Depends(get_session)):
    e = _event(session, event_id)
    return {**_event_json(e), "progress": event_progress(session, e.id)}


@router.patch("/events/{event_id}")
def patch_event(event_id: str, body: EventPatch, session: Session = Depends(get_session)):
    e = _event(session, event_id)
    if body.name is not None:
        e.name = body.name
    if body.status is not None:
        e.status = body.status
    if body.has_minors is not None:
        e.has_minors = body.has_minors
    if body.access_code is not None:
        e.access_code_hash = security.hash_code(body.access_code) if body.access_code else None
    if body.config is not None:
        e.config = {**e.config, **body.config}
    if body.retention_days is not None:
        e.retention_until = (utcnow() + timedelta(days=body.retention_days)).date().isoformat()
    return _event_json(e)


@router.get("/events/{event_id}/progress")
def progress(event_id: str, session: Session = Depends(get_session)):
    return event_progress(session, _event(session, event_id).id)


@router.post("/events/{event_id}/scan")
def scan(event_id: str, session: Session = Depends(get_session)):
    e = _event(session, event_id)
    try:
        report = scan_event(session, e)
    except (FileNotFoundError, PermissionError, RuntimeError) as exc:
        raise HTTPException(400, f"Não consegui acessar a fonte: {exc}") from exc
    return {
        "found": report.found,
        "new": report.new,
        "replaced": report.replaced,
        "unchanged": report.unchanged,
    }


@router.get("/events/{event_id}/metrics")
def metrics(event_id: str, session: Session = Depends(get_session)):
    e = _event(session, event_id)
    total, ok, avg_ms = session.execute(
        select(
            func.count(),
            func.coalesce(func.sum(case((Search.n_certain + Search.n_maybe > 0, 1), else_=0)), 0),
            func.coalesce(func.avg(Search.latency_ms), 0),
        ).where(Search.event_id == e.id)
    ).one()
    fb = dict(
        session.execute(
            select(Feedback.kind, func.count())
            .where(Feedback.event_id == e.id)
            .group_by(Feedback.kind)
        ).all()
    )
    return {
        "searches": total,
        "with_results": int(ok or 0),
        "success_rate": round((ok or 0) / total, 3) if total else None,
        "avg_latency_ms": int(avg_ms or 0),
        "feedback": fb,
        "progress": event_progress(session, e.id),
    }


# --------------------------------------------------------------------------- moderação
@router.get("/events/{event_id}/photos")
def list_photos(
    event_id: str,
    status: str | None = None,
    hidden: bool = False,
    offset: int = 0,
    limit: int = 60,
    session: Session = Depends(get_session),
):
    e = _event(session, event_id)
    q = select(Photo).where(Photo.event_id == e.id, Photo.visible.is_(not hidden))
    if status:
        q = q.where(Photo.status == status)
    rows = session.scalars(
        q.order_by(Photo.created_at.desc()).offset(offset).limit(min(limit, 200))
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "error": p.error,
            "visible": p.visible,
            "thumb": f"/v1/admin/photos/{p.id}/thumb",
        }
        for p in rows
    ]


@router.get("/photos/{photo_id}/thumb")
def admin_thumb(photo_id: str, session: Session = Depends(get_session)):
    p = session.get(Photo, photo_id)
    if p is None:
        raise HTTPException(404)
    path = get_store().path(p.tenant_id, p.event_id, p.id, "thumb")
    if path is None:
        raise HTTPException(404)
    return FileResponse(path, media_type=mimetypes.types_map[".jpg"])


@router.post("/photos/{photo_id}/hide")
def hide(photo_id: str, session: Session = Depends(get_session)):
    p = session.get(Photo, photo_id)
    if p is None:
        raise HTTPException(404)
    set_photo_visibility(session, p, False)
    get_index().invalidate(p.event_id)
    return {"ok": True}


@router.post("/photos/{photo_id}/show")
def show(photo_id: str, session: Session = Depends(get_session)):
    p = session.get(Photo, photo_id)
    if p is None:
        raise HTTPException(404)
    set_photo_visibility(session, p, True)
    get_index().invalidate(p.event_id)
    return {"ok": True}


@router.get("/feedback")
def list_feedback(status: str = "open", session: Session = Depends(get_session)):
    rows = session.scalars(
        select(Feedback).where(Feedback.status == status).order_by(Feedback.id.desc()).limit(200)
    )
    return [
        {
            "id": f.id,
            "event_id": f.event_id,
            "photo_id": f.photo_id,
            "kind": f.kind,
            "created_at": f.created_at.isoformat(),
        }
        for f in rows
    ]
