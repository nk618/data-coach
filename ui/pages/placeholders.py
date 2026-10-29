"""Placeholders for modules arriving in later build phases."""

from __future__ import annotations

import streamlit as st

from ui.styles import hero


def _coming_soon(
    eyebrow: str,
    title: str,
    subtitle: str,
    features: list[str],
    coach_prompt: str,
) -> None:
    st.markdown(hero(eyebrow, title, subtitle), unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### What's coming")
        for feature in features:
            st.markdown(f"- {feature}")
        st.caption(
            "Until then, the Coach can handle this manually — paste your data summary, code, "
            "or dashboard screenshot and ask for feedback."
        )

    col_today, col_coach = st.columns(2)
    if col_today.button("Back to today's plan", width="stretch"):
        st.session_state.page = "Today"
        st.rerun()
    if col_coach.button("Ask the coach instead", type="primary", width="stretch"):
        st.session_state.pending_prompt = coach_prompt
        st.session_state.page = "Coach"
        st.rerun()


def data_lab() -> None:
    _coming_soon(
        "Phase 2 · next build",
        "Data Lab",
        "Upload a dataset and work through it with a guided profiler, cleaning checklist, "
        "and a safe SQL runner.",
        [
            "Upload CSV or Excel and get an instant profile: shape, types, missing values, duplicates, outliers, and correlations.",
            "A plain-English data understanding brief with business questions worth asking.",
            "A prioritized cleaning checklist with pandas and SQL for every step — plus before/after validation.",
            "Run SELECT queries against your upload in a sandboxed DuckDB engine and export the cleaned file.",
            "Generate a portfolio-ready cleaning log automatically.",
        ],
        "I want to practice the Data Lab workflow on a dataset. Give me a checklist for "
        "profiling and cleaning it, and tell me what to look for first.",
    )


def interview_room() -> None:
    _coming_soon(
        "Phase 3 · next build",
        "Interview Room",
        "Timed mock interviews across HR, SQL, Python, statistics, Power BI, and case studies — "
        "with a scored report card at the end.",
        [
            "Choose role, focus area, difficulty, and session length (20, 30, or 45 minutes).",
            "One question at a time with realistic follow-ups — no answer leaks mid-interview.",
            "Live SQL questions checked against a real sample database, not just judged by the model.",
            "Scoring across correctness, structure, communication, and depth, with model answers.",
            "Weak areas feed back into your roadmap and the coach's context.",
        ],
        "Run a 30-minute mock interview for a Data Analyst role. Start with SQL, then one "
        "behavioral question. Ask one question at a time and score me at the end.",
    )


def dashboard_coach() -> None:
    _coming_soon(
        "Phase 4 · next build",
        "Dashboard Coach",
        "Design KPIs and charts, write DAX, and get a prioritized critique of your Power BI "
        "dashboard from a screenshot.",
        [
            "Turn a business question into the right KPI, chart, and layout.",
            "Power BI DAX and Tableau calculated-field help with explanations, not just formulas.",
            "Upload a dashboard screenshot for a scored review: chart choice, hierarchy, clutter, color, and insight titles.",
            "A pre-publish checklist so you catch broken numbers and misleading axes before an interviewer does.",
        ],
        "Review my dashboard plan. I'm building a Power BI page for an e-commerce business. "
        "Ask me what the page needs to answer, then recommend KPIs, charts, and layout.",
    )
