import json, os, re

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_LANGS_FILE = os.path.join(_BASE_DIR, "user_langs.json")
_user_langs = {}

def load_user_langs():
    global _user_langs
    if os.path.exists(USER_LANGS_FILE):
        try:
            with open(USER_LANGS_FILE, "r", encoding="utf-8") as f:
                _user_langs = json.load(f)
        except Exception:
            pass

def get_lang(chat_id):
    return _user_langs.get(str(chat_id), "vi")  # default to vi

def set_lang(chat_id, lang):
    _user_langs[str(chat_id)] = lang
    try:
        with open(USER_LANGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_user_langs, f, ensure_ascii=False)
    except Exception:
        pass


VI_TO_EN = {
    # System / General
    "Lệnh không nhận ra. Gõ": "Unknown command. Type",
    "Không có quyền": "Unauthorized",
    "Bot đã khởi động!": "Bot has started!",
    "Bot vẫn đang chạy": "Bot is still running",
    "Uptime:": "Uptime:",
    "Chưa đăng nhập — dùng /login": "Not logged in — use /login",
    "để đăng nhập lại": "to login again",
    "để thử thủ công": "to try manually",
    "Dùng /login để bắt đầu.": "Use /login to start.",
    "Lỗi:": "Error:",
    "Lỗi kết nối:": "Connection Error:",
    "Thành công": "Success",
    "Thất bại:": "Failed:",
    "Hợp lệ": "Valid",
    "Hết hạn": "Expired",
    "ngày": "days", "giờ": "hours", "phút": "mins", "giây": "secs",

    # Commands List (/help)
    "📋 DANH SÁCH LỆNH": "📋 COMMAND LIST",
    "🎮 GENSHIN": "🎮 GENSHIN",
    "— trạng thái bot": "— bot status & schedules",
    "— UID và nickname": "— UID and nickname",
    "— điểm danh ngay": "— check-in now",
    "— danh sách nhân vật": "— character list",
    "— nhựa + expedition": "— resin + expedition & daily",
    "— báo khi nhựa": "— alert when resin reaches N",
    "— tắt thông báo nhựa": "— disable resin alert",
    "— đổi 1 gift code": "— redeem 1 gift code",
    "— đổi toàn bộ": "— redeem all codes in codes.txt",
    "— tìm code từ": "— auto-hunt codes from 20+ sources",
    "— xem code bị": "— view blacklisted codes",
    "— xóa toàn bộ": "— clear the entirely blacklist",
    "💻 MÁY TÍNH": "💻 COMPUTER",
    "— chụp màn hình": "— snap PC screen",
    "⚡ NGUỒN ĐIỆN": "⚡ POWER",
    "— tắt máy (xác nhận bằng nút bấm)": "— PC shutdown (with confirm button)",
    "— restart máy (xác nhận bằng nút bấm)": "— PC restart (with confirm button)",
    "— huỷ lệnh": "— cancel shutdown/restart",
    "🔐 TÀI KHOẢN": "🔐 ACCOUNT",
    "— mở trình duyệt": "— open browser to login",
    "— lưu cookie": "— manually save cookie",
    "— huỷ phiên": "— cancel pending login session",
    "— danh sách này": "— show this list",
    "ℹ️ Tính năng tự động:": "ℹ️ Automated Features:",
    "Điểm danh 09:00": "Check-in at 09:00 & 21:00",
    "Cảnh báo nhựa 2 mức": "Smart Resin alerts (Threshold & Capping)",
    "Heartbeat mỗi 12h": "Heartbeat ping every 12 hours",

    # Power operations
    "Đã huỷ lệnh tắt/restart máy.": "Cancelled shutdown/restart command.",
    "Đang tắt máy": "Shutting down",
    "Đang restart": "Restarting",
    "Bạn có chắc muốn": "Are you sure you want to",
    "TẮT MÁY": "SHUT DOWN",
    "RESTART MÁY": "RESTART",
    "sau 60 giây": "in 60 seconds",
    "Tắt máy": "Shutdown",
    "✅ Xác nhận": "✅ Confirm",
    "❌ Huỷ": "❌ Cancel",

    # Status & Check-in
    "Cookie:": "Cookie:",
    "📅 Điểm danh:": "📅 Check-in:",
    "✅ Đã điểm": "✅ Checked in",
    "❌ Chưa điểm": "❌ Not Checked",
    "Điểm danh thành công": "Check-in successful",
    "Điểm danh thất bại": "Check-in failed",
    "Hôm nay đã điểm danh rồi": "Already checked in today",
    "Đang có lệnh": "Command is pending or running",
    
    # Resin
    "⚗️ Nhựa:": "⚗️ Resin:",
    "Đang lấy thông tin nhựa": "Fetching resin info",
    "đầy lúc": "full at",
    "Đầy sau  :": "Full in  :",
    "đầy hoàn toàn": "fully recovered",
    "Đã đầy ✅": "Fully refilled ✅",
    "Nhựa hiện tại:": "Current Resin:",
    "Ngưỡng:": "Threshold:",
    "Cần thêm:": "Needs:",
    "Sẽ báo lúc:": "Alert at:",
    "Đã đặt ngưỡng thông báo:": "Set notification threshold to:",
    "Đã bật thông báo": "Enabled alerts",
    "Đã tắt thông báo": "Disabled alerts",
    "báo khi nhựa": "alert when resin",
    "Sẵn sàng!": "Ready!",
    "Chưa sẵn sàng": "Not ready",
    "Đã nhận": "Claimed",
    "Chưa nhận": "Not claimed",
    "Thưởng   :": "Rewards :",
    "Nhựa": "Resin",
    "NHỰA ĐÃ ĐẠT NGƯỠNG": "RESIN REACHED THRESHOLD",
    "NHỰA SẮP TRÀN!": "RESIN ALMOST CAPPED!",
    "Còn": "Remaining",
    "nhựa nữa là tràn!": "resin until capped!",
    "Vào farm NGAY kẻo mất nhựa!": "Farm NOW to avoid capping!",
    "Vào farm nhựa kẻo tràn!": "Farm resin before it caps!",

    # Fetch Codes / Redeem
    "Tìm được": "Found",
    "nguồn": "sources",
    "MỚI": "NEW",
    "Không tìm thấy code nào": "No active codes found",
    "Đang tìm code": "Hunting codes",
    "Đang đổi": "Redeeming",
    "đổi thành công": "redeemed successfully",
    "Đã blacklist": "Blacklisted",
    "xóa blacklist": "cleared blacklist",
    "Blacklist trống": "Blacklist is empty",
    "Đã bỏ qua": "Skipped",

    # Characters
    "nhân vật": "characters",
    "Không có nhân vật": "No characters",
    "Tổng:": "Total:",

    # Screenshot
    "Chụp màn hình thất bại": "Screenshot failed",
    "Đang chụp màn hình...": "Snapping screenshot...",

    # Login
    "Đã hủy phiên đăng nhập.": "Login session canceled.",
    "Đăng nhập thành công!": "Login successful!",
    "Trình duyệt đã mở!": "Browser opened!",
    "Đang mở trình duyệt": "Opening browser...",
    "Click ô": "Click",
    "tự điền": "auto-fills",
    "Giải Captcha": "Solve Captcha",
    "nhấn Log In": "click Log In",
    "Bot sẽ TỰ ĐỘNG lưu cookie": "Bot will AUTO save cookie",
    "Quá 10 phút": "Over 10 minutes",
    "Phiên đăng nhập đã kết thúc": "Login session ended",
    "Không thấy browser": "Browser not found",
    "Đang có phiên đăng nhập": "Login session pending",
    
    # Time/Other short terms
    "Tắt": "Off",
    "Bật": "On",
}

def translate_str(text: str, lang: str) -> str:
    if lang == "vi":
        return text
    
    # We apply specific exact regex replacements or simple replace
    # Replacing longer strings first is safer, so let's sort keys by length descending
    keys = sorted(VI_TO_EN.keys(), key=len, reverse=True)
    for k in keys:
        text = text.replace(k, VI_TO_EN[k])
    
    return text

def t_send(chat_id, text, original_send_func):
    """Wrapper for send()"""
    lang = get_lang(chat_id)
    translated = translate_str(str(text), lang)
    return original_send_func(chat_id, translated)

def t_send_with_buttons(chat_id, text, buttons, original_func):
    """Wrapper for send_with_buttons()"""
    lang = get_lang(chat_id)
    translated_text = translate_str(str(text), lang)
    
    # Translate button texts too
    translated_buttons = []
    for row in buttons:
        new_row = []
        for btn in row:
            new_btn = btn.copy()
            if "text" in new_btn:
                new_btn["text"] = translate_str(new_btn["text"], lang)
            new_row.append(new_btn)
        translated_buttons.append(new_row)
        
    return original_func(chat_id, translated_text, translated_buttons)

def t_answer_callback(callback_id, text, original_func, chat_id=None):
    if not text:
        return original_func(callback_id, text)
    # Since we might not have chat_id in answer_callback easily without storing it,
    # if chat_id is provided logic is simple.
    lang = get_lang(chat_id) if chat_id else "vi" # fallback
    translated_text = translate_str(str(text), lang)
    return original_func(callback_id, translated_text)

# load db on import
load_user_langs()
