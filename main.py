import telebot
from telebot import types
import os
import time
import json
import random
from datetime import datetime
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.environ.get("TOKEN")
ADMIN_ID = 8626196183  # Admin Telegram ID
CHANNELS = ["@Yaxshi_Kino_Tv"]  # Majburiy kanallar

bot = telebot.TeleBot(TOKEN)
DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "users": {},
        "movies": {},
        "stats": {"total_users": 0, "total_movies": 0, "total_requests": 0}
    }

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()

# ================= FORCE SUBSCRIBE =================
def check_subscription(user_id):
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False
    return True

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {"joined": time.time(), "requests": 0, "referrals": 0}
        db["stats"]["total_users"] += 1
        save_db(db)

    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for ch in CHANNELS:
            markup.add(types.InlineKeyboardButton("➕ Kanalga a'zo bo'lish", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
        bot.send_message(message.chat.id, "🤖 Botdan foydalanish uchun barcha kanallarga a'zo bo'ling!",
                        parse_mode='Markdown', reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔍 Qidirish", callback_data="search"),
        types.InlineKeyboardButton("🎲 Tasodifiy kino", callback_data="random")
    )
    markup.add(
        types.InlineKeyboardButton("📋 Barcha kinolar", callback_data="all_movies"),
        types.InlineKeyboardButton("📊 Statistika", callback_data="stats")
    )
    markup.add(
        types.InlineKeyboardButton("👤 Profil", callback_data="profile"),
        types.InlineKeyboardButton("🆘 Admin bilan bog'lanish", callback_data="support")
    )

    bot.send_message(message.chat.id,
        f"👋 **Xush kelibsiz, {message.from_user.first_name}!**\n\n"
        "🎬 Kod orqali: `/kino ABC123`\n"
        "Yoki menyudan foydalaning.",
        parse_mode='Markdown', reply_markup=markup)

# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    data = call.data

    if data == "check_sub":
        if check_subscription(user_id):
            bot.answer_callback_query(call.id, "✅ Muvaffaqiyatli!", show_alert=True)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Hali a'zo bo'lmadingiz!", show_alert=True)

    elif data == "search":
        bot.send_message(call.message.chat.id, "🔍 Kino nomini yoki kodini yozing:")

    elif data == "random":
        if db["movies"]:
            code = random.choice(list(db["movies"].keys()))
            send_movie(call.message.chat.id, code)
        else:
            bot.send_message(call.message.chat.id, "Hozircha kinolar yo'q.")

    elif data == "all_movies":
        if not db["movies"]:
            bot.send_message(call.message.chat.id, "Hozircha kinolar yo'q.")
            return
        text = "🎬 **Barcha kinolar:**\n\n"
        for code, movie in list(db["movies"].items())[:20]:
            text += f"• `{code}` — {movie['title']}\n"
        if len(db["movies"]) > 20:
            text += f"\n_... va yana {len(db['movies']) - 20} ta kino_"
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

    elif data == "stats":
        text = f"""📊 **Bot Statistika**

👥 Foydalanuvchilar: {db['stats']['total_users']}
🎬 Kinolar: {len(db['movies'])}
📈 Jami so'rovlar: {db['stats']['total_requests']}
"""
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

    elif data == "profile":
        user = db["users"].get(str(user_id), {})
        text = f"""👤 **Sizning profilingiz**

🆔 ID: `{user_id}`
📅 Qo'shilgan: {datetime.fromtimestamp(user.get('joined', time.time())).strftime('%Y-%m-%d')}
🎥 So'rovlar: {user.get('requests', 0)}
👥 Referallar: {user.get('referrals', 0)}
"""
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

    elif data == "support":
        bot.send_message(call.message.chat.id, "🆘 Admin bilan yozish uchun: @adminusername\nYoki /support xabar")

# ================= KINO =================
def send_movie(chat_id, code):
    movie = db["movies"].get(code.upper())
    if movie:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📥 Yuklab olish", url=movie["link"]))

        caption = f"🎬 **{movie['title']}**\n\n{movie.get('desc', '')}\n\nKod: `{code}`"

        if movie.get("photo"):
            bot.send_photo(chat_id, movie["photo"], caption=caption, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(chat_id, caption, parse_mode='Markdown', reply_markup=markup)

        db["stats"]["total_requests"] += 1
        save_db(db)
    else:
        bot.send_message(chat_id, "❌ Bunday kod topilmadi!")

@bot.message_handler(commands=['kino'])
def get_movie(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        bot.reply_to(message, "❗ Avval kanallarga a'zo bo'ling!")
        return

    try:
        code = message.text.split(maxsplit=1)[1].strip().upper()
        send_movie(message.chat.id, code)
        db["users"][str(user_id)]["requests"] += 1
        save_db(db)
    except:
        bot.reply_to(message, "📝 Ishlatish: `/kino KOD`")

# ================= ADMIN PANEL =================
@bot.message_handler(commands=['addmovie'])
def add_movie(message):
    if message.from_user.id != ADMIN_ID:
        return
    # Format: /addmovie KOD | Title | Link | Photo | Description
    try:
        parts = [x.strip() for x in message.text.split(" | ")]
        code = parts[0].split(maxsplit=1)[1].upper()
        title = parts[1]
        link = parts[2]
        photo = parts[3] if len(parts) > 3 else ""
        desc = parts[4] if len(parts) > 4 else "Yaxshi kino!"

        if "movies" not in db:
            db["movies"] = {}
        db["movies"][code] = {"title": title, "link": link, "photo": photo, "desc": desc}
        db["stats"]["total_movies"] = len(db["movies"])
        save_db(db)
        bot.reply_to(message, f"✅ **{title}** qo'shildi!\nKod: `{code}`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, "❌ Xato!\nTo'g'ri format:\n`/addmovie KOD | Nomi | Link | PhotoLink | Tavsif`")

@bot.message_handler(commands=['addmany'])
def generate_movies(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        count = int(message.text.split()[1])
        for i in range(count):
            code = f"MOV{random.randint(10000,99999)}"
            db["movies"][code] = {
                "title": f"Sample Movie {i+1}",
                "link": "https://example.com/download",
                "photo": "",
                "desc": "Avtomatik qo'shilgan test kino."
            }
        db["stats"]["total_movies"] = len(db["movies"])
        save_db(db)
        bot.reply_to(message, f"✅ {count} ta test kino qo'shildi!")
    except:
        bot.reply_to(message, "Ishlatish: `/addmany 500`")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        text = message.text.split(maxsplit=1)[1]
        sent = 0
        for uid in db["users"]:
            try:
                bot.send_message(int(uid), f"📢 **Admin xabari:**\n\n{text}", parse_mode='Markdown')
                sent += 1
            except:
                pass
        bot.reply_to(message, f"✅ {sent} ta foydalanuvchiga xabar yuborildi!")
    except:
        bot.reply_to(message, "Ishlatish: `/broadcast Xabar matni`")

@bot.message_handler(commands=['support'])
def support(message):
    if len(message.text.split()) > 1:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.reply_to(message, "✅ Admin ga yuborildi!")
    else:
        bot.reply_to(message, "🆘 Xabaringizni yozing: /support Salom, muammo...")

@bot.message_handler(commands=['id'])
def get_id(message):
    bot.reply_to(message, f"🆔 Sizning ID: `{message.from_user.id}`", parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = f"""📊 **Bot Statistika**

👥 Foydalanuvchilar: {db['stats']['total_users']}
🎬 Kinolar: {len(db['movies'])}
📈 Jami so'rovlar: {db['stats']['total_requests']}
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['delmovie'])
def del_movie(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        code = message.text.split(maxsplit=1)[1].strip().upper()
        if code in db["movies"]:
            del db["movies"][code]
            db["stats"]["total_movies"] = len(db["movies"])
            save_db(db)
            bot.reply_to(message, f"✅ `{code}` o'chirildi.", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ `{code}` topilmadi.", parse_mode='Markdown')
    except:
        bot.reply_to(message, "Ishlatish: `/delmovie KOD`")

# ================= TEXT SEARCH =================
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        bot.reply_to(message, "❗ Avval kanallarga a'zo bo'ling!")
        return

    text = message.text.strip().upper()

    # Direct code lookup
    if text in db["movies"]:
        send_movie(message.chat.id, text)
        db["users"][str(user_id)]["requests"] += 1
        save_db(db)
        return

    # Search by title
    results = [(code, m) for code, m in db["movies"].items()
               if message.text.strip().lower() in m["title"].lower()]

    if results:
        if len(results) == 1:
            send_movie(message.chat.id, results[0][0])
        else:
            reply = "🔍 **Topildi:**\n\n"
            for code, m in results[:10]:
                reply += f"• `{code}` — {m['title']}\n"
            reply += "\nKodni yuboring: `/kino KOD`"
            bot.send_message(message.chat.id, reply, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Hech narsa topilmadi. Kodni to'g'ri kiriting.")

# ================= HEALTH SERVER =================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Kinobot ishlayapti!")
    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 0))
    if port == 0:
        return
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        server.serve_forever()
    except OSError:
        pass

Thread(target=run_health_server, daemon=True).start()

# ================= RUN =================
print("🚀 Professional Kinobot ishga tushdi...")
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Xato: {e}")
        print("🔄 5 soniyadan keyin qayta ulanmoqda...")
        time.sleep(5)
