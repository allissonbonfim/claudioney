"""Canais de entrega (ADR-018).

O domínio (`flash.search`, `flash.ingest`) não conhece canais. Cada canal é um adaptador fino que:

1. traduz a mensagem de entrada em (evento, vetores da selfie, `subject_ref`);
2. chama `flash.search.service.run_search`;
3. entrega o resultado do jeito do canal.

Hoje existe só `web` (rotas em `flash.api.public`). O Instagram será outro adaptador, com a
máquina de estados de docs/05, sem alterar busca, dados ou entrega.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

CHANNEL_WEB = "web"
CHANNEL_INSTAGRAM = "instagram"  # futuro
CHANNEL_WHATSAPP = "whatsapp"  # futuro


@dataclass(slots=True)
class SelfieRequest:
    channel: str
    tenant_id: str
    event_id: str
    subject_ref: str  # HMAC do id do dispositivo / IGSID — nunca a imagem
    vectors: np.ndarray
    quality: float
    consent_version: str


class Channel(Protocol):
    name: str

    def deliver(self, request: SelfieRequest, search_id: str) -> None:
        """Entrega o resultado ao participante (galeria, DM, mensagem...)."""
        ...
