import telebot, os, json, threading
from flask import Flask
from instagrapi import Client

# --- Render के लिए डमी वेब सर्वर ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🎬 Flix Nova Bot is Live on Render!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- Flix Nova बोट का इंजन ---
TOKEN = "7999904883:AAGffqEBU05YjoHUcc50lWGo2HqMUCRad0w"
bot = telebot.TeleBot(TOKEN)
DB_FILE = "flx_db.json"
TEMP_DIR = "temp_files"

if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

def load_db(): return json.load(open(DB_FILE, 'r')) if os.path.exists(DB_FILE) else {}
def save_db(data): json.dump(data, open(DB_FILE, 'w'))

@bot.message_handler(commands=['start'])
def start(m):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Login ID", "📤 Upload", "🗑️ Delete ID")
    bot.send_message(m.chat.id, "🎬 **Flix Nova Pro Studio (Render Edition)**\nबोट रेडी है, अपना कमांड चुनें:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Login ID")
def login(m):
    msg = bot.send_message(m.chat.id, "भेजें: `username|sessionid`")
    bot.register_next_step_handler(msg, save_acc)

def save_acc(m):
    try:
        u, s = m.text.split('|')
        db = load_db()
        db[u] = s
        save_db(db)
        bot.send_message(m.chat.id, f"✅ @{u} सेव हो गया!")
    except: bot.send_message(m.chat.id, "❌ गलत फॉर्मेट!")

@bot.message_handler(func=lambda m: m.text == "📤 Upload")
def select_acc(m):
    db = load_db()
    if not db: bot.send_message(m.chat.id, "कोई आईडी लॉगिन नहीं है!")
    else:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        for u in db.keys(): markup.add(u)
        msg = bot.send_message(m.chat.id, "किस आईडी से अपलोड करना है?", reply_markup=markup)
        bot.register_next_step_handler(msg, get_video)

def get_video(m):
    user_data = {"username": m.text}
    msg = bot.send_message(m.chat.id, "अब वीडियो (MP4) फाइल भेजें:")
    bot.register_next_step_handler(msg, get_thumb, user_data)

def get_thumb(m, data):
    file_info = bot.get_file(m.video.file_id)
    path = f"{TEMP_DIR}/{data['username']}.mp4"
    with open(path, 'wb') as f: f.write(bot.download_file(file_info.file_path))
    data['video'] = path
    msg = bot.send_message(m.chat.id, "अब कवर फोटो (JPG) भेजें:")
    bot.register_next_step_handler(msg, get_caption, data)

def get_caption(m, data):
    file_info = bot.get_file(m.photo[-1].file_id)
    thumb_path = f"{TEMP_DIR}/{data['username']}.jpg"
    with open(thumb_path, 'wb') as f: f.write(bot.download_file(file_info.file_path))
    data['thumb'] = thumb_path
    msg = bot.send_message(m.chat.id, "अब कैप्शन लिखें:")
    bot.register_next_step_handler(msg, final_upload, data)

def final_upload(m, data):
    bot.send_message(m.chat.id, "🚀 रेंडर सर्वर से अपलोडिंग शुरू हो गई है...")
    db = load_db()
    cl = Client()
    cl.set_device({"app_version": "269.0.0.18.230", "android_version": "29", "manufacturer": "Xiaomi", "device": "Redmi Note 8 Pro", "model": "begonia"})
    try:
        cl.login_by_sessionid(db[data['username']])
        cl.clip_upload(data['video'], m.text, thumbnail=data['thumb'])
        bot.send_message(m.chat.id, "🎉 रील लाइव हो गई!")
        os.remove(data['video']); os.remove(data['thumb'])
    except Exception as e: bot.send_message(m.chat.id, f"❌ एरर: {e}")

@bot.message_handler(func=lambda m: m.text == "🗑️ Delete ID")
def del_list(m):
    db = load_db()
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for u in db.keys(): markup.add(u)
    msg = bot.send_message(m.chat.id, "कौन सी आईडी डिलीट करनी है?", reply_markup=markup)
    bot.register_next_step_handler(msg, do_del)

def do_del(m):
    db = load_db()
    if m.text in db:
        del db[m.text]
        save_db(db)
        bot.send_message(m.chat.id, "🗑️ आईडी डिलीट हो गई!")

if __name__ == "__main__":
    # पहले वेब सर्वर चालू करो (ताकि Render खुश रहे)
    server = threading.Thread(target=run_server)
    server.start()
    # अब अपना असली बोट चालू करो
    bot.infinity_polling()
