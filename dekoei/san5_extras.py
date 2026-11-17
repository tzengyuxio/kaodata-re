"""三國志V PK (PC-98, san5pk-pc98): event pictures, scenes, maps, items (道具) and the MESSAGE.S5 texts.

Formats and evidence: notes/san5.md「事件、插圖、道具」. MAIN.EXE addresses are file offsets of the PK MAIN.EXE.
- Raw pictures (no header) are packed planar: each row is w/8 groups of 4 bytes, the bytes are planes 0-3 of 8 pixels
  (MSB leftmost), so a w x h picture is w*h/2 bytes (`rcp`). The game draws them with 0x1041:d296
  (push x, y, w, h, offset in the buffer).
- ESTL.S5 (LS11, 34 parts) is 3 planes in the same order, 240 x 160, colours 8-15 (like the faces).
- Palette: MAIN.EXE DGROUP 0x910 (16 x B,R,G nibbles); colours 8-15 are the face colours, 0-7 change with the season
  on the main map (DGROUP 0x940 + 24 x season, MAIN.EXE 0x18dad).
- MAINMAP.S5 / MAP256.S5: 50 columns of 16 x 592 pixels (MAIN.EXE 0x88540, column size 0x77fc); a 16-colour column
  is 4 planes one after the other, a 256-colour one is 1 byte per pixel; PAL256.S5 is 4 seasons x 213 colours
  (indices 32-244) of B, R, G bytes.
- Items: MAIN.EXE 0x48e80, 32 x 16 bytes (3 bonus bytes, 13-byte Shift-JIS name); per scenario, the last 1100 bytes
  of an SNDATA.S5 part are 100 x 11-byte records whose u16 +0 is the holder (1-based record index of the scenario,
  SNDATA then TAIKI); ITEM.S5 picture k (80 x 80, 3200 bytes) is item k's (MAIN.EXE 0xb4c3a).
- MESSAGE.S5 (LS11, 56 parts of a u16 count and u16 offsets): Shift-JIS with half-width kana shown as hiragana,
  01 22 line attribute, 01 xx + 2 bytes control, 02 + 2 bytes variable, 0A line break, 05 05 05 end of a variant.
"""
import csv
import json
import os
import re
import struct

import click
from PIL import Image, ImageDraw

import biography
import ls11
import sango
from utils import unpack_npk

DGROUP = 0x51250  # MAIN.EXE (PK) file offset of DGROUP
PALETTE = DGROUP + 0x910  # 16 x (B, R, G)
SEASONS = DGROUP + 0x940  # 4 x 8 colours of the main map, chosen by MAIN.EXE 0x18dad
SEASON_NAMES = ["1-3月", "4-6月", "7-9月", "10-12月"]
ITEMS, ITEM_SIZE, ITEM_COUNT = 0x48E80, 16, 32  # MAIN.EXE (PK); the copy at 0x494C0 is the same
ITEMS_DOS = 0x4FA20  # san5pk-dos MAIN.EXE, the same table in Chinese
ITEM_TAIL, HOLDER_SIZE = 1100, 11  # SNDATA.S5 scenario tail: 100 x 11-byte item records
GAIJI = {**sango.SAN5_PC98_GAIJI, 0xEBC8: "釭", 0xEBF8: "蒺"}  # FONT.S5 glyphs 41 and 89

# ESTL.S5 part -> name (read off the pictures, 🟡)
ESTL_NAMES = ["暴動", "疫病", "蝗害", "暴風", "洪水", "豐收", "飢荒", "臨終", "出陣", "君主", "朝廷", "美女",
              "婚姻", "行刺", "仕官", "密議", "閱兵", "行軍", "夜談", "上奏", "火攻", "攻城戰", "騎兵戰", "騎將",
              "討取", "謁見", "拜謁", "突擊", "混戰", "宴會", "大軍", "宮殿", "對陣", "亂戰"]
# CANMB.S5 entries 0-8: the backgrounds of the animated scenes (names read off the pictures, 🟡)
CANMB_SCENES = [(256, "室內（屏風）"), (256, "街道"), (256, "宅門"), (256, "城門"), (256, "庭院"), (256, "空房"),
                (256, "宴會廳"), (400, "大廳（玉座）"), (400, "謁見室")]


_SPREAD = [sum((b >> (7 - i) & 1) << (8 * (7 - i)) for i in range(8)) for b in range(256)]


def rcp(buf, w, h, planes=4):
    """Packed planar (row, 8-pixel group, plane) -> 'P' image of colour indices."""
    out = bytearray()
    for i in range(0, w * h * planes // 8, planes):
        v = 0
        for p in range(planes):
            v |= _SPREAD[buf[i + p]] << p
        out += v.to_bytes(8, "big")
    return Image.frombytes("P", (w, h), bytes(out))


def plane_seq(buf, w, h, planes=4):
    """Planes one after the other, each h rows of w/8 bytes -> 'P' image."""
    size, out = w * h // 8, bytearray()
    for i in range(size):
        v = 0
        for p in range(planes):
            v |= _SPREAD[buf[p * size + i]] << p
        out += v.to_bytes(8, "big")
    return Image.frombytes("P", (w, h), bytes(out))


def nibbles(raw):
    return [(raw[3 * i + 1] * 17, raw[3 * i + 2] * 17, raw[3 * i] * 17) for i in range(len(raw) // 3)]


def palette(main, season=None, shift=0):
    """MAIN.EXE 16-colour palette (optionally the season's colours 0-7); shift 8 maps index 0-7 to colours 8-15."""
    pal = nibbles(main[PALETTE:PALETTE + 48])
    if season is not None:
        pal[:8] = nibbles(main[SEASONS + 24 * season:SEASONS + 24 * season + 24])
    return pal[shift:] + pal[:shift]


def image(im, pal):
    im = im.copy()
    im.putpalette([v for c in pal for v in c] + [0] * (768 - 3 * len(pal)))
    return im.convert("RGB")


def read(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return f.read()


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def pictures(game_dir):
    """(file name, group, name, source, evidence, image) of the named pictures."""
    main = read(game_dir, "MAIN.EXE")
    pal, shifted = palette(main), palette(main, shift=8)
    out = []
    for k, p in enumerate(ls11.ls11_decode_parts(read(game_dir, "ESTL.S5"))):
        out.append((f"estl-{k:02d}", "事件", ESTL_NAMES[k], f"ESTL.S5 #{k}",
                    "圖 ✅ code（0x1a41e，240×160、3 面）；名稱 🟡 看圖", image(rcp(p, 240, 160, 3), shifted)))
    # IKKIHAI.S5 (MAIN.EXE 0x8c0e0): 640 x 400 from two 320 x 400 halves; with the 624 x 116 bands (y 160, 276) it is
    # the 武術大会 version; the other pieces frame the 800 x 600 screen
    d = read(game_dir, "IKKIHAI.S5")

    def part(o, w, h):
        return image(rcp(d[o:], w, h), pal)
    field = Image.new("RGB", (640, 400))
    field.paste(part(0x13100, 320, 400), (0, 0))
    field.paste(part(0x22B00, 320, 400), (320, 0))
    hall = field.copy()
    hall.paste(part(0x39D00, 624, 116), (8, 160))
    hall.paste(part(0x42A60, 624, 116), (8, 276))
    big = Image.new("RGB", (800, 600))
    for o, x, y in [(0, 0, 4), (0x2E40, 0, 300), (0x5C80, 720, 4), (0x8AC0, 720, 300)]:
        big.paste(part(o, 80, 296), (x, y))
    big.paste(part(0xB900, 640, 56), (80, 4))
    big.paste(part(0x35700, 640, 56), (80, 540))
    big.paste(part(0xFF00, 640, 40), (80, 60))
    big.paste(field, (80, 100))
    big.paste(part(0x32500, 640, 40), (80, 500))
    out += [("ikkihai-field", "一騎討ち", "一騎討ち（戰場）", "IKKIHAI.S5 0x13100、0x22B00", "✅ code（0x8c0e0）", field),
            ("ikkihai-hall", "一騎討ち", "一騎討ち（武術大會）", "IKKIHAI.S5 0x13100、0x22B00、0x39D00、0x42A60",
             "✅ code（0x8c0e0，條件 DGROUP 0x2a00）；用途 🟡", hall),
            ("ikkihai-800x600", "一騎討ち", "一騎討ち（800×600 畫面框）", "IKKIHAI.S5 0x0–0xFF00、0x32500、0x35700",
             "各塊 ✅ code；中央與下框的位置 🟡", big)]
    b = read(game_dir, "BUDOUKAI.S5")
    out.append(("budoukai", "武術大會", "武術大會對戰表", "BUDOUKAI.S5 0", "✅ code（0xbcdd8，328×312）",
                image(rcp(b, 328, 312), pal)))
    m = read(game_dir, "IMODE.S5")  # four 320 x 200 quarters (MAIN.EXE 0xafd54): (0,0) (0,200) (320,0) (320,200)
    title = Image.new("RGB", (640, 400))
    for k, (x, y) in enumerate([(0, 0), (0, 200), (320, 0), (320, 200)]):
        title.paste(image(rcp(m[32000 * k:], 320, 200), pal), (x, y))
    out.append(("imode", "一騎討ちモード", "一騎討ちモード標題", "IMODE.S5 0–0x1F3FF",
                "排法 ✅ code（0xafd54）；色盤 🟡（只用色 1–4、8，可能另有色盤）；用途 🟡", title))
    f = read(game_dir, "FMAP.S5")
    out.append(("fmap", "地圖", "勢力分布圖", "FMAP.S5 0", "讀取 ✅ code（0x18b4f，64800 bytes）；360×360 🟡 看圖",
                image(rcp(f, 360, 360), pal)))
    c = read(game_dir, "CANMB.S5")
    n = struct.unpack_from("<H", c)[0]
    for k, (w, name) in enumerate(CANMB_SCENES):
        o, size = struct.unpack_from("<IH", c, 2 + 6 * k)
        out.append((f"canmb-{k:02d}", "場景", name, f"CANMB.S5 #{k}", "索引 ✅；寬度 🟡 看圖；名稱 🟡",
                    image(rcp(c[2 + 6 * n + o:], w, size * 2 // w), pal)))
    return out


def export_pictures(game_dir, out):
    os.makedirs(out, exist_ok=True)
    rows = []
    for fname, group, name, src, ev, im in pictures(game_dir):
        im.save(os.path.join(out, fname + ".png"))
        rows.append([fname + ".png", group, name, src, f"{im.width}x{im.height}", ev])
    write_csv(os.path.join(out, "index.csv"), ["file", "group", "name", "source", "size", "evidence"], rows)
    return len(rows)


def export_maps(game_dir, out):
    """The main map, 800 x 592: 16 colours with the 4 season groups, and the 256-colour version (PC-9821)."""
    os.makedirs(out, exist_ok=True)
    main = read(game_dir, "MAIN.EXE")
    d = read(game_dir, "MAINMAP.S5")
    idx = Image.new("P", (800, 592))
    for k in range(50):
        idx.paste(plane_seq(d[k * 4736:], 16, 592), (16 * k, 0))
    d = read(game_dir, "MAP256.S5")
    idx256 = Image.new("P", (800, 592))
    for k in range(50):
        idx256.paste(Image.frombytes("P", (16, 592), d[k * 9472:(k + 1) * 9472]), (16 * k, 0))
    pal256 = read(game_dir, "PAL256.S5")
    rows = []
    for s in range(4):
        image(idx, palette(main, s)).save(os.path.join(out, f"mainmap-{s}.png"))
        raw = pal256[639 * s:639 * (s + 1)]
        pal = [(0, 0, 0)] * 32 + [(raw[3 * i + 1], raw[3 * i + 2], raw[3 * i]) for i in range(213)]
        image(idx256, pal).save(os.path.join(out, f"map256-{s}.png"))
        rows += [[f"mainmap-{s}.png", SEASON_NAMES[s], "MAINMAP.S5", f"DGROUP 0x{0x940 + 24 * s:X}",
                  "排法 ✅ capture（guest-os-000，季節 3 的色也對上）" if s == 3 else "排法 ✅ capture；色 ✅ code"],
                 [f"map256-{s}.png", SEASON_NAMES[s], "MAP256.S5", f"PAL256.S5 第 {s} 組",
                  "排法 ✅ code（0x88540）；色的順序 B、R、G 與季節對應 🟡"]]
    write_csv(os.path.join(out, "index.csv"), ["file", "season", "source", "palette", "evidence"], rows)
    return len(rows)


def sjis_name(b):
    out, i = [], 0
    while i < len(b):
        v = b[i] << 8 | b[i + 1] if i + 1 < len(b) else b[i]
        out.append(GAIJI.get(v) or b[i:i + 2].decode("cp932", "replace"))
        i += 2
    return "".join(out)


def kaodata_ids(game_dir):
    """(scenario, 1-based record index) -> (kaodata san5pk-pc98 id, name); ids follow the face codes in order."""
    recs = list(sango.san5_records(os.path.join(game_dir, "SNDATA.S5"), os.path.join(game_dir, "TAIKI.S5"), True))
    ids, out, count = {}, {}, {}
    for scenario, name, _, p in recs:
        code = int.from_bytes(p[30:32], "little")
        ids.setdefault(code, len(ids))
        count[scenario] = count.get(scenario, 0) + 1
        out[scenario, count[scenario]] = (ids[code], name)
    return out


def export_items(game_dir, out, dos_dir=None):
    os.makedirs(os.path.join(out, "pictures"), exist_ok=True)
    main = read(game_dir, "MAIN.EXE")
    zh = read(dos_dir, "MAIN.EXE") if dos_dir else None
    pal = palette(main)
    pics = read(game_dir, "ITEM.S5")
    for k in range(len(pics) // 3200):
        image(rcp(pics[3200 * k:], 80, 80), pal).save(os.path.join(out, "pictures", f"{k:02d}.png"))
    parts = sango.san5_parts(os.path.join(game_dir, "SNDATA.S5"))
    ids = kaodata_ids(game_dir)
    rows, holders = [], []
    for k in range(ITEM_COUNT):
        r = main[ITEMS + ITEM_SIZE * k:][:ITEM_SIZE]
        name = sjis_name(r[3:].split(b"\0")[0])
        name_zh = sango.to_unicode_name(zh[ITEMS_DOS + ITEM_SIZE * k + 3:][:13].split(b"\0")[0]) if zh else ""
        per = []
        for s, part in enumerate(parts, 1):
            h = struct.unpack_from("<H", part, len(part) - ITEM_TAIL + HOLDER_SIZE * k)[0]
            if h != 0xFFFF:
                i, pname = ids.get((s, h), (None, "?"))
                per.append(f"{s:02d}:{pname}")
                holders.append([k, name, s, h, i, pname])
        rows.append([k, name, name_zh, r[0], r[1], r[2], f"pictures/{k:02d}.png", " ".join(per)])
    write_csv(os.path.join(out, "items.csv"),
              ["id", "name", "name_zh", "bonus0", "bonus1", "bonus2", "picture", "holders"], rows)
    write_csv(os.path.join(out, "holders.csv"), ["item", "name", "scenario", "record", "kaodata_id", "holder"],
              holders)
    return len(rows), len(holders), len(pics) // 3200


KATA = "。「」、・をぁぃぅぇぉゃゅょっーあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん゛゜"
VOICED = {**{a: b for a, b in zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ")}, "う": "ゔ"}
SEMI = {a: b for a, b in zip("はひふへほ", "ぱぴぷぺぽ")}


def join_marks(s):
    out = []
    for c in s:
        if c == "゛" and out and out[-1] in VOICED:
            out[-1] = VOICED[out[-1]]
        elif c == "゜" and out and out[-1] in SEMI:
            out[-1] = SEMI[out[-1]]
        else:
            out.append(c)
    return "".join(out)


def text(m, glyph):
    """MESSAGE.S5 message -> text with control codes kept as {xx:hex} / {V:hex}; glyph(2 bytes) -> str."""
    out, i = [], 0
    while i < len(m):
        b = m[i]
        if b == 5:
            i += 1
            if out and out[-1] != "\n\n":
                out.append("\n\n")
        elif b == 0x0A:
            out.append("\n")
            i += 1
        elif b == 1 and i + 1 < len(m):
            if m[i + 1] != 0x22:  # 01 22: line attribute
                out.append("{%02X:%s}" % (m[i + 1], m[i + 2:i + 4].hex()))
                i += 2
            i += 2
        elif b in (4, 6) and i + 1 < len(m):  # 04 xx / 06 xx: condition codes of the variant lists (🟡)
            out.append("{%02X:%02x}" % (b, m[i + 1]))
            i += 2
        elif b == 2 and i + 2 < len(m):
            out.append("{V:%s}" % m[i + 1:i + 3].hex())
            i += 3
        elif 0xA1 <= b <= 0xDF and glyph is ja_glyph:  # half-width kana, shown as hiragana
            out.append(KATA[b - 0xA1])
            i += 1
        elif b >= 0x81 and i + 1 < len(m):
            out.append(glyph(m[i:i + 2]))
            i += 2
        elif 0x20 <= b < 0x7F:
            out.append(chr(b))
            i += 1
        else:
            out.append("<%02X>" % b)
            i += 1
    return "".join(out).strip("\n")


def ja_glyph(b):
    v = b[0] << 8 | b[1]
    if v in GAIJI:
        return GAIJI[v]
    try:
        return b.decode("cp932")
    except UnicodeDecodeError:
        return "[%04X]" % v


def zh_glyph(b):
    try:
        return biography.koei_tw_text(b, "。") or "[%s]" % b.hex()
    except (AssertionError, KeyError, IndexError, ValueError):
        return "[%s]" % b.hex()


def plain(t):
    return re.sub(r"\{[0-9A-FV]{1,2}:[0-9a-f]*\}|<[0-9A-F]{2}>", "", t)


def messages(path):
    return [biography.offset_table(p, True) for p in ls11.ls11_decode_parts(open(path, "rb").read())]


def export_events(game_dir, out, dos_dir=None):
    os.makedirs(out, exist_ok=True)
    n = 0
    with open(os.path.join(out, "messages.jsonl"), "w", encoding="utf-8") as f:
        for lang, d, glyph in [("ja", game_dir, ja_glyph), ("zh-Hant", dos_dir, zh_glyph)]:
            if not d:
                continue
            for p, ms in enumerate(messages(os.path.join(d, "MESSAGE.S5"))):
                for i, m in enumerate(ms):
                    t = text(m, glyph)
                    t = join_marks(t) if lang == "ja" else t
                    f.write(json.dumps({"part": p, "index": i, "lang": lang, "text": t, "plain": plain(t)},
                                       ensure_ascii=False) + "\n")
                    n += 1
    return n


# unnamed fragments (re-common §11): one strip per file, cut into columns, for browsing only
UI = [("MAINWIN.S5", 272), ("BTNGRP.S5", 32), ("GRAPH.S5", 32), ("CALC.S5", 192), ("HENV.S5", 32), ("HUNIT.S5", 32),
      ("HANIME.S5", 32), ("MAPANM.S5", 16)]
SPRITES = [("IKKI1.S5", 64), ("IKKI2.S5", 64)]


def strip(im, rows=600):
    """Cut a tall picture into columns of `rows` lines."""
    cols = [im.crop((0, y, im.width, min(im.height, y + rows))) for y in range(0, im.height, rows)]
    out = Image.new("RGB", (len(cols) * (im.width + 4), min(im.height, rows) + 14), (48, 0, 48))
    for k, c in enumerate(cols):
        out.paste(c, (k * (im.width + 4), 14))
    return out


def sheet(items, path):
    out = Image.new("RGB", (max(im.width for _, im in items), sum(im.height + 6 for _, im in items)), (32, 32, 32))
    y, draw = 0, ImageDraw.Draw(out)
    for label, im in items:
        out.paste(im, (0, y))
        draw.text((2, y), label, fill=(255, 255, 0))
        y += im.height + 6
    out.save(path)


def export_fragments(game_dir, out):
    os.makedirs(out, exist_ok=True)
    pal = palette(read(game_dir, "MAIN.EXE"))

    def raw(name, w):
        d = read(game_dir, name)
        return strip(image(rcp(d, w, len(d) * 2 // w), pal))
    sheet([(f"{n} (w {w})", raw(n, w)) for n, w in UI], os.path.join(out, "ui.png"))
    sprites = [(f"{n} (w {w})", raw(n, w)) for n, w in SPRITES]
    c = read(game_dir, "CANMA.S5")
    n = struct.unpack_from("<H", c)[0]
    cels = []
    for k in range(n):
        o, size = struct.unpack_from("<IH", c, 2 + 6 * k)
        cels.append(rcp(c[2 + 6 * n + o:], 32, size * 2 // 32))
    tall = Image.new("P", (32, sum(i.height for i in cels)))
    y = 0
    for i in cels:
        tall.paste(i, (0, y))
        y += i.height
    sprites.append(("CANMA.S5 (180 cels, w 32)", strip(image(tall, pal), 960)))
    sheet(sprites, os.path.join(out, "sprites.png"))
    return 2


# ---- opening (OPEN.EXE) and ending (END.EXE). Addresses are OPEN.EXE / END.EXE file offsets (code segment 0 = file
# 0x1800 / 0x1600; open 0:0x89a8 / 0:0x88bc, seek 0:0x7ab0 / 0:0x79d0, read 0:0x7a70 / 0:0x7990, NPK 0:0x671e, set
# palette 0:0x6676 / 0:0x658a). NPK16 is NPK016 with another magic (header +0xC w, +0xE h, data at +0x30,
# utils.unpack_npk); its header palette is the default digital one and is not used. OPENPLD.S5 (43) / EDPAL.S5 (41)
# are 48-byte palettes, 16 x (B, R, G) nibbles, chosen by file offset.
def npk_blocks(data, stops=()):
    """(offset, end) of every NPK16/NPK016 block; a block also ends at the next raw data start in `stops`."""
    offs = [m.start() for m in re.finditer(rb"NPK0?16", data)]
    bounds = sorted(set(offs[1:]) | set(stops) | {len(data)})
    return [(o, min(b for b in bounds if b > o)) for o in offs]


def npk_image(data, block):
    o, e = block
    w, h = struct.unpack_from("<2H", data, o + 0xC)
    return Image.frombytes("P", (w, h), bytes(unpack_npk(data[o + 0x30:e], w, h)[:w * h]))


def pld(table, k):
    return nibbles(table[48 * k:48 * k + 48])


def place(size, *parts):
    out = Image.new("P", size)
    for im, xy in parts:
        out.paste(im, xy)
    return out


def thumbs(ims, cols, scale=4):
    ims = [i.resize((i.width // scale, i.height // scale)) for i in ims]
    w, h = max(i.width for i in ims) + 2, max(i.height for i in ims) + 2
    out = Image.new("RGB", (cols * w, (len(ims) + cols - 1) // cols * h), (48, 48, 48))
    for k, i in enumerate(ims):
        out.paste(i, (k % cols * w, k // cols * h))
    return out


def export_open_end(game_dir, out):
    rows = []

    def save(folder, fname, im, group, name, source, ev):
        os.makedirs(os.path.join(out, folder), exist_ok=True)
        im.save(os.path.join(out, folder, fname + ".png"))
        rows.append([f"{folder}/{fname}.png", group, name, source, f"{im.width}x{im.height}", ev])

    pl = read(game_dir, "OPENPLD.S5")
    o1 = read(game_dir, "OPEN1.S5")
    b1 = npk_blocks(o1, (0x357D0,))
    o2, o3 = read(game_dir, "OPEN2.S5"), read(game_dir, "OPEN3.S5")
    mono = [read(game_dir, f"OPMONO{s}.S5") for s in ("", "2", "3")]
    b3 = npk_blocks(o3, (0xC0F6, 0xE26C))
    tt = read(game_dir, "OPTITLE.S5")
    bt = npk_blocks(tt)

    def half(d, o):
        return rcp(d[o:o + 0xFA00], 640, 200)

    def pair(a, b):
        return place((640, 400), (a, (0, 0)), (b, (0, 200)))
    code = "✅ code（檔位置、色盤號）；名稱看圖 🟡"
    op = [
        ("01", pair(npk_image(o1, b1[0]), npk_image(o1, b1[1])), 0, "龍", "OPEN1 NPK16 #0+#1；OPENPLD #0（0x5684）", code),
        ("02", pair(half(o1, 0x357D0), half(o1, 0x451D0)), 0, "龍（全身）",
         "OPEN1 0x357D0+0x451D0 raw；OPENPLD #0（0x5808）", "🟡 上下拼合看圖；檔位置 ✅ code"),
        ("03", pair(half(o1, 0x54BD0), half(o1, 0x645D0)), 1, "龍紋浮雕",
         "OPEN1 0x54BD0+0x645D0 raw；OPENPLD #1（0x59DD，畫在 y=0／200，0x5AA0）", code),
        ("04", pair(half(o1, 0x73FD0), half(o1, 0x839D0)), 1, "城樓遠望",
         "OPEN1 0x73FD0+0x839D0 raw（0x5B1D）；色盤沿用 #1", "🟡 拼合與色盤推定；檔位置 ✅ code"),
    ]
    for k, (blk, pk, at) in enumerate([(12, 2, 0x5E96), (13, 3, 0x5F82), (14, 4, 0x607A)]):
        op.append((f"{5 + k:02d}", npk_image(o1, b1[blk]), pk, f"戰場 {k + 1}",
                   f"OPEN1 NPK16 #{blk}（416×272，畫在 0x70,0x40）；OPENPLD #{pk}（{at:#x}）", code))
    for s in range(3):
        op.append((f"{8 + s:02d}", pair(half(o2, s * 0x1F400), half(o2, s * 0x1F400 + 0xFA00)), 5 + s,
                   f"武將 {s + 1}", f"OPEN2 {s * 0x1F400:#x}（0x64A0 第 {s} 幕）；OPENPLD #{5 + s}（0x61E8）", code))
    op.append(("11", pair(npk_image(o3, b3[0]), npk_image(o3, b3[1])), 8, "山水",
               "OPEN3 NPK16 #0+#1；OPENPLD #8（0x6648，畫在 y=0／200，0x67C3）", code))
    op.append(("12", pair(npk_image(o3, b3[2]), npk_image(o3, b3[3])), 9, "三君主",
               "OPEN3 NPK16 #2+#3；OPENPLD #9（0x6912）", "✅ code（檔位置、色盤號）；上下拼合 🟡"))
    op.append(("13", place((640, 400), (npk_image(tt, bt[0]), (0, 40)), (npk_image(tt, bt[1]), (0, 200))), 14,
               "標題「三國志V」", "OPTITLE NPK16 #0（y=40）+#1（y=200，0x77D8）；OPENPLD #14（0x75AA 讀 #14–30 的淡出表）",
               "✅ code；用淡出表第一組 🟡"))
    for n, im, pk, name, src, ev in op:
        save("opening", f"op-{n}", image(im, pld(pl, pk)), "開場", name, src, ev)
    cels = [image(npk_image(o1, b1[k]), pld(pl, 0)) for k in range(2, 12)]
    for s, d in enumerate(mono):
        cels += [image(half(d, k * 0xFA00), pld(pl, 5 + s)) for k in range(len(d) // 0xFA00)]
    cels += [image(npk_image(o3, b3[k]), pld(pl, 10)) for k in (4, 5)]
    cels.append(image(npk_image(tt, bt[2]), pld(pl, 31)))
    os.makedirs(os.path.join(out, "fragments"), exist_ok=True)
    thumbs(cels, 8).save(os.path.join(out, "fragments", "opening-cels.png"))

    ep = read(game_dir, "EDPAL.S5")
    e2, e3, e4, scr = (read(game_dir, f) for f in ("END2.S5", "END3.S5", "END4.S5", "ENDSCR.S5"))
    ed = [
        ("01", place((512, 320), (rcp(e2, 512, 160), (0, 0)), (rcp(e2[0xA000:], 512, 160), (0, 160))),
         14, "都城鳥瞰", "END2 0+0xA000（2 × 0xA000，0x5A0A）；EDPAL #14（0x5AAD）", "✅ code（位置、色盤）；512 寬由大小推 🟡"),
        ("02", rcp(e2[0x138800:], 432, 256), 16, "宮門", "END2 0x138800（0xD800，0x5C64）；EDPAL #16（0x5CD0）",
         "✅ code（位置、色盤）；432×256 由大小推 🟡"),
        ("03", pair(half(e2, 0x146000), half(e2, 0x155A00)), 17, "皇帝即位",
         "END2 0x146000+0x155A00（0x5D0B）；EDPAL #17（0x5DCC）", code),
        ("04", rcp(e3, 640, 400), 18, "宮殿內", "END3 0–0x1F400；EDPAL #18（0x621C）", "🟡 大小與色盤看圖"),
        ("05", rcp(e4, 272, 336), 20, "皇帝背影 1", "END4 0（0xB280，0x6771）；EDPAL #20（0x660C）",
         "✅ code（272×336＝0x110×0x150，0x678D）；色盤 🟡"),
        ("06", rcp(e4[0xB280:], 272, 336), 20, "皇帝背影 2", "END4 0xB280（0x6819）；EDPAL #20", "✅ code；色盤 🟡"),
        ("07", npk_image(scr, npk_blocks(scr)[0]), 40, "騎兵（結尾）", "ENDSCR NPK016 640×400（0x6BA7）；EDPAL #40（0x7112）",
         "✅ code（圖）；色盤 🟡（檔頭是預設數位色盤）"),
    ]
    for n, im, pk, name, src, ev in ed:
        save("ending", f"ed-{n}", image(im, pld(ep, pk)), "結局", name, src, ev)
    frames = [image(rcp(e2[0x14000 + k * 0xB400:], 576, 160), pld(ep, 15)) for k in range(26)]
    thumbs(frames, 6).save(os.path.join(out, "fragments", "ending-cels.png"))
    write_csv(os.path.join(out, "opening-ending.csv"), ["file", "group", "name", "source", "size", "evidence"], rows)
    return len(rows)


@click.command("san5-extras", help="三國志V PK (PC-98): event pictures, maps, items and MESSAGE.S5 texts.")
@click.option("--game-dir", required=True, help="san5pk-pc98 directory")
@click.option("--dos-dir", default=None, help="san5pk-dos directory (Chinese item names and MESSAGE.S5)")
@click.option("--out", required=True, help="output directory (extract/)")
def san5_extras(game_dir, dos_dir, out):
    print("eventcg:", export_pictures(game_dir, os.path.join(out, "eventcg")))
    print("map:", export_maps(game_dir, os.path.join(out, "map")))
    print("items, holder rows, pictures:", export_items(game_dir, os.path.join(out, "items"), dos_dir))
    print("messages:", export_events(game_dir, os.path.join(out, "events"), dos_dir))
    print("opening, ending:", export_open_end(game_dir, out))
    print("fragment sheets:", export_fragments(game_dir, os.path.join(out, "fragments")))
