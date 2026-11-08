"""三國志11 PK (Steam 628070): event stills, items (寶物), rule tables and message texts, extracted for archiving.

See notes/san11.md「事件、插圖、道具」. Usage (from dekoei/):
    dekoei.py san11-extras --game-dir ../games/san11pk-win --out ../games/san11pk-win/extract
"""
import csv
import os
import struct
import unicodedata

import click
from PIL import Image

from ls11 import ls11_decode
from sango import SAN11_GAIJI, load_san11_persons

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


@click.command("san11-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam install (628070)")
@click.option("--out", required=True, type=click.Path())
def san11_extras(game_dir, out):
    """三國志11 PK: event stills, items, rule tables (特技, 技巧, 施設 ...) and the S11MSG texts."""
    print(f"{pictures(game_dir, out)} pictures")
    n, h = items(game_dir, out)
    print(f"{n} items, {h} holder rows, {len(KINDS)} item pictures")
    print("tables:", tables(game_dir, out))
    m, b = texts(game_dir, out)
    print("messages:", m, f"biography parts: {b}")


if __name__ == "__main__":
    san11_extras()
