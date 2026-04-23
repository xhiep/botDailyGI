from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from botdailygi.config import ROOT_DIR as APP_ROOT  # noqa: E402
from botdailygi.runtime.paths import COOKIES_DIR, ensure_runtime_dirs  # noqa: E402


USER = os.getenv("HOYOLAB_USER", "").strip()
PASSWORD = os.getenv("HOYOLAB_PASS", "").strip()
IS_WINDOWS = sys.platform == "win32"
HEADLESS_MODE = os.getenv("HEADLESS", "0") == "1"

DEFAULT_OUTPUT = COOKIES_DIR / "pc-login-export.json"
OUTPUT_PATH = Path(os.getenv("COOKIE_OUTPUT_FILE", "")).expanduser() if os.getenv("COOKIE_OUTPUT_FILE") else DEFAULT_OUTPUT
if not OUTPUT_PATH.is_absolute():
    OUTPUT_PATH = (Path.cwd() / OUTPUT_PATH).resolve()

_xvfb_proc = None
_vnc_proc = None


def _terminate_proc(proc):
    if not proc:
        return
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
        return
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def _cleanup_display():
    global _xvfb_proc, _vnc_proc
    _terminate_proc(_vnc_proc)
    _terminate_proc(_xvfb_proc)
    _vnc_proc = None
    _xvfb_proc = None


def _ensure_display():
    global _xvfb_proc, _vnc_proc
    if IS_WINDOWS or HEADLESS_MODE:
        return
    if os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"):
        print("[login] Using existing display:", os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"), flush=True)
        return
    os.environ["DISPLAY"] = ":0"
    try:
        result = subprocess.run(["xdpyinfo", "-display", ":0"], capture_output=True, timeout=3)
        if result.returncode == 0:
            print("[login] Using DISPLAY=:0", flush=True)
            return
    except Exception:
        pass
    print("[login] No X11 display found - starting Xvfb on :99", flush=True)
    try:
        _xvfb_proc = subprocess.Popen(
            ["Xvfb", ":99", "-screen", "0", "1920x1080x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.5)
        os.environ["DISPLAY"] = ":99"
        print("[login] Xvfb ready on DISPLAY=:99", flush=True)
    except FileNotFoundError as exc:
        print("[login] LOGIN_FATAL Xvfb is not installed", flush=True)
        raise exc
    try:
        _vnc_proc = subprocess.Popen(
            ["x11vnc", "-display", ":99", "-nopw", "-forever", "-quiet", "-rfbport", "5900"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("[login] x11vnc listening on port 5900", flush=True)
    except FileNotFoundError:
        print("[login] x11vnc not installed - skipping VNC bridge", flush=True)


def _launch_args():
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ]
    if not IS_WINDOWS and os.getenv("WAYLAND_DISPLAY"):
        args.extend(["--ozone-platform-hint=auto", "--enable-wayland-ime"])
    if not HEADLESS_MODE:
        args.append("--start-maximized")
    return args


def _build_user_agent():
    if IS_WINDOWS:
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    return (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )


def _install_autofill_script(context):
    rules = []
    if USER:
        rules.append(
            f"""
            if (ph.includes('username') || ph.includes('email') || nm === 'username') {{
                setTimeout(() => smartFill(el, {json.dumps(USER)}), 150);
            }}
            """
        )
    if PASSWORD:
        rules.append(
            f"""
            if (ph.includes('password') || typ === 'password' || nm === 'password') {{
                setTimeout(() => smartFill(el, {json.dumps(PASSWORD)}), 150);
            }}
            """
        )
    if not rules:
        print("[login] No HOYOLAB_USER/PASS set - enter credentials manually", flush=True)
        return
    context.add_init_script(
        """
        const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
        function smartFill(input, value) {
            descriptor.set.call(input, value);
            ['input', 'change', 'keydown', 'keyup', 'keypress'].forEach((evt) =>
                input.dispatchEvent(new Event(evt, { bubbles: true }))
            );
        }
        document.addEventListener('focusin', (e) => {
            const el = e.target;
            if (!el || el.tagName !== 'INPUT') return;
            const ph = (el.placeholder || '').toLowerCase();
            const typ = (el.type || '').toLowerCase();
            const nm = (el.name || '').toLowerCase();
        """
        + "\n".join(rules)
        + """
        }, true);
        """
    )


def _click_login(page):
    try:
        button = page.locator('button:has-text("Log In"), a:has-text("Log In"), [class*="login"]:has-text("Log In")').first
        button.click(timeout=5000)
        page.wait_for_timeout(1500)
        print("[login] Click Log In button OK", flush=True)
        return True
    except Exception:
        pass
    try:
        page.evaluate(
            """
            const els = [...document.querySelectorAll('*')];
            const btn = els.find((el) => el.innerText && el.innerText.trim() === 'Log In' && el.offsetParent !== null);
            if (btn) btn.click();
            """
        )
        page.wait_for_timeout(1500)
        print("[login] JS click Log In OK", flush=True)
        return True
    except Exception:
        return False


def _wait_login_iframe(page):
    try:
        page.wait_for_selector("#hyv-account-frame, iframe[src*='account.hoyolab']", timeout=15000)
        page.wait_for_timeout(1000)
        print("[login] Login iframe is ready", flush=True)
    except Exception:
        print("[login] Login iframe not detected yet", flush=True)


def _save_storage_state_atomic(context, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".login_", suffix=".json", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        context.storage_state(path=str(tmp_path))
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _poll_login_success(context):
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        try:
            cookies = {cookie["name"]: cookie["value"] for cookie in context.cookies()}
            if cookies.get("ltoken_v2") and cookies.get("ltuid_v2"):
                _save_storage_state_atomic(context, OUTPUT_PATH)
                print(f"[login] LOGIN_SUCCESS Saved cookie to {OUTPUT_PATH}", flush=True)
                return
        except Exception as exc:
            text = str(exc).lower()
            if any(token in text for token in ("closed", "disconnected", "crashed", "target page", "browser has been")):
                print("[login] BROWSER_CLOSED Browser closed before login completed", flush=True)
                return
            print(f"[login] poll error: {exc}", flush=True)
        time.sleep(5)
    print("[login] TIMEOUT No successful login detected within 10 minutes", flush=True)


def main() -> int:
    browser = None
    context = None
    ensure_runtime_dirs()
    print(f"[login] Repo root: {APP_ROOT}", flush=True)
    print(f"[login] Cookie output: {OUTPUT_PATH}", flush=True)
    try:
        from playwright.sync_api import sync_playwright

        _ensure_display()
        if HEADLESS_MODE:
            print("[login] Running in HEADLESS mode", flush=True)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=HEADLESS_MODE, args=_launch_args())
            viewport = {"width": 1920, "height": 1080} if HEADLESS_MODE else None
            context = browser.new_context(
                no_viewport=not HEADLESS_MODE,
                viewport=viewport,
                user_agent=_build_user_agent(),
            )
            _install_autofill_script(context)
            page = context.new_page()
            page.goto("https://www.hoyolab.com/home", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            if not _click_login(page):
                print("[login] Could not auto-click Log In - click it manually in the browser", flush=True)
            _wait_login_iframe(page)
            print("", flush=True)
            print("[login] Ready. Focus Username then Password to auto-fill if configured.", flush=True)
            print("[login] Solve captcha and click Log In.", flush=True)
            print("[login] The tool will save Playwright storage-state automatically on successful login.", flush=True)
            _poll_login_success(context)
        return 0
    except Exception as exc:
        print(f"[login] LOGIN_FATAL {exc}", flush=True)
        traceback.print_exc()
        return 1
    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        _cleanup_display()


if __name__ == "__main__":
    sys.exit(main())
