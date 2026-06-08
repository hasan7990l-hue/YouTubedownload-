import logging
import streamlit as st
import asyncio
from threading import Thread
from telethon import TelegramClient, events, Button
from telethon.errors import UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.functions.channels import GetParticipantRequest as GetGroupParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator

# --- 1. إعدادات واجهة Streamlit الأساسية لضمان عمل السيرفر 24/7 ---
st.set_page_config(page_title="Group Forced Subscription Bot", page_icon="🛡️")
st.title("🛡️ خادم بوت الاشتراك الإجباري للمجموعات")
st.markdown("### ⚡ حالة الخادم: **نشط ويعمل بكفاءة**")
st.info("تم فصل بيئة عمل البوت عن واجهة الويب لمنع تعارض الذاكرة (Weak Reference Error). البوت يعمل الآن بالخلفية بشكل مستمر.")

# إعدادات تسجيل الأخطاء (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 2. البيانات الخاصة بك ---
API_ID = 27485469
API_HASH = '544459a0701b32741254945b08daebfe'
BOT_TOKEN = '8442853121:AAGIKd_rM5_o9p8ea7XqYtB3fM0KRlqsfc4'
DEVELOPER_ID = 8456056018

# --- 3. قنوات الاشتراك الإجباري ---
CHANNELS = [
    "@YourChannel1", 
    "@YourChannel2"
]

# تهيئة عميل التليجرام خارج نطاق دالة st.cache لتفادي مشاكل الذاكرة
bot_client = TelegramClient('group_forced_sub_session', API_ID, API_HASH)

# دالة للتحقق من الاشتراك
async def check_subscription(user_id):
    not_joined = []
    for channel in CHANNELS:
        try:
            await bot_client(GetParticipantRequest(channel=channel, participant=user_id))
        except UserNotParticipantError:
            not_joined.append(channel)
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق من القناة {channel}: {e}")
            not_joined.append(channel)
    return not_joined

# دالة للتحقق من رتبة العضو في المجموعة
async def is_user_admin(chat_id, user_id):
    try:
        p = await bot_client(GetGroupParticipantRequest(channel=chat_id, participant=user_id))
        if isinstance(p.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
            return True
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من رتبة العضو: {e}")
    return False

# --- 4. معالجات الأحداث للأوامر والبوت ---

# أمر /start في الخاص
@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
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

# التفاعل مع زر التأكيد الشفاف
@bot_client.on(events.CallbackQuery(data="check_sub"))
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

# --- 5. نظام حماية المجموعات (الاشتراك الإجباري) ---
@bot_client.on(events.NewMessage)
async def group_protection_handler(event):
    if event.is_group or event.is_channel:
        if event.text.startswith('/start'):
            return
            
        user_id = event.sender_id
        chat_id = event.chat_id
        
        if not user_id or event.sender_id == (await bot_client.get_me()).id:
            return
            
        if await is_user_admin(chat_id, user_id):
            return
            
        missing_channels = await check_subscription(user_id)
        
        if missing_channels:
            try:
                await event.delete()
            except Exception as e:
                logger.error(f"فشل حذف الرسالة: {e}")
                
            buttons = []
            for index, ch in enumerate(missing_channels, start=1):
                buttons.append([Button.url(f"🔗 اضغط للاشتراك بالقناة {index}", f"https://t.me/{ch.replace('@', '')}")])
            
            sender = await event.get_sender()
            first_name = sender.first_name if hasattr(sender, 'first_name') else "العضو"
            
            warning_text = f"⚠️ **عذراً [ {first_name} ](tg://user?id={user_id})**\n\nتم حذف رسالتك تلقائياً! لا يمكنك إرسال الرسائل داخل المجموعة قبل الاشتراك في قنوات البوت أولاً.\n\nاشترك بالقنوات أدناه ثم يمكنك الكتابة:"
            
            warn_msg = await event.respond(warning_text, buttons=buttons)
            await asyncio.sleep(30)
            try:
                await warn_msg.delete()
            except Exception:
                pass

# --- 6. آلية التشغيل المعزولة تماماً وخارج نطاق خيوط Streamlit ---
def run_isolated_bot():
    # إنشاء حلقة أحداث نظيفة تماماً ومنفصلة عن الـ Streamlit Loop لتلافي خطأ Weak Reference
    isolated_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(isolated_loop)
    
    # تشغيل الاتصال بالبوت
    bot_client.start(bot_token=BOT_TOKEN)
    isolated_loop.run_until_complete(bot_client.run_until_disconnected())

# تشغيل البوت في خيط (Thread) نقي ومستقل عند إقلاع السيرفر لأول مرة
if 'bot_process_active' not in st.session_state:
    st.session_state['bot_process_active'] = True
    backend_thread = Thread(target=run_isolated_bot, daemon=True)
    backend_thread.start()
