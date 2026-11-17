import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, audio_path: str) -> None:
    """Extract mono 16 kHz PCM audio for Whisper."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            audio_path,
        ],
        check=True,
        timeout=600,
    )


def render_ai_clip(
    input_path: str,
    output_path: str,
    start: float,
    end: float,
    ass_path: str,
) -> None:
    """
    Cut [start, end], crop to 9:16, scale to 1080x1920, burn ASS captions.
    Uses -ss before -i for fast seeking.
    """
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", f"{start:.3f}",
            "-to", f"{end:.3f}",
            "-i", input_path,
            "-vf",
            f"crop=ih*9/16:ih,scale=1080:1920,ass={ass_path}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ],
        check=True,
        timeout=600,
    )
    logger.info(f"Rendered: {output_path}")


def build_ass_captions(
    segments: list[dict],
    clip_start: float,
    clip_end: float,
    hook: str,
    output_path: str,
) -> None:
    """
    Build an ASS subtitle file with:
    - A persistent hook overlay for the first 3 seconds
    - 3-word rolling caption chunks synced to the clip window
    """
    # Filter segments inside the clip window and rebase times to 0
    words: list[tuple[float, str]] = []
    for seg in segments:
        if seg["end"] < clip_start or seg["start"] > clip_end:
            continue
        seg_duration = seg["end"] - seg["start"]
        seg_words = seg["text"].split()
        if not seg_words:
            continue
        per_word = seg_duration / len(seg_words)

        for i, w in enumerate(seg_words):
            abs_start = seg["start"] + i * per_word
            rel_start = max(0.0, abs_start - clip_start)
            words.append((rel_start, w))

    # Group into 3-word chunks
    chunks: list[tuple[float, float, str]] = []
    buffer: list[tuple[float, str]] = []
    for w in words:
        buffer.append(w)
        if len(buffer) >= 3:
            start_t = buffer[0][0]
            end_t = buffer[-1][0] + 0.6
            text = " ".join(x[1] for x in buffer)
            chunks.append((start_t, end_t, text))
            buffer = []
    if buffer:
        start_t = buffer[0][0]
        end_t = buffer[-1][0] + 0.6
        text = " ".join(x[1] for x in buffer)
        chunks.append((start_t, end_t, text))

    duration = clip_end - clip_start
    for i, (s, e, _t) in enumerate(chunks):
        if i < len(chunks) - 1:
            next_s = chunks[i + 1][0]
            chunks[i] = (s, min(e, next_s), _t)
        else:
            chunks[i] = (s, min(e, duration), _t)

    # Build ASS file
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
        "Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,Arial,72,&H00FFFFFF,&H00000000,&H80000000,-1,0,1,5,2,2,60,60,220,1",
        "Style: Hook,Arial,80,&H0000FFFF,&H00000000,&H80000000,-1,0,1,6,3,8,60,60,60,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    # Hook: first 3 seconds, bottom of screen
    safe_hook = hook.replace("\n", " ").replace(",", "\\,")
    if safe_hook:
        lines.append(
            f"Dialogue: 1,0:00:00.00,0:00:03.00,Hook,,0,0,0,,{{\\fad(200,200)}}{safe_hook}"
        )

    # Captions
    for s, e, text in chunks:
        safe = text.replace("\n", " ").replace(",", "\\,")
        lines.append(
            f"Dialogue: 0,{_ass_time(s)},{_ass_time(e)},Caption,,0,0,0,,{safe}"
        )

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def _ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"
