"""成吉思汗 蒼狼與白鹿IV 威力加強版 (Win 中文版): the four scenarios (regions, countries, cities, 特產品, 文化寶物,
兵種, persons), the 列傳, the small world maps with the cities, item / product / event pictures.

See notes/genghis4.md. Usage (from dekoei/):
    dekoei.py genghis4-extras --game-dir ../games/genghis4pk-win --out ../games/genghis4pk-win/extract
"""
import csv
import os
import struct

import click
from PIL import Image, ImageDraw, ImageFont

# Counts per scenario 1-4, hard-coded in CKW95.EXE (countries 0x491630, cities 0x4916A0, men 0x491710,
# women 0x491790). The country record holds one relation per country, so its size depends on the scenario.
COUNTRIES = {1: 30, 2: 27, 3: 25, 4: 29}
CITIES = {1: 42, 2: 41, 3: 38, 4: 37}
MEN = {1: 204, 2: 149, 3: 145, 4: 126}
WOMEN = {1: 31, 2: 27, 3: 25, 4: 29}
REGIONS, PRODUCTS, TREASURES, UNITS = 56, 31, 80, 24
NONE_PERSON = 500  # person references are indexes into the scenario's men list; 500 = nobody
NONE_CITY = 80     # the person has not appeared yet
APTITUDES = ["步兵", "弓兵", "騎兵", "水軍"]  # MESSAGE.CK 6342 tests aptitude 0-3 = 步兵 箭術 騎兵 海戰
SKILLS = ["農業", "商業", "建設", "文化", "外交", "錄用", "機動", "突擊", "連射", "火攻", "攻城", "伏兵"]  # 🟡 order
STATUS = {1: "未登場", 2: "將軍", 3: "在野", 4: "君主", 5: "未登場（子女）", 6: "將軍（6）"}  # +44 bits 0-2, 🟡
# MESSAGE.CK section table in CKW95.EXE (VA 0x5DC798): message id = section * 1000 + index
MSG_TABLE_VA, DATA_VA, DATA_OFF = 0x5DC798, 0x5D5000, 0x1D3800


def _s(raw: bytes) -> str:
    return raw.split(b"\0")[0].decode("big5", "replace").rstrip()


def _write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _read(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return f.read()


def load_scenario(game_dir, k):
    """SCEDATk.CK in the order CKW95.EXE 0x494400 reads it (each section's reader is named below)."""
    d = _read(game_dir, f"SCEDAT{k}.CK")
    sc = {"year": struct.unpack_from("<H", d, 0)[0], "title": _s(d[2:0x13]), "intro": _s(d[0x13:0x207])}
    o = 0x207
    sc["regions"] = []  # 0x494CD0: u8 id, 15 name, u8 kind, u8 culture, u8 c
    for _ in range(REGIONS):
        sc["regions"].append({"id": d[o], "name": _s(d[o + 1:o + 16]), "kind": d[o + 16], "culture": d[o + 17],
                              "c": d[o + 18]})
        o += 19
    n = COUNTRIES[k]
    sc["countries"] = []  # 0x494F30: 19 name, u8 id, u16 ruler, n x u16 relations
    for _ in range(n):
        sc["countries"].append({"name": _s(d[o:o + 19]), "id": d[o + 19], "ruler": struct.unpack_from("<H", d, o + 20)[0],
                                "relations": list(struct.unpack_from(f"<{n}H", d, o + 22))})
        o += 22 + 2 * n
    sc["cities"] = []  # 0x495450: 21 name, u8 id, u8 owner, u8 size, 5 x u16, u16 x, u16 y, u8 culture, 10, 8, 4
    for _ in range(CITIES[k]):
        r = d[o:o + 61]
        x, y = struct.unpack_from("<2H", r, 34)
        sc["cities"].append({"name": _s(r[:21]), "id": r[21], "owner": r[22], "size": r[23],
                             "values": struct.unpack_from("<5H", r, 24), "x": x, "y": y, "culture": r[38],
                             "levels": list(r[39:49]), "treasures": [t for t in r[49:57] if t != TREASURES],
                             "flags": struct.unpack_from("<I", r, 57)[0]})
        o += 61
    sc["products"] = []  # 0x4955C0: 11 name, u8, u8, u8, 7 bytes
    for _ in range(PRODUCTS):
        r = d[o:o + 21]
        sc["products"].append({"name": _s(r[:11]), "a": r[11], "b": r[12], "c": r[13], "x": list(r[14:21])})
        o += 21
    sc["treasures"] = []  # 0x495680: u8 id, 23 name, u8 category, u8
    for _ in range(TREASURES):
        r = d[o:o + 26]
        sc["treasures"].append({"id": r[0], "name": _s(r[1:24]), "category": r[24], "b": r[25]})
        o += 26
    sc["units"] = []  # 0x495730: 13 name, 5 x u8
    for _ in range(UNITS):
        r = d[o:o + 18]
        sc["units"].append({"name": _s(r[:13]), "x": list(r[13:18])})
        o += 18
    sc["men"] = []  # 0x495C90 + 0x495E10, 51 bytes
    for _ in range(MEN[k]):
        (pid, name, region, city, father, grandfather, born, served, affinity, pol, war, intel, loyal, merit, a0, a1, a2,
         a3, skills, mark, status, face, appear_year, appear_city) = struct.unpack_from("<H17sBBHHHHHBBBBB4BHHHHHB", d, o)
        sc["men"].append({"id": pid, "name": _s(name), "region": region, "city": city, "father": father,
                          "grandfather": grandfather, "born": born, "served": served, "affinity": affinity, "pol": pol,
                          "war": war, "int": intel, "loyalty": loyal, "merit": merit, "apt": [a0, a1, a2, a3],
                          "skills": skills, "mark": mark, "status": status, "face": face, "appear_year": appear_year,
                          "appear_city": appear_city})
        o += 51
    sc["women"] = []  # 0x495F10: u8 id, 17 name, u8 region, u16 husband, u8 文化傾向 🟡, u8 (always 2), u8 face
    for _ in range(WOMEN[k]):
        r = d[o:o + 24]
        sc["women"].append({"id": r[0], "name": _s(r[1:18]), "region": r[18], "husband": struct.unpack_from("<H", r, 19)[0],
                            "culture": r[21], "x22": r[22], "face": r[23]})
        o += 24
    assert o == len(d), (k, o, len(d))
    return sc


def load_messages(game_dir):
    """MESSAGE.CK: {section * 1000 + index: raw bytes}. A section is u16 count, count x u16 offsets from its start."""
    exe, d = _read(game_dir, "CKW95.EXE"), _read(game_dir, "MESSAGE.CK")
    starts = list(struct.unpack_from("<12I", exe, MSG_TABLE_VA - DATA_VA + DATA_OFF)) + [len(d)]
    out = {}
    for sec in range(12):
        s = starts[sec]
        n = struct.unpack_from("<H", d, s)[0]
        offs = list(struct.unpack_from(f"<{n}H", d, s + 2)) + [starts[sec + 1] - s]
        for i in range(n):
            out[sec * 1000 + i] = d[s + offs[i]:s + offs[i + 1]]
    return out


def _text(raw: bytes) -> str:
    return raw.split(b"\x05")[0].decode("big5", "replace").strip()


def bio_id(pid: int) -> int:
    """CKW95.EXE 0x462B60: men below 338 have their 列傳 at 6000 + id, the rest at 8000 + id - 338."""
    return 6000 + pid if pid < 0x152 else pid + 0x1DEE


def biographies(msgs, scenarios, out):
    ids = sorted({m["id"] for sc in scenarios.values() for m in sc["men"]})
    rows = []
    for pid in range(max(ids) + 1):
        head = _text(msgs[7000 + pid])  # 0x46496A: "name born∼died"
        name, _, years = head.rpartition(" ")
        born, _, died = years.partition("∼")
        rows.append([pid, name, born, died, "yes" if pid in ids else "", _text(msgs[bio_id(pid)])])
    _write_csv(os.path.join(out, "biographies.csv"), ["id", "name", "born", "died", "has_record", "text"], rows)
    return len(rows)


def tables(scenarios, out):
    s1 = scenarios[1]
    _write_csv(os.path.join(out, "scenarios.csv"), ["scenario", "year", "title", "intro"],
               [[k, sc["year"], sc["title"], sc["intro"]] for k, sc in scenarios.items()])
    _write_csv(os.path.join(out, "regions.csv"), ["id", "name", "kind", "culture", "c"],
               [[r["id"], r["name"], r["kind"], r["culture"], r["c"]] for r in s1["regions"]])
    _write_csv(os.path.join(out, "products.csv"), ["index", "name", "a", "b", "c", "x"],
               [[i, p["name"], p["a"], p["b"], p["c"], " ".join(map(str, p["x"]))]
                for i, p in enumerate(s1["products"])])
    treasures = {}
    for k, sc in scenarios.items():
        for t in sc["treasures"]:
            treasures.setdefault(t["id"], [t["name"], t["category"], {}])[2][k] = t["b"]
    _write_csv(os.path.join(out, "treasures.csv"), ["id", "name", "category", "b_s1", "b_s2", "b_s3", "b_s4"],
               [[i, n, c, *[b.get(k, "") for k in range(1, 5)]] for i, (n, c, b) in sorted(treasures.items())])
    rows, crows, rel, cit, men, women = [], [], [], [], [], []
    for k, sc in scenarios.items():
        names = [m["name"] for m in sc["men"]]  # rulers, fathers, husbands... are indexes into the men list
        cities = [c["name"] for c in sc["cities"]]
        countries = [c["name"] for c in sc["countries"]]
        tnames = {t["id"]: t["name"] for t in sc["treasures"]}
        rows += [[k, i, *u["x"], u["name"]] for i, u in enumerate(sc["units"])]

        def who(i):  # 500 = nobody; 501-512 a parent without a record, shared by brothers
            return names[i] if i < len(names) else "" if i == NONE_PERSON else f"({i})"

        for i, c in enumerate(sc["countries"]):
            crows.append([k, i, c["id"], c["name"], c["ruler"], who(c["ruler"])])
            rel += [[k, c["name"], countries[j], v] for j, v in enumerate(c["relations"]) if j > i and v != 7]
        for i, c in enumerate(sc["cities"]):
            cit.append([k, i, c["id"], c["name"], countries[c["owner"]] if c["owner"] < len(countries) else c["owner"],
                        c["size"], *c["values"], c["x"], c["y"], c["culture"], " ".join(map(str, c["levels"])),
                        " ".join(tnames.get(t, str(t)) for t in c["treasures"]), f"{c['flags']:08x}"])

        for i, m in enumerate(sc["men"]):
            men.append([k, i, m["id"], m["name"], s1["regions"][m["region"]]["name"],
                        cities[m["city"]] if m["city"] < len(cities) else "", who(m["father"]), who(m["grandfather"]),
                        m["born"], m["served"], who(m["affinity"]), m["pol"], m["war"], m["int"], m["loyalty"], m["merit"],
                        *m["apt"], " ".join(s for b, s in enumerate(SKILLS) if m["skills"] >> b & 1),
                        f"{m['skills']:04x}", STATUS.get(m["status"] & 7, m["status"] & 7), m["status"] >> 3 & 15,
                        m["status"] >> 7 & 7, m["face"], m["appear_year"] or "",
                        cities[m["appear_city"]] if m["appear_city"] < len(cities) else ""])
        for w in sc["women"]:
            women.append([k, w["id"], w["name"], s1["regions"][w["region"]]["name"], who(w["husband"]), w["culture"],
                          w["x22"], w["face"]])
    _write_csv(os.path.join(out, "units.csv"), ["scenario", "index", "class", "a", "b", "c", "d", "name"], rows)
    _write_csv(os.path.join(out, "countries.csv"), ["scenario", "index", "id", "name", "ruler_id", "ruler"], crows)
    _write_csv(os.path.join(out, "relations.csv"), ["scenario", "a", "b", "value"], rel)
    _write_csv(os.path.join(out, "cities.csv"),
               ["scenario", "index", "id", "name", "owner", "size", "v0", "v1", "v2", "v3", "v4", "x", "y", "culture",
                "levels", "treasures", "flags"], cit)
    _write_csv(os.path.join(out, "persons.csv"),
               ["scenario", "index", "id", "name", "region", "city", "father", "grandfather", "born", "served", "affinity", "政治",
                "戰鬥", "智謀", "忠誠", "merit", *APTITUDES, "skills", "skills_hex", "status", "status_b3", "status_b7",
                "face", "appear_year", "appear_city"], men)
    _write_csv(os.path.join(out, "women.csv"),
               ["scenario", "id", "name", "region", "husband", "culture", "x22", "face"], women)
    return len(crows), len(cit), len(men), len(women)


def _grid(game_dir, name, cell, names, out):
    """Cut a picture sheet into cell x cell pictures named by index (and name)."""
    im = Image.open(os.path.join(game_dir, name)).convert("RGB")
    os.makedirs(out, exist_ok=True)
    cols = im.width // cell
    for i, n in names.items():
        x, y = i % cols * cell, i // cols * cell
        im.crop((x, y, x + cell, y + cell)).save(os.path.join(out, f"{i:03d}_{n}.png"))
    return len(names)


def pictures(game_dir, scenarios, out):
    s1 = scenarios[1]
    treasures = {t["id"]: t["name"] for sc in scenarios.values() for t in sc["treasures"]}
    n = _grid(game_dir, "ITEMSPUK.bmp", 80, treasures, os.path.join(out, "items", "treasures"))
    p = _grid(game_dir, "PRODUCTS.BMP", 80, {i: x["name"] for i, x in enumerate(s1["products"])},
              os.path.join(out, "items", "products"))
    os.makedirs(os.path.join(out, "eventcg"), exist_ok=True)
    ev = Image.open(os.path.join(game_dir, "EVENTS.BMP")).convert("RGB")
    for i in range(5):  # 2 x 3 cells of 280 x 160, the last one empty
        x, y = i % 2 * 280, i // 2 * 160
        ev.crop((x, y, x + 280, y + 160)).save(os.path.join(out, "eventcg", f"event{i}.png"))
    os.makedirs(os.path.join(out, "ui"), exist_ok=True)
    for name in ["CHRONICL.bmp", "CK.BMP", "KOEI.BMP", "TWP.BMP"]:  # 年表 parchment, title and logo screens
        Image.open(os.path.join(game_dir, name)).save(os.path.join(out, "ui", name.split(".")[0].lower() + ".png"))
    return n, p


def world_maps(game_dir, scenarios, out):
    """The small world maps, and MIDMAP x2 with each scenario's cities: (x, y) of a city is a cell of the
    250 x 226 map grid, drawn at (4 + 2x, 4 + y) on the 508 x 233 maps (🟡, matched by eye)."""
    os.makedirs(os.path.join(out, "map"), exist_ok=True)
    for name in ["MIDMAP.BMP", "BLANKMAP.BMP", "AREAMAP.BMP", "MASKMAP.BMP", "SMALLMAP.BMP"]:
        Image.open(os.path.join(game_dir, name)).save(os.path.join(out, "map", name.split(".")[0].lower() + ".png"))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 13)
    except OSError:
        font = ImageFont.load_default()
    base = Image.open(os.path.join(game_dir, "MIDMAP.BMP")).convert("RGB")
    for k, sc in scenarios.items():
        im = base.resize((base.width * 3, base.height * 3), Image.NEAREST)
        dr = ImageDraw.Draw(im)
        for i, c in enumerate(sc["cities"]):
            x, y = (4 + 2 * c["x"]) * 3, (4 + c["y"]) * 3
            dr.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 0, 0), outline=(0, 0, 0))
            dr.text((x + 6, y - 7), f"{i} {c['name']}", font=font, fill=(255, 255, 255), stroke_width=2,
                    stroke_fill=(0, 0, 0))
        im.save(os.path.join(out, "map", f"cities_s{k}.png"))
    return len(scenarios)


@click.command()
@click.option("--game-dir", required=True, help="games/genghis4pk-win")
@click.option("--out", required=True, help="output directory, e.g. games/genghis4pk-win/extract")
def genghis4_extras(game_dir, out):
    """成吉思汗IV PK (Win 中文版): scenario tables, persons, 列傳, maps, item and event pictures."""
    scenarios = {k: load_scenario(game_dir, k) for k in range(1, 5)}
    msgs = load_messages(game_dir)
    c, t, m, w = tables(scenarios, out)
    b = biographies(msgs, scenarios, out)
    n, p = pictures(game_dir, scenarios, out)
    world_maps(game_dir, scenarios, out)
    print(f"4 scenarios: {c} countries, {t} cities, {m} men, {w} women; {b} 列傳; {n} 文化寶物 + {p} 特產品 "
          f"pictures, 5 event pictures, 4 city maps")


if __name__ == "__main__":
    genghis4_extras()
