from app.services.trader import get_free_trader, send_order
from app.database import AsyncSessionLocal
from app.models import Order
from sqlalchemy.ext.asyncio import AsyncSession

async def dispatch_order(order_data):
    trader = await get_free_trader()
    if not trader:
        return False

    # сохраняем заявку в БД
    async with AsyncSessionLocal() as session:
        new_order = Order(
            merchant_order_id=order_data["id"],
            amount=order_data["amount"],
            currency=order_data["currency"],
            trader_id=trader.id
        )
        session.add(new_order)
        await session.commit()

    await send_order(trader.tg_id, order_data)
    return True
