from balethon.objects import InlineKeyboard
from config.config import config

user_pages = {}
user_send_target = {}
user_info_request = {}
user_info_target = {}
auto_manual_request = {}
admin_add_request = set()

def build_page(items, page, per_page=10):
    start = page * per_page
    end = start + per_page
    sliced = items[start:end]
    keyboard = []
    for title, uid in sliced:
        keyboard.append([(title, f"open-{uid}")])
    nav = []
    if page > 0:
        nav.append(("⬅️ قبلی", "prev"))
    if end < len(items):
        nav.append(("بعدی ➡️", "next"))
    if nav:
        keyboard.append(nav)
    keyboard.append([("بازگشت ⬅️", "back-main")])
    return keyboard

def main_menu():
    return (
        "یک گزینه انتخاب کنید:",
        InlineKeyboard(
            [("📥 دریافت پیام از تلگرام", "get-msg")],
            [("📤 ارسال پیام به تلگرام", "send-msg")],
            [("🧾 دریافت مشخصات", "get-info")],
            [("⚙️ تنظیمات دریافت خودکار", "settings")],
            [("🛠 مدیریت ربات", "bot-manage")],
        ),
    )

def settings_menu(cfg):
    state_main = "روشن" if cfg["enabled"] else "خاموش"
    state_users = "روشن" if cfg["users"] else "خاموش"
    state_groups = "روشن" if cfg["groups"] else "خاموش"
    state_channels = "روشن" if cfg["channels"] else "خاموش"
    state_bots = "روشن" if cfg["bots"] else "خاموش"
    state_all = "روشن" if cfg["all"] else "خاموش"

    text = (
        "تنظیمات دریافت خودکار پیام‌ها:\n\n"
        f"وضعیت کلی: {state_main}\n"
        f"پیوی‌ها: {state_users}\n"
        f"گروه‌ها: {state_groups}\n"
        f"کانال‌ها: {state_channels}\n"
        f"ربات‌ها: {state_bots}\n"
        f"همه: {state_all}\n\n"
        "توضیح:\n"
        "- اگر «همه» روشن باشد، از تمام چت‌ها پیام می‌آید.\n"
        "- اگر «همه» خاموش باشد، فقط بر اساس فیلترها و موارد دستی پیام می‌آید.\n"
        "- پیام‌ها برای تمام ادمین‌های ثبت‌شده ارسال می‌شوند."
    )

    keyboard = InlineKeyboard(
        [(f"دریافت خودکار: {state_main}", "toggle-auto-main")],
        [(f"پیوی‌ها: {state_users}", "toggle-auto-users")],
        [(f"گروه‌ها: {state_groups}", "toggle-auto-groups")],
        [(f"کانال‌ها: {state_channels}", "toggle-auto-channels")],
        [(f"ربات‌ها: {state_bots}", "toggle-auto-bots")],
        [(f"همه: {state_all}", "toggle-auto-all")],
        [("➕ افزودن دستی چت", "add-manual-auto")],
        [("🗑 حذف موارد دستی چت", "remove-manual-auto")],
        [("بازگشت ⬅️", "back-main")],
    )
    return text, keyboard

def bot_manage_menu(chat_id):
    """منوی مدیریت ربات - فقط ادمین اصلی دسترسی کامل دارد"""
    is_main_admin = (chat_id == config.MAIN_ADMIN_ID)
    
    text = "مدیریت ربات:\n\n"
    
    if is_main_admin:
        text += "👑 شما ادمین اصلی هستید\n\n✅ می‌توانید:\n• ادمین جدید اضافه کنید\n• ادمین حذف کنید\n• لیست ادمین‌ها را ببینید\n\n"
        keyboard = InlineKeyboard(
            [("➕ افزودن ادمین جدید", "admin-add")],
            [("🗑 حذف ادمین", "admin-remove")],
            [("📋 لیست ادمین‌ها", "admin-list")],
            [("بازگشت ⬅️", "back-main")],
        )
    else:
        text += "👤 شما یک ادمین معمولی هستید\n\n✅ فقط می‌توانید:\n• لیست ادمین‌ها را ببینید\n\n"
        keyboard = InlineKeyboard(
            [("📋 لیست ادمین‌ها", "admin-list")],
            [("بازگشت ⬅️", "back-main")],
        )
    
    return text, keyboard

def admin_list_menu(admins, main_admin_id):
    """نمایش لیست ادمین‌ها با مشخص کردن ادمین اصلی"""
    text = "📋 لیست ادمین‌های ربات:\n━━━━━━━━━━━━━━━\n\n"
    
    for admin_id in admins:
        if admin_id == main_admin_id:
            text += f"👑 **{admin_id}** (ادمین اصلی)\n"
        else:
            text += f"👤 {admin_id}\n"
    
    text += f"\n━━━━━━━━━━━━━━━\n📊 تعداد کل: {len(admins)} ادمین"
    
    keyboard = InlineKeyboard([("🔙 بازگشت", "bot-manage")])
    
    return text, keyboard