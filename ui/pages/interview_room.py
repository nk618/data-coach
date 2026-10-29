"""Interview Room: timed mock interviews with a scored report card."""

from __future__ import annotations

import time
from datetime import datetime

import streamlit as st

from core import config, db, llm, prompts, roadmap
from ui.styles import hero, stat_card

FOCUS_OPTIONS = [
    "SQL",
    "Python / pandas",
    "Statistics",
    "Power BI / DAX",
    "Case study",
    "Behavioral (STAR)",
    "Mixed (full panel)",
]

DIFFICULTY = ["Junior", "Mid-level", "Senior"]
LENGTHS = [15, 20, 30, 45]


def _system_prompt(profile, focus, difficulty, length, skills, day_info, tasks, overall) -> str:
    base = prompts.coach_system_prompt(
        profile=profile,
        skills=skills,
        day=roadmap.get_current_day(profile)[0],
        day_info=day_info,
        tasks=tasks,
        overall=overall,
        sprint_finished=False,
    )
    return (
        base
        + f"\n\nINTERVIEW MODE\n"
        f"- You are running a timed mock interview for a {profile.get('target_role', 'Data Analyst')} role.\n"
        f"- Focus: {focus}. Difficulty: {difficulty}. Target length: {length} minutes.\n"
        f"- Ask ONE question at a time. Wait for the candidate's answer before the next question.\n"
        f"- Do not reveal the answer or give hints unless the candidate asks.\n"
        f"- After each answer, give brief feedback (correct/incorrect + one key point) but do NOT move on until the candidate is ready.\n"
        f"- Use realistic follow-ups: 'How would you handle NULLs?', 'What's the denominator?', 'Can you optimize this?'.\n"
        f"- After {length} minutes or when the candidate says 'end interview', stop and produce a REPORT CARD with scores 1-5 for: "
        "Technical correctness, Problem solving, Communication, Business sense, and Overall. Include strengths, gaps, and the single highest-impact thing to practice.\n"
        f"- For SQL questions, give a short scenario and ask for a query. For behavioral, ask STAR stories.\n"
        f"- Keep each question self-contained and realistic for a {difficulty.lower()} analyst.\n"
    )


def render() -> None:
    profile = db.get_profile()
    if not profile:
        st.error("No profile found. Please reload and complete onboarding.")
        return

    api_key = config.get_api_key()
    if not api_key:
        st.warning("The Interview Room needs a Gemini API key. Add one in Settings.")
        if st.button("Go to Settings", type="primary"):
            st.session_state.page = "Settings"
            st.rerun()
        return

    st.markdown(
        hero(
            "Interview Room",
            "Timed mock interviews with a scored report card",
            "One question at a time, realistic follow-ups, and a scored report at the end. "
            "Your weak areas feed the question mix.",
        ),
        unsafe_allow_html=True,
    )

    # Session state
    active = st.session_state.get("interview_active", False)
    messages = st.session_state.get("interview_messages", [])

    if not active:
        st.markdown("#### Configure the interview")
        with st.container(border=True):
            focus = st.selectbox("Focus area", FOCUS_OPTIONS, index=0)
            difficulty = st.selectbox("Difficulty", DIFFICULTY, index=1)
            length = st.selectbox("Length (minutes)", LENGTHS, index=2)
            col_start, col_info = st.columns([0.4, 0.6])
            if col_start.button("Start interview", type="primary", width="stretch"):
                st.session_state.interview_active = True
                st.session_state.interview_focus = focus
                st.session_state.interview_difficulty = difficulty
                st.session_state.interview_length = length
                st.session_state.interview_start = time.time()
                st.session_state.interview_messages = []
                st.session_state.interview_ended = False
                st.rerun()
            col_info.caption(
                "The coach asks one question at a time. Answer in the chat box, then "
                "say 'next' or 'end interview' when you're ready for feedback or to finish."
            )

        st.markdown("#### Tips")
        st.markdown(
            "- Think out loud. Interviewers score the process, not just the final answer.\n"
            "- State assumptions and edge cases before writing code.\n"
            "- If you don't know, say what you'd check instead of guessing.\n"
            "- Use 'end interview' to trigger the report card early."
        )
        return

    focus = st.session_state.get("interview_focus", "Mixed (full panel)")
    difficulty = st.session_state.get("interview_difficulty", "Mid-level")
    length = st.session_state.get("interview_length", 30)
    start = st.session_state.get("interview_start", time.time())
    elapsed = time.time() - start
    remaining = max(0, length * 60 - elapsed)
    ended = st.session_state.get("interview_ended", False)

    # Header with timer
    timer_col, end_col = st.columns([0.7, 0.3])
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    timer_col.markdown(
        f"**{focus}** · {difficulty} · {mins:02d}:{secs:02d} remaining",
    )
    if not ended and end_col.button("End interview", type="primary", width="stretch"):
        st.session_state.interview_ended = True
        st.session_state.interview_messages.append(
            {"role": "user", "content": "end interview"}
        )
        st.rerun()

    if remaining <= 0 and not ended:
        st.session_state.interview_ended = True
        st.session_state.interview_messages.append(
            {"role": "user", "content": "time is up, end interview"}
        )
        st.rerun()

    # Render transcript
    for msg in messages:
        role = "user" if msg["role"] == "user" else "assistant"
        avatar = "🧑‍💻" if role == "user" else "🎯"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

    # If just started, kick off with an opening
    if not messages:
        st.session_state.interview_messages.append(
            {"role": "user", "content": "Start the interview. Greet me briefly and ask the first question."}
        )
        st.rerun()

    # Handle pending AI reply
    if messages and messages[-1]["role"] == "user":
        profile = db.get_profile()
        skills = db.get_skills()
        day, _ = roadmap.get_current_day(profile)
        day_info = db.get_day(day)
        tasks = db.get_tasks(day)
        overall = db.get_overall_progress()
        system_prompt = _system_prompt(profile, focus, difficulty, length, skills, day_info, tasks, overall)
        model = db.get_setting("model") or config.DEFAULT_MODEL
        payload = [{"role": m["role"], "content": m["content"]} for m in messages]

        with st.chat_message("assistant", avatar="🎯"):
            try:
                reply = st.write_stream(llm.stream_chat(payload, system_prompt, model=model))
            except llm.LLMError as exc:
                st.error(str(exc))
                reply = None
        if reply:
            st.session_state.interview_messages.append({"role": "assistant", "content": reply})
            st.rerun()

    typed = st.chat_input("Your answer…", key="interview_input")
    if typed:
        st.session_state.interview_messages.append({"role": "user", "content": typed})
        st.rerun()

    if ended and messages and messages[-1]["role"] == "assistant":
        st.success("Interview complete. Review the report card above.")
        if st.button("Start a new interview", type="primary"):
            for key in ["interview_active", "interview_messages", "interview_ended",
                        "interview_focus", "interview_difficulty", "interview_length",
                        "interview_start"]:
                st.session_state.pop(key, None)
            st.rerun()
