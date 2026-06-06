import os
import asyncio
import random
from flask import Flask
from threading import Thread
import nest_asyncio
from telethon import TelegramClient, events, Button
from yt_dlp import YoutubeDL

# تفعيل nest_asyncio لمنع تضارب تشغيل Flask مع Telethon
nest_asyncio.apply()

# --- بيانات المطور والبوت ---
API_ID = 27485469
API_HASH = '544459a0701b32741254945b08daebfe'
BOT_TOKEN = '8277082493:AAEjNtAo4GroDkM0-mIFNLxhgLZ-53qalBg'
DEVELOPER_ID = 8456056018
DEVELOPER_USERNAME = '@Eror_7'

# مسار ملف الكوكيز الأساسي
COOKIES_FILE = 'cookies.txt'

# --- قائمة متصفحات الموبايل الحديثة للتمويه ---
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
]

# --- إعداد تطبيق Flask (الويب الصغير) ---
app = Flask(__name__)

@app.route('/')
def home():
    cookies_status = "نشط وموجود" if os.path.exists(COOKIES_FILE) else "غير موجود! يرجى رفعه"
    return f"""
    <html>
        <head>
            <title>YouTube Downloader Bot Status</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; background-color: #2c3e50; color: white; padding-top: 50px; }}
                h1 {{ color: #e74c3c; }}
                .status {{ font-size: 24px; color: #2ecc71; }}
                .info {{ margin-top: 20px; font-size: 18px; color: #bdc3c7; }}
            </style>
        </head>
        <body>
            <h1>YouTube Downloader Bot</h1>
            <p class="status">● البوت يعمل بنجاح الآن</p>
            <div class="info">
                <p>المطور: <a href="https://t.me/Eror_7" style="color:#3498db; text-decoration:none;">{DEVELOPER_USERNAME}</a></p>
                <p>نظام الكوكيز: {cookies_status}</p>
            </div>
        </body>
    </html>
    """

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- إعداد بوت التليجرام ---
bot = TelegramClient('yt_downloader_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_steps = {}

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    sender = await event.get_sender()
    welcome_msg = (
        f"🙋‍♂️ أهلاً بك يا {sender.first_name} في بوت تحميل يوتيوب.\n\n"
        "🔗 أرسل لي رابط الفيديو من اليوتيوب الآن لكي أقوم بتحميله لك.\n\n"
        f"👨‍💻 مبرمج البوت: {DEVELOPER_USERNAME}"
    )
    await event.respond(welcome_msg)

@bot.on(events.NewMessage)
async def link_handler(event):
    if event.text.startswith('/'):
        return
        
    url = event.text.strip()
    
    if "youtube.com" in url or "youtu.be" in url:
        user_id = event.sender_id
        user_steps[user_id] = url
        
        buttons = [
            [
                Button.inline("🎥 تحميل كفيديو (MP4)", data=f"video_{user_id}"),
                Button.inline("🎵 تحميل كملف صوتي (MP3)", data=f"audio_{user_id}")
            ]
        ]
        await event.respond("⚙️ اختر صيغة التحميل المناسبة لك:", buttons=buttons)
    else:
        if event.sender_id != DEVELOPER_ID:
            await event.respond("❌ عذراً، هذا الرابط غير مدعوم. يرجى إرسال رابط فيديو يوتيوب صحيح.")

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    
    if data.startswith("video_") or data.startswith("audio_"):
        target_user_id = int(data.split("_")[1])
        
        if user_id != target_user_id:
            await event.answer("⚠️ هذه الأزرار ليست لك!", alert=True)
            return
            
        action = data.split("_")[0]
        url = user_steps.get(user_id)
        
        if not url:
            await event.edit("❌ انتهت صلاحية الجلسة، يرجى إرسال الرابط مجدداً.")
            return
            
        await event.edit("⏳ جاري معالجة الرابط وبدء التحميل، يرجى الانتظار...")
        
        chosen_ua = random.choice(USER_AGENTS)
        
        # إعدادات yt-dlp مع تفعيل ملف الكوكيز بشكل إجباري
        ydl_opts = {
            'outtmpl': f'downloads/{user_id}_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 5,
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': chosen_ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
        }

        # الربط الإجباري بملف الكوكيز إذا كان موجوداً
        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE
        
        if action == "video":
            ydl_opts['format'] = 'best'
        elif action == "audio":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            
        try:
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
                
            await asyncio.sleep(random.uniform(1.0, 2.0))
                
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: download_media(url, ydl_opts))
            
            file_path = info['file_path']
            title = info.get('title', 'YouTube Media')
            
            await event.respond(f"📥 جاري رفع الملف الآن: **{title}**")
            
            if action == "video":
                await bot.send_file(event.chat_id, file_path, caption=f"🎬 **{title}**\n\nتم التحميل بنجاح.")
            elif action == "audio":
                await bot.send_file(event.chat_id, file_path, caption=f"🎵 **{title}**\n\nتم التحميل بنجاح.", voice_note=False)
                
            if os.path.exists(file_path):
                os.remove(file_path)
                
            if user_id in user_steps:
                del user_steps[user_id]
                
        except Exception as e:
            error_msg = str(e)
            # تنبيه ذكي إذا اختفت الكوكيز أو انتهت صلاحيتها
            if "Sign in to confirm you" in error_msg:
                await event.respond("❌ فشل التحميل: يوتيوب يطلب تسجيل الدخول. ملف `cookies.txt` قد يكون غير موجود أو انتهت صلاحيته.")
            else:
                await event.respond(f"❌ حدث خطأ أثناء التحميل.\nالسبب: {error_msg}")
            if user_id in user_steps:
                del user_steps[user_id]

def download_media(url, opts):
    with YoutubeDL(opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info_dict)
        
        if not os.path.exists(filename):
            base, _ = os.path.splitext(filename)
            for ext in ['mp4', 'mkv', 'webm', '3gp', 'mp3', 'm4a']:
                if os.path.exists(f"{base}.{ext}"):
                    filename = f"{base}.{ext}"
                    break
                    
        info_dict['file_path'] = filename
        return info_dict

if __name__ == '__main__':
    print("⚡ جاري تشغيل سيرفر الويب...")
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("🤖 البوت جاهز ومستعد...")
    bot.run_until_disconnected()
