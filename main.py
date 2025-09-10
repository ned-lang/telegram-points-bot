# main.py
# Telegram bot (polling) + small Flask webserver so Render sees an open port.
# Убедитесь, что в requirements.txt есть python-telegram-bot и Flask.
import os
import time
import secrets
import sqlite3
import asyncio
from threading import Thread

from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ----- Конфигурация -----
DB_FILE = "data.db"
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 5000))  # Render задаёт PORT автоматически

# ----- Простейший веб-сервер Flask (чтобы Render видел порт) -----
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "Bot is running (polling)!"

def run_web():
    # Запускаем Flask на 0.0.0.0:PORT
    # use_reloader=False чтобы не было двойного запуска в некоторых окружениях
    app_web.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

# ----- Простая sqlite БД для очков -----
def ensure_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        points INTEGER DEFAULT 1000,
        created_at INTEGER
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        game TEXT,
        stake INTEGER,
        result TEXT,
        delta INTEGER,
        created_at INTEGER
    )
    """)
    con.commit()
    con.close()

def get_user(user_id, username=""):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("SELECT user_id, username, points FROM users WHERE user_id=?", (user_id,))
    r = cur.fetchone()
    if not r:
        cur.execute("INSERT INTO users(user_id, username, created_at) VALUES(?,?,?)",
                    (user_id, username or "", int(time.time())))
        con.commit()
        cur.execute("SELECT user_id, username, points FROM users WHERE user_id=?", (user_id,))
        r = cur.fetchone()
    con.close()
    return {"user_id": r[0], "username": r[1], "points": r[2]}

def change_points(user_id, delta):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("UPDATE users SET points = points + ? WHERE user_id=?", (delta, user_id))
    con.commit()
    cur.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    pts = cur.fetchone()[0]
    con.close()
    return pts

# ----- Команды бота -----
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    get_user(u.id, u.username or "")
    await update.message.reply_text(
        "Привет! Это развлекательная игра на виртуальные очки.\n"
        "Нет денег и призов реальной ценности. 18+.\n\n"
        "Команды:\n"
        "/balance — показать баланс\n"
        "/bet coin <ставка> <heads|tails> — ставка монетка\n"
        "/leaderboard — топ игроков\n"
        "/rules — правила\n"
    )

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Правила:\n"
        "- Играем только на виртуальные очки (нет денег).\n"
        "- Ставка от 10 до 500 очков.\n"
        "- Не используйте реальные деньги."
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    user = get_user(u.id, u.username or "")
    await update.message.reply_text(f"Ваш баланс: {user['points']} очков")

async def bet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    args = context.args
    if len(args) < 3:
        return await update.message.reply_text("Использование: /bet coin <ставка> <heads|tails>")
    game = args[0].lower()
    try:
        stake = int(args[1])
    except:
        return await update.message.reply_text("Ставка должна быть числом.")
    if stake < 10 or stake > 500:
        return await update.message.reply_text("Ставка должна быть между 10 и 500 очков.")
    user = get_user(u.id, u.username or "")
    if stake > user['points']:
        return await update.message.reply_text("У вас недостаточно очков.")
    if game == "coin":
        pick = args[2].lower()
        if pick not in ("heads", "tails"):
            return await update.message.reply_text("Укажите heads или tails.")
        flip = "heads" if secrets.randbits(1) == 0 else "tails"
        if pick == flip:
            delta = stake
            result = f"win ({flip})"
        else:
            delta = -stake
            result = f"lose ({flip})"
    else:
        return await update.message.reply_text("Доступная игра: coin")

    new_pts = change_points(u.id, delta)
    con = sqlite3.connect(DB_FILE)
    con.execute("INSERT INTO bets(user_id, game, stake, result, delta, created_at) VALUES(?,?,?,?,?,?)",
                (u.id, game, stake, result, delta, int(time.time())))
    con.commit()
    con.close()
    sign = "+" if delta >= 0 else ""
    await update.message.reply_text(f"Результат: {result}. Изменение: {sign}{delta}. Баланс: {new_pts} очков")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    rows = cur.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10").fetchall()
    con.close()
    if not rows:
        return await update.message.reply_text("Топ пуст.")
    text = "Топ игроков:\n" + "\n".join(f"{i+1}. @{(r[0] or 'anon')} — {r[1]} очков" for i,r in enumerate(rows))
    await update.message.reply_text(text)

# ----- Точка входа для бота -----
async def run_bot():
    if not TOKEN:
        print("Ошибка: переменная окружения BOT_TOKEN не задана.")
        return
    ensure_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("bet", bet_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    print("Bot started (polling)...")
    await app.run_polling()

def main():
    # Запускаем Flask в отдельном потоке, чтобы Render видел открытый порт
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()

    # Запускаем телеграм-бота в основном потоке (asyncio)
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
