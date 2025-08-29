import os
from dotenv import load_dotenv
import telebot
from telebot import types
import json
from gtts import gTTS

# بارگذاری متغیرهای محیطی
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ توکن در فایل .env پیدا نشد.")

bot = telebot.TeleBot(TOKEN)

# مسیر پوشه فایل‌های صوتی
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# مسیر فایل ذخیره پیشرفت کاربران
PROGRESS_FILE = "user_progress.json"
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        user_data = json.load(f)
else:
    user_data = {}

# خواندن تمرین‌ها از JSON
with open("exercises.json", "r", encoding="utf-8") as f:
    exercises = json.load(f)

# مدیریت فایل‌های صوتی
existing_audio = set(os.listdir(AUDIO_DIR))
current_audio_files = set()

for exercise in exercises:
    audio_file = f"{exercise['id']}.mp3"
    current_audio_files.add(audio_file)
    audio_path = os.path.join(AUDIO_DIR, audio_file)
    if not os.path.exists(audio_path):
        tts = gTTS(text=exercise['correct_sentence'], lang='en')
        tts.save(audio_path)
        print(f"✔ ساخته شد: {audio_file}")

# حذف فایل‌های صوتی که دیگر جایی در JSON ندارند
for file in existing_audio - current_audio_files:
    os.remove(os.path.join(AUDIO_DIR, file))
    print(f"🗑 حذف شد: {file}")

# ذخیره پیشرفت کاربران
def save_progress():
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

# ساخت کیبورد دینامیک
def get_inline_keyboard(words, selected_words, show_check=False, correctness=None):
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    free_words = [w for w in words if w not in selected_words]
    if free_words:
        row = [types.InlineKeyboardButton(w, callback_data=f"select:{w}") for w in free_words]
        keyboard.row(*row)

    if selected_words:
        row = []
        for idx, w in enumerate(selected_words):
            label = w
            if correctness:
                label = f"{w} ✅" if correctness[idx] else f"{w} ❌"
            row.append(types.InlineKeyboardButton(label, callback_data=f"remove:{idx}"))
        keyboard.row(*row)

    if show_check and len(selected_words) == len(words):
        keyboard.row(types.InlineKeyboardButton("بررسی جمله ✅", callback_data="check"))

    return keyboard

# شروع
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = str(message.chat.id)
    if chat_id not in user_data:
        user_data[chat_id] = {"exercise_index": 0, "selected": []}

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("شروع تمرین جدید از ابتدا", callback_data="start_over"),
        types.InlineKeyboardButton("ادامه تمرین قبلی", callback_data="continue")
    )
    bot.send_message(
        message.chat.id,
        "سلام! لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data in ["start_over", "continue"])
def handle_start_choice(call):
    chat_id = str(call.message.chat.id)
    if call.data == "start_over":
        user_data[chat_id] = {"exercise_index": 0, "selected": []}
    save_progress()
    bot.answer_callback_query(call.id)
    send_exercise(chat_id)

# ارسال تمرین
def send_exercise(chat_id):
    idx = user_data[chat_id]["exercise_index"]
    if idx >= len(exercises):
        bot.send_message(chat_id, "🎉 شما همه تمرین‌ها را کامل کردید! 👏")
        return

    exercise = exercises[idx]
    user_data[chat_id]["selected"] = []
    bot.send_message(
        chat_id,
        f"تمرین {idx+1}: کلمات را به ترتیب درست انتخاب کنید.",
        reply_markup=get_inline_keyboard(exercise["words"], [], show_check=True)
    )

# مدیریت دکمه‌ها
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = str(call.message.chat.id)
    if chat_id not in user_data:
        user_data[chat_id] = {"exercise_index": 0, "selected": []}

    data = call.data
    idx = user_data[chat_id]["exercise_index"]
    state = user_data[chat_id]
    exercise = exercises[idx]

    if data.startswith("select:"):
        word = data.split(":")[1]
        state["selected"].append(word)
    elif data.startswith("remove:"):
        word_idx = int(data.split(":")[1])
        state["selected"].pop(word_idx)
    elif data == "check":
        user_sentence = " ".join(state["selected"])
        correct_sentence = exercise["correct_sentence"]

        if user_sentence.lower() == correct_sentence.lower():
            bot.answer_callback_query(call.id, "✅ عالی! جمله درست است.")
            bot.send_message(
                call.message.chat.id,
                f"✅ جمله شما درست است:\n\n{correct_sentence}\n\nترجمه فارسی:\n{exercise['translation']}"
            )

            # پخش فایل صوتی آماده
            audio_file = os.path.join(AUDIO_DIR, f"{exercise['id']}.mp3")
            with open(audio_file, 'rb') as audio:
                bot.send_audio(call.message.chat.id, audio)

            # بروزرسانی پیشرفت
            state["exercise_index"] += 1
            save_progress()
            send_exercise(chat_id)
            return
        else:
            correct_words = correct_sentence.split()
            correctness = [i < len(correct_words) and w.lower() == correct_words[i].lower() for i, w in enumerate(state["selected"])]

            bot.answer_callback_query(call.id, "❌ جمله اشتباه است. رنگ کلمات را بررسی کنید.")
            bot.edit_message_reply_markup(
                chat_id,
                call.message.message_id,
                reply_markup=get_inline_keyboard(exercise["words"], state["selected"], show_check=True, correctness=correctness)
            )
            return

    bot.edit_message_reply_markup(
        chat_id,
        call.message.message_id,
        reply_markup=get_inline_keyboard(exercise["words"], state["selected"], show_check=True)
    )

# اجرای ربات
if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.polling(none_stop=True)
