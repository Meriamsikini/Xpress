/*
const form = document.getElementById("form");
const input = document.getElementById("input");
const chat = document.getElementById("chat");

function appendBubble(text, cls="bot", meta="") {
  const node = document.createElement("div");
  node.className = `bubble ${cls}`;
  node.innerHTML = `<div>${text}</div>` + (meta ? `<div class="meta">${meta}</div>` : "");
  chat.appendChild(node);
  chat.scrollTop = chat.scrollHeight;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  // show user's message
  appendBubble(q, "user");
  input.value = "";
  // show spinner
  appendBubble("Recherche en cours...", "bot", "");
  const placeholder = chat.lastChild;

  try {
    const res = await fetch("/ask", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query: q })
});

    
    const data = await res.json();

    // remove placeholder
    placeholder.remove();

    // display bot answer
    appendBubble(data.answer || "Pas de réponse.", "bot");

    // display sources
    if (data.sources && data.sources.length) {
      const sdiv = document.createElement("div");
      sdiv.className = "source-list";
      sdiv.innerHTML = "<strong>Sources :</strong><br/>";
      data.sources.forEach((s, idx) => {
        const a = document.createElement("a");
        a.href = s.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = `${s.title || ("Source " + (idx+1))}`;
        sdiv.appendChild(a);
        sdiv.appendChild(document.createElement("br"));
      });
      chat.appendChild(sdiv);
      chat.scrollTop = chat.scrollHeight;
    }
  } catch (err) {
    placeholder.remove();
    appendBubble("Erreur serveur : " + err.message, "bot");
  }
});
*/
const userEmail = localStorage.getItem("user_email") || "";
if (!userEmail) window.location.href = "/register";

const sidebar = document.getElementById("sidebar");
const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const disconnectBtn = document.getElementById("disconnect");
const historyBtn = document.getElementById("history");
const newConvoBtn = document.getElementById("new-convo");
const historyListDiv = document.getElementById("history-list");

// add reference to the main container so we can shift it
const container = document.querySelector(".container");

const confirmModal = document.getElementById("confirm-modal");
const confirmYes = document.getElementById("confirm-yes");
const confirmNo = document.getElementById("confirm-no");

// add references for delete modal
const deleteModal = document.getElementById("delete-modal");
const deleteConfirmBtn = document.getElementById("delete-confirm");
const deleteCancelBtn = document.getElementById("delete-cancel");
const deleteMessage = document.getElementById("delete-message");
const deleteErrorDiv = document.getElementById("delete-error");

let pendingDelete = null; // { id, row }

function addMessage(msg, cls) {
    const div = document.createElement("div");
    div.classList.add("message", cls);
    div.textContent = msg;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
    const question = userInput.value.trim();
    if (!question) return;
    addMessage(question, "user-message");
    userInput.value = "";

    const loading = document.createElement("div");
    loading.classList.add("message", "bot-message");
    loading.textContent = "✳️ Génération de la réponse...";
    chatBox.appendChild(loading);

    try {
        const res = await fetch(`/ask?email=${userEmail}`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ query: question })
        });
        const data = await res.json();
        chatBox.removeChild(loading);
        addMessage(data.answer, "bot-message");
    } catch (err) {
        chatBox.removeChild(loading);
        addMessage("❌ Erreur serveur.", "bot-message");
    }
}

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keypress", e => { if(e.key==="Enter") sendMessage(); });

// Nouvelle conversation
newConvoBtn.addEventListener("click", () => {
    chatBox.innerHTML = "";
});

// Sidebar / Historique toggle: opens/closes, shifts chat, and fetches history when opening
historyBtn.addEventListener("click", async () => {
    const willOpen = !sidebar.classList.contains("open");
    if (willOpen) {
        // open sidebar and shift chat
        sidebar.classList.add("open");
        container.classList.add("shifted");

        // fetch history
        try {
            const res = await fetch(`/history?email=${userEmail}`);
            const data = await res.json();
            historyListDiv.innerHTML = "";
            if (data.history && data.history.length) {
                data.history.forEach(h => {
                    // create a row wrapper: left = select button, right = delete button
                    const row = document.createElement("div");
                    row.classList.add("history-row");

                    const selectBtn = document.createElement("button");
                    selectBtn.classList.add("history-item");
                    // Title = first 50 chars of question
                    const title = (h.question || "").slice(0,50) + ((h.question || "").length>50 ? "…" : "");
                    selectBtn.textContent = title;
                    selectBtn.addEventListener("click", () => {
                        // fill chat with question/answer
                        chatBox.innerHTML = "";
                        addMessage(h.question, "user-message");
                        addMessage(h.answer, "bot-message");
                        // close sidebar, hide history list and unshift chat
                        sidebar.classList.remove("open");
                        container.classList.remove("shifted");
                        historyListDiv.style.display = "none";
                    });

                    const delBtn = document.createElement("button");
                    delBtn.classList.add("delete-btn");
                    delBtn.type = "button";
                    delBtn.title = "Supprimer la conversation";
                    // When creating delete button, use icon markup instead of emoji
                    delBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';

                    // delete handler: remove from DB and from UI
                    delBtn.addEventListener("click", async (ev) => {
                        ev.stopPropagation();
                        // open delete modal instead of confirm()
                        const convId = extractId(h);
                        if(!convId) {
                            // show a quick inline alert in the modal
                            deleteErrorDiv.textContent = "Impossible de déterminer l'identifiant de la conversation.";
                            deleteErrorDiv.style.display = "block";
                            deleteModal.style.display = "flex";
                            pendingDelete = null;
                            return;
                        }
                        deleteErrorDiv.style.display = "none";
                        deleteMessage.textContent = `Supprimer la conversation : "${((h.question||"")).slice(0,80)}${(h.question && h.question.length>80?"…":"")}" ?`;
                        deleteModal.style.display = "flex";
                        pendingDelete = { id: convId, row };
                    });

                    row.appendChild(selectBtn);
                    row.appendChild(delBtn);
                    historyListDiv.appendChild(row);
                });
            } else {
                const empty = document.createElement("div");
                empty.classList.add("history-empty");
                empty.textContent = "Aucun historique.";
                historyListDiv.appendChild(empty);
            }
            historyListDiv.style.display = "block";
        } catch (err) {
            historyListDiv.innerHTML = "<div class='history-empty'>Erreur en récupérant l'historique.</div>";
            historyListDiv.style.display = "block";
        }
    } else {
        // close sidebar and unshift chat
        sidebar.classList.remove("open");
        container.classList.remove("shifted");
        historyListDiv.style.display = "none";
    }
});

// Déconnexion: show modal instead of alert
disconnectBtn.addEventListener("click", () => {
    confirmModal.style.display = "flex";
});

// Modal actions
confirmYes.addEventListener("click", () => {
    localStorage.removeItem("user_email");
    window.location.href = "/login";
});
confirmNo.addEventListener("click", () => {
    confirmModal.style.display = "none";
});

// close modal when clicking overlay
confirmModal.querySelector(".modal-overlay").addEventListener("click", () => {
    confirmModal.style.display = "none";
});

deleteCancelBtn.addEventListener("click", () => {
    deleteModal.style.display = "none";
    pendingDelete = null;
});

deleteConfirmBtn.addEventListener("click", async () => {
    if(!pendingDelete || !pendingDelete.id) return;
    deleteConfirmBtn.disabled = true;
    deleteErrorDiv.style.display = "none";
    const result = await deleteConversationById(pendingDelete.id);
    deleteConfirmBtn.disabled = false;
    if (result.ok) {
        // remove row visually
        if (pendingDelete.row && pendingDelete.row.remove) pendingDelete.row.remove();
        deleteModal.style.display = "none";
        pendingDelete = null;
    } else {
        const msg = result.error || result.text || `Erreur ${result.status || ""}`;
        deleteErrorDiv.textContent = `Impossible de supprimer : ${msg}`;
        deleteErrorDiv.style.display = "block";
    }
});

// close delete modal when clicking overlay
deleteModal.querySelector(".modal-overlay").addEventListener("click", () => {
    deleteModal.style.display = "none";
    pendingDelete = null;
});

// helper to extract id from history item
function extractId(h) {
    if (!h) return "";
    if (typeof h === "string") return h;
    if (h._id) {
        if (typeof h._id === "string") return h._id;
        if (h._id.$oid) return h._id.$oid;
        try { return String(h._id); } catch(e) {}
    }
    if (h.id) return h.id;
    return "";
}

// delete helper: try DELETE, if 405 then fallback to POST with action=delete
async function deleteConversationById(id) {
    // try DELETE first
    try {
        const q = `/history?email=${encodeURIComponent(userEmail)}&id=${encodeURIComponent(id)}`;
        let res = await fetch(q, { method: "DELETE" });
        if (res.ok) return { ok: true };
        if (res.status === 405) {
            // fallback: some servers don't accept DELETE; try POST fallback
            const fallback = await fetch("/history", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "delete", email: userEmail, id })
            });
            if (fallback.ok) return { ok: true };
            const text = await fallback.text();
            return { ok: false, status: fallback.status, text };
        }
        const text = await res.text();
        return { ok: false, status: res.status, text };
    } catch (err) {
        return { ok: false, error: err.message || String(err) };
    }
}


// === Mode nuit / jour ===
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-icon");
const bodyEl = document.body;

if (localStorage.getItem("theme") === "dark") {
  bodyEl.classList.add("dark-mode");
  if (themeIcon) {
    themeIcon.classList.remove("fa-moon");
    themeIcon.classList.add("fa-sun");
  }
}

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    bodyEl.classList.toggle("dark-mode");
    const isDark = bodyEl.classList.contains("dark-mode");
    if (themeIcon) {
      themeIcon.classList.toggle("fa-moon", !isDark);
      themeIcon.classList.toggle("fa-sun", isDark);
    }
    localStorage.setItem("theme", isDark ? "dark" : "light");
  });
}

