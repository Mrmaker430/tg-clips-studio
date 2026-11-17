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
      const err = await res.json();
      throw new Error(err.detail || "Request failed");
    }

    const data = await res.json();
    showStatus(`✅ ${data.message}`, "success");
    tg.HapticFeedback.notificationOccurred("success");

    // Close the Mini App—results will arrive in the chat
    setTimeout(() => tg.close(), 1500);
  } catch (err) {
    showStatus(`❌ ${err.message}`, "error");
    tg.HapticFeedback.notificationOccurred("error");
    submitBtn.disabled = false;
  }
});
