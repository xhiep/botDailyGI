# UI Issues Found - 2026-04-25

## Phân tích theo DESIGN.md

### 1. ICONS - Không tuân thủ Apple minimal style

**DESIGN.md yêu cầu:** Minimal icons, restrained use of emojis
**Thực tế:** Code sử dụng quá nhiều emoji phức tạp

#### Vị trí vi phạm:

1. **schedule.py:40-55** - Sử dụng emoji phức tạp:
   - `✅` (checkmark) - OK
   - `🔴` (red circle) - quá nổi bật
   - `📺` (TV) - không minimal
   - `🟢` (green circle) - quá nổi bật
   - `🔥` (fire) - không minimal
   - `🗓` (calendar) - không minimal

2. **profile.py:34,37** - Icon `🪪` (ID card) - không minimal, nên dùng `•`

3. **accounts.py:47** - Icon `🗂️` (file cabinet) - không minimal, nên dùng `•`

4. **profile.py:135-147** - Element icons OK (functional)
   - `❤️` và `🤍` - OK cho fetter
   - `✅` - OK cho C6

5. **profile.py:266-269** - Stats icons:
   - `💥` (collision) - quá phức tạp
   - `🛡️` (shield) - quá phức tạp
   - `☠️` (skull) - quá phức tạp
   - `✨` (sparkles) - OK

6. **resin.py:?** - Daily icon `✅`/`❌` - OK

7. **checkin.py:50** - `📅` (calendar) - không minimal

8. **status.py:189** - `📄` (document) - không minimal

9. **profile.py:273** - `🎭` (theater masks) - không minimal

### 2. DIVIDER - Không nhất quán

**DESIGN.md:** Spacing system 8px base, standardized widths
**Thực tế:** Nhiều giá trị divider không chuẩn

#### Vị trí vi phạm:

1. **status.py:138** - `divider(12)` - OK (DIVIDER_SHORT)
2. **profile.py:278** - `divider(21)` - KHÔNG CHUẨN (nên dùng 20 hoặc 24)

### 3. PROGRESS ANIMATION - Hardcoded text

**DESIGN.md:** Minimal, Apple-style animation
**Thực tế:** Hardcoded Vietnamese text trong progress.py

#### Vị trí vi phạm:

1. **progress.py:22** - `"Đang xử lý..."` - hardcoded, không i18n
2. **progress.py:43** - `"Hoàn tất"` - hardcoded, không i18n
3. **progress.py:52** - `"Có lỗi xảy ra"` - hardcoded, không i18n

### 4. SPACING - Một số chỗ chưa dùng constants

**DESIGN.md:** Use spacing constants from ui_constants.py
**Thực tế:** Một số nơi hardcode spacing

#### Cần kiểm tra:
- Các meter_bar width=10 có nhất quán không
- Các divider có dùng đúng constants không

### 5. ACCOUNT HEADING ICON - Không nhất quán

**DESIGN.md:** Minimal icon, default `•`
**Thực tế:** 
- `account_heading()` default là `•` - OK
- Nhưng nhiều nơi override với emoji phức tạp

## Tổng kết lỗi cần fix:

### Priority 1 - Icons không minimal:
- [ ] schedule.py: Thay `🔴📺🟢🔥🗓` → minimal alternatives
- [ ] profile.py: Thay `🪪` → `•`
- [ ] accounts.py: Thay `🗂️` → `•`
- [ ] profile.py: Thay `💥🛡️☠️` → minimal alternatives
- [ ] checkin.py: Thay `📅` → minimal alternative
- [ ] status.py: Thay `📄` → minimal alternative
- [ ] profile.py: Thay `🎭` → minimal alternative

### Priority 2 - Divider không chuẩn:
- [ ] profile.py:278: Thay `divider(21)` → `divider(DIVIDER_LONG)` (24)

### Priority 3 - Progress hardcoded text:
- [ ] progress.py: Move hardcoded text to i18n catalog

### Priority 4 - Verify consistency:
- [ ] Check all meter_bar widths
- [ ] Check all divider usages
- [ ] Check all icon usages

## Apple Design Principles to Follow:

1. **Restraint over decoration** - Ít emoji, nhiều text
2. **Minimal icon vocabulary** - Chỉ dùng: `•`, `✓`, `✗`, `○`, `⚠`
3. **Functional icons only** - Element icons OK vì functional
4. **Consistent spacing** - Dùng constants, không hardcode
5. **Clean typography** - Text > Icons
