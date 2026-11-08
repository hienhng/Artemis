"""Bounded, in-memory conversations owned by one Streamlit session.

Never cache ChatSession objects globally or load legacy shared history here.
"""

from dataclasses import dataclass, field
from uuid import uuid4

MAX_CONVERSATIONS = 10
MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_CHARS = 16_000


def trim_history(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep the most recent complete user/assistant turns within both limits."""
    result = [message.copy() for message in messages]
    size = sum(len(message["content"]) for message in result)
    while result and (len(result) > MAX_HISTORY_MESSAGES or size > MAX_HISTORY_CHARS):
        removed, result = result[:2], result[2:]
        size -= sum(len(message["content"]) for message in removed)
    return result


@dataclass
class Conversation:
    personality: str
    id: str = field(default_factory=lambda: uuid4().hex)
    messages: list[dict[str, str]] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.messages[0]["content"][:50] if self.messages else "New conversation"


@dataclass
class ChatSession:
    id: str = field(default_factory=lambda: uuid4().hex)
    personality: str = "ly_thuong_kiet"
    conversations: dict[str, Conversation] = field(default_factory=dict)
    current_id: str | None = None

    @property
    def current(self) -> Conversation | None:
        return self.conversations.get(self.current_id)

    def new_conversation(self, personality: str | None = None) -> None:
        if personality is not None:
            self.personality = personality
        self.current_id = None

    def select(self, conversation_id: str) -> None:
        # Only IDs present in this session can be selected.
        conversation = self.conversations[conversation_id]
        self.current_id = conversation_id
        self.personality = conversation.personality

    def delete(self, conversation_id: str) -> None:
        self.conversations.pop(conversation_id, None)
        if self.current_id == conversation_id:
            self.current_id = None

    def clear(self) -> None:
        self.conversations.clear()
        self.current_id = None

    def add_turn(self, prompt: str, reply: str) -> None:
        conversation = self.current or Conversation(personality=self.personality)
        conversation.messages = trim_history([
            *conversation.messages,
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": reply},
        ])
        # Updating insertion order makes retention follow most recent activity.
        self.conversations.pop(conversation.id, None)
        self.conversations[conversation.id] = conversation
        self.current_id = conversation.id
        while len(self.conversations) > MAX_CONVERSATIONS:
            self.conversations.pop(next(iter(self.conversations)))
