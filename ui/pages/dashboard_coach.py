"""Dashboard Coach: turn business questions into KPIs, charts, and DAX, plus screenshot critique."""

from __future__ import annotations

import base64

import streamlit as st

from core import config, db, llm
from ui.styles import hero


SYSTEM_PROMPT = """You are a senior BI lead mentoring a junior analyst on dashboard design and DAX.
You coach on Power BI and Tableau. Be direct, concrete, and opinionated.

When the user describes a business question or dashboard:
1. Ask what decision the dashboard must support and who the audience is.
2. Recommend 3-5 KPIs with exact definitions and denominators.
3. Recommend the chart type for each metric and why (line for trend, bar for ranking, KPI card for headline, scatter for relationship, table for detail).
4. Recommend layout: top row KPIs, middle row trend, bottom row drivers. One message per page.
5. Flag chart choices that mislead: pie charts with many slices, dual axes, truncated y-axes, 3D, rainbow colors.
6. Give DAX or calculated-field formulas when asked, with explanations of filter context.
7. When given a screenshot, critique it on: chart choice, hierarchy, clutter, color, insight titles, and whether every number reconciles to SQL. Score 1-5 each.

Rules:
- Never invent data or numbers. Ask for them.
- Prefer simple, readable DAX. Avoid nested CALCULATE unless needed.
- Always check the denominator and the grain.
- Keep replies under 300 words unless asked for depth.
- End with one clear next action.
"""


def _image_to_base64(uploaded) -> str | None:
    if uploaded is None:
        return None
    try:
        return base64.b64encode(uploaded.read()).decode("ascii")
    except Exception:
        return None


def render() -> None:
    st.markdown(
        hero(
            "Dashboard Coach",
            "Design KPIs, charts, and DAX — plus screenshot critique",
            "Turn a business question into the right metrics and layout, get DAX help, "
            "and paste a screenshot for a scored review.",
        ),
        unsafe_allow_html=True,
    )

    api_key = config.get_api_key()
    if not api_key:
        st.warning("The Dashboard Coach needs a Gemini API key. Add one in Settings.")
        if st.button("Go to Settings", type="primary"):
            st.session_state.page = "Settings"
            st.rerun()
        return

    model = db.get_setting("model") or config.DEFAULT_MODEL

    if "dashboard_messages" not in st.session_state:
        st.session_state.dashboard_messages = []

    messages = st.session_state.dashboard_messages

    if not messages:
        st.markdown("#### Start here")
        starters = [
            "I'm building an e-commerce dashboard. What KPIs and charts should page 1 have?",
            "Write DAX for: revenue, average order value, on-time delivery %, and month-over-month growth.",
            "Review my dashboard plan: I want to show revenue by category, region, and time.",
            "What's the difference between a measure and a calculated column, and when do I use each?",
        ]
        cols = st.columns(2)
        for index, starter in enumerate(starters):
            if cols[index % 2].button(starter, key=f"dash_starter_{index}", width="stretch"):
                st.session_state.dashboard_pending = starter
                st.rerun()
        st.write("")

    for msg in messages:
        role = "user" if msg["role"] == "user" else "assistant"
        avatar = "🧑‍💻" if role == "user" else "📊"
        with st.chat_message(role, avatar=avatar):
            if msg.get("image"):
                st.image(msg["image"], width=400)
            st.markdown(msg["content"])

    # Screenshot upload
    with st.expander("Upload a dashboard screenshot for critique", expanded=False):
        shot = st.file_uploader(
            "Screenshot (PNG/JPG)",
            type=["png", "jpg", "jpeg"],
            key="dashboard_shot",
        )
        if shot is not None and st.button("Critique this screenshot", type="primary"):
            image_b64 = _image_to_base64(shot)
            prompt = (
                "Critique this dashboard screenshot. Score 1-5 on: chart choice, hierarchy, "
                "clutter, color, insight titles, and whether the numbers look reconciled. "
                "List the top three fixes in priority order, then supporting details."
            )
            st.session_state.dashboard_pending = (prompt, image_b64, shot)
            st.rerun()

    pending = st.session_state.pop("dashboard_pending", None)
    typed = st.chat_input("Ask about KPIs, charts, DAX, or paste a plan…", key="dashboard_input")

    user_text = None
    user_image = None
    if pending is not None:
        if isinstance(pending, tuple):
            user_text, user_image, _ = pending
        else:
            user_text = pending
    elif typed:
        user_text = typed

    if not user_text:
        return

    db.add_message("user", user_text, thread="dashboard")
    with st.chat_message("user", avatar="🧑‍💻"):
        if user_image:
            st.image(user_image, width=400) if False else None
        st.markdown(user_text)

    messages.append({"role": "user", "content": user_text, "image": user_image})
    st.session_state.dashboard_messages = messages

    history = [{"role": m["role"], "content": m["content"]} for m in messages]
    payload = history

    # If an image was provided, send it to Gemini as a multimodal turn.
    reply = None
    with st.chat_message("assistant", avatar="📊"):
        try:
            if user_image:
                # Build a one-off multimodal request.
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=config.get_api_key())
                model = model
                contents = []
                for m in messages:
                    role = "user" if m["role"] == "user" else "model"
                    parts = [types.Part(text=m["content"])]
                    if m.get("image") and m["role"] == "user":
                        parts.append(
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type="image/png",
                                    data=base64.b64decode(m["image"]),
                                )
                            )
                        )
                    contents.append(types.Content(role=role, parts=parts))
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.5,
                        max_output_tokens=1500,
                    ),
                )
                reply = (getattr(response, "text", None) or "").strip()
                if reply:
                    st.markdown(reply)
            else:
                reply = st.write_stream(
                    llm.stream_chat(payload, SYSTEM_PROMPT, model=model)
                )
        except Exception as exc:
            st.error(f"AI request failed: {exc}")

    if reply:
        messages.append({"role": "assistant", "content": reply})
        st.session_state.dashboard_messages = messages
        db.add_message("assistant", reply, thread="dashboard")

    if st.button("Clear conversation", width="stretch"):
        st.session_state.dashboard_messages = []
        db.clear_messages(thread="dashboard")
        st.rerun()
