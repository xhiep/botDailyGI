"""Deep testing script for edge cases and runtime issues."""
import sys
import io
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from botdailygi.services.accounts import read_accounts
from botdailygi.services.codes import load_codes_from_file, load_blacklist
from botdailygi.services.resin_config import load_resin_config
from botdailygi.services.hoyolab import get_account_info_cached, get_realtime_notes
from botdailygi.config import TELEGRAM_CHAT_ID

bugs_found = []

def test_edge_case(name, func):
    """Test an edge case and catch any errors."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    try:
        result = func()
        print(f"✅ {name} - PASSED")
        if result is not None:
            print(f"   Result: {result}")
        return True
    except Exception as e:
        error_msg = f"❌ {name} - FAILED: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        bugs_found.append({
            "test": name,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return False

print("Starting edge case testing...")

# Test data loading functions
test_edge_case("Load accounts", lambda: read_accounts())
test_edge_case("Load codes", lambda: load_codes_from_file())
test_edge_case("Load blacklist", lambda: load_blacklist())
test_edge_case("Load resin config", lambda: load_resin_config())

# Test with actual accounts
accounts = read_accounts()
if accounts:
    print(f"\nFound {len(accounts)} accounts, testing API calls...")
    for entry in accounts[:1]:  # Test first account only
        name = entry.get("name", "?")
        cookies = entry.get("cookies", {})

        test_edge_case(
            f"Get account info for {name}",
            lambda: get_account_info_cached(cookies)
        )

        info = get_account_info_cached(cookies)
        if info:
            uid, nickname, region = info
            test_edge_case(
                f"Get realtime notes for {name}",
                lambda: get_realtime_notes(cookies, uid, region)
            )

# Test empty/invalid inputs
print("\n" + "="*60)
print("Testing error handling with invalid inputs...")
print("="*60)

test_edge_case(
    "Get account info with empty cookies",
    lambda: get_account_info_cached({})
)

test_edge_case(
    "Get realtime notes with invalid UID",
    lambda: get_realtime_notes({}, "invalid", "os_asia")
)

# Summary
print(f"\n{'='*60}")
print(f"EDGE CASE TEST SUMMARY")
print(f"{'='*60}")
print(f"Total bugs found: {len(bugs_found)}")

if bugs_found:
    print("\n🐛 BUGS FOUND:")
    for i, bug in enumerate(bugs_found, 1):
        print(f"\n{i}. {bug['test']}")
        print(f"   Error: {bug['error']}")
else:
    print("\n✅ All edge cases handled correctly!")
