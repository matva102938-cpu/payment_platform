import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from app.database import AsyncSessionLocal
from app.models import Trader
from sqlalchemy.ext.asyncio import AsyncSession

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer("Привет! Введи реквизиты командой /requisites")

@dp.message(Command("requisites"))
async def requisites(msg: Message):
    await msg.answer("Отправь реквизиты одной строкой")

@dp.message()
async def save_requisites(msg: Message):
    async with AsyncSessionLocal() as session:
        trader = Trader(tg_id=str(msg.from_user.id), requisites=msg.text)
        session.add(trader)
        await session.commit()
    await msg.answer("Реквизиты сохранены!")

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_bot())
