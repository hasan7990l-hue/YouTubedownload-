import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL

# =====================================================================
# جزء سيرفر الويب (Flask) لمنع خوادم الاستضافة من إغلاق أو تعطيل البوت
# =====================================================================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is Running Live and Healthy 2026!"

def run_flask():
    # تشغيل السيرفر على البورت المحدد ليتوافق مع الحاوية والاستضافة
    flask_app.run(host="0.0.0.0", port=7860)

# تشغيل سيرفر الويب في خيط خلفي (Thread) مستقل لمنع تجميد حلقة البوت الأساسية
threading.Thread(target=run_flask, daemon=True).start()

# =====================================================================
# إعدادات البوت والبيانات الخاصة بالمطور والمنصة
# =====================================================================
API_ID = 27485469
API_HASH = "544459a0701b32741254945b08daebfe"
BOT_TOKEN = "8277082493:AAExFWp3SUp375JcH3RgXprf8wwU3JZZCi4"
DEVELOPER_ID = 8456056018
DEVELOPER_USERNAME = "@Eror_7"
BOT_CHANNEL = "@lb2_c"

# تكوين البوت مع إجبار الاستخدام على IPv4 لمنع حظر خوادم Hugging Face وتجنب فشل الاتصال (sign_in_bot)
app = Client(
    "yt_audio_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    ipv6=False  # هذا السطر يمنع انقطاع الاتصال بخوادم تليجرام داخل الحاوية
)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    start_text = (
        "**أهلاً بك في بوت تحميل صوتيات يوتيوب!**\n\n"
        "أرسل لي أي رابط من يوتيوب وسأقوم بتحميله وإرساله لك كملف صوتي فوراً.\n\n"
        f"**قناة البوت:** {BOT_CHANNEL}\n"
        f"**المبرمج:** {DEVELOPER_USERNAME}"
    )
    await message.reply_text(start_text)

@app.on_message(filters.text & filters.private)
async def download_audio(client: Client, message: Message):
    url = message.text.strip()
    
    # التحقق من أن النص المرسل يحتوي على رابط يوتيوب
    if "youtube.com" not in url and "youtu.be" not in url:
        await message.reply_text("**عذراً، يرجى إرسال رابط يوتيوب صحيح فقط.**")
        return

    status_message = await message.reply_text("**جاري معالجة الرابط وتحميل الصوت... انتظر قليلاً**")
    
    # إعدادات تحويل الصوت باستخدام yt-dlp و ffmpeg مع دمج الكوكيز وحل مشكلة محاكاة المتصفح بالكامل
    outtmpl = f"downloads/{message.from_user.id}_%(title)s.%(ext)s"
    ydl_opts = {
        'format': 'ba/b',             # تم استخدام الاختصار البرمجي ba/b لتوسيع نطاق قبول أفضل صيغة صوتية متاحة دون قيود صارمة
        'outtmpl': outtmpl,
        'cookiefile': 'cookies.txt',  # استخدام الكوكيز لتخطي الحظر الأمني
        'nocheckcertificate': True,   # تخطي فحص شهادات SSL لتفادي انقطاع الاتصال EOF
        'source_address': '0.0.0.0',  # إجبار الخادم على استخدام IPv4 بدلاً من IPv6 المستهدف بالحظر
        'ignoreerrors': True,         # تخطي الأخطاء الطفيفة أثناء جلب البيانات لضمان استمرار التحميل
        'http_headers': {             # إضافة حزمة رؤوس طلبات كاملة لمحاكاة متصفح حقيقي ومنع الـ NoneType
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }

    try:
        # استخدام loop الحالي بشكل آمن متوافق مع جميع إصدارات بايثون المستقرة والحديثة
        loop = asyncio.get_running_loop()
        with YoutubeDL(ydl_opts) as ydl:
            # استخراج البيانات مع التحقق الكامل لمنع أخطاء NoneType
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            if info is None:
                await status_message.edit_text("**عذراً، فشل يوتيوب في الاستجابة للطلب أو الرابط غير صالح. يرجى تجديد ملف cookies.txt الخاص بك.**")
                return
                
            file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"

        if os.path.exists(file_path):
            await status_message.edit_text("**جاري رفع الملف الصوتي إلى تليجرام...**")
            
            # إرسال الملف الصوتي للمستخدم
            caption_text = (
                "**تم التحميل بنجاح بواسطة البوت**\n\n"
                f"**قناة البوت:** {BOT_CHANNEL}\n"
                f"**المطور:** {DEVELOPER_USERNAME}"
            )
            await message.reply_audio(audio=file_path, caption=caption_text)
            
            # حذف الملف بعد الإرسال للحفاظ على مساحة الاستضافة
            os.remove(file_path)
            await status_message.delete()
        else:
            await status_message.edit_text("**حدث خطأ أثناء معالجة الملف الصوتي.**")

    except Exception as e:
        await status_message.edit_text(f"**حدث خطأ غير متوقع أثناء التحميل:**\n`{str(e)}`")
        # تنظيف أي ملف قد يكون قد تم تحميله جزئياً في حال حدوث خطأ
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

# الدالة الأساسية لتشغيل البوت بنظام حلقة أحداث مستقرة (Event Loop) للتعامل الصحيح مع الاستضافة وبايثون الحديث
async def main():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    
    print("جاري بدء تشغيل بوت تليجرام...")
    await app.start()
    print("البوت يعمل الآن بنجاح وبدون توقف!")
    
    # الحفاظ على البوت نشطاً ومستمعاً للطلبات بصورة مستمرة وآمنة
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        # تشغيل الدالة الأساسية عبر نظام إدارة المهام الرسمي لمنع مشاكل الـ Weak References نهائياً
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("تم إيقاف البوت يدوياً.")
