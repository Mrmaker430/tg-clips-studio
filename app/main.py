import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.clips import router as clips_router
from app.bot.dispatcher import dp
from app.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.BOT_TOKEN)


async def _setup_webhook(retries: int = 5) -> None:
    """Set webhook with FloodWait-aware retries. Never raises."""
    url = f"{settings.WEBHOOK_BASE_URL}/webhook"
    for attempt in range(1, retries + 1):
        try:
            await bot.set_webhook(url, drop_pending_updates=False)
            logger.info(f"Webhook set: {url}")
            return
        except TelegramRetryAfter as e:
            logger.warning(
                f"FloodWait {e.retry_after}s setting webhook "
                f"(attempt {attempt}/{retries})"
            )
            await asyncio.sleep(e.retry_after + 1)
        except Exception as e:
            logger.warning(
                f"Webhook setup attempt {attempt}/{retries} failed: {e}"
            )
            await asyncio.sleep(2 * attempt)
    logger.error("Webhook setup failed after all retries — continuing anyway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Never let webhook bootstrap kill the app
    try:
        await _setup_webhook()
    except Exception:
        logger.exception("Webhook bootstrap failed; app will still serve")

    yield

    # Close the aiohttp session cleanly (fixes the "Unclosed connector" warnings)
    try:
        await bot.session.close()
    except Exception:
        pass


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
