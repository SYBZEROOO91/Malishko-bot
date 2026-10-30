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

@app.route('/')
def home():
    return "Монитор света онлайн 24/7", 200

def send_telegram(text: str):
    for chat_id in CHAT_IDS:
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
                if last_status is None:
                    last_status = status

                # Роутер недоступен 2 проверки подряд
                if not status and last_status:
                    offline_count += 1
                    if offline_count >= 2:
                        send_telegram("🔴 <b>Свет пропал!</b>\nСвязь с роутером дома потеряна.")
                        last_status = False
                        offline_count = 0
                elif status and not last_status:
                    send_telegram("🟢 <b>Свет появился!</b>\nРоутер дома снова в сети.")
                    last_status = True
                    offline_count = 0
                else:
                    offline_count = 0
        except Exception as err:
            print(f"Сбой цикла: {err}")

        time.sleep(60)

# Фоновый поток опроса облака
threading.Thread(target=monitor, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
