import hashlib, json, random, requests, datetime, time, os, re, socket, string, sys, threading, subprocess
from config import HOYOLAB_FILE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────
CODES_FILE = "codes.txt"
ACT_ID     = "e202102251931481"
INFO_API   = "https://sg-hk4e-api.hoyolab.com/event/sol/info"
SIGN_API   = "https://sg-hk4e-api.hoyolab.com/event/sol/sign"
BASE_URL   = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ─────────────────────────────────────────
# DS SALT — nguồn: reverse engineering / community
# ─────────────────────────────────────────
# Salt cho overseas HoYoLAB game_record API (bbs-api-os.hoyolab.com)
# DS type 1 — dùng cho cả GET (với query) và POST (với body)
_SALT_OS = "6cqshh5dhw73bzxn20oexa9k516chk7s"

# Dict lưu subprocess login đang chờ Enter
_LOGIN_PROCS: dict = {}

# ─────────────────────────────────────────
# DS HELPER
# ─────────────────────────────────────────
def _make_ds(body: str = "", query: str = "") -> str:
    """
    Tạo Dynamic Secret type-1 cho HoYoLAB overseas API.
    - GET requests: truyền query="role_id=xxx&server=yyy", body=""
    - POST requests: truyền body=json_string, query=""
    """
    t = int(time.time())
    r = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    h = hashlib.md5(f"salt={_SALT_OS}&t={t}&r={r}&b={body}&q={query}".encode()).hexdigest()
    return f"{t},{r},{h}"

def _cookie_str(cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())

def _safe_json(resp) -> dict:
    try:
        return resp.json()
    except Exception:
        return {"retcode": -1, "message": f"Invalid JSON (HTTP {resp.status_code})"}

def _base_headers(cookie_str: str) -> dict:
    return {
        "User-Agent":        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer":           "https://act.hoyolab.com",
        "Origin":            "https://act.hoyolab.com",
        "x-rpc-app_version": "1.5.0",
        "x-rpc-client_type": "5",
        "x-rpc-language":    "vi-vn",
        "Cookie":            cookie_str,
    }

# ─────────────────────────────────────────
# TELEGRAM HELPERS
# ─────────────────────────────────────────
def send(chat_id, text):
    try:
        requests.post(f"{BASE_URL}/sendMessage",
                      data={"chat_id": chat_id, "text": text},
                      timeout=10)
    except Exception:
        pass

def send_photo(chat_id, photo_path, caption=""):
    try:
        with open(photo_path, "rb") as f:
            requests.post(f"{BASE_URL}/sendPhoto",
                          data={"chat_id": chat_id, "caption": caption},
                          files={"photo": f}, timeout=30)
    except Exception as e:
        send(chat_id, f"❌ Lỗi gửi ảnh: {e}")

def send_file(chat_id, file_path, caption=""):
    try:
        with open(file_path, "rb") as f:
            requests.post(f"{BASE_URL}/sendDocument",
                          data={"chat_id": chat_id, "caption": caption},
                          files={"document": f}, timeout=60)
    except Exception as e:
        send(chat_id, f"❌ Lỗi gửi file: {e}")

def get_updates(offset=None):
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
        return r.json().get("result", [])
    except Exception:
        return []

# ─────────────────────────────────────────
# COOKIE / ACCOUNT
# ─────────────────────────────────────────
def load_cookie():
    if not os.path.exists(HOYOLAB_FILE):
        return None, "❌ Không tìm thấy hoyolab.json"
    try:
        with open(HOYOLAB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return None, f"❌ Lỗi đọc JSON: {e}"
    cookies = {
        c["name"]: c["value"]
        for c in data.get("cookies", [])
        if c.get("name") and c.get("value")
    }
    if "ltoken_v2" not in cookies or "ltuid_v2" not in cookies:
        return None, "❌ Cookie thiếu ltoken_v2/ltuid_v2 — đăng nhập lại (/login)"
    return cookies, "OK"

def load_headers():
    with open(HOYOLAB_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    cs = "; ".join(f"{c['name']}={c['value']}" for c in state["cookies"])
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer":    "https://www.hoyolab.com",
        "Cookie":     cs,
        "Origin":     "https://www.hoyolab.com",
    }

def get_account_info(cookies):
    url = "https://api-os-takumi.hoyoverse.com/binding/api/getUserGameRolesByLtoken"
    try:
        r = requests.get(url,
                         headers={"User-Agent": "Mozilla/5.0",
                                  "Referer":    "https://www.hoyolab.com/"},
                         cookies=cookies,
                         params={"game_biz": "hk4e_global"},
                         timeout=10)
        data = r.json()
    except Exception:
        return None
    if data.get("retcode") != 0:
        return None
    roles      = data.get("data", {}).get("list", [])
    asia_roles = [r for r in roles if r.get("region") == "os_asia"] or roles
    if not asia_roles:
        return None
    role = asia_roles[0]
    return role["game_uid"], role["nickname"], role["region"]

def check_cookie_status(cookies):
    url = "https://bbs-api-os.hoyolab.com/community/user/wapi/getUserFullInfo"
    try:
        r = requests.get(url,
                         headers={"User-Agent": "Mozilla/5.0",
                                  "Referer":    "https://www.hoyolab.com"},
                         cookies=cookies, timeout=10)
        j = r.json()
        if j.get("retcode") == 0:
            return f"✅ Cookie hợp lệ — tài khoản: {j['data']['user_info']['nickname']}"
        return f"⚠️ Cookie lạ: {j.get('message')} (retcode {j.get('retcode')})"
    except Exception as e:
        return f"❌ Không kết nối được: {e}"

# ─────────────────────────────────────────
# CHARACTERS
# Endpoint đúng: POST bbs-api-os.hoyolab.com/game_record/genshin/api/character
# Salt đúng: 6cqshh5dhw73bzxn20oexa9k516chk7s
# ─────────────────────────────────────────
def get_characters(cookies, uid, region):
    cs       = _cookie_str(cookies)
    # body phải sort_keys để DS hash nhất quán
    body_str = json.dumps({"role_id": str(uid), "server": region},
                          separators=(",", ":"), sort_keys=True)
    headers  = _base_headers(cs)
    headers["Content-Type"] = "application/json"
    headers["DS"]           = _make_ds(body=body_str, query="")

    # Endpoint chính xác theo community research
    url = "https://bbs-api-os.hoyolab.com/game_record/genshin/api/character"
    try:
        r = requests.post(url, headers=headers, data=body_str, timeout=15)
        d = _safe_json(r)
        print(f"[chars] HTTP {r.status_code} rc={d.get('retcode')} msg={d.get('message','')[:60]}")
        return d
    except Exception as e:
        print(f"[chars] lỗi: {e}")
        return {"retcode": -1, "message": str(e)}

# ─────────────────────────────────────────
# REAL-TIME NOTES (Resin)
# Endpoint: GET bbs-api-os.hoyolab.com/game_record/genshin/api/dailyNote
# DS: query string phải khớp CHÍNH XÁC với URL params
# ─────────────────────────────────────────
def get_realtime_notes(cookies, uid, region):
    cs = _cookie_str(cookies)
    # QUAN TRỌNG: query string cho DS phải khớp y hệt URL params
    # Sort alphabet: role_id trước server
    query_str = f"role_id={uid}&server={region}"
    headers   = _base_headers(cs)
    headers["DS"] = _make_ds(body="", query=query_str)
    # Dùng f-string URL — không dùng params= để requests không encode lại thứ tự
    url = f"https://bbs-api-os.hoyolab.com/game_record/genshin/api/dailyNote?{query_str}"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        d = _safe_json(r)
        print(f"[resin] HTTP {r.status_code} rc={d.get('retcode')} msg={d.get('message','')[:60]}")
        return d
    except Exception as e:
        print(f"[resin] lỗi: {e}")
        return {"retcode": -1, "message": str(e)}

# ─────────────────────────────────────────
# GENSHIN VERSION / LIVESTREAM SCHEDULE
# ─────────────────────────────────────────
GENSHIN_VERSIONS = [
    ("5.4", "2026-02-05"),
    ("5.5", "2026-03-19"),
    ("5.6", "2026-04-30"),
    ("5.7", "2026-06-11"),
    ("5.8", "2026-07-23"),
]

def get_livestream_info():
    today = datetime.date.today()
    for ver, patch_str in GENSHIN_VERSIONS:
        patch_date  = datetime.date.fromisoformat(patch_str)
        stream_date = patch_date - datetime.timedelta(days=7)
        if patch_date > today:
            return {
                "version":        ver,
                "patch_date":     patch_date,
                "stream_date":    stream_date,
                "days_to_stream": max(0, (stream_date - today).days),
                "stream_passed":  stream_date <= today,
                "days_to_patch":  (patch_date - today).days,
            }
    return None

# ─────────────────────────────────────────
# AUTO FETCH CODES
# ─────────────────────────────────────────
_CODE_BLACKLIST = {
    "WINDOWS","MOZILLA","WEBKIT","CHROME","SAFARI","FIREFOX","OPERA","EDGE",
    "GENSHIN","IMPACT","HOYOLAB","HOYOVERSE","MIHOYO","PAIMON","TEYVAT",
    "MONDSTADT","LIYUE","INAZUMA","SUMERU","FONTAINE","NATLAN","SNEZHNAYA",
    "PRIMOGEM","INTERTWINED","ACQUAINT","FATES","GENESIS",
    "JAVASCRIPT","STYLESHEET","BOOTSTRAP","JQUERY","CLOUDFLARE",
    "TWITTER","FACEBOOK","INSTAGRAM","YOUTUBE","TWITCH","DISCORD","REDDIT",
    "COPYRIGHT","PRIVACY","POLICY","TERMS","SERVICE","CONTACT","ABOUT",
    "ANDROID","IPHONE","IPAD","MACOS","LINUX","UBUNTU",
    "JANUARY","FEBRUARY","MARCH","APRIL","JUNE","JULY",
    "AUGUST","SEPTEMBER","OCTOBER","NOVEMBER","DECEMBER",
    "HTML","HTTP","HTTPS","JSON","XML","CSS","PHP","PYTHON",
    "SUBSCRIBE","COMMENT","FOLLOW","DOWNLOAD","INSTALL","UPDATE",
    "PRIMOGEMS","WISHES","BANNER","CHARACTER","VERSION","PATCH",
    "ANNIVERSARY","CELEBRATION","SPECIAL","PROGRAM","EVENT",
}

def _is_valid_code(s):
    if len(s) < 8 or len(s) > 20:         return False
    if s in _CODE_BLACKLIST:               return False
    if not any(c.isdigit() for c in s):    return False
    if not any(c.isalpha() for c in s):    return False
    if not re.fullmatch(r'[A-Z0-9]+', s):  return False
    return True

def fetch_codes_from_web():
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    headers = {"User-Agent": ua, "Accept-Language": "en-US,en;q=0.9"}
    SOURCES = [
        ("genshin.gg",    "https://genshin.gg/gift-codes/"),
        ("pockettactics", "https://www.pockettactics.com/genshin-impact/codes"),
        ("game8",         "https://game8.co/games/Genshin-Impact/archives/304759"),
        ("eurogamer",     "https://www.eurogamer.net/genshin-impact-codes-8639"),
        ("gamesradar",    "https://www.gamesradar.com/genshin-impact-codes/"),
    ]
    found: dict = {}
    for src_name, url in SOURCES:
        try:
            r    = requests.get(url, headers=headers, timeout=15)
            html = r.text
            kw   = re.compile(r'(?:redeem|gift.?code|promo.?code|coupon|cdkey)', re.IGNORECASE)
            search_text = ""
            for m in kw.finditer(html):
                search_text += html[max(0, m.start()-200):min(len(html), m.start()+600)] + " "
            if not search_text:
                search_text = html
            for code in re.findall(r'\b([A-Z][A-Z0-9]{7,19})\b', search_text):
                if _is_valid_code(code):
                    found.setdefault(code, set()).add(src_name)
        except Exception as e:
            print(f"[fetchcodes] {src_name} lỗi: {e}")
    sorted_codes = sorted(found.keys(), key=lambda c: (-len(found[c]), c))
    return {"active": sorted_codes, "source_count": {c: len(found[c]) for c in sorted_codes}}

# ─────────────────────────────────────────
# REDEEM HELPERS
# ─────────────────────────────────────────
def parse_cooldown_seconds(message):
    m = re.search(r"(\d+)\s*(giây|second)", message, re.IGNORECASE)
    if m:
        return int(m.group(1))
    if any(w in message.lower() for w in ("cd", "cooldown", "wait")):
        return 5
    return 0

def redeem_one(cookies, uid, code, max_retries=3):
    url    = "https://sg-hk4e-api.hoyoverse.com/common/apicdkey/api/webExchangeCdkey"
    params = {"uid": uid, "region": "os_asia", "lang": "vi",
              "cdkey": code, "game_biz": "hk4e_global"}
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://genshin.hoyoverse.com/",
               "x-rpc-language": "vi-vn"}
    for attempt in range(1, max_retries + 1):
        try:
            r      = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=10)
            result = r.json()
        except Exception as e:
            return False, f"Lỗi kết nối: {e}"
        retcode = result.get("retcode", -1)
        msg     = result.get("message", "unknown error")
        if retcode == 0:
            return True, "Thành công"
        cd = parse_cooldown_seconds(msg)
        if cd > 0 and attempt < max_retries:
            time.sleep(cd + 1)
            continue
        return False, msg
    return False, "Hết retry"

def load_codes_from_file():
    if not os.path.exists(CODES_FILE):
        return []
    codes = []
    with open(CODES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            c = line.strip().upper()
            if c and not c.startswith("#"):
                codes.append(c)
    return codes

# ─────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────
def cmd_status(chat_id):
    lines = ["━━━━━━━━━━━━━━━━━━━━",
             "📊 TRẠNG THÁI HỆ THỐNG",
             "━━━━━━━━━━━━━━━━━━━━",
             f"🖥  Host : {socket.gethostname()}",
             f"🕐 Giờ  : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             ""]
    cookies, err = load_cookie()
    if not cookies:
        lines.append(f"🍪 COOKIE\n   {err}")
        send(chat_id, "\n".join(lines)); return
    lines += ["🍪 COOKIE", f"   {check_cookie_status(cookies)}", ""]
    info = get_account_info(cookies)
    if info:
        uid, nickname, region = info
        lines += ["🎮 TÀI KHOẢN GENSHIN",
                  f"   👤 Tên   : {nickname}",
                  f"   🆔 UID   : {uid}",
                  f"   🌏 Server: {region}", ""]
    try:
        hdrs    = load_headers()
        r       = requests.get(INFO_API, params={"act_id": ACT_ID}, headers=hdrs, timeout=10)
        data    = r.json().get("data", {})
        is_sign = data.get("is_sign", False)
        today   = data.get("today", "?")
        sign_day= data.get("total_sign_day", "?")
        lines  += ["📅 ĐIỂM DANH",
                   f"   📆 Hôm nay : {today}",
                   f"   {'✅ Đã điểm danh' if is_sign else '❌ Chưa điểm danh'}",
                   f"   📈 Tháng này: {sign_day} ngày"]
    except Exception as e:
        lines.append(f"📅 ĐIỂM DANH\n   ⚠️ Lỗi: {e}")
    send(chat_id, "\n".join(lines))

def cmd_uid(chat_id):
    cookies, err = load_cookie()
    if not cookies:
        send(chat_id, err); return
    info = get_account_info(cookies)
    if not info:
        send(chat_id, "❌ Không lấy được thông tin tài khoản"); return
    uid, nickname, region = info
    send(chat_id, f"🎮 Nhân vật: {nickname}\n🆔 UID: {uid}\n🌏 Server: {region}")

def cmd_checkin(chat_id):
    cookies, err = load_cookie()
    if not cookies:
        send(chat_id, err); return
    send(chat_id, "⏳ Đang điểm danh...")
    try:
        hdrs = load_headers()
        r    = requests.get(INFO_API, params={"act_id": ACT_ID}, headers=hdrs, timeout=15)
        if r.json().get("data", {}).get("is_sign") is True:
            send(chat_id, "ℹ️ Hôm nay đã điểm danh rồi!"); return
        r = requests.post(SIGN_API, json={"act_id": ACT_ID}, headers=hdrs, timeout=15)
        result = r.json()
        if result.get("retcode") == 0:
            send(chat_id, "✅ Điểm danh thành công!")
        else:
            send(chat_id, f"❌ Điểm danh thất bại: {result.get('message')}")
    except Exception as e:
        send(chat_id, f"❌ Lỗi: {e}")

def cmd_redeem(chat_id, code):
    if not code:
        send(chat_id, "⚠️ Dùng: /redeem ABCD1234"); return
    cookies, err = load_cookie()
    if not cookies:
        send(chat_id, err); return
    info = get_account_info(cookies)
    if not info:
        send(chat_id, "❌ Không lấy được UID"); return
    uid, nickname, _ = info
    send(chat_id, f"⏳ Đang đổi code [{code}]...")
    ok, msg = redeem_one(cookies, uid, code)
    send(chat_id, f"✅ [{code}] Đổi thành công!" if ok else f"❌ [{code}] Thất bại: {msg}")

def cmd_redeemall(chat_id):
    codes = load_codes_from_file()
    if not codes:
        send(chat_id, f"⚠️ Không có code nào trong {CODES_FILE}"); return
    cookies, err = load_cookie()
    if not cookies:
        send(chat_id, err); return
    info = get_account_info(cookies)
    if not info:
        send(chat_id, "❌ Không lấy được UID"); return
    uid, nickname, _ = info
    send(chat_id, f"📄 Tìm thấy {len(codes)} code, bắt đầu redeem...")
    ok_list, fail_list = [], []
    for code in codes:
        ok, msg = redeem_one(cookies, uid, code)
        (ok_list if ok else fail_list).append(code if ok else f"{code}: {msg}")
        time.sleep(2)
    lines = [f"🏁 Redeem xong cho {nickname}"]
    if ok_list:   lines.append("✅ Thành công:\n" + "\n".join(f"  • {c}" for c in ok_list))
    if fail_list: lines.append("❌ Thất bại:\n"   + "\n".join(f"  • {c}" for c in fail_list))
    send(chat_id, "\n".join(lines))

def cmd_characters(chat_id):
    cookies, err = load_cookie()
    if not cookies:
        send(chat_id, err); return
    info = get_account_info(cookies)
    if not info:
        send(chat_id, "❌ Không lấy được UID"); return
    uid, nickname, region = info
    send(chat_id, "⏳ Đang lấy danh sách nhân vật...")
    data    = get_characters(cookies, uid, region)
    retcode = data.get("retcode", -1)
    if retcode != 0:
        msg  = data.get("message", "unknown")
        hint = ""
        if retcode in (10001, -100):
            hint = "\n💡 Cookie hết hạn → /login để đăng nhập lại."
        elif retcode == 10307:
            hint = "\n💡 HoYoLAB → Cài đặt → Hồ sơ game → bật 'Hiển thị chi tiết nhân vật'."
        elif retcode == 10102:
            hint = "\n💡 HoYoLAB → Cài đặt → Hồ sơ game → chuyển sang chế độ công khai."
        else:
            hint = "\n💡 Kiểm tra: HoYoLAB → Cài đặt → Hồ sơ game → bật tất cả toggle."
        send(chat_id, f"❌ Lỗi ({retcode}): {msg}{hint}"); return
    chars = data.get("data", {}).get("list", [])
    if not chars:
        send(chat_id, "❌ Không có nhân vật.\n💡 Bật 'Hiển thị chi tiết nhân vật' trong HoYoLAB."); return
    chars.sort(key=lambda x: x.get("level", 0), reverse=True)
    elem_map = {1: "🌬", 2: "💧", 3: "🔥", 4: "⚡", 5: "🌿", 6: "❄️", 7: "🪨"}
    lines = [f"🎭 NHÂN VẬT — {nickname} ({len(chars)} nhân vật)\n"]
    for c in chars[:25]:
        elem  = elem_map.get(c.get("element_attr_id", 0), "✨")
        stars = "⭐" * min(c.get("rarity", 4), 5)
        lines.append(f"{elem} {c['name']} | Lv.{c['level']} | C{c.get('actived_constellation_num',0)} | {stars}")
    if len(chars) > 25:
        lines.append(f"\n... và {len(chars)-25} nhân vật nữa")
    send(chat_id, "\n".join(lines))

def cmd_resin(chat_id):
    cookies, err = load_cookie()
    if not cookies:
        send(chat_id, err); return
    info = get_account_info(cookies)
    if not info:
        send(chat_id, "❌ Không lấy được UID"); return
    uid, nickname, region = info
    send(chat_id, "⏳ Đang lấy thông tin nhựa...")
    data    = get_realtime_notes(cookies, uid, region)
    retcode = data.get("retcode", -1)
    if retcode != 0:
        msg  = data.get("message", "unknown")
        hint = ""
        if retcode in (10001, -100):
            hint = "\n💡 Cookie hết hạn → /login để đăng nhập lại."
        elif retcode in (10307, -10001, 10102):
            hint = "\n💡 HoYoLAB → Cài đặt → Hồ sơ game → bật 'Ghi Chép Thời Gian Thực'."
        send(chat_id, f"❌ Lỗi ({retcode}): {msg}{hint}"); return
    d = data.get("data", {})
    resin_cur = d.get("current_resin", 0)
    resin_max = d.get("max_resin", 160)
    eta_sec   = int(d.get("resin_recovery_time", "0"))
    eta_str   = "Đã đầy ✅" if eta_sec <= 0 else str(datetime.timedelta(seconds=eta_sec))
    full_at   = ""
    if eta_sec > 0:
        full_time = datetime.datetime.now() + datetime.timedelta(seconds=eta_sec)
        full_at   = f"\n   ⏰ Đầy lúc: {full_time.strftime('%H:%M %d/%m')}"
    exps     = d.get("expeditions", [])
    exp_done = sum(1 for e in exps if e.get("status") == "Finished")
    exp_text = f"{exp_done}/{len(exps)} xong" if exps else "Không có"
    daily_done  = d.get("finished_task_num", 0)
    daily_total = d.get("total_task_num", 4)
    extra_recv  = d.get("is_extra_task_reward_received", False)
    lines = [
        f"⚗️ NHỰA — {nickname}",
        f"   💧 Nhựa: {resin_cur}/{resin_max}",
        f"   ⏱ Đầy sau: {eta_str}{full_at}",
        f"   🗺 Expeditions: {exp_text}",
        f"   📋 Daily: {daily_done}/{daily_total} {'✅' if daily_done >= daily_total else '❌'}",
        f"   🎁 Thưởng daily: {'✅ Đã nhận' if extra_recv else '❌ Chưa nhận'}",
    ]
    transformer = d.get("transformer", {})
    if transformer.get("obtained"):
        trans_ready = transformer.get("recovery_time", {}).get("reached", False)
        lines.append(f"   🔮 Transformer: {'✅ Sẵn sàng!' if trans_ready else '⏳ Chưa sẵn sàng'}")
    send(chat_id, "\n".join(lines))

def cmd_screenshot(chat_id):
    send(chat_id, "📸 Đang chụp màn hình...")
    try:
        import tempfile
        path   = os.path.join(tempfile.gettempdir(), "screenshot.png")
        ps_cmd = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
            "$bmp = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height);"
            "$g = [System.Drawing.Graphics]::FromImage($bmp);"
            "$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size);"
            f"$bmp.Save('{path}');"
            "$g.Dispose(); $bmp.Dispose()"
        )
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, timeout=15)
        if os.path.exists(path):
            send_photo(chat_id, path, f"📸 {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
            os.remove(path)
        else:
            send(chat_id, "❌ Chụp màn hình thất bại")
    except Exception as e:
        send(chat_id, f"❌ Lỗi: {e}")

def _fmt_size(b):
    if b < 1024:    return f"{b}B"
    if b < 1024**2: return f"{b//1024}KB"
    if b < 1024**3: return f"{b//1024**2}MB"
    return f"{b//1024**3}GB"

def cmd_ls(chat_id, path=""):
    path = path.strip() or os.path.expanduser("~")
    if not os.path.exists(path):
        send(chat_id, f"❌ Không tìm thấy: {path}"); return
    try:
        items = os.listdir(path)
        lines = [f"📁 {path}\n"]
        dirs  = [i for i in items if os.path.isdir(os.path.join(path, i))]
        files = [i for i in items if os.path.isfile(os.path.join(path, i))]
        for d in sorted(dirs)[:30]:  lines.append(f"📂 {d}/")
        for f in sorted(files)[:30]:
            size = os.path.getsize(os.path.join(path, f))
            lines.append(f"📄 {f} ({_fmt_size(size)})")
        if len(items) > 60:
            lines.append(f"\n... và {len(items)-60} mục nữa")
        send(chat_id, "\n".join(lines))
    except Exception as e:
        send(chat_id, f"❌ Lỗi: {e}")

def cmd_sendfile(chat_id, path):
    path = path.strip()
    if not path:
        send(chat_id, "⚠️ Dùng: /sendfile C:\\path\\to\\file.txt"); return
    if not os.path.exists(path):
        send(chat_id, f"❌ Không tìm thấy: {path}"); return
    size = os.path.getsize(path)
    if size > 50 * 1024 * 1024:
        send(chat_id, f"❌ File quá lớn ({_fmt_size(size)}), giới hạn 50MB"); return
    send(chat_id, f"📤 Đang gửi {os.path.basename(path)} ({_fmt_size(size)})...")
    send_file(chat_id, path, os.path.basename(path))

def cmd_run(chat_id, cmd):
    if not cmd:
        send(chat_id, "⚠️ Dùng: /run notepad  hoặc  /run ipconfig"); return
    send(chat_id, f"▶️ Đang chạy: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True,
                                text=True, timeout=15, encoding="utf-8", errors="ignore")
        out = (result.stdout + result.stderr).strip()
        send(chat_id, out[:4000] if out else "✅ Lệnh đã chạy (không có output)")
    except subprocess.TimeoutExpired:
        send(chat_id, "✅ Chương trình đã mở (chạy nền)")
    except Exception as e:
        send(chat_id, f"❌ Lỗi: {e}")

def cmd_fetchcodes(chat_id):
    ls = get_livestream_info()
    if ls:
        if ls["stream_passed"] and ls["days_to_patch"] > 0:
            ls_line = (f"📺 Special Program {ls['version']} đã diễn ra "
                       f"({ls['stream_date'].strftime('%d/%m')}), "
                       f"patch sau {ls['days_to_patch']} ngày ({ls['patch_date'].strftime('%d/%m')})")
        elif ls["days_to_stream"] == 0:
            ls_line = f"🔴 LIVE NGAY HÔM NAY! Special Program {ls['version']} — check Twitch/YouTube!"
        else:
            days_str = "ngày mai" if ls["days_to_stream"] == 1 else f"{ls['days_to_stream']} ngày nữa"
            ls_line = (f"📺 Special Program {ls['version']} còn {days_str} "
                       f"({ls['stream_date'].strftime('%d/%m/%Y')}) → có ~3 code 🎁")
        send(chat_id, ls_line)

    send(chat_id, "🔍 Đang tìm code từ 5 nguồn...")
    result = fetch_codes_from_web()
    codes  = result["active"]
    sc     = result["source_count"]
    if not codes:
        send(chat_id, "❌ Không tìm thấy code nào\n💡 Code livestream chỉ xuất hiện sau khi stream kết thúc")
        return

    preview = ["🎯 Code tìm được:"]
    for c in codes[:15]:
        preview.append(f"  {c}  ({'⭐'*sc.get(c,1)}) ({sc.get(c,1)} nguồn)")
    if len(codes) > 15:
        preview.append(f"  ... và {len(codes)-15} code nữa")
    send(chat_id, "\n".join(preview))

    cookies, err = load_cookie()
    if not cookies:
        send(chat_id, err); return
    info = get_account_info(cookies)
    if not info:
        send(chat_id, "❌ Không lấy được UID"); return
    uid, nickname, _ = info

    send(chat_id, f"⏳ Đang redeem {len(codes)} code cho {nickname}...")
    ok_list, skip_list, fail_list = [], [], []
    for code in codes:
        ok, msg = redeem_one(cookies, uid, code)
        if ok:
            ok_list.append(code)
        else:
            msg_l = msg.lower()
            if any(w in msg_l for w in ("used", "invalid", "expired", "already",
                                        "does not exist", "redeemed", "unavailable",
                                        "quá hạn", "đã dùng", "vượt quá hạn mức")):
                skip_list.append(code)
            else:
                fail_list.append(f"{code}: {msg}")
        time.sleep(2)

    lines = [f"🏁 Kết quả — {nickname}"]
    if ok_list:   lines.append("✅ Đổi thành công:\n" + "\n".join(f"  🎁 {c}" for c in ok_list))
    if fail_list: lines.append("❌ Lỗi:\n" + "\n".join(f"  • {c}" for c in fail_list))
    if not ok_list:
        lines.append(f"ℹ️ {len(skip_list)} code đã dùng/hết hạn" if skip_list else "ℹ️ Không có code mới nào")
    send(chat_id, "\n".join(lines))

def cmd_login(chat_id):
    login_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login.py")
    if not os.path.exists(login_script):
        send(chat_id, "❌ Không tìm thấy login.py — đặt cùng thư mục với bot.py")
        return
    old_proc = _LOGIN_PROCS.pop(chat_id, None)
    if old_proc:
        try: old_proc.kill()
        except: pass
    send(chat_id, "🌐 Đang mở trình duyệt...\n⏳ Chờ 10-20 giây để browser khởi động.")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-u", login_script],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=0,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        _LOGIN_PROCS[chat_id] = proc
        ready_event = threading.Event()
        def _reader():
            for raw in proc.stdout:
                line = raw.rstrip()
                print(f"[login.py] {line}")
                if any(kw in line for kw in ("nhan Enter", "nhấn Enter", "press Enter",
                                              "San sang", "Sau khi dang nhap")):
                    ready_event.set()
        threading.Thread(target=_reader, daemon=True).start()
        got_ready = ready_event.wait(timeout=60)
        if proc.poll() is not None:
            _LOGIN_PROCS.pop(chat_id, None)
            send(chat_id, "❌ login.py thoát sớm — kiểm tra playwright:\n"
                          "pip install playwright\n"
                          "python -m playwright install chromium")
            return
        if got_ready:
            send(chat_id, "✅ Trình duyệt đã mở!\n"
                          "👆 Click ô Username → tự điền\n"
                          "👆 Click ô Password → tự điền\n"
                          "🔐 Giải Captcha → nhấn Log In\n\n"
                          "📱 Sau khi đăng nhập xong → gửi /logindone")
        else:
            send(chat_id, "✅ Browser đang chạy!\n"
                          "👆 Nếu cửa sổ đã mở: click Username → tự điền\n"
                          "🔐 Giải Captcha → nhấn Log In\n\n"
                          "📱 Sau khi đăng nhập xong → gửi /logindone\n"
                          "❌ Nếu không thấy cửa sổ → gửi /login lại")
    except Exception as e:
        _LOGIN_PROCS.pop(chat_id, None)
        send(chat_id, f"❌ Lỗi: {e}")

def cmd_logindone(chat_id):
    proc = _LOGIN_PROCS.pop(chat_id, None)
    if proc is None:
        send(chat_id, "⚠️ Không có phiên login nào đang mở. Dùng /login trước."); return
    if proc.poll() is not None:
        send(chat_id, "⚠️ Tiến trình login đã kết thúc. Dùng /login lại."); return
    try:
        send(chat_id, "💾 Đang lưu cookie...")
        proc.stdin.write("\n")
        proc.stdin.flush()
        proc.wait(timeout=15)
    except Exception as e:
        send(chat_id, f"⚠️ Lưu cookie lỗi: {e}"); return
    cookies, err = load_cookie()
    if cookies:
        info = get_account_info(cookies)
        if info:
            uid, nickname, region = info
            send(chat_id, f"✅ Đăng nhập thành công!\n👤 {nickname}\n🆔 {uid} | {region}")
        else:
            send(chat_id, "✅ Cookie đã lưu. Thử /status để kiểm tra.")
    else:
        send(chat_id, f"⚠️ {err}")

def cmd_help(chat_id):
    send(chat_id, (
        "📋 DANH SÁCH LỆNH\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎮 GENSHIN\n"
        "/status        — trạng thái bot + cookie\n"
        "/uid           — UID và nickname\n"
        "/checkin       — điểm danh ngay\n"
        "/characters    — danh sách nhân vật\n"
        "/resin         — nhựa + expedition + daily\n"
        "/redeem ABC    — đổi 1 gift code\n"
        "/redeemall     — đổi toàn bộ codes.txt\n"
        "/fetchcodes    — tìm code mới + redeem luôn\n"
        "\n💻 MÁY TÍNH\n"
        "/screenshot    — chụp màn hình\n"
        "/ls [path]     — xem danh sách file\n"
        "/sendfile path — gửi file lên đây\n"
        "/run cmd       — chạy lệnh/chương trình\n"
        "\n⚡ NGUỒN ĐIỆN\n"
        "/shutdown      — tắt máy (sau 10 giây)\n"
        "/restart       — restart máy (sau 10 giây)\n"
        "/cancel        — huỷ lệnh tắt/restart\n"
        "\n🔐 KHÁC\n"
        "/login         — mở trình duyệt đăng nhập\n"
        "/logindone     — lưu cookie sau khi đăng nhập xong\n"
        "/help          — danh sách này"
    ))

# ─────────────────────────────────────────
# TẮT MÁY / KHỞI ĐỘNG LẠI
# ─────────────────────────────────────────
def cmd_shutdown(chat_id):
    send(chat_id, "⚠️ Đang tắt máy trong 10 giây...\nGửi /cancel để huỷ.")
    import platform
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["shutdown", "/s", "/t", "10"])
        else:
            subprocess.Popen(["shutdown", "-h", "+0"])
    except Exception as e:
        send(chat_id, f"❌ Lỗi: {e}")

def cmd_restart(chat_id):
    send(chat_id, "🔄 Đang restart trong 10 giây...\nGửi /cancel để huỷ.")
    import platform
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["shutdown", "/r", "/t", "10"])
        else:
            subprocess.Popen(["shutdown", "-r", "+0"])
    except Exception as e:
        send(chat_id, f"❌ Lỗi: {e}")

def cmd_cancel_shutdown(chat_id):
    import platform
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["shutdown", "/a"])
        else:
            subprocess.Popen(["shutdown", "-c"])
        send(chat_id, "✅ Đã huỷ lệnh tắt/restart máy.")
    except Exception as e:
        send(chat_id, f"❌ Lỗi: {e}")

# ─────────────────────────────────────────
# AUTO CHECKIN BACKGROUND THREAD
# ─────────────────────────────────────────
def auto_checkin_loop():
    print("⏰ Auto check-in thread đang chạy...")
    while True:
        now    = datetime.datetime.now()
        target = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        print(f"⏰ Auto check-in sẽ chạy lúc {target.strftime('%H:%M %d/%m')}")
        time.sleep((target - now).total_seconds())
        cookies, err = load_cookie()
        if not cookies:
            send(TELEGRAM_CHAT_ID, f"⚠️ Auto check-in thất bại: {err}"); continue
        try:
            hdrs = load_headers()
            r    = requests.get(INFO_API, params={"act_id": ACT_ID}, headers=hdrs, timeout=15)
            if r.json().get("data", {}).get("is_sign"):
                continue
            r = requests.post(SIGN_API, json={"act_id": ACT_ID}, headers=hdrs, timeout=15)
            if r.json().get("retcode") == 0:
                send(TELEGRAM_CHAT_ID, "🌅 Auto check-in: ✅ Điểm danh thành công!")
            else:
                send(TELEGRAM_CHAT_ID, f"🌅 Auto check-in: ❌ {r.json().get('message')}")
        except Exception as e:
            send(TELEGRAM_CHAT_ID, f"🌅 Auto check-in lỗi: {e}")

# ─────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────
def handle(chat_id, text):
    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        send(chat_id, "⛔ Không có quyền dùng bot này."); return
    text  = text.strip()
    parts = text.split(maxsplit=1)
    cmd   = parts[0].lower().split("@")[0]
    arg   = parts[1].strip() if len(parts) > 1 else ""
    dispatch = {
        "/status":     (cmd_status,          ()),
        "/uid":        (cmd_uid,             ()),
        "/checkin":    (cmd_checkin,         ()),
        "/characters": (cmd_characters,      ()),
        "/resin":      (cmd_resin,           ()),
        "/redeem":     (cmd_redeem,          (arg.upper(),)),
        "/redeemall":  (cmd_redeemall,       ()),
        "/fetchcodes": (cmd_fetchcodes,      ()),
        "/screenshot": (cmd_screenshot,      ()),
        "/ls":         (cmd_ls,              (arg,)),
        "/sendfile":   (cmd_sendfile,        (arg,)),
        "/run":        (cmd_run,             (arg,)),
        "/shutdown":   (cmd_shutdown,        ()),
        "/restart":    (cmd_restart,         ()),
        "/cancel":     (cmd_cancel_shutdown, ()),
        "/login":      (cmd_login,           ()),
        "/logindone":  (cmd_logindone,       ()),
        "/help":       (cmd_help,            ()),
        "/start":      (cmd_help,            ()),
    }
    if cmd in dispatch:
        fn, args = dispatch[cmd]
        threading.Thread(target=fn, args=(chat_id, *args), daemon=True).start()
    else:
        send(chat_id, "❓ Lệnh không nhận ra. Gõ /help")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print(f"🤖 Bot đang chạy trên {socket.gethostname()}...")
    print(f"   Chat ID được phép: {TELEGRAM_CHAT_ID}")
    print("   Gõ Ctrl+C để dừng.\n")
    threading.Thread(target=auto_checkin_loop, daemon=True).start()
    send(TELEGRAM_CHAT_ID,
         f"🤖 Bot đã khởi động!\n"
         f"🖥 {socket.gethostname()}\n"
         f"🕐 {datetime.datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
         "Gõ /help để xem lệnh.")
    offset = None
    while True:
        updates = get_updates(offset)
        for upd in updates:
            offset  = upd["update_id"] + 1
            msg     = upd.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text    = msg.get("text", "")
            if chat_id and text.startswith("/"):
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {chat_id}: {text}")
                handle(chat_id, text)

if __name__ == "__main__":
    main()