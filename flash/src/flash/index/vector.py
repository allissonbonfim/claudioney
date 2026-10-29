"""Busca vetorial exata por evento (ADR-005/020).

`NumpyIndex` mantém, por evento, uma matriz float32 em memória (rostos × dimensão) e a atualiza
de forma incremental quando entram rostos novos. Para eventos muito grandes (> ~500 mil rostos) a
mesma interface ganha uma implementação com pgvector/HNSW.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flash.db import Face


@dataclass(slots=True)
class FaceHit:
    face_id: int
    photo_id: str
    sim: float
    quality: float


class VectorIndex(Protocol):
    def search(
        self, session: Session, event_id: str, index_version: int, queries: np.ndarray, k: int
    ) -> list[FaceHit]: ...


@dataclass
class _Matrix:
    dim: int
    mat: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), np.float32))
    face_ids: np.ndarray = field(default_factory=lambda: np.zeros(0, np.int64))
    quality: np.ndarray = field(default_factory=lambda: np.zeros(0, np.float32))
    photo_ids: list[str] = field(default_factory=list)
    max_id: int = 0
    count: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


class NumpyIndex:
    def __init__(self) -> None:
        self._events: dict[tuple[str, int], _Matrix] = {}
        self._guard = threading.Lock()

    def invalidate(self, event_id: str | None = None) -> None:
        with self._guard:
            if event_id is None:
                self._events.clear()
            else:
                for key in [k for k in self._events if k[0] == event_id]:
                    del self._events[key]

    def _matrix(self, key: tuple[str, int]) -> _Matrix:
        with self._guard:
            return self._events.setdefault(key, _Matrix(dim=0))

    @staticmethod
    def _base(event_id: str, version: int):
        return (
            Face.event_id == event_id,
            Face.visible.is_(True),
            Face.index_version == version,
            Face.embedding.is_not(None),
        )

    def _refresh(self, session: Session, event_id: str, version: int) -> _Matrix:
        m = self._matrix((event_id, version))
        with m.lock:
            base = self._base(event_id, version)
            count_now, max_now = session.execute(
                select(func.count(), func.coalesce(func.max(Face.id), 0)).where(*base)
            ).one()
            if count_now == m.count and max_now == m.max_id:
                return m
            new_rows = session.scalar(select(func.count()).where(*base, Face.id > m.max_id)) or 0
            append_only = m.count + new_rows == count_now and m.count > 0
            after = m.max_id if append_only else 0
            rows = session.execute(
                select(Face.id, Face.photo_id, Face.quality, Face.embedding)
                .where(*base, Face.id > after)
                .order_by(Face.id)
            ).all()
            if rows:
                vecs = np.stack([np.frombuffer(r.embedding, dtype=np.float16) for r in rows])
                vecs = vecs.astype(np.float32)
                ids = np.array([r.id for r in rows], dtype=np.int64)
                qual = np.array([r.quality for r in rows], dtype=np.float32)
                photos = [r.photo_id for r in rows]
            else:
                vecs = np.zeros((0, m.dim or 1), np.float32)
                ids = np.zeros(0, np.int64)
                qual = np.zeros(0, np.float32)
                photos = []
            if append_only:
                m.mat = np.vstack([m.mat, vecs])
                m.face_ids = np.concatenate([m.face_ids, ids])
                m.quality = np.concatenate([m.quality, qual])
                m.photo_ids.extend(photos)
            else:
                m.mat, m.face_ids, m.quality, m.photo_ids = vecs, ids, qual, photos
            m.dim = m.mat.shape[1] if m.mat.size else m.dim
            m.max_id, m.count = int(max_now), int(count_now)
            return m

    def search(
        self, session: Session, event_id: str, index_version: int, queries: np.ndarray, k: int
    ) -> list[FaceHit]:
        m = self._refresh(session, event_id, index_version)
        if m.mat.shape[0] == 0:
            return []
        q = np.atleast_2d(queries).astype(np.float32)
        sims = (m.mat @ q.T).max(axis=1)  # melhor entre as selfies enviadas
        k = min(k, sims.shape[0])
        top = np.argpartition(-sims, k - 1)[:k]
        top = top[np.argsort(-sims[top])]
        return [
            FaceHit(int(m.face_ids[i]), m.photo_ids[i], float(sims[i]), float(m.quality[i]))
            for i in top
        ]


_index = NumpyIndex()


def get_index() -> NumpyIndex:
    return _index
