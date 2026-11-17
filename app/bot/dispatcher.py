from aiogram import Dispatcher

from app.bot.handlers import start

dp = Dispatcher()
dp.include_router(start.router)
