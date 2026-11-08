"""Input validation, bounded model context, and process-wide API budgets."""

from collections import deque
from threading import Lock
from time import monotonic

from chatbot.conversations import ChatSession, MAX_HISTORY_MESSAGES

MAX_INPUT_CHARS = 2_000
MAX_REPLY_CHARS = 4_000
MAX_CONTEXT_CHARS = 16_000
MODEL_ID = "openai/gpt-oss-20b"


class InvalidPrompt(ValueError):
    """A question or its instructions exceeded the supported input bounds."""


class RateLimitExceeded(ValueError):
    """A request exceeded a session or shared process budget."""


class RequestLimiter:
    """Shared by sessions in one process; requests across workers need a gateway.

    The event list is bounded by the global hourly limit, including failed calls.
    New conversations and cleared history never reset these budgets.
    """

    def __init__(self, clock=monotonic):
        self._clock = clock
        self._events: deque[tuple[float, str]] = deque()
        self._lock = Lock()

    def acquire(self, session_id: str) -> None:
        with self._lock:
            now = self._clock()
            while self._events and self._events[0][0] <= now - 3_600:
                self._events.popleft()
            recent = [event for event in self._events if event[0] > now - 60]
            own = [event for event in self._events if event[1] == session_id]
            own_recent = sum(event[1] == session_id for event in recent)
            if (len(self._events) >= 200 or len(recent) >= 20
                    or len(own) >= 50 or own_recent >= 5):
                raise RateLimitExceeded("Request limit reached. Please try again later.")
            self._events.append((now, session_id))


def validate_prompt(prompt: str) -> str:
    # Check the original length too, so padding cannot bypass the server limit.
    if not isinstance(prompt, str) or len(prompt) > MAX_INPUT_CHARS:
        raise InvalidPrompt(f"Questions must be at most {MAX_INPUT_CHARS:,} characters.")
    prompt = prompt.strip()
    if not prompt:
        raise InvalidPrompt("Enter a question first.")
    return prompt


def build_context(system_prompt: str, history: list[dict[str, str]],
                  prompt: str) -> list[dict[str, str]]:
    prompt = validate_prompt(prompt)
    size = len(system_prompt) + len(prompt)
    if size > MAX_CONTEXT_CHARS:
        raise InvalidPrompt("The character instructions are too long.")
    selected: list[dict[str, str]] = []
    # Include complete turns only, preserving order and the newest question.
    for end in range(len(history), 1, -2):
        turn = history[end - 2:end]
        turn_size = sum(len(message["content"]) for message in turn)
        if size + turn_size > MAX_CONTEXT_CHARS or len(selected) + 2 > MAX_HISTORY_MESSAGES:
            break
        selected = [message.copy() for message in turn] + selected
        size += turn_size
    return [
        {"role": "system", "content": system_prompt},
        *selected,
        {"role": "user", "content": prompt},
    ]


def complete_turn(client, limiter: RequestLimiter, session: ChatSession,
                  system_prompt: str, prompt: str) -> None:
    prompt = validate_prompt(prompt)
    history = session.current.messages if session.current else []
    messages = build_context(system_prompt, history, prompt)
    limiter.acquire(session.id)
    response = client.chat.completions.create(
        model=MODEL_ID, messages=messages,
        temperature=0.7, max_completion_tokens=600,
        reasoning_effort="low", include_reasoning=False,
    )
    reply = response.choices[0].message.content
    if not isinstance(reply, str) or not reply.strip():
        raise RuntimeError("The provider returned an empty response.")
    # Only commit a completed turn; failed requests cannot poison later context.
    session.add_turn(prompt, reply[:MAX_REPLY_CHARS])
