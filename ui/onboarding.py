"""First-run onboarding: profile, self-assessment, diagnostic, and plan preview."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from core import db, diagnostic, roadmap
from ui.styles import badge, hero, skill_bar

HIDE_SIDEBAR = """
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] {display: none !important;}
</style>
"""

ROLES = [
    "Data Analyst",
    "Business Analyst",
    "BI Analyst",
    "Product Analyst",
    "Analytics Engineer",
]

SKILLS = [
    ("SQL", "SQL & databases", "Joins, aggregation, CTEs, window functions."),
    ("Python", "Python / pandas", "Loading, cleaning, grouping, and plotting data."),
    ("Excel", "Excel", "Lookups, pivot tables, formulas, and charts."),
    ("Statistics", "Statistics", "Distributions, correlation, confidence intervals, testing."),
    ("Power BI", "Power BI / DAX", "Data models, visuals, measures, and dashboard design."),
    (
        "Communication",
        "Communication & business sense",
        "Turning findings into clear, decision-ready recommendations.",
    ),
]


def _stepper(step: int) -> None:
    labels = ["Profile", "Skills", "Diagnostic", "Plan"]
    columns = st.columns(4)
    for index, (label, column) in enumerate(zip(labels, columns), start=1):
        if index < step:
            html = badge(f"✓ {label}", "green")
        elif index == step:
            html = badge(f"{index}. {label}")
        else:
            html = badge(f"{index}. {label}", "gray")
        column.markdown(html, unsafe_allow_html=True)
    st.write("")


def _step_profile() -> None:
    st.markdown(
        hero(
            "Step 1 of 4",
            "Let's build your 21-day sprint",
            "Four questions, then a short diagnostic. The coach uses this to calibrate the plan "
            "and the difficulty of your practice.",
            "Takes about 10 minutes · everything is stored on this PC",
        ),
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.62, 0.38], gap="large")

    with left:
        with st.form("onboarding_profile"):
            name = st.text_input(
                "What should I call you?",
                placeholder="Your first name",
                key="ob_name",
            )
            role = st.selectbox("Target role", ROLES, index=0, key="ob_role")
            location = st.text_input(
                "Location (optional)",
                placeholder="City, or Remote",
                key="ob_location",
            )
            hours = st.slider(
                "Focused study hours per day",
                min_value=1.0,
                max_value=8.0,
                value=3.5,
                step=0.5,
                key="ob_hours",
                help="Be honest. The plan is calibrated to the time you actually have.",
            )
            start = st.date_input(
                "Sprint start date",
                value=date.today(),
                key="ob_start",
                help="Day 1 begins on this date.",
            )
            submitted = st.form_submit_button(
                "Continue →", type="primary", width="stretch"
            )

        if submitted:
            if not name.strip():
                st.error("Please enter your name so the coach knows what to call you.")
            else:
                st.session_state.ob_profile = {
                    "name": name.strip(),
                    "target_role": role,
                    "location": location.strip(),
                    "hours_per_day": float(hours),
                    "start_date": start.isoformat(),
                }
                st.session_state.ob_step = 2
                st.rerun()

    with right:
        with st.container(border=True):
            st.markdown("#### What happens next")
            st.markdown(
                "1. **A 12-question diagnostic** across SQL, Python, Excel, statistics, "
                "Power BI, and business thinking.\n"
                "2. **A calibrated plan** — your scores adjust the depth of each week.\n"
                "3. **Day 1 starts immediately** — no waiting for the app to be finished."
            )
            st.markdown("---")
            st.markdown(
                "<span class='tiny'>The diagnostic is for calibration, not a grade. "
                "Wrong answers are useful.</span>",
                unsafe_allow_html=True,
            )


def _step_skills() -> None:
    st.markdown(
        hero(
            "Step 2 of 4",
            "How confident are you today?",
            "Rate yourself honestly. These ratings are blended with your diagnostic score — "
            "they are not used to judge you.",
        ),
        unsafe_allow_html=True,
    )

    existing = st.session_state.get("ob_self", {})
    with st.form("onboarding_skills"):
        st.caption("1 = never used it · 3 = can do it with help · 5 = confident and independent")
        columns = st.columns(2, gap="large")
        values: dict[str, float] = {}
        for index, (key, label, help_text) in enumerate(SKILLS):
            target = columns[index % 2]
            with target:
                values[key] = st.slider(
                    label,
                    min_value=1,
                    max_value=5,
                    value=int(existing.get(key, 2)),
                    step=1,
                    key=f"ob_self_{key}",
                    help=help_text,
                )
        submitted = st.form_submit_button(
            "Continue →", type="primary", width="stretch"
        )

    if submitted:
        st.session_state.ob_self = {key: float(value) for key, value in values.items()}
        st.session_state.ob_step = 3
        st.session_state.diag_page = 0
        st.rerun()


def _step_diagnostic() -> None:
    questions = diagnostic.load_questions()
    page = int(st.session_state.get("diag_page", 0))
    start = page * 4
    subset = questions[start : start + 4]

    st.markdown(
        hero(
            f"Step 3 of 4 · Questions {start + 1}–{start + len(subset)}",
            "Quick diagnostic",
            "No searching, no AI help. Pick the best answer. You will see the explanations "
            "at the end.",
            f"{len(questions)} questions total · about 8 minutes",
        ),
        unsafe_allow_html=True,
    )

    with st.form(f"diagnostic_page_{page}"):
        choices: dict[str, Any] = {}
        for offset, question in enumerate(subset):
            number = start + offset + 1
            st.markdown(f"**{number}. {question['question']}**")
            st.caption(f"{question['skill']} · {question['difficulty'].title()}")
            choices[question["id"]] = st.radio(
                "Choose one",
                options=list(range(len(question["options"]))),
                format_func=lambda index, options=question["options"]: options[index],
                index=None,
                key=f"diag_choice_{question['id']}",
                label_visibility="collapsed",
            )
            if offset < len(subset) - 1:
                st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        label = "See my results →" if page >= 2 else "Next questions →"
        submitted = st.form_submit_button(
            label, type="primary", width="stretch"
        )

    if submitted:
        missing = [qid for qid, value in choices.items() if value is None]
        if missing:
            st.error("Please answer every question on this page before continuing.")
        else:
            answers = st.session_state.setdefault("diag_answers", {})
            answers.update({qid: int(value) for qid, value in choices.items()})
            if page < 2:
                st.session_state.diag_page = page + 1
            else:
                st.session_state.ob_step = 4
            st.rerun()


def _step_results() -> None:
    questions = diagnostic.load_questions()
    answers = st.session_state.get("diag_answers", {})
    self_ratings = st.session_state.get("ob_self", {})
    _, ratios, _ = diagnostic.score_answers(questions, answers)
    skills = diagnostic.build_skill_rows(self_ratings, ratios)
    weak = [row["skill"] for row in skills if float(row["level"]) <= 2.5]

    st.markdown(
        hero(
            "Step 4 of 4",
            "Your starting point",
            "This is where the coach will apply pressure — and where it will support you.",
        ),
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.58, 0.42], gap="large")

    with left:
        with st.container(border=True):
            st.markdown("#### Skill profile")
            for row in skills:
                col_name, col_bar, col_value = st.columns([0.38, 0.44, 0.18])
                col_name.markdown(f"**{row['skill']}**")
                col_bar.markdown(skill_bar(row["level"]), unsafe_allow_html=True)
                col_value.markdown(
                    f"<span class='tiny'>{row['level']:.1f}/5</span>",
                    unsafe_allow_html=True,
                )

    with right:
        with st.container(border=True):
            st.markdown("#### Focus areas")
            if weak:
                for skill in weak:
                    st.markdown(badge(skill, "amber"), unsafe_allow_html=True)
                st.caption(
                    "The coach will add extra drills here and check your reasoning more closely."
                )
            else:
                st.markdown(badge("No major gaps detected", "green"), unsafe_allow_html=True)
                st.caption(
                    "Your first plan will still include fundamentals, but with harder stretches."
                )

            st.markdown("---")
            st.markdown("#### Your 21 days")
            template = roadmap.load_template()
            for week in template["weeks"]:
                st.markdown(
                    f"**Week {week['week']} — {week['theme']}**  \n"
                    f"<span class='tiny'>{week['focus']}</span>",
                    unsafe_allow_html=True,
                )

    with st.expander("Review the diagnostic answers and explanations"):
        for number, question in enumerate(questions, start=1):
            chosen = answers.get(question["id"])
            correct = chosen == question["answer"]
            chosen_text = (
                question["options"][int(chosen)] if chosen is not None else "No answer"
            )
            st.markdown(f"**{number}. {question['question']}**")
            icon = "✅" if correct else "❌"
            st.markdown(
                f"{icon} **Your answer:** {chosen_text}  \n"
                f"**Correct answer:** {question['options'][question['answer']]}"
            )
            st.caption(question["explanation"])
            if number < len(questions):
                st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    st.write("")
    if st.button("Create my plan and start Day 1 →", type="primary", width="stretch"):
        profile = st.session_state.get("ob_profile")
        if not profile or not self_ratings or not answers:
            st.error("Something is missing. Please refresh the page and start again.")
            return

        _, ratios, details = diagnostic.score_answers(questions, answers)
        rows = diagnostic.build_skill_rows(self_ratings, ratios)

        db.save_profile(
            name=profile["name"],
            target_role=profile["target_role"],
            location=profile.get("location", ""),
            hours_per_day=profile["hours_per_day"],
            start_date=profile["start_date"],
        )
        db.save_skills(rows)
        db.save_diagnostic_answers(details)
        days, tasks = roadmap.seed_from_template()

        for key in list(st.session_state.keys()):
            if key.startswith("ob_") or key.startswith("diag_"):
                del st.session_state[key]

        st.session_state.page = "Today"
        st.session_state.just_onboarded = True
        st.session_state.onboarding_summary = f"{days} days and {tasks} tasks created."
        st.rerun()


def render() -> None:
    st.markdown(HIDE_SIDEBAR, unsafe_allow_html=True)
    step = int(st.session_state.get("ob_step", 1))
    _stepper(step)

    if step == 1:
        _step_profile()
    elif step == 2:
        _step_skills()
    elif step == 3:
        _step_diagnostic()
    else:
        _step_results()
