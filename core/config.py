"""Paths, constants, and secure API-key storage for Data Coach."""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional convenience
    load_dotenv = None

APP_NAME = "Data Coach"
VERSION = "0.1.0"

ROOT = Path(__file__).resolve().parent.parent


def _default_data_dir() -> Path:
    """Writable per-user storage for the frozen build, project folder otherwise."""
    if getattr(sys, "frozen", False):
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "DataCoach"
    return ROOT / "data"


if load_dotenv is not None:
    load_dotenv(ROOT / ".env")
    if getattr(sys, "frozen", False):
        load_dotenv(Path(sys.executable).resolve().parent / ".env")

DATA_DIR = Path(os.getenv("DATACOACH_DATA_DIR") or _default_data_dir())
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "coach.db"
ASSETS_DIR = ROOT / "assets"

KEYRING_SERVICE = "DataCoach"
KEYRING_USER = "gemini_api_key"

DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_CHOICES = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def get_api_key() -> str | None:
    """Return the Gemini key from the environment or Windows Credential Locker."""
    env_key = _clean(os.getenv("GEMINI_API_KEY")) or _clean(os.getenv("GOOGLE_API_KEY"))
    if env_key:
        return env_key
    try:
        import keyring

        return _clean(keyring.get_password(KEYRING_SERVICE, KEYRING_USER))
    except Exception:
        return None


def save_api_key(key: str) -> None:
    key = key.strip()
    if not key:
        raise ValueError("API key is empty.")
    import keyring

    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key)


def delete_api_key() -> None:
    try:
        import keyring

        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except Exception:
        pass


def mask_key(key: str | None) -> str:
    if not key:
        return ""
    if len(key) <= 10:
        return "•" * len(key)
    return f"{key[:4]}…{key[-4:]}"
