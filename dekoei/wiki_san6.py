"""三國志VI 威力加強版 (san6pk-win, 繁中版) for koei-wiki: persons (koei-persons/1). id is the kaodata san6pk-win id:
the person slots of SNDATA01-23.S6 in slot order, the four 武將 slots of each tribe counted once (as
kaodata_export.build_san6pk_win and wiki_stats.stats_san6pk_win). The game is only in Chinese, so there is no nameJa.
Layout and evidence: notes/san6.md「koei-wiki 匯出」, notes/san-attributes.md「三國志VI」.

Scenario file header: u16 year, u16 month. Factions: 27 x 0xC0 bytes from 0x7EF68, +10 u16 the ruler's slot (0xFFFF
none). Person record (650 bytes from sango.SAN6_PERSONS): +12 字, +32 身份 (SAN6.EXE pointer table 0x337EA0: 群雄 太守
一般), +34 狀況 (table 0x337EB0: 現役 在野 未發現 待命 俘虜 死亡), +36 出場年, +38 出生年, +44 faction (0xFFFF none),
+48 統率 武力 智力 政治 魅力, +68 忠誠, +76 city (= places id), +80 血緣, +82 father's slot (1000+ a group of brothers
with no father in the game, 0xFFFF none), +84 相性, +118 bits of 義理 野心 冷靜 勇猛."""
import os
import struct

import sango
from kaodata_export import SAN6PK_WIN_NAME_HISTORICAL

DATASET = "san6pk-win"
FACTIONS, FACTION_SIZE, FACTION_COUNT = 0x7EF68, 0xC0, 27
RANKS = ("群雄", "太守", "一般")
STATES = ("現役", "在野", "未發現", "待命", "俘虜", "死亡")
# SAN6.EXE 0x34D338: the titles in the order of SNDATA01-23 (7 main, 7 historical, 單挑, 3 more, 5 of the PK)
TITLES = ["黃巾之亂", "董卓之野望", "群雄割據", "河北爭亂", "臥龍與鳳雛", "漢中王劉備", "星落五丈原",
          "義勇軍初陣", "呂布討伐戰", "河北統一戰", "皇帝袁術", "赤壁之戰", "馬超復仇", "出師表", "單挑",
          "誅殺董太師", "入蜀", "昭烈帝駕崩", "白馬長史", "小霸王的奇襲", "驅逐袁氏", "強行北伐", "諸葛誕的崛起"]
DUEL = 15  # 單挑: the duel mode's data (5 rulers, everyone else 現役 under them), not a starting placement
TRAITS = [("義理", 0, 4), ("野心", 4, 4), ("冷靜", 8, 3), ("勇猛", 11, 3)]  # (name, first bit, bits) of +118


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _text(b):
    return b.split(b"\0")[0].strip().decode("big5")


def _load(game_dir):
    """[(number, year, month, [record] by slot, [ruler slot] by faction)] of the 23 scenario files."""
    out = []
    for n in range(1, 24):
        with open(os.path.join(game_dir, f"SNDATA{n:02}.S6"), "rb") as f:
            d = f.read()
        recs = [d[sango.SAN6_PERSONS + s * sango.SAN6_PERSON_SIZE:][:sango.SAN6_PERSON_SIZE]
                for s in range(sango.SAN6_PERSON_SIZE)]
        rulers = [_u16(d, FACTIONS + f * FACTION_SIZE + 10) for f in range(FACTION_COUNT)]
        out.append((n, _u16(d, 0), _u16(d, 2), recs, rulers))
    return out


def persons(game_dir):
    scen = _load(game_dir)
    # ids as build_san6pk_win: the first slot of each (name, face code)
    ids, slot_of = {}, {}
    for slot, name, code in sango.load_san6_persons(game_dir):
        if (name, code) not in ids:
            ids[(name, code)] = len(ids)
            slot_of[ids[(name, code)]] = slot
    id_of = {s: i for i, s in slot_of.items()}
    assert len(ids) == 532
    first = {}  # the record of the first scenario where the slot has a face (stats are the same in all 23)
    for _, _, _, recs, _ in scen:
        for i, s in slot_of.items():
            if i not in first and _u16(recs[s], 30):
                first[i] = recs[s]

    father = {i: id_of[_u16(first[i], 82)] for i in slot_of if _u16(first[i], 82) in id_of}
    group = {i: _u16(first[i], 82) for i in slot_of if 1000 <= _u16(first[i], 82) < 0xFFFF}
    children = {}
    for c, p in father.items():
        children.setdefault(p, []).append(c)

    rows = []
    for i, s in slot_of.items():
        r = first[i]
        name = _text(r[0:6]) + _text(r[6:12])
        row = {"id": i, "name": name}
        courtesy = _text(r[12:18])
        if courtesy:
            row["courtesy"] = courtesy
        row["born"] = _u16(r, 38)
        row["stats"] = dict(zip(sango.SAN6_STATS, struct.unpack_from("<5H", r, 48)))
        bits = _u16(r, 118)
        row["hidden"] = {"相性": _u16(r, 84), **{k: bits >> b & (1 << n) - 1 for k, b, n in TRAITS}}
        rel = {}
        if i in father:
            rel["father"] = [father[i]]
        if i in children:
            rel["children"] = sorted(children[i])
        sib = sorted(j for j in slot_of if j != i and (
            (i in father and father.get(j) == father[i]) or (i in group and group.get(j) == group[i])))
        if sib:
            rel["siblings"] = sib
        if _u16(r, 80) != 0xFFFF:
            rel["clan"] = _u16(r, 80)
        if rel:
            row["relations"] = rel

        out = []
        for n, year, month, recs, rulers in scen:
            if n == DUEL:
                continue
            p = recs[s]
            if not _u16(p, 30):
                continue
            state = _u16(p, 34)
            e = {"scenario": n, "year": year, "month": month}
            if state == 0:
                e["status"] = RANKS[_u16(p, 32)]
                faction = _u16(p, 44)
                if faction < FACTION_COUNT and rulers[faction] in id_of:
                    e["lord"] = id_of[rulers[faction]]
                e["location"] = _u16(p, 76)
                if e["status"] != "群雄":
                    e["loyalty"] = p[68]
            else:
                e["status"] = STATES[state]
                if state == 3:
                    e["debut"] = _u16(p, 36)
                elif state != 5:
                    e["location"] = _u16(p, 76)
            out.append(e)
        if out:
            row["scenarios"] = out
        row["uncertain"] = ["hidden.義理", "hidden.野心", "hidden.冷靜", "hidden.勇猛"] + \
            (["relations.clan"] if "clan" in rel else []) + \
            (["scenarios.loyalty"] if any("loyalty" in e for e in out) else [])
        notes = []
        if name in SAN6PK_WIN_NAME_HISTORICAL:
            notes.append(f"史書寫法 {SAN6PK_WIN_NAME_HISTORICAL[name]}。")
        if s >= 520:
            notes.append("異族（南蠻、匈奴、烏丸、山越、羌、氐）；每族的 4 筆「武將」記錄同名同頭像，只列一人，劇本資料取第一筆。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows
