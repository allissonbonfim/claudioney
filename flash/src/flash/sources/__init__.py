from __future__ import annotations

from flash.config import get_settings
from flash.db import Event
from flash.sources.base import SourceConnector, SourceFile


def source_for(event: Event) -> SourceConnector:
    if event.source_type == "local":
        from flash.sources.local import LocalSource

        return LocalSource(event.source_ref)
    if event.source_type == "drive":
        from flash.sources.drive import DriveSource

        return DriveSource(event.source_ref, get_settings().google_credentials_file)
    raise ValueError(f"Fonte desconhecida: {event.source_type}")


__all__ = ["SourceConnector", "SourceFile", "source_for"]
