from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from flash.config import get_settings
from flash.db import Event, Tenant, get_session


class RateLimiter:
    """Janela deslizante em memória. Suficiente para 1 instância; em escala, Redis/Postgres."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_s: int) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] < now - window_s:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def get_tenant(
    request: Request,
    session: Session = Depends(get_session),
    x_flash_tenant: str | None = Header(default=None),
) -> Tenant:
    """Resolve o cliente por cabeçalho (dev), domínio próprio ou cliente padrão."""
    settings = get_settings()
    if x_flash_tenant:
        tenant = session.scalar(select(Tenant).where(Tenant.slug == x_flash_tenant))
    else:
        host = (request.headers.get("host") or "").split(":")[0].lower()
        tenant = next(
            (t for t in session.scalars(select(Tenant)) if host in t.config.get("domains", [])),
            None,
        ) or session.scalar(select(Tenant).where(Tenant.slug == settings.default_tenant))
    if tenant is None:
        raise HTTPException(404, "Cliente não encontrado")
    return tenant


def get_open_event(
    slug: str, tenant: Tenant = Depends(get_tenant), session: Session = Depends(get_session)
) -> Event:
    event = session.scalar(select(Event).where(Event.tenant_id == tenant.id, Event.slug == slug))
    if event is None or event.status not in ("open", "indexing"):
        raise HTTPException(404, "Evento não encontrado")
    return event


def require_admin(authorization: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_token
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(401, "Não autorizado")
