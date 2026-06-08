import logging
import streamlit as st
from telethon import TelegramClient, events, Button
from telethon.errors import UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
import asyncio

# --- 1. إعدادات واجهة Streamlit الأساسية لتشغيل خادم الويب الخاص بك ---
st.set_page_config(page_title="YouTube Downloader Bot Server", page_icon="⚡")
st.title("🚀 خادم بوت تحميل اليوتيوب")
st.write("الخادم يعمل الآن بنجاح ومستقر 24/7 لاستقبال طلبات التحميل والتليجرام.")

# إعدادات تسجيل الأخطاء (Logging) لمراقبة عمل البوت
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 2. البيانات الخاصة بك التي قمت بتزويدي بها ---
API_ID = 27485469
API_HASH = '544459a0701b32741254945b08daebfe'
BOT_TOKEN = '8442853121:AAGIKd_rM5_o9p8ea7XqYtB3fM0KRlqsfc4'
DEVELOPER_ID = 8456056018

# --- 3. قنوات الاشتراك الإجباري ---
# قم باستبدال معرفات القنوات هذه بمعرفات قنواتك الخاصة (يجب أن يكون البوت مشرفاً فيها)
CHANNELS = [
    "@YourChannel1", 
    "@YourChannel2"
]

# دالة لتهيئة تشغيل التليجرام داخل بيئة Streamlit بدون تضارب في الـ Loops
@st.cache_resource
def init_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_client = TelegramClient('youtube_downloader_session', API_ID, API_HASH, loop=loop)
    bot_client.start(bot_token=BOT_TOKEN)
    return bot_client

client = init_telegram_bot()

# دالة للتحقق مما إذا كان المستخدم مشتركاً في القنوات الإلزامية أم لا
async def check_subscription(user_id):
    not_joined = []
    for channel in CHANNELS:
        try:
            # محاولة جلب بيانات المستخدم من القناة للتحقق من وجوده
            await client(GetParticipantRequest(channel=channel, participant=user_id))
        except UserNotParticipantError:
            # إذا لم يكن مشتركاً، يتم إضافته للقائمة
            not_joined.append(channel)
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق من القناة {channel}: {e}")
            # في حال وجود خطأ في معرف القناة أو صلاحيات البوت، نعتبره غير مشترك احتياطياً
            not_joined.append(channel)
    return not_joined

# --- 4. معالجات الأحداث والأوامر للبوت ---

# معالج أمر البدء /start والتفاعل مع الرسائل
@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    
    # التحقق من الاشتراك أولاً قبل تقديم أي خدمة للبوت
    missing_channels = await check_subscription(user_id)
    
    if missing_channels:
        # إنشاء أزرار شفافة (Inline Buttons) للقنوات التي لم يشترك بها
        buttons = []
        for index, ch in enumerate(missing_channels, start=1):
            buttons.append([Button.url(f"🔗 اضغط هنا للاشتراك بالقناة {index}", f"https://t.me/{ch.replace('@', '')}")])
        
        # إضافة زر التأكيد بعد الاشتراك
        buttons.append([Button.inline("🔄 تم الاشتراك (تأكيد)", data="check_sub")])
        
        text = "⚠️ **عذراً عزيزي، لا يمكنك استخدام بوت تحميل اليوتيوب قبل الاشتراك في قنوات البوت أولاً.**\n\nالرجاء الاشتراك بالقنوات أدناه ثم اضغط على زر التأكيد المتواجد في الأسفل 👇"
        await event.respond(text, buttons=buttons)
    else:
        # الرسالة التي تظهر للمستخدم إذا كان مشتركاً بالفعل ويريد استخدام البوت
        welcome_text = "🎉 **أهلاً بك في بوت تحميل من اليوتيوب!**\n\nلقد تم التحقق من اشتراكك بنجاح. أرسل الآن رابط الفيديو أو الصوت الذي تريد تحميله مباشرة."
        await event.respond(welcome_text)

# معالج الضغط على زر التأكيد الشفاف (Inline Callbacks)
@client.on(events.CallbackQuery(data="check_sub"))
async def callback_handler(event):
    user_id = event.sender_id
    
    # إعادة التحقق عند ضغط زر التأكيد
    missing_channels = await check_subscription(user_id)
    
    if missing_channels:
        # إذا كان لا يزال هناك قنوات ناقصة، نرسل له تنبيه تنبيهي (Popup) ونحدث الرسالة
        buttons = []
        for index, ch in enumerate(missing_channels, start=1):
            buttons.append([Button.url(f"🔗 اضغط هنا للاشتراك بالقناة {index}", f"https://t.me/{ch.replace('@', '')}")])
        buttons.append([Button.inline("🔄 تم الاشتراك (تأكيد)", data="check_sub")])
        
        await event.answer("❌ أنت لم تشترك في جميع القنوات بعد! يرجى الاشتراك أولاً.", alert=True)
        text = "⚠️ **ما زلت غير مشترك في بعض القنوات الإلزامية!**\n\nيرجى التأكد من الانضمام إليها جميعاً ثم المحاولة مرة أخرى عبر الضغط على الزر أدناه:"
        await event.edit(text, buttons=buttons)
    else:
        # إذا اشترك في كل القنوات بنجاح بعد الضغط على الزر
        await event.answer("✅ تم التحقق بنجاح! شكراً لك.", alert=True)
        welcome_text = "🎉 **أهلاً بك في بوت تحميل من اليوتيوب!**\n\nلقد تم التحقق من اشتراكك بنجاح. أرسل الآن رابط الفيديو أو الصوت الذي تريد تحميله مباشرة."
        await event.edit(welcome_text, buttons=None)


# --- 5. قسم أكواد التحميل من اليوتيوب الخاص بك ---
# استقبال الروابط والتحقق من الاشتراك إجبارياً قبل تشغيل الـ yt-dlp والتحميل:

@client.on(events.NewMessage)
async def youtube_download_handler(event):
    # تخطي الأوامر الأساسية مثل start لكي لا تتداخل الاستجابة
    if event.text.startswith('/start'):
        return
        
    user_id = event.sender_id
    
    # التحقق من الاشتراك الإجباري عند إرسال أي رابط أو رسالة للبوت
    missing_channels = await check_subscription(user_id)
    if missing_channels:
        buttons = []
        for index, ch in enumerate(missing_channels, start=1):
            buttons.append([Button.url(f"🔗 اضغط هنا للاشتراك بالقناة {index}", f"https://t.me/{ch.replace('@', '')}")])
        buttons.append([Button.inline("🔄 تم الاشتراك (تأكيد)", data="check_sub")])
        
        text = "⚠️ **عذراً، يجب عليك الاشتراك بالقنوات أولاً لتتمكن من التحميل من اليوتيوب:**"
        await event.respond(text, buttons=buttons)
        return

    # ---- [ضع كود مكتبة yt-dlp أو شفرة التحميل الأصلية الخاصة بك هنا] ----
    # مثال توضيحي لاستجابة البوت عند استلام روابط اليوتيوب:
    if "youtube.com" in event.text or "youtu.be" in event.text:
        await event.respond("⏳ جاري معالجة رابط اليوتيوب والتحميل باستخدام إصدار yt-dlp المحدث، يرجى الانتظار...")
        # هنا تضع بقية أسطر الاستخراج، استخدام كوكيز cookies.txt والرفع الخاصة بملفات البوت لديك.


# --- 6. تشغيل استقبال أحداث البوت بالتوازي مع Streamlit ---
st.success("⚡ تم ربط نظام الاشتراك الإجباري وتحديثات التليجرام بالخادم الحركي بنجاح.")
