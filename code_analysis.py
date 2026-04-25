"""Code analysis to find potential bugs."""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("="*60)
print("CODE ANALYSIS - POTENTIAL BUGS")
print("="*60)

bugs = []

# Bug #2: Potential race condition in resin_monitor_loop
bugs.append({
    "id": 2,
    "severity": "Low",
    "file": "botdailygi/background/jobs.py",
    "line": "217-218",
    "title": "Potential race condition when saving resin config",
    "description": """
The resin_monitor_loop modifies the config dict and saves it at line 218.
However, if multiple accounts trigger notifications simultaneously, the config
could be modified between load and save, potentially losing updates.

Current code:
```python
if changed:
    save_resin_config(config)
```

The config is loaded once at line 95, modified throughout the loop, then saved.
If the file is modified externally or by another process, changes could be lost.
""",
    "impact": "Low - unlikely in single-threaded bot, but could cause notification state loss",
    "recommendation": "Consider using file locking or atomic writes for config updates"
})

# Bug #3: Cache invalidation issue in account_info_cache
bugs.append({
    "id": 3,
    "severity": "Low",
    "file": "botdailygi/background/jobs.py",
    "line": "90-92, 144",
    "title": "Account info cache not cleared when account removed",
    "description": """
The account_info_cache at line 90 stores account info with TTL of 3600s.
When an account is removed, the cache entry persists until TTL expires.
The code only clears resin_state_cache (line 111-112) but not account_info_cache.

This could cause stale data to be used if an account is removed and re-added
with different credentials within the cache TTL window.
""",
    "impact": "Low - minor data staleness issue",
    "recommendation": "Clear account_info_cache entries for removed accounts at line 111-112"
})

# Bug #4: Missing error handling in _render_checkin_lines
bugs.append({
    "id": 4,
    "severity": "Low",
    "file": "botdailygi/background/jobs.py",
    "line": "33-36",
    "title": "No error handling in _render_checkin_lines",
    "description": """
The function imports and calls _render_checkin_result without error handling.
If any result item is malformed or the render function raises an exception,
the entire checkin notification will fail.

Current code:
```python
def _render_checkin_lines(results: list[dict]) -> str:
    from botdailygi.commands.checkin import _render_checkin_result
    return "\\n".join(_render_checkin_result(TELEGRAM_CHAT_ID, item) for item in results)
```
""",
    "impact": "Low - could cause checkin notifications to fail silently",
    "recommendation": "Add try-except around each render call to handle malformed results"
})

print(f"\nFound {len(bugs)} potential bugs:\n")

for bug in bugs:
    print(f"Bug #{bug['id']}: {bug['title']}")
    print(f"Severity: {bug['severity']}")
    print(f"File: {bug['file']}:{bug['line']}")
    print(f"Description: {bug['description']}")
    print(f"Impact: {bug['impact']}")
    print(f"Recommendation: {bug['recommendation']}")
    print("="*60)
    print()

print(f"\nTotal: {len(bugs)} potential issues identified")
print("\nNote: These are potential issues found through code analysis.")
print("They may not manifest as runtime bugs in normal operation.")
