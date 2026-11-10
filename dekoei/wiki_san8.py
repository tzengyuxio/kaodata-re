"""三國志VIII with PK (san8pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list.

All 51 scenarios (one a year, 184-234) come from the one file D_Sce.s8: the person table holds the fixed fields and a
timeline table holds every person's state from a given year on; a scenario of year Y takes, per person, the last
timeline record with year <= Y. Names are the Steam 繁中版's (depot 628040, san8_extras.zh_persons), the Japanese
ones go to nameJa. Layout and evidence: notes/san8.md「koei-wiki 匯出：人物」, notes/san-attributes.md「三國志VIII」.

    ../.venv/bin/python wiki_san8.py --game-dir ../games/san8pk-win   # writes extract/tables/scenarios.csv

The people are the kaodata san8pk-win characters: the records minus SAN8PK_WIN_ROLES and the alias 単福 (587, only
ever 身分 10, never an officer; 徐庶 is 236), id = record number.
"""
import collections
import csv
import os
import struct
import unicodedata

import click

import sango
import san8_extras
from kaodata_export import SAN8PK_WIN_ALIASES, SAN8PK_WIN_ROLES

SCE = "D_Sce.s8"
ZH_DIR = os.path.join("..", "steam", "628040-tchinese", "depot")  # relative to game_dir
# Header u16 at 0: counts of the tables (16 州, 192 戦場?, 51 scenarios at +6, 512 city states at +8, 86 roads,
# 255 items, 112 item holders at +16, 4098 timeline records at +20)
SCENARIO_COUNT, FIRST_YEAR = 51, 184
# Timeline, 0x12BF5: 4098 x 13 bytes sorted by (person, year): u16 person, u16 year (from), u8 city (0-49, 0xFF),
# u8 勢力 (0xFF none), u8 身分, u8 忠誠, u8 階級? (0xFF none), u32 ? (not decoded). Year 271 records are past the
# last scenario and never apply.
TIMELINE, TL_SIZE, TL_COUNT = 0x12BF5, 13, 4098
# 身分: 3-9 match the EXE's strategy classes (一般 軍師 太守 軍団長 君主 / 同志 頭領 of a 放浪軍) and history
# (劉備 9 with 関羽 8 in 185, 198, 200; 諸葛亮 4 from 208, 6 in the 北伐 years; 関羽 6 from 212). 0, 1, 2 have no
# 勢力, 忠誠 0 and 階級 0xFF: exported as 在野 (the three are not told apart). 10 is never an officer (霊帝, 献帝,
# 華佗, 于吉, 祝融, 孫尚香 208, 単福): left out like san9's 9.
STATUS = {0: "在野", 1: "在野", 2: "在野", 3: "一般", 4: "軍師", 5: "太守", 6: "軍団長", 7: "君主", 8: "同志",
          9: "頭領"}
LORDS = (7, 9)
NOT_OFFICER = 10
SKILLS = san8_extras.SKILLS
TACTICS = ["突撃", "乱撃", "撹乱", "奇襲", "槍衾", "車懸", "火矢", "斉射", "乱射", "矢嵐", "激流", "烈火", "落石", "妖術",
           "攻城"]


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _read(game_dir):
    with open(os.path.join(game_dir, SCE), "rb") as f:
        return f.read()


def _record(data, i):
    o = sango.SAN8_PERSONS + i * sango.SAN8_PERSON_SIZE
    return data[o:o + sango.SAN8_PERSON_SIZE]


def timeline(data):
    """person id -> [(year, city, force, status, loyalty, rank)] in year order"""
    assert _u16(data, 6) == SCENARIO_COUNT and _u16(data, 20) == TL_COUNT
    out = collections.defaultdict(list)
    for k in range(TL_COUNT):
        pid, year, city, force, status, loyalty, rank = struct.unpack_from("<HHBBBBB", data, TIMELINE + TL_SIZE * k)
        out[pid].append((year, city, force, status, loyalty, rank))
    return out


def died(data, i):
    return _u16(_record(data, i), 0x2B)


def state(tl, i, year):
    """the timeline record in force in a scenario year, or None (not yet in the game)"""
    s = None
    for r in tl[i]:
        if r[0] <= year:
            s = r
    return s


def scenario_states(data, tl, year):
    """{person: record} of the people alive in the scenario (year < 歿年), and {force: lord}"""
    states, lords = {}, {}
    for i in range(len(tl)):
        s = state(tl, i, year)
        if s and year < died(data, i):
            states[i] = s
            if s[3] in LORDS:
                assert s[2] not in lords
                lords[s[2]] = i
    return states, lords


def _kana(s):
    s = unicodedata.normalize("NFKC", s)
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def _zh_text(b):
    return b.split(b"\0")[0].decode("cp950").strip()


def persons(game_dir):
    data = _read(game_dir)
    zh_dir = os.path.join(game_dir, ZH_DIR)
    zh = san8_extras.bio_names(zh_dir)
    with open(os.path.join(zh_dir, "D_SCE.S8"), "rb") as f:
        zh_data = f.read()
    people = {p["id"]: p for p in sango.load_san8_persons(os.path.join(game_dir, SCE))
              if p["name"] not in SAN8PK_WIN_ROLES | SAN8PK_WIN_ALIASES}
    tl = timeline(data)
    scens = [(n, FIRST_YEAR + n - 1, *scenario_states(data, tl, FIRST_YEAR + n - 1)) for n in range(1, SCENARIO_COUNT + 1)]
    children = {}
    for i in people:
        parent = _u16(_record(data, i), 0x33)
        if parent in people and parent != i:
            children.setdefault(parent, []).append(i)
    rows = []
    for i, p in people.items():
        r = _record(data, i)
        row = {"id": i, "name": zh[i]}
        if zh[i] != p["name"]:
            row["nameJa"] = p["name"]
        courtesy = _zh_text(_record(zh_data, i)[0x22:0x27])
        if courtesy:
            row["courtesy"] = courtesy
        row["reading"] = _kana("".join(p["kana"]))
        row["born"], row["died"] = _u16(r, 0x29), _u16(r, 0x2B)
        row["stats"] = dict(zip(sango.SAN8_STATS, r[0x2D:0x31]))
        row["more"] = {"性別": "女" if r[0x38] & 0x80 else "男"}
        row["hidden"] = {"相性": r[0x35], "義理": r[0x36] & 15, "野望": r[0x36] >> 4, "冷静": r[0x37] & 7,
                         "勇猛": r[0x37] >> 3 & 7, "有名度": r[0x38] & 15, "寿命": r[0x3A]}
        bits = int.from_bytes(r[0x3B:0x3E], "little")
        skills = {}
        tokugi = [s for k, s in enumerate(SKILLS) if bits >> k & 1]
        if tokugi:
            skills["特技"] = tokugi
        levels = {t: v for t, v in zip(TACTICS, r[0x40:0x4F]) if v != 0xFF}
        if levels:
            skills["戦法"] = list(levels)
            row["game"] = {"戦法等級": levels}
        if skills:
            row["skills"] = skills
        rel = {"clan": _u16(r, 0x31)}
        parent = _u16(r, 0x33)
        if parent in people and parent != i:
            rel["father"] = [parent]
        if i in children:
            rel["children"] = sorted(children[i])
        row["relations"] = rel
        entries = []
        first = tl[i][0][0] if tl[i] else None
        for n, year, states, lords in scens:
            if i not in states:
                # not yet in the game: list it when a later record makes the person an officer or 在野
                if first is not None and year < first < row["died"] and state(tl, i, first)[3] != NOT_OFFICER:
                    entries.append({"scenario": n, "year": year, "status": "未登場", "debut": first})
                continue
            _, city, force, code, loyalty, _ = states[i]
            if code == NOT_OFFICER:
                continue
            e = {"scenario": n, "year": year, "status": STATUS[code]}
            if code >= 3:
                if lords[force] in people:
                    e["lord"] = lords[force]
                if code not in LORDS:
                    e["loyalty"] = loyalty
            if city < 50:
                e["location"] = city
            entries.append(e)
        if entries:
            row["scenarios"] = entries
        row["uncertain"] = ["born", "died", "more.性別", "hidden", "relations.clan", "relations.father",
                            "relations.children", "skills.戦法", "game.戦法等級", "scenarios.status"]
        rows.append(row)
    return rows


@click.command()
@click.option("--game-dir", "game_dir", required=True)
def main(game_dir):
    """寫 <game-dir>/extract/tables/scenarios.csv（劇本號、檔名、名稱、年、各勢力的君主）"""
    data = _read(game_dir)
    names = {p["id"]: p["name"] for p in sango.load_san8_persons(os.path.join(game_dir, SCE))}
    tl = timeline(data)
    out = os.path.join(game_dir, "extract", "tables", "scenarios.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "name", "nameZh", "year", "rulers"])
        for n in range(1, SCENARIO_COUNT + 1):
            year = FIRST_YEAR + n - 1
            states, lords = scenario_states(data, tl, year)
            rulers = [names[i] for i in sorted(lords.values(), key=lambda i: (states[i][3], i)) if states[i][3] == 7]
            w.writerow([n, SCE, f"{year}年", f"{year}年", year, " ".join(rulers)])
    print(out)


if __name__ == "__main__":
    main()
