"""Fila em tabela com reserva atômica (sem Redis). Mesmo código em SQLite e Postgres."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from flash.db import Job, utcnow

STALE_AFTER = timedelta(minutes=10)
MAX_ATTEMPTS = 3


def enqueue(session: Session, kind: str, ref_id: str) -> None:
    session.add(Job(kind=kind, ref_id=ref_id))


def claim(session: Session) -> Job | None:
    now = utcnow()
    # Recupera jobs de workers que morreram no meio do trabalho.
    session.execute(
        update(Job)
        .where(Job.status == "running", Job.locked_at < now - STALE_AFTER)
        .values(status="queued", locked_at=None)
    )
    candidates = session.scalars(
        select(Job.id).where(Job.status == "queued", Job.run_after <= now).order_by(Job.id).limit(8)
    ).all()
    for job_id in candidates:
        res = session.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == "queued")
            .values(status="running", locked_at=now, attempts=Job.attempts + 1)
        )
        if res.rowcount == 1:
            session.commit()
            return session.get(Job, job_id)
    session.commit()
    return None


def complete(session: Session, job: Job) -> None:
    job.status = "done"
    job.locked_at = None
    job.error = None


def fail(session: Session, job: Job, error: str) -> bool:
    """Devolve True se vai tentar de novo."""
    job.error = error[:500]
    job.locked_at = None
    if job.attempts < MAX_ATTEMPTS:
        job.status = "queued"
        job.run_after = utcnow() + timedelta(seconds=10 * 2**job.attempts)
        return True
    job.status = "failed"
    return False
