from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from app.config import settings
from app.bot.dispatcher import dp
from app.api.v1.clips import router as clips_router

bot = Bot(token=settings.BOT_TOKEN)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set webhook on startup
    await bot.set_webhook(f"{settings.WEBHOOK_BASE_URL}/webhook")
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

# Mount Mini App static frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API routes
app.include_router(clips_router, prefix="/api/v1")

# Telegram webhook endpoint
@app.post("/webhook")
async def telegram_webhook(update: Update):
    await dp.feed_update(bot, update)
    return {"ok": True}
