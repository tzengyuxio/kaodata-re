"""三國志11 with PK (san11pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list. The data is the 14
scenario files Scen000-013.s11 (plain cp932); names and 字 are the Steam 繁中版's (depot 628072: the same records
from 17760 instead of 0x3BCD, cp950 + the 三國志IX gaiji), the Japanese ones go to nameJa. Fields and evidence:
notes/san11.md「koei-wiki 匯出：人物」, notes/san-attributes.md「三國志11」.

    ../.venv/bin/python wiki_san11.py --game-dir ../games/san11pk-win   # writes extract/tables/scenarios.csv

The people are the kaodata san11pk-win characters: records 0-849 minus the empty slots and the townsfolk roles
(kaodata_export.SAN11PK_WIN_EMPTY / _ROLES), id = record number.
"""
import csv
import os

import click

import sango
from kaodata_export import SAN11PK_WIN_EMPTY, SAN11PK_WIN_ROLES, SAN11PK_WIN_SCENARIOS, kana_to_hiragana
from san9_extras import zh_text
from common import read_file, u16
import struct

from PIL import Image
from places_export import _gaiji
import kaodata_export as K
from wiki_stats import _pick

START, SIZE, COUNT = sango.SAN11_PERSONS
ZH_START = 17760
# person record (152 bytes): +0 姓 5, +5 名 5, +10 字 5, +15 読み 25, +0x35 u16 face, +0x37 性別 (0 男, 1 女, FF
# empty), +0x38 登場年, +0x3A 生年, +0x3C 没年 (u16), +0x3E 死因, +0x3F u16 血縁 (the clan head's id), +0x41 u16
# 父親, +0x43 u16 母親 (2000- are people not in the game), +0x45 世代, +0x46 u16 配偶者, +0x48 u16 義兄 (the
# eldest of the sworn brothers; himself for the eldest), +0x4A 相性 (0-149), +0x4B 5 x u16 親愛武将, +0x55 5 x u16
# 嫌悪武将, +0x5F 軍団 (row of the 軍団 table, FF none), +0x60 u16 所在 (place id of the places export: city 0-41,
# 関/港 42-86; FFFF none), +0x64 身分 (STATUS), +0x68 忠誠 (FF none), +0x69 u16 功績, +0x6B 適性 x 6 (0-3 = C-S, stored
# 槍 戟 弩 騎 兵器 水軍), +0x71 統率 武力 知力 政治 魅力, +0x7C 特技 (Scenario.s11 skill table row), +0x7E 義理,
# +0x7F 野望, +0x80 起用, +0x81 性格, +0x84 漢室, +0x85 戦略傾向. Field names: the EXE's editor labels (性別 登場年
# 出生年 血緣 父親 母親 世代 配偶 義兄 相性 …, 繁中 San11WPK.exe 0x3ECA60).
APTITUDE = ["槍兵", "戟兵", "弩兵", "騎兵", "兵器", "水軍"]
GRADES = "CBAS"
# 身分 (+0x64): 0 the one ruler of each force; 1 the 軍団 commanders (= the commander of their 軍団 row); 3 the
# officers; 4 people in a city with no 軍団 (in 184: 袁胤, 区星, 厳白虎, 公孫度, 張魯 …); 6 debut after the scenario
# year; 7 debut year reached, no 軍団 (王朗, 賈詡 in 184; 郭嘉, 伊籍 in 190), named after the game's 未発見; 8 死亡;
# FF not in the scenario. 2 and 5 (太守?, 捕虜?) are not used by any scenario.
STATUS = {0: "君主", 1: "都督", 3: "一般", 4: "在野", 6: "未登場", 7: "未発見", 8: "死亡"}
TEMPERS = ["小心", "冷静", "剛胆", "猪突"]  # +0x81, the EXE's list order
DEATHS = ["自然死", "不自然死"]  # +0x3E (関羽, 孫策, 呂布 1; 曹操, 諸葛亮 0)
# 軍団 table: 0x257F9, 47 rows of 8 bytes: +0 force, +1 number in the force (1 = the ruler's own), +2 u16 commander;
# rows 42-46 are the tribes (羌, 山越, 烏丸, 南蛮, 賊), which are no force
ARMIES, ARMY_SIZE, ARMY_COUNT, TRIBES = 0x257F9, 8, 47, range(42, 47)
SKILLS = 0x5210, 93  # Scenario.s11 特技 table: +0 name 5


def _zh_dir(game_dir):
    return os.path.join(game_dir, "..", "steam", "628070-tchinese", "depot", "media", "scenario")


def scenarios(game_dir):
    """[(number, file, data, year, month, title)]"""
    out = []
    for n, name in enumerate(SAN11PK_WIN_SCENARIOS, 1):
        d = read_file(os.path.join(game_dir, name))
        out.append((n, name, d, u16(d, 0x5B), d[0x5D], d[0x5F:0x70].split(b"\0")[0].decode("cp932")))
    return out


def _record(d, i):
    return d[START + SIZE * i:START + SIZE * (i + 1)]


def _rulers(d):
    """軍団 row -> ruler of its force (the 身分 0 person whose 軍団 is in that force)"""
    force = {k: d[ARMIES + ARMY_SIZE * k] for k in range(ARMY_COUNT)}
    ruler = {}
    for i in range(COUNT):
        r = _record(d, i)
        if r[0x64] == 0:
            assert force[r[0x5F]] not in ruler, i
            ruler[force[r[0x5F]]] = i
    return {k: ruler.get(f) for k, f in force.items() if k not in TRIBES}


def _skills(game_dir):
    d = read_file(os.path.join(game_dir, "Scenario.s11"))
    start, size = SKILLS
    return [d[start + size * k:][:5].split(b"\0")[0].decode("cp932") for k in range(100)]


def persons(game_dir):
    empty = {i for r in SAN11PK_WIN_EMPTY for i in r} | set(SAN11PK_WIN_ROLES)
    scens = scenarios(game_dir)
    main = scens[0][2]
    ja = {p["id"]: p for p in sango.load_san11_persons(os.path.join(game_dir, SAN11PK_WIN_SCENARIOS[0]))}
    people = [i for i in range(COUNT) if i not in empty]
    assert all(ja[i]["sex"] in (0, 1) for i in people)
    ids = set(people)
    zh = read_file(os.path.join(_zh_dir(game_dir), "SCEN000.s11"))
    skills = _skills(game_dir)
    rulers = [(n, d, year, _rulers(d)) for n, _, d, year, _, _ in scens]
    sworn, children = {}, {}
    for i in people:
        r = _record(main, i)
        if u16(r, 0x48) in ids:
            sworn.setdefault(u16(r, 0x48), []).append(i)
        for o in (0x41, 0x43):
            if u16(r, o) in ids:
                children.setdefault(u16(r, o), []).append(i)
    rows = []
    for i in people:
        r, z, p = _record(main, i), zh[ZH_START + SIZE * i:ZH_START + SIZE * (i + 1)], ja[i]
        name = zh_text(z[0:5].split(b"\0")[0]) + zh_text(z[5:10].split(b"\0")[0])
        row = {"id": i, "name": name}
        surname, given = zh_text(z[0:5].split(b"\0")[0]), zh_text(z[5:10].split(b"\0")[0])
        if surname and given:  # 姓 and 名 are separate fields; the reading is one field, so no familyReading
            row["familyName"] = surname
        if name != p["name"]:
            row["nameJa"] = p["name"]
        courtesy = zh_text(z[10:15].split(b"\0")[0])
        if courtesy:
            row["courtesy"] = courtesy
        row["reading"] = kana_to_hiragana(p["kana"])
        row["born"], row["died"], row["debut"] = u16(r, 0x3A), u16(r, 0x3C), u16(r, 0x38)
        row["stats"] = dict(zip(sango.SAN11_STATS, r[0x71:0x76]))
        row["more"] = {"性別": "女" if r[0x37] else "男"}
        row["hidden"] = {"相性": r[0x4A], "死因": DEATHS[r[0x3E]] if r[0x3E] < 2 else r[0x3E], "義理": r[0x7E],
                         "野望": r[0x7F], "起用": r[0x80], "性格": TEMPERS[r[0x81]] if r[0x81] < 4 else r[0x81],
                         "漢室": r[0x84], "戦略傾向": r[0x85], "世代": r[0x45]}
        row["aptitude"] = {a: GRADES[v] for a, v in zip(APTITUDE, r[0x6B:0x71])}
        if r[0x7C] < len(skills) and skills[r[0x7C]]:
            row["skills"] = {"特技": [skills[r[0x7C]]]}
        rel = {}
        for key, o in (("father", 0x41), ("mother", 0x43), ("spouse", 0x46)):
            if u16(r, o) in ids:
                rel[key] = [u16(r, o)]
        if i in children:
            rel["children"] = sorted(children[i])
        group = sworn.get(u16(r, 0x48), [])
        if len(group) > 1:
            rel["sworn"] = sorted(x for x in group if x != i)
        if u16(r, 0x3F) in ids:
            rel["clan"] = u16(r, 0x3F)
        if rel:
            row["relations"] = rel
        game = {}
        liked = [u16(r, 0x4B + 2 * k) for k in range(5)]
        hated = [u16(r, 0x55 + 2 * k) for k in range(5)]
        if any(x in ids for x in liked):
            game["親愛武将"] = [x for x in liked if x in ids]
        if any(x in ids for x in hated):
            game["嫌悪武将"] = [x for x in hated if x in ids]
        if game:
            row["game"] = game
        row["scenarios"] = []
        for n, d, year, ruler in rulers:
            s = _record(d, i)
            code, army, place = s[0x64], s[0x5F], u16(s, 0x60)
            if code == 0xFF:
                continue
            e = {"scenario": n, "year": year, "status": STATUS.get(code, str(code))}
            if code in (0, 1, 3) and ruler.get(army) in ids:
                e["lord"] = ruler[army]
            if code in (1, 3) and s[0x68] != 0xFF:
                e["loyalty"] = s[0x68]
            if code not in (6, 8) and place < 87:
                e["location"] = place
            if code in (6, 7):
                e["debut"] = u16(s, 0x38)
            row["scenarios"].append(e)
        if not row["scenarios"]:
            del row["scenarios"]
        row["uncertain"] = ["debut", "hidden", "relations.father", "relations.mother", "relations.children",
                            "scenarios.loyalty"]
        if any(e["status"] == "未発見" for e in row.get("scenarios", [])):
            row["uncertain"].append("scenarios.status")
        rows.append(row)
    return rows


@click.command()
@click.option("--game-dir", "game_dir", required=True)
def main(game_dir):
    """寫 <game-dir>/extract/tables/scenarios.csv（劇本號、檔名、標題（日、繁中）、年月、各勢力的君主）"""
    names = {p["id"]: p["name"] for p in sango.load_san11_persons(os.path.join(game_dir, SAN11PK_WIN_SCENARIOS[0]))}
    out = os.path.join(game_dir, "extract", "tables", "scenarios.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "title", "titleZh", "year", "month", "rulers"])
        for n, name, d, year, month, title in scenarios(game_dir):
            zh = read_file(os.path.join(_zh_dir(game_dir), "SCEN000.s11" if n == 1 else name))
            assert u16(zh, 0x5B) == year
            rulers = sorted({v for v in _rulers(d).values() if v is not None},
                            key=lambda v: next(k for k, x in _rulers(d).items() if x == v))
            w.writerow([n, name, title, zh_text(zh[0x5F:0x70].split(b"\0")[0]), year, month,
                        " ".join(names[v] for v in rulers)])
    print(out)


if __name__ == "__main__":
    main()


##############################################################################
# 三國志11 PK (Steam 628070): media/scenario/Scenario.s11 (cp932): 42 cities from 0x5A (25 bytes: name 5,
# reading 13, +18 州, +19 six neighbour cities FF-padded), then 45 関 / 港 (26 bytes: name 7, reading 19; 42-51
# 関, 52-86 港), 12 州 from 0x906 (0x2C bytes: name 5, +38 地方), 6 地方 from 0xB16 (0x12 bytes). 関 and 港 have
# no city field: parentCity is the city whose territory shares the longest border with theirs on the 200 x 200
# map SHEX0008 (media/san11pkres.bin item 4791, 11 bytes a cell, +1 territory).
SAN11_EXTRA_GAIJI = {0xE02D: "鄴", 0xE020: "邳", 0xE00B: "兗", 0xE02A: "涪", 0xE030: "鄱"}  # from the readings


SAN11_SHEX_ITEM, SAN11_MAP = 4791, 200


def san11_borders(path):
    """{territory: Counter(other territory: border cells)} of SHEX0008."""
    from collections import Counter, defaultdict
    with open(path, "rb") as f:
        f.seek(0x10 + 8 * SAN11_SHEX_ITEM)
        offset, size = struct.unpack("<II", f.read(8))
        f.seek(offset)
        d = f.read(size)
    assert d[:8] == b"SHEX0008"
    n = SAN11_MAP
    terr = d[8 + 1::11][:n * n]
    border = defaultdict(Counter)
    for y in range(n):
        for x in range(n):
            a = terr[y * n + x]
            for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
                if 0 <= x + dx < n and 0 <= y + dy < n:
                    b = terr[(y + dy) * n + x + dx]
                    if a != b:
                        border[a][b] += 1
                        border[b][a] += 1
    return border


# 全國地圖 (world/minimap.png): the 628 x 628 minimap of san11pkres.bin item 4857, layer 0 (the map) under layer 2
# (roads and borders); layer 1 colours each territory with its id (cities 0-41 match SHEX0008 on 95.6 % of the cells
# inside a city territory, 港 territories and the sea are colour 87). The hex at column x, row y lies at
# (SAN11_MM_SCALE x + SAN11_MM_X, SAN11_MM_SCALE (y + x % 2 / 2) + SAN11_MM_Y) on it, fitted to those cells (🟡).
# The facilities are SHEX cells of terrain 16 (都市, 7 cells), 18 (関, 3-5) and 17 (港, 1) whose territory is the
# place id; pos is the mean of their positions.
SAN11_MM_ITEM, SAN11_MM_SCALE, SAN11_MM_X, SAN11_MM_Y, SAN11_MM = 4857, 2.97, 18.5, 18.25, 628
SAN11_FACILITY = {16, 17, 18}


def san11_minimap(game_dir):
    """(the minimap with roads and borders, the territory layer, {place: (x, y)} on it)."""
    import san11_extras
    path = os.path.join(game_dir, san11_extras.PK_RES)
    ents = san11_extras.link_entries(path)
    layers = san11_extras.wftx_frames(san11_extras.link_item(path, ents, SAN11_MM_ITEM))
    im = Image.new("RGBA", layers[0].size, (0, 0, 0, 255))
    im.alpha_composite(layers[0])
    im.alpha_composite(layers[2])
    b = san11_extras.link_item(path, ents, san11_extras.WORLD_HEX)
    acc = {}
    for x in range(SAN11_MAP):
        for y in range(SAN11_MAP):
            c = b[8 + 11 * (SAN11_MAP * x + y):][:2]
            if c[0] in SAN11_FACILITY:
                a = acc.setdefault(c[1], [0, 0, 0])
                a[0] += SAN11_MM_SCALE * x + SAN11_MM_X
                a[1] += SAN11_MM_SCALE * (y + x % 2 / 2) + SAN11_MM_Y
                a[2] += 1
    pos = {k: (round(a[0] / a[2]), round(a[1] / a[2])) for k, a in acc.items()}
    return im.convert("RGB"), layers[1], pos


def world_check(game_dir, rows):
    """Each city's pos lies in its own territory colour on the minimap's territory layer, and every place has a
    facility on the hex map."""
    _, terr, pos = san11_minimap(game_dir)
    px, bad = terr.load(), []
    for r in rows:
        if r["id"] not in pos:
            bad.append(f"{r['id']}: no facility cells")
        elif r["id"] < 42 and px[pos[r["id"]]] != r["id"]:
            bad.append(f"{r['id']}: pos on territory {px[pos[r['id']]]}")
    return len(rows), bad


def places(game_dir, out_dir):
    minimap, _, pos = san11_minimap(game_dir)
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    minimap.save(os.path.join(out_dir, "world", "minimap.png"))
    with open(os.path.join(game_dir, "Scenario.s11"), "rb") as f:
        sc = f.read()
    gaiji = {**sango.SAN11_GAIJI, **SAN11_EXTRA_GAIJI}

    def s(b):
        return _gaiji(b.split(b"\0")[0].decode("cp932"), gaiji)

    regions = [s(sc[0xB16 + 0x12 * k:][:5]) for k in range(6)]
    states = [(s(sc[0x906 + 0x2C * k:][:5]), regions[sc[0x906 + 0x2C * k + 38]]) for k in range(12)]
    border = san11_borders(os.path.join(game_dir, "san11pkres.bin"))
    rows = []
    for i in range(42):
        r = sc[0x5A + 25 * i:][:25]
        state, region = states[r[18]]
        rows.append({"id": i, "name": s(r[:5]), "reading": s(r[5:18]), "level": "都市", "province": state,
                     "region": region, "adjacent": [b for b in r[19:25] if b != 0xFF]})
    for k in range(45):
        i = 42 + k
        r = sc[0x474 + 26 * k:][:26]
        city = next(c for c, _ in border[i].most_common() if c < 42)
        rows.append({"id": i, "name": s(r[:7]), "reading": s(r[7:26]), "level": "関" if i < 52 else "港",
                     "parentCity": city, "province": rows[city]["province"], "region": rows[city]["region"],
                     "uncertain": ["parentCity", "province", "region"],
                     "notes": "関、港沒有所屬都市的欄位，parentCity 是大地圖上和它的領地接壤最長的都市（推定），"
                              "州、地方照那個都市。関、港沒有相鄰表。"})
    for row in rows:
        row["pos"] = {"x": pos[row["id"]][0], "y": pos[row["id"]][1], "grid": "pixel", "w": SAN11_MM, "h": SAN11_MM}
        row["notes"] = row.get("notes", "") + "沒有戰場圖，野戰、攻城都在 200 × 200 格的大地圖上打。" \
            "pos 是這個地點在大地圖上的設施格（都市 7 格、関 3–5 格、港 1 格）的平均位置，換算到小地圖 world/minimap.png" \
            "（628×628）上的像素；格子到小地圖的換算是用領地圖擬合的，誤差約 1–2 點。"
    return rows


def stats(game_dir):
    sce = os.path.join(game_dir, K.SAN11PK_WIN_SCENARIOS[0])
    empty = {i for r in K.SAN11PK_WIN_EMPTY for i in r}
    chars = {p["id"]: p["name"] for p in sango.load_san11_persons(sce)
             if p["id"] not in empty and p["id"] not in K.SAN11PK_WIN_ROLES}
    return _pick(sango.load_san11_stats(sce), sango.SAN11_STATS, chars)
