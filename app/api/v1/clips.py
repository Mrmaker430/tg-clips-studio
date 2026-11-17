import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.celery_app import celery_app
from app.core.security import verify_init_data

logger = logging.getLogger(__name__)

router = APIRouter()


class AIClipRequest(BaseModel):
    video_url: str = Field(..., description="YouTube, Twitch, Kick, or direct MP4 URL")


class AIClipResponse(BaseModel):
    status: str
    task_id: str
    message: str


@router.post("/clips", response_model=AIClipResponse)
async def create_ai_clips(
    req: AIClipRequest,
    init_data: dict = Depends(verify_init_data),
):
    chat_id = init_data["user"]["id"]

    try:
        task = celery_app.send_task(
            "worker.tasks.ai_clip_video",
            args=[chat_id, req.video_url],
        )
    except Exception as exc:
        logger.exception("Failed to enqueue Celery task")
        raise HTTPException(
            status_code=503,
            detail=f"Queue unavailable: {exc}. Check REDIS_URL on the web service.",
        )

    return AIClipResponse(
        status="queued",
        task_id=task.id,
        message="🤖 AI is analyzing the video. Clips will appear in this chat shortly.",
    )


@router.get("/health/redis")
async def redis_health():
    """Diagnostic: verify the web service can reach Redis."""
    try:
        celery_app.backend.client.ping()
        return {"redis": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unreachable: {exc}")
