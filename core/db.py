"""SQLite storage for profile, skills, roadmap, chat history, and settings."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    target_role TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    hours_per_day REAL NOT NULL DEFAULT 3.5,
    start_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    skill TEXT PRIMARY KEY,
    self_rating REAL NOT NULL,
    diagnostic REAL,
    level REAL NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diagnostic_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    skill TEXT NOT NULL,
    chosen INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    answered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roadmap_days (
    day INTEGER PRIMARY KEY,
    week INTEGER NOT NULL,
    theme TEXT NOT NULL,
    goal TEXT NOT NULL,
    deliverable TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roadmap_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day INTEGER NOT NULL REFERENCES roadmap_days(day) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    title TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    minutes INTEGER NOT NULL DEFAULT 30,
    resource_label TEXT,
    resource_url TEXT,
    completed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_day ON roadmap_tasks(day);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread TEXT NOT NULL DEFAULT 'coach',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    date_applied TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Applied',
    source TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    follow_up_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_date ON applications(date_applied);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
def get_profile() -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return dict(row) if row else None


def save_profile(
    name: str,
    target_role: str,
    location: str,
    hours_per_day: float,
    start_date: str,
) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO profile (id, name, target_role, location, hours_per_day, start_date, created_at)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                target_role = excluded.target_role,
                location = excluded.location,
                hours_per_day = excluded.hours_per_day,
                start_date = excluded.start_date
            """,
            (name.strip(), target_role, location.strip(), float(hours_per_day), start_date, _now()),
        )


def update_profile(profile: dict[str, Any]) -> None:
    save_profile(
        name=profile["name"],
        target_role=profile["target_role"],
        location=profile.get("location", ""),
        hours_per_day=float(profile.get("hours_per_day", 3.5)),
        start_date=profile["start_date"],
    )


# ---------------------------------------------------------------------------
# Skills and diagnostic
# ---------------------------------------------------------------------------
def save_skills(rows: Iterable[dict[str, Any]]) -> None:
    now = _now()
    with connection() as conn:
        conn.execute("DELETE FROM skills")
        for index, row in enumerate(rows):
            conn.execute(
                """
                INSERT INTO skills (skill, self_rating, diagnostic, level, sort_order, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["skill"],
                    float(row["self_rating"]),
                    float(row["diagnostic"]) if row.get("diagnostic") is not None else None,
                    float(row["level"]),
                    int(row.get("sort_order", index)),
                    now,
                ),
            )


def get_skills() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM skills ORDER BY sort_order, skill").fetchall()
    return [dict(r) for r in rows]


def save_diagnostic_answers(rows: Iterable[dict[str, Any]]) -> None:
    now = _now()
    with connection() as conn:
        conn.execute("DELETE FROM diagnostic_answers")
        for row in rows:
            conn.execute(
                """
                INSERT INTO diagnostic_answers (question_id, skill, chosen, correct, answered_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row["question_id"], row["skill"], int(row["chosen"]), int(row["correct"]), now),
            )


def get_diagnostic_answers() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM diagnostic_answers ORDER BY id").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------
def seed_roadmap(template: dict[str, Any]) -> tuple[int, int]:
    with connection() as conn:
        conn.execute("DELETE FROM roadmap_tasks")
        conn.execute("DELETE FROM roadmap_days")
        day_count = 0
        task_count = 0
        for day in template.get("days", []):
            conn.execute(
                """
                INSERT INTO roadmap_days (day, week, theme, goal, deliverable)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    int(day["day"]),
                    int(day["week"]),
                    day["theme"],
                    day.get("goal", ""),
                    day.get("deliverable", ""),
                ),
            )
            day_count += 1
            for order, task in enumerate(day.get("tasks", [])):
                conn.execute(
                    """
                    INSERT INTO roadmap_tasks
                        (day, sort_order, task_type, title, details, minutes,
                         resource_label, resource_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(day["day"]),
                        order,
                        task.get("type", "learn"),
                        task["title"],
                        task.get("details", ""),
                        int(task.get("minutes", 30)),
                        task.get("resource_label"),
                        task.get("resource_url"),
                    ),
                )
                task_count += 1
    return day_count, task_count


def get_all_days() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM roadmap_days ORDER BY day").fetchall()
    return [dict(r) for r in rows]


def get_day(day: int) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM roadmap_days WHERE day = ?", (int(day),)).fetchone()
    return dict(row) if row else None


def get_tasks(day: int) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM roadmap_tasks WHERE day = ? ORDER BY sort_order, id",
            (int(day),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_task(task_id: int) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM roadmap_tasks WHERE id = ?", (int(task_id),)).fetchone()
    return dict(row) if row else None


def set_task_completed(task_id: int, completed: bool) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE roadmap_tasks SET completed = ?, completed_at = ? WHERE id = ?",
            (1 if completed else 0, _now() if completed else None, int(task_id)),
        )


def _progress_from_row(row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None:
        return {"done": 0, "total": 0, "pct": 0.0, "minutes_done": 0, "minutes_total": 0}
    total = int(row["total"] or 0)
    done = int(row["done"] or 0)
    return {
        "done": done,
        "total": total,
        "pct": (done / total) if total else 0.0,
        "minutes_done": int(row["minutes_done"] or 0),
        "minutes_total": int(row["minutes_total"] or 0),
    }


def get_day_progress(day: int) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(completed), 0) AS done,
                COALESCE(SUM(minutes), 0) AS minutes_total,
                COALESCE(SUM(CASE WHEN completed = 1 THEN minutes ELSE 0 END), 0) AS minutes_done
            FROM roadmap_tasks
            WHERE day = ?
            """,
            (int(day),),
        ).fetchone()
    return _progress_from_row(row)


def get_overall_progress() -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(completed), 0) AS done,
                COALESCE(SUM(minutes), 0) AS minutes_total,
                COALESCE(SUM(CASE WHEN completed = 1 THEN minutes ELSE 0 END), 0) AS minutes_done
            FROM roadmap_tasks
            """
        ).fetchone()
    return _progress_from_row(row)


def get_all_days_with_progress() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT d.day, d.week, d.theme, d.goal, d.deliverable,
                   COUNT(t.id) AS total,
                   COALESCE(SUM(t.completed), 0) AS done
            FROM roadmap_days d
            LEFT JOIN roadmap_tasks t ON t.day = d.day
            GROUP BY d.day
            ORDER BY d.day
            """
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        total = int(item["total"] or 0)
        done = int(item["done"] or 0)
        item["pct"] = (done / total) if total else 0.0
        result.append(item)
    return result


def get_streak(reference: date | None = None) -> int:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT substr(completed_at, 1, 10) AS day
            FROM roadmap_tasks
            WHERE completed_at IS NOT NULL AND completed_at != ''
            """
        ).fetchall()
    dates = set()
    for row in rows:
        try:
            dates.add(date.fromisoformat(row["day"]))
        except (TypeError, ValueError):
            continue
    if not dates:
        return 0
    anchor = reference or date.today()
    if anchor not in dates:
        anchor -= timedelta(days=1)
        if anchor not in dates:
            return 0
    streak = 0
    while anchor in dates:
        streak += 1
        anchor -= timedelta(days=1)
    return streak


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def add_message(role: str, content: str, thread: str = "coach") -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (thread, role, content, created_at) VALUES (?, ?, ?, ?)",
            (thread, role, content, _now()),
        )


def get_messages(limit: int | None = None, thread: str = "coach") -> list[dict[str, Any]]:
    with connection() as conn:
        if limit:
            rows = conn.execute(
                """
                SELECT * FROM (
                    SELECT * FROM chat_messages WHERE thread = ? ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
                """,
                (thread, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE thread = ? ORDER BY id ASC",
                (thread,),
            ).fetchall()
    return [dict(r) for r in rows]


def clear_messages(thread: str = "coach") -> None:
    with connection() as conn:
        conn.execute("DELETE FROM chat_messages WHERE thread = ?", (thread,))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def get_setting(key: str, default: str | None = None) -> str | None:
    with connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


# ---------------------------------------------------------------------------
# Job applications
# ---------------------------------------------------------------------------
APPLICATION_STATUSES = [
    "Applied",
    "Screening",
    "Interview",
    "Offer",
    "Rejected",
    "Withdrawn",
]


def add_application(
    company: str,
    role: str,
    date_applied: str,
    status: str = "Applied",
    source: str = "",
    notes: str = "",
    follow_up_date: str | None = None,
) -> int:
    now = _now()
    with connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO applications
                (company, role, date_applied, status, source, notes,
                 follow_up_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company.strip(),
                role.strip(),
                date_applied,
                status,
                source.strip(),
                notes.strip(),
                follow_up_date,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)


def update_application(
    application_id: int,
    company: str,
    role: str,
    date_applied: str,
    status: str,
    source: str = "",
    notes: str = "",
    follow_up_date: str | None = None,
) -> None:
    with connection() as conn:
        conn.execute(
            """            UPDATE applications
            SET company = ?, role = ?, date_applied = ?, status = ?,
                source = ?, notes = ?, follow_up_date = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                company.strip(),
                role.strip(),
                date_applied,
                status,
                source.strip(),
                notes.strip(),
                follow_up_date,
                _now(),
                int(application_id),
            ),
        )


def delete_application(application_id: int) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM applications WHERE id = ?", (int(application_id),))


def get_application(application_id: int) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (int(application_id),)
        ).fetchone()
    return dict(row) if row else None


def get_applications(status: str | None = None) -> list[dict[str, Any]]:
    with connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY date_applied DESC, id DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM applications ORDER BY date_applied DESC, id DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def get_application_stats() -> dict[str, Any]:
    with connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM applications").fetchone()["c"]
        by_status = conn.execute(
            "SELECT status, COUNT(*) AS c FROM applications GROUP BY status"
        ).fetchall()
        recent = conn.execute(
            "SELECT COUNT(*) AS c FROM applications WHERE date_applied >= date('now', '-7 days')"
        ).fetchone()["c"]
        follow_ups = conn.execute(
            """
            SELECT COUNT(*) AS c FROM applications
            WHERE follow_up_date IS NOT NULL AND follow_up_date != ''
              AND follow_up_date <= date('now')
            """
        ).fetchone()["c"]
    return {
        "total": int(total or 0),
        "by_status": {row["status"]: int(row["c"]) for row in by_status},
        "recent": int(recent or 0),
        "follow_ups_due": int(follow_ups or 0),
    }


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------
def reset_all() -> None:
    with connection() as conn:
        for table in (
            "roadmap_tasks",
            "roadmap_days",
            "chat_messages",
            "diagnostic_answers",
            "skills",
            "profile",
            "settings",
            "applications",
        ):
            conn.execute(f"DELETE FROM {table}")
