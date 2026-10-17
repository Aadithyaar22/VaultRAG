"""Environment-driven settings. No secrets are hardcoded."""
import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_BACKEND_DIR.parent / ".env"), ".env"), extra="ignore"
    )

    vaultrag_db_path: str = str(_BACKEND_DIR / "data" / "vaultrag.db")
    vaultrag_secret: str = ""
    vaultrag_token_ttl_seconds: int = 28800

    llm_provider: str = "openai_compatible"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    llm_timeout_seconds: float = 30.0

    embedding_provider: str = "hashing"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""

    retrieval_top_k: int = 4
    retrieval_min_score: float = 0.08
    rseg_max_regenerations: int = 1
    cache_enabled: bool = True
    demo_mode: bool = True

    def resolved_secret(self) -> str:
        # An unset secret gets a per-process random value (tokens die on restart) rather than a default.
        if not self.vaultrag_secret:
            object.__setattr__(self, "vaultrag_secret", secrets.token_hex(32))
        return self.vaultrag_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
    os.environ.pop("_VAULTRAG_SETTINGS_LOADED", None)
