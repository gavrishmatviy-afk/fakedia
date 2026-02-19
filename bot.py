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

# --- Менеджер (тільки цей username має право підтверджувати) ---
ADMIN_USERNAME = "arielend"  # без @

# ---- Налаштування (можеш міняти) ----
CARD_NUMBER = "4874 0700 5229 8484"
ANDROID_PRICE = "140₴"
IOS_PRICE = "170₴"
ANDROID_APK_PATH = "files/app_android.apk"
IOS_TEXT_LINK = "👉 @funpapers_bot"
# ------------------------------------


# --- Flask сервер (щоб Render бачив порт) ---
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


# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Ласкаво просимо! Виберіть платформу для покупки:",
        reply_markup=platform_keyboard(),
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def android_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["platform"] = "android"
    await update.message.reply_text(
        f"📱 Ви обрали Android.\n\n"
        f"💳 Оплата на картку:\n{CARD_NUMBER}\n\n"
        f"💰 Сума: {ANDROID_PRICE}\n\n"
        f"⚠️ ВАЖЛИВО: Після оплати обов'язково надішліть у чат свій Telegram-юзернейм, "
        f"щоб ми могли підтвердити оплату.\n\n"
        f"Після цього натисніть кнопку ✅ Я оплатив, або ❌ Відмінити.",
        reply_markup=paid_keyboard(),
    )

async def ios_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["platform"] = "ios"
    await update.message.reply_text(
        f"🍎 Ви обрали iOS.\n\n"
        f"💳 Оплата на картку:\n{CARD_NUMBER}\n\n"
        f"💰 Сума: {IOS_PRICE}\n\n"
        f"⚠️ ВАЖЛИВО: Після оплати обов'язково надішліть у чат свій Telegram-юзернейм, "
        f"щоб ми могли підтвердити оплату.\n\n"
        f"Після цього натисніть кнопку ✅ Я оплатив, або ❌ Відмінити.",
        reply_markup=paid_keyboard(),
    )

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    platform = context.user_data.get("platform")
    if platform not in ("android", "ios"):
        await update.message.reply_text("Спочатку обери платформу: /start")
        return

    buyer = update.effective_user
    buyer_chat_id = update.effective_chat.id

    await update.message.reply_text(
        "⏳ Очікуйте, йде перевірка оплати...\n\n"
        "Менеджер перевірить оплату і після підтвердження надішле файл."
    )

    price = ANDROID_PRICE if platform == "android" else IOS_PRICE
    buyer_username = f"@{buyer.username}" if buyer.username else "(без username)"

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Підтвердити", callback_data=f"approve:{buyer_chat_id}:{platform}"),
            InlineKeyboardButton("❌ Відхилити", callback_data=f"reject:{buyer_chat_id}:{platform}"),
        ]]
    )

    # Надсилаємо менеджеру (по username)
    await context.bot.send_message(
        chat_id=f"@{ADMIN_USERNAME}",
        text=(
            "🧾 НОВА ОПЛАТА (очікує підтвердження)\n\n"
            f"Клієнт: {buyer_username}\n"
            f"ID: {buyer.id}\n"
            f"Чат: {buyer_chat_id}\n"
            f"Платформа: {platform}\n"
            f"Сума: {price}\n\n"
            "Натисни кнопку:"
        ),
        reply_markup=keyboard
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("platform", None)
    await update.message.reply_text(
        "❌ Відмінено.\nЯкщо захочеш — натисни /start або /buy.",
        reply_markup=platform_keyboard(),
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Доступ тільки менеджеру
    if (query.from_user.username or "").lower() != ADMIN_USERNAME.lower():
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
            text="❌ Оплату не підтверджено. Напиши менеджеру або спробуй ще раз."
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


# (опційно) твоя команда /send_file лишилась для ручної відправки у відповідь
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
        if not os.path.exists(ANDROID_APK_PATH):
            await update.message.reply_text(f"❌ Файл не знайдено: {ANDROID_APK_PATH}")
            return

        with open(ANDROID_APK_PATH, "rb") as file:
            await context.bot.send_document(chat_id=target_chat_id, document=file)

    elif platform == "ios":
        await context.bot.send_message(
            chat_id=target_chat_id,
            text=f"🍎 Для iPhone переходь сюди:\n{IOS_TEXT_LINK}",
        )
    else:
        await update.message.reply_text("Вкажи android або ios")


def run_bot():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Add it in Render Environment Variables.")

    print("[BOOT] TOKEN exists:", bool(TOKEN))
    print("[BOT] Starting Telegram bot polling...")

    app = ApplicationBuilder().token(TOKEN).build()

    # Команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("send_file", send_file))

    # Reply-кнопки
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^📱 Android –"), android_choice))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^🍎 iOS –"), ios_choice))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^✅ Я оплатив$"), paid))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^❌ Відмінити$"), cancel))

    # Inline-кнопки менеджера
    app.add_handler(CallbackQueryHandler(admin_callback))

    app.run_polling()


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
