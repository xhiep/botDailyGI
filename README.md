<div align="center">
  <h1>botDailyGI 🤖</h1>
  <p><i>Telegram Bot đa nền tảng tự động hóa Genshin Impact (Điểm danh, săn Resin, auto đổi Giftcode)</i></p>
</div>

**botDailyGI** là một Telegram Bot dành cho Genshin Impact, được thiết kế để tự động hóa các tác vụ hàng ngày và theo dõi tài nguyên lượng nhựa tối ưu. Bot chạy mượt mà, **tiêu tốn cực kỳ ít tài nguyên** trên cả **Windows 11** và **Linux (Arch/CachyOS/Ubuntu)**.

---

## ✨ Tính năng nổi bật

- 📅 **Điểm danh HoYoLAB tự động:** Tự động điểm danh 2 lần mỗi ngày (09:00 và 21:00 VN) với cơ chế tự động thử lại (retry) khi mạng gặp sự cố.
- ⚗️ **Theo dõi Nhựa (Resin):** Cảnh báo khi nhựa đạt ngưỡng bạn thiết lập và cảnh báo khẩn cấp khi nhựa sắp tràn (ví dụ: cách 8 nhựa sẽ tràn).
- 🎁 **Tự động săn & đổi Giftcode Livestream:** Chạy lịch dò tìm code mới sau sự kiện livestream từ nhiều nguồn (Reddit, HoYoLAB, v.v) và tự động đổi code vào tài khoản của bạn.
- 📸 **Tính năng chụp màn hình PC:** Hỗ trợ cấu hình đa màn hình (Multi-monitor) trên Windows. Tối ưu hoàn toàn các trình chụp ảnh phổ biến (spectacle, grim, scrot, flameshot) trên môi trường X11/Wayland (Linux CachyOS/Arch).
- 🔐 **Đăng nhập trình duyệt thông minh:** Đăng nhập trực tiếp từ cửa sổ trình duyệt an toàn bằng Playwright. Hỗ trợ chạy không giao diện (Headless) qua thư viện Xvfb trên các server Linux.
- 💤 **Quản lý đa luồng tiên tiến (Multi-threading):** Không sử dụng `while(True)/poll` liên tục gây hao tổn CPU. Mỗi thread nền tự tính toán giờ thức giấc riêng bằng khoảng nghỉ logic, hỗ trợ tương tác tối ưu với kernel BORE của CachyOS.
- 💻 **Quản trị phần cứng:** Tắt máy hoặc khởi động lại PC từ xa ngay qua Telegram với thao tác nút bấm xác nhận an toàn.

---

## 📋 Danh sách lệnh Telegram

| Lệnh | Ý nghĩa |
|---|---|
| `/status` | Xem trạng thái phần cứng thiết bị, lượng nhựa & nhắc nhở lịch livestream |
| `/uid` | Xem UID và nickname đang kết nối với bot |
| `/checkin` | Điểm danh HoYoLAB thủ công ngay lập tức |
| `/characters` | Xem danh sách nhân vật hiện có và chỉ số cơ bản |
| `/resin` | Chi tiết số lượng nhựa hiện tại, các đoàn thám hiểm, nhiệm vụ hàng ngày |
| `/resinnotify [N]` | Báo nhắc nhở ngay khi nhựa đạt mức $\ge$ N (vd: `/resinnotify 150`) |
| `/resinnotify off` | Tắt chức năng thông báo nhựa |
| `/redeem [Mã Code]` | Đổi 1 giftcode thủ công do tự nhập |
| `/fetchcodes` | Dò tìm và đổi code tân thủ/livestream từ mạng ngay lập tức |
| `/screenshot` | Chụp hình màn hình PC gửi siêu tốc qua Telegram |
| `/shutdown` | Hẹn giờ tắt PC (sau 60 giây) |
| `/login` | Bật Playwright để đăng nhập lấy Cookie HoYoLAB mới |

---

## 🚀 Cấu hình và Cài đặt (Setup)

### 1. Chuẩn bị File Cấu Hình (`.env` hoặc `config.py`)

Bot ưu tiên đọc biến môi trường từ file `.env` (khuyên dùng) để đảm bảo sạch sẽ và bảo mật.

➤ **Tạo tệp `.env` ở cùng thư mục chứa `bot.py`** với nội dung:

```env
# Tên tệp tin lưu trữ cấu hình Cookie HoYoLAB (để mặc định)
HOYOLAB_FILE=hoyolab.json

# Token bot Telegram (lấy từ tài khoản @BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCDefGHIJKlmnOPQRstuVWxyz
# Chat ID Telegram của cá nhân bạn (lấy từ @userinfobot)
TELEGRAM_CHAT_ID=123456789

# Thông tin điền tự động khi đăng nhập HoYoLAB Playwright
HOYOLAB_USER=email_hoac_username_cua_ban
HOYOLAB_PASS=mat_khau_cua_ban

# CAO CẤP (Tùy chọn - bạn có thể không cần thêm bên dưới cũng được)
AUTO_LIVE_DETECT=1       # 1: Bật tự động dò giờ live genshin (Dò từ bài đăng Hoyolab)
STREAM_HOUR=11           # Fix giờ cố định livestream trên lịch
STREAM_MINUTE=0          # Fix phút cố định
FETCH_WAIT_AFTER_MIN=210 # Đợi sau Live BAO LÂU (phút) để lấy Code (vd: 210 phút = 3.5 tiếng)
```

*(Lưu ý: Nếu bạn không thích dùng `.env`, bạn vẫn có thể mở file `config.py` và gán cứng biến vào code).*

---

### 2. Cài đặt trên Windows 11

**Bước 1:** Tải [Python 3.10+](https://www.python.org/downloads/) (Nhớ tick vào ô `"Add Python to PATH"` khi cài đặt).

**Bước 2:** Mở PowerShell trong thư mục của bot và chạy các lệnh:
```powershell
# Cài đặt thư viện xử lý và ảnh nền
pip install requests playwright pillow
# Tải lõi duyệt Chromium của Playwright
python -m playwright install chromium
```

**Bước 3: Lấy Cookie lần đầu tiên**
```powershell
python login.py
```
> Lúc này cửa sổ trình duyệt Chromium sẽ mở. Bạn chọn vào ô `Tài khoản` và `Mật khẩu`, nó sẽ **tự động điền** thông tin bạn thiết lập ở `.env`. Bạn giải Captcha thủ công, bấm Đăng Nhập. Khi hoàn tất, quay lại tắt terminal này đi. (File `hoyolab.json` sẽ tự sinh ra).

**Bước 4: Chạy Bot**
```powershell
python bot.py
```
> Trên Telegram sẽ báo `🤖 Bot đã khởi động!`.
> *(Mẹo: Để cho bot tự bật khi khởi động thiết bị, bạn tạo 1 Task trong `Task Scheduler` trỏ file `python bot.py` hoặc tạo file `start_bot.bat` bỏ vào cấu hình thư mục shell:startup).*

---

### 3. Cài đặt trên Linux (Arch / CachyOS / Ubuntu)

Phiên bản Linux cho phép chạy Background Service (systemd) chạy siêu mượt không lo xung đột.

**Bước 1: Cài đặt thư viện lõi hệ điều hành:**
```bash
# Trên Arch / CachyOS
sudo pacman -S python python-pip python-requests xorg-server-xvfb

# (Nếu bạn dùng Ubuntu: sudo apt install python3-pip xvfb x11vnc)
```

**Bước 2: Cài Python Packages**
```bash
pip install requests playwright --break-system-packages
python -m playwright install chromium
```

**Bước 3: Khởi tạo đăng nhập lấy biến Cookie HoYoLAB**
> Cần đảm bảo bạn đã tạo file `.env` như bước trên trước khi làm bước này.
```bash
python login.py
```

**Bước 4: Tạo User Systemd Service (Chạy ngầm chuyên nghiệp)**

Giúp bot khởi động ngay lập tức cùng với Linux mà **không cần quyền `sudo`**.

Mở Terminal và gõ:
```bash
mkdir -p ~/.config/systemd/user/
nano ~/.config/systemd/user/botdailygi.service
```
Dán nội dung sau (lưu ý sửa `/path/to/botDailyGI` thành đường dẫn thực tế của bạn, ví dụ: `/home/xhiep/botDailyGI`):

```ini
[Unit]
Description=botDailyGI Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/botDailyGI
ExecStart=/usr/bin/python /path/to/botDailyGI/bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```
Lưu tệp lại (`Ctrl+O -> Enter -> Ctrl+X`) và cấp quyền chạy khi hệ thống khởi động:
```bash
# Cho phép user chạy daemon khi không đăng nhập
sudo loginctl enable-linger $USER

# Bật service
systemctl --user daemon-reload
systemctl --user enable --now botdailygi
```
> Kiểm tra log xem bot đã sống chưa: `journalctl --user -u botdailygi -f`

✅ Tận hưởng trải nghiệm cày cuốc tự động hóa!
