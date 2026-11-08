"""Credential lookup and a minimum security baseline for stale installations."""

import os
import re


def supported_streamlit(version: str) -> bool:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\+[A-Za-z0-9.-]+)?", version)
    return bool(match and tuple(map(int, match.groups())) >= (1, 54, 0))


def get_api_key(secrets) -> str:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return key
    try:
        key = secrets.get("GROQ_API_KEY", "")
    except FileNotFoundError:
        # StreamlitSecretNotFoundError subclasses FileNotFoundError.
        return ""
    return key.strip() if isinstance(key, str) else ""
