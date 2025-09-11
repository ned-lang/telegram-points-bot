import os
import sqlite3
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler

# === Flask (для Render) ===
app_web = Flask(__name__)

# === Конфигурация ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не задана!")

WEBHOOK_PATH = f"/webhook/{TOKEN}"   # секретный путь
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{WEBHOOK_PATH}"

DB_FILE = "casino.db"

# === База данных ===
def ensure_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 1000
    )""")
    conn.commit()
    conn.close()

# === Команды бота ===
async def start(update: Update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (user_id, 1000))
    conn.commit()
    conn.close()
    await update.message.reply_text("Привет 🎰!\nИспользуй /bet для ставки или /balance для проверки баланса.")

async def bet(update: Update, context):
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
        await update.message.reply_text("Недостаточно средств 💸")
    else:
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

async def balance(update: Update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        await update.message.reply_text(f"💰 Баланс: {row[0]}")
    else:
        await update.message.reply_text("Ты ещё не зарегистрирован. Используй /start.")

# === Telegram Application ===
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("bet", bet))
application.add_handler(CommandHandler("balance", balance))

# === Flask routes ===
@app_web.route("/")
def index():
    return "Бот работает ✅"

@app_web.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

# === Запуск ===
if __name__ == "__main__":
    ensure_db()
    # Устанавливаем webhook при запуске
    import asyncio
    async def set_webhook():
        await application.bot.set_webhook(WEBHOOK_URL)
        print(f"Webhook установлен: {WEBHOOK_URL}")

    asyncio.run(set_webhook())

    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)
