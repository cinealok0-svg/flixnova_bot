import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from instagrapi import Client
import os
import threading
from flask import Flask
import json  # परमानेंट मेमोरी के लिए नया फीचर

# ==========================================
# 1. FLASK WEB SERVER (रेंडर को जगाए रखने के लिए)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home():
    return "Flix Nova Pro Studio is Running 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web_server, daemon=True).start()


# ==========================================
# 2. TELEGRAM BOT & DATABASE SETUP
# ==========================================
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE' # यहाँ अपना टोकन डालें
bot = telebot.TeleBot(TOKEN)

DB_FILE = "user_db.json"

# डेटाबेस से पुराना लॉगिन डेटा लोड करने का फंक्शन
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

# डेटाबेस में नया डेटा सुरक्षित (Save) करने का फंक्शन
def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(user_data, f, indent=4)

# बोट चालू होते ही पुराना डेटा लोड करेगा
user_data = load_db()


# 🔙 कैंसल बटन
def get_cancel_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ प्रक्रिया रद्द करें (Cancel)", callback_data="cancel"))
    return markup

# ==========================================
# 3. MENUS & UI
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    show_main_menu(str(message.chat.id))

def show_main_menu(chat_id, message_id=None):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔐 अकाउंट लॉगिन", callback_data="login"), 
               InlineKeyboardButton("📊 अकाउंट स्टेटस", callback_data="status"))
    markup.row(InlineKeyboardButton("📤 अपलोड मेन्यू (Reel/Post)", callback_data="upload_menu"))
    markup.row(InlineKeyboardButton("🔗 बायो लिंक बदलें", callback_data="change_link"),
               InlineKeyboardButton("🚪 लॉगआउट", callback_data="logout"))
    
    # चेक करना कि यूजर पहले से लॉगिन है या नहीं
    if chat_id in user_data and 'username' in user_data[chat_id]:
        status_msg = f"✅ लॉग-इन एक्टिव: **{user_data[chat_id]['username']}** (अब दोबारा लॉगिन की जरूरत नहीं)"
    else:
        status_msg = "⚠️ कोई अकाउंट लॉगिन नहीं है। कृपया पहले लॉगिन करें।"

    text = f"👑 **Flix Nova Pro Studio [Persistent Edition]** 👑\n\n{status_msg}\n\nअपना कमांड चुनें:"
    
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ==========================================
# 4. BUTTON CLICKS (CALLBACKS)
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = str(call.message.chat.id) # JSON के लिए स्ट्रिंग जरूरी है
    
    if call.data == "cancel":
        if chat_id in user_data: user_data[chat_id]['step'] = 'idle'
        save_db()
        show_main_menu(chat_id, call.message.message_id)
        
    elif call.data == "logout":
        if chat_id in user_data:
            del user_data[chat_id]
            save_db() # डेटाबेस से नाम मिटाएं
        bot.answer_callback_query(call.id, "✅ डेटाबेस से आपका अकाउंट हटा दिया गया है!", show_alert=True)
        show_main_menu(chat_id, call.message.message_id)

    elif call.data == "login":
        if chat_id not in user_data: user_data[chat_id] = {}
        user_data[chat_id]['step'] = 'waiting_for_login'
        save_db()
        bot.edit_message_text("अपना Username and SessionID भेजें:\n`username|sessionid`", chat_id, call.message.message_id, reply_markup=get_cancel_markup(), parse_mode="Markdown")

    elif call.data == "status":
        if chat_id not in user_data or 'sessionid' not in user_data.get(chat_id, {}):
            bot.answer_callback_query(call.id, "⚠️ कोई डेटा नहीं मिला! पहले लॉगिन करें।", show_alert=True)
            return
        msg = bot.edit_message_text("⏳ डेटाबेस से ऑटो-लॉगिन चेक किया जा रहा है...", chat_id, call.message.message_id)
        try:
            cl = Client()
            cl.login_by_sessionid(user_data[chat_id]['sessionid'])
            user_info = cl.user_info(cl.user_id)
            bot.edit_message_text(f"📊 **अकाउंट स्टेटस (Auto-Login):**\n\n👤 **ID:** {user_info.username}\n👥 **Followers:** {user_info.follower_count}\n✅ **कनेक्शन:** परमानेंट सेव्ड और एक्टिव!", chat_id, msg.message_id, parse_mode="Markdown")
            bot.send_message(chat_id, "मुख्य मेन्यू के लिए /start दबाएं।")
        except Exception as e:
            bot.edit_message_text(f"❌ फेल! शायद Session ID एक्सपायर हो गई है। दोबारा लॉगिन करें।\n`{str(e)}`", chat_id, msg.message_id, parse_mode="Markdown")

    elif call.data == "change_link":
        if chat_id not in user_data or 'sessionid' not in user_data.get(chat_id, {}):
            bot.answer_callback_query(call.id, "⚠️ पहले लॉगिन करें!", show_alert=True)
            return
        user_data[chat_id]['step'] = 'waiting_for_link'
        save_db()
        bot.edit_message_text("🔗 अपना नया बायो URL भेजें:", chat_id, call.message.message_id, reply_markup=get_cancel_markup())

    elif call.data == "upload_menu":
        if chat_id not in user_data or 'sessionid' not in user_data.get(chat_id, {}):
            bot.answer_callback_query(call.id, "⚠️ पहले लॉगिन करें!", show_alert=True)
            return
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🎬 Reel", callback_data="up_reel"), 
                   InlineKeyboardButton("📸 Photo Post", callback_data="up_photo"))
        markup.row(InlineKeyboardButton("🌟 Story", callback_data="up_story"))
        markup.row(InlineKeyboardButton("🔙 वापस", callback_data="cancel"))
        bot.edit_message_text("क्या अपलोड करना चाहते हैं?", chat_id, call.message.message_id, reply_markup=markup)

    elif call.data in ["up_reel", "up_photo", "up_story"]:
        user_data[chat_id]['upload_type'] = call.data
        save_db()
        if call.data == "up_reel":
            user_data[chat_id]['step'] = 'waiting_for_video'
            save_db()
            bot.edit_message_text("📥 कृपया अपनी **वीडियो (MP4)** फाइल भेजें:", chat_id, call.message.message_id, reply_markup=get_cancel_markup())
        else:
            user_data[chat_id]['step'] = 'waiting_for_photo_only'
            save_db()
            bot.edit_message_text("📥 कृपया अपनी **फोटो (JPG/PNG)** भेजें:", chat_id, call.message.message_id, reply_markup=get_cancel_markup())

# ==========================================
# 5. SMART MESSAGE HANDLER (Core Engine)
# ==========================================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_all_messages(message):
    chat_id = str(message.chat.id)
    step = user_data.get(chat_id, {}).get('step', 'idle')

    if step == 'waiting_for_login':
        if message.content_type == 'text' and '|' in message.text:
            username, sessionid = message.text.split('|', 1)
            if chat_id not in user_data: user_data[chat_id] = {}
            user_data[chat_id]['username'] = username.strip()
            user_data[chat_id]['sessionid'] = sessionid.strip()
            user_data[chat_id]['step'] = 'idle'
            save_db() # 💾 यहाँ डेटा परमानेंट सेव हो गया!
            bot.reply_to(message, "✅ लॉगिन डिटेल्स डेटाबेस में हमेशा के लिए लॉक हो गईं! अब /start दबाएं।")
        else:
            bot.reply_to(message, "⚠️ गलत फॉर्मेट!", reply_markup=get_cancel_markup())

    elif step == 'waiting_for_link':
        if message.content_type == 'text':
            link = message.text.strip()
            msg = bot.reply_to(message, "⏳ अपडेट हो रहा है...")
            try:
                cl = Client()
                cl.login_by_sessionid(user_data[chat_id]['sessionid'])
                cl.account_edit(external_url=link)
                bot.edit_message_text(f"✅ बायो लिंक `{link}` पर सेट हो गया!", chat_id, msg.message_id, parse_mode="Markdown")
            except Exception as e:
                bot.edit_message_text(f"❌ फेल: `{str(e)}`", chat_id, msg.message_id)
            user_data[chat_id]['step'] = 'idle'
            save_db()

    elif step == 'waiting_for_video':
        if message.content_type == 'video':
            if message.video.file_size > 20971520:
                bot.reply_to(message, "⚠️ फाइल 20MB से बड़ी है! छोटी फाइल दें।", reply_markup=get_cancel_markup())
                return
            msg = bot.reply_to(message, "⏳ वीडियो सर्वर पर डाउनलोड हो रहा है...")
            file_info = bot.get_file(message.video.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            video_path = f"video_{chat_id}.mp4"
            with open(video_path, 'wb') as f: f.write(downloaded_file)
            user_data[chat_id]['video_path'] = video_path
            user_data[chat_id]['step'] = 'waiting_for_cover'
            save_db()
            bot.edit_message_text("✅ वीडियो सेव! अब कवर **फोटो** भेजें:", chat_id, msg.message_id, reply_markup=get_cancel_markup())
        else:
            bot.reply_to(message, "⚠️ कृपया वीडियो भेजें!", reply_markup=get_cancel_markup())

    elif step == 'waiting_for_cover':
        if message.content_type == 'photo':
            msg = bot.reply_to(message, "⏳ कवर सेव हो रहा है...")
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            photo_path = f"thumb_{chat_id}.jpg"
            with open(photo_path, 'wb') as f: f.write(downloaded_file)
            user_data[chat_id]['photo_path'] = photo_path
            user_data[chat_id]['step'] = 'waiting_for_caption'
            save_db()
            bot.edit_message_text("✅ फोटो सेव! अब **कैप्शन** भेजें:", chat_id, msg.message_id, reply_markup=get_cancel_markup())
        else:
            bot.reply_to(message, "⚠️ कृपया फोटो भेजें!", reply_markup=get_cancel_markup())

    elif step == 'waiting_for_photo_only':
        if message.content_type == 'photo':
            msg = bot.reply_to(message, "⏳ फोटो सर्वर पर डाउनलोड हो रही है...")
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            photo_path = f"post_{chat_id}.jpg"
            with open(photo_path, 'wb') as f: f.write(downloaded_file)
            user_data[chat_id]['photo_path'] = photo_path
            
            if user_data[chat_id]['upload_type'] == "up_story":
                user_data[chat_id]['step'] = 'process_upload'
                save_db()
                handle_upload(message, chat_id, "")
            else:
                user_data[chat_id]['step'] = 'waiting_for_caption'
                save_db()
                bot.edit_message_text("✅ फोटो सेव! अब **कैप्शन** भेजें:", chat_id, msg.message_id, reply_markup=get_cancel_markup())
        else:
            bot.reply_to(message, "⚠️ कृपया फोटो भेजें!", reply_markup=get_cancel_markup())

    elif step == 'waiting_for_caption':
        if message.content_type == 'text':
            user_data[chat_id]['step'] = 'process_upload'
            save_db()
            handle_upload(message, chat_id, message.text)
        else:
            bot.reply_to(message, "⚠️ कृपया टेक्स्ट भेजें!", reply_markup=get_cancel_markup())

# --- FINAL INSTAGRAM UPLOAD ENGINE ---
def handle_upload(message, chat_id, caption):
    status_msg = bot.reply_to(message, "🚀 इंस्टाग्राम पर असली अपलोडिंग शुरू... (इसमें समय लग सकता है)")
    up_type = user_data[chat_id].get('upload_type')
    try:
        cl = Client()
        cl.login_by_sessionid(user_data[chat_id]['sessionid'])
        bot.edit_message_text("✅ इंस्टाग्राम कनेक्टेड! पब्लिश हो रहा है...", chat_id, status_msg.message_id)
        
        if up_type == "up_reel":
            cl.clip_upload(path=user_data[chat_id]['video_path'], caption=caption, thumbnail=user_data[chat_id]['photo_path'])
        elif up_type == "up_photo":
            cl.photo_upload(path=user_data[chat_id]['photo_path'], caption=caption)
        elif up_type == "up_story":
            cl.photo_upload_to_story(path=user_data[chat_id]['photo_path'])
            
        bot.edit_message_text("🎉 **मिशन सक्सेसफुल! फाइल इंस्टाग्राम पर लाइव है।**", chat_id, status_msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ **अपलोड फेल!**\nकारण: `{str(e)}`", chat_id, status_msg.message_id, parse_mode="Markdown")
    finally:
        for key in ['video_path', 'photo_path']:
            if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
                os.remove(user_data[chat_id][key])
        user_data[chat_id]['step'] = 'idle'
        save_db()

print("👑 Flix Nova Pro Studio [Persistent Memory Engine] चालू है!")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
                         
