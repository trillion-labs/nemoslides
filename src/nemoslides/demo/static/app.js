const STORAGE_KEY = "slides-sft-demo-session";

const form = document.getElementById("deck-form");
const promptField = document.getElementById("prompt");
const generateButton = document.getElementById("generate-button");
const statusEl = document.getElementById("status");
const emptyState = document.getElementById("empty-state");
const viewerFrame = document.getElementById("viewer-frame");
const openLink = document.getElementById("open-link");

function selectedValue(name) {
  const selected = form.querySelector(`input[name="${name}"]:checked`);
  return selected ? selected.value : null;
}

function applyViewer(presentationUrl) {
  viewerFrame.src = presentationUrl;
  viewerFrame.classList.remove("hidden");
  emptyState.classList.add("hidden");
  openLink.href = presentationUrl;
  openLink.classList.remove("hidden");
}

function saveSession(payload) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function restoreSession() {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return;

  try {
    const saved = JSON.parse(raw);
    if (saved.prompt) promptField.value = saved.prompt;

    for (const field of ["audience", "tone", "slide_count"]) {
      const value = saved[field];
      if (!value) continue;
      const input = form.querySelector(`input[name="${field}"][value="${value}"]`);
      if (input) input.checked = true;
    }

    if (saved.presentation_url) {
      applyViewer(saved.presentation_url);
      statusEl.textContent = "Restored the latest deck from this browser session.";
    }
  } catch (_error) {
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

async function handleSubmit(event) {
  event.preventDefault();

  const payload = {
    prompt: promptField.value.trim(),
    audience: selectedValue("audience"),
    tone: selectedValue("tone"),
    slide_count: Number.parseInt(selectedValue("slide_count"), 10),
  };

  generateButton.disabled = true;
  statusEl.textContent = "Generating deck and building Slidev site...";

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Generation failed.");
    }

    applyViewer(data.presentation_url);
    saveSession({ ...payload, presentation_url: data.presentation_url });
    statusEl.textContent = "Deck ready. The interactive presentation is loaded below.";
  } catch (error) {
    statusEl.textContent = error.message || "Something failed during generation.";
  } finally {
    generateButton.disabled = false;
  }
}

form.addEventListener("submit", handleSubmit);
restoreSession();
