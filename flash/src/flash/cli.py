"""Linha de comando: `flash <comando>` (ou `python -m flash.cli`)."""

from __future__ import annotations

import argparse
import json
import sys
import time

from sqlalchemy import select

from flash import security
from flash.config import get_settings
from flash.db import Event, Tenant, init_db, session_scope


def cmd_seed(args) -> None:
    init_db()
    with session_scope() as s:
        if not s.scalar(select(Tenant).where(Tenant.slug == args.slug)):
            s.add(
                Tenant(
                    slug=args.slug,
                    name=args.name,
                    config={
                        "brand": {
                            "primary": "#0b6b3a",
                            "accent": "#f5b800",
                            "tagline": "Ache suas fotos em segundos",
                        },
                    },
                )
            )
            print(f"cliente '{args.slug}' criado")
        else:
            print(f"cliente '{args.slug}' já existe")


def cmd_event(args) -> None:
    init_db()
    with session_scope() as s:
        t = s.scalar(select(Tenant).where(Tenant.slug == args.tenant))
        if t is None:
            sys.exit(f"cliente '{args.tenant}' não existe (rode `flash seed`)")
        e = s.scalar(select(Event).where(Event.tenant_id == t.id, Event.slug == args.slug))
        if e is None:
            e = Event(
                tenant_id=t.id,
                slug=args.slug,
                name=args.name,
                source_type=args.source,
                source_ref=args.ref,
                engine=args.engine or get_settings().engine,
                has_minors=not args.adults,
                status="open",
            )
            s.add(e)
        if args.code:
            e.access_code_hash = security.hash_code(args.code)
        s.flush()
        print(json.dumps({"id": e.id, "slug": e.slug, "status": e.status}, ensure_ascii=False))


def cmd_scan(args) -> None:
    from flash.ingest.pipeline import scan_event

    with session_scope() as s:
        e = _find_event(s, args.slug)
        print(scan_event(s, e))


def _find_event(s, slug: str) -> Event:
    e = s.scalar(select(Event).where(Event.slug == slug))
    if e is None:
        sys.exit(f"evento '{slug}' não existe")
    return e


def cmd_worker(args) -> None:
    from flash.ingest.worker import run_worker

    t0 = time.perf_counter()
    run_worker(threads=args.threads or get_settings().worker_threads, until_empty=args.once)
    if args.once:
        print(f"fila vazia após {time.perf_counter() - t0:.1f}s")


def cmd_progress(args) -> None:
    from flash.ingest.pipeline import event_progress

    with session_scope() as s:
        print(event_progress(s, _find_event(s, args.slug).id))


def cmd_serve(args) -> None:
    import uvicorn

    uvicorn.run("flash.api.main:app", host=args.host, port=args.port, reload=args.reload)


def main() -> None:
    p = argparse.ArgumentParser(prog="flash")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("seed", help="cria o cliente (tenant)")
    sp.add_argument("--slug", default="cbde")
    sp.add_argument("--name", default="CBDE")
    sp.set_defaults(fn=cmd_seed)

    sp = sub.add_parser("event", help="cria/atualiza um evento")
    sp.add_argument("slug")
    sp.add_argument("--tenant", default="cbde")
    sp.add_argument("--name", required=True)
    sp.add_argument("--source", choices=["local", "drive"], required=True)
    sp.add_argument("--ref", required=True, help="caminho da pasta ou ID da pasta do Drive")
    sp.add_argument("--engine")
    sp.add_argument("--code", help="código de acesso do evento (modo menores)")
    sp.add_argument(
        "--adults", action="store_true", help="evento sem menores (afrouxa o modo restrito)"
    )
    sp.set_defaults(fn=cmd_event)

    sp = sub.add_parser("scan", help="lista a fonte e enfileira fotos novas")
    sp.add_argument("slug")
    sp.set_defaults(fn=cmd_scan)

    sp = sub.add_parser("worker", help="processa a fila de indexação")
    sp.add_argument("--threads", type=int)
    sp.add_argument("--once", action="store_true", help="sai quando a fila esvaziar")
    sp.set_defaults(fn=cmd_worker)

    sp = sub.add_parser("progress", help="mostra o andamento da indexação")
    sp.add_argument("slug")
    sp.set_defaults(fn=cmd_progress)

    sp = sub.add_parser("serve", help="sobe a API")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8000)
    sp.add_argument("--reload", action="store_true")
    sp.set_defaults(fn=cmd_serve)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
