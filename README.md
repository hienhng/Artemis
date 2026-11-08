# 📜 Chatbot Lịch Sử Việt Nam

A Streamlit chatbot for conversations with Vietnamese historical figures,
powered by Groq using `openai/gpt-oss-20b`. Requires Python 3.11 or newer;
CI covers Python 3.11 and 3.13.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:GROQ_API_KEY = "your-api-key"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

On macOS/Linux, use `.venv/bin/python` and `export GROQ_API_KEY="your-api-key"`.
Alternatively, create `.streamlit/secrets.toml` (ignored by Git):

```toml
GROQ_API_KEY = "your-api-key"
```

Get a key from [Groq Console](https://console.groq.com/keys). Missing credentials
show setup instructions instead of a traceback. Install the pinned requirements
before running; the app refuses Streamlit releases below the 1.54.0 security baseline.

## Conversation privacy and limits

- Chats belong to the current browser session and are never written to a shared file.
  A new session starts empty; a reconnect may resume an existing session temporarily.
  Closing the app or restarting its server does not provide durable chat storage.
- Each session retains at most 10 chats. Each chat retains at most 10 complete
  turns and 16,000 characters, removing the oldest content first.
- Questions are limited to 2,000 characters. Model context is limited to 16,000
  characters including character instructions; completions are limited to 600
  tokens including reasoning and 4,000 retained response characters. Reasoning
  effort is set to low and reasoning content is excluded from responses.
  Chat content renders as plain text.
- Requests are limited to 5/minute and 50/hour per session, and 20/minute and
  200/hour across one server process. Failed calls also consume the budget.
  Requests time out after 30 seconds and have no automatic retries.
- Messages are sent to Groq to generate replies. Avoid entering sensitive information.

Rate budgets reset when the process restarts and do not coordinate separate workers.
For a public deployment, set provider-side spending limits; for multiple workers,
enforce a shared quota at an authenticated gateway or in a shared store.
Persistent history requires authenticated user ownership and transactional storage.

## Project structure

```text
app.py                       Streamlit page and event handling
chatbot/
  conversations.py           Bounded session-local conversation state
  service.py                 Validation, context budgets, rate limits, Groq calls
  settings.py                Credential lookup and runtime security baseline
  ui.py                      Cached presentation assets and plain-text messages
personalities.py             Historical characters and prompts
data.json                    Suggested questions
style.css                    Active application stylesheet
assets/background.png        Runtime background image
assets/artemis-logo.svg      Oldenburg A monogram for the sidebar
assets/artemis-logo.png      Matching browser tab icon
docs/screenshots/            Preserved design references
docs/legacy/                 Archived generated commit log
tests/                       Security and Streamlit regression tests
.streamlit/config.toml       CORS/XSRF protections enabled
.github/workflows/checks.yml Tests and dependency audit
.local/                      Ignored local backups and temporary files
```

See [CUSTOMIZATION_GUIDE.md](CUSTOMIZATION_GUIDE.md) to add characters.
Paths for application resources resolve relative to the project, not the shell's
working directory. CSS and background image updates appear on the next page rerun.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

Tests use synthetic conversations and a mocked provider; they do not send live API
requests. CI runs tests on Windows and Linux and audits dependencies weekly and on
changes. Direct dependencies are pinned; transitive dependencies are resolved by pip
and checked by the audit job.

## Deployment

Configure `GROQ_API_KEY` through the hosting platform's secrets. Keep
`server.enableCORS` and `server.enableXsrfProtection` enabled. When using a reverse
proxy, set `browser.serverAddress` to the public hostname and `browser.serverPort`
to the external port, for example with `STREAMLIT_BROWSER_SERVER_ADDRESS` and
`STREAMLIT_BROWSER_SERVER_PORT`. Bind the server only to the interfaces needed by
your hosting platform. Use `.venv` locally so an older global Streamlit installation
does not take precedence.

## Authentication failures

If Groq returns `AuthenticationError` (HTTP 401), the configured key was rejected.
Create or obtain a valid key at [Groq Console](https://console.groq.com/keys), update
`GROQ_API_KEY`, and restart the server. Never paste the key into chat or commit it.

The environment variable takes precedence. Otherwise, Streamlit merges the user's
`~/.streamlit/secrets.toml` and the project's `.streamlit/secrets.toml`, with the
project value taking precedence. A missing project file is valid when the user-level
file supplies the key. On Windows, the user-level file is under
`%USERPROFILE%\.streamlit\secrets.toml`. Check for an older value in a higher-priority
source if replacing the key has no effect.

## Model availability

The model ID is defined once in `chatbot/service.py`. The default is
`openai/gpt-oss-20b`, Groq's recommended replacement for `llama-3.1-8b-instant`,
which was retired for free/developer accounts on August 16, 2026. See
[Groq's deprecation history](https://console.groq.com/docs/deprecations).
An HTTP 404 (`NotFoundError`) can indicate an unavailable model or endpoint;
check account model access and the current Groq model catalog before changing it.
When migrating models, verify completion and reasoning parameters as well as the ID.

## Legacy chat files

The former `conversation_history.json` is no longer loaded. During this security
cleanup, the existing local file was preserved as
`.local/legacy-conversation-history.json`, which is ignored by Git. Keep that backup
private; the app does not import it or expose it to browser sessions.

Deleting the tracked file in a new commit does **not** erase transcripts from older
commits or existing clones. If the historical transcripts require removal, coordinate
a repository-history purge and cleanup of affected clones with repository owners.

## License

[MIT](LICENSE).
