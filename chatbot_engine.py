"""
Chatbot reply engine.

generate_reply(message, session, history) is what app.py calls. It tries
an OpenAI call first if OPENAI_API_KEY is set in the environment, and
otherwise (or if that call fails for any reason) falls back to a
rule-based engine so the bot always replies.
"""

import os
import random
import re
from datetime import datetime

try:
    import requests
except ImportError:  # requests is only needed if the OpenAI path is used
    requests = None

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_SYSTEM_PROMPT = (
    "You are PyBot, a friendly, concise chatbot embedded in a small Flask "
    "web app. Keep replies short (1-3 sentences) and conversational. "
    "Respond in the same language/style (English or Hinglish) the user uses."
)


# ---------------------------------------------------------------------------
# Rule-based engine
# ---------------------------------------------------------------------------
# Each entry is (topic, regex, [possible replies]). Checked top to bottom,
# so more specific phrases sit above generic single-word ones.
# {name} gets filled in if the user has already told the bot their name.

RULES = [
    ("name_share", r"\bmy name is (\w+)|\bmera naam (\w+)|\bcall me (\w+)",
     ["Nice to meet you, {name}! How can I help you today?",
      "Got it, {name} — what do you want to talk about?",
      "{name}, noted! What's up?"]),

    ("nothing_much", r"^(kuch (b|bhi) (nahi|nhi)|kuch (nahi|nhi)|nothing much|nothing)$",
     ["Koi baat nahi! Jab kuch poochna ho, main yahin hoon.",
      "All good — I'm here whenever you want to chat about something.",
      "Chill hi rehna, koi tension nahi.",
      "Sab shant hai idhar bhi. Kuch pucho toh sahi."]),

    ("greeting", r"\b(hi+|hello+|hey+|yo|hola|namaste+|namaskar)\b",
     ["Hey there! How can I help you today?",
      "Hello! What's on your mind?",
      "Hi! Good to see you here.",
      "Hey! Kaise ho? Kuch pucho na.",
      "Yo! Ready when you are.",
      "Namaste! Bolo, kya chahiye."]),

    ("bot_identity", r"\bwhat('s| is) your name\b|\bwho are you\b|\btera naam\b|\btum kaun ho\b",
     ["I'm PyBot, a small chatbot built with Flask and Python.",
      "I'm PyBot — a Python-powered chat assistant.",
      "PyBot hoon main, ek chota sa Flask chatbot."]),

    ("user_wellbeing", r"\bhow are you\b|\bkaise ho\b|\bkya haal\b|\bkaisa hai\b|\bwhat'?s up\b|\bwassup\b|\bkya chal raha\b",
     ["I'm just code, but I'm running smoothly! How about you?",
      "Doing great, thanks for asking! What can I do for you?",
      "Sab badhiya! Aap batao, kya chal raha hai?",
      "Main toh theek hoon, server up hai. Tum sunao?"]),

    ("time", r"\btime\b|\bsamay\b",
     ["The current time is {time}.",
      "Right now it's {time} on this server."]),

    ("date", r"\bdate\b|\bday is it\b|\btoday\b|\baaj ki date\b",
     ["Today's date is {date}.",
      "It's {date} today."]),

    ("age", r"\bhow old are you\b|\byour age\b|\bumar kitni\b|\bage kitni\b",
     ["I don't really have an age — I just run whenever the server starts.",
      "Ageless, technically. Started up today at {time} though.",
      "No birthday for me, sorry! I just exist while the app is running."]),

    ("location", r"\bwhere are you\b|\bkaha ho\b|\byour location\b",
     ["I live on whichever machine is running this Flask app.",
      "Nowhere in particular — I only exist while the server's running."]),

    ("joke", r"\bjoke\b|\bchutkula\b|\bhasao\b|\bfunny\b",
     ["Why do programmers prefer dark mode? Because light attracts bugs!",
      "Why did the developer go broke? Because they used up all their cache.",
      "There are 10 types of people: those who understand binary and those who don't.",
      "I'd tell you a UDP joke, but you might not get it.",
      "Why do Java developers wear glasses? Because they don't C#.",
      "I told my computer I needed a break, and now it won't stop sending me kit-kats."]),

    ("capabilities", r"\bhelp\b|\bwhat can you do\b|\bkya kar sakte ho\b|\bfeatures\b",
     ["I can chat, tell a joke, share the time/date, or just talk. Try 'tell me a joke' or 'what's the time'.",
      "Think of me as a small talk buddy — greetings, jokes, time/date, that kind of thing.",
      "Ask me for a joke, the time, or just say hi and see what happens."]),

    ("thanks", r"\bthank(s| you)\b|\bshukriya\b|\bdhanyavad\b",
     ["You're welcome!", "Anytime!", "Glad I could help.", "No problem at all."]),

    ("bye", r"\bbye\b|\bgoodbye\b|\bsee you\b|\balvida\b",
     ["Goodbye! Have a great day.", "See you later!", "Bye! Come back anytime.",
      "Alvida! Phir milte hain."]),

    ("compliment", r"\bgood bot\b|\bnice bot\b|\bawesome\b|\byou'?re (smart|cool|great|the best)\b|\bbest bot\b",
     ["Aw, thank you! I try my best.", "That made my day.",
      "Appreciate that!", "Thanks, that's kind of you to say."]),

    ("insult", r"\bstupid\b|\buseless\b|\bdumb\b|\bbad bot\b|\bworst\b",
     ["Fair, I'm still pretty basic. Try rephrasing and I'll give it another shot.",
      "Ouch, but okay. What were you trying to ask?"]),

    ("boredom", r"\bbored\b|\bboring\b|\bbore ho raha\b|\bbakwas\b",
     ["Bored, huh? Want a joke, or should I quiz you on something?",
      "Let's fix that — say 'tell me a joke' or ask me anything.",
      "Bore mat ho, kuch pucho mujhse."]),

    ("motivation", r"\btired\b|\bthak gaya\b|\bthak gyi\b|\bno mood\b|\bmann nahi\b|\blazy\b",
     ["Take a short break, then come back to it — even five focused minutes helps.",
      "One task at a time. You don't have to feel ready to start, just start small.",
      "Thoda rest le lo, phir wapas try karna."]),

    ("study", r"\bexam\b|\bstudy\b|\bpadhai\b|\bassignment\b|\bhomework\b",
     ["Break it into small chunks — it makes the workload feel lighter.",
      "Try the Pomodoro method: 25 minutes focused, 5 minute break, repeat.",
      "Padhai ho jayegi, bas thoda thoda karke karo."]),

    ("sleep", r"\bsleepy\b|\bsleep\b|\bneend\b|\bso raha\b|\bso rhi\b",
     ["Get some rest if you can, I'll still be here.",
      "Sleep well!",
      "So jao, subah dekh lena."]),

    ("food", r"\bhungry\b|\bbhookh\b|\bkhana\b|\bfood\b",
     ["Go grab a bite!", "Hungry? Maybe it's snack time.",
      "Khana kha lo pehle, phir baat karte hain."]),

    ("music", r"\bsong\b|\bgaana\b|\bmusic\b",
     ["I don't have ears, but I hear lo-fi is popular while coding.",
      "Music's a great coding companion — what's on your playlist?"]),

    ("movies", r"\bmovie\b|\bfilm\b|\bpicture dekh\b",
     ["I don't watch movies, but I'd probably like anything with robots in it.",
      "Not really my area, but I'm happy to chat about them!"]),

    ("love", r"\blove\b|\bpyaar\b|\bcrush\b",
     ["Aw, that's sweet. I can't feel it myself, but glad to hear it.",
      "Outside my expertise, but tell me more if you want."]),

    ("weather", r"\bweather\b|\bmausam\b|\bbaarish\b|\bgarmi\b|\bthand\b",
     ["I don't have live weather data plugged in — check your phone's weather app for now!",
      "No weather sensor here, sorry. I'm just a chat app."]),

    ("python", r"\bpython\b",
     ["Python's my home turf, I'm built with it using Flask. What do you want to know?"]),

    ("flask", r"\bflask\b",
     ["Flask is the Python web framework running this app — it handles the routes you're talking to right now."]),

    ("small_ack", r"\bnice\b|\bcool\b|\bgreat\b|\bbadhiya\b|\bmast\b|\bwah\b|\bok(ay)?\b",
     ["Glad you think so!", "Noted!", "Cool, what's next?", "Theek hai, aage bolo."]),

    ("yes", r"\byes\b|\bhaan\b|\bhan\b",
     ["Great, go ahead!", "Okay, tell me more."]),

    ("no", r"\bno\b|\bnahi\b|\bnhi\b",
     ["No worries. Anything else you'd like to ask?"]),
]

QUESTION_WORDS = ("what", "why", "how", "kya", "kyu", "kyun", "kaise", "kab", "kaun")

STOPWORDS = {
    "the", "a", "an", "is", "am", "are", "was", "were", "and", "or", "but",
    "to", "of", "in", "on", "at", "for", "with", "this", "that", "i", "you",
    "hai", "hi", "ho", "ka", "ki", "ke", "ko", "se", "me", "mein", "ek", "aur",
    "kya", "kyu", "kyun", "kaise", "hu", "hoon", "tha", "thi", "the",
}

FALLBACKS_STATEMENT = [
    "Interesting — tell me more about that.",
    "Got it. What else is on your mind?",
    "Hmm, I don't have a specific answer for that yet, but I'm listening.",
    "Samajh gaya, aage bolo.",
    "That's new to me, go on.",
]

FALLBACKS_QUESTION = [
    "That's a good question, but it's outside what I've been taught to answer yet.",
    "I don't have a real answer for that one — I'm a rule-based bot, not a search engine!",
    "Not sure about that one, honestly. Try asking it a different way?",
]


def _extract_keyword(text: str):
    """Pick the longest non-stopword token so the fallback can reference it."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    candidates = [w for w in words if w not in STOPWORDS and len(w) >= 4]
    if not candidates:
        return None
    return max(candidates, key=len)


def _pick_reply(replies, state, topic):
    """Random pick that avoids repeating the exact same line twice in a row
    for the same topic (falls back to a plain random choice if there's only
    one option, or if avoiding the last one would leave nothing)."""
    if len(replies) == 1:
        return replies[0]
    last = state.get("_last_reply_by_topic", {}).get(topic)
    choices = [r for r in replies if r != last] or replies
    return random.choice(choices)


def _remember_reply(state, topic, reply):
    seen = state.get("_last_reply_by_topic", {})
    seen[topic] = reply
    state["_last_reply_by_topic"] = seen


def _rule_based_reply(message: str, state: dict) -> str:
    """state is dict-like (e.g. flask.session) and is used to remember the
    user's name, the last topic, and the last reply given per topic."""
    text = message.strip().lower()

    for topic, pattern, replies in RULES:
        match = re.search(pattern, text)
        if match:
            reply = _pick_reply(replies, state, topic)
            name = None
            if match.groups():
                name = next((g for g in match.groups() if g), None)
            if "{name}" in reply and name:
                state["user_name"] = name.capitalize()
                reply = reply.format(name=name.capitalize())
            if "{time}" in reply:
                reply = reply.format(time=datetime.now().strftime("%I:%M %p"))
            if "{date}" in reply:
                reply = reply.format(date=datetime.now().strftime("%A, %d %B %Y"))
            _remember_reply(state, topic, reply)
            state["last_topic"] = topic
            return reply

    is_question = text.rstrip().endswith("?") or any(
        re.search(rf"\b{w}\b", text) for w in QUESTION_WORDS
    )
    keyword = _extract_keyword(text)
    stored_name = state.get("user_name")
    last_topic = state.get("last_topic")

    if keyword:
        if is_question:
            fallback = random.choice([
                f"I don't have a solid answer about '{keyword}' yet — try asking differently?",
                f"'{keyword}' isn't something I know much about, honestly. Rephrase and I'll try again.",
            ])
        else:
            fallback = random.choice([
                f"Tell me more about '{keyword}' — I'm curious what you mean.",
                f"'{keyword}', interesting. Go on.",
            ])
    else:
        pool = FALLBACKS_QUESTION if is_question else FALLBACKS_STATEMENT
        fallback = _pick_reply(pool, state, "fallback")
        _remember_reply(state, "fallback", fallback)
        if last_topic and last_topic != "fallback" and random.random() < 0.25:
            fallback += " Or we could go back to talking about that last thing."

    if stored_name and random.random() < 0.15:
        fallback = f"{fallback} (Still here for you, {stored_name}!)"

    state["last_topic"] = "fallback"
    return fallback


# ---------------------------------------------------------------------------
# Optional OpenAI-backed path
# ---------------------------------------------------------------------------

def _openai_reply(message: str, history: list):
    """Calls the OpenAI chat completions API. Returns None (never raises) if
    no key is set or the call fails, so the caller falls back to the rule
    engine automatically."""
    if not OPENAI_API_KEY or requests is None:
        return None
    try:
        messages = [{"role": "system", "content": OPENAI_SYSTEM_PROMPT}]
        for turn in history[-10:]:
            role = "assistant" if turn.get("role") == "bot" else "user"
            messages.append({"role": role, "content": turn.get("text", "")})
        messages.append({"role": "user", "content": message})

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.7,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_reply(message: str, state: dict, history: list = None):
    """Returns (reply_text, source) where source is 'ai' or 'rule'."""
    ai_reply = _openai_reply(message, history or [])
    if ai_reply:
        return ai_reply, "ai"
    return _rule_based_reply(message, state), "rule"
