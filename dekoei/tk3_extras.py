"""提督の決断III パワーアップキット (PC-98): every picture and map of the game, the weapon tables and weapon cards,
written under --out (notes/koei-games.md「提督の決断III」「事件、插圖、地圖」).

Pictures
- Almost every *.TK3 picture file is LS11 with one headerless picture per part: 4 bpp, 4 planes interleaved per
  byte (byte 4 * (y * w / 8 + x / 8) + q is plane q, MSB leftmost), the same layout as the faces
  (kaodata_export.tk3_pc98_face). The width is not stored: it comes from the game code where traced (FIXED below)
  and otherwise from a row-similarity search checked by eye (WIDTHS, run-length coded).
- Files that are not LS11 (HMAPGRP, HMAPVGRP, HEX*) are the same 4 bpp layout without compression.
- DIRGRP.TK3 is 19 1 bpp masks (the 方面 of the Pacific map); BINDATA.TK3 0x312 has their x, y, w, h.
- LOGO.TK3 is NPK016 (genpei_extras.npk_unpack).
- Palettes: MAIN.EXE 0x3E6BA (16 x B, R, G 4-bit values, the in-game palette); OPEN.EXE 0x99B0 for the opening;
  HEXPAL.TK3 (32 palettes) for the battle files; BRDGPAL.TK3 (12) is written as palettes.png.

Maps
- MMAPGRP: 144 tiles 208 x 112, 12 x 12 → maps/mainmap.png 2496 x 1344.
- PACIFIC: two halves 624 x 168 → maps/pacific.png; DIRGRP drawn over it → maps/pacific-regions.png.

Weapon tables (MAIN.EXE; the SNDATA*.TK3 scenario blocks hold copies)
- Ship classes 0x3FB10: 235 x 38 bytes. Aircraft 0x41E00: 120 x 22, with performance 0x52180: 120 x 15.
  Tanks 0x42850: 20 x 20. New weapons 0x429E0: 16 x 21. Field layouts in SHIP_FIELDS etc. and in the notes.
- Pictures: ship → KSGRP part = class number (record +31, MAIN.EXE root 0x249E2 reads part n % 190),
  aircraft → KKGRP part = record, tank → SSGRP part = record, new weapon → HKGRP part = record.
- Aircraft perf +11 bits: 1 艦上, 2 水上, 4 偵察 (the 機種 label and the 偵察 box of the 3 aircraft screenshots).

Weapon cards (tk3_cards.py): cards/{ships,aircraft,tanks,new_weapons}/NNN_name.png, one 640 x 400-scale picture
per record drawn like the game's window; needs DOSBox-X's freecg98.bmp (--font) and the screenshots (--captures).

    cd dekoei && ../.venv/bin/python dekoei.py tk3-extras --game-dir ../games/tk3pk-pc98 --out ../games/tk3pk-pc98/extract
"""
import csv
import os
import struct

import click
from PIL import Image, ImageDraw

from genpei_extras import npk_chunks, npk_unpack
from koei_games import tk3_pc98_messages
from ls11 import ls11_decode_parts
from tk3_cards import FONT, write_cards

MAIN_PALETTE = 0x3E6BA  # MAIN.EXE (PK), set by root 0x2A6C4
OPEN_PALETTE = 0x99B0  # OPEN.EXE, the title picture (OPEN part 45 matches the title screenshot)

# file: (width, height) of every part, from the code or checked against screenshots (see the notes)
FIXED = {
    "BACKGRP": [(288, 72)] * 4 + [(192, 64), (120, 56)],
    "BRFGRP": [(432, 196)] * 2,
    "EVTGRP": [(128, 80)] * 33,
    "EVTGRP2": [(128, 80)] * 8,
    "HKGRP": [(152, 88)] * 16,
    "KCGRP": [(400, 208)] * 2 + [(48, 776)],
    "KKGRP": [(192, 64)] * 120,
    "KKGRP2": [(192, 64)] * 6,
    "KSGRP": [(288, 72)] * 190,
    "MMAPGRP": [(208, 112)] * 144,
    "PACIFIC": [(624, 168)] * 2,
    "RSLTGRP": [(368, 208), (400, 176), (400, 176)],
    "SSGRP": [(120, 56)] * 20,
    "VIEWGRP": [(160, 84)],
    "DBWIN": [(256, 256)] * 49,
    "DENTAKU": [(192, 172)],
}
# widths found by searching for the width with the most similar neighbouring rows, then looked at;
# "w*n" is n parts of width w (height = part size * 2 / w)
WIDTHS = {
    "OPEN": ("320*11 640*12 320*11 288 592 576*2 288*8 16 32 48 72 96 112 136 160 192 216 248 280 320*2 312 "
             "280 248 216 176 136 96 56 640 24 88 104 160 32*2 56 32*2 56 480*2 136 56 208 136 56 208 320 40 16 24 "
             "32 40 16 24 32 24"),
    "END": ("320*32 104*2 248 40*2 320*2 136 224 320*13 640*4 160*2 640*2 480*2 112 320*2 96*3 200*2 64*3 48*3 "
            "104*4 64*3 88*5 64*8 32 64*6 32 480"),
    "END2": "128 248 640*2",
    "SCEEND": "320*2 232*13 48*19 280*13 232*10 48*18 280*14",
    "SOPEN": "56*4 32*4 56*4 32*4 24*2 64 376 336 136 200 216 64 96 48 344 160 32 40 32 128*38",
    "SETUP": "64 624*2 80 64 80 64*2 80 248 368 256 216 200 112 56 24*2 72*2",
    "KANKYOU": "192 384 32*4 24*4 32",
    "HEXFGRP": ("160*50 32 16 40*4 56*4 64*4 48*21 80*2 56 64 88*6 112 104 56*2 64*6 40*2 48*4 72*5 48*4 80*4 88 "
                "48*4 88*5 48*4 72*5 16 32 16 32 16 32*2 40*4 56 40*3 56 40 56 72 88*2 80*2 96 80*3 24 48*4 64 96 16 "
                "64 16 32 64*2 16*3 32*2 24 80*7 64*2 160*64 64*9 88*18 80*9 56*8 24*4 16 24*7 32 16 80*5 72*3 104*7 "
                "56*7 32*4 16 72*7 80*3 64*18 40 56 64 80 88*4 48 56 48*14 160*30 56*8 64 56 32*2 24 32 16*2 24*2 "
                "32 24 40 64 48 56 32 16*2 112 32 16*2 64 40 56*2 48*3 56 48 32*2 16 56*4 64 40 48 40 32 16 32 16 "
                "32*2 40*2 32 48 56 16 24 32 40 56 64 72*3 16*2 32 48 40*2 48*3 16*2 40*2 56 64 72*3 32 160*9 72 64 "
                "72 56 48 32 40 16 32 72*3 64*2 48 32 16*2 40*2 64 40 48*4 80 40*2 48 40*2 24 32 40 32 16 24 32 "
                "40*2 48 16 24 32 40*2 32 16 40 32 24 16 40 48 24"),
    "HEXFGRPP": ("160*12 32*3 160*44 32*18 80*7 32*3 80*4 32 16 56*3 32*7 320*7 160*8 32*5 128 160*42 32*6 24 "
                 "96*4 112 104 112*5 32 160*7 32 16*2 24 32 40 72 80 64 16 80 96 104*3 96 120 128 112 104 72*2 64 "
                 "72*2 88 16*2 32 24*2 40 48*2 16 48 80*3 88*3 72 88 120*2 96*2 16*4 24*5 16*8 32 16*4 40 32 16*2 "
                 "40 16 32 56 112 64 16*5 24 32 48 64*2 72 64 16*2 32 48 72 80*3 16*2 32 40 64 72 80*2 16*2 40 48 "
                 "64 72 80*2 16*4 24 32*2 40 16*4 48 64 16 80 16*2 104*2 32*4 160*36 24*4 120*3 32 64*5 160*4 80*6 "
                 "152*3 160*5 112*5 56*12 72*3 160*21 24*2 48 64 136 152 144 152 24 40 160 80 104 120 152 144 16 24 "
                 "48 64 24 40 48 56 88 112 24*3 32*3 24*3 64*2 24 48 64 16*2 104*2 112 136*2 128 32*2 40 48 80 16*3 "
                 "160*14 64*9 80*3"),
    "HEXANIM": ("16*2 32 16*2 40*2 16*3 40 16*3 32 16*3 24 16*3 32 16*2 24*2 16*2 24*2 16*2 32*2 16*2 32*2 16*2 32*2 "
                "16*2 32*2 16*3 32 16*2 40*2 16*3 32 16*3 40 16*3 40 16*3 24 16*2 32*2 16*2 32 40 16*3 40 16*3 40 "
                "16*3 40 16*3 40 16*2 24*2 16*2 24*2 16*2 32*2 16*2 32*2 16*2 32*2 16*2 32*2 16*3 40 16*2 32 40 16*3 "
                "40 16*2 32 40 16*3 40 16*3 40 16*3 32 16*2 40*2 16*2 40*2 16*3 40 16*3 32*2 16 32 40 16*3 32 16*2 "
                "32*2 16*3 32 16*2 40*2 16*2 32 40 16*3 32*2 16 32*2 16*3 32*2 16*2 40 16*2 24*2 16*2 32*2 16*3 40 "
                "16*3 32*2 16 32*2 16*3 32 16*3 32*2 16 32*2 16*3 32 16*3 32*2 24*3 16*2 24*2 16*2 40*2 32 16 40*2 32 "
                "16 40*3 16 40*3 16 24*2 16*2 40*3 16 40*3 16*2 32 16*3 32*2 16*2 32 16*3 32*2 16*2 32 16*3 32 16*3 "
                "32*2 16 32*2 16 32 16 32 16*2 32*2 16*2 24*2 16*2 24*2 16 24*2 16 24*2 16*2 32 16*3 24*2 16*2 32*2 "
                "16*3 24*2 16*2 24 16*7 24 16*11 24*2 16*11 24 16*2 24*2 16*9 24 16*7 24 16*4 24 16*2 24 16*4 24 "
                "16*2 24 16*4 24 16*2 24 16*7 24 16*4 24 16*2 24 16*4 24 16*2 24 16*12 32 16*2 32 16*27 40*4 56*14 "
                "24*4 40 24*7 40*3 16*9 40*3 16 40*7 16 40*3 16*17 24*3 16 24*3 16 24*3 16 24*3 16*24 48*3 24 48*3 "
                "24 16*8 40*5 32*2 40 16*8 48*3 24 48*3 24 16*8 40 32*2 40*5 16*120 56*49"),
}
# LS11 files whose parts are not pictures of one size: one strip per part at this width
STRIPS = {"PARTS": 32, "PARTS2": 32}
# uncompressed files: (width, tile height or 0 = one strip)
RAW = {"HMAPGRP": (56, 32), "HMAPVGRP": (24, 0), "HEXOBJ": (56, 32), "HEXPARTS": (32, 0), "HEXTILE": (32, 0),
       "HEXUNIT": (64, 0), "HEXVOBJ": (24, 0), "HEXVUNIT": (24, 0), "HEXSENKA": (176, 0), "HVIEWMAP": (40, 0)}
OPENING = {"OPEN"}  # drawn by OPEN.EXE with its own palettes
BATTLE = {"HEXFGRP", "HEXFGRPP", "HEXANIM", *RAW}  # HEXPAL palettes
EVENT_FILES = ["EVTGRP", "EVTGRP2"]
SOPEN_EVENTS = 32  # SOPEN parts 32-69 are 128 x 80 event pictures of the scenario openings
# sprites drawn with colour 0 transparent over a BACKGRP picture (checked against the weapon windows)
SPRITES = {"KSGRP": 0, "KKGRP": 4, "KKGRP2": 4, "SSGRP": 5}

DIR_RECTS = 0x312  # BINDATA.TK3: 19 x (x, y, w, h) words, read with DIRGRP by overlay 0xA5D10 (file offset)

SHIPS, N_SHIPS, SHIP_SIZE = 0x3FB10, 235, 38
AIRCRAFT, N_AIRCRAFT, AIRCRAFT_SIZE = 0x41E00, 120, 22
AIR_PERF, AIR_PERF_SIZE = 0x52180, 15
TANKS, N_TANKS, TANK_SIZE = 0x42850, 20, 20
NEW_WEAPONS, N_NEW_WEAPONS, NEW_WEAPON_SIZE = 0x429E0, 16, 21
# PK SNDATA1-3.TK3: 7 blocks of 0xC16D bytes, the first starting 2 bytes before the file; table offsets in a block
SN_BLOCK, SN_BLOCKS, SN_SHIPS, SN_AIRCRAFT, SN_AIR_PERF = 0xC16D, 7, 0x88F7, 0xABD9, 0x8163

# MESSAGE.TK3 ids (1000 * part + index)
M_CALIBRE, M_MOUNT, M_SHIP_KIND, M_CLASS, M_NATION, M_AIR_KIND, M_NEW_WEAPON_TEXT = 2008, 2036, 2304, 2070, 4000, \
    2707, 1240


def palette(raw):
    """16 x (B, R, G) 4-bit values -> PIL palette."""
    out = []
    for i in range(16):
        b, r, g = raw[3 * i:3 * i + 3]
        out += [r * 17, g * 17, b * 17]
    return out


def planes(data, w, h):
    """4 planes interleaved per byte -> one colour number per pixel."""
    out = bytearray(w * h)
    for i in range(min(w * h // 8, len(data) // 4)):
        p0, p1, p2, p3 = data[4 * i:4 * i + 4]
        for b in range(8):
            s = 7 - b
            out[8 * i + b] = ((p0 >> s) & 1) | ((p1 >> s) & 1) << 1 | ((p2 >> s) & 1) << 2 | ((p3 >> s) & 1) << 3
    return bytes(out)


def picture(data, w, h, pal):
    im = Image.frombytes("P", (w, h), planes(data, w, h))
    im.putpalette(pal)
    return im


def widths(spec):
    out = []
    for item in spec.split():
        w, _, n = item.partition("*")
        out += [int(w)] * int(n or 1)
    return out


def sizes(name, parts):
    if name in FIXED:
        return FIXED[name]
    ws = widths(WIDTHS[name])
    assert len(ws) == len(parts), name
    return [(w, len(p) * 2 // w) for w, p in zip(ws, parts)]


def save_parts(folder, parts, dims, pal, transparent=False):
    os.makedirs(folder, exist_ok=True)
    ims = []
    for i, (data, (w, h)) in enumerate(zip(parts, dims)):
        assert len(data) == w * h // 2, (folder, i, len(data), w, h)
        im = picture(data, w, h, pal)
        if transparent:
            im.save(os.path.join(folder, f"{i:03d}.png"), transparency=0)
        else:
            im.save(os.path.join(folder, f"{i:03d}.png"))
        ims.append(im)
    return ims


def strip(data, w, pal, column=400):
    """A long strip of width w cut into columns of `column` rows (for files whose pieces are not split)."""
    h = len(data) * 2 // w
    im = picture(data, w, h, pal)
    cols = (h + column - 1) // column
    out = Image.new("P", (cols * (w + 8), min(h, column)))
    out.putpalette(pal)
    for c in range(cols):
        out.paste(im.crop((0, c * column, w, min(h, (c + 1) * column))), (c * (w + 8), 0))
    return out


def dirgrp(game_dir, pacific, pal):
    """The 19 方面 masks (1 bpp) at their BINDATA rectangles, drawn on the Pacific map in colour 15."""
    parts = ls11_decode_parts(open(os.path.join(game_dir, "DIRGRP.TK3"), "rb").read())
    rects = struct.unpack_from(f"<{4 * len(parts)}H", open(os.path.join(game_dir, "BINDATA.TK3"), "rb").read(),
                               DIR_RECTS)
    masks, over = [], pacific.copy()
    for i, data in enumerate(parts):
        x, y, w, h = rects[4 * i:4 * i + 4]
        assert len(data) == w * h // 8, (i, len(data), w, h)
        m = Image.frombytes("1", (w, h), data)
        masks.append((m, (x, y, w, h)))
        over.paste(15, (x, y), m)
    return masks, over


# ---------------------------------------------------------------------------------------------------- tables

def cstr(b):
    import unicodedata
    return unicodedata.normalize("NFKC", b.split(b"\0", 1)[0].decode("cp932", "replace"))


def msg(messages, mid):
    return messages[mid // 1000][mid % 1000]


def ships(exe, messages):
    rows = []
    for i in range(N_SHIPS):
        r = exe[SHIPS + i * SHIP_SIZE:SHIPS + (i + 1) * SHIP_SIZE]
        main, sec, torp = r[15], r[17], r[19]
        flags = r[34]
        link = struct.unpack_from("<H", r, 32)[0]
        rows.append({
            "record": i + 1, "name": cstr(r[:12]), "艦型": msg(messages, M_CLASS + r[31]),
            "国籍": msg(messages, M_NATION + r[13] - 1), "艦種": msg(messages, M_SHIP_KIND + (flags & 15)),
            "改装型": "○" if flags & 0x40 else "", "改装先": "" if link == 0xFFFF else link,
            "主砲": f"{msg(messages, M_CALIBRE + r[16])}cm{msg(messages, M_MOUNT + (main >> 4))}砲 {main & 15}基"
            if main else "なし",
            "副砲": f"{msg(messages, M_CALIBRE + r[18])}cm{msg(messages, M_MOUNT + (sec >> 5))}砲 {sec & 31}基"
            if sec else "なし",
            "魚雷管": f"{msg(messages, M_MOUNT + (torp >> 4))}発射管 {torp & 15}基" if torp else "なし",
            "高角砲": r[20], "機銃": r[21], "爆雷装置": "あり" if flags & 0x10 else "なし", "耐久度": r[22],
            "飛行甲板": r[23] or "", "速度": r[24], "艦載機数": r[25], "石油積載量": r[26],
            "建造費": struct.unpack_from("<H", r, 27)[0], "鉄鋼消費量": struct.unpack_from("<H", r, 29)[0],
            "flags": f"0x{flags:02X}", "picture": f"ksgrp/{r[31]:03d}.png",
            "raw": r[12:].hex(" "),
        })
    return rows


def aircraft(exe, messages, base=AIRCRAFT, perf=AIR_PERF):
    rows = []
    for i in range(N_AIRCRAFT):
        r = exe[base + i * AIRCRAFT_SIZE:base + (i + 1) * AIRCRAFT_SIZE]
        p = exe[perf + i * AIR_PERF_SIZE:perf + (i + 1) * AIR_PERF_SIZE]
        kind = r[21]
        abilities = p[11]
        rows.append({
            "record": i, "name": cstr(r[:12]), "国籍": msg(messages, M_NATION + r[13] - 1),
            "軍籍": "海軍" if kind & 1 else "陸軍",
            "艦上/水上": "艦上" if abilities & 1 else "水上" if abilities & 2 else "",
            "機種": msg(messages, M_AIR_KIND + ((kind >> 1) & 7)),
            "兵装": "雷装" if kind & 0x20 else "爆装" if kind & 0x10 else "銃装",
            "偵察": "○" if abilities & 4 else "",
            "攻撃力": p[0], "爆撃力": p[1], "防御力": p[2], "速度": struct.unpack_from("<H", p, 3)[0],
            "航続範囲": struct.unpack_from("<H", p, 5)[0] * 10,
            "生産費": struct.unpack_from("<H", r, 15)[0], "アルミ量": struct.unpack_from("<H", r, 17)[0],
            "u19": struct.unpack_from("<H", r, 19)[0], "kind": f"0x{kind:02X}",
            "picture": f"kkgrp/{i:03d}.png", "raw": r[12:].hex(" "), "raw_perf": p.hex(" "),
        })
    return rows


def tanks(exe, messages):
    rows = []
    for i in range(N_TANKS):
        r = exe[TANKS + i * TANK_SIZE:TANKS + (i + 1) * TANK_SIZE]
        cost, steel, u17 = struct.unpack_from("<3H", r, 13)
        rows.append({"record": i, "name": cstr(r[:11]), "国籍": msg(messages, M_NATION + r[11] - 1),
                     "戦闘力": r[19], "生産費": cost, "鉄鋼量": steel, "u17": u17,
                     "picture": f"ssgrp/{i:03d}.png", "raw": r[11:].hex(" ")})
    return rows


def new_weapons(exe, messages):
    rows = []
    for i in range(N_NEW_WEAPONS):
        r = exe[NEW_WEAPONS + i * NEW_WEAPON_SIZE:NEW_WEAPONS + (i + 1) * NEW_WEAPON_SIZE]
        ind, arm, air, ship, info = struct.unpack_from("<5H", r, 11)
        rows.append({"record": i, "name": cstr(r[:11]), "工業": ind, "兵器": arm, "航空": air, "艦船": ship,
                     "情報": info, "説明": msg(messages, M_NEW_WEAPON_TEXT + i).replace("\n", ""),
                     "picture": f"hkgrp/{i:03d}.png"})
    return rows


def scenario_diffs(game_dir, exe):
    """Records of the PK scenario blocks that differ from MAIN.EXE (ships, aircraft, aircraft performance)."""
    tables = [("ship", SN_SHIPS, SHIPS, N_SHIPS, SHIP_SIZE), ("aircraft", SN_AIRCRAFT, AIRCRAFT, N_AIRCRAFT,
              AIRCRAFT_SIZE), ("aircraft_perf", SN_AIR_PERF, AIR_PERF, N_AIRCRAFT, AIR_PERF_SIZE)]
    rows = []
    for f in ("SNDATA1.TK3", "SNDATA2.TK3", "SNDATA3.TK3"):
        data = b"\0\0" + open(os.path.join(game_dir, f), "rb").read()
        for blk in range(SN_BLOCKS):
            for table, sn, base, n, size in tables:
                for k in range(n):
                    a = data[blk * SN_BLOCK + sn + k * size:][:size]
                    b = exe[base + k * size:][:size]
                    if a != b:
                        name = cstr(exe[AIRCRAFT + k * AIRCRAFT_SIZE:][:12]) if table != "ship" else cstr(b[:12])
                        rows.append({"file": f, "block": blk, "table": table, "record": k, "name": name,
                                     "main": b.hex(" "), "scenario": a.hex(" ")})
    return rows


def event_picture(pid):
    """EVENTSEQ picture id -> eventcg file. 0-32 are EVTGRP parts (inferred: the place titles fit the pictures).
    Higher ids (55-100) go to EVTGRP2 / SOPEN by a rule not found yet (an offset of 24 fits ホワイトハウス = SOPEN 36
    but not 大統領就任式 or 大和艦橋), so they are left empty."""
    return f"evtgrp_{pid:03d}.png" if pid < 33 else ""


def eventseq(data, messages):
    """EVENTSEQ.TK3: u32 count, u32 offsets, then (u16 op, u16 value) pairs per sequence. Op 1 shows a picture,
    op 7 the place title (MESSAGE id), op 2 a face; the other ops are text and control."""
    n = struct.unpack_from("<I", data)[0]
    offs = list(struct.unpack_from(f"<{n}I", data, 4)) + [len(data)]
    rows = []
    for k in range(n):
        ops = [struct.unpack_from("<HH", data, o) for o in range(offs[k], offs[k + 1], 4)]
        titles = [msg(messages, v).replace("\x02$", "＊") for op, v in ops if op == 7]
        pics = [v for op, v in ops if op == 1]
        rows.append({"sequence": k, "picture_ids": " ".join(map(str, pics)),
                     "files": " ".join(event_picture(v) for v in pics), "title": " / ".join(titles)})
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------------------------------- command

@click.command("tk3-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="game files (games/tk3pk-pc98)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/tk3pk-pc98/extract)")
@click.option("--font", default=FONT, show_default=True, help="DOSBox-X freecg98.bmp, for the weapon cards")
@click.option("--captures", default="../captures/screenshots/tk3pk-pc98", show_default=True,
              help="screenshots the card frames are taken from")
def tk3_extras(game_dir, out, font, captures):
    """Pictures, maps, weapon tables and weapon cards of 提督の決断III PK (PC-98)."""
    read = lambda name: open(os.path.join(game_dir, name), "rb").read()  # noqa: E731
    exe = read("MAIN.EXE")
    main_pal = palette(exe[MAIN_PALETTE:MAIN_PALETTE + 48])
    open_pal = palette(read("OPEN.EXE")[OPEN_PALETTE:OPEN_PALETTE + 48])
    hexpal = read("HEXPAL.TK3")
    battle_pal = palette(hexpal[:48])

    # palettes.png: MAIN.EXE, OPEN.EXE, the 12 BRDGPAL and 32 HEXPAL palettes, one row of 16 swatches each
    brdg = b"".join(ls11_decode_parts(read("BRDGPAL.TK3")))
    sets = [exe[MAIN_PALETTE:MAIN_PALETTE + 48], read("OPEN.EXE")[OPEN_PALETTE:OPEN_PALETTE + 48]]
    sets += [brdg[k:k + 48] for k in range(0, len(brdg), 48)] + [hexpal[k:k + 48] for k in range(0, len(hexpal), 48)]
    sw = Image.new("RGB", (16 * 16, 16 * len(sets)))
    dr = ImageDraw.Draw(sw)
    for j, raw in enumerate(sets):
        p = palette(raw)
        for i in range(16):
            dr.rectangle((i * 16, j * 16, i * 16 + 15, j * 16 + 15), fill=tuple(p[3 * i:3 * i + 3]))
    os.makedirs(out, exist_ok=True)
    sw.save(os.path.join(out, "palettes.png"))

    pictures = {}
    for name in list(FIXED) + list(WIDTHS):
        parts = ls11_decode_parts(read(f"{name}.TK3"))
        pal = open_pal if name in OPENING else battle_pal if name in BATTLE else main_pal
        pictures[name] = save_parts(os.path.join(out, name.lower()), parts, sizes(name, parts), pal,
                                    transparent=name in SPRITES)
        print(f"{name}.TK3: {len(parts)} pictures")
    for name, w in STRIPS.items():
        os.makedirs(os.path.join(out, name.lower()), exist_ok=True)
        for i, data in enumerate(ls11_decode_parts(read(f"{name}.TK3"))):
            strip(data, w, main_pal).save(os.path.join(out, name.lower(), f"{i:03d}.png"))
        print(f"{name}.TK3: strip of width {w}")
    for name, (w, th) in RAW.items():
        data = read(f"{name}.TK3")
        folder = os.path.join(out, name.lower())
        os.makedirs(folder, exist_ok=True)
        if th:
            n = len(data) // (w * th // 2)
            save_parts(folder, [data[k * w * th // 2:(k + 1) * w * th // 2] for k in range(n)], [(w, th)] * n,
                       battle_pal)
            print(f"{name}.TK3: {n} tiles {w}x{th}")
        else:
            strip(data, w, battle_pal).save(os.path.join(folder, "strip.png"))
            print(f"{name}.TK3: strip of width {w}")

    # LOGO.TK3 (NPK016)
    logo = read("LOGO.TK3")
    os.makedirs(os.path.join(out, "logo"), exist_ok=True)
    for c in npk_chunks(logo):
        px, _ = npk_unpack(c["payload"], c["w"] // 2, c["w"] * c["h"])
        im = Image.frombytes("P", (c["w"], c["h"]), bytes(px[:c["w"] * c["h"]]))
        im.putpalette(main_pal)
        im.save(os.path.join(out, "logo", f"{c['index']:03d}.png"))

    # maps
    maps = os.path.join(out, "maps")
    os.makedirs(maps, exist_ok=True)
    mm = Image.new("P", (12 * 208, 12 * 112))
    mm.putpalette(main_pal)
    for k, im in enumerate(pictures["MMAPGRP"]):
        mm.paste(im, ((k % 12) * 208, (k // 12) * 112))
    mm.save(os.path.join(maps, "mainmap.png"))
    pac = Image.new("P", (624, 336))
    pac.putpalette(main_pal)
    for k, im in enumerate(pictures["PACIFIC"]):
        pac.paste(im, (0, 168 * k))
    pac.save(os.path.join(maps, "pacific.png"))
    masks, over = dirgrp(game_dir, pac, main_pal)
    over.save(os.path.join(maps, "pacific-regions.png"))
    os.makedirs(os.path.join(out, "dirgrp"), exist_ok=True)
    with open(os.path.join(out, "dirgrp", "rects.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["part", "x", "y", "w", "h"])
        for i, (m, rect) in enumerate(masks):
            m.save(os.path.join(out, "dirgrp", f"{i:03d}.png"))
            w.writerow([i, *rect])

    # event pictures
    ev = os.path.join(out, "eventcg")
    os.makedirs(ev, exist_ok=True)
    for name in EVENT_FILES:
        for i, im in enumerate(pictures[name]):
            im.save(os.path.join(ev, f"{name.lower()}_{i:03d}.png"))
    for i, im in enumerate(pictures["SOPEN"][SOPEN_EVENTS:], SOPEN_EVENTS):
        im.save(os.path.join(ev, f"sopen_{i:03d}.png"))
    message = read("MESSAGE.TK3")
    messages = [tk3_pc98_messages(message, p) for p in range(len(ls11_decode_parts(message)))]
    write_csv(os.path.join(ev, "eventseq.csv"), eventseq(read("EVENTSEQ.TK3"), messages))

    # weapon tables and cards
    tables = os.path.join(out, "tables")
    os.makedirs(tables, exist_ok=True)
    rows = [ships(exe, messages), aircraft(exe, messages), tanks(exe, messages), new_weapons(exe, messages)]
    for fn, r in zip(("ships.csv", "aircraft.csv", "tanks.csv", "new_weapons.csv"), rows):
        write_csv(os.path.join(tables, fn), r)
    diffs = scenario_diffs(game_dir, exe)
    if diffs:
        write_csv(os.path.join(tables, "scenario_diffs.csv"), diffs)
    print(f"tables: {', '.join(str(len(r)) for r in rows)} rows, {len(diffs)} scenario differences")
    font = os.path.expanduser(font)
    if os.path.exists(font) and os.path.isdir(captures):
        n = write_cards(os.path.join(out, "cards"), game_dir, font, captures, rows)
        print(f"cards: {n}")
    else:
        print(f"cards skipped: no {font} or {captures}")
