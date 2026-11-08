"""Regression coverage for session boundaries and API/resource budgets."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import os
import unittest
from unittest.mock import Mock, patch

from chatbot.conversations import (
    ChatSession, MAX_CONVERSATIONS, MAX_HISTORY_CHARS, MAX_HISTORY_MESSAGES,
)
from chatbot.service import (
    InvalidPrompt, MAX_CONTEXT_CHARS, MAX_INPUT_CHARS, MAX_REPLY_CHARS,
    RateLimitExceeded, RequestLimiter, build_context, complete_turn,
)
from chatbot.settings import get_api_key, supported_streamlit


def fake_client(reply="A historical answer"):
    create = Mock(return_value=SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content=reply)),
    ]))
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


class ConversationTests(unittest.TestCase):
    def test_sessions_cannot_load_or_delete_each_others_chats(self):
        alice, bob = ChatSession(), ChatSession()
        alice.add_turn("Private marker", "Answer")
        original_id = alice.current_id
        with self.assertRaises(KeyError):
            bob.select(original_id)
        bob.delete(original_id)
        bob.add_turn("Independent", "Reply")
        bob.clear()
        self.assertEqual(alice.current.messages[0]["content"], "Private marker")
        self.assertNotEqual(alice.id, bob.id)
        self.assertFalse(bob.conversations)

    def test_retention_evicts_least_recently_used_chat(self):
        session = ChatSession()
        for i in range(MAX_CONVERSATIONS):
            session.new_conversation()
            session.add_turn(str(i), "answer")
        oldest, second = list(session.conversations)[:2]
        session.select(oldest)
        session.add_turn("Keep this chat", "answer")
        session.new_conversation()
        session.add_turn("One more chat", "answer")
        self.assertEqual(len(session.conversations), MAX_CONVERSATIONS)
        self.assertIn(oldest, session.conversations)
        self.assertNotIn(second, session.conversations)

    def test_history_limits_preserve_complete_recent_turns(self):
        session = ChatSession()
        for i in range(30):
            session.add_turn(f"{i}:" + "u" * 1990, "a" * 4000)
        history = session.current.messages
        self.assertLessEqual(len(history), MAX_HISTORY_MESSAGES)
        self.assertLessEqual(sum(len(m["content"]) for m in history), MAX_HISTORY_CHARS)
        self.assertEqual([m["role"] for m in history], ["user", "assistant"] * (len(history) // 2))
        self.assertTrue(history[-2]["content"].startswith("29:"))

    def test_context_includes_system_and_latest_question_within_budget(self):
        session = ChatSession()
        for i in range(20):
            session.add_turn("u" * 1900, "a" * 3900)
        context = build_context("Instructions" * 100, session.current.messages, "new question")
        self.assertEqual(context[0]["role"], "system")
        self.assertEqual(context[-1], {"role": "user", "content": "new question"})
        self.assertLessEqual(sum(len(m["content"]) for m in context), MAX_CONTEXT_CHARS)
        self.assertEqual([m["role"] for m in context[1:-1]], ["user", "assistant"] * ((len(context) - 2) // 2))


class RequestTests(unittest.TestCase):
    def test_bad_input_never_calls_provider_or_consumes_budget(self):
        session, client, limiter = ChatSession(), fake_client(), Mock()
        for prompt in ("", "   ", "x" * (MAX_INPUT_CHARS + 1), " " * 2000 + "q"):
            with self.assertRaises(InvalidPrompt):
                complete_turn(client, limiter, session, "system", prompt)
        client.chat.completions.create.assert_not_called()
        limiter.acquire.assert_not_called()
        self.assertFalse(session.conversations)

    def test_success_commits_one_complete_turn_and_caps_reply(self):
        session, client = ChatSession(), fake_client("r" * (MAX_REPLY_CHARS + 100))
        complete_turn(client, RequestLimiter(), session, "system", " question ")
        self.assertEqual(session.current.messages[0]["content"], "question")
        self.assertEqual(len(session.current.messages[1]["content"]), MAX_REPLY_CHARS)
        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["model"], "openai/gpt-oss-20b")
        self.assertEqual(request["max_completion_tokens"], 600)
        self.assertEqual(request["reasoning_effort"], "low")
        self.assertFalse(request["include_reasoning"])

    def test_failed_and_empty_responses_leave_history_unchanged(self):
        for failure in (True, False):
            with self.subTest(provider_failure=failure):
                session, client = ChatSession(), fake_client(None)
                session.add_turn("Previous", "Answer")
                before = session.current.messages.copy()
                if failure:
                    client.chat.completions.create.side_effect = RuntimeError("private provider detail")
                with self.assertRaises(RuntimeError):
                    complete_turn(client, RequestLimiter(), session, "system", "Question")
                self.assertEqual(session.current.messages, before)

    def test_rate_limit_blocks_provider_and_survives_clearing_history(self):
        session, client = ChatSession(), fake_client()
        limiter = RequestLimiter(clock=lambda: 100.0)
        for _ in range(5):
            complete_turn(client, limiter, session, "system", "Question")
        session.clear()
        session.new_conversation("general")
        with self.assertRaises(RateLimitExceeded):
            complete_turn(client, limiter, session, "system", "Question")
        self.assertEqual(client.chat.completions.create.call_count, 5)

    def test_process_budget_limits_concurrent_fresh_sessions(self):
        limiter = RequestLimiter(clock=lambda: 100.0)
        def attempt(index):
            try:
                limiter.acquire(str(index))
                return True
            except RateLimitExceeded:
                return False
        with ThreadPoolExecutor(max_workers=12) as executor:
            self.assertEqual(sum(executor.map(attempt, range(40))), 20)

    def test_hourly_global_budget_and_expiry(self):
        now = [100.0]
        limiter = RequestLimiter(clock=lambda: now[0])
        for batch in range(10):
            for index in range(20):
                limiter.acquire(f"{batch}-{index}")
            now[0] += 61
        with self.assertRaises(RateLimitExceeded):
            limiter.acquire("new-session")
        now[0] = 3700.0
        limiter.acquire("new-session")

    def test_session_hourly_budget_survives_minute_window_expiry(self):
        now = [100.0]
        limiter = RequestLimiter(clock=lambda: now[0])
        for _ in range(10):
            for _ in range(5):
                limiter.acquire("same-session")
            now[0] += 61
        with self.assertRaises(RateLimitExceeded):
            limiter.acquire("same-session")


class SettingsTests(unittest.TestCase):
    def test_missing_secrets_produce_empty_key(self):
        secrets = Mock()
        secrets.get.side_effect = FileNotFoundError()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_api_key(secrets), "")

    def test_environment_key_takes_precedence_without_reading_secrets(self):
        secrets = Mock()
        with patch.dict(os.environ, {"GROQ_API_KEY": " test-key "}):
            self.assertEqual(get_api_key(secrets), "test-key")
        secrets.get.assert_not_called()

    def test_secrets_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_api_key({"GROQ_API_KEY": " test-key "}), "test-key")
            self.assertEqual(get_api_key({"GROQ_API_KEY": None}), "")

    def test_vulnerable_or_prerelease_runtime_is_rejected(self):
        for value in ("1.46.1", "1.53.0", "1.54.0rc1", "1.54.0.dev1", "invalid"):
            self.assertFalse(supported_streamlit(value), value)
        for value in ("1.54.0", "1.67.0", "2.0.0"):
            self.assertTrue(supported_streamlit(value), value)


if __name__ == "__main__":
    unittest.main()
