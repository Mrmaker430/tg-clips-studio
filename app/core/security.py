from fastapi import Header, HTTPException
from telegram_init_data import validate, parse
from app.config import settings

async def verify_init_data(x_telegram_init_data: str = Header(...)) -> dict:
    try:
        validate(x_telegram_init_data, settings.BOT_TOKEN)
        return parse(x_telegram_init_data)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid init data: {e}")
