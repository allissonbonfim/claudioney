from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
# Pastas que o fotógrafo marca como privadas nunca entram no índice (RN9).
PRIVATE_PREFIXES = ("_nao_publicar", "_privado", "_private")


@dataclass(slots=True)
class SourceFile:
    id: str  # id no Drive / caminho relativo na pasta local
    name: str
    checksum: str  # md5 do Drive; "tamanho:mtime" no local
    size: int = 0
    modified: datetime | None = None
    path_parts: tuple[str, ...] = field(default_factory=tuple)  # subpastas → facetas


class SourceConnector(Protocol):
    def list_files(self) -> Iterator[SourceFile]: ...

    def read(self, file_id: str) -> bytes: ...

    def stream(self, file_id: str, chunk_size: int = 1 << 20) -> Iterator[bytes]: ...


def is_private(parts: tuple[str, ...]) -> bool:
    return any(p.lower().startswith(PRIVATE_PREFIXES) for p in parts)
