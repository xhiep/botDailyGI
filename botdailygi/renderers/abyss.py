# -*- coding: utf-8 -*-
"""
abyss_render.py — Spiral Abyss image renderer (Pillow).
Public API: render_abyss_image(ab, nickname, label, live_names) → path | None
"""
import io, math, tempfile
from concurrent.futures import ThreadPoolExecutor
import datetime

from botdailygi.clients.http import HTTP
from botdailygi.runtime.logging import log
from botdailygi.runtime.state import VN_TZ

# ─────────────────────────────────────────
# AVATAR ID → NAME fallback map
# ─────────────────────────────────────────
AVATAR_NAMES: dict = {
    # Mondstadt / Liyue / Inazuma
    10000002: "Kamisato Ayaka", 10000003: "Qiqi",
    10000005: "Traveler",       10000006: "Lisa",
    10000007: "Traveler",       10000014: "Barbara",
    10000015: "Kaeya",          10000016: "Diluc",
    10000020: "Razor",          10000021: "Amber",
    10000022: "Venti",          10000023: "Xiangling",
    10000024: "Beidou",         10000025: "Xingqiu",
    10000026: "Xiao",           10000027: "Ningguang",
    10000029: "Klee",           10000030: "Zhongli",
    10000031: "Fischl",         10000032: "Bennett",
    10000033: "Tartaglia",      10000034: "Noelle",
    10000036: "Chongyun",       10000037: "Ganyu",
    10000038: "Albedo",         10000039: "Diona",
    10000041: "Mona",           10000042: "Keqing",
    10000043: "Sucrose",        10000044: "Xinyan",
    10000045: "Rosaria",        10000046: "Hu Tao",
    10000047: "Kazuha",         10000048: "Yanfei",
    10000049: "Yoimiya",        10000050: "Thoma",
    10000051: "Eula",           10000052: "Raiden Shogun",
    10000053: "Sayu",           10000054: "Kokomi",
    10000055: "Gorou",          10000056: "Kujou Sara",
    10000057: "Itto",           10000058: "Yae Miko",
    10000059: "Heizou",         10000060: "Yelan",
    10000061: "Aloy",           10000062: "Shenhe",
    10000063: "Yun Jin",        10000064: "Kuki Shinobu",
    10000065: "Kamisato Ayato",
    # Sumeru
    10000066: "Collei",         10000067: "Dori",
    10000068: "Tighnari",       10000069: "Nilou",
    10000070: "Cyno",           10000071: "Candace",
    10000072: "Nahida",         10000073: "Layla",
    10000074: "Wanderer",       10000075: "Faruzan",
    10000076: "Yaoyao",         10000077: "Alhaitham",
    10000078: "Dehya",          10000079: "Mika",
    10000080: "Kaveh",          10000081: "Baizhu",
    # Fontaine
    10000082: "Lynette",        10000083: "Lyney",
    10000084: "Freminet",       10000085: "Wriothesley",
    10000086: "Neuvillette",    10000087: "Charlotte",
    10000088: "Furina",         10000089: "Chevreuse",
    10000090: "Navia",          10000091: "Gaming",
    10000092: "Xianyun",        10000093: "Chiori",
    10000094: "Arlecchino",     10000095: "Sigewinne",
    10000096: "Sethos",         10000097: "Clorinde",
    10000098: "Emilie",
    # Natlan
    10000099: "Kachina",        10000100: "Kinich",
    10000101: "Mualani",        10000102: "Xilonen",
    10000103: "Chasca",         10000104: "Ororon",
    10000105: "Mavuika",        10000106: "Citlali",
    # 5.3+ — KHÔNG hardcode vì ID chưa chắc chắn.
    # Dùng live_names (từ rank data) thay thế.
}

# Font cache — load 1 lần duy nhất
_FONT_CACHE: dict = {}


def render_abyss_image(ab: dict, nickname: str, label: str, live_names: dict):
    """Vẽ kết quả Spiral Abyss thành ảnh PNG.
    Trả về path file PNG, hoặc None nếu PIL không có / lỗi.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    try:
        # ── Palette ──────────────────────────────────────────────────────────
        C_BG     = (10,  14,  20)
        C_HEADER = (16,  24,  50)
        C_CARD   = (20,  26,  36)
        C_CARD2  = (28,  36,  54)
        C_FLOOR  = (22,  38,  74)
        C_BORDER = (42,  50,  65)
        C_ACCENT = (58, 142, 255)
        C_GOLD   = (230, 180,  48)
        C_GOLD2  = (255, 215,  80)
        C_WHITE  = (230, 238, 248)
        C_GREY   = (115, 128, 148)
        C_5STAR  = (200, 148,  36)
        C_4STAR  = (118,  88, 180)

        SCALE = 2
        W     = 900
        PAD   = 22

        # ── Font helper ───────────────────────────────────────────────────────
        def _f(size: int, bold: bool = False):
            key = (size, bold)
            if key in _FONT_CACHE:
                return _FONT_CACHE[key]
            bold_paths = [
                "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/noto/NotoSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ]
            regular_paths = [
                "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/noto/NotoSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            ]
            for p in (bold_paths if bold else regular_paths):
                try:
                    f = ImageFont.truetype(p, size * SCALE)
                    _FONT_CACHE[key] = f
                    return f
                except Exception:
                    pass
            try:
                fb = ImageFont.load_default(size=max(size * SCALE, 10))
            except TypeError:
                fb = ImageFont.load_default()
            _FONT_CACHE[key] = fb
            return fb

        def _tw(d_obj, text, font):
            try:    return d_obj.textlength(text, font=font)
            except: return len(text) * getattr(font, "size", 16)

        def _draw_star(d_obj, cx, cy, r, color, filled=True):
            pts = []
            for i in range(10):
                angle = math.pi / 2 + i * math.pi / 5
                rad   = r if i % 2 == 0 else r * 0.42
                pts.append((cx + rad * math.cos(angle), cy - rad * math.sin(angle)))
            if filled: d_obj.polygon(pts, fill=color)
            else:      d_obj.polygon(pts, outline=color, fill=C_CARD2)

        # ── Avatar helpers ────────────────────────────────────────────────────
        AV_R = 34 * SCALE

        def _av_name(item: dict) -> str:
            name = (item.get("name") or "").strip()
            if not name:
                aid = item.get("id") or item.get("avatar_id")
                if aid:
                    aid  = int(aid)
                    name = (live_names.get(aid) or AVATAR_NAMES.get(aid) or f"#{aid % 10000}")
            return name or "?"

        def _av_rarity(item: dict) -> int:
            return int(item.get("rarity", 4))

        def _av_icon(item: dict) -> str:
            return item.get("icon") or item.get("avatar_icon") or item.get("image") or ""

        def _dl_icon(url: str):
            try:
                r   = HTTP.get(url, timeout=6)
                raw = Image.open(io.BytesIO(r.content)).convert("RGBA")
                D   = AV_R * 2
                raw = raw.resize((D, D), Image.LANCZOS)
                mask = Image.new("L", (D, D), 0)
                ImageDraw.Draw(mask).ellipse([0, 0, D - 1, D - 1], fill=255)
                out = Image.new("RGBA", (D, D), (0, 0, 0, 0))
                out.paste(raw, mask=mask)
                return out
            except Exception:
                return None

        # Collect icon URLs
        all_urls: set = set()
        for rk in ("damage_rank","take_damage_rank","kill_rank","energy_skill_rank","reveal_rank"):
            for it in ab.get(rk, []):
                u = _av_icon(it)
                if u: all_urls.add(u)
        for fl in ab.get("floors", []):
            for lvl in fl.get("levels", []):
                for bat in lvl.get("battles", []):
                    for av in bat.get("avatars", []):
                        u = _av_icon(av)
                        if u: all_urls.add(u)

        icon_cache: dict = {}
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = {ex.submit(_dl_icon, u): u for u in all_urls}
            for fut in futures:
                icon_cache[futures[fut]] = fut.result()

        def _get_icon(url):
            return icon_cache.get(url)

        def _draw_avatar(canvas_2x, d_obj, cx, cy, item):
            rarity = _av_rarity(item)
            url    = _av_icon(item)
            R      = AV_R
            bc     = C_5STAR if rarity >= 5 else C_4STAR
            d_obj.ellipse([cx - R - 3, cy - R - 3, cx + R + 3, cy + R + 3], fill=bc)
            img = _get_icon(url)
            if img:
                canvas_2x.paste(img, (cx - R, cy - R), img)
            else:
                d_obj.ellipse([cx - R, cy - R, cx + R, cy + R], fill=C_CARD2)
                init = _av_name(item)[:2].upper()
                fn   = _f(12, True)
                tw   = _tw(d_obj, init, fn)
                d_obj.text((cx - tw // 2, cy - R // 2), init, font=fn, fill=C_WHITE)

        # ── Layout vars ───────────────────────────────────────────────────────
        AV_DIAM  = AV_R * 2
        AV_GAP   = 14 * SCALE
        NAME_H   = 18 * SCALE
        AV_BLOCK = AV_DIAM + NAME_H + 6 * SCALE

        def sc(v): return v * SCALE

        FLOOR_H  = 44
        ROOM_PAD = 10
        HALF_H   = AV_BLOCK // SCALE + 20

        def _battle_row_h(battles):
            return ROOM_PAD + 20 + len(battles) * (HALF_H + 6) + ROOM_PAD

        # ── Metadata ─────────────────────────────────────────────────────────
        floors_sorted = sorted(ab.get("floors", []), key=lambda x: x.get("index", 0), reverse=True)
        total_star    = ab.get("total_star", 0)
        max_floor     = ab.get("max_floor", "?")
        total_battles = ab.get("total_battle_times") or ab.get("total_battles", 0)
        total_wins    = ab.get("total_win_times")    or ab.get("total_wins", 0)
        start_dt = datetime.datetime.fromtimestamp(int(ab.get("start_time", 0)), VN_TZ).strftime("%d/%m")
        end_dt   = datetime.datetime.fromtimestamp(int(ab.get("end_time",   0)), VN_TZ).strftime("%d/%m/%Y")
        reveal   = ab.get("reveal_rank", [])

        # ── Canvas height ─────────────────────────────────────────────────────
        H = 100 + 68
        if reveal:
            rv_cols   = min(len(reveal[:8]), 8)
            rv_slot_w = (AV_DIAM + AV_GAP) // SCALE
            rows_rv   = max(1, math.ceil(rv_cols * rv_slot_w / (W - PAD * 2)))
            H += 12 + 22 + rows_rv * (AV_BLOCK // SCALE + 12) + 8
        for fl in floors_sorted:
            H += FLOOR_H + 4
            for lvl in fl.get("levels", []):
                if lvl.get("battles"):
                    H += _battle_row_h(lvl["battles"])
            H += 12
        H += 20

        # ── Render 2× ─────────────────────────────────────────────────────────
        W2 = W * SCALE; H2 = H * SCALE
        canvas = Image.new("RGB", (W2, H2), C_BG)
        d      = ImageDraw.Draw(canvas)
        y2     = 0

        def sy(v): return v * SCALE

        # Header
        HH = 100
        d.rectangle([0, 0, W2, sy(HH)], fill=C_HEADER)
        d.rectangle([0, 0, sc(6), sy(HH)], fill=C_ACCENT)
        d.text((sc(PAD + 10), sc(12)), f"SPIRAL ABYSS  [{label}]", font=_f(22, True), fill=C_ACCENT)
        d.text((sc(PAD + 10), sc(42)), f"{nickname}   {start_dt} -> {end_dt}", font=_f(14), fill=C_WHITE)
        bx0, by0 = sc(PAD + 10), sc(68)
        bw  = W2 - sc(PAD * 2 + 20)
        d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + sc(10)], radius=sc(5), fill=C_CARD2)
        fw  = int(bw * total_star / 36)
        if fw > 0:
            d.rounded_rectangle([bx0, by0, bx0 + fw, by0 + sc(10)], radius=sc(5), fill=C_GOLD)
        d.text((sc(PAD + 10), sc(80)),
               f"  {total_star}/36 stars   Floor {max_floor}   {total_battles} battles ({total_wins} wins)",
               font=_f(12), fill=C_GREY)
        y2 = sy(HH)

        # Stats row
        STAT_H   = 68
        d.rectangle([0, y2, W2, y2 + sy(STAT_H)], fill=C_CARD)
        d.line([0, y2, W2, y2], fill=C_BORDER, width=sc(1))
        stat_defs = [
            ("damage_rank","DMG"), ("take_damage_rank","DEF"),
            ("kill_rank","KILLS"), ("energy_skill_rank","BURST"),
        ]
        sx_list = []
        for rk, lbl in stat_defs:
            top = (ab.get(rk) or [None])[0]
            if top:
                n   = _av_name(top)
                v   = top.get("value", 0)
                val = f"{v:,}" if "damage" in rk else str(v)
                sx_list.append((lbl, val, n))
        col_w = W2 // max(len(sx_list), 1) if sx_list else W2 // 2
        for i, (lbl, val, name) in enumerate(sx_list[:4]):
            cx_s = sc(PAD) + i * col_w; cy_s = y2 + sc(10)
            d.text((cx_s, cy_s),              lbl,  font=_f(10),       fill=C_GREY)
            d.text((cx_s, cy_s + sc(14)),     val,  font=_f(14, True), fill=C_GOLD2)
            d.text((cx_s, cy_s + sc(34)),     name, font=_f(11),       fill=C_WHITE)
        y2 += sy(STAT_H)

        # Most used
        if reveal:
            d.rectangle([0, y2, W2, y2 + sy(10)], fill=C_BG); y2 += sy(10)
            d.text((sc(PAD), y2 + sc(2)), "MOST USED :", font=_f(12, True), fill=C_GOLD)
            y2 += sy(22)
            rx2 = sc(PAD)
            for rv in reveal[:8]:
                rval   = rv.get("value", 0)
                slot_w = AV_DIAM + AV_GAP
                if rx2 + slot_w > W2 - sc(PAD):
                    rx2 = sc(PAD); y2 += AV_BLOCK + sc(12)
                av_cx = rx2 + AV_R; av_cy = y2 + AV_R
                _draw_avatar(canvas, d, av_cx, av_cy, rv)
                fn12      = _f(10)
                rname     = _av_name(rv)
                name_s    = rname if len(rname) <= 9 else rname[:8] + "."
                tw_n      = _tw(d, name_s, fn12)
                d.text((av_cx - tw_n // 2, av_cy + AV_R + sc(3)),  name_s,   font=fn12, fill=C_WHITE)
                count_txt = f"x{rval}"; tw_c = _tw(d, count_txt, fn12)
                d.text((av_cx - tw_c // 2, av_cy + AV_R + sc(15)), count_txt, font=fn12, fill=C_GOLD)
                rx2 += slot_w
            y2 += AV_BLOCK + sc(12)

        # Floors
        STAR_R    = 8
        FL_STAR_R = 9
        for fl in floors_sorted:
            fl_idx  = fl.get("index", "?")
            fl_star = fl.get("star", 0)
            fl_max  = fl.get("max_star", 9)
            d.rectangle([0, y2, W2, y2 + sy(FLOOR_H)], fill=C_FLOOR)
            d.rectangle([0, y2, sc(6), y2 + sy(FLOOR_H)], fill=C_GOLD)
            d.text((sc(PAD + 10), y2 + sc(10)), f"FLOOR {fl_idx}", font=_f(17, True), fill=C_GOLD2)
            sx_off = sc(PAD + 10 + 80)
            for si in range(fl_max):
                _draw_star(d,
                           sx_off + sc(si * (FL_STAR_R * 2 + 5) + FL_STAR_R),
                           y2 + sy(FLOOR_H // 2), sc(FL_STAR_R),
                           C_GOLD2 if si < fl_star else (50, 60, 80), filled=(si < fl_star))
            score_txt = f"{fl_star}/{fl_max}"
            stw = _tw(d, score_txt, _f(14, True))
            d.text((W2 - sc(PAD) - stw, y2 + sc(12)), score_txt, font=_f(14, True), fill=C_WHITE)
            y2 += sy(FLOOR_H + 4)

            for lvl in fl.get("levels", []):
                battles = lvl.get("battles", [])
                if not battles: continue
                ch_idx  = lvl.get("index", "?")
                ch_star = lvl.get("star", 0)
                rh      = _battle_row_h(battles)
                d.rectangle([0, y2, W2, y2 + sy(rh)], fill=C_CARD)
                d.line([sc(4), y2, sc(4), y2 + sy(rh)], fill=C_ACCENT, width=sc(2))
                d.text((sc(PAD), y2 + sc(ROOM_PAD)), f"Chamber {ch_idx}", font=_f(13, True), fill=C_WHITE)
                for si in range(3):
                    _draw_star(d,
                               sc(PAD + 110 + si * (STAR_R * 2 + 4) + STAR_R),
                               y2 + sy(ROOM_PAD + STAR_R + 2), sc(STAR_R),
                               C_GOLD2 if si < ch_star else (50, 60, 80), filled=(si < ch_star))
                ry2 = y2 + sy(ROOM_PAD + 20)
                for hi, battle in enumerate(battles):
                    avs        = battle.get("avatars", [])
                    two_halves = len(battles) > 1
                    if two_halves:
                        d.text((sc(PAD), ry2 + sc(6)), f"[{hi + 1}]", font=_f(11, True), fill=C_ACCENT)
                        ax2 = sc(PAD) + sc(34)
                    else:
                        ax2 = sc(PAD)
                    for av in avs:
                        av_cx2 = ax2 + AV_R; av_cy2 = ry2 + AV_R
                        _draw_avatar(canvas, d, av_cx2, av_cy2, av)
                        aname   = _av_name(av)
                        aname_s = aname if len(aname) <= 9 else aname[:8] + "."
                        fn10    = _f(10)
                        atw     = _tw(d, aname_s, fn10)
                        d.text((av_cx2 - atw // 2, av_cy2 + AV_R + sc(3)), aname_s, font=fn10, fill=C_GREY)
                        ax2 += AV_DIAM + AV_GAP
                    ry2 += sy(HALF_H + 6)
                d.line([sc(PAD), y2 + sy(rh) - sc(2), W2 - sc(PAD), y2 + sy(rh) - sc(2)],
                       fill=C_BORDER, width=sc(1))
                y2 += sy(rh)
            y2 += sy(12)

        # Downsample 2× → 1×
        final = canvas.resize((W, H), Image.LANCZOS)
        tmp   = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=tempfile.gettempdir())
        final.save(tmp.name, "PNG", optimize=True)
        tmp.close()
        return tmp.name

    except Exception as e:
        log.warning(f"[abyss_img] Lỗi render: {e}")
        return None
