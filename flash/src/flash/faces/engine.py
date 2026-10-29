"""Contrato do motor facial. Nada fora de `flash.faces` importa OpenCV/ONNX diretamente.

Vetores de motores (ou versões) diferentes NÃO se misturam: cada evento fixa um motor e uma
`index_version`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass(slots=True)
class FaceObs:
    x: int
    y: int
    w: int
    h: int
    det_score: float
    quality: float  # 0–1: tamanho, nitidez e pose
    embedding: np.ndarray = field(repr=False)  # float32, norma L2 = 1

    @property
    def area(self) -> int:
        return self.w * self.h


@dataclass(slots=True)
class Thresholds:
    """Limiares de similaridade (cosseno). Valores iniciais; calibrar no golden set (docs/04)."""

    certain: float
    maybe: float
    min_quality_certain: float = 0.35


class FaceEngine(Protocol):
    name: str
    version: str
    dim: int
    default_thresholds: Thresholds

    def detect_and_embed(self, bgr: np.ndarray) -> list[FaceObs]:
        """Detecta todos os rostos da imagem (BGR uint8) e devolve um vetor por rosto."""
        ...
