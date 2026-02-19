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
    print(f"[FLASK] Starting on port {port}")
    # threaded=True щоб не блокувалось
    app_flask.run(host="0.0.0.0", port=port, threaded=True)

# --- Telegram bot ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Я працюю!\n\n"
        "Відповідай на повідомлення і пиши:\n"
        "/send_file android\n"
        "або\n"
        "/send_file ios"
    )

async def send_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

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
        path = "files/app_android.apk_
