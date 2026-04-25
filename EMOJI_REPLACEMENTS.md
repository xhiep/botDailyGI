# Emoji Replacements for Apple Design System Compliance

## Principle
DESIGN.md requires minimal icons, avoiding complex emojis. Replace with simple text indicators: `✓`, `✗`, `•`, `○`, `⚠`

## Files to Fix

### 1. botdailygi/i18n/catalog.py
**Complex emojis found in translation strings:**

#### Success indicators (✅ → ✓)
- Lines with `✅` - Replace with `✓`
- Used in: acct.status_ok, acct.add_success, checkin.success, code.success, lang.changed, etc.

#### Error indicators (❌ → ✗)
- Lines with `❌` - Replace with `✗`
- Used in: gen.error, gen.conn_error, gen.no_uid, acct.add_dup, etc.

#### Loading/Info (✨ → •)
- Lines with `✨` - Replace with `•`
- Used in: status.fetching, resin.fetching, start.msg, help messages

#### Element icons (🔥💧⚡🌿❄️🪨🌬️ → Already fixed in common.py)
- Already replaced with single letters: P, H, E, D, C, G, A

#### Heart icons (❤️🤍 → Already fixed in profile.py)
- Already replaced: `✓` for max fetter, `○{n}` for others

#### Other complex emojis to replace:
- `🔮` (transformer) → `○` or `•`
- `👤` (user) → Already fixed to `•` in renderers/text.py
- `⚗️` (resin alert) → `⚠`
- `🚨` (critical alert) → `⚠`
- `🔴` (critical) → `✗`
- `💡` (hint) → `•`
- `⏳` (waiting) → `○`
- `🔔` (notification) → `•`
- `💧` (resin/water) → Keep or replace with "R" for Resin
- `⚡` (energy) → Keep as simple indicator or use `•`

## Strategy
Since catalog.py contains user-facing messages in Vietnamese and English, we need to:
1. Replace complex emojis with minimal indicators
2. Keep simple indicators like `✓`, `✗`, `•`, `○`, `⚠` (these are Apple-compliant)
3. Test that messages still make sense after replacement

## Next Steps
1. Read full catalog.py file
2. Create replacement mapping
3. Apply replacements systematically
4. Verify bot still works
5. Test all commands to ensure UI consistency
