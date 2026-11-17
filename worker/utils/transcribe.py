import logging

from faster_whisper import WhisperModel

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton: load the model once per worker process
_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
        _model = WhisperModel(
            settings.WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
        )
    return _model


def transcribe_video(audio_path: str) -> list[dict]:
    """
    Return word-level segments with start/end in seconds.
    Segments are trimmed to natural sentence boundaries by Whisper's VAD.
    """
    model = _get_model()
    segments, _info = model.transcribe(
        audio_path,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    result = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        result.append(
            {
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": text,
            }
        )
    logger.info(f"Transcribed {len(result)} segments")
    return result
