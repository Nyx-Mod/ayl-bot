#!/usr/bin/env python3
# Telegram Account Link Bot
# Python Implementation - Enhanced with Multi-Admin Support
# create and update @x_nyx_s

import requests
import json
import time
import uuid
from datetime import datetime, timedelta
import threading

# Configuration
BOT_TOKEN = "7925127595:AAGQReL1FBeqsKNvMtxSkOsJsWllvXL_x2I"
ADMINS = {
    1065137173: 'super_admin',  # دسترسی کامل
    7329773064: 'super_admin',  # دسترسی کامل
    1690187708: 'super_admin',  # دسترسی کامل
    1234567890: 'admin',   # دسترسی محدود
}
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
CHANNEL_USERNAME = "@cpy_teel"  # Channel for membership verification

# Global variables to store bot state
bot_state = {}
account_links = {}
link_access = {}
pending_access = {}  # Store users waiting to access accounts after joining channel
user_access_history = {}  # Track user access times for rate limiting
banned_users = {}  # Changed from set to dict to store ban dates
unbanned_users = {}  # Store unbanned users with dates
link_user_details = {}  # Structure: {link_id: {'users': [user_data], 'feedback': [feedback_data]}}
user_reaction_state = {}  # Structure: {user_id: {'link_id': str, 'start_time': datetime}}
active_monitors = {}  # Store active monitoring threads

def send_telegram_request(method, parameters=None):
    """Send HTTP request to Telegram API"""
    if parameters is None:
        parameters = {}

    try:
        url = f"{API_BASE}/{method}"
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, data=json.dumps(parameters), headers=headers)
        result = response.json()
        print(f"API Request {method}: {result}")  # Debug log
        return result
    except Exception as e:
        print(f"Error sending request: {e}")
        return None

def send_message(chat_id, text, reply_markup=None):
    """Send message to chat"""
    params = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'  # Enable HTML formatting
    }

    if reply_markup:
        params['reply_markup'] = reply_markup

    print(f"Sending message to {chat_id}: {text[:50]}...")  # Debug log
    result = send_telegram_request('sendMessage', params)
    print(f"Message send result: {result}")  # Debug log
    return result

def generate_link_id():
    """Generate unique link ID"""
    return str(uuid.uuid4()).replace('-', '')[:8]

def check_channel_membership(user_id):
    """Check if user is a member of the required channel"""
    try:
        params = {
            'chat_id': CHANNEL_USERNAME,
            'user_id': user_id
        }
        response = send_telegram_request('getChatMember', params)

        print(f"Channel membership API response for user {user_id}: {response}")  # Debug log

        if response and response.get('ok'):
            status = response['result']['status']
            print(f"User {user_id} channel status: {status}")  # Debug log
            is_member = status in ['creator', 'administrator', 'member', 'restricted']
            print(f"User {user_id} is member: {is_member}")  # Debug log
            return is_member
        else:
            print(f"Channel membership check failed for user {user_id}: {response}")  # Debug log
            return False
    except Exception as e:
        print(f"Error checking channel membership for user {user_id}: {e}")
        return False

def format_datetime(dt):
    """Format datetime to string"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def create_inline_keyboard(buttons):
    """Create inline keyboard markup"""
    return {
        'inline_keyboard': buttons
    }

def is_user_banned(user_id):
    """Check if user is banned"""
    return user_id in banned_users

def is_admin(user_id):
    """Check if user is admin"""
    return user_id in ADMINS

def ban_user(user_id, banned_by_admin_id):
    """Ban a user from using the bot"""
    banned_users[user_id] = {
        'ban_date': datetime.now(),
        'banned_by': banned_by_admin_id
    }

def unban_user(user_id, unbanned_by_admin_id):
    """Unban a user from using the bot"""
    if user_id in banned_users:
        unban_data = {
            'user_id': user_id,
            'ban_date': banned_users[user_id]['ban_date'],
            'unban_date': datetime.now(),
            'unbanned_by': unbanned_by_admin_id
        }
        unbanned_users[user_id] = unban_data
        del banned_users[user_id]
        return True
    return False

def get_banned_users_text():
    """Get formatted text of banned users"""
    if not banned_users:
        return "🚫 <b>لیست بن شده‌ها خالی است!</b>"

    text = "🚫 <b>لیست کاربران بن شده</b>\n\n"
    for user_id, data in banned_users.items():
        ban_date = format_datetime(data['ban_date'])
        banned_by = data['banned_by']
        text += f"👤 <b>کاربر:</b> <code>{user_id}</code>\n"
        text += f"📅 <b>تاریخ بن:</b> {ban_date}\n"
        text += f"👑 <b>بن شده توسط:</b> {banned_by}\n"
        text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
    return text

def get_unbanned_users_text():
    """Get formatted text of unbanned users"""
    if not unbanned_users:
        return "✅ <b>لیست آنبن شده‌ها خالی است!</b>"

    text = "✅ <b>لیست کاربران آنبن شده</b>\n\n"
    for user_id, data in unbanned_users.items():
        ban_date = format_datetime(data['ban_date'])
        unban_date = format_datetime(data['unban_date'])
        unbanned_by = data['unbanned_by']
        text += f"👤 <b>کاربر:</b> <code>{user_id}</code>\n"
        text += f"📅 <b>تاریخ بن:</b> {ban_date}\n"
        text += f"🔄 <b>تاریخ آنبن:</b> {unban_date}\n"
        text += f"👑 <b>آنبن شده توسط:</b> {unbanned_by}\n"
        text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
    return text

def get_admin_main_menu():
    """Get admin main menu keyboard"""
    return create_inline_keyboard([
        [{
            'text': '🔗 ساخت لینک اکانت',
            'callback_data': 'create_link'
        }],
        [{
            'text': '🎛️ پنل مدیریت',
            'callback_data': 'admin_management'
        }]
    ])

def get_management_menu():
    """Get beautiful management menu with cards"""
    # محاسبه آمار
    today_users = 0
    today = datetime.now().date()
    for times in user_access_history.values():
        if any(t.date() == today for t in times):
            today_users += 1
    
    active_links = sum(1 for link_id in account_links if not check_link_expiry(link_id))
    
    return create_inline_keyboard([
        [{
            'text': f'👑 مدیریت ادمین‌ها ({len(ADMINS)})',
            'callback_data': 'manage_admins'
        }],
        [{
            'text': f'📊 آمار کاربران ({len(user_access_history)})',
            'callback_data': 'show_stats'
        }],
        [{
            'text': f'🔗 لینک‌های اخیر ({len(account_links)})',
            'callback_data': 'show_recent_links'
        }],
        [{
            'text': f'🚫 لیست بن شده‌ها ({len(banned_users)})',
            'callback_data': 'show_banned'
        }],
        [{
            'text': f'✅ لیست آنبن شده‌ها ({len(unbanned_users)})',
            'callback_data': 'show_unbanned'
        }],
        [{
            'text': '🏠 بازگشت به خانه',
            'callback_data': 'back_to_main'
        }]
    ])

def get_user_stats():
    """Get user statistics"""
    total_users = len(user_access_history)
    
    # کاربران فعال (در ۷ روز گذشته)
    active_users = 0
    for user_times in user_access_history.values():
        if any(time > datetime.now() - timedelta(days=7) for time in user_times):
            active_users += 1
    
    # کاربران امروز
    today_users = 0
    today = datetime.now().date()
    for times in user_access_history.values():
        if any(t.date() == today for t in times):
            today_users += 1
    
    # کل دسترسی‌ها
    total_accesses = sum(len(times) for times in user_access_history.values())
    
    text = "📊 <b>آمار کاربران ربات</b>\n\n"
    text += f"👥 <b>کاربران کل:</b> <code>{total_users}</code>\n"
    text += f"🔥 <b>کاربران امروز:</b> <code>{today_users}</code>\n"
    text += f"📈 <b>کاربران فعال (۷ روز):</b> <code>{active_users}</code>\n"
    text += f"🔄 <b>کل دسترسی‌ها:</b> <code>{total_accesses}</code>\n"
    text += f"🚫 <b>کاربران بن شده:</b> <code>{len(banned_users)}</code>\n"
    text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
    
    # ۵ کاربر پراستفاده
    if user_access_history:
        top_users = sorted(
            [(user_id, len(times)) for user_id, times in user_access_history.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        text += "\n🏆 <b>۵ کاربر پراستفاده:</b>\n"
        for i, (user_id, count) in enumerate(top_users, 1):
            text += f"  {i}. 👤 {user_id}: <code>{count} بار</code>\n"
    
    return text

def handle_admin_management(user_id, chat_id):
    """Handle admin management commands"""
    if not is_admin(user_id):
        return

    keyboard = create_inline_keyboard([
        [{'text': '➕ افزودن ادمین', 'callback_data': 'add_admin'}],
        [{'text': '➖ حذف ادمین', 'callback_data': 'remove_admin'}],
        [{'text': '📋 لیست ادمین‌ها', 'callback_data': 'list_admins'}],
        [{'text': '🔙 بازگشت', 'callback_data': 'admin_management'}],
    ])

    send_message(chat_id, "👑 <b>مدیریت ادمین‌ها</b>\n\nلطفاً یک گزینه را انتخاب کنید:", keyboard)

def handle_add_admin(user_id, chat_id, message_id):
    """Handle adding admin"""
    if user_id not in ADMINS or ADMINS[user_id] != 'super_admin':
        send_message(chat_id, "⛔ <b>شما دسترسی لازم برای افزودن ادمین را ندارید!</b>")
        return
    
    bot_state[user_id] = {
        'step': 'waiting_for_admin_id',
        'chat_id': chat_id,
        'message_id': message_id,
        'action': 'add_admin'
    }
    
    send_message(chat_id, "👤 <b>افزودن ادمین جدید</b>\n\nلطفاً آیدی عددی کاربر مورد نظر را ارسال کنید:")

def handle_remove_admin(user_id, chat_id, message_id):
    """Handle removing admin"""
    if user_id not in ADMINS or ADMINS[user_id] != 'super_admin':
        send_message(chat_id, "⛔ <b>شما دسترسی لازم برای حذف ادمین را ندارید!</b>")
        return
    
    # لیست ادمین‌ها با امکان حذف
    keyboard_buttons = []
    for admin_id, role in ADMINS.items():
        if admin_id != user_id:  # نمی‌توان خودش را حذف کند
            role_emoji = '👑' if role == 'super_admin' else '🛡️'
            keyboard_buttons.append([{
                'text': f"{role_emoji} ادمین {admin_id}",
                'callback_data': f'remove_admin_{admin_id}'
            }])
    
    keyboard_buttons.append([{'text': '🔙 بازگشت', 'callback_data': 'manage_admins'}])
    
    if len(keyboard_buttons) == 1:  # فقط دکمه بازگشت وجود دارد
        send_message(chat_id, "📭 <b>هیچ ادمینی برای حذف وجود ندارد!</b>")
        return
    
    edit_message(
        chat_id,
        message_id,
        "🗑️ <b>حذف ادمین</b>\n\nلطفاً ادمینی که می‌خواهید حذف کنید را انتخاب کنید:",
        create_inline_keyboard(keyboard_buttons)
    )

def list_admins(user_id, chat_id, message_id):
    """List all admins with beautiful cards"""
    if user_id not in ADMINS:
        send_message(chat_id, "⛔ <b>شما دسترسی لازم برای مشاهده لیست ادمین‌ها را ندارید!</b>")
        return
    
    # شماره‌گذاری ادمین‌ها
    admin_list = list(ADMINS.items())
    
    if not admin_list:
        edit_message(
            chat_id,
            message_id,
            "📭 <b>لیست ادمین‌ها خالی است!</b>",
            create_inline_keyboard([
                [{'text': '➕ افزودن ادمین', 'callback_data': 'add_admin'}],
                [{'text': '🔙 بازگشت', 'callback_data': 'manage_admins'}]
            ])
        )
        return
    
    text = "👑 <b>لیست ادمین‌های ربات</b>\n\n"
    
    for index, (admin_id, role) in enumerate(admin_list, 1):
        user_link = f"tg://user?id={admin_id}"
        role_emoji = {
            'super_admin': '👑',
            'admin': '🛡️',
            'limited_admin': '⚔️'
        }.get(role, '👤')
        
        # کارت زیبا برای هر ادمین
        text += f"<b>▫️ ادمین #{index}</b>\n"
        text += f"{role_emoji} <b>نقش:</b> {role}\n"
        text += f"🆔 <a href=\"{user_link}\"><b>{admin_id}</b></a>\n"
        
        # اگر خود کاربر باشد، علامت مخصوص بگذار
        if admin_id == user_id:
            text += "📍 <i>(شما)</i>\n"
        
        text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
    
    # آمار پایین
    super_admins = sum(1 for role in ADMINS.values() if role == 'super_admin')
    total_admins = len(ADMINS)
    
    text += f"\n📊 <b>آمار:</b> {super_admins} سوپر ادمین | {total_admins} کل ادمین‌ها"
    
    # دکمه‌های اکشن
    buttons = []
    
    if 'super_admin' in ADMINS.get(user_id, ''):
        buttons.append([
            {'text': '➕ افزودن ادمین', 'callback_data': 'add_admin'},
            {'text': '➖ حذف ادمین', 'callback_data': 'remove_admin'}
        ])
    
    buttons.append([
        {'text': '🔄 بروزرسانی', 'callback_data': 'list_admins'},
        {'text': '🔙 بازگشت', 'callback_data': 'manage_admins'}
    ])
    
    edit_message(
        chat_id,
        message_id,
        text,
        create_inline_keyboard(buttons)
    )

def handle_admin_id_input(user_id, text, chat_id):
    """Handle admin ID input for adding admin"""
    if user_id not in bot_state or bot_state[user_id]['action'] != 'add_admin':
        return
    
    try:
        new_admin_id = int(text)
        
        if new_admin_id in ADMINS:
            send_message(chat_id, "⚠️ <b>این کاربر از قبل ادمین است!</b>")
        else:
            ADMINS[new_admin_id] = 'limited_admin'  # نقش پیش‌فرض
            send_message(chat_id, f"✅ <b>کاربر با آیدی {new_admin_id} با موفقیت به لیست ادمین‌ها اضافه شد!</b>")
        
        del bot_state[user_id]
        
        # بازگشت به منوی مدیریت ادمین‌ها
        send_message(chat_id, "👑 <b>مدیریت ادمین‌ها</b>", create_inline_keyboard([
            [{'text': '➕ افزودن ادمین', 'callback_data': 'add_admin'}],
            [{'text': '➖ حذف ادمین', 'callback_data': 'remove_admin'}],
            [{'text': '📋 لیست ادمین‌ها', 'callback_data': 'list_admins'}],
            [{'text': '🔙 بازگشت', 'callback_data': 'admin_management'}],
        ]))
        
    except ValueError:
        send_message(chat_id, "❌ <b>لطفاً یک آیدی عددی معتبر وارد کنید!</b>")

def handle_start_command(message):
    """Handle /start command"""
    user_id = message['from']['id']
    chat_id = message['chat']['id']
    first_name = message['from'].get('first_name', 'کاربر')

    print(f"handle_start_command called for user {user_id}")

    if is_admin(user_id):
        send_message(
            chat_id,
            "👑 <b>سلام ادمین عزیز!</b>\n\n"
            "به پنل مدیریت ربات خوش آمدید.\n"
            "برای شروع کار یکی از گزینه‌های زیر را انتخاب کنید:",
            get_admin_main_menu()
        )
    else:
        welcome_text = (
            f"👋 <b>سلام {first_name} عزیز!</b>\n\n"
            "🎯 <b>به ربات دریافت اکانت خوش آمدید</b>\n\n"
            f"📌 برای استفاده از ربات، ابتدا باید عضو کانال {CHANNEL_USERNAME} شوید.\n\n"
            "💡 <b>نحوه کار ربات:</b>\n"
            "۱. عضویت در کانال\n"
            "۲. دریافت لینک اکانت\n"
            "۳. واکنش به پست‌ها\n"
            "۴. دریافت اکانت\n\n"
            "🚀 <i>لینک‌های اکانت از طریق لینک‌های اختصاصی در دسترس هستند.</i>"
        )
        send_message(chat_id, welcome_text)

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Edit existing message"""
    params = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        params['reply_markup'] = reply_markup
    return send_telegram_request('editMessageText', params)

def handle_callback_query(callback_query):
    """Handle button presses"""
    user_id = callback_query['from']['id']
    chat_id = callback_query['message']['chat']['id']
    message_id = callback_query['message']['message_id']
    data = callback_query['data']

    print(f"handle_callback_query called: user {user_id}, data: {data}")

    send_telegram_request('answerCallbackQuery', {
        'callback_query_id': callback_query['id']
    })

    if is_admin(user_id):
        if data.startswith('ban_left_user_'):
            user_id_to_ban = int(data.split('ban_left_user_')[1])
            ban_user(user_id_to_ban, user_id)
            edit_message(
                chat_id,
                message_id,
                f"✅ <b>کاربر با آیدی {user_id_to_ban} با موفقیت بن شد!</b>"
            )
            try:
                send_message(user_id_to_ban, "🚫 <b>شما به دلیل خروج از کانال از ربات بن شدید!</b>")
            except:
                print(f"Could not notify banned user {user_id_to_ban}")
            return

        elif data == 'manage_admins':
            handle_admin_management(user_id, chat_id)
            return
        elif data == 'add_admin':
            handle_add_admin(user_id, chat_id, message_id)
            return
        elif data == 'remove_admin':
            handle_remove_admin(user_id, chat_id, message_id)
            return
        elif data == 'list_admins':
            list_admins(user_id, chat_id, message_id)
            return
        elif data.startswith('remove_admin_'):
            admin_to_remove = int(data.split('remove_admin_')[1])
            
            if user_id not in ADMINS or ADMINS[user_id] != 'super_admin':
                send_telegram_request('answerCallbackQuery', {
                    'callback_query_id': callback_query['id'],
                    'text': '⛔ شما دسترسی لازم را ندارید!',
                    'show_alert': True
                })
                return
            
            if admin_to_remove == user_id:
                send_telegram_request('answerCallbackQuery', {
                    'callback_query_id': callback_query['id'],
                    'text': '❌ نمی‌توانید خودتان را حذف کنید!',
                    'show_alert': True
                })
                return
            
            if admin_to_remove in ADMINS:
                del ADMINS[admin_to_remove]
                send_telegram_request('answerCallbackQuery', {
                    'callback_query_id': callback_query['id'],
                    'text': f'✅ ادمین {admin_to_remove} با موفقیت حذف شد!',
                    'show_alert': True
                })
                
                # بازگشت به لیست ادمین‌ها
                list_admins(user_id, chat_id, message_id)
            return

        elif data == 'admin_management':
            # محاسبه کاربران امروز
            today_users = 0
            today = datetime.now().date()
            for times in user_access_history.values():
                if any(t.date() == today for t in times):
                    today_users += 1
            
            # محاسبه لینک‌های فعال
            active_links = 0
            for link_id in account_links:
                if not check_link_expiry(link_id):
                    active_links += 1
            
            edit_message(
                chat_id,
                message_id,
                "✨ <b>𝗠𝗔𝗡𝗔𝗚𝗘𝗠𝗘𝗡𝗧 𝗣𝗔𝗡𝗘𝗟</b> ✨\n\n"
                
                "▫️ ━━━━━━━━━━━━━━━━ ▫️\n\n"
                
                "📈 <b>آمار لحظه‌ای ربات:</b>\n"
                "├─ 👥 کاربران کل: <code>{}</code>\n"
                "├─ 🔥 کاربران امروز: <code>{}</code>\n"
                "├─ 👑 ادمین‌ها: <code>{}</code>\n"
                "├─ 🔗 لینک‌های فعال: <code>{}</code>\n"
                "└─ 🚫 بن شده‌ها: <code>{}</code>\n\n"
                
                "▫️ ━━━━━━━━━━━━━━━━ ▫️\n\n"
                
                "📌 <i>برای مدیریت بخش‌های مختلف، گزینه مورد نظر را انتخاب کنید:</i>".format(
                    len(user_access_history),
                    today_users,
                    len(ADMINS),
                    active_links,
                    len(banned_users)
                ),
                get_management_menu()
            )
            return

        elif data == 'show_banned':
            edit_message(
                chat_id,
                message_id,
                get_banned_users_text(),
                create_inline_keyboard([
                    [{
                        'text': '🔙 بازگشت',
                        'callback_data': 'admin_management'
                    }]
                ])
            )
            return

        elif data == 'show_unbanned':
            edit_message(
                chat_id,
                message_id,
                get_unbanned_users_text(),
                create_inline_keyboard([
                    [{
                        'text': '🔙 بازگشت',
                        'callback_data': 'admin_management'
                    }]
                ])
            )
            return

        elif data == 'show_stats':
            edit_message(
                chat_id,
                message_id,
                get_user_stats(),
                create_inline_keyboard([
                    [{
                        'text': '🔙 بازگشت',
                        'callback_data': 'admin_management'
                    }]
                ])
            )
            return

        elif data == 'back_to_main':
            edit_message(
                chat_id,
                message_id,
                "👑 <b>سلام ادمین عزیز!</b>\n\n"
                "به پنل مدیریت ربات خوش آمدید.\n"
                "برای شروع کار یکی از گزینه‌های زیر را انتخاب کنید:",
                get_admin_main_menu()
            )
            return

        elif data == 'create_link':
            bot_state[user_id] = {
                'step': 'waiting_for_vpn_name',
                'chat_id': chat_id
            }
            send_message(chat_id, "🔗 <b>ساخت لینک اکانت</b>\n\nاسم VPN را وارد کنید:")
            return

        elif data == 'show_recent_links':
            recent_links = get_recent_links()
            if not recent_links:
                edit_message(
                    chat_id,
                    message_id,
                    "📭 <b>در 24 ساعت گذشته هیچ لینکی ساخته نشده است.</b>",
                    get_management_menu()
                )
                return

            edit_message(
                chat_id,
                message_id,
                "🔗 <b>لینک‌های ساخته شده در 24 ساعت گذشته:</b>",
                get_recent_links_menu()
            )
            return

        elif data.startswith('view_link_info_'):
            link_id = data.split('view_link_info_')[1]
            if link_id in account_links:
                link = account_links[link_id]
                access = link_access.get(link_id, {'access_count': 0, 'accessed_users': []})

                # Add active/inactive status
                is_active = not check_link_expiry(link_id)
                status = "فعال ✅" if is_active else "غیرفعال ❌"

                # Calculate remaining time
                current_time = datetime.now()
                if is_active:
                    time_diff = link['expires_at'] - current_time
                    hours = time_diff.total_seconds() / 3600
                    if hours >= 1:
                        remaining_time = f"{hours:.1f} ساعت"
                    else:
                        minutes = time_diff.total_seconds() / 60
                        remaining_time = f"{int(minutes)} دقیقه"
                else:
                    remaining_time = "منقضی شده"

                info_text = (
                    f"📊 <b>اطلاعات لینک {link['vpn_name']}</b>\n\n"
                    f"🔹 <b>شناسه لینک:</b> <code>{link_id}</code>\n"
                    f"🔹 <b>وضعیت:</b> {status}\n"
                    f"🔹 <b>تعداد استفاده:</b> {access['access_count']}/{link['limit']}\n"
                    f"🔹 <b>تاریخ ساخت:</b> {link['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"🔹 <b>زمان باقی‌مانده:</b> {remaining_time}"
                )

                keyboard = create_inline_keyboard([
                    [{
                        'text': '➕ افزایش ظرفیت',
                        'callback_data': f'increase_limit_{link_id}'
                    },
                    {
                        'text': '➖ کاهش ظرفیت',
                        'callback_data': f'decrease_limit_{link_id}'
                    }],
                    [{
                        'text': '➕ افزایش زمان',
                        'callback_data': f'increase_time_{link_id}'
                    },
                    {
                        'text': '➖ کاهش زمان',
                        'callback_data': f'decrease_time_{link_id}'
                    }],
                    [{
                        'text': '🔄 تغییر وضعیت',
                        'callback_data': f'toggle_status_{link_id}'
                    }],
                    [{
                        'text': '👥 مشاهده کاربران',
                        'callback_data': f'view_users_{link_id}'
                    }],
                    [{
                        'text': '🔙 بازگشت به لیست',
                        'callback_data': 'show_recent_links'
                    }]
                ])

                edit_message(chat_id, message_id, info_text, keyboard)
            return

        elif data.startswith('increase_limit_'):
            link_id = data.split('increase_limit_')[1]
            if link_id in account_links:
                account_links[link_id]['limit'] += 1
                send_telegram_request('answerCallbackQuery', {
                    'callback_query_id': callback_query['id'],
                    'text': '✅ ظرفیت با موفقیت افزایش یافت',
                    'show_alert': True
                })
                # Refresh the link info view
                callback_query['data'] = f'view_link_info_{link_id}'
                handle_callback_query(callback_query)
            return

        elif data.startswith('decrease_limit_'):
            link_id = data.split('decrease_limit_')[1]
            if link_id in account_links:
                current_usage = link_access.get(link_id, {'access_count': 0})['access_count']
                if account_links[link_id]['limit'] > current_usage:
                    account_links[link_id]['limit'] -= 1
                    send_telegram_request('answerCallbackQuery', {
                        'callback_query_id': callback_query['id'],
                        'text': '✅ ظرفیت با موفقیت کاهش یافت',
                        'show_alert': True
                    })
                else:
                    send_telegram_request('answerCallbackQuery', {
                        'callback_query_id': callback_query['id'],
                        'text': '❌ ظرفیت نمی‌تواند از تعداد استفاده‌های فعلی کمتر باشد',
                        'show_alert': True
                    })
                # Refresh the link info view
                callback_query['data'] = f'view_link_info_{link_id}'
                handle_callback_query(callback_query)
            return

        elif data.startswith('increase_time_'):
            link_id = data.split('increase_time_')[1]
            if link_id in account_links:
                # Add 30 minutes instead of 1 hour
                account_links[link_id]['expires_at'] += timedelta(minutes=30)
                account_links[link_id]['expiry_hours'] += 0.5
                send_telegram_request('answerCallbackQuery', {
                    'callback_query_id': callback_query['id'],
                    'text': '✅ 30 دقیقه به زمان انقضا اضافه شد',
                    'show_alert': True
                })
                # Refresh the link info view
                callback_query['data'] = f'view_link_info_{link_id}'
                handle_callback_query(callback_query)
            return

        elif data.startswith('decrease_time_'):
            link_id = data.split('decrease_time_')[1]
            if link_id in account_links:
                current_time = datetime.now()
                remaining_time = (account_links[link_id]['expires_at'] - current_time).total_seconds() / 60  # Convert to minutes

                if remaining_time > 30:  # If more than 30 minutes remaining
                    account_links[link_id]['expires_at'] -= timedelta(minutes=30)
                    account_links[link_id]['expiry_hours'] -= 0.5
                    send_telegram_request('answerCallbackQuery', {
                        'callback_query_id': callback_query['id'],
                        'text': '✅ 30 دقیقه از زمان انقضا کم شد',
                        'show_alert': True
                    })
                else:
                    send_telegram_request('answerCallbackQuery', {
                        'callback_query_id': callback_query['id'],
                        'text': '❌ زمان انقضا نمی‌تواند کمتر از 30 دقیقه باشد',
                        'show_alert': True
                    })
                # Refresh the link info view
                callback_query['data'] = f'view_link_info_{link_id}'
                handle_callback_query(callback_query)
            return

        elif data.startswith('toggle_status_'):
            link_id = data.split('toggle_status_')[1]
            if link_id in account_links:
                current_time = datetime.now()
                if check_link_expiry(link_id):
                    # اگر لینک غیرفعال است، آن را فعال کن
                    account_links[link_id]['expires_at'] = current_time + timedelta(hours=account_links[link_id].get('expiry_hours', 24))
                    message = "✅ لینک فعال شد"
                else:
                    # اگر لینک فعال است، آن را غیرفعال کن
                    account_links[link_id]['expires_at'] = current_time - timedelta(minutes=1)
                    message = "⏸️ لینک غیرفعال شد"

                send_telegram_request('answerCallbackQuery', {
                    'callback_query_id': callback_query['id'],
                    'text': message,
                    'show_alert': True
                })
                # Refresh the link info view
                callback_query['data'] = f'view_link_info_{link_id}'
                handle_callback_query(callback_query)
            return

    if not is_admin(user_id) and check_user_banned_and_notify(user_id, chat_id):
        return

    if data.startswith('verify_membership_'):
        link_id = data.split('verify_membership_')[1]
        print(f"Verifying membership for user {user_id}, link {link_id}")

        if check_link_expiry(link_id):
            edit_message(chat_id, message_id, "⏰ <b>این لینک منقضی شده است.</b>")
            return

        if check_channel_membership(user_id):
            reaction_text = (
                "🎉 <b>خوش آمدید!</b>\n\n"
                "✅ شما عضو کانال هستید!\n\n"
                "📌 <b>مرحله نهایی:</b>\n"
                "برای حمایت از کانال، لطفاً روی چند پست اخیر واکنش (ری‌اکشن) بزنید.\n\n"
                "💡 <i>بعد از واکنش‌ها، روی دکمه 'تایید' کلیک کنید.</i>"
            )

            keyboard = create_inline_keyboard([
                [{
                    'text': '✅ تایید و ادامه',
                    'callback_data': f'start_reaction_{link_id}'
                }]
            ])

            edit_message(chat_id, message_id, reaction_text, keyboard)

            if user_id in pending_access:
                del pending_access[user_id]
        else:
            edit_message(
                chat_id,
                message_id,
                "⚠️ <b>هنوز عضو کانال نشده‌اید!</b>\n\n"
                "ابتدا عضو شوید، سپس دوباره روی دکمه بررسی کلیک کنید.",
                create_inline_keyboard([
                    [{
                        'text': '📢 عضویت در کانال',
                        'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
                    }],
                    [{
                        'text': '🔄 بررسی عضویت',
                        'callback_data': f'verify_membership_{link_id}'
                    }]
                ])
            )
        return

    if data.startswith('get_account_'):
        link_id = data.split('get_account_')[1]
        print(f"Account access requested: user {user_id}, link {link_id}")

        if check_user_banned_and_notify(user_id, chat_id):
            return

        if link_id not in account_links:
            edit_message(chat_id, message_id, "❌ <b>لینک نامعتبر یا منقضی شده است!</b>")
            return

        if check_link_expiry(link_id):
            edit_message(chat_id, message_id, "⏰ <b>این لینک منقضی شده است.</b>")
            return

        reaction_text = (
            "👋 <b>کاربر گرامی!</b>\n\n"
            "برای دریافت اکانت و حمایت از کانال ما، "
            "لطفاً مراحل زیر را دنبال کنید:\n\n"
            "۱. عضویت در کانال\n"
            "۲. واکنش به پست‌های اخیر\n"
            "۳. تایید نهایی\n\n"
            "👇 برای شروع کلیک کنید:"
        )

        keyboard = create_inline_keyboard([
            [{
                'text': '📢 عضویت در کانال',
                'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
            }],
            [{
                'text': '✅ تایید و ادامه',
                'callback_data': f'start_reaction_{link_id}'
            }]
        ])

        edit_message(chat_id, message_id, reaction_text, keyboard)
        return

    if data.startswith('start_reaction_'):
        link_id = data.split('start_reaction_')[1]
        user_reaction_state[user_id] = {
            'link_id': link_id,
            'start_time': datetime.now()
        }
        start_reaction_timer(user_id, chat_id, message_id, link_id)
        return

    if data.startswith('confirm_reaction_'):
        link_id = data.split('confirm_reaction_')[1]
        print(f"Reaction confirmation from user {user_id} for link {link_id}")

        if user_id not in user_reaction_state:
            edit_message(
                chat_id,
                message_id,
                "⚠️ <b>لطفاً ابتدا به پست‌های کانال واکنش دهید</b>\n\n"
                "سپس روی دکمه تایید کلیک کنید.",
                create_inline_keyboard([
                    [{
                        'text': '📢 رفتن به کانال',
                        'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
                    }],
                    [{
                        'text': '✅ تایید',
                        'callback_data': f'start_reaction_{link_id}'
                    }]
                ])
            )
            return

        if user_reaction_state[user_id]['link_id'] != link_id:
            edit_message(chat_id, message_id, "⚠️ <b>لطفاً دوباره از ابتدا شروع کنید.</b>")
            del user_reaction_state[user_id]
            return

        time_spent = (datetime.now() - user_reaction_state[user_id]['start_time']).total_seconds()
        print(f"User {user_id} spent {time_spent} seconds before confirming")

        if time_spent < 5:  # Changed from 7 to 5 seconds
            edit_message(
                chat_id,
                message_id,
                "⚠️ <b>لطفاً ابتدا به پست‌های کانال واکنش دهید</b>\n\n"
                "سپس روی دکمه تایید کلیک کنید.",
                create_inline_keyboard([
                    [{
                        'text': '📢 رفتن به کانال',
                        'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
                    }],
                    [{
                        'text': '✅ تایید',
                        'callback_data': f'start_reaction_{link_id}'
                    }]
                ])
            )
            return

        # Only proceed if enough time has passed
        if time_spent >= 5:  # Changed from 7 to 5 seconds
            del user_reaction_state[user_id]
            handle_link_access(user_id, chat_id, link_id, message_id)

            # Start monitoring channel membership
            vpn_name = account_links[link_id]['vpn_name']
            threading.Timer(5.0, check_user_left_channel, args=[user_id, vpn_name]).start()
        return

    if data.startswith('like_') or data.startswith('dislike_'):
        parts = data.split('_')[1:]  # Split and remove first part (like/dislike)
        if len(parts) >= 2:
            feedback_user_id = int(parts[0])
            link_id = parts[1]
            feedback_type = 'like' if data.startswith('like_') else 'dislike'

            if has_user_reacted(link_id, feedback_user_id):
                # Send message for repeated feedback
                send_message(
                    chat_id,
                    "✅ <b>شما قبلاً نظر خود را اعلام کرده‌اید!</b>\n\n"
                    "اگر نظری دارید، در گپ پشتیبانی مطرح کنید:",
                    get_feedback_keyboard()
                )
            else:
                # Record the feedback
                record_user_feedback(link_id, feedback_user_id, feedback_type)
                # Send thank you message
                send_message(
                    chat_id,
                    "🙏 <b>ممنون از بازخورد شما!</b>\n\n"
                    "اگر پیشنهادی دارید، خوشحال می‌شویم در گپ مطرح کنید:",
                    get_feedback_keyboard()
                )
        return

    if data.startswith('view_users_'):
        if not is_admin(user_id):
            return

        link_id = data.split('view_users_')[1]

        if link_id not in link_user_details or not link_user_details[link_id]['users']:
            send_message(chat_id, "📭 <b>هیچ کاربری هنوز از این لینک استفاده نکرده است.</b>")
            return

        link_info = account_links.get(link_id, {})
        vpn_name = link_info.get('vpn_name', 'Unknown')
        users_data = link_user_details[link_id]['users']

        info_message = f"👥 <b>کاربران اکانت {vpn_name}</b>\n\n"
        info_message += f"🔗 <b>شناسه لینک:</b> <code>{link_id}</code>\n"
        info_message += f"👤 <b>تعداد کاربران:</b> {len(users_data)}\n\n"
        info_message += f"<b>لیست کاربران:</b>\n"

        for user in users_data:
            info_message += f"\n🆔 <b>آیدی:</b> <code>{user['user_id']}</code>\n"
            info_message += f"🕒 <b>زمان دسترسی:</b> {user['access_time']}\n"
            info_message += f"⭐ <b>رضایت:</b> {user['satisfaction']}\n"
            info_message += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"

        satisfied = sum(1 for f in link_user_details[link_id]['feedback'] if f['feedback'] == 'like')
        dissatisfied = sum(1 for f in link_user_details[link_id]['feedback'] if f['feedback'] == 'dislike')
        info_message += f"\n\n📊 <b>خلاصه بازخوردها:</b>\n"
        info_message += f"👍 <b>راضی:</b> {satisfied}\n"
        info_message += f"👎 <b>ناراضی:</b> {dissatisfied}"

        send_message(chat_id, info_message)
        return

def handle_text_message(message):
    """Handle text messages"""
    user_id = message['from']['id']
    chat_id = message['chat']['id']
    text = message.get('text', '')

    print(f"handle_text_message: user {user_id}, text: {text}")

    if not is_admin(user_id) and check_user_banned_and_notify(user_id, chat_id):
        return

    if text.startswith('/start'):
        parts = text.split(' ', 1)
        if len(parts) > 1 and parts[1].startswith('link_'):
            link_id = parts[1][5:]
            print(f"Deep link access: User {user_id} accessing link {link_id}")
            if check_user_banned_and_notify(user_id, chat_id):
                return
            send_welcome_page(user_id, chat_id, link_id)
        else:
            handle_start_command(message)
        return

    if text == '/pannel' and is_admin(user_id):
        # محاسبه آمار برای نمایش در پنل
        today_users = 0
        today = datetime.now().date()
        for times in user_access_history.values():
            if any(t.date() == today for t in times):
                today_users += 1
        
        active_links = sum(1 for link_id in account_links if not check_link_expiry(link_id))
        
        panel_text = (
            "✨ <b>𝗠𝗔𝗡𝗔𝗚𝗘𝗠𝗘𝗡𝗧 𝗣𝗔𝗡𝗘𝗟</b> ✨\n\n"
            
            "▫️ ━━━━━━━━━━━━━━━━ ▫️\n\n"
            
            "📈 <b>آمار لحظه‌ای ربات:</b>\n"
            f"├─ 👥 کاربران کل: <code>{len(user_access_history)}</code>\n"
            f"├─ 🔥 کاربران امروز: <code>{today_users}</code>\n"
            f"├─ 👑 ادمین‌ها: <code>{len(ADMINS)}</code>\n"
            f"├─ 🔗 لینک‌های فعال: <code>{active_links}</code>\n"
            f"└─ 🚫 بن شده‌ها: <code>{len(banned_users)}</code>\n\n"
            
            "▫️ ━━━━━━━━━━━━━━━━ ▫️\n\n"
            
            "📌 <i>برای مدیریت بخش‌های مختلف، گزینه مورد نظر را انتخاب کنید:</i>"
        )
        
        send_message(
            chat_id,
            panel_text,
            get_management_menu()
        )
        return

    if is_admin(user_id) and user_id in bot_state:
        state = bot_state[user_id]

        if state['step'] == 'waiting_for_content':
            content = None
            caption = None

            if 'photo' in message:
                content = {'photo': message['photo']}
                caption = message.get('caption')
            elif 'video' in message:
                content = {'video': message['video']}
                caption = message.get('caption')
            elif 'audio' in message:
                content = {'audio': message['audio']}
                caption = message.get('caption')
            elif 'document' in message:
                content = {'document': message['document']}
                caption = message.get('caption')
            elif 'voice' in message:
                content = {'voice': message['voice']}
                caption = message.get('caption')
            else:
                content = text

            link_id = generate_link_id()
            expiry_time = datetime.now() + timedelta(hours=state['expiry_hours'])

            account_links[link_id] = {
                'content': content,
                'caption': caption,
                'vpn_name': state['vpn_name'],
                'limit': state['limit'],
                'expires_at': expiry_time,
                'expiry_hours': state['expiry_hours'],
                'created_by': user_id,
                'created_at': datetime.now()
            }

            link_access[link_id] = {
                'accessed_users': [],
                'access_count': 0
            }

            bot_info = send_telegram_request('getMe')
            bot_username = bot_info['result']['username'] if bot_info and bot_info.get('ok') else 'YourBot'

            telegram_link = f"https://t.me/{bot_username}?start=link_{link_id}"

            response_text = (
                "✅ <b>لینک اکانت با موفقیت ساخته شد!</b>\n\n"
                f"🔗 <b>لینک قابل کلیک:</b>\n<code>{telegram_link}</code>\n\n"
                f"📛 <b>نام VPN:</b> {state['vpn_name']}\n"
                f"👥 <b>حداکثر کاربران:</b> {state['limit']} کاربر\n"
                f"⏰ <b>مدت اعتبار:</b> {state['expiry_hours']} ساعت\n"
                f"📅 <b>تاریخ انقضا:</b> {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            info_keyboard = create_inline_keyboard([
                [{
                    'text': '👥 مشاهده اطلاعات کاربران',
                    'callback_data': f'view_users_{link_id}'
                }]
            ])

            send_message(chat_id, response_text, info_keyboard)

            del bot_state[user_id]

            keyboard = create_inline_keyboard([
                [{
                    'text': '🔗 ایجاد لینک جدید',
                    'callback_data': 'create_link'
                }]
            ])
            send_message(chat_id, "🔗 آیا می‌خواهید لینک دیگری ایجاد کنید؟", keyboard)
            
            return

        elif state['step'] == 'waiting_for_vpn_name':
            state['vpn_name'] = text
            state['step'] = 'waiting_for_limit'
            send_message(chat_id, "🔗 <b>ساخت لینک اکانت</b>\n\nتعداد کاربر مجاز برای استفاده از لینک را وارد کنید:")

        elif state['step'] == 'waiting_for_limit':
            if text.isdigit() and int(text) > 0:
                state['limit'] = int(text)
                state['step'] = 'waiting_for_expiry'
                send_message(chat_id, "⏰ <b>ساخت لینک اکانت</b>\n\nچند ساعت بعد لینک منقضی شود؟")
            else:
                send_message(chat_id, "❌ <b>لطفاً عددی معتبر و بزرگتر از 0 وارد کنید!</b>")

        elif state['step'] == 'waiting_for_expiry':
            try:
                expiry = float(text)
                if expiry > 0:
                    # Convert hours to minutes for better precision
                    minutes = int(expiry * 60)
                    if minutes < 1:
                        send_message(chat_id, "❌ <b>لطفاً عددی بزرگتر از 0.016 (یک دقیقه) وارد کنید!</b>")
                        return
                    state['expiry_hours'] = expiry
                    state['step'] = 'waiting_for_content'
                    send_message(chat_id, "📝 <b>ساخت لینک اکانت</b>\n\nاطلاعات اکانت را وارد کنید (متن، عکس، فیلم، فایل یا صدا):")
                else:
                    send_message(chat_id, "❌ <b>لطفاً عددی بزرگتر از 0 وارد کنید!</b>")
            except ValueError:
                send_message(chat_id, "❌ <b>لطفاً یک عدد معتبر وارد کنید!</b>\nمثال: 1 یا 0.5 یا 0.30")

    # ✅ اینجا کد مدیریت ادمین‌ها (درست است)
    if is_admin(user_id) and user_id in bot_state:
        state = bot_state[user_id]
        if state.get('action') == 'add_admin' and state.get('step') == 'waiting_for_admin_id':
            handle_admin_id_input(user_id, text, chat_id)
            return

def handle_link_access(user_id, chat_id, link_id, message_id):
    """Handle link access attempts"""
    print(f"handle_link_access: user {user_id}, link {link_id}")

    if check_user_banned_and_notify(user_id, chat_id):
        return

    if link_id not in account_links:
        edit_message(chat_id, message_id, "❌ <b>لینک نامعتبر یا منقضی شده است!</b>")
        return

    if check_link_expiry(link_id):
        edit_message(chat_id, message_id, "⏰ <b>این لینک منقضی شده است.</b>")
        return

    if not check_channel_membership(user_id):
        edit_message(chat_id, message_id, "⚠️ <b>ابتدا باید عضو کانال شوید!</b>")
        return

    can_access, wait_time = check_user_rate_limit(user_id)
    if not can_access:
        rate_limit_msg = (
            "⏳ <b>شما به حد مجاز دسترسی رسیده‌اید!</b>\n\n"
            f"📊 <b>محدودیت:</b> حداکثر 2 اکانت در هر 3 ساعت\n"
            f"⏰ <b>زمان باقی‌مانده:</b> {wait_time}\n\n"
            f"لطفاً بعد از این زمان مجدداً تلاش کنید."
        )
        edit_message(chat_id, message_id, rate_limit_msg)
        return

    link = account_links[link_id]
    access = link_access[link_id]

    if user_id in access['accessed_users']:
        edit_message(chat_id, message_id, "✅ <b>شما قبلاً این اکانت را دریافت کرده‌اید!</b>")
        return

    if access['access_count'] >= link['limit']:
        edit_message(chat_id, message_id, "⚠️ <b>ظرفیت این اکانت پر شده!</b>\n\nلطفاً بعداً امتحان کنید.")
        return

    access['accessed_users'].append(user_id)
    access['access_count'] += 1

    record_user_access(user_id)

    user_info = {
        'user_id': user_id,
        'username': 'N/A',
        'first_name': 'N/A',
        'last_name': 'N/A'
    }
    record_user_details(link_id, user_id, user_info)

    remaining_accesses = 2 - len(user_access_history[user_id])

    base_text = f"🎉 <b>اطلاعات اکانت {link['vpn_name']}</b>\n\n"
    footer_text = (
        f"\n\n📌 <b>توجه:</b>\n"
        f"هر عضو می‌تواند حداکثر 2 اکانت در هر 3 ساعت دریافت کند.\n"
        f"شما تاکنون {len(user_access_history[user_id])} اکانت دریافت کرده‌اید، "
        f"بنابراین در این بازه زمانی {remaining_accesses} فرصت دیگر دارید."
    )

    # ارسال محتوا بر اساس نوع آن
    content = link['content']
    caption = link.get('caption', '')
    full_caption = base_text + (caption if caption else '') + footer_text

    keyboard = create_inline_keyboard([
        [
            {
                'text': '👍 راضی هستم',
                'callback_data': f'like_{user_id}_{link_id}'
            },
            {
                'text': '👎 راضی نیستم',
                'callback_data': f'dislike_{user_id}_{link_id}'
            }
        ]
    ])

    if isinstance(content, dict):  # اگر محتوا یک فایل مدیا باشد
        if 'photo' in content:
            send_telegram_request('sendPhoto', {
                'chat_id': chat_id,
                'photo': content['photo'][-1]['file_id'],
                'caption': full_caption,
                'reply_markup': keyboard
            })
        elif 'video' in content:
            send_telegram_request('sendVideo', {
                'chat_id': chat_id,
                'video': content['video']['file_id'],
                'caption': full_caption,
                'reply_markup': keyboard
            })
        elif 'audio' in content:
            send_telegram_request('sendAudio', {
                'chat_id': chat_id,
                'audio': content['audio']['file_id'],
                'caption': full_caption,
                'reply_markup': keyboard
            })
        elif 'document' in content:
            send_telegram_request('sendDocument', {
                'chat_id': chat_id,
                'document': content['document']['file_id'],
                'caption': full_caption,
                'reply_markup': keyboard
            })
        elif 'voice' in content:
            send_telegram_request('sendVoice', {
                'chat_id': chat_id,
                'voice': content['voice']['file_id'],
                'caption': full_caption,
                'reply_markup': keyboard
            })
    else:  # اگر محتوا متن باشد
        response_text = base_text + f"<code>{content}</code>" + footer_text
        edit_message(chat_id, message_id, response_text, keyboard)

    # Start monitoring channel membership
    start_membership_monitoring(user_id, link['vpn_name'])

def get_updates(offset=0):
    """Get updates from Telegram"""
    params = {
        'offset': offset,
        'timeout': 30
    }

    return send_telegram_request('getUpdates', params)

def start_bot():
    """Main bot loop"""
    print("Starting Telegram Account Link Bot...")
    print(f"Bot Token: {BOT_TOKEN.split(':')[0]}:****")
    print(f"Admins: {', '.join(str(admin_id) for admin_id in ADMINS)}")
    print(f"Channel: {CHANNEL_USERNAME}")
    print("Bot is running... Press Ctrl+C to stop.\n")

    bot_info = send_telegram_request('getMe')
    if bot_info and bot_info.get('ok'):
        print(f" !Bot connected successfully: @{bot_info['result']['username']}")
    else:
        print(" !Failed to connect to bot. Check your token!")
    last_update_id = 0

    try:
        while True:
            try:
                updates = get_updates(last_update_id + 1)

                if updates and updates.get('ok') and updates.get('result'):
                    for update in updates['result']:
                        last_update_id = update['update_id']
                        print(f"Processing update: {update['update_id']}")

                        if 'message' in update:
                            message = update['message']
                            user_name = message['from'].get('first_name', 'Unknown')
                            user_id = message['from']['id']
                            text = message.get('text', '')
                            print(f" Message from {user_name} ({user_id}): {text}")
                            handle_text_message(message)

                        elif 'callback_query' in update:
                            callback_query = update['callback_query']
                            user_name = callback_query['from'].get('first_name', 'Unknown')
                            user_id = callback_query['from']['id']
                            data = callback_query['data']
                            print(f" Button pressed by {user_name} ({user_id}): {data}")
                            handle_callback_query(callback_query)

                time.sleep(0.1)

            except Exception as e:
                print(f" Error in main loop: {e}")
                time.sleep(5)

    except KeyboardInterrupt:
        print("\n Bot stopped by user.")

def check_user_banned_and_notify(user_id, chat_id):
    """Check if user is banned and notify them"""
    if is_user_banned(user_id):
        send_message(chat_id, "🚫 <b>شما توسط ادمین از ربات بن شدید!</b>")
        return True
    return False

def check_link_expiry(link_id):
    """Check if link has expired"""
    if link_id not in account_links:
        return True

    link = account_links[link_id]
    if 'expires_at' not in link:
        return False

    return datetime.now() > link['expires_at']

def check_user_rate_limit(user_id):
    """Check if user can access another link (max 2 per 3 hours)"""
    current_time = datetime.now()
    three_hours_ago = current_time - timedelta(hours=3)

    if user_id not in user_access_history:
        user_access_history[user_id] = []

    user_access_history[user_id] = [
        access_time for access_time in user_access_history[user_id]
        if access_time > three_hours_ago
    ]

    if len(user_access_history[user_id]) >= 2:
        oldest_access = min(user_access_history[user_id])
        time_until_reset = oldest_access + timedelta(hours=3) - current_time

        total_seconds = int(time_until_reset.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        time_str = ""
        if hours > 0:
            time_str += f"{hours} ساعت "
        if minutes > 0:
            time_str += f"{minutes} دقیقه "
        if seconds > 0 and hours == 0:
            time_str += f"{seconds} ثانیه"

        return False, time_str.strip()

    return True, ""

def record_user_access(user_id):
    """Record user access time"""
    current_time = datetime.now()

    if user_id not in user_access_history:
        user_access_history[user_id] = []

    user_access_history[user_id].append(current_time)

def record_user_details(link_id, user_id, user_info):
    """Record detailed user information for admin viewing"""
    if link_id not in link_user_details:
        link_user_details[link_id] = {'users': [], 'feedback': []}

    for user in link_user_details[link_id]['users']:
        if user['user_id'] == user_id:
            return

    user_data = {
        'user_id': user_id,
        'username': user_info.get('username', 'N/A'),
        'first_name': user_info.get('first_name', 'N/A'),
        'last_name': user_info.get('last_name', 'N/A'),
        'access_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'satisfaction': 'Pending'
    }

    link_user_details[link_id]['users'].append(user_data)

def record_user_feedback(link_id, user_id, feedback_type):
    """Record user feedback for specific link"""
    if link_id not in link_user_details:
        return

    for user in link_user_details[link_id]['users']:
        if user['user_id'] == user_id:
            user['satisfaction'] = 'Like' if feedback_type == 'like' else 'Dislike'
            break

    feedback_data = {
        'user_id': user_id,
        'feedback': feedback_type,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    link_user_details[link_id]['feedback'].append(feedback_data)

def send_welcome_page(user_id, chat_id, link_id):
    """Send beautiful welcome page with channel join requirement"""
    print(f"send_welcome_page called for user {user_id} with link {link_id}")

    if check_user_banned_and_notify(user_id, chat_id):
        return

    if check_link_expiry(link_id):
        send_message(chat_id, "⏰ <b>این لینک منقضی شده است.</b>")
        return

    is_member = check_channel_membership(user_id)
    print(f"User {user_id} membership check: {is_member}")

    if is_member:
        # اگر کاربر از قبل عضو کانال است
        reaction_text = (
            "🎉 <b>خوش آمدید!</b>\n\n"
            "✅ شما عضو کانال هستید!\n\n"
            "📌 <b>مرحله نهایی:</b>\n"
            "برای حمایت از کانال، لطفاً روی چند پست اخیر واکنش (ری‌اکشن) بزنید.\n\n"
            "💡 <i>بعد از واکنش‌ها، روی دکمه 'تایید' کلیک کنید.</i>"
        )

        keyboard = create_inline_keyboard([
            [{
                'text': '✅ تایید و ادامه',
                'callback_data': f'start_reaction_{link_id}'
            }]
        ])

        result = send_message(chat_id, reaction_text, keyboard)
        return result

    # پیام خوش‌آمدگویی زیبا
    welcome_text = (
        "🌟 <b>به ربات ما خوش آمدید!</b>\n\n"
        
        "📌 <b>شرایط دریافت اکانت:</b>\n"
        f"۱️⃣ عضویت در کانال {CHANNEL_USERNAME}\n"
        "۲️⃣ واکنش به پست‌های کانال\n"
        "۳️⃣ دریافت اکانت رایگان\n\n"
        
        "💎 <b>مزایای عضویت:</b>\n"
        "✓ اکانت‌های باکیفیت\n"
        "✓ پشتیبانی ۲۴ ساعته\n"
        "✓ آپدیت‌های رایگان\n\n"
        
        "👇 <i>برای شروع، ابتدا در کانال عضو شوید:</i>"
    )

    keyboard = create_inline_keyboard([
        [{
            'text': '📢 عضویت در کانال',
            'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
        }],
        [{
            'text': '🔄 بررسی عضویت',
            'callback_data': f'verify_membership_{link_id}'
        }]
    ])

    print(f"Sending join channel message to user {user_id}")
    result = send_message(chat_id, welcome_text, keyboard)
    print(f"Message send result: {result}")
    return result

def check_user_left_channel(user_id, vpn_name):
    """Check if user has left the channel and notify admins"""
    if not check_channel_membership(user_id):
        # ارسال پیام به همه ادمین‌ها
        for admin_id in ADMINS:
            keyboard = create_inline_keyboard([
                [{
                    'text': '🚫 بن کردن کاربر',
                    'callback_data': f'ban_left_user_{user_id}'
                }]
            ])

            admin_message = (
                f"⚠️ <b>هشدار خروج از کانال!</b>\n\n"
                f"👤 <b>کاربر:</b> <code>{user_id}</code>\n"
                f"🔗 <b>اکانت:</b> {vpn_name}\n\n"
                f"این کاربر بعد از دریافت اکانت از کانال خارج شده است!"
            )

            send_message(admin_id, admin_message, keyboard)
        return True
    return False

def start_reaction_timer(user_id, chat_id, message_id, link_id):
    """Start reaction timer with both buttons"""
    keyboard = create_inline_keyboard([
        [{
            'text': '📢 رفتن به کانال',
            'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
        }],
        [{
            'text': '✅ تایید واکنش‌ها',
            'callback_data': f'confirm_reaction_{link_id}'
        }]
    ])

    edit_message(
        chat_id,
        message_id,
        "🎯 <b>مرحله واکنش‌ها</b>\n\n"
        "لطفاً به پست‌های اخیر کانال واکنش (ری‌اکشن) دهید\n\n"
        "💡 <i>بعد از واکنش‌ها، روی دکمه 'تایید' کلیک کنید:</i>",
        keyboard
    )

def monitor_channel_membership(user_id, vpn_name):
    """Continuously monitor channel membership"""
    if not check_channel_membership(user_id):
        if user_id in active_monitors:  # User left the channel
            del active_monitors[user_id]  # Stop monitoring

            # فقط برای کاربرانی که قبلاً از ربات استفاده کرده‌اند پیام ارسال شود
            if user_id in user_access_history:
                # ارسال پیام به همه ادمین‌ها
                for admin_id in ADMINS:
                    keyboard = create_inline_keyboard([
                        [{
                            'text': '🚫 بن کردن کاربر',
                            'callback_data': f'ban_left_user_{user_id}'
                        }]
                    ])

                    admin_message = (
                        f"⚠️ <b>هشدار خروج از کانال!</b>\n\n"
                        f"👤 <b>کاربر:</b> <code>{user_id}</code>\n"
                        f"🔗 <b>اکانت:</b> {vpn_name}\n\n"
                        f"این کاربر بعد از دریافت اکانت از کانال خارج شده است!"
                    )

                    send_message(admin_id, admin_message, keyboard)
            return

    if user_id in active_monitors:  # Continue monitoring if still active
        threading.Timer(30.0, monitor_channel_membership, args=[user_id, vpn_name]).start()

def start_membership_monitoring(user_id, vpn_name):
    """Start monitoring channel membership for a user"""
    if user_id not in active_monitors:
        active_monitors[user_id] = True
        threading.Timer(30.0, monitor_channel_membership, args=[user_id, vpn_name]).start()

def get_recent_links():
    """Get links created in the last 24 hours"""
    current_time = datetime.now()
    recent_links = []

    for link_id, link_info in account_links.items():
        if 'created_at' in link_info:
            time_diff = current_time - link_info['created_at']
            if time_diff.total_seconds() <= 24 * 3600:  # 24 hours in seconds
                recent_links.append((link_id, link_info))

    return recent_links

def get_recent_links_menu():
    """Create keyboard with recent links"""
    recent_links = get_recent_links()
    buttons = []

    for link_id, link_info in recent_links:
        is_active = not check_link_expiry(link_id)
        status_emoji = "✅" if is_active else "⏰"
        buttons.append([{
            'text': f"{status_emoji} لینک {link_info['vpn_name']}",
            'callback_data': f'view_link_info_{link_id}'
        }])

    buttons.append([{
        'text': '🔙 بازگشت',
        'callback_data': 'admin_management'
    }])

    return create_inline_keyboard(buttons)

def get_feedback_keyboard():
    """Get keyboard with group link"""
    return create_inline_keyboard([
        [{
            'text': '💬 گپ پشتیبانی',
            'url': 'https://t.me/cpy_gap'
        }]
    ])

def has_user_reacted(link_id, user_id):
    """Check if user has already given feedback for this link"""
    if link_id in link_user_details and 'feedback' in link_user_details[link_id]:
        return any(f['user_id'] == user_id for f in link_user_details[link_id]['feedback'])
    return False

if __name__ == "__main__":
    print("✨ Telegram Account Link Bot - Multi-Admin Version ✨")
    print("=" * 50)
    start_bot()
