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

# --- إعداد تطبيق Flask ---
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

def get_base_ydl_opts():
    chosen_ua = random.choice(USER_AGENTS)
    opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 5,
        'nocheckcertificate': True,
        'source_address': '0.0.0.0',
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': chosen_ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        },
        # الخيار السحري الأهم: محاكاة عملاء تطبيقات الموبايل الرسمية لليوتيوب لتخطي الحجب
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'skip': ['dash', 'hls']
            }
        }
    }
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    return opts

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    sender = await event.get_sender()
    welcome_msg = (
        f"🙋‍♂️ أهلاً بك يا {sender.first_name} في بوت تحميل يوتيوب المتطور.\n\n"
        "🔗 أرسل لي رابط الفيديو من اليوتيوب الآن لكي أقوم بمعالجته وعرض الخيارات لك.\n\n"
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
        
        status_msg = await event.respond("🔍 جاري جلب معلومات الفيديو والصورة المصغرة...")
        
        try:
            ydl_opts = get_base_ydl_opts()
            loop = asyncio.get_event_loop()
            
            with YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            
            title = info.get('title', 'فيديو يوتيوب')
            thumbnail = info.get('thumbnail', '')
            
            buttons = [
                [
                    Button.inline("🎥 تحميل بالفيديو الأصلي", data=f"quality_best_{user_id}"),
                    Button.inline("🎵 تحميل كملف صوتي MP3", data=f"quality_audio_{user_id}")
                ]
            ]
            
            caption_text = f"📝 **اسم الفيديو:** {title}\n\n⚙️ اختر صيغة التحميل التي تريدها:"
            
            await status_msg.delete()
            
            if thumbnail:
                await bot.send_file(event.chat_id, thumbnail, caption=caption_text, buttons=buttons)
            else:
                await event.respond(caption_text, buttons=buttons)
                
        except Exception as e:
            try:
                await status_msg.delete()
            except:
                pass
            error_msg = str(e)
            if "Sign in to confirm you" in error_msg:
                await event.respond("❌ يوتيوب يطلب تسجيل الدخول. يرجى التأكد من أن ملف الـ `cookies.txt` حديث وصالح ولم تنتهي صلاحيته.")
            else:
                await event.respond(f"❌ فشل جلب معلومات الرابط.\nالسبب: {error_msg}")
    else:
        if event.sender_id != DEVELOPER_ID:
            await event.respond("❌ عذراً، هذا الرابط غير مدعوم. يرجى إرسال رابط فيديو يوتيوب صحيح.")

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    
    if data.startswith("quality_"):
        parts = data.split("_")
        quality_type = parts[1]
        target_user_id = int(parts[2])
        
        if user_id != target_user_id:
            await event.answer("⚠️ هذه الأزرار ليست لك!", alert=True)
            return
            
        url = user_steps.get(user_id)
        
        if not url:
            await event.edit("❌ انتهت صلاحية الجلسة، يرجى إرسال الرابط مجدداً.")
            return
            
        await event.edit("⏳ جاري بدء التحميل الفعلي الآن، يرجى الانتظار...")
        
        ydl_opts = get_base_ydl_opts()
        ydl_opts['outtmpl'] = f'downloads/{user_id}_%(id)s.%(ext)s'
        
        if quality_type == "best":
            ydl_opts['format'] = 'best'
        elif quality_type == "audio":
            ydl_opts['format'] = 'bestaudio/best'
            
        try:
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
                
            await asyncio.sleep(random.uniform(1.0, 2.0))
                
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: download_media(url, ydl_opts))
            
            file_path = info['file_path']
            title = info.get('title', 'YouTube Media')
            
            await event.respond(f"📥 جاري رفع الملف إلى تليجرام: **{title}**")
            
            if quality_type == "audio":
                await bot.send_file(event.chat_id, file_path, caption=f"🎵 **{title}**\n\nتم تحميل الملف الصوتي بنجاح.", voice_note=False)
            else:
                await bot.send_file(event.chat_id, file_path, caption=f"🎬 **{title}**\n\nتم التحميل بالجودة الأصلية بنجاح.")
                
            if os.path.exists(file_path):
                os.remove(file_path)
                
            if user_id in user_steps:
                del user_steps[user_id]
                
        except Exception as e:
            error_msg = str(e)
            if "Sign in to confirm you" in error_msg:
                await event.respond("❌ فشل التحميل: يوتيوب يمنع البوت ويطلب كوكيز جديدة وصالحة.")
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
    
    print("🤖 البوت المطور جاهز الآن...")
    bot.run_until_disconnected()
