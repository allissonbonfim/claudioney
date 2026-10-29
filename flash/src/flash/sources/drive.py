"""Google Drive via conta de serviço (o cliente compartilha a pasta com o e-mail da conta).

Escopo somente leitura. Não usa OAuth de usuário (escopo restrito exigiria auditoria do Google).
"""

from __future__ import annotations

import io
import threading
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from flash.sources.base import IMAGE_EXTENSIONS, SourceFile, is_private

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_MIME = "application/vnd.google-apps.folder"
_FIELDS = "nextPageToken, files(id, name, mimeType, md5Checksum, size, modifiedTime)"
_RETRY_STATUS = {403, 429, 500, 502, 503, 504}


def _retry(fn, attempts: int = 5):
    """Backoff exponencial para cotas (403/429) e erros transitórios do Drive."""
    for i in range(attempts):
        try:
            return fn()
        except HttpError as exc:
            status = getattr(exc.resp, "status", 0)
            if status not in _RETRY_STATUS or i == attempts - 1:
                raise
            time.sleep(min(2**i, 30))


class DriveSource:
    def __init__(self, folder_id: str, credentials_file: Path | None = None, service=None):
        self.folder_id = folder_id
        self._credentials_file = credentials_file
        self._service = service  # injetável nos testes
        self._tls = threading.local()  # o cliente httplib2 não é thread-safe

    def _svc(self):
        if self._service is not None:
            return self._service
        if not hasattr(self._tls, "svc"):
            from google.oauth2 import service_account

            if not self._credentials_file:
                raise RuntimeError(
                    "Defina FLASH_GOOGLE_CREDENTIALS_FILE (JSON da conta de serviço)"
                )
            creds = service_account.Credentials.from_service_account_file(
                str(self._credentials_file), scopes=SCOPES
            )
            self._tls.svc = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._tls.svc

    def _list_children(self, parent: str) -> Iterator[dict]:
        token = None
        while True:
            resp = _retry(
                lambda tok=token: (
                    self._svc()
                    .files()
                    .list(
                        q=f"'{parent}' in parents and trashed = false",
                        fields=_FIELDS,
                        pageSize=1000,
                        pageToken=tok,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
            )
            yield from resp.get("files", [])
            token = resp.get("nextPageToken")
            if not token:
                return

    def list_files(self) -> Iterator[SourceFile]:
        stack: list[tuple[str, tuple[str, ...]]] = [(self.folder_id, ())]
        while stack:
            folder, parts = stack.pop()
            for item in self._list_children(folder):
                if item["mimeType"] == FOLDER_MIME:
                    sub = (*parts, item["name"])
                    if not is_private(sub):
                        stack.append((item["id"], sub))
                    continue
                name = item["name"]
                is_image = item["mimeType"].startswith("image/") and (
                    Path(name).suffix.lower() in IMAGE_EXTENSIONS
                )
                if not is_image:
                    continue
                modified = None
                if item.get("modifiedTime"):
                    modified = datetime.fromisoformat(item["modifiedTime"].replace("Z", "+00:00"))
                    modified = modified.replace(tzinfo=None)
                yield SourceFile(
                    id=item["id"],
                    name=name,
                    checksum=item.get("md5Checksum", ""),
                    size=int(item.get("size", 0)),
                    modified=modified,
                    path_parts=parts,
                )

    def read(self, file_id: str) -> bytes:
        return b"".join(self.stream(file_id))

    def stream(self, file_id: str, chunk_size: int = 4 << 20) -> Iterator[bytes]:
        request = self._svc().files().get_media(fileId=file_id, supportsAllDrives=True)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request, chunksize=chunk_size)
        done = False
        while not done:
            _, done = _retry(downloader.next_chunk)
            data = buf.getvalue()
            if data:
                yield data
                buf.seek(0)
                buf.truncate(0)
