"""三國志14 PK (Steam): event pictures, items (寶物) and event texts, plus an inventory of the RDB containers, written
to <out>/{eventcg,items,events}/ and <out>/inventory.csv. Formats are in notes/san14.md「事件、插圖、道具」.

- Pictures: 0002/ScreenLayout.rdb sprites (sango.san14_entries / san14_read). A sprite definition (u32 count, 104-byte
  sprites: 64-byte name, u32 texture index into its GT1G0600, four corners' (u, v), u32) follows the texture it cuts;
  the same name can be defined twice (an 8 x 8 placeholder and the real one), the largest cut is kept.
- Items: 0010_<lang>/fixdataex.s14 (LWC) holds u32 201 then 201 records: name 7 UTF-16 chars, (JP only) reading 20
  chars, then u8 kind, u8 stat, u8 amount, u8 effect, u8 effect amount, u8 value, u8 0, u8 picture (sti_itemNNN).
  Records 132-200 are placeholders (アイテム). Kind names are string 2051 + kind, effect names 2077 + effect and
  descriptions 1886 + item of table 0 of 0001_<lang>/msgdata.bin.
- Events: table 3 of msgdata.bin; event e is strings 4e + 1 (title), 4e + 2 (summary), 4e + 3 (result).
- World map (worldmap/): the 3D map has no painted 2D picture; what is 2D is the ground's base colour (FieldEditor4.rdb),
  the editor's 8192 x 8192 hex terrain preview (RRPreview.rdb) and the painted backdrop around the map (map_cover).
"""
import csv
import json
import os
import re
import struct

import click
from PIL import Image

import ls11
import sango

LAYOUT = "0002/ScreenLayout.rdb"
ITEMS = "0010_{}/fixdataex.s14"
MSGDATA = "0001_{}/msgdata.bin"
ITEM_COUNT, ITEM_USED = 201, 132
KINDS, EFFECTS, DESCRIPTIONS = 2051, 2077, 1886
STATS = ["", "統率", "武力", "知力", "政治", "魅力"]  # 🟡 order inferred from the kinds (兵書 1, 刀劍 2, 經書 3, 政書 4)
LANGS = {"JP": "ja", "TC": "zh-Hant"}
# Japanese gaiji (U+E000-) of the event texts: from the person names (JP name vs TC name of the same person) and,
# for the place names, from the context (下邳, 鄴, 兗州, 涪水関)
GAIJI_JP = dict(zip(
    ""
    ""
    ""
    "",
    "瓚郃蒯煨傕邕詡龐繇邈騭闞玠邢歆闓譙琬郝褚珩彤嵇磾莒綝笮祜蕤毌瓘靚琰頎龔眭嘏豨璆媯宓珝禕琨蹋淩璜璿騄夔喈廞淯惲瑗豔邳鄴兗涪"))
# Traditional Chinese: one string writes 公孫瓚 with the Japanese code
GAIJI_TC = {"公孫": "公孫瓚"}
# picture groups: (folder, sprite name pattern, kind)
PICTURES = [
    ("eventcg/still", r"stl_event_\d+(_ch)?", "事件插圖（864×648）"),
    ("eventcg/poem", r"stl_event_p_\d+", "事件插圖（1920×1080，畫上有題字）"),
    ("eventcg/background", r"stl_event_bg_\d+", "事件背景（1920×1080）"),
    ("eventcg/scene", r"stl_event_d_\d+", "事件插圖（1920×1080）"),
    ("eventcg/prop", r"stl_event_komono_\d+", "事件小圖（600×336）"),
    ("eventcg/advantage", r"sti_advantage\d+", "插圖（512×512，用途未確認）"),
    ("eventcg/scenery", r"sti_scenery_\d+", "名勝插圖（480×320）"),
    ("eventcg/cutin", r"texture_chara_unique_\d+", "人物插圖（1024×1024，人物未對應）"),
    ("eventcg/expressions", r"\d{4}b?_\d\d", "事件表情（636×900，頭像號_表情號）"),
    ("items/pictures", r"sti_item\d{3}(_ch)?", "寶物圖（512×512；_ch 是中文字的版本）"),
]


def _strip(s: str) -> str:
    return re.sub(r"\^\d\d", "", s)


def _csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def sprites(game_dir) -> dict[str, tuple]:
    """sprite name -> (texture entry, texture index, (u0, v0, u1, v1)); the largest cut of a name defined twice."""
    rdb = os.path.join(game_dir, LAYOUT)
    es = sango.san14_entries(rdb)
    texs = sorted((e[2][0], e[2][1], e) for e in es if e[0] == sango.SAN14_TEXTURE)
    out = {}
    for typ, fsize, loc in es:
        if typ != sango.SAN14_SPRITES:
            continue
        t = sango.san14_read(rdb, fsize, loc)
        before = [x for x in texs if x[0] == loc[0] and x[1] < loc[1]]
        if not before:
            continue
        tex = max(before)[2]
        for i in range(struct.unpack_from("<I", t)[0]):
            name = t[4 + 104 * i:68 + 104 * i].split(b"\0")[0].decode("latin-1")
            ti = struct.unpack_from("<I", t, 4 + 104 * i + 64)[0]
            c = struct.unpack_from("<8f", t, 4 + 104 * i + 68)
            ref = ((tex[1], tex[2]), ti, (c[0], c[1], c[6], c[7]))
            if name not in out or _area(out[name]) < _area(ref):
                out[name] = ref
    return out


def _area(ref):
    # texture size is unknown until read; compare the UV area of 1 x 1 textures by the stored size instead
    (fsize, _), _, (u0, v0, u1, v1) = ref
    return fsize * (u1 - u0) * (v1 - v0)


class Textures:
    """Reads GT1G0600 textures (BC3) of ScreenLayout.rdb, caching the last one (atlases hold many sprites)."""

    def __init__(self, game_dir):
        self.rdb = os.path.join(game_dir, LAYOUT)
        self.key, self.data = None, None

    def cut(self, ref) -> Image.Image:
        (fsize, loc), ti, (u0, v0, u1, v1) = ref
        if self.key != loc:
            self.key, self.data = loc, sango.san14_read(self.rdb, fsize, loc)
        t = self.data
        header = struct.unpack_from("<I", t, 0x0C)[0]
        o = header + struct.unpack_from("<I", t, header + 4 * ti)[0]
        fmt, dim = t[o + 1], t[o + 2]
        w, h = 1 << (dim & 15), 1 << (dim >> 4)
        start = o + 8 + (struct.unpack_from("<I", t, o + 8)[0] if t[o + 7] & 0x10 else 0)
        assert fmt == 0x5B, fmt
        im = Image.frombytes("RGBA", (w, h), t[start:start + w * h], "bcn", 3)
        return im.crop((round(u0 * w), round(v0 * h), round(u1 * w), round(v1 * h)))


def strings(game_dir, lang, table) -> list[str]:
    with open(os.path.join(game_dir, MSGDATA.format(lang)), "rb") as f:
        x = sango.san13_items(sango.san13_items(sango.san13_unzip(f.read()))[0])[table]
    rows, size = struct.unpack_from("<2H", x, 8)
    out = []
    for r in range(rows):
        o = 0x18 + struct.unpack_from("<I", x, 0x18 + r * size)[0]
        e = o
        while x[e:e + 2] != b"\0\0":
            e += 2
        out.append(x[o:e].decode("utf-16-le"))
    return out


def items(game_dir) -> list[dict]:
    out = []
    recs = {}
    for lang, size in (("JP", 60), ("TC", 22)):
        with open(os.path.join(game_dir, ITEMS.format(lang)), "rb") as f:
            d = f.read()
        d = ls11.lwc_decode(d[d.index(b"LWC\x1a"):])
        # the table is u32 201 followed by the record of item 0 (無効／無效) and item 1 (赤兎馬); the 戦法 table
        # before it also starts with 201 and 無効
        head = struct.pack("<I", ITEM_COUNT) + ("無効" if lang == "JP" else "無效").encode("utf-16-le")
        s = next(m.start() for m in re.finditer(re.escape(head), d)
                 if d[m.start() + 4 + size:][:2] == "赤".encode("utf-16-le"))
        recs[lang] = [d[s + 4 + k * size:s + 4 + (k + 1) * size] for k in range(ITEM_COUNT)]
    text = {lang: strings(game_dir, lang, 0) for lang in LANGS}
    for k in range(1, ITEM_USED):
        jp, tc = recs["JP"][k], recs["TC"][k]
        assert jp[-8:] == tc[-8:], k
        kind, stat, amount, effect, eamount, value, _, pic = jp[-8:]
        name = {lang: r[:14].decode("utf-16-le").split("\0")[0] for lang, r in (("JP", jp), ("TC", tc))}
        out.append({
            "id": k, "name": name["JP"], "reading": jp[14:54].decode("utf-16-le").split("\0")[0],
            "nameZh": name["TC"], "kind": text["JP"][KINDS + kind], "kindZh": text["TC"][KINDS + kind],
            "stat": STATS[stat], "amount": amount, "effect": text["JP"][EFFECTS + effect] if effect else "",
            "effectAmount": eamount, "value": value, "picture": f"sti_item{pic:03d}",
            "description": text["JP"][DESCRIPTIONS + k], "descriptionZh": text["TC"][DESCRIPTIONS + k]})
    return out


def events(game_dir) -> list[dict]:
    text = {}
    for lang, gaiji in (("JP", GAIJI_JP), ("TC", GAIJI_TC)):
        t = strings(game_dir, lang, 3)
        for a, b in gaiji.items():
            t = [s.replace(a, b) for s in t]
        text[lang] = t
    out = []
    for e in range(1, len(text["JP"]) // 4):
        for lang in LANGS:
            title, summary, result = (text[lang][4 * e + i] for i in (1, 2, 3))
            if title or summary or result:
                out.append({"id": e, "lang": LANGS[lang], "title": _strip(title), "summary": _strip(summary),
                            "result": _strip(result), "raw": [title, summary, result]})
    return out


def inventory(game_dir) -> list[tuple]:
    """(rdb, type KTID, magic, entries, MB) for every RDB of 0002/."""
    rows = []
    base = os.path.join(game_dir, "0002")
    for name in sorted(os.listdir(base)):
        if not name.endswith(".rdb"):
            continue
        rdb = os.path.join(base, name)
        groups = {}
        for typ, fsize, loc in sango.san14_entries(rdb):
            g = groups.setdefault(typ, [0, 0, loc])
            g[0] += 1
            g[1] += fsize
        for typ, (n, size, loc) in groups.items():
            rows.append((name, f"{typ:08X}", _magic(rdb, loc), n, round(size / 1e6, 1)))
    return rows


def _magic(rdb, loc) -> str:
    import zlib
    b, off, size = loc
    with open(rdb + ".bin" + ("" if b < 0 else str(b)), "rb") as f:
        f.seek(off)
        raw = f.read(min(size, 1 << 16))
    total, comp = struct.unpack_from("<QQ", raw, 8)
    q = total - comp
    k = struct.unpack_from("<I", raw, q)[0]
    head = zlib.decompressobj().decompress(raw[q + 4:q + 4 + k], 8)
    return head[:8].decode("latin-1").replace("\0", ".")


# world map textures: (rdb, (bin, offset, stored size) of the entry, texture index, file name); the locations are those
# of the Steam PK build in notes/steam.md (depot 1427650)
WORLDMAP = [("0002/FieldEditor4.rdb", (14, 57802752, 30968596), 2, "ground_color.png"),  # BC3 4096, GT1G4600
            ("0002/RRPreview.rdb", (-1, 8323072, 64039516), 0, "hex_terrain.png")]  # RGBA8 8192, GT1G0500


def worldmap(game_dir, out, sp=None) -> list[tuple]:
    """The 2D world map textures to out/worldmap/ and worldmap/index.csv."""
    os.makedirs(os.path.join(out, "worldmap"), exist_ok=True)
    index = []
    for rdb, loc, k, file in WORLDMAP:
        path = os.path.join(game_dir, rdb)
        fsize = next(e[1] for e in sango.san14_entries(path) if e[2] == loc)
        t = sango.san14_read(path, fsize, loc)
        header = struct.unpack_from("<I", t, 0x0C)[0]
        o = header + struct.unpack_from("<I", t, header + 4 * k)[0]
        fmt, dim = t[o + 1], t[o + 2]
        w, h = 1 << (dim & 15), 1 << (dim >> 4)
        start = o + 8 + (struct.unpack_from("<I", t, o + 8)[0] if t[o + 7] & 0x10 else 0)
        if fmt == 1:
            im = Image.frombytes("RGBA", (w, h), t[start:start + w * h * 4])
        else:
            assert fmt == 0x5B, fmt
            im = Image.frombytes("RGBA", (w, h), t[start:start + w * h], "bcn", 3)
        im.convert("RGB").save(os.path.join(out, "worldmap", file))
        index.append((file, f"{w}x{h}", f"{os.path.basename(rdb)} {loc} texture {k}"))
    sp = sp or sprites(game_dir)
    im = Textures(game_dir).cut(sp["map_cover"])
    im.save(os.path.join(out, "worldmap", "map_cover.png"))
    index.append(("map_cover.png", f"{im.width}x{im.height}", "ScreenLayout.rdb sprite map_cover"))
    _csv(os.path.join(out, "worldmap", "index.csv"), ["file", "size", "source"], index)
    return index


@click.command(help="三國志14 PK: event pictures, items (寶物), event texts and an RDB inventory.")
@click.option("--game-dir", required=True, help="the Steam files (games/san14pk-win)")
@click.option("--out", required=True, help="output folder (games/san14pk-win/extract)")
@click.option("--no-pictures", is_flag=True, help="skip the PNGs (tables only)")
def san14_extras(game_dir, out, no_pictures):
    rows = items(game_dir)
    used = {r["picture"] for r in rows}
    os.makedirs(os.path.join(out, "items"), exist_ok=True)
    with open(os.path.join(out, "items", "items.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    _csv(os.path.join(out, "items", "items.csv"), list(rows[0]) + ["evidence"],
         [list(r.values()) + ["✅ cross: 名稱、種類、說明、圖；stat 順序與 value 🟡"] for r in rows])
    ev = events(game_dir)
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    with open(os.path.join(out, "events", "events.jsonl"), "w", encoding="utf-8") as f:
        for r in ev:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    _csv(os.path.join(out, "inventory.csv"), ["rdb", "type", "magic", "entries", "MB"], inventory(game_dir))
    click.echo(f"{len(rows)} items, {len(ev)} event texts ({len({r['id'] for r in ev})} events)")
    if no_pictures:
        return
    sp = sprites(game_dir)
    tex = Textures(game_dir)
    index = []
    # group by texture so each container entry is read once
    todo = []
    for folder, pattern, kind in PICTURES:
        rx = re.compile(pattern)
        for name in sorted(n for n in sp if rx.fullmatch(n)):
            todo.append((sp[name][0][1], name, folder, kind))
    for loc, name, folder, kind in sorted(todo):
        ref = sp[name]
        im = tex.cut(ref)
        if im.width <= 8:
            continue  # an unused 8 x 8 placeholder
        sub = name.split("_")[0] if folder.endswith("expressions") else ""
        path = os.path.join(out, folder, sub, (name.split("_")[1] if sub else name) + ".png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        im.save(path)
        note = "用於寶物" if name in used else ""
        index.append((os.path.relpath(path, out), name, kind, f"{im.width}x{im.height}",
                      f"ScreenLayout.rdb {loc}", note))
    index.sort()
    _csv(os.path.join(out, "eventcg", "index.csv"), ["file", "sprite", "kind", "size", "source", "note"],
         [r for r in index if r[0].startswith("eventcg")])
    _csv(os.path.join(out, "items", "pictures", "index.csv"), ["file", "sprite", "kind", "size", "source", "note"],
         [r for r in index if r[0].startswith("items")])
    click.echo(f"{len(index)} pictures")
    click.echo(f"{len(worldmap(game_dir, out, sp))} world maps")
