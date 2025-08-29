import telebot

# توکن ربات (بهتره از متغیر محیطی بخونی، ولی برای سادگی مستقیم نوشتیم)
TOKEN = "8172850383:AAEYBN-y0zD7SGdlexHC1QPVzVO5HzX86Kk"
bot = telebot.TeleBot(TOKEN)

# دیکشنری برای ذخیره‌سازی نام کاربران
user_names = {}

# هندلر دستور /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id in user_names:
        # اگر قبلاً اسم داده
        bot.reply_to(message, f"سلام {user_names[user_id]}! خوش آمدی 👋")
    else:
        # اولین بارشه → ازش اسم بخواه
        bot.reply_to(message, "سلام! خوش آمدی 🌹\nلطفاً اسم خودت رو بگو:")
        # علامت می‌زنیم که منتظر اسم هستیم
        user_names[user_id] = None  

# هندلر همه پیام‌های متنی
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    # اگر کاربر هنوز اسم نداده
    if user_id in user_names and user_names[user_id] is None:
        user_names[user_id] = message.text  # اسم ذخیره میشه
        bot.reply_to(message, f"خیلی ممنون {user_names[user_id]}! اسمت ذخیره شد ✅")
    elif user_id in user_names:
        bot.reply_to(message, f"{user_names[user_id]} جان خوش آمدی دوباره 👋")
    else:
        # کاربر هنوز /start نزده
        bot.reply_to(message, "لطفاً اول /start رو بزن 🙂")

print("ربات در حال اجرا است...")
bot.infinity_polling()
