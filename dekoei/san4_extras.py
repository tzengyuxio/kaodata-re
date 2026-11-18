"""三國志IV PK (PC-98, san4pk-pc98): event pictures, items (道具) and the MESSAGE.S4 texts.

Formats and evidence: notes/san4.md「事件、插圖、道具」.
- Pictures are NPK016 (header: +0xC width, +0xE height, +0x10 sixteen u16 colours 0GRB, data at +0x30, utils.unpack_npk).
  PACKGRP*.S4 carry their own palette; REVGRP/HEGRP/HIBACK carry the default digital one and are drawn with the
  main palette (MAIN.EXE 0x4E736, 16 x B,R,G nibbles).
- Items: SNDATA.S4 part (one per scenario) +1421, 31 x 20 bytes: u16 holder (1-based index into the scenario's
  person records, 0xFFFF none), kind, flag, rank, bonus 1, bonus 2, 13-byte Shift-JIS name. MESSAGE.S4 part 34
  message k is item k's description (effect text first).
- OPENDAT.S4 / ENDDAT.S4 (opening, ending) and PREGRP.S4 are NPK016 / NPK16 pictures whose header palette is the
  default one; the real palettes are 48-byte sets (16 x B, R, G nibbles, the order OPEN.EXE file 0x5E2D writes to the
  ports 0xAE, 0xAC, 0xAA) at the file head (ENDDAT 31 sets, PREGRP 4) or between the pictures (OPENDAT 5 blocks).
  Which set each picture uses: OPENING_PALETTES / ENDING_PALETTES (OPEN.EXE / END.EXE, partly by eye).
- TOSHICG.S4 + TOSHIMAP.S4 (LS11): the 43 city views, 16 x 13 cells of 16 x 16 in 3 layers (tile = 128 bytes, four
  32-byte planes); layer 0 at tile 110 + v, layers 1-2 at tile v with colour 0 transparent (bases by eye).
- MESSAGE.S4 (LS11, 38 parts of u16-offset messages): text is Shift-JIS with half-width kana shown as hiragana,
  0x0A line break, 05 05 05 end of message, 01 xx .. control codes (kept as {xx:hex}).
"""
import contextlib
import io
import re
import json
import os
import struct

import click
from PIL import Image, ImageDraw

import biography
import ls11
import sango
from utils import unpack_npk
from common import write_csv
from gfx import decode_planar

MAIN_PALETTE = 0x4E736  # MAIN.EXE (PK), 16 x (B, R, G) nibbles
ITEMS = 1421  # SNDATA.S4 part offset of the item table
ITEM_SIZE, ITEM_COUNT = 20, 31
ITEM_DESC_PART = 34
ITEM_PICTURE_FIRST = 18  # PACKGRP.S4 picture 18 + k is item k
# kind byte -> label (read off the descriptions, the game shows no kind names)
ITEM_KINDS = {0: "兵法書", 1: "妖術書（天変）", 2: "妖術書（風変）", 3: "醫書", 4: "武器", 5: "名馬", 6: "玉璽"}
# item-name gaiji (FONT.S4 glyphs read by eye) on top of the person-name ones
GAIJI = {**sango.SAN4PK_SUIKODEN_GAIJI, 0xEBC8: "釭", 0xEBF8: "蒺"}
# control code lengths after 01 xx (from the message streams; unknown codes take 2)
CONTROL_ARGS = {0x49: 2, 0x53: 3, 0x43: 2, 0x4A: 2}

# (file, picture indices, group, names, palette: "own" or "main", compose vertically into one picture)
PICTURES = [
    ("PACKGRP.S4", range(0, 4), "場景", ["宮廷・謁見の間"], "own", True),
    ("PACKGRP.S4", range(4, 8), "場景", ["軍營"], "own", True),
    ("PACKGRP.S4", range(8, 12), "君主（背影）", ["文官", "女性", "武將", "女武將"], "own", False),
    ("PACKGRP.S4", range(12, 16), "君主（坐像）", ["文官", "女性", "武將", "女武將"], "own", False),
    ("PACKGRP.S4", range(16, 18), "人物（立像）", ["男", "女"], "own", False),
    ("PACKGRP.S4", range(49, 60), "事件", ["戰鬥", "暴動", "皇帝", "蝗害", "疫病", "豐作", "婚姻", "洪水", "暴風雨",
                                          "臨終", "密談"], "own", False),
    ("PACKGRP3.S4", range(6, 10), "場景", ["玉座"], "own", True),
    ("PACKGRP3.S4", range(10, 14), "人物（立像）", ["文官 1", "文官 2", "武將 1", "武將 2"], "own", False),
    ("PACKGRP3.S4", range(14, 18), "人物（立像）", ["后妃 1", "后妃 2", "后妃 3", "后妃 4"], "own", False),
    ("PACKGRP3.S4", range(18, 20), "人物（背影）", ["男", "女"], "own", False),
    ("REVGRP.S4", range(0, 7), "事件", ["王允", "貂蟬の舞", "呂布と貂蟬", "朝廷", "閲兵", "密詔", "月下の亭"],
     "main", False),
    ("HEGRP.S4", range(0, 7), "計略", ["混乱?", "落石", "同討?", "連環", "天変?", "火計", "陥穽?"], "main", False),
    ("HIBACK.S4", range(0, 5), "戰鬥背景", ["一騎討ち畫面", "野戰 1", "野戰 2", "野戰 3", "野戰 4"], "main", False),
]


def npk_offsets(data: bytes) -> list[int]:
    """Start of every NPK016 / NPK16 picture (NPK16 is the same format, only the magic and the 640x480 screen size
    in the header differ; see notes/npk016.md)."""
    return [m.start() for m in re.finditer(b"NPK0?16\0?", data)]


def set_palette(data: bytes, o: int) -> list[tuple]:
    """A 48-byte palette set: 16 x (B, R, G) nibbles."""
    return [(data[o + 3 * i + 1] * 17, data[o + 3 * i + 2] * 17, data[o + 3 * i] * 17) for i in range(16)]


def npk_palette(data: bytes, o: int) -> list[tuple]:
    out = []
    for k in range(16):
        v = struct.unpack_from("<H", data, o + 0x10 + 2 * k)[0]
        out.append(((v >> 4 & 15) * 17, (v >> 8 & 15) * 17, (v & 15) * 17))
    return out


def main_palette(game_dir) -> list[tuple]:
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        f.seek(MAIN_PALETTE)
        raw = f.read(48)
    return [(raw[3 * i + 1] * 17, raw[3 * i + 2] * 17, raw[3 * i] * 17) for i in range(16)]


def npk_pixels(data: bytes) -> list[tuple[int, int, bytes]]:
    """(width, height, colour indices) of every picture; trailing bytes (palette blocks) are ignored."""
    offs = npk_offsets(data) + [len(data)]
    out = []
    for o, end in zip(offs, offs[1:]):
        w, h = struct.unpack_from("<2H", data, o + 0xC)
        with contextlib.redirect_stdout(io.StringIO()):  # unpack_npk reports the unused tail
            out.append((w, h, unpack_npk(data[o + 0x30:end], w, h)[:w * h]))
    return out


def paint(w, h, px, pal) -> Image.Image:
    im = Image.new("RGB", (w, h))
    im.putdata([pal[c] for c in px])
    return im


def npk_images(path, palette=None) -> list[Image.Image]:
    with open(path, "rb") as f:
        data = f.read()
    return [paint(w, h, px, palette or npk_palette(data, o))
            for o, (w, h, px) in zip(npk_offsets(data), npk_pixels(data))]


def stack(ims):
    out = Image.new("RGB", (max(i.width for i in ims), sum(i.height for i in ims)))
    y = 0
    for im in ims:
        out.paste(im, (0, y))
        y += im.height
    return out


def ja_text(m: bytes) -> str:
    """MESSAGE.S4 (PC-98) message -> text; half-width kana become hiragana, control codes {xx:hex}."""
    out, i = [], 0
    while i < len(m):
        b = m[i]
        if b == 5:
            i += 1
            if out and out[-1] != "\n\n":
                out.append("\n\n")
            continue
        if b == 0x0A:
            out.append("\n")
            i += 1
        elif b == 1 and i + 1 < len(m):
            n = CONTROL_ARGS.get(m[i + 1], 2)
            out.append("{%02X:%s}" % (m[i + 1], m[i + 2:i + 2 + n].hex()))
            i += 2 + n
        elif 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC:
            v = b << 8 | m[i + 1] if i + 1 < len(m) else b
            if v in GAIJI:
                out.append(GAIJI[v])
            else:
                try:
                    out.append(m[i:i + 2].decode("cp932"))
                except UnicodeDecodeError:
                    out.append("[%04X]" % v)
            i += 2
        elif 0xA1 <= b <= 0xDF:
            out.append(hiragana(b))
            i += 1
        elif 0x20 <= b < 0x7F:
            out.append(chr(b))
            i += 1
        else:
            out.append("<%02X>" % b)
            i += 1
    return "".join(out).strip("\n")


KATA = "。「」、・をぁぃぅぇぉゃゅょっーあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん゛゜"
VOICED = {**{a: b for a, b in zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ")}, "う": "ゔ"}
SEMI = {a: b for a, b in zip("はひふへほ", "ぱぴぷぺぽ")}


def hiragana(b: int) -> str:
    return KATA[b - 0xA1]


def join_marks(s: str) -> str:
    out = []
    for c in s:
        if c == "゛" and out and out[-1] in VOICED:
            out[-1] = VOICED[out[-1]]
        elif c == "゜" and out and out[-1] in SEMI:
            out[-1] = SEMI[out[-1]]
        else:
            out.append(c)
    return "".join(out)


def plain(text: str) -> str:
    return re.sub(r"\{[0-9A-F]{2}:[0-9a-f]*\}|<[0-9A-F]{2}>", "", text)


def zh_text(m: bytes) -> str:
    """MESSAGE.S4 (DOS 中文版) message -> text: KOEI-TW code as in biography.koei_tw_text, control codes kept."""
    import utils
    if not utils.cns11643_unicode_table:
        utils.cns11643_unicode_table = utils.load_cns11643_unicode_table()
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
            n = CONTROL_ARGS.get(m[i + 1], 2)
            out.append("{%02X:%s}" % (m[i + 1], m[i + 2:i + 2 + n].hex()))
            i += 2 + n
        elif b >= 0x81 and i + 1 < len(m):
            try:
                out.append(biography.koei_tw_text(m[i:i + 2], "。") or "[%s]" % m[i:i + 2].hex())
            except (AssertionError, KeyError, IndexError, ValueError):
                out.append("[%s]" % m[i:i + 2].hex())
            i += 2
        elif 0x20 <= b < 0x7F:
            out.append(chr(b))
            i += 1
        else:
            out.append("<%02X>" % b)
            i += 1
    return "".join(out).strip("\n")


def messages(path):
    return [biography.offset_table(p, False) for p in ls11.ls11_decode_parts(open(path, "rb").read())]


def export_pictures(game_dir, out):
    os.makedirs(out, exist_ok=True)
    main = main_palette(game_dir)
    cache, rows = {}, []
    for name, idx, group, names, pal, compose in PICTURES:
        key = (name, pal)
        if key not in cache:
            cache[key] = npk_images(os.path.join(game_dir, name), main if pal == "main" else None)
        ims = cache[key]
        stem = name.split(".")[0].lower()
        items = [(f"{stem}-{idx[0]:02d}-{idx[-1]:02d}", stack([ims[k] for k in idx]), names[0], f"{idx[0]}–{idx[-1]}")] \
            if compose else [(f"{stem}-{k:02d}", ims[k], names[j], str(k)) for j, k in enumerate(idx)]
        for fname, im, label, src in items:
            im.save(os.path.join(out, fname + ".png"))
            ev = "🟡 名稱看圖取" + ("；色盤 main 🟡" if pal == "main" else "")
            rows.append([fname + ".png", group, label, f"{name} #{src}", f"{im.width}x{im.height}", ev])
    write_csv(os.path.join(out, "index.csv"), ["file", "group", "name", "source", "size", "evidence"], rows)
    return len(rows)


def kaodata_ids(game_dir):
    """(scenario, 1-based record index) -> kaodata san4pk-pc98 id (scenario order, unique (face code, name))."""
    seen, out, counters = {}, {}, {}
    for scenario, name, _, rec in sango.san4_records(os.path.join(game_dir, "SNDATA.S4"),
                                                      os.path.join(game_dir, "TAIKI.S4"), True):
        counters[scenario] = counters.get(scenario, 0) + 1
        key = (int.from_bytes(rec[20:22], "little"), name)
        seen.setdefault(key, len(seen))
        out[scenario, counters[scenario]] = (seen[key], name)
    return out


def export_items(game_dir, out, dos_dir=None):
    os.makedirs(os.path.join(out, "pictures"), exist_ok=True)
    with open(os.path.join(game_dir, "SNDATA.S4"), "rb") as f:
        parts = sango.san4_parts(f.read())
    descs = messages(os.path.join(game_dir, "MESSAGE.S4"))[ITEM_DESC_PART]
    zh = messages(os.path.join(dos_dir, "MESSAGE.S4"))[ITEM_DESC_PART] if dos_dir else [b""] * ITEM_COUNT
    ids = kaodata_ids(game_dir)
    pics = npk_images(os.path.join(game_dir, "PACKGRP.S4"))
    rows, holders = [], []
    base = parts[0][ITEMS:ITEMS + ITEM_SIZE * ITEM_COUNT]
    for k in range(ITEM_COUNT):
        r = base[ITEM_SIZE * k:ITEM_SIZE * (k + 1)]
        kind, flag, rank, b1, b2 = r[2:7]
        name = sango.san4_pc98_name(r[7:].split(b"\0")[0], GAIJI)
        desc = join_marks(plain(ja_text(descs[k])))
        lines = [s.strip(" 　") for s in desc.split("\n")]
        effect = ("；" if re.search(r"[0-9０-９]$", lines[0]) else "").join(s for s in lines[:2] if s)
        text = "".join(lines[2:]).strip()
        pic = f"pictures/{k:02d}.png"
        pics[ITEM_PICTURE_FIRST + k].save(os.path.join(out, pic))
        per = []
        for s, part in enumerate(parts, 1):
            h = struct.unpack_from("<H", part, ITEMS + ITEM_SIZE * k)[0]
            if h != 0xFFFF:
                i, pname = ids.get((s, h), (None, "?"))
                per.append(f"{s:02d}:{pname}")
                holders.append([k, name, s, h, i, pname])
        rows.append([k, name, kind, ITEM_KINDS.get(kind, ""), flag, rank, b1, b2, effect, text,
                     zh_text(zh[k]).replace("\n", "").strip(), pic, " ".join(per)])
    write_csv(os.path.join(out, "items.csv"),
              ["id", "name", "kind", "kind_name", "flag", "rank", "bonus1", "bonus2", "effect", "description",
               "description_zh", "picture", "holders"], rows)
    write_csv(os.path.join(out, "holders.csv"), ["item", "name", "scenario", "record", "kaodata_id", "holder"],
              holders)
    return len(rows), len(holders)


def export_events(game_dir, out, dos_dir=None):
    os.makedirs(out, exist_ok=True)
    n = 0
    with open(os.path.join(out, "messages.jsonl"), "w", encoding="utf-8") as f:
        for p, ms in enumerate(messages(os.path.join(game_dir, "MESSAGE.S4"))):
            for i, m in enumerate(ms):
                t = join_marks(ja_text(m))
                f.write(json.dumps({"part": p, "index": i, "lang": "ja", "text": t, "plain": plain(t)},
                                   ensure_ascii=False) + "\n")
                n += 1
        if dos_dir:
            for p, ms in enumerate(messages(os.path.join(dos_dir, "MESSAGE.S4"))):
                for i, m in enumerate(ms):
                    t = zh_text(m)
                    f.write(json.dumps({"part": p, "index": i, "lang": "zh-Hant", "text": t}, ensure_ascii=False)
                            + "\n")
                    n += 1
    return n


# OPENDAT.S4 palette blocks (file offset, sets), read by OPEN.EXE into DS:0x1202 (read calls at OPEN.EXE image
# 0x3D9C / 0x5892, 0x45C1, 0x5184, 0x5521, 0x60D7); each block sits in front of the pictures of its scene.
OPENING_BLOCKS = {"A": (0x0, 8), "B": (0x1615E, 32), "C": (0x2EEB8, 1), "D": (0x4B58E, 10), "E": (0x69FD5, 6)}
# (first picture, last picture, block, set, evidence, label)
OPENING_PALETTES = [
    (0, 1, "A", 0, "🟡 看圖（A 是 4 組循環的第 1 組）", "夕陽"),
    (2, 7, "A", 0, "🟡 看圖", "字幕"),
    (8, 8, "A", 0, "🟡 看圖", "夕陽"),
    (9, 11, "A", 0, "🟡 看圖", "黄巾の民"),
    (12, 12, "A", 0, "🟡 看圖", "字幕"),
    (13, 16, "B", 0, "🟡 看圖（B 是火焰的 32 組循環）", "炎"),
    (17, 17, "A", 0, "✅ code: OPEN.EXE 0x40A3 讀圖後循環 0x1202 的 8 組", "張角と黄巾"),
    (18, 18, "B", 0, "🟡 看圖（用 A 是群眾，用 B 只剩火焰）", "黄巾の炎"),
    (19, 20, "B", 0, "🟡 看圖", "叫ぶ顔"),
    (21, 22, "C", 0, "🟡 看圖", "地図"),
    (23, 29, "C", 0, "🟡 看圖", "字幕"),
    (30, 30, "C", 0, "🟡 看圖", "宮廷"),
    (31, 31, "C", 0, "🟡 看圖", "董卓"),
    (32, 37, "C", 0, "🟡 看圖", "群雄"),
    (38, 44, "C", 0, "🟡 看圖", "字幕"),
    (45, 45, "C", 0, "✅ code: OPEN.EXE 0x5184 讀 C、0x51AB 讀圖、0x5220 淡入 0x1202", "大河"),
    (46, 46, "C", 0, "🟡 看圖", "劉備?"),
] + [(47 + j, 47 + j, "D", s, "✅ code: OPEN.EXE 0x5272 圖表 bp-0x94，第 j 張淡入第 j+1 組", "竜")
     for j, s in enumerate([1, 2, 3, 4, 5, 6, 7, 9])] + [
    (55, 80, "E", 0, "🟡 看圖（E 0–2 是水面循環）", "竜・水面"),
    (81, 83, "E", 0, "🟡 看圖", "竜"),
    (84, 84, "E", 3, "🟡 看圖（E 3–5 是金色）", "タイトル"),
]
# ENDDAT.S4: 31 sets at the file head, loaded by END.EXE to DS:0x1D12 (set k at 0x1D12 + 0x30 k).
# (first, last, set, evidence, label); the scene functions are END.EXE image 0x354E, 0x390A, 0x42F4, 0x4924, 0x4AE6,
# 0x5652, 0x61DA, 0x6DB0.
ENDING_PALETTES = [
    (0, 4, 2, "✅ code: 0x354E 淡入 0→1→2", "宮殿の柱と扉"),
    (5, 18, 3, "✅ code: 0x390A 只用第 3 組", "宮城と皇帝"),
    (19, 21, 4, "✅ code: 0x42F4 由 3 淡入 4", "光"),
    (22, 22, 4, "✅ code: 0x42F4 由 3 淡入 4", "竜"),
    (23, 37, 6, "🟡 code: 0x4924 用 5（閃白）、6，取 6", "宮殿と空"),
    (38, 39, 7, "🟡 code: 0x4AE6 第一組 7", "空"),
    (40, 45, 14, "🟡 code: 0x4AE6／0x5652 用 7–17，取金色的 14", "竜"),
    (46, 49, 17, "🟡 code: 0x4AE6 最後一組 17", "人々"),
    (50, 53, 14, "🟡 code: 0x5652 用 14、15", "空"),
    (54, 59, 18, "✅ code: 0x61DA 讀圖後設第 18 組", "大地"),
    (60, 61, 19, "✅ code: 0x61DA 讀圖後設第 19 組", "大地"),
    (62, 62, 21, "🟡 code: 0x61DA 讀圖後設第 21 組", ""),
    (63, 64, 24, "✅ code: 0x61DA 讀圖後淡入第 24 組", "紋章"),
    (65, 65, 29, "✅ code: 0x6DB0 讀圖後設第 29 組", "完"),
    (66, 66, 14, "🟡 code: 0x5652", ""),
    (67, 71, 3, "🟡 code: 0x390A 圖表 DS:0x2C6", "字幕"),
    (72, 75, 17, "🟡 code: 0x4AE6 圖表 DS:0x378", "字幕"),
    (76, 78, 14, "🟡 code: 0x5652", ""),
]
CITY_TILE_BASES = (110, 0, 0)  # TOSHICG tile of value 0 in layers 0, 1, 2 (by eye: walls and roads join up)
CITY_W, CITY_H = 16, 13
# city order of TOSHIMAP.S4 parts = the game's city numbers (MAIN.EXE image 0x2066E reads part DGROUP 0x1D12)
CITIES = ["襄平", "北平", "代県", "晋陽", "南皮", "平原", "鄴", "北海", "濮陽", "陳留", "洛陽", "弘農", "長安", "安定",
          "天水", "西涼", "下邳", "徐州", "許昌", "譙", "汝南", "宛", "新野", "襄陽", "上庸", "江夏", "江陵", "武陵",
          "長沙", "桂陽", "零陵", "寿春", "建業", "呉", "会稽", "廬江", "柴桑", "漢中", "下弁", "梓潼", "成都", "永安",
          "江州"]


def contact_sheet(items, width=1280, bg=(64, 64, 80)) -> Image.Image:
    """items: (label, image); rows are filled left to right."""
    pos, x, y, row = [], 0, 0, 0
    for _, im in items:
        if x and x + im.width > width:
            x, y, row = 0, y + row + 14, 0
        pos.append((x, y))
        x += im.width + 6
        row = max(row, im.height)
    sheet = Image.new("RGB", (width, y + row + 14), bg)
    draw = ImageDraw.Draw(sheet)
    for (label, im), (x, y) in zip(items, pos):
        sheet.paste(im, (x, y + 12))
        draw.text((x, y), label, fill=(255, 255, 0))
    return sheet


def export_scenes(path, out, table, palette_of, prefix):
    """Opening / ending pictures, one PNG each, with index.csv and contact.png."""
    os.makedirs(out, exist_ok=True)
    with open(path, "rb") as f:
        data = f.read()
    pics = npk_pixels(data)
    rows, sheet = [], []
    for first, last, *rest in table:
        for n in range(first, last + 1):
            w, h, px = pics[n]
            source, pal, evidence, label = palette_of(data, n, *rest)
            im = paint(w, h, px, pal)
            fname = f"{prefix}-{n:02d}.png"
            im.save(os.path.join(out, fname))
            rows.append([fname, label, f"{os.path.basename(path)} #{n}", f"{w}x{h}", source, evidence])
            sheet.append((str(n), im))
    assert len(rows) == len(pics), (len(rows), len(pics))
    write_csv(os.path.join(out, "index.csv"), ["file", "name", "source", "size", "palette", "evidence"], rows)
    contact_sheet(sheet).save(os.path.join(out, "contact.png"))
    return len(rows)


def opening_palette(data, n, block, s, evidence, label):
    o, count = OPENING_BLOCKS[block]
    assert s < count
    return f"{block} 0x{o:X} 組 {s}", set_palette(data, o + 48 * s), evidence, label


def ending_palette(data, n, s, evidence, label):
    return f"檔首組 {s}", set_palette(data, 48 * s), evidence, label


def export_pregrp(game_dir, out):
    """PREGRP.S4: two 640x200 NPK16 halves of one 640x400 screen, palette set 0 of the 4 at the file head."""
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(game_dir, "PREGRP.S4"), "rb") as f:
        data = f.read()
    pal = set_palette(data, 0)
    im = stack([paint(w, h, px, pal) for w, h, px in npk_pixels(data)])
    im.save(os.path.join(out, "pregrp.png"))
    return 1


def city_tiles(cg: bytes) -> list[list[int]]:
    out = []
    for t in range(len(cg) // 128):
        out.append([sum((cg[t * 128 + 32 * k + y * 2 + x // 8] >> (7 - x % 8) & 1) << k for k in range(4))
                    for y in range(16) for x in range(16)])
    return out


def export_cities(game_dir, out):
    os.makedirs(out, exist_ok=True)
    pal = main_palette(game_dir)
    with open(os.path.join(game_dir, "TOSHICG.S4"), "rb") as f:
        tiles = city_tiles(ls11.ls11_decode_parts(f.read())[0])
    with open(os.path.join(game_dir, "TOSHIMAP.S4"), "rb") as f:
        maps = ls11.ls11_decode_parts(f.read())
    assert len(maps) == len(CITIES)
    rows, sheet = [], []
    for k, m in enumerate(maps):
        w = CITY_W * 16
        idx = bytearray(w * CITY_H * 16)
        for layer, base in enumerate(CITY_TILE_BASES):
            for c in range(CITY_W * CITY_H):
                v = m[layer * CITY_W * CITY_H + c]
                if v == 0xFF:
                    continue
                o = (c // CITY_W) * 16 * w + (c % CITY_W) * 16
                for i, p in enumerate(tiles[base + v]):
                    if layer == 0 or p:
                        idx[o + (i >> 4) * w + (i & 15)] = p
        im = paint(w, CITY_H * 16, idx, pal)
        fname = f"{k:02d}-{CITIES[k]}.png"
        im.save(os.path.join(out, fname))
        rows.append([fname, k, CITIES[k], f"TOSHIMAP.S4 part {k}", "🟡 都市對應看 code（part＝都市號），圖塊起點看圖"])
        sheet.append((str(k), im))
    write_csv(os.path.join(out, "index.csv"), ["file", "city", "name", "source", "evidence"], rows)
    contact_sheet(sheet, width=2096).save(os.path.join(out, "contact.png"))
    return len(rows)


def tile_strip(data: bytes, cols=16) -> tuple[int, int, list[int]]:
    tiles = city_tiles(data)
    rows = (len(tiles) + cols - 1) // cols
    w = cols * 16
    idx = [0] * (w * rows * 16)
    for t, px in enumerate(tiles):
        o = (t // cols) * 16 * w + (t % cols) * 16
        for i, p in enumerate(px):
            idx[o + (i >> 4) * w + (i & 15)] = p
    return w, rows * 16, idx


def export_ui(game_dir, out):
    """One contact sheet of the unnamed parts that decode (main palette, 🟡)."""
    os.makedirs(out, exist_ok=True)
    pal = main_palette(game_dir)

    def parts(name):
        with open(os.path.join(game_dir, name), "rb") as f:
            return ls11.ls11_decode_parts(f.read())
    items = []
    higrp, newgrp = parts("HIGRP.S4"), parts("NEWGRP.S4")
    items += [(f"HIGRP {k}", paint(96, 96, decode_planar(higrp[k], 0, 96, 96, 4), pal)) for k in range(13)]
    items += [(f"NEWGRP {k}", paint(240, 160, decode_planar(newgrp[k], 0, 240, 160, 4), pal)) for k in (2, 3, 4)]
    items += [(f"NEWGRP {k}", paint(112, 112, decode_planar(newgrp[k], 0, 112, 112, 4), pal)) for k in (6, 7, 8)]
    for k, p in enumerate(parts("HUNIT.S4")):
        items.append((f"HUNIT {k}", paint(*tile_strip(p), pal)))
    with open(os.path.join(game_dir, "HWGRP.S4"), "rb") as f:
        items.append(("HWGRP 0-15", paint(*tile_strip(f.read()[:16 * 128]), pal)))
    contact_sheet(items).save(os.path.join(out, "parts.png"))
    return len(items)


@click.command("san4-extras", help="三國志IV PK (PC-98): event pictures, items and MESSAGE.S4 texts.")
@click.option("--game-dir", required=True, help="san4pk-pc98 directory")
@click.option("--dos-dir", default=None, help="san4pk-dos directory (adds the Chinese MESSAGE.S4)")
@click.option("--out", required=True, help="output directory (extract/)")
def san4_extras(game_dir, dos_dir, out):
    print("eventcg:", export_pictures(game_dir, os.path.join(out, "eventcg")))
    print("items, holder rows:", export_items(game_dir, os.path.join(out, "items"), dos_dir))
    print("messages:", export_events(game_dir, os.path.join(out, "events"), dos_dir))
    print("opening:", export_scenes(os.path.join(game_dir, "OPENDAT.S4"), os.path.join(out, "opening"),
                                    OPENING_PALETTES, opening_palette, "opening"))
    print("ending:", export_scenes(os.path.join(game_dir, "ENDDAT.S4"), os.path.join(out, "ending"),
                                   ENDING_PALETTES, ending_palette, "ending"))
    print("screens:", export_pregrp(game_dir, os.path.join(out, "screens")))
    print("cities:", export_cities(game_dir, os.path.join(out, "cities")))
    print("ui parts:", export_ui(game_dir, os.path.join(out, "ui")))
