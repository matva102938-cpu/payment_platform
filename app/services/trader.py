from app.database import AsyncSessionLocal
from app.models import Trader
from sqlalchemy.future import select
from app.bot import bot

async def get_free_trader():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Trader).where(Trader.is_active==1))
        traders = result.scalars().all()
        return traders[0] if traders else None

async def send_order(tg_id, order):
    text = f"""
💸 Новая заявка
Сумма: {order['amount']} {order['currency']}
ID заявки: {order['merchant_order_id']}
"""
    await bot.send_message(tg_id, text)
