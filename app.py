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

# --- 2. البيانات الثابتة للمطور والسورس ---
API_ID = 27485469
API_HASH = '544459a0701b32741254945b08daebfe'
BOT_TOKEN = '8442853121:AAGIKd_rM5_o9p8ea7XqYtB3fM0KRlqsfc4'
DEVELOPER_ID = 8456056018

# حقوق المطور والسورس الثابتة (تمت إضافة قناة السورس الخاصة بك هنا وحذف الوهمي)
DEV_USERNAME = "@Eror_7"
SOURCE_CHANNEL = "@lb2_c"

# --- 3. قاعدة البيانات المؤقتة في الذاكرة (تخزين إعدادات البوت والتحكم) ---
if 'BOT_CONFIG' not in globals():
    BOT_CONFIG = {
        "channels": [],           # تم مسح القنوات الوهمية تماماً ليكون التحكم عبر الأزرار نظيفاً ومن الصفر
        "user_channels": {},      # تخزين قنوات المستخدمين للمجموعات بتنسيق: {chat_id: ["@ch1", "@ch2"]}
        "user_welcome": "🎉 **أهلاً بك في البوت!**\n\nلقد تم التحقق من اشتراكك بنجاح، يمكنك الآن إرسال الرسائل في المجموعات بحرية.",
        "user_media": None,       # ملف الميديا الخاص بواجهة المستخدمين (file_id أو مسار)
        "admin_media": None,      # ملف الميديا الخاص بواجهة المطور (file_id أو مسار)
        "stats_users": set(),     # لتخزين الآيدي الخاص بالمستخدمين الفريدين للإحصائيات
        "stats_groups": set(),    # لتخزين آيدي المجموعات المحمية للإحصائيات
        "awaiting_input": {}      # لتتبع حالة المطور عند تعديل الإعدادات (مثل إرسال ميديا أو قنوات)
    }

# تهيئة عميل التليجرام خارج نطاق دالة st.cache لتفادي مشاكل الذاكرة
bot_client = TelegramClient('group_forced_sub_session', API_ID, API_HASH)

# دالة للتحقق من الاشتراك الإجباري الخاص بالمطور (في الرسائل الخاصة)
async def check_subscription(user_id):
    not_joined = []
    for channel in BOT_CONFIG["channels"]:
        if not channel.startswith("@"):
            continue
        try:
            await bot_client(GetParticipantRequest(channel=channel, participant=user_id))
        except UserNotParticipantError:
            not_joined.append(channel)
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق من القناة {channel}: {e}")
            not_joined.append(channel)
    return not_joined

# دالة للتحقق من الاشتراك الإجباري الخاص بالمجموعات (الذي يضيفه المستخدمون)
async def check_group_subscription(chat_id, user_id):
    not_joined = []
    # إذا لم يقم أدمن المجموعة بتعيين أي قناة، فلن يتم إجبار الأعضاء على شيء
    if chat_id not in BOT_CONFIG["user_channels"] or not BOT_CONFIG["user_channels"][chat_id]:
        return not_joined
        
    for channel in BOT_CONFIG["user_channels"][chat_id]:
        if not channel.startswith("@"):
            continue
        try:
            await bot_client(GetParticipantRequest(channel=channel, participant=user_id))
        except UserNotParticipantError:
            not_joined.append(channel)
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق من قناة المجموعة {channel}: {e}")
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

# --- 4. دالة توليد لوحة التحكم المتقدمة للمطور ---
async def send_admin_panel(event, edit=False):
    try:
        dev_entity = await bot_client.get_entity(DEVELOPER_ID)
        dev_name = dev_entity.first_name
    except Exception:
        dev_name = "المطور المعتمد"

    admin_text = (
        f"👑 **مرحباً بك يا {dev_name} في لوحة تحكم البوت المتقدمة!**\n\n"
        f"⚙️ يمكنك التحكم الكامل بإعدادات القنوات الافتراضية، الاختيارية، الميديا، والإحصائيات من خلال الأزرار أدناه."
    )
    
    buttons = [
        [Button.inline("📊 إحصائيات البوت الكاملة", data="admin_stats")],
        [Button.inline("📢 تعيين قنوات الاشتراك (اختياري 1 إلى 3)", data="admin_set_channels")],
        [Button.inline("🖼️ تعيين ميديا واجهة المستخدمين", data="admin_media_user")],
        [Button.inline("⚙️ تعيين ميديا لوحة التحكم", data="admin_media_admin")],
        [Button.inline("📝 تعديل رسالة ترحيب المستخدمين", data="admin_set_welcome")],
        [Button.inline("🔙 العودة للواجهة الرئيسية", data="admin_to_user_interface")],
        [Button.inline("❌ إغلاق اللوحة", data="admin_close")]
    ]
    
    if edit:
        try:
            await event.delete()
        except Exception:
            pass

    if BOT_CONFIG["admin_media"]:
        await bot_client.send_file(event.chat_id, BOT_CONFIG["admin_media"], caption=admin_text, buttons=buttons)
    else:
        await bot_client.send_message(event.chat_id, admin_text, buttons=buttons)

# --- 5. معالجات الأحداث للأوامر والبوت ولوحة التحكم ---

# أمر /start في الخاص (يظهر واجهة المستخدمين للجميع، مع زر الإعدادات السري للمطور فقط)
@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if event.is_private:
        user_id = event.sender_id
        BOT_CONFIG["stats_users"].add(user_id)
        
        missing_channels = await check_subscription(user_id)
        
        # أزرار واجهة المستخدمين الأساسية الثابتة
        user_buttons = [
            [Button.url("👨‍💻 مطور البوت", f"https://t.me/{DEV_USERNAME.replace('@', '')}")],
            [Button.url("📢 قناة السورس", f"https://t.me/{SOURCE_CHANNEL.replace('@', '')}")]
        ]
        
        # إذا كان مرسل الأمر هو المطور، يتم حقن زر "الإعدادات" في نهاية القائمة بشكل حصري وسري
        if user_id == DEVELOPER_ID:
            user_buttons.append([Button.inline("⚙️ الإعدادات (خاص بالمطور)", data="admin_open_panel")])
        
        if missing_channels:
            buttons = []
            for index, ch in enumerate(missing_channels, start=1):
                buttons.append([Button.url(f"🔗 الاشتراك بالقناة {index}", f"https://t.me/{ch.replace('@', '')}")])
            buttons.append([Button.inline("🔄 تم الاشتراك (تأكيد)", data="check_sub")])
            buttons.extend(user_buttons)
            
            text = "⚠️ **عذراً عزيزي، يجب عليك الاشتراك في القنوات أولاً لتتمكن من التفاعل في المجموعات المحمية.**"
            
            if BOT_CONFIG["user_media"]:
                await bot_client.send_file(event.chat_id, BOT_CONFIG["user_media"], caption=text, buttons=buttons)
            else:
                await event.respond(text, buttons=buttons)
        else:
            welcome_text = BOT_CONFIG["user_welcome"]
            if BOT_CONFIG["user_media"]:
                await bot_client.send_file(event.chat_id, BOT_CONFIG["user_media"], caption=welcome_text, buttons=user_buttons)
            else:
                await event.respond(welcome_text, buttons=user_buttons)

# نظام إعداد تعيين قنوات الاشتراك الإجباري للمستخدمين داخل مجموعاتهم الخاصة
@bot_client.on(events.NewMessage)
async def group_admin_commands_handler(event):
    if not (event.is_group or event.is_channel):
        return

    text = event.text.strip()
    chat_id = event.chat_id
    user_id = event.sender_id

    is_set_command = text.startswith('/setsub') or text.startswith('تعيين اشتراك') or text.startswith('اضف')
    is_delete_command = text.startswith('/delsub') or text.startswith('مسح الاشتراك') or text.startswith('حذف')

    if not (is_set_command or is_delete_command):
        return

    if not await is_user_admin(chat_id, user_id):
        warn = await event.reply("⚠️ **عذراً، هذا الأمر مخصص فقط لمشرفي المجموعة!**")
        await asyncio.sleep(10)
        try:
            await event.delete()
            await warn.delete()
        except Exception:
            pass
        return

    # معالجة أمر التعيين والإضافة الاختيارية
    if is_set_command:
        parts = text.split(" ")
        channels = [ch.strip() for ch in parts if ch.strip().startswith("@")]
        
        if not channels:
            await event.reply("❌ **خطأ في التنسيق!** يرجى كتابة الأمر يليه معرف القناة تبدأ بـ @\n\n*يمكنك إضافة قنوات بشكل اختياري (من 1 إلى 3 قنوات максимум):*\n*مثال بقناة واحدة:* `تعيين اشتراك @MyChannel`\n*مثال بقناتين:* `اضف @Ch1 @Ch2`")
            return
            
        # حفظ القنوات بشكل اختياري حسب مدخلات المستخدم (بحد أقصى 3)
        BOT_CONFIG["user_channels"][chat_id] = channels[:3]
        current_subs = ", ".join(BOT_CONFIG["user_channels"][chat_id])
        await event.reply(f"✅ **تم حفظ قنوات الاشتراك الإجباري الاختيارية لهذه المجموعة بنجاح!**\n📢 القنوات النشطة حالياً: {current_subs}\n\n*سيتم الآن إجبار الأعضاء على الاشتراك بها قبل التمكن من الكتابة.*")

    # معالجة أمر الحذف والمسح الكامل
    elif is_delete_command:
        if chat_id in BOT_CONFIG["user_channels"]:
            BOT_CONFIG["user_channels"].pop(chat_id, None)
            await event.reply("❌ **تم حذف ومسح قنوات الاشتراك الإجباري لهذه المجموعة بنجاح!**\nيمكن الآن لجميع الأعضاء الكتابة بحرية دون أي قيود اشتراك.")
        else:
            await event.reply("⚠️ **لا توجد قنوات اشتراك إجباري معينة لهذه المجموعة ليتم حذفها.**")

# التفاعل مع الأزرار الشفافة (لوحة التحكم + تأكيد الاشتراك + فتح الإعدادات للمطور)
@bot_client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    
    if data == "check_sub":
        missing_channels = await check_subscription(user_id)
        
        if missing_channels:
            buttons = []
            for index, ch in enumerate(missing_channels, start=1):
                buttons.append([Button.url(f"🔗 الاشتراك بالقناة {index}", f"https://t.me/{ch.replace('@', '')}")])
            buttons.append([Button.inline("🔄 تم الاشتراك (تأكيد)", data="check_sub")])
            buttons.append([Button.url("👨‍💻 مطور البوت", f"https://t.me/{DEV_USERNAME.replace('@', '')}")])
            buttons.append([Button.url("📢 قناة السورس", f"https://t.me/{SOURCE_CHANNEL.replace('@', '')}")])
            if user_id == DEVELOPER_ID:
                buttons.append([Button.inline("⚙️ الإعدادات (خاص بالمطور)", data="admin_open_panel")])
            
            await event.answer("❌ أنت لم تشترك في جميع القنوات بعد!", alert=True)
            text = "⚠️ **ما زلت غير مشترك في بعض القنوات الإلزامية!**"
            await event.edit(text, buttons=buttons)
        else:
            await event.answer("✅ تم التحقق بنجاح! شكراً لك.", alert=True)
            welcome_text = BOT_CONFIG["user_welcome"]
            user_buttons = [
                [Button.url("👨‍💻 مطور البوت", f"https://t.me/{DEV_USERNAME.replace('@', '')}")],
                [Button.url("📢 قناة السورس", f"https://t.me/{SOURCE_CHANNEL.replace('@', '')}")]
            ]
            if user_id == DEVELOPER_ID:
                user_buttons.append([Button.inline("⚙️ الإعدادات (خاص بالمطور)", data="admin_open_panel")])
            try:
                await event.delete()
            except Exception:
                pass
            if BOT_CONFIG["user_media"]:
                await bot_client.send_file(event.chat_id, BOT_CONFIG["user_media"], caption=welcome_text, buttons=user_buttons)
            else:
                await bot_client.send_message(event.chat_id, welcome_text, buttons=user_buttons)
        return

    # فتح لوحة التحكم من خلال زر الإعدادات السري للمطور
    if data == "admin_open_panel":
        if user_id != DEVELOPER_ID:
            await event.answer("⚠️ عذراً، هذا الزر مخصص للمطور فقط.", alert=True)
            return
        await send_admin_panel(event, edit=True)
        return

    if user_id != DEVELOPER_ID:
        await event.answer("⚠️ عذراً، هذه اللوحة مخصصة للمطور فقط.", alert=True)
        return

    if data == "admin_stats":
        total_users = len(BOT_CONFIG["stats_users"])
        total_groups = len(BOT_CONFIG["stats_groups"])
        current_ch = ", ".join(BOT_CONFIG["channels"]) if BOT_CONFIG["channels"] else "لا يوجد (لم يتم تعيين قنوات)"
        
        stats_msg = (
            f"📊 **إحصائيات الخادم والبوت الشاملة:**\n\n"
            f"👥 عدد مستخدمي البوت في الخاص: `{total_users}`\n"
            f"🛡️ عدد المجموعات المحمية النشطة: `{total_groups}`\n"
            f"📢 القنوات المربوطة حالياً للمطور: `{current_ch}`\n"
            f"🖼️ ميديا المستخدمين: `{'مفعلة ✅' if BOT_CONFIG['user_media'] else 'غير مفعلة ❌'}`\n"
            f"⚙️ ميديا لوحة التحكم: `{'مفعلة ✅' if BOT_CONFIG['admin_media'] else 'غير مفعلة ❌'}`"
        )
        await event.answer("تم جلب الإحصائيات الحالية", alert=False)
        await event.edit(stats_msg, buttons=[[Button.inline("🔙 العودة للوحة التحكم", data="admin_back")]])

    elif data == "admin_set_channels":
        BOT_CONFIG["awaiting_input"][user_id] = "set_channels"
        await event.edit("📢 **قم بإرسال معرفات قنوات المطور الآن بشكل اختياري (من 1 إلى 3 قنوات)**\nتفصل بينها بمسافة واحدة فقط.\n\nمثال لقناة واحدة:\n`@MyChannel`\nمثال لثلاث قنوات:\n`@Ch1 @Ch2 @Ch3`", buttons=[[Button.inline("❌ إلغاء", data="admin_back")]])

    elif data == "admin_media_user":
        BOT_CONFIG["awaiting_input"][user_id] = "media_user"
        await event.edit("🖼️ **قم بإرسال الصورة أو الفيديو لواجهة المستخدمين مباشرة الآن (كصورة/فيديو وليس كملف)**:", buttons=[[Button.inline("❌ إلغاء", data="admin_back")]])

    elif data == "admin_media_admin":
        BOT_CONFIG["awaiting_input"][user_id] = "media_admin"
        await event.edit("⚙️ **قم بإرسال الصورة أو الفيديو للوحة التحكم مباشرة الآن (كصورة/فيديو وليس كملف)**:", buttons=[[Button.inline("❌ إلغاء", data="admin_back")]])

    elif data == "admin_set_welcome":
        BOT_CONFIG["awaiting_input"][user_id] = "set_welcome"
        await event.edit("📝 **قم بإرسال رسالة الترحيب الجديدة واجهة المستخدمين الآن**:", buttons=[[Button.inline("❌ إلغاء", data="admin_back")]])

    elif data == "admin_back":
        BOT_CONFIG["awaiting_input"].pop(user_id, None)
        await send_admin_panel(event, edit=True)

    elif data == "admin_to_user_interface":
        BOT_CONFIG["awaiting_input"].pop(user_id, None)
        try:
            await event.delete()
        except Exception:
            pass
        # إعادة المطور لواجهة المستخدمين العادية مع الحفاظ على زر الإعدادات
        welcome_text = BOT_CONFIG["user_welcome"]
        user_buttons = [
            [Button.url("👨‍💻 مطور البوت", f"https://t.me/{DEV_USERNAME.replace('@', '')}")],
            [Button.url("📢 قناة السورس", f"https://t.me/{SOURCE_CHANNEL.replace('@', '')}")],
            [Button.inline("⚙️ الإعدادات (خاص بالمطور)", data="admin_open_panel")]
        ]
        if BOT_CONFIG["user_media"]:
            await bot_client.send_file(event.chat_id, BOT_CONFIG["user_media"], caption=welcome_text, buttons=user_buttons)
        else:
            await bot_client.send_message(event.chat_id, welcome_text, buttons=user_buttons)

    elif data == "admin_close":
        BOT_CONFIG["awaiting_input"].pop(user_id, None)
        await event.delete()

# استقبال الرسائل النصية والميديا الخاصة بالمدخلات للمطور في الخاص
@bot_client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def admin_input_handler(event):
    user_id = event.sender_id
    if user_id != DEVELOPER_ID or user_id not in BOT_CONFIG["awaiting_input"]:
        return

    action = BOT_CONFIG["awaiting_input"][user_id]

    if action == "set_channels":
        text = event.text.strip()
        channels = [ch.strip() for ch in text.split(" ") if ch.strip().startswith("@")]
        if not channels:
            await event.respond("❌ عذراً، المعرفات المرسلة غير صالحة. يرجى إرسال المعرفات تبدأ بـ @")
            return
        
        # حفظ القنوات اختيارياً من 1 إلى 3 قنوات بنجاح
        BOT_CONFIG["channels"] = channels[:3]
        BOT_CONFIG["awaiting_input"].pop(user_id, None)
        await event.respond(f"✅ تم حفظ قنوات الاشتراك الإجباري للمطور بنجاح!\nالقنوات الحالية النشطة: {', '.join(BOT_CONFIG['channels'])}")
        await send_admin_panel(event, edit=False)

    elif action == "media_user":
        if event.photo or event.video:
            media = event.photo if event.photo else event.video
            BOT_CONFIG["user_media"] = media
            BOT_CONFIG["awaiting_input"].pop(user_id, None)
            await event.respond("✅ تم تعيين وحفظ ميديا واجهة المستخدمين بنجاح!")
            await send_admin_panel(event, edit=False)
        else:
            await event.respond("⚠️ يرجى إرسال الميديا كفيديو أو كصورة مباشرة وليس كملف مضغوط أو مستند!")

    elif action == "media_admin":
        if event.photo or event.video:
            media = event.photo if event.photo else event.video
            BOT_CONFIG["admin_media"] = media
            BOT_CONFIG["awaiting_input"].pop(user_id, None)
            await event.respond("✅ تم تعيين وحفظ ميديا لوحة تحكم المطور بنجاح!")
            await send_admin_panel(event, edit=False)
        else:
            await event.respond("⚠️ يرجى إرسال الميديا كفيديو أو كصورة مباشرة وليس كملف مضغوط أو مستند!")

    elif action == "set_welcome":
        BOT_CONFIG["user_welcome"] = event.text
        BOT_CONFIG["awaiting_input"].pop(user_id, None)
        await event.respond("✅ تم تحديث رسالة ترحيب المستخدمين بنجاح!")
        await send_admin_panel(event, edit=False)

# --- 6. نظام حماية المجموعات (الاشتراك الإجباري المطور) ---
@bot_client.on(events.NewMessage)
async def group_protection_handler(event):
    if event.is_group or event.is_channel:
        text = event.text.strip()
        
        # تجنب اعتراض أوامر التعيين والحذف أو أمر start
        if text.startswith('/start') or text.startswith('/setsub') or text.startswith('تعيين اشتراك') or text.startswith('اضف') or text.startswith('/delsub') or text.startswith('مسح الاشتراك') or text.startswith('حذف'):
            return
            
        user_id = event.sender_id
        chat_id = event.chat_id
        
        BOT_CONFIG["stats_groups"].add(chat_id)
        
        if not user_id or event.sender_id == (await bot_client.get_me()).id:
            return
            
        if await is_user_admin(chat_id, user_id):
            return
            
        # هنا يتم فحص القنوات الاختيارية التي تم تعيينها من قبل مستخدمي/أدمنز هذه المجموعة تحديداً
        missing_channels = await check_group_subscription(chat_id, user_id)
        
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

# --- 7. آلية التشغيل المعزولة تماماً وخارج نطاق خيوط Streamlit ---
def run_isolated_bot():
    isolated_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(isolated_loop)
    
    bot_client.start(bot_token=BOT_TOKEN)
    isolated_loop.run_until_complete(bot_client.run_until_disconnected())

if 'bot_process_active' not in st.session_state:
    st.session_state['bot_process_active'] = True
    backend_thread = Thread(target=run_isolated_bot, daemon=True)
    backend_thread.start()
