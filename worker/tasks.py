import subprocess, requests, os
from worker.celery_app import celery_app
from app.config import settings

@celery_app.task(bind=True, max_retries=2)
def clip_video(self, chat_id: int, video_url: str, start: str, end: str):
    input_path = f"/tmp/{self.request.id}.mp4"
    output_path = f"/tmp/{self.request.id}_clip.mp4"

    try:
        # 1. Download (yt-dlp for YouTube/Twitch, or requests for direct URLs)
        subprocess.run([
            "yt-dlp", "-f", "mp4", "-o", input_path, video_url
        ], check=True, timeout=300)

        # 2. FFmpeg: cut, crop to 9:16, scale
        subprocess.run([
            "ffmpeg", "-ss", start, "-to", end, "-i", input_path,
            "-vf", "crop=ih*9/16:ih,scale=1080:1920",
            "-c:a", "aac", "-y", output_path
        ], check=True, timeout=300)

        # 3. Send finished clip to Telegram chat
        with open(output_path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendVideo",
                data={"chat_id": chat_id},
                files={"video": f},
                timeout=120
            )
    finally:
        # Cleanup
        for p in [input_path, output_path]:
            if os.path.exists(p):
                os.remove(p)
