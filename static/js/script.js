const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const typingRow = document.getElementById("typingRow");
const clearBtn = document.getElementById("clearBtn");
const themeSelect = document.getElementById("themeSelect");
const modeToggle = document.getElementById("modeToggle");
const micBtn = document.getElementById("micBtn");
const speakToggle = document.getElementById("speakToggle");

// ---------------------------------------------------------------------
// Theme + dark mode (persisted in localStorage, applied on load)
// ---------------------------------------------------------------------
const root = document.documentElement;

function applyTheme(theme) {
  root.setAttribute("data-theme", theme);
  if (themeSelect) themeSelect.value = theme;
  localStorage.setItem("pybot-theme", theme);
}

function applyMode(mode) {
  root.setAttribute("data-mode", mode);
  if (modeToggle) modeToggle.textContent = mode === "dark" ? "☀️" : "🌙";
  localStorage.setItem("pybot-mode", mode);
}

applyTheme(localStorage.getItem("pybot-theme") || "teal");
applyMode(localStorage.getItem("pybot-mode") || "light");

if (themeSelect) {
  themeSelect.addEventListener("change", () => applyTheme(themeSelect.value));
}
if (modeToggle) {
  modeToggle.addEventListener("click", () => {
    const current = root.getAttribute("data-mode") === "dark" ? "light" : "dark";
    applyMode(current);
  });
}

// ---------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------
function appendMessage(role, text, timestamp) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role === "bot" ? "bot-avatar" : "user-avatar"}`;
  avatar.textContent = role === "bot" ? ">_" : "you";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const p = document.createElement("p");
  p.textContent = text;

  const time = document.createElement("span");
  time.className = "timestamp";
  time.textContent = timestamp || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  bubble.appendChild(p);
  bubble.appendChild(time);
  msg.appendChild(avatar);
  msg.appendChild(bubble);

  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function showTyping(show) {
  typingRow.classList.toggle("hidden", !show);
  if (show) chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage(text) {
  appendMessage("user", text);
  messageInput.value = "";
  showTyping(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();

    // small delay so the typing indicator feels natural
    await new Promise((r) => setTimeout(r, 450 + Math.random() * 400));
    showTyping(false);

    if (res.ok) {
      appendMessage("bot", data.reply, data.timestamp);
      speakReply(data.reply);
    } else {
      appendMessage("bot", "Something went wrong. Please try again.");
    }
  } catch (err) {
    showTyping(false);
    appendMessage("bot", "Connection error — is the server running?");
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  sendMessage(text);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.getAttribute("data-prompt");
    sendMessage(prompt);
  });
});

clearBtn.addEventListener("click", async () => {
  await fetch("/api/history", { method: "DELETE" });
  chatWindow.innerHTML = "";
  appendMessage("bot", "Conversation cleared. Ask me something new!", "system");
});

// ---------------------------------------------------------------------
// Voice chatbot (bonus): speech-to-text input, text-to-speech output.
// Both use standard browser Web Speech APIs — no extra dependencies.
// Silently disables itself if the browser doesn't support them.
// ---------------------------------------------------------------------
let speakEnabled = true;

function speakReply(text) {
  if (!speakEnabled || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

if (speakToggle) {
  speakToggle.addEventListener("click", () => {
    speakEnabled = !speakEnabled;
    speakToggle.classList.toggle("active", speakEnabled);
    speakToggle.textContent = speakEnabled ? "🔊" : "🔇";
    if (!speakEnabled) window.speechSynthesis?.cancel();
  });
}

const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognitionAPI && micBtn) {
  const recognition = new SpeechRecognitionAPI();
  recognition.lang = "en-IN";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  let listening = false;

  micBtn.addEventListener("click", () => {
    if (listening) {
      recognition.stop();
      return;
    }
    try {
      recognition.start();
    } catch (err) {
      // recognition may already be starting; ignore
    }
  });

  recognition.addEventListener("start", () => {
    listening = true;
    micBtn.classList.add("listening");
  });

  recognition.addEventListener("end", () => {
    listening = false;
    micBtn.classList.remove("listening");
  });

  recognition.addEventListener("result", (event) => {
    const transcript = event.results[0][0].transcript;
    messageInput.value = transcript;
    sendMessage(transcript);
  });

  recognition.addEventListener("error", () => {
    listening = false;
    micBtn.classList.remove("listening");
  });
} else if (micBtn) {
  micBtn.style.display = "none"; // browser doesn't support speech recognition
}

messageInput.focus();
