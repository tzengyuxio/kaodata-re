"""三國志IV PK (PC-98, san4pk-pc98): event pictures, items (道具) and the MESSAGE.S4 texts.

Formats and evidence: notes/san4.md「事件、插圖、道具」.
- Pictures are NPK016 (header: +0xC width, +0xE height, +0x10 sixteen u16 colours 0GRB, data at +0x30, utils.unpack_npk).
  PACKGRP*.S4 carry their own palette; REVGRP/HEGRP/HIBACK carry the default digital one and are drawn with the
  main palette (MAIN.EXE 0x4E736, 16 x B,R,G nibbles).
- Items: SNDATA.S4 part (one per scenario) +1421, 31 x 20 bytes: u16 holder (1-based index into the scenario's
  person records, 0xFFFF none), kind, flag, rank, bonus 1, bonus 2, 13-byte Shift-JIS name. MESSAGE.S4 part 34
  message k is item k's description (effect text first).
- MESSAGE.S4 (LS11, 38 parts of u16-offset messages): text is Shift-JIS with half-width kana shown as hiragana,
  0x0A line break, 05 05 05 end of message, 01 xx .. control codes (kept as {xx:hex}).
"""
import csv
import re
import json
import os
import struct

import click
from PIL import Image

import biography
import ls11
import sango
from utils import unpack_npk

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
    out, i = [], data.find(b"NPK016")
    while i != -1:
        out.append(i)
        i = data.find(b"NPK016", i + 1)
    return out


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


def npk_images(path, palette=None) -> list[Image.Image]:
    with open(path, "rb") as f:
        data = f.read()
    offs = npk_offsets(data) + [len(data)]
    out = []
    for o, end in zip(offs, offs[1:]):
        w, h = struct.unpack_from("<2H", data, o + 0xC)
        pal = palette or npk_palette(data, o)
        im = Image.new("RGB", (w, h))
        im.putdata([pal[c] for c in unpack_npk(data[o + 0x30:end], w, h)[:w * h]])
        out.append(im)
    return out


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


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


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


@click.command("san4-extras", help="三國志IV PK (PC-98): event pictures, items and MESSAGE.S4 texts.")
@click.option("--game-dir", required=True, help="san4pk-pc98 directory")
@click.option("--dos-dir", default=None, help="san4pk-dos directory (adds the Chinese MESSAGE.S4)")
@click.option("--out", required=True, help="output directory (extract/)")
def san4_extras(game_dir, dos_dir, out):
    print("eventcg:", export_pictures(game_dir, os.path.join(out, "eventcg")))
    print("items, holder rows:", export_items(game_dir, os.path.join(out, "items"), dos_dir))
    print("messages:", export_events(game_dir, os.path.join(out, "events"), dos_dir))
