# -*- coding: utf-8 -*-
"""
login.py — Mở browser, tự điền user/pass vào iframe HoYoLAB, chờ captcha.
Chạy độc lập hoặc qua subprocess từ bot.py.
Hỗ trợ: Windows 11, Linux (có X11 hoặc Xvfb qua systemd).
"""
import sys
import os
import subprocess
import time
import config

USER = config.HOYOLAB_USER
PASS = config.HOYOLAB_PASS

IS_WINDOWS = sys.platform == "win32"

# Nếu bot.py truyền HEADLESS=1 → chạy hoàn toàn không cần X server
HEADLESS_MODE = os.environ.get("HEADLESS", "0") == "1"

# ── Phát hiện và khởi động display (chỉ Linux, chỉ khi không headless) ──────
_xvfb_proc = None
_vnc_proc   = None

def _ensure_display():
    """Đảm bảo có DISPLAY (chỉ cần trên Linux, chỉ khi HEADLESS_MODE=False).
    Trả về True nếu đã tự tạo Xvfb (cần dọn dẹp sau)."""
    global _xvfb_proc, _vnc_proc

    if IS_WINDOWS or HEADLESS_MODE:
        return False

    # Đã có display thật → dùng luôn
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        print("[login] Dùng display hiện có:", os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"), flush=True)
        return False

    # Thử dùng :0 của user đang login
    os.environ["DISPLAY"] = ":0"
    try:
        result = subprocess.run(["xdpyinfo", "-display", ":0"],
                                capture_output=True, timeout=3)
        if result.returncode == 0:
            print("[login] Dùng DISPLAY=:0 (X11 user session)", flush=True)
            return False
    except Exception:
        pass

    # Không có X11 → khởi động Xvfb trên :99
    print("[login] Không có X11 display — khởi động Xvfb trên :99", flush=True)
    try:
        _xvfb_proc = subprocess.Popen(
            ["Xvfb", ":99", "-screen", "0", "1920x1080x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(1.5)
        os.environ["DISPLAY"] = ":99"
        print("[login] Xvfb khởi động OK — DISPLAY=:99", flush=True)
    except FileNotFoundError:
        print("[login] ❌ Xvfb không được cài! Chạy: sudo apt install xvfb", flush=True)
        sys.exit(1)

    # Khởi động x11vnc để xem từ xa (port 5900)
    try:
        _vnc_proc = subprocess.Popen(
            ["x11vnc", "-display", ":99", "-nopw", "-forever", "-quiet",
             "-rfbport", "5900"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print("[login] x11vnc đang chạy tại port 5900 — kết nối VNC để thấy browser", flush=True)
    except FileNotFoundError:
        print("[login] ⚠️  x11vnc không có — không xem được qua VNC", flush=True)
        print("[login]    Cài bằng: sudo apt install x11vnc", flush=True)

    return True  # dùng Xvfb

_used_xvfb = _ensure_display()

if HEADLESS_MODE:
    print("[login] Chạy chế độ HEADLESS (không cần X server)", flush=True)

from playwright.sync_api import sync_playwright

# ── Chọn User-Agent theo nền tảng ───────────────────────────
if IS_WINDOWS:
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
else:
    _UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

with sync_playwright() as p:
    _launch_args = ["--disable-blink-features=AutomationControlled",
                    "--no-sandbox", "--disable-dev-shm-usage"]
    
    # ── Tối ưu cho Arch Linux (Wayland native) ────────────────────────
    if not IS_WINDOWS and os.environ.get("WAYLAND_DISPLAY"):
        _launch_args.extend(["--ozone-platform-hint=auto", "--enable-wayland-ime"])

    if not HEADLESS_MODE:
        _launch_args.append("--start-maximized")

    browser = p.chromium.launch(
        headless=HEADLESS_MODE,
        args=_launch_args
    )
    _viewport = {"width": 1920, "height": 1080} if HEADLESS_MODE else None
    context = browser.new_context(
        no_viewport=not HEADLESS_MODE,
        viewport=_viewport,
        user_agent=_UA
    )

    context.add_init_script(f"""
        const _orig = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');

        function smartFill(input, value) {{
            _orig.set.call(input, value);
            ['input', 'change', 'keydown', 'keyup', 'keypress'].forEach(evt =>
                input.dispatchEvent(new Event(evt, {{ bubbles: true }}))
            );
        }}

        document.addEventListener('focusin', (e) => {{
            const el = e.target;
            if (el.tagName !== 'INPUT') return;
            const ph  = (el.placeholder || '').toLowerCase();
            const typ = (el.type || '').toLowerCase();
            const nm  = (el.name  || '').toLowerCase();

            if (ph.includes('username') || ph.includes('email') || nm === 'username') {{
                setTimeout(() => smartFill(el, '{USER}'), 150);
            }}
            if (ph.includes('password') || typ === 'password' || nm === 'password') {{
                setTimeout(() => smartFill(el, '{PASS}'), 150);
            }}
        }}, true);
    """)

    page = context.new_page()
    page.goto("https://www.hoyolab.com/home", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    clicked = False

    try:
        btn = page.locator('button:has-text("Log In"), a:has-text("Log In"), '
                           '[class*="login"]:has-text("Log In")').first
        btn.click(timeout=5000)
        page.wait_for_timeout(1500)
        clicked = True
        print("[login] Click Log In button OK", flush=True)
    except Exception:
        pass

    if not clicked:
        try:
            page.evaluate("""
                const els = [...document.querySelectorAll('*')];
                const btn = els.find(el =>
                    el.innerText && el.innerText.trim() === 'Log In' &&
                    el.offsetParent !== null
                );
                if (btn) btn.click();
            """)
            page.wait_for_timeout(1500)
            clicked = True
            print("[login] JS click Log In OK", flush=True)
        except Exception:
            pass

    if not clicked:
        print("[login] Khong tu click duoc - hay tu click nut Log In tren browser", flush=True)

    try:
        page.wait_for_selector("#hyv-account-frame, iframe[src*='account.hoyolab']",
                                timeout=15000)
        page.wait_for_timeout(1000)
        print("[login] iframe login da xuat hien", flush=True)
    except Exception:
        print("[login] Khong tim thay iframe - co the trang dang load", flush=True)

    print("", flush=True)
    print("[login] San sang! Click vao o Username roi Password de tu dien.", flush=True)
    print("[login] Giai Captcha va nhan Log In.", flush=True)
    print("[login] Bot se TU DONG luu cookie khi phat hien dang nhap thanh cong.", flush=True)
    sys.stdout.flush()

    # ── Tự động phát hiện đăng nhập qua cookie ──────────────────────────────
    # Poll mỗi 2 giây tối đa 10 phút — khi thấy ltoken_v2 + ltuid_v2 là OK
    POLL_INTERVAL = 2
    MAX_WAIT_SEC  = 600   # 10 phút
    saved = False
    for _ in range(MAX_WAIT_SEC // POLL_INTERVAL):
        try:
            clist = context.cookies()
            cmap  = {c["name"]: c["value"] for c in clist}
            if "ltoken_v2" in cmap and "ltuid_v2" in cmap:
                context.storage_state(path=config.HOYOLAB_FILE)
                print(f"[login] LOGIN_SUCCESS Da luu cookie vao {config.HOYOLAB_FILE}", flush=True)
                saved = True
                break
        except Exception as e:
            err_lower = str(e).lower()
            # Playwright báo browser/context bị đóng → thoát ngay, đừng chờ tiếp
            if any(k in err_lower for k in ("closed", "disconnected", "crashed",
                                             "target page", "browser has been")):
                print("[login] BROWSER_CLOSED Browser bi dong truoc khi dang nhap.", flush=True)
                saved = True   # đánh dấu "đã xử lý" để không in TIMEOUT
                break
            print(f"[login] poll error: {e}", flush=True)
        time.sleep(POLL_INTERVAL)

    if not saved:
        print("[login] TIMEOUT Het 10 phut, khong phat hien dang nhap thanh cong.", flush=True)

    browser.close()

# Dọn dẹp Xvfb / VNC nếu đã tự tạo
if _used_xvfb:
    if _vnc_proc:
        try: _vnc_proc.terminate()
        except: pass
    if _xvfb_proc:
        try: _xvfb_proc.terminate()
        except: pass
