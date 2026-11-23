from __future__ import annotations

import secrets

from django.conf import settings


def configured_pwa_tokens() -> list[str]:
    out: list[str] = []
    for attr in ("PWA_API_TOKEN", "PWA_API_TOKEN_PREVIOUS"):
        value = (getattr(settings, attr, "") or "").strip()
        if value and value not in out:
            out.append(value)
    return out


def pwa_token_is_valid(key: str | None) -> bool:
    if not key:
        return False
    stripped = key.strip()
    if not stripped:
        return False
    for expected in configured_pwa_tokens():
        if secrets.compare_digest(expected, stripped):
            return True
    return False