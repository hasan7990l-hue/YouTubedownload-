import os
import re
import asyncio
import threading
import streamlit as st
from telethon import TelegramClient, events, Button
from telethon.sessions import MemorySession
from yt_dlp import YoutubeDL

# --- إعداد واجهة Streamlit الرسومية ---
st.set_page_config(page_title="خادم بوت تحميل يوتيوب", page_icon="🎵", layout="centered")

st.markdown("<h1 style='text-align: center;'>🎵 خادم بوت تحميل صوتيات وفيديوهات يوتيوب</h1>", unsafe_allow_html=True)
st.success("🟢 السيرفر يعمل الآن بنجاح تامة!")
st.info("⚡️ تم تحديث إعدادات التمويه لتخطي حظر يوتيوب وسيرفرات الحماية.")

# --- البيانات الخاصة بك ---
API_ID = 27485469
API_HASH = "544459a0701b32741254945b08daebfe"
BOT_TOKEN = "8180650384:AAG6ZhD7YxQk1nHOL7xhOVCbqQ_8XvOadQ0"
DEV_ID = 8456056018
SOURCE_CHANNEL = "@lb2_c"

# دالة مطورة للتحقق من الروابط واستخراج آيدي الفيديو بشكل صحيح
def extract_video_id(url):
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# --- دالة تشغيل البوت الأساسية ---
def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    bot = TelegramClient(MemorySession(), API_ID, API_HASH).start(bot_token=BOT_TOKEN)

    # --- حدث بدء التشغيل /start ---
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        first_name = event.sender.first_name or "المستخدم"
        welcome_text = (
            f"🙋‍♂️ أهلاً بك يا {first_name} في بوت تحميل يوتيوب السريع والمحدث!\n\n"
            f"📥 أرسل رابط الفيديو (تأكد أن الرابط كامل وليس مقطوعاً) وسأقوم بمعالجته فوراً.\n\n"
            f"قناة السورس: {SOURCE_CHANNEL}"
        )
        buttons = [
            [Button.url("قناة السورس", f"https://t.me/{SOURCE_CHANNEL.replace('@', '')}")],
            [Button.url("المطور", f"tg://user?id={DEV_ID}")]
        ]
        await event.respond(welcome_text, buttons=buttons)

    # --- حدث استقبال الروابط وتحميلها ---
    @bot.on(events.NewMessage)
    async def download_handler(event):
        if event.text.startswith('/'):
            return

        url = event.text.strip()
        video_id = extract_video_id(url)
        
        if not video_id:
            return # يتجاهل الرسائل التي لا تحتوي على رابط يوتيوب صحيح وصريح

        status_msg = await event.respond("🔍 جاري فحص الرابط وتخطي الحماية، يرجى الانتظار...")
        
        # إعدادات تمويه قوية لتخطي حظر السيرفرات والـ HTTP Error
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.google.com/',
            'nocheckcertificate': True
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                video_title = info_dict.get('title', 'فيديو يوتيوب')
                video_duration = info_dict.get('duration', 0)
                
                if video_duration > 7200:
                    await status_msg.edit("⚠️ عذراً، لا يمكن تحميل مقاطع فيديو تزيد مدتها عن ساعتين.")
                    return

            await status_msg.delete()
            choice_text = f"🎬 **العنوان:** {video_title}\n\n⏱ **المدة:** {video_duration // 60} دقيقة.\n\nاختر صيغة التحميل المناسبة لك أدناه:"
            buttons = [
                [Button.inline("🎥 تحميل كـ فيديو (MP4)", data=f"vid_{video_id}")],
                [Button.inline("🎵 تحميل كـ صوت (MP3)", data=f"aud_{video_id}")]
            ]
            await event.respond(choice_text, buttons=buttons)

        except Exception as e:
            await status_msg.edit("❌ عذراً، واجه السيرفر قيوداً من يوتيوب أثناء قراءة هذا الرابط.\nيرجى محاولة إرسال رابط فيديو آخر أو التأكد من أن الرابط ليس خاصاً.")

    # --- حدث الضغط على أزرار التحميل ---
    @bot.on(events.CallbackQuery)
    async def callback_handler(event):
        data = event.data.decode('utf-8')
        video_id = data.split('_')[1]
        download_type = data.split('_')[0]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        await event.answer("📥 بدأت عملية المعالجة والتحميل الفعلي...", alert=False)
        progress_msg = await event.edit("⚡️ جاري تحميل الملف الآن عبر بروكسي التمويه...")

        os.makedirs("downloads", exist_ok=True)
        outtmpl = f"downloads/{video_id}_%(title)s.%(ext)s"

        base_opts = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.google.com/',
            'nocheckcertificate': True,
            'quiet': True,
            'outtmpl': outtmpl
        }

        if download_type == "vid":
            base_opts['format'] = 'best[ext=mp4]/best'
        else:
            base_opts['format'] = 'bestaudio/best'
            base_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        try:
            with YoutubeDL(base_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                filename = ydl.prepare_filename(info)
                if download_type == "aud":
                    filename = os.path.splitext(filename)[0] + ".mp3"

            await progress_msg.edit("🚀 جاري رفع الملف الناتج الآن إلى تليجرام...")
            
            if download_type == "vid":
                await bot.send_file(event.chat_id, filename, caption=f"🎬 تم التحميل بنجاح عبر {SOURCE_CHANNEL}", supports_streaming=True)
            else:
                await bot.send_file(event.chat_id, filename, caption=f"🎵 تم تحميل الصوت بنجاح عبر {SOURCE_CHANNEL}")
                
            if os.path.exists(filename):
                os.remove(filename)
            await progress_msg.delete()

        except Exception as e:
            await progress_msg.edit("❌ فشل تحميل الملف الفعلي. قد يكون الحجم ضخماً جداً بالنسبة للاستضافة المجانية أو تم حظر العملية.")
            if 'filename' in locals() and os.path.exists(filename):
                os.remove(filename)

    bot.run_until_disconnected()

# --- حماية لمنع التكرار ---
if "bot_thread_started" not in st.session_state:
    st.session_state.bot_thread_started = True
    t = threading.Thread(target=run_telegram_bot, daemon=True)
    t.start()
