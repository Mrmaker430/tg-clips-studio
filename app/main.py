from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.clips import router as clips_router
from app.bot.dispatcher import dp
from app.config import settings

bot = Bot(token=settings.BOT_TOKEN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_url = f"{settings.WEBHOOK_BASE_URL}/webhook"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    yield
    await bot.delete_webhook()


app = FastAPI(title="AI Clip Studio", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clips_router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok"}
