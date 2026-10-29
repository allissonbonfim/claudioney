from __future__ import annotations

import logging
import threading
import time

from flash.db import Event, Job, Photo, session_scope
from flash.ingest import queue
from flash.ingest.pipeline import process_photo
from flash.sources import SourceConnector, source_for

log = logging.getLogger("flash.worker")

_sources: dict[str, SourceConnector] = {}
_sources_lock = threading.Lock()


def _source(session, event_id: str) -> SourceConnector:
    with _sources_lock:
        if event_id not in _sources:
            event = session.get(Event, event_id)
            assert event is not None
            _sources[event_id] = source_for(event)
        return _sources[event_id]


def forget_sources() -> None:
    with _sources_lock:
        _sources.clear()


def run_one() -> bool:
    """Executa um job. Devolve False quando a fila está vazia."""
    with session_scope() as session:
        job = queue.claim(session)
        if job is None:
            return False
        try:
            if job.kind == "index_photo":
                photo = session.get(Photo, job.ref_id)
                source = _source(session, photo.event_id) if photo else None
                process_photo(session, job.ref_id, source=source)
            else:
                raise ValueError(f"Job desconhecido: {job.kind}")
            queue.complete(session, job)
        except Exception as exc:  # noqa: BLE001 - uma foto ruim nunca derruba o worker
            log.warning("job %s falhou: %s", job.id, exc)
            session.rollback()
            job = session.get(Job, job.id)
            will_retry = queue.fail(session, job, f"{type(exc).__name__}: {exc}")
            if not will_retry and job.kind == "index_photo":
                photo = session.get(Photo, job.ref_id)
                if photo:
                    photo.status = "error"
                    photo.error = job.error
        return True


def run_worker(threads: int = 4, poll_interval: float = 1.0, until_empty: bool = False) -> None:
    stop = threading.Event()

    def loop() -> None:
        while not stop.is_set():
            try:
                did = run_one()
            except Exception:  # noqa: BLE001
                log.exception("erro inesperado no worker")
                did = False
            if not did:
                if until_empty:
                    return
                time.sleep(poll_interval)

    pool = [threading.Thread(target=loop, daemon=True, name=f"worker-{i}") for i in range(threads)]
    for t in pool:
        t.start()
    try:
        for t in pool:
            while t.is_alive():
                t.join(0.5)
    except KeyboardInterrupt:
        stop.set()
        for t in pool:
            t.join(5)
