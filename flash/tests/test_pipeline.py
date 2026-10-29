from __future__ import annotations

from sqlalchemy import select

from conftest import make_photo
from flash.db import Event, Face, Photo, session_scope
from flash.ingest.pipeline import event_progress, scan_event
from flash.ingest.worker import run_worker
from flash.storage import get_store


def test_scan_index_and_progress(client, admin, indexed_event, photos_dir):
    with session_scope() as s:
        prog = event_progress(s, indexed_event)
        # a pasta _nao_publicar nunca entra (RN9)
        assert prog == {"total": 4, "indexed": 4, "pending": 0, "error": 0, "faces": 6}
        names = {p.name for p in s.scalars(select(Photo))}
        assert "x.jpg" not in names
        ev = s.get(Event, indexed_event)
        p = s.scalar(select(Photo).where(Photo.name == "a1.jpg"))
        assert p.facets["dia"] == "Sabado" and p.facets["modalidade"] == "Volei"
        for kind in ("thumb", "preview"):
            assert get_store().path(ev.tenant_id, ev.id, p.id, kind).exists()
        assert p.width == 900 and p.phash is not None


def test_scan_is_idempotent_and_detects_replaced_file(client, admin, indexed_event, photos_dir):
    with session_scope() as s:
        ev = s.get(Event, indexed_event)
        r = scan_event(s, ev)
        assert (r.found, r.new, r.unchanged) == (4, 0, 4)

    # conteúdo novo no mesmo arquivo → o antigo some das buscas, o novo é enfileirado
    make_photo(photos_dir / "Sabado" / "Volei" / "a2.jpg", ["edu"], size=(1000, 700))
    with session_scope() as s:
        r = scan_event(s, s.get(Event, indexed_event))
        assert (r.new, r.replaced) == (1, 1)
    run_worker(threads=1, until_empty=True)
    with session_scope() as s:
        old = s.scalars(select(Photo).where(Photo.name == "a2.jpg", Photo.visible.is_(False))).all()
        assert len(old) == 1
        assert s.query(Face).filter(Face.photo_id == old[0].id, Face.visible.is_(True)).count() == 0


def test_corrupt_file_goes_to_error_without_breaking_the_rest(
    client, admin, indexed_event, photos_dir, monkeypatch
):
    import flash.ingest.queue as q

    monkeypatch.setattr(q, "MAX_ATTEMPTS", 1)
    (photos_dir / "quebrada.jpg").write_bytes(b"isto nao e uma imagem")
    make_photo(photos_dir / "boa.jpg", ["dani"])
    with session_scope() as s:
        scan_event(s, s.get(Event, indexed_event))
    run_worker(threads=1, until_empty=True)
    with session_scope() as s:
        prog = event_progress(s, indexed_event)
        assert prog["error"] == 1 and prog["indexed"] == 5
        bad = s.scalar(select(Photo).where(Photo.name == "quebrada.jpg"))
        assert bad.status == "error" and "Imagem inválida" in bad.error


def test_exif_rotation_is_respected(client, admin, indexed_event, photos_dir):
    from PIL import Image

    img = Image.new("RGB", (900, 600), (128, 128, 128))
    exif = Image.Exif()
    exif[274] = 6  # "girar 90°": a foto de celular em pé é gravada deitada
    img.save(photos_dir / "pe.jpg", "JPEG", exif=exif)
    with session_scope() as s:
        scan_event(s, s.get(Event, indexed_event))
    run_worker(threads=1, until_empty=True)
    with session_scope() as s:
        p = s.scalar(select(Photo).where(Photo.name == "pe.jpg"))
        assert (p.width, p.height) == (600, 900)
