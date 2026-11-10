"""信長の野望・創造 with PK (nobu14pk-win, Steam 292990, Traditional Chinese): faces, event pictures, event scripts,
家宝, 戦法 titles and 家紋, written under --out as faces/, eventcg/, events/, items/ and kamon/ (notes/nobu14.md「事件、插圖、道具」).

- RES_PK/res_grp.bin is a LINK archive like 大志 (nobu15_extras._outer/_read/_cells); the picture entries are LINKs of
  cells, each an 'LWC\\x1a'-packed (or plain) GT1G0600 texture. 創造 also uses BC1 (format 0x06) and BC2 (0x07).
- Faces: entries 31 (240x240) and 32 (422x600) hold 7047 slots, 2510 (470) of them filled. A person's face number
  (person record +24) is the slot below 2000; 7400+k is slot 2281+k, 9000+k is 3878+k, 9500+k is 3896+k (FACE_BLOCKS).
  4000-8214 are not resolved, so their slots carry no name. Face 0 (織田信長) is also what persons without a face of
  their own point to; index.csv names only 信長 there.
- Entries 36-47 are 64x80 faces from earlier titles (歴代武将).
- RES_PK/res_event.bin: 1000 slots, 548 records of 47108 bytes: +0 u32 id, +0xB8 i32 step count (-1 unused), steps of 0xB8 bytes
  from +0xBC: +0 i32 background, +4 person slot, +8 second person slot (-1 none), +0xC 1 when the second person
  speaks, +0x10 speaker (16), +0x20 text (128), +0xA0 six i32 (commands, all -1 in ordinary steps).
- Event titles: NOBU14PK.exe holds 56-byte records (u32 event id, i32 scenario year or -1, name 48); found by 天下布武.
- 家宝 pictures: entry 8 cells 0-53 (140x140) and 54-107 (32x32 icons); the item's 細類 (scenario record +4) is the
  picture number.
"""
import os
import struct
from multiprocessing import Pool

import click
from PIL import Image

import ls11
import wiki_nobu14 as W
from nobu15_extras import _cells, _csv, _read, placeholders

RES = ("RES_PK", "res_grp.bin")
FACES = [(31, "240"), (32, "large")]
REKIDAI = range(36, 48)
PICTURE_SETS = [
    (15, "ichimaie"),     # 1280x720 event pictures
    (7, "still"),         # 720x400 event stills
    (27, "senpo_title"),  # 440x128 戦法 calligraphy
]
KAHOU = 8  # 54 x 140x140 + 54 x 32x32
KAMON, KAMON_CELL, KAMON_COLS = 9, 72, 28  # one 2048x1024 atlas, 72x72 cells in rows of 28
FACE_BLOCKS = [(9500, 3896), (9000, 3878), (7400, 2281)]  # (first face number, its slot); below 2000 slot = number
BC = {0x06: 1, 0x07: 2, 0x08: 3, 0x59: 1, 0x5B: 3}
EVENT_SIZE, STEPS, STEP0, STEP = 47108, 0xB8, 0xBC, 0xB8
TITLE_REC = 56


def face_slot(n):
    if n < 2000:
        return n
    for first, slot in FACE_BLOCKS:
        if first <= n < first + 100:
            return slot + n - first
    return None


def _texture(t):
    assert t[:8] == b"GT1G0600", t[:8]
    o, = struct.unpack_from("<I", t, 0x0C)
    o += struct.unpack_from("<I", t, o)[0]
    fmt, dim = t[o + 1], t[o + 2]
    w, h = 1 << (dim & 15), 1 << (dim >> 4)
    p = o + 8 + (struct.unpack_from("<I", t, o + 8)[0] if t[o + 7] & 0x10 else 0)
    if fmt in BC:
        n = BC[fmt]
        return Image.frombytes("RGBA", (w, h), t[p:p + w * h // (2 if n == 1 else 1)], "bcn", n)
    assert fmt == 1, hex(fmt)
    return Image.frombytes("RGBA", (w, h), t[p:p + 4 * w * h], "raw", "BGRA")


def _save_cell(job):
    data, rect, dst = job
    if data[:4] == b"LWC\x1a":
        data = ls11.lwc_decode(data)
    x, y, w, h = rect
    _texture(data).crop((x, y, x + w, y + h)).save(dst)
    return dst


def _dump(link, folder, jobs, cells=None):
    os.makedirs(folder, exist_ok=True)
    rows = []
    for k, rect, data in _cells(link):
        if cells is None or k in cells:
            jobs.append((data, rect, os.path.join(folder, f"{k:04d}.png")))
            rows.append((k, rect[2], rect[3]))
    return rows


def _face_names(game_dir):
    """face number -> {name: scenarios}"""
    out = {}
    for s in W.SCENARIOS:
        _, _, data = W.scenario(game_dir, s)
        for name, _, fixed in W.persons_raw(data)[0]:
            if name == "預備預備":
                continue
            for o in (24, 28):
                n, = struct.unpack_from("<H", fixed, o)
                if n != 0xFFFF:
                    out.setdefault(n, {}).setdefault(name, set()).add(s)
    return out


def faces(game_dir, out, jobs):
    res = os.path.join(game_dir, *RES)
    names = _face_names(game_dir)
    by_slot = {}
    for n, who in names.items():
        slot = face_slot(n)
        if slot is not None:
            by_slot.setdefault(slot, []).append((n, who))
    filled = {}
    for entry, folder in FACES:
        for k, w, h in _dump(_read(res, entry), os.path.join(out, "faces", folder), jobs):
            filled.setdefault(k, []).append(folder)
    rows = []
    for k in sorted(filled):
        nums = by_slot.get(k, [])
        if k == 0:  # face 0 is 織田信長, and also the default of the persons that have no face of their own
            nums = [(0, {"織田信長": names[0]["織田信長"]})]
        rows.append([k, " ".join(f for f in filled[k]), " ".join(str(n) for n, _ in nums),
                     "、".join(f"{name}（{' '.join(sorted(sc))}）" for _, who in nums for name, sc in who.items())])
    _csv(os.path.join(out, "faces", "index.csv"), ["slot", "sizes", "face_numbers", "persons"], rows)
    rekidai = []
    for entry in REKIDAI:
        for k, w, h in _dump(_read(res, entry), os.path.join(out, "faces", "rekidai", f"{entry}"), jobs):
            rekidai.append([f"rekidai/{entry}/{k:04d}.png", entry, k, w, h])
    _csv(os.path.join(out, "faces", "rekidai.csv"), ["file", "entry", "cell", "width", "height"], rekidai)
    unresolved = sorted(n for n in names if face_slot(n) is None)
    return len(rows), len(rekidai), unresolved


def kamon(game_dir, out):
    """家紋: cells of the res_grp 9 atlas (its LINK records only the first cell) -> out/kamon/NNNN.png + index.csv;
    the number is the 血族 (person +22), named after the 家 its members lead (wiki_nobu14.house_names)"""
    link = _read(os.path.join(game_dir, *RES), KAMON)
    [(_, _, data)] = list(_cells(link))
    if data[:4] == b"LWC\x1a":
        data = ls11.lwc_decode(data)
    atlas, folder = _texture(data), os.path.join(out, "kamon")
    os.makedirs(folder, exist_ok=True)
    cells = []
    for k in range(KAMON_COLS * (atlas.height // KAMON_CELL)):
        x, y = k % KAMON_COLS * KAMON_CELL, k // KAMON_COLS * KAMON_CELL
        cell = atlas.crop((x, y, x + KAMON_CELL, y + KAMON_CELL))
        if cell.getchannel("A").getbbox():
            cell.save(os.path.join(folder, f"{k:04d}.png"))
            cells.append(k)
    empty = placeholders(folder, cells)
    names, surnames = W.house_names(game_dir), W.house_surnames(game_dir)
    rows = []
    for k in cells:
        if k in empty:
            rows.append([k, f"{k:04d}.png", "", "", "placeholder"])
        elif k in names:
            rows.append([k, f"{k:04d}.png", names[k][0], "、".join(names[k][1:]), "勢力名"])
        elif k in surnames:
            rows.append([k, f"{k:04d}.png", surnames[k] + "家", "", "推定：該血族武將最常見的姓"])
        else:
            rows.append([k, f"{k:04d}.png", "", "", ""])
    _csv(os.path.join(folder, "index.csv"), ["kamon", "file", "name", "other_names", "source"], rows)
    return len(cells), sum(1 for r in rows if r[2]), len(empty)


def event_titles(game_dir):
    """event id -> (name, scenario year or -1) from NOBU14PK.exe"""
    with open(os.path.join(game_dir, "NOBU14PK.exe"), "rb") as f:
        d = f.read()

    def ok(o):
        a, _ = struct.unpack_from("<ii", d, o)
        t = d[o + 8:o + TITLE_REC].split(b"\0")[0]
        return 0 <= a < 5000 and len(t) >= 2 and t[0] >= 0x81 and not any(d[o + 8 + len(t):o + TITLE_REC])

    o = d.index("天下布武".encode("cp950")) - 8
    assert ok(o)
    while ok(o - TITLE_REC):
        o -= TITLE_REC
    out = {}
    while ok(o):
        a, year = struct.unpack_from("<ii", d, o)
        out[a] = (W.text(d[o + 8:o + TITLE_REC]), year)
        o += TITLE_REC
    return out


def events(game_dir, out):
    """res_event.bin scripts -> out/events/events.jsonl + index.csv"""
    import json
    dst = os.path.join(out, "events")
    os.makedirs(dst, exist_ok=True)
    titles = event_titles(game_dir)
    _, _, data = W.scenario(game_dir, W.MAIN)
    names = [n for n, _, _ in W.persons_raw(data)[0]]
    path = os.path.join(game_dir, "RES_PK", "res_event.bin")
    with open(path, "rb") as f:
        d = f.read()
    n, = struct.unpack_from("<I", d, 4)
    rows = []
    with open(os.path.join(dst, "events.jsonl"), "w", encoding="utf-8") as fo:
        for i in range(n):
            o, s = struct.unpack_from("<II", d, 0x10 + 8 * i)
            if s != EVENT_SIZE:
                continue
            e = d[o:o + s]
            eid, = struct.unpack_from("<I", e, 0)
            count, = struct.unpack_from("<i", e, STEPS)
            if count < 0:  # unused slot
                continue
            assert STEP0 + STEP * count <= s, (i, count)
            steps = []
            for k in range(count):
                b = e[STEP0 + STEP * k:STEP0 + STEP * (k + 1)]
                bg, p1, p2, side = struct.unpack_from("<4i", b)
                steps.append({"bg": bg, "person": p1, "person2": p2, "side": side,
                              "speaker": W.text(b[0x10:0x20]), "text": W.text(b[0x20:0xA0]),
                              "cmd": list(struct.unpack_from("<6i", b, 0xA0))})
            title, year = titles.get(eid, ("", -1))
            fo.write(json.dumps({"id": eid, "title": title, "year": year, "steps": steps}, ensure_ascii=False) + "\n")
            people = sorted({x for st in steps for x in (st["person"], st["person2"]) if 0 <= x < len(names)})
            rows.append([eid, title, year if year >= 0 else "", count,
                         " ".join(str(b) for b in sorted({st["bg"] for st in steps if st["bg"] >= 0})),
                         "、".join(names[p] for p in people if names[p])])
    _csv(os.path.join(dst, "index.csv"), ["id", "title", "year", "steps", "backgrounds", "persons"], rows)
    return len(rows), sum(1 for r in rows if r[1])


def items(game_dir, out, jobs):
    """家宝 table and pictures -> out/items/"""
    dst = os.path.join(out, "items")
    pics = _dump(_read(os.path.join(game_dir, *RES), KAHOU), os.path.join(dst, "pictures"), jobs)
    assert len(pics) == 108, len(pics)
    _, _, data = W.scenario(game_dir, W.MAIN)
    raw = W._items_raw(data)
    rows = []
    for r in W.items(game_dir):
        _, _, sub, grade, kind, flags = raw[r["id"]]
        rows.append([r["id"], r["name"], kind, r["kind"], grade, sub, f"pictures/{sub:04d}.png",
                     f"pictures/{sub + 54:04d}.png", flags, r["description"]])
    _csv(os.path.join(dst, "kahou.csv"), ["id", "name", "kind_id", "kind", "grade", "subkind", "picture", "icon",
                                          "flags", "description"], rows)
    return len(rows)


@click.command("nobu14-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True),
              help="Steam depot (games/steam/292990-tchinese/depot)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/nobu14pk-win/extract)")
@click.option("--jobs", default=os.cpu_count(), help="processes for the LWC decoding")
def nobu14_extras(game_dir, out, jobs):
    """信長の野望・創造 PK: faces, event pictures and scripts, 家宝, 戦法 titles."""
    work = []
    n, rk, unresolved = faces(game_dir, out, work)
    click.echo(f"faces: {n} slots, rekidai {rk}; face numbers without a slot: {len(unresolved)}")
    click.echo(f"items: {items(game_dir, out, work)}")
    click.echo("kamon: %d (%d named, %d placeholders)" % kamon(game_dir, out))
    ev, titled = events(game_dir, out)
    click.echo(f"events: {ev} ({titled} with a title)")
    index = []
    res = os.path.join(game_dir, *RES)
    for entry, folder in PICTURE_SETS:
        for k, w, h in _dump(_read(res, entry), os.path.join(out, "eventcg", folder), work):
            index.append([f"{folder}/{k:04d}.png", folder, k, w, h, f"RES_PK/res_grp.bin {entry}"])
    _csv(os.path.join(out, "eventcg", "index.csv"), ["file", "set", "cell", "width", "height", "source"], index)
    click.echo(f"eventcg: {len(index)}")
    with Pool(jobs) as pool:
        for k, _ in enumerate(pool.imap_unordered(_save_cell, work, chunksize=4), 1):
            if k % 1000 == 0:
                click.echo(f"  {k}/{len(work)} pictures")
    click.echo(f"pictures written: {len(work)}")


if __name__ == "__main__":
    nobu14_extras()
