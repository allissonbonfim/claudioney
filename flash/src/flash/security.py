from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import jwt

from flash.config import get_settings

ALGO = "HS256"


class TokenError(Exception):
    pass


def _key() -> str:
    return get_settings().secret


def hmac_hex(value: str, purpose: str) -> str:
    """HMAC com finalidade: a mesma entrada gera valores diferentes por uso."""
    return hmac.new(_key().encode(), f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()


def subject_ref(raw: str) -> str:
    """Identificador pseudonimizado de quem busca (dispositivo / usuário do canal)."""
    return hmac_hex(raw, "subject")[:48]


def hash_code(code: str) -> str:
    return hmac_hex(code.strip().lower(), "event-code")


def check_code(code: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_code(code), expected_hash)


def make_token(typ: str, ttl: timedelta, **claims) -> str:
    payload = {"typ": typ, "exp": datetime.now(UTC) + ttl, **claims}
    return jwt.encode(payload, _key(), algorithm=ALGO)


def read_token(token: str, typ: str) -> dict:
    try:
        payload = jwt.decode(token, _key(), algorithms=[ALGO])
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("typ") != typ:
        raise TokenError("Tipo de token inválido")
    return payload
