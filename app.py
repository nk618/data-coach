"""Data Coach — a local desktop coach for a 21-day data analyst sprint."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Data Coach",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core import config, db, roadmap  # noqa: E402
from ui import onboarding  # noqa: E402
from ui.pages import coach, placeholders, progress, settings, today  # noqa: E402
from ui.styles import inject_css  # noqa: E402

NAV = [
    ("Today", "🏠  Today"),
    ("Coach", "💬  Coach"),
    ("Data Lab", "🧪  Data Lab · soon"),
    ("Interview Room", "🎯  Interview Room · soon"),
    ("Progress", "📈  Progress"),
    ("Settings", "⚙️  Settings"),
]

PAGES = {
    "Today": today.render,
    "Coach": coach.render,
    "Data Lab": placeholders.data_lab,
    "Interview Room": placeholders.interview_room,
    "Progress": progress.render,
    "Settings": settings.render,
}

BRAND = """
<div style="display:flex;align-items:center;gap:10px;margin:0 0 6px 0;">
  <div style="width:38px;height:38px;border-radius:11px;background:#2563EB;color:#FFFFFF;
              display:flex;align-items:center;justify-content:center;font-size:19px;">📊</div>
  <div>
    <div style="font-weight:800;font-size:1.06rem;color:#0F172A;line-height:1.1;">Data Coach</div>
    <div style="font-size:0.72rem;color:#64748B;">21-day analyst sprint</div>
  </div>
</div>
"""


def _render_sidebar(profile: dict) -> None:
    with st.sidebar:
        st.markdown(BRAND, unsafe_allow_html=True)
        st.caption(f"{profile['name']} · {profile['target_role']}")
        st.write("")

        page = st.session_state.get("page", "Today")
        for key, label in NAV:
            if st.button(
                label,
                key=f"nav_{key}",
                width="stretch",
                type="primary" if page == key else "secondary",
            ):
                st.session_state.page = key
                st.rerun()

        st.write("")
        st.markdown("---")
        day, _ = roadmap.get_current_day(profile)
        overall = db.get_overall_progress()
        st.caption(f"Day {day} of 21 · {overall['done']}/{overall['total']} tasks")
        st.progress(overall["pct"] if overall["total"] else 0.0)
        streak = db.get_streak()
        if streak:
            st.caption(f"🔥 {streak}-day streak")
        else:
            st.caption("Start today to build your streak.")

        st.write("")
        st.caption(f"v{config.VERSION} · local-first")


def main() -> None:
    inject_css()
    db.init_db()

    profile = db.get_profile()
    if not profile:
        onboarding.render()
        return

    if db.get_overall_progress()["total"] == 0:
        roadmap.seed_from_template()

    if "page" not in st.session_state or st.session_state.page not in PAGES:
        st.session_state.page = "Today"

    _render_sidebar(profile)
    page = st.session_state.page
    PAGES[page]()


main()
