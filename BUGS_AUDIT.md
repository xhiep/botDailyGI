# Bug Audit Report - 2026-04-26

## Lỗi tìm được:

### 1. status.py - Hardcoded text thay vì dùng constants
- **File**: `botdailygi/commands/status.py`
- **Dòng 67**: Hardcoded "Resin:" thay vì dùng icon constant
- **Dòng 106**: Hardcoded "Resin:" và "Nhựa:" trong logic check
- **Fix**: Sử dụng i18n key hoặc icon constant từ ui_constants.py

### 2. profile.py - Indent sai
- **File**: `botdailygi/commands/profile.py`
- **Dòng 263**: Thừa indent (8 spaces thay vì 4)
- **Fix**: Sửa indent về đúng 4 spaces

### 3. Kiểm tra thêm các file khác
- Cần kiểm tra: accounts.py, checkin.py, redeem.py, schedule.py, system.py
- Cần kiểm tra: services/, i18n/, background/

## Trạng thái:
- [x] ui_constants.py - OK
- [x] renderers/text.py - OK  
- [x] renderers/abyss.py - OK
- [x] commands/common.py - OK
- [ ] commands/status.py - CÓ LỖI
- [ ] commands/resin.py - Đang kiểm tra
- [ ] commands/profile.py - CÓ LỖI
- [ ] commands/accounts.py
- [ ] commands/checkin.py
- [ ] commands/redeem.py
- [ ] commands/schedule.py
- [ ] commands/system.py
- [ ] services/
- [ ] i18n/
- [ ] background/
