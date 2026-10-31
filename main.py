import os
import time
import threading
import uuid
import requests
from flask import Flask

# ================= НАСТРОЙКИ =================
TPLINK_EMAIL = "maroz911111@gmail.com"
TPLINK_PASSWORD = "DjMoroz1991"
ROUTER_MAC = "AC-A7-F1-1D-9D-5C"

BOT_TOKEN = "9144693739:AAGpzCAJqvXh1g63rNmauThBHkFTIKFwjhU"
CHAT_IDS = ["2016745729"]
# =============================================

TERMINAL_UUID = str(uuid.uuid4())
app = Flask(__name__)

current_status = None
last_check_time = "еще не проверялось"

@app.route('/')
def home():
    return "Монитор света онлайн 24/7", 200

def send_telegram(text: str, target_chat_id=None):
    recipients = [target_chat_id] if target_chat_id else CHAT_IDS
    for chat_id in recipients:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Ошибка отправки Telegram: {e}")

def get_tplink_token():
    url = "https://n-wap.tplinkcloud.com"
    payload = {
        "method": "login",
        "params": {
            "appType": "Tether",
            "cloudUserName": TPLINK_EMAIL,
            "cloudPassword": TPLINK_PASSWORD,
            "terminalUUID": TERMINAL_UUID
        }
    }
    try:
        res = requests.post(url, json=payload, timeout=15).json()
        if res.get("error_code") == 0:
            return res["result"]["token"]
        print(f"Ошибка авторизации TP-Link: {res}")
    except Exception as e:
        print(f"Ошибка запроса токена TP-Link: {e}")
    return None

def is_router_online(token):
    if not token:
        return None
    url = f"https://n-wap.tplinkcloud.com?token={token}"
    payload = {"method": "getDeviceList", "params": {}}
    try:
        res = requests.post(url, json=payload, timeout=15).json()
        if res.get("error_code") == 0:
            for dev in res.get("result", {}).get("deviceList", []):
                mac = dev.get("deviceMac", "").upper().replace(":", "-")
                target_mac = ROUTER_MAC.upper().replace(":", "-")
                if target_mac in mac or mac in target_mac:
                    return dev.get("status") == 1
    except Exception as e:
        print(f"Ошибка проверки статуса: {e}")
    return None

def monitor():
    global current_status, last_check_time
    token = get_tplink_token()
    last_status = None
    offline_count = 0

    while True:
        try:
            status = is_router_online(token)
            if status is None:
                token = get_tplink_token()
                status = is_router_online(token)

            if status is not None:
                current_status = status
                last_check_time = time.strftime("%H:%M:%S")
