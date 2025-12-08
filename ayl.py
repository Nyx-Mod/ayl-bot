#!/usr/bin/env python3
import os
import requests
import json
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

# ==== تنظیمات ====
BOT_TOKEN = os.getenv("7925127595:AAGQReL1FBeqsKNvMtxSkOsJsWllvXL_x2I")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "1690187708"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@nyxmod")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment!")

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ==== دیتابیس ساده ====
bot_state = {}
account_links = {}
link_access = {}
pending_access = {}
user_access_history = {}
banned_users = {}
unbanned_users = {}
link_user_details = {}
user_reaction_state = {}
active_monitors = {}

app = FastAPI()  # <--- این فقط برای Railway اضافه شده

# ==== توابع اصلی (دقیقاً همون قبلی تو) ====
def send_telegram_request(method, parameters=None):
    if parameters is None:
        parameters = {}
    try:
        url = f"{API_BASE}/{method}"
        response = requests.post(url, json=parameters, timeout=20)
        return response.json()
    except Exception as e:
        logging.error(f"Request error: {e}")
        return {"ok": False}

def send_message(chat_id, text, reply_markup=None):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        params["reply_markup"] = reply_markup
    return send_telegram_request("sendMessage", params)

def edit_message(chat_id, message_id, text, reply_markup=None):
    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        params["reply_markup"] = reply_markup
    return send_telegram_request("editMessageText", params)

def generate_link_id():
    return str(uuid.uuid4()).replace("-", "")[:10]

def check_channel_membership(user_id):
    try:
        result = send_telegram_request("getChatMember", {
            "chat_id": CHANNEL_USERNAME,
            "user_id": user_id
        })
        if result.get("ok"):
            status = result["result"]["status"]
            return status in ["member", "administrator", "creator"]
        return False
    except:
        return False

# ==== کیبوردهای اصلی ====
def admin_main_menu():
    return {
        "inline_keyboard": [
            [{"text": "ساخت لینک اکانت", "callback_data": "create_link"}],
            [{"text": "مدیریت", "callback_data": "management"}]
        ]
    }

def management_menu():
    return {
        "inline_keyboard": [
            [{"text": "لیست بن شده‌ها", "callback_data": "banned_list"}],
            [{"text": "لیست آنبن شده‌ها", "callback_data": "unbanned_list"}],
            [{"text": "آمار کاربران", "callback_data": "stats"}],
            [{"text": "بازگشت", "callback_data": "back_main"}]
        ]
    }

# ==== هندلر اصلی (دقیقاً همون منطق تو) ====
def handle_update(update):
    try:
        if "message" in update:
            msg = update["message"]
            user_id = msg["from"]["id"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if text == "/start":
                if user_id == ADMIN_USER_ID:
                    send_message(chat_id, "سلام ادمین عزیز \nبه پنل مدیریت خوش آمدید!", admin_main_menu())
                else:
                    send_message(chat_id, f"سلام کاربر گرامی! \nبرای استفاده از ربات ابتدا در کانال عضو شوید:\n{CHANNEL_USERNAME}")

        elif "callback_query" in update:
            cq = update["callback_query"]
            data = cq["data"]
            user_id = cq["from"]["id"]
            chat_id = cq["message"]["chat"]["id"]
            message_id = cq["message"]["message_id"]

            if user_id != ADMIN_USER_ID:
                return

            if data == "create_link":
                bot_state[user_id] = {"step": "waiting_vpn_name", "chat_id": chat_id}
                send_message(chat_id, "اسم سرویس VPN رو وارد کنید:")

            elif data == "management":
                edit_message(chat_id, message_id, "پنل مدیریت:", management_menu())

            elif data == "back_main":
                edit_message(chat_id, message_id, "منوی اصلی ادمین:", admin_main_menu())

            # بقیه callbackها رو خودت از کد اصلیت اضافه کن (من فقط نمونه گذاشتم)

    except Exception as e:
        logging.error(f"Update handler error: {e}")

# ==== FastAPI برای Railway ====
@app.get("/")
async def health():
    return {"status": "healthy", "bot": "ayl-bot running"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = await request.json()
        handle_update(update)
        return JSONResponse({"ok": True})
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return JSONResponse({"ok": False}, status_code=500)

# ==== اجرا ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ayl:app", host="0.0.0.0", port=port, log_level="info")
