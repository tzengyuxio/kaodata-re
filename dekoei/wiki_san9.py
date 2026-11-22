"""三國志IX with PK (san9pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list. The data is the 20
scenario files D_Sce001-020.S9 (RIFF S9SC); names are the Steam 繁中版's (depot 628052, san9_extras.zh_names), the
Japanese ones go to nameJa. Fields and evidence: notes/san9.md「koei-wiki 匯出：人物」, notes/san-attributes.md
「三國志IX」.

    ../.venv/bin/python wiki_san9.py --game-dir ../games/san9pk-win   # writes extract/tables/scenarios.csv

The people are the kaodata san9pk-win characters (records 0-699 minus the role records 693-699, one per (name,
face): a tribe's officers share a face and only the first is kept), id = record number.
"""
import csv
import os
import struct

import click

import san9_extras
import sango
from common import fold_kana, u16
import unicodedata
from places_export import PLACE_GAIJI, area_interior, label_world_map
import kaodata_export as K
from wiki_stats import _pick

# chunk prsn: 800 x 134 (records 0-699 used). +0 u32 flags (bit 0 female), +14 u16 face, +18 登場年, +20 生年 (u16,
# year - 130), +22 仕官 (year - 130, 0 none), +24 所在 (place id of the places export: city 0-49, bldg + 50),
# +26 軍団?, +28 身分 code (STATUS), +30 統率 武力 知力 政治 (u16 each), +38 忠誠 (0xFFFF none), +40 寿命,
# +44 血縁番号 (a person id), +46 親 (person id; 1000- are people not in the game), +48 相性, +50 義理, +52 野望,
# +54 性格, +56 9 x u16 兵法熟練, +78 50 x u8 勢力親密, +128 u32 兵法 bits. Field names: the person editor labels
# of M_MsgPK.s9 4878-4999 (登場年 生年 年齢 仕官 所属 所在 … 寿命 健康 血縁番号 親 子 相性 義理 野望 性格 …).
PRSN, SIZE, COUNT = b"prsn", 134, 700
YEAR0 = 130
# 身分 (+28): the help text (M_MsgPK.s9 8956) lists 君主、都督、軍師、一般、在野、捕虜; the scenarios use 0-3, 5-9.
# 0 君主 = the ruler of a forc record; 2 軍師 is one per force; 5 is people free in the scenario year (華歆, 許靖 in
# 184; 何儀, 管亥 in 190) = 在野; 7 debut after the scenario year = 未登場; 8 = 死亡 (most people in the late
# scenarios); 9 the emperors, hermits and role records (霊帝, 華佗, 左慈, 北斗…), never officers. 6 is people whose
# debut year has come but who are not placed; its name is not known (exported as 未登場, uncertain).
STATUS = {0: "君主", 1: "都督", 2: "軍師", 3: "一般", 5: "在野", 6: "未登場", 7: "未登場", 8: "死亡"}
# 性格 (+54): 猪突 剛胆 冷静 慎重 (the manual's order; 劉備 1 = 剛胆 matches the 本體 capture, one case)
TEMPERS = ["猪突", "剛胆", "冷静", "慎重"]
# 兵法 (+128 bit i), the screen's order (M_MsgPK.s9 4999-; ✅ capture of 関羽)
HEIHOU = ["奮戦", "奮闘", "奮迅", "突破", "突進", "突撃", "騎射", "走射", "飛射", "斉射", "連射", "連弩", "蒙衝", "楼船",
          "闘艦", "井闌", "衝車", "投石", "象兵", "造営", "石兵", "罠破", "教唆", "混乱", "罠", "心攻", "幻術", "罵声",
          "鼓舞", "治療", "妖術"]
SKILLED = ["歩兵", "騎兵", "弓騎", "弩兵", "水軍", "攻城", "知識", "謀略", "策略"]
# chunk forc: 50 x 86, +18 u16 ruler (person id, 0xFFFF none). chunk city: 50 x 56, +28 u16 owning force (0xFFFF
# none). chunk bldg: 200 x 28, +12 u16 force (🟡). chunk head: +20 u16 scenario number - 1 (+23 is 1 in 19, 20), +24 u16 date in days
# from 130 (360-day years: 21600 = 190).
FORCES, CITIES, BUILDINGS = (b"forc", 86, 50), (b"city", 56, 50), (b"bldg", 28, 200)


def _zh_dir(game_dir):
    return os.path.join(game_dir, "..", "steam", "628050-tchinese", "depot")


def _chunks(path):
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"RIFF" and d[8:12] == b"S9SC"
    out, o = {}, 12
    while o < len(d):
        n = struct.unpack_from("<I", d, o + 4)[0]
        out[d[o:o + 4]] = d[o + 8:o + 8 + n]
        o += 8 + n + (n & 1)
    return out


def _records(c, spec):
    tag, size, count = spec
    return [c[tag][size * k:size * (k + 1)] for k in range(count)]


def _titles(game_dir):
    """the 20 scenario titles (M_MsgPK.s9 entries 0, 2, 4…: title / description pairs)"""
    msg = san9_extras.entries(os.path.join(game_dir, "M_MsgPK.s9"))
    return [san9_extras.text(msg[2 * k]) for k in range(20)]


def scenarios(game_dir):
    """[(number, file, chunks, year, month)]"""
    out = []
    for n, name in enumerate(sango.SAN9_SCENARIOS, 1):
        c = _chunks(os.path.join(game_dir, name))
        assert u16(c[b"head"], 20) == n - 1
        days = u16(c[b"head"], 24)
        out.append((n, name, c, YEAR0 + days // 360, days % 360 // 30 + 1))
    return out


def _people(game_dir):
    """kaodata characters: id -> (Japanese name, kana)"""
    out, seen = {}, set()
    for p in sango.load_san9_persons(game_dir):
        if p["id"] in range(693, 700) or (p["name"], p["face"]) in seen:
            continue
        seen.add((p["name"], p["face"]))
        out[p["id"]] = (p["name"], p["kana"])
    return out


def _owner(c, place):
    """force owning a place id (city +28, bldg +12), or None"""
    if place < 50:
        f = u16(_records(c, CITIES)[place], 28)
    elif place < 250:
        f = u16(_records(c, BUILDINGS)[place - 50], 12)
    else:
        return None
    return None if f == 0xFFFF else f


def persons(game_dir):
    people = _people(game_dir)
    zh = san9_extras.zh_names(_zh_dir(game_dir))
    scens = scenarios(game_dir)
    main = scens[0][2]
    recs = _records(main, (PRSN, SIZE, COUNT))
    children = {}
    for i in people:
        parent = u16(recs[i], 46)
        if parent in people:
            children.setdefault(parent, []).append(i)
    rows = []
    for i, (ja, kana) in people.items():
        r = recs[i]
        stats = dict(zip(sango.SAN9_STATS, struct.unpack_from("<4H", r, 30)))
        row = {"id": i, "name": zh[i]}
        if zh[i] != ja:
            row["nameJa"] = ja
        row["reading"] = fold_kana(kana)
        row["born"] = YEAR0 + u16(r, 20)
        row["debut"] = YEAR0 + u16(r, 18)
        if any(stats.values()):
            row["stats"] = stats
        row["more"] = {"性別": "女" if r[0] & 1 else "男",
                       "性格": TEMPERS[r[54]] if r[54] < 4 else r[54],
                       **{f"{k}熟練": v for k, v in zip(SKILLED, struct.unpack_from("<9H", r, 56))}}
        row["hidden"] = {"寿命": r[40], "相性": u16(r, 48), "義理": r[50], "野望": r[52]}
        bits = struct.unpack_from("<I", r, 128)[0]
        heihou = [h for k, h in enumerate(HEIHOU) if bits >> k & 1]
        if heihou:
            row["skills"] = {"兵法": heihou}
        rel = {"clan": u16(r, 44)}
        parent = u16(r, 46)
        if parent in people:
            rel["father"] = [parent]
        if i in children:
            rel["children"] = sorted(children[i])
        row["relations"] = rel
        row["scenarios"] = []
        for n, _, c, year, _ in scens:
            sr = c[PRSN][SIZE * i:SIZE * (i + 1)]
            code, place = u16(sr, 28), u16(sr, 24)
            if code == 9:  # not an officer in any scenario
                continue
            e = {"scenario": n, "year": year, "status": STATUS.get(code, str(code))}
            if code in (0, 1, 2, 3):
                force = _owner(c, place)
                ruler = None if force is None else u16(_records(c, FORCES)[force], 18)
                if ruler in people:
                    e["lord"] = ruler
                if u16(sr, 38) != 0xFFFF:
                    e["loyalty"] = u16(sr, 38)
            if code not in (7, 8) and place < 250:
                e["location"] = place
            if code in (6, 7):
                e["debut"] = YEAR0 + u16(sr, 18)
            row["scenarios"].append(e)
        if not row["scenarios"]:
            del row["scenarios"]
        row["uncertain"] = ["more.性格", "more.性別", "hidden", "relations.father", "relations.children",
                            "relations.clan", "scenarios.lord", "scenarios.loyalty"]
        if any(e["status"] == "未登場" and e["debut"] <= e["year"] for e in row.get("scenarios", [])):
            row["uncertain"].append("scenarios.status")
        rows.append(row)
    return rows


@click.command()
@click.option("--game-dir", "game_dir", required=True)
def main(game_dir):
    """寫 <game-dir>/extract/tables/scenarios.csv（劇本號、檔名、標題、年月、各勢力的君主）"""
    people = {p["id"]: p["name"] for p in sango.load_san9_persons(game_dir)}
    titles = _titles(game_dir)
    out = os.path.join(game_dir, "extract", "tables", "scenarios.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "title", "year", "month", "rulers"])
        for n, name, c, year, month in scenarios(game_dir):
            rulers = [people[r] for r in (u16(f, 18) for f in _records(c, FORCES)) if r != 0xFFFF]
            w.writerow([n, name, titles[n - 1], year, month, " ".join(rulers)])
    print(out)


if __name__ == "__main__":
    main()


##############################################################################
# 三國志IX PK: names in M_MsgPK.s9 (LS11) part 0, items split by 05 05 05, (name, reading) pairs: 136-165 the 14
# 州 and 異民, 166-439 the 137 named places of the 200 bldg slots, 721-820 the 45 cities and 5 異民族; 959-975 the
# 17 facility kinds. D_Sce001.S9 (RIFF S9SC): `city` 50 x 56 bytes (+22 u16 州, +44/+46 x, y), `bldg` 200 x 28
# bytes (+6 u16 kind = fbld index, 0xFFFF a name only; +14 u16 city; +18/+20 x, y). No battle maps: battles are
# on the 200 x 200 map (`squa`).
# 全國地圖 (world/overview.png): G_MMap.s9 picture 168, the flat 576 x 512 stone-relief map of the strategic screen
# (palette guessed, san9_extras.WORLDMAP). Picture 166 colours each city's area on the same map with colour city + 1
# (1-50), as the isometric picture 162 does on the 200 x 200 grid; the game has no point for a city on the flat map.
SAN9_FLAT, SAN9_FLAT_AREAS, SAN9_ISO_AREAS = 168, 166, 162


def san9_world(game_dir):
    """(the flat map, its area index image, the isometric area index image), all "P" images."""
    from PIL import Image
    depot = os.path.join(game_dir, san9_extras.WORLDMAP_DEPOT)
    pals, pics = san9_extras.load_pictures(os.path.join(depot, "G_MMap.s9"))
    w, h, px = pics[SAN9_FLAT]
    flat = san9_extras.to_image(w, h, px, pals[san9_extras.pick_palette(w, h, px, pals)])
    areas = [Image.frombytes("P", pics[k][:2], bytes(pics[k][2])) for k in (SAN9_FLAT_AREAS, SAN9_ISO_AREAS)]
    return flat, areas[0], areas[1]


# The isometric land map (land/land-<season>.png, not in world/: its scale differs from pos): san9_extras.land's
# 12800 x 6430 render in the four seasons, reduced to an eighth. The ground piece of cell (x, y) is a 64 x 32 diamond
# centred at ((200 - y + x) * 32, (x + y) * 16 + 56 - 10 * height) on the render (D_Land00's corner formula, the flat
# ground mask's offset (32, 48) and the render's top edge at -30), height from the cell's layer-9 record.
SAN9_LAND_SCALE = 8


def san9_land(game_dir, out_dir, rows):
    """Writes land/land-<season>.png and land/land-labelled.png (spring, 2x, the 50 cities)."""
    from PIL import Image
    depot = os.path.join(game_dir, san9_extras.WORLDMAP_DEPOT)
    with open(os.path.join(depot, "D_Land00.s9"), "rb") as f:
        d = f.read()
    height = {}
    for i in range(struct.unpack_from("<I", d)[0]):
        r = d[8 + 13 * i:21 + 13 * i]
        if r[7] == 9:
            height[r[4], r[5]] = r[6]
    folder = os.path.join(out_dir, "land")
    os.makedirs(folder, exist_ok=True)
    for code, name in san9_extras.LAND_SEASONS:
        im = san9_extras.land(depot, code)
        im = im.resize((im.width // SAN9_LAND_SCALE, round(im.height / SAN9_LAND_SCALE)), Image.LANCZOS)
        path = os.path.join(folder, f"land-{name}.png")
        im.save(path)
        if name == "spring":
            spring = path
    cities = []
    for r in rows[:50]:
        x, y = r["game"]["座標"]["x"], r["game"]["座標"]["y"]
        cx, cy = (200 - y + x) * 32, (x + y) * 16 + 56 - 10 * height[x, y]
        cities.append({"id": r["id"], "name": r["name"],
                       "pos": {"x": round(cx / SAN9_LAND_SCALE), "y": round(cy / SAN9_LAND_SCALE)}})
    label_world_map(spring, cities, 4, scale=2).save(os.path.join(folder, "land-labelled.png"))


def world_check(game_dir, rows):
    """Each city's grid position (game.座標) falls in area city + 1 of the isometric area picture (cell (x, y) at
    pixel ((200 - y + x) * 2, x + y), D_Land00's corner formula / 16), each other place's in its parent city's area,
    and each city's pos lies inside its own area on the flat picture (at least 2 px from the edge)."""
    _, flat, iso = san9_world(game_dir)
    fp, ip = flat.load(), iso.load()
    bad, checked = [], 0
    for r in rows:
        g = r["game"]["座標"]
        city = r["id"] if r["id"] < 50 else r["parentCity"]
        checked += 1
        if ip[(200 - g["y"] + g["x"]) * 2, g["x"] + g["y"]] != city + 1:
            bad.append(f"{r['id']}: grid {g} not in area {city + 1}")
        if "pos" in r:
            x, y = r["pos"]["x"], r["pos"]["y"]
            checked += 1
            if any(fp[x + i, y + j] != r["id"] + 1 for i in range(-2, 3) for j in range(-2, 3)):
                bad.append(f"{r['id']}: pos not inside its area")
    return checked, bad


SAN9_KIND_LEVEL = {0: "都市", 1: "港", 2: "関", 3: "関", 4: "関"}  # fbld index -> level (2-4 are 3 grades of 関)


def places(game_dir, out_dir):
    import ls11
    with open(os.path.join(game_dir, "D_Sce001.S9"), "rb") as f:
        sce = f.read()

    def chunk(tag):
        i = sce.index(tag)
        return sce[i + 8:i + 8 + struct.unpack_from("<I", sce, i + 4)[0]]

    with open(os.path.join(game_dir, "M_MsgPK.s9"), "rb") as f:
        msg = ls11.ls11_decode_parts(f.read())[0].split(b"\x05\x05\x05")
    gaiji = {**sango.SAN9_GAIJI, **PLACE_GAIJI}

    def text(i):
        return "".join(gaiji.get(ord(c), c) for c in msg[i].decode("cp932")).strip()

    def reading(i):
        return unicodedata.normalize("NFKC", msg[i][2:-2].decode("cp932"))

    states = [text(136 + 2 * k) for k in range(15)]
    kinds = [text(959 + k) for k in range(17)]
    city, bldg = chunk(b"city"), chunk(b"bldg")
    flat, areas, _ = san9_world(game_dir)
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    flat.save(os.path.join(out_dir, "world", "overview.png"))
    centre = area_interior(areas, range(1, 51))
    rows = []
    for k in range(50):
        state, x, y = (struct.unpack_from("<H", city, 56 * k + o)[0] for o in (22, 44, 46))
        row = {"id": k, "name": text(721 + 2 * k), "reading": reading(722 + 2 * k),
               "level": "都市" if k < 45 else "異民族", "province": states[state],
               "pos": {"x": centre[k + 1][0], "y": centre[k + 1][1], "grid": "pixel", "w": 576, "h": 512},
               "game": {"座標": {"x": x, "y": y}},
               "notes": "沒有戰場圖，野戰、攻城都在 200 × 200 格的大地圖上打。沒有相鄰表。"
                        "game.座標是 200 × 200 格大地圖上的格子；pos 是平面全國圖 world/overview.png（576×512）上"
                        "這個都市的區域（G_MMap.s9 第 166 張，色號＝都市號＋1）裡離邊界最遠的點，遊戲沒有都市在這張圖上的座標。"}
        if k >= 45:
            row["uncertain"] = ["level"]
            row["notes"] += "「異民族」是這邊的稱呼（州表裡寫「異民」）。"
        rows.append(row)
    for k in range(137):
        kind, parent, x, y = (struct.unpack_from("<H", bldg, 28 * k + o)[0] for o in (6, 14, 18, 20))
        row = {"id": 50 + k, "name": text(166 + 2 * k), "reading": reading(167 + 2 * k),
               "level": SAN9_KIND_LEVEL.get(kind, kinds[kind] if kind < 17 else "地名"), "parentCity": parent,
               "game": {"座標": {"x": x, "y": y}},
               "notes": "號碼是 bldg 區塊的序號＋50。所屬都市是 bldg +14。game.座標是 200 × 200 格大地圖上的格子。"}
        if kind == 0xFFFF:
            row["uncertain"] = ["level"]
            row["notes"] += "這一筆只有地名、沒有設施，「地名」是這邊的分類。"
        rows.append(row)
    san9_land(game_dir, out_dir, rows)
    return rows


def stats(game_dir):
    # the builder's characters: persons minus roles 693-699, deduplicated by (name, face)
    chars, seen = {}, set()
    for p in sango.load_san9_persons(game_dir):
        if p["id"] in K.SAN9PK_WIN_ROLES or (p["name"], p["face"]) in seen:
            continue
        seen.add((p["name"], p["face"]))
        chars[p["id"]] = p["name"]
    rows = [r[1:] for r in sango.load_san9_stats(game_dir) if r[0] == sango.SAN9_SCENARIOS[0]]
    return _pick(rows, sango.SAN9_STATS, chars)
