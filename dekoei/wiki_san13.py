"""三國志13 with PK (san13pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list. Names are the
繁中 ones (string table of PK item 1416), the Japanese ones (PK item 2) go to nameJa. Fields and evidence:
notes/san13.md「koei-wiki 匯出：人物」, notes/san-attributes.md「三國志13」.

    ../.venv/bin/python wiki_san13.py --game-dir ../games/san13pk-win   # writes extract/tables/scenarios.csv

The people are the kaodata san13pk-win characters: persons with pictures, minus the role records
(kaodata_export.SAN13PK_WIN_ROLES) and the nameless 古武將; id = person number (row of the person tables).

Person data comes from two layouts. PK item 941 (scenario_bs, the editor's base data) item 6: 307 columns, the
fixed attributes (SAN13 below). PK items 942-952 (scenario_00-10, the 11 scenarios in menu order) item 6: 275
columns, the scenario state (SCEN below); item 0 is the header (col0 scenario number, col6 year), item 5 the forces
(row = force, col0 255 unused, col1 ruler). Items 992-1030 (scenario_50-88) are the 英傑伝 stages, not exported.
"""
import csv
import os

import click

import sango
from kaodata_export import SAN13PK_WIN_ROLES, kana_to_hiragana
from places_export import _xl_rows

SCENARIOS = range(942, 953)
BASE = 941
NAMES_JA, NAMES_TC = sango.SAN13_NAMES, sango.SAN13_NAMES_TC
TITLES = 4  # string 4 + scenario number: the title
# 941 item 6 columns: 0 属性, 1 性別, 6 生年, 7 登場年, 8 没年, 9 病死, 10-13 統率 武力 知力 政治, 14-16 適性 (0-3 =
# C-S), 17 戦法 (-1 none), 18 重臣特性 (255 none), 19 相性 (i8, read as u8), 20 一門 (the head's person number), 21
# 父親, 22 母親, 23 性格, 24-27 武具 書物 宝物 酒興味, 28 物欲, 33 配偶者, 36 義兄 (the eldest), 38 義理, 40 勇愛,
# 42 才愛
APTITUDE = ["槍兵", "騎兵", "弓兵"]
GRADES = "CBAS"
TACTICS = 18403, 141  # Japanese strings: 戦法 names (呂布 0 天下無双, 関羽 2 軍神)
TRAITS = 20443, 17  # 重臣特性 names (諸葛亮 0 神算鬼謀, 関羽 14 槍術調練)
SKILLS = 16707, 20  # 特技 names, 商業 … 鬼謀
TEMPERS = 20620  # 小心 冷静 豪胆 猪突
INTERESTS = ["武具興味", "書物興味", "宝物興味", "酒興味"]
# 942-952 item 6 columns: 13 status (STATUS), 14 96-120 for officers (not 忠誠, which is 0-100; not exported), 17 force (255 none), 18 place (places export id, 255
# none), 25-64 20 pairs (特技 k or 255, value) — the same in every scenario
STATUS = 20626  # 未登場 未発見 在野 現役 捕虜 死亡 特殊 イベント = codes 0-7
ACTIVE = 3


def _strings(game_dir, item, enc, gaiji={}):
    return sango.san13_strings(sango.san13_items(sango.san13_items(sango.san13_entry(game_dir, item))[0])[0], enc,
                               gaiji)


def _table(game_dir, entry, sub):
    return _xl_rows(sango.san13_unzip(sango.san13_items(sango.san13_entry(game_dir, entry))[sub]))


def scenarios(game_dir):
    """[(number, file, title, titleZh, year, {force: ruler}, person table)]"""
    ja, tc = _strings(game_dir, NAMES_JA, "cp932"), _strings(game_dir, NAMES_TC, "cp950", sango.SAN13_GAIJI_TC)
    out = []
    for n, e in enumerate(SCENARIOS, 1):
        header = _table(game_dir, e, 0)[0]
        assert header[0] == n - 1 and header[1] == 0, e
        rulers = {f: r[1] for f, r in enumerate(_table(game_dir, e, 5)) if r[0] != 255}
        out.append((n, f"pk/data/scenario/scenario_{n - 1:02d}.bin.zp", ja[TITLES + n - 1], tc[TITLES + n - 1],
                    header[6], rulers, _table(game_dir, e, 6)))
    return out


def _places():
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "export", "koei-wiki", "places", "san13pk-win.jsonl")
    with open(path, encoding="utf-8") as f:
        return {json.loads(line)["id"] for line in f}


def persons(game_dir):
    data = sango.load_san13_persons(game_dir)
    people = sorted(p for p, (name, _, _) in data["names"].items() if name and p not in SAN13PK_WIN_ROLES)
    ids = set(people)
    ja = _strings(game_dir, NAMES_JA, "cp932")
    tc = _strings(game_dir, NAMES_TC, "cp950", sango.SAN13_GAIJI_TC)
    start, run = sango.SAN13_NAME_FIELDS
    base = _table(game_dir, BASE, 6)
    scens = scenarios(game_dir)
    places = _places()
    first = scens[0][6]
    status = ja[STATUS:STATUS + 8]
    sworn, children = {}, {}
    for p in people:
        r = base[p]
        if r[36] in ids:
            sworn.setdefault(r[36], []).append(p)
        for c in (21, 22):
            if r[c] in ids:
                children.setdefault(r[c], []).append(p)
    rows = []
    for p in people:
        r = base[p]
        name_ja, name, reading = data["names"][p]
        row = {"id": p, "name": name}
        if name != name_ja:
            row["nameJa"] = name_ja
        courtesy = tc[start + 2 * run + p]
        if courtesy:
            row["courtesy"] = courtesy
        row["reading"] = kana_to_hiragana(reading)
        row["born"], row["debut"], row["died"] = r[6], r[7], r[8]
        row["stats"] = dict(zip(sango.SAN13_STATS, r[10:14]))
        row["more"] = {"性別": "女" if r[1] else "男"}
        hidden = {"相性": r[19] & 0xFF, "性格": ja[TEMPERS + r[23]] if r[23] < 4 else r[23]}
        hidden.update(zip(INTERESTS, r[24:28]))
        hidden.update({"物欲": r[28], "義理": r[38], "勇愛": r[40], "才愛": r[42], "属性": r[0], "病死": r[9]})
        row["hidden"] = hidden
        if r[14] != 255:  # 255: 霊帝, 献帝, 華佗, 左慈 … (no troops)
            row["aptitude"] = {a: GRADES[v] for a, v in zip(APTITUDE, r[14:17])}
        skills, values = {}, {}
        if 0 <= r[17] < TACTICS[1]:
            skills["戦法"] = [ja[TACTICS[0] + r[17]]]
        if r[18] < TRAITS[1] and ja[TRAITS[0] + r[18]]:
            skills["重臣特性"] = [ja[TRAITS[0] + r[18]]]
        for k in range(SKILLS[1]):
            s, v = first[p][25 + 2 * k:27 + 2 * k]
            if s != 255:
                assert s == k, (p, k)
                values[ja[SKILLS[0] + k]] = v
        if values:
            skills["特技"] = list(values)
        if skills:
            row["skills"] = skills
        if values:
            row["game"] = {"特技値": values}
        rel = {}
        for key, c in (("father", 21), ("mother", 22), ("spouse", 33)):
            if r[c] in ids:
                rel[key] = [r[c]]
        if p in children:
            rel["children"] = sorted(children[p])
        group = sworn.get(r[36], [])
        if len(group) > 1:
            rel["sworn"] = sorted(x for x in group if x != p)
        if r[20] in ids:
            rel["clan"] = r[20]
        if rel:
            row["relations"] = rel
        row["scenarios"] = []
        for n, _, _, _, year, rulers, table in scens:
            s = table[p]
            code, force, place = s[13], s[17], s[18]
            e = {"scenario": n, "year": year, "status": status[code]}
            if code == ACTIVE:
                ruler = rulers[force]
                if ruler == p:
                    e["status"] = "君主"
                elif ruler in ids:
                    e["lord"] = ruler
            else:
                assert force == 255, (p, n)
            if place in places and code != 5:  # 死亡 keeps a place
                e["location"] = place
            if code == 0:
                e["debut"] = r[7]
            row["scenarios"].append(e)
        row["uncertain"] = ["aptitude", "skills", "game.特技値", "hidden", "relations"]
        if any(e["status"] not in ("君主", "現役", "未登場", "死亡") for e in row["scenarios"]):
            row["uncertain"].append("scenarios.status")
        rows.append(row)
    return rows


@click.command()
@click.option("--game-dir", "game_dir", required=True)
def main(game_dir):
    """寫 <game-dir>/extract/tables/scenarios.csv（劇本號、檔名、標題（日、繁中）、年、各勢力的君主）"""
    names = sango.load_san13_persons(game_dir)["names"]
    out = os.path.join(game_dir, "extract", "tables", "scenarios.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "name", "nameZh", "year", "rulers"])
        for n, file, title, title_zh, year, rulers, _ in scenarios(game_dir):
            w.writerow([n, file, title, title_zh, year, " ".join(names[r][0] for f, r in sorted(rulers.items()))])
    print(out)


if __name__ == "__main__":
    main()
