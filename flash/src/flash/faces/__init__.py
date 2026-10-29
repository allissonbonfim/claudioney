from __future__ import annotations

import threading

from flash.config import get_settings
from flash.faces.engine import FaceEngine, FaceObs, Thresholds

__all__ = ["FaceEngine", "FaceObs", "Thresholds", "get_engine", "set_engine"]

_lock = threading.Lock()
_engines: dict[str, FaceEngine] = {}


def get_engine(name: str | None = None) -> FaceEngine:
    name = name or get_settings().engine
    with _lock:
        if name not in _engines:
            if name == "sface":
                from flash.faces.sface import SFaceEngine

                _engines[name] = SFaceEngine(get_settings().models_dir)
            elif name == "fake":
                from flash.faces.fake import FakeEngine

                _engines[name] = FakeEngine()
            else:
                raise ValueError(f"Motor facial desconhecido: {name}")
        return _engines[name]


def set_engine(name: str, engine: FaceEngine) -> None:
    """Registra um motor (testes e adaptadores futuros, como Rekognition)."""
    with _lock:
        _engines[name] = engine
