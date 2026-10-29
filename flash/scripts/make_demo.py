"""Gera um evento de demonstração com o motor falso (quadrados coloridos no lugar de rostos).

Serve para ver o site funcionando sem fotos reais. Uso: FLASH_ENGINE=fake FLASH_DATA_DIR=data/demo \
python scripts/make_demo.py
"""

from __future__ import annotations

import colorsys
import random

from PIL import Image, ImageDraw

from flash.config import get_settings
from flash.db import Event, Tenant, init_db, session_scope
from flash.ingest.pipeline import scan_event
from flash.ingest.worker import run_worker

PEOPLE = {"ana": 0, "bia": 60, "caio": 120, "dani": 180, "edu": 240}


def rgb(h: int):
    r, g, b = colorsys.hsv_to_rgb(h / 360, 1, 1)
    return int(r * 255), int(g * 255), int(b * 255)


def main() -> None:
    s = get_settings()
    root = s.data_dir / "fotos-demo"
    rng = random.Random(7)
    for day, sport in [("Sabado", "Volei"), ("Sabado", "Futsal"), ("Domingo", "Basquete")]:
        for i in range(14):
            img = Image.new("RGB", (1600, 1067), (rng.randint(60, 200),) * 3)
            d = ImageDraw.Draw(img)
            who = rng.sample(list(PEOPLE), rng.randint(1, 3))
            for k, name in enumerate(who):
                x = 120 + k * 420 + rng.randint(-30, 30)
                d.rectangle([x, 300, x + 220, 520], fill=rgb(PEOPLE[name]))
            p = root / day / sport / f"{sport.lower()}_{i:03d}.jpg"
            p.parent.mkdir(parents=True, exist_ok=True)
            img.save(p, "JPEG", quality=90)
    img = Image.new("RGB", (900, 900), (128, 128, 128))
    ImageDraw.Draw(img).rectangle([300, 300, 600, 600], fill=rgb(PEOPLE["ana"]))
    (s.data_dir / "selfie-ana.jpg").parent.mkdir(parents=True, exist_ok=True)
    img.save(s.data_dir / "selfie-ana.jpg", "JPEG", quality=92)

    init_db()
    with session_scope() as db:
        t = Tenant(
            slug="cbde",
            name="CBDE",
            config={
                "brand": {
                    "primary": "#0b6b3a",
                    "accent": "#f5b800",
                    "tagline": "Ache suas fotos em segundos",
                }
            },
        )
        db.add(t)
        db.flush()
        e = Event(
            tenant_id=t.id,
            slug="demo",
            name="Jogos de Demonstração 2026",
            source_type="local",
            source_ref=str(root),
            engine="fake",
            status="open",
            has_minors=True,
            starts_on="2026-11-07",
            ends_on="2026-11-08",
            config={"facet_names": ["dia", "modalidade"]},
        )
        db.add(e)
        db.flush()
        print(scan_event(db, e))
    run_worker(threads=4, until_empty=True)
    print("pronto:", s.data_dir)


if __name__ == "__main__":
    main()
