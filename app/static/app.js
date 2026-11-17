const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Every fetch to the backend must include initData
const initData = tg.initData;

async function submitClip(videoUrl, start, end) {
    const res = await fetch("/api/v1/clips", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Telegram-Init-Data": initData
        },
        body: JSON.stringify({
            video_url: videoUrl,
            start_time: start,
            end_time: end
        })
    });
    const data = await res.json();
    tg.showAlert(`Job queued: ${data.task_id}`);
          }
