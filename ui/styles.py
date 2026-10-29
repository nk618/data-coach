"""Shared styling helpers for a clean, desktop-app feel."""

from __future__ import annotations

import html

import streamlit as st

CSS = """
<style>
#MainMenu, footer, header {visibility: hidden; height: 0;}
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"],
[data-testid="stHeaderActionElements"] {display: none !important;}
.block-container {padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1120px;}
[data-testid="stSidebar"] {background: #FFFFFF; border-right: 1px solid #E2E8F0;}
[data-testid="stSidebar"] > div:first-child {padding-top: 1.2rem;}
h1 {font-size: 2.05rem !important; letter-spacing: -0.03em;}
h2 {letter-spacing: -0.02em;}
h3 {letter-spacing: -0.01em;}
.stButton > button {border-radius: 10px; font-weight: 600;}
[data-testid="stChatMessage"] {padding: 0.35rem 0.15rem;}
[data-testid="stChatInput"] textarea {font-size: 0.95rem;}

.hero {
    background: linear-gradient(135deg, #EFF6FF 0%, #F8FAFC 62%, #F0FDFA 100%);
    border: 1px solid #DBEAFE;
    border-radius: 18px;
    padding: 24px 28px;
    margin-bottom: 18px;
}
.hero .eyebrow {
    font-size: 0.74rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #2563EB;
    margin-bottom: 6px;
}
.hero h1 {
    margin: 0 0 6px 0;
    font-size: 1.9rem !important;
    color: #0F172A;
}
.hero p {margin: 0; color: #475569; font-size: 0.98rem; line-height: 1.5;}
.hero .meta {margin-top: 10px; font-size: 0.82rem; color: #64748B;}

.badge {
    display: inline-block;
    background: #E0E7FF;
    color: #3730A3;
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 0.73rem;
    font-weight: 700;
    margin: 0 6px 6px 0;
}
.badge.green {background: #DCFCE7; color: #166534;}
.badge.amber {background: #FEF3C7; color: #92400E;}
.badge.red {background: #FEE2E2; color: #991B1B;}
.badge.gray {background: #F1F5F9; color: #475569;}

.stat {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 15px 17px;
    height: 100%;
}
.stat .label {
    color: #64748B;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.stat .value {
    color: #0F172A;
    font-size: 1.55rem;
    font-weight: 800;
    line-height: 1.25;
    margin-top: 2px;
}
.stat .note {color: #94A3B8; font-size: 0.76rem; margin-top: 2px;}

.muted {color: #64748B; font-size: 0.88rem;}
.tiny {font-size: 0.78rem; color: #64748B;}
.pill {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 0.71rem;
    font-weight: 800;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.pill.learn {background: #DBEAFE; color: #1D4ED8;}
.pill.build {background: #DCFCE7; color: #15803D;}
.pill.prove {background: #FEF3C7; color: #B45309;}
.pill.log {background: #F1F5F9; color: #475569;}

.skill-row {margin-bottom: 2px;}
.skill-track {background: #E2E8F0; border-radius: 999px; height: 8px; overflow: hidden; margin: 4px 0 10px 0;}
.skill-fill {height: 8px; border-radius: 999px; background: linear-gradient(90deg, #60A5FA, #2563EB);}

.divider {height: 1px; background: #E2E8F0; margin: 18px 0;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(eyebrow: str, title: str, subtitle: str = "", meta: str = "") -> str:
    parts = [
        '<div class="hero">',
        f'<div class="eyebrow">{html.escape(eyebrow)}</div>',
        f"<h1>{html.escape(title)}</h1>",
    ]
    if subtitle:
        parts.append(f"<p>{html.escape(subtitle)}</p>")
    if meta:
        parts.append(f'<div class="meta">{html.escape(meta)}</div>')
    parts.append("</div>")
    return "".join(parts)


def stat_card(label: str, value: str, note: str = "") -> str:
    note_html = f'<div class="note">{html.escape(note)}</div>' if note else ""
    return (
        '<div class="stat">'
        f'<div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(value)}</div>'
        f"{note_html}"
        "</div>"
    )


def badge(text: str, variant: str = "") -> str:
    cls = f"badge {variant}".strip()
    return f'<span class="{cls}">{html.escape(text)}</span>'


def skill_bar(level: float) -> str:
    pct = max(0.0, min(1.0, float(level) / 5.0)) * 100
    return (
        '<div class="skill-track">'
        f'<div class="skill-fill" style="width:{pct:.1f}%"></div>'
        "</div>"
    )
