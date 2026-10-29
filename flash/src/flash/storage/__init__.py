from __future__ import annotations

from functools import lru_cache

from flash.config import get_settings
from flash.storage.derivatives import DerivativeStore, LocalDerivativeStore


@lru_cache
def get_store() -> DerivativeStore:
    return LocalDerivativeStore(get_settings().derivatives_dir)


def reset_store() -> None:
    get_store.cache_clear()


__all__ = ["DerivativeStore", "get_store", "reset_store"]
