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
import unicodedata

import click

import san9_extras
import sango

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


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


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
        assert _u16(c[b"head"], 20) == n - 1
        days = _u16(c[b"head"], 24)
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


def _kana(s):
    s = unicodedata.normalize("NFKC", s)
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def _owner(c, place):
    """force owning a place id (city +28, bldg +12), or None"""
    if place < 50:
        f = _u16(_records(c, CITIES)[place], 28)
    elif place < 250:
        f = _u16(_records(c, BUILDINGS)[place - 50], 12)
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
        parent = _u16(recs[i], 46)
        if parent in people:
            children.setdefault(parent, []).append(i)
    rows = []
    for i, (ja, kana) in people.items():
        r = recs[i]
        stats = dict(zip(sango.SAN9_STATS, struct.unpack_from("<4H", r, 30)))
        row = {"id": i, "name": zh[i]}
        if zh[i] != ja:
            row["nameJa"] = ja
        row["reading"] = _kana(kana)
        row["born"] = YEAR0 + _u16(r, 20)
        row["debut"] = YEAR0 + _u16(r, 18)
        if any(stats.values()):
            row["stats"] = stats
        row["more"] = {"性別": "女" if r[0] & 1 else "男",
                       "性格": TEMPERS[r[54]] if r[54] < 4 else r[54],
                       **{f"{k}熟練": v for k, v in zip(SKILLED, struct.unpack_from("<9H", r, 56))}}
        row["hidden"] = {"寿命": r[40], "相性": _u16(r, 48), "義理": r[50], "野望": r[52]}
        bits = struct.unpack_from("<I", r, 128)[0]
        heihou = [h for k, h in enumerate(HEIHOU) if bits >> k & 1]
        if heihou:
            row["skills"] = {"兵法": heihou}
        rel = {"clan": _u16(r, 44)}
        parent = _u16(r, 46)
        if parent in people:
            rel["father"] = [parent]
        if i in children:
            rel["children"] = sorted(children[i])
        row["relations"] = rel
        row["scenarios"] = []
        for n, _, c, year, _ in scens:
            sr = c[PRSN][SIZE * i:SIZE * (i + 1)]
            code, place = _u16(sr, 28), _u16(sr, 24)
            if code == 9:  # not an officer in any scenario
                continue
            e = {"scenario": n, "year": year, "status": STATUS.get(code, str(code))}
            if code in (0, 1, 2, 3):
                force = _owner(c, place)
                ruler = None if force is None else _u16(_records(c, FORCES)[force], 18)
                if ruler in people:
                    e["lord"] = ruler
                if _u16(sr, 38) != 0xFFFF:
                    e["loyalty"] = _u16(sr, 38)
            if code not in (7, 8) and place < 250:
                e["location"] = place
            if code in (6, 7):
                e["debut"] = YEAR0 + _u16(sr, 18)
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
            rulers = [people[r] for r in (_u16(f, 18) for f in _records(c, FORCES)) if r != 0xFFFF]
            w.writerow([n, name, titles[n - 1], year, month, " ".join(rulers)])
    print(out)


if __name__ == "__main__":
    main()
