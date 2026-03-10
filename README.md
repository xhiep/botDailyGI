# botDailyGI 🤖

botDailyGI là một Telegram Bot dành cho Genshin Impact, được thiết kế để tự động hóa các tác vụ hàng ngày và theo dõi tài nguyên một cách tối ưu. Bot chạy mượt mà và tiêu tốn tối thiểu tài nguyên hệ thống trên **Windows 11** và **Linux (Arch/CachyOS/Ubuntu)**.

## ✨ Tính năng nổi bật

- 📅 **Điểm danh HoYoLAB tự động:** Điểm danh 2 lần mỗi ngày (09:00 và 21:00 VN) với cơ chế tự động retry khi gặp lỗi mạng.
- ⚗️ **Theo dõi Nhựa (Resin) theo thời gian thực:** Cảnh báo khi nhựa đạt ngưỡng bạn thiết lập và cảnh báo khẩn cấp khi nhựa sắp tràn (cách 8 nhựa).
- 🎁 **Tự động săn & đổi Giftcode Livestream:** Tự động phát hiện lịch livestream phiên bản mới, dò tìm code từ nhiều nguồn (Reddit, HoYoLAB, các trang tin tức) sau buổi livestream và tự động đổi code vào tài khoản của bạn.
- 📸 **Tính năng chụp màn hình PC:** Hỗ trợ đa màn hình trên Windows và hầu hết các trình chụp ảnh phổ biến trên Linux (spectacle, grim, scrot, v.v) hỗ trợ mọi môi trường X11/Wayland.
- 🔐 **Đăng nhập tự động & Bảo mật:** Hỗ trợ đăng nhập trực tiếp từ cửa sổ trình duyệt an toàn bằng Playwright, tự động giải quyết Captcha. Hỗ trợ chạy chế độ Headless (không giao diện) cho máy Linux Server.
- 💤 **Tối ưu kiến trúc Đa luồng (Multi-threading):** Không sử dụng cơ chế poll (vòng lặp liên tục), mỗi dịch vụ tự động tính toán thời gian nghỉ `sleep` thông minh, giúp tiết kiệm tối đa CPU/RAM, đặc biệt hữu ích trên các kernel tùy chỉnh như Linux CachyOS.
- 📱 **Giao diện Telegram trực quan:** Tương tác với người dùng thông qua hệ thống nút bấm (Inline Keyboard) và các lệnh đơn giản.
- 💻 **Quản lý máy tính:** Lệnh tắt máy/khởi động lại máy tính trực tiếp qua Telegram (có xác nhận nút bấm).

## 📋 Danh sách lệnh

| Lệnh | Mô tả |
|---|---|
| `/status` | Trạng thái bot, tiến trình nhựa & lịch livestream tiếp theo |
| `/uid` | Xem UID và nickname đang kết nối |
| `/checkin` | Điểm danh HoYoLAB ngay lập tức |
| `/characters` | Xem danh sách nhân vật và chỉ số cơ bản |
| `/resin` | Chi tiết số nhựa hiện tại, thám hiểm, nhiệm vụ uỷ thác hàng ngày |
| `/resinnotify [N]` | Báo nhắc nhở khi nhựa $\ge$ N (vd: `/resinnotify 150`) |
| `/resinnotify off` | Tắt thông báo nhựa |
| `/redeem [CODE]` | Đổi 1 giftcode thủ công |
| `/fetchcodes` | Tìm và đổi code livestream từ 20+ nguồn ngay lập tức |
| `/screenshot` | Chụp hình màn hình PC gửi qua Telegram |
| `/shutdown` | Hẹn giờ tắt máy tính (60s) |
| `/login` | Hiện trình duyệt để đăng nhập HoYoLAB lấy cookie mới |

## 🚀 Cài đặt

### Yêu cầu hệ thống:
- **Ngôn ngữ:** Python 3.9+
- **Thư viện Python:** `requests`, `playwright`, `pillow` (trên Windows)

### 1. Cài đặt trên Windows 11
1. Cài đặt Python và Pip. Mở Terminal/PowerShell chạy lệnh:
   ```powershell
   pip install requests playwright pillow
   python -m playwright install chromium
   ```
2. Đổi tên tệp cấu hình theo ý bạn:
   Tạo tệp `config.py` và điền thông tin sau:
   ```python
   HOYOLAB_FILE       = "hoyolab.json"
   TELEGRAM_BOT_TOKEN = "Token của BotFather"
   TELEGRAM_CHAT_ID   = "ID Telegram của bạn"
   HOYOLAB_USER       = "email/user của bạn"
   HOYOLAB_PASS       = "mật khẩu"
   ```
3. Chạy bot lần đầu để đăng nhập và lấy cookie:
   ```powershell
   python login.py
   ```
4. Cuối cùng, chạy bot chính:
   ```powershell
   python bot.py
   ```
   *(Tham khảo chi tiết tại `huong-dan-setup-Windows.txt`)*

### 2. Cài đặt trên Linux (Arch / CachyOS)
1. Cài đặt các gói hệ thống và thư viện:
   ```bash
   sudo pacman -S python python-pip python-requests xorg-server-xvfb
   pip install requests playwright --break-system-packages
   python -m playwright install chromium
   ```
2. Tạo tệp cấu hình `config.py` tương tự như Windows.
3. Chạy `python login.py` lần đầu để khởi tạo Cookie HoYoLAB.
4. Đưa bot vào **User Systemd Service** (không cần sudo) để chạy tự động ngay cả khi chưa đăng nhập.
   *(Tham khảo chi tiết tại `huong-dan-setup-botDailyGI.txt`)*

## 🛠 Nền tảng
- Cập nhật tương thích API Genshin Impact Version ~> 5.5.
- Code Python đồng bộ hoá hoàn toàn trên cả Windows 11 & Linux.
