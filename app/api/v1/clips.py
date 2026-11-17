from fastapi import APIRouter, Depends
from app.core.security import verify_init_data
from app.core.celery_app import celery_app
from app.models.job import ClipJob

router = APIRouter()

@router.post("/clips")
async def create_clip(
    job: ClipJob,
    init_data: dict = Depends(verify_init_data)
):
    user = init_data["user"]
    # Send task to Celery worker via Redis
    task = celery_app.send_task(
        "worker.tasks.clip_video",
        args=[user["id"], job.video_url, job.start_time, job.end_time]
    )
    return {"status": "queued", "task_id": task.id}
