# -*- coding: utf-8 -*-
"""
bot.py — Telegram Bot HoYoLAB / Genshin Impact
Chạy tốt trên: Windows 11 + Linux (Arch / Ubuntu / systemd)
Thiết kế thread:
  - auto_checkin_loop     → ngủ đúng đến 09:00 / 21:00, không poll
  - resin_monitor_loop    → tính chính xác bao lâu đến ngưỡng, ngủ đúng đó
  - auto_fetchcodes_loop    → ngủ đến sau giờ live, tự fetch + redeem code
  Tất cả đều KHÔNG chạy ngầm liên tục.
"""
import hashlib, json, random, requests, datetime, time
import os, re, socket, string, sys, threading, subprocess, logging, tempfile
from config import HOYOLAB_FILE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import lang
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging.handlers import RotatingFileHandler
# ─────────────────────────────────────────
# LOGGING — ghi ra cả console lẫn bot.log
# ─────────────────────────────────────────
_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        RotatingFileHandler(_LOG_FILE, encoding="utf-8", maxBytes=2*1024*1024, backupCount=3),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("botDailyGI")
# Patch print() → cũng ghi vào log file (giữ nguyên print trong code cũ)
_orig_print = print
def print(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    log.info(msg)
    # Không gọi _orig_print nữa vì StreamHandler đã lo console
# ─────────────────────────────────────────
# PLATFORM / TIMEZONE / UPTIME
# ─────────────────────────────────────────
IS_WINDOWS = sys.platform == "win32"
VN_TZ      = datetime.timezone(datetime.timedelta(hours=7))
_BOT_START = time.monotonic()
def now_vn() -> datetime.datetime:
    return datetime.datetime.now(VN_TZ)
def today_vn() -> datetime.date:
    return now_vn().date()
def uptime_str() -> str:
    s = int(time.monotonic() - _BOT_START)
    h, r = divmod(s, 3600); m, s = divmod(r, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else (f"{m}m{s:02d}s" if m else f"{s}s")
# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CODES_FILE            = os.path.join(_BASE_DIR, "codes.txt")
CODES_BLACKLIST_FILE  = os.path.join(_BASE_DIR, "codes_blacklist.txt")
RESIN_NOTIFY_FILE     = os.path.join(_BASE_DIR, "resin_notify.json")
LIVE_DETECT_FILE      = os.path.join(_BASE_DIR, "live_detect.json")
ACT_ID   = "e202102251931481"
INFO_API = "https://sg-hk4e-api.hoyolab.com/event/sol/info"
SIGN_API = "https://sg-hk4e-api.hoyolab.com/event/sol/sign"
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
_SALT_OS = "6cqshh5dhw73bzxn20oexa9k516chk7s"
# Stream schedule — dùng chung ở auto_fetchcodes_loop và cmd_status
STREAM_HOUR   = int(os.getenv("STREAM_HOUR", "11") or 11)
STREAM_MINUTE = int(os.getenv("STREAM_MINUTE", "0") or 0)
WAIT_AFTER    = int(os.getenv("FETCH_WAIT_AFTER_MIN", "210") or 210)
_LOGIN_PROCS: dict     = {}  # chat_id → subprocess.Popen
_LOGIN_SESSIONS: dict  = {}  # chat_id → int tăng dần, invalidate _reader cũ khi /login lại
_redeem_lock           = threading.Lock()   # guard API redeem — tránh song song
_fetchcodes_lock       = threading.Lock()   # guard TOÀN BỘ cmd_fetchcodes (scrape+redeem)
_checkin_lock          = threading.Lock()   # guard cmd_checkin thủ công
# User-Agent theo nền tảng (dùng nhất quán mọi nơi)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    if IS_WINDOWS else
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_retry = Retry(total=3, backoff_factor=0.2,
               status_forcelist=(429,500,502,503,504),
               allowed_methods=["GET","POST"])
_adapter = HTTPAdapter(pool_connections=32, pool_maxsize=32, max_retries=_retry)
_HTTP = requests.Session()
_HTTP.headers.update({"User-Agent": _UA})
_HTTP.mount("https://", _adapter)
_HTTP.mount("http://", _adapter)
_MAX_WORKERS = int(os.getenv("BOT_MAX_WORKERS", "8") or 8)
_CMD_EXEC = ThreadPoolExecutor(max_workers=_MAX_WORKERS)
# ─────────────────────────────────────────
# DS / COOKIE HELPERS
# ─────────────────────────────────────────
def _make_ds(body: str = "", query: str = "") -> str:
    t = int(time.time())
    r = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    h = hashlib.md5(f"salt={_SALT_OS}&t={t}&r={r}&b={body}&q={query}".encode()).hexdigest()
    return f"{t},{r},{h}"
def _cookie_str(cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())
def _safe_json(resp) -> dict:
    try:   return resp.json()
    except Exception:
        return {"retcode": -1, "message": f"Invalid JSON (HTTP {resp.status_code})"}
def _base_headers(cookie_str: str) -> dict:
    return {
        "User-Agent":        _UA,
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
def _send(chat_id, text: str):
    try:
        s = text if isinstance(text, str) else str(text)
        MAX_LEN = 4000
        while s:
            if len(s) <= MAX_LEN:
                _HTTP.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": s}, timeout=10)
                break
            # Tìm điểm cắt hợp lý (xuống dòng hoặc khoảng trắng)
            cut_at = s.rfind("\n", 0, MAX_LEN)
            if cut_at == -1: cut_at = s.rfind(" ", 0, MAX_LEN)
            if cut_at == -1: cut_at = MAX_LEN
            chunk = s[:cut_at]
            _HTTP.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": chunk}, timeout=10)
            s = s[cut_at:].lstrip()  # Bỏ khoảng trắng thừa đầu dòng tiếp theo
    except Exception as e:
        log.warning(f"[send] Lỗi gửi Telegram (chat={chat_id}): {e}")
def _send_with_buttons(chat_id, text: str, buttons: list):
    """Gửi tin nhắn kèm inline keyboard.
    buttons: [[{"text":"✅ Xác nhận","callback_data":"yes_shutdown"}], ...]
    """
    try:
        _HTTP.post(f"{BASE_URL}/sendMessage",
                   json={
                       "chat_id": chat_id,
                       "text": text,
                       "reply_markup": {"inline_keyboard": buttons},
                   },
                   timeout=10)
    except Exception as e:
        log.warning(f"[send_with_buttons] Lỗi gửi inline keyboard (chat={chat_id}): {e}")
def _answer_callback(callback_id: str, text: str = ""):
    """Trả lời callback_query để Telegram tắt loading spinner."""
    try:
        _HTTP.post(f"{BASE_URL}/answerCallbackQuery",
                   json={"callback_query_id": callback_id, "text": text},
                   timeout=5)
    except Exception as e:
        log.warning(f"[_answer_callback] Lỗi trả lời callback {callback_id}: {e}")

def send(chat_id, text: str):
    return lang.t_send(chat_id, text, _send)

def send_with_buttons(chat_id, text: str, buttons: list):
    return lang.t_send_with_buttons(chat_id, text, buttons, _send_with_buttons)

def answer_callback(callback_id: str, text: str = "", chat_id=None):
    return lang.t_answer_callback(callback_id, text, _answer_callback, chat_id)
def send_photo(chat_id, photo_path, caption=""):
    try:
        with open(photo_path, "rb") as f:
            _HTTP.post(f"{BASE_URL}/sendPhoto",
                       data={"chat_id": chat_id, "caption": caption},
                       files={"photo": f}, timeout=30)
    except Exception as e:
        send(chat_id, f"❌ Lỗi gửi ảnh: {e}")
def send_file(chat_id, file_path, caption=""):
    try:
        with open(file_path, "rb") as f:
            _HTTP.post(f"{BASE_URL}/sendDocument",
                       data={"chat_id": chat_id, "caption": caption},
                       files={"document": f}, timeout=60)
    except Exception as e:
        send(chat_id, f"❌ Lỗi gửi file: {e}")
def get_updates(offset=None):
    params = {"timeout": 30, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:   # offset=0 hợp lệ, chỉ bỏ khi thực sự None
        params["offset"] = offset
    try:
        r = _HTTP.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
        return r.json().get("result", [])
    except Exception:
        return []
# ─────────────────────────────────────────
# COOKIE / ACCOUNT
# ─────────────────────────────────────────
_cookie_cache: dict      = {}   # name → value
_cookie_cache_mtime: float = 0.0
def _read_hoyolab_file() -> dict:
    """Đọc hoyolab.json với cache theo mtime — tránh đọc file nhiều lần."""
    global _cookie_cache, _cookie_cache_mtime
    try:
        mtime = os.path.getmtime(HOYOLAB_FILE)
    except OSError:
        return {}
    if mtime == _cookie_cache_mtime and _cookie_cache:
        return _cookie_cache
    try:
        with open(HOYOLAB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cookie_cache = {
            c["name"]: c["value"]
            for c in data.get("cookies", [])
            if c.get("name") and c.get("value")
        }
        _cookie_cache_mtime = mtime
        return _cookie_cache
    except Exception:
        return {}
def load_cookie():
    if not os.path.exists(HOYOLAB_FILE):
        return None, "❌ Không tìm thấy hoyolab.json — dùng /login để đăng nhập"
    cookies = _read_hoyolab_file()
    if not cookies:
        return None, "❌ Lỗi đọc hoyolab.json hoặc file rỗng"
    if "ltoken_v2" not in cookies or "ltuid_v2" not in cookies:
        return None, "❌ Cookie thiếu ltoken_v2/ltuid_v2 — dùng /login để đăng nhập lại"
    return cookies, "OK"
def load_headers():
    """Build headers dùng cho check-in. Raise nếu cookie không hợp lệ."""
    cookies, err = load_cookie()
    if not cookies:
        raise RuntimeError(err)
    cs = _cookie_str(cookies)
    return {
        "User-Agent": _UA,
        "Referer":    "https://www.hoyolab.com",
        "Cookie":     cs,
        "Origin":     "https://www.hoyolab.com",
    }
def get_account_info(cookies):
    url = "https://api-os-takumi.hoyoverse.com/binding/api/getUserGameRolesByLtoken"
    try:
        r = _HTTP.get(url,
                      headers={"User-Agent": _UA, "Referer": "https://www.hoyolab.com/"},
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
# Cache account info — TTL 5 phút, dùng chung cho tất cả cmd handlers
_acct_cache:      tuple  = ()    # (uid, nickname, region)
_acct_cache_time: float  = 0.0
_ACCT_CACHE_TTL            = 300  # 5 phút
def get_account_info_cached(cookies):
    """Trả về (uid, nickname, region) từ cache nếu còn mới, ngược lại gọi API."""
    global _acct_cache, _acct_cache_time
    if _acct_cache and (time.time() - _acct_cache_time) < _ACCT_CACHE_TTL:
        return _acct_cache
    info = get_account_info(cookies)   # FIX: gọi hàm gốc, không đệ quy
    if info:
        _acct_cache      = info
        _acct_cache_time = time.time()
    return info
def invalidate_account_cache():
    """Gọi khi cookie thay đổi để buộc refresh."""
    global _acct_cache, _acct_cache_time
    _acct_cache = (); _acct_cache_time = 0.0
def check_cookie_status(cookies):
    url = "https://bbs-api-os.hoyolab.com/community/user/wapi/getUserFullInfo"
    try:
        r = _HTTP.get(url,
                      headers={"User-Agent": _UA, "Referer": "https://www.hoyolab.com"},
                      cookies=cookies, timeout=10)
        j = r.json()
        if j.get("retcode") == 0:
            return f"✅ Hợp lệ — {j['data']['user_info']['nickname']}"
        return f"⚠️ retcode {j.get('retcode')}: {j.get('message')}"
    except Exception as e:
        return f"❌ Lỗi kết nối: {e}"
# ─────────────────────────────────────────
# CHARACTERS
# ─────────────────────────────────────────
def get_characters(cookies, uid, region):
    cs       = _cookie_str(cookies)
    body_str = json.dumps({"role_id": str(uid), "server": region},
                          separators=(",", ":"), sort_keys=True)
    headers  = _base_headers(cs)
    headers["Content-Type"]       = "application/json"
    headers["x-rpc-tool-version"] = "v5.0.0-ys"
    headers["x-rpc-page"]         = "v5.0.0-ys"
    endpoints = [
        "https://bbs-api-os.hoyolab.com/game_record/genshin/api/character/list",
        "https://sg-public-api.hoyolab.com/game_record/genshin/api/character/list",
        "https://bbs-api-os.hoyolab.com/game_record/genshin/api/character",
    ]
    for url in endpoints:
        try:
            headers["DS"] = _make_ds(body=body_str, query="")
            r  = _HTTP.post(url, headers=headers, data=body_str, timeout=15)
            d  = _safe_json(r)
            rc = d.get("retcode", -99)
            print(f"[chars] HTTP {r.status_code} rc={rc} msg={d.get('message','')[:50]}")
            if r.status_code == 200 and rc == 0:            return d
            if r.status_code == 200 and rc not in (-99,-1,0): return d
        except Exception as e:
            print(f"[chars] {url}: {e}")
    return {"retcode": -1, "message": "Không kết nối được API nhân vật"}
# ─────────────────────────────────────────
# REAL-TIME NOTES (Resin)
# ─────────────────────────────────────────
def get_realtime_notes(cookies, uid, region):
    cs        = _cookie_str(cookies)
    query_str = f"role_id={uid}&server={region}"
    headers   = _base_headers(cs)
    headers["x-rpc-tool-version"] = "v5.0.0-ys"
    headers["x-rpc-page"]         = "v5.0.0-ys"
    for base in [
        "https://bbs-api-os.hoyolab.com/game_record/genshin/api/dailyNote",
        "https://sg-public-api.hoyolab.com/game_record/genshin/api/dailyNote",
    ]:
        try:
            headers["DS"] = _make_ds(body="", query=query_str)
            r  = _HTTP.get(f"{base}?{query_str}", headers=headers, timeout=15)
            d  = _safe_json(r)
            rc = d.get("retcode", -99)
            print(f"[resin] HTTP {r.status_code} rc={rc} msg={d.get('message','')[:50]}")
            if r.status_code == 200 and rc == 0:            return d
            if r.status_code == 200 and rc not in (-99,-1,0): return d
        except Exception as e:
            print(f"[resin] {base}: {e}")
    return {"retcode": -1, "message": "Không kết nối được API resin"}
# ─────────────────────────────────────────
# GENSHIN VERSIONS + LIVESTREAM SCHEDULE
# ─────────────────────────────────────────
_VERSIONS_FALLBACK = [
    ("5.5", "2026-03-19"),
    ("5.6", "2026-04-30"),
    ("5.7", "2026-06-11"),
    ("5.8", "2026-07-23"),
    ("5.9", "2026-09-03"),
    # v6.x dự phóng (42 ngày/phiên bản)
    ("6.0", "2026-10-15"),
    ("6.1", "2026-11-26"),
    ("6.2", "2027-01-07"),
    ("6.3", "2027-02-18"),
    ("6.4", "2027-04-01"),
]
_VERSION_CACHE:      list  = []
_VERSION_CACHE_TIME: float = 0.0
_VERSION_CACHE_TTL         = 6 * 3600   # refresh mỗi 6 tiếng
def _vkey(v: str):
    return tuple(int(x) for x in v.split(".") if x.isdigit())
def fetch_versions_from_web() -> list:
    hdrs = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}
    found = {}
    today = today_vn()
    try:
        r = _HTTP.get("https://genshin-impact.fandom.com/wiki/Version",
                         headers=hdrs, timeout=12)
        rows = re.findall(r'(\d\.\d+)\D{1,80}?(\d{4}-\d{2}-\d{2})', r.text)
        for ver, ds in rows:
            try:
                d = datetime.date.fromisoformat(ds)
                if (d - today).days > -365:
                    found.setdefault(ver, ds)
            except ValueError:
                pass
    except Exception as e:
        print(f"[versions] lỗi: {e}")
    return sorted(found.items(), key=lambda x: _vkey(x[0])) if found else []
def get_versions() -> list:
    global _VERSION_CACHE, _VERSION_CACHE_TIME
    if _VERSION_CACHE and (time.time() - _VERSION_CACHE_TIME) < _VERSION_CACHE_TTL:
        return _VERSION_CACHE
    fetched = fetch_versions_from_web()
    if fetched:
        _VERSION_CACHE = fetched
        _VERSION_CACHE_TIME = time.time()
        return _VERSION_CACHE
    return _VERSIONS_FALLBACK
# ─────────────────────────────────────────
# RESIN CONFIG
# ─────────────────────────────────────────
_resin_cfg_cache:      dict  = {}
_resin_cfg_mtime:      float = 0.0
def _load_resin_cfg() -> dict:
    """Load resin_notify.json với mtime cache — tránh parse JSON khi file không đổi."""
    global _resin_cfg_cache, _resin_cfg_mtime
    defaults = {"threshold": 200, "enabled": True, "notified": False, "notified_critical": False}
    if not os.path.exists(RESIN_NOTIFY_FILE):
        return dict(defaults)
    try:
        mtime = os.path.getmtime(RESIN_NOTIFY_FILE)
    except OSError:
        return dict(defaults)
    if _resin_cfg_cache and mtime == _resin_cfg_mtime:
        return dict(_resin_cfg_cache)   # trả bản copy để caller có thể sửa an toàn
    try:
        with open(RESIN_NOTIFY_FILE, "r", encoding="utf-8") as f:
            c = json.load(f)
        merged = dict(defaults)
        merged.update(c)
        _resin_cfg_cache = merged
        _resin_cfg_mtime = mtime
        return dict(merged)
    except Exception:
        return dict(defaults)
def _save_resin_cfg(cfg: dict):
    """Lưu resin_notify.json và invalidate mtime cache ngay."""
    with open(RESIN_NOTIFY_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    # Invalidate cache để lần đọc tiếp theo load từ file mới
    global _resin_cfg_mtime
    _resin_cfg_mtime = 0.0

# ─────────────────────────────────────────
# BLACKLIST
# ─────────────────────────────────────────
_bl_cache:      dict  = {}
_bl_cache_mtime: float = 0.0
def load_blacklist() -> dict:
    """Đọc codes_blacklist.txt → {code: reason} với mtime cache."""
    global _bl_cache, _bl_cache_mtime
    if not os.path.exists(CODES_BLACKLIST_FILE):
        return {}
    try:
        mtime = os.path.getmtime(CODES_BLACKLIST_FILE)
    except OSError:
        return {}
    if _bl_cache and mtime == _bl_cache_mtime:
        return dict(_bl_cache)
    bl = {}
    try:
        with open(CODES_BLACKLIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split("|", 2)
                code   = parts[0].strip()
                reason = parts[1].strip() if len(parts) > 1 else "blacklisted"
                if code:
                    bl[code] = reason
        _bl_cache = bl
        _bl_cache_mtime = mtime
    except Exception:
        pass
    return dict(bl)

def add_to_blacklist(code: str, reason: str, existing_bl: dict = None):
    """Thêm code vào blacklist file và invalidate cache."""
    global _bl_cache_mtime
    ts = now_vn().strftime("%Y-%m-%d %H:%M")
    try:
        with open(CODES_BLACKLIST_FILE, "a", encoding="utf-8") as f:
            f.write(f"{code} | {reason} | {ts}\n")
        _bl_cache_mtime = 0.0   # invalidate
    except Exception as e:
        log.warning(f"[blacklist] Lỗi ghi blacklist: {e}")

def _should_blacklist(msg: str, retcode: int) -> tuple:
    """Trả về (should_blacklist: bool, reason: str)."""
    msg_l = (msg or "").lower()
    if retcode in (-2017, -2018) or "expired" in msg_l or "hết hạn" in msg_l:
        return True, "hết hạn"
    if retcode == -2016 or "used" in msg_l or "redeemed" in msg_l or "đã dùng" in msg_l:
        return True, "đã dùng"
    if retcode in (-2001, -2003, -2004, -2014) or "invalid" in msg_l or "not found" in msg_l or "không hợp lệ" in msg_l:
        return True, "không hợp lệ"
    return False, ""

def load_codes_from_file() -> list:
    """Đọc codes.txt, bỏ comment và dòng trống, trả list code chưa blacklist."""
    if not os.path.exists(CODES_FILE):
        return []
    bl = load_blacklist()
    codes = []
    try:
        with open(CODES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                code = s.upper()
                if code not in bl:
                    codes.append(code)
    except Exception:
        pass
    return codes

# ─────────────────────────────────────────
# REDEEM CODE
# ─────────────────────────────────────────
def redeem_one(cookies, uid, region, code: str) -> tuple:
    """Đổi 1 gift code. Trả về (ok: bool, message: str, retcode: int)."""
    cs  = _cookie_str(cookies)
    url = "https://sg-hk4e-api.hoyoverse.com/common/apicdkey/api/webExchangeCdkeyHyl"
    params = {
        "uid":      str(uid),
        "region":   region,
        "game_biz": "hk4e_global",
        "lang":     "vi-vn",
        "cdkey":    code,
    }
    headers = _base_headers(cs)
    try:
        r  = _HTTP.get(url, headers=headers, params=params, timeout=15)
        d  = _safe_json(r)
        rc = d.get("retcode", -1)
        msg = d.get("message", "unknown")
        return (rc == 0), msg, rc
    except Exception as e:
        return False, str(e), -1

def _do_redeem_codes(chat_id, codes: list, cookies, uid, region, nickname, label=""):
    """Redeem danh sách codes, gửi báo cáo, cập nhật blacklist."""
    bl = load_blacklist()
    new_codes = [c for c in codes if c not in bl]
    already_bl = [c for c in codes if c in bl]

    if not new_codes:
        msg = f"⚠️ Toàn bộ {len(codes)} code đã trong blacklist."
        if chat_id: send(chat_id, msg)
        else: send(TELEGRAM_CHAT_ID, msg)
        return

    target = chat_id or TELEGRAM_CHAT_ID
    prefix = f"[{label}] " if label else ""
    send(target, f"⏳ {prefix}Đang đổi {len(new_codes)} code cho {nickname} ({uid})...")

    results = {"ok": [], "fail_bl": [], "fail_other": []}
    for code in new_codes:
        time.sleep(random.uniform(0.8, 1.5))  # tránh rate limit
        ok, msg, rc = redeem_one(cookies, uid, region, code)
        if ok:
            results["ok"].append(code)
        else:
            should_bl, reason = _should_blacklist(msg, rc)
            if should_bl:
                add_to_blacklist(code, reason)
                results["fail_bl"].append((code, reason, msg))
            else:
                results["fail_other"].append((code, msg))

    lines = [f"📊 {prefix}Kết quả redeem — {nickname}"]
    if results["ok"]:
        lines.append(f"✅ Thành công ({len(results['ok'])}): {', '.join(results['ok'])}")
    if results["fail_bl"]:
        lines.append(f"🚫 Blacklist ({len(results['fail_bl'])}):")
        for code, reason, msg in results["fail_bl"]:
            lines.append(f"  • {code} — {reason}: {msg[:60]}")
    if results["fail_other"]:
        lines.append(f"⚠️ Lỗi khác ({len(results['fail_other'])}):")
        for code, msg in results["fail_other"]:
            lines.append(f"  • {code} — {msg[:60]}")
    if already_bl:
        lines.append(f"⏭️ Đã bỏ qua {len(already_bl)} code (đã blacklist)")
    send(target, "\n".join(lines))

# ─────────────────────────────────────────
# FETCH CODES FROM WEB
# ─────────────────────────────────────────
_CODE_PAT = re.compile(r"\b([A-Z0-9]{8,20})\b")
_SOURCES = [
    ("reddit_genshin",   "https://www.reddit.com/r/Genshin_Impact/search.json?q=gift+code&sort=new&limit=10&t=week"),
    ("genshinlab",       "https://genshinlab.com/promo-codes/"),
    ("pockettactics",    "https://www.pockettactics.com/genshin-impact/codes"),
    ("gamesradar",       "https://www.gamesradar.com/genshin-impact-codes-redeem/"),
    ("progameguides",    "https://progameguides.com/genshin-impact/genshin-impact-codes/"),
]
_KNOWN_WORDS = {
    "GENSHIN","IMPACT","PRIMOGEMS","REDEEM","CODES","WELCOME","JANUARY","FEBRUARY",
    "MARCH","APRIL","MAY","JUNE","JULY","AUGUST","SEPTEMBER","OCTOBER","NOVEMBER",
    "DECEMBER","HOYOLAB","ANNIVERSARY","SPECIAL","PROGRAM","STREAM","LIVESTREAM",
    "COMMUNITY","MANGA","UPDATE","VERSION","PATCH","LOGIN","GUIDE","TWITTER","FACEBOOK",
    "INSTAGRAM","YOUTUBE","DISCORD","REDDIT","LIKE","SHARE","CODE","GIFT","REDEEM",
    "PRIMOGEM","MORA","CROWN","BOOK","ORE","RESIN","FRAGILE","FRAGILE",
}

def _is_likely_code(s: str) -> bool:
    if len(s) < 8 or len(s) > 20: return False
    if s in _KNOWN_WORDS: return False
    # Phải có ít nhất 1 chữ số và 1 chữ cái
    if not any(c.isdigit() for c in s): return False
    if not any(c.isalpha() for c in s): return False
    return True

def fetch_codes_from_web() -> dict:
    """Fetch active Genshin codes từ nhiều nguồn.
    Trả về {"active": [code,...], "source_count": {code: n}, "live_codes": set()}"""
    bl = load_blacklist()
    source_count: dict = {}
    live_codes: set = set()

    hdrs = {"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"}

    def _fetch_one(name, url):
        try:
            r = _HTTP.get(url, headers=hdrs, timeout=12)
            if r.status_code != 200: return []
            text = r.text.upper()
            found = []
            if "reddit" in url:
                try:
                    j = r.json()
                    posts = j.get("data",{}).get("children",[])
                    for p in posts:
                        t = (p.get("data",{}).get("title","") + " " +
                             p.get("data",{}).get("selftext","")).upper()
                        for m in _CODE_PAT.findall(t):
                            if _is_likely_code(m): found.append(m)
                except Exception:
                    pass
            else:
                for m in _CODE_PAT.findall(text):
                    if _is_likely_code(m): found.append(m)
            return list(set(found))
        except Exception as e:
            print(f"[fetch] {name}: {e}")
            return []

    # Fetch parallel
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_fetch_one, name, url): name for name, url in _SOURCES}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                codes_found = fut.result()
                for c in codes_found:
                    if c not in bl:
                        source_count[c] = source_count.get(c, 0) + 1
                        if "reddit" in name or "hoyolab" in name:
                            live_codes.add(c)
            except Exception:
                pass

    # Sắp xếp theo số nguồn xác nhận (nhiều nhất lên đầu)
    active = sorted(source_count.keys(), key=lambda c: source_count[c], reverse=True)
    return {"active": active, "source_count": source_count, "live_codes": live_codes}

# ─────────────────────────────────────────
# COMMANDS — /status /uid /checkin
# ─────────────────────────────────────────
def cmd_status(chat_id):
    lines = [
        f"🤖 BOT STATUS",
        f"🖥  {socket.gethostname()}  ({'Win' if IS_WINDOWS else 'Linux'})",
        f"🕐  {now_vn().strftime('%H:%M:%S  %d/%m/%Y')}",
        f"⏱  Uptime: {uptime_str()}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    # Hiển thị nếu đang có phiên login đang chờ
    if chat_id in _LOGIN_PROCS:
        proc = _LOGIN_PROCS[chat_id]
        if proc.poll() is None:
            lines.append("🔐 Đang có phiên đăng nhập → /logincancel để huỷ")
        else:
            _LOGIN_PROCS.pop(chat_id, None)   # dọn dẹp proc chết

    cookies, _ = load_cookie()
    if cookies:
        info = get_account_info_cached(cookies)
        if info:
            uid, nickname, region = info
            lines.append(f"👤 {nickname}  🆔 {uid}  🌏 {region}")
            cs = check_cookie_status(cookies)
            lines.append(f"🔑 Cookie: {cs}")
            # Resin
            data = get_realtime_notes(cookies, uid, region)
            if data.get("retcode") == 0:
                d = data["data"]
                r_cur = d.get("current_resin", 0)
                r_max = d.get("max_resin", 200)
                eta_sec = int(d.get("resin_recovery_time", "0"))
                fill = int(r_cur / r_max * 10)
                bar  = "█" * fill + "░" * (10 - fill)
                eta_s = " — đầy ✅" if eta_sec <= 0 else f" — đầy {(now_vn() + datetime.timedelta(seconds=eta_sec)).strftime('%H:%M %d/%m')}"
                lines.append(f"⚗️ Nhựa: [{bar}] {r_cur}/{r_max}{eta_s}")
            # Check-in
            try:
                hdrs_ci = load_headers()
                ri = _HTTP.get(INFO_API, params={"act_id": ACT_ID}, headers=hdrs_ci, timeout=8)
                d2 = ri.json().get("data", {})
                lines.append(f"📅 Điểm danh: {'✅ Đã điểm' if d2.get('is_sign') else '❌ Chưa điểm'} ({d2.get('total_sign_day','?')} ngày)")
            except Exception:
                pass
    else:
        lines.append("⚠️ Chưa đăng nhập — dùng /login")
    # Lịch livestream tiếp
    try:
        now = now_vn()
        for ver, ps in get_versions():
            pd = datetime.date.fromisoformat(ps)
            sd = pd - datetime.timedelta(days=7)
            st = datetime.datetime(sd.year, sd.month, sd.day, STREAM_HOUR, STREAM_MINUTE, tzinfo=VN_TZ)
            if st > now:
                days_left = (st.date() - now.date()).days
                lines.append(f"🎮 Live v{ver}: {st.strftime('%H:%M  %d/%m/%Y')} (còn {days_left} ngày)")
                break
    except Exception:
        pass
    send(chat_id, "\n".join(lines))

def cmd_uid(chat_id):
    cookies, err = load_cookie()
    if not cookies: send(chat_id, err); return
    info = get_account_info_cached(cookies)
    if not info: send(chat_id, "❌ Không lấy được UID\n💡 Thử /login nếu cookie hết hạn"); return
    uid, nickname, region = info
    send(chat_id, f"👤 Nickname : {nickname}\n🆔 UID      : {uid}\n🌏 Server   : {region}")

def cmd_checkin(chat_id):
    if not _checkin_lock.acquire(blocking=False):
        send(chat_id, "⏳ Đang có lệnh /checkin đang chạy rồi.\n💡 Chờ xíu nhé!"); return
    try:
        hdrs = load_headers()
        r    = _HTTP.get(INFO_API, params={"act_id": ACT_ID}, headers=hdrs, timeout=15)
        d    = r.json().get("data", {})
        if d.get("is_sign") is True:
            total = d.get("total_sign_day", "?")
            send(chat_id, f"ℹ️ Hôm nay đã điểm danh rồi! (Tích lũy: {total} ngày)"); return
        r = _HTTP.post(SIGN_API, json={"act_id": ACT_ID}, headers=hdrs, timeout=15)
        result = r.json()
        if result.get("retcode") == 0:
            send(chat_id, "✅ Điểm danh thành công!")
        else:
            send(chat_id, f"❌ Điểm danh thất bại: {result.get('message')}")
    except RuntimeError as e:
        send(chat_id, f"❌ Cookie không hợp lệ: {e}")
    except Exception as e:
        send(chat_id, f"❌ Lỗi: {e}")
    finally:
        _checkin_lock.release()

# ── /redeem ──────────────────────────────
def cmd_redeem(chat_id, code):
    if not code: send(chat_id, "⚠️ Dùng: /redeem ABCD1234"); return
    bl = load_blacklist()
    if code in bl:
        send(chat_id, f"⛔ [{code}] Đã blacklist ({bl[code]})\n💡 /clearblacklist để xóa"); return
    cookies, err = load_cookie()
    if not cookies: send(chat_id, err); return
    info = get_account_info_cached(cookies)
    if not info: send(chat_id, "❌ Không lấy được UID"); return
    uid, nickname, region = info
    if not _redeem_lock.acquire(blocking=False):
        send(chat_id, "⏳ Đang có lệnh redeem đang chạy rồi.\n💡 Chờ nó xong nhé!"); return
    try:
        send(chat_id, f"⏳ Đang đổi [{code}]...")
        ok, msg, retcode = redeem_one(cookies, uid, region, code)
        if ok:
            send(chat_id, f"✅ [{code}] Đổi thành công!")
        else:
            should_bl, reason = _should_blacklist(msg, retcode)
            if should_bl:
                add_to_blacklist(code, reason, existing_bl=bl)  # dùng lại bl đã load
                send(chat_id, f"❌ [{code}] Thất bại: {msg}\n🚫 Đã thêm vào blacklist ({reason})")
            else:
                send(chat_id, f"❌ [{code}] Thất bại: {msg}")
    finally:
        _redeem_lock.release()
# ── /redeemall ───────────────────────────
def cmd_redeemall(chat_id):
    if not _redeem_lock.acquire(blocking=False):
        send(chat_id, "⏳ Đang có lệnh redeem đang chạy rồi.\n💡 Chờ nó xong, đừng gọi lại!"); return
    try:
        codes = load_codes_from_file()
        if not codes: send(chat_id, f"⚠️ Không có code nào trong {CODES_FILE}"); return
        cookies, err = load_cookie()
        if not cookies: send(chat_id, err); return
        info = get_account_info_cached(cookies)
        if not info: send(chat_id, "❌ Không lấy được UID"); return
        uid, nickname, region = info
        _do_redeem_codes(chat_id, codes, cookies, uid, region, nickname)
    finally:
        _redeem_lock.release()
# ── /characters ──────────────────────────
def cmd_characters(chat_id):
    cookies, err = load_cookie()
    if not cookies: send(chat_id, err); return
    info = get_account_info_cached(cookies)
    if not info: send(chat_id, "❌ Không lấy được UID"); return
    uid, nickname, region = info
    data    = get_characters(cookies, uid, region)
    retcode = data.get("retcode", -1)
    if retcode != 0:
        msg  = data.get("message", "unknown")
        hint = {
            10001: "\n💡 Cookie hết hạn → /login",
            -100:  "\n💡 Cookie hết hạn → /login",
            10307: "\n💡 HoYoLAB → Cài đặt → Hồ sơ game → bật 'Hiển thị chi tiết nhân vật'",
            10102: "\n💡 HoYoLAB → Cài đặt → Hồ sơ game → chuyển sang công khai",
            1034:  "\n💡 Bị xác minh — mở HoYoLAB và xác nhận captcha",
        }.get(retcode, "\n💡 HoYoLAB → Cài đặt → bật tất cả toggle hồ sơ game")
        send(chat_id, f"❌ Lỗi ({retcode}): {msg}{hint}"); return
    chars = data.get("data", {}).get("list", [])
    if not chars:
        send(chat_id, "❌ Không có nhân vật\n💡 Bật 'Hiển thị chi tiết nhân vật' trong HoYoLAB"); return
    chars.sort(key=lambda x: (x.get("rarity",0), x.get("level",0)), reverse=True)
    # API trả về field "element" dạng string theo tên Genshin: Pyro, Hydro, Anemo, Electro, Dendro, Cryo, Geo
    elem_map = {
        "Pyro":    ("🔥", "Hỏa"),
        "Hydro":   ("💧", "Thủy"),
        "Anemo":   ("🌬️", "Phong"),
        "Electro": ("⚡", "Lôi"),
        "Dendro":  ("🌿", "Thảo"),
        "Cryo":    ("❄️", "Băng"),
        "Geo":     ("🪨", "Nham"),
    }
    five_star = [c for c in chars if c.get("rarity",0)==5]
    four_star = [c for c in chars if c.get("rarity",0)==4]
    # ── Header ───────────────────────────────
    lines = [
        f"🎭 NHÂN VẬT — {nickname}",
        f"🆔 {uid}  |  ⭐×{len(five_star)}  🌟×{len(four_star)}  |  Tổng {len(chars)}",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    # ── 5 SAO ────────────────────────────────
    if five_star:
        lines.append(f"⭐⭐⭐⭐⭐  5 SAO ({len(five_star)})")
        for c in five_star:
            ei, _ = elem_map.get(c.get("element",""), ("✨","???"))
            cons  = c.get("actived_constellation_num", 0)
            lv    = c.get("level", 0)
            ft    = c.get("fetter", 0)
            heart = "❤️" if ft == 10 else f"🤍{ft}"
            lines.append(f"  {ei} {c['name']}  Lv.{lv} C{cons} {heart}")
    # ── 4 SAO ────────────────────────────────
    if four_star:
        lines.append("")
        lines.append(f"⭐⭐⭐⭐  4 SAO ({len(four_star)})")
        for c in four_star:
            ei, _ = elem_map.get(c.get("element",""), ("✨","???"))
            cons  = c.get("actived_constellation_num", 0)
            lv    = c.get("level", 0)
            c6    = " ✅" if cons == 6 else ""
            lines.append(f"  {ei} {c['name']}  Lv.{lv} C{cons}{c6}")
    # ── Thống kê nguyên tố ───────────────────
    elem_count: dict = {}
    elem_count_5: dict = {}
    for c in chars:
        _, ename = elem_map.get(c.get("element",""), ("✨","???"))
        elem_count[ename] = elem_count.get(ename, 0) + 1
        if c.get("rarity",0) == 5:
            elem_count_5[ename] = elem_count_5.get(ename, 0) + 1
    def _elem_bar(d):
        return "  ".join(
            f"{ei}×{d[ename]}"
            for ei, ename in elem_map.values()
            if d.get(ename, 0) > 0
        )
    lines += [
        "━━━━━━━━━━━━━━━━━━━━━",
        f"📊 Tổng:   {_elem_bar(elem_count)}",
        f"⭐ 5 sao: {_elem_bar(elem_count_5)}",
    ]
    # Chia thành nhiều đoạn nếu quá dài (Telegram giới hạn 4096 ký tự)
    MAX_LEN = 4000
    chunk = []
    chunk_len = 0
    for line in lines:
        add = len(line) + 1  # +1 cho \n
        if chunk and chunk_len + add > MAX_LEN:
            send(chat_id, "\n".join(chunk))
            chunk = []
            chunk_len = 0
        chunk.append(line)
        chunk_len += add
    if chunk:
        send(chat_id, "\n".join(chunk))
# ── /resin ───────────────────────────────
def cmd_resin(chat_id):
    cookies, err = load_cookie()
    if not cookies: send(chat_id, err); return
    info = get_account_info_cached(cookies)
    if not info: send(chat_id, "❌ Không lấy được UID"); return
    uid, nickname, region = info
    send(chat_id, "⏳ Đang lấy thông tin nhựa...")
    data    = get_realtime_notes(cookies, uid, region)
    retcode = data.get("retcode", -1)
    if retcode != 0:
        msg  = data.get("message", "unknown")
        hint = {
            10001:  "\n💡 Cookie hết hạn → /login",
            -100:   "\n💡 Cookie hết hạn → /login",
            10307:  "\n💡 HoYoLAB → bật 'Ghi Chép Thời Gian Thực'",
            -10001: "\n💡 HoYoLAB → bật 'Ghi Chép Thời Gian Thực'",
            10102:  "\n💡 HoYoLAB → chuyển hồ sơ sang công khai",
        }.get(retcode, "")
        send(chat_id, f"❌ Lỗi ({retcode}): {msg}{hint}"); return
    d        = data["data"]
    r_cur    = d.get("current_resin", 0)
    r_max    = d.get("max_resin", 200)
    eta_sec  = int(d.get("resin_recovery_time", "0"))
    fill     = int(r_cur / r_max * 12)
    bar      = "█" * fill + "░" * (12 - fill)
    if eta_sec <= 0:
        eta_s = "Đã đầy ✅"; full_at = ""
    else:
        ft    = now_vn() + datetime.timedelta(seconds=eta_sec)
        hh, mm = divmod(eta_sec // 60, 60)
        eta_s = f"{hh}h{mm:02d}m"
        full_at = f"\n   ⏰ Đầy lúc   : {ft.strftime('%H:%M  %d/%m/%Y')}"
    exps     = d.get("expeditions", [])
    exp_done = sum(1 for e in exps if e.get("status")=="Finished")
    daily_d  = d.get("finished_task_num", 0)
    daily_t  = d.get("total_task_num", 4)
    extra    = d.get("is_extra_task_reward_received", False)
    lines = [
        f"⚗️ NHỰA — {nickname}",
        f"   [{bar}] {r_cur}/{r_max}",
        f"   ⏱ Đầy sau  : {eta_s}{full_at}",
        f"   🗺 Expedition: {exp_done}/{len(exps)} xong",
        f"   📋 Daily    : {daily_d}/{daily_t}  {'✅' if daily_d>=daily_t else '❌'}",
        f"   🎁 Thưởng   : {'✅ Đã nhận' if extra else '❌ Chưa nhận'}",
    ]
    tf = d.get("transformer", {})
    if tf.get("obtained"):
        tr = tf.get("recovery_time", {}).get("reached", False)
        lines.append(f"   🔮 Transformer: {'✅ Sẵn sàng!' if tr else '⏳ Chưa sẵn sàng'}")
    send(chat_id, "\n".join(lines))
# ── /resinnotify ─────────────────────────
def cmd_resinnotify(chat_id, arg):
    cfg = _load_resin_cfg()
    arg = arg.strip().lower()
    if arg in ("off", "0"):
        cfg["enabled"] = False; _save_resin_cfg(cfg)
        send(chat_id, "🔕 Đã tắt thông báo nhựa."); return
    if arg == "on":
        cfg["enabled"] = True; _save_resin_cfg(cfg)
        send(chat_id, f"🔔 Đã bật thông báo nhựa (ngưỡng: {cfg['threshold']}/200)."); return
    if arg.isdigit():
        val = int(arg)
        if not 1 <= val <= 200:
            send(chat_id, "⚠️ Ngưỡng phải từ 1 đến 200."); return
        cfg["threshold"] = val; cfg["enabled"] = True
        cfg["notified"] = False; cfg["notified_critical"] = False   # reset cả 2 flag
        _save_resin_cfg(cfg)
        cookies, _ = load_cookie()
        if cookies:
            info = get_account_info_cached(cookies)
            if info:
                uid, _, region = info
                data = get_realtime_notes(cookies, uid, region)
                if data.get("retcode") == 0:
                    cur = data["data"].get("current_resin", 0)
                    mx  = data["data"].get("max_resin", 200)
                    if cur >= val:
                        send(chat_id, f"✅ Ngưỡng {val}/{mx} — nhựa {cur}/{mx} đã đạt!"); return
                    secs = (val - cur) * 480
                    eta  = now_vn() + datetime.timedelta(seconds=secs)
                    hh, mm = divmod(secs // 60, 60)
                    send(chat_id, f"✅ Ngưỡng: {val}/{mx}\n💧 Nhựa hiện tại: {cur}/{mx}\n"
                                  f"⏳ Cần thêm: {val-cur} × 8ph = {hh}h{mm:02d}m\n"
                                  f"🔔 Sẽ báo lúc: {eta.strftime('%H:%M  %d/%m/%Y')}"); return
        send(chat_id, f"✅ Đã đặt ngưỡng thông báo: {val}/200"); return
    send(chat_id,
         f"⚗️ THÔNG BÁO NHỰA\n"
         f"🔔 Trạng thái : {'BẬT' if cfg.get('enabled') else 'TẮT'}\n"
         f"⚠️ Ngưỡng    : {cfg.get('threshold',200)}/200\n\n"
         f"💡 /resinnotify 150  — báo khi nhựa ≥ 150\n"
         f"💡 /resinnotify off  — tắt")
# ── /fetchcodes ──────────────────────────
def cmd_fetchcodes(chat_id):
    # Guard: chỉ cho 1 lần fetchcodes chạy — reject nếu đang chạy
    if not _fetchcodes_lock.acquire(blocking=False):
        send(chat_id, "⏳ Đang có lệnh /fetchcodes đang chạy rồi.\n💡 Chờ nó xong nhé!"); return
    try:
        send(chat_id, "🔍 Đang tìm code từ 20+ nguồn...\n⏳ Chờ 30-60 giây...")
        result    = fetch_codes_from_web()
        all_codes = result["active"]
        sc        = result["source_count"]
        live_codes = result.get("live_codes", set())

        # Lọc blacklist LẦN NỮA ngay đây (fetch_codes_from_web đã lọc,
        # nhưng lọc lại để chắc chắn + tính số lượng bị bỏ)
        bl = load_blacklist()
        codes     = [c for c in all_codes if c not in bl]
        skipped_bl = len(all_codes) - len(codes)

        if not codes:
            msg = "❌ Không tìm thấy code nào còn hiệu lực"
            if skipped_bl:
                msg += f"\n⏭️ ({skipped_bl} code đã trong blacklist, bỏ qua)"
            msg += "\n💡 Code livestream xuất hiện sau khi stream kết thúc"
            send(chat_id, msg); return

        live_count    = len(live_codes & set(codes))
        total_confirm = sum(sc.get(c, 1) for c in codes)
        header = f"🎯 Tìm được {len(codes)} code mới ({total_confirm} lượt xác nhận)"
        if skipped_bl:
            header += f"\n⏭️ Đã bỏ qua {skipped_bl} code (trong blacklist)"
        if live_count:
            header += f"\n🔴 {live_count} code MỚI từ Reddit/HoYoLAB"

        preview = [header]
        for c in codes[:20]:
            n = sc.get(c, 1)
            tag = "🔴" if c in live_codes else "⭐" * min(n, 5)
            suffix = " — MỚI" if c in live_codes else ""
            preview.append(f"  {tag} {c}  ({n} nguồn{suffix})")
        if len(codes) > 20:
            preview.append(f"  ... và {len(codes)-20} code nữa")
        send(chat_id, "\n".join(preview))

        # Redeem
        if not _redeem_lock.acquire(blocking=False):
            send(chat_id, "⏳ Đang có lệnh redeem đang chạy; đã gửi danh sách code, thử /redeemall sau."); return
        try:
            cookies, err = load_cookie()
            if not cookies: send(chat_id, err); return
            info = get_account_info_cached(cookies)
            if not info: send(chat_id, "❌ Không lấy được UID"); return
            uid, nickname, region = info
            _do_redeem_codes(chat_id, codes, cookies, uid, region, nickname)
        finally:
            _redeem_lock.release()
    finally:
        _fetchcodes_lock.release()
# ── /blacklist / /clearblacklist ─────────
def cmd_blacklist(chat_id):
    bl = load_blacklist()
    if not bl: send(chat_id, "✅ Blacklist trống."); return
    lines = [f"🚫 BLACKLIST CODE ({len(bl)} code)", "━━━━━━━━━━━━━━━━━━━━"]
    for code, reason in sorted(bl.items()):
        lines.append(f"  • {code}  —  {reason}")
    lines += ["━━━━━━━━━━━━━━━━━━━━", "💡 /clearblacklist để xóa toàn bộ"]
    send(chat_id, "\n".join(lines))
def cmd_clearblacklist(chat_id):
    bl = load_blacklist()
    if not bl: send(chat_id, "ℹ️ Blacklist đã trống rồi."); return
    try:
        os.remove(CODES_BLACKLIST_FILE)
        # Invalidate bl cache sau khi xóa file
        global _bl_cache, _bl_cache_mtime
        _bl_cache = {}; _bl_cache_mtime = 0.0
        send(chat_id, f"✅ Đã xóa blacklist ({len(bl)} code).\nLần redeem tiếp sẽ thử lại tất cả.")
    except Exception as e:
        send(chat_id, f"❌ Lỗi xóa blacklist: {e}")
# ── /screenshot ──────────────────────────
def cmd_screenshot(chat_id):
    send(chat_id, "📸 Đang chụp màn hình...")
    try:
        path    = os.path.join(tempfile.gettempdir(), "bot_screenshot.png")
        success = False
        if IS_WINDOWS:
            try:
                from PIL import ImageGrab
                ImageGrab.grab().save(path); success = True
            except ImportError:
                ps = (
                    "Add-Type -AssemblyName System.Windows.Forms;"
                    "$bmp=[System.Drawing.Bitmap]::new("
                    "[System.Windows.Forms.SystemInformation]::VirtualScreen.Width,"
                    "[System.Windows.Forms.SystemInformation]::VirtualScreen.Height);"
                    "$g=[System.Drawing.Graphics]::FromImage($bmp);"
                    "$g.CopyFromScreen("
                    "[System.Windows.Forms.SystemInformation]::VirtualScreen.Left,"
                    "[System.Windows.Forms.SystemInformation]::VirtualScreen.Top,"
                    "0,0,$bmp.Size);"
                    f'$bmp.Save("{path}");$g.Dispose();$bmp.Dispose()'
                )
                r = subprocess.run(["powershell","-Command",ps], capture_output=True, timeout=15)
                success = r.returncode == 0
        else:
            tool_used = None
            for cmd_try, tool_name in [
                (["grim", path],                          "grim"),
                (["scrot",  path],                        "scrot"),
                (["maim",   path],                        "maim"),
                (["spectacle", "-b", "-n", "-o", path],   "spectacle"),
                (["gnome-screenshot", "-f", path],        "gnome-screenshot"),
                (["import", "-window", "root", path],     "imagemagick"),
            ]:
                try:
                    r = subprocess.run(cmd_try, capture_output=True, timeout=10,
                                       env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")})
                    if r.returncode == 0 and os.path.exists(path):
                        success = True; tool_used = tool_name; break
                except FileNotFoundError:
                    continue
                except Exception:
                    continue
        if success and os.path.exists(path):
            send_photo(chat_id, path, f"📸 {now_vn().strftime('%H:%M:%S  %d/%m/%Y')}")
            os.remove(path)
        else:
            if IS_WINDOWS:
                hint = "pip install Pillow"
            else:
                hint = "Cài công cụ chụp:\n  sudo pacman -S grim scrot  (Arch)\n  sudo apt install scrot  (Ubuntu/Debian)"
            send(chat_id, f"❌ Chụp màn hình thất bại\n💡 {hint}")
    except Exception as e:
        send(chat_id, f"❌ Lỗi: {e}")
# ── /shutdown / /restart / /cancel ───────
def cmd_shutdown(chat_id):
    send_with_buttons(chat_id,
        "⚠️ Bạn có chắc muốn TẮT MÁY sau 60 giây?",
        [[
            {"text": "✅ Tắt máy", "callback_data": "confirm_shutdown"},
            {"text": "❌ Huỷ",     "callback_data": "cancel_poweroff"},
        ]]
    )
def cmd_restart(chat_id):
    send_with_buttons(chat_id,
        "🔄 Bạn có chắc muốn RESTART MÁY sau 60 giây?",
        [[
            {"text": "✅ Restart", "callback_data": "confirm_restart"},
            {"text": "❌ Huỷ",    "callback_data": "cancel_poweroff"},
        ]]
    )
def cmd_cancel_shutdown(chat_id):
    try:
        if IS_WINDOWS:
            r = subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
        else:
            r = subprocess.run(["shutdown", "-c"], capture_output=True, text=True)
        if r.returncode == 0:
            send(chat_id, "✅ Đã huỷ lệnh tắt/restart máy.")
        else:
            send(chat_id, f"⚠️ Lệnh huỷ trả về lỗi: {(r.stderr or r.stdout).strip()}\n💡 Có thể không có lệnh tắt nào đang chờ.")
    except Exception as e:
        send(chat_id, f"❌ Lỗi huỷ shutdown: {e}")
# ── /login ───────────────────────────────
def _finish_login(chat_id, session_id=None):
    """Gọi khi login.py thành công. session_id: bỏ qua nếu /login đã gọi lại."""
    if session_id is not None and _LOGIN_SESSIONS.get(chat_id) != session_id:
        log.debug(f"[login] _finish_login session {session_id} hết hạn, bỏ qua")
        return
    _LOGIN_PROCS.pop(chat_id, None)
    time.sleep(0.8)
    global _cookie_cache_mtime
    _cookie_cache_mtime = 0.0
    cookies, err = load_cookie()
    if cookies:
        invalidate_account_cache()
        info = get_account_info_cached(cookies)
        if info:
            uid, nickname, region = info
            send(chat_id, f"✅ Đăng nhập thành công!\n👤 {nickname}\n🆔 {uid} | {region}\n💾 Cookie đã tự động lưu.")
        else:
            send(chat_id, "✅ Cookie đã lưu. Thử /status để kiểm tra.")
    else:
        send(chat_id, f"⚠️ Lưu cookie thất bại: {err}")
def cmd_login(chat_id):
    login_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login.py")
    if not os.path.exists(login_script):
        send(chat_id, "❌ Không tìm thấy login.py — đặt cùng thư mục với bot.py"); return
    old = _LOGIN_PROCS.pop(chat_id, None)
    if old:
        try: old.kill()
        except: pass
    # Tăng session_id TRƯỚC KHI gửi bất kỳ message nào
    # → _reader thread cũ (nếu còn sống) sẽ _valid() = False → thoát im lặng
    _sid = _LOGIN_SESSIONS.get(chat_id, 0) + 1
    _LOGIN_SESSIONS[chat_id] = _sid
    send(chat_id, "🌐 Đang mở trình duyệt...\n⏳ Chờ 10-20 giây để browser khởi động.")
    try:
        env = os.environ.copy()
        if not IS_WINDOWS:
            has_display = bool(
                os.environ.get("DISPLAY") or
                os.environ.get("WAYLAND_DISPLAY") or
                os.environ.get("XDG_SESSION_TYPE")
            )
            if has_display:
                # Co man hinh (desktop) → chay headed de user thay va tuong tac browser
                env["HEADLESS"] = "0"
            else:
                # Khong co display (SSH/server thuan) → chay headless
                env["HEADLESS"] = "1"
                env.pop("DISPLAY", None)
        if IS_WINDOWS:
            python_exe = sys.executable.replace("pythonw.exe","python.exe").replace("pythonw","python")
            log_file = os.path.join(tempfile.gettempdir(), f"login_log_{chat_id}.txt")
            log_fh   = open(log_file, "w", encoding="utf-8")
            proc = subprocess.Popen(
                [python_exe, "-u", login_script],
                stdin=subprocess.PIPE,
                stdout=log_fh, stderr=log_fh,
                text=True, encoding="utf-8", errors="replace",
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            proc._log_file = log_fh
            proc._log_path = log_file
        else:
            python_exe = sys.executable
            proc = subprocess.Popen(
                [python_exe, "-u", login_script],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=0, encoding="utf-8", errors="replace",
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env,
            )
        _LOGIN_PROCS[chat_id] = proc
        ready_event = threading.Event()
        _done       = threading.Event()  # SHARED: đặt ở ngoài _reader để tránh race với main thread

        def _reader():
            my_sid = _sid   # capture session ID tại thời điểm tạo thread

            def _valid() -> bool:
                """False nếu /login đã gọi lại hoặc /logincancel → thread thoát im lặng."""
                return _LOGIN_SESSIONS.get(chat_id) == my_sid

            def _on_line(line: str):
                if not line: return
                print(f"[login.py] {line}")
                if any(k in line for k in ("San sang", "TU DONG", "nhan Enter")):
                    ready_event.set()
                if "LOGIN_SUCCESS" in line:
                    ready_event.set()
                    if not _done.is_set() and _valid():
                        _done.set()
                        _CMD_EXEC.submit(_finish_login, chat_id, my_sid)
                    return
                if "TIMEOUT" in line:
                    if not _done.is_set() and _valid():
                        _done.set()
                        send(chat_id, "⏰ Quá 10 phút không phát hiện đăng nhập.\n💡 Gửi /login để thử lại.")
                        _LOGIN_PROCS.pop(chat_id, None)
                    return
                if "BROWSER_CLOSED" in line:
                    if not _done.is_set() and _valid():
                        _done.set()
                        send(chat_id, "🔒 Phiên đăng nhập đã kết thúc (trình duyệt bị đóng).\n"
                             "💡 /login để đăng nhập lại.")
                        _LOGIN_PROCS.pop(chat_id, None)
                    return

            if IS_WINDOWS and hasattr(proc, "_log_path"):
                lp = proc._log_path; seen = 0
                while not _done.is_set() and _valid():
                    try:
                        with open(lp, "r", encoding="utf-8", errors="replace") as f:
                            f.seek(seen); chunk = f.read()
                            if chunk:
                                seen += len(chunk)
                                for line in chunk.splitlines():
                                    _on_line(line.rstrip())
                                    if _done.is_set() or not _valid(): return
                    except Exception: pass
                    if proc.poll() is not None:
                        time.sleep(0.5)  # đọc nốt output còn lại
                        try:
                            with open(lp, "r", encoding="utf-8", errors="replace") as f:
                                f.seek(seen)
                                for line in f.read().splitlines():
                                    _on_line(line.rstrip())
                        except Exception: pass
                        if not _done.is_set() and _valid():
                            _done.set()
                            send(chat_id, "🔒 Phiên đăng nhập đã kết thúc.\n💡 /login để đăng nhập lại.")
                            _LOGIN_PROCS.pop(chat_id, None)
                        return
                    time.sleep(0.5)
            else:
                for raw in proc.stdout:
                    _on_line(raw.rstrip())
                    if _done.is_set() or not _valid(): return
                # stdout đóng = proc kết thúc
                if not _done.is_set() and _valid():
                    _done.set()
                    send(chat_id, "🔒 Phiên đăng nhập đã kết thúc.\n💡 /login để đăng nhập lại.")
                    _LOGIN_PROCS.pop(chat_id, None)

        threading.Thread(target=_reader, daemon=True).start()
        got_ready = ready_event.wait(timeout=60)

        # Cho _reader 0.4s xử lý EOF trước khi main kiểm tra
        if proc.poll() is not None:
            time.sleep(0.4)
        if proc.poll() is not None and not _done.is_set():
            _done.set()
            _LOGIN_PROCS.pop(chat_id, None)
            if not got_ready:
                # Browser chưa bao giờ mở → playwright lỗi → hướng dẫn cài lại
                send(chat_id,
                     "❌ Không mở được trình duyệt.\n"
                     "💡 Kiểm tra playwright:\n"
                     "pip install playwright\n"
                     "python -m playwright install chromium")
            else:
                # Browser đã mở nhưng _reader chưa kịp báo (race hiếm) → im lặng huỷ
                send(chat_id, "🔒 Phiên đăng nhập đã kết thúc.\n💡 /login để đăng nhập lại.")
            return

        msg_login = (
            "✅ Trình duyệt đã mở!\n"
            "👆 Click ô Username → tự điền\n"
            "👆 Click ô Password → tự điền\n"
            "🔐 Giải Captcha → nhấn Log In\n\n"
            "🤖 Bot sẽ TỰ ĐỘNG lưu cookie sau khi phát hiện đăng nhập.\n"
            "⏱ Tối đa 10 phút.\n\n"
            "🚨 Dự phòng: /logindone nếu bot không tự thông báo sau vài phút."
        ) if got_ready else (
            "⏳ Browser đang khởi động, chưa nhận được tín hiệu sẵn sàng.\n"
            "🔐 Hãy đăng nhập khi browser xuất hiện — bot sẽ tự động lưu.\n"
            "❌ Không thấy browser → thử /login lại.\n"
            "🚨 Dự phòng: /logindone nếu bot không tự thông báo sau vài phút."
        )
        send_with_buttons(chat_id, msg_login,
            [[{"text": "❌ Huỷ đăng nhập", "callback_data": "cancel_login"}]])
    except Exception as e:
        _LOGIN_PROCS.pop(chat_id, None)
        send(chat_id, f"❌ Lỗi: {e}")
# ── /logincancel ─────────────────────────
def cmd_logincancel(chat_id):
    """Hủy phiên đăng nhập đang chờ."""
    proc = _LOGIN_PROCS.pop(chat_id, None)
    if proc is None:
        send(chat_id, "ℹ️ Không có phiên đăng nhập nào đang chạy.\n💡 Dùng /login để bắt đầu."); return
    # Invalidate session TRƯỚC khi kill → _reader thoát im lặng, KHÔNG gửi "trình duyệt đã đóng"
    _LOGIN_SESSIONS[chat_id] = _LOGIN_SESSIONS.get(chat_id, 0) + 1
    try:
        proc.kill()
        proc.wait(timeout=3)
    except Exception: pass
    send(chat_id, "✅ Đã hủy phiên đăng nhập.\n💡 Gửi /login để đăng nhập lại.")

# ── /logindone ───────────────────────────
def cmd_logindone(chat_id):
    """
    Dự phòng thủ công — chỉ dùng khi bot không tự thông báo sau vài phút.
    Invalidate session → _reader sẽ không gọi _finish_login thêm lần nữa.
    """
    proc = _LOGIN_PROCS.get(chat_id)
    if proc is None:
        send(chat_id, "⚠️ Không có phiên login nào đang chạy. Dùng /login trước."); return
    # Invalidate → _reader sẽ bỏ qua nếu sau này cũng nhận LOGIN_SUCCESS
    _LOGIN_SESSIONS[chat_id] = _LOGIN_SESSIONS.get(chat_id, 0) + 1
    if proc.poll() is None:
        send(chat_id, "⏳ Chờ login.py hoàn tất...")
        try: proc.wait(timeout=12)
        except Exception: pass
    _finish_login(chat_id)


# ── /start ───────────────────────────────
def cmd_start(chat_id):
    msg = (
        "👋 Welcome to botDailyGI! / Chào mừng đến với botDailyGI!\n\n"
        "🌐 Please select your language / Vui lòng chọn ngôn ngữ:"
    )
    send_with_buttons(chat_id, msg, [
        [{"text": "🇬🇧 English", "callback_data": "lang_en"}],
        [{"text": "🇻🇳 Tiếng Việt", "callback_data": "lang_vi"}]
    ])

# ── /help ────────────────────────────────
def cmd_help(chat_id):
    send(chat_id, (
        "📋 DANH SÁCH LỆNH\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎮 GENSHIN\n"
        "/status          — trạng thái bot + resin + lịch\n"
        "/uid             — UID và nickname\n"
        "/checkin         — điểm danh ngay\n"
        "/characters      — danh sách nhân vật\n"
        "/resin           — nhựa + expedition + daily\n"
        "/resinnotify N   — báo khi nhựa ≥ N (vd: /resinnotify 140)\n"
        "/resinnotify off — tắt thông báo nhựa\n"
        "/redeem CODE     — đổi 1 gift code\n"
        "/redeemall       — đổi toàn bộ codes.txt\n"
        "/fetchcodes      — tìm code từ 20+ nguồn + redeem luôn\n"
        "/blacklist       — xem code bị blacklist\n"
        "/clearblacklist  — xóa toàn bộ blacklist\n"
        "\n💻 MÁY TÍNH\n"
        "/screenshot      — chụp màn hình\n"
        "\n⚡ NGUỒN ĐIỆN\n"
        "/shutdown        — tắt máy (xác nhận bằng nút bấm)\n"
        "/restart         — restart máy (xác nhận bằng nút bấm)\n"
        "/cancel          — huỷ lệnh tắt/restart\n"
        "\n🔐 TÀI KHOẢN\n"
        "/login           — mở trình duyệt đăng nhập HoYoLAB\n"
        "/logindone       — lưu cookie (dự phòng thủ công)\n"
        "/logincancel     — huỷ phiên đăng nhập đang chờ\n"
        "/help            — danh sách này\n"
        "\nℹ️ Tính năng tự động:\n"
        "• Điểm danh 09:00 & 21:00 (retry 3 lần nếu lỗi)\n"
        "• Cảnh báo nhựa 2 mức (ngưỡng & sắp tràn)\n"
        "• Heartbeat mỗi 12h  |  📝 Log: bot.log"
    ))
# ─────────────────────────────────────────
# ──────── BACKGROUND THREADS ─────────────
#
# Nguyên tắc: KHÔNG poll liên tục.
# Mỗi thread tính chính xác thời điểm cần
# thức dậy rồi time.sleep() đúng khoảng đó.
# ─────────────────────────────────────────
def _do_checkin(label: str, max_retries: int = 3, retry_wait_min=None):
    """Điểm danh HoYoLAB với cơ chế thử lại khi lỗi mạng/server.
    Nếu thất bại: đợi retry_wait_min phút rồi thử lại, tối đa max_retries lần.
    retry_wait_min: None → tự động backoff [5, 15, 30] phút.
    """
    _RETRY_WAITS = [5, 15, 30]   # phút theo backoff
    for attempt in range(1, max_retries + 1):
        cookies, err = load_cookie()
        if not cookies:
            send(TELEGRAM_CHAT_ID, f"⚠️ Auto check-in thất bại: {err}"); return
        try:
            hdrs = load_headers()
            r    = _HTTP.get(INFO_API, params={"act_id": ACT_ID}, headers=hdrs, timeout=15)
            if r.json().get("data", {}).get("is_sign"):
                send(TELEGRAM_CHAT_ID, f"{label} Hôm nay đã điểm danh rồi ✅"); return
            r = _HTTP.post(SIGN_API, json={"act_id": ACT_ID}, headers=hdrs, timeout=15)
            rc = r.json().get("retcode", -1)
            if rc == 0:
                send(TELEGRAM_CHAT_ID, f"{label} ✅ Điểm danh thành công!")
                return
            msg = r.json().get("message", "unknown")
            # Lỗi "đã điểm danh" → không retry
            if any(k in msg.lower() for k in ["already", "đã điểm danh", "signed in", "traveler, check-in"]):
                send(TELEGRAM_CHAT_ID, f"{label} ℹ️ Đã điểm danh rồi ({msg})")
                return
            # Lỗi khác → retry
            if attempt < max_retries:
                wait_m = _RETRY_WAITS[min(attempt - 1, len(_RETRY_WAITS) - 1)] \
                         if retry_wait_min is None else retry_wait_min
                print(f"{label} Lần {attempt} thất bại (rc={rc}: {msg}). Thử lại sau {wait_m} phút...")
                send(TELEGRAM_CHAT_ID,
                     f"⚠️ {label} Điểm danh lần {attempt} thất bại: {msg}\n"
                     f"🔄 Thử lại sau {wait_m} phút...")
                time.sleep(wait_m * 60)
            else:
                send(TELEGRAM_CHAT_ID,
                     f"❌ {label} Điểm danh thất bại sau {max_retries} lần thử: {msg}\n"
                     f"💡 Dùng /checkin để thử thủ công hoặc /login nếu cookie hết hạn.")
        except Exception as e:
            if attempt < max_retries:
                wait_m = _RETRY_WAITS[min(attempt - 1, len(_RETRY_WAITS) - 1)] \
                         if retry_wait_min is None else retry_wait_min
                print(f"{label} Lần {attempt} lỗi mạng: {e}. Thử lại sau {wait_m} phút...")
                send(TELEGRAM_CHAT_ID,
                     f"⚠️ {label} Lỗi mạng lần {attempt}: {e}\n"
                     f"🔄 Thử lại sau {wait_m} phút...")
                time.sleep(wait_m * 60)
            else:
                send(TELEGRAM_CHAT_ID, f"❌ {label} Lỗi sau {max_retries} lần: {e}")
def auto_checkin_loop():
    """Ngủ đúng đến 09:00 / 21:00, sau đó điểm danh."""
    SCHEDULE = [(9, 0), (21, 0)]
    print("⏰ Auto check-in thread sẵn sàng (sẽ chạy lúc 09:00 và 21:00 VN)")
    while True:
        now  = now_vn()
        nxt  = None
        for h, m in SCHEDULE:
            t = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if t <= now: t += datetime.timedelta(days=1)
            if nxt is None or t < nxt: nxt = t
        secs = max((nxt - now).total_seconds(), 0)   # đảm bảo không âm
        hh, mm = divmod(int(secs)//60, 60)
        print(f"⏰ Auto check-in: ngủ {hh}h{mm:02d}m → thức lúc {nxt.strftime('%H:%M %d/%m')}")
        time.sleep(secs)
        actual = now_vn()
        _do_checkin(f"🌅 [{actual.strftime('%H:%M')}] Auto check-in:")
def resin_monitor_loop():
    """
    Tính chính xác bao lâu nữa nhựa đạt ngưỡng → ngủ đúng khoảng đó.
    Chỉ thức dậy khi thực sự cần kiểm tra / gửi thông báo.
    Hỗ trợ 2 mức cảnh báo:
      - Mức 1 (threshold): cảnh báo lần đầu
      - Mức 2 (threshold + 8): cảnh báo gắt trước khi tràn 160
    """
    print("⚗️ Resin monitor thread sẵn sàng")
    # Cache UID/nickname/region — refresh sau 1 giờ hoặc khi lỗi
    _uid = _nickname = _region = None
    _account_cache_time: float = 0.0
    _ACCOUNT_CACHE_TTL = 3600   # 1 giờ
    while True:
        cfg = _load_resin_cfg()
        if not cfg.get("enabled"):
            # Tắt → ngủ 30 phút, check lại
            time.sleep(1800); continue
        cookies, _ = load_cookie()
        if not cookies:
            time.sleep(1800); continue
        # Refresh account info nếu chưa có hoặc đã quá TTL
        if _uid is None or (time.time() - _account_cache_time) > _ACCOUNT_CACHE_TTL:
            info = get_account_info(cookies)
            if not info:
                time.sleep(1800); continue
            _uid, _nickname, _region = info
            _account_cache_time = time.time()
        uid, nickname, region = _uid, _nickname, _region
        try:
            data = get_realtime_notes(cookies, uid, region)
            if data.get("retcode", -1) != 0:
                # Lỗi API → reset cache account phòng cookie hết hạn
                _uid = None
                time.sleep(1800); continue
            d            = data["data"]
            resin_cur    = d.get("current_resin", 0)
            resin_max    = d.get("max_resin", 200)
            eta_full_sec = int(d.get("resin_recovery_time", "0"))
            threshold          = min(cfg.get("threshold", resin_max), resin_max)  # clamp
            threshold_critical = min(threshold + 8, resin_max)
            # Chỉ bật mức 2 khi có khoảng cách (tránh skip mức 1 khi threshold=200)
            _critical_active   = threshold_critical > threshold
            print(f"[resin] {nickname}: {resin_cur}/{resin_max}, ngưỡng={threshold}, critical={threshold_critical}(active={_critical_active})")
            # ── Mức 2: sắp tràn ─────────────────────────────────
            if _critical_active and resin_cur >= threshold_critical:
                if not cfg.get("notified_critical", False):
                    send(TELEGRAM_CHAT_ID,
                         f"🚨 NHỰA SẮP TRÀN!\n"
                         f"👤 {nickname}\n"
                         f"💧 Nhựa: {resin_cur}/{resin_max}\n"
                         f"🔴 Còn {resin_max - resin_cur} nhựa nữa là tràn!\n"
                         f"⚡ Vào farm NGAY kẻo mất nhựa!")
                    cfg["notified_critical"] = True; _save_resin_cfg(cfg)
                else:
                    print(f"[resin] Đã báo critical rồi ({resin_cur}/{resin_max}), bỏ qua")
                time.sleep(1800); continue
            # ── Mức 1: đạt ngưỡng ────────────────────────────────
            if resin_cur >= threshold:
                if not cfg.get("notified", False):
                    full_str = "đầy hoàn toàn ✅" if eta_full_sec <= 0 else f"{resin_cur}/{resin_max}"
                    send(TELEGRAM_CHAT_ID,
                         f"⚗️ NHỰA ĐÃ ĐẠT NGƯỠNG!\n"
                         f"👤 {nickname}\n"
                         f"💧 Nhựa: {full_str}\n"
                         f"⚠️ Ngưỡng: {threshold}/{resin_max}\n"
                         f"💡 Vào farm nhựa kẻo tràn!\n"
                         f"(Sẽ cảnh báo thêm khi ≥{threshold_critical})")
                    cfg["notified"] = True; _save_resin_cfg(cfg)
                else:
                    print(f"[resin] Đã báo rồi ({resin_cur}/{resin_max}), bỏ qua")
                # Tính ngủ đến khi đạt critical threshold
                secs_to_critical = (threshold_critical - resin_cur) * 480
                sleep_sec = max(secs_to_critical, 300)
                eta_time  = now_vn() + datetime.timedelta(seconds=sleep_sec)
                hh, mm    = divmod(int(sleep_sec)//60, 60)
                print(f"[resin] Ngủ {hh}h{mm:02d}m đến critical threshold → {eta_time.strftime('%H:%M %d/%m')}")
                time.sleep(sleep_sec)
                continue
            # Dưới ngưỡng → reset flag notified + notified_critical
            changed = False
            if cfg.get("notified", False):
                cfg["notified"] = False; changed = True
            if cfg.get("notified_critical", False):
                cfg["notified_critical"] = False; changed = True
            if changed:
                _save_resin_cfg(cfg)
            # Tính chính xác bao lâu nhựa đạt ngưỡng
            resin_needed = threshold - resin_cur
            sleep_sec    = resin_needed * 480          # 8 phút / nhựa
            if 0 < eta_full_sec < sleep_sec:
                sleep_sec = eta_full_sec
            sleep_sec = max(sleep_sec, 300)            # tối thiểu 5 phút
            eta_time  = now_vn() + datetime.timedelta(seconds=sleep_sec)
            hh, mm    = divmod(int(sleep_sec)//60, 60)
            print(f"[resin] Ngủ {hh}h{mm:02d}m → thức lúc {eta_time.strftime('%H:%M %d/%m')}")
            time.sleep(sleep_sec)
        except Exception as e:
            print(f"[resin] Lỗi: {e}"); time.sleep(1800)
def auto_fetchcodes_loop():
    """
    Tự động fetch + redeem code sau mỗi livestream Genshin.
    Logic:
      - Tính giờ live tiếp theo (patch_date - 7 ngày, mặc định 11:00 VN)
      - Ngủ đến (giờ live + 1 tiếng) — lúc này stream đã xong, code đã được post
      - Fetch code từ 20+ nguồn, ưu tiên Reddit/HoYoLAB real-time
      - Redeem tất cả code mới tìm được
      - Lặp lại cho livestream tiếp theo
    """
    # Giờ livestream Genshin — dùng module constants (STREAM_HOUR / STREAM_MINUTE / WAIT_AFTER)
    print("🎮 Auto fetchcodes loop sẵn sàng")
    while True:
        # Tìm thời điểm fetch tiếp theo = giờ live + WAIT_AFTER phút
        now = now_vn()
        fetch_dt = None
        ver_next = None
        # ── Ưu tiên 1: đọc lịch đã lưu từ file live_detect.json ──────────────
        try:
            with open(LIVE_DETECT_FILE, "r", encoding="utf-8") as rf:
                saved = json.load(rf)
                iso = saved.get("fetch_dt_iso")
                if iso:
                    cand = datetime.datetime.fromisoformat(iso)
                    if cand > now:   # lịch còn hiệu lực
                        fetch_dt = cand
                        ver_next = saved.get("ver", "?")
                        print(f"[fetchcodes_auto] Dùng lịch đã lưu: v{ver_next} lúc {fetch_dt.strftime('%H:%M %d/%m')}")
        except Exception:
            pass
        # ── Ưu tiên 2: dò giờ live từ HoYoLAB News (nếu bật AUTO_LIVE_DETECT=1) ──
        if fetch_dt is None and os.getenv("AUTO_LIVE_DETECT", "0") == "1":
            try:
                url = "https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList?gids=2&page_size=20&type=1"
                r   = _HTTP.get(url, headers={"User-Agent": _UA}, timeout=10)
                j   = r.json()
                lst = j.get("data", {}).get("list", [])
                pat = re.compile(r"(\d{1,2}):(\d{2}).{0,12}UTC\s*([+-]?\d{1,2})", re.IGNORECASE)
                for it in lst:
                    title   = (it.get("post", {}) or {}).get("subject", "") or it.get("title", "")
                    content = (it.get("post", {}) or {}).get("content", "")
                    txt = (title + " " + content).lower()
                    if ("special program" in txt) or ("chương trình đặc biệt" in txt):
                        m = pat.search(txt)
                        if m:
                            hh = int(m.group(1)); mm_t = int(m.group(2)); off = int(m.group(3))
                            # Quy đổi giờ VN: VN(UTC+7) = giờ_UTC±off + (7 - off)
                            vn_h = (hh + (7 - off)) % 24
                            live_vn = now.replace(hour=vn_h, minute=mm_t, second=0, microsecond=0)
                            if live_vn <= now:
                                live_vn += datetime.timedelta(days=1)
                            fetch_dt = live_vn + datetime.timedelta(minutes=WAIT_AFTER)
                            print(f"[detect_live] Found {hh:02d}:{mm_t:02d} UTC{off:+} → VN {live_vn.strftime('%H:%M %d/%m')}")
                            # Lưu lịch vào file để dùng lại khi bot restart
                            try:
                                with open(LIVE_DETECT_FILE, "w", encoding="utf-8") as wf:
                                    json.dump({"fetch_dt_iso": fetch_dt.isoformat(), "ver": "?"}, wf)
                            except Exception: pass
                            break
            except Exception as e:
                print(f"[detect_live] lỗi: {e}")
        # ── Ưu tiên 3: fallback theo lịch patch ──────────────────────────────
        if fetch_dt is None:
            for ver, ps in get_versions():
                try:
                    pd = datetime.date.fromisoformat(ps)
                except Exception:
                    continue
                sd = pd - datetime.timedelta(days=7)
                stream_start = datetime.datetime(
                    sd.year, sd.month, sd.day,
                    STREAM_HOUR, STREAM_MINUTE, tzinfo=VN_TZ
                )
                candidate = stream_start + datetime.timedelta(minutes=WAIT_AFTER)
                if candidate > now:
                    fetch_dt = candidate
                    ver_next = ver
                    break
        if not fetch_dt:
            # Không có lịch trong fallback → ngủ 24h rồi check lại
            print("[fetchcodes_auto] Không tìm được lịch live → ngủ 24h")
            time.sleep(24 * 3600)
            continue
        secs = (fetch_dt - now_vn()).total_seconds()
        hh, mm = divmod(int(secs) // 60, 60)
        print(f"[fetchcodes_auto] v{ver_next} — fetch lúc {fetch_dt.strftime('%H:%M %d/%m')}, ngủ {hh}h{mm:02d}m")
        time.sleep(max(secs, 0))
        # Thức dậy → fetch + redeem
        print(f"[fetchcodes_auto] Thức dậy sau live v{ver_next}, bắt đầu fetch code...")
        send(TELEGRAM_CHAT_ID,
             f"🎮 Auto fetch code sau livestream v{ver_next}!\n"
             f"🔍 Đang tìm code từ 20+ nguồn...")
        # ── Retry loop: chờ đủ 3 code, tối đa 2 tiếng, retry mỗi 15 phút ──
        NEED_CODES   = 3
        RETRY_MINS   = 15
        MAX_WAIT_HRS = 2
        deadline     = now_vn() + datetime.timedelta(hours=MAX_WAIT_HRS)
        attempt      = 0
        codes        = []
        sc           = {}
        live_codes   = set()
        while True:
            attempt += 1
            result     = fetch_codes_from_web()
            codes      = result["active"]
            sc         = result["source_count"]
            live_codes = result.get("live_codes", set())
            remaining_min = int((deadline - now_vn()).total_seconds() / 60)
            if len(codes) >= NEED_CODES:
                send(TELEGRAM_CHAT_ID,
                     f"✅ v{ver_next}: Tìm đủ {len(codes)} code (lần {attempt}) — bắt đầu redeem!")
                break
            if now_vn() >= deadline:
                send(TELEGRAM_CHAT_ID,
                     f"⏰ v{ver_next}: Hết {MAX_WAIT_HRS}h chờ, chỉ tìm được {len(codes)}/{NEED_CODES} code.\n"
                     f"⏭️ Bỏ qua, không redeem. Dùng /fetchcodes để thử thủ công.")
                codes = []
                break
            send(TELEGRAM_CHAT_ID,
                 f"🔍 v{ver_next} lần {attempt}: Tìm được {len(codes)}/{NEED_CODES} code — "
                 f"chờ {RETRY_MINS} phút thử lại (còn {remaining_min} phút).")
            time.sleep(RETRY_MINS * 60)
        if not codes:
            try:
                os.remove(LIVE_DETECT_FILE)
            except Exception:
                pass
            time.sleep(2 * 3600)
            continue
        # Hiển thị danh sách tìm được
        total_confirm = sum(sc.values())
        live_count = len(live_codes & set(codes))
        header = f"🎯 v{ver_next}: Tìm được {len(codes)} code ({total_confirm} lượt xác nhận)"
        if live_count:
            header += f"\n🔴 {live_count} code MỚI từ Reddit/HoYoLAB"
        preview = [header]
        for c in codes[:20]:
            n = sc.get(c, 1)
            if c in live_codes:
                preview.append(f"  🔴 {c}  ({n} nguồn — MỚI)")
            else:
                stars = "⭐" * min(n, 5)
                preview.append(f"  {stars} {c}  ({n} nguồn)")
        if len(codes) > 20:
            preview.append(f"  ... và {len(codes)-20} code nữa")
        send(TELEGRAM_CHAT_ID, "\n".join(preview))
        # Redeem
        cookies, err = load_cookie()
        if not cookies:
            send(TELEGRAM_CHAT_ID, f"❌ Không redeem được: {err}"); time.sleep(2*3600); continue
        info = get_account_info_cached(cookies)
        if not info:
            send(TELEGRAM_CHAT_ID, "❌ Không lấy được UID"); time.sleep(2*3600); continue
        uid, nickname, region = info
        # Acquire cả 2 lock — không xung đột với cmd_fetchcodes thủ công
        if not _fetchcodes_lock.acquire(blocking=False):
            log.info("[auto_fetch] cmd_fetchcodes đang chạy, bỏ qua lần này")
            time.sleep(300); continue
        try:
            with _redeem_lock:
                _do_redeem_codes(None, codes, cookies, uid, region, nickname, label=f"v{ver_next}")
        finally:
            _fetchcodes_lock.release()
        # Ngủ 2h tránh loop tức thì, rồi xử lý livestream tiếp theo
        try:
            os.remove(LIVE_DETECT_FILE)
        except Exception:
            pass
        print(f"[fetchcodes_auto] v{ver_next} xong. Ngủ 2h rồi chờ lịch tiếp.")
        time.sleep(2 * 3600)
# ─────────────────────────────────────────
# HEARTBEAT — "I'm alive" mỗi 12 tiếng
# ─────────────────────────────────────────
def heartbeat_loop():
    """Gửi tin nhắn xác nhận bot còn sống mỗi 12 tiếng."""
    INTERVAL_H = 12
    print(f"💓 Heartbeat thread sẵn sàng (mỗi {INTERVAL_H}h)")
    # Đợi 12h lần đầu trước khi bắt đầu gửi
    time.sleep(INTERVAL_H * 3600)
    while True:
        try:
            cookies, _ = load_cookie()
            extra_str = ""
            if cookies:
                info = get_account_info_cached(cookies)
                if info:
                    uid, nickname, region = info
                    data = get_realtime_notes(cookies, uid, region)
                    if data.get("retcode") == 0:
                        d = data["data"]
                        r_cur = d.get("current_resin", 0)
                        r_max = d.get("max_resin", 200)
                        eta_sec = int(d.get("resin_recovery_time", "0"))
                        fill = int(r_cur / r_max * 10)
                        bar  = "█" * fill + "░" * (10 - fill)
                        if eta_sec > 0:
                            ft = now_vn() + datetime.timedelta(seconds=eta_sec)
                            eta_s = f" — đầy {ft.strftime('%H:%M %d/%m')}"
                        else:
                            eta_s = " — đầy ✅"
                        # Trạng thái điểm danh
                        sign_str = ""
                        try:
                            hdrs = load_headers()
                            ri = _HTTP.get(INFO_API, params={"act_id": ACT_ID},
                                           headers=hdrs, timeout=8)
                            d2 = ri.json().get("data", {})
                            sign_str = f"\n📅 Điểm danh: {'✅ Đã điểm' if d2.get('is_sign') else '❌ Chưa điểm'} ({d2.get('total_sign_day','?')} ngày)"
                        except Exception:
                            pass
                        extra_str = f"\n⚗️ Nhựa: [{bar}] {r_cur}/{r_max}{eta_s}{sign_str}"
            send(TELEGRAM_CHAT_ID,
                 f"💓 Bot vẫn đang chạy\n"
                 f"🖥 {socket.gethostname()}\n"
                 f"🕐 {now_vn().strftime('%H:%M:%S  %d/%m/%Y')}\n"
                 f"⏱ Uptime: {uptime_str()}"
                 f"{extra_str}")
        except Exception as e:
            print(f"[heartbeat] Lỗi: {e}")
        time.sleep(INTERVAL_H * 3600)
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
        "/status":          (cmd_status,          ()),
        "/uid":             (cmd_uid,             ()),
        "/checkin":         (cmd_checkin,         ()),
        "/characters":      (cmd_characters,      ()),
        "/resin":           (cmd_resin,           ()),
        "/resinnotify":     (cmd_resinnotify,     (arg,)),
        "/redeem":          (cmd_redeem,          (arg.upper(),)),
        "/redeemall":       (cmd_redeemall,       ()),
        "/fetchcodes":      (cmd_fetchcodes,      ()),
        "/blacklist":       (cmd_blacklist,       ()),
        "/clearblacklist":  (cmd_clearblacklist,  ()),
        "/screenshot":      (cmd_screenshot,      ()),
        "/shutdown":        (cmd_shutdown,        ()),
        "/restart":         (cmd_restart,         ()),
        "/cancel":          (cmd_cancel_shutdown, ()),
        "/login":           (cmd_login,           ()),
        "/logindone":       (cmd_logindone,       ()),
        "/logincancel":     (cmd_logincancel,     ()),
        "/help":            (cmd_help,            ()),
        "/start":           (cmd_start,           ()),
    }
    if cmd in dispatch:
        fn, args = dispatch[cmd]
        fn(chat_id, *args)
    else:
        send(chat_id, "❓ Lệnh không nhận ra. Gõ /help")
# ─────────────────────────────────────────
# CALLBACK QUERY HANDLER (inline buttons)
# ─────────────────────────────────────────
def handle_callback(callback_id: str, chat_id, data: str):
    """Xử lý callback từ inline keyboard buttons."""
    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        answer_callback(callback_id, "⛔ Không có quyền", chat_id=chat_id)
        return
    if data.startswith("lang_"):
        l = data.split("_")[1]
        lang.set_lang(chat_id, l)
        answer_callback(callback_id, f"✅ Language set to {l.upper()}", chat_id=chat_id)
        cmd_help(chat_id)
        return
    if data == "confirm_shutdown":
        answer_callback(callback_id, "⚠️ Đang tắt máy...", chat_id=chat_id)
        send(chat_id, "⚠️ Đang tắt máy sau 60 giây...\nDùng /cancel để huỷ.")
        try:
            if IS_WINDOWS: subprocess.Popen(["shutdown","/s","/t","60"])
            else:          subprocess.Popen(["shutdown","-h","+1"])
        except Exception as e:
            send(chat_id, f"❌ Lỗi: {e}")
    elif data == "confirm_restart":
        answer_callback(callback_id, "🔄 Đang restart...", chat_id=chat_id)
        send(chat_id, "🔄 Đang restart sau 60 giây...\nDùng /cancel để huỷ.")
        try:
            if IS_WINDOWS: subprocess.Popen(["shutdown","/r","/t","60"])
            else:          subprocess.Popen(["shutdown","-r","+1"])
        except Exception as e:
            send(chat_id, f"❌ Lỗi: {e}")
    elif data == "cancel_poweroff":
        answer_callback(callback_id, "✅ Đã huỷ", chat_id=chat_id)
        send(chat_id, "✅ Đã huỷ lệnh tắt/restart.")
    elif data == "confirm_logindone":
        answer_callback(callback_id, "💾 Đang lưu cookie...", chat_id=chat_id)
        cmd_logindone(chat_id)
    elif data == "cancel_login":
        answer_callback(callback_id, "✅ Đã huỷ", chat_id=chat_id)
        cmd_logincancel(chat_id)
    else:
        answer_callback(callback_id, "❓ Không rõ hành động", chat_id=chat_id)
# ─────────────────────────────────────────
# REGISTER COMMANDS (menu Telegram)
# ─────────────────────────────────────────
def register_commands():
    commands = [
        {"command": "status",          "description": "Trạng thái bot + resin + lịch"},
        {"command": "uid",             "description": "UID và nickname"},
        {"command": "checkin",         "description": "Điểm danh HoYoLAB ngay"},
        {"command": "characters",      "description": "Danh sách nhân vật"},
        {"command": "resin",           "description": "Nhựa + expedition + daily"},
        {"command": "resinnotify",     "description": "Thông báo nhựa (vd: /resinnotify 140)"},
        {"command": "fetchcodes",      "description": "Tìm code từ 20+ nguồn + redeem luôn"},
        {"command": "redeem",          "description": "Đổi 1 gift code (vd: /redeem ABC123)"},
        {"command": "redeemall",       "description": "Đổi toàn bộ code trong codes.txt"},
        {"command": "blacklist",       "description": "Xem code bị blacklist"},
        {"command": "clearblacklist",  "description": "Xóa toàn bộ blacklist"},
        {"command": "screenshot",      "description": "Chụp màn hình máy tính"},
        {"command": "shutdown",        "description": "Tắt máy tính"},
        {"command": "restart",         "description": "Khởi động lại máy"},
        {"command": "cancel",          "description": "Huỷ lệnh tắt/restart"},
        {"command": "login",           "description": "Mở trình duyệt đăng nhập HoYoLAB"},
        {"command": "logindone",       "description": "Lưu cookie HoYoLAB (dự phòng)"},
        {"command": "logincancel",     "description": "Huỷ phiên đăng nhập đang chờ"},
        {"command": "help",            "description": "Xem toàn bộ danh sách lệnh"},
    ]
    try:
        r = _HTTP.post(f"{BASE_URL}/setMyCommands",
                          json={"commands": commands}, timeout=10)
        if r.json().get("ok"):
            print(f"✅ Đã đăng ký {len(commands)} lệnh với Telegram")
        else:
            print(f"⚠️ setMyCommands thất bại: {r.json()}")
    except Exception as e:
        print(f"⚠️ Không đăng ký được lệnh: {e}")
# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def _startup_checkin():
    """Điểm danh khi khởi động. Im lặng nếu đã điểm rồi (tránh spam khi restart)."""
    time.sleep(3)
    cookies, err = load_cookie()
    if not cookies:
        log.info(f"[startup_checkin] Bỏ qua: {err}"); return
    try:
        hdrs = load_headers()
        r = _HTTP.get(INFO_API, params={"act_id": ACT_ID}, headers=hdrs, timeout=15)
        if r.json().get("data", {}).get("is_sign"):
            log.info("[startup_checkin] Hôm nay đã điểm danh rồi, bỏ qua."); return
    except Exception as e:
        log.warning(f"[startup_checkin] Không kiểm tra được: {e}")
    _do_checkin("🚀 [Khởi động] Auto check-in:")
def main():
    print(f"🤖 Bot đang khởi động trên {socket.gethostname()}")
    print(f"   OS      : {'Windows' if IS_WINDOWS else 'Linux'}")
    print(f"   Chat ID : {TELEGRAM_CHAT_ID}")
    print(f"   Giờ VN  : {now_vn().strftime('%H:%M:%S  %d/%m/%Y')}")
    print("   Ctrl+C để dừng.\n")
    try:
        gm = _HTTP.get(f"{BASE_URL}/getMe", timeout=8)
        if not gm.json().get("ok", False):
            print(f"⚠️ getMe thất bại: {gm.text[:120]}")
    except Exception as e:
        print(f"⚠️ getMe lỗi: {e}")
    register_commands()
    # Khởi động 4 thread nền — mỗi thread chỉ thức dậy khi đến giờ
    threading.Thread(target=auto_checkin_loop,    daemon=True, name="CheckIn").start()
    threading.Thread(target=resin_monitor_loop,   daemon=True, name="ResinMon").start()
    threading.Thread(target=auto_fetchcodes_loop, daemon=True, name="AutoFetch").start()
    threading.Thread(target=heartbeat_loop,       daemon=True, name="Heartbeat").start()
    send(TELEGRAM_CHAT_ID,
         f"🤖 Bot đã khởi động!\n"
         f"🖥 {socket.gethostname()}  ({'Win' if IS_WINDOWS else 'Linux'})\n"
         f"🕐 {now_vn().strftime('%H:%M:%S  %d/%m/%Y')}\n"
         f"💓 Heartbeat mỗi 12h  |  📝 Log: bot.log\n\n"
         "Gõ /help để xem lệnh.")
    # Kiểm tra và điểm danh ngay khi khởi động
    threading.Thread(target=_startup_checkin, daemon=True).start()
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for upd in updates:
                try:
                    offset = upd["update_id"] + 1
                    # ── Inline button callback ────────────────────────
                    cb = upd.get("callback_query")
                    if cb:
                        cb_id   = cb["id"]
                        cb_data = cb.get("data", "")
                        cb_chat = cb.get("message", {}).get("chat", {}).get("id")
                        if cb_chat and cb_data:
                            print(f"[{now_vn().strftime('%H:%M:%S')}] callback {cb_chat}: {cb_data}")
                            _CMD_EXEC.submit(handle_callback, cb_id, cb_chat, cb_data)
                        continue
                    # ── Tin nhắn thường ───────────────────────────────
                    msg     = upd.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text    = msg.get("text", "")
                    if chat_id and text.startswith("/"):
                        print(f"[{now_vn().strftime('%H:%M:%S')}] {chat_id}: {text}")
                        _CMD_EXEC.submit(handle, chat_id, text)
                except Exception as e:
                    print(f"[main] Lỗi xử lý update: {e}")
        except KeyboardInterrupt:
            print("Bot dừng.")
            break
        except Exception as e:
            _ec = getattr(main, '_ec', 0) + 1; main._ec = _ec
            wait = min(5 * _ec, 60)
            print(f"[main] Lỗi (lần {_ec}): {e} — thử lại sau {wait}s...")
            time.sleep(wait)
        else:
            main._ec = 0  # reset khi lấy update thành công
if __name__ == "__main__":
    main()
