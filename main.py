import os
import sqlite3
import asyncio
from threading import Thread
from flask import Flask
from telegram.ext import Application, CommandHandler

# === Flask для Render ===
app_web = Flask(__name__)

@app_web.route("/")
def index():
    return "Бот работает ✅"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

# === Telegram Bot ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не задана!")

DB_FILE = "casino.db"

def ensure_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 1000
    )""")
    conn.commit()
    conn.close()

# --- обработчики команд ---
async def start(update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (user_id, 1000))
    conn.commit()
    conn.close()
    await update.message.reply_text("Привет! 🎰 Добро пожаловать в казино-бота!\n"
                                    "Используй /bet для ставки или /balance для проверки баланса.")

async def bet(update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        balance = 1000
        cur.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, balance))
    else:
        balance = row[0]

    if balance < 100:
        await update.message.reply_text("Недостаточно средств для ставки 💸")
    else:
        # простая логика: 50% выигрыш/проигрыш
        import random
        if random.choice([True, False]):
            balance += 100
            result = "Ты выиграл +100! 🎉"
        else:
            balance -= 100
            result = "Ты проиграл -100 😢"

        cur.execute("UPDATE users SET balance = ? WHERE user_id = ?", (balance, user_id))
        await update.message.reply_text(f"{result}\nТекущий баланс: {balance}")

    conn.commit()
    conn.close()

async def balance(update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        await update.message.reply_text(f"💰 Твой баланс: {row[0]}")
    else:
        await update.message.reply_text("Ты ещё не зарегистрирован. Введи /start.")

# --- запуск бота ---
async def run_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("balance", balance))

    print("Bot started (polling)...")
    await app.run_polling()

def main():
    ensure_db()

    # Flask в отдельном потоке
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()

    # Telegram-бот в основном потоке
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

if __name__ == "__main__":
    main()
