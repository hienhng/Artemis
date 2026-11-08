"""Trusted presentation assets; chat content is always rendered as plain text."""

import base64
from html import escape
from functools import lru_cache
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Display metadata stays separate from the character's conversation instructions.
CHARACTER_DETAILS = {
    "ly_thuong_kiet": {
        "initials": "LK", "era": "Lý Dynasty", "years": "1019–1105",
        "role": "General, strategist & poet", "icon": ":material/account_balance:",
        "topics": ("The art of strategy", "Words of independence", "Poetry & patriotism"),
    },
    "ho_chi_minh": {
        "initials": "HM", "era": "Modern Vietnam", "years": "1890–1969",
        "role": "President & revolutionary", "icon": ":material/star:",
        "topics": ("A revolutionary path", "A journey abroad", "The story of a name"),
    },
    "tran_hung_dao": {
        "initials": "TH", "era": "Trần Dynasty", "years": "1228–1300",
        "role": "General & military thinker", "icon": ":material/shield:",
        "topics": ("Against the odds", "The Bạch Đằng River", "The element of surprise"),
    },
    "general": {
        "initials": "HS", "era": "Through the ages", "years": "All eras",
        "role": "Your guide to Vietnamese history", "icon": ":material/menu_book:",
        "topics": ("The Lam Sơn uprising", "A defining victory", "Resistance & change"),
    },
}


def _background_image() -> str:
    # Read on each rerun so replacing the image does not require a server restart.
    background = (PROJECT_ROOT / "assets" / "background.png").read_bytes()
    return base64.b64encode(background).decode("ascii")


@lru_cache(maxsize=2)
def _font_data(filename: str) -> str:
    font = (PROJECT_ROOT / "assets" / filename).read_bytes()
    return base64.b64encode(font).decode("ascii")


def stylesheet() -> str:
    # Re-read the small stylesheet so local design edits appear on a rerun.
    css = (PROJECT_ROOT / "style.css").read_text(encoding="utf-8")
    return css.replace(
        "__BACKGROUND_IMAGE__", f"data:image/png;base64,{_background_image()}",
    ).replace(
        "__PRATA_FONT__", f"data:font/ttf;base64,{_font_data('Prata-Regular.ttf')}",
    ).replace(
        "__OLDENBURG_FONT__", f"data:font/ttf;base64,{_font_data('Oldenburg-Regular.ttf')}",
    )


def load_css() -> None:
    st.markdown(f"<style>{stylesheet()}</style>", unsafe_allow_html=True)


def render_brand() -> None:
    logo = base64.b64encode(
        (PROJECT_ROOT / "assets" / "artemis-logo.svg").read_bytes(),
    ).decode("ascii")
    st.markdown(
        '<div class="brand">'
        f'<img class="brand-seal" src="data:image/svg+xml;base64,{logo}" '
        'width="44" height="44" alt="" aria-hidden="true">'
        '<div class="brand-name">Artemis<span>.</span></div></div>',
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        '<div class="page-topline"><span>THE VIETNAMESE HISTORY COMPANION</span>'
        '<span class="topline-note"></span></div>'
        '<section class="history-hero" aria-label="Explore Vietnamese history">'
        '<div class="hero-content"><div class="hero-eyebrow"></div>'
        '<h1>Every story starts<br><em>with a question.</em></h1>'
        '<p>Explore Vietnam’s past with the people who shaped it.<br>'
        'Choose a companion. Follow your curiosity.</p>'
        '<div class="hero-bottom"><span class="hero-rule"></span></div>'
        '</div><span class="hero-caption"></span></section>',
        unsafe_allow_html=True,
    )


def render_welcome(personality, key: str) -> None:
    details = CHARACTER_DETAILS[key]
    st.markdown(
        '<section class="welcome-intro" aria-label="Start a conversation">'
        '<div class="section-eyebrow">A CONVERSATION ACROSS TIME</div>'
        f'<h1>What would you ask<br><em>{escape(personality.name)}?</em></h1>'
        f'<div class="welcome-era">{details["role"]}<br>'
        f'<span>{details["era"]} &nbsp;·&nbsp; {details["years"]}</span></div>'
        f'<p class="welcome-greeting">“{escape(personality.greeting)}”</p>'
        '</section>',
        unsafe_allow_html=True,
    )


def render_thread_header(personality, key: str) -> None:
    details = CHARACTER_DETAILS[key]
    st.markdown(
        '<div class="thread-heading"><div class="character-identity">'
        '<div class="thread-identity"><div class="section-eyebrow">IN CONVERSATION WITH</div>'
        f'<h1>{escape(personality.name)}</h1>'
        f'<p>{details["era"]} <span>·</span> {details["years"]}</p></div></div>'
        '<span class="thread-badge">AI history companion</span></div>',
        unsafe_allow_html=True,
    )


def render_learning_note() -> None:
    st.markdown(
        '<div class="learning-note">AI brings these historical perspectives to life. '
        'Verify important details with historical sources.</div>', unsafe_allow_html=True,
    )


def render_messages(messages: list[dict[str, str]], name: str = "History companion") -> None:
    for message in messages:
        is_user = message["role"] == "user"
        with st.chat_message(message["role"], avatar=":material/person:" if is_user else ":material/history_edu:"):
            st.caption("YOU" if is_user else name.upper())
            # Plain text prevents HTML and remote Markdown images from either
            # user input or model output becoming active browser content.
            st.text(message["content"])
