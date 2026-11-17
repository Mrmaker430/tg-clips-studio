from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.celery_app import celery_app
from app.core.security import verify_init_data

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

    task = celery_app.send_task(
        "worker.tasks.ai_clip_video",
        args=[chat_id, req.video_url],
    )

    return AIClipResponse(
        status="queued",
        task_id=task.id,
        message="🤖 AI is analyzing the video. Clips will appear in this chat shortly.",
    )
