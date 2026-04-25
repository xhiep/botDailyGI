# Bugs Found - 2026-04-25

## Bug #1: /characters command - MESSAGE_TOO_LONG error ✅ FIXED

**Severity:** Medium
**Command:** `/characters`
**Error:** Telegram API returns 400 Bad Request: MESSAGE_TOO_LONG

**Log output:**
```
2026-04-25 23:25:44 [WARNING] [editMessageText] Telegram reject (chat=7928031598) code=400 desc=Bad Request: MESSAGE_TOO_LONG
2026-04-25 23:25:44 [WARNING] [editMessageText.fallback] Telegram reject (chat=7928031598) code=400 desc=Bad Request: MESSAGE_TOO_LONG
```

**Root Cause:**
The `edit_text()` function in `botdailygi/clients/telegram.py` didn't have length checking like `send_text()` does. When editing messages with character lists from multiple accounts, the combined text exceeded Telegram's 4096 character limit.

**Fix Applied:**
Added length truncation to `edit_text()` function at line 108-112:
- Truncates text to 4000 characters if too long
- Adds "⚠️ (Đã cắt bớt)" indicator when truncated
- Prevents MESSAGE_TOO_LONG errors

**File:** `botdailygi/clients/telegram.py:108-112`

**Status:** ✅ Fixed and verified

---

## Bug #2: Account info cache not cleared when account removed ✅ FIXED

**Severity:** Low
**File:** `botdailygi/background/jobs.py:120-122`
**Error:** Stale cache data when accounts are removed

**Root Cause:**
The `account_info_cache` stores account info with TTL of 3600s. When an account is removed, only `resin_state_cache` was cleared but not `account_info_cache`. This could cause stale data if an account is removed and re-added with different credentials within the cache TTL window.

**Fix Applied:**
Added cache cleanup for `account_info_cache` at lines 120-122:
```python
for cached_name in list(account_info_cache):
    if cached_name not in live_accounts:
        account_info_cache.pop(cached_name, None)
```

**Status:** ✅ Fixed and verified

---

## Bug #3: No error handling in _render_checkin_lines ✅ FIXED

**Severity:** Low
**File:** `botdailygi/background/jobs.py:33-43`
**Error:** Checkin notifications could fail if any result is malformed

**Root Cause:**
The function called `_render_checkin_result` without error handling. If any result item was malformed or the render function raised an exception, the entire checkin notification would fail.

**Fix Applied:**
Added try-except around each render call at lines 36-42:
```python
lines = []
for item in results:
    try:
        lines.append(_render_checkin_result(TELEGRAM_CHAT_ID, item))
    except Exception as exc:
        log.warning(f"[checkin] Failed to render result for {item.get('name', '?')}: {exc}")
        lines.append(f"⚠️ {item.get('name', '?')}: Lỗi hiển thị kết quả")
return "\n".join(lines)
```

**Status:** ✅ Fixed and verified

---

## Summary

**Total bugs found:** 3
**Total bugs fixed:** 3
**Status:** All bugs resolved ✅

