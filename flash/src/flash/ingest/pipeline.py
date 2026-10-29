"""Descoberta de arquivos e indexação de uma foto (docs/03, fluxo A)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from flash import imaging
from flash.config import get_settings
from flash.db import Event, Face, Photo, new_id, utcnow
from flash.faces import FaceEngine, get_engine
from flash.ingest.queue import enqueue
from flash.sources import SourceConnector, source_for
from flash.storage import DerivativeStore, get_store

MIN_DET_SCORE = 0.6


def facets_from_path(event: Event, parts: tuple[str, ...]) -> dict:
    """Subpastas viram facetas: `Sábado/Vôlei` → {"dia": "Sábado", "modalidade": "Vôlei"}."""
    names: list[str] = event.config.get("facet_names", [])
    facets = {"pasta": "/".join(parts)} if parts else {}
    for i, part in enumerate(parts):
        facets[names[i] if i < len(names) else f"nivel{i + 1}"] = part
    return facets


@dataclass(slots=True)
class ScanReport:
    found: int = 0
    new: int = 0
    replaced: int = 0
    unchanged: int = 0


def scan_event(session: Session, event: Event, source: SourceConnector | None = None) -> ScanReport:
    """Lista a fonte e enfileira o que é novo. Idempotente: pode rodar a cada minuto."""
    source = source or source_for(event)
    report = ScanReport()
    known = {
        (p.source_id, p.checksum): p
        for p in session.scalars(select(Photo).where(Photo.event_id == event.id))
    }
    by_source: dict[str, list[Photo]] = {}
    for p in known.values():
        by_source.setdefault(p.source_id, []).append(p)

    for f in source.list_files():
        report.found += 1
        if (f.id, f.checksum) in known:
            report.unchanged += 1
            continue
        # Mesmo arquivo com conteúdo novo: o antigo deixa de aparecer nas buscas.
        for old in by_source.get(f.id, []):
            if old.visible:
                old.visible = False
                session.execute(update(Face).where(Face.photo_id == old.id).values(visible=False))
                report.replaced += 1
        photo = Photo(
            id=new_id(),
            tenant_id=event.tenant_id,
            event_id=event.id,
            source_id=f.id,
            checksum=f.checksum,
            name=f.name,
            facets=facets_from_path(event, f.path_parts),
        )
        session.add(photo)
        enqueue(session, "index_photo", photo.id)
        report.new += 1

    if event.status == "draft" and report.new:
        event.status = "indexing"
    session.flush()
    return report


def process_photo(
    session: Session,
    photo_id: str,
    source: SourceConnector | None = None,
    engine: FaceEngine | None = None,
    store: DerivativeStore | None = None,
) -> int:
    """Baixa, gera derivados, detecta rostos e grava vetores. Devolve nº de rostos."""
    settings = get_settings()
    photo = session.get(Photo, photo_id)
    if photo is None:
        return 0
    event = session.get(Event, photo.event_id)
    assert event is not None
    source = source or source_for(event)
    engine = engine or get_engine(event.engine)
    store = store or get_store()

    data = source.read(photo.source_id)
    work, taken_at, (ow, oh) = imaging.decode(data, settings.work_max_px)

    preview = imaging.resized(work, settings.preview_px)
    thumb = imaging.resized(work, settings.thumb_px)
    store.put(event.tenant_id, event.id, photo.id, "preview", imaging.jpeg_bytes(preview, 82))
    store.put(event.tenant_id, event.id, photo.id, "thumb", imaging.jpeg_bytes(thumb, 78))

    # Reindexar nunca duplica rostos.
    session.query(Face).filter(Face.photo_id == photo.id).delete()
    faces = [
        f for f in engine.detect_and_embed(imaging.to_bgr(work)) if f.det_score >= MIN_DET_SCORE
    ]

    # As caixas ficam nas coordenadas da imagem de trabalho (≤ 2048 px).
    for f in faces:
        session.add(
            Face(
                tenant_id=photo.tenant_id,
                event_id=photo.event_id,
                photo_id=photo.id,
                x=f.x,
                y=f.y,
                w=f.w,
                h=f.h,
                det_score=f.det_score,
                quality=f.quality,
                embedding=f.embedding.astype(np.float16).tobytes(),
                index_version=event.index_version,
                visible=photo.visible,
            )
        )
    photo.width, photo.height = ow, oh
    photo.taken_at = taken_at
    photo.phash = imaging.dhash(thumb)
    photo.status = "indexed"
    photo.error = None
    photo.indexed_at = utcnow()
    return len(faces)


def event_progress(session: Session, event_id: str) -> dict:
    rows = dict(
        session.execute(
            select(Photo.status, func.count())
            .where(Photo.event_id == event_id)
            .group_by(Photo.status)
        ).all()
    )
    faces = session.scalar(select(func.count()).select_from(Face).where(Face.event_id == event_id))
    total = sum(rows.values())
    return {
        "total": total,
        "indexed": rows.get("indexed", 0),
        "pending": rows.get("discovered", 0),
        "error": rows.get("error", 0),
        "faces": faces or 0,
    }
