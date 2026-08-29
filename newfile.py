import asyncio
import random
import string
import logging
import time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

BOT_TOKEN = "8682855134:AAEW9py89DRL8ycHdtYNC5sNSzZJASeXOBc"
ADMIN_PASSWORD = "050611"
SUPPORT_USERNAME = "fpifik"  # Без символа @

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хранилище данных пользователей
users_db = {}
admins_set = set()
cooldowns = {}  # user_id: last_gen_timestamp

class AdminStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_target_id = State()

def get_or_create_user(user_id: int):
    if user_id not in users_db:
        users_db[user_id] = {
            "is_premium": False,
            "is_blocked": False,
            "favorites": []
        }
    return users_db[user_id]

def generate_username(length: int) -> str:
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))

def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    user_data = get_or_create_user(user_id)
    buttons = [
        [InlineKeyboardButton(text="🎲 Сгенерировать 6-значный 🔤", callback_data="gen_6")],
        [InlineKeyboardButton(text="🎲 Сгенерировать 7-значный 🔤", callback_data="gen_7")],
    ]
    
    if user_data["is_premium"]:
        buttons.append([InlineKeyboardButton(text="⭐ Сгенерировать 5-значный 💎", callback_data="gen_5")])
    else:
        buttons.append([InlineKeyboardButton(text="💎 Купить Премиум подписку ⭐️", callback_data="menu_premium")])
        
    buttons.append([InlineKeyboardButton(text="⭐ Избранное 📁", callback_data="show_favorites")])
    buttons.append([InlineKeyboardButton(text="🛟 Поддержка 👤", url=f"https://t.me/{SUPPORT_USERNAME}")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_premium_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓 1 день — 59 ⭐️", callback_data="buy_prem_1d")],
        [InlineKeyboardButton(text="📅 1 неделя — 150 ⭐️", callback_data="buy_prem_1w")],
        [InlineKeyboardButton(text="📆 1 месяц — 250 ⭐️", callback_data="buy_prem_1m")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])

def get_admin_keyboard(target_id: int) -> InlineKeyboardMarkup:
    target_data = get_or_create_user(target_id)
    prem_btn = InlineKeyboardButton(text="❌ Снять Премиум", callback_data=f"adm_unprem_{target_id}") if target_data["is_premium"] else InlineKeyboardButton(text="⭐ Выдать Премиум", callback_data=f"adm_prem_{target_id}")
    block_btn = InlineKeyboardButton(text="🟢 Разблокировать", callback_data=f"adm_unblock_{target_id}") if target_data["is_blocked"] else InlineKeyboardButton(text="🔴 Заблокировать", callback_data=f"adm_block_{target_id}")
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [prem_btn],
        [block_btn],
        [InlineKeyboardButton(text="🔄 Найти другого юзера 🔍", callback_data="adm_search_again")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    user_data = get_or_create_user(user_id)
    
    if user_data["is_blocked"]:
        await message.answer("⛔️ **Вы заблокированы в системе!** ⛔️", parse_mode="Markdown")
        return

    text = (
        f"👋 Привет, **{first_name}**! ✨\n\n"
        f"🆔 **Ваш ID:** `{user_id}`\n\n"
        f"🎯 Выберите нужный вариант генерации юзернейма ниже 👇"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    text = f"👋 **Главное меню**\n\n🆔 **Ваш ID:** `{user_id}`"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))

@dp.callback_query(F.data.in_({"gen_5", "gen_6", "gen_7"}))
async def handle_manual_gen(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = get_or_create_user(user_id)
    
    if user_data["is_blocked"]:
        return await callback.answer("⛔️ Вы заблокированы!", show_alert=True)

    # Проверка кулдауна 5 секунд
    current_time = time.time()
    last_gen = cooldowns.get(user_id, 0)
    if current_time - last_gen < 5:
        wait_time = int(5 - (current_time - last_gen))
        return await callback.answer(f"⏳ Подождите еще {wait_time} сек. перед повторной генерацией!", show_alert=True)

    if callback.data == "gen_5":
        if not user_data["is_premium"]:
            return await callback.answer("🔒 Требуется Премиум доступ!", show_alert=True)
        length = 5
        icon = "⭐"
    elif callback.data == "gen_6":
        length = 6
        icon = "🎲"
    else:
        length = 7
        icon = "🎲"

    cooldowns[user_id] = current_time
    username = generate_username(length)
    
    fav_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Добавить в избранное 📌", callback_data=f"add_fav_{username}")]
    ])
    
    await callback.message.answer(
        f"{icon} Ваш {length}-значный юзернейм:\n`@{username}` 🔤",
        parse_mode="Markdown",
        reply_markup=fav_keyboard
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("add_fav_"))
async def add_to_favorites(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = get_or_create_user(user_id)
    username = callback.data.split("add_fav_")[1]
    
    if username not in user_data["favorites"]:
        user_data["favorites"].append(username)
        await callback.answer(f"✅ Юзернейм @{username} добавлен в избранное!", show_alert=True)
    else:
        await callback.answer("⚠️ Этот юзернейм уже есть в избранном!", show_alert=True)

@dp.callback_query(F.data == "show_favorites")
async def show_favorites(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = get_or_create_user(user_id)
    
    if not user_data["favorites"]:
        text = "📁 Ваш список избранного пока пуст."
    else:
        fav_list = "\n".join([f"• `@{u}`" for u in user_data["favorites"]])
        text = f"⭐ **Ваши избранные юзернеймы:**\n\n{fav_list}"
        
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_kb)

@dp.callback_query(F.data == "menu_premium")
async def show_premium_menu(callback: CallbackQuery):
    text = (
        "💎 **Премиум доступ** 💎\n\n"
        "Выберите удобный период подписки для доступа к 5-значным юзернеймам:"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_premium_keyboard())

@dp.callback_query(F.data.startswith("buy_prem_"))
async def process_buy_premium(callback: CallbackQuery):
    plan = callback.data.split("_")[2]
    
    plans_info = {
        "1d": ("1 день", 59),
        "1w": ("1 неделя", 150),
        "1m": ("1 месяц", 250)
    }
    
    title_suffix, price_val = plans_info[plan]
    
    prices = [LabeledPrice(label=f"Премиум ({title_suffix}) 💎", amount=price_val)]
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"⭐ Премиум на {title_suffix}",
        description=f"Разблокировка 5-значных юзернеймов на {title_suffix}!",
        payload=f"buy_prem_{plan}",
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    user_id = message.from_user.id
    user_data = get_or_create_user(user_id)
    user_data["is_premium"] = True
    
    await message.answer(
        "🎉 **Оплата прошла успешно!** ⭐️\nВам открыт доступ к 5-значным юзернеймам!",
        reply_markup=get_main_keyboard(user_id),
        parse_mode="Markdown"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in admins_set:
        await state.set_state(AdminStates.waiting_for_target_id)
        await message.answer("🛠 **Панель Администратора** 🛠\nВведите ID пользователя для управления 🔍:")
    else:
        await state.set_state(AdminStates.waiting_for_password)
        await message.answer("🔑 **Введите пароль администратора:**")

@dp.message(AdminStates.waiting_for_password)
async def process_admin_password(message: Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        admins_set.add(message.from_user.id)
        await state.set_state(AdminStates.waiting_for_target_id)
        await message.answer("🔓 **Доступ разрешен!** 👑\nВведите ID пользователя для настройки 🔍:")
    else:
        await state.clear()
        await message.answer("💥 **Неверный пароль!** ❌")

@dp.message(AdminStates.waiting_for_target_id)
async def process_target_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("⚠️ Введите корректный числовой ID 🔢:")
    
    target_id = int(message.text)
    target_data = get_or_create_user(target_id)
    await state.clear()
    
    status_prem = "Да ⭐" if target_data["is_premium"] else "Нет ❌"
    status_block = "Заблокирован 🔴" if target_data["is_blocked"] else "Активен 🟢"
    
    await message.answer(
        f"⚙️ **Управление пользователем** ⚙️\n\n"
        f"👤 **ID:** `{target_id}`\n"
        f"⭐️ **Премиум:** {status_prem}\n"
        f"🛡 **Статус:** {status_block}",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard(target_id)
    )

@dp.callback_query(F.data.startswith("adm_"))
async def handle_admin_actions(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in admins_set:
        return await callback.answer("⛔️ Отказано в доступе!", show_alert=True)
        
    action = callback.data.split("_")[1]
    
    if action == "search":
        await state.set_state(AdminStates.waiting_for_target_id)
        return await callback.message.answer("🔍 Введите ID пользователя:")

    target_id = int(callback.data.split("_")[2])
    target_data = get_or_create_user(target_id)

    if action == "prem":
        target_data["is_premium"] = True
    elif action == "unprem":
        target_data["is_premium"] = False
    elif action == "block":
        target_data["is_blocked"] = True
    elif action == "unblock":
        target_data["is_blocked"] = False

    await callback.message.edit_reply_markup(reply_markup=get_admin_keyboard(target_id))
    await callback.answer("✅ Данные обновлены!")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
