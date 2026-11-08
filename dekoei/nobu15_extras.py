"""信長の野望・大志 with PK (Steam, appid 628890): event pictures, event scripts, quests, 家宝 and 家紋, written under
--out as eventcg/, events/, items/ and kamon/ (notes/nobu15.md「事件、插圖、道具」).

- RES_PK/res_face.bin and res_grp.bin are LINK archives (notes/nobu15.md「封裝」); the picture entries are LINKs of
  cells, each cell an 'LWC\\x1a'-packed (or plain) GT1G0600 texture cropped to the cell rectangle; 8x8 cells are empty.
- RES_PK/res_event.bin (and RES_PK_TC/): 1002 slots, 328 events of 0xC1B4 bytes: +0 u32 id, +4 title (64 bytes),
  +0x268 u32 step count, steps of 0xC0 bytes from +0x274: +0 u32 background (res_face entry 7), +4 u32 person slot,
  +8 u32 second person slot (9999 / -1 none), +0xC u32 1 when the second person speaks, +0x10 speaker name (16),
  +0x20 text (128), +0xA0 u32 command.
- QUEST_PK_JP/QuestInfo.bqi (and _TC): u32 0, u32 438, ..., 216-byte records from 0x10: +0 u32 person slot, +0x14
  text (80), +0x64 second text (80), +0xC4 u32, +0xD0 u32, +0xD4 u32.
- 家宝: names, readings and related persons are fixdata key 9 (121 records: name 15, reading 33, u32 n, n x u16 person
  slots); kind, grade and picture are scenario key 9 (121 x 18 bytes: u16, u16, u8, u32 picture, u32 grade, u32 kind,
  u8 flags); descriptions are MSG_PK_JP/kahou_retsuden01-03 (N15A, name and text pairs, same order).
"""
import csv
import json
import os
import struct
from multiprocessing import Pool

import click
from PIL import Image

import ls11

# (res file, outer entry, folder): the non-face picture entries
PICTURE_SETS = [
    ("res_face.bin", 5, "ichimaie"),       # 1920x1080 一枚絵
    ("res_face.bin", 7, "background"),     # 1920x1080 event backgrounds (step +0)
    ("res_face.bin", 8, "still"),          # 1080x600 event stills (disasters etc.)
    ("res_face.bin", 9, "banner"),         # 510x198
    ("res_face.bin", 12, "paper"),         # 1920x1080 paper backgrounds
    ("res_face.bin", 29, "paper_pk"),
    ("res_face.bin", 18, "title_1188"),    # calligraphy titles
    ("res_face.bin", 19, "title_1296"),
    ("res_face.bin", 20, "title_2880a"),
    ("res_face.bin", 21, "title_2880b"),
    ("res_face.bin", 37, "tutorial_pk"),   # 1080x600 PK tutorial stills
    ("res_grp.bin", 28, "battle_title"),   # 1584x360 battle names
    ("res_grp.bin", 30, "era"),            # 240x132 era names
]
KAHOU_PICTURES = ("res_face.bin", 10)      # 121 x 315x315
KAMON = ("res_grp.bin", 18)                # 255 x 1024x1024 (22: 204, 42: 256; 19/23/43 are byte copies)
KAHOU_TC = (59, 60, 61)  # MSG_PK_TC files holding kahou_retsuden01-03
KINDS = ["茶道具", "武具", "名馬", "書物", "絵画", "香道具", "舶来品", "唐物"]  # NOBU15PK_JP.exe strings, in order
EVENT_SIZE, STEP0, STEP = 0xC1B4, 0x274, 0xC0
PERSONS = 3952
FIXED_PK = 101  # fixed part of a PK person record


def _outer(path):
    with open(path, "rb") as f:
        n, = struct.unpack_from("<I", f.read(8), 4)
        f.seek(0)
        table = f.read(0x10 + 8 * n)
    return [struct.unpack_from("<II", table, 0x10 + 8 * i) for i in range(n)]


def _read(path, entry):
    o, s = _outer(path)[entry]
    with open(path, "rb") as f:
        f.seek(o)
        return f.read(s)


def _cells(link):
    n, = struct.unpack_from("<I", link, 4)
    rects, = struct.unpack_from("<I", link, 0x10)
    for k in range(n):
        rect = struct.unpack_from("<4H", link, rects + 12 * k)
        o, s = struct.unpack_from("<II", link, 0x20 + 8 * k)
        if rect[2:] != (8, 8):
            yield k, rect, link[o:o + s]


def _texture(t):
    assert t[:8] == b"GT1G0600", t[:8]
    o, = struct.unpack_from("<I", t, 0x0C)
    o += struct.unpack_from("<I", t, o)[0]
    fmt, dim = t[o + 1], t[o + 2]
    w, h = 1 << (dim & 15), 1 << (dim >> 4)
    p = o + 8 + (struct.unpack_from("<I", t, o + 8)[0] if t[o + 7] & 0x10 else 0)
    if fmt in (0x5B, 8):  # BC3
        return Image.frombytes("RGBA", (w, h), t[p:p + w * h], "bcn", 3)
    if fmt == 0x59:  # BC1
        return Image.frombytes("RGBA", (w, h), t[p:p + w * h // 2], "bcn", 1)
    assert fmt == 1, hex(fmt)
    return Image.frombytes("RGBA", (w, h), t[p:p + 4 * w * h], "raw", "BGRA")


def _save_cell(job):
    data, rect, dst = job
    if data[:4] == b"LWC\x1a":
        data = ls11.lwc_decode(data)
    x, y, w, h = rect
    _texture(data).crop((x, y, x + w, y + h)).save(dst)
    return dst


def _dump(path, entry, folder, jobs):
    """queue every cell of one picture entry as folder/NNNN.png; returns the index rows"""
    os.makedirs(folder, exist_ok=True)
    rows = []
    for k, rect, data in _cells(_read(path, entry)):
        dst = os.path.join(folder, f"{k:04d}.png")
        jobs.append((data, rect, dst))
        rows.append([k, rect[2], rect[3]])
    return rows


def _csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _scenario(path):
    with open(path, "rb") as f:
        d = f.read()
    return ls11.lwc_decode(d[d.index(b"LWC\x1a"):])


def _key(d, key, count):
    """position of the records after the (u32 key, u32 count) pair"""
    i = d.index(struct.pack("<II", key, count))
    return i + 8


def person_names(game_dir, lang="JP", scenario="02"):
    """slot -> name (姓名) of PK scenario `scenario`"""
    enc = "cp932" if lang == "JP" else "cp950"
    d = _scenario(os.path.join(game_dir, f"SCENARIO_PK_{lang}", f"sceda{scenario}.n15"))
    p = _key(d, 0, PERSONS)
    names = []
    for _ in range(PERSONS):
        name = (d[p:p + 11].split(b"\0")[0] + d[p + 11:p + 22].split(b"\0")[0]).decode(enc, "replace")
        names.append(name)
        p += 90
        for _ in range(4):
            n, = struct.unpack_from("<I", d, p)
            p += 4 + 2 * n
        p += FIXED_PK
    return names


def _n15a(path, enc):
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"N15A"
    t, = struct.unpack_from("<I", d, 4)
    n, = struct.unpack_from("<I", d, t)
    offs = struct.unpack_from(f"<{n + 1}I", d, t + 8)
    b = t + 8 + 4 * (n + 1)
    return [d[b + offs[k]:b + offs[k + 1]].split(b"\0")[0].decode(enc, "replace") for k in range(n)]


def items(game_dir, out, jobs, names):
    """家宝 table and pictures -> out/items/"""
    dst = os.path.join(out, "items")
    pics = _dump(os.path.join(game_dir, "RES_PK", KAHOU_PICTURES[0]), KAHOU_PICTURES[1],
                 os.path.join(dst, "pictures"), jobs)
    fx = _scenario(os.path.join(game_dir, "SCENARIO_PK_JP", "fixdata.n15"))
    sc = _scenario(os.path.join(game_dir, "SCENARIO_PK_JP", "sceda02.n15"))
    texts = []
    for k in (1, 2, 3):
        texts += _n15a(os.path.join(game_dir, "MSG_PK_JP", f"kahou_retsuden{k:02d}_0.bin"), "cp932")[2:]
    tc = []
    for k in KAHOU_TC:  # MsgTag.bin: messages 5208-5507
        tc += _n15a(os.path.join(game_dir, "MSG_PK_TC", f"{k:04d}.bin"), "cp950")[2:]
    p, s = _key(fx, 9, 121), _key(sc, 9, 121)
    rows = []
    for i in range(121):
        name = fx[p:p + 15].split(b"\0")[0].decode("cp932")
        reading = fx[p + 15:p + 48].split(b"\0")[0].decode("cp932")
        n, = struct.unpack_from("<I", fx, p + 48)
        related = struct.unpack_from(f"<{n}H", fx, p + 52)
        p += 52 + 2 * n
        a, b, c, picture, grade, kind, flags = struct.unpack_from("<HHBIIIB", sc, s + 18 * i)
        assert texts[2 * i] == name, (i, name, texts[2 * i])
        rows.append([i, name, reading, kind, KINDS[kind], grade, f"pictures/{picture:04d}.png", flags,
                     " ".join(map(str, related)), "、".join(names[r] for r in related),
                     texts[2 * i + 1].replace("\\n", ""), tc[2 * i], tc[2 * i + 1].replace("\\n", "")])
    assert len(pics) == 121
    _csv(os.path.join(dst, "kahou.csv"),
         ["id", "name", "reading", "kind_id", "kind", "grade", "picture", "flags", "related_slots", "related",
          "description", "name_zh", "description_zh"], rows)
    return len(rows)


def _events(path, enc):
    with open(path, "rb") as f:
        d = f.read()
    n, = struct.unpack_from("<I", d, 4)
    for i in range(n):
        o, s = struct.unpack_from("<II", d, 0x10 + 8 * i)
        if s != EVENT_SIZE:
            continue
        e = d[o:o + s]
        steps = []
        for k in range(struct.unpack_from("<I", e, 0x268)[0]):
            b = e[STEP0 + STEP * k:STEP0 + STEP * (k + 1)]
            bg, p1, p2, side = struct.unpack_from("<4i", b)
            steps.append({"bg": bg, "person": p1, "person2": p2, "side": side,
                          "speaker": b[0x10:0x20].split(b"\0")[0].decode(enc, "replace"),
                          "text": b[0x20:0xA0].split(b"\0")[0].decode(enc, "replace"),
                          "cmd": struct.unpack_from("<i", b, 0xA0)[0]})
        yield i, e[4:0x44].split(b"\0")[0].decode(enc, "replace"), steps


def events(game_dir, out, names):
    """res_event.bin scripts (ja + zh) -> out/events/events.jsonl + index.csv; quests -> quests.csv"""
    dst = os.path.join(out, "events")
    os.makedirs(dst, exist_ok=True)
    tc = {i: (t, st) for i, t, st in _events(os.path.join(game_dir, "RES_PK_TC", "res_event.bin"), "cp950")}
    rows = []
    with open(os.path.join(dst, "events.jsonl"), "w", encoding="utf-8") as f:
        for i, title, steps in _events(os.path.join(game_dir, "RES_PK", "res_event.bin"), "cp932"):
            zt, zs = tc.get(i, ("", []))
            for k, st in enumerate(steps):
                st["speakerSlot"] = st["person2"] if st["side"] == 1 else st["person"]
                if k < len(zs):
                    st["textZh"] = zs[k]["text"]
                    st["speakerZh"] = zs[k]["speaker"]
            f.write(json.dumps({"id": i, "title": title, "titleZh": zt, "steps": steps}, ensure_ascii=False) + "\n")
            people = sorted({s["speakerSlot"] for s in steps if 0 <= s["speakerSlot"] < PERSONS})
            rows.append([i, title, zt, len(steps), " ".join(sorted({str(s["bg"]) for s in steps if s["bg"] >= 0},
                                                                     key=int)),
                         "、".join(names[p] for p in people)])
    _csv(os.path.join(dst, "index.csv"), ["id", "title", "title_zh", "steps", "backgrounds", "speakers"], rows)
    quests = []
    for lang, enc in (("JP", "cp932"), ("TC", "cp950")):
        with open(os.path.join(game_dir, f"QUEST_PK_{lang}", "QuestInfo.bqi"), "rb") as fq:
            d = fq.read()
        n, = struct.unpack_from("<I", d, 4)
        for k in range(n):
            p = 0x10 + 216 * k
            if p + 216 > len(d):
                break
            r = d[p:p + 216]
            a = r[0x14:0x64].split(b"\0")[0].decode(enc, "replace")
            b = r[0x64:0xB4].split(b"\0")[0].decode(enc, "replace")
            if lang == "JP":
                person, = struct.unpack_from("<i", r, 0)
                quests.append([k, person, names[person] if 0 <= person < PERSONS else "", a, b, "", "",
                               *struct.unpack_from("<3i", r, 0xC4), *struct.unpack_from("<2i", r, 0xD0)])
            elif k < len(quests):
                quests[k][5:7] = [a, b]
    _csv(os.path.join(dst, "quests.csv"),
         ["record", "person_slot", "person", "text", "text2", "text_zh", "text2_zh", "u_c4", "u_c8", "u_cc", "u_d0",
          "u_d4"], quests)
    return len(rows), len(quests)


@click.command("nobu15-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam files (games/nobu15pk-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/nobu15pk-win/extract)")
@click.option("--jobs", default=os.cpu_count(), help="processes for the LWC decoding")
def nobu15_extras(game_dir, out, jobs):
    """信長の野望・大志 PK: event pictures, event scripts and quests, 家宝, 家紋."""
    names = person_names(game_dir)
    work, index = [], []
    click.echo(f"items: {items(game_dir, out, work, names)}")
    ev, qu = events(game_dir, out, names)
    click.echo(f"events: {ev}, quest records: {qu}")
    for res, entry, folder in PICTURE_SETS:
        for k, w, h in _dump(os.path.join(game_dir, "RES_PK", res), entry, os.path.join(out, "eventcg", folder),
                             work):
            index.append([f"{folder}/{k:04d}.png", folder, k, w, h, f"RES_PK/{res} {entry}"])
    _csv(os.path.join(out, "eventcg", "index.csv"), ["file", "set", "cell", "width", "height", "source"], index)
    click.echo(f"eventcg: {len(index)}")
    kamon = _dump(os.path.join(game_dir, "RES_PK", KAMON[0]), KAMON[1], os.path.join(out, "kamon"), work)
    click.echo(f"kamon: {len(kamon)}")
    with Pool(jobs) as pool:
        for n, _ in enumerate(pool.imap_unordered(_save_cell, work, chunksize=4), 1):
            if n % 200 == 0:
                click.echo(f"  {n}/{len(work)} pictures")
    click.echo(f"pictures written: {len(work)}")


if __name__ == "__main__":
    nobu15_extras()
