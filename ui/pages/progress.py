"""Progress page: sprint completion, skill profile, and the full roadmap."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from core import db, roadmap
from ui.styles import badge, stat_card


def _open_day(day: int) -> None:
    st.session_state.view_day = day
    st.session_state.page = "Today"


def render() -> None:
    profile = db.get_profile()
    if not profile:
        st.error("No profile found. Please reload and complete onboarding.")
        return

    current_day, _ = roadmap.get_current_day(profile)
    days = db.get_all_days_with_progress()
    skills = db.get_skills()
    overall = db.get_overall_progress()
    streak = db.get_streak()
    days_complete = sum(1 for d in days if d["total"] and d["done"] == d["total"])

    st.title("Progress")
    st.caption(
        "Your sprint at a glance. Update the plan by finishing tasks — the coach uses this page "
        "to decide what to push next."
    )

    col_progress, col_streak, col_days, col_tasks = st.columns(4)
    col_progress.markdown(
        stat_card("Sprint", f"{overall['pct'] * 100:.0f}%", f"{overall['done']}/{overall['total']} tasks"),
        unsafe_allow_html=True,
    )
    col_streak.markdown(
        stat_card("Streak", f"{streak} day{'s' if streak != 1 else ''}", "consecutive study days"),
        unsafe_allow_html=True,
    )
    col_days.markdown(
        stat_card("Days complete", f"{days_complete}/21", f"today is Day {current_day}"),
        unsafe_allow_html=True,
    )
    col_tasks.markdown(
        stat_card("Focus time", f"{overall['minutes_done']} min", "logged by completed tasks"),
        unsafe_allow_html=True,
    )

    st.write("")
    left, right = st.columns([0.52, 0.48], gap="large")

    with left:
        with st.container(border=True):
            st.markdown("#### Skill profile")
            if skills:
                figure = go.Figure(
                    data=go.Scatterpolar(
                        r=[float(s["level"]) for s in skills],
                        theta=[s["skill"] for s in skills],
                        fill="toself",
                        line={"color": "#2563EB", "width": 2},
                        fillcolor="rgba(37, 99, 235, 0.14)",
                        hovertemplate="%{theta}: %{r:.1f}/5<extra></extra>",
                    )
                )
                figure.update_layout(
                    polar={
                        "radialaxis": {
                            "visible": True,
                            "range": [0, 5],
                            "tickvals": [1, 2, 3, 4, 5],
                            "gridcolor": "#E2E8F0",
                        },
                        "bgcolor": "rgba(0,0,0,0)",
                    },
                    showlegend=False,
                    margin={"l": 45, "r": 45, "t": 20, "b": 20},
                    height=310,
                    paper_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#475569"},
                )
                st.plotly_chart(
                    figure,
                    width="stretch",
                    config={"displayModeBar": False},
                )
            else:
                st.caption("Complete onboarding to build your skill profile.")

    with right:
        with st.container(border=True):
            st.markdown("#### Where to push next")
            weak = [s for s in skills if float(s["level"]) <= 2.5]
            if weak:
                st.markdown(
                    "".join(badge(s["skill"], "amber") for s in weak),
                    unsafe_allow_html=True,
                )
                st.caption(
                    "These skills are below 2.5/5. Ask the coach for extra drills and expect "
                    "harder follow-up questions here."
                )
            else:
                st.markdown(
                    badge("No major gaps detected", "green"),
                    unsafe_allow_html=True,
                )
                st.caption("Raise the difficulty: ask for harder SQL and case questions.")

            st.markdown("---")
            if skills:
                lowest = min(skills, key=lambda s: float(s["level"]))
                st.markdown(
                    f"**Suggested next drill:** a 20-minute {lowest['skill']} session. "
                    "Ask the coach to quiz you one question at a time."
                )

            st.markdown("---")
            st.markdown("#### Recent work")
            recent = [
                task
                for day in days
                for task in db.get_tasks(day["day"])
                if task["completed"]
            ]
            recent = sorted(
                [t for t in recent if t["completed_at"]],
                key=lambda t: t["completed_at"],
                reverse=True,
            )[:5]
            if recent:
                for task in recent:
                    st.markdown(
                        f"<span class='tiny'>Day {task['day']}</span> "
                        f"**{task['title']}**",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No completed tasks yet. Day 1 starts with the setup task.")

    st.write("")
    st.markdown("### Your 21-day plan")
    current_week = next((int(d["week"]) for d in days if d["day"] == current_day), 1)

    for week in (1, 2, 3):
        week_days = [d for d in days if int(d["week"]) == week]
        week_done = sum(1 for d in week_days if d["total"] and d["done"] == d["total"])
        with st.expander(
            f"Week {week} — {roadmap.week_theme(week)}  ·  {week_done}/{len(week_days)} days complete",
            expanded=(week == current_week),
        ):
            st.caption(roadmap.week_focus(week))
            for day in week_days:
                col_day, col_theme, col_bar, col_count, col_open = st.columns(
                    [0.1, 0.44, 0.2, 0.12, 0.14]
                )
                is_current = int(day["day"]) == current_day
                label = f"**Day {day['day']}**"
                if is_current:
                    label += "  \n<span class='tiny'>today</span>"
                col_day.markdown(label, unsafe_allow_html=True)
                col_theme.markdown(day["theme"])
                col_bar.progress(day["pct"] if day["total"] else 0.0)
                col_count.markdown(
                    f"<span class='tiny'>{day['done']}/{day['total']}</span>",
                    unsafe_allow_html=True,
                )
                col_open.button(
                    "Open",
                    key=f"open_day_{day['day']}",
                    on_click=_open_day,
                    args=(int(day["day"]),),
                    width="stretch",
                )
