"""Job tracker: log applications, follow-ups, and interview outcomes."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from core import db
from ui.styles import badge, hero, stat_card

STATUSES = db.APPLICATION_STATUSES


def _status_badge(status: str) -> str:
    variant = {
        "Applied": "",
        "Screening": "amber",
        "Interview": "amber",
        "Offer": "green",
        "Rejected": "red",
        "Withdrawn": "gray",
    }.get(status, "gray")
    return badge(status, variant)


def render() -> None:
    st.markdown(
        hero(
            "Job tracker",
            "Log applications, follow-ups, and outcomes",
            "Every application, one place. The coach uses this to tailor your prep and "
            "spot which channels are working.",
        ),
        unsafe_allow_html=True,
    )

    stats = db.get_application_stats()
    cols = st.columns(4)
    cols[0].markdown(stat_card("Applications", str(stats["total"]), "logged"), unsafe_allow_html=True)
    cols[1].markdown(stat_card("This week", str(stats["recent"]), "new applications"), unsafe_allow_html=True)
    cols[2].markdown(stat_card("Follow-ups due", str(stats["follow_ups_due"]), "overdue or today"), unsafe_allow_html=True)
    offers = stats["by_status"].get("Offer", 0)
    cols[3].markdown(stat_card("Offers", str(offers), "received"), unsafe_allow_html=True)

    if stats["by_status"]:
        st.write("")
        st.markdown("#### Pipeline")
        pipeline_cols = st.columns(len(STATUSES))
        for index, status in enumerate(STATUSES):
            count = stats["by_status"].get(status, 0)
            pipeline_cols[index].markdown(
                f"<div style='text-align:center'>{_status_badge(status)}<br>"
                f"<span style='font-size:1.4rem;font-weight:800'>{count}</span></div>",
                unsafe_allow_html=True,
            )

    st.write("")
    left, right = st.columns([0.42, 0.58], gap="large")

    with left:
        with st.container(border=True):
            st.markdown("#### Add application")
            with st.form("add_application"):
                company = st.text_input("Company", placeholder="e.g. Acme Corp")
                role = st.text_input("Role", placeholder="e.g. Data Analyst")
                date_applied = st.date_input("Date applied", value=date.today())
                status = st.selectbox("Status", STATUSES, index=0)
                source = st.text_input(
                    "Source",
                    placeholder="LinkedIn, referral, company site…",
                )
                follow_up = st.date_input(
                    "Follow-up date (optional)",
                    value=None,
                    help="Leave blank if none.",
                )
                notes = st.text_area("Notes", height=80, placeholder="Recruiter name, salary range, links…")
                submitted = st.form_submit_button("Add application", type="primary", width="stretch")
            if submitted:
                if not company.strip() or not role.strip():
                    st.error("Company and role are required.")
                else:
                    db.add_application(
                        company=company,
                        role=role,
                        date_applied=date_applied.isoformat(),
                        status=status,
                        source=source,
                        notes=notes,
                        follow_up_date=follow_up.isoformat() if follow_up else None,
                    )
                    st.success(f"Added {role} at {company}.")
                    st.rerun()

    with right:
        st.markdown("#### Applications")
        filter_status = st.selectbox(
            "Filter by status",
            ["All"] + STATUSES,
            key="job_tracker_filter",
        )
        applications = db.get_applications(
            None if filter_status == "All" else filter_status
        )
        if not applications:
            st.info("No applications logged yet. Add one on the left.")
        else:
            for app in applications:
                with st.container(border=True):
                    header_col, badge_col = st.columns([0.78, 0.22])
                    header_col.markdown(f"**{app['role']}** — {app['company']}")
                    badge_col.markdown(_status_badge(app["status"]), unsafe_allow_html=True)
                    meta = [
                        f"Applied {app['date_applied']}",
                    ]
                    if app.get("source"):
                        meta.append(f"via {app['source']}")
                    if app.get("follow_up_date"):
                        follow = app["follow_up_date"]
                        overdue = follow <= date.today().isoformat()
                        meta.append(
                            ("⚠️ " if overdue else "📅 ") + f"follow up {follow}"
                        )
                    st.caption(" · ".join(meta))
                    if app.get("notes"):
                        st.markdown(app["notes"])

                    edit_col, delete_col = st.columns(2)
                    if edit_col.button("Edit", key=f"edit_app_{app['id']}", width="stretch"):
                        st.session_state[f"editing_app_{app['id']}"] = True
                        st.rerun()
                    if delete_col.button("Delete", key=f"del_app_{app['id']}", width="stretch"):
                        db.delete_application(app["id"])
                        st.toast("Application deleted.")
                        st.rerun()

                    if st.session_state.get(f"editing_app_{app['id']}"):
                        with st.form(f"edit_form_{app['id']}"):
                            new_company = st.text_input("Company", value=app["company"])
                            new_role = st.text_input("Role", value=app["role"])
                            try:
                                start_value = date.fromisoformat(app["date_applied"])
                            except ValueError:
                                start_value = date.today()
                            new_date = st.date_input("Date applied", value=start_value)
                            new_status = st.selectbox(
                                "Status",
                                STATUSES,
                                index=STATUSES.index(app["status"]) if app["status"] in STATUSES else 0,
                            )
                            new_source = st.text_input("Source", value=app.get("source", ""))
                            try:
                                fu_value = date.fromisoformat(app["follow_up_date"]) if app.get("follow_up_date") else None
                            except ValueError:
                                fu_value = None
                            new_follow = st.date_input(
                                "Follow-up date",
                                value=fu_value,
                                help="Clear by setting to today's date and ignoring.",
                            )
                            new_notes = st.text_area("Notes", value=app.get("notes", ""), height=80)
                            save = st.form_submit_button("Save changes", type="primary", width="stretch")
                            cancel = st.form_submit_button("Cancel", width="stretch")
                        if save:
                            db.update_application(
                                application_id=app["id"],
                                company=new_company,
                                role=new_role,
                                date_applied=new_date.isoformat(),
                                status=new_status,
                                source=new_source,
                                notes=new_notes,
                                follow_up_date=new_follow.isoformat() if new_follow else None,
                            )
                            st.session_state.pop(f"editing_app_{app['id']}", None)
                            st.success("Updated.")
                            st.rerun()
                        if cancel:
                            st.session_state.pop(f"editing_app_{app['id']}", None)
                            st.rerun()

    st.write("")
    st.markdown("#### Follow-up reminders")
    due = [a for a in db.get_applications() if a.get("follow_up_date") and a["follow_up_date"] <= date.today().isoformat()]
    if not due:
        st.success("No follow-ups due today. Keep applying.")
    else:
        for app in due:
            st.warning(
                f"**{app['company']}** — {app['role']} (applied {app['date_applied']}). "
                f"Follow-up was due {app['follow_up_date']}."
            )

    st.write("")
    st.markdown("#### Coach this list")
    if st.button("Ask the coach to review my applications", type="primary", width="stretch"):
        summary = "\n".join(
            f"- {a['company']} | {a['role']} | {a['status']} | applied {a['date_applied']}"
            for a in applications
        ) or "No applications logged yet."
        st.session_state.pending_prompt = (
            "Here is my job application log:\\n" + summary + "\\n\\n"
            "Review it: which channels are working, where I'm losing people, what to change "
            "in my resume or outreach, and what to do next week. Be specific."
        )
        st.session_state.page = "Coach"
        st.rerun()
