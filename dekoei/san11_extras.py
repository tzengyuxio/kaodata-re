"""三國志11 PK (Steam 628070): event stills, items (寶物), rule tables and message texts, extracted for archiving.

See notes/san11.md「事件、插圖、道具」. Usage (from dekoei/):
    dekoei.py san11-extras --game-dir ../games/san11pk-win --out ../games/san11pk-win/extract
"""
import csv
import os
import struct
import unicodedata

import click
from PIL import Image, ImageDraw

from ls11 import ls11_decode
from sango import SAN11_GAIJI, SAN11_PERSONS, load_san11_persons

# media/san11pkres.bin, media/san11res1.bin: "LINK", u32 count at +4, (u32 offset, u32 size) pairs from +0x10.
# A WFTX0010 texture: u32 total size at +8, u32 frame count at +12, then per frame u16 w, u16 h, u8 bpp, 3 flag
# bytes and the pixels, top-down: 32 bit B G R A, 24 bit B G R, 8 bit indices + 256 colours of 4 bytes (R G B 0).
PK_RES, BASE_RES = "media/san11pkres.bin", "media/san11res1.bin"
# (folder, file, first item, last item); picked from contact sheets of every texture
PICTURES = [("still", PK_RES, 1, 88),      # 1-2 the empty audience hall, 3-88 event stills (800x512, 512x384 ...)
            ("pk", BASE_RES, 17, 35),      # 19 stills of the PK 決戦制覇 battles
            ("cutin", PK_RES, 500, 561)]   # 62 painted 512x512 portraits (一騎討ち／舌戦 cut-ins 🟡)
ITEM_PICTURES = (PK_RES, 89)               # 35 item pictures, item kind k is item 89 + k (240x240, 24 bit)
SCENARIOS = ["Scen000.s11", "SCEN001.S11", "SCEN002.S11", "SCEN003.S11", "SCEN004.S11", "SCEN005.S11",
             "SCEN006.S11", "SCEN007.S11", "Scen008.s11", "Scen009.s11", "Scen010.s11", "Scen011.s11",
             "Scen012.s11", "Scen013.s11"]
# Scen*.s11: 50 item records of 57 bytes from 0x2347D: +0 name 13, +13 reading 38, +51 value, +52 kind (= picture),
# u16 +53 holder (person id, 0xFFFF none), u16 +55 place (city 0-41, 関／港 42-86; 511 held, 767 unused slot)
ITEMS = (0x2347D, 57, 50)
# kinds by their pictures; the EXE word list has 名馬 長柄 弓 書物 玉璽 銅雀, 剣 and 暗器 are read off the names
KINDS = {**dict.fromkeys(range(0, 5), "名馬"), **dict.fromkeys(range(5, 9), "剣"),
         **dict.fromkeys(range(9, 12), "長柄"), **dict.fromkeys(range(12, 17), "暗器"),
         **dict.fromkeys(range(17, 22), "弓"), **dict.fromkeys(range(22, 33), "書物"), 33: "玉璽", 34: "銅雀"}
# media/scenario/Scenario.s11: fixed-size records; the bytes after a string's NUL hold leftovers of other text, so
# every field is read from its own offset up to its NUL. (name, start, record size, count, fields, tail)
# fields: (column, offset, length); tail: (column, offset, struct format) numbers whose meaning is 🟡
TABLES = [
    ("facilities", 0xB82, 189, 64, [("name", 0, 9), ("reading", 9, 21), ("description", 30, 159)], []),
    ("equipment", 0x3AC2, 150, 12, [("name", 0, 7), ("reading", 7, 19), ("description", 26, 124)], []),
    ("ranks", 0x41CA, 44, 10, [("name", 0, 11), ("reading", 11, 33)], []),
    ("offices", 0x4382, 46, 81, [("name", 0, 9), ("reading", 9, 27)],
     [("troops", 40, "<H"), ("b42", 42, "B"), ("b43", 43, "B"), ("b44", 44, "B"), ("grade", 45, "B")]),
    ("skills", 0x5210, 93, 100, [("name", 0, 5), ("reading", 5, 13), ("description", 24, 67)],
     [("level", 91, "B"), ("group", 92, "B")]),
    ("techniques", 0x7664, 92, 36, [("name", 0, 9), ("reading", 9, 18), ("description", 42, 50)], []),
    ("tactics", 0x8354, 56, 19, [("name", 0, 9), ("reading", 9, 14)], []),
    ("terrain", 0x8A54, 23, 20, [("name", 0, 5), ("reading", 5, 18)], []),
    ("training", 0x9E64, 74, 98, [("name", 0, 9), ("description", 9, 65)], []),
]
# places for the item locations: 42 cities from 0x5A (25 bytes), 45 関／港 from 0x474 (26 bytes)
PLACE_GAIJI = {0xE02D: "鄴", 0xE020: "邳", 0xE00B: "兗", 0xE02A: "涪", 0xE030: "鄱"}
# the strategic map (all in PK_RES; notes/san11.md「大地圖」): (file stem, item, frame)
WORLD_PICTURES = [("minimap-448", 4854, 0),                 # water transparent
                  ("minimap-208", 4855, 0),
                  ("minimap-628", 4857, 0),                 # three layers of one 628x628 minimap
                  ("minimap-628-territories", 4857, 1),     # one flat colour per territory
                  ("minimap-628-borders", 4857, 2)]
WORLD_COLOURS = range(4787, 4791)  # GCOL0001: 1025x1025 B G R, column-major; 4 seasons in item order 🟡
WORLD_HEX = 4791                   # SHEX0008: 200x200 cells of 11 bytes, column-major; +0 terrain, +1 territory
# terrain colours for the SHEX rendering (Scenario.s11 terrain table order), picked by hand
TERRAIN_RGB = [(150, 190, 100), (190, 160, 110), (225, 210, 150), (110, 150, 120), (150, 90, 160),
               (40, 110, 50), (110, 170, 230), (60, 120, 210), (30, 70, 160), (170, 150, 120),
               (230, 200, 90), (200, 120, 60), (120, 200, 230), (160, 210, 230), (200, 200, 170),
               (90, 80, 70), (220, 40, 40), (240, 140, 0), (40, 200, 220), (210, 170, 120)]
MSG = "media/msg/S11MSG0{}.s11"
# gaiji of the S11MSG texts not in SAN11_GAIJI, read off the rubies next to them (🟡); E052 is not known
MSG_GAIJI = {**PLACE_GAIJI, 0xE01F: "郿", 0xE022: "淄", 0xE057: "滎", 0xE059: "蒺", 0xE05A: "氐", 0xE05E: "涿",
             0xE060: "瑀", 0xE061: "瑒", 0xE064: "嬴", 0xE066: "颺", 0xE06C: "雟", 0xE0BC: "雒", 0xE0BD: "洮",
             0xE0BE: "煨", 0xE0C3: "顓", 0xE0C4: "頊", 0xE0C5: "嚳", 0xE0C6: "媧", 0xE0C7: "嵆", 0xE0C8: "焯",
             0xE0C9: "鈇", 0xE0CA: "晊", 0xE0D2: "牂", 0xE0D3: "牁", 0xE0D4: "嬀", 0xE0D8: "廙"}
BIOGRAPHY_ICONS = {"\ue06d": "史實", "\ue06e": "演義"}  # F0AE, F0AF


def link_entries(path):
    with open(path, "rb") as f:
        head = f.read(16)
        assert head[:4] == b"LINK"
        n = struct.unpack_from("<I", head, 4)[0]
        return [struct.unpack("<II", f.read(8)) for _ in range(n)]


def link_item(path, entries, i):
    with open(path, "rb") as f:
        f.seek(entries[i][0])
        return f.read(entries[i][1])


def wftx_frames(d):
    assert d[:8] == b"WFTX0010"
    n = struct.unpack_from("<I", d, 12)[0]
    p, frames = 16, []
    for _ in range(n):
        w, h, bpp = struct.unpack_from("<HHB", d, p)
        p += 8
        if bpp == 32:
            im = Image.frombytes("RGBA", (w, h), d[p:p + 4 * w * h], "raw", "BGRA")
            p += 4 * w * h
        elif bpp == 24:
            im = Image.frombytes("RGB", (w, h), d[p:p + 3 * w * h], "raw", "BGR")
            p += 3 * w * h
        elif bpp == 8:
            im = Image.frombytes("P", (w, h), d[p:p + w * h])
            pal = d[p + w * h:p + w * h + 1024]
            im.putpalette(bytes(b for i in range(256) for b in pal[4 * i:4 * i + 3]))
            p += w * h + 1024
        else:
            raise ValueError(f"bpp {bpp}")
        frames.append(im)
    return frames


def sjis(b, gaiji=None):
    s = b.split(b"\0")[0].decode("cp932", "replace")
    table = {**SAN11_GAIJI, **(gaiji or {})}
    return "".join(table.get(ord(c), c) for c in s)


def _kana(run, katakana):
    """Half-width kana stand for hiragana (ESC H, the default) or katakana (ESC K)."""
    s = unicodedata.normalize("NFKC", run)
    if katakana:
        return s
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def decode_message(b):
    """S11MSG text: cp932, half-width kana in hiragana / katakana mode (1B 'H' / 1B 'K'), 0A new line, 05 end.
    02 96 'NNx' colour (dropped), 02 97 68 / 02 97 7A ruby start / end (dropped, the reading stays in []),
    1C (or 1D) '[' 1C 'I' [1B 'H'] + 8 digits ... 1C ']' a glossary link (the text stays); other codes
    (variables, conditions) are kept as {xx}, 02 with its next byte."""
    out, i, kata, run = [], 0, False, []

    def flush():
        if run:
            out.append(_kana(bytes(run).decode("cp932"), kata))
            run.clear()

    while i < len(b):
        c = b[i]
        if 0xA1 <= c <= 0xDF:
            run.append(c)
            i += 1
            continue
        flush()
        if c == 0x1B and i + 1 < len(b) and b[i + 1] in b"HK":
            kata = b[i + 1] == ord("K")
            i += 2
        elif c == 0x1B and i + 1 < len(b) and b[i + 1] in b"hk":  # inside rubies; the mode is kept
            i += 2
        elif c == 0x02 and b[i + 1:i + 2] == b"\x96":
            j = b.index(b"x", i + 2)
            i = j + 1
        elif c == 0x02 and b[i + 1:i + 2] == b"\x97":
            i += 3
        elif c in (0x1C, 0x1D) and b[i + 1:i + 2] == b"[":
            i += 2
            if b[i:i + 1] in (b"\x1c", b"\x1d") and b[i + 1:i + 2] == b"I":
                i += 2
                if b[i:i + 2] == b"\x1bH":
                    i += 2
                i += 8
        elif c in (0x1C, 0x1D) and b[i + 1:i + 2] == b"]":
            i += 2
        elif c == 0x0A:
            out.append("\n")
            i += 1
        elif c == 0x05:
            i += 1
        elif c < 0x20:
            n = 2 if c == 0x02 else 1
            out.append("{" + b[i:i + n].hex() + "}")
            i += n
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC:
            try:
                ch = b[i:i + 2].decode("cp932")
                out.append(SAN11_GAIJI.get(ord(ch), MSG_GAIJI.get(ord(ch), ch)))
            except UnicodeDecodeError:
                out.append("{" + b[i:i + 2].hex() + "}")
            i += 2
        else:
            out.append(chr(c))
            i += 1
    flush()
    return "".join(out).strip("\n")


def messages(game_dir, n):
    """S11MSG0n: LS11; u16 count, then count u32 offsets."""
    with open(os.path.join(game_dir, MSG.format(n)), "rb") as f:
        d = ls11_decode(f.read())
    count = struct.unpack_from("<H", d)[0]
    offs = list(struct.unpack_from(f"<{count}I", d, 2)) + [len(d)]
    return [d[offs[k]:offs[k + 1]] for k in range(count)]


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def pictures(game_dir, out):
    rows = []
    for folder, res, a, b in PICTURES:
        path = os.path.join(game_dir, res)
        ents = link_entries(path)
        os.makedirs(os.path.join(out, "eventcg", folder), exist_ok=True)
        for i in range(a, b + 1):
            im = wftx_frames(link_item(path, ents, i))[0]
            name = f"{folder}/{i:04d}.png"
            im.save(os.path.join(out, "eventcg", name))
            rows.append([name, os.path.basename(res), i, im.width, im.height])
    write_csv(os.path.join(out, "eventcg", "index.csv"), ["file", "source", "item", "w", "h"], rows)
    return len(rows)


def places(game_dir):
    with open(os.path.join(game_dir, "media/scenario/Scenario.s11"), "rb") as f:
        d = f.read()
    return ([sjis(d[0x5A + 25 * i:][:5], PLACE_GAIJI) for i in range(42)] +
            [sjis(d[0x474 + 26 * k:][:7], PLACE_GAIJI) for k in range(45)])


def items(game_dir, out):
    path = os.path.join(game_dir, ITEM_PICTURES[0])
    ents = link_entries(path)
    os.makedirs(os.path.join(out, "items", "pictures"), exist_ok=True)
    for k in range(len(KINDS)):
        wftx_frames(link_item(path, ents, ITEM_PICTURES[1] + k))[0].save(
            os.path.join(out, "items", "pictures", f"{k:02d}.png"))
    names = places(game_dir)
    start, size, count = ITEMS
    table, holders = [], []
    for sc in SCENARIOS:
        fn = os.path.join(game_dir, "media/scenario", sc)
        with open(fn, "rb") as f:
            d = f.read()
        persons = {p["id"]: p["name"] for p in load_san11_persons(fn)}
        for i in range(count):
            r = d[start + size * i:start + size * (i + 1)]
            name = sjis(r[:13])
            if not name:
                continue
            holder, place = struct.unpack_from("<HH", r, 53)
            if sc == SCENARIOS[0]:
                table.append([i, name, sjis(r[13:51]), r[51], r[52], KINDS[r[52]], f"pictures/{r[52]:02d}.png",
                              "unused slot" if place == 767 else ""])
            if place == 767:
                continue
            holders.append([sc, i, name, "" if holder == 0xFFFF else holder, persons.get(holder, ""),
                            "" if place >= len(names) else place, names[place] if place < len(names) else ""])
    write_csv(os.path.join(out, "items", "items.csv"),
              ["id", "name", "reading", "value", "kind", "kind_name", "picture", "notes"], table)
    write_csv(os.path.join(out, "items", "holders.csv"),
              ["scenario", "item", "name", "holder_id", "holder", "place_id", "place"], holders)
    return len([t for t in table if not t[-1]]), len(holders)


# The 繁中版 (depot 628072) keeps the item table of SCEN000.s11 in the same 57-byte records at 0x23E10 (cp950 name,
# empty reading); it has no item descriptions either (S11MSG02 850- is the glossary, not item texts).
ZH_ITEMS = 0x23E10


def zh_items(game_dir) -> dict[int, tuple[str, str]]:
    """item k -> (name, "") of the 繁中版"""
    from san9_extras import ZH_GAIJI, zh_text
    with open(os.path.join(game_dir, "media/scenario", SCENARIOS[0]), "rb") as f:
        d = f.read()
    size, count = ITEMS[1:]
    out = {}
    for k in range(count):
        name = zh_text(d[ZH_ITEMS + size * k:][:13].split(b"\0")[0], gaiji=ZH_GAIJI)
        if name:
            out[k] = (name, "")
    return out


def tables(game_dir, out):
    with open(os.path.join(game_dir, "media/scenario/Scenario.s11"), "rb") as f:
        d = f.read()
    counts = {}
    for name, start, size, count, fields, tail in TABLES:
        rows = []
        for i in range(count):
            r = d[start + size * i:start + size * (i + 1)]
            rows.append([i] + [sjis(r[o:o + n]) for _, o, n in fields] +
                        [struct.unpack_from(fmt, r, o)[0] for _, o, fmt in tail])
        write_csv(os.path.join(out, "tables", f"{name}.csv"),
                  ["id"] + [c for c, _, _ in fields] + [c for c, _, _ in tail], rows)
        counts[name] = len(rows)
    return counts


def texts(game_dir, out):
    msgs = {n: messages(game_dir, n) for n in range(4)}
    for n, folder in [(0, "text"), (1, "text"), (2, "text"), (3, "events")]:
        write_csv(os.path.join(out, folder, f"S11MSG0{n}.csv"), ["index", "text"],
                  [[k, decode_message(b)] for k, b in enumerate(msgs[n])])
    # S11MSG02 0-849 are the 列伝 of person ids 0-849: a short introduction, then 演義 and 史實 parts behind icons
    persons = {p["id"]: p["name"] for p in load_san11_persons(os.path.join(game_dir, "media/scenario/Scen000.s11"))}
    rows = []
    for k in range(850):
        text = decode_message(msgs[2][k])
        if not text:
            continue
        kind, part = "簡介", []
        for line in text.split("\n"):
            if line[:1] in BIOGRAPHY_ICONS:
                if part:
                    rows.append([k, persons.get(k, ""), kind, "\n".join(part)])
                kind, part = BIOGRAPHY_ICONS[line[0]], [line[1:]]
            else:
                part.append(line)
        if part:
            rows.append([k, persons.get(k, ""), kind, "\n".join(part)])
    write_csv(os.path.join(out, "text", "biographies.csv"), ["id", "name", "kind", "text"], rows)
    return {n: len(m) for n, m in msgs.items()}, len(rows)


# biography.py reads the Steam 繁中版 (depot 628072): S11MSG02 has the 列傳 in the Japanese order (BIO_INDEX),
# cp950 with the gaiji of 三國志IX (san9_extras.ZH_GAIJI) and 02 96 'NNx' colour codes; the 演義 part starts with
# the icon FA60 and the 史實 part with FA49 (the Japanese F0AF, F0AE). The scenario's person records are the Japanese
# ones (152 bytes, surname +0, given name +5) but start at 17760 (SCEN000.s11).
BIO_LANG = "zh-Hant"
ZH_ICONS = {b"\xfa\x60": "演義", b"\xfa\x49": "史實"}
ZH_PERSONS = 17760
# S11MSG02 entry of a person's 列傳, by content (🟡 cross: the names, offices and stories of the Japanese texts): the
# same number up to 669 and for 700-713 (霊帝 … 南斗); 699 is a second 献帝, 714-721 and 724 are the tribe and 盗賊
# roles, 722, 723 are 張譲 729 and 蹇碩 730, 725-756 the 古武將 800-831 in order, 757 on the glossary
BIO_INDEX = {**{k: k for k in [*range(670), *range(700, 714)]}, 729: 722, 730: 723,
             **{800 + k: 725 + k for k in range(32)}}
# the Japanese 記述なし; 並供記載 (once) is a typo of 並無記載
ZH_NO_RECORD = {"沒有記載", "並無記載", "沒有記述", "並供記載"}


def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    import re
    from biography import sections
    from san9_extras import zh_text
    msgs = messages(game_dir, 2)
    out = {}
    for k, m in BIO_INDEX.items():
        lines = re.sub(rb"\x02\x96[0-9]+x", b"", msgs[m]).rstrip(b"\x05").split(b"\n")
        intro, parts = zh_text(lines[0]).strip(), []
        for line in lines[1:]:
            if line[:2] in ZH_ICONS:
                parts.append((ZH_ICONS[line[:2]], zh_text(line[2:]).strip()))
            elif parts:
                parts[-1] = (parts[-1][0], parts[-1][1] + zh_text(line).strip())
            else:
                intro += zh_text(line).strip()
        parts = [(kind, t) for kind, t in parts if t.rstrip("。") not in ZH_NO_RECORD]
        if sections(intro, parts):
            out[k] = sections(intro, parts)
    return out


def bio_names(game_dir) -> dict[int, str]:
    from san9_extras import zh_text
    _, size, count = SAN11_PERSONS
    with open(os.path.join(game_dir, "media/scenario/SCEN000.s11"), "rb") as f:
        data = f.read()
    out = {}
    for k in range(count):
        r = data[ZH_PERSONS + k * size:ZH_PERSONS + (k + 1) * size]
        name = zh_text(r[0:5].split(b"\0")[0]) + zh_text(r[5:10].split(b"\0")[0])
        if name:
            out[k] = name
    return out


def worldmap(game_dir, out):
    """The minimaps, the four 1025x1025 colour maps and a hex rendering of SHEX0008 (terrain, black territory
    borders): flat-topped hexes, x is the column, odd columns half a row lower (picked by the shortest borders)."""
    path = os.path.join(game_dir, PK_RES)
    ents = link_entries(path)
    d = os.path.join(out, "worldmap")
    os.makedirs(d, exist_ok=True)
    rows = []
    for stem, i, k in WORLD_PICTURES:
        im = wftx_frames(link_item(path, ents, i))[k]
        im.save(os.path.join(d, f"{stem}.png"))
        rows.append([f"{stem}.png", os.path.basename(PK_RES), i, k, im.width, im.height])
    for n, i in enumerate(WORLD_COLOURS):
        b = link_item(path, ents, i)
        assert b[:8] == b"GCOL0001" and len(b) == 8 + 3 * 1025 * 1025
        im = Image.frombytes("RGB", (1025, 1025), b[8:], "raw", "BGR").transpose(Image.Transpose.TRANSPOSE)
        im.save(os.path.join(d, f"colour-{n}.png"))
        rows.append([f"colour-{n}.png", os.path.basename(PK_RES), i, 0, 1025, 1025])
    b = link_item(path, ents, WORLD_HEX)
    assert b[:8] == b"SHEX0008"
    cell = lambda x, y, k: b[8 + 11 * (200 * x + y) + k]
    centre = lambda x, y: (12 * x + 8, 12 * y + 6 + 6 * (x % 2))
    im = Image.new("RGB", (12 * 200 + 4, 12 * 200 + 6), (255, 255, 255))
    draw = ImageDraw.Draw(im)
    corners = [(-8, 0), (-4, -6), (4, -6), (8, 0), (4, 6), (-4, 6)]  # edge j joins corner j and j + 1
    sides = [(-1, -1), (0, -1), (1, -1), (1, 0), (0, 1), (-1, 0)]       # neighbour column, row (odd shifts +1)
    for x in range(200):
        for y in range(200):
            cx, cy = centre(x, y)
            draw.polygon([(cx + a, cy + c) for a, c in corners], fill=TERRAIN_RGB[cell(x, y, 0)])
    for x in range(200):
        for y in range(200):
            cx, cy = centre(x, y)
            for j, (dx, dy) in enumerate(sides):
                nx, ny = x + dx, y + dy + (x % 2 if dx else 0)
                if 0 <= nx < 200 and 0 <= ny < 200 and cell(nx, ny, 1) != cell(x, y, 1):
                    (a, c), (e, f) = corners[j], corners[(j + 1) % 6]
                    draw.line([(cx + a, cy + c), (cx + e, cy + f)], fill=(0, 0, 0), width=2)
    im.save(os.path.join(d, "terrain.png"))
    rows.append(["terrain.png", os.path.basename(PK_RES), WORLD_HEX, 0, im.width, im.height])
    write_csv(os.path.join(d, "index.csv"), ["file", "source", "item", "frame", "w", "h"], rows)
    return len(rows)


@click.command("san11-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam install (628070)")
@click.option("--out", required=True, type=click.Path())
def san11_extras(game_dir, out):
    """三國志11 PK: event stills, items, rule tables (特技, 技巧, 施設 ...) and the S11MSG texts."""
    print(f"{pictures(game_dir, out)} pictures")
    print(f"{worldmap(game_dir, out)} world map pictures")
    n, h = items(game_dir, out)
    print(f"{n} items, {h} holder rows, {len(KINDS)} item pictures")
    print("tables:", tables(game_dir, out))
    m, b = texts(game_dir, out)
    print("messages:", m, f"biography parts: {b}")


if __name__ == "__main__":
    san11_extras()
