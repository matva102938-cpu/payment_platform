import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from app.database import AsyncSessionLocal
from app.models import Trader, Order
from sqlalchemy import select, func

BOT_TOKEN = "8413951764:AAFfkVAECaOpXiD-SfMXm1jOWgdfTQnWh_c"


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------------- START ----------------

@dp.message(Command("start"))
async def start_cmd(msg: Message):
    text = (
        "Добро пожаловать!\n\n"
        "/requisites - указать реквизиты\n"
        "/on - начать принимать заявки\n"
        "/off - остановить приём\n"
        "/stats - статистика\n"
    )
    await msg.answer(text)

# ---------------- REQUISITES ----------------

@dp.message(Command("requisites"))
async def set_requisites(msg: Message):
    await msg.answer("Отправь реквизиты одним сообщением")

@dp.message(F.text)
async def save_requisites(msg: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Trader).where(Trader.tg_id == str(msg.from_user.id))
        )
        trader = result.scalar()

        if trader:
            trader.requisites = msg.text
        else:
            trader = Trader(
                tg_id=str(msg.from_user.id),
                requisites=msg.text,
                is_active=0
            )
            session.add(trader)

        await session.commit()

    await msg.answer("Реквизиты сохранены")

# ---------------- ON ----------------

@dp.message(Command("on"))
async def trader_on(msg: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Trader).where(Trader.tg_id == str(msg.from_user.id))
        )
        trader = result.scalar()

        if not trader:
            await msg.answer("Сначала задай реквизиты: /requisites")
            return

        trader.is_active = 1
        await session.commit()

    await msg.answer("Ты активен и принимаешь заявки")

# ---------------- OFF ----------------

@dp.message(Command("off"))
async def trader_off(msg: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Trader).where(Trader.tg_id == str(msg.from_user.id))
        )
        trader = result.scalar()

        if trader:
            trader.is_active = 0
            await session.commit()

    await msg.answer("Ты отключён")

# ---------------- STATS ----------------

@dp.message(Command("stats"))
async def stats(msg: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(Order.id)).where(
                Order.trader_id == msg.from_user.id
            )
        )
        total = result.scalar() or 0

    await msg.answer(f"Всего заявок: {total}")
