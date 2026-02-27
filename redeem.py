import json
import requests
import datetime
import time
import os
import re
import sys
from config import HOYOLAB_FILE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

LOG_FILE   = "redeem.log"
CODES_FILE = "codes.txt"

# ================= LOG =================
def log(msg):
    now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
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
def load_cookie():
    if not os.path.exists(HOYOLAB_FILE):
        log("❌ Không tìm thấy hoyolab.json")
        return None

    try:
        with open(HOYOLAB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log(f"❌ Lỗi đọc JSON: {e}")
        return None

    cookies = {
        c["name"]: c["value"]
        for c in data.get("cookies", [])
        if c.get("name") and c.get("value")
    }

    if "ltoken_v2" not in cookies or "ltuid_v2" not in cookies:
        log("❌ Thiếu ltoken_v2 hoặc ltuid_v2 trong cookie")
        return None

    return cookies

# ================= GET UID =================
def get_asia_uid(cookies):
    url     = "https://api-os-takumi.hoyoverse.com/binding/api/getUserGameRolesByLtoken"
    params  = {"game_biz": "hk4e_global"}
    headers = {
        "User-Agent":     "Mozilla/5.0",
        "Referer":        "https://www.hoyolab.com/",
        "x-rpc-language": "vi-vn"
    }

    try:
        r    = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=10)
        data = r.json()
    except Exception as e:
        log(f"❌ Lỗi kết nối: {e}")
        return None

    if data.get("retcode") != 0:
        log(f"❌ Không lấy được danh sách tài khoản: {data.get('message')}")
        return None

    roles = data.get("data", {}).get("list", [])
    if not roles:
        log("❌ Không tìm thấy tài khoản Genshin nào")
        return None

    asia_roles = [r for r in roles if r.get("region") == "os_asia"] or roles
    role       = asia_roles[0]

    log(f"🎮 Nhân vật: {role['nickname']} | UID: {role['game_uid']} | Server: {role['region']}")
    return role["game_uid"], role["nickname"]

# ================= PARSE COOLDOWN =================
def parse_cooldown_seconds(message):
    """
    Trích xuất số giây cooldown từ message của HoYo.
    Ví dụ: "Đang CD đổi thưởng, vui lòng đợi 1 giây sau thử lại"  → 1
            "please wait 5 seconds"                                  → 5
    """
    match = re.search(r"(\d+)\s*(giây|second)", message, re.IGNORECASE)
    if match:
        return int(match.group(1))
    # Nếu message có chữ CD nhưng không rõ số giây → mặc định 5s
    if "cd" in message.lower() or "cooldown" in message.lower() or "wait" in message.lower():
        return 5
    return 0

# ================= REDEEM (có retry khi CD) =================
def redeem_code(cookies, uid, code, nickname="", max_retries=3):
    url    = "https://sg-hk4e-api.hoyoverse.com/common/apicdkey/api/webExchangeCdkey"
    params = {
        "uid":      uid,
        "region":   "os_asia",
        "lang":     "vi",
        "cdkey":    code,
        "game_biz": "hk4e_global"
    }
    headers = {
        "User-Agent":     "Mozilla/5.0",
        "Referer":        "https://genshin.hoyoverse.com/",
        "x-rpc-language": "vi-vn"
    }

    for attempt in range(1, max_retries + 1):
        try:
            r      = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=10)
            result = r.json()
        except Exception as e:
            log(f"❌ Lỗi kết nối khi redeem: {e}")
            return False

        retcode = result.get("retcode", -1)
        msg     = result.get("message", "unknown error")

        if retcode == 0:
            log(f"✅ [{code}] ĐỔI CODE THÀNH CÔNG!")
            send_telegram(f"✅ Genshin ({nickname}): Đổi code [{code}] thành công!")
            return True

        # Kiểm tra có phải đang cooldown không
        cd_secs = parse_cooldown_seconds(msg)
        if cd_secs > 0 and attempt < max_retries:
            wait = cd_secs + 1   # cộng thêm 1s buffer
            log(f"⏳ [{code}] Đang CD ({msg}) — chờ {wait}s rồi thử lại (lần {attempt}/{max_retries})...")
            time.sleep(wait)
            continue  # retry

        # Lỗi thật (hết hạn, đã dùng, sai code...)
        log(f"❌ [{code}] FAIL: {msg}")
        send_telegram(f"❌ Genshin ({nickname}): Code [{code}] thất bại — {msg}")
        return False

    # Hết retry mà vẫn CD
    log(f"❌ [{code}] Hết lần retry, bỏ qua.")
    send_telegram(f"❌ Genshin ({nickname}): Code [{code}] bị bỏ qua sau {max_retries} lần thử")
    return False

# ================= ĐỌC FILE TXT =================
def load_codes_from_file(filepath):
    codes = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            code = line.strip().upper()
            if code and not code.startswith("#"):
                codes.append(code)
    return codes

# ================= MAIN =================
def main():
    print("===== GENSHIN REDEEM TOOL (ASIA) =====")
    log("===== START REDEEM =====")

    cookies = load_cookie()
    if not cookies:
        log("===== END REDEEM =====\n")
        return

    result = get_asia_uid(cookies)
    if not result:
        log("===== END REDEEM =====\n")
        return
    uid, nickname = result

    # ── Chế độ tự động: đọc từ codes.txt ──
    if os.path.exists(CODES_FILE):
        codes = load_codes_from_file(CODES_FILE)
        if not codes:
            log(f"⚠️ {CODES_FILE} trống, chuyển sang nhập tay.")
        else:
            log(f"📄 Tìm thấy {len(codes)} code trong {CODES_FILE}, bắt đầu redeem tự động...")
            ok = fail = 0
            for code in codes:
                success = redeem_code(cookies, uid, code, nickname)
                if success:
                    ok += 1
                else:
                    fail += 1
                time.sleep(2)   # delay cơ bản giữa các code

            log(f"🏁 Xong! Thành công: {ok} | Thất bại: {fail}")
            send_telegram(
                f"🏁 Genshin ({nickname}): Redeem xong\n"
                f"✅ Thành công: {ok}\n❌ Thất bại: {fail}"
            )
            log("===== END REDEEM =====\n")
            return

    # ── Chế độ nhập tay (fallback nếu không có codes.txt) ──
    print(f"💡 Không tìm thấy {CODES_FILE}. Nhập tay từng code rồi Enter. Nhấn 't' để thoát.\n")
    while True:
        code = input("Nhập Gift Code (hoặc 't' để thoát): ").strip().upper()
        if code == "T":
            log("👋 Thoát chương trình.")
            break
        if not code:
            log("⚠️ Chưa nhập code, thử lại.")
            continue

        redeem_code(cookies, uid, code, nickname)
        time.sleep(2)

    log("===== END REDEEM =====\n")

if __name__ == "__main__":
    main()