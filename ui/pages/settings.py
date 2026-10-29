"""Settings: API key, model, profile, data folder, and reset."""

from __future__ import annotations

import os
from datetime import date, datetime

import streamlit as st

from core import config, db, llm

ROLES = [
    "Data Analyst",
    "Business Analyst",
    "BI Analyst",
    "Product Analyst",
    "Analytics Engineer",
]


def _save_key(new_key: str) -> None:
    try:
        config.save_api_key(new_key.strip())
        st.toast("API key saved to Windows Credential Locker.")
    except Exception as exc:  # noqa: BLE001
        st.error(
            "Could not save the key to Windows Credential Locker. "
            f"Use a .env file instead. Details: {exc}"
        )


def render() -> None:
    profile = db.get_profile()
    if not profile:
        st.error("No profile found. Please reload and complete onboarding.")
        return

    st.title("Settings")
    st.caption("Connection, profile, and local data. Nothing here is shared with anyone.")

    # ------------------------------------------------------------------
    # AI connection
    # ------------------------------------------------------------------
    st.markdown("### AI connection")
    key = config.get_api_key()
    current_model = db.get_setting("model") or config.DEFAULT_MODEL

    with st.container(border=True):
        if key:
            st.success(
                f"Gemini key saved · {config.mask_key(key)} · stored in Windows Credential Locker"
            )
        else:
            st.warning("No Gemini API key saved yet. The coach cannot reply without one.")

        new_key = st.text_input(
            "Add or replace the API key",
            type="password",
            placeholder="AIza…",
            key="settings_key_input",
            help="Create a free key at aistudio.google.com/apikey",
        )
        col_save, col_remove, col_test = st.columns(3)
        if col_save.button(
            "Save key",
            type="primary",
            disabled=not new_key.strip(),
            width="stretch",
        ):
            _save_key(new_key)
            st.rerun()

        if col_remove.button(
            "Remove key",
            disabled=not key,
            width="stretch",
        ):
            config.delete_api_key()
            st.toast("API key removed.")
            st.rerun()

        if col_test.button(
            "Test connection",
            disabled=not key,
            width="stretch",
        ):
            with st.spinner("Testing the saved key and model…"):
                try:
                    reply = llm.test_connection(key, current_model)
                    db.set_setting("last_test", datetime.now().isoformat(timespec="seconds"))
                    st.success(f"Connected. The model replied: {reply[:80]}")
                except llm.LLMError as exc:
                    st.error(str(exc))

        st.markdown("---")
        st.markdown("#### Model")
        choices = list(dict.fromkeys(config.MODEL_CHOICES + [current_model]))
        labels = choices + ["Custom…"]
        default_index = labels.index(current_model) if current_model in labels else 0
        selection = st.selectbox(
            "Model",
            labels,
            index=default_index,
            help="Flash models are faster and cheaper. Pro is stronger for evaluation-heavy work.",
        )
        custom = st.text_input(
            "Custom model name",
            placeholder="e.g., gemini-2.5-flash",
            disabled=(selection != "Custom…"),
        )
        selected_model = custom.strip() if selection == "Custom…" else selection
        if st.button("Save model", disabled=not selected_model):
            db.set_setting("model", selected_model)
            st.toast(f"Model set to {selected_model}.")
            st.rerun()

        last_test = db.get_setting("last_test")
        if last_test:
            st.caption(f"Last successful connection test: {last_test.replace('T', ' ')}")

        st.caption(
            "The free tier has daily request limits. If you hit one, the coach will tell you "
            "and you can retry shortly or switch to a lighter model."
        )

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------
    st.markdown("### Your profile")
    with st.container(border=True):
        with st.form("settings_profile"):
            name = st.text_input("Name", value=profile["name"])
            role = st.selectbox(
                "Target role",
                ROLES,
                index=ROLES.index(profile["target_role"])
                if profile["target_role"] in ROLES
                else 0,
            )
            location = st.text_input("Location", value=profile.get("location", ""))
            hours = st.slider(
                "Focused hours per day",
                min_value=1.0,
                max_value=8.0,
                value=float(profile.get("hours_per_day", 3.5)),
                step=0.5,
            )
            try:
                start_value = date.fromisoformat(str(profile["start_date"]))
            except ValueError:
                start_value = date.today()
            start = st.date_input("Sprint start date", value=start_value)
            submitted = st.form_submit_button("Save profile", type="primary")

        if submitted:
            if not name.strip():
                st.error("Name cannot be empty.")
            else:
                db.update_profile(
                    {
                        "name": name.strip(),
                        "target_role": role,
                        "location": location.strip(),
                        "hours_per_day": float(hours),
                        "start_date": start.isoformat(),
                    }
                )
                st.toast("Profile updated. The day counter follows the start date.")
                st.rerun()

        st.caption(
            "Changing the start date shifts your current day. It does not erase completed tasks."
        )

    # ------------------------------------------------------------------
    # Data and privacy
    # ------------------------------------------------------------------
    st.markdown("### Data and privacy")
    with st.container(border=True):
        st.markdown(
            "Your profile, roadmap, progress, and chat history live in a local SQLite database. "
            "Only chat text and your questions are sent to Google Gemini. Datasets and files stay "
            "on this PC."
        )
        st.code(str(config.DATA_DIR), language=None)
        col_open, col_reset = st.columns(2)
        if col_open.button("Open data folder", width="stretch"):
            try:
                os.startfile(str(config.DATA_DIR))  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not open the folder: {exc}")

        with col_reset:
            st.caption("Reset is destructive and cannot be undone.")
        confirm = st.text_input(
            "Type RESET to wipe profile, roadmap progress, and chat history",
            key="settings_reset_confirm",
        )
        if st.button(
            "Reset all data",
            disabled=confirm.strip().upper() != "RESET",
            width="stretch",
        ):
            db.reset_all()
            for key_name in list(st.session_state.keys()):
                if key_name.startswith(("ob_", "diag_", "done_", "today_")) or key_name in {
                    "page",
                    "view_day",
                    "pending_prompt",
                    "just_onboarded",
                    "onboarding_summary",
                }:
                    del st.session_state[key_name]
            st.rerun()

    st.markdown("### About")
    st.caption(
        f"Data Coach v{config.VERSION} · local-first · built for a 21-day data analyst sprint. "
        "AI feedback is a coach, not an oracle — verify numbers against source data."
    )
