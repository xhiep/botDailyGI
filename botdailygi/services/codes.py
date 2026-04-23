from __future__ import annotations

import random
import threading
import time

from botdailygi.runtime.logging import log
from botdailygi.runtime.paths import CODES_BLACKLIST_FILE, CODES_FILE
from botdailygi.runtime.state import now_vn
from botdailygi.services.hoyolab import redeem_one


HOYOLAB_LANG = {"vi": "vi-vn", "en": "en-us"}
BLACKLIST_MAX_ENTRIES = 500

_blacklist_cache: dict[str, str] = {}
_blacklist_mtime = 0.0
_blacklist_lock = threading.Lock()
_blacklist_write_lock = threading.Lock()


def invalidate_blacklist_cache() -> None:
    global _blacklist_cache, _blacklist_mtime
    with _blacklist_lock:
        _blacklist_cache = {}
        _blacklist_mtime = 0.0


def _is_transient_reason(reason: str) -> bool:
    return (reason or "").strip().lower() in {
        "code.reason.used",
        "used",
        "already used",
        "already redeemed",
        "da dung",
        "đã dùng",
    }


def load_blacklist() -> dict[str, str]:
    global _blacklist_cache, _blacklist_mtime
    if not CODES_BLACKLIST_FILE.exists():
        return {}
    with _blacklist_lock:
        try:
            mtime = CODES_BLACKLIST_FILE.stat().st_mtime
        except OSError:
            return {}
        if _blacklist_cache and mtime == _blacklist_mtime:
            return dict(_blacklist_cache)
        blacklist = {}
        skipped = 0
        try:
            for line in CODES_BLACKLIST_FILE.read_text(encoding="utf-8").splitlines():
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                parts = raw.split("|", 2)
                code = parts[0].strip().upper()
                reason = parts[1].strip() if len(parts) > 1 else "blacklisted"
                if not code:
                    continue
                if _is_transient_reason(reason):
                    skipped += 1
                    continue
                blacklist[code] = reason
        except Exception as exc:
            log.warning(f"[blacklist] Cannot read {CODES_BLACKLIST_FILE.name}: {exc}")
        _blacklist_cache = blacklist
        _blacklist_mtime = mtime
        if skipped:
            log.info(f"[blacklist] Skipped {skipped} legacy transient entries")
        return dict(blacklist)


def add_to_blacklist(code: str, reason: str) -> None:
    if _is_transient_reason(reason):
        return
    timestamp = now_vn().strftime("%Y-%m-%d %H:%M")
    try:
        with _blacklist_write_lock:
            with CODES_BLACKLIST_FILE.open("a", encoding="utf-8") as handle:
                handle.write(f"{code.upper()} | {reason} | {timestamp}\n")
            lines = CODES_BLACKLIST_FILE.read_text(encoding="utf-8").splitlines(True)
            if len(lines) > BLACKLIST_MAX_ENTRIES:
                CODES_BLACKLIST_FILE.write_text("".join(lines[-BLACKLIST_MAX_ENTRIES:]), encoding="utf-8")
        invalidate_blacklist_cache()
    except Exception as exc:
        log.warning(f"[blacklist] Cannot write {CODES_BLACKLIST_FILE.name}: {exc}")


def should_blacklist(message: str, retcode: int) -> tuple[bool, str]:
    text = (message or "").lower()
    if retcode in (-2017, -2018) or "expired" in text or "hết hạn" in text:
        return True, "code.reason.expired"
    if retcode in (-2001, -2003, -2004, -2014) or "invalid" in text or "not found" in text or "không hợp lệ" in text:
        return True, "code.reason.invalid"
    if (
        retcode == -2016
        or "already used" in text
        or "already been used" in text
        or "already redeemed" in text
        or "đã được sử dụng" in text
        or "đã dùng" in text
        or "đã đổi" in text
    ):
        return False, "code.reason.used"
    return False, ""


def load_codes_from_file() -> list[str]:
    if not CODES_FILE.exists():
        return []
    blacklist = load_blacklist()
    results: list[str] = []
    try:
        for line in CODES_FILE.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            code = raw.upper()
            if code not in blacklist:
                results.append(code)
    except Exception as exc:
        log.warning(f"[codes] Cannot read {CODES_FILE.name}: {exc}")
    return results


def redeem_batch(*, codes: list[str], cookies: dict, uid, region, lang_code: str) -> dict:
    blacklist = load_blacklist()
    pending = [code for code in codes if code not in blacklist]
    skipped = [code for code in codes if code in blacklist]
    results = {"ok": [], "fail_bl": [], "fail_other": [], "skipped": skipped}
    for index, code in enumerate(pending):
        ok, message, retcode = redeem_one(cookies, uid, region, code, lang_code)
        if ok:
            results["ok"].append(code)
        else:
            should_add, reason_key = should_blacklist(message, retcode)
            if should_add:
                add_to_blacklist(code, reason_key)
                results["fail_bl"].append((code, reason_key, message))
            else:
                results["fail_other"].append((code, message))
        if index < len(pending) - 1:
            time.sleep(random.uniform(0.8, 1.5))
    return results
