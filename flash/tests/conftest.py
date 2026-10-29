from __future__ import annotations

import colorsys
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

HUES = {"ana": 0, "bia": 60, "caio": 120, "dani": 180, "edu": 240}


def _rgb(name: str) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(HUES[name] / 360, 1.0, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


def make_photo(path: Path, people: list[str], size=(900, 600)) -> Path:
    """Foto cinza com um quadrado colorido por pessoa (o motor falso trata como rosto)."""
    img = Image.new("RGB", size, (128, 128, 128))
    d = ImageDraw.Draw(img)
    for i, name in enumerate(people):
        x = 60 + i * 220
        d.rectangle([x, 150, x + 130, 280], fill=_rgb(name))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=92)
    return path


def selfie_bytes(name: str, extra: str | None = None) -> bytes:
    img = Image.new("RGB", (640, 640), (128, 128, 128))
    d = ImageDraw.Draw(img)
    d.rectangle([200, 200, 440, 440], fill=_rgb(name))
    if extra:
        d.rectangle([20, 20, 150, 150], fill=_rgb(extra))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FLASH_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("FLASH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FLASH_ENGINE", "fake")
    monkeypatch.setenv("FLASH_SECRET", "segredo-de-teste-com-mais-de-32-bytes-ok")
    monkeypatch.setenv("FLASH_ADMIN_TOKEN", "admin-teste")
    monkeypatch.setenv("FLASH_WEB_DIST", str(tmp_path / "nao-existe"))

    from flash import faces
    from flash.api.deps import limiter
    from flash.config import get_settings
    from flash.db import init_db, reset_engine
    from flash.index.vector import get_index
    from flash.ingest.worker import forget_sources
    from flash.storage import reset_store

    def reset():
        get_settings.cache_clear()
        reset_engine()
        reset_store()
        get_index().invalidate()
        forget_sources()
        limiter.reset()
        faces._engines.clear()

    reset()
    init_db()
    yield tmp_path
    reset()


@pytest.fixture()
def photos_dir(env) -> Path:
    root = env / "fotos"
    make_photo(root / "Sabado" / "Volei" / "a1.jpg", ["ana", "bia"])
    make_photo(root / "Sabado" / "Volei" / "a2.jpg", ["ana"])
    make_photo(root / "Domingo" / "Futsal" / "c1.jpg", ["caio"])
    make_photo(root / "Domingo" / "Futsal" / "b1.jpg", ["bia", "dani"])
    make_photo(root / "_nao_publicar" / "x.jpg", ["ana"])
    return root


@pytest.fixture()
def client(env):
    from flash.api.main import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture()
def admin():
    return {"Authorization": "Bearer admin-teste"}


@pytest.fixture()
def indexed_event(client, admin, photos_dir):
    """Cliente + evento (aberto, sem código) com as fotos já indexadas."""
    from flash.ingest.worker import run_worker

    assert (
        client.post(
            "/v1/admin/tenants", headers=admin, json={"slug": "cbde", "name": "CBDE"}
        ).status_code
        == 201
    )
    r = client.post(
        "/v1/admin/events",
        headers=admin,
        json={
            "tenant_slug": "cbde",
            "slug": "jebs-2026",
            "name": "JEBs 2026",
            "source_type": "local",
            "source_ref": str(photos_dir),
            "engine": "fake",
            "config": {"facet_names": ["dia", "modalidade"]},
        },
    )
    assert r.status_code == 201, r.text
    eid = r.json()["id"]
    assert (
        client.patch(f"/v1/admin/events/{eid}", headers=admin, json={"status": "open"}).status_code
        == 200
    )
    assert client.post(f"/v1/admin/events/{eid}/scan", headers=admin).status_code == 200
    run_worker(threads=2, until_empty=True)
    return eid
