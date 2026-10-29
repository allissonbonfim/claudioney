from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from flash.faces.engine import FaceEngine

MESSAGES = {
    "no_face": "Não encontramos um rosto. Tire a selfie de frente, com boa luz.",
    "multiple_faces": "Apareceu mais de uma pessoa. Tire uma selfie só sua.",
    "too_small": "Seu rosto está pequeno na foto. Aproxime o celular.",
    "low_quality": "A foto ficou tremida ou de lado. Tente de novo, olhando para a câmera.",
}


@dataclass(slots=True)
class SelfieResult:
    ok: bool
    reason: str | None = None
    message: str | None = None
    embedding: np.ndarray | None = None
    quality: float = 0.0


def analyze_selfie(
    engine: FaceEngine,
    bgr: np.ndarray,
    min_face_px: int = 110,
    min_quality: float = 0.30,
) -> SelfieResult:
    """Exige exatamente um rosto principal, grande e nítido. A imagem não é guardada."""
    faces = sorted(engine.detect_and_embed(bgr), key=lambda f: f.area, reverse=True)

    def fail(reason: str) -> SelfieResult:
        return SelfieResult(False, reason, MESSAGES[reason])

    if not faces:
        return fail("no_face")
    main = faces[0]
    if len(faces) > 1 and faces[1].area > 0.25 * main.area:
        return fail("multiple_faces")
    if min(main.w, main.h) < min_face_px:
        return fail("too_small")
    if main.quality < min_quality:
        return fail("low_quality")
    return SelfieResult(True, embedding=main.embedding, quality=main.quality)
