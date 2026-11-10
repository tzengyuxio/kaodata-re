"""三國志13 PK (Steam 363150): event stills, items and events, plus an inventory of every container entry.

Outputs (notes/san13.md「事件、插圖、道具」):
  inventory.csv             every entry of DATA0.S13, pk/DATA0.S13, pk/DATA0_2.S13: name, sizes, magic, kind, extracted to
  eventcg/<group>/*.png     event stills, cropped to their content; eventcg/index.csv
  items/items.csv           the 234 items (宝物) with names, category, description, picture, first owner, raw columns
  items/pictures/NNN.png    the 256 item pictures (240 x 240)
  events/titles.csv         event names from the message table (string 20503-)
  events/event_data.jsonl   the 999 event tables of pk/data/event/event_data.bin (35 i16 columns per row, raw)
  events/msggame.jsonl      the compiled message scripts of pk/data/msggame.bin, text with control bytes as {xx}

File names come from the executables' (u32 string pointer, u32 1) tables: San13_jp.exe for the base container,
San13PK_jp.exe for pk/ entries < 1524 and San13PK_kr.exe for the rest (the per-language data), San13PK_sc.exe entry
1873 + i for pk/DATA0_2.S13 entry i (Simplified Chinese data).
"""
import csv
import json
import os
import struct
import zlib

import click

from sango import san13_items, san13_strings, san13_unzip

CONTAINERS = [("base", "DATA0.S13", "DATA1.S13"), ("pk", "pk/DATA0.S13", "pk/DATA1.S13"),
              ("pk2", "pk/DATA0_2.S13", "pk/DATA1_2.S13")]
# first name of each executable's table: the table starts one entry (8 bytes) before its pointer
NAME_TABLES = {"base": ("San13_jp.exe", "data/ctrl2d_sh.bin.zp"), "pk": ("San13PK_jp.exe", "pk/data/ctrl2d_sh.bin.zp"),
               "pk_lang": ("San13PK_kr.exe", "pk/data/ctrl2d_sh.bin.zp"),
               "pk2": ("San13PK_sc.exe", "pk/data/ctrl2d_sh.bin.zp")}
PK_LANG_FROM, PK2_FROM = 1524, 1873

# event stills: directory -> (group, crop w, h); every still is the first texture of a GT1G0600
STILLS = {"pk/data/ui/still_event/": ("still_event", 576, 432),
          "pk/data/ui/still_event_ED/": ("still_event_ED", 576, 432),
          "pk/data/ui/still_story_15/": ("still_story_15", 576, 432),
          "pk/data/ui/still_komono/": ("still_komono", 400, 224),
          "pk/data/ui/ev_still_bg/": ("ev_still_bg", 1280, 720),
          "pk/data/ui/still_tutorial/": ("still_tutorial", 576, 432)}

MSGDATA, MSGGAME, ITEM_PICTURES, SCENARIO_BS, EVENT_DATA = 2, 3, 26, 941, 1084
MSGDATA_TC = 1416
ITEM_TABLE = 7  # XL item of scenario_bs: 400 rows x 19 columns, 234 used
ITEM_NAME, ITEM_READING, ITEM_DESC, ITEM_COUNT = 17073, 17473, 17873, 234
ITEM_CATEGORY = 20678  # category c of column 0 is string 20678 + c (名馬, 剣, 刀 … 特殊)
PERSON_NAME = 6535, 1450  # surname 6535 + p, given name 6535 + 1450 + p
EVENT_TITLES = 20503, 20600  # 桃園の誓い, 美女連環の計・前編 … 漢帝崩御 (20568), with empty slots
XL_TYPES = {0: "I", 1: "i", 2: "h", 3: "B", 4: "i", 5: "H", 6: "b", 7: "f"}


def exe_names(game_dir, exe, first):
    """Names of an executable's file table (index = DATA0 entry)."""
    with open(os.path.join(game_dir, exe), "rb") as f:
        b = f.read()
    pe = struct.unpack_from("<I", b, 0x3C)[0]
    nsec, opt = struct.unpack_from("<H", b, pe + 6)[0], struct.unpack_from("<H", b, pe + 20)[0]
    base = struct.unpack_from("<I", b, pe + 52)[0]
    secs = []
    for i in range(nsec):
        vs, va, rs, ra = struct.unpack_from("<4I", b, pe + 24 + opt + 40 * i + 8)
        secs.append((va, max(vs, rs), ra))

    def to_file(v):
        return next((v - base - va + ra for va, size, ra in secs if va <= v - base < va + size), None)

    def to_va(o):
        return next(o - ra + va + base for va, size, ra in secs if ra <= o < ra + size)

    table = b.index(struct.pack("<II", to_va(b.index(first.encode() + b"\0")), 1)) - 8
    names = []
    while True:
        p, one = struct.unpack_from("<II", b, table + 8 * len(names))
        if one != 1:
            return names
        o = to_file(p)
        names.append(b[o:b.index(b"\0", o)].decode("ascii", "replace") if o is not None else "")


def entry_names(game_dir):
    t = {k: exe_names(game_dir, *v) for k, v in NAME_TABLES.items()}
    return {"base": t["base"], "pk": t["pk"][:PK_LANG_FROM] + t["pk_lang"][PK_LANG_FROM:],
            "pk2": t["pk2"][PK2_FROM:]}


class Container:
    def __init__(self, game_dir, index, data):
        with open(os.path.join(game_dir, index), "rb") as f:
            idx = f.read()
        self.entries = [struct.unpack_from("<4Q", idx, 32 * i) for i in range(len(idx) // 32)]
        self.f = open(os.path.join(game_dir, data), "rb")

    def raw(self, i, limit=None):
        offset, _, stored, _ = self.entries[i]
        self.f.seek(offset)
        return self.f.read(stored if limit is None else min(stored, limit))

    def __getitem__(self, i):
        return san13_unzip(self.raw(i))


def head(b):
    """The first bytes of an entry, inflating only the first chunk of a zp1."""
    if b[:4] == b"zp1\0":
        n = struct.unpack_from("<I", b, 12)[0]
        o = (16 + 4 * n + 0x7FF) // 0x800 * 0x800
        return zlib.decompressobj().decompress(b[o + 4:], 4096)
    return b[:4096]


def magic(h):
    if not h:
        return "empty"
    if h[:2] == b"XL":
        return "XL"
    if all(32 <= c < 127 for c in h[:4]):
        return h[:8].split(b"\0")[0].decode("latin1")
    if len(h) >= 12:
        n, o = struct.unpack_from("<2I", h)
        if 0 < n < 100000 and 4 + 8 * n <= o <= 4 + 8 * n + 64:
            return f"archive:{n}"
    return h[:4].hex()


def kind(name, mg):
    """A rough kind for archiving decisions, from the file name and magic."""
    n = name.lower()
    if not mg or mg == "empty":
        return "empty"
    for key, k in (("/face/", "face"), ("still_tutorial", "tutorial still"), ("still", "event still"),
                   ("item.bin", "item picture"), ("/event/", "event data"), ("msg", "text"), ("subtitle", "text"),
                   ("scenario", "scenario"), ("/ui/", "ui"), ("font", "font"), ("/unit/", "3d model"),
                   ("/stage/", "3d stage"), ("ikkiuchi", "3d duel"), ("/sound/", "sound"), ("effect", "effect"),
                   ("/battle/", "battle data"), ("shader", "shader")):
        if key in n:
            return k
    return {"GT1G0600": "texture", "XL": "table", "_M1G6300": "3d model"}.get(mg, "other")


def texture(t, w, h):
    """The first texture of a GT1G0600 (DXT1 or BC3), cropped to w x h, as RGBA."""
    from PIL import Image
    table = struct.unpack_from("<I", t, 0x0C)[0]
    o = table + struct.unpack_from("<I", t, table)[0]
    fmt, dim = t[o + 1], t[o + 2]
    tw, th = 1 << (dim & 15), 1 << (dim >> 4)
    start = o + 8 + (struct.unpack_from("<I", t, o + 8)[0] if t[o + 7] & 0x10 else 0)
    n, bpp = {6: (1, 8), 8: (3, 16)}[fmt]
    im = Image.frombytes("RGBA", (tw, th), t[start:start + tw * th * bpp // 16], "bcn", n)
    return im.crop((0, 0, w, h))


def xl_rows(b):
    assert b[:2] == b"XL"
    cols, rows, size, header = struct.unpack_from("<4H", b, 6)
    fmt = "<" + "".join(XL_TYPES[t] for t in b[0x10:0x10 + cols])
    return [list(struct.unpack_from(fmt, b, header + r * size)) for r in range(rows)]


def kana(t, katakana=False):
    """The scripts write hiragana as half-width katakana bytes (0xA6-0xDD), katakana between ESC K and ESC H."""
    import unicodedata
    t = unicodedata.normalize("NFKC", t)
    return t if katakana else "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ン" else c for c in t)


def script_text(b):
    """A compiled message script as text: Shift-JIS runs as text (half-width kana as hiragana), other bytes as
    {xx}."""
    out, i, katakana = [], 0, False
    while i < len(b):
        c = b[i]
        if c == 0x1B and i + 1 < len(b):  # ESC C x / ESC E x: colours; ESC K … ESC H: katakana; ESC R: reset
            n = 3 if b[i + 1] in b"CE" else 2
            katakana = {0x4B: True, 0x48: False}.get(b[i + 1], katakana)
            out.append("{1b}" + b[i + 1:i + n].decode("latin1"))
            i += n
            continue
        if (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC) and i + 1 < len(b) and 0x40 <= b[i + 1] <= 0xFC and b[i + 1] != 0x7F:
            try:
                out.append(b[i:i + 2].decode("cp932"))
                i += 2
                continue
            except UnicodeDecodeError:
                pass
        out.append(chr(c) if 0x20 <= c < 0x7F else kana(b[i:i + 1].decode("cp932"), katakana) if 0xA1 <= c <= 0xDF
                   else f"{{{c:02x}}}")
        i += 1
    import unicodedata
    return unicodedata.normalize("NFC", "".join(out))  # joins the separate (semi-)voiced marks


def plain(text):
    """script_text without the control codes: {01}" opens a string, the ESC codes are dropped, {0a} is a line
    break; everything else between the strings is dropped."""
    import re
    lines = []
    for part in text.split('{01}"')[1:]:
        part = re.sub(r"\{1b\}([CE].|[A-Z])", "", part).replace("{0a}", "\n")
        lines.append(re.split(r"\{[0-9a-f]{2}\}", part)[0])
    return "".join(lines)


def message_strings(pk, i, encoding):
    return san13_strings(san13_items(san13_items(pk[i])[0])[0], encoding)


def zh_items(game_dir) -> dict[int, tuple[str, str]]:
    """item i -> (name, description) of the 繁中 string table (PK item 1416, the same numbering as the Japanese)"""
    import sango
    from wiki_san13 import _strings
    tc = _strings(game_dir, MSGDATA_TC, "cp950", sango.SAN13_GAIJI_TC)
    return {i: (tc[ITEM_NAME + i], "".join(line.strip() for line in tc[ITEM_DESC + i].splitlines()))
            for i in range(ITEM_COUNT)}


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


@click.command(help="三國志13 PK: event stills, items, events and a container inventory (notes/san13.md)")
@click.option("--game-dir", required=True, help="the Steam files (games/san13pk-win)")
@click.option("--out", required=True, help="output directory (games/san13pk-win/extract)")
def san13_extras(game_dir, out):
    names = entry_names(game_dir)
    cont = {tag: Container(game_dir, d0, d1) for tag, d0, d1 in CONTAINERS}
    pk = cont["pk"]
    extracted = {}

    # event stills (the base container's are the same pictures, so only pk/ is read)
    index = []
    for i, name in enumerate(names["pk"]):
        for prefix, (group, w, h) in STILLS.items():
            if name.startswith(prefix):
                file = f"{group}/{os.path.basename(name).split('.')[0]}.png"
                os.makedirs(os.path.join(out, "eventcg", group), exist_ok=True)
                texture(pk[i], w, h).save(os.path.join(out, "eventcg", file))
                index.append([file, group, w, h, "pk", i, name, "✅ code: GT1G texture, crop = content bbox"])
                extracted[("pk", i)] = f"eventcg/{file}"
    write_csv(os.path.join(out, "eventcg", "index.csv"),
              ["file", "group", "width", "height", "container", "entry", "source", "evidence"], index)

    # items: table 7 of scenario_bs, names from msgdata (Japanese, and the Big5 copy), pictures from item.bin
    ja, tc = message_strings(pk, MSGDATA, "cp932"), message_strings(pk, MSGDATA_TC, "cp950")
    rows = xl_rows(san13_items(pk[SCENARIO_BS])[ITEM_TABLE])[:ITEM_COUNT]
    run = PERSON_NAME[1]

    def person(p):
        return ja[PERSON_NAME[0] + p] + ja[PERSON_NAME[0] + run + p] if 0 <= p < run else ""

    table = []
    for i, r in enumerate(rows):
        table.append([i, ja[ITEM_NAME + i], tc[ITEM_NAME + i], ja[ITEM_READING + i], r[0], ja[ITEM_CATEGORY + r[0]],
                      r[13], f"pictures/{r[13]:03d}.png" if r[13] >= 0 else "", r[15], person(r[15]), r[8], r[9],
                      ja[ITEM_DESC + i].replace("\n", ""), json.dumps(r)])
    write_csv(os.path.join(out, "items", "items.csv"),
              ["id", "name", "nameZh", "reading", "category", "categoryName", "picture", "file", "owner", "ownerName",
               "col8", "price?", "description", "raw"], table)
    pictures = san13_items(pk[ITEM_PICTURES])
    os.makedirs(os.path.join(out, "items", "pictures"), exist_ok=True)
    for k, t in enumerate(pictures):
        texture(san13_unzip(t), 240, 240).save(os.path.join(out, "items", "pictures", f"{k:03d}.png"))
    extracted[("pk", ITEM_PICTURES)] = "items/pictures"
    extracted[("pk", SCENARIO_BS)] = "items/items.csv (table 7 only)"

    # events
    titles = []
    for k in range(*EVENT_TITLES):
        if ja[k]:
            titles.append([k - EVENT_TITLES[0], ja[k], tc[k], k])
    write_csv(os.path.join(out, "events", "titles.csv"), ["n", "title", "titleZh", "string"], titles)
    with open(os.path.join(out, "events", "event_data.jsonl"), "w", encoding="utf-8") as f:
        for k, t in enumerate(san13_items(pk[EVENT_DATA])):
            if t[:2] == b"XL":
                f.write(json.dumps({"event": k, "rows": xl_rows(t)}) + "\n")
    extracted[("pk", EVENT_DATA)] = "events/event_data.jsonl"
    n_script = 0
    with open(os.path.join(out, "events", "msggame.jsonl"), "w", encoding="utf-8") as f:
        for g, part in enumerate(san13_items(pk[MSGGAME])):
            n = struct.unpack_from("<I", part)[0]
            offs = list(struct.unpack_from(f"<{n}I", part, 4)) + [len(part)]
            for k in range(n):
                text = script_text(part[offs[k]:offs[k + 1]])
                f.write(json.dumps({"group": g, "n": k, "plain": plain(text), "text": text}, ensure_ascii=False)
                        + "\n")
                n_script += 1
    extracted[("pk", MSGGAME)] = "events/msggame.jsonl"

    # inventory
    inv = []
    for tag, _, _ in CONTAINERS:
        c = cont[tag]
        for i, (offset, size, stored, comp) in enumerate(c.entries):
            name = names[tag][i] if i < len(names[tag]) else ""
            mg = magic(head(c.raw(i, 0x41000))) if stored else "empty"
            inv.append([tag, i, name, size, stored, comp, mg, kind(name, mg), extracted.get((tag, i), "")])
    write_csv(os.path.join(out, "inventory.csv"),
              ["container", "entry", "name", "size", "stored", "compressed", "magic", "kind", "extracted"], inv)
    click.echo(f"{len(index)} stills, {len(table)} items, {len(pictures)} item pictures, {len(titles)} event titles, "
               f"{n_script} message scripts, {len(inv)} inventory rows")
