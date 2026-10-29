"""Diagnostic quiz loading and skill-level scoring."""

from __future__ import annotations

import json
from typing import Any

from .config import ASSETS_DIR

SKILL_ORDER = ["SQL", "Python", "Excel", "Statistics", "Power BI", "Communication"]

SKILL_LABELS = {
    "SQL": "SQL & databases",
    "Python": "Python / pandas",
    "Excel": "Excel",
    "Statistics": "Statistics",
    "Power BI": "Power BI / DAX",
    "Communication": "Communication & business sense",
}


def load_questions() -> list[dict[str, Any]]:
    path = ASSETS_DIR / "diagnostic.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["questions"]


def score_answers(
    questions: list[dict[str, Any]], answers: dict[str, int | None]
) -> tuple[dict[str, dict[str, int]], dict[str, float], list[dict[str, Any]]]:
    """Return per-skill counts, per-skill ratio (0-1), and answer details."""
    per_skill = {skill: {"correct": 0, "total": 0} for skill in SKILL_ORDER}
    details: list[dict[str, Any]] = []

    for question in questions:
        skill = question["skill"]
        choice = answers.get(question["id"])
        is_correct = choice is not None and int(choice) == int(question["answer"])
        per_skill.setdefault(skill, {"correct": 0, "total": 0})
        per_skill[skill]["total"] += 1
        per_skill[skill]["correct"] += int(is_correct)
        details.append(
            {
                "question_id": question["id"],
                "skill": skill,
                "chosen": -1 if choice is None else int(choice),
                "correct": int(is_correct),
            }
        )

    ratios = {
        skill: (counts["correct"] / counts["total"] if counts["total"] else 0.0)
        for skill, counts in per_skill.items()
    }
    return per_skill, ratios, details


def build_skill_rows(
    self_ratings: dict[str, float], ratios: dict[str, float]
) -> list[dict[str, Any]]:
    """Blend self-assessment with the diagnostic into a 1-5 level."""
    rows: list[dict[str, Any]] = []
    for index, skill in enumerate(SKILL_ORDER):
        self_rating = max(1.0, min(5.0, float(self_ratings.get(skill, 2))))
        diagnostic_level = 1.0 + 4.0 * max(0.0, min(1.0, ratios.get(skill, 0.0)))
        level = round(0.5 * self_rating + 0.5 * diagnostic_level, 1)
        rows.append(
            {
                "skill": skill,
                "self_rating": self_rating,
                "diagnostic": round(diagnostic_level, 1),
                "level": max(1.0, min(5.0, level)),
                "sort_order": index,
            }
        )
    return rows


def weak_skills(rows: list[dict[str, Any]], threshold: float = 2.5) -> list[str]:
    return [row["skill"] for row in rows if float(row["level"]) <= threshold]
