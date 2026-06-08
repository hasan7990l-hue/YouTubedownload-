import os
import re
import asyncio
import threading
import streamlit as st
from telethon import TelegramClient, events, Button
from yt_dlp import YoutubeDL

# --- إعداد واجهة Streamlit الرسومية ---
st.set_page_config(page_title="خادم بوت تحميل يوتيوب", page_icon="🎵", layout="centered")

st.markdown("<h1 style='text-align: center;'>🎵 خادم بوت تحميل صوتيات وفيديوهات يوتيوب</h1>", unsafe_allow_html=True)
st.success("🟢 السيرفر يعمل الآن ومحمي من الإغلاق المفاجئ!")
st.info("🔹 تم عزل البوت في بيئة خلفية مستقرة لضمان عدم تدمير المهام المعلقة (Pending Tasks).")

# --- البيانات الخاصة بك ---
API_ID = 27485469
API_HASH = "544459a0701b32741254945b08daebfe"
BOT_TOKEN = "8180650384:AAG6ZhD7YxQk1nHOL7xhOVCbqQ_8XvOadQ0"
DEV_ID = 8456056018
SOURCE_CHANNEL = "@lb2_c"

# دالة للتحقق من صحة روابط يوتيوب
def is_youtube_url(url):
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?\{\}\s]+)'
    return re.match(youtube_regex, url)

# --- دالة تشغيل البوت الأساسية ---
def run_telegram_bot():
    # إنشاء حلقة أحداث (Event Loop) جديدة وخاصة بهذا الـ Thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    bot = TelegramClient('yt_downloader_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

    # --- حدث بدء التشغيل /start ---
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        first_name = event.sender.first_name or "المستخدم"
        welcome_text = (
            f"🙋‍♂️ أهلاً بك يا {first_name} في بوت تحميل يوتيوب السريع على استضافة Streamlit!\n\n"
            f"📥 كل ما عليك فعله هو إرسال رابط الفيديو من اليوتيوب، وسأقوم بتحميله لك مباشرة (فيديو أو صوت).\n\n"
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
        if not is_youtube_url(url):
            return
            
        status_msg = await event.respond("🔍 جاري جلب معلومات الفيديو والتحقق من الرابط، يرجى الانتظار...")
        
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                video_title = info_dict.get('title', 'فيديو يوتيوب')
                video_duration = info_dict.get('duration', 0)
                
                if video_duration > 7200:
                    await status_msg.edit("⚠️ عذراً، لا يمكن تحميل مقاطع فيديو تزيد مدتها عن ساعتين.")
                    return

            await status_msg.delete()
            choice_text = f"🎬 **العنوان:** {video_title}\n\n⏱ **المدة:** {video_duration // 60} دقيقة.\n\n اختر صيغة التحميل المناسبة لك أدناه:"
            buttons = [
                [Button.inline("🎥 تحميل كـ فيديو (MP4)", data=f"vid_{info_dict['id']}")],
                [Button.inline("🎵 تحميل كـ صوت (MP3)", data=f"aud_{info_dict['id']}")]
            ]
            await event.respond(choice_text, buttons=buttons)

        except Exception as e:
            await status_msg.edit("❌ حدث خطأ أثناء جلب تفاصيل الرابط. تأكد من أن الرابط عام وصحيح.")

    # --- حدث الضغط على أزرار التحميل inline ---
    @bot.on(events.CallbackQuery)
    async def callback_handler(event):
        data = event.data.decode('utf-8')
        video_id = data.split('_')[1]
        download_type = data.split('_')[0]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        await event.answer("📥 بدأت عملية المعالجة والتحميل...", alert=False)
        progress_msg = await event.edit("⚡️ جاري تحميل الملف من سيرفرات يوتيوب إلى الاستضافة...")

        os.makedirs("downloads", exist_ok=True)
        outtmpl = f"downloads/{video_id}_%(title)s.%(ext)s"

        if download_type == "vid":
            ydl_opts = {'format': 'best[ext=mp4]/best', 'outtmpl': outtmpl, 'quiet': True}
        else:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': outtmpl,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
            }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                filename = ydl.prepare_filename(info)
                if download_type == "aud":
                    filename = os.path.splitext(filename)[0] + ".mp3"

            await progress_msg.edit("🚀 جاري رفع الملف الآن إلى تليجرام...")
            
            if download_type == "vid":
                await bot.send_file(event.chat_id, filename, caption=f"🎬 تم التحميل بنجاح عبر {SOURCE_CHANNEL}", supports_streaming=True)
            else:
                await bot.send_file(event.chat_id, filename, caption=f"🎵 تم تحميل الصوت بنجاح عبر {SOURCE_CHANNEL}")
                
            if os.path.exists(filename):
                os.remove(filename)
            await progress_msg.delete()

        except Exception as e:
            await progress_msg.edit("❌ عذراً، فشل تحميل ومعالجة الملف بسبب حجمه الكبير أو قيود اليوتيوب.")
            if 'filename' in locals() and os.path.exists(filename):
                os.remove(filename)

    # تشغيل الحلقات اللانهائية للبوت
    bot.run_until_disconnected()

# --- منع التكرار وتشغيل البوت في الخلفية (Thread-safe) ---
if "bot_started" not in st.session_state:
    st.session_state.bot_started = True
    threading.Thread(target=run_telegram_bot, daemon=True).start()
