"""Motor de mentira para testes e demos sem modelos: "rostos" são quadrados coloridos.

A matiz do quadrado define a identidade; o vetor é determinístico por identidade, com um pequeno
ruído por posição. Não use fora de testes/demonstração.
"""

from __future__ import annotations

import cv2
import numpy as np

from flash.faces.engine import FaceObs, Thresholds


class FakeEngine:
    name = "fake"
    version = "fake-1"
    dim = 32
    default_thresholds = Thresholds(certain=0.80, maybe=0.60)

    def _identity_vec(self, bin_id: int) -> np.ndarray:
        rng = np.random.default_rng(bin_id + 12345)
        v = rng.normal(size=self.dim).astype(np.float32)
        return v / np.linalg.norm(v)

    def detect_and_embed(self, bgr: np.ndarray) -> list[FaceObs]:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = ((hsv[..., 1] > 150) & (hsv[..., 2] > 80)).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out: list[FaceObs] = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w < 20 or h < 20:
                continue
            hue = int(np.median(hsv[y : y + h, x : x + w, 0]))
            bin_id = hue // 6  # 30 identidades possíveis
            rng = np.random.default_rng(x * 7919 + y)
            v = self._identity_vec(bin_id) + rng.normal(scale=0.02, size=self.dim).astype(
                np.float32
            )
            v /= np.linalg.norm(v)
            quality = float(np.clip(min(w, h) / 80.0, 0.0, 1.0))
            out.append(FaceObs(x, y, w, h, 0.99, quality, v))
        return out
