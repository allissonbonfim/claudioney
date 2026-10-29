"""Pasta local — desenvolvimento, testes e eventos sem Drive."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from flash.sources.base import IMAGE_EXTENSIONS, SourceFile, is_private


class LocalSource:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"Pasta não encontrada: {self.root}")

    def list_files(self) -> Iterator[SourceFile]:
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            rel = path.relative_to(self.root)
            parts = rel.parts[:-1]
            if is_private(parts) or path.name.startswith("."):
                continue
            st = path.stat()
            yield SourceFile(
                id=rel.as_posix(),
                name=path.name,
                checksum=f"{st.st_size}:{st.st_mtime_ns}",
                size=st.st_size,
                modified=datetime.fromtimestamp(st.st_mtime),
                path_parts=parts,
            )

    def _path(self, file_id: str) -> Path:
        path = (self.root / file_id).resolve()
        if not path.is_relative_to(self.root):  # evita "../" vindo de dados corrompidos
            raise PermissionError("Caminho fora da pasta do evento")
        return path

    def read(self, file_id: str) -> bytes:
        return self._path(file_id).read_bytes()

    def stream(self, file_id: str, chunk_size: int = 1 << 20) -> Iterator[bytes]:
        with self._path(file_id).open("rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk
