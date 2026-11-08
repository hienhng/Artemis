"""Exercise the real Streamlit page with an offline Groq client."""

from pathlib import Path
from types import SimpleNamespace
import os
import unittest
from unittest.mock import MagicMock, patch

from groq import AuthenticationError, NotFoundError
from httpx import Request, Response
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


class AppTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"GROQ_API_KEY": "offline-test-key"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.factory_patch = patch("groq.Groq")
        self.factory = self.factory_patch.start()
        self.addCleanup(self.factory_patch.stop)
        self.client = MagicMock()
        self.factory.return_value.__enter__.return_value = self.client
        self.client.chat.completions.create.return_value = SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(content="A synthetic historical answer")),
        ])

    def page(self):
        page = AppTest.from_file(APP, default_timeout=20).run()
        self.assertFalse(page.exception)
        return page

    def test_missing_credentials_show_setup_without_creating_client(self):
        with patch("chatbot.settings.get_api_key", return_value=""):
            page = self.page()
        self.assertTrue(any("GROQ_API_KEY" in message.value for message in page.info))
        self.assertEqual(len(page.chat_input), 0)
        self.factory.assert_not_called()

    def test_vulnerable_runtime_stops_before_chat(self):
        with patch("chatbot.settings.supported_streamlit", return_value=False):
            page = self.page()
        self.assertTrue(page.error)
        self.assertEqual(len(page.chat_input), 0)
        self.factory.assert_not_called()

    def test_welcome_and_active_chat_transition_when_starting_restoring_and_deleting(self):
        page = self.page()

        def has_markup(fragment):
            return any(fragment in item.value for item in page.markdown)

        self.assertFalse(has_markup('class="history-hero"'))
        self.assertTrue(has_markup('class="welcome-intro"'))
        self.assertEqual(page.chat_input[0].key, "welcome_prompt")
        page.button(key="suggest_0").click().run()
        self.assertFalse(page.exception)
        self.assertFalse(has_markup('class="history-hero"'))
        self.assertFalse(has_markup('class="welcome-intro"'))
        self.assertTrue(has_markup('class="thread-heading"'))
        self.assertEqual(len(page.chat_message), 2)
        self.assertEqual(page.chat_input[0].key, "conversation_prompt")
        self.assertFalse(any(button.key == "suggest_0" for button in page.button))

        conversation_id = page.session_state["chat_session_v2"].current_id
        page.button(key="new_conversation").click().run()
        self.assertFalse(page.exception)
        self.assertTrue(has_markup('class="welcome-intro"'))
        self.assertIn(conversation_id, page.session_state["chat_session_v2"].conversations)

        page.button(key=f"load_{conversation_id}").click().run()
        self.assertFalse(page.exception)
        self.assertTrue(has_markup('class="thread-heading"'))
        self.assertFalse(has_markup('class="history-hero"'))
        page.button(key=f"delete_{conversation_id}").click().run()
        self.assertFalse(page.exception)
        self.assertTrue(has_markup('class="welcome-intro"'))
        self.assertEqual(len(page.chat_message), 0)

    def test_real_pages_have_independent_history_and_deletion(self):
        alice = self.page()
        alice.chat_input[0].set_value("Alice private marker").run()
        self.assertFalse(alice.exception)
        alice_session = alice.session_state["chat_session_v2"]
        self.assertEqual(len(alice_session.current.messages), 2)
        bob = self.page()
        self.assertFalse(bob.session_state["chat_session_v2"].conversations)
        bob.button(key="suggest_0").click().run()
        self.assertFalse(bob.exception)
        self.assertEqual(len(bob.session_state["chat_session_v2"].current.messages), 2)
        next(button for button in bob.button if button.label == "🗑️ Delete All History").click().run()
        self.assertFalse(bob.session_state["chat_session_v2"].conversations)
        self.assertEqual(alice_session.current.messages[0]["content"], "Alice private marker")
        self.assertEqual(self.factory.call_args.kwargs["max_retries"], 0)
        self.assertEqual(self.factory.call_args.kwargs["timeout"], 30.0)

    def test_provider_errors_are_redacted_and_do_not_save_partial_turns(self):
        self.client.chat.completions.create.side_effect = RuntimeError("private-provider-marker")
        page = self.page()
        page.chat_input[0].set_value("Question").run()
        self.assertFalse(page.exception)
        self.assertTrue(page.error)
        self.assertNotIn("private-provider-marker", page.error[0].value)
        self.assertFalse(page.session_state["chat_session_v2"].conversations)

    def test_authentication_failure_shows_actionable_message_without_provider_details(self):
        marker = "private-authentication-marker"
        self.client.chat.completions.create.side_effect = AuthenticationError(
            marker,
            response=Response(401, request=Request("POST", "https://api.groq.com/openai/v1/chat/completions")),
            body={"error": {"message": marker}},
        )
        page = self.page()
        page.chat_input[0].set_value("Question").run()
        self.assertFalse(page.exception)
        self.assertIn("Groq rejected", page.error[0].value)
        self.assertIn("GROQ_API_KEY", page.error[0].value)
        self.assertNotIn(marker, page.error[0].value)
        self.assertFalse(page.session_state["chat_session_v2"].conversations)

    def test_user_and_model_html_are_plain_text(self):
        reply = '<img src="https://example.invalid/private-marker">'
        prompt = '<script>alert("marker")</script>'
        self.client.chat.completions.create.return_value.choices[0].message.content = reply
        page = self.page()
        page.chat_input[0].set_value(prompt).run()
        self.assertFalse(page.exception)
        self.assertIn(prompt, [message.value for message in page.text])
        self.assertIn(reply, [message.value for message in page.text])
        self.assertFalse(any(prompt in item.value or reply in item.value for item in page.markdown))

    def test_missing_model_shows_actionable_message_without_provider_details(self):
        marker = "private-not-found-marker"
        self.client.chat.completions.create.side_effect = NotFoundError(
            marker,
            response=Response(404, request=Request("POST", "https://api.groq.com/openai/v1/chat/completions")),
            body={"error": {"message": marker}},
        )
        page = self.page()
        page.chat_input[0].set_value("Question").run()
        self.assertFalse(page.exception)
        self.assertIn("AI model is unavailable", page.error[0].value)
        self.assertNotIn(marker, page.error[0].value)
        self.assertFalse(page.session_state["chat_session_v2"].conversations)


if __name__ == "__main__":
    unittest.main()
