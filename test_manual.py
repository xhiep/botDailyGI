"""Manual testing script to identify bugs in bot commands."""
import sys
import traceback
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from botdailygi.commands.status import cmd_status
from botdailygi.commands.checkin import cmd_checkin
from botdailygi.commands.resin import cmd_resin, cmd_resinnotify
from botdailygi.commands.profile import cmd_characters, cmd_abyss, cmd_stats, cmd_uid
from botdailygi.commands.redeem import cmd_redeem, cmd_redeemall, cmd_blacklist, cmd_clearblacklist
from botdailygi.commands.accounts import cmd_accounts, cmd_addaccount, cmd_removeaccount
from botdailygi.commands.schedule import cmd_livestream
from botdailygi.commands.system import cmd_help, cmd_lang, cmd_start
from botdailygi.config import TELEGRAM_CHAT_ID

bugs_found = []

def test_command(name, func, *args):
    """Test a command and catch any errors."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    try:
        func(*args)
        print(f"✅ {name} - PASSED")
        return True
    except Exception as e:
        error_msg = f"❌ {name} - FAILED: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        bugs_found.append({
            "command": name,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return False

print("Starting manual command tests...")
CHAT_ID = int(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else 7928031598
print(f"Chat ID: {CHAT_ID}")

# Test basic commands
test_command("/help", cmd_help, CHAT_ID)
test_command("/start", cmd_start, CHAT_ID)
test_command("/lang", cmd_lang, CHAT_ID, "")
test_command("/status", cmd_status, CHAT_ID, "")
test_command("/accounts", cmd_accounts, CHAT_ID)
test_command("/livestream", cmd_livestream, CHAT_ID)

# Test commands that require accounts
test_command("/uid", cmd_uid, CHAT_ID, "")
test_command("/checkin", cmd_checkin, CHAT_ID)
test_command("/resin", cmd_resin, CHAT_ID, "")
test_command("/resinnotify (no args)", cmd_resinnotify, CHAT_ID, "")
test_command("/stats", cmd_stats, CHAT_ID, "")
test_command("/characters", cmd_characters, CHAT_ID, "")
test_command("/abyss", cmd_abyss, CHAT_ID, "")

# Test redeem commands
test_command("/blacklist", cmd_blacklist, CHAT_ID)
test_command("/clearblacklist", cmd_clearblacklist, CHAT_ID)
test_command("/redeem (no code)", cmd_redeem, CHAT_ID, "")
test_command("/redeemall", cmd_redeemall, CHAT_ID)

# Test account management
test_command("/addaccount (no name)", cmd_addaccount, CHAT_ID, "")
test_command("/removeaccount (no name)", cmd_removeaccount, CHAT_ID, "")

# Summary
print(f"\n{'='*60}")
print(f"TEST SUMMARY")
print(f"{'='*60}")
print(f"Total bugs found: {len(bugs_found)}")

if bugs_found:
    print("\n🐛 BUGS FOUND:")
    for i, bug in enumerate(bugs_found, 1):
        print(f"\n{i}. {bug['command']}")
        print(f"   Error: {bug['error']}")
        print(f"   Traceback:\n{bug['traceback']}")
else:
    print("\n✅ All commands executed without errors!")
