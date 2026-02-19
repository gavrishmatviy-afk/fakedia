import os
import threading
from flask import Flask
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

# ✅ ВПИШИ СЮДИ ID ДВОХ МЕНЕДЖЕРІВ (через кому)
# приклад: ADMIN_IDS = {123456789, 987654321}
ADMIN_IDS = {111111111, 222222222}  # <-- ЗАМІНИ НА РЕАЛЬНІ

# ---- Налаштування (можеш міняти) ----
CARD_NUMBER = "4874 0700 5229 8484"
ANDROID_PRICE = "140₴"
IOS_PRICE = "170₴"
ANDROID_APK_PATH = "files/app_android.apk"
IOS_TEXT_LINK = "👉 @funpapers_bot"
# ------------------------------------

# --- Flask (Render порт) ---
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"[FLASK] Starting on port {port}")
    app_flask.run(host="0.0.0.0", port=port, threaded=True)

# --- Кнопки ---
def platform_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(f"📱 Android – {ANDROID_PRICE}")],
            [KeyboardButton(f"🍎 iOS – {IOS_PRICE}")],
        ],
        resize_keyboard=True,
    )

def paid_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("✅ Я оплатив")],
            [KeyboardButton("❌ Відмінити")],
        ],
        resize_keyboard=True,
    )

def admin_keyboard(buyer_chat_id: int, platform: str):
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Підтвердити", callback_data=f"approve:{buyer_chat_id}:{platform}"),
            InlineKeyboardButton("❌ Відхилити", callback_data=f"reject:{buyer_chat_id}:{platform}"),
        ]]
    )

# --- Команди ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Ласкаво просимо! Виберіть платформу для покупки:",
        reply_markup=platform_keyboard(),
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ваш ID: {update.effective_user.id}")

# --- Вибір платформи ---
async def android_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["platform"] = "android"
    await update.message.reply_text(
        f"📱 Ви обрали Android.\n\n"
        f"💳 Оплата на картку:\n{CARD_NUMBER}\n\n"
        f"💰 Сума: {ANDROID_PRICE}\n\n"
        f"⚠️ Після оплати надішліть свій Telegram-юзернейм.\n\n"
        f"Потім натисніть ✅ Я оплатив або ❌ Відмінити.",
        reply_markup=paid_keyboard(),
    )

async def ios_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["platform"] = "ios"
    await update.message.reply_text(
        f"🍎 Ви обрали iOS.\n\n"
        f"💳 Оплата на картку:\n{CARD_NUMBER}\n\n"
        f"💰 Сума: {IOS_PRICE}\n\n"
        f"⚠️ Після оплати надішліть свій Telegram-юзернейм.\n\n"
        f"Потім натисніть ✅ Я оплатив або ❌ Відмінити.",
        reply_markup=paid_keyboard(),
    )

# --- Натиснув "Я оплатив" ---
async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_IDS or ADMIN_IDS == {111111111, 222222222}:
        await update.message.reply_text("❌ Не налаштовано ADMIN_IDS (впиши ID менеджерів у код).")
        return

    platform = context.user_data.get("platform")
    if platform not in ("android", "ios"):
        await update.message.reply_text("Спочатку обери платформу: /start")
        return

    buyer = update.effective_user
    buyer_chat_id = update.effective_chat.id
    buyer_username = f"@{buyer.username}" if buyer.username else "(без username)"
    price = ANDROID_PRICE if platform == "android" else IOS_PRICE

    await update.message.reply_text(
        "⏳ Очікуйте, йде перевірка оплати...\n\n"
        "Менеджер підтвердить і бот надішле доступ."
    )

    text = (
        "🧾 НОВА ОПЛАТА (очікує підтвердження)\n\n"
        f"Клієнт: {buyer_username}\n"
        f"ID: {buyer.id}\n"
        f"Чат: {buyer_chat_id}\n"
        f"Платформа: {platform}\n"
        f"Сума: {price}\n\n"
        "Натисни кнопку:"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=admin_keyboard(buyer_chat_id, platform),
            )
        except Exception as e:
            print("[ADMIN_SEND_ERROR]", admin_id, e)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("platform", None)
    await update.message.reply_text(
        "❌ Відмінено. Натисни /start щоб почати знову.",
        reply_markup=platform_keyboard(),
    )

# --- Натиснув менеджер ---
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("❌ У вас немає доступу.")
        return

    try:
        action, buyer_chat_id_str, platform = query.data.split(":")
        buyer_chat_id = int(buyer_chat_id_str)
    except Exception:
        await query.edit_message_text("❌ Некоректна кнопка.")
        return

    if action == "reject":
        await query.edit_message_text("❌ Відхилено.")
        await context.bot.send_message(
            chat_id=buyer_chat_id,
            text="❌ Оплату не підтверджено. Зверніться до менеджера або спробуйте ще раз."
        )
        return

    if action == "approve":
        await query.edit_message_text("✅ Підтверджено. Надсилаю…")

        if platform == "android":
            if not os.path.exists(ANDROID_APK_PATH):
                await context.bot.send_message(
                    chat_id=buyer_chat_id,
                    text=f"❌ Файл не знайдено на сервері: {ANDROID_APK_PATH}"
                )
                return
            with open(ANDROID_APK_PATH, "rb") as f:
                await context.bot.send_document(chat_id=buyer_chat_id, document=f)
        else:
            await context.bot.send_message(
                chat_id=buyer_chat_id,
                text=f"🍎 Для iPhone переходь сюди:\n{IOS_TEXT_LINK}"
            )
        return

def run_bot():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Add it in Render Environment Variables.")

    print("[BOOT] TOKEN exists:", bool(TOKEN))
    print("[BOT] Starting Telegram bot polling...")

    app = ApplicationBuilder().token(TOKEN).build()

    # Команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("getid", getid))

    # Reply кнопки
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^📱 Android –"), android_choice))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🍎 iOS –"), ios_choice))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^✅ Я оплатив$"), paid))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^❌ Відмінити$"), cancel))

    # Inline кнопки менеджера
    app.add_handler(CallbackQueryHandler(admin_callback))

    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
