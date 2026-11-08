"""信長の野望・新生 with PK (Steam, appid 1336980): event pictures, 家宝, 家紋, event texts and the 歴代 faces, written
under --out as eventcg/, items/, kamon/, events/, rekidai/ and banners/ (notes/nobu16.md「事件、插圖、道具」).

- RES*/res_*.bin are 'LINK' archives: +4 u32 entry count, +8 u32 0x20 when an inner (picture) LINK, else 1; the
  (u32 offset, u32 size) entries follow from 0x20 (inner) or 0x10 (outer), offsets relative to that LINK. An inner
  LINK has +0x10 u32 the offset of a 12-byte rectangle per cell (u16 x, y, w, h, u32 0); an empty cell is size 0 or
  8 x 8.
- Every cell (and the MSG files) is the "01 01" LZ4 wrapper: +8 u64 size, +0x10 u64 packed size, an LZ4 block from
  +0x18 ("00 01": stored). Inside is a GT1G0600 texture set; each 8-byte texture header has +1 the format (0x59 BC1, 0x5B BC3, 0x01
  R8G8B8A8), +2 log2 height << 4 | log2 width, +7 bit 4 an extra header whose size is the next u32.
- MSG*/<lang>/*.bin: u32 table count, (u32 offset, u32 size) per table; each table is an XL string table (+6 u16
  columns, +8 rows, +10 row size, +12 header size, a type byte per column from +0x10; strings are UTF-16LE at the
  header size + the row's u32). Text marks: ESC C A/B/C ... ESC C Z colour a person / clan / place, written here as
  {A}…{Z}.
"""
import csv
import hashlib
import os
import re
import struct
from collections import Counter

import click
from PIL import Image

STILL = "RES/res_still.bin"
# res_still.bin entries -> output folder (all pictures are named NNNN.png by cell)
STILL_SETS = [(0, "eventcg/event"), (1, "eventcg/small"), (2, "eventcg/wide"), (18, "eventcg/other")]
EXTRA_STILLS = [("RES/res_exp.bin", 30, "eventcg/exp"), ("RES_JP_PK/res_lang_pk.bin", 22, "eventcg/pk")]
ITEM_PICTURES = 3  # res_still.bin entry: 123 家宝 pictures at 512 x 512 (cell 122 is the blank one)
# picture cell of 家宝 k when not k (by eye: 慶長日本図 is the last picture, the ones after it moved up one)
ITEM_PICTURE = {105: 120, **{k: k - 1 for k in range(106, 121)}}
# res_still.bin entries 4-17: faces of the earlier games at 96 x 120 (series guessed from count and style)
REKIDAI = {4: "nobu2", 5: "nobu3", 6: "nobu4", 7: "nobu5", 8: "nobu6", 9: "nobu7", 10: "nobu8", 11: "nobu9",
           12: "nobu10", 13: "nobu11", 14: "nobu12", 15: "nobu13", 16: "nobu14", 17: "nobu15"}
GRP = "RES/res_grp.bin"
KAMON_SETS = [(0, "flat"), (4, "gold")]  # 257 家紋 at 1024 x 1024: white (alpha) and gold; entry 3 is flat at 256
PK = "RES_PK/res_pk.bin"
PK_KAMON = {"flat": 405, "gold": 409}  # PK replacements (cell 137)
BANNERS = [("RES_JP/res_lang.bin", 4, "banners/base"), ("RES_JP_PK/res_lang_pk.bin", 21, "banners/pk")]
MSG = "MSG_PK/{}/{}.bin"
ITEM_NAMES, ITEM_COUNT = 14119, 122  # 家宝 names in msgdata (the descriptions are msgire, same order)
TITLES, TITLE_ROWS, READING = 13201, 799, 799  # event titles in msgev; their katakana reading is 799 rows on
TITLE_DUMMY = re.compile(r"タイトルダミー_(\d+)$")  # unused title rows
EVENT_FILES = ["RES/res_event.bin", "RES_PK/res_eventpk.bin"]


def lz4_block(src: bytes, size: int) -> bytes:
    """A raw LZ4 block (no frame), decoded to size bytes."""
    out, i, n_src = bytearray(), 0, len(src)
    while i < n_src:
        tok = src[i]
        i += 1
        n = tok >> 4
        if n == 15:
            while src[i] == 255:
                n += 255
                i += 1
            n += src[i]
            i += 1
        out += src[i:i + n]
        i += n
        if i >= n_src or len(out) >= size:
            break
        back = src[i] | src[i + 1] << 8
        i += 2
        m = tok & 15
        if m == 15:
            while src[i] == 255:
                m += 255
                i += 1
            m += src[i]
            i += 1
        m += 4
        s = len(out) - back
        if back >= m:
            out += out[s:s + m]
        else:  # the match overlaps what it writes
            for k in range(m):
                out.append(out[s + k])
    assert len(out) == size, (len(out), size)
    return bytes(out)


def unpack(c: bytes) -> bytes:
    """The "01 01" LZ4 wrapper; "00 01" is the same header with the data stored."""
    if c[1:2] != b"\x01" or c[0] > 1:
        return bytes(c)
    size, packed = struct.unpack_from("<QQ", c, 8)
    if c[0] == 0:
        return bytes(c[0x18:0x18 + size])
    return lz4_block(bytes(c[0x18:0x18 + packed]), size)


def link(d: bytes, base: int = 0) -> list[tuple[int, int]]:
    """(absolute offset, size) of the entries of the LINK at base."""
    assert d[base:base + 4] == b"LINK", d[base:base + 8]
    n, kind = struct.unpack_from("<2I", d, base + 4)
    table = base + (0x20 if kind == 0x20 else 0x10)
    return [(base + o, s) for o, s in (struct.unpack_from("<2I", d, table + 8 * i) for i in range(n))]


def cells(d: bytes, base: int):
    """(cell, w, h, packed bytes) of the non-empty cells of a picture LINK."""
    rects = struct.unpack_from("<I", d, base + 0x10)[0]
    for i, (o, s) in enumerate(link(d, base)):
        x, y, w, h = struct.unpack_from("<4H", d, base + rects + 12 * i)
        if s and (w, h) != (8, 8):
            assert (x, y) == (0, 0)
            yield i, w, h, d[o:o + s]


BCN = {0x59: 1, 0x5B: 3}


def texture(t: bytes, w: int, h: int) -> Image.Image:
    """The first texture of a GT1G0600 set, cropped to w x h."""
    assert t[:8] == b"GT1G0600", t[:8]
    heads = struct.unpack_from("<I", t, 0x0C)[0]
    o = heads + struct.unpack_from("<I", t, heads)[0]
    fmt, dim = t[o + 1], t[o + 2]
    tw, th = 1 << (dim & 15), 1 << (dim >> 4)
    p = o + 8 + (struct.unpack_from("<I", t, o + 8)[0] if t[o + 7] & 0x10 else 0)
    if fmt in BCN:
        im = Image.frombytes("RGBA", (tw, th), t[p:], "bcn", BCN[fmt])
    elif fmt == 0x01:
        im = Image.frombytes("RGBA", (tw, th), t[p:p + 4 * tw * th])
    else:
        raise ValueError(f"texture format {fmt:#x}")
    return im.crop((0, 0, w, h))


def _read(game_dir, rel) -> bytes:
    with open(os.path.join(game_dir, rel), "rb") as f:
        return f.read()


def _csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def save_cells(d: bytes, base: int, folder: str) -> list[tuple]:
    """Every picture of a picture LINK as folder/NNNN.png; rows (cell, file, w, h, sha1 of the packed cell)."""
    os.makedirs(folder, exist_ok=True)
    rows = []
    for i, w, h, c in cells(d, base):
        name = f"{i:04d}.png"
        texture(unpack(c), w, h).save(os.path.join(folder, name))
        rows.append((i, name, w, h, hashlib.sha1(c).hexdigest()[:12]))
    return rows


def eventcg(game_dir, out) -> int:
    rows = []
    d = _read(game_dir, STILL)
    top = link(d)
    for e, folder in STILL_SETS:
        rows += [(folder, STILL, e) + r[:4] for r in save_cells(d, top[e][0], os.path.join(out, folder))]
    for rel, e, folder in EXTRA_STILLS:
        x = _read(game_dir, rel)
        rows += [(folder, rel, e) + r[:4] for r in save_cells(x, link(x)[e][0], os.path.join(out, folder))]
    _csv(os.path.join(out, "eventcg", "index.csv"), ["folder", "source", "entry", "cell", "file", "w", "h"], rows)
    return len(rows)


def banners(game_dir, out) -> int:
    n = 0
    for rel, e, folder in BANNERS:
        x = _read(game_dir, rel)
        n += len(save_cells(x, link(x)[e][0], os.path.join(out, folder)))
    return n


def rekidai(game_dir, out) -> int:
    d = _read(game_dir, STILL)
    top = link(d)
    rows = []
    for e, game in REKIDAI.items():
        r = save_cells(d, top[e][0], os.path.join(out, "rekidai", f"{e:02d}_{game}"))
        rows.append((e, f"{e:02d}_{game}", game, len(r)))
    _csv(os.path.join(out, "rekidai", "index.csv"), ["entry", "folder", "series_guess", "faces"], rows)
    return sum(r[3] for r in rows)


def strings(game_dir, lang, name, table=0) -> list[str]:
    d = unpack(_read(game_dir, MSG.format(lang, name)))
    o, s = struct.unpack_from("<2I", d, 4 + 8 * table)
    b = d[o:o + s]
    assert b[:2] == b"XL"
    cols, rows, size, header = struct.unpack_from("<4H", b, 6)
    out = []
    for r in range(rows):
        p = header + struct.unpack_from("<I", b, header + r * size)[0]
        e = p
        while b[e:e + 2] != b"\0\0":
            e += 2
        out.append(b[p:e].decode("utf-16-le"))
    return out


def text(s: str) -> str:
    return re.sub("\x1bC([A-Z])", r"{\1}", s)


def items(game_dir, out) -> int:
    names, names_tc = strings(game_dir, "JP", "msgdata"), strings(game_dir, "TC", "msgdata")
    desc, desc_tc = strings(game_dir, "JP", "msgire"), strings(game_dir, "TC", "msgire")
    assert len(desc) == ITEM_COUNT
    d = _read(game_dir, STILL)
    pics = {r[0]: r for r in save_cells(d, link(d)[ITEM_PICTURES][0], os.path.join(out, "items", "kahou"))}
    cell = [ITEM_PICTURE.get(k, k) for k in range(ITEM_COUNT)]
    rows = [(k, names[ITEM_NAMES + k], names_tc[ITEM_NAMES + k], f"kahou/{pics[cell[k]][1]}", desc[k], desc_tc[k])
            for k in range(ITEM_COUNT)]
    _csv(os.path.join(out, "items", "kahou.csv"), ["id", "name", "nameZh", "picture", "description",
                                                  "descriptionZh"], rows)
    return ITEM_COUNT


def kamon(game_dir, out) -> int:
    d, pk = _read(game_dir, GRP), _read(game_dir, PK)
    top, pk_top = link(d), link(pk)
    rows = {}
    for e, style in KAMON_SETS:
        folder = os.path.join(out, "kamon", style)
        for i, name, w, h, sha in save_cells(d, top[e][0], folder):
            rows.setdefault(i, [i, name, "", sha])
        for i, name, w, h, sha in save_cells(pk, pk_top[PK_KAMON[style]][0], folder):
            rows[i][2] = "PK"  # the PK picture replaces the base game's
            rows[i][3] = sha
    common = Counter(r[3] for r in rows.values()).most_common(1)[0]
    for r in rows.values():
        if common[1] > 1 and r[3] == common[0]:
            r[2] = (r[2] + " placeholder").strip()  # the 「欠」 picture of unused slots
    _csv(os.path.join(out, "kamon", "index.csv"), ["kamon", "file", "notes", "sha1"],
         [r for _, r in sorted(rows.items())])
    return sum(1 for r in rows.values() if "placeholder" not in r[2])


def event_titles(game_dir) -> dict[int, set[int]]:
    """Title (row - TITLES) -> event numbers: an event record (RES/res_event.bin, RES_PK/res_eventpk.bin, one LZ4
    cell per cut set) starts with u32 event number, u32 title."""
    out = {}
    for rel in EVENT_FILES:
        d = _read(game_dir, rel)
        for o, s in link(d):
            if s:
                number, title = struct.unpack_from("<2I", unpack(d[o:o + s]), 0)
                if number:
                    out.setdefault(title, set()).add(number)
    return out


def events(game_dir, out) -> int:
    ja, tc = strings(game_dir, "JP", "msgev"), strings(game_dir, "TC", "msgev")
    assert len(ja) == len(tc)
    numbers = event_titles(game_dir)
    rows = [(k, TITLES + k, ja[TITLES + k], ja[TITLES + READING + k], tc[TITLES + k],
             " ".join(map(str, sorted(numbers.get(k, ())))))
            for k in range(TITLE_ROWS) if ja[TITLES + k] and not TITLE_DUMMY.match(ja[TITLES + k])]
    _csv(os.path.join(out, "events", "titles.csv"), ["title", "row", "name", "reading", "nameZh", "events"], rows)
    _csv(os.path.join(out, "events", "msgev.csv"), ["row", "ja", "zh"],
         [(i, text(a), text(b)) for i, (a, b) in enumerate(zip(ja, tc)) if a or b])
    return len(rows)


@click.command("nobu16-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam files (games/nobu16pk-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/nobu16pk-win/extract)")
def nobu16_extras(game_dir, out):
    """信長の野望・新生 PK: event pictures, 家宝, 家紋, event texts and the 歴代 faces."""
    click.echo(f"events: {events(game_dir, out)} titles")
    click.echo(f"items: {items(game_dir, out)}")
    click.echo(f"kamon: {kamon(game_dir, out)}")
    click.echo(f"eventcg: {eventcg(game_dir, out)}")
    click.echo(f"banners: {banners(game_dir, out)}")
    click.echo(f"rekidai: {rekidai(game_dir, out)}")


if __name__ == "__main__":
    nobu16_extras()
