<div align="center">
  <h1>botDailyGI 🤖</h1>
  <p><i>A multi-platform Telegram Bot for Genshin Impact automation (Check-in, Resin tracking, Auto-redeem Giftcodes)</i></p>
</div>

**botDailyGI** is a Telegram Bot designed for Genshin Impact players to automate daily tasks and optimally track resin resources. The bot runs smoothly with **extremely low system resource footprint** on both **Windows 11** and **Linux (Arch/CachyOS/Ubuntu)**.

---

## ✨ Key Features

- 📅 **Auto HoYoLAB Check-in:** Automatically checks in twice a day (09:00 and 21:00 UTC+7) with a built-in retry mechanism for network issues.
- ⚗️ **Resin Tracker:** Alerts you when your resin reaches a custom threshold and sends an urgent warning when it's about to cap (e.g., 8 resin away from the cap).
- 🎁 **Live-stream Giftcode Auto-hunter:** Monitors for new gift codes after version update livestreams from multiple sources (Reddit, HoYoLAB, etc.) and automatically redeems them to your account.
- 📸 **PC Screenshot Utility:** Supports multi-monitor setups on Windows. fully optimized for popular screenshot tools (spectacle, grim, scrot, flameshot) on both X11/Wayland environments (Linux CachyOS/Arch).
- 🔐 **Smart Browser Login:** Logs in directly via a secure Playwright browser window. Supports Headless mode via Xvfb for Linux servers.
- 💤 **Advanced Multi-threading:** Does NOT use continuous `while(True)/poll` loops that drain CPU. Each background thread calculates its own logical sleep time, perfectly complimenting custom kernels like BORE on CachyOS.
- 💻 **Hardware Management:** Shutdown or restart your PC remotely via Telegram with safe confirmation buttons.
- 🌐 **Multi-language Support:** Supports English and Vietnamese, configurable via the `/start` command.

---

## 📋 Telegram Commands

| Command | Description |
|---|---|
| `/start` | Start the bot and select your preferred language |
| `/status` | View hardware status, resin progress & next livestream schedule |
| `/uid` | View connected UID and nickname |
| `/checkin` | Manually trigger HoYoLAB check-in immediately |
| `/characters` | View character list and basic stats |
| `/resin` | Detailed view of current resin, expeditions, and daily commissions |
| `/resinnotify [N]` | Set a reminder when resin reaches $\ge$ N (e.g.: `/resinnotify 150`) |
| `/resinnotify off` | Turn off resin notifications |
| `/redeem [Code]` | Manually redeem a gift code |
| `/fetchcodes` | Instantly hunt and redeem livestream/newbie codes from 20+ sources |
| `/screenshot` | Snap a blazing-fast PC screenshot sent via Telegram |
| `/shutdown` | Scheduled PC shutdown (in 60 seconds) |
| `/login` | Open Playwright to login and fetch a new HoYoLAB Cookie |

---

## 🚀 Setup & Installation

### 1. Preparation (`.env` or `config.py`)

The bot prioritizes reading environment variables from a `.env` file (recommended) for cleanliness and security.

➤ **Create a `.env` file in the same directory as `bot.py`** with the following content:

```env
# File name for hoarding HoYoLAB Cookie config (leave as default)
HOYOLAB_FILE=hoyolab.json

# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCDefGHIJKlmnOPQRstuVWxyz
# Your personal Telegram Chat ID (from @userinfobot)
TELEGRAM_CHAT_ID=123456789

# Auto-fill credentials for HoYoLAB Playwright Login
HOYOLAB_USER=your_email_or_username
HOYOLAB_PASS=your_password

# ADVANCED (Optional - you can exclude these if not needed)
AUTO_LIVE_DETECT=1       # 1: Enable auto-detecting Genshin live stream times (from Hoyolab posts)
STREAM_HOUR=11           # Fix the live stream hour explicitly
STREAM_MINUTE=0          # Fix the live stream minute explicitly
FETCH_WAIT_AFTER_MIN=210 # HOW LONG (mins) to wait after Live to fetch Codes (e.g. 210 mins = 3.5 hrs)
```

*(Note: If you dislike `.env`, you can edit `config.py` directly and hardcode your variables).*

---

### 2. Installation on Windows 11

**Step 1:** Download [Python 3.10+](https://www.python.org/downloads/) (Make sure to tick `"Add Python to PATH"` during installation).

**Step 2:** Open PowerShell in the bot's directory and run:
```powershell
# Install core and image processing libraries
pip install requests playwright pillow
# Download Playwright's Chromium core
python -m playwright install chromium
```

**Step 3: Fetching the initial Cookie**
```powershell
python login.py
```
> A Chromium window will pop open. Click on the `Account` and `Password` inputs, it will **auto-fill** the credentials from your `.env`. Manually solve the Captcha, and click Log In. Once done, terminal will notify you and you can close it. (The `hoyolab.json` file will be generated automatically).

**Step 4: Run the Bot**
```powershell
python bot.py
```
> Telegram will notify you that the bot has started.
> *(Tip: To have the bot start automatically on boot, create a Task in `Task Scheduler` pointing to `python bot.py` or create a `start_bot.bat` file in your shell:startup folder).*

---

### 3. Installation on Linux (Arch / CachyOS / Ubuntu)

The Linux version allows running a Background Service (systemd) for buttery smooth performance without conflicts.

**Step 1: Install core OS libraries:**
```bash
# On Arch / CachyOS
sudo pacman -S python python-pip python-requests xorg-server-xvfb

# (If you use Ubuntu: sudo apt install python3-pip xvfb x11vnc)
```

**Step 2: Install Python Packages**
```bash
pip install requests playwright --break-system-packages
python -m playwright install chromium
```

**Step 3: Initial Login for HoYoLAB Cookie**
> Make sure you have created the `.env` file first.
```bash
python login.py
```

**Step 4: Create User Systemd Service (Pro Background Run)**

This allows the bot to start immediately alongside Linux **without `sudo` access**.

Open Terminal and type:
```bash
mkdir -p ~/.config/systemd/user/
nano ~/.config/systemd/user/botdailygi.service
```
Paste the following (remember to change `/path/to/botDailyGI` to your actual path, e.g.: `/home/xhiep/botDailyGI`):

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
Save the file (`Ctrl+O -> Enter -> Ctrl+X`) and grant boot execution rights:
```bash
# Allow user to run daemon when not logged in
sudo loginctl enable-linger $USER

# Enable service
systemctl --user daemon-reload
systemctl --user enable --now botdailygi
```
> Check the logs to see if the bot is alive: `journalctl --user -u botdailygi -f`

✅ Enjoy automated farming!
