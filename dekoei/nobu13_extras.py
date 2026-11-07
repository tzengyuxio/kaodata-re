"""信長の野望・天道 with PK (Steam, appid 363110): event pictures, 家宝 and event scripts, written under --out as
eventcg/, items/, kamon/ and events/ (notes/nobu13.md「事件、插圖、道具」).

- grp/*.n13 picture files are 'LINK' archives holding one 'GT1G0600' texture set: +0xC u32 sprite count, +0x10 u32
  sprite table (12 bytes each: u16 x, y, w, h, u32 texture), entries (u32 offset, u32 size) from 0x20. The texture
  set has +0xC a u32 table of header offsets (relative to the table) and +0x10 the texture count; each 8-byte header
  has +1 the format (8 BC3, 1 B8G8R8A8), +2 log2 height << 4 | log2 width, +7 bit 4: an extra header follows whose
  size is the next u32.
- Script CG numbers (msg/*.n13 calls of Fnc044, last argument) count hanyoucg 0-52, rekishicg 53-160, endingcg
  161-170, tutorialstl 171-197.
- 家宝: section (0x0E, 453) of the LWC-decoded scenario (218-byte records: name 15, reading from +15, +201 i16 ?,
  +203 i16 owner slot in that scenario, +205 u32 picture, +209 u32 grade, +213 u32 kind, +217 u8 flags); kind names
  are the NOBU13PK.exe pointer table at file 0xC47AD0. The 353 named records follow msg/Kfile01-08.n13 in order
  (a few description headers write the name differently: description_name).
- msg/*.n13 (N13F) scripts: tokens split by ',\\n'; '&,MSGnnn' a string, '&,<var>.FncNNN' a value shown in the text,
  '),<n>' and ',,<var>' arguments of the next '(,FncNNN' call, '(,Fnc000' ends a text box.
"""
import csv
import glob
import json
import os
import struct

import click
from PIL import Image

import wiki_nobu13
from wiki_nobu12 import msg_entries

SCENARIO = "11"  # the scenario the 家宝 owners are read from (the kaodata names come from it too)
ITEMS = (0x0E, 453)
ITEM_SIZE = 218
KIND_TABLE, KINDS = 0xC47AD0, 36  # NOBU13PK.exe file offset of the kind-name pointers
CG_SETS = [("hanyou", "hanyoucg.n13", 0), ("rekishi", "rekishicg.n13", 53), ("ending", "endingcg.n13", 161),
           ("tutorial", "tutorialstl.n13", 171)]
CG_CALL = "044"  # Fnc044(cg) / Fnc044(person, cg) shows a picture
PICTURES = 73  # kahou.n13: 73 pictures at 96 x 96, then the same 73 at 60 x 60
KINDS_OF_FILE = [("rks_", "歴史イベント"), ("cev_", "勢力イベント"), ("han_", "汎用イベント"), ("tut_", "チュートリアル"),
                 ("end", "エンディング")]
SKIP_MSG = ("Bfile", "Kfile")  # 列伝 (biography export) and 家宝 descriptions (items/)


def link_images(path):
    """The sprites of a grp LINK file as RGBA images, in sprite order."""
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"LINK"
    count, table = struct.unpack_from("<2I", d, 0xC)
    base, = struct.unpack_from("<I", d, 0x20)
    assert d[base:base + 8] == b"GT1G0600"
    heads, n = struct.unpack_from("<2I", d, base + 0xC)
    textures = {}

    def texture(i):
        if i not in textures:
            o = base + heads + struct.unpack_from("<I", d, base + heads + 4 * i)[0]
            fmt, dim = d[o + 1], d[o + 2]
            w, h = 1 << (dim & 15), 1 << (dim >> 4)
            s = o + 8 + (struct.unpack_from("<I", d, o + 8)[0] if d[o + 7] & 0x10 else 0)
            if fmt == 8:
                textures[i] = Image.frombytes("RGBA", (w, h), d[s:s + w * h], "bcn", 3)
            else:
                assert fmt == 1, fmt
                textures[i] = Image.frombytes("RGBA", (w, h), d[s:s + 4 * w * h], "raw", "BGRA")
        return textures[i]

    for k in range(count):
        x, y, w, h, i = struct.unpack_from("<4HI", d, table + 12 * k)
        assert i < n
        yield texture(i).crop((x, y, x + w, y + h))


def _strings(d, st):
    cnt, first = struct.unpack_from("<2I", d, st)
    offs = struct.unpack_from(f"<{cnt + 1}I", d, st + 8)
    base = st + 8 + 4 * (cnt + 1)
    return first, [d[base + offs[k]:base + offs[k + 1]].decode("cp932") for k in range(cnt)]


def script(path):
    """(text boxes, calls) of one N13F file: a box is its text with '{var}' for shown values; a call is
    (function, [arguments]) in order, with 'box' entries marking where each text box falls."""
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"N13F"
    st, n = struct.unpack_from("<2I", d, 4)
    first, strings = _strings(d, st)
    boxes, steps, cur, args = [], [], [], []
    for t in d[0x14 + 4 * n:st].split(b",\n"):
        t = t.decode("cp932")
        if t.startswith("&,MSG"):
            cur.append(strings[int(t[5:]) - first])
        elif t.startswith("&,"):
            cur.append("{" + t[2:].split(".")[0] + "}")
        elif t.startswith("),"):
            args.append(t[2:])
        elif t.startswith(",,"):
            args.append(t[2:])
        elif t.startswith("(,Fnc"):
            fn = t[5:]
            if fn == "000" and not args:
                if cur:
                    boxes.append("".join(cur).replace("\\n", "\n"))
                    steps.append(["box", len(boxes) - 1])
                cur = []
            else:
                steps.append([fn, args])
            args = []
    if cur:
        boxes.append("".join(cur).replace("\\n", "\n"))
        steps.append(["box", len(boxes) - 1])
    return boxes, steps, strings


def _kind_names(exe):
    with open(exe, "rb") as f:
        d = f.read()
    pe, = struct.unpack_from("<I", d, 0x3C)
    image_base, = struct.unpack_from("<I", d, pe + 0x34)
    sections, opt = struct.unpack_from("<H", d, pe + 6)[0], struct.unpack_from("<H", d, pe + 0x14)[0]
    secs = [struct.unpack_from("<8sIIII", d, pe + 0x18 + opt + 40 * i) for i in range(sections)]

    def text(va):
        for _, _, rva, raw_size, raw in secs:
            if image_base + rva <= va < image_base + rva + raw_size:
                o = va - image_base - rva + raw
                return d[o:d.index(b"\0", o)].decode("cp932")
        raise ValueError(hex(va))

    return [text(v) for v in struct.unpack_from(f"<{KINDS}I", d, KIND_TABLE)]


def _csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def items(game_dir, out):
    """家宝 table, 96 and 60 px pictures and descriptions -> out/items/"""
    os.makedirs(os.path.join(out, "items", "pictures"), exist_ok=True)
    pics = list(link_images(os.path.join(game_dir, "grp", "kahou.n13")))
    assert len(pics) == 2 * PICTURES
    for k in range(PICTURES):
        pics[k].save(os.path.join(out, "items", "pictures", f"{k:02d}.png"))
        pics[PICTURES + k].save(os.path.join(out, "items", "pictures", f"{k:02d}-small.png"))
    kinds = _kind_names(os.path.join(game_dir, "NOBU13PK.exe"))
    data = wiki_nobu13._data(os.path.join(game_dir, "scenario"), SCENARIO)
    base = wiki_nobu13._section(data, ITEMS)
    names = wiki_nobu13._names(os.path.join(game_dir, "scenario"))
    texts = msg_entries([os.path.join(game_dir, "msg", f"Kfile{k:02d}.n13") for k in range(1, 9)])
    rows, t = [], iter(texts)
    for i in range(ITEMS[1]):
        r = data[base + ITEM_SIZE * i:base + ITEM_SIZE * (i + 1)]
        name = r[:15].split(b"\0")[0].decode("cp932")
        if not name:
            continue
        reading = r[15:].split(b"\0")[0].decode("cp932")
        a, owner, picture, grade, kind = struct.unpack_from("<hhIII", r, 201)
        tname, text = next(t)
        rows.append([i, name, reading, kind, kinds[kind], grade, f"pictures/{picture:02d}.png", owner,
                     names[owner][0] if owner >= 0 else "", a, r[217], "" if tname == name else tname, text])
    assert next(t, None) is None
    _csv(os.path.join(out, "items", "kahou.csv"),
         ["id", "name", "reading", "kind_id", "kind", "grade", "picture", "owner_slot_s11", "owner_s11", "u201",
          "flags", "description_name", "description"], rows)
    return len(rows)


def eventcg(game_dir, out):
    """the script-numbered event pictures and the title pictures -> out/eventcg/, with index.csv"""
    used, people = {}, {}
    for path in sorted(glob.glob(os.path.join(game_dir, "msg", "*.n13"))):
        if os.path.basename(path).startswith(SKIP_MSG) or not open(path, "rb").read(4) == b"N13F":
            continue
        for fn, args in script(path)[1]:
            if fn == CG_CALL:
                cg = int(args[-1])
                used.setdefault(cg, set()).add(os.path.basename(path)[:-4])
                if len(args) == 2:
                    people.setdefault(cg, set()).add(int(args[0]))
    names = wiki_nobu13._names(os.path.join(game_dir, "scenario"))
    rows = []
    for kind, name, first in CG_SETS + [("title", "titlecg.n13", None)]:
        os.makedirs(os.path.join(out, "eventcg", kind), exist_ok=True)
        for k, im in enumerate(link_images(os.path.join(game_dir, "grp", name))):
            file = f"{kind}/{k:03d}.png"
            im.save(os.path.join(out, "eventcg", file))
            cg = "" if first is None else first + k
            who = "、".join(names[p][0] for p in sorted(people.get(cg, ())))
            # the rekishicg offset is checked by the ten 1-person portraits (145-155) whose Fnc044 person matches
            evidence = "" if first is None else "✅ cross" if kind == "rekishi" else "🟡"
            rows.append([cg, kind, k, im.width, im.height, file, f"grp/{name}", " ".join(sorted(used.get(cg, ()))),
                         who, evidence])
    _csv(os.path.join(out, "eventcg", "index.csv"),
         ["cg", "set", "index", "width", "height", "file", "source", "used_by", "person_arg", "cg_evidence"], rows)
    return len(rows)


def kamon(game_dir, out):
    os.makedirs(os.path.join(out, "kamon"), exist_ok=True)
    ims = list(link_images(os.path.join(game_dir, "grp", "kamon.n13")))
    half = len(ims) // 2
    for k, im in enumerate(ims):
        im.save(os.path.join(out, "kamon", f"{k % half:03d}{'-small' if im.width < 16 else ''}.png"))
    return half


def _kind(name):
    return next((k for p, k in KINDS_OF_FILE if name.startswith(p)), "その他")


def events(game_dir, out):
    """one JSONL record per N13F script (all msg/*.n13 but 列伝 and 家宝) -> out/events/events.jsonl"""
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    n = 0
    with open(os.path.join(out, "events", "events.jsonl"), "w", encoding="utf-8") as f:
        for path in sorted(glob.glob(os.path.join(game_dir, "msg", "*.n13"))):
            name = os.path.basename(path)[:-4]
            if name.startswith(SKIP_MSG) or open(path, "rb").read(4) != b"N13F":
                continue
            boxes, steps, strings = script(path)
            cgs = [int(a[-1]) for fn, a in steps if fn == CG_CALL]
            f.write(json.dumps({"file": f"msg/{name}.n13", "kind": _kind(name), "cg": cgs, "boxes": boxes,
                                "steps": steps, "strings": strings}, ensure_ascii=False) + "\n")
            n += 1
    return n


@click.command("nobu13-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam install (games/steam/363110)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/nobu13pk-win/extract)")
def nobu13_extras(game_dir, out):
    """信長の野望・天道 PK: event pictures, 家宝, 家紋 and event scripts."""
    click.echo(f"items: {items(game_dir, out)}")
    click.echo(f"eventcg: {eventcg(game_dir, out)}")
    click.echo(f"kamon: {kamon(game_dir, out)}")
    click.echo(f"events: {events(game_dir, out)}")
