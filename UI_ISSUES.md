# UI Issues Found - 2026-04-25

## Phân tích so sánh với DESIGN.md

### 1. ICON & SYMBOLS

#### ❌ Lỗi tìm được:
- **progress.py:9** - Sử dụng spinner frames `⠋⠙⠹⠸⠼⠴⠦⠧` - không theo Apple style
- **progress.py:42** - Icon `✨ Hoàn tất` - quá nhiều emoji, không tối giản
- **progress.py:51** - Icon `⚠️ Có lỗi xảy ra` - cần đơn giản hóa
- **text.py:40** - Default icon `•` cho account heading - tốt, nhưng cần kiểm tra consistency
- **status.py:34** - Mixed icons: `✓`, `✗` - cần thống nhất
- **status.py:144** - Thread status icons không consistent
- **common.py:32-40** - Element icons sử dụng emoji - cần review xem có phù hợp không

#### 📋 Cần kiểm tra:
- Tất cả emoji icons trong commands
- Consistency của success/error/warning icons
- Spinner animation có phù hợp với Apple minimal style không

### 2. TYPOGRAPHY

#### ❌ Lỗi tìm được:
- **Không có font family definition** - DESIGN.md yêu cầu SF Pro Display/Text
- **Không có typography scale** - thiếu size hierarchy (80px, 56px, 48px...)
- **Không có line-height rules** - DESIGN.md có chi tiết 1.00-1.47
- **Không có letter-spacing** - DESIGN.md có -1.2px đến 0.352px

#### 📋 Note:
- Telegram bot text-based nên không control được font
- Nhưng có thể optimize text hierarchy và spacing

### 3. COLOR PALETTE

#### ❌ Lỗi tìm được:
- **Không có color constants** - không thấy định nghĩa màu theo DESIGN.md
- **Không có color roles** - thiếu Primary/Secondary/Accent colors
- DESIGN.md yêu cầu:
  - `#000000` - Absolute Black
  - `#f5f5f7` - Pale Apple Gray  
  - `#0071e3` - Apple Action Blue
  - `#6e6e73` - Secondary Neutral Gray
  - etc.

#### 📋 Note:
- Telegram bot không support custom colors trong text
- Nhưng có thể dùng cho web dashboard nếu có

### 4. SPACING & LAYOUT

#### ❌ Lỗi tìm được:
- **text.py:4** - `divider(width=12)` - hardcoded, không có spacing system
- **text.py:9** - `meter_bar(width=10)` - hardcoded width
- **Không có spacing constants** - DESIGN.md yêu cầu 8px base unit
- **Không có consistent padding/margin** - thiếu spacing scale (2,4,6,7,8,9,10,12,14,17,20px)

#### 📋 Cần fix:
- Tạo spacing constants
- Standardize divider widths
- Consistent meter bar widths

### 5. COMPONENT STYLING

#### ❌ Lỗi tìm được:
- **progress.py:21** - Format `{text}\n\n{frame} Đang xử lý...` - spacing không consistent
- **progress.py:42** - Format `✨ Hoàn tất\n\n{text}` - cần review spacing
- **status.py:85-91** - Header format không có clear hierarchy
- **Divider usage** - width varies (12, 18, 20, 21) - không consistent

#### 📋 Cần standardize:
- Message format templates
- Spacing between sections
- Header/body/footer hierarchy

### 6. ANIMATION & INTERACTION

#### ❌ Lỗi tìm được:
- **progress.py:9** - Spinner animation `_FRAMES` - 8 frames, cần review tốc độ
- **Không có animation timing** - thiếu duration/easing definitions
- **Không có loading states** - chỉ có spinner, thiếu skeleton/placeholder

#### 📋 Note:
- Telegram bot giới hạn animation
- Nhưng có thể optimize spinner frames

### 7. BORDER RADIUS

#### ❌ Không áp dụng được:
- Telegram text-based bot không có border radius
- DESIGN.md radius scale (5px, 8-12px, 16-18px, 28-36px) không relevant

### 8. TEXT FORMATTING

#### ❌ Lỗi tìm được:
- **text.py:17-27** - `md_escape()` - escape characters, cần review
- **text.py:30-32** - `md_code()` - format code blocks
- **Inconsistent text formatting** - một số chỗ dùng bold, italic, code không đồng nhất

#### 📋 Cần review:
- Markdown formatting consistency
- Code block usage
- Bold/italic usage rules

### 9. ERROR HANDLING UI

#### ❌ Lỗi tìm được:
- **progress.py:48-55** - `fail()` method format `⚠️ Có lỗi xảy ra\n\n{text}`
- **Không có error severity levels** - thiếu warning/error/critical distinction
- **Error messages không có hint/action** - thiếu "what to do next"

#### 📋 Cần improve:
- Error message templates
- Severity indicators
- Actionable hints

### 10. ACCESSIBILITY

#### ❌ Lỗi tìm được:
- **Emoji overuse** - có thể gây khó đọc với screen readers
- **Không có alt text** - cho các icon/emoji
- **Color-only indicators** - nếu có web UI, cần text labels

#### 📋 Cần review:
- Emoji usage guidelines
- Text alternatives
- Screen reader compatibility

---

## Summary

### Critical Issues (Cần fix ngay):
1. ❌ Inconsistent spacing (divider widths: 12, 18, 20, 21)
2. ❌ Inconsistent icons (✓, ✗, ✨, ⚠️, •)
3. ❌ Progress message format không standardized
4. ❌ Không có spacing constants/system

### Medium Priority:
5. ⚠️ Spinner animation cần review
6. ⚠️ Error message format cần improve
7. ⚠️ Text formatting consistency

### Low Priority (Nice to have):
8. 💡 Typography scale (limited by Telegram)
9. 💡 Color system (for future web UI)
10. 💡 Animation timing definitions

---

## Next Steps:
1. Tạo constants file cho spacing, icons
2. Standardize divider widths
3. Unify progress message formats
4. Review và reduce emoji usage
5. Create component templates
