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
import struct

import click

import sango
from kaodata_export import SAN11PK_WIN_EMPTY, SAN11PK_WIN_ROLES, SAN11PK_WIN_SCENARIOS, kana_to_hiragana
from san9_extras import zh_text

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


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _zh_dir(game_dir):
    return os.path.join(game_dir, "..", "steam", "628070-tchinese", "depot", "media", "scenario")


def scenarios(game_dir):
    """[(number, file, data, year, month, title)]"""
    out = []
    for n, name in enumerate(SAN11PK_WIN_SCENARIOS, 1):
        d = _read(os.path.join(game_dir, name))
        out.append((n, name, d, _u16(d, 0x5B), d[0x5D], d[0x5F:0x70].split(b"\0")[0].decode("cp932")))
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
    d = _read(os.path.join(game_dir, "Scenario.s11"))
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
    zh = _read(os.path.join(_zh_dir(game_dir), "SCEN000.s11"))
    skills = _skills(game_dir)
    rulers = [(n, d, year, _rulers(d)) for n, _, d, year, _, _ in scens]
    sworn, children = {}, {}
    for i in people:
        r = _record(main, i)
        if _u16(r, 0x48) in ids:
            sworn.setdefault(_u16(r, 0x48), []).append(i)
        for o in (0x41, 0x43):
            if _u16(r, o) in ids:
                children.setdefault(_u16(r, o), []).append(i)
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
        row["born"], row["died"], row["debut"] = _u16(r, 0x3A), _u16(r, 0x3C), _u16(r, 0x38)
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
            if _u16(r, o) in ids:
                rel[key] = [_u16(r, o)]
        if i in children:
            rel["children"] = sorted(children[i])
        group = sworn.get(_u16(r, 0x48), [])
        if len(group) > 1:
            rel["sworn"] = sorted(x for x in group if x != i)
        if _u16(r, 0x3F) in ids:
            rel["clan"] = _u16(r, 0x3F)
        if rel:
            row["relations"] = rel
        game = {}
        liked = [_u16(r, 0x4B + 2 * k) for k in range(5)]
        hated = [_u16(r, 0x55 + 2 * k) for k in range(5)]
        if any(x in ids for x in liked):
            game["親愛武将"] = [x for x in liked if x in ids]
        if any(x in ids for x in hated):
            game["嫌悪武将"] = [x for x in hated if x in ids]
        if game:
            row["game"] = game
        row["scenarios"] = []
        for n, d, year, ruler in rulers:
            s = _record(d, i)
            code, army, place = s[0x64], s[0x5F], _u16(s, 0x60)
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
                e["debut"] = _u16(s, 0x38)
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
            zh = _read(os.path.join(_zh_dir(game_dir), "SCEN000.s11" if n == 1 else name))
            assert _u16(zh, 0x5B) == year
            rulers = sorted({v for v in _rulers(d).values() if v is not None},
                            key=lambda v: next(k for k, x in _rulers(d).items() if x == v))
            w.writerow([n, name, title, zh_text(zh[0x5F:0x70].split(b"\0")[0]), year, month,
                        " ".join(names[v] for v in rulers)])
    print(out)


if __name__ == "__main__":
    main()
