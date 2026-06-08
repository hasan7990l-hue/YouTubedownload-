import logging
import streamlit as st
from telethon import TelegramClient, events, Button
from telethon.errors import UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.functions.channels import GetParticipantRequest as GetGroupParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
import asyncio

# --- 1. إعدادات واجهة Streamlit الأساسية لتشغيل خادم الويب الخاص بك ---
st.set_page_config(page_title="Group Forced Subscription Bot", page_icon="🛡️")
st.title("🛡️ خادم بوت الاشتراك الإجباري للمجموعات")
st.write("الخادم يعمل الآن بنجاح ومستقر 24/7 لحماية المجموعات وإلزام الأعضاء بالاشتراك.")

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
    bot_client = TelegramClient('group_forced_sub_session', API_ID, API_HASH, loop=loop)
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

# دالة للتحقق مما إذا كان العضو مشرفاً أو مالكاً في المجموعة لتخطيه من الاشتراك الإجبارى
async def is_user_admin(chat_id, user_id):
    try:
        p = await client(GetGroupParticipantRequest(channel=chat_id, participant=user_id))
        if isinstance(p.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
            return True
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من رتبة العضو: {e}")
    return False

# --- 4. معالجات الأحداث والأوامر للبوت ---

# معالج أمر البدء /start في الخاص (تأكيد الاشتراك يدوياً)
@client.on(events.NewMessage(pattern='/start', chats=None))
async def start_handler(event):
    # التحقق من أن الرسالة في الخاص وليست في مجموعة
    if event.is_private:
        user_id = event.sender_id
        missing_channels = await check_subscription(user_id)
        
        if missing_channels:
            buttons = []
            for index, ch in enumerate(missing_channels, start=1):
                buttons.append([Button.url(f"🔗 الاشتراك بالقناة {index}", f"https://t.me/{ch.replace('@', '')}")])
            buttons.append([Button.inline("🔄 تم الاشتراك (تأكيد)", data="check_sub")])
            
            text = "⚠️ **عذراً عزيزي، يجب عليك الاشتراك في القنوات أولاً لتتمكن من التفاعل في المجموعات المحمية.**"
            await event.respond(text, buttons=buttons)
        else:
            welcome_text = "🎉 **أهلاً بك!**\n\nلقد تم التحقق من اشتراكك بنجاح، يمكنك الآن إرسال الرسائل في المجموعات بحرية."
            await event.respond(welcome_text)

# معالج الضغط على زر التأكيد الشفاف (Inline Callbacks) في الخاص
@client.on(events.CallbackQuery(data="check_sub"))
async def callback_handler(event):
    user_id = event.sender_id
    missing_channels = await check_subscription(user_id)
    
    if missing_channels:
        buttons = []
        for index, ch in enumerate(missing_channels, start=1):
            buttons.append([Button.url(f"🔗 الاشتراك بالقناة {index}", f"https://t.me/{ch.replace('@', '')}")])
        buttons.append([Button.inline("🔄 تم الاشتراك (تأكيد)", data="check_sub")])
        
        await event.answer("❌ أنت لم تشترك في جميع القنوات بعد!", alert=True)
        text = "⚠️ **ما زلت غير مشترك في بعض القنوات الإلزامية!**"
        await event.edit(text, buttons=buttons)
    else:
        await event.answer("✅ تم التحقق بنجاح! شكراً لك.", alert=True)
        welcome_text = "🎉 **أهلاً بك!**\n\nلقد تم التحقق من اشتراكك بنجاح، يمكنك الآن إرسال الرسائل في المجموعات بحرية."
        await event.edit(welcome_text, buttons=None)


# --- 5. نظام حماية المجموعات (الاشتراك الإجباري للمجموعات) ---

@client.on(events.NewMessage)
async def group_protection_handler(event):
    # تشغيل الفحص فقط داخل المجموعات والجروبات
    if event.is_group or event.is_channel:
        user_id = event.sender_id
        chat_id = event.chat_id
        
        # تجنب فحص البوت لنفسه أو للرسائل التي ليست من مستخدم حقيقي
        if not user_id or event.sender_id == (await client.get_me()).id:
            return
            
        # 1. التحقق أولاً إذا كان العضو مشرف أو مالك الجروب (تخطيه لحماية الإشراف)
        if await is_user_admin(chat_id, user_id):
            return
            
        # 2. التحقق من اشتراك العضو في القنوات الإلزامية
        missing_channels = await check_subscription(user_id)
        
        if missing_channels:
            try:
                # حذف رسالة العضو غير المشترك فوراً لحماية المجموعة
                await event.delete()
            except Exception as e:
                logger.error(f"فشل حذف الرسالة (تأكد من رفع البوت مشرفاً بصلاحية الحذف): {e}")
                
            # إرسال أزرار الاشتراك في المجموعة وتنبيهه بالمنشن
            buttons = []
            for index, ch in enumerate(missing_channels, start=1):
                buttons.append([Button.url(f"🔗 اضغط للاشتراك بالقناة {index}", f"https://t.me/{ch.replace('@', '')}")])
            
            # جلب اسم العضو للمنشن
            sender = await event.get_sender()
            first_name = sender.first_name if hasattr(sender, 'first_name') else "العضو"
            
            warning_text = f"⚠️ **عذراً [ {first_name} ](tg://user?id={user_id})**\n\nتم حذف رسالتك تلقائياً! لا يمكنك إرسال الرسائل داخل المجموعة قبل الاشتراك في قنوات البوت أولاً.\n\nاشترك بالقنوات أدناه ثم يمكنك الكتابة:"
            
            # إرسال التنبيه وحذفه تلقائياً بعد 30 ثانية لكي لا تتسخ المجموعة بالرسائل التنبيهية
            warn_msg = await event.respond(warning_text, buttons=buttons)
            await asyncio.sleep(30)
            try:
                await warn_msg.delete()
            except Exception:
                pass


# --- 6. تشغيل النظام ---
st.success("⚡ تم تشغيل نظام حماية المجموعات والاشتراك الإجباري بنجاح.")
