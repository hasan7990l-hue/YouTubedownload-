import os
import asyncio
from flask import Flask
from threading import Thread
import nest_asyncio
from telethon import TelegramClient, events, Button
from yt_dlp import YoutubeDL

# تفعيل nest_asyncio لمنع تضارب تشغيل Flask مع Telethon
nest_asyncio.apply()

# --- بيانات المطور والبوت المقدمة ---
API_ID = 27485469
API_HASH = '544459a0701b32741254945b08daebfe'
BOT_TOKEN = '8277082493:AAGpRt5OG4adspV_wDH52Pk9O8TolEXJYbU'
DEVELOPER_ID = 8456056018
DEVELOPER_USERNAME = '@Eror_7'

# --- إعداد ملف الكوكيز ---
# ملاحظة: قم بإنشاء ملف باسم cookies.txt في نفس المجلد وضع فيه كوكيز اليوتيوب الخاصة بك لتفادي الحظر
COOKIES_FILE = 'cookies.txt'
if not os.path.exists(COOKIES_FILE):
    with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
        f.write("# Netscape HTTP Cookie File\n")

# --- إعداد تطبيق Flask (الويب الصغير) ---
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>YouTube Downloader Bot Status</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; background-color: #2c3e50; color: white; padding-top: 50px; }
                h1 { color: #e74c3c; }
                .status { font-size: 24px; color: #2ecc71; }
                .info { margin-top: 20px; font-size: 18px; color: #bdc3c7; }
            </style>
        </head>
        <body>
            <h1>YouTube Downloader Bot</h1>
            <p class="status">● البوت يعمل بنجاح الآن</p>
            <div class="info">
                <p>المطور: <a href="https://t.me/Eror_7" style="color:#3498db; text-decoration:none;">@Eror_7</a></p>
                <p>نظام الكوكيز: نشط ومفعل (cookies.txt)</p>
            </div>
        </body>
    </html>
    """

def run_flask():
    # هنا تم جعل البورت يقرأ من إعدادات المنصة (مثل بورت 5000 المطلوب في الصورة) وإذا لم يجدها يستخدم 5000 الافتراضي لـ Back4App
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- إعداد بوت التليجرام ---
bot = TelegramClient('yt_downloader_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# تخزين مؤقت لروابط المستخدمين لتحديد نوع التحميل لاحقاً
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
    # تجاهل الأوامر مثل /start
    if event.text.startswith('/'):
        return
        
    url = event.text.strip()
    
    # التحقق من أن الرابط ينتمي لليوتيوب
    if "youtube.com" in url or "youtu.be" in url:
        user_id = event.sender_id
        user_steps[user_id] = url
        
        # إنشاء أزرار الخيارات (فيديو أو ملف صوتي)
        buttons = [
            [
                Button.inline("🎥 تحميل كفيديو (MP4)", data=f"video_{user_id}"),
                Button.inline("🎵 تحميل كملف صوتي (MP3)", data=f"audio_{user_id}")
            ]
        ]
        await event.respond("⚙️ اختر صيغة التحميل المناسبة لك:", buttons=buttons)
    else:
        # إذا لم يكن الرابط من اليوتيوب، يطلب رابط صحيح (إلا إذا كان المطور يرسل شيئاً آخر)
        if event.sender_id == DEVELOPER_ID:
            pass
        else:
            await event.respond("❌ عذراً، هذا الرابط غير مدعوم. يرجى إرسال رابط فيديو يوتيوب صحيح.")

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    
    if data.startswith("video_") or data.startswith("audio_"):
        target_user_id = int(data.split("_")[1])
        
        # التأكد من أن الذي ضغط على الزر هو صاحب الرابط
        if user_id != target_user_id:
            await event.answer("⚠️ هذه الأزرار ليست لك!", alert=True)
            return
            
        action = data.split("_")[0]
        url = user_steps.get(user_id)
        
        if not url:
            await event.edit("❌ انتهت صلاحية الجلسة، يرجى إرسال الرابط مجدداً.")
            return
            
        await event.edit("⏳ جاري معالجة الرابط وبدء التحميل، يرجى الانتظار...")
        
        # إعدادات yt-dlp المشتركة ونظام الكوكيز
        ydl_opts = {
            'cookiefile': COOKIES_FILE,
            'outtmpl': f'downloads/{user_id}_%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True
        }
        
        if action == "video":
            # تم تحسين السطر بالأسفل ليقوم بجلب أفضل جودة فيديو + أفضل صوت كخيار أول، وإذا فشل يجلب أفضل ملف مدمج جاهز لتفادي خطأ الصيغ تماماً
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
        elif action == "audio":
            # جلب أفضل صوت متاح بصيغة عامة ثم تحويله
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            
        try:
            # إنشاء مجلد التحميلات إذا لم يكن موجوداً
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
                
            # تشغيل التحميل في سياق منفصل لتجنب بلوك البوت
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: download_media(url, ydl_opts))
            
            file_path = info['file_path']
            title = info.get('title', 'YouTube Media')
            
            await event.respond(f"📥 جاري رفع الملف الآن: **{title}**")
            
            # إرسال الملف بناءً على الخيار المحدد
            if action == "video":
                await bot.send_file(event.chat_id, file_path, caption=f"🎬 **{title}**\n\nتم التحميل بواسطة البوت الخاص بك.")
            elif action == "audio":
                await bot.send_file(event.chat_id, file_path, caption=f"🎵 **{title}**\n\nتم التحميل بواسطة البوت الخاص بك.", voice_note=False)
                
            # حذف الملف محلياً بعد الإرسال لتوفير المساحة
            if os.path.exists(file_path):
                os.remove(file_path)
                
            # تنظيف الذاكرة المؤقتة للمستخدم
            if user_id in user_steps:
                del user_steps[user_id]
                
        except Exception as e:
            await event.respond(f"❌ حدث خطأ أثناء التحميل أو الرفع.\nالسبب: {str(e)}")
            if user_id in user_steps:
                del user_steps[user_id]

def download_media(url, opts):
    with YoutubeDL(opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info_dict)
        
        # إذا تم تحويل الصوت إلى mp3، فإن الامتداد في prepare_filename قد يختلف، لذا نقوم بتعديله
        if 'postprocessors' in opts:
            filename = os.path.splitext(filename)[0] + '.mp3'
            
        info_dict['file_path'] = filename
        return info_dict

# --- تشغيل التطبيق بالكامل ---
if __name__ == '__main__':
    print("⚡ جاري تشغيل سيرفر الويب المدمج...")
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("🤖 البوت يعمل الآن بنجاح ومستعد لاستقبال الروابط...")
    bot.run_until_disconnected()
