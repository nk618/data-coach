"""Today page: the daily plan, task checkboxes, and progress."""

from __future__ import annotations

import streamlit as st

from core import config, db, roadmap
from ui.styles import hero, stat_card

TYPE_META = {
    "learn": {"label": "Learn", "emoji": "📘"},
    "build": {"label": "Build", "emoji": "🛠️"},
    "prove": {"label": "Prove", "emoji": "🎯"},
    "log": {"label": "Log", "emoji": "📝"},
}


def _toggle_task(task_id: int, key: str) -> None:
    db.set_task_completed(task_id, bool(st.session_state.get(key)))


def _back_to_today() -> None:
    st.session_state.pop("view_day", None)


def render() -> None:
    profile = db.get_profile()
    if not profile:
        st.error("No profile found. Please reload and complete onboarding.")
        return

    current_day, raw_day = roadmap.get_current_day(profile)
    view_day = int(st.session_state.get("view_day", current_day))
    if view_day < 1 or view_day > roadmap.SPRINT_DAYS:
        view_day = current_day

    if st.session_state.pop("just_onboarded", False):
        summary = st.session_state.pop("onboarding_summary", "Your plan is ready.")
        st.toast(f"Plan created. {summary}")

    day_info = db.get_day(view_day)
    if day_info is None:
        st.error("That day is not in your plan. Reset the app in Settings to rebuild the roadmap.")
        return

    tasks = db.get_tasks(view_day)
    progress = db.get_day_progress(view_day)
    overall = db.get_overall_progress()
    week_theme = roadmap.week_theme(day_info["week"])

    if view_day != current_day:
        banner_col, button_col = st.columns([0.78, 0.22])
        banner_col.info(
            f"You are reviewing Day {view_day}. Today is Day {current_day} of the sprint."
        )
        button_col.button(
            "← Back to today",
            on_click=_back_to_today,
            width="stretch",
        )

    if roadmap.is_sprint_finished(profile) and view_day == current_day:
        st.success(
            "Your 21-day sprint window is complete. Keep the streak alive with applications, "
            "mock interviews, and portfolio polish — or reset the sprint in Settings to run it again."
        )

    if not config.get_api_key():
        message_col, button_col = st.columns([0.72, 0.28])
        message_col.warning(
            "The coach is not connected yet. Add your free Gemini API key to unlock chat and feedback."
        )
        if button_col.button(
            "Connect now",
            type="primary",
            width="stretch",
        ):
            st.session_state.page = "Settings"
            st.rerun()

    st.markdown(
        hero(
            f"Day {view_day} of 21 · Week {day_info['week']}",
            day_info["theme"],
            day_info["goal"],
            f"{week_theme} · Deliverable: {day_info['deliverable']}",
        ),
        unsafe_allow_html=True,
    )

    col_tasks, col_time, col_sprint = st.columns(3)
    col_tasks.markdown(
        stat_card(
            "Today's tasks",
            f"{progress['done']}/{progress['total']}",
            "complete" if progress["total"] else "no tasks",
        ),
        unsafe_allow_html=True,
    )
    col_time.markdown(
        stat_card(
            "Focus time",
            f"{progress['minutes_done']} min",
            f"of {progress['minutes_total']} planned",
        ),
        unsafe_allow_html=True,
    )
    col_sprint.markdown(
        stat_card(
            "Sprint progress",
            f"{overall['pct'] * 100:.0f}%",
            f"{overall['done']} of {overall['total']} tasks",
        ),
        unsafe_allow_html=True,
    )

    st.progress(
        progress["pct"],
        text=f"{progress['done']} of {progress['total']} tasks finished on Day {view_day}",
    )
    st.write("")

    for task in tasks:
        meta = TYPE_META.get(task["task_type"], {"label": task["task_type"].title(), "emoji": "•"})
        is_done = bool(task["completed"])
        with st.container(border=True):
            col_check, col_body = st.columns([0.055, 0.945])
            with col_check:
                st.checkbox(
                    "Done",
                    value=is_done,
                    key=f"done_{task['id']}",
                    label_visibility="collapsed",
                    on_change=_toggle_task,
                    args=(task["id"], f"done_{task['id']}"),
                )
            with col_body:
                title = f"~~{task['title']}~~" if is_done else task["title"]
                st.markdown(f"**{title}**")
                st.markdown(
                    f"<span class='pill {task['task_type']}'>{meta['label']}</span> "
                    f"<span class='tiny'>{meta['emoji']} ~{task['minutes']} min</span>",
                    unsafe_allow_html=True,
                )
                if task["details"]:
                    st.markdown(task["details"])
                if task["resource_url"]:
                    st.link_button(
                        f"Open: {task['resource_label'] or 'resource'} ↗",
                        task["resource_url"],
                    )

    if progress["total"] and progress["done"] == progress["total"]:
        st.success(
            "Day complete. Write down three takeaways and one thing that still confuses you — "
            "that five-minute habit is what makes tomorrow's session faster."
        )

    st.info(f"**Deliverable for today:** {day_info['deliverable']}")

    if st.button(
        "Discuss this day with your coach →",
        type="primary",
        width="stretch",
    ):
        st.session_state.pending_prompt = (
            f"I'm on Day {view_day}: {day_info['theme']}. My goal is: {day_info['goal']}. "
            "Walk me through how to approach today's tasks, tell me what good work looks like, "
            "and ask me one question to check my understanding before I start."
        )
        st.session_state.page = "Coach"
        st.rerun()

    if current_day > 1 or view_day != current_day:
        st.caption(
            f"Today is Day {current_day} of the sprint. Use Progress to open any day you want to review."
        )
    elif raw_day == 1:
        st.caption("Day 1 is today. Start with the first learn task — do not skip the setup.")
