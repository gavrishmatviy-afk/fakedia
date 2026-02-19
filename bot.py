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
        path = "files/app_android.apk"  # <- твій файл
        if not os.path.exists(path):
            await update.message.reply_text(f"❌ Файл не знайдено: {path}")
            return

        with open(path, "rb") as file:
            await context.bot.send_document(chat_id=target_chat_id, document=file)

    elif platform == "ios":
        await context.bot.send_message(
            chat_id=target_chat_id,
            text="🍎 Для iPhone переходь сюди:\n👉 @funpapers_bot"
        )
    else:
        await update.message.reply_text("Вкажи тільки: android або ios")

def run_bot():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Add it in Render Environment Variables.")

    print("[BOT] Starting Telegram bot polling...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send_file", send_file))

    app.run_polling()

# --- Запуск обох ---
if __name__ == "__main__":
    print("[BOOT] TOKEN exists:", bool(TOKEN))

    # Flask у окремому потоці
    threading.Thread(target=run_flask, daemon=True).start()

    # Bot в головному потоці
    run_bot()
