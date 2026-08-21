# PyBot — AI Chatbot Web App

A chat web app made with Flask, SQLite, and plain HTML/CSS/JS.

## What it does

- Chat UI with user/bot message bubbles and a typing animation
- Login/Signup with hashed passwords, plus a "Continue as guest" option
- Dark mode and a few color themes (saved in the browser)
- Mic input and spoken replies using the browser's built-in speech APIs
- Chat history saved in SQLite for logged-in users, so it's still there next time you log in
- If you set an `OPENAI_API_KEY` env variable it'll use that for replies instead of the built-in rule engine

## Project structure
```
ai-chatbot/
├── app.py                 # Flask routes: auth, chat API, history
├── chatbot_engine.py      # Rule-based engine + optional OpenAI call
├── database.py            # SQLite helpers (users, messages)
├── requirements.txt
├── templates/
│   ├── index.html
│   ├── login.html
│   └── signup.html
└── static/
    ├── css/style.css
    └── js/script.js
```

## Running it
```bash
cd ai-chatbot
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 — you'll land on the login page, sign up or log in, or click "Continue as guest".

To use real AI replies instead of the rule-based ones:
```bash
export OPENAI_API_KEY="sk-..."
python app.py
```
Without the key set it just uses the built-in rule engine, no extra setup needed.

## How the chatbot answers

`chatbot_engine.py` has a list of (topic, regex, replies) rules for things like greetings,
jokes, time/date, mood, Python/Flask questions, etc, in English and Hinglish. It checks the
message against each pattern and picks a reply, trying not to repeat the same line twice in a
row. If nothing matches, it checks whether the message looks like a question and gives a
fallback reply, sometimes referencing the keyword from what you typed.

## Database

`database.py` sets up two tables in `chatbot.db` the first time you run the app:
- `users` — id, username, password_hash, created_at
- `messages` — id, user_id, role, text, created_at

## Notes

- Add more `(topic, pattern, [replies])` entries in `chatbot_engine.py` to teach it new topics
- To add a theme, add a `[data-theme="name"]` block in `style.css` and an option in `index.html`
