# -*- coding: utf-8 -*-
"""
login.py — Mở browser, tự điền user/pass vào iframe HoYoLAB, chờ captcha.
Chạy độc lập hoặc qua subprocess từ bot.py.
"""
import sys
import io

# Fix encoding cho Windows (cp1252 không hỗ trợ emoji/tiếng Việt)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import config

USER = config.HOYOLAB_USER
PASS = config.HOYOLAB_PASS

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
    )
    context = browser.new_context(no_viewport=True)

    # Script inject tự điền — hook cả iframe
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

    # ── Tìm và click nút "Log In" ─────────────────────────────────────────────
    clicked = False

    # Cách 1: click trực tiếp (nếu không bị iframe chặn)
    try:
        btn = page.locator('button:has-text("Log In"), a:has-text("Log In"), '
                           '[class*="login"]:has-text("Log In")').first
        btn.click(timeout=5000)
        page.wait_for_timeout(1500)
        clicked = True
        print("[login] Click Log In button OK", flush=True)
    except Exception:
        pass

    # Cách 2: dùng JavaScript click (bypass iframe intercept)
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

    # ── Chờ iframe login xuất hiện rồi inject vào bên trong ──────────────────
    try:
        # Chờ iframe account xuất hiện
        page.wait_for_selector("#hyv-account-frame, iframe[src*='account.hoyolab']",
                                timeout=15000)
        page.wait_for_timeout(1000)
        print("[login] iframe login da xuat hien", flush=True)
    except Exception:
        print("[login] Khong tim thay iframe - co the trang dang load", flush=True)

    print("", flush=True)
    print("[login] San sang! Click vao o Username roi Password de tu dien.", flush=True)
    print("[login] Giai Captcha va nhan Log In.", flush=True)
    print("[login] Sau khi dang nhap xong, nhan Enter de luu cookie...", flush=True)
    sys.stdout.flush()

    # Chờ Enter (từ terminal hoặc stdin của bot.py)
    try:
        input()
    except EOFError:
        # Khi chạy qua subprocess với stdin pipe, EOFError = nhận được \n
        pass

    context.storage_state(path=config.HOYOLAB_FILE)
    browser.close()
    print(f"[login] Da luu cookie vao {config.HOYOLAB_FILE}", flush=True)