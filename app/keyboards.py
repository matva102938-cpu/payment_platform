from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def trader_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Включить Реквизиты", callback_data="req_on")
    kb.button(text="❌ Отключить Реквизиты", callback_data="req_off")
    kb.button(text="📌 Апелляции", callback_data="appeals")
    kb.button(text="🗂 Сделки", callback_data="deals")
    kb.button(text="💸 Выплаты", callback_data="payouts")
    kb.button(text="📦 Баланс", callback_data="balance")
    kb.button(text="✂️ Реквизиты", callback_data="requisites")
    kb.adjust(1, 1, 1, 1, 1, 1, 1)
    return kb.as_markup()
