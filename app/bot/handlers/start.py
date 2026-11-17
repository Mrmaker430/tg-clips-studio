from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.config import settings

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎬 Open Clip Studio",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]
        ]
    )
    await message.answer(
        "👋 *Welcome to AI Clip Studio!*\n\n"
        "Paste a YouTube / Twitch / Kick link and I'll:\n"
        "• Transcribe the audio\n"
        "• Find the most viral-worthy moments\n"
        "• Write hooks & titles\n"
        "• Cut and send the clips back here\n\n"
        "Tap below to start 👇",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
