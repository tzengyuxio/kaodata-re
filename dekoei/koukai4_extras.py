"""大航海時代IV with PK HD Version (Steam, appid 1424800): every picture, the items, ships, trade goods, ports and
landing places, the scenario dialogue and the message file, written under --out (notes/koukai4.md「事件、插圖、道具」).

- Pictures: every *.dk4 GT1G texture set (the format of bustup.dk4). Per texture: byte 1 format (0x59 BC1, 0x5B BC3,
  0x01 RGBA8), byte 2 size as log2 (low nibble width, high nibble height), +8 u32 extra header size; when byte 2 is 0
  the size is the u32 pair at +0x14 (extra header of 0x14). The pixels follow the extra header. The JP and TC copies
  are written for files that have a language suffix; bustup.dk4 (kaodata) and the fonts are left out.
- Items: JP/World0.dll (JP/World1.dll for PK mode: same names, other places), 231 records of 32 bytes found by the
  pointer to カボチャの種: +0 name (pointer), +8 u32 price, +0xC u32 x and +0x10 u32 y (0xFFFFFFFF: not placed),
  +0x14 kind (ITEM_KINDS), +0x15 region (8 none), +0x16 related post, +0x17 power, +0x18 port that sells it (port
  record, 98 none: コショウの実 カリカット, タバコの苗木 ハバナ, 陣太鼓 大坂), +0x19 flags; +0x15 is the sea area
  (SEA_AREAS, 8 none). The record
  number is the picture of Item56.dk4 / Item32.dk4.
- Ports: JP/World0.dll, 97 records of 132 bytes from ロンドン (GetFixTownProc(i) of the DLL; DK4HD_jp.exe copies them
  at 0x1402aed50) with the name inline (20 bytes): +0x14 x, y of the town and +0x1C x, y of the anchorage (map units),
  +0x24 1 = the zone's centre port, +0x25 zone (ZONES), +0x26 ?, +0x28 five (u16 good, u16 ?, u16 rate) market
  slots (good = trade-good record, 106 empty), +0x46 u16 ?, +0x48 u32 facility bits (FACILITIES), +0x4C three
  (force, influence %) pairs (0x1A none), +0x52 / +0x54 u16 ?, +0x58 two u32 (0), +0x60 five (u16 flag, u16 price,
  u16 rate) in market-slot order, the rest raw. World1.dll (PK) differs in +0x49, +0x4C-0x4F and +0x52-0x55.
- Ships: DK4HD_jp.exe, 39 records of 64 bytes found by the pointer to ハンザコグ: +0 name, +8 u16, +0xA u16 ?, +0xC u32
  price, the rest raw; the 107 ship builds (48 bytes, +8 u16 build code) follow; 商用… variants are another table.
- Trade goods: DK4HD_jp.exe, 105 records of 16 bytes found by the pointer to 小麦: +0 name, +8 u16 price, +0xA
  category (GOODS_KINDS), +0xB, +0xC u16, +0xE 1 base game / 0 the goods PK adds (蜂蜜, キャビア … 🟡). The record
  number is the picture of TItem48.dk4 / TItem24.dk4.
- Landing places: DK4HD_jp.exe, 24 records of 56 bytes from イヌビク: +0 name, +8 x, +0xC y (map units), then raw.
- The TC tables are found by the same record bytes (pointers left out) in the TC files and give the zh names.
- Scenario dialogue: {JP,TC}/Sc0-6.dk4: u32 count, count x (u32 offset, size) of "DS" scripts. A line is
  40 FF FF <a> <b> text 00: a = 0 → b is the speaker (person record of World0.dll), a = 0x80 → narration. JP and TC
  have the same lines in the same order.
- {JP,TC}/mesfile.dk4: the same container of string blocks; a block is NUL-separated text (some strings are
  continued without a NUL). The JP and TC blocks are not the same, so they are written separately.
- World.dat: 2500 x 1250 u16 map cells, each the tile number of Chip.DK4 texture 0 (16 tiles of 32 x 32 per row,
  the sea transparent); drawn over the sea texture (texture 4) as map/world.png. Map units are 1/16 cell: the
  全世界 area of DK4HD_jp.exe 0x14058c590 is 0, 0, 40000, 20000. Only with the pictures.
"""
import csv
import os
import re
import struct

import click
from PIL import Image, ImageDraw

import koei_games

BCN = {0x59: 1, 0x5B: 3}
# (file, folder); {lang} = JP / TC
PICTURES = [
    *[(f"EventBG{i}.dk4", f"eventcg/bg{i}") for i in range(1, 9)], ("EventBGEX.dk4", "eventcg/bgex"),
    ("EvItem.dk4", "eventcg/items"), ("EvFrame.dk4", "eventcg/frame"), ("Remains.dk4", "eventcg/remains"),
    ("OldMapStill.dk4", "eventcg/oldmap"), ("GoldRoad.dk4", "eventcg/goldroad"),
    ("GoldRoadAnime{lang}.dk4", "eventcg/goldroad_anime_{lang}"), ("Portrait.dk4", "eventcg/portrait"),
    ("FirstGrp.dk4", "eventcg/opening"), ("startup.dk4", "eventcg/startup"), ("Title{lang}.dk4", "eventcg/title_{lang}"),
    ("Search.DK4", "eventcg/search"), ("TownGrp.DK4", "towns"),
    ("Item56.dk4", "items/pictures"), ("Item32.dk4", "items/pictures_small"),
    ("TItem48.dk4", "tables/goods_pictures"), ("TItem24.dk4", "tables/goods_pictures_small"),
    ("ship.dk4", "ships/sprites"), ("StlShip.dk4", "ships/icons"), ("DeckShip.dk4", "ships/deck"),
    ("DeckScrn.dk4", "ships/deck_ui"), ("Gun.dk4", "ships/guns"),
    ("Chip.DK4", "map/chip"), ("OldMap.dk4", "map/oldmap"), ("RouteMap.dk4", "map/route"),
    ("RouteFrm.dk4", "map/route_frame"), ("RouteMkr.dk4", "map/route_marker"), ("mappoint.dk4", "map/mappoint"),
    ("Sky.DK4", "map/sky"), ("Weather.dk4", "map/weather"), ("Zodiac.dk4", "map/zodiac"),
    ("CmScreen.dk4", "ui/cmscreen"), ("InfoBox.dk4", "ui/infobox"), ("InfoBox2.dk4", "ui/infobox2"),
    ("mainbox.dk4", "ui/mainbox"), ("Icon{lang}.dk4", "ui/icon_{lang}"), ("NxIcon.dk4", "ui/nxicon"),
    ("OcFrm.DK4", "ui/ocfrm"), ("Plaza.dk4", "ui/plaza"), ("TradeWin.dk4", "ui/tradewin"),
    ("ScEffect.dk4", "ui/sceffect"),
    *[(f"Chara{i:02d}.DK4", f"sprites/chara{i:02d}") for i in range(42)],
]
LANGS = [("JP", "cp932"), ("TC", "cp950")]
# +0x14 of the item record; the item categories of the EXE (原産物 … 宝の地図), in record order 🟡
ITEM_KINDS = ["原産物", "航海用品", "装備品(武器)", "装備品(防具)", "航海用具", "船首像", "謎の小物", "贈り物", "覇者の証",
              "証の地図", "遺跡地図", "形見の品", "宝の地図"]
# the 19 trade-good categories (the EXE labels 食料品 … 雑貨, put in the order the goods of each category show: 小麦 食料品,
# 砂糖 調味料, キャビア 珍味, コショウ 香辛料, コーヒー 嗜好品, ワイン 酒類, 金 貴金属 …)
GOODS_KINDS = ["食料品", "調味料", "珍味", "香辛料", "嗜好品", "酒類", "貴金属", "工芸品", "繊維", "織物", "贅沢品", "香料",
               "装飾品", "宝石", "薬", "染料", "武器", "鉱石", "雑貨"]
ITEM_SIZE, PORT_SIZE, PORTS = 32, 132, 97
# DK4HD_jp.exe 0x1405b73e0 (0xE0 per zone): the zone of port +0x25; zone +8 is the sea area below
ZONES = ["イギリス", "フランドル", "ドイツ", "北欧", "ポルトガル", "スペイン", "イタリア", "ギリシャ", "トルコ", "エジプト",
         "西アフリカ", "東アフリカ", "アラブ", "インド", "インドシナ", "インドネシア", "中国", "朝鮮", "日本", "カリブ海",
         "メキシコ"]
# DK4HD_jp.exe 0x14058c590 (0x38 per area: name, then the area rectangle x0 y0 x1 y1 in map units): item +0x15
SEA_AREAS = ["北海", "地中海", "アフリカ", "インド洋", "東南アジア", "東アジア", "新大陸", "全世界"]
# DK4HD_jp.exe 0x1401417e0: facility i of a town; port +0x48 bit i
FACILITIES = ["広場", "交易所", "造船所", "出港所", "酒場", "ギルド", "王宮", "総督府", "宿屋", "遺跡", "教会", "城門"]
NO_FORCE = 0x1A
# World.dat: 2500 x 1250 cells; map units (port, item, landing place positions) are 1/16 cell (全世界 = 40000 x 20000)
WORLD_W, WORLD_H, UNIT, TILE = 2500, 1250, 16, 32
MAP_SCALE = 4  # world.png: pixels per cell, so a map position in pixels is units * MAP_SCALE / UNIT


def textures(data):
    """(index, format, width, height, pixel bytes) of a GT1G texture set."""
    table, count = struct.unpack_from("<2I", data, 12)
    offsets = struct.unpack_from(f"<{count}I", data, table)
    ends = [table + o for o in offsets[1:]] + [len(data)]
    for i, o in enumerate(offsets):
        h = table + o
        fmt, size = data[h + 1], data[h + 2]
        extra, = struct.unpack_from("<I", data, h + 8)
        if size == 0 and extra >= 0x14:
            w, ht = struct.unpack_from("<2I", data, h + 0x14)
        else:
            w, ht = 1 << (size & 15), 1 << (size >> 4)
        yield i, fmt, w, ht, data[h + 8 + extra:ends[i]]


def decode(fmt, w, h, px):
    if fmt in BCN:
        n = BCN[fmt]
        return Image.frombytes("RGBA", (w, h), px[:w * h // 2 if n == 1 else w * h], "bcn", n)
    if fmt == 0x01:
        return Image.frombytes("RGBA", (w, h), px[:w * h * 4])
    raise ValueError(f"texture format {fmt:#x}")


def write_pictures(game_dir, out):
    rows = []
    for name, folder in PICTURES:
        for lang in (["JP", "TC"] if "{lang}" in name else [""]):
            path = os.path.join(game_dir, name.format(lang=lang))
            dst = os.path.join(out, folder.format(lang=lang.lower()))
            os.makedirs(dst, exist_ok=True)
            with open(path, "rb") as f:
                data = f.read()
            for i, fmt, w, h, px in textures(data):
                rel = os.path.join(os.path.relpath(dst, out), f"{i:03d}.png")
                decode(fmt, w, h, px).save(os.path.join(out, rel))
                rows.append([os.path.basename(path), i, w, h, f"{fmt:#04x}", rel])
    _csv(os.path.join(out, "pictures.csv"), ["file", "index", "width", "height", "format", "png"], rows)
    return len(rows)


class PE:
    """Sections and strings of a PE file (x64: 8-byte pointers)."""

    def __init__(self, path, encoding):
        with open(path, "rb") as f:
            self.data = d = f.read()
        self.encoding = encoding
        pe, = struct.unpack_from("<I", d, 0x3C)
        n, header = struct.unpack_from("<H", d, pe + 6)[0], struct.unpack_from("<H", d, pe + 20)[0]
        self.base, = struct.unpack_from("<Q", d, pe + 48)
        self.sections = [struct.unpack_from("<3I", d, pe + 24 + header + 40 * i + 12) for i in range(n)]

    def offset(self, va):
        r = va - self.base
        return next((raw + r - rva for rva, size, raw in self.sections if rva <= r < rva + size), None)

    def va(self, o):
        return next(self.base + rva + o - raw for rva, size, raw in self.sections if raw <= o < raw + size)

    def text(self, va):
        o = self.offset(va) if va else None
        if o is None:
            return None
        return self.data[o:self.data.index(b"\0", o)].decode(self.encoding, "replace")

    def ptr(self, o):
        return struct.unpack_from("<Q", self.data, o)[0]

    def table(self, first, stride):
        """File offset and count of a table of records starting with a name pointer, from its first name."""
        b = b"\0" + first.encode(self.encoding) + b"\0"
        o = self.data.index(b) + 1
        start = self.data.index(struct.pack("<Q", self.va(o)))
        n = 0
        while self.text(self.ptr(start + n * stride)) is not None:
            n += 1
        return start, n


def twin(jp: PE, start, stride, n, other: PE, skip=8):
    """The same table in another language's file: the record bytes after the name pointer are identical."""
    sig = jp.data[start + skip:start + stride]
    i = other.data.find(sig)
    while i >= 0:
        s = i - skip
        if all(other.data[s + k * stride + skip:s + (k + 1) * stride] ==
               jp.data[start + k * stride + skip:start + (k + 1) * stride] for k in range(n)):
            return s
        i = other.data.find(sig, i + 1)
    return None


def tables(game_dir, out):
    counts = {}
    w0 = {lang: PE(os.path.join(game_dir, lang, "World0.dll"), enc) for lang, enc in LANGS}
    w1 = PE(os.path.join(game_dir, "JP", "World1.dll"), "cp932")
    exe = {lang: PE(os.path.join(game_dir, f"DK4HD_{lang.lower()}.exe"), enc) for lang, enc in LANGS}

    e = exe["JP"]
    gs, gn = e.table("小麦", 16)
    goods = [e.text(e.ptr(gs + 16 * i)) for i in range(gn)]  # market slot 106 = empty

    # ports (names inline, 97 records from ロンドン = GetFixTownProc(0) of World0.dll); World1.dll (PK mode) has its
    # own copy: +0x49, +0x4C-0x4F and +0x52-0x55 differ
    first = b"\x0c\x00" + "ブリストル".encode("cp932") + b"\0"
    o0, p1 = w0["JP"].data.index(first) + 2 - PORT_SIZE, w1.data.index(first) + 2 - PORT_SIZE
    jp, tc = w0["JP"], w0["TC"]
    assert jp.data[o0:o0 + 20].split(b"\0")[0].decode("cp932") == "ロンドン"
    t0 = tc.data.find(jp.data[o0 + 20:o0 + PORT_SIZE]) - 20
    fs, fn = jp.table("カストール商会", 0x58)
    forces = [jp.text(jp.ptr(fs + 0x58 * i)) for i in range(fn)]
    ports, rows = [], []

    def market(r):
        slots = [struct.unpack_from("<3H", r, 40 + 6 * k) for k in range(5)]
        return " ".join(f"{goods[g]}:{p}:{q}" for g, p, q in slots if g < len(goods))

    def market2(r):  # +0x60 five (u16 flag, u16 price, u16 rate), the same order as the market slots
        return " ".join("{}:{}:{}".format(*struct.unpack_from("<3H", r, 0x60 + 6 * k)) for k in range(5)
                        if struct.unpack_from("<H", r, 40 + 6 * k)[0] < len(goods))

    def facilities(r):
        bits, = struct.unpack_from("<I", r, 0x48)
        return " ".join(f for k, f in enumerate(FACILITIES) if bits >> k & 1)

    def influence(r):  # +0x4C three (force, influence %) pairs (DK4HD_jp.exe 0x1402ae543)
        return " ".join(f"{forces[r[0x4C + 2 * k]] if r[0x4C + 2 * k] < len(forces) else r[0x4C + 2 * k]}:"
                        f"{r[0x4D + 2 * k]}" for k in range(3) if r[0x4C + 2 * k] != NO_FORCE and r[0x4D + 2 * k])

    for i in range(PORTS):
        o, t = o0 + i * PORT_SIZE, t0 + i * PORT_SIZE
        rec, pk = jp.data[o:o + PORT_SIZE], w1.data[p1 + i * PORT_SIZE:p1 + (i + 1) * PORT_SIZE]
        name = rec[:20].split(b"\0")[0].decode("cp932")
        ports.append(name)
        zh = tc.data[t:t + 20].split(b"\0")[0].decode("cp950", "replace") if t0 >= 0 else ""
        x1, y1, x2, y2 = struct.unpack_from("<4I", rec, 20)
        rows.append([i, name, zh, x1, y1, x2, y2, rec[36:40].hex(" "), market(rec),
                     rec[70:].hex(" "), market(pk), "" if pk[70:] == rec[70:] else pk[70:].hex(" "),
                     *_map(x1, y1), *_map(x2, y2), rec[0x24], ZONES[rec[0x25]], rec[0x26],
                     struct.unpack_from("<H", rec, 0x46)[0], facilities(rec), influence(rec),
                     *struct.unpack_from("<2H", rec, 0x52), *struct.unpack_from("<2I", rec, 0x58), market2(rec),
                     facilities(pk), influence(pk), *struct.unpack_from("<2H", pk, 0x52)])
    _csv(os.path.join(out, "tables", "ports.csv"),
         ["id", "name", "nameZh", "x1", "y1", "x2", "y2", "b36", "market (good:price:?)", "rest", "pkMarket",
          "pkRest (when different)", "mapX", "mapY", "anchorMapX", "anchorMapY", "center", "zone", "b26", "u16_46",
          "facilities", "influence (force:%)", "u16_52", "u16_54", "u32_58", "u32_5C", "market2 (flag:price:rate)",
          "pkFacilities", "pkInfluence", "pkU16_52", "pkU16_54"], rows)
    counts["ports"] = len(rows)
    counts["port_pixels"] = [(r[12], r[13]) for r in rows]

    # items; World1.dll (PK mode) has the same names in the same order, other places and shops
    start, n = jp.table("カボチャの種", ITEM_SIZE)
    s1, _ = w1.table("カボチャの種", ITEM_SIZE)
    tc_start = twin(jp, start, ITEM_SIZE, n, w0["TC"])

    def place(data, o):
        x, y = struct.unpack_from("<2I", data, o + 0xC)
        port = data[o + 0x18]
        return ["" if x == 0xFFFFFFFF else x, "" if y == 0xFFFFFFFF else y, data[o + 0x15],
                ports[port] if port < len(ports) else "", data[o + 0x19]]
    def extra(data, o):
        x, y = struct.unpack_from("<2I", data, o + 0xC)
        area = data[o + 0x15]
        return [SEA_AREAS[area] if area < len(SEA_AREAS) else "", *(_map(x, y) if x != 0xFFFFFFFF else ["", ""])]
    rows = []
    for i in range(n):
        o = start + i * ITEM_SIZE
        price, = struct.unpack_from("<I", jp.data, o + 8)
        kind, post, power = jp.data[o + 0x14], jp.data[o + 0x16], jp.data[o + 0x17]
        zh = w0["TC"].text(w0["TC"].ptr(tc_start + i * ITEM_SIZE)) if tc_start is not None else ""
        rows.append([i, jp.text(jp.ptr(o)), zh, ITEM_KINDS[kind] if kind < len(ITEM_KINDS) else kind, kind, price,
                     post, power, *place(jp.data, o), *place(w1.data, s1 + i * ITEM_SIZE),
                     f"items/pictures/{i:03d}.png", *extra(jp.data, o), *extra(w1.data, s1 + i * ITEM_SIZE)])
    _csv(os.path.join(out, "items", "items.csv"),
         ["id", "name", "nameZh", "kind", "kindCode", "price", "post", "power", "x", "y", "region", "shop", "b19",
          "pkX", "pkY", "pkRegion", "pkShop", "pkB19", "picture", "area", "mapX", "mapY", "pkArea", "pkMapX",
          "pkMapY"], rows)
    counts["items"] = n

    # EXE tables: (file, first name, stride)
    for fname, first, stride, header in [
            ("ships", "ハンザコグ", 64, ["u16_8", "u16_A", "price"]),
            ("ship_builds", None, 48, ["code"]),
            ("goods", "小麦", 16, ["price", "kind", "kindName", "b11", "u16_C", "base"]),
            ("places", "イヌビク", 56, ["x", "y", "mapX", "mapY", "u32_10", "u32_14", "u32_18", "u32_1C", "b30", "b31"]),
    ]:
        e = exe["JP"]
        if fname == "ship_builds":
            start = e.data.index(struct.pack("<Q", e.ptr(ships_start)), ships_start + 1)
            n = 0
            while e.text(e.ptr(start + n * stride)) is not None:
                n += 1
        else:
            start, n = e.table(first, stride)
        if fname == "ships":
            ships_start = start
        tc_start = twin(e, start, stride, n, exe["TC"])
        rows = []
        for i in range(n):
            o = start + i * stride
            zh = exe["TC"].text(exe["TC"].ptr(tc_start + i * stride)) if tc_start is not None else ""
            rec = e.data[o:o + stride]
            if fname == "ships":
                fields = [*struct.unpack_from("<2HI", rec, 8)]
                rest = rec[16:]
            elif fname == "ship_builds":
                fields = [struct.unpack_from("<H", rec, 8)[0]]
                rest = rec[10:]
            elif fname == "goods":
                price, b11, u12 = struct.unpack_from("<H", rec, 8)[0], rec[11], struct.unpack_from("<H", rec, 12)[0]
                fields = [price, rec[10], GOODS_KINDS[rec[10]] if rec[10] < len(GOODS_KINDS) else "", b11, u12, rec[14]]
                rest = rec[15:]
            else:  # landing place: +8 x, +0xC y (map units), +0x10 four u32 (cell-sized, meaning unknown), +0x30, +0x31
                x, y, *box = struct.unpack_from("<6I", rec, 8)
                fields, rest = [x, y, *_map(x, y), *box, rec[0x30], rec[0x31]], rec[0x32:]
            extra = [f"tables/goods_pictures/{i:03d}.png"] if fname == "goods" else []
            rows.append([i, e.text(e.ptr(o)), zh, *fields, *extra, rest.hex(" ")])
        h = ["id", "name", "nameZh", *header]
        if fname == "goods":
            h += ["picture"]
        _csv(os.path.join(out, "tables", f"{fname}.csv"), h + ["rest"], rows)
        counts[fname] = n
    return counts


SPEECH = re.compile(rb"\x40\xff\xff([\x00\x80])(.)([^\x00]+)\x00", re.S)


def _blocks(path):
    with open(path, "rb") as f:
        data = f.read()
    n, = struct.unpack_from("<I", data, 0)
    return [data[o:o + s] for o, s in (struct.unpack_from("<2I", data, 4 + 8 * k) for k in range(n))]


def events(game_dir, out):
    persons = {lang: koei_games.load_koukai4_win_persons(os.path.join(game_dir, lang, "World0.dll"), first, enc)
               for (lang, enc), first in zip(LANGS, ["ラファエル", "拉斐爾"])}

    def speaker(lang, kind, b):
        if kind:
            return ""
        given, family, middle = persons[lang][b][:3] if b < len(persons[lang]) else (str(b), "", "")
        return given if not family else "・".join(x for x in (given, middle, family) if x)

    rows, total = [], 0
    for k in range(7):
        lines = {}
        for lang, enc in LANGS:
            lines[lang] = [(b, m.group(1)[0], m.group(2)[0], m.group(3).decode(enc, "replace"))
                           for b, blk in enumerate(_blocks(os.path.join(game_dir, lang, f"Sc{k}.dk4")))
                           for m in SPEECH.finditer(blk)]
        assert len(lines["JP"]) == len(lines["TC"])
        for (b, kind, who, ja), (_, _, _, zh) in zip(lines["JP"], lines["TC"]):
            rows.append([k, b, "" if kind else who, speaker("JP", kind, who), ja, zh])
        total += len(lines["JP"])
    _csv(os.path.join(out, "events", "scenario.csv"), ["scenario", "script", "speaker", "speakerName", "ja", "zh"],
         rows)
    for lang, enc in LANGS:
        rows = [[b, i, s.decode(enc, "replace").lstrip(" ")]
                for b, blk in enumerate(_blocks(os.path.join(game_dir, lang, "mesfile.dk4")))
                for i, s in enumerate(blk.split(b"\0")) if s.strip(b" ")]
        _csv(os.path.join(out, "text", f"mesfile_{lang.lower()}.csv"), ["block", "index", "text"], rows)
    return total


def _map(x, y):
    """A map position (1/16 cell) as pixels of map/world.png."""
    return [x * MAP_SCALE // UNIT, y * MAP_SCALE // UNIT]


def world_map(game_dir, out, ports=None):
    """map/world.png: World.dat (u16 per cell = tile k of Chip.DK4 texture 0, 16 tiles of 32 x 32 per row; the sea is
    transparent) over the sea texture (Chip.DK4 texture 4, 512 x 512 = 16 cells), MAP_SCALE pixels per cell.
    map/world_ports.png: the same at a quarter of the size with every port (x1, y1) marked. world_cells.png is the
    old preview with one colour per cell value."""
    with open(os.path.join(game_dir, "World.dat"), "rb") as f:
        data = f.read()
    cells = struct.unpack(f"<{len(data) // 2}H", data)
    pal = {}
    for v in sorted(set(cells)):
        h = (v * 2654435761) & 0xFFFFFF
        pal[v] = (h >> 16, (h >> 8) & 255, h & 255)
    im = Image.new("RGB", (WORLD_W, len(cells) // WORLD_W))
    im.putdata([pal[v] for v in cells])
    os.makedirs(os.path.join(out, "map"), exist_ok=True)
    im.save(os.path.join(out, "map", "world_cells.png"))

    with open(os.path.join(game_dir, "Chip.DK4"), "rb") as f:
        tex = [decode(fmt, w, h, px) for _, fmt, w, h, px in textures(f.read())]
    chip, sea = tex[0], tex[4].convert("RGB")
    s = MAP_SCALE
    sea = sea.resize((s * 16, s * 16), Image.BOX)
    world = Image.new("RGB", (WORLD_W * s, WORLD_H * s))
    for y in range(0, world.height, sea.height):
        for x in range(0, world.width, sea.width):
            world.paste(sea, (x, y))
    tiles = {}
    for v in set(cells):
        t = chip.crop((v % 16 * TILE, v // 16 * TILE, v % 16 * TILE + TILE, v // 16 * TILE + TILE))
        if t.getextrema()[3][1]:  # skip the fully transparent (open sea) tiles
            t = t.resize((s, s), Image.BOX)
            tiles[v] = (t.convert("RGB"), t.getchannel("A"))
    for i, v in enumerate(cells):
        if v in tiles:
            rgb, a = tiles[v]
            world.paste(rgb, (i % WORLD_W * s, i // WORLD_W * s), a)
    world.save(os.path.join(out, "map", "world.png"))
    if ports:
        small = world.resize((world.width // 4, world.height // 4), Image.BOX)
        d = ImageDraw.Draw(small)
        for x, y in ports:
            x, y = x // 4, y // 4
            d.ellipse((x - 3, y - 3, x + 3, y + 3), outline=(255, 0, 0), width=2)
        small.save(os.path.join(out, "map", "world_ports.png"))


def _csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


@click.command("koukai4-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam files (games/koukai4pk-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/koukai4pk-win/extract)")
@click.option("--no-pictures", is_flag=True, help="only the tables and texts")
def koukai4_extras(game_dir, out, no_pictures):
    """大航海時代IV PK HD: pictures, items, ships, trade goods, ports, scenario dialogue, messages."""
    os.makedirs(out, exist_ok=True)
    counts = tables(game_dir, out)
    port_pixels = counts.pop("port_pixels")
    print(", ".join(f"{k} {v}" for k, v in counts.items()))
    print(f"scenario lines: {events(game_dir, out)}")
    if not no_pictures:
        world_map(game_dir, out, port_pixels)
        print(f"pictures: {write_pictures(game_dir, out)}")


if __name__ == "__main__":
    koukai4_extras()
