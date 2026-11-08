"""Streamlit entry point. Conversation state belongs only to the current session."""

import json
import logging

import streamlit as st
from groq import AuthenticationError, Groq, NotFoundError

from chatbot.conversations import ChatSession
from chatbot.service import (
    InvalidPrompt, MAX_INPUT_CHARS, RateLimitExceeded, RequestLimiter, complete_turn,
)
from chatbot.settings import get_api_key, supported_streamlit
from chatbot.ui import (
    CHARACTER_DETAILS, PROJECT_ROOT, load_css, render_brand,
    render_learning_note, render_messages, render_thread_header, render_welcome,
)
from personalities import get_personality, get_personality_options

st.set_page_config(
    page_title="Artemis · Vietnamese History",
    page_icon=str(PROJECT_ROOT / "assets" / "artemis-logo.png"),
    layout="wide", initial_sidebar_state="auto",
)

if not supported_streamlit(st.__version__):
    st.error("Please update this app's dependencies before running it.")
    st.code("python -m pip install -r requirements.txt")
    st.stop()

load_css()
try:
    api_key = get_api_key(st.secrets)
except Exception:
    st.error("Unable to read the app's secrets. Check the secrets configuration.")
    st.stop()


@st.cache_resource
def request_limiter() -> RequestLimiter:
    # This object holds budgets only, never conversations or credentials.
    return RequestLimiter()


@st.cache_data
def load_questions() -> dict[str, list[str]]:
    return json.loads((PROJECT_ROOT / "data.json").read_text(encoding="utf-8"))


# Discard state from the previous shared-file implementation on a hot reload.
for legacy_key in ("messages", "current_conversation_id", "current_personality_key"):
    st.session_state.pop(legacy_key, None)
if "chat_session_v2" not in st.session_state:
    st.session_state.chat_session_v2 = ChatSession()
session = st.session_state.chat_session_v2

with st.sidebar:
    render_brand()
    if st.button("New conversation", key="new_conversation", icon=":material/add:",
                 use_container_width=True, type="primary"):
        session.new_conversation()
        st.rerun()
    st.markdown('<div class="sidebar-label">CHOOSE YOUR COMPANION</div>', unsafe_allow_html=True)
    for key, name in get_personality_options():
        details = CHARACTER_DETAILS[key]
        with st.container(key=f"companion_{key}"):
            if st.button(f"{name}\n{details['era']}", key=f"character_{key}",
                         icon=details["icon"], use_container_width=True,
                         type="primary" if key == session.personality else "secondary"):
                if key != session.personality:
                    session.new_conversation(key)
                    st.rerun()

    personality = get_personality(session.personality)
    st.markdown('<div class="sidebar-label history-label">YOUR CONVERSATIONS</div>', unsafe_allow_html=True)
    if not session.conversations:
        st.markdown(
            '<div class="empty-history"><span aria-hidden="true">↳</span>'
            '<div>Your story starts here.<br><small>Conversations will appear as you explore.</small></div></div>',
            unsafe_allow_html=True,
        )
    for conversation in reversed(list(session.conversations.values())):
        title_col, delete_col = st.columns([5, 1], gap="small")
        with title_col:
            if st.button(conversation.title, key=f"load_{conversation.id}",
                         use_container_width=True, icon=":material/chat_bubble_outline:",
                         help=conversation.title,
                         type="primary" if conversation.id == session.current_id else "secondary"):
                session.select(conversation.id)
                st.rerun()
        with delete_col:
            if st.button("Delete", key=f"delete_{conversation.id}",
                         icon=":material/delete_outline:", help="Delete this chat",
                         type="tertiary"):
                session.delete(conversation.id)
                st.rerun()
    if session.conversations:
        with st.expander("Manage conversations", icon=":material/settings:"):
            st.caption("Up to 10 chats and 10 recent turns per chat. Older content is removed automatically.")
            if st.button("🗑️ Delete All History", use_container_width=True):
                session.clear()
                st.rerun()
    st.markdown(
        '<div class="sidebar-footer"><span class="footer-mark" aria-hidden="true">✧</span>'
        '<p>A new way to explore an old world.</p><small>Chats stay in this browser session.</small></div>',
        unsafe_allow_html=True,
    )

# A new draft gets the discovery screen even when other chats exist in history.
has_messages = bool(session.current and session.current.messages)
suggested_prompt = None
typed_prompt = None
if has_messages:
    with st.container(key="active_chat"):
        with st.container(key="thread_header"):
            render_thread_header(personality, session.personality)
        render_messages(session.current.messages, personality.name)
    if api_key:
        # Root-level chat input stays pinned while the conversation scrolls.
        typed_prompt = st.chat_input(
            "Ask a follow-up question…",
            max_chars=MAX_INPUT_CHARS, key="conversation_prompt",
        )
    render_learning_note()
else:
    with st.container(key="empty_chat"):
        render_welcome(personality, session.personality)
        with st.container(key="welcome_composer"):
            if api_key:
                # Nesting the input makes it part of the welcome screen.
                typed_prompt = st.chat_input(
                    "Ask your first question…",
                    max_chars=MAX_INPUT_CHARS, key="welcome_prompt",
                )
        with st.container(key="suggestions"):
            st.markdown(
                '<div class="suggestion-heading"><span>A LITTLE INSPIRATION</span>'
                '<span>Choose a question to begin</span></div>', unsafe_allow_html=True,
            )
            for index, (column, question) in enumerate(zip(
                st.columns(3), load_questions().get(session.personality, [])[:3],
            )):
                with column:
                    topic = CHARACTER_DETAILS[session.personality]["topics"][index]
                    if st.button(f"**{index + 1:02d}  ·  {topic}**\n\n{question}",
                                 key=f"suggest_{index}", use_container_width=True, disabled=not api_key):
                        suggested_prompt = question
        render_learning_note()

if not api_key:
    st.info("Add GROQ_API_KEY to your environment or .streamlit/secrets.toml, then restart the app.")
    st.stop()

prompt = suggested_prompt if suggested_prompt is not None else typed_prompt
if prompt is not None:
    with st.spinner(f"⏳ {personality.name} is thinking..."):
        try:
            with Groq(api_key=api_key, timeout=30.0, max_retries=0) as client:
                complete_turn(client, request_limiter(), session, personality.system_prompt, prompt)
        except (InvalidPrompt, RateLimitExceeded) as error:
            st.warning(str(error))
        except AuthenticationError:
            logging.getLogger(__name__).warning("Groq authentication failed; update GROQ_API_KEY.")
            st.error(
                "Groq rejected the chatbot's API key. The app administrator needs to "
                "update GROQ_API_KEY in the environment or Streamlit secrets, then restart the app."
            )
        except NotFoundError:
            logging.getLogger(__name__).warning("Groq model or endpoint not found.")
            st.error(
                "The chatbot's AI model is unavailable. The app administrator needs to "
                "update the model configuration or check Groq access."
            )
        except Exception as error:
            # Do not render SDK exceptions, request bodies, or credentials.
            logging.getLogger(__name__).warning("Chat request failed (%s)", type(error).__name__)
            st.error("Unable to get a response right now. Please try again later.")
        else:
            st.rerun()
