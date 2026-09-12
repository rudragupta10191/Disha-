"""Configuration loaded from environment variables without secret values."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    """Non-secret settings used by the local runtime and provider layer."""

    name: str = "Disha"
    owner: str = "Rudra"
    master: str = "Neo/Hermes"
    primary_ai: str = "Cactus Needle 2"
    log_level: str = "INFO"
    ai_provider: str = "cactus_needle2"
    needle2_runtime: str = "cactus_needle2"
    needle2_model: str | None = None
    cloud_provider: str | None = None
    cloud_base_url: str | None = None
    cloud_api_key_configured: bool = False


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Load settings from ``DISHA_*`` variables, using safe defaults."""

    values = os.environ if environ is None else environ
    return Settings(
        name=values.get("DISHA_NAME", "Disha").strip() or "Disha",
        owner=values.get("DISHA_OWNER", "Rudra").strip() or "Rudra",
        master=values.get("DISHA_MASTER", "Neo/Hermes").strip() or "Neo/Hermes",
        primary_ai=values.get("DISHA_PRIMARY_AI", "Cactus Needle 2").strip()
        or "Cactus Needle 2",
        log_level=values.get("DISHA_LOG_LEVEL", "INFO").strip().upper() or "INFO",
        ai_provider=values.get("DISHA_AI_PROVIDER", "cactus_needle2").strip()
        or "cactus_needle2",
        needle2_runtime=values.get("DISHA_NEEDLE2_RUNTIME", "cactus_needle2").strip()
        or "cactus_needle2",
        needle2_model=values.get("DISHA_NEEDLE2_MODEL", "").strip() or None,
        cloud_provider=values.get("DISHA_CLOUD_PROVIDER", "").strip() or None,
        cloud_base_url=values.get("DISHA_CLOUD_BASE_URL", "").strip() or None,
        cloud_api_key_configured=bool(values.get("DISHA_CLOUD_API_KEY", "").strip()),
    )
