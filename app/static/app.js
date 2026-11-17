const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const initData = tg.initData;
const submitBtn = document.getElementById("submitBtn");
const statusEl = document.getElementById("status");

function showStatus(msg, kind = "info") {
  statusEl.textContent = msg;
  statusEl.className = `status ${kind}`;
  statusEl.classList.remove("hidden");
}

async function readError(res) {
  const text = await res.text();
  try {
    const json = JSON.parse(text);
    return json.detail || json.message || text;
  } catch {
    return text.slice(0, 300);
  }
}

submitBtn.addEventListener("click", async () => {
  const videoUrl = document.getElementById("videoUrl").value.trim();
  if (!videoUrl) {
    showStatus("Paste a video URL first.", "error");
    return;
  }

  submitBtn.disabled = true;
  showStatus("⏳ Sending to AI…", "info");

  try {
    const res = await fetch("/api/v1/clips", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": initData,
      },
      body: JSON.stringify({ video_url: videoUrl }),
    });

    if (!res.ok) {
      const msg = await readError(res);
      throw new Error(`HTTP ${res.status}: ${msg}`);
    }

    const data = await res.json();
    showStatus(`✅ ${data.message}`, "success");
    tg.HapticFeedback.notificationOccurred("success");
    setTimeout(() => tg.close(), 1500);
  } catch (err) {
    showStatus(`❌ ${err.message}`, "error");
    tg.HapticFeedback.notificationOccurred("error");
    submitBtn.disabled = false;
  }
});
