"""OpenCV YuNet (detecção) + SFace (reconhecimento). Licença Apache 2.0 (OpenCV Zoo)."""

from __future__ import annotations

import threading
from pathlib import Path

import cv2
import numpy as np

from flash.faces.engine import FaceObs, Thresholds

DETECTOR_FILE = "face_detection_yunet_2023mar.onnx"
RECOGNIZER_FILE = "face_recognition_sface_2021dec.onnx"


class ModelsMissingError(RuntimeError):
    pass


def _quality(row: np.ndarray, aligned: np.ndarray) -> float:
    """Combina tamanho, nitidez e pose frontal em [0, 1]. Heurística: calibrar no golden set."""
    w, h = float(row[2]), float(row[3])
    size_q = float(np.clip((min(w, h) - 30.0) / 60.0, 0.0, 1.0))

    gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    sharp_q = float(np.clip(cv2.Laplacian(gray, cv2.CV_64F).var() / 120.0, 0.0, 1.0))

    # landmarks YuNet: olho dir., olho esq., nariz, canto boca dir., canto boca esq.
    re, le, nose = row[4:6], row[6:8], row[8:10]
    eye_dist = max(float(np.linalg.norm(le - re)), 1.0)
    yaw = abs(float((nose[0] - (re[0] + le[0]) / 2.0) / eye_dist))
    pose_q = float(np.clip(1.0 - yaw / 0.6, 0.0, 1.0))

    det_q = float(np.clip(row[14], 0.0, 1.0))
    return float(det_q * (0.4 * size_q + 0.3 * sharp_q + 0.3 * pose_q))


class SFaceEngine:
    name = "sface"
    version = "yunet2023mar+sface2021dec"
    dim = 128
    # SFace sugere cosseno ≈ 0,363 para 1:1. Em busca 1:N o limiar seguro é mais alto.
    default_thresholds = Thresholds(certain=0.50, maybe=0.38)

    def __init__(self, models_dir: Path, score_threshold: float = 0.6, nms: float = 0.3):
        self._det_path = models_dir / DETECTOR_FILE
        self._rec_path = models_dir / RECOGNIZER_FILE
        for p in (self._det_path, self._rec_path):
            if not p.exists():
                raise ModelsMissingError(
                    f"Modelo ausente: {p}. Rode `python scripts/fetch_models.py`."
                )
        self._score = score_threshold
        self._nms = nms
        self._tls = threading.local()  # os objetos do OpenCV não são thread-safe

    def _models(self):
        if not hasattr(self._tls, "det"):
            self._tls.det = cv2.FaceDetectorYN.create(
                str(self._det_path), "", (320, 320), self._score, self._nms, 5000
            )
            self._tls.rec = cv2.FaceRecognizerSF.create(str(self._rec_path), "")
        return self._tls.det, self._tls.rec

    def detect_and_embed(self, bgr: np.ndarray) -> list[FaceObs]:
        det, rec = self._models()
        h, w = bgr.shape[:2]
        det.setInputSize((w, h))
        _, rows = det.detect(bgr)
        if rows is None:
            return []
        out: list[FaceObs] = []
        for row in rows:
            aligned = rec.alignCrop(bgr, row)
            feat = rec.feature(aligned)[0].astype(np.float32)
            norm = float(np.linalg.norm(feat))
            if norm == 0.0:
                continue
            x, y, bw, bh = (int(round(v)) for v in row[:4])
            out.append(
                FaceObs(
                    x=x,
                    y=y,
                    w=bw,
                    h=bh,
                    det_score=float(row[14]),
                    quality=_quality(row, aligned),
                    embedding=feat / norm,
                )
            )
        return out
