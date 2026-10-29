"""Coach page: streaming chat grounded in the learner's sprint and skill profile."""

from __future__ import annotations

import streamlit as st

from core import config, db, llm, prompts, roadmap


def _new_conversation() -> None:
    db.clear_messages()


def _render_key_setup() -> None:
    st.title("Coach")
    st.caption("Your data analyst mentor — direct feedback, real examples, no fluff.")
    st.warning("The coach needs a free Google Gemini API key before it can reply.")

    with st.container(border=True):
        st.markdown("#### Connect your key in 5 minutes")
        st.markdown(
            "1. Open [Google AI Studio](https://aistudio.google.com/apikey) and sign in.\n"
            "2. Click **Create API key** — let it create a project if asked.\n"
            "3. Copy the key (it starts with `AIza`).\n"
            "4. Open **Settings** in the sidebar, paste the key, and test the connection.\n\n"
            "The key is stored in Windows Credential Locker, not in a text file."
        )
        col_link, col_settings = st.columns(2)
        col_link.link_button(
            "Open Google AI Studio ↗",
            "https://aistudio.google.com/apikey",
            width="stretch",
        )
        if col_settings.button("Go to Settings", type="primary", width="stretch"):
            st.session_state.page = "Settings"
            st.rerun()


def render() -> None:
    profile = db.get_profile()
    if not profile:
        st.error("No profile found. Please reload and complete onboarding.")
        return

    messages = db.get_messages()
    api_key = config.get_api_key()
    if not api_key:
        _render_key_setup()
        return

    skills = db.get_skills()
    day, raw_day = roadmap.get_current_day(profile)
    day_info = db.get_day(day)
    tasks = db.get_tasks(day)
    overall = db.get_overall_progress()
    model = db.get_setting("model") or config.DEFAULT_MODEL

    header_left, header_right = st.columns([0.72, 0.28])
    with header_left:
        st.title("Coach")
        theme = day_info["theme"] if day_info else "Today's plan"
        st.caption(f"Day {day} · {theme} · {model}")
    with header_right:
        if messages:
            st.button(
                "New conversation",
                on_click=_new_conversation,
                width="stretch",
            )

    if not messages:
        st.markdown("#### Start here")
        suggestions = [
            "Explain INNER vs LEFT JOIN with a business example.",
            "Quiz me on SQL — one question at a time.",
            f"Review my plan for Day {day} and tell me what to focus on.",
            "Help me write the business context for my e-commerce project.",
        ]
        columns = st.columns(2)
        for index, suggestion in enumerate(suggestions):
            if columns[index % 2].button(
                suggestion,
                key=f"coach_suggestion_{index}",
                width="stretch",
            ):
                st.session_state.pending_prompt = suggestion
                st.rerun()
        st.write("")

    for message in messages:
        role = "user" if message["role"] == "user" else "assistant"
        avatar = "🧑‍💻" if role == "user" else "📊"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message["content"])

    pending = st.session_state.pop("pending_prompt", None)
    typed = st.chat_input(
        "Ask about SQL, pandas, your project, or interview prep…",
        key="coach_input",
    )
    user_text = typed or pending

    if not user_text:
        return

    db.add_message("user", user_text)
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_text)

    history = db.get_messages(limit=20)
    payload = [{"role": m["role"], "content": m["content"]} for m in history]
    system_prompt = prompts.coach_system_prompt(
        profile=profile,
        skills=skills,
        day=day,
        day_info=day_info,
        tasks=tasks,
        overall=overall,
        sprint_finished=raw_day > roadmap.SPRINT_DAYS,
    )

    reply: str | None = None
    with st.chat_message("assistant", avatar="📊"):
        try:
            reply = st.write_stream(
                llm.stream_chat(payload, system_prompt, model=model)
            )
        except llm.LLMError as exc:
            st.error(str(exc))

    if reply:
        db.add_message("assistant", reply)
