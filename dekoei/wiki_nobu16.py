"""信長の野望・新生 with PK (nobu16pk-win, Steam 1336980): persons, castles, 列伝 and 家宝 for koei-wiki
(koei-persons/1, koei-places/1, biographies, koei-items/1). Fields and evidence: notes/nobu16.md「koei-wiki 匯出」.

- Scenarios: SCENARIO_PK/scedaPK??.n16, an 'LWC\\x1a' block at 0x3805 (ls11.lwc_decode); raw +0x14 u32 is the scenario
  number, its name is msgdata row 15113 + number; the start year is the u16 at (decoded size - 0x734A).
- Persons: 4250 slots from decoded 0x0C (variable length, see persons_raw); a slot is also the 列伝 row and the id.
- Clans: 21-byte records after the persons, +1 u16 record number, +6 u32 clan id,
  +10 u16 leader slot (_clans).
- Names: MSG_PK/<lang>/msgdata.bin, one XL table; a person's 姓/名 are rows, readings at row + 3332; castle k is row
  9151 + k (k < 77) or 9151 + k - 8 (k >= 85), checked against 大志's castle names of the same id (CASTLES).
"""
import os
import struct

import ls11
import nobu16_extras as X

SCENARIOS = ["01", "02", "04", "03", "05", "06", "10", "11", "12", "13", "14"]  # file numbers, in scenario order
SCENARIO_NAMES = 15113  # msgdata row of scenario 0
SLOTS = 4250
PERSON_SLOTS = range(0, 2400)  # 武将 and 姫; 2400-2532 are 国衆頭領, 2780-2959 culture and generic people
CULTURE = range(2780, 2960)  # taken only when the slot has a 列伝
READING = 3332  # msgdata row offset of a name's reading
CASTLE_NAMES = 9151
# castle ids whose msgdata name (row 9151 + id, or + id - 8 from 85 on) equals 大志's castle of the same id; the others
# (32, 52, 75, 77-85, 89, 90, 92, 94, 96, 107, 110, 115, 121, 125, 128, 140-142, 145, 146, 149, 153, 158, 159, 164,
# 168, 171, 172, 176, 178, 182, 186, 188, 189, 193, 198-200, 202, 203, 207, 210-213, 216, 219, 227, 256, 266, 268,
# 274, 284, 286, 288, 289, 294, 296, 298, 299, 303-306, 310, 314, 316, 317, 321, 323) are left out: 安祥 (186 by its
# residents and 大志) is row 347, so the rows are not in id order everywhere
CASTLES = [(0, 31), (33, 51), (53, 74), (76, 76), (86, 88), (91, 91), (93, 93), (95, 95), (97, 106), (108, 109),
           (111, 114), (116, 120), (122, 124), (126, 127), (129, 139), (143, 144), (147, 148), (150, 152), (154, 157),
           (160, 163), (165, 167), (169, 170), (173, 175), (177, 177), (179, 181), (183, 185), (187, 187), (190, 192),
           (194, 197), (201, 201), (204, 206), (208, 209), (214, 215), (217, 218), (220, 226), (228, 255), (257, 265),
           (267, 267), (269, 273), (275, 283), (285, 285), (287, 287), (290, 293), (295, 295), (297, 297), (300, 302),
           (307, 309), (311, 313), (315, 315), (318, 320), (322, 322), (324, 324)]
CLAN_REC = 21
# skills (fixed part): +38 u8 戦法 (msgdata SENPO_NAMES + n, 0-95; 0xFF none), +60/+62/+64 u16 特性 (TRAIT_NAMES + n,
# 0xFFFF empty), +52 u8 主義; checked with 柴田勝家 and 宮部継潤 (notes/nobu16.md「人物欄位」)
SENPO_AT, SENPO_NAMES, SENPO_COUNT = 38, 15194, 96
TRAITS_AT, TRAIT_NAMES = (60, 62, 64), 24416
IDEOLOGY_AT, IDEOLOGY = 52, {1: "保守", 2: "中道", 3: "革新"}
KOKUJIN = 15  # fixed +6 of a 国衆 member; +10 is then the 国衆 number (頭領 slot 2400 + number)
STATUS = {7: "家臣", 3: "浪人", 6: "姫"}
ITEM_NAMES, ITEM_COUNT = X.ITEM_NAMES, X.ITEM_COUNT


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def scenario(game_dir, f):
    """(number, year, decoded data) of SCENARIO_PK/scedaPK<f>.n16"""
    with open(os.path.join(game_dir, "SCENARIO_PK", f"scedaPK{f}.n16"), "rb") as fh:
        raw = fh.read()
    number, = struct.unpack_from("<I", raw, 0x14)
    data = ls11.lwc_decode(raw[raw.index(b"LWC\x1a"):])
    return number, _u16(data, len(data) - 0x734A), data


def persons_raw(data):
    """[(header 5 u16, [4 lists of u16], gap 6 bytes, fixed 85 bytes)] for the 4250 slots, and the end offset"""
    p, out = 0x0C, []
    for _ in range(SLOTS):
        head = struct.unpack_from("<5H", data, p)
        q, lists, gap = p + 10, [], b""
        for j in range(4):
            if j == 3:
                gap, q = data[q:q + 6], q + 6
            c, = struct.unpack_from("<I", data, q)
            lists.append(struct.unpack_from(f"<{c}H", data, q + 4))
            q += 4 + 2 * c
        out.append((head, lists, gap, data[q:q + 85]))
        p = q + 85
    return out, p


def _clans(data, recs, start):
    """clan id -> leader slot from the 21-byte records after the persons: +1 u16 record number, +6 u32 clan id, +10 u16
    leader slot (whose person record has that clan at +0); record 0's +2 u32 is the record count"""
    def ok(p, k):
        cid, = struct.unpack_from("<I", data, p + 6)
        lead = _u16(data, p + 10)
        return (k == 0 or _u16(data, p + 1) == k) and lead < SLOTS and _u16(recs[lead][3], 0) == cid

    p = start
    while not all(ok(p + CLAN_REC * k, k) for k in range(4)):
        p += 1
    n, = struct.unpack_from("<I", data, p + 2)
    assert all(ok(p + CLAN_REC * k, k) for k in range(n))
    return {struct.unpack_from("<I", data, p + CLAN_REC * k + 6)[0]: _u16(data, p + CLAN_REC * k + 10)
            for k in range(n)}


def _castle_ids():
    return [k for a, b in CASTLES for k in range(a, b + 1)]


def castle_names(game_dir, lang="TC"):
    rows = X.strings(game_dir, lang, "msgdata")
    return {k: rows[CASTLE_NAMES + (k if k < 77 else k - 8)] for k in _castle_ids()}


def places(game_dir, out_dir):
    names, ja = castle_names(game_dir), castle_names(game_dir, "JP")
    used = {}
    for f in SCENARIOS:
        number, _, data = scenario(game_dir, f)
        for _, _, _, t in persons_raw(data)[0]:
            if t[6] != KOKUJIN and t[28] in (7, 3, 6):
                used.setdefault(_u16(t, 10), set()).add(number)
    rows = []
    for k, name in names.items():
        row = {"id": k, "name": name, "level": "城", "uncertain": ["level"],
               "notes": f"城號 {k}（人物固定部 +10）；名字取 msgdata 第 {CASTLE_NAMES + (k if k < 77 else k - 8)} 列，"
                        "和大志同一號的城名相同才收。城、館等的分類與所屬國沒找到，level 一律寫城。"}
        if ja[k] != name:
            row["nameJa"] = ja[k]
        if k not in used:
            row["notes"] += "PK 劇本開局沒有武將在這座城。"
        rows.append(row)
    return rows


def _names(game_dir):
    tc, ja = X.strings(game_dir, "TC", "msgdata"), X.strings(game_dir, "JP", "msgdata")

    def name(rows, head, reading=False):
        parts = [rows[x + (READING if reading else 0)] for x in head[:2] if x != 0xFFFF]
        return "".join(parts)
    return tc, ja, name


def persons(game_dir):
    tc, ja, name = _names(game_dir)
    bios_tc = X.strings(game_dir, "TC", "msgbre")
    scen = [scenario(game_dir, f) for f in SCENARIOS]
    recs = []
    for number, year, data in scen:
        r, end = persons_raw(data)
        recs.append((number, year, r, _clans(data, r, end)))
    main = recs[0][2]  # 信長元服 (1546): names, stats and relations
    msg = X.strings(game_dir, "JP", "msgdata")
    people = [k for k in list(PERSON_SLOTS) + list(CULTURE)
              if main[k][0][0] != 0xFFFF and (k in PERSON_SLOTS or bios_tc[k].strip())]
    known = set(people)
    fathers = {k: _u16(main[k][2], 0) for k in people}
    castles = set(_castle_ids())
    rows = []
    for k in people:
        head, lists, gap, t = main[k]
        row = {"id": k, "name": name(tc, head)}
        if name(ja, head) != row["name"]:
            row["nameJa"] = name(ja, head)
        row["reading"] = name(ja, head, True)
        if 0xFFFF not in head[:2] and tc[head[0]] and row["name"].startswith(tc[head[0]]) and tc[head[1]]:
            row["familyName"] = tc[head[0]]  # head[0] is the 姓 row, head[1] the 名 row
            if ja[head[0] + READING] and row["reading"].startswith(ja[head[0] + READING]):
                row["familyReading"] = ja[head[0] + READING]
        row["born"], row["died"] = _u16(t, 22), _u16(t, 26)
        row["stats"] = {"統率": t[46], "武勇": t[47], "知略": t[48], "政務": t[49]}
        if t[IDEOLOGY_AT] in IDEOLOGY:
            row["more"] = {"主義": IDEOLOGY[t[IDEOLOGY_AT]]}
        skills = {}
        if t[SENPO_AT] < SENPO_COUNT and msg[SENPO_NAMES + t[SENPO_AT]]:
            skills["戦法"] = [msg[SENPO_NAMES + t[SENPO_AT]]]
        traits = [msg[TRAIT_NAMES + _u16(t, o)] for o in TRAITS_AT if _u16(t, o) != 0xFFFF]
        if traits:
            skills["特性"] = traits
        if skills:
            row["skills"] = skills
        relations = {}
        father = fathers[k]
        if father in known:
            relations["father"] = [father]
        children = [j for j, v in fathers.items() if v == k]
        if children:
            relations["children"] = children
        siblings = [j for j, v in fathers.items() if j != k and father != 0xFFFF and v == father]
        if siblings:
            relations["siblings"] = siblings
        spouses = list(dict.fromkeys(_u16(r[k][2], 4) for _, _, r, _ in recs if _u16(r[k][2], 4) in known))
        if spouses:
            relations["spouse"] = spouses
        if _u16(t, 12) != 0xFFFF:
            relations["clan"] = _u16(t, 12)
        if relations:
            row["relations"] = relations
        row["scenarios"] = []
        for number, year, r, clans in recs:
            ts = r[k][3]
            st, clan, loc = ts[28], _u16(ts, 0), _u16(ts, 10)
            sc = {"scenario": number, "year": year}
            if st == 7 and ts[6] == KOKUJIN:
                sc["status"] = "国衆"
            elif st in STATUS:
                lord = clans.get(clan)
                if st == 7 and lord in known:
                    sc["lord"] = lord
                sc["status"] = "大名" if lord == k else STATUS[st]
                if loc in castles:
                    sc["location"] = loc
            elif st in (0, 1) and _u16(ts, 26) >= year:
                sc["status"] = "未登場"
                sc["debut"] = _u16(ts, 24)
            else:  # 13: dead or not in this scenario
                continue
            row["scenarios"].append(sc)
        row["uncertain"] = ["relations.spouse", "relations.clan", "scenarios.status", "scenarios.debut"]
        row["notes"] = ("名字與固定欄位取劇本 1（1546 信長元服），scenarios 是 PK 的 11 個劇本。能力 +46–49（統率、武勇、知略、政務）、主義 +52、"
                        "戦法 +38、特性 +60／+62／+64 對過柴田勝家、宮部継潤的武將情報截圖（全同）；其餘欄位是從資料推的，"
                        "沒有讀程式：生年 +22、登場年 +24、歿年 +26、所屬勢力 +0、家 +12（relations.clan）、"
                        "所在城 +10；父、配偶是最後一個陣列前 6 bytes 的 +0、+4。status 依 +28：7 仕官（勢力的当主是自己時寫大名；"
                        "+6 是 15 的是国衆的成員）、3 浪人、6 姫、0／1 未登場（debut 用 +24），13 不列。"
                        "所在城只寫城名對得上大志同號城的那些（見 places 的 notes）。")
        rows.append(row)
    return rows


def bios(game_dir):
    rows = X.strings(game_dir, "JP", "msgbre")
    return {k: [("單段", X.text(v).replace("\n", ""))] for k, v in enumerate(rows) if v.strip()}


def bio_names(game_dir):
    _, ja, name = _names(game_dir)
    _, _, data = scenario(game_dir, SCENARIOS[0])
    recs = persons_raw(data)[0]
    return {k: name(ja, recs[k][0]) for k in bios(game_dir) if k < SLOTS and recs[k][0][0] != 0xFFFF}


BIO_LANG = "ja"  # as 大志 (wiki_nobu15); msgbre also has TC


def items(game_dir):
    """koei-items/1 rows: 家宝 names (msgdata rows 14119-14240) and descriptions (msgire), Japanese and 繁中"""
    names, names_zh = X.strings(game_dir, "JP", "msgdata"), X.strings(game_dir, "TC", "msgdata")
    desc, desc_zh = X.strings(game_dir, "JP", "msgire"), X.strings(game_dir, "TC", "msgire")
    assert len(desc) == ITEM_COUNT
    rows = []
    for k in range(ITEM_COUNT):
        rows.append({"id": k, "name": names[ITEM_NAMES + k], "nameZh": names_zh[ITEM_NAMES + k],
                     "description": X.text(desc[k]).replace("\n", ""),
                     "descriptionZh": X.text(desc_zh[k]).replace("\n", ""),
                     "notes": "名稱取 MSG_PK/<語言>/msgdata 第 14119 列起，說明取 msgire（日文、繁中逐列對上）；"
                              "種類、等級、效果與各劇本的持有者在資料裡沒找到。"})
    return rows
