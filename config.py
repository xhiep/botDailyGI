import os

def _load_env_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ[k] = v
    except Exception:
        pass

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_load_env_file(_env_path)

HOYOLAB_FILE = os.getenv("HOYOLAB_FILE", "hoyolab.json")

# Token bot Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Chat ID của bạn
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Tài khoản HoYoLAB (dùng để tự điền vào form đăng nhập)
HOYOLAB_USER = os.getenv("HOYOLAB_USER", "")
HOYOLAB_PASS = os.getenv("HOYOLAB_PASS", "")
