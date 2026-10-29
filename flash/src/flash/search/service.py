"""Caso de uso central: selfie → fotos. Independe do canal (site, Instagram, WhatsApp...)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flash.db import Event, Photo, Search, SearchResult, utcnow
from flash.faces import Thresholds, get_engine
from flash.index.vector import get_index

TOP_K_FACES = 1500


@dataclass(slots=True)
class PhotoHit:
    photo_id: str
    sim: float
    quality: float
    tier: str  # certain | maybe


@dataclass(slots=True)
class SearchOutcome:
    search_id: str
    certain: list[PhotoHit]
    maybe: list[PhotoHit]
    latency_ms: int


class RateLimited(Exception):
    pass


def thresholds_for(event: Event) -> Thresholds:
    base = get_engine(event.engine).default_thresholds
    over = event.config.get("thresholds", {})
    return Thresholds(
        certain=float(over.get("certain", base.certain)),
        maybe=float(over.get("maybe", base.maybe)),
        min_quality_certain=float(over.get("min_quality_certain", base.min_quality_certain)),
    )


def searches_today(session: Session, event_id: str, subject: str) -> int:
    since = utcnow() - timedelta(hours=24)
    return (
        session.scalar(
            select(func.count())
            .select_from(Search)
            .where(
                Search.event_id == event_id,
                Search.subject_ref == subject,
                Search.created_at >= since,
            )
        )
        or 0
    )


def run_search(
    session: Session,
    event: Event,
    vectors: np.ndarray,
    *,
    subject: str,
    channel: str,
    quality: float,
    daily_limit: int,
) -> SearchOutcome:
    if searches_today(session, event.id, subject) >= daily_limit:
        raise RateLimited("Limite diário de buscas atingido")

    t0 = time.perf_counter()
    th = thresholds_for(event)
    hits = get_index().search(session, event.id, event.index_version, vectors, TOP_K_FACES)

    best: dict[str, PhotoHit] = {}
    for h in hits:
        if h.sim < th.maybe:
            break  # `hits` vem ordenado por similaridade decrescente
        tier = (
            "certain" if (h.sim >= th.certain and h.quality >= th.min_quality_certain) else "maybe"
        )
        cur = best.get(h.photo_id)
        if (
            cur is None
            or (tier == "certain" and cur.tier == "maybe")
            or (tier == cur.tier and h.sim > cur.sim)
        ):
            best[h.photo_id] = PhotoHit(h.photo_id, h.sim, h.quality, tier)

    visible = (
        set(
            session.scalars(
                select(Photo.id).where(
                    Photo.id.in_(list(best)), Photo.visible.is_(True), Photo.status == "indexed"
                )
            )
        )
        if best
        else set()
    )
    ordered = sorted((b for b in best.values() if b.photo_id in visible), key=lambda b: -b.sim)
    certain = [b for b in ordered if b.tier == "certain"]
    maybe = [b for b in ordered if b.tier == "maybe"]

    latency = int((time.perf_counter() - t0) * 1000)
    search = Search(
        tenant_id=event.tenant_id,
        event_id=event.id,
        channel=channel,
        subject_ref=subject,
        quality=quality,
        n_certain=len(certain),
        n_maybe=len(maybe),
        latency_ms=latency,
    )
    session.add(search)
    session.flush()
    for rank, hit in enumerate([*certain, *maybe]):
        session.add(
            SearchResult(
                search_id=search.id, photo_id=hit.photo_id, tier=hit.tier, sim=hit.sim, rank=rank
            )
        )
    return SearchOutcome(search.id, certain, maybe, latency)
