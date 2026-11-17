from fastapi import Header, HTTPException
from telegram_init_data import parse, validate

from app.config import settings


async def verify_init_data(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
) -> dict:
    try:
        validate(x_telegram_init_data, settings.BOT_TOKEN)
        data = parse(x_telegram_init_data)
        if "user" not in data:
            raise ValueError("initData missing user")
        return data
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid init data: {exc}")
