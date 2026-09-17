import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp

load_dotenv("keys.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
APEX_API_KEY = os.getenv("APEX_API_KEY")

if not BOT_TOKEN or not APEX_API_KEY:
    raise ValueError(f"Error, API keys not found")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_real_map_data(mode: str = "ranked") -> dict | None:
    url = f"https://api.mozambiquehe.re/maprotation?version=2&auth={APEX_API_KEY}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return None
                data = await response.json()

        target_data = data.get(mode)
        if not target_data or not target_data.get("current"):
            # Фолбэк на ranked, если запрошенный режим недоступен
            target_data = data.get("ranked")
            mode = "ranked"

        if not target_data or not target_data.get("current"):
            return None

        current_map = target_data["current"]
        next_map = target_data.get("next", {})

        return {
            "mode_name": "Рейтинговый режим" if mode == "ranked" else "Публичные матчи",
            "current": current_map.get("map", "Неизвестно"),
            "timer": current_map.get("remainingTimer", "00:00:00"),
            "next": next_map.get("map", "Неизвестно")
        }
    except Exception as e:
        logging.error(f"Ошибка запроса к Apex API: {e}")
        return None

def get_maps_keyboard(current_mode: str) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Рейтинг", callback_data="mode_ranked")
    builder.button(text="Паблики", callback_data="mode_battle_royale")
    builder.button(text="Обновить", callback_data=f"refresh_{current_mode}")
    
    builder.adjust(2, 1)
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}!\nВыбери режим для просмотра карт Apex Legends:",
        reply_markup=get_maps_keyboard("ranked")
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "<b>Команды бота:</b>\n"
        "/start - Начать работу\n"
        "/help - Справка\n"
        "/map [ranked/pubs] - Узнать текущую карту"
    )
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("map"))
@dp.message(F.text.startswith("/карта"))
async def cmd_map(message: types.Message):
    text = message.text.lower()
    mode = "battle_royale" if ("паб" in text or "pubs" in text) else "ranked"
    
    map_data = await get_real_map_data(mode)
    if map_data:
        msg = (
            f"🗺 <b>{map_data['mode_name']}</b>\n\n"
            f"Текущая карта: <b>{map_data['current']}</b>\n"
            f"До смены: {map_data['timer']}\n"
            f"Следующая: {map_data['next']}"
        )
        await message.answer(msg, parse_mode="HTML", reply_markup=get_maps_keyboard(mode))
    else:
        await message.answer("⚠️ Не удалось получить данные о картах Apex.")

@dp.callback_query(F.data.startswith("mode_") | F.data.startswith("refresh_"))
async def process_map_callback(callback: types.CallbackQuery):
    action, mode = callback.data.split("_", 1)
    
    map_data = await get_real_map_data(mode)
    
    if map_data:
        text = (
            f"<b>{map_data['mode_name']}</b>\n\n"
            f"Текущая карта: <b>{map_data['current']}</b>\n"
            f"До смены: {map_data['timer']}\n"
            f"Следующая: {map_data['next']}"
        )
    else:
        text = "Не удалось обновить данные."

    try:
        await callback.message.edit_text(
            text, 
            parse_mode="HTML", 
            reply_markup=get_maps_keyboard(mode)
        )
    except Exception:
        pass
    
    await callback.answer("Данные обновлены!" if action == "refresh" else None)

async def main():
    print("Бот Apex Legends успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())