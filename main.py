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
raw_debug_info = "ожидание первой проверки..."
is_ started = False

@app.route('/')
def home():
    return f"Монитор онлайн | Статус: {current_status} | Время: {last_check_time}", 200

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
            requests.post(url, json=payload, timeout=8)
        except Exception as e:
            print(f"Ошибка отправки Telegram: {e}")

def check_router():
    global current_status, last_check_time, raw_debug_info
    
    # Пробуем глобальный и европейский серверы TP-Link
    endpoints = [
        "https://eu-wap.tplinkcloud.com",
        "https://n-wap.tplinkcloud.com",
        "https://wap.tplinkcloud.com"
    ]
    
    login_payload = {
        "method": "login",
        "params": {
            "appType": "Tether",
            "cloudUserName": TPLINK_EMAIL,
            "cloudPassword": TPLINK_PASSWORD,
            "terminalUUID": TERMINAL_UUID
        }
    }

    token = None
    active_url = None
    last_err = ""

    for base_url in endpoints:
        try:
            res = requests.post(base_url, json=login_payload, timeout=7).json()
            if res.get("error_code") == 0:
                token = res["result"]["token"]
                active_url = base_url
                break
            else:
                last_err = f"Код {res.get('error_code')}: {res.get('msg')}"
        except Exception as e:
            last_err = str(e)

    if not token:
        raw_debug_info = f"Ошибка входа в TP-Link ({last_err})"
        return None

    try:
        dev_url = f"{active_url}?token={token}"
        res = requests.post(dev_url, json={"method": "getDeviceList", "params": {}}, timeout=7).json()
        
        if res.get("error_code") == 0:
            devices = res.get("result", {}).get("deviceList", [])
            if not devices:
                raw_debug_info = "Список устройств в аккаунте TP-Link пуст (0 роутеров)"
                return None

            clean_target = ROUTER_MAC.upper().replace(":", "").replace("-", "")

            for dev in devices:
                dev_mac = str(dev.get("deviceMac", "")).upper().replace(":", "").replace("-", "")
                alias = dev.get("alias", dev.get("deviceName", "Роутер"))
                status_val = dev.get("status")
                app_server = dev.get("appServerUrl", active_url)

                # Если устройство привязано к региональному appServerUrl, проверим его там при необходимости
                if clean_target in dev_mac or len(devices) == 1:
                    is_online = (status_val == 1)
                    current_status = is_online
                    last_check_time = time.strftime("%H:%M:%S")
                    raw_debug_info = f"Найден: {alias} | MAC: {dev.get('deviceMac')} | status={status_val}"
                    return is_online

            mac_list = [f"{d.get('alias')}: {d.get('deviceMac')} (st={d.get('status')})" for d in devices]
            raw_debug_info = f"MAC не совпал. Устройства в аккаунте: {', '.join(mac_list)}"
        else:
            raw_debug_info = f"Ошибка списка устройств: {res}"
    except Exception as e:
        raw_debug_info = f"Ошибка связи с облаком: {e}"

    return None

def monitor():
    last_status = None
    offline_count = 0

    while True:
        try:
