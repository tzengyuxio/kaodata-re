"""大航海時代III (Win, Chinese, CDS95.EXE): cities and ports, nations, trade goods and market zones, facilities,
ships, items, discoveries, the extra person fields and the world map, written under --out
(notes/koukai3.md「港口、交易品、道具、地圖」). All tables are in CDS95.EXE (VA, pointers to Big5 strings).

- Cities: 0x4EF150, 226 records of 0x88 (0x469BE0 copies them to the runtime objects 0x5E04E0, stride 0x5C):
  +0 name, +4 x, +8 y (WORLD.CDS cells, 0x46A220), +0xC kind, +0x10 linked city, +0x14 ?, +0x18 u16 ship bits,
  +0x1C market zone (0x467CE0, 0x46A3B0), +0x20 region, +0x24 nation, +0x28 規模 1-5, +0x2C 行情 %, +0x30 特產品
  (goods), +0x34 ?, +0x38 level (index of LEVELS), +0x3C 8 shop items (-1 none, 0x469CCE, 0x4979C1), +0x5C 狀況 (CONDITIONS),
  +0x60 u16 facility bits (FACILITY_KINDS), +0x62 u16 ?, +0x64 4 discoveries (-1 none), +0x74 9 u16 ?.
- Nations: 0x4C5160, 78 records of 24: +0 name, +4 language, +8 capital city, +0xC religion, +0x10, +0x14 ?.
- Trade goods: 0x4EC9F0, 70 records of 0x88: +0 name, +4 picture id, +8 category, +0xC 28 base prices (one per
  market zone), +0x7C 個體重量, +0x80 耐久度, +0x84 flag. Market zones: 0x4EEF20, 28 x 5 goods (-1 none).
- Facilities: 0x4C5FA8, 1508 records of 0x38: +0 name, +4 generic name, +8 city, +0xC kind, +0x10 4 links,
  +0x20 x, y, w, h in the town picture, +0x30, +0x34 ?.
- Ships: 0x4FAF60, 8 records of 64: +4 ?, +8 required city size, +0xC/+0x10 推進力, +0x14/+0x18 耐久度,
  +0x1C/+0x20 最大重量, +0x24/+0x28 最大容量, +0x2C/+0x30 (cannons?), +0x34 ?, +0x38 price / 1000, +0x3C u16 flags.
- Items: 0x509978, 285 records of 28: +0 name, +4 ITEM.CDS picture (-1 none), +8 price, +0xC, +0x10 power, +0x14
  kind; descriptions 0x5501A8 by item number. ITEM.CDS: 205 x (120 x 120 picture, 86-colour palette).
- Discoveries: 0x4DE540, 273 records of 0x5C: +0 name, +4 category, +8 code, +0xC DSTILL.CDS still, +0x10 ?,
  +0x14 ?, +0x18 reward, +0x30 ?, +0x38 description (0x5326C8), +0x44 x1, y1, x2, y2 (WORLD.CDS cells, -1 none).
  DSTILL.CDS: 84 x (picture, palette, u32 w, h).
- CITYCG.CDS: 226 x (400 x 320 town picture, palette at colour 74), by city number; the facility rectangles are on it.
- Persons (KOUKAI3_WIN_PERSONS): +0x14 nation, +0x18 star sign, +0x1C blood type, +0x20 occupation, +0x24 名聲,
  +0x28 惡名, +0x58 (疲勞 for the player), +0x5C ?.
- WORLD.CDS: 2500 x 1250 u16 cells (0.144 degree each); the high byte is the terrain class. The map is drawn by
  class (the OCEAN.CDS tiles are not mapped yet) as map/world.png, with the cities as map/world_cities.png.
"""
import csv
import os
import struct

import click
from PIL import Image, ImageDraw

import koei_games
import ls11

EXE = "CDS95.EXE.pec2bac"
CITIES = (0x4EF150, 226, 0x88)
NATIONS = (0x4C5160, 78, 24)
GOODS = (0x4EC9F0, 70, 0x88)
ZONES = (0x4EEF20, 28, 20)
FACILITIES = (0x4C5FA8, 1508, 0x38)
SHIPS = (0x4FAF60, 8, 64)
ITEMS = (0x509978, 285, 28)
DISCOVERIES = (0x4DE540, 273, 0x5C)
# string tables (pointer arrays)
LANGUAGES = (0x551F88, 14)
RELIGIONS = (0x552158, 13)
GOODS_KINDS = (0x53D6F8, 13)
CONDITIONS = (0x53E5C0, 8)
ITEM_KINDS = (0x550620, 8)
ITEM_TEXTS = 0x5501A8
DISCOVERY_KINDS = (0x5521A0, 8)
DISCOVERY_TEXTS = 0x5326C8
STAR_SIGNS = (0x551F18, 12)
BLOOD_TYPES = (0x551EF0, 4)
JOBS = (0x551FE8, 22)
LEVELS = [20, 50, 100, 200, 350, 500, 700, 1000]  # 0x53E5A0, by city +0x38
FACILITY_KINDS = ["港口", "交易所", "王宮", "教堂", "酒館", "旅館", "造船廠", "市集", "圖書館", "行會", "城門",
                  "自宅", "其他12", "其他13", "其他14", "其他15"]
SEA = {0, 1, 4, 5, 6, 7, 8, 9, 10}


class Exe:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = f.read()

    def words(self, va, n, fmt="i"):
        o = koei_games.koukai3_win_offset(va)
        return list(struct.unpack_from(f"<{n}{fmt}", self.data, o))

    def text(self, va):
        if not va:
            return ""
        o = koei_games.koukai3_win_offset(va)
        return self.data[o:self.data.index(b"\0", o)].decode("big5", "replace")

    def strings(self, table):
        va, n = table
        return [self.text(p) for p in self.words(va, n, "I")]

    def records(self, table):
        va, n, size = table
        return [(i, va + i * size) for i in range(n)]


def terrain(v):
    hi = v >> 8
    if hi in SEA:
        return "sea"
    if 64 <= hi <= 68:
        return "land"
    if 86 <= hi <= 116:
        return "feature"
    if 153 <= hi <= 179 or 217 <= hi <= 243:
        return "town"
    return "other"


COLOURS = {"sea": (40, 70, 140), "land": (110, 150, 80), "feature": (150, 120, 80), "town": (220, 60, 60),
           "other": (200, 200, 200)}


def load_world(game_dir):
    with open(os.path.join(game_dir, "WORLD.CDS"), "rb") as f:
        data = f.read()
    return struct.unpack(f"<{2500 * 1250}H", data)


def palette(sys_rgb, part, base):
    pal = [0] * 768
    for i, rgb in enumerate(sys_rgb):
        pal[3 * (10 + i):3 * (10 + i) + 3] = rgb
    for i in range(len(part) // 3):
        b, r, g = part[3 * i:3 * i + 3]
        pal[3 * (base + i):3 * (base + i) + 3] = [r, g, b]
    return pal


def picture(px, w, h, pal):
    im = Image.frombytes("P", (w, h), px)
    im.putpalette(pal)
    return im.convert("RGB")


def tables(exe: Exe, persons, out):
    nation_names = [exe.text(exe.words(va, 1, "I")[0]) for _, va in exe.records(NATIONS)]
    city_names = [exe.text(exe.words(va, 1, "I")[0]) for _, va in exe.records(CITIES)]
    goods_names = [exe.text(exe.words(va, 1, "I")[0]) for _, va in exe.records(GOODS)]
    disc_names = [exe.text(exe.words(va, 1, "I")[0]) for _, va in exe.records(DISCOVERIES)]
    item_names = [exe.text(exe.words(va, 1, "I")[0]) for _, va in exe.records(ITEMS)]
    languages, religions = exe.strings(LANGUAGES), exe.strings(RELIGIONS)
    goods_kinds, conditions = exe.strings(GOODS_KINDS), exe.strings(CONDITIONS)

    def name(names, i):
        return names[i] if 0 <= i < len(names) else ""

    rows = []
    for i, va in exe.records(NATIONS):
        _, lang, capital, religion, a, b = exe.words(va, 6)
        rows.append([i, nation_names[i], lang, name(languages, lang), capital, name(city_names, capital),
                     religion, name(religions, religion), a, b])
    _csv(os.path.join(out, "tables", "nations.csv"),
         ["nation", "name", "language", "languageName", "capital", "capitalName", "religion", "religionName",
          "+0x10", "+0x14"], rows)

    cities = []
    rows = []
    for i, va in exe.records(CITIES):
        w = exe.words(va, 0x60 // 4)
        bits, u62 = exe.words(va + 0x60, 2, "H")
        disc = exe.words(va + 0x64, 4)
        matrix = exe.words(va + 0x74, 9, "H")
        ship_bits = w[6] & 0xFFFF
        x, y, kind, link, u14, zone, region, nation, size, rate, special, u34, level = w[1:6] + w[7:15]
        more = [g for g in w[15:23] if g >= 0]
        cities.append((i, city_names[i], x, y, bits))
        rows.append([i, city_names[i], x, y, kind, link, name(city_names, link), u14, f"{ship_bits:08b}", zone,
                     region, nation, name(nation_names, nation), size, rate, special, name(goods_names, special),
                     u34, level, LEVELS[level] if 0 <= level < 8 else "",
                     " ".join(item_names[g] for g in more), w[23], name(conditions, w[23]),
                     f"{bits:016b}", " ".join(FACILITY_KINDS[k] for k in range(16) if bits >> k & 1), u62,
                     " ".join(disc_names[d] for d in disc if d >= 0), " ".join(map(str, matrix))])
    _csv(os.path.join(out, "tables", "cities.csv"),
         ["city", "name", "x", "y", "kind", "link", "linkName", "+0x14", "shipBits", "marketZone", "region",
          "nation", "nationName", "size", "rate", "specialty", "specialtyName", "+0x34", "level", "levelValue",
          "shopItems", "condition", "conditionName", "facilityBits", "facilities", "+0x62", "discoveries",
          "+0x74"], rows)

    rows = []
    for i, va in exe.records(GOODS):
        w = exe.words(va, 0x88 // 4)
        rows.append([i, goods_names[i], w[1], w[2], name(goods_kinds, w[2]), w[31], w[32], w[33], *w[3:31]])
    _csv(os.path.join(out, "tables", "goods.csv"),
         ["goods", "name", "picture", "category", "categoryName", "weight", "durability", "flag",
          *[f"price{z}" for z in range(28)]], rows)

    rows = []
    for z, va in exe.records(ZONES):
        g = exe.words(va, 5)
        members = [c[1] for c, va2 in zip(cities, [v for _, v in exe.records(CITIES)])
                   if exe.words(va2 + 0x1C, 1)[0] == z]
        rows.append([z, " ".join(name(goods_names, x) for x in g if x >= 0), " ".join(members)])
    _csv(os.path.join(out, "tables", "market_zones.csv"), ["zone", "goods", "cities"], rows)

    rows = []
    for i, va in exe.records(FACILITIES):
        p0, p1, city, kind, *rest = exe.words(va, 14)
        rows.append([i, exe.text(p0), exe.text(p1), city, name(city_names, city), kind,
                     name(FACILITY_KINDS, kind), *rest])
    _csv(os.path.join(out, "tables", "facilities.csv"),
         ["facility", "name", "genericName", "city", "cityName", "kind", "kindName", "link0", "link1", "link2",
          "link3", "x", "y", "w", "h", "+0x30", "+0x34"], rows)

    rows = []
    for i, va in exe.records(SHIPS):
        w = exe.words(va, 15)
        flags = exe.words(va + 0x3C, 1, "H")[0]
        rows.append([i, exe.text(w[0]), *w[1:14], w[14] * 1000, f"{flags:04x}"])
    _csv(os.path.join(out, "tables", "ships.csv"),
         ["ship", "name", "+4", "citySizeNeeded", "propulsion", "propulsionMax", "durability", "durabilityMax",
          "weight", "weightMax", "capacity", "capacityMax", "cannons?", "cannonsMax?", "+0x34", "price",
          "flags"], rows)

    item_kinds = exe.strings(ITEM_KINDS)
    texts = exe.words(ITEM_TEXTS, ITEMS[1], "I")
    rows = []
    for i, va in exe.records(ITEMS):
        p, pic, price, v2, power, kind, last = exe.words(va, 7)
        rows.append([i, exe.text(p), pic, price, v2, power, kind, name(item_kinds, kind), last,
                     exe.text(texts[i]).replace("\n", " ")])
    _csv(os.path.join(out, "items", "items.csv"),
         ["item", "name", "picture", "price", "+0xC", "power", "kind", "kindName", "+0x18", "description"], rows)

    disc_kinds = exe.strings(DISCOVERY_KINDS)
    rows = []
    for i, va in exe.records(DISCOVERIES):
        w = exe.words(va, 0x5C // 4)
        text = exe.text(exe.words(DISCOVERY_TEXTS + 4 * w[14], 1, "I")[0]) if w[14] >= 0 else ""
        rows.append([i, disc_names[i], w[1], name(disc_kinds, w[1]), w[2], w[3], w[4], w[5], w[6], w[12],
                     w[14], *w[17:21], w[21], w[22], " ".join(map(str, w[7:12])), w[13], w[15], w[16],
                     text.replace("\n", " ")])
    _csv(os.path.join(out, "discoveries", "discoveries.csv"),
         ["discovery", "name", "category", "categoryName", "code", "still", "+0x10", "+0x14", "reward", "+0x30",
          "text", "x1", "y1", "x2", "y2", "+0x54", "+0x58", "+0x1C..+0x2C", "+0x34", "+0x3C", "+0x40",
          "description"], rows)

    stars, bloods, jobs = exe.strings(STAR_SIGNS), exe.strings(BLOOD_TYPES), exe.strings(JOBS)
    va0, n, size = koei_games.KOUKAI3_WIN_PERSONS
    rows = []
    for i, (pname, face, sex) in enumerate(persons):
        w = exe.words(va0 + i * size, 0x60 // 4)
        nation, star, blood, job, fame, notoriety = w[5:11]
        rows.append([i, pname, nation, name(nation_names, nation), star, name(stars, star), blood,
                     name(bloods, blood), job, name(jobs, job), fame, notoriety, w[22], w[23]])
    _csv(os.path.join(out, "persons_extra.csv"),
         ["person", "name", "nation", "nationName", "starSign", "starSignName", "bloodType", "bloodTypeName",
          "job", "jobName", "fame", "notoriety", "+0x58", "+0x5C"], rows)

    return cities, {"nations": len(nation_names), "cities": len(cities), "goods": len(goods_names),
                    "zones": ZONES[1], "facilities": FACILITIES[1], "ships": SHIPS[1], "items": ITEMS[1],
                    "discoveries": len(disc_names), "persons": len(persons)}


def world_map(game_dir, out, cities):
    cells = load_world(game_dir)
    classes = [terrain(v) for v in cells]
    im = Image.new("RGB", (2500, 1250))
    im.putdata([COLOURS[c] for c in classes])
    os.makedirs(os.path.join(out, "map"), exist_ok=True)
    im.save(os.path.join(out, "map", "world.png"))
    d = ImageDraw.Draw(im)
    on_town = near_sea = ports = 0
    for _, _, x, y, bits in cities:
        on_town += classes[y * 2500 + x] == "town"
        port = bits & 1
        ports += port
        if port and any(classes[yy * 2500 + xx] == "sea" for yy in range(max(0, y - 3), min(1250, y + 4))
                        for xx in range(max(0, x - 3), min(2500, x + 4))):
            near_sea += 1
        c = (255, 255, 0) if port else (255, 255, 255)
        d.ellipse((x - 3, y - 3, x + 3, y + 3), outline=c, width=2)
    im.save(os.path.join(out, "map", "world_cities.png"))
    return on_town, ports, near_sea


def pictures(game_dir, out, sys_rgb):
    parts = ls11.ls11_decode_parts(open(os.path.join(game_dir, "ITEM.CDS"), "rb").read())
    folder = os.path.join(out, "items", "pictures")
    os.makedirs(folder, exist_ok=True)
    for n in range(len(parts) // 2):
        picture(parts[2 * n], 120, 120, palette(sys_rgb, parts[2 * n + 1], 160)).save(
            os.path.join(folder, f"{n:03d}.png"))
    items = len(parts) // 2
    parts = ls11.ls11_decode_parts(open(os.path.join(game_dir, "DSTILL.CDS"), "rb").read())
    folder = os.path.join(out, "discoveries", "stills")
    os.makedirs(folder, exist_ok=True)
    for n in range(len(parts) // 3):
        w, h = struct.unpack("<II", parts[3 * n + 2])
        picture(parts[3 * n], w, h, palette(sys_rgb, parts[3 * n + 1], 160)).save(
            os.path.join(folder, f"{n:03d}.png"))
    stills = len(parts) // 3
    parts = ls11.ls11_decode_parts(open(os.path.join(game_dir, "CITYCG.CDS"), "rb").read())
    folder = os.path.join(out, "towns")
    os.makedirs(folder, exist_ok=True)
    for n in range(len(parts) // 2):
        picture(parts[2 * n], 400, 320, palette(sys_rgb, parts[2 * n + 1], 74)).save(
            os.path.join(folder, f"{n:03d}.png"))
    return items, stills, len(parts) // 2


def _csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


@click.command("koukai3-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="games/koukai3-win")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/koukai3-win/extract)")
def koukai3_extras(game_dir, out):
    """大航海時代III: cities, nations, goods, facilities, ships, items, discoveries, persons, world map."""
    path = os.path.join(game_dir, EXE)
    exe = Exe(path)
    cities, counts = tables(exe, koei_games.load_koukai3_win_persons(path), out)
    print(", ".join(f"{k} {v}" for k, v in counts.items()))
    on_town, ports, near_sea = world_map(game_dir, out, cities)
    print(f"cities on a town cell: {on_town}/{len(cities)}; ports {ports}, within 3 cells of sea: {near_sea}")
    items, stills, towns = pictures(game_dir, out, koei_games.load_koukai3_win_face_palette(path))
    print(f"item pictures {items}, discovery stills {stills}, town pictures {towns}")


if __name__ == "__main__":
    koukai3_extras()
