from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import settings

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎬 Open Clip Studio",
            web_app=WebAppInfo(url=settings.WEBAPP_URL)
        )]
    ])
    await message.answer(
        "Welcome! Tap the button below to open the clipping workspace.",
        reply_markup=keyboard
    )
