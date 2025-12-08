#!/usr/bin/env python3
# Telegram Account Link Bot
# Python Implementation - Enhanced with Admin User Info Button (Corrected)

import requests
import json
import time
import uuid
from datetime import datetime, timedelta
import threading

# Configuration
BOT_TOKEN = "7925127595:AAGQReL1FBeqsKNvMtxSkOsJsWllvXL_x2I"
ADMIN_USER_ID = 1690187708
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
CHANNEL_USERNAME = "@nyxmod"  # Channel for membership verification

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

def ban_user(user_id):
    """Ban a user from using the bot"""
    banned_users[user_id] = {
        'ban_date': datetime.now(),
        'banned_by': ADMIN_USER_ID
    }

def unban_user(user_id):
    """Unban a user from using the bot"""
    if user_id in banned_users:
        unban_data = {
            'user_id': user_id,
            'ban_date': banned_users[user_id]['ban_date'],
            'unban_date': datetime.now(),
            'unbanned_by': ADMIN_USER_ID
        }
        unbanned_users[user_id] = unban_data
        del banned_users[user_id]
        return True
    return False

def get_banned_users_text():
    """Get formatted text of banned users"""
    if not banned_users:
        return "هیچ کاربری در لیست بن شده‌ها نیست!"
    
    text = "لیست کاربران بن شده:\n\n"
    for user_id, data in banned_users.items():
        ban_date = format_datetime(data['ban_date'])
        text += f"کاربر: <code>{user_id}</code>\n"
        text += f"تاریخ بن: {ban_date}\n"
        text += "─────────────────\n"
    return text

def get_unbanned_users_text():
    """Get formatted text of unbanned users"""
    if not unbanned_users:
        return "هیچ کاربری در لیست آنبن شده‌ها نیست!"
    
    text = "لیست کاربران آنبن شده:\n\n"
    for user_id, data in unbanned_users.items():
        ban_date = format_datetime(data['ban_date'])
        unban_date = format_datetime(data['unban_date'])
        text += f"کاربر: <code>{user_id}</code>\n"
        text += f"تاریخ بن: {ban_date}\n"
        text += f"تاریخ آنبن: {unban_date}\n"
        text += "─────────────────\n"
    return text

def get_admin_main_menu():
    """Get admin main menu keyboard"""
    return create_inline_keyboard([
        [{
            'text': 'Create Account Link',
            'callback_data': 'create_link'
        }],
        [{
            'text': 'مدیریت',
            'callback_data': 'admin_management'
        }]
    ])

def get_management_menu():
    """Get management menu keyboard"""
    return create_inline_keyboard([
        [{
            'text': 'لیست بن شده‌ها',
            'callback_data': 'show_banned'
        }],
        [{
            'text': 'لیست آنبن شده‌ها',
            'callback_data': 'show_unbanned'
        }],
        [{
            'text': 'آمار کاربران',
            'callback_data': 'show_stats'
        }],
        [{
            'text': 'اطلاعات لینک',
            'callback_data': 'show_recent_links'
        }],
        [{
            'text': 'بازگشت',
            'callback_data': 'back_to_main'
        }]
    ])

def get_user_stats():
    """Get user statistics"""
    total_users = len(user_access_history)
    active_users = sum(1 for user_times in user_access_history.values() 
                      if any(time > datetime.now() - timedelta(days=7) for time in user_times))
    
    text = "آمار کاربران ربات:\n\n"
    text += f"تعداد کل کاربران: {total_users}\n"
    text += f"کاربران فعال در 7 روز گذشته: {active_users}\n"
    text += "─────────────────\n"
    return text

def handle_start_command(message):
    """Handle /start command"""
    user_id = message['from']['id']
    chat_id = message['chat']['id']
    
    print(f"handle_start_command called for user {user_id}")
    
    if user_id == ADMIN_USER_ID:
        send_message(
            chat_id,
            "سلام ادمین! برای ساخت لینک روی دکمه زیر کلیک کنید",
            get_admin_main_menu()
        )
    else:
        welcome_text = (
            f"سلام {message['from'].get('first_name', '')} !\n"
            "برای استفاده از ربات و دریافت اکانت ابتدا جوین چنل شین."
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

    if user_id == ADMIN_USER_ID:
        if data.startswith('ban_left_user_'):
            user_id_to_ban = int(data.split('ban_left_user_')[1])
            ban_user(user_id_to_ban)
            edit_message(
                chat_id,
                message_id,
                f"کاربر با آیدی {user_id_to_ban} با موفقیت بن شد!"
            )
            try:
                send_message(user_id_to_ban, "شما به دلیل خروج از کانال از ربات بن شدید!")
            except:
                print(f"Could not notify banned user {user_id_to_ban}")
            return

        elif data == 'admin_management':
            edit_message(
                chat_id,
                message_id,
                "پنل مدیریت\n\n"
                "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
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
                        'text': 'بازگشت',
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
                        'text': 'بازگشت',
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
                        'text': 'بازگشت',
                        'callback_data': 'admin_management'
                    }]
                ])
            )
            return
            
        elif data == 'back_to_main':
            edit_message(
                chat_id,
                message_id,
                "سلام ادمین! برای ساخت لینک روی دکمه زیر کلیک کنید",
                get_admin_main_menu()
            )
            return
            
        elif data == 'create_link':
            bot_state[user_id] = {
                'step': 'waiting_for_vpn_name',
                'chat_id': chat_id
            }
            send_message(chat_id, "اسم VPN را وارد کنید:")
            return

        elif data == 'show_recent_links':
            recent_links = get_recent_links()
            if not recent_links:
                edit_message(
                    chat_id,
                    message_id,
                    "در 24 ساعت گذشته هیچ لینکی ساخته نشده است.",
                    get_management_menu()
                )
                return
                
            edit_message(
                chat_id,
                message_id,
                "لینک‌های ساخته شده در 24 ساعت گذشته:",
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
                    f"اطلاعات لینک {link['vpn_name']}:\n\n"
                    f"🔹 شناسه لینک: <code>{link_id}</code>\n"
                    f"🔹 وضعیت: {status}\n"
                    f"🔹 تعداد استفاده: {access['access_count']}/{link['limit']}\n"
                    f"🔹 تاریخ ساخت: {link['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"🔹 زمان باقی‌مانده: {remaining_time}"
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
                        'text': 'تغییر وضعیت (فعال/غیرفعال)',
                        'callback_data': f'toggle_status_{link_id}'
                    }],
                    [{
                        'text': 'مشاهده کاربران',
                        'callback_data': f'view_users_{link_id}'
                    }],
                    [{
                        'text': 'بازگشت به لیست',
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
                    'text': 'ظرفیت با موفقیت افزایش یافت',
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
                        'text': 'ظرفیت با موفقیت کاهش یافت',
                        'show_alert': True
                    })
                else:
                    send_telegram_request('answerCallbackQuery', {
                        'callback_query_id': callback_query['id'],
                        'text': 'خطا: ظرفیت نمی‌تواند از تعداد استفاده‌های فعلی کمتر باشد',
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
                    'text': '30 دقیقه به زمان انقضا اضافه شد',
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
                        'text': '30 دقیقه از زمان انقضا کم شد',
                        'show_alert': True
                    })
                else:
                    send_telegram_request('answerCallbackQuery', {
                        'callback_query_id': callback_query['id'],
                        'text': 'خطا: زمان انقضا نمی‌تواند کمتر از 30 دقیقه باشد',
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
                    message = "لینک فعال شد"
                else:
                    # اگر لینک فعال است، آن را غیرفعال کن
                    account_links[link_id]['expires_at'] = current_time - timedelta(minutes=1)
                    message = "لینک غیرفعال شد"
                
                send_telegram_request('answerCallbackQuery', {
                    'callback_query_id': callback_query['id'],
                    'text': message,
                    'show_alert': True
                })
                # Refresh the link info view
                callback_query['data'] = f'view_link_info_{link_id}'
                handle_callback_query(callback_query)
            return
    
    if user_id != ADMIN_USER_ID and check_user_banned_and_notify(user_id, chat_id):
        return
    
    if data.startswith('verify_membership_'):
        link_id = data.split('verify_membership_')[1]
        print(f"Verifying membership for user {user_id}, link {link_id}")
        
        if check_link_expiry(link_id):
            edit_message(chat_id, message_id, "این لینک منقضی شده است.")
            return
        
        if check_channel_membership(user_id):
            reaction_text = (
                "کاربر گرامی! قبل دریافت اکانت برای حمایت از چنل باید روی چند پست اخیر ریکشن بزنید\n"
                "اگه مایل به ادامه دادن هستین روی دکمه زیر کلیک کنید :"
            )
            
            keyboard = create_inline_keyboard([
                [{
                    'text': 'تایید',
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
                "هنوز عضو کانال نشده‌اید!\nابتدا عضو شوید، سپس دوباره روی دکمه بررسی کلیک کنید.",
                create_inline_keyboard([
                    [{
                        'text': 'Channel',
                        'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
                    }],
                    [{
                        'text': 'Refresh',
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
            edit_message(chat_id, message_id, "لینک نامعتبر یا منقضی شده است!")
            return
        
        if check_link_expiry(link_id):
            edit_message(chat_id, message_id, "این لینک منقضی شده است.")
            return
        
        reaction_text = (
            "کاربر گرامی! برای دریافت اکانت و حمایت از کانال ما، "
            "لطفاً روی دکمه زیر کلیک کنید، وارد کانال شوید، "
            "به چند پست اخیر واکنش نشان دهید، سپس برگردید و دکمه تایید را بزنید."
        )
        
        keyboard = create_inline_keyboard([
            [{
                'text': 'Channel',
                'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
            }],
            [{
                'text': 'تایید',
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
                "لطفا اول ریکشن بزنین و بعد روی تایید کلیک کنید",
                create_inline_keyboard([
                    [{
                        'text': 'Channel',
                        'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
                    }],
                    [{
                        'text': 'تایید',
                        'callback_data': f'start_reaction_{link_id}'
                    }]
                ])
            )
            return
            
        if user_reaction_state[user_id]['link_id'] != link_id:
            edit_message(chat_id, message_id, "لطفاً دوباره از ابتدا شروع کنید.")
            del user_reaction_state[user_id]
            return
        
        time_spent = (datetime.now() - user_reaction_state[user_id]['start_time']).total_seconds()
        print(f"User {user_id} spent {time_spent} seconds before confirming")
        
        if time_spent < 5:  # Changed from 7 to 5 seconds
            edit_message(
                chat_id,
                message_id,
                "لطفا اول ریکشن بزنین و بعد روی تایید کلیک کنید",
                create_inline_keyboard([
                    [{
                        'text': 'Channel',
                        'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
                    }],
                    [{
                        'text': 'تایید',
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
                    "شما قبلا نظرتون رو اعلام کردین!\nنظری بود تو گپ بیان کنید :",
                    get_feedback_keyboard()
                )
            else:
                # Record the feedback
                record_user_feedback(link_id, feedback_user_id, feedback_type)
                # Send thank you message
                send_message(
                    chat_id,
                    "ممنون از بازخوردتون\nاگه انتقال یا پیشنهادی داشتین خوشحال میشیم تو گپ مطرح کنین :",
                    get_feedback_keyboard()
                )
        return
    
    if data.startswith('view_users_'):
        if user_id != ADMIN_USER_ID:
            return
        
        link_id = data.split('view_users_')[1]
        
        if link_id not in link_user_details or not link_user_details[link_id]['users']:
            send_message(chat_id, "هیچ کاربری هنوز از این لینک استفاده نکرده است.")
            return
        
        link_info = account_links.get(link_id, {})
        vpn_name = link_info.get('vpn_name', 'Unknown')
        users_data = link_user_details[link_id]['users']
        
        info_message = f"<b>Users of Account {vpn_name}</b>\n\n"
        info_message += f"<b>Link ID:</b> <code>{link_id}</code>\n"
        info_message += f"<b>User Count:</b> {len(users_data)}\n\n"
        info_message += f"<b>Users:</b>\n"
        
        for user in users_data:
            info_message += f"ID: <code>{user['user_id']}</code>\n"
            info_message += f"Access Time: {user['access_time']}\n"
            info_message += f"Satisfaction: {user['satisfaction']}\n\n"
        
        satisfied = sum(1 for f in link_user_details[link_id]['feedback'] if f['feedback'] == 'like')
        dissatisfied = sum(1 for f in link_user_details[link_id]['feedback'] if f['feedback'] == 'dislike')
        info_message += f"<b>Feedback Summary:</b>\n"
        info_message += f"Satisfied: {satisfied}\n"
        info_message += f"Not Satisfied: {dissatisfied}"
        
        send_message(chat_id, info_message)
        return

def handle_text_message(message):
    """Handle text messages"""
    user_id = message['from']['id']
    chat_id = message['chat']['id']
    text = message.get('text', '')
    
    print(f"handle_text_message: user {user_id}, text: {text}")
    
    if user_id != ADMIN_USER_ID and check_user_banned_and_notify(user_id, chat_id):
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

    if text == '/pannel' and user_id == ADMIN_USER_ID:
        send_message(
            chat_id,
            "پنل مدیریت\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            get_management_menu()
        )
        return

    if user_id == ADMIN_USER_ID and user_id in bot_state:
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
                "Account link has been successfully created!\n\n"
                f"<b>Clickable Link : </b>\n{telegram_link}\n\n"
                f"<b>VPN Name : </b> {state['vpn_name']}\n"
                f"<b>User Limit : </b> {state['limit']} users\n"
                f"<b>Expires in : </b> {state['expiry_hours']} hours\n"
                f"<b>Expiration Date : </b> {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            info_keyboard = create_inline_keyboard([
                [{
                    'text': 'مشاهده اطلاعات کاربران',
                    'callback_data': f'view_users_{link_id}'
                }]
            ])
            
            send_message(chat_id, response_text, info_keyboard)
            
            del bot_state[user_id]
            
            keyboard = create_inline_keyboard([
                [{
                    'text': 'ایجاد لینک جدید',
                    'callback_data': 'create_link'
                }]
            ])
            send_message(chat_id, "آیا میخواهید لینک دیگری ایجاد کنید؟", keyboard)
            return
        
        elif state['step'] == 'waiting_for_vpn_name':
            state['vpn_name'] = text
            state['step'] = 'waiting_for_limit'
            send_message(chat_id, "تعداد کاربر مجاز برای استفاده از لینک را وارد کنید:")
        
        elif state['step'] == 'waiting_for_limit':
            if text.isdigit() and int(text) > 0:
                state['limit'] = int(text)
                state['step'] = 'waiting_for_expiry'
                send_message(chat_id, "چند ساعت بعد منقضی شود ؟ ")
            else:
                send_message(chat_id, "لطفاً عددی معتبر و بزرگتر از 0 وارد کنید!")
        
        elif state['step'] == 'waiting_for_expiry':
            try:
                expiry = float(text)
                if expiry > 0:
                    # Convert hours to minutes for better precision
                    minutes = int(expiry * 60)
                    if minutes < 1:
                        send_message(chat_id, "لطفاً عددی بزرگتر از 0.016 (یک دقیقه) وارد کنید!")
                        return
                    
                    state['expiry_hours'] = expiry
                    state['step'] = 'waiting_for_content'
                    send_message(chat_id, "اطلاعات اکانت را وارد کنید (متن، عکس، فیلم، فایل یا صدا):")
                else:
                    send_message(chat_id, "لطفاً عددی بزرگتر از 0 وارد کنید!")
            except ValueError:
                send_message(chat_id, "لطفاً یک عدد معتبر وارد کنید! (مثال: 1 یا 0.5 یا 0.30)")
    
    if user_id == ADMIN_USER_ID:
        # اگر ادمین هر نوع محتوایی فرستاد، آن را به عنوان محتوای اکانت در نظر بگیر
        if 'photo' in message:
            content = message['photo'][-1]['file_id']
        elif 'video' in message:
            content = message['video']['file_id']
        elif 'audio' in message:
            content = message['audio']['file_id']
        elif 'document' in message:
            content = message['document']['file_id']
        elif 'voice' in message:
            content = message['voice']['file_id']
        else:
            content = text
            
        if user_id in bot_state and bot_state[user_id]['step'] == 'waiting_for_content':
            bot_state[user_id]['content'] = content
            # ادامه روند ساخت لینک...

def handle_link_access(user_id, chat_id, link_id, message_id):
    """Handle link access attempts"""
    print(f"handle_link_access: user {user_id}, link {link_id}")
    
    if check_user_banned_and_notify(user_id, chat_id):
        return
    
    if link_id not in account_links:
        edit_message(chat_id, message_id, "لینک نامعتبر یا منقضی شده است!")
        return
    
    if check_link_expiry(link_id):
        edit_message(chat_id, message_id, "این لینک منقضی شده است.")
        return
    
    if not check_channel_membership(user_id):
        edit_message(chat_id, message_id, "ابتدا باید عضو کانال شوید!")
        return
    
    can_access, wait_time = check_user_rate_limit(user_id)
    if not can_access:
        rate_limit_msg = (
            f"شما به حد مجاز دسترسی رسیده‌اید! (حداکثر 2 اکانت در هر 3 ساعت)\n"
            f"زمان باقی‌مانده تا بازنشانی: {wait_time}\n\n"
            f"لطفاً بعد از این زمان مجدداً تلاش کنید."
        )
        edit_message(chat_id, message_id, rate_limit_msg)
        return
    
    link = account_links[link_id]
    access = link_access[link_id]
    
    if user_id in access['accessed_users']:
        edit_message(chat_id, message_id, "شما قبلاً این اکانت را دریافت کرده‌اید!")
        return
    
    if access['access_count'] >= link['limit']:
        edit_message(chat_id, message_id, "ظرفیت این اکانت پر شده! لطفاً بعداً امتحان کنید.")
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
    
    base_text = f"اطلاعات اکانت {link['vpn_name']}:\n\n"
    footer_text = (
        f"\n\nتوجه :\n"
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
                'text': '👍',
                'callback_data': f'like_{user_id}_{link_id}'
            },
            {
                'text': '👎',
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
    print(f"Admin User ID: {ADMIN_USER_ID}")
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
        send_message(chat_id, "شما توسط ادمین از ربات بن شدید!")
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
    """Send welcome page with channel join requirement"""
    print(f"send_welcome_page called for user {user_id} with link {link_id}")
    
    if check_user_banned_and_notify(user_id, chat_id):
        return
    
    if check_link_expiry(link_id):
        send_message(chat_id, "این لینک منقضی شده است.")
        return
    
    is_member = check_channel_membership(user_id)
    print(f"User {user_id} membership check: {is_member}")
    
    if is_member:
        # اگر کاربر از قبل عضو کانال است، مستقیم به مرحله ریکشن برود
        reaction_text = (
            "کاربر گرامی! قبل دریافت اکانت برای حمایت از چنل باید روی چند پست اخیر ریکشن بزنید\n"
            "اگه مایل به ادامه دادن هستین روی دکمه زیر کلیک کنید :"
        )
        
        keyboard = create_inline_keyboard([
            [{
                'text': 'تایید',
                'callback_data': f'start_reaction_{link_id}'
            }]
        ])
        
        result = send_message(chat_id, reaction_text, keyboard)
        return result
    
    welcome_text = (
        f"سلام {message['from'].get('first_name', '')} !\n"
        "برای استفاده از ربات و دریافت اکانت ابتدا جوین چنل شین."
    )

    keyboard = create_inline_keyboard([
        [{
            'text': 'Channel',
            'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
        }],
        [{
            'text': 'Refresh',
            'callback_data': f'verify_membership_{link_id}'
        }]
    ])

    print(f"Sending join channel message to user {user_id}")
    result = send_message(chat_id, welcome_text, keyboard)
    print(f"Message send result: {result}")
    return result

def check_user_left_channel(user_id, vpn_name):
    """Check if user has left the channel and notify admin"""
    if not check_channel_membership(user_id):
        # ارسال پیام به ادمین
        keyboard = create_inline_keyboard([
            [{
                'text': 'بن کردن کاربر',
                'callback_data': f'ban_left_user_{user_id}'
            }]
        ])
        
        admin_message = (
            f"کاربر با آیدی <code>{user_id}</code>\n"
            f"بعد از دریافت اکانت ({vpn_name}) از کانال خارج شد!"
        )
        
        send_message(ADMIN_USER_ID, admin_message, keyboard)
        return True
    return False

def start_reaction_timer(user_id, chat_id, message_id, link_id):
    """Start reaction timer with both buttons"""
    keyboard = create_inline_keyboard([
        [{
            'text': 'Channel',
            'url': f'https://t.me/{CHANNEL_USERNAME[1:]}'
        }],
        [{
            'text': 'تایید',
            'callback_data': f'confirm_reaction_{link_id}'
        }]
    ])
    
    edit_message(
        chat_id,
        message_id,
        "لطفا به پست های کانال واکنش دهید و سپس روی تایید کلیک کنید:",
        keyboard
    )

def monitor_channel_membership(user_id, vpn_name):
    """Continuously monitor channel membership"""
    if not check_channel_membership(user_id):
        if user_id in active_monitors:  # User left the channel
            del active_monitors[user_id]  # Stop monitoring
            
            # فقط برای کاربرانی که قبلاً از ربات استفاده کرده‌اند پیام ارسال شود
            if user_id in user_access_history:
                keyboard = create_inline_keyboard([
                    [{
                        'text': 'بن کردن کاربر',
                        'callback_data': f'ban_left_user_{user_id}'
                    }]
                ])
                
                admin_message = (
                    f"کاربر با آیدی <code>{user_id}</code>\n"
                    f"بعد از دریافت اکانت ({vpn_name}) از کانال خارج شد!"
                )
                
                send_message(ADMIN_USER_ID, admin_message, keyboard)
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
        buttons.append([{
            'text': f"لینک {link_info['vpn_name']}",
            'callback_data': f'view_link_info_{link_id}'
        }])
    
    buttons.append([{
        'text': 'بازگشت',
        'callback_data': 'admin_management'
    }])
    
    return create_inline_keyboard(buttons)

def get_feedback_keyboard():
    """Get keyboard with group link"""
    return create_inline_keyboard([
        [{
            'text': 'گپ',
            'url': 'https://t.me/cpy_gap'
        }]
    ])

def has_user_reacted(link_id, user_id):
    """Check if user has already given feedback for this link"""
    if link_id in link_user_details and 'feedback' in link_user_details[link_id]:
        return any(f['user_id'] == user_id for f in link_user_details[link_id]['feedback'])
    return False

if __name__ == "__main__":
    print("Telegram Account Link Bot - Corrected Version")
    print("=" * 50)
    start_bot()
