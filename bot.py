import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from traffic import (
    get_city_traffic_score,
    get_mock_traffic_data,
    format_traffic_message
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@probka_uz")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",")]
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
USE_MOCK = not bool(YANDEX_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def format_report(user, text, location=None):
    time_str = datetime.now().strftime("%H:%M")
    name = user.full_name or "Номаълум"
    loc_text = ""
    if location:
        loc_text = f"\n📍 <a href='https://yandex.uz/maps/?ll={location.longitude},{location.latitude}&z=16'>Харитада кўриш</a>"
    return (
        f"🚨 <b>Янги хабар</b> | {time_str}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{text}"
        f"{loc_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {name} хабар берди\n"
        f"📲 @probka_uz"
    )

async def send_to_channel(text):
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML", disable_web_page_preview=True)
        return True
    except Exception as e:
        logger.error(f"Каналга юборишда хато: {e}")
        return False

def main_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🚗 Тирбандлик"), types.KeyboardButton(text="💥 Авария")],
            [types.KeyboardButton(text="⚠️ Хавфли ҳолат"), types.KeyboardButton(text="🚧 Йўл ёпилиши")],
            [types.KeyboardButton(text="📊 Ҳозирги ҳолат")],
            [types.KeyboardButton(text="📍 Локация юбориш", request_location=True)],
        ],
        resize_keyboard=True
    )

def admin_keyboard(user_id):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Тасдиқлаш", callback_data=f"approve_{user_id}"),
            types.InlineKeyboardButton(text="❌ Рад этиш", callback_data=f"reject_{user_id}"),
        ]]
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 <b>Probka.uz ботига хуш келибсиз!</b>\n\n"
        "Ўзбекистон йўлларидаги тирбандлик, авария ва хавфли ҳолатлар ҳақида хабар беринг.\n\n"
        "📊 <b>Ҳозирги ҳолат</b> — Тошкент йўллари жорий тирбандлиги",
        parse_mode="HTML", reply_markup=main_keyboard()
    )

@dp.message(Command("traffic"))
@dp.message(F.text == "📊 Ҳозирги ҳолат")
async def cmd_traffic(message: types.Message):
    wait_msg = await message.answer("⏳ Маълумот олиняпти...")
    if USE_MOCK:
        data = get_mock_traffic_data()
        text = format_traffic_message(data)
        text += "\n\n<i>⚠️ Тест режими — реал маълумот эмас</i>"
    else:
        data = await get_city_traffic_score(YANDEX_API_KEY)
        text = format_traffic_message(data)
    await wait_msg.delete()
    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())

user_states = {}
pending_reports = {}

REPORT_TYPES = {
    "🚗 Тирбандлик": "🚗 Тирбандлик",
    "💥 Авария": "💥 Авария",
    "⚠️ Хавфли ҳолат": "⚠️ Хавфли ҳолат",
    "🚧 Йўл ёпилиши": "🚧 Йўл ёпилиши",
}

@dp.message(F.text.in_(REPORT_TYPES.keys()))
async def report_type_selected(message: types.Message):
    user_states[message.from_user.id] = {"type": REPORT_TYPES[message.text]}
    await message.answer(
        f"{REPORT_TYPES[message.text]} ҳақида хабар юбораяпсиз.\n\n"
        f"📝 Қисқача ёзинг:\n<i>Мисол: Чилонзор, 14-мактаб олдида машина тўхтаб қолган</i>",
        parse_mode="HTML"
    )

@dp.message(F.location)
async def location_received(message: types.Message):
    user_id = message.from_user.id
    if user_id in pending_reports:
        pending_reports[user_id]["location"] = message.location
        await message.answer("📍 Локация қабул қилинди!")
        await process_and_send(message, user_id)
    else:
        await message.answer("Аввал хабар турини танланг.")

@dp.message(F.text & ~F.text.startswith("/"))
async def text_received(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_states:
        await message.answer("Илтимос, аввал хабар турини танланг 👇", reply_markup=main_keyboard())
        return
    full_text = f"{user_states[user_id]['type']}\n\n{message.text}"
    pending_reports[user_id] = {"text": full_text, "user": message.from_user, "location": None}
    await message.answer(
        "📍 Локация қўшмоқчимисиз? (ихтиёрий)\n\n"
        "Қўшиш учун <b>📍 Локация юбориш</b> тугмасини босинг\n"
        "Ёки <b>/send</b> — локациясиз юбориш учун",
        parse_mode="HTML"
    )

@dp.message(Command("send"))
async def force_send(message: types.Message):
    if message.from_user.id in pending_reports:
        await process_and_send(message, message.from_user.id)
    else:
        await message.answer("Юбориш учун хабар йўқ.")

async def process_and_send(message, user_id):
    report = pending_reports.get(user_id)
    if not report:
        return
    formatted = format_report(report["user"], report["text"], report.get("location"))
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"📬 <b>Янги хабар (модерация)</b>\n\n{formatted}",
                parse_mode="HTML",
                reply_markup=admin_keyboard(user_id)
            )
        except Exception as e:
            logger.error(f"Админга юборишда хато: {e}")
    del pending_reports[user_id]
    user_states.pop(user_id, None)
    await message.answer("✅ Хабарингиз модераторга юборилди. Раҳмат!", reply_markup=main_keyboard())

@dp.callback_query(F.data.startswith("approve_"))
async def approve_report(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Рухсат йўқ!")
        return
    original_text = callback.message.text.replace("📬 Янги хабар (модерация)\n\n", "")
    success = await send_to_channel(original_text)
    if success:
        await callback.message.edit_text(callback.message.text + "\n\n✅ <b>ТАСДИҚЛАНДИ</b>", parse_mode="HTML")
        await callback.answer("Каналга юборилди! ✅")
    else:
        await callback.answer("Хато юз берди ❌")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_report(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Рухсат йўқ!")
        return
    await callback.message.edit_text(callback.message.text + "\n\n❌ <b>РАД ЭТИЛДИ</b>", parse_mode="HTML")
    await callback.answer("Рад этилди ❌")

async def auto_traffic_update():
    scheduled = {7: 30, 8: 30, 17: 30, 18: 30}
    while True:
        now = datetime.now()
        if now.hour in scheduled and now.minute == scheduled[now.hour]:
            logger.info(f"Автоматик хабар: {now.strftime('%H:%M')}")
            data = get_mock_traffic_data() if USE_MOCK else await get_city_traffic_score(YANDEX_API_KEY)
            if data:
                await send_to_channel(format_traffic_message(data))
            await asyncio.sleep(61)
        else:
            await asyncio.sleep(30)

async def main():
    logger.info(f"Бот ишга тушмоқда... Режим: {'ТЕСТ' if USE_MOCK else 'РЕАЛ'}")
    asyncio.create_task(auto_traffic_update())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
