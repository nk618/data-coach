"""UI smoke tests using Streamlit's AppTest harness."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault(
    "DATACOACH_DATA_DIR", tempfile.mkdtemp(prefix="datacoach_ui_tests_")
)

from core import db, roadmap  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
SKILLS = ["SQL", "Python", "Excel", "Statistics", "Power BI", "Communication"]


class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db.init_db()
        db.reset_all()
        db.save_profile(
            name="Smoke Tester",
            target_role="Data Analyst",
            location="Remote",
            hours_per_day=3.5,
            start_date=date.today().isoformat(),
        )
        db.save_skills(
            [
                {
                    "skill": skill,
                    "self_rating": 3,
                    "diagnostic": 3.0,
                    "level": 3.0,
                    "sort_order": index,
                }
                for index, skill in enumerate(SKILLS)
            ]
        )
        roadmap.seed_from_template()

    def _run(self, page: str | None = None) -> AppTest:
        app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
        if page:
            app.session_state["page"] = page
            app.run()
        if len(app.exception) > 0:
            self.fail(f"App raised on page {page or 'default'}: {app.exception[0].value}")
        return app

    def test_today_renders(self) -> None:
        app = self._run("Today")
        self.assertIn("Today", app.session_state["page"])

    def test_all_pages_render(self) -> None:
        for page in [
            "Coach",
            "Data Lab",
            "Interview Room",
            "Dashboard Coach",
            "Job Tracker",
            "Progress",
            "Settings",
        ]:
            with self.subTest(page=page):
                self._run(page)

    def test_onboarding_renders_for_new_users(self) -> None:
        db.reset_all()
        try:
            app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("21-day sprint" in item.value for item in app.markdown))
        finally:
            db.save_profile(
                name="Smoke Tester",
                target_role="Data Analyst",
                location="Remote",
                hours_per_day=3.5,
                start_date=date.today().isoformat(),
            )
            db.save_skills(
                [
                    {
                        "skill": skill,
                        "self_rating": 3,
                        "diagnostic": 3.0,
                        "level": 3.0,
                        "sort_order": index,
                    }
                    for index, skill in enumerate(SKILLS)
                ]
            )
            roadmap.seed_from_template()


if __name__ == "__main__":
    unittest.main()
