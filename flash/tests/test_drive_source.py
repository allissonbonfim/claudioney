from __future__ import annotations

from flash.sources.drive import FOLDER_MIME, DriveSource


class _Req:
    def __init__(self, data):
        self._data = data

    def execute(self):
        return self._data


class FakeFiles:
    """Árvore: raiz → [Sabado/(a.jpg, nota.txt), _nao_publicar/(x.jpg), b.png]."""

    tree = {
        "root": [
            {"id": "f1", "name": "Sabado", "mimeType": FOLDER_MIME},
            {"id": "f2", "name": "_nao_publicar", "mimeType": FOLDER_MIME},
            {
                "id": "i3",
                "name": "b.png",
                "mimeType": "image/png",
                "md5Checksum": "m3",
                "size": "10",
                "modifiedTime": "2026-10-20T10:00:00.000Z",
            },
        ],
        "f1": [
            {
                "id": "i1",
                "name": "a.jpg",
                "mimeType": "image/jpeg",
                "md5Checksum": "m1",
                "size": "5",
            },
            {"id": "t1", "name": "nota.txt", "mimeType": "text/plain"},
        ],
        "f2": [{"id": "i2", "name": "x.jpg", "mimeType": "image/jpeg", "md5Checksum": "m2"}],
    }

    def list(self, q, **kw):
        parent = q.split("'")[1]
        return _Req({"files": self.tree.get(parent, [])})


class FakeService:
    def files(self):
        return FakeFiles()


def test_drive_lists_images_recursively_and_skips_private_folders():
    src = DriveSource("root", service=FakeService())
    files = {f.name: f for f in src.list_files()}
    assert set(files) == {"a.jpg", "b.png"}
    assert files["a.jpg"].path_parts == ("Sabado",)
    assert files["a.jpg"].checksum == "m1" and files["b.png"].modified.year == 2026
