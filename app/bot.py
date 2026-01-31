import os
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models import Trader, Order, Ticket, Payout  # если каких-то моделей нет — скажи, подстрою

# -------------------- CONFIG --------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Админы (tg id через запятую): "12345,67890"
ADMIN_IDS = set(x.strip() for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip())

def is_admin(tg_id: int) -> bool:
    return str(tg_id) in ADMIN_IDS

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Простая память для ввода (для 1 реплики Railway норм)
# mode: "requisites" | "ticket" | "payout"
WAITING_INPUT: Dict[int, str] = {}

# -------------------- KEYBOARDS --------------------

def trader_menu_kb(requisites_enabled: bool) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    if requisites_enabled:
        kb.button(text="❌ Отключить Реквизиты", callback_data="t:req_off")
    else:
        kb.button(text="✅ Включить Реквизиты", callback_data="t:req_on")

    kb.button(text="📌 Апелляции", callback_data="t:appeals")
    kb.button(text="🗂 Сделки", callback_data="t:deals")
    kb.button(text="💸 Выплаты", callback_data="t:payouts")
    kb.button(text="📦 Баланс", callback_data="t:balance")
    kb.button(text="✂️ Реквизиты", callback_data="t:requisites")

    kb.adjust(1, 1, 1, 1, 1, 1)
    return kb

def admin_menu_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Пользователи (трейдеры)", callback_data="a:traders")
    kb.button(text="📄 Заявки обычные", callback_data="a:orders")
    kb.button(text="💸 Заявки на выплату", callback_data="a:payouts")
    kb.button(text="💬 Тикеты", callback_data="a:tickets")
    kb.button(text="💱 Курсы", callback_data="a:rates")
    kb.adjust(1, 1, 1, 1, 1)
    return kb

def admin_trader_actions_kb(trader_id: int, enabled: bool) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить реквизиты", callback_data=f"a:trader_edit_req:{trader_id}")
    if enabled:
        kb.button(text="⛔️ Выключить реквизиты", callback_data=f"a:trader_disable:{trader_id}")
    else:
        kb.button(text="✅ Включить реквизиты", callback_data=f"a:trader_enable:{trader_id}")
    kb.button(text="⬅️ Назад", callback_data="a:traders")
    kb.adjust(1, 1, 1)
    return kb

# -------------------- HELPERS (DB) --------------------

async def get_or_create_trader(tg_id: int) -> Trader:
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(Trader).where(Trader.tg_id == str(tg_id)))
        t = r.scalar()
        if t:
            return t
        t = Trader(tg_id=str(tg_id))
        session.add(t)
        await session.commit()
        await session.refresh(t)
        return t

async def set_trader_requisites(tg_id: int, text: str) -> None:
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(Trader).where(Trader.tg_id == str(tg_id)))
        t = r.scalar()
        if not t:
            t = Trader(tg_id=str(tg_id))
            session.add(t)
        t.requisites = text
        await session.commit()

async def set_requisites_enabled(tg_id: int, enabled: bool) -> None:
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(Trader).where(Trader.tg_id == str(tg_id)))
        t = r.scalar()
        if not t:
            t = Trader(tg_id=str(tg_id))
            session.add(t)
        t.requisites_enabled = enabled
        await session.commit()

async def trader_stats_text(t: Trader) -> str:
    # Простейший “курс” и обороты (можно позже заменить на реальный)
    rate = 80.74

    # Оборот за всё время: сумма done по заявкам
    async with AsyncSessionLocal() as session:
        total_q = await session.execute(
            select(func.coalesce(func.sum(Order.amount), 0)).where(
                Order.trader_id == t.id,
                Order.status == "done",
            )
        )
        all_time = float(total_q.scalar() or 0)

    return (
        f"Приветствую {t.tg_id}\n"
        f"🇷🇺 Курс - {rate}\n\n"
        f"💰 Рабочий Депозит - {float(getattr(t, 'deposit_rub', 0) or 0):.2f}RUB\n"
        f"❄️ Заморожено - {float(getattr(t, 'frozen_rur', 0) or 0):.2f}RUR\n"
        f"🧊 Зарезервировано - {float(getattr(t, 'reserved_usdt', 0) or 0):.2f}USDT\n"
        f"💎 Реферальный Баланс - {float(getattr(t, 'referral_usdt', 0) or 0):.2f}USDT\n\n"
        f"⚙️ Оборот за Сегодня - 0.00RUR\n"
        f"⚙️ Оборот за Неделю - 0.00RUR\n"
        f"⚙️ Оборот за Месяц - 0.00RUR\n"
        f"⚙️ Оборот за Все Время - {all_time:.2f}RUR\n"
    )

# -------------------- TRADER: START --------------------

@dp.message(Command("start"))
async def cmd_start(msg: Message):
    t = await get_or_create_trader(msg.from_user.id)
    text = await trader_stats_text(t)
    kb = trader_menu_kb(bool(getattr(t, "requisites_enabled", False))).as_markup()
    await msg.answer(text, reply_markup=kb)

# -------------------- TRADER: CALLBACKS --------------------

@dp.callback_query(F.data.startswith("t:"))
async def trader_callbacks(cb: CallbackQuery):
    t = await get_or_create_trader(cb.from_user.id)
    action = cb.data.split(":", 1)[1]

    if action == "req_on":
        if not (t.requisites or "").strip():
            await cb.answer("Сначала добавь реквизиты", show_alert=True)
            WAITING_INPUT[cb.from_user.id] = "requisites"
            await cb.message.answer("✂️ Отправь реквизиты одним сообщением (банк/карта/ФИО).")
            return
        await set_requisites_enabled(cb.from_user.id, True)
        await cb.answer("Реквизиты включены ✅")

    elif action == "req_off":
        await set_requisites_enabled(cb.from_user.id, False)
        await cb.answer("Реквизиты отключены ❌")

    elif action == "requisites":
        WAITING_INPUT[cb.from_user.id] = "requisites"
        await cb.answer()
        await cb.message.answer("✂️ Отправь реквизиты одним сообщением (банк/карта/ФИО).")
        return

    elif action == "appeals":
        WAITING_INPUT[cb.from_user.id] = "ticket"
        await cb.answer()
        await cb.message.answer("📌 Опиши апелляцию/проблему одним сообщением. Я создам тикет.")
        return

    elif action == "deals":
        # Показать последние 10 заявок трейдера
        async with AsyncSessionLocal() as session:
            r = await session.execute(
                select(Order).where(Order.trader_id == t.id).order_by(Order.id.desc()).limit(10)
            )
            orders = r.scalars().all()

        if not orders:
            await cb.answer()
            await cb.message.answer("🗂 Сделок пока нет.")
            return

        lines = ["🗂 Последние сделки:"]
        for o in orders:
            lines.append(f"#{o.id} | {o.merchant_order_id} | {float(o.amount):.2f} {o.currency} | {o.status}")
        await cb.answer()
        await cb.message.answer("\n".join(lines))
        return

    elif action == "payouts":
        WAITING_INPUT[cb.from_user.id] = "payout"
        await cb.answer()
        await cb.message.answer("💸 Напиши сумму выплаты (числом). Например: 50")
        return

    elif action == "balance":
        await cb.answer()
        await cb.message.answer("📦 Баланс: пока без детализации (добавим следующим шагом).")
        return

    # обновим дашборд после действий
    t2 = await get_or_create_trader(cb.from_user.id)
    text = await trader_stats_text(t2)
    kb = trader_menu_kb(bool(getattr(t2, "requisites_enabled", False))).as_markup()
    await cb.message.edit_text(text, reply_markup=kb)

# -------------------- TRADER: TEXT INPUT --------------------

@dp.message(F.text)
async def trader_text_input(msg: Message):
    mode = WAITING_INPUT.get(msg.from_user.id)
    if not mode:
        return

    text = (msg.text or "").strip()
    if not text:
        return

    if mode == "requisites":
        await set_trader_requisites(msg.from_user.id, text)
        WAITING_INPUT.pop(msg.from_user.id, None)
        await msg.answer("✅ Реквизиты сохранены. Теперь можешь нажать «Включить Реквизиты».")
        return

    if mode == "ticket":
        t = await get_or_create_trader(msg.from_user.id)
        async with AsyncSessionLocal() as session:
            session.add(Ticket(trader_id=t.id, text=text, status="open"))
            await session.commit()
        WAITING_INPUT.pop(msg.from_user.id, None)
        await msg.answer("💬 Тикет создан и отправлен в поддержку.")
        return

    if mode == "payout":
        try:
            amount = float(text.replace(",", "."))
        except ValueError:
            await msg.answer("Напиши число, например: 50")
            return

        t = await get_or_create_trader(msg.from_user.id)
        async with AsyncSessionLocal() as session:
            session.add(Payout(trader_id=t.id, amount=amount, currency="USDT", status="new"))
            await session.commit()
        WAITING_INPUT.pop(msg.from_user.id, None)
        await msg.answer("💸 Заявка на выплату создана. Ожидай подтверждения админа.")
        return

# -------------------- ADMIN --------------------

@dp.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ Нет доступа.")
        return
    await msg.answer("Администрирование бота", reply_markup=admin_menu_kb().as_markup())

@dp.callback_query(F.data.startswith("a:"))
async def admin_callbacks(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return

    parts = cb.data.split(":")
    action = parts[1]

    if action == "traders":
        async with AsyncSessionLocal() as session:
            r = await session.execute(select(Trader).order_by(Trader.id.desc()).limit(20))
            traders = r.scalars().all()

        lines = ["👤 Трейдеры (последние 20):", ""]
        for t in traders:
            lines.append(f"ID {t.id} | tg {t.tg_id} | req {'ON' if t.requisites_enabled else 'OFF'}")
        lines.append("")
        lines.append("Открыть трейдера: /trader <id>")
        await cb.answer()
        await cb.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb().as_markup())
        return

    if action == "orders":
        async with AsyncSessionLocal() as session:
            r = await session.execute(select(Order).order_by(Order.id.desc()).limit(20))
            orders = r.scalars().all()

        lines = ["📄 Заявки (последние 20):", ""]
        for o in orders:
            lines.append(f"#{o.id} | {o.merchant_order_id} | {float(o.amount):.2f} {o.currency} | {o.status}")
        await cb.answer()
        await cb.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb().as_markup())
        return

    if action == "payouts":
        async with AsyncSessionLocal() as session:
            r = await session.execute(select(Payout).order_by(Payout.id.desc()).limit(20))
            payouts = r.scalars().all()

        lines = ["💸 Выплаты (последние 20):", ""]
        for p in payouts:
            lines.append(f"#{p.id} | trader {p.trader_id} | {float(p.amount):.2f} {p.currency} | {p.status}")
        await cb.answer()
        await cb.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb().as_markup())
        return

    if action == "tickets":
        async with AsyncSessionLocal() as session:
            r = await session.execute(select(Ticket).order_by(Ticket.id.desc()).limit(20))
            tickets = r.scalars().all()

        lines = ["💬 Тикеты (последние 20):", ""]
        for t in tickets:
            lines.append(f"#{t.id} | trader {t.trader_id} | {t.status}")
        lines.append("")
        lines.append("Открыть тикет: /ticket <id>")
        await cb.answer()
        await cb.message.edit_text("\n".join(lines), reply_markup=admin_menu_kb().as_markup())
        return

    if action == "rates":
        await cb.answer()
        await cb.message.edit_text("💱 Курсы: пока заглушка. Сделаем редактирование кнопками.", reply_markup=admin_menu_kb().as_markup())
        return

    if action in ("trader_edit_req", "trader_enable", "trader_disable"):
        # формат: a:trader_enable:<id>
        trader_id = int(parts[2])

        async with AsyncSessionLocal() as session:
            r = await session.execute(select(Trader).where(Trader.id == trader_id))
            tr = r.scalar()
            if not tr:
                await cb.answer("Трейдер не найден", show_alert=True)
                return

            if action == "trader_enable":
                tr.requisites_enabled = True
                await session.commit()
                await cb.answer("Включено ✅")
            elif action == "trader_disable":
                tr.requisites_enabled = False
                await session.commit()
                await cb.answer("Выключено ❌")
            elif action == "trader_edit_req":
                await cb.answer("Редактирование сделаем следующим шагом через FSM.", show_alert=True)

        # обновим карточку
        async with AsyncSessionLocal() as session:
            r = await session.execute(select(Trader).where(Trader.id == trader_id))
            tr = r.scalar()

        text = (
            f"👤 Трейдер {tr.id}\n"
            f"tg_id: {tr.tg_id}\n"
            f"requisites_enabled: {tr.requisites_enabled}\n"
            f"requisites: {(tr.requisites or '')[:300]}\n"
        )
        await cb.message.edit_text(text, reply_markup=admin_trader_actions_kb(tr.id, tr.requisites_enabled).as_markup())
        return

    await cb.answer()

@dp.message(Command("trader"))
async def cmd_open_trader(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ Нет доступа.")
        return

    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("Формат: /trader <id>")
        return

    trader_id = int(parts[1])
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(Trader).where(Trader.id == trader_id))
        tr = r.scalar()

    if not tr:
        await msg.answer("Трейдер не найден.")
        return

    text = (
        f"👤 Трейдер {tr.id}\n"
        f"tg_id: {tr.tg_id}\n"
        f"requisites_enabled: {tr.requisites_enabled}\n"
        f"requisites: {(tr.requisites or '')[:300]}\n"
    )
    await msg.answer(text, reply_markup=admin_trader_actions_kb(tr.id, tr.requisites_enabled).as_markup())

@dp.message(Command("ticket"))
async def cmd_open_ticket(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("⛔ Нет доступа.")
        return

    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("Формат: /ticket <id>")
        return

    ticket_id = int(parts[1])
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(Ticket).where(Ticket.id == ticket_id))
        t = r.scalar()

    if not t:
        await msg.answer("Тикет не найден.")
        return

    await msg.answer(f"💬 Тикет #{t.id}\ntrader_id: {t.trader_id}\nstatus: {t.status}\n\n{t.text}")
