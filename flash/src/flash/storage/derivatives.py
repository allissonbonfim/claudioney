"""Derivados regeneráveis (miniatura e preview). O permanente vive no Drive (ADR-019).

Interface pequena para trocar o destino (disco → R2/S3) sem tocar no resto do código.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

KINDS = ("thumb", "preview")


class DerivativeStore(Protocol):
    def put(self, tenant_id: str, event_id: str, photo_id: str, kind: str, data: bytes) -> None: ...

    def path(self, tenant_id: str, event_id: str, photo_id: str, kind: str) -> Path | None: ...

    def delete_photo(self, tenant_id: str, event_id: str, photo_id: str) -> None: ...


class LocalDerivativeStore:
    def __init__(self, root: Path):
        self.root = root

    def _file(self, tenant_id: str, event_id: str, photo_id: str, kind: str) -> Path:
        if kind not in KINDS:
            raise ValueError(f"Tipo de derivado inválido: {kind}")
        return self.root / tenant_id / event_id / photo_id[:2] / f"{photo_id}.{kind}.jpg"

    def put(self, tenant_id: str, event_id: str, photo_id: str, kind: str, data: bytes) -> None:
        target = self._file(tenant_id, event_id, photo_id, kind)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)  # escrita atômica

    def path(self, tenant_id: str, event_id: str, photo_id: str, kind: str) -> Path | None:
        target = self._file(tenant_id, event_id, photo_id, kind)
        return target if target.exists() else None

    def delete_photo(self, tenant_id: str, event_id: str, photo_id: str) -> None:
        for kind in KINDS:
            self._file(tenant_id, event_id, photo_id, kind).unlink(missing_ok=True)
