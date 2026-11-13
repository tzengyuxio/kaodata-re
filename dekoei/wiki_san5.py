"""三國志V (san5pk-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san5pk-pc98 id (500 people,
scenarios 1-12 with SNDATA before TAIKI, deduplicated by face code, wiki_stats.stats_san5pk_pc98). name is the DOS
Chinese version's spelling of the same face code (the two versions have the same records in the same order), nameJa
the PC-98 one. Field sources: notes/san5.md「koei-wiki 匯出」, notes/san-attributes.md「三國志V」."""
import os
import re

import kaodata_export as ke
import ls11
import sango
import wiki_stats

# SNDATA.S5 scenario part (PC-98 PK): u16 year at +577 (the year before for the January scenarios), u16 person
# count at +579; city n's 30-byte record at 961 + 30n (u16 heads of three person lists at +0 officers, +2 在野,
# +4 未発見; the next person is the ability record's +2); 18 force records of 77 bytes at 3899 (u16 ruler +2,
# u16 軍師 +14). Person numbers are 1-based indexes into the scenario's SNDATA person table.
YEAR, COUNT, CITIES, FORCES, FORCE_SIZE, N_FORCES = 577, 579, 961, 3899, 77, 18
# PC-98 MAIN.EXE 0x54742: 身分 君主 軍師 一般 修行 在野 未発見 待機 死亡, then 将軍 太守 皇帝
TITLE = re.compile(r'"(\d+)年 *([０-９\d]+)月 ([^"|]+?) *\|')
N_SCENARIOS = 11  # the 12th scenario of SNDATA.S5 has no title (MESSAGE.S5 part 13 lists 11) and is not exported
SEPARATE = 1000  # +32 parent face code; from 1000 up it is a sibling group without a parent in the game (🟡)
TEMPER = (("義理", 0, 15), ("野望", 4, 15), ("冷静", 8, 7), ("勇猛", 11, 7))  # +34 u16 bit fields (🟡)


def _u16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def _titles(game_dir):
    """(year, month, name) of scenarios 1-11 from the scenario menu in MESSAGE.S5 part 13."""
    with open(os.path.join(game_dir, "MESSAGE.S5"), "rb") as f:
        part = ls11.ls11_decode_parts(f.read())[13]
    text = re.sub(rb"[\x00-\x1f]", b"|", part).decode("cp932", "replace")
    return [(int(y), int(m.translate(str.maketrans("０１２３４５６７８９", "0123456789"))), n)
            for y, m, n in TITLE.findall(text)]


def persons(game_dir):
    sn, tk = os.path.join(game_dir, "SNDATA.S5"), os.path.join(game_dir, "TAIKI.S5")
    stats = wiki_stats.stats_san5pk_pc98(game_dir)
    codes = list(dict.fromkeys(c for _, _, c in sango.load_san5_persons(sn, tk, True)))
    assert len(codes) == len(stats)
    cid = {c: i for i, c in enumerate(codes)}
    dos = os.path.join(game_dir, "..", "san5pk-dos")
    zh = {}
    for _, name, code in sango.load_san5_persons(os.path.join(dos, "SNDATA.S5"), os.path.join(dos, "TAIKI.S5")):
        zh.setdefault(code, name)
    assert set(zh) == set(codes)
    titles = _titles(game_dir)
    assert len(titles) == N_SCENARIOS
    parts = sango.san5_parts(sn)
    records = list(sango.san5_records(sn, tk, True))
    person = {}  # face code -> 38-byte person record (the same in every scenario)
    scen = []  # per scenario: {id: scenario entry}
    for k in range(N_SCENARIOS):
        part, (year, month, _) = parts[k], titles[k]
        assert _u16(part, YEAR) == year - (month == 1)
        recs = [(a, b) for s, _, a, b in records if s == k + 1]
        count = _u16(part, COUNT)
        pid = [cid[_u16(b, 30)] for _, b in recs]
        lists = {}  # SNDATA index -> (city, list offset, first in the list)
        for n in range(1, 48):
            city = part[CITIES + 30 * n:][:30]
            for off in (0, 2, 4):
                h, first = _u16(city, off), True
                while h not in (0, 0xFFFF):
                    a = recs[h - 1][0]
                    assert a[20] == n and h - 1 not in lists
                    lists[h - 1], h, first = (n, off, first), _u16(a, 2), False
        assert len(lists) == count
        forces = {}
        for f in range(N_FORCES):
            r = part[FORCES + FORCE_SIZE * f:][:FORCE_SIZE]
            if _u16(r, 2) not in (0, 0xFFFF):
                forces[f + 1] = (_u16(r, 2) - 1, _u16(r, 14) - 1)
        out = {}
        for i, (a, b) in enumerate(recs):
            person.setdefault(_u16(b, 30), b)
            s = {"scenario": k + 1, "year": year, "month": month, "location": a[20]}
            if i >= count:
                s["status"] = "待機"
            else:
                city, off, first = lists[i]
                if a[21] == 0xFF:
                    assert off == (4 if a[10] & 1 else 2)
                    s["status"] = "未発見" if a[10] & 1 else "在野"
                else:
                    assert off == 0
                    ruler, adviser = forces[a[21]]
                    s["status"] = "君主" if i == ruler else "軍師" if i == adviser else "一般"
                    s["lord"] = pid[ruler]
                    if i != ruler:
                        s["loyalty"] = a[19]
                        if first:
                            s["rank"] = "太守"
            out[pid[i]] = s
        scen.append(out)

    by_code = {c: i for i, c in enumerate(codes)}
    rows = []
    for i, ((_, name_ja, st), code) in enumerate(zip(stats, codes)):
        b = person[code] if code in person else next(b for _, _, _, b in records if _u16(b, 30) == code)
        row = {"id": i, "name": zh[code]}
        if name_ja != zh[code]:
            row["nameJa"] = name_ja
        row["born"] = b[21] + 100
        row["stats"] = st
        temper = _u16(b, 34)
        row["hidden"] = {"相性": b[20], **{k: temper >> sh & mask for k, sh, mask in TEMPER}}
        rel = {}
        parent = _u16(b, 32)
        if parent < SEPARATE and parent in by_code:
            rel["father"] = [by_code[parent]]
        children = [j for j, c in enumerate(codes) if _u16(_record(person, records, c), 32) == code]
        if children:
            rel["children"] = children
        if parent != 0xFFFF:
            sib = [j for j, c in enumerate(codes) if j != i and _u16(_record(person, records, c), 32) == parent]
            if sib:
                rel["siblings"] = sib
        if b[22]:
            rel["clan"] = b[22]
        if rel:
            row["relations"] = rel
        out = [s[i] for s in scen if i in s]
        assert out
        row["scenarios"] = out
        row["uncertain"] = [f"hidden.{k}" for k in row["hidden"]] + (["relations.clan"] if "clan" in rel else []) + \
            (["relations.siblings"] if parent >= SEPARATE and "siblings" in rel else []) + \
            [f"scenarios.{k}" for k in ("loyalty", "rank") if any(k in s for s in out)]
        notes = []
        if code in ke.SAN5PK_NAME_HISTORICAL:
            notes.append(f"中文版寫法的史書寫法 {ke.SAN5PK_NAME_HISTORICAL[code]}。")
        if code in ke.SAN5PK_PC98_NAME_HISTORICAL:
            notes.append(f"日文版寫法的史書寫法 {ke.SAN5PK_PC98_NAME_HISTORICAL[code]}。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def _record(person, records, code):
    if code not in person:
        person[code] = next(b for _, _, _, b in records if _u16(b, 30) == code)
    return person[code]
