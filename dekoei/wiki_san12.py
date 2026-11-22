"""三國志12 with PK (san12pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list.

The persons are the kaodata characters (kaodata_export.build_san12pk_win): the named records of PK/Scenario/Scenario0.dat
minus the 60 title slots (文官, 兵士, 山賊将…, faces SAN12PK_WIN_ROLE_FACES), 770 people, id = record id. Records are
292-byte bit fields read as one little-endian integer ("bit n"); field names follow the cp950 field-name list of the
繁中版 San12WPK.exe (0x1a57b2c–0x1a57c8c: 所屬勢力 基礎忠誠 位階 相性武將 軍團長 … 義兄 勇猛 死因 卒年 生年 登場年 性別
血緣 所在都市), evidence per field in notes/san12.md「koei-wiki 匯出：人物」. Names are the 繁中版's (Steam depot 628082,
san12_extras.bio_names), the Japanese ones go to nameJa.

The scenarios are the 17 of PK/Scenario (1–15, 20, 21; Scenario0 is the master copy, not playable); the PK set
contains the base game's scenarios, so there is no separate base list. Their number is the header byte +0 (= the
file number).

    persons(game_dir) -> [row]          (persons_export.py; reads ZH_DIR too)
    scenarios_csv(game_dir, path)       the 17 scenarios: number, file, titles, year, rulers
"""
import csv
import os
import struct

import sango
from kaodata_export import SAN12PK_WIN_ROLE_FACES, kana_to_hiragana
from places_export import PLACE_GAIJI, _gaiji, area_interior
import kaodata_export as K
from wiki_stats import _pick

SCENARIOS = [*range(1, 16), 20, 21]
MASTER = 0  # Scenario0: the values the stats export uses
SIZE = 292
ZH_DIR = os.path.join("..", "steam", "628080-tchinese", "depot")  # relative to game_dir
# part type ids (part 0 of the ILNK container lists them)
HEADER, FORCES, CORPS, CITIES, PERSONS = 0x95, 0x85, 0x87, 0x82, 0x92
NONE = 0x7FF
# person bit fields (offset, width)
FORCE, CITY = (1866, 6), (1873, 6)  # 63 = none
LOYALTY = (1824, 8)
SEX, BORN, DEBUT, DIED = (480, 1), (512, 10), (522, 10), (532, 10)
CLAN, FATHER, MOTHER = (1280, 11), (1292, 11), (1312, 11)
SPOUSES = [(1344, 11), (1376, 11), (1408, 11)]
SWORN = (1440, 11)  # the eldest brother; he points to himself
LIKED = [(b, 11) for b in (1472, 1504, 1536, 1568)]
DISLIKED = [(b, 11) for b in (1632, 1664, 1696, 1728)]
HIDDEN = {"相性": (1263, 8), "義理": (1813, 3)}
SKILLS = "商才 耕作 名士 兵心 練兵 収集 人脈 監視 補修 弁舌 豪傑 一騎 神速 水練 遠射 攻城 兵器 冷静 鬼謀 軍師".split()
UNITS = ["槍兵", "騎兵", "弓兵", "固有"]


def _bits(v, field):
    b, w = field
    return v >> b & ((1 << w) - 1)


def _parts(path):
    """{part type: decrypted bytes} of a Scenario*.dat"""
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"ILNK"
    n = struct.unpack_from("<I", d, 4)[0]
    offs = list(struct.unpack_from(f"<{n}I", d, 8)) + [len(d)]
    types = struct.unpack_from(f"<{n - 1}I", d, offs[0])
    return {t: sango.san12_decrypt(d[offs[i + 1]:offs[i + 2]]) for i, t in enumerate(types)}


def _records(part, size):
    return [int.from_bytes(part[k:k + size], "little") for k in range(0, len(part), size)]


def _scenario(game_dir, n):
    """year, title (ja), [person int], {force: ruler}, {corps leader}, {city governor}"""
    p = _parts(os.path.join(game_dir, "PK", "Scenario", f"Scenario{n}.dat"))
    h = p[HEADER]
    assert h[0] == n
    year = struct.unpack_from("<I", h, 0)[0] >> 12 & 0x3FF
    year = year - 0x400 if year & 0x200 else year  # 戦国七雄: 246 BC
    title = h[4:25].split(b"\0")[0].decode("cp932")
    rulers = {k: _bits(v, (14, 11)) for k, v in enumerate(_records(p[FORCES], 84)) if _bits(v, (14, 11)) != NONE}
    corps = {_bits(v, (7, 11)) for v in _records(p[CORPS], 800)} - {NONE}
    governors = {_bits(v, (967, 11)) for v in _records(p[CITIES], 248)} - {NONE}
    return year, title, _records(p[PERSONS], SIZE), rulers, corps, governors


def _zh_titles(game_dir):
    out = []
    for n in SCENARIOS:
        h = _parts(os.path.join(game_dir, ZH_DIR, "PK", "Scenario", f"Scenario{n}.dat"))[HEADER]
        out.append(h[4:25].split(b"\0")[0].decode("cp950"))
    return out


def _people(game_dir):
    """the kaodata characters: [(id, ja name, kana)]"""
    ja = sango.load_san12_persons(os.path.join(game_dir, "PK", "Scenario", f"Scenario{MASTER}.dat"), SIZE)
    return [p for p in ja if p["name"] and p["face"] not in SAN12PK_WIN_ROLE_FACES]


# 1410-1475: the 66 relatives (「〇〇の父」 and 橋玄 … 田嬰), only referenced as fathers or mothers. The 繁中版 names of
# these slots do not match the records (slot 1413 王允の父 is named 公孫瓚父 there, 1469 and 1472 lost the surname
# 吳國), so their Chinese names are built from the son's Chinese name like the 繁中版 writes them (韓玄之父, 公孫瓚父)
RELATIVES = range(1410, 1476)
RELATIVE_ZH = {"呉国太": "吳國太", "呉国": "吳國"}  # 呉国の父 is 呉国太's father


def _relative_names(zh, people):
    """zh with the RELATIVES slots renamed from the Japanese name: Xの父 / X父 -> 中文(X)之父 (2 characters) or 中文(X)父"""
    by_ja = {p["name"]: zh.get(p["id"], p["name"]) for p in people if p["id"] not in RELATIVES}
    by_ja.update(RELATIVE_ZH)
    out = dict(zh)
    for p in people:
        k, n = p["id"], p["name"]
        if k not in RELATIVES:
            continue
        if n.endswith("父") and n not in by_ja:
            x = n[:-2] if n.endswith("の父") else n[:-1]
            son = by_ja.get(x, x)  # 袁遺, 荀勗, 孫秀 … are not in the game; their names are the same in both scripts
            if not zh.get(k, "").startswith(son):  # 1466-1470 (陸凱父 …) are right in the 繁中版
                out[k] = son + ("之父" if len(son) == 2 else "父")
        else:
            out[k] = by_ja.get(n, n)
    return out


def persons(game_dir):
    import san12_extras
    people = _people(game_dir)
    zh = _relative_names(san12_extras.bio_names(os.path.join(game_dir, ZH_DIR)), people)
    ids = {p["id"] for p in people}
    master = _scenario(game_dir, MASTER)[2]
    data = [_scenario(game_dir, n) for n in SCENARIOS]
    raw = sango.san12_person_part(os.path.join(game_dir, "PK", "Scenario", f"Scenario{MASTER}.dat"), SIZE)

    def ref(v, field):
        x = _bits(v, field)
        return x if x in ids else None

    fathers = {k: ref(master[k], FATHER) for k in ids}
    mothers = {k: ref(master[k], MOTHER) for k in ids}
    eldest = {k: ref(master[k], SWORN) for k in ids}
    sworn = {}
    for k, e in eldest.items():
        if e is not None:
            sworn.setdefault(e, set()).add(k)

    rows = []
    for p in people:
        k, r = p["id"], master[p["id"]]
        b = raw[k * SIZE:(k + 1) * SIZE]
        row = {"id": k, "name": zh.get(k, p["name"])}
        if row["name"] != p["name"]:
            row["nameJa"] = p["name"]
        if p["kana"]:
            row["reading"] = kana_to_hiragana(p["kana"])
        born, died, debut = _bits(r, BORN), _bits(r, DIED), _bits(r, DEBUT)
        if born:
            row["born"], row["died"], row["debut"] = born, died, debut
        row["stats"] = dict(zip(sango.SAN12_STATS, b[68:72]))
        row["more"] = {"性別": "女" if _bits(r, SEX) else "男", "兵科": UNITS[b[0x48] & 3]}
        row["hidden"] = {label: _bits(r, f) for label, f in HIDDEN.items()}
        skills = [s for i, s in enumerate(SKILLS) if struct.unpack_from("<I", b, 0x4C + 4 * i)[0]]
        if skills:
            row["skills"] = {"特技": skills}
        notes = ["能力、特技、隱藏值與關係取 Scenario0（各劇本相同的母本）；姓名取繁中版，nameJa 是日文版。"]
        if not born:
            notes.append("沒有生年、登場年、沒年與能力（只當親屬引用的人）。")

        rel = {}
        if fathers[k] is not None:
            rel["father"] = [fathers[k]]
        if mothers[k] is not None:
            rel["mother"] = [mothers[k]]
        children = sorted(j for j in ids if fathers[j] == k or mothers[j] == k)
        if children:
            rel["children"] = children
        sib = sorted(j for j in ids if j != k and (fathers[k] is not None and fathers[j] == fathers[k]
                                                    or mothers[k] is not None and mothers[j] == mothers[k]))
        if sib:
            rel["siblings"] = sib
        spouses = [x for x in (ref(r, f) for f in SPOUSES) if x is not None]
        spouses += [j for j in ids if j not in spouses and k in (ref(master[j], f) for f in SPOUSES)]
        if spouses:
            rel["spouse"] = sorted(spouses)
        if eldest[k] is not None and len(sworn[eldest[k]]) > 1:
            rel["sworn"] = sorted(sworn[eldest[k]] - {k})
        if ref(r, CLAN) is not None:
            rel["clan"] = _bits(r, CLAN)
        if rel:
            row["relations"] = rel
        for label, fields in (("親愛武將", LIKED), ("厭惡武將", DISLIKED)):
            xs = [x for x in (ref(r, f) for f in fields) if x is not None]
            if xs:
                notes.append(f"{label}：{'、'.join(zh.get(x, x) for x in xs)}。")

        scen = []
        for n, (year, _, recs, rulers, corps, governors) in zip(SCENARIOS, data):
            x = recs[k]
            force, city = _bits(x, FORCE), _bits(x, CITY)
            if city == 63:
                continue  # not in this scenario (dead, or a person of another scenario)
            e = {"scenario": n, "year": year}
            if force != 63:
                lord = rulers[force]
                e["status"] = ("君主" if k == lord else "都督" if k in corps else "太守" if k in governors else "一般")
                e["lord"], e["location"] = lord, city
                if k != lord:
                    e["loyalty"] = _bits(x, LOYALTY)
            elif _bits(x, DEBUT) <= year:
                e["status"], e["location"] = "在野", city
            else:
                e["status"], e["debut"] = "未登場", _bits(x, DEBUT)
            scen.append(e)
        if scen:
            row["scenarios"] = scen
        row["uncertain"] = ["more.性別", "more.兵科", "skills.特技", "died", "debut",
                            *[f"hidden.{label}" for label in HIDDEN], "relations.mother", "relations.spouse",
                            "relations.sworn", "relations.clan", "relations.siblings",
                            "scenarios.status", "scenarios.location", "scenarios.loyalty"]
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def scenarios_csv(game_dir, path):
    import san12_extras
    zh = san12_extras.bio_names(os.path.join(game_dir, ZH_DIR))
    zh_titles = _zh_titles(game_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "name", "nameZh", "year", "rulers"])
        for n, zt in zip(SCENARIOS, zh_titles):
            year, title, _, rulers, _, _ = _scenario(game_dir, n)
            w.writerow([n, f"PK/Scenario/Scenario{n}.dat", title, zt, year,
                        "、".join(zh[rulers[k]] for k in sorted(rulers))])
    return len(SCENARIOS)


##############################################################################
# 三國志12 PK: PK/Scenario/Scenario0.dat part 6 (sango.san12_decrypt) holds the 40 cities (248 bytes: name +4,
# 地方 the low 4 bits of +0x18, six u32 neighbours from +0x1C). The battle number is the city number (RVA 0x3E600),
# but the maps are 3D terrain: no PNG.
SAN12_REGIONS = ["河北", "中原", "西北", "呉越", "荊楚", "巴蜀"]


# 全國地圖 (world/minimap.png): the strategic map is 3D; the only flat whole-country picture is the minimap base
# Data/UI/20_shoki/20_map_minimap_base.G1T of the 繁中版 depot (512 x 512 BGRA, China in the top-left 320 x 340, sea
# transparent, flattened here onto SAN12_SEA). Its 40 areas are split by 1 px lines about 15 % darker than their
# surroundings; SAN12_AREAS gives the city of each area in the order san12_areas finds them (top to bottom), assigned
# by geography and checked by world_check: every pair of adjacent cities has touching areas.
SAN12_DEPOT = os.path.join("..", "steam", "628080-tchinese", "depot")
SAN12_MINIMAP, SAN12_CROP, SAN12_SEA = "Data/UI/20_shoki/20_map_minimap_base.G1T", (320, 340), (40, 44, 90)
SAN12_AREAS = [0, 1, 2, 5, 17, 3, 4, 7, 6, 16, 14, 10, 8, 15, 11, 9, 35, 13, 12, 24, 36, 28, 18, 37, 25, 20, 21, 26, 38,
               34, 27, 19, 22, 29, 23, 30, 39, 31, 33, 32]


def san12_areas(game_dir):
    """(the cropped minimap on SAN12_SEA, a "P" image colouring each city's area with city + 1)."""
    from PIL import Image, ImageFilter
    import san12_extras
    with open(os.path.join(game_dir, SAN12_DEPOT, SAN12_MINIMAP), "rb") as f:
        im = san12_extras.gt1g(f.read()).crop((0, 0) + SAN12_CROP)
    w, h = im.size
    grey = im.convert("RGB").convert("L")
    g, m, a = grey.load(), grey.filter(ImageFilter.MaxFilter(5)).load(), im.getchannel("A").load()
    areas = Image.new("P", (w, h))
    lab = areas.load()
    seen, n = set(), 0
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or not (a[x, y] > 200 and g[x, y] >= 0.85 * m[x, y]):
                continue
            seen.add((x, y))
            stack, cells = [(x, y)], []
            while stack:
                p, q = stack.pop()
                cells.append((p, q))
                for u, v in ((p + 1, q), (p - 1, q), (p, q + 1), (p, q - 1)):
                    if 0 <= u < w and 0 <= v < h and (u, v) not in seen and a[u, v] > 200 and g[u, v] >= 0.85 * m[u, v]:
                        seen.add((u, v))
                        stack.append((u, v))
            if len(cells) >= 40:  # specks along the lines are left out
                for c in cells:
                    lab[c] = SAN12_AREAS[n] + 1
                n += 1
    assert n == 40
    flat = Image.new("RGBA", (w, h), SAN12_SEA + (255,))
    flat.alpha_composite(im)
    return flat.convert("RGB"), areas


def world_check(game_dir, rows):
    """Two adjacent cities have touching areas (within 3 px, across the line), and each pos is inside its area."""
    _, areas = san12_areas(game_dir)
    px, (w, h) = areas.load(), areas.size
    touch = set()
    for y in range(h):
        for x in range(w):
            if px[x, y]:
                for i in range(-3, 4):
                    for j in range(-3, 4):
                        if 0 <= x + i < w and 0 <= y + j < h and px[x + i, y + j] not in (0, px[x, y]):
                            touch.add((px[x, y] - 1, px[x + i, y + j] - 1))
    bad, checked = [], 0
    for r in rows:
        checked += 1
        if any(px[r["pos"]["x"] + i, r["pos"]["y"] + j] != r["id"] + 1 for i in range(-2, 3) for j in range(-2, 3)):
            bad.append(f"{r['id']}: pos not inside its area")
        for b in r["adjacent"]:
            checked += 1
            if (r["id"], b) not in touch:
                bad.append(f"{r['id']}-{b}: areas do not touch")
    return checked, bad


def places(game_dir, out_dir):
    with open(os.path.join(game_dir, "PK", "Scenario", "Scenario0.dat"), "rb") as f:
        d = f.read()
    n = struct.unpack_from("<I", d, 4)[0]
    offsets = list(struct.unpack_from(f"<{n}I", d, 8)) + [len(d)]
    city = sango.san12_decrypt(d[offsets[6]:offsets[7]])
    minimap, areas = san12_areas(game_dir)
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    minimap.save(os.path.join(out_dir, "world", "minimap.png"))
    pos = area_interior(areas, range(1, 41))
    rows = []
    for k in range(40):
        r = city[248 * k:][:248]
        rows.append({"id": k, "name": _gaiji(r[4:9].split(b"\0")[0].decode("cp932"), PLACE_GAIJI), "level": "都市",
                     "region": SAN12_REGIONS[struct.unpack_from("<I", r, 0x18)[0] & 0xF],
                     "adjacent": [x for x in struct.unpack_from("<6I", r, 0x1C) if x < 40],
                     "pos": {"x": pos[k + 1][0], "y": pos[k + 1][1], "grid": "pixel",
                             "w": SAN12_CROP[0], "h": SAN12_CROP[1]},
                     "notes": "戰場號＝都市號（San12WPK.exe RVA 0x3E600），戰場推定用守方都市的地形；地形是 3D，沒有輸出圖。"
                              "沒有関、港。pos 是小地圖 world/minimap.png（320×340）上這個都市的區塊裡離邊界最遠的點，"
                              "區塊和都市的對應是照地理排的，遊戲沒有都市在這張圖上的座標。"})
    return rows


def stats(game_dir):
    sce = os.path.join(game_dir, K.SAN12PK_WIN_SCENARIOS[0])
    chars = {p["id"]: p["name"] for p in sango.load_san12_persons(sce)
             if p["name"] and p["face"] not in K.SAN12PK_WIN_ROLE_FACES}
    return _pick(sango.load_san12_stats(sce), sango.SAN12_STATS, chars)
