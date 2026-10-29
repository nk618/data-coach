"""The 21-day sprint: loading the template and locating the current day."""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from typing import Any

from . import db
from .config import ASSETS_DIR

SPRINT_DAYS = 21


@lru_cache(maxsize=1)
def load_template() -> dict[str, Any]:
    path = ASSETS_DIR / "sprint_21day.json"
    return json.loads(path.read_text(encoding="utf-8"))


def seed_from_template() -> tuple[int, int]:
    template = load_template()
    return db.seed_roadmap(template)


def get_current_day(profile: dict[str, Any]) -> tuple[int, int]:
    """Return (clamped day 1-21, raw day number since the start date)."""
    try:
        start = date.fromisoformat(str(profile["start_date"]))
    except (KeyError, TypeError, ValueError):
        return 1, 1
    raw = (date.today() - start).days + 1
    return max(1, min(raw, SPRINT_DAYS)), raw


def week_theme(week: int) -> str:
    for item in load_template().get("weeks", []):
        if int(item["week"]) == int(week):
            return item["theme"]
    return f"Week {week}"


def week_focus(week: int) -> str:
    for item in load_template().get("weeks", []):
        if int(item["week"]) == int(week):
            return item.get("focus", "")
    return ""


def is_sprint_finished(profile: dict[str, Any]) -> bool:
    _, raw = get_current_day(profile)
    return raw > SPRINT_DAYS
