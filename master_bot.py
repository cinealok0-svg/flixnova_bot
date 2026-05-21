import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from instagrapi import Client
import yt_dlp
import os
import threading
from flask import Flask
import json
import time

# ==========================================
# 1. आपका BOT TOKEN (यहाँ सेट कर दिया गया है)
# ==========================================
TOKEN = '8529193805:AAHDMK2V5MRnRUJk7REQiFzN43_XdsE1w4E'
bot = telebot.TeleBot(TOKEN)


# ==========================================
# 2. ANTI-SLEEP WEB SERVER (Render के लिए)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home():
    return "Flix Nova Supreme Bot is Running 24/7!"

def run_server():
    try:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    except:
        pass

threading.Thread(target=run_server, daemon=True).start()


# ==========================================
# 3. DATABASE SETUP (परमानेंट मेमोरी)
# ==========================================
DB_FILE = "user_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_db():
    with open(DB_FILE, "w") as f: json.dump(user_data, f, indent=4)

user_data = load_db()

def get_cancel_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ प्रक्रिया रद्द करें (Cancel)", callback_data="cancel"))
    return markup


# ==========================================
# 4. PROFESSIONAL UI MAIN MENU
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    show_main_menu(str(message.chat.id))

def show_main_menu(chat_id, message_id=None):
    if chat_id not in user_data:
        user_data[chat_id] = {"step": "idle", "active_account": "", "accounts": {}}
    
    markup = InlineKeyboardMarkup()
    
    # 1. अकाउंट मैनेजमेंट
    markup.row(InlineKeyboardButton("🔐 नई ID लॉगिन करें", callback_data="login"),
               InlineKeyboardButton("📊 सभी IDs / स्विच करें", callback_data="view_accounts"))
    
    # 2. अपलोड मेन्यू (लिंक + फाइल दोनों)
    markup.row(InlineKeyboardButton("🚀 Upload via YouTube Link", callback_data="upload_link"))
    markup.row(InlineKeyboardButton("📥 Upload via Telegram File", callback_data="upload_file_menu"))
    
    # 3. एक्स्ट्रा फीचर्स
    markup.row(InlineKeyboardButton("🔗 बायो लिंक बदलें", callback_data="change_link"),
               InlineKeyboardButton("🗑️ ID डिलीट करें", callback_data="delete_menu"))

    active = user_data[chat_id].get("active_account", "")
    total_accounts = len(user_data[chat_id].get("accounts", {}))
    
    if active:
        status_text = f"🎯 **एक्टिव ID:** `@{active}`\n👥 **टोटल लॉगिन:** {total_accounts}"
    else:
        status_text = f"⚠️ **स्टेटस:** कोई भी आईडी एक्टिव नहीं है!\n👥 **टोटल लॉगिन:** {total_accounts}"
        
    text = f"⚙️ **Flix Nova Pro Studio**\n\n{status_text}\n\nनीचे दिए गए बटन से बोट को कंट्रोल करें:"
    
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


# ==========================================
# 5. BUTTON CLICKS HANDLING (CALLBACKS)
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = str(call.message.chat.id)
    
    if call.data == "cancel":
        user_data[chat_id]['step'] = 'idle'
        save_db()
        show_main_menu(chat_id, call.message.message_id)
        
    elif call.data == "login":
        user_data[chat_id]['step'] = 'waiting_for_login'
        save_db()
        bot.edit_message_text("अपना Username और SessionID भेजें:\n`username|sessionid`", chat_id, call.message.message_id, reply_markup=get_cancel_markup(), parse_mode="Markdown")
        
    elif call.data == "view_accounts":
        accounts = user_data[chat_id].get("accounts", {})
        if not accounts:
            bot.answer_callback_query(call.id, "⚠️ कोई आईडी लॉगिन नहीं है!", show_alert=True)
            return
        markup = InlineKeyboardMarkup()
        for acc in accounts.keys():
            prefix = "✅ " if acc == user_data[chat_id]["active_account"] else "👤 "
            markup.add(InlineKeyboardButton(f"{prefix}@{acc}", callback_data=f"switch_{acc}"))
        markup.add(InlineKeyboardButton("🔙 वापस", callback_data="cancel"))
        bot.edit_message_text("📊 **एक्टिव करने के लिए ID पर क्लिक करें:**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("switch_"):
        target_acc = call.data.split("switch_")[1]
        user_data[chat_id]["active_account"] = target_acc
        save_db()
        bot.answer_callback_query(call.id, f"🎯 @{target_acc} एक्टिव है!", show_alert=True)
        show_main_menu(chat_id, call.message.message_id)

    elif call.data == "delete_menu":
        accounts = user_data[chat_id].get("accounts", {})
        if not accounts:
            bot.answer_callback_query(call.id, "⚠️ कोई आईडी नहीं है!", show_alert=True)
            return
        markup = InlineKeyboardMarkup()
        for acc in accounts.keys():
            markup.add(InlineKeyboardButton(f"❌ @{acc} डिलीट करें", callback_data=f"del_{acc}"))
        markup.add(InlineKeyboardButton("🔙 वापस", callback_data="cancel"))
        bot.edit_message_text("🗑️ **कौन सी ID डिलीट करनी है?**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("del_"):
        target_acc = call.data.split("del_")[1]
        if target_acc in user_data[chat_id]["accounts"]:
            del user_data[chat_id]["accounts"][target_acc]
            if user_data[chat_id]["active_account"] == target_acc:
                user_data[chat_id]["active_account"] = list(user_data[chat_id]["accounts"].keys())[0] if user_data[chat_id]["accounts"] else ""
            save_db()
            bot.answer_callback_query(call.id, f"🗑️ @{target_acc} डिलीट हो गई!", show_alert=True)
        show_main_menu(chat_id, call.message.message_id)

    elif call.data == "upload_link":
        if not user_data[chat_id].get("active_account"):
            bot.answer_callback_query(call.id, "⚠️ पहले ID सेलेक्ट करें!", show_alert=True)
            return
        user_data[chat_id]['step'] = 'waiting_for_yt_link'
        save_db()
        bot.edit_message_text(f"🔗 **[@{user_data[chat_id]['active_account']}]** के लिए YouTube का लिंक भेजें:", chat_id, call.message.message_id, reply_markup=get_cancel_markup(), parse_mode="Markdown")

    elif call.data == "change_link":
        if not user_data[chat_id].get("active_account"):
            bot.answer_callback_query(call.id, "⚠️ पहले ID सेलेक्ट करें!", show_alert=True)
            return
        user_data[chat_id]['step'] = 'waiting_for_bio_link'
        save_db()
        bot.edit_message_text(f"🔗 **[@{user_data[chat_id]['active_account']}]** के बायो के लिए नया लिंक भेजें:", chat_id, call.message.message_id, reply_markup=get_cancel_markup(), parse_mode="Markdown")

    elif call.data == "upload_file_menu":
        if not user_data[chat_id].get("active_account"):
            bot.answer_callback_query(call.id, "⚠️ पहले ID सेलेक्ट करें!", show_alert=True)
            return
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🎬 Reel (Video)", callback_data="up_reel"), 
                   InlineKeyboardButton("📸 Photo Post", callback_data="up_photo"))
        markup.row(InlineKeyboardButton("🔙 वापस", callback_data="cancel"))
        bot.edit_message_text("क्या अपलोड करना चाहते हैं?", chat_id, call.message.message_id, reply_markup=markup)

    elif call.data in ["up_reel", "up_photo"]:
        user_data[chat_id]['upload_type'] = call.data
        if call.data == "up_reel":
            user_data[chat_id]['step'] = 'waiting_for_video'
            bot.edit_message_text("📥 कृपया अपनी **वीडियो (MP4)** फाइल भेजें (Max 20MB):", chat_id, call.message.message_id, reply_markup=get_cancel_markup(), parse_mode="Markdown")
        else:
            user_data[chat_id]['step'] = 'waiting_for_photo_only'
            bot.edit_message_text("📥 कृपया अपनी **फोटो (JPG/PNG)** भेजें:", chat_id, call.message.message_id, reply_markup=get_cancel_markup(), parse_mode="Markdown")
        save_db()


# ==========================================
# 6. MESSAGE HANDLER (ऑल-इन-वन अपलोडर इंजन)
# ==========================================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_all_messages(message):
    chat_id = str(message.chat.id)
    step = user_data.get(chat_id, {}).get('step', 'idle')

    if step == 'waiting_for_login':
        if message.content_type == 'text' and '|' in message.text:
            u, s = message.text.split('|', 1)
            username = u.strip()
            sessionid = s.strip()
            
            if chat_id not in user_data:
                user_data[chat_id] = {"step": "idle", "active_account": "", "accounts": {}}
            
            user_data[chat_id]['accounts'][username] = sessionid
            user_data[chat_id]['active_account'] = username
            user_data[chat_id]['step'] = 'idle'
            save_db()
            bot.reply_to(message, f"✅ **सफलतापूर्वक लॉग-इन!**\nID `@{username}` सेव हो गई है। मेन्यू के लिए /start दबाएं।", parse_mode="Markdown")
        else:
            bot.reply_to(message, "⚠️ गलत फॉर्मेट! कृपया `username|sessionid` में भेजें।", reply_markup=get_cancel_markup())

    elif step == 'waiting_for_bio_link' and message.content_type == 'text':
        new_link = message.text.strip()
        active_acc = user_data[chat_id]['active_account']
        msg = bot.reply_to(message, f"⏳ @{active_acc} का बायो अपडेट हो रहा है...")
        try:
            cl = Client()
            cl.login_by_sessionid(user_data[chat_id]['accounts'][active_acc])
            cl.account_edit(external_url=new_link)
            bot.edit_message_text(f"✅ **Success!**\n@{active_acc} का बायो लिंक `{new_link}` हो गया है!", chat_id, msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.edit_message_text(f"❌ एरर: `{str(e)}`", chat_id, msg.message_id, parse_mode="Markdown")
        user_data[chat_id]['step'] = 'idle'
        save_db()

    elif step == 'waiting_for_yt_link' and message.content_type == 'text':
        link = message.text.strip()
        active_acc = user_data[chat_id]['active_account']
        msg = bot.reply_to(message, f"⏳ **Processing Link...**\nDownloading for @{active_acc}...")
        try:
            video_path = f"video_{chat_id}.mp4"
            ydl_opts = {'outtmpl': video_path, 'format': 'best', 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                title = info.get('title', 'New Reel')
            
            bot.edit_message_text(f"🚀 **Uploading to Instagram...**", chat_id, msg.message_id, parse_mode="Markdown")
            cl = Client()
            cl.login_by_sessionid(user_data[chat_id]['accounts'][active_acc])
            cl.clip_upload(path=video_path, caption=f"{title}\n\n#reels")
            bot.edit_message_text("✅ **Success! Reel Uploaded**", chat_id, msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.edit_message_text(f"❌ **Error:** `{str(e)}`", chat_id, msg.message_id, parse_mode="Markdown")
        finally:
            if os.path.exists(f"video_{chat_id}.mp4"): os.remove(f"video_{chat_id}.mp4")
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
            bot.edit_message_text("✅ वीडियो सेव! अब कवर **फोटो** भेजें:", chat_id, msg.message_id, reply_markup=get_cancel_markup(), parse_mode="Markdown")
        else:
            bot.reply_to(message, "⚠️ कृपया वीडियो फाइल (MP4) भेजें!", reply_markup=get_cancel_markup())

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
            bot.edit_message_text("✅ फोटो सेव! अब अपना **कैप्शन** भेजें:", chat_id, msg.message_id, reply_markup=get_cancel_markup(), parse_mode="Markdown")
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
            user_data[chat_id]['step'] = 'waiting_for_caption'
            save_db()
            bot.edit_message_text("✅ फोटो सेव! अब अपना **कैप्शन** भेजें:", chat_id, msg.message_id, reply_markup=get_cancel_markup(), parse_mode="Markdown")
        else:
            bot.reply_to(message, "⚠️ कृपया फोटो भेजें!", reply_markup=get_cancel_markup())

    elif step == 'waiting_for_caption' and message.content_type == 'text':
        caption = message.text
        active_acc = user_data[chat_id]['active_account']
        status_msg = bot.reply_to(message, f"🚀 @{active_acc} पर अपलोडिंग शुरू... (इसमें समय लग सकता है)")
        up_type = user_data[chat_id].get('upload_type')
        try:
            cl = Client()
            cl.login_by_sessionid(user_data[chat_id]['accounts'][active_acc])
            
            if up_type == "up_reel":
                cl.clip_upload(path=user_data[chat_id]['video_path'], caption=caption, thumbnail=user_data[chat_id]['photo_path'])
            elif up_type == "up_photo":
                cl.photo_upload(path=user_data[chat_id]['photo_path'], caption=caption)
                
            bot.edit_message_text("🎉 **मिशन सक्सेसफुल! फाइल इंस्टाग्राम पर लाइव है।**", chat_id, status_msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.edit_message_text(f"❌ **अपलोड फेल!**\nकारण: `{str(e)}`", chat_id, status_msg.message_id, parse_mode="Markdown")
        finally:
            for key in ['video_path', 'photo_path']:
                if key in user_data[chat_id] and os.path.exists(user_data[chat_id][key]):
                    os.remove(user_data[chat_id][key])
            user_data[chat_id]['step'] = 'idle'
            save_db()

# ==========================================
# 7. ANTI-CRASH BOT START ENGINE
# ==========================================
print("👑 Supreme Bot चालू हो रहा है...")
try:
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
except Exception as e:
    print("=====================================================")
    print(f"❌ BOT CRASHED: {e}")
    print("=====================================================")
    while True:
        time.sleep(60)
