import json
import logging

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

ANALYSIS_PROMPT = """You are a short-form video editor who has grown multiple TikTok and YouTube Shorts accounts to millions of views.

You will receive a timestamped transcript of a long video. Identify moments with the highest viral potential.

A viral moment must:
- Be emotionally charged: funny, intense, surprising, shocking, angry, or deeply relatable.
- Be self-contained: makes sense without the rest of the video.
- Be hook-first: the first 3 seconds contain a line that stops the scroll.
- Be 20–60 seconds long. Cut on natural sentence boundaries, never mid-word.

Return ONLY valid JSON. No markdown fences, no explanation. Use this exact schema:

{
  "clips": [
    {
      "start": 123.4,
      "end": 156.8,
      "title": "Punchy, curiosity-driven title under 70 characters",
      "hook": "3-second on-screen text, under 45 characters, no emojis",
      "score": 87,
      "reason": "One sentence on why this will go viral",
      "emotion": "funny | intense | shocking | relatable | inspiring | interesting"
    }
  ]
}

Rank by score (0-100). Return 3 to {max_clips} clips. If nothing is strong, return {"clips": []}.

Transcript:
{transcript}
"""


def analyze_transcript(segments: list[dict], max_clips: int = 6) -> list[dict]:
    if not segments:
        return []

    transcript_text = "\n".join(
        f"[{s['start']:.1f} - {s['end']:.1f}] {s['text']}" for s in segments
    )

    # Hard cap to fit context window on long VODs
    if len(transcript_text) > 60_000:
        transcript_text = transcript_text[:60_000] + "\n[...truncated...]"

    prompt = ANALYSIS_PROMPT.format(
        transcript=transcript_text, max_clips=max_clips
    )

    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
        timeout=120,
    )

    raw = response.choices[0].message.content or ""
    raw = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"LLM returned non-JSON: {raw[:300]}")
        return []

    clips = data.get("clips", [])
    validated = []

    for clip in clips[:max_clips]:
        try:
            start = max(0.0, float(clip["start"]))
            end = float(clip["end"])
        except (KeyError, TypeError, ValueError):
            continue

        # Snap to Whisper segment boundaries for natural cuts
        start, end = _snap_to_segments(start, end, segments)

        duration = end - start
        if duration < settings.MIN_CLIP_SECONDS or duration > settings.MAX_CLIP_SECONDS:
            logger.warning(f"Rejected clip ({duration:.1f}s): {clip.get('title', '?')}")
            continue

        emotion = str(clip.get("emotion", "interesting")).lower()
        if emotion not in {"funny", "intense", "shocking", "relatable", "inspiring", "interesting"}:
            emotion = "interesting"

        validated.append(
            {
                "start": start,
                "end": end,
                "title": str(clip.get("title", "Untitled"))[:100],
                "hook": str(clip.get("hook", ""))[:60],
                "score": int(clip.get("score", 50)),
                "reason": str(clip.get("reason", ""))[:200],
                "emotion": emotion,
            }
        )

    validated.sort(key=lambda c: c["score"], reverse=True)
    logger.info(f"LLM returned {len(clips)} raw → {len(validated)} valid clips")
    return validated


def _snap_to_segments(
    start: float, end: float, segments: list[dict]
) -> tuple[float, float]:
    """
    Snap [start, end] to the nearest Whisper segment boundaries so clips
    don't cut mid-sentence.
    """
    new_start = start
    for seg in segments:
        if seg["end"] > start:
            new_start = seg["start"]
            break

    new_end = end
    for seg in reversed(segments):
        if seg["start"] < end:
            new_end = seg["end"]
            break

    if new_end <= new_start:
        return start, end  # fallback to original
    return new_start, new_end
