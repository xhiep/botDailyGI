# Manual Testing Checklist

## Test Commands

### ✓ Basic Commands
- [ ] /start - Check language selection buttons
- [ ] /help - Verify help text displays
- [ ] /status - Check status display with new icons (✓/✗)
- [ ] /lang - Test language switching

### ✓ Account Management
- [ ] /accounts - List accounts with new divider widths
- [ ] /uid - Display UIDs with standardized spacing

### ✓ Profile Commands
- [ ] /stats - Check stats display with new dividers
- [ ] /characters - Verify character list formatting
- [ ] /abyss - Test abyss display (current)
- [ ] /abyss prev - Test previous abyss

### ✓ Game Commands
- [ ] /checkin - Manual check-in with new progress animation
- [ ] /resin - Check resin display
- [ ] /redeem <code> - Test code redemption
- [ ] /redeemall - Batch redeem test

### ✓ Schedule
- [ ] /livestream - Check livestream schedule display

## UI Elements to Verify

### Icons
- [ ] Progress spinner: ○◔◑◕●◕◑◔ (not ⠋⠙⠹⠸⠼⠴⠦⠧)
- [ ] Success: ✓ Hoàn tất (not ✨)
- [ ] Error: ✗ Có lỗi (not ⚠️)
- [ ] Thread status: ✓/✗ (consistent)

### Spacing
- [ ] Short dividers: 12 chars (─────────────)
- [ ] Medium dividers: 18 chars
- [ ] Long dividers: 24 chars
- [ ] Meter bars: 10 chars width

### Animation
- [ ] Progress messages show spinner animation
- [ ] Spinner cycles through frames smoothly
- [ ] Final messages show ✓ or ✗

## Edge Cases
- [ ] No accounts logged in
- [ ] Invalid command
- [ ] Network error handling
- [ ] Concurrent command execution
- [ ] Long text truncation

## Performance
- [ ] Commands respond quickly
- [ ] No memory leaks
- [ ] Background threads running
- [ ] Locks working properly
