from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
import requests, os
from dotenv import load_dotenv

load_dotenv()

# === СТАНИ ===
DEVICE, PASSWORD, FIRMWARE, NETWORK, EXTERNAL, IP_CHECK, ASK_MODEL = range(7)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY")

# === СТАРТ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Почати перевірку 🔍", callback_data="start_check")],
        [InlineKeyboardButton("Перевірити IP 🌐", callback_data="check_ip")],
        [InlineKeyboardButton("Порада 💡", callback_data="tips")],
        [InlineKeyboardButton("Про бота ℹ️", callback_data="about")]
    ]
    await update.message.reply_text(
        "👋 Вітаю! Я — IoT Security Advisor.\n"
        "Оберіть дію нижче:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === ГОЛОВНЕ МЕНЮ ===
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👋 Ви повернулись в головне меню.\n"
        "Оберіть дію нижче:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Почати перевірку 🔍", callback_data="start_check")],
            [InlineKeyboardButton("Перевірити IP 🌐", callback_data="check_ip")],
            [InlineKeyboardButton("Порада 💡", callback_data="tips")],
            [InlineKeyboardButton("Про бота ℹ️", callback_data="about")]
        ])
    )
    return ConversationHandler.END

# === ГОЛОВНЕ МЕНЮ: Обробка ===
async def main_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "start_check":
        await query.edit_message_text("🔎 Вкажіть назву пристрою (наприклад: камера, лампа):")
        return DEVICE
    elif data == "check_ip":
        await query.edit_message_text("🌐 Введіть IP-адресу для перевірки через Shodan:")
        return IP_CHECK
    elif data == "tips":
        keyboard = [
            [InlineKeyboardButton("🛜 Гостьовий Wi-Fi", callback_data="tip_guest_wifi")],
            [InlineKeyboardButton("🔑 Зміна пароля роутера", callback_data="tip_router_password")],
            [InlineKeyboardButton("⚙️ Оновлення прошивки", callback_data="tip_firmware_update")],
            [InlineKeyboardButton("🔙 Повернутись в головне меню", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "❓ З чим потрібна допомога?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EXTERNAL
    elif data == "about":
        await query.edit_message_text(
            "🤖 *IoT Security Advisor Bot*\n"
            "Перевіряє пристрої IoT та IP через Shodan, допомагає покращити кібербезпеку.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

# === ОПИТУВАННЯ: ЕТАПИ ===
async def ask_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_name = update.message.text
    context.user_data["device"] = device_name
    keyboard = [
        [InlineKeyboardButton("Так", callback_data="pw_yes"),
         InlineKeyboardButton("Ні", callback_data="pw_no")]
    ]
    await update.message.reply_text(
        f"🔐 Чи змінено стандартний пароль для {device_name}?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PASSWORD

async def password_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["password_secure"] = (query.data == "pw_yes")

    keyboard = [
        [InlineKeyboardButton("Так", callback_data="fw_yes"),
         InlineKeyboardButton("Ні", callback_data="fw_no")]
    ]
    await query.edit_message_text(
        "⚙️ Чи оновлена прошивка пристрою?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return FIRMWARE

async def firmware_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["firmware_updated"] = (query.data == "fw_yes")

    keyboard = [
        [InlineKeyboardButton("Так", callback_data="net_yes"),
         InlineKeyboardButton("Ні", callback_data="net_no")]
    ]
    await query.edit_message_text(
        "🌐 Чи підключено пристрій до окремої (гістьової) мережі Wi-Fi?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return NETWORK

async def network_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["isolated_network"] = (query.data == "net_yes")

    keyboard = [
        [InlineKeyboardButton("Так", callback_data="ext_yes"),
         InlineKeyboardButton("Ні", callback_data="ext_no")]
    ]
    await query.edit_message_text(
        "🌍 Чи має пристрій відкритий доступ з Інтернету?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return EXTERNAL

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["external_access"] = (query.data == "ext_yes")

    score = sum([
        context.user_data.get("password_secure", False),
        context.user_data.get("firmware_updated", False),
        context.user_data.get("isolated_network", False),
        not context.user_data.get("external_access", True)
    ])
    result = ["❌ Небезпечний", "⚠️ Сумнівний", "✅ Безпечний"][min(score, 2)]

    text = f"🔒 Рівень безпеки пристрою: *{result}*"
    keyboard = [
        [InlineKeyboardButton("🛜 Гостьовий Wi-Fi", callback_data="tip_guest_wifi")],
        [InlineKeyboardButton("🔑 Зміна пароля роутера", callback_data="tip_router_password")],
        [InlineKeyboardButton("⚙️ Оновлення прошивки", callback_data="tip_firmware_update")],
        [InlineKeyboardButton("🔙 Повернутись в головне меню", callback_data="main_menu")]
    ]
    await query.edit_message_text(
        text=text + "\n\n📋 Оберіть тему, щоб отримати рекомендацію:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return EXTERNAL

# === РЕКОМЕНДАЦІЇ ===
async def tips_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["tip_type"] = query.data

    tips = {
        "tip_guest_wifi": (
            "🛜 *Гостьовий Wi-Fi*\nСтворіть окрему гостьову мережу для IoT-пристроїв.\n"
            "Це зменшить ризик доступу до головної мережі у разі злому пристрою."
        ),
        "tip_router_password": (
            "🔑 *Пароль роутера*\nЗмініть стандартний пароль для входу в налаштування роутера.\n"
            "Використовуйте складний пароль і вимкніть віддалене адміністрування, якщо воно не потрібне."
        ),
        "tip_firmware_update": (
            "⚙️ *Оновлення прошивки*\nРегулярно перевіряйте оновлення у налаштуваннях пристрою або на сайті виробника.\n"
            "Оновлення усувають вразливості та покращують безпеку."
        )
    }

    keyboard = [
        [InlineKeyboardButton("🔍 Як це зробити на моєму пристрої?", callback_data="ask_model")],
        [InlineKeyboardButton("🔙 Повернутись в головне меню", callback_data="main_menu")]
    ]

    await query.edit_message_text(
        text=tips.get(query.data, "Невідома порада."),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === ЗАПИТ МОДЕЛІ ===
async def ask_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🧠 Вкажіть модель вашого пристрою (наприклад: TP-Link Archer C6 або Xiaomi Smart Camera):"
    )
    return ASK_MODEL

# === GOOGLE ПОШУК ===
async def search_google(update: Update, context: ContextTypes.DEFAULT_TYPE):
    model = update.message.text.strip()
    tip_type = context.user_data.get("tip_type", "")
    if tip_type == "tip_router_password":
        query_text = f"як змінити стандартний пароль на роутері {model}"
    elif tip_type == "tip_firmware_update":
        query_text = f"як оновити прошивку на {model}"
    elif tip_type == "tip_guest_wifi":
        query_text = f"як налаштувати гостьовий Wi-Fi на {model}"
    else:
        query_text = f"налаштування безпеки для {model}"
    url = f"https://www.google.com/search?q={query_text.replace(' ', '+')} -и"
    await update.message.reply_text(f"🔎 [Результати пошуку у Google]({url})", parse_mode="Markdown")

    # Автоматично повертаємо до головного меню
    keyboard = [
        [InlineKeyboardButton("Головне меню 🏠", callback_data="main_menu")]
    ]
    await update.message.reply_text(
        "📋 Ви можете повернутись у головне меню:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

# === SHODAN ===
async def shodan_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ip = update.message.text.strip()
    url = f"https://api.shodan.io/shodan/host/{ip}?key={SHODAN_API_KEY}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            vulns = data.get("vulns", [])
            await update.message.reply_text(
                f"✅ IP {ip} знайдено.\n"
                f"Організація: {data.get('org','Невідомо')}\n"
                f"Відкритих портів: {len(data.get('ports', []))}\n"
                f"Вразливостей: {len(vulns)}"
            )
        else:
            await update.message.reply_text("❌ Не вдалося знайти інформацію про IP.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка: {e}")
    return ConversationHandler.END

# === MAIN ===
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(main_menu_entry, pattern="^(start_check|check_ip|tips|about)$")],
        states={
            DEVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_password)],
            PASSWORD: [CallbackQueryHandler(password_choice, pattern="^pw_")],
            FIRMWARE: [CallbackQueryHandler(firmware_choice, pattern="^fw_")],
            NETWORK: [CallbackQueryHandler(network_choice, pattern="^net_")],
            EXTERNAL: [
                CallbackQueryHandler(summary, pattern="^ext_"),
                CallbackQueryHandler(tips_handler, pattern="^tip_"),
                CallbackQueryHandler(ask_model, pattern="^ask_model$"),
                CallbackQueryHandler(main_menu, pattern="^main_menu$")
            ],
            ASK_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_google)],
            IP_CHECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, shodan_lookup)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
