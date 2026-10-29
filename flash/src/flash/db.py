from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from flash.config import get_settings


def utcnow() -> datetime:
    """UTC "ingênuo": compatível com SQLite e Postgres sem surpresas de fuso."""
    return datetime.now(UTC).replace(tzinfo=None)


def new_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenant"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    # marca, domínios, textos, limites... (ver docs/06)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Event(Base):
    __tablename__ = "event"
    __table_args__ = (UniqueConstraint("tenant_id", "slug"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenant.id"), index=True)
    slug: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    # draft | indexing | open | closed | archived
    status: Mapped[str] = mapped_column(String(16), default="draft")
    source_type: Mapped[str] = mapped_column(String(16), default="drive")  # drive | local
    source_ref: Mapped[str] = mapped_column(String(500), default="")  # id da pasta / caminho
    engine: Mapped[str] = mapped_column(String(32), default="sface")
    index_version: Mapped[int] = mapped_column(Integer, default=1)
    has_minors: Mapped[bool] = mapped_column(Boolean, default=True)
    access_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    starts_on: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ends_on: Mapped[str | None] = mapped_column(String(10), nullable=True)
    retention_until: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # limiares, textos e facetas do evento
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Photo(Base):
    __tablename__ = "photo"
    __table_args__ = (
        UniqueConstraint("event_id", "source_id", "checksum"),
        Index("photo_event_status", "event_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("event.id"))
    source_id: Mapped[str] = mapped_column(String(500))  # id do arquivo no Drive / caminho relativo
    checksum: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(300))
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    facets: Mapped[dict] = mapped_column(JSON, default=dict)
    # discovered | indexed | error
    status: Mapped[str] = mapped_column(String(16), default="discovered")
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phash: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Face(Base):
    __tablename__ = "face"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[str] = mapped_column(String(32), index=True)
    photo_id: Mapped[str] = mapped_column(ForeignKey("photo.id"), index=True)
    cluster_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    w: Mapped[int] = mapped_column(Integer)
    h: Mapped[int] = mapped_column(Integer)
    det_score: Mapped[float] = mapped_column(Float)
    quality: Mapped[float] = mapped_column(Float)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)  # float16, L2=1
    index_version: Mapped[int] = mapped_column(Integer, default=1)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)


class Job(Base):
    """Fila mínima em tabela: reserva atômica, funciona em SQLite e Postgres."""

    __tablename__ = "job"
    __table_args__ = (Index("job_claim", "status", "run_after"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(32))
    ref_id: Mapped[str] = mapped_column(String(32), index=True)  # ex.: photo_id
    status: Mapped[str] = mapped_column(String(12), default="queued")  # queued|running|done|failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    run_after: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Search(Base):
    __tablename__ = "search"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[str] = mapped_column(String(32), index=True)
    channel: Mapped[str] = mapped_column(String(16))  # web | instagram | ...
    subject_ref: Mapped[str] = mapped_column(String(64), index=True)  # HMAC; nunca a imagem
    quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_certain: Mapped[int] = mapped_column(Integer, default=0)
    n_maybe: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class SearchResult(Base):
    __tablename__ = "search_result"
    search_id: Mapped[str] = mapped_column(ForeignKey("search.id"), primary_key=True)
    photo_id: Mapped[str] = mapped_column(ForeignKey("photo.id"), primary_key=True)
    tier: Mapped[str] = mapped_column(String(8))  # certain | maybe
    sim: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)


class ConsentLog(Base):
    """Somente inserção."""

    __tablename__ = "consent_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(32))
    event_id: Mapped[str] = mapped_column(String(32))
    subject_ref: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(16))
    terms_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(32))
    event_id: Mapped[str] = mapped_column(String(32))
    photo_id: Mapped[str] = mapped_column(String(32))
    search_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))  # not_me | remove
    status: Mapped[str] = mapped_column(String(12), default="open")  # open | resolved
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        url = settings.database_url
        kwargs: dict = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        _engine = create_engine(url, **kwargs)
        if url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _pragmas(dbapi_conn, _):  # pragma: no cover - configuração de driver
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA synchronous=NORMAL")
                cur.execute("PRAGMA busy_timeout=30000")
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

        _session_factory = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def init_db() -> None:
    Base.metadata.create_all(get_engine())


def reset_engine() -> None:
    """Usado nos testes para trocar o banco."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI."""
    with session_scope() as session:
        yield session
