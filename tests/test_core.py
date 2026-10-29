"""Core logic tests. Run with: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta

TEMP_DATA = tempfile.mkdtemp(prefix="datacoach_tests_")
os.environ["DATACOACH_DATA_DIR"] = TEMP_DATA

from core import db, diagnostic, prompts, roadmap  # noqa: E402


class CoreLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        db.init_db()
        db.reset_all()
        db.save_profile(
            name="Test Learner",
            target_role="Data Analyst",
            location="Remote",
            hours_per_day=3.5,
            start_date=date.today().isoformat(),
        )
        roadmap.seed_from_template()

    # ------------------------------------------------------------------
    # Content integrity
    # ------------------------------------------------------------------
    def test_template_has_21_days_and_four_tasks_each(self) -> None:
        template = roadmap.load_template()
        self.assertEqual(len(template["days"]), 21)
        self.assertEqual([d["day"] for d in template["days"]], list(range(1, 22)))
        for day in template["days"]:
            self.assertEqual(len(day["tasks"]), 4, f"Day {day['day']} task count")
            total_minutes = sum(int(t["minutes"]) for t in day["tasks"])
            self.assertGreaterEqual(total_minutes, 120, f"Day {day['day']} is too light")
            self.assertLessEqual(total_minutes, 300, f"Day {day['day']} is too heavy")
            types = {t["type"] for t in day["tasks"]}
            self.assertEqual(types, {"learn", "build", "prove", "log"})
            for task in day["tasks"]:
                if task.get("resource_url"):
                    self.assertTrue(task["resource_url"].startswith("https://"))

    def test_diagnostic_has_two_questions_per_skill(self) -> None:
        questions = diagnostic.load_questions()
        self.assertEqual(len(questions), 12)
        for skill in diagnostic.SKILL_ORDER:
            count = sum(1 for q in questions if q["skill"] == skill)
            self.assertEqual(count, 2, f"{skill} question count")
        for question in questions:
            self.assertIn(question["answer"], range(len(question["options"])))
            self.assertTrue(question["explanation"].strip())

    # ------------------------------------------------------------------
    # Profile and skills
    # ------------------------------------------------------------------
    def test_profile_roundtrip(self) -> None:
        profile = db.get_profile()
        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"], "Test Learner")
        self.assertEqual(profile["target_role"], "Data Analyst")

        profile["name"] = "Updated Name"
        db.update_profile(profile)
        self.assertEqual(db.get_profile()["name"], "Updated Name")

    def test_skills_roundtrip(self) -> None:
        rows = [
            {
                "skill": "SQL",
                "self_rating": 4,
                "diagnostic": 4.0,
                "level": 4.0,
                "sort_order": 0,
            },
            {
                "skill": "Python",
                "self_rating": 2,
                "diagnostic": 2.0,
                "level": 2.0,
                "sort_order": 1,
            },
        ]
        db.save_skills(rows)
        saved = db.get_skills()
        self.assertEqual(len(saved), 2)
        self.assertEqual(saved[0]["skill"], "SQL")
        self.assertAlmostEqual(float(saved[0]["level"]), 4.0)

    # ------------------------------------------------------------------
    # Roadmap and progress
    # ------------------------------------------------------------------
    def test_seeded_roadmap_counts(self) -> None:
        self.assertEqual(len(db.get_all_days()), 21)
        all_tasks = sum(len(db.get_tasks(day)) for day in range(1, 22))
        self.assertEqual(all_tasks, 84)

    def test_task_completion_and_streak(self) -> None:
        task = db.get_tasks(1)[0]
        self.assertEqual(db.get_day_progress(1)["done"], 0)

        db.set_task_completed(task["id"], True)
        progress = db.get_day_progress(1)
        self.assertEqual(progress["done"], 1)
        self.assertGreater(progress["minutes_done"], 0)
        self.assertEqual(db.get_overall_progress()["done"], 1)
        self.assertEqual(db.get_streak(), 1)

        db.set_task_completed(task["id"], False)
        self.assertEqual(db.get_day_progress(1)["done"], 0)
        self.assertEqual(db.get_streak(), 0)

    def test_current_day_calculation(self) -> None:
        profile = dict(db.get_profile())
        profile["start_date"] = (date.today() - timedelta(days=4)).isoformat()
        self.assertEqual(roadmap.get_current_day(profile), (5, 5))

        profile["start_date"] = (date.today() + timedelta(days=3)).isoformat()
        day, raw = roadmap.get_current_day(profile)
        self.assertEqual(day, 1)
        self.assertLessEqual(raw, 0)

        profile["start_date"] = (date.today() - timedelta(days=40)).isoformat()
        self.assertEqual(roadmap.get_current_day(profile), (21, 41))

    # ------------------------------------------------------------------
    # Diagnostic scoring
    # ------------------------------------------------------------------
    def test_diagnostic_all_correct(self) -> None:
        questions = diagnostic.load_questions()
        answers = {q["id"]: q["answer"] for q in questions}
        per_skill, ratios, details = diagnostic.score_answers(questions, answers)

        self.assertEqual(len(details), 12)
        for skill in diagnostic.SKILL_ORDER:
            self.assertEqual(per_skill[skill]["correct"], 2)
            self.assertAlmostEqual(ratios[skill], 1.0)

        rows = diagnostic.build_skill_rows({skill: 5 for skill in diagnostic.SKILL_ORDER}, ratios)
        for row in rows:
            self.assertAlmostEqual(row["level"], 5.0)

    def test_diagnostic_no_answers(self) -> None:
        questions = diagnostic.load_questions()
        _, ratios, details = diagnostic.score_answers(questions, {})
        self.assertTrue(all(value == 0.0 for value in ratios.values()))
        self.assertTrue(all(detail["chosen"] == -1 for detail in details))

        rows = diagnostic.build_skill_rows(
            {skill: 5 for skill in diagnostic.SKILL_ORDER}, ratios
        )
        for row in rows:
            self.assertAlmostEqual(row["level"], 3.0)

    # ------------------------------------------------------------------
    # Chat, settings, prompt, reset
    # ------------------------------------------------------------------
    def test_chat_history(self) -> None:
        db.add_message("user", "first")
        db.add_message("assistant", "second")
        db.add_message("user", "third")

        history = db.get_messages()
        self.assertEqual([m["content"] for m in history], ["first", "second", "third"])

        recent = db.get_messages(limit=2)
        self.assertEqual([m["content"] for m in recent], ["second", "third"])

        db.clear_messages()
        self.assertEqual(db.get_messages(), [])

    def test_settings(self) -> None:
        self.assertIsNone(db.get_setting("missing"))
        self.assertEqual(db.get_setting("missing", "fallback"), "fallback")
        db.set_setting("model", "gemini-test")
        self.assertEqual(db.get_setting("model"), "gemini-test")
        db.set_setting("model", "gemini-test-2")
        self.assertEqual(db.get_setting("model"), "gemini-test-2")

    def test_coach_prompt_contains_context(self) -> None:
        profile = db.get_profile()
        skills = [
            {
                "skill": "SQL",
                "self_rating": 2,
                "diagnostic": 2.0,
                "level": 2.0,
                "sort_order": 0,
            }
        ]
        day_info = db.get_day(1)
        tasks = db.get_tasks(1)
        overall = db.get_overall_progress()

        prompt = prompts.coach_system_prompt(
            profile, skills, 1, day_info, tasks, overall
        )
        self.assertIn("Test Learner", prompt)
        self.assertIn("Data Analyst", prompt)
        self.assertIn("SQL: 2.0/5", prompt)
        self.assertIn("Weak areas", prompt)
        self.assertIn("Day 1 of 21", prompt)

    def test_reset_all(self) -> None:
        db.reset_all()
        self.assertIsNone(db.get_profile())
        self.assertEqual(db.get_skills(), [])
        self.assertEqual(db.get_messages(), [])
        self.assertEqual(db.get_all_days(), [])


if __name__ == "__main__":
    unittest.main()
