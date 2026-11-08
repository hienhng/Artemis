<p align="center">
  <img src="assets/artemis-logo.svg" alt="Artemis logo" width="72">
</p>

<h1 align="center">Artemis</h1>

<p align="center"><strong>Vietnamese history, one question at a time.</strong></p>

<p align="center">
  A conversational companion for exploring Vietnam’s past and the people who shaped it.<br>
  Built with Python, Streamlit, and Groq.
</p>

Artemis lets you ask questions from the perspective of a historical figure or explore
events with a history scholar. Choose a companion, start with a suggested question,
and follow the conversation wherever your curiosity takes you.

The interface pairs burgundy and parchment tones with locally bundled serif fonts,
a responsive welcome screen, and a dedicated chat view.

[Get started](#get-started) · [Companions](#meet-your-companions) ·
[Customization](#customization) · [Development](#development) · [Deployment](#deployment)

## What you can do

- **Choose a perspective.** Switch between three historical figures and a general history scholar.
- **Find a starting point.** Each companion offers three suggested questions on the welcome screen.
- **Keep a conversation going.** Ask follow-up questions with recent exchanges included as context.
- **Revisit a chat.** Restore, delete, or start conversations from the sidebar during your session.
- **Explore on any screen.** Suggested questions stack on mobile, and the chat composer stays at the bottom of the conversation.

Responses are AI-generated interpretations, and the companions are configured to
reply in English. Use historical sources to verify facts and quotations.

## Meet your companions

| Companion | Perspective | Explore |
| --- | --- | --- |
| **Lý Thường Kiệt** | General, strategist, and poet of the Lý dynasty | Military strategy, independence, and patriotic poetry |
| **Ho Chi Minh** | President and revolutionary | The revolutionary movement, journeys abroad, and national independence |
| **Trần Hưng Đạo** | General and military thinker of the Trần dynasty | Resistance to the Mongol-Yuan invasions, Bạch Đằng, and military tactics |
| **History Scholar** | A general guide to Vietnamese history | Events, movements, and connections across eras |

## Get started

You need **Python 3.11 or newer**, Git, and a **Groq API key** from the
[Groq Console](https://console.groq.com/keys).

Clone the repository:

```sh
git clone https://github.com/hienhng/Artemis.git
cd Artemis
```

### Windows — PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:GROQ_API_KEY = "your-groq-api-key"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
export GROQ_API_KEY="your-groq-api-key"
.venv/bin/python -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally
[localhost:8501](http://localhost:8501). Choose a companion, then select a suggested
question or enter your own. **New conversation** opens a fresh welcome screen;
existing chats remain available in the sidebar until removed or evicted by the
session limits.

### Configure the API key with a secrets file

Instead of an environment variable, you can create `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "your-groq-api-key"
```

This file is ignored by Git. Keep your real key out of source files and commits.
The `GROQ_API_KEY` environment variable takes precedence over Streamlit secrets.
When using secrets files, project-level values override user-level values. Restart
the app after changing credentials.

Without a key, Artemis displays the welcome screen and setup instructions; chat
input is unavailable and suggested questions are disabled.

## How it works

Artemis uses Streamlit for the interface and session state. Each question is
validated, combined with the companion’s instructions and a bounded selection of
recent conversation turns, then sent to Groq. A completed question-and-answer pair
is added to the session only after a successful response.

The model is configured as `openai/gpt-oss-20b` in
[chatbot/service.py](chatbot/service.py). Requests use a temperature of `0.7`,
low reasoning effort, and a completion budget of 600 tokens. Reasoning content is
excluded from responses.

## Conversation storage and limits

Conversation history is held **in server memory, scoped to the current Streamlit
session**. Artemis does not write transcripts to disk or provide account-based
storage. A temporary reconnect may resume a session; a new session or server restart
does not preserve its chats.

Your questions, companion instructions, and selected conversation context are sent
to Groq to generate replies. Avoid including sensitive information. Chat messages
render as plain text, so user and model content cannot insert active HTML or remote
Markdown images into the conversation.

| Resource | Limit |
| --- | --- |
| Conversations retained per session | 10; the least recently active chat is removed first |
| History retained per conversation | Up to 10 complete turns and 16,000 characters |
| Question length | 2,000 characters |
| Model input context | 16,000 characters, including instructions and the latest question |
| Response retained | 4,000 characters |
| Requests per session | 5 per minute and 50 per hour |
| Requests across one server process | 20 per minute and 200 per hour |
| Provider timeout | 30 seconds, with no automatic retries |

Older turns are removed as needed to stay within the history limits. Failed
provider calls also consume the request budget. Starting a new conversation or
clearing history does not reset that budget.

## Project structure

```text
app.py                       Streamlit page, sidebar, and conversation events
chatbot/
  conversations.py           Session-owned history and retention rules
  service.py                 Prompt validation, context limits, rate limits, and Groq calls
  settings.py                Credential lookup and Streamlit version check
  ui.py                      Welcome screen, chat rendering, and asset loading
personalities.py             Companion definitions and conversation instructions
data.json                    Suggested questions for each companion
style.css                    Application styling and responsive layouts
assets/                      Runtime images, brand assets, fonts, and font licenses
tests/                       App, session isolation, security, and server checks
.streamlit/config.toml       Streamlit theme and server settings
.github/workflows/checks.yml Cross-platform tests and dependency audit
docs/                        Original design references and archived project material
```

## Customization

To add a companion, use the same character key in these three places:

1. **`personalities.py`** — add a `HistoricalPersonality` with a name, description,
   system prompt, and greeting. The system prompt defines its perspective and reply language.
2. **`data.json`** — add at least three suggested questions.
3. **`chatbot/ui.py`** — add an entry to `CHARACTER_DETAILS` with initials, era,
   years, role, a Streamlit Material icon, and three topic labels for the question cards.

Edit `style.css` to adjust colors, typography, spacing, and responsive behavior.
The logo and background live in `assets/`; font files are bundled locally. CSS and
background changes appear on the next app rerun. Restart the server after replacing
cached font files.

The [customization guide](CUSTOMIZATION_GUIDE.md) includes character-definition
examples in Vietnamese. Use the current three-file structure above when adding a
companion.

## Development

Install the development requirements, then run the checks from the repository root.
The commands below use the Windows virtual environment; on macOS/Linux, replace
`.\.venv\Scripts\python.exe` with `.venv/bin/python`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

Tests use synthetic conversations and a mocked Groq client, so no real API key or
live model calls are needed. The server test starts a temporary loopback server to
check HTTP health and WebSocket origin protection.

GitHub Actions runs the suite on Windows and Linux with Python 3.11 and 3.13.
Dependency audits run on pushes, pull requests, and a weekly schedule. Runtime
dependencies are pinned in `requirements.txt`; development tooling is listed in
`requirements-dev.txt`.

## Deployment

Use a host that supports a long-running Python process and Streamlit’s WebSocket
connection. Install `requirements.txt`, provide `GROQ_API_KEY` through the host’s
secret configuration, and start `app.py` with Streamlit.

For a host that requires listening on all interfaces and a specified port:

```sh
python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

Adjust the port to match the host. The included Replit configuration uses port
`5000`; the development container forwards port `8501`.

Keep CORS and XSRF protection enabled. If a reverse proxy requires an explicit
public address, configure `STREAMLIT_BROWSER_SERVER_ADDRESS` and
`STREAMLIT_BROWSER_SERVER_PORT` for the external hostname and port.

Request budgets are shared only within one server process and reset on restart.
For a public deployment, configure provider-side spending limits. Multiple workers
need a shared quota mechanism; persistent, account-owned history requires
authentication and durable storage.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Setup instructions appear instead of chat input | Set `GROQ_API_KEY` in the environment or Streamlit secrets, then restart. |
| Groq rejects the API key | Replace the rejected key. Check for an older environment variable overriding your secrets file. |
| The AI model is unavailable | Check Groq model access and the `MODEL_ID` value in `chatbot/service.py`. |
| A request limit is reached | Wait for the relevant minute or hour window to expire. New chats do not reset the limit. |
| A response fails or times out | Try again later. Failed calls do not save a partial turn. |
| Chat history disappears | History belongs to a temporary session and is also subject to retention limits. |
| The app asks you to update dependencies | Reinstall `requirements.txt` with the virtual environment’s Python. The app requires Streamlit 1.54.0 or newer and rejects prerelease versions. |

## License

Artemis is distributed under the [MIT License](LICENSE). The bundled
[Prata](assets/Prata-OFL.txt) and [Oldenburg](assets/Oldenburg-OFL.txt) fonts retain
their accompanying SIL Open Font License notices.
