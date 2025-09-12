import os
import sys
import logging
import asyncio
import telegram

# Выведем версию PTB в логи Render
print("PTB VERSION:", telegram.__version__)

# Логирование (чтобы видеть что происходит)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = os.environ.get("BOT_TOKEN")  # На Render задай BOT_TOKEN в Settings -> Environment


# ========= Обработчики команд =========
async def start(update, context):
    await update.message.reply_text("Привет! Я работаю 🚀")


async def help_cmd(update, context):
    await update.message.reply_text("Доступные команды: /start /help")


# ========= Универсальный запуск =========
def main():
    version = telegram.__version__
    major = int(version.split(".")[0])

    # ========== PTB v20+ ==========
    if major >= 20:
        from telegram.ext import Application, CommandHandler

        async def run():
            app = Application.builder().token(TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("help", help_cmd))
            print("Bot started with PTB 20+")
            await app.run_polling()

        asyncio.run(run())

    # ========== PTB v13 (старое API) ==========
    else:
        from telegram.ext import Updater, CommandHandler

        def start_old(update, context):
            update.message.reply_text("Привет! Я работаю 🚀 (старое API)")

        def help_old(update, context):
            update.message.reply_text("Доступные команды: /start /help")

        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start_old))
        dp.add_handler(CommandHandler("help", help_old))

        print("Bot started with PTB 13.x")
        updater.start_polling()
        updater.idle()


if __name__ == "__main__":
    if not TOKEN:
        print("Ошибка: переменная окружения BOT_TOKEN не задана!", file=sys.stderr)
        sys.exit(1)
    main()
