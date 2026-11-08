# Vietnamese Historical Chatbot

Run `streamlit run app.py --server.port=5000 --server.address=0.0.0.0`.
Supply `GROQ_API_KEY` through Replit Secrets and install `requirements.txt`.
Keep CORS and XSRF protection enabled. Configure the public browser address/port
when required by the deployment proxy; do not disable security checks.

`app.py` owns page events; `chatbot/` contains bounded session-local conversations,
request limits, credential lookup, and presentation helpers. `style.css` is loaded
by `chatbot/ui.py`; runtime images are `assets/background.png` and the
`assets/artemis-logo.svg` / `assets/artemis-logo.png` brand assets.
No conversation file is read or written. Browser sessions have independent history.
See README.md for resource limits, deployment guidance, and regression checks.
