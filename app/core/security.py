import json
import logging

from fastapi import Header, HTTPException
from telegram_init_data import parse, validate

from app.config import settings

logger = logging.getLogger(__name__)


async def verify_init_data(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
) -> dict:
    try:
        validate(x_telegram_init_data, settings.BOT_TOKEN)
        data = parse(x_telegram_init_data)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid init data: {exc}")

    user = data.get("user")
    if isinstance(user, str):
        try:
            user = json.loads(user)
        except json.JSONDecodeError:
            raise HTTPException(status_code=401, detail="Malformed user in initData")

    if not isinstance(user, dict) or "id" not in user:
        raise HTTPException(status_code=401, detail="initData missing user.id")

    data["user"] = user
    return data
