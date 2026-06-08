import os
import asyncio
import sys
import threading

# =====================================================================
# نظام حماية متطور لإجبار حلقة الأحداث على الاستقرار داخل Streamlit
# =====================================================================
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

class StreamlitSafePolicy(asyncio.DefaultEventLoopPolicy):
    def get_event_loop(self):
        try:
            return super().get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            self.set_event_loop(loop)
            return loop

asyncio.set_event_loop_policy(StreamlitSafePolicy())

import streamlit as st
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL

# واجهة تفاعلية أساسية لمنع المنصة من قتل السيرفر
st.set_page_config(page_title="YouTube Audio Bot", page_icon="🎵")
st.title("🎵 خادم بوت تحميل صوتيات يوتيوب")
st.success("السيرفر يعمل الآن ومحمي من الإغلاق المفاجئ!")
st.info("تم عزل البوت في بيئة خلفية مستقرة لضمان عدم تدمير المهام (Pending Tasks).")

# =====================================================================
# جزء سيرفر الويب (Flask) لمنع خوادم الاستضافة من إغلاق أو تعطيل البوت
# =====================================================================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is Running Live and Healthy 2026!"

def run_flask():
    # تشغيل السيرفر على البورت المحدد ليتوافق مع الحاوية والاستضافة
    try:
        flask_app.run(host="0.0.0.0", port=7860, use_reloader=False)
    except Exception as e:
        print(f"Flask Server Notification: {e}")

# استخدام قفل على مستوى نظام التشغيل (Global Environment) لمنع تكرار تشغيل السيرفر والبوت عند الـ Refresh
if os.environ.get("FLASK_STARTED") is None:
    os.environ["FLASK_STARTED"] = "true"
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
    await asyncio.Event().wait()

def start_async_loop():
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_until_complete(main())

# حماية التشغيل القصوى (Global Server Scope): نتحقق عبر البيئة العامة للسيرفر لمنع التضارب نهائياً عند Refresh
if os.environ.get("BOT_RUNNING_GLOBAL") is None:
    os.environ["BOT_RUNNING_GLOBAL"] = "true"
    threading.Thread(target=start_async_loop, daemon=True).start()

# للحفاظ على استقرار واجهة المستخدم الفردية لكل مستخدم داخل Streamlit
if "bot_running_instance" not in st.session_state:
    st.session_state.bot_running_instance = True
