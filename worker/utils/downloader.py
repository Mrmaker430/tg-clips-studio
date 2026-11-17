import logging
import subprocess

logger = logging.getLogger(__name__)


def download_video(url: str, output_path: str) -> None:
    """
    Download using yt-dlp. Handles YouTube, Twitch, Kick, TikTok,
    and direct MP4 URLs. Caps at 1080p to save bandwidth and CPU.
    """
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-warnings",
        "--retries", "3",
        "--socket-timeout", "30",
        "-o", output_path,
        url,
    ]
    logger.info(f"yt-dlp: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, timeout=900)
