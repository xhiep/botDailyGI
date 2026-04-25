# Bug Testing Report

## Testing Method
Static code analysis and review of all command files, UI constants, and i18n files.

## Bugs Found

### 1. Hardcoded Vietnamese strings in status.py (Lines 148, 154, 156, 162-167, 177, 182)
**Severity**: High - Breaks i18n
**Location**: `botdailygi/commands/status.py`
**Issue**: Multiple hardcoded Vietnamese strings that should use translation keys:
- Line 148: "Có background thread đã dừng."
- Line 154: "rảnh"
- Line 156: "lệnh chờ"
- Lines 162-167: Network state messages ("đang khởi tạo", "ổn định", "mất DNS", "lỗi polling", "không rõ")
- Line 177, 182: "bật", "tắt"

**Fix**: Add translation keys to catalog.py and use t() function

### 2. Hardcoded strings in checkin.py (Line 50)
**Severity**: Medium
**Location**: `botdailygi/commands/checkin.py:50`
**Issue**: "Check-in" header is hardcoded
**Fix**: Use translation key

### 3. Missing translation keys in catalog.py
**Severity**: High
**Issue**: Need to add missing keys for status.py hardcoded strings
**Status**: ✓ FIXED - Added all missing translation keys

### 4. Hardcoded Vietnamese in background/jobs.py (Line 43, 298)
**Severity**: High - Breaks i18n
**Location**: `botdailygi/background/jobs.py`
**Issue**: 
- Line 43: "Lỗi hiển thị kết quả"
- Line 298: "rảnh"
**Fix**: Add translation keys and use t() function

### 5. Hardcoded Vietnamese in telegram.py (Line 112)
**Severity**: High - Breaks i18n
**Location**: `botdailygi/clients/telegram.py:112`
**Issue**: "(Đã cắt bớt)" - truncation message
**Fix**: Add translation key

### 6. Hardcoded Vietnamese in status.py (Line 183, 189)
**Severity**: Medium
**Location**: `botdailygi/commands/status.py`
**Issue**: 
- Line 183: "ngưỡng=" 
- Line 189: "bot.log" label
**Fix**: Add translation keys

### 7. Hardcoded Vietnamese in services/checkin.py (Line 33)
**Severity**: High - Breaks i18n
**Location**: `botdailygi/services/checkin.py:33`
**Issue**: "đã điểm danh" in check logic
**Fix**: Should use API response codes, not string matching

### 8. Hardcoded Vietnamese in services/codes.py (Lines 36, 94-105)
**Severity**: High - Breaks i18n
**Location**: `botdailygi/services/codes.py`
**Issue**: Multiple Vietnamese strings in error detection:
- Line 36: "đã dùng"
- Line 94: "hết hạn"
- Line 96: "không hợp lệ"
- Lines 103-105: "đã được sử dụng", "đã dùng", "đã đổi"
**Fix**: Should use API retcode, not string matching

## Fixed Issues

### ✓ 1. status.py hardcoded strings - FIXED
- Added translation keys: status.thread_dead, status.locks_idle, status.cmd_pending, status.net_starting, status.net_ok, status.net_dns_fail, status.net_poll_fail, status.net_unknown, status.cfg_enabled, status.cfg_disabled
- Updated status.py to use t() function

### ✓ 2. checkin.py hardcoded header - FIXED
- Added translation key: checkin.header
- Updated checkin.py to use t() function

