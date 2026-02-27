import requests
import json
import os
import socket
from datetime import datetime
from config import HOYOLAB_FILE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# ================= CONFIG =================
LOG_FILE = "checkin.log"
ACT_ID   = "e202102251931481"

INFO_API      = "https://sg-hk4e-api.hoyolab.com/event/sol/info"
SIGN_API      = "https://sg-hk4e-api.hoyolab.com/event/sol/sign"
USER_INFO_API = "https://bbs-api-os.hoyolab.com/community/user/wapi/getUserFullInfo"

# ================= LOG =================
def log(msg):
    t    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{t}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ================= TELEGRAM =================
def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception:
        pass

# ================= COOKIE =================
def load_headers():
    with open(HOYOLAB_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    cookie_str = "; ".join(
        f"{c['name']}={c['value']}" for c in state["cookies"]
    )
    return {
        "User-Agent": "Mozilla/5.0",
        "Referer":    "https://www.hoyolab.com",
        "Cookie":     cookie_str
    }

# ================= ACCOUNT NAME =================
def get_account_name(headers):
    try:
        r = requests.get(USER_INFO_API, headers=headers, timeout=10)
        j = r.json()
        if j.get("retcode") == 0:
            return j["data"]["user_info"]["nickname"]
    except Exception:
        pass
    return "UNKNOWN"

# ================= MAIN =================
if __name__ == "__main__":
    log("===== START CHECK-IN =====")
    log(f"Host: {socket.gethostname()}")

    if not os.path.exists(HOYOLAB_FILE):
        log("STATUS: FAIL — hoyolab.json not found")
        send_telegram("❌ HoYoLAB: Không tìm thấy cookie (hoyolab.json)")
        exit(1)

    headers      = load_headers()
    account_name = get_account_name(headers)   # luôn có giá trị, ít nhất là "UNKNOWN"
    log(f"Account: {account_name}")

    try:
        r    = requests.get(INFO_API, params={"act_id": ACT_ID}, headers=headers, timeout=15)
        data = r.json()

        if data.get("data", {}).get("is_sign") is True:
            log("STATUS: ALREADY")
            send_telegram(f"ℹ️ HoYoLAB ({account_name}): Hôm nay đã điểm danh rồi")
        else:
            r      = requests.post(SIGN_API, json={"act_id": ACT_ID}, headers=headers, timeout=15)
            result = r.json()

            if result.get("retcode") == 0:
                log("STATUS: SUCCESS")
                send_telegram(f"✅ HoYoLAB ({account_name}): Điểm danh thành công!")
            else:
                log("STATUS: FAIL")
                log(f"DETAIL: {result}")
                send_telegram(f"❌ HoYoLAB ({account_name}): Check-in thất bại\n{result}")

    except Exception as e:
        log("STATUS: ERROR")
        log(f"DETAIL: {e}")
        send_telegram(f"❌ HoYoLAB ({account_name}): Lỗi\n{e}")

    log("===== END CHECK-IN =====\n")
