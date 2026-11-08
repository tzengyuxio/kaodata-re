"""信長の野望・将星録 with PK (Steam, appid 628100): event pictures, 家宝, 家紋, the PK message file, the big map and
the sprite sets, written under --out (notes/nobu7.md「事件、插圖、道具」).

- Every picture file (EvtStill, GaikouCG, ITEMDATA, KAMON, LOGO, MSMAP, HEXMAP, EditGrp, HEXUNIT, HEXMARK, ATKGRP,
  Mapgrp01, WINFRAME) is the ATKMAP.NB7 container: u32 count, count x (u32 offset, size, w, h), 8-bit pixels from
  4 + 16 count. The palette is grppal.nb7 part 0 (B, R, G), the one the faces and the 攻城圖 use; colours 0-9 are
  the key colour of the sprites and are written transparent.
- mainmap.nb7: 26828 tiles of 32x32 (raw, 8 bit), column-major in columns of 76 tiles: tile i at x (i // 76) * 32,
  y (i % 76) * 32, giving the 11296 x 2432 map of Japan.
- 家宝: scenario files 0x15F30, 200 records of 0x20 bytes: +0 u16 number, +2 name (14 bytes), +0x10 kind (0-29),
  +0x12 grade (1-10, 1 the best), +0x14 picture (ITEMDATA.NB7, 0-26), +0x16 value, +0x18 flag, +0x1A holder (person
  number, 0xFFFF none), +0x1C effect group. Names with readings and descriptions are message.nb7 parts 32-35.
- 大名 record (0xD0 + 0x118 (n - 1)) +0x04 is the 家紋 number (KAMON.NB7).
- message.nb7 (LS11, 45 parts): u16 count, offsets, strings; half-width katakana, ESC K / ESC H switch the script,
  ESC k opens a reading; 0x02 xx yy and 0x01 C xx yy are variables, 0x05 ends a page.
"""
import csv
import os
import re
import struct

import click
from PIL import Image

import ls11
import wiki_nobu7 as w

ITEMS, ITEM_SIZE, ITEM_COUNT = 0x15F30, 0x20, 200
DAIMYO, DAIMYO_SIZE, DAIMYO_COUNT = 0xD0, 0x118, 30
MAP_TILE, MAP_COLUMN = 32, 76
# (file, folder): picture sets written one PNG per entry
PICTURES = [
    ("EvtStill.nb7", "eventcg/still"),      # 32 x 360x160 event stills
    ("GaikouCG.nb7", "eventcg/gaikou"),     # 3 x 760x504 外交 scenes
    ("LOGO.NB7", "eventcg/logo"),           # 6 x 768x512 title pictures
    ("ITEMDATA.NB7", "items/pictures"),     # 27 x 64x64, one per 家宝 picture number
    ("KAMON.NB7", "kamon"),                 # 147 x 24x24
    ("MSMAP.NB7", "map/msmap"),             # 18 small maps (4 sizes)
    ("HEXMAP.NB7", "map/hexmap"),           # 32 field pieces
    ("EditGrp.nb7", "ui/editgrp"),          # 5 edit / info panels
    ("HEXUNIT.NB7", "sprites/hexunit"),     # 1296 x 144x104 unit sprites
    ("HEXMARK.NB7", "sprites/hexmark"),     # 205 map marks
    ("ATKGRP.NB7", "sprites/atkgrp"),       # 127 siege sprites
    ("Mapgrp01.nb7", "sprites/mapgrp"),     # 641 map tiles and marks
    ("WINFRAME.NB7", "ui/winframe"),        # 468 window parts
]
# message.nb7 parts holding (name ESC k reading, description) pairs
CASTLE_PARTS, KAHOU_PARTS, KANI_PARTS, KASSEN_PART, HELP_PART = (30, 31), (32, 33, 34, 35), (36, 37, 38, 39, 40), 42, 27


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def palette(game_dir):
    p = ls11.ls11_decode_parts(_read(os.path.join(game_dir, "grppal.nb7")))[0]
    return b"".join(bytes((p[3 * c + 1], p[3 * c + 2], p[3 * c])) for c in range(256))


def pictures(data):
    n = struct.unpack_from("<I", data)[0]
    base = 4 + 16 * n
    for i in range(n):
        o, s, wd, h = struct.unpack_from("<4I", data, 4 + 16 * i)
        yield wd, h, data[base + o:base + o + s]


def _image(wd, h, pixels, pal):
    im = Image.frombytes("P", (wd, h), pixels)
    im.putpalette(pal)
    if min(pixels) < 10:
        im.info["transparency"] = bytes(0 if c < 10 else 255 for c in range(256))
    return im


def write_pictures(game_dir, out, pal):
    counts = {}
    for name, folder in PICTURES:
        d = os.path.join(out, folder)
        os.makedirs(d, exist_ok=True)
        n = 0
        for i, (wd, h, px) in enumerate(pictures(_read(os.path.join(game_dir, name)))):
            _image(wd, h, px, pal).save(os.path.join(d, f"{i:04d}.png"))
            n += 1
        counts[folder] = n
    return counts


def main_map(game_dir, out, pal):
    data = _read(os.path.join(game_dir, "mainmap.nb7"))
    tiles = len(data) // (MAP_TILE * MAP_TILE)
    cols = tiles // MAP_COLUMN
    im = Image.new("P", (cols * MAP_TILE, MAP_COLUMN * MAP_TILE))
    im.putpalette(pal)
    t = MAP_TILE * MAP_TILE
    for i in range(tiles):
        im.paste(Image.frombytes("P", (MAP_TILE, MAP_TILE), data[i * t:(i + 1) * t]),
                 ((i // MAP_COLUMN) * MAP_TILE, (i % MAP_COLUMN) * MAP_TILE))
    os.makedirs(os.path.join(out, "map"), exist_ok=True)
    im.save(os.path.join(out, "map", "mainmap.png"))
    return im.size


def clean(s: str) -> str:
    """Message text with readings and script switches removed, variables as {..}, half-width kana widened."""
    s = re.sub(r"\x1b[A-Za-z]", "", s)
    s = re.sub(r"\x01C(..)", lambda m: "{C:" + m.group(1).encode("cp932", "replace").hex() + "}", s, flags=re.S)
    s = re.sub(r"\x02(..)", lambda m: "{v:" + m.group(1).encode("cp932", "replace").hex() + "}", s, flags=re.S)
    s = re.sub(r"\x05+", "", s)
    s = re.sub(r"[\x00-\x09\x0b-\x1f]", lambda m: f"{{{ord(m.group()):02x}}}", s)
    return w.half_kana(s).strip()


HEAD = re.compile(r"^(.*?)　\x1bk(.*?)(?:\x1bH(.*))?$", re.S)


def _strings(parts, k):
    return [x.decode("cp932", "replace") for x in w.message_strings(parts[k])]


def named_entries(parts, keys):
    """(name, reading, extra, description) from (header, text) pairs."""
    out = []
    for k in keys:
        s = _strings(parts, k)
        for head, text in zip(s[0::2], s[1::2]):
            m = HEAD.match(head.replace("\x05", ""))
            name, reading, extra = m.groups() if m else (head, "", "")
            out.append((w.half_kana(re.sub(r"\x1b[A-Za-z]", "", name)).strip(), w.half_kana(reading or "").strip(), clean(extra or ""),
                        clean(text)))
    return out


def kassen(parts):
    """合戦 entries of part 42: a header string, then text strings up to the one ending in 0x05."""
    out, cur = [], None
    for s in _strings(parts, KASSEN_PART):
        m = HEAD.match(s.replace("\x05", "")) if "\x1bk" in s else None
        if m:
            cur = [clean(m.group(1)), w.half_kana(m.group(2)).strip(),
                   clean(m.group(3) or "").strip("（）() 　"), ""]
            out.append(cur)
        elif cur is not None:
            cur[3] += s
    for e in out:
        e[3] = clean(e[3])
    return out


def _csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(header)
        wr.writerows(rows)


def _person_names(data):
    return {n: w._name(data, k, "cp932") for n, k in w._records(data).items()}


def _kata(s):
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def items(game_dir, out, parts, scenarios):
    text = named_entries(parts, KAHOU_PARTS)
    main = scenarios[w.MAIN]
    names = [_person_names(d) for d in scenarios]
    rows = []
    for i in range(ITEM_COUNT):
        o = ITEMS + ITEM_SIZE * i
        num = struct.unpack_from("<H", main, o)[0]
        name = main[o + 2:o + 16].split(b"\0")[0].decode("cp932")
        kind, grade, pic, value, flag, _, effect, _ = struct.unpack_from("<8H", main, o + 0x10)
        holders = []
        for d, ns in zip(scenarios, names):
            h = struct.unpack_from("<H", d, o + 0x1A)[0]
            holders.append("" if h == 0xFFFF else f"{h} {ns.get(h, '?')}")
        rows.append([num, name, "" if _kata(text[i][0]) == _kata(name) else text[i][0], text[i][1], kind, grade, pic, f"{pic:04d}.png", value, flag, effect, *holders,
                     text[i][3]])
    _csv(os.path.join(out, "items", "kahou.csv"),
         ["no", "name", "name_message", "reading", "kind", "grade", "picture", "file", "value", "flag", "effect",
          *[f"holder_s{k + 1:02d}" for k in range(len(scenarios))], "description"], rows)
    helps = [clean(x) for x in _strings(parts, HELP_PART)]
    _csv(os.path.join(out, "items", "help_texts.csv"), ["index", "group", "text"],
         [[i, "技術" if i < 10 else "家宝効能" if i < 30 else "城修行", t] for i, t in enumerate(helps)])
    return len(rows), sum(1 for r in rows for h in r[11:11 + len(scenarios)] if h)


def kamon(out, scenarios):
    rows = []
    for s, d in enumerate(scenarios):
        ns = _person_names(d)
        for n in range(1, DAIMYO_COUNT + 1):
            o = DAIMYO + DAIMYO_SIZE * (n - 1)
            no, lord, crest = struct.unpack_from("<3H", d, o)
            if lord:
                rows.append([s + 1, no, lord, ns.get(lord, "?"), crest, f"{crest:04d}.png"])
    _csv(os.path.join(out, "kamon", "daimyo.csv"), ["scenario", "daimyo", "lord", "lord_name", "kamon", "file"], rows)
    return len(rows)


def texts(out, parts):
    rows = [[k, i, clean(s)] for k in range(len(parts)) for i, s in enumerate(_strings(parts, k))]
    _csv(os.path.join(out, "events", "messages.csv"), ["part", "index", "text"], rows)
    ks = kassen(parts)
    _csv(os.path.join(out, "events", "kassen.csv"), ["name", "reading", "sides", "text"], ks)
    castles = named_entries(parts, CASTLE_PARTS)
    _csv(os.path.join(out, "tables", "castles.csv"), ["index", "name", "reading", "description"],
         [[i + 1, n, r, t] for i, (n, r, _, t) in enumerate(castles)])
    kani = named_entries(parts, KANI_PARTS)
    _csv(os.path.join(out, "tables", "kani.csv"), ["index", "name", "reading", "description"],
         [[i + 1, n, r, t] for i, (n, r, _, t) in enumerate(kani)])
    return len(rows), len(ks), len(castles), len(kani)


@click.command("nobu7-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam files (games/nobu7pk-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/nobu7pk-win/extract)")
def nobu7_extras(game_dir, out):
    """信長の野望・将星録 PK: event pictures, 家宝, 家紋, messages, the big map and sprites."""
    pal = palette(game_dir)
    parts = ls11.ls11_decode_parts(_read(os.path.join(game_dir, "message.nb7")))
    scenarios = w._scenarios(game_dir)
    for folder, n in write_pictures(game_dir, out, pal).items():
        click.echo(f"{folder}: {n}")
    click.echo(f"map/mainmap.png: {main_map(game_dir, out, pal)}")
    n, held = items(game_dir, out, parts, scenarios)
    click.echo(f"kahou: {n} ({held} holder entries over {len(scenarios)} scenarios)")
    click.echo(f"kamon/daimyo.csv: {kamon(out, scenarios)} rows")
    m, ks, cs, kn = texts(out, parts)
    click.echo(f"messages: {m}, kassen: {ks}, castles: {cs}, kani: {kn}")


if __name__ == "__main__":
    nobu7_extras()
