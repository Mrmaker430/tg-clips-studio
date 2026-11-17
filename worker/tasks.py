import logging
import os
import shutil

import requests

from app.config import settings
from app.core.celery_app import celery_app
from worker.utils.ai_analyzer import analyze_transcript
from worker.utils.downloader import download_video
from worker.utils.ffmpeg import build_ass_captions, extract_audio, render_ai_clip
from worker.utils.transcribe import transcribe_video

logger = logging.getLogger(__name__)

CAPTION_MAX_LEN = 1000  # Telegram cap is 1024


@celery_app.task(bind=True, max_retries=0, name="worker.tasks.ai_clip_video")
def ai_clip_video(self, chat_id: int, video_url: str):
    job_id = self.request.id
    work_dir = f"/tmp/{job_id}"
    os.makedirs(work_dir, exist_ok=True)

    input_path = f"{work_dir}/input.mp4"
    audio_path = f"{work_dir}/audio.wav"

    try:
        # 1. Download
        _notify(chat_id, "⬇️ Downloading video…")
        download_video(video_url, input_path)

        # 2. Extract audio
        _notify(chat_id, "🎧 Extracting audio…")
        extract_audio(input_path, audio_path)

        # 3. Transcribe
        _notify(chat_id, "📝 Transcribing (this may take a minute)…")
        segments = transcribe_video(audio_path)
        if not segments:
            _notify(chat_id, "⚠️ No speech detected. Cannot analyze.")
            return {"clips_sent": 0}

        # 4. AI analysis
        _notify(chat_id, "🧠 AI is finding the most viral moments…")
        clips = analyze_transcript(segments, max_clips=settings.MAX_CLIPS)

        if not clips:
            _notify(chat_id, "😕 No strong viral moments found in this video.")
            return {"clips_sent": 0}

        _notify(
            chat_id,
            f"✂️ Found *{len(clips)}* high-potential moments. Rendering…",
        )

        # 5. Render + send each clip
        sent = 0
        for i, clip in enumerate(clips, start=1):
            try:
                ass_path = f"{work_dir}/clip_{i}.ass"
                clip_path = f"{work_dir}/clip_{i}.mp4"

                build_ass_captions(
                    segments=segments,
                    clip_start=clip["start"],
                    clip_end=clip["end"],
                    hook=clip["hook"],
                    output_path=ass_path,
                )
                render_ai_clip(
                    input_path=input_path,
                    output_path=clip_path,
                    start=clip["start"],
                    end=clip["end"],
                    ass_path=ass_path,
                )

                caption = _format_caption(clip, i, len(clips))
                _send_video(chat_id, clip_path, caption)
                sent += 1

                os.remove(ass_path)
                os.remove(clip_path)

            except Exception:
                logger.exception(f"[{job_id}] Failed to render clip {i}")
                continue

        _notify(chat_id, f"✅ Done — {sent}/{len(clips)} clips sent.")
        return {"clips_sent": sent, "clips_found": len(clips)}

    except Exception as exc:
        logger.exception(f"[{job_id}] Job failed")
        _notify(chat_id, f"❌ Clipping failed: {exc}")
        raise
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _format_caption(clip: dict, idx: int, total: int) -> str:
    caption = (
        f"*{clip['title']}*\n\n"
        f"🔥 Score: {clip['score']}/100 · 🎭 {clip['emotion']}\n"
        f"💡 {clip['reason']}\n\n"
        f"_Clip {idx}/{total}_"
    )
    if len(caption) > CAPTION_MAX_LEN:
        caption = caption[: CAPTION_MAX_LEN - 3] + "…"
    return caption


def _notify(chat_id: int, text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=30,
        )
    except Exception:
        logger.exception("Failed to send notification")


def _send_video(chat_id: int, path: str, caption: str):
    with open(path, "rb") as f:
        response = requests.post(
            f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendVideo",
            data={
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "Markdown",
                "supports_streaming": "true",
            },
            files={"video": f},
            timeout=300,
        )
    response.raise_for_status()
