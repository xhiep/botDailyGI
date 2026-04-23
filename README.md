# botDailyGI

Telegram bot cho Genshin Impact, tối ưu cho runtime nhẹ trên Android/Linux/Windows, với flow cookie-first:

- Bot runtime không phụ thuộc Playwright.
- Cookie HoYoLAB có thể lấy trên máy tính bằng `login.py` hoặc `tools/login_playwright.py`.
- Sau đó dùng `/addaccount <ten>` rồi gửi file JSON cookie qua Telegram để import vào bot.
- Runtime data chỉ nằm trong `runtime/`.

## Kiến trúc mới

- `main.py`: entrypoint chính.
- `python -m botdailygi`: cách chạy package trực tiếp.
- `botdailygi/`: package chính.
- `runtime/accounts.json`: danh sách account.
- `runtime/cookies/*.json`: cookie Playwright storage-state.
- `runtime/codes.txt`: danh sách gift code cho `/redeemall`.
- `runtime/logs/bot.log`: log runtime.
- `tools/login_playwright.py`: tool lấy cookie trên PC.

## UI Telegram

- Lệnh dài dùng progress message + `sendChatAction`.
- Bot ưu tiên edit cùng một message thay vì spam nhiều message rời.
- Nếu Markdown lỗi, transport tự fallback sang plain text.

## Lệnh chính

- `/status`
- `/livestream`
- `/uid`
- `/checkin`
- `/resin`
- `/resinnotify 140`
- `/resinnotify hiep 160`
- `/resinnotify lam off`
- `/stats`
- `/characters`
- `/abyss`
- `/redeem CODE`
- `/redeemall`
- `/blacklist`
- `/clearblacklist`
- `/accounts`
- `/addaccount <ten>`: thêm mới hoặc cập nhật cookie khi hết hạn
- `/removeaccount <ten>`
- `/lang`
- `/help`

## Cài đặt

Tạo `.env` từ `.env.example`, rồi cài package:

```powershell
pip install requests pillow
```

Nếu muốn lấy cookie bằng browser trên PC:

```powershell
pip install playwright
python -m playwright install chromium
python login.py
```

Mặc định file export sẽ được lưu tại `runtime/cookies/pc-login-export.json`.

Chạy bot:

```powershell
python main.py
```

Hoặc:

```powershell
python -m botdailygi
```

## Flow thêm account

1. Trên PC, export hoặc tạo file cookie JSON theo format Playwright storage-state.
   Mặc định có thể dùng luôn file `runtime/cookies/pc-login-export.json`.
2. Trong Telegram, gọi `/addaccount <ten>`.
3. Gửi file `.json` đó cho bot.
4. Bot validate `ltoken_v2` và `ltuid_v2`, lưu vào `runtime/cookies/`, cập nhật `runtime/accounts.json`, rồi refresh thông tin account.
5. Nếu account đã tồn tại, `/addaccount <ten>` sẽ chuyển sang chế độ cập nhật và ghi đè cookie cũ an toàn.

## Ghi chú

- Nếu có nhiều account, nên dùng `/resinnotify <tên_account> <on|off|1..200>` hoặc `/resinnotify all <...>` để cấu hình riêng từng account.

- Root runtime cũ như `hoyolab.json`, `accounts.json`, `bot.log` không còn là nguồn dữ liệu chính.
- Dữ liệu cũ đã được chuyển vào `runtime/`; root chỉ còn code mới và tool login trên PC.
- `bot.py` đã được bỏ để tránh trùng entrypoint; dùng `python main.py` hoặc `python -m botdailygi`.
- `login.py` vẫn giữ lại để lấy cookie trên PC; runtime bot không import Playwright khi khởi động.
