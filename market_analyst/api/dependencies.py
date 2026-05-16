from __future__ import annotations

from market_analyst.config.settings import Settings, load_settings


def get_settings() -> Settings:
    return load_settings()
