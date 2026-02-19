import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# --- Flask сервер (щоб Render бачив порт) ---
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

# --- Telegram бот ---
async def send_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Відповідай на повідомлення та пиши:\n/send_file android або /send_file ios"
        )
        return

    if len(context.args) != 1:
        await update.message.reply_text("Вкажи android або ios")
        return

    platform = context.args[0].lower()
    target_chat_id = update.message.reply_to_message.chat.id

    if platform == "android":
        with open("files/android.apk", "rb") as file:
            await context.bot.send_document(chat_id=target_chat_id, document=file)

    elif platform == "ios":
        await context.bot.send_message(
            chat_id=target_chat_id,
            text="🍎 Для iPhone переходь сюди:\n👉 @funpapers_bot"
        )

def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("send_file", send_file))
    app.run_polling()

# --- Запуск обох ---
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
