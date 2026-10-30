"""Baixa os modelos YuNet e SFace do OpenCV Zoo (Apache 2.0) para ./models e confere o SHA-256.

Tenta o Hugging Face e, se falhar, o espelho oficial do OpenCV Zoo no GitHub.
Se models/SHA256SUMS existir, o arquivo baixado precisa bater com ele; senão o arquivo é criado.

Uso: python scripts/fetch_models.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import httpx

ZOO = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models"
MODELS = {
    "face_detection_yunet_2023mar.onnx": [
        "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
        f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    ],
    "face_recognition_sface_2021dec.onnx": [
        "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
        f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    ],
}
DEST = Path(__file__).resolve().parents[1] / "models"
SUMS = DEST / "SHA256SUMS"


def expected_digests() -> dict[str, str]:
    if not SUMS.exists():
        return {}
    pairs = (line.split() for line in SUMS.read_text().splitlines() if line.strip())
    return {name: digest for digest, name in pairs}


def download(urls: list[str], target: Path) -> None:
    for url in urls:
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
                r.raise_for_status()
                with target.open("wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            return
        except httpx.HTTPError as exc:
            print(f"  falhou em {url}: {exc}")
            target.unlink(missing_ok=True)
    raise SystemExit(f"não foi possível baixar {target.name}")


def main() -> int:
    DEST.mkdir(exist_ok=True)
    expected = expected_digests()
    lines = []
    for name, urls in MODELS.items():
        target = DEST / name
        if not target.exists():
            print(f"baixando {name} ...")
            download(urls, target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if name in expected and expected[name] != digest:
            target.unlink()
            raise SystemExit(f"SHA-256 de {name} não confere ({digest}); arquivo apagado")
        print(f"{name}  {target.stat().st_size} bytes  sha256={digest}  ok")
        lines.append(f"{digest}  {name}")
    if not expected:
        SUMS.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
