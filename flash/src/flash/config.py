from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLASH_", env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{ROOT / 'data' / 'flash.db'}"
    data_dir: Path = ROOT / "data"
    models_dir: Path = ROOT / "models"
    web_dist: Path = ROOT / "web" / "dist"

    env: str = "dev"  # "production" liga as travas de segurança abaixo
    engine: str = "sface"
    default_tenant: str = "cbde"

    # Segredos: em produção, sempre definidos por variável de ambiente.
    secret: str = "dev-secret-troque-em-producao"
    admin_token: str = "dev-admin"

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Ingestão
    work_max_px: int = 2048
    preview_px: int = 1600
    thumb_px: int = 400
    worker_threads: int = 4

    # Busca / abuso
    max_upload_bytes: int = 10 * 1024 * 1024
    searches_per_day: int = 10
    session_ttl_hours: int = 12
    gallery_ttl_days: int = 30

    # Google Drive (conta de serviço)
    google_credentials_file: Path | None = None

    def assert_safe(self) -> None:
        """Em produção, recusa subir com segredos de desenvolvimento."""
        if self.env != "production":
            return
        problems = []
        if self.secret.startswith("dev-") or len(self.secret) < 32:
            problems.append("FLASH_SECRET (mín. 32 caracteres, aleatório)")
        if self.admin_token.startswith("dev-") or len(self.admin_token) < 16:
            problems.append("FLASH_ADMIN_TOKEN (mín. 16 caracteres)")
        if problems:
            raise RuntimeError("Defina: " + "; ".join(problems))

    @property
    def derivatives_dir(self) -> Path:
        return self.data_dir / "derivatives"


@lru_cache
def get_settings() -> Settings:
    return Settings()
