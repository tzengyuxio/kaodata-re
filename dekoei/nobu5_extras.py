"""信長の野望・覇王伝 with PK (Steam, appid 628090; PC-98 for cross-checks): 家宝, event pictures, 家紋, world maps and
event text, written under --out as items/, eventcg/, kamon/, map/ and events/ (notes/nobu5.md「事件、插圖、道具」).

- Nobunaga5WPK.exe: .rdata file offset = VA - 0x401600 (SteamStub encrypts only .text). 家宝 names: u32 pointer table
  at 0xB9C30 (120 entries). Category names: pointers at 0xD669C (6: 茶器 武器 舶来 絵画 書籍 財宝), followed at 0xD66B4
  by 26 bytes mapping a picture kind to its category.
- SVnn.N5S (scenarios): 家宝 table at 0x6EE4, 120 x 4 bytes: u16 holder (0xFFFF in all five scenarios), u8 value,
  u8 kind (low 5 bits = picture 0-25, bit 6 and bit 7 = flags).
- Pictures are BMP resources (type 2): EXE 201-226 the 26 item pictures (64x45), EXE 153 a 640x480 painting,
  gaiko.dll 101-104 the 外交 scenes (320x240), Kamon.dll 200-305 家紋, Map.dll 101-104 the world map (1920x376) and
  120 the 割拠図 map.
- PC-98: ITEM.NB5 = the same 26 pictures, 64x45 3bpp byte-interleaved (utils.to_3bpp_indexes order), shown with the
  face colours 8-15 (palette inferred); KAN.NB5 0xB7A = the 120 item names, 11 bytes each, same order.
- Event text: every Japanese string in the EXE .rdata, with the .data pointer tables (runs of string pointers) that
  reference it; the events themselves are coded in the encrypted .text, so the text is not grouped per event.
"""
import csv
import io
import json
import os
import struct

import click
from PIL import Image

from utils import pe_resources

EXE = "Nobunaga5WPK.exe"
RDATA, RDATA_END, DATA, DATA_END = 0x72A00, 0x86800, 0x86800, 0xD7C00
VA = 0x401600
ITEM_NAMES, ITEM_COUNT = 0xB9C30, 120
CATEGORY_NAMES, KIND_CATEGORY = 0xD669C, 0xD66B4
SCENARIOS = ["SV10.N5S", "Sv11.n5s", "Sv12.n5s", "Sv13.n5s", "SV14.N5S"]  # 1534, 1551, 1568, 1582, 1583
ITEMS = 0x6EE4
PC98_NAMES = 0xB7A
FACE_COLOURS = "#000000 #0066AA #FF4422 #FFAACC #66AA44 #88DDFF #FFCC66 #FFFFFF"  # MAIN.EXE colours 8-15
EVENT_CG = [("Nobunaga5WPK.exe", 153, "painting_153", "640x480 一枚絵（用途不明）"),
            ("gaiko.dll", 101, "gaiko_1", "外交・謁見"), ("gaiko.dll", 102, "gaiko_2", "外交・謁見"),
            ("gaiko.dll", 103, "gaiko_3", "外交・謁見"), ("gaiko.dll", 104, "gaiko_4", "外交・謁見")]
MAPS = [(101, "world_1"), (102, "world_2"), (103, "world_3"), (104, "world_4"), (120, "kakkyozu")]
MOVIES = [("op.avi", "オープニング"), ("ED1.AVI", "エンディング"), ("ED2.AVI", "エンディング"), ("ed3.avi", "エンディング"),
          ("REKIS1.AVI", "歴史事件"), ("REKIS2.AVI", "歴史事件"), ("jisin.avi", "地震"), ("taifuu.avi", "台風"),
          ("housa.avi", "豊作"), ("kyous.avi", "凶作"), ("katid.avi", "勝鬨"), ("Testavi.avi", "テスト")]


def _csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _cstr(data, off):
    return data[off:data.index(b"\0", off)].decode("cp932")


def _ptr_str(exe, ptr_off):
    return _cstr(exe, struct.unpack_from("<I", exe, ptr_off)[0] - VA)


def _bitmaps(path):
    """resource id -> PIL image for every BMP resource of a PE file."""
    out = {}
    for rid, b in pe_resources(open(path, "rb").read(), 2):
        size, bpp = struct.unpack_from("<I", b)[0], struct.unpack_from("<H", b, 14)[0]
        colours = struct.unpack_from("<I", b, 32)[0] or (1 << bpp if bpp <= 8 else 0)
        head = b"BM" + struct.pack("<IHHI", 14 + len(b), 0, 0, 14 + size + 4 * colours)
        im = Image.open(io.BytesIO(head + b))
        im.load()
        out[rid] = im
    return out


def _pc98_item_pictures(data):
    pal = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in FACE_COLOURS.split()]
    out = []
    for k in range(len(data) // 1080):
        b = data[1080 * k:1080 * k + 1080]
        px = [pal[(b[3 * (j // 8)] >> (7 - j % 8) & 1) << 2 | (b[3 * (j // 8) + 1] >> (7 - j % 8) & 1) << 1
                  | (b[3 * (j // 8) + 2] >> (7 - j % 8) & 1)] for j in range(64 * 45)]
        im = Image.new("RGB", (64, 45))
        im.putdata(px)
        out.append(im)
    return out


def items(steam, pc98, out):
    exe = open(os.path.join(steam, EXE), "rb").read()
    names = [_ptr_str(exe, ITEM_NAMES + 4 * i) for i in range(ITEM_COUNT)]
    categories = [_ptr_str(exe, CATEGORY_NAMES + 4 * i) for i in range(6)]
    kind_category = exe[KIND_CATEGORY:KIND_CATEGORY + 26]
    tables = [open(os.path.join(steam, s), "rb").read()[ITEMS:ITEMS + 4 * ITEM_COUNT] for s in SCENARIOS]
    assert all(t == tables[0] for t in tables), "item table differs between scenarios"
    pc98_names = None
    if pc98:
        kan = open(os.path.join(pc98, "KAN.NB5"), "rb").read()
        pc98_names = [kan[PC98_NAMES + 11 * i:PC98_NAMES + 11 * i + 11].split(b"\0")[0].decode("cp932")
                      for i in range(ITEM_COUNT)]
    pics = os.path.join(out, "items", "pictures")
    os.makedirs(pics, exist_ok=True)
    bmps = _bitmaps(os.path.join(steam, EXE))
    for k in range(26):
        bmps[201 + k].save(os.path.join(pics, f"{k:02d}.png"))
    if pc98:
        os.makedirs(os.path.join(pics, "pc98"), exist_ok=True)
        for k, im in enumerate(_pc98_item_pictures(open(os.path.join(pc98, "ITEM.NB5"), "rb").read())):
            im.save(os.path.join(pics, "pc98", f"{k:02d}.png"))
    rows = []
    for i, name in enumerate(names):
        holder, value, kind = struct.unpack_from("<HBB", tables[0], 4 * i)
        pic = kind & 0x1F
        rows.append([i, name, "" if pc98_names is None or pc98_names[i] == name else pc98_names[i],
                     categories[kind_category[pic]], pic, f"pictures/{pic:02d}.png", value,
                     kind >> 6 & 1, kind >> 7, "" if holder == 0xFFFF else holder])
    _csv(os.path.join(out, "items", "kahou.csv"),
         ["id", "name", "name_pc98", "category", "kind", "picture", "value", "flag6", "flag7", "holder"], rows)
    return len(rows), sum(1 for r in rows if r[2] == "")


def eventcg(steam, out):
    d = os.path.join(out, "eventcg")
    os.makedirs(d, exist_ok=True)
    cache, rows = {}, []
    for k, (src, rid, name, purpose) in enumerate(EVENT_CG):
        cache.setdefault(src, _bitmaps(os.path.join(steam, src)))
        im = cache[src][rid]
        im.save(os.path.join(d, f"{name}.png"))
        rows.append([k, f"{name}.png", purpose, f"{src} BMP {rid}", f"{im.width}x{im.height}", "🟡"])
    _csv(os.path.join(d, "index.csv"), ["no", "file", "purpose", "source", "size", "evidence"], rows)
    rows = [[f, p, os.path.getsize(os.path.join(steam, f)), "🟡 名前から推定"] for f, p in MOVIES
            if os.path.exists(os.path.join(steam, f))]
    _csv(os.path.join(d, "movies.csv"), ["file", "purpose", "bytes", "evidence"], rows)
    return len(EVENT_CG), len(rows)


def kamon(steam, out):
    d = os.path.join(out, "kamon")
    os.makedirs(d, exist_ok=True)
    bmps = _bitmaps(os.path.join(steam, "Kamon.dll"))
    for rid, im in bmps.items():
        im.save(os.path.join(d, f"{rid - 200:03d}.png"))
    return len(bmps)


def world_maps(steam, out):
    d = os.path.join(out, "map")
    os.makedirs(d, exist_ok=True)
    bmps = _bitmaps(os.path.join(steam, "Map.dll"))
    for rid, name in MAPS:
        bmps[rid].save(os.path.join(d, f"{name}.png"))
    return len(MAPS)


def events(steam, out):
    exe = open(os.path.join(steam, EXE), "rb").read()
    refs = {}  # string offset -> [(table offset, index)]
    table, index = None, 0
    for o in range(DATA, DATA_END, 4):
        t = struct.unpack_from("<I", exe, o)[0] - VA
        if RDATA <= t < RDATA_END and exe[t - 1] == 0 and exe[t] != 0:
            if table is None:
                table, index = o, 0
            refs.setdefault(t, []).append([f"0x{table:X}", index])
            index += 1
        else:
            table = None
    d = os.path.join(out, "events")
    os.makedirs(d, exist_ok=True)
    n, o = 0, RDATA
    with open(os.path.join(d, "messages.jsonl"), "w", encoding="utf-8") as f:
        while o < RDATA_END:
            if exe[o] == 0:
                o += 1
                continue
            e = exe.index(b"\0", o)
            try:
                text = exe[o:e].decode("cp932")
            except UnicodeDecodeError:
                text = None
            if (text and len(text) >= 2 and sum(ord(c) >= 0x3040 for c in text) >= 2
                    and all(c == "\n" or ord(c) >= 0x20 for c in text)):
                f.write(json.dumps({"offset": f"0x{o:X}", "text": text, "tables": refs.get(o, [])},
                                   ensure_ascii=False) + "\n")
                n += 1
            o = e + 1
    return n


@click.command("nobu5-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam install (games/steam/628090)")
@click.option("--pc98-dir", type=click.Path(exists=True), help="PC-98 files for cross-checks (games/nobu5-pc98)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/nobu5pk-win/extract)")
def nobu5_extras(game_dir, pc98_dir, out):
    """信長の野望・覇王伝 PK: 家宝, event pictures, 家紋, world maps and event text."""
    n, same = items(game_dir, pc98_dir, out)
    click.echo(f"items: {n} 家宝" + (f", {same} names equal to PC-98 KAN.NB5" if pc98_dir else ""))
    click.echo("eventcg: %d pictures, %d movies listed" % eventcg(game_dir, out))
    click.echo(f"kamon: {kamon(game_dir, out)}")
    click.echo(f"map: {world_maps(game_dir, out)}")
    click.echo(f"events: {events(game_dir, out)} strings")


if __name__ == "__main__":
    nobu5_extras()
