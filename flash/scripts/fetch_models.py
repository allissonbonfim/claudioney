"""Baixa os modelos YuNet e SFace do OpenCV Zoo (Apache 2.0) para ./models e registra o SHA-256.

Uso: python scripts/fetch_models.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import httpx

MODELS = {
    "face_detection_yunet_2023mar.onnx": "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx": "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
}
DEST = Path(__file__).resolve().parents[1] / "models"


def main() -> int:
    DEST.mkdir(exist_ok=True)
    lines = []
    for name, url in MODELS.items():
        target = DEST / name
        if not target.exists():
            print(f"baixando {name} ...")
            with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
                r.raise_for_status()
                with target.open("wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        print(f"{name}  {target.stat().st_size} bytes  sha256={digest}")
        lines.append(f"{digest}  {name}")
    (DEST / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
