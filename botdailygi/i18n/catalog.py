# -*- coding: utf-8 -*-
"""Static i18n catalog for botDailyGI."""

STRINGS: dict[str, dict[str, str]] = {

    # ── General ───────────────────────────────────────────────────────────
    "gen.unauthorized":    {"vi": "⛔ Không có quyền dùng bot này.", "en": "⛔ Unauthorized to use this bot."},
    "gen.cooldown":        {"vi": "○ Vui lòng chờ {sec:.1f}s trước khi thay đổi lại.", "en": "○ Please wait {sec:.1f}s before changing again."},
    "gen.unknown_cmd":     {"vi": "❓ Lệnh không nhận ra. Gõ /help", "en": "❓ Unknown command. Type /help"},
    "gen.error":           {"vi": "✗ Lỗi: {e}", "en": "✗ Error: {e}"},
    "gen.conn_error":      {"vi": "✗ Lỗi kết nối: {e}", "en": "✗ Connection error: {e}"},
    "gen.no_login":        {"vi": "⚠ Chưa có tài khoản — dùng /addaccount <tên>", "en": "⚠ No account found — use /addaccount <name>"},
    "gen.no_uid":          {"vi": "✗ Không lấy được UID", "en": "✗ Could not get UID"},
    "gen.no_uid_login":    {"vi": "✗ Không lấy được UID\n• Thử /addaccount nếu cookie hết hạn", "en": "✗ Could not get UID\n• Try /addaccount if cookie expired"},
    "gen.render_error":    {"vi": "Lỗi hiển thị kết quả", "en": "Error rendering result"},

    # ── Multi-account ──────────────────────────────────────────────────────
    "acct.empty":              {"vi": "⚠ Chưa có tài khoản nào. Dùng /addaccount <tên> rồi gửi JSON cookie để thêm.", "en": "⚠ No accounts yet. Use /addaccount <name> and upload a cookie JSON to add one."},
    "acct.list_header":        {"vi": "• Tài khoản ({count})", "en": "• Accounts ({count})"},
    "acct.list_footer":        {"vi": "➕ /addaccount <tên> để thêm hoặc cập nhật cookie\n➖ /removeaccount <tên> để xoá", "en": "➕ /addaccount <name> to add or refresh a cookie\n➖ /removeaccount <name> to remove it"},
    "acct.status_ok":          {"vi": "✓ {nickname} • UID {uid} • {region}", "en": "✓ {nickname} • UID {uid} • {region}"},
    "acct.status_cookie_bad":  {"vi": "⚠ Cookie không hợp lệ — dùng /addaccount <tên> rồi gửi lại JSON", "en": "⚠ Cookie invalid — use /addaccount <name> and upload a new JSON"},
    "acct.status_no_cookie":   {"vi": "○ Chưa login — dùng /addaccount <tên>", "en": "○ Not logged in — use /addaccount <name>"},
    "acct.status_no_file":     {"vi": "✗ Không tìm thấy file cookie", "en": "✗ Cookie file not found"},
    "acct.add_usage":          {"vi": "○ Dùng: /addaccount <tên>\nVí dụ: /addaccount Alt\n• Sau đó gửi file cookie JSON lấy từ máy tính.", "en": "○ Usage: /addaccount <name>\nExample: /addaccount Alt\n• Then upload the cookie JSON exported from your PC."},
    "acct.add_dup":            {"vi": "✗ Đã tồn tại tài khoản tên \"{name}\"", "en": "✗ Account named \"{name}\" already exists"},
    "acct.add_file_dup":       {"vi": "✗ Tên \"{name}\" tạo ra file cookie trùng: {file}\n• Hãy đổi tên account khác.", "en": "✗ Name \"{name}\" would reuse cookie file {file}\n• Choose a different account name."},
    "acct.add_import_open":    {"vi": "○ Mở phiên nhận cookie cho **{name}**...", "en": "○ Opening a cookie import session for **{name}**..."},
    "acct.add_import_wait":    {"vi": "• Gửi file cookie JSON cho **{name}** trong {minutes} phút tới.\n• Hỗ trợ file Playwright storage-state có `ltoken_v2` và `ltuid_v2`.", "en": "• Upload the cookie JSON for **{name}** within {minutes} minutes.\n• The bot accepts a Playwright storage-state file with `ltoken_v2` and `ltuid_v2`."},
    "acct.update_import_open": {"vi": "○ Mở phiên cập nhật cookie cho **{name}**...", "en": "○ Opening a cookie refresh session for **{name}**..."},
    "acct.update_import_wait": {"vi": "• Gửi file cookie JSON mới cho **{name}** trong {minutes} phút tới.\n• Bot sẽ ghi đè file cũ tại `{file}`.", "en": "• Upload a fresh cookie JSON for **{name}** within {minutes} minutes.\n• The bot will replace the old file at `{file}`."},
    "acct.add_success":        {"vi": "✓ Đã thêm tài khoản **{name}**: {nickname} (UID {uid})", "en": "✓ Added account **{name}**: {nickname} (UID {uid})"},
    "acct.add_success_no_info":{"vi": "✓ Đã thêm tài khoản **{name}** (không lấy được UID)", "en": "✓ Added account **{name}** (could not fetch UID)"},
    "acct.update_success_no_info":{"vi": "✓ Đã cập nhật cookie cho **{name}** (chưa lấy được UID mới)", "en": "✓ Cookie updated for **{name}** (could not fetch fresh UID info yet)"},
    "acct.add_error":          {"vi": "✗ Không thêm được tài khoản {name}: {err}", "en": "✗ Could not add account {name}: {err}"},
    "acct.remove_usage":       {"vi": "❓ Dùng: /removeaccount <tên>\nVí dụ: /removeaccount Alt", "en": "❓ Usage: /removeaccount <name>\nExample: /removeaccount Alt"},
    "acct.remove_error":       {"vi": "✗ Không xóa được tài khoản {name}: {err}", "en": "✗ Could not remove account {name}: {err}"},
    "acct.remove_success":     {"vi": "✓ Đã xóa tài khoản **{name}**. {file_note}", "en": "✓ Removed account **{name}**. {file_note}"},
    "acct.remove_file_deleted":{"vi": "(File cookie đã xóa)", "en": "(Cookie file deleted)"},
    "acct.import.no_pending":  {"vi": "• Hiện không có phiên /addaccount nào đang chờ file JSON.", "en": "• There is no pending /addaccount session waiting for a JSON file."},
    "acct.import.bad_type":    {"vi": "✗ Chỉ nhận file `.json` cho cookie import.", "en": "✗ Only `.json` files are accepted for cookie import."},
    "acct.import.too_large":   {"vi": "✗ File quá lớn ({size} bytes). Giới hạn: {max_size} bytes.", "en": "✗ File is too large ({size} bytes). Limit: {max_size} bytes."},
    "acct.import.bad_file":    {"vi": "✗ Không đọc được file từ Telegram.", "en": "✗ Could not read the file from Telegram."},
    "acct.import.downloading": {"vi": "• Đang tải file cookie cho **{name}**...", "en": "• Downloading cookie file for **{name}**..."},
    "acct.import.download_fail":{"vi": "✗ Tải file từ Telegram thất bại.", "en": "✗ Failed to download the file from Telegram."},
    "acct.import.validating":  {"vi": "○ Đang kiểm tra cookie cho **{name}**...", "en": "○ Validating cookie data for **{name}**..."},
    "acct.import.success":     {"vi": "✓ Đã import **{name}**: {nickname} (UID {uid}, {region})", "en": "✓ Imported **{name}**: {nickname} (UID {uid}, {region})"},
    "acct.import.updated":     {"vi": "✓ Đã cập nhật cookie cho **{name}**: {nickname} (UID {uid}, {region})", "en": "✓ Updated cookie for **{name}**: {nickname} (UID {uid}, {region})"},
    "acct.import.failed":      {"vi": "✗ Import cookie thất bại: {err}", "en": "✗ Cookie import failed: {err}"},
    "gen.api_error":       {"vi": "✗ Lỗi ({code}): {msg}{hint}", "en": "✗ Error ({code}): {msg}{hint}"},
    "gen.img_error":       {"vi": "✗ Lỗi gửi ảnh: {e}", "en": "✗ Error sending image: {e}"},

    # ── Hints (appended to API errors) ────────────────────────────────────
    "hint.cookie_expired": {"vi": "\n• Cookie hết hạn → /addaccount <tên> rồi gửi JSON mới", "en": "\n• Cookie expired → /addaccount <name> and upload a fresh JSON"},
    "hint.realtime_notes": {"vi": "\n• HoYoLAB → bật 'Ghi Chép Thời Gian Thực'", "en": "\n• HoYoLAB → enable 'Real-Time Notes'"},
    "hint.set_public":     {"vi": "\n• HoYoLAB → chuyển hồ sơ sang công khai", "en": "\n• HoYoLAB → set profile to public"},
    "hint.captcha":        {"vi": "\n• Bị xác minh — mở HoYoLAB và xác nhận captcha", "en": "\n• Verification required — open HoYoLAB & complete captcha"},
    "hint.all_toggles":    {"vi": "\n• HoYoLAB → Cài đặt → bật tất cả toggle hồ sơ game", "en": "\n• HoYoLAB → Settings → enable all game profile toggles"},
    "hint.char_detail":    {"vi": "\n• HoYoLAB → Cài đặt → bật 'Hiển thị chi tiết nhân vật'", "en": "\n• HoYoLAB → Settings → enable 'Show character details'"},
    "hint.view_profile":   {"vi": "\n• HoYoLAB → bật 'Bật Tính Năng Xem Hồ Sơ Game'", "en": "\n• HoYoLAB → enable 'View Game Profile'"},
    "hint.char_detail2":   {"vi": "• Bật 'Hiển thị chi tiết nhân vật' trong HoYoLAB", "en": "• Enable 'Show character details' in HoYoLAB"},

    # ── Cookie / File errors ───────────────────────────────────────────────
    "cookie.not_found":    {"vi": "✗ Không tìm thấy cookie — dùng /addaccount <tên> rồi gửi JSON cookie", "en": "✗ Cookie not found — use /addaccount <name> and upload the cookie JSON"},

    # ── Bot lifecycle ──────────────────────────────────────────────────────
    "bot.type_help":       {"vi": "Gõ /help để xem lệnh.", "en": "Type /help to see commands."},
    "bot.stopping":        {"vi": "○ Bot đang dừng lại (Ctrl+C).\n• Khởi động lại để tiếp tục.", "en": "○ Bot is shutting down (Ctrl+C).\n• Restart to continue."},
    "bot.unknown_cb":      {"vi": "❓ Không rõ hành động", "en": "❓ Unknown action"},
    "bot.saving_cookie":   {"vi": "○ Đang lưu cookie...", "en": "○ Saving cookie..."},
    "bot.cancelled":       {"vi": "✓ Đã huỷ", "en": "✓ Cancelled"},

    # ── Progress messages ─────────────────────────────────────────────────
    "progress.processing": {"vi": "Đang xử lý...", "en": "Processing..."},
    "progress.done":       {"vi": "Hoàn tất", "en": "Done"},
    "progress.error":      {"vi": "Có lỗi xảy ra", "en": "Error occurred"},

    # ── /status header (hardcoded lines) ────────────────────────────────
    "status.header":       {"vi": "○ Trạng thái bot",          "en": "○ Bot status"},
    "status.fetching":     {"vi": "• Đang gom trạng thái bot, tài khoản và nhựa...", "en": "• Gathering bot, account, and resin status..."},
    "status.host_line":    {"vi": "○ {host}  ({os})",          "en": "○ {host}  ({os})"},
    "status.time_line":    {"vi": "○ {time}",                   "en": "○ {time}"},
    "status.uptime_line":  {"vi": "○ Uptime: {uptime}",         "en": "○ Uptime: {uptime}"},

    # ── /status ────────────────────────────────────────────────────────────
    "status.login_pending":{"vi": "○ Đang có phiên đăng nhập → dùng nút Huỷ ở tin nhắn login", "en": "○ Login session pending → use the Cancel button in the login message"},
    "status.cookie_line":  {"vi": "○ Cookie: {status}", "en": "○ Cookie: {status}"},
    "status.resin_bar":    {"vi": "⚠ Nhựa: [{bar}] {cur}/{max}{eta}", "en": "⚠ Resin: [{bar}] {cur}/{max}{eta}"},
    "status.eta_full":     {"vi": " — đầy ✓", "en": " — fully refilled ✓"},
    "status.eta_at":       {"vi": " — đầy lúc {time}", "en": " — full at {time}"},
    "status.checkin_line": {"vi": "○ Điểm danh: {icon} ({total} ngày)", "en": "○ Check-in: {icon} ({total} days)"},
    "status.checked":      {"vi": "✓ Đã điểm", "en": "✓ Checked"},
    "status.not_checked":  {"vi": "✗ Chưa điểm", "en": "✗ Not checked"},
    "status.resin_error":  {"vi": "Resin: lỗi rc={rc} ({msg})", "en": "Resin: error rc={rc} ({msg})"},
    "status.resin_dup_uid":{"vi": "Resin: xem tài khoản {account} (cùng UID)", "en": "Resin: see account {account} (same UID)"},
    "status.live_future":  {"vi": "○ Livestream v{ver}: {time} (còn {days} ngày)", "en": "○ Livestream v{ver}: {time} (in {days} days)"},
    "status.live_today":   {"vi": "○ Livestream v{ver}: hôm nay lúc {time}", "en": "○ Livestream v{ver}: today at {time}"},
    "status.thread_dead":  {"vi": "Có background thread đã dừng.", "en": "Some background threads have stopped."},
    "status.locks_idle":   {"vi": "rảnh", "en": "idle"},
    "status.cmd_pending":  {"vi": "lệnh chờ", "en": "pending"},
    "status.net_starting": {"vi": "đang khởi tạo", "en": "starting"},
    "status.net_ok":       {"vi": "ổn định", "en": "stable"},
    "status.net_dns_fail": {"vi": "mất DNS x{count}", "en": "DNS fail x{count}"},
    "status.net_poll_fail":{"vi": "lỗi polling x{count}", "en": "polling error x{count}"},
    "status.net_unknown":  {"vi": "không rõ", "en": "unknown"},
    "status.cfg_enabled":  {"vi": "bật", "en": "on"},
    "status.cfg_disabled": {"vi": "tắt", "en": "off"},

    # ── /resin ─────────────────────────────────────────────────────────────
    "resin.fetching":      {"vi": "• Đang lấy trạng thái nhựa...", "en": "• Fetching resin status..."},
    "resin.title":         {"vi": "⚠ Nhựa — {nickname}", "en": "⚠ Resin — {nickname}"},
    "resin.full_done":     {"vi": "Đã đầy ✓", "en": "Fully refilled ✓"},
    "resin.full_in":       {"vi": "   ○ Đầy sau  : {hhmm}", "en": "   ○ Full in  : {hhmm}"},
    "resin.full_at":       {"vi": "   • Đầy lúc   : {time}", "en": "   • Full at   : {time}"},
    "resin.expedition":    {"vi": "   • Expedition: {done}/{total} xong", "en": "   • Expedition: {done}/{total} done"},
    "resin.daily":         {"vi": "   • Daily    : {done}/{total}  {icon}", "en": "   • Daily    : {done}/{total}  {icon}"},
    "resin.reward":        {"vi": "   • Thưởng   : {status}", "en": "   • Rewards  : {status}"},
    "resin.claimed":       {"vi": "✓ Đã nhận", "en": "✓ Claimed"},
    "resin.unclaimed":     {"vi": "✗ Chưa nhận", "en": "✗ Not claimed"},
    "resin.transformer_rdy":  {"vi": "   ○ Transformer: ✓ Sẵn sàng!", "en": "   ○ Transformer: ✓ Ready!"},
    "resin.transformer_wait": {"vi": "   ○ Transformer: ○ Chưa sẵn sàng", "en": "   ○ Transformer: ○ Not ready"},

    # ── /resinnotify ───────────────────────────────────────────────────────
    "resin.notify.disabled":    {"vi": "○ Đã tắt thông báo nhựa.", "en": "○ Resin alerts disabled."},
    "resin.notify.enabled":     {"vi": "○ Đã bật thông báo nhựa (ngưỡng: {threshold}/200).", "en": "○ Resin alerts enabled (threshold: {threshold}/200)."},
    "resin.notify.bad_val":     {"vi": "⚠ Ngưỡng phải từ 1 đến 200.", "en": "⚠ Threshold must be between 1 and 200."},
    "resin.notify.reached":     {"vi": "✓ Ngưỡng {val}/{max} — nhựa {cur}/{max} đã đạt!", "en": "✓ Threshold {val}/{max} — resin {cur}/{max} already reached!"},
    "resin.notify.pending":     {"vi": "✓ Ngưỡng: {val}/{max}\nR Nhựa hiện tại: {cur}/{max}\n○ Cần thêm: {need} × 8m = {hhmm}\n○ Sẽ báo lúc: {eta}", "en": "✓ Threshold: {val}/{max}\nR Current Resin: {cur}/{max}\n○ Needs: {need} × 8m = {hhmm}\n○ Alert at: {eta}"},
    "resin.notify.set_simple":  {"vi": "✓ Đã đặt ngưỡng thông báo: {val}/200", "en": "✓ Notification threshold set: {val}/200"},
    "resin.notify.status":      {"vi": "⚠ Thông báo nhựa\n○ Trạng thái: {state}\n• Ngưỡng: {threshold}/200\n\n• /resinnotify 150\n• /resinnotify off", "en": "⚠ Resin alerts\n○ Status: {state}\n• Threshold: {threshold}/200\n\n• /resinnotify 150\n• /resinnotify off"},
    "resin.notify.state_on":    {"vi": "BẬT", "en": "ON"},
    "resin.notify.state_off":   {"vi": "TẮT", "en": "OFF"},
    "resin.notify.usage_multi": {"vi": "❓ Dùng: /resinnotify <tài_khoản|all> <on|off|1..200>\nVí dụ:\n/resinnotify hiep 160\n/resinnotify lam off\n/resinnotify all 180", "en": "❓ Usage: /resinnotify <account|all> <on|off|1..200>\nExamples:\n/resinnotify hiep 160\n/resinnotify lam off\n/resinnotify all 180"},
    "resin.notify.account_missing": {"vi": "✗ Không tìm thấy tài khoản `{name}`.", "en": "✗ Account `{name}` not found."},
    "resin.notify.account_enabled": {"vi": "○ **{name}**: đã bật thông báo nhựa (ngưỡng: {threshold}/200).", "en": "○ **{name}**: resin alerts enabled (threshold: {threshold}/200)."},
    "resin.notify.account_disabled": {"vi": "○ **{name}**: đã tắt thông báo nhựa.", "en": "○ **{name}**: resin alerts disabled."},
    "resin.notify.account_set": {"vi": "✓ **{name}**: đã đặt ngưỡng thông báo {val}/200.", "en": "✓ **{name}**: notification threshold set to {val}/200."},
    "resin.notify.multi_header": {"vi": "⚠ Thông báo nhựa theo tài khoản", "en": "⚠ Per-account resin alerts"},
    "resin.notify.multi_line": {"vi": "• {name} — {state}, ngưỡng {threshold}/200", "en": "• {name} — {state}, threshold {threshold}/200"},

    # ── Resin alerts (auto from threads) ──────────────────────────────────
    "resin.alert.threshold":    {"vi": "⚠ NHỰA ĐÃ ĐẠT NGƯỠNG!\n• {nickname}\nR Nhựa: {full_str}\n⚠ Ngưỡng: {threshold}/{max}\n• Vào farm nhựa kẻo tràn!{hint}", "en": "⚠ RESIN REACHED THRESHOLD!\n• {nickname}\nR Resin: {full_str}\n⚠ Threshold: {threshold}/{max}\n• Farm resin before it caps!{hint}"},
    "resin.alert.critical":     {"vi": "⚠ NHỰA SẮP TRÀN!\n• {nickname}\nR Nhựa: {cur}/{max}\n✗ Còn {remain} nhựa nữa là tràn!\n• Vào farm NGAY kẻo mất nhựa!", "en": "⚠ RESIN ALMOST CAPPED!\n• {nickname}\nR Resin: {cur}/{max}\n✗ {remain} resin until capped!\n• Farm NOW to avoid capping!"},
    "resin.alert.hint_critical":{"vi": "\n(Sẽ cảnh báo thêm khi ≥{critical})", "en": "\n(Will alert again when ≥{critical})"},
    "resin.alert.full_str":     {"vi": "đầy hoàn toàn ✓", "en": "fully recovered ✓"},

    # ── /checkin ──────────────────────────────────────────────────────────
    "checkin.busy":        {"vi": "○ Đang có lệnh /checkin đang chạy rồi.\n• Chờ xíu nhé!", "en": "○ /checkin is already running.\n• Hold on a sec!"},
    "checkin.checking":    {"vi": "○ Đang kiểm tra điểm danh...", "en": "○ Checking check-in status..."},
    "checkin.header":      {"vi": "• Điểm danh", "en": "• Check-in"},
    "checkin.manual.label":{"vi": "Thủ công", "en": "Manual"},
    "checkin.already":     {"vi": "• Hôm nay đã điểm danh rồi! (Tích lũy: {total} ngày)", "en": "• Already checked in today! (Accumulated: {total} days)"},
    "checkin.success":     {"vi": "✓ Điểm danh thành công!", "en": "✓ Check-in successful!"},
    "checkin.failed":      {"vi": "✗ Điểm danh thất bại: {msg}", "en": "✗ Check-in failed: {msg}"},
    "checkin.invalid_cok": {"vi": "✗ Cookie không hợp lệ: {e}", "en": "✗ Invalid cookie: {e}"},

    # ── Auto check-in (hoyolab_api.py + threads) ──────────────────────────
    "checkin.auto.label_startup": {"vi": "🚀 [Khởi động]", "en": "🚀 [Startup]"},
    "checkin.auto.label_sched":   {"vi": "🌅 [{time}]",    "en": "🌅 [{time}]"},
    "checkin.auto.no_cookie":  {"vi": "⚠ Auto check-in thất bại: {err}", "en": "⚠ Auto check-in failed: {err}"},
    "checkin.auto.already":    {"vi": "{label} Hôm nay đã điểm danh rồi ✓", "en": "{label} Already checked in today ✓"},
    "checkin.auto.already2":   {"vi": "{label} • Đã điểm danh rồi ({msg})", "en": "{label} • Already checked in ({msg})"},
    "checkin.auto.success":    {"vi": "{label} ✓ Điểm danh thành công!", "en": "{label} ✓ Check-in successful!"},
    "checkin.auto.retry":      {"vi": "⚠ {label} Điểm danh lần {attempt} thất bại: {msg}\n○ Thử lại sau {wait_m} phút...", "en": "⚠ {label} Check-in attempt {attempt} failed: {msg}\n○ Retrying in {wait_m} mins..."},
    "checkin.auto.failed":     {"vi": "✗ {label} Điểm danh thất bại sau {retries} lần thử: {msg}\n• Dùng /checkin để thử thủ công", "en": "✗ {label} Check-in failed after {retries} attempts: {msg}\n• Use /checkin to retry manually"},
    "checkin.auto.error":      {"vi": "✗ {label} Lỗi sau {retries} lần: {e}", "en": "✗ {label} Error after {retries} attempts: {e}"},

    # ── /uid ──────────────────────────────────────────────────────────────
    "uid.list_header":     {"vi": "○ Danh sách UID ({count} tài khoản):", "en": "○ UID List ({count} accounts):"},
    "uid.info":            {"vi": "• Nickname : {nickname}\n○ UID      : {uid}\n• Server   : {region}", "en": "• Nickname : {nickname}\n○ UID      : {uid}\n• Server   : {region}"},

    # ── /livestream ───────────────────────────────────────────────────────
    "live.title":          {"vi": "• GENSHIN IMPACT — LỊCH PHIÊN BẢN", "en": "• GENSHIN IMPACT — VERSION SCHEDULE"},
    "live.cur_ver":        {"vi": "• Phiên bản hiện tại : v{ver}", "en": "• Current version     : v{ver}"},
    "live.ver_header":     {"vi": "• Phiên bản v{ver}", "en": "• Version v{ver}"},
    "live.stream_passed":  {"vi": "{time} (đã qua)", "en": "{time} (passed)"},
    "live.stream_today":   {"vi": "HÔM NAY {time} ←", "en": "TODAY {time} ←"},
    "live.stream_future":  {"vi": "{time} (còn {days} ngày)", "en": "{time} (in {days} days)"},
    "live.patch_running":  {"vi": "{time} (đang chạy)", "en": "{time} (in progress)"},
    "live.patch_today":    {"vi": "HÔM NAY {time} ←", "en": "TODAY {time} ←"},
    "live.patch_future":   {"vi": "{time} (còn {days} ngày)", "en": "{time} (in {days} days)"},
    "live.stream_lbl":     {"vi": "Live  :", "en": "Stream:"},
    "live.patch_lbl":      {"vi": "Patch :", "en": "Patch :"},
    "live.no_schedule":    {"vi": "⚠ Không tìm được lịch — thử lại sau.", "en": "⚠ Schedule not found — try again later."},
    "live.default_time":   {"vi": "• Giờ live mặc định: {h:02d}:{m:02d} (VN)", "en": "• Default stream time: {h:02d}:{m:02d} (VN)"},

    # ── /stats ────────────────────────────────────────────────────────────
    "stats.fetching":      {"vi": "○ Đang lấy thống kê tài khoản...", "en": "○ Fetching account stats..."},
    "stats.title":         {"vi": "• THỐNG KÊ — {nickname}",          "en": "• ACCOUNT STATS — {nickname}"},
    "stats.uid_region":    {"vi": "○ {uid}  |  • {region}",          "en": "○ {uid}  |  • {region}"},
    "stats.days":          {"vi": "• Ngày chơi        :",              "en": "• Days Active      :"},
    "stats.achievement":   {"vi": "• Thành tựu        :",              "en": "• Achievement      :"},
    "stats.chars_owned":   {"vi": "• Nhân vật sở hữu  :",              "en": "• Characters Owned :"},
    "stats.waypoint":      {"vi": "• Waypoint         :",              "en": "• Waypoint         :"},
    "stats.domain":        {"vi": "• Domain           :",              "en": "• Domain           :"},
    "stats.chests_hdr":    {"vi": "• CHEST ĐÃ MỞ",                    "en": "• CHESTS OPENED"},
    "stats.chest.luxurious":   {"vi": "  Xa xỉ      :", "en": "  Luxurious  :"},
    "stats.chest.precious":    {"vi": "  Quý giá    :", "en": "  Precious   :"},
    "stats.chest.exquisite":   {"vi": "  Tinh xảo   :", "en": "  Exquisite  :"},
    "stats.chest.common":      {"vi": "  Phổ thông  :", "en": "  Common     :"},
    "stats.chest.remarkable":  {"vi": "  Đặc biệt   :", "en": "  Remarkable :"},
    "stats.oculi_hdr":     {"vi": "• OCULI",                          "en": "• OCULI"},
    "stats.oculi.anemoculus":  {"vi": "  Anemoculus  :", "en": "  Anemoculus  :"},
    "stats.oculi.geoculus":    {"vi": "  Geoculus    :", "en": "  Geoculus    :"},
    "stats.oculi.electroculus":{"vi": "  Electroculus:", "en": "  Electroculus:"},
    "stats.oculi.dendroculus": {"vi": "  Dendroculus :", "en": "  Dendroculus :"},
    "stats.oculi.hydroculus":  {"vi": "  Hydroculus  :", "en": "  Hydroculus  :"},
    "stats.oculi.pyroculus":   {"vi": "  Pyroculus   :", "en": "  Pyroculus   :"},
    "stats.world_hdr":     {"vi": "• KHÁM PHÁ THẾ GIỚI",             "en": "• WORLD EXPLORATION"},

    # ── /characters ───────────────────────────────────────────────────────
    "chars.title":         {"vi": "• NHÂN VẬT — {nickname}", "en": "• CHARACTERS — {nickname}"},
    "chars.fetching":      {"vi": "○ Đang lấy danh sách nhân vật...", "en": "○ Fetching character list..."},
    "chars.summary":       {"vi": "○ {uid}  |  •×{five}  •×{four}  |  Tổng {total}", "en": "○ {uid}  |  •×{five}  •×{four}  |  Total {total}"},
    "chars.five_hdr":      {"vi": "• 5 SAO ({count})", "en": "• 5-STAR ({count})"},
    "chars.four_hdr":      {"vi": "• 4 SAO ({count})", "en": "• 4-STAR ({count})"},
    "chars.none":          {"vi": "✗ Không có nhân vật", "en": "✗ No characters"},
    "chars.total_bar":     {"vi": "• Tổng:   {bar}", "en": "• Total:   {bar}"},
    "chars.five_bar":      {"vi": "• 5 sao: {bar}", "en": "• 5-star: {bar}"},
    # Element display names — key từ API element string
    "elem.Pyro":    {"vi": "Hỏa",  "en": "Pyro"},
    "elem.Hydro":   {"vi": "Thủy", "en": "Hydro"},
    "elem.Anemo":   {"vi": "Phong","en": "Anemo"},
    "elem.Electro": {"vi": "Lôi",  "en": "Electro"},
    "elem.Dendro":  {"vi": "Thảo", "en": "Dendro"},
    "elem.Cryo":    {"vi": "Băng", "en": "Cryo"},
    "elem.Geo":     {"vi": "Nham", "en": "Geo"},

    # ── /abyss ────────────────────────────────────────────────────────────
    "abyss.fetching":      {"vi": "○ Đang lấy dữ liệu Spiral Abyss [{label}]...", "en": "○ Fetching Spiral Abyss data [{label}]..."},
    "abyss.locked":        {"vi": "✗ Spiral Abyss chưa mở hoặc chưa có dữ liệu kỳ này.\n• /abyss 2 để xem kỳ trước", "en": "✗ Spiral Abyss is locked or no data for this period.\n• /abyss 2 to view previous period"},
    "abyss.label_prev":    {"vi": "KỲ TRƯỚC", "en": "PREV PERIOD"},
    "abyss.label_cur":     {"vi": "KỲ NÀY",   "en": "CUR PERIOD"},
    "abyss.caption":       {"vi": "• SPIRAL ABYSS [{label}] — {nickname}\n• {stars}/36   • {floor}   • {battles} trận", "en": "• SPIRAL ABYSS [{label}] — {nickname}\n• {stars}/36   • {floor}   • {battles} battles"},
    "abyss.ready_img":     {"vi": "○ Đã render xong {count} ảnh Abyss, đang gửi...", "en": "○ Rendered {count} Abyss images, sending..."},
    "abyss.text_header":   {"vi": "• SPIRAL ABYSS [{label}] — {nickname}", "en": "• SPIRAL ABYSS [{label}] — {nickname}"},
    "abyss.text_period":   {"vi": "• {start} → {end}",                     "en": "• {start} → {end}"},
    "abyss.stats":         {"vi": "• {stars}/36   • {floor}   • {battles} trận ({wins} thắng)", "en": "• {stars}/36   • {floor}   • {battles} battles ({wins} wins)"},
    "abyss.floor":         {"vi": "Tầng {n}", "en": "Floor {n}"},
    "abyss.footer_prev":   {"vi": "• /abyss — kỳ này", "en": "• /abyss — current period"},
    "abyss.footer_cur":    {"vi": "• /abyss 2 — kỳ trước", "en": "• /abyss 2 — previous period"},
    "abyss.phase_lbl":     {"vi": "P", "en": "P"},    # Prefix cho "P1 ➀" / "P2 ➀" trong text fallback


    # ── Gift codes ────────────────────────────────────────────────────────
    "code.usage":          {"vi": "⚠ Dùng: /redeem ABCD1234", "en": "⚠ Usage: /redeem ABCD1234"},
    "code.blacklisted":    {"vi": "✗ [{code}] Đã blacklist ({reason})\n• /clearblacklist để xóa", "en": "✗ [{code}] Blacklisted ({reason})\n• /clearblacklist to remove"},
    "code.redeeming":      {"vi": "○ Đang đổi [{code}]...", "en": "○ Redeeming [{code}]..."},
    "code.success":        {"vi": "✓ [{code}] Đổi thành công!", "en": "✓ [{code}] Redeemed successfully!"},
    "code.failed_bl":      {"vi": "✗ [{code}] Thất bại: {msg}\n✗ Đã thêm vào blacklist ({reason})", "en": "✗ [{code}] Failed: {msg}\n✗ Added to blacklist ({reason})"},
    "code.failed":         {"vi": "✗ [{code}] Thất bại: {msg}", "en": "✗ [{code}] Failed: {msg}"},
    "code.redeem_busy":    {"vi": "○ Đang có lệnh redeem đang chạy rồi.\n• Chờ nó xong nhé!", "en": "○ Redeem already in progress.\n• Wait for it to finish!"},
    "code.redeem_busy2":   {"vi": "○ Đang có lệnh redeem đang chạy rồi.\n• Chờ nó xong, đừng gọi lại!", "en": "○ Redeem already in progress.\n• Don't call again!"},
    "code.no_codes":       {"vi": "⚠ Không có code nào trong codes.txt", "en": "⚠ No codes found in codes.txt"},
    "code.bl_empty":       {"vi": "✓ Blacklist trống.", "en": "✓ Blacklist is empty."},
    "code.bl_already_empty":{"vi": "• Blacklist đã trống rồi.", "en": "• Blacklist is already empty."},
    "code.bl_header":      {"vi": "✗ BLACKLIST CODE ({count} code)", "en": "✗ BLACKLISTED CODES ({count} codes)"},
    "code.bl_footer":      {"vi": "• /clearblacklist để xóa toàn bộ", "en": "• /clearblacklist to clear all"},
    "code.cleared":        {"vi": "✓ Đã xóa blacklist ({count} code).\nLần redeem tiếp sẽ thử lại tất cả.", "en": "✓ Cleared blacklist ({count} codes).\nNext redeem will retry all."},
    "code.clear_error":    {"vi": "✗ Lỗi xóa blacklist: {e}", "en": "✗ Error clearing blacklist: {e}"},



    # ── /lang ─────────────────────────────────────────────────────────────
    "lang.current":        {"vi": "• Ngôn ngữ hiện tại: {cur}\nChọn ngôn ngữ:", "en": "• Current language: {cur}\nChoose language:"},
    "lang.changed":        {"vi": "✓ Đã đổi ngôn ngữ sang {name}.", "en": "✓ Language changed to {name}."},
    "lang.changed_cb":     {"vi": "✓ {name}",                        "en": "✓ {name}"},
    "lang.vi_name":        {"vi": "Tiếng Việt", "en": "Vietnamese"},
    "lang.en_name":        {"vi": "English", "en": "English"},
    "lang.vi_btn":         {"vi": "• Tiếng Việt", "en": "• Tiếng Việt"},
    "lang.en_btn":         {"vi": "• English", "en": "• English"},

    # ── /start ────────────────────────────────────────────────────────────
    "start.msg":           {"vi": "• Chào mừng đến với botDailyGI\n\n• Chọn ngôn ngữ để bắt đầu:", "en": "• Welcome to botDailyGI\n\n• Choose your language to begin:"},

    # ── /help ─────────────────────────────────────────────────────────────
    "help.body": {
        "vi": (
            "• LỆNH NHANH\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• GENSHIN\n"
            "/status          — trạng thái bot, nhựa, lịch\n"
            "/uid             — UID và tên ingame\n"
            "/checkin         — điểm danh ngay\n"
            "/stats           — thống kê tài khoản\n"
            "/characters      — danh sách nhân vật\n"
            "/resin           — nhựa, daily, expedition\n"
            "/resinnotify N   — báo khi nhựa đạt N\n"
            "/resinnotify off — tắt báo nhựa\n"
            "/abyss           — La Hoàn kỳ này\n"
            "/abyss 2         — La Hoàn kỳ trước\n"
            "/redeem CODE     — nhập 1 gift code\n"
            "/redeemall       — nhập toàn bộ code trong codes.txt\n"
            "/blacklist       — xem code đã chặn\n"
            "/clearblacklist  — xoá blacklist\n"
            "\n• TÀI KHOẢN\n"
            "/accounts             — xem danh sách tài khoản\n"
            "/addaccount <tên>     — thêm mới hoặc cập nhật cookie\n"
            "/removeaccount <tên>  — xoá tài khoản\n"
            "\n• HỆ THỐNG\n"
            "/lang            — đổi ngôn ngữ\n"
            "/livestream      — lịch livestream và patch\n"
            "/help            — mở bảng này\n"
            "\n• Tự động:\n"
            "• Điểm danh lúc 09:00 và 21:00\n"
            "• Cảnh báo nhựa theo ngưỡng và gần tràn\n"
            "• Heartbeat mỗi 12 giờ  |  • bot.log"
        ),
        "en": (
            "• QUICK COMMANDS\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• GENSHIN\n"
            "/status          — bot status, resin, schedule\n"
            "/uid             — UID and in-game name\n"
            "/checkin         — check-in now\n"
            "/stats           — account stats\n"
            "/characters      — character list\n"
            "/resin           — resin, daily, expedition\n"
            "/resinnotify N   — alert when resin reaches N\n"
            "/resinnotify off — disable resin alerts\n"
            "/abyss           — current Spiral Abyss\n"
            "/abyss 2         — previous Spiral Abyss\n"
            "/redeem CODE     — redeem one gift code\n"
            "/redeemall       — redeem all codes in codes.txt\n"
            "/blacklist       — view blacklisted codes\n"
            "/clearblacklist  — clear the entire blacklist\n"
            "\n• ACCOUNT\n"
            "/accounts             — list all accounts\n"
            "/addaccount <name>    — add or refresh a cookie\n"
            "/removeaccount <name> — remove an account\n"
            "\n• SYSTEM\n"
            "/lang            — change language\n"
            "/livestream      — stream and patch schedule\n"
            "/help            — show this panel\n"
            "\n• Automated:\n"
            "• Check-in at 09:00 and 21:00\n"
            "• Resin alerts for threshold and near-cap\n"
            "• Heartbeat every 12 hours  |  • bot.log"
        ),
    },

    # ── Heartbeat ─────────────────────────────────────────────────────────
    "heartbeat.msg":       {"vi": "○ Bot vẫn đang chạy\n○ {host}\n○ {time}\n○ Uptime: {uptime}{extra}", "en": "○ Bot is still running\n○ {host}\n○ {time}\n○ Uptime: {uptime}{extra}"},
    "heartbeat.resin":     {"vi": "\n⚠ Nhựa: [{bar}] {cur}/{max}{eta}", "en": "\n⚠ Resin: [{bar}] {cur}/{max}{eta}"},
    "heartbeat.checkin":   {"vi": "\n○ Điểm danh: {icon} ({total} ngày)", "en": "\n○ Check-in: {icon} ({total} days)"},

    # ── Blacklist reasons (i18n key — stored in file, translated on display) ──
    "code.reason.expired": {"vi": "hết hạn",      "en": "expired"},
    "code.reason.used":    {"vi": "đã dùng",       "en": "already used"},
    "code.reason.invalid": {"vi": "không hợp lệ",  "en": "invalid"},

    # ── do_redeem_codes() result messages ─────────────────────────────────
    "code.redeem.all_bl":     {"vi": "⚠ Toàn bộ {count} code đã trong blacklist.", "en": "⚠ All {count} codes are already blacklisted."},
    "code.redeem.start":      {"vi": "○ {prefix}Đang đổi {count} code cho {nickname} ({uid})...", "en": "○ {prefix}Redeeming {count} codes for {nickname} ({uid})..."},
    "code.redeem.batch_start":{"vi": "○ Đang đổi {count} code cho toàn bộ tài khoản...", "en": "○ Redeeming {count} codes across all accounts..."},
    "code.redeem.summary":    {"vi": "• {prefix}Kết quả redeem — {nickname}", "en": "• {prefix}Redeem results — {nickname}"},
    "code.redeem.ok":         {"vi": "✓ Thành công ({count}): {codes}", "en": "✓ Success ({count}): {codes}"},
    "code.redeem.fail_bl":    {"vi": "✗ Blacklist ({count}):", "en": "✗ Blacklisted ({count}):"},
    "code.redeem.fail_other": {"vi": "⚠ Lỗi khác ({count}):", "en": "⚠ Other errors ({count}):"},
    "code.redeem.skipped":    {"vi": "○ Đã bỏ qua {count} code (đã blacklist)", "en": "○ Skipped {count} codes (already blacklisted)"},

    # ── Cookie status (check_cookie_status) ───────────────────────────────
    "cookie.status_ok":   {"vi": "✓ Hợp lệ — {nickname}", "en": "✓ Valid — {nickname}"},
    "cookie.status_err":  {"vi": "⚠ retcode {code}: {msg}", "en": "⚠ retcode {code}: {msg}"},
    "cookie.status_fail": {"vi": "✗ Lỗi kết nối: {e}", "en": "✗ Connection error: {e}"},

    # ── Bot startup message ───────────────────────────────────────────────
    "bot.startup": {
        "vi": "○ Bot đã khởi động!\n○ {host}  ({os})\n○ {time}\n○ Heartbeat mỗi 12h  |  • Log: bot.log",
        "en": "○ Bot started!\n○ {host}  ({os})\n○ {time}\n○ Heartbeat every 12h  |  • Log: bot.log",
    },

    # ── gen.file_error (telegram_api.py send_file) ───────────────────────
    "gen.file_error": {"vi": "✗ Lỗi gửi file: {e}", "en": "✗ Error sending file: {e}"},

    # ── Time format ───────────────────────────────────────────────────────────
    "fmt.duration":        {"vi": "{hh}h{mm:02d}m", "en": "{hh}h {mm:02d}m"},

}


VI_TO_EN: dict[str, str] = {
    "ngày": "days",
    "giờ": "hours",
    "phút": "mins",
    "giây": "secs",
    "Hợp lệ": "Valid",
    "Hết hạn": "Expired",
}
