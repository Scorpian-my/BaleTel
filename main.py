import asyncio
import os
from dotenv import load_dotenv
from balethon import Client
from balethon.conditions import private
from balethon.objects import InlineKeyboard
from telethon import TelegramClient
from telethon.events import NewMessage
from config.config import config
from filters.filters import auto_filtersّ
from handler.handlers import (
    user_pages,
    user_send_target,
    user_info_request,
    user_info_target,
    auto_manual_request,
    admin_add_request,
    build_page,
    main_menu,
    settings_menu,
    bot_manage_menu,
    admin_list_menu,
)


load_dotenv()

tele = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
bot = Client(config.TOKEN)


async def get_list(list_type):
    dialogs = await tele.get_dialogs()
    result = []

    for d in dialogs:
        if (
            list_type == "channels"
            and d.is_channel
            and not getattr(d.entity, "megagroup", False)
        ):
            result.append((d.name, d.entity.id))
        if list_type == "users" and d.is_user and not d.entity.bot:
            name = f"{d.entity.first_name or ''} {d.entity.last_name or ''}".strip()
            result.append((name, d.entity.id))
        if list_type == "bots" and d.is_user and d.entity.bot:
            result.append((d.name, d.entity.id))
        if list_type == "groups" and (
            d.is_group or (d.is_channel and getattr(d.entity, "megagroup", False))
        ):
            result.append((d.name, d.entity.id))

    return result


async def show_page(chat_id, msg_id):
    info = user_pages.get(chat_id)
    if not info:
        return

    list_type = info["type"]
    page = info["page"]
    items = await get_list(list_type)
    keyboard = build_page(items, page)

    title_map = {
        "channels": "📢 لیست کانال‌ها",
        "users": "👤 لیست پیوی‌ها",
        "bots": "🤖 لیست ربات‌ها",
        "groups": "👥 لیست گروه‌ها",
    }

    await bot.edit_message_text(
        chat_id,
        msg_id,
        f"{title_map[list_type]} (صفحه {page + 1})",
        InlineKeyboard(*keyboard),
    )


async def send_to_all_admins_text(text: str):
    for admin_id in config.ADMINS:
        try:
            await bot.send_message(admin_id, text)
        except:
            pass


async def send_to_all_admins_media(kind: str, path: str, *args):
    for admin_id in config.ADMINS:
        try:
            if kind == "photo":
                await bot.send_photo(admin_id, path, *args)
            elif kind == "video":
                await bot.send_video(admin_id, path, *args)
            elif kind == "voice":
                await bot.send_voice(admin_id, path, *args)
            elif kind == "audio":
                await bot.send_audio(admin_id, path, *args)
            elif kind == "document":
                await bot.send_document(admin_id, path, *args)
        except:
            pass


async def forward_to_bale(event, chat):
    try:
        name = getattr(chat, "title", None) or getattr(chat, "first_name", "ناشناس")
    except Exception:
        name = "ناشناس"

    msg = event.message
    caption = msg.message or ""
    raw_text = event.raw_text or ""
    header = f"📩 پیام جدید از: {name}\n\n"

    if not (
        msg.photo
        or getattr(msg, "video", None)
        or getattr(msg, "voice", None)
        or getattr(msg, "audio", None)
        or getattr(msg, "document", None)
    ):
        text = header + (raw_text or "[پیام غیرمتنی]")
        await send_to_all_admins_text(text)
        return

    path = await msg.download_media()
    if not path:
        text = header + (caption or raw_text or "[پیام مدیا، اما دانلود نشد]")
        await send_to_all_admins_text(text)
        return

    try:
        if msg.photo:
            await send_to_all_admins_media(
                "photo", path, header + (caption or raw_text or "")
            )
        elif getattr(msg, "video", None):
            v = msg.video
            duration = getattr(v, "duration", 0) or 0
            width = getattr(v, "w", 0) or 0
            height = getattr(v, "h", 0) or 0
            await send_to_all_admins_media(
                "video",
                path,
                duration,
                width,
                height,
                header + (caption or raw_text or ""),
            )
        elif getattr(msg, "voice", None):
            v = msg.voice
            duration = getattr(v, "duration", 0) or 0
            await send_to_all_admins_media(
                "voice", path, header + (caption or raw_text or ""), duration, None
            )
        elif getattr(msg, "audio", None):
            a = msg.audio
            duration = getattr(a, "duration", 0) or 0
            title = getattr(a, "title", None) or "Audio"
            await send_to_all_admins_media(
                "audio",
                path,
                header + (caption or raw_text or ""),
                duration,
                title,
                None,
            )
        elif getattr(msg, "document", None):
            await send_to_all_admins_media(
                "document", path, header + (caption or raw_text or "")
            )
    except Exception as e:
        print("خطا در ارسال مدیا به بله:", e)
        text = header + (caption or raw_text or "[پیام مدیا، اما ارسال نشد]")
        await send_to_all_admins_text(text)
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass

@tele.on(NewMessage)
async def handler_new_message(event):
    cfg = auto_filters["global"]
    if not cfg["enabled"]:
        return

    try:
        chat = await event.get_chat()
    except Exception:
        return

    chat_id = chat.id

    if cfg["all"]:
        await forward_to_bale(event, chat)
        return
    if chat_id in cfg["manual"]:
        await forward_to_bale(event, chat)
        return
    if event.is_private and not getattr(chat, "bot", False):
        if cfg["users"]:
            await forward_to_bale(event, chat)
        return
    if event.is_private and getattr(chat, "bot", False):
        if cfg["bots"]:
            await forward_to_bale(event, chat)
        return
    if getattr(chat, "megagroup", False) or getattr(chat, "gigagroup", False):
        if cfg["groups"]:
            await forward_to_bale(event, chat)
        return
    if getattr(chat, "broadcast", False):
        if cfg["channels"]:
            await forward_to_bale(event, chat)
        return


@bot.on_message(private)
async def handle_message(message):
    chat_id = message.author.id
    if chat_id not in config.ADMINS:
        await message.reply("❌ دسترسی شما رد شد")
        return

    if chat_id in admin_add_request:
        if chat_id != config.MAIN_ADMIN_ID:
            admin_add_request.remove(chat_id)
            await message.reply("❌ فقط ادمین اصلی می‌تواند ادمین جدید اضافه کند!")
            return
        
        admin_add_request.remove(chat_id)
        text_id = message.text.strip()
        try:
            new_admin_id = int(text_id)
            
            if new_admin_id in config.ADMINS:
                await message.reply(f"⚠️ کاربر با آیدی {new_admin_id} قبلاً ادمین است!")
                return
            
            if new_admin_id == config.MAIN_ADMIN_ID:
                await message.reply("❌ این آیدی مربوط به ادمین اصلی است!")
                return
            
            config.ADMINS.add(new_admin_id)
            await message.reply(f"✔ ادمین جدید با آیدی {new_admin_id} اضافه شد.")
            
            try:
                await bot.send_message(new_admin_id, "🎉 به جمع ادمین‌های ربات خوش آمدید!")
            except:
                pass
                
        except Exception:
            await message.reply("❌ آیدی عددی معتبر نیست.")
        return

    if chat_id in auto_manual_request:
        query = message.text.strip()
        del auto_manual_request[chat_id]
        try:
            info = await tele.get_entity(query)
            uid = info.id
            auto_filters["global"]["manual"].add(uid)
            name = getattr(info, "title", None) or getattr(info, "first_name", "ناشناس")
            await message.reply(f"✔ چت «{name}» با آیدی {uid} به لیست دستی اضافه شد.")
        except Exception:
            await message.reply("❌ آیدی، یوزرنیم یا لینک معتبر نیست.")
        return

    if chat_id in user_send_target:
        target = user_send_target[chat_id]
        await tele.send_message(target, message.text)
        await message.reply("پیام با موفقیت ارسال شد ✔️")
        del user_send_target[chat_id]
        return

    if chat_id in user_info_request:
        query = message.text.strip()
        del user_info_request[chat_id]

        if "t.me/" in query:
            try:
                info = await tele.get_entity(query)
                name = getattr(info, "title", None) or getattr(
                    info, "first_name", "ناشناس"
                )
                is_channel = getattr(info, "broadcast", False)
                is_group = getattr(info, "megagroup", False)
                try:
                    participants = await tele.get_participants(info)
                    count = len(participants)
                except:
                    count = "نامشخص"
                joined = False
                try:
                    await tele.get_permissions(info, "me")
                    joined = True
                except:
                    joined = False

                text = f"📌 مشخصات:\n\nنام: {name}\nآیدی: {info.id}\nنوع: {'کانال' if is_channel and not is_group else 'گروه'}\nتعداد اعضا: {count}\n"
                keyboard = (
                    InlineKeyboard([("درحال حاضر عضو هستید", "none")])
                    if joined
                    else InlineKeyboard([("جوین", f"join-{info.id}")])
                )
                await message.reply(text, keyboard)
                return
            except Exception:
                await message.reply("❌ لینک معتبر نیست.")
                return

        try:
            info = await tele.get_entity(query)
            name = getattr(info, "first_name", None) or getattr(info, "title", "ناشناس")
            username = getattr(info, "username", None)
            uid = info.id
            is_bot = getattr(info, "bot", False)

            text = f"📌 مشخصات کاربر:\n\nنام: {name}\n"
            text += f"یوزرنیم: @{username}\n" if username else "یوزرنیم: ندارد\n"
            text += f"آیدی: {uid}\nنوع: {'ربات' if is_bot else 'کاربر'}\n"

            user_info_target[chat_id] = uid
            await message.reply(text, InlineKeyboard([("ارسال پیام", "send-to-user")]))
            return
        except Exception:
            await message.reply("❌ آیدی یا یوزرنیم معتبر نیست.")
            return

    text, keyboard = main_menu()
    await message.reply(text, keyboard)


@bot.on_callback_query()
async def callback(callback_query):
    chat_id = callback_query.message.chat.id
    msg_id = callback_query.message.id
    data = callback_query.data

    if chat_id not in config.ADMINS:
        await callback_query.answer("❌ دسترسی شما رد شد", show_alert=True)
        return

    if data == "back-main":
        text, keyboard = main_menu()
        await bot.edit_message_text(chat_id, msg_id, text, keyboard)
        return

    if data == "settings":
        text, keyboard = settings_menu(auto_filters["global"])
        await bot.edit_message_text(chat_id, msg_id, text, keyboard)
        return

    if data == "bot-manage":
        text, keyboard = bot_manage_menu(chat_id)
        await bot.edit_message_text(chat_id, msg_id, text, keyboard)
        return

    if data == "admin-list":
        text, keyboard = admin_list_menu(config.ADMINS, config.MAIN_ADMIN_ID)
        await bot.edit_message_text(chat_id, msg_id, text, keyboard)
        return

    if data == "admin-add":
        if chat_id != config.MAIN_ADMIN_ID:
            await callback_query.answer("❌ فقط ادمین اصلی می‌تواند ادمین اضافه کند!", show_alert=True)
            return
        
        admin_add_request.add(chat_id)
        await bot.edit_message_text(
            chat_id,
            msg_id,
            "آیدی عددی ادمین جدید را ارسال کنید:",
            InlineKeyboard([("بازگشت ⬅️", "bot-manage")]),
        )
        return

    if data == "admin-remove":
        if chat_id != config.MAIN_ADMIN_ID:
            await callback_query.answer("❌ فقط ادمین اصلی می‌تواند ادمین حذف کند!", show_alert=True)
            return
        
        if len(config.ADMINS) <= 1:
            await bot.edit_message_text(
                chat_id,
                msg_id,
                "❗ فقط یک ادمین وجود دارد و نمی‌توان آن را حذف کرد.",
                InlineKeyboard([("بازگشت ⬅️", "bot-manage")]),
            )
            return
        
        keyboard = []
        for admin_id in config.ADMINS:
            if admin_id != config.MAIN_ADMIN_ID:
                keyboard.append([(f"❌ حذف {admin_id}", f"deladmin-{admin_id}")])
        
        if not keyboard:
            await bot.edit_message_text(
                chat_id,
                msg_id,
                "❗ هیچ ادمین دیگری برای حذف وجود ندارد.",
                InlineKeyboard([("بازگشت ⬅️", "bot-manage")]),
            )
            return
            
        keyboard.append([("بازگشت ⬅️", "bot-manage")])
        await bot.edit_message_text(
            chat_id, msg_id, "🗑 ادمین‌ها برای حذف:", InlineKeyboard(*keyboard)
        )
        return

    if data.startswith("deladmin-"):
        if chat_id != config.MAIN_ADMIN_ID:
            await callback_query.answer("❌ فقط ادمین اصلی می‌تواند ادمین حذف کند!", show_alert=True)
            return
        
        aid = int(data.replace("deladmin-", ""))
        
        if aid == config.MAIN_ADMIN_ID:
            await bot.edit_message_text(
                chat_id,
                msg_id,
                "❌ نمی‌توانید ادمین اصلی را حذف کنید!",
                InlineKeyboard([("بازگشت ⬅️", "bot-manage")]),
            )
            return
        
        if aid in config.ADMINS and len(config.ADMINS) > 1:
            config.ADMINS.remove(aid)
            await bot.edit_message_text(
                chat_id,
                msg_id,
                f"✔ ادمین با آیدی {aid} با موفقیت حذف شد.",
                InlineKeyboard(
                    [("🔄 بازنشانی لیست", "admin-remove")], 
                    [("بازگشت ⬅️", "bot-manage")]
                ),
            )
        else:
            await bot.edit_message_text(
                chat_id,
                msg_id,
                "❌ حذف ادمین امکان‌پذیر نیست.",
                InlineKeyboard([("بازگشت ⬅️", "bot-manage")]),
            )
        return

    if data == "toggle-auto-main":
        auto_filters["global"]["enabled"] = not auto_filters["global"]["enabled"]
        text, keyboard = settings_menu(auto_filters["global"])
        await bot.edit_message_text(chat_id, msg_id, text, keyboard)
        return

    if data in [
        "toggle-auto-users",
        "toggle-auto-groups",
        "toggle-auto-channels",
        "toggle-auto-bots",
        "toggle-auto-all",
    ]:
        key = data.replace("toggle-auto-", "")
        if key == "users":
            auto_filters["global"]["users"] ^= True
        elif key == "groups":
            auto_filters["global"]["groups"] ^= True
        elif key == "channels":
            auto_filters["global"]["channels"] ^= True
        elif key == "bots":
            auto_filters["global"]["bots"] ^= True
        elif key == "all":
            auto_filters["global"]["all"] ^= True
        text, keyboard = settings_menu(auto_filters["global"])
        await bot.edit_message_text(chat_id, msg_id, text, keyboard)
        return

    if data == "add-manual-auto":
        auto_manual_request[chat_id] = True
        await bot.edit_message_text(
            chat_id,
            msg_id,
            "لطفاً آیدی عددی، یوزرنیم یا لینک گروه/کانال/چت تلگرام را برای افزودن دستی ارسال کنید:",
            InlineKeyboard([("بازگشت ⬅️", "settings")]),
        )
        return

    if data == "remove-manual-auto":
        manual_list = list(auto_filters["global"]["manual"])
        if not manual_list:
            await bot.edit_message_text(
                chat_id,
                msg_id,
                "❗ هیچ مورد دستی برای حذف وجود ندارد.",
                InlineKeyboard([("بازگشت ⬅️", "settings")]),
            )
            return
        keyboard = []
        for uid in manual_list:
            try:
                entity = await tele.get_entity(uid)
                name = getattr(entity, "title", None) or getattr(
                    entity, "first_name", "ناشناس"
                )
            except:
                name = f"آیدی {uid}"
            keyboard.append([(f"❌ حذف {name}", f"delmanual-{uid}")])
        keyboard.append([("بازگشت ⬅️", "settings")])
        await bot.edit_message_text(
            chat_id, msg_id, "🗑 موارد دستی برای حذف:", InlineKeyboard(*keyboard)
        )
        return

    if data.startswith("delmanual-"):
        uid = int(data.replace("delmanual-", ""))
        if uid in auto_filters["global"]["manual"]:
            auto_filters["global"]["manual"].remove(uid)
        await bot.edit_message_text(
            chat_id,
            msg_id,
            "✔ مورد دستی با موفقیت حذف شد.",
            InlineKeyboard(
                [("🔄 بازنشانی لیست", "remove-manual-auto")], [("بازگشت ⬅️", "settings")]
            ),
        )
        return

    if data == "get-info":
        user_info_request[chat_id] = True
        await bot.edit_message_text(
            chat_id,
            msg_id,
            "لطفاً آیدی عددی، یوزرنیم یا لینک گروه/کانال را ارسال کنید:",
            InlineKeyboard([("بازگشت ⬅️", "back-main")]),
        )
        return

    if data == "send-to-user":
        uid = user_info_target.get(chat_id)
        if not uid:
            await callback_query.answer("خطا در یافتن کاربر")
            return
        user_send_target[chat_id] = uid
        await bot.edit_message_text(
            chat_id,
            msg_id,
            "پیام خود را بنویسید:",
            InlineKeyboard([("بازگشت ⬅️", "back-main")]),
        )
        return

    if data.startswith("join-"):
        gid = int(data.replace("join-", ""))
        try:
            entity = await tele.get_entity(gid)
            await tele.join_channel(entity)
            await bot.edit_message_text(
                chat_id,
                msg_id,
                "✔ با موفقیت عضو شدید",
                InlineKeyboard([("بازگشت ⬅️", "back-main")]),
            )
        except Exception:
            await bot.edit_message_text(
                chat_id,
                msg_id,
                "❌ امکان جوین وجود ندارد",
                InlineKeyboard([("بازگشت ⬅️", "back-main")]),
            )
        return

    if data == "get-msg":
        await bot.edit_message_text(
            chat_id,
            msg_id,
            "نوع پیام‌هایی که می‌خواهی دریافت کنی را انتخاب کن:",
            InlineKeyboard(
                [("پیوی‌ها", "users")],
                [("کانال‌ها", "channels")],
                [("گروه‌ها", "groups")],
                [("ربات‌ها", "bots")],
                [("بازگشت ⬅️", "back-main")],
            ),
        )
        return

    if data == "send-msg":
        await bot.edit_message_text(
            chat_id,
            msg_id,
            "پیام را به کجا می‌خواهی ارسال کنی؟",
            InlineKeyboard(
                [("پیوی‌ها", "send-users")],
                [("کانال‌ها", "send-channels")],
                [("گروه‌ها", "send-groups")],
                [("ربات‌ها", "send-bots")],
                [("بازگشت ⬅️", "back-main")],
            ),
        )
        return

    if data in ["channels", "users", "bots", "groups"]:
        user_pages[chat_id] = {"type": data, "page": 0, "send_mode": False}
        await show_page(chat_id, msg_id)
        return

    if data in ["send-channels", "send-users", "send-bots", "send-groups"]:
        list_type = data.replace("send-", "")
        user_pages[chat_id] = {"type": list_type, "page": 0, "send_mode": True}
        await show_page(chat_id, msg_id)
        return

    if data == "next":
        user_pages[chat_id]["page"] += 1
        await show_page(chat_id, msg_id)
        return

    if data == "prev":
        user_pages[chat_id]["page"] -= 1
        await show_page(chat_id, msg_id)
        return

    if data.startswith("open-"):
        uid = int(data.replace("open-", ""))
        if user_pages.get(chat_id, {}).get("send_mode"):
            user_send_target[chat_id] = uid
            await bot.edit_message_text(
                chat_id,
                msg_id,
                "لطفاً پیام خود را ارسال کنید:",
                InlineKeyboard([("بازگشت ⬅️", "back-main")]),
            )
            return
        messages = await tele.get_messages(uid, limit=50)
        text = "50 پیام آخر:\n\n"
        for m in reversed(messages):
            text += f"- {m.text or '[پیام غیرمتنی]'}\n"
        await bot.edit_message_text(
            chat_id, msg_id, text, InlineKeyboard([("بازگشت ⬅️", "back-main")])
        )
        return


async def init_tele():
    await tele.connect()
    if not await tele.is_user_authorized():
        print("⚠️ لطفاً یک‌بار به‌صورت دستی سشن را لاگین کن.")
        return False
    return True


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    if loop.run_until_complete(init_tele()):
        print("✅ ربات با موفقیت شروع به کار کرد...")
        bot.run()
    else:
        print("❌ اتصال به تلگرام برقرار نشد.")