/**
 * app.js – AcademicRAG frontend logic
 * Communicates with the FastAPI backend at /api/upload and /api/chat.
 */

const API_BASE = "";   // same origin; change to "http://localhost:8000" for dev with Vite

// ── DOM refs ──────────────────────────────────────────────────────────────
const dropZone      = document.getElementById("dropZone");
const fileInput     = document.getElementById("fileInput");
const uploadBtn     = document.getElementById("uploadBtn");
const statusBadge   = document.getElementById("statusBadge");
const fileList      = document.getElementById("fileList");
const chatFeed      = document.getElementById("chatFeed");
const emptyState    = document.getElementById("emptyState");
const questionInput = document.getElementById("questionInput");
const sendBtn       = document.getElementById("sendBtn");

// ── State ─────────────────────────────────────────────────────────────────
let selectedFile    = null;
let uploadedFiles   = [];   // { filename, chunks }
let chatUnlocked    = false;

// ── File selection ────────────────────────────────────────────────────────
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) selectFile(fileInput.files[0]);
});

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
});

function selectFile(file) {
  selectedFile = file;
  uploadBtn.disabled = false;
  showStatus("loading", `Selected: ${file.name}`);
}

// ── Upload ────────────────────────────────────────────────────────────────
uploadBtn.addEventListener("click", uploadFile);

async function uploadFile() {
  if (!selectedFile) return;

  uploadBtn.disabled = true;
  showStatus("loading", "Uploading & processing…");

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      showStatus("error", data.detail || "Upload failed.");
      uploadBtn.disabled = false;
      return;
    }

    // Success
    uploadedFiles.push({ filename: data.filename, chunks: data.chunks });
    renderFileList();
    showStatus("success", `Processed ${data.chunks} chunks from "${data.filename}"`);
    unlockChat();

    // Reset selector
    selectedFile = null;
    fileInput.value = "";
    uploadBtn.disabled = true;

  } catch (err) {
    showStatus("error", "Network error — is the backend running?");
    uploadBtn.disabled = false;
  }
}

function renderFileList() {
  fileList.innerHTML = "";
  uploadedFiles.forEach(({ filename, chunks }) => {
    const ext = filename.split(".").pop().toLowerCase();
    const icon = ext === "pdf" ? "📕" : ext === "docx" ? "📘" : "📄";
    const item = document.createElement("div");
    item.className = "file-item";
    item.innerHTML = `
      <span class="file-icon">${icon}</span>
      <div>
        <div class="file-name">${escapeHtml(filename)}</div>
        <div class="file-meta">${chunks} chunks indexed</div>
      </div>`;
    fileList.appendChild(item);
  });
}

// ── Chat ──────────────────────────────────────────────────────────────────
function unlockChat() {
  if (chatUnlocked) return;
  chatUnlocked = true;
  questionInput.disabled = false;
  sendBtn.disabled = false;
  questionInput.placeholder = "Ask a question about your documents…";
  questionInput.focus();
}

sendBtn.addEventListener("click", sendQuestion);
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendQuestion();
  }
});

// Auto-grow textarea
questionInput.addEventListener("input", () => {
  questionInput.style.height = "auto";
  questionInput.style.height = Math.min(questionInput.scrollHeight, 140) + "px";
});

async function sendQuestion() {
  const question = questionInput.value.trim();
  if (!question) return;

  // Hide empty state on first message
  emptyState && emptyState.remove();

  appendMessage("user", question);
  questionInput.value = "";
  questionInput.style.height = "auto";
  setInputsDisabled(true);

  const typingId = appendTyping();

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    removeTyping(typingId);

    if (!res.ok) {
      appendMessage("assistant", `Error: ${data.detail || "Something went wrong."}`, []);
    } else {
      appendMessage("assistant", data.answer, data.sources || []);
    }
  } catch (err) {
    removeTyping(typingId);
    appendMessage("assistant", "Network error — is the backend running?", []);
  }

  setInputsDisabled(false);
  questionInput.focus();
}

function appendMessage(role, text, sources = []) {
  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "U" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (role === "assistant") {
    // Render markdown; wrap in scoped container for CSS targeting
    const mdBody = document.createElement("div");
    mdBody.className = "md-body";
    mdBody.innerHTML = typeof marked !== "undefined"
      ? marked.parse(text, { breaks: true, gfm: true })
      : escapeHtml(text).replace(/\n/g, "<br>");
    bubble.appendChild(mdBody);
  } else {
    // User messages: plain text, no markdown
    bubble.textContent = text;
  }

  if (sources.length) {
    const sourcesDiv = document.createElement("div");
    sourcesDiv.className = "sources";
    sources.forEach((s) => {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      // Split "filename — Page N" for the icon placement
      const pageMatch = s.match(/— Page (.+)$/);
      const icon = document.createElement("span");
      icon.className = "src-icon";
      icon.textContent = "📄";
      const label = document.createTextNode(s);
      tag.appendChild(icon);
      tag.appendChild(label);
      sourcesDiv.appendChild(tag);
    });
    bubble.appendChild(sourcesDiv);
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatFeed.appendChild(row);
  scrollToBottom();
}

function appendTyping() {
  const id = "typing-" + Date.now();
  const row = document.createElement("div");
  row.className = "msg-row assistant";
  row.id = id;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = `<div class="typing"><span></span><span></span><span></span></div>`;

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatFeed.appendChild(row);
  scrollToBottom();
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ── Helpers ───────────────────────────────────────────────────────────────
function showStatus(type, message) {
  statusBadge.className = `status-badge show ${type}`;
  const icons = { loading: "⏳", success: "✅", error: "❌" };
  statusBadge.innerHTML = `<span>${icons[type]}</span><span>${escapeHtml(message)}</span>`;
}

function setInputsDisabled(disabled) {
  questionInput.disabled = disabled;
  sendBtn.disabled = disabled;
  if (disabled) {
    sendBtn.innerHTML = `<div class="spinner"></div>`;
  } else {
    sendBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" y1="2" x2="11" y2="13"/>
        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
      </svg>`;
  }
}

function scrollToBottom() {
  chatFeed.scrollTop = chatFeed.scrollHeight;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
