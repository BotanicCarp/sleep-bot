import time
import json
import os
import random
import asyncio
import schedule
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8048123065:AAEFBvf9A85q7eJPGdnFwxp9H_-ypQSgyu0"

# Добавь сюда свой chat_id (как админ, кто видит статистику)
ADMIN_IDS = {8342597247}  # <-- ЗАМЕНИ на свой id (int)

DATA_FILE = "sleep_times.json"

chat_id_saved = None

sleep_messages = [
    "🌙 Время спать",
    "🛌 Уже 23:00, пора отдыхать",
    "✨ Ложись спать, завтра новый день"
]

dream_messages = [
    "Сладких снов 🌙",
    "Спокойной ночи 😊",
    "Пусть тебе приснятся хорошие сны ✨"
]

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"times": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def record_sleep_time():
    data = load_data()
    now = datetime.now().strftime("%H:%M")
    data["times"].append(now)
    save_data(data)
    return now

def compute_stats():
    data = load_data()
    times = data.get("times", [])
    if not times:
        return "Пока нет данных."

    # переводим HH:MM в минуты
    mins = []
    for t in times:
        h, m = map(int, t.split(":"))
        mins.append(h * 60 + m)

    avg = int(sum(mins) / len(mins))
    avg_h = avg // 60
    avg_m = avg % 60
    avg_str = f"{avg_h:02d}:{avg_m:02d}"

    last7 = times[-7:]
    last7_str = ", ".join(last7)

    return f"Среднее время сна: {avg_str}\nПоследние 7: {last7_str}"

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    global chat_id_saved
    chat_id_saved = update.effective_chat.id
    await update.message.reply_text(
        "Буду напоминать в 23:00.\n"
        "Кнопки: «Я иду спать» и «Ещё 10 минут»."
    )

async def send_sleep_message(app):
    global chat_id_saved
    if not chat_id_saved:
        return

    text = random.choice(sleep_messages)
    keyboard = [
        [
            InlineKeyboardButton("Я иду спать 😴", callback_data="sleep_now"),
            InlineKeyboardButton("Ещё 10 минут ⏰", callback_data="plus_10")
        ]
    ]
    await app.bot.send_message(
        chat_id=chat_id_saved,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "sleep_now":
        t = record_sleep_time()
        text = random.choice(dream_messages) + f"\n(Отмечено: {t})"
        await query.message.reply_text(text)

        # отправить статистику админу
        stats = compute_stats()
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"Отметка сна: {t}\n\n{stats}"
            )

    elif data == "plus_10":
        await query.message.reply_text("Хорошо, напомню через 10 минут ⏰")

        # через 10 минут прислать снова
        context.job_queue.run_once(
            callback=remind_again,
            when=600,  # 600 сек = 10 мин
            data=query.message.chat_id
        )

async def remind_again(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data
    keyboard = [
        [
            InlineKeyboardButton("Я иду спать 😴", callback_data="sleep_now"),
            InlineKeyboardButton("Ещё 10 минут ⏰", callback_data="plus_10")
        ]
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text="⏰ Прошло 10 минут. Пора спать",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stats_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    # доступно только админу
    if update.effective_chat.id in ADMIN_IDS:
        await update.message.reply_text(compute_stats())
    else:
        await update.message.reply_text("Нет доступа.")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats_cmd))
app.add_handler(CallbackQueryHandler(button_handler))

print("Бот работает...")

# планировщик
import threading

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(30)

def job():
    asyncio.run(send_sleep_message(app))

schedule.every().day.at("23:00").do(job)

threading.Thread(target=run_schedule).start()

app.run_polling()

