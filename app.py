# Main Flask app for PyBot.
# Handles login/signup, a guest mode, and the chat API. Chat replies come
# from chatbot_engine.generate_reply(). Logged-in users' history is saved
# to SQLite (database.py); guests just get session-based history.

import os
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from chatbot_engine import generate_reply
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

with app.app_context():
    init_db()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id") and not session.get("guest"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Username and password are required."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        else:
            db = get_db()
            existing = db.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if existing:
                error = "That username is already taken."
                db.close()
            else:
                db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
                user = db.execute(
                    "SELECT id FROM users WHERE username = ?", (username,)
                ).fetchone()
                db.close()
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = username
                return redirect(url_for("home"))

    return render_template("signup.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/guest")
def guest():
    session.clear()
    session["guest"] = True
    session["username"] = "Guest"
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Chat routes
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def home():
    return render_template("index.html", username=session.get("username", "Guest"))


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    history = session.get("history", [])
    reply, source = generate_reply(message, session, history)

    history.append({"role": "user", "text": message})
    history.append({"role": "bot", "text": reply})
    session["history"] = history[-50:]
    session.modified = True

    # Save to SQLite for logged-in users only
    if session.get("user_id"):
        db = get_db()
        db.execute(
            "INSERT INTO messages (user_id, role, text) VALUES (?, ?, ?)",
            (session["user_id"], "user", message),
        )
        db.execute(
            "INSERT INTO messages (user_id, role, text) VALUES (?, ?, ?)",
            (session["user_id"], "bot", reply),
        )
        db.commit()
        db.close()

    return jsonify(
        {
            "reply": reply,
            "timestamp": datetime.now().strftime("%I:%M %p"),
            "source": source,  # "ai" or "rule" — which engine answered
        }
    )


@app.route("/api/history", methods=["GET"])
@login_required
def get_history():
    if session.get("user_id"):
        db = get_db()
        rows = db.execute(
            "SELECT role, text FROM messages WHERE user_id = ? ORDER BY id ASC LIMIT 200",
            (session["user_id"],),
        ).fetchall()
        db.close()
        return jsonify({"history": [{"role": r["role"], "text": r["text"]} for r in rows]})
    return jsonify({"history": session.get("history", [])})


@app.route("/api/history", methods=["DELETE"])
@login_required
def clear_history():
    session["history"] = []
    if session.get("user_id"):
        db = get_db()
        db.execute("DELETE FROM messages WHERE user_id = ?", (session["user_id"],))
        db.commit()
        db.close()
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
