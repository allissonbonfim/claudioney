"""Decodificação segura e geração de derivados."""

from __future__ import annotations

import io
from datetime import datetime

import numpy as np
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 200_000_000  # acima disso o Pillow recusa (proteção contra "bombas")

_EXIF_IFD = 0x8769
_DATETIME_ORIGINAL = 36867
_DATETIME = 306


class InvalidImageError(ValueError):
    pass


def decode(data: bytes, max_px: int) -> tuple[Image.Image, datetime | None, tuple[int, int]]:
    """Decodifica já reduzido (modo `draft` do JPEG lê em escala menor, muito mais rápido).

    Retorna (imagem RGB orientada, data da foto, tamanho original).
    """
    try:
        img = Image.open(io.BytesIO(data))
        original_size = img.size
        if img.getexif().get(274, 1) in (5, 6, 7, 8):  # orientação EXIF: troca largura/altura
            original_size = (original_size[1], original_size[0])
        taken_at = _taken_at(img)
        img.draft("RGB", (max_px, max_px))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
    except (OSError, Image.DecompressionBombError, ValueError) as exc:
        raise InvalidImageError(f"Imagem inválida: {exc}") from exc
    if max(img.size) > max_px:
        img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    return img, taken_at, original_size


def _taken_at(img: Image.Image) -> datetime | None:
    try:
        exif = img.getexif()
        raw = exif.get_ifd(_EXIF_IFD).get(_DATETIME_ORIGINAL) or exif.get(_DATETIME)
        if raw:
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
    except Exception:  # noqa: BLE001 - EXIF malformado não deve derrubar a ingestão
        return None
    return None


def to_bgr(img: Image.Image) -> np.ndarray:
    return np.ascontiguousarray(np.asarray(img)[:, :, ::-1])


def resized(img: Image.Image, px: int) -> Image.Image:
    if max(img.size) <= px:
        return img
    out = img.copy()
    out.thumbnail((px, px), Image.Resampling.LANCZOS)
    return out


def jpeg_bytes(img: Image.Image, quality: int = 85) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def dhash(img: Image.Image) -> int:
    """Hash perceptual de 64 bits (rajadas e quase duplicatas), como inteiro com sinal."""
    g = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    px = np.asarray(g, dtype=np.int16)
    bits = (px[:, 1:] > px[:, :-1]).flatten()
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return value - (1 << 64) if value >= (1 << 63) else value
