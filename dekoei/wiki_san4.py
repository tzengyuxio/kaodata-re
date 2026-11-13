"""三國志IV PK (san4pk-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san4pk-pc98 id: the 462
scenario people (SNDATA.S4 then TAIKI.S4 of the 10 scenarios, deduplicated by (face code, name), as
kaodata_export.build_san4) and the 117 水滸伝 officers of NBDATA.SUI (462-578). Names are the DOS Chinese PK's
(san4pk-dos, same ids and faces), the PC-98 ones go to nameJa. Layout and evidence: notes/san4.md「koei-wiki 匯出」,
notes/san-attributes.md「三國志IV」.

Ability record a+ (20 bytes): +2-6 統率 武力 知力 政治 魅力, +11 忠誠, +12 city (= places id), +13 faction (255 none),
+14 u32 特殊能力 bits, +18 low nibble 身分 (MAIN.EXE DS:0x37EE table, read at 0e7f:99A0 as a+18 & 0xF). Person
record p+ (30 bytes): +9 reading (11 bytes half-width kana), +20 face code, +22 血縁, +24 相性, +25 born - 100, +27 24
bits of 義理 野望 冷静 勇猛. Scenario year: u16 at part offset 0x584."""
import os

import kaodata_export as ke
import sango

DATASET = "san4pk-pc98"
YEAR = 0x584
# scenario 10 (237) has all 400 people in city 0 under one ruler (劉諶): not a starting placement, so it is left out
SKIPPED = 9
STATUS = "君主 将軍 軍師 侍中 一般 在野 未発 死亡 待機 太守 捕虜 皇帝".split()
SKILLS = "外交 情報 人材 製造 作敵 駆虎 流言 焼計 諜報 歩兵 騎兵 弓兵 海戦 火計 落石 同討 天変 風変 混乱 連環 落雷 修復 罵声 虚報".split()
TRAITS = [("義理", 0, 4), ("野望", 4, 4), ("冷静", 11, 3), ("勇猛", 14, 3)]  # (name, first bit, bits) of p+27


def _skills(a):
    bits = int.from_bytes(a[14:18], "little")
    return [s for i, s in enumerate(SKILLS) if bits >> (i if i <= 8 else i + 3) & 1]


def _traits(p):
    bits = int.from_bytes(p[27:30], "little")
    return {k: bits >> b & (1 << n) - 1 for k, b, n in TRAITS}


def _scenarios(game_dir):
    """[(year, [(name, ability, person)] of SNDATA, [same] of TAIKI)] for the 10 scenarios; san4_records yields each
    part's SNDATA records (as many as its person table) before its TAIKI ones."""
    with open(os.path.join(game_dir, "SNDATA.S4"), "rb") as f:
        sn = sango.san4_parts(f.read())
    counts = []
    for part in sn:
        start = len(part)
        while start >= 30 and part[start - 30] >= 0x80 and part[start - 10:start - 8] != b"\xff\xff":
            start -= 30
        counts.append((len(part) - start) // 30)
    out = [(int.from_bytes(part[YEAR:YEAR + 2], "little"), [], []) for part in sn]
    seen = [0] * len(sn)
    for scenario, name, a, p in sango.san4_records(os.path.join(game_dir, "SNDATA.S4"),
                                                    os.path.join(game_dir, "TAIKI.S4"), True):
        k = scenario - 1
        (out[k][1] if seen[k] < counts[k] else out[k][2]).append((name, a, p))
        seen[k] += 1
    return out


def persons(game_dir):
    zh, _ = ke.build_san4(os.path.join(game_dir, "..", "san4pk-dos"), pk=True)
    ja, _ = ke.build_san4(game_dir, pc98=True, pk=True)
    zh, ja = zh["characters"], ja["characters"]
    assert len(zh) == len(ja) == 579 and all(a["face"] == b["face"] for a, b in zip(zh, ja))
    scen = _scenarios(game_dir)
    # ids as build_san4: first appearance of (face code, name) in scenario order, SNDATA before TAIKI
    ids, first = {}, {}
    for _, people, later in scen:
        for name, a, p in people + later:
            key = (int.from_bytes(p[20:22], "little"), name)
            if key not in ids:
                ids[key] = len(ids)
                first[ids[key]] = (a, p)
    assert len(ids) == 462 and all(ja[i]["name"] == n for (_, n), i in ids.items())
    code_of = {i: c for (c, _), i in ids.items()}
    by_face = {}
    for i, c in code_of.items():
        by_face.setdefault(c, i)
    kin = {i: int.from_bytes(p[22:24], "little") for i, (_, p) in first.items()}

    per = []  # per scenario: {id: (ability, status word)}, {faction: ruler id}, {id} of TAIKI
    for year, people, later in scen:
        here, rulers = {}, {}
        for name, a, p in people:
            i = ids[(int.from_bytes(p[20:22], "little"), name)]
            if i in here:
                continue  # the 4 異民族 have several records of one name and face (one army each)
            here[i] = a
            if a[18] & 0xF == 0 and a[13] != 0xFF:
                assert rulers.setdefault(a[13], i) == i
        taiki = {ids[(int.from_bytes(p[20:22], "little"), name)] for name, a, p in later} - set(here)
        per.append((year, here, rulers, taiki))

    rows = []
    for i in range(579):
        name = zh[i]["name"]
        row = {"id": i, "name": name}
        if ja[i]["name"] != name:
            row["nameJa"] = ja[i]["name"]
        notes = []
        for c, label in ((zh[i], "中文版"), (ja[i], "日文版")):
            if "nameHistorical" in c:
                notes.append(f"{label}寫法有誤，史書寫法 {c['nameHistorical']}。")
        if i >= 462:
            row.update(_suikoden(game_dir, i - 462))
            notes.append("威力加強版 NBDATA.SUI 的水滸伝武將，不在任何劇本裡（新武將登錄時可以選用）。")
            row["notes"] = "".join(notes)
            rows.append(row)
            continue
        a, p = first[i]
        reading = ke.kana_to_hiragana(p[9:20].split(b"\0")[0].decode("cp932")).strip()
        if reading:
            row["reading"] = reading
        row["born"] = p[25] + 100
        row["stats"] = dict(zip(sango.SAN4_STATS, a[2:7]))
        skills = _skills(a)
        if skills:
            row["skills"] = {"特殊能力": skills}
        row["hidden"] = {"相性": p[24], **_traits(p), "血縁": kin[i]}
        # 血縁: a person's face code makes that person the father (孫策 -> 孫堅); 1000 and up is a group number shared
        # by kin whose father is not in the game (袁紹 and 袁術 1001); same father = siblings
        relations = {}
        if kin[i] in by_face and by_face[kin[i]] != i:
            relations["father"] = [by_face[kin[i]]]
            sib = sorted(j for j, k in kin.items() if k == kin[i] and j != i)
            if sib:
                relations["siblings"] = sib
        elif kin[i] != 0xFFFF and kin[i] >= 1000:
            relations["clan"] = kin[i]
        children = sorted(j for j, k in kin.items() if k == code_of[i] and j != i)
        if children:
            relations["children"] = children
        if relations:
            row["relations"] = relations
        out = []
        for n, (year, here, rulers, taiki) in enumerate(per):
            if n == SKIPPED or i not in here:
                continue
            s = {"scenario": n + 1, "year": year}
            r = here[i]
            s["status"] = STATUS[r[18] & 0xF]
            if r[13] != 0xFF and r[13] in rulers:
                s["lord"] = rulers[r[13]]
            s["location"] = r[12]
            if r[18] & 0xF not in (0, 5, 6):
                s["loyalty"] = r[11]
            if row["stats"] != dict(zip(sango.SAN4_STATS, r[2:7])):
                s["stats"] = dict(zip(sango.SAN4_STATS, r[2:7]))
            out.append(s)
        if out:
            row["scenarios"] = out
        later = [n + 1 for n, (_, here, _, taiki) in enumerate(per) if i in taiki and n != SKIPPED]
        if later:
            notes.append(f"劇本 {'、'.join(map(str, later))} 是後登場武將（TAIKI.S4），登場年的規則沒追，所以這些劇本沒列。")
        row["uncertain"] = ["hidden"] + (["relations"] if relations else [])
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def _suikoden(game_dir, k):
    """reading, stats and skills of NBDATA.SUI officer k (117 x 20-byte ability records, then 117 x 30-byte persons)."""
    with open(os.path.join(game_dir, "NBDATA.SUI"), "rb") as f:
        nb = f.read()
    a, p = nb[k * 20:k * 20 + 20], nb[117 * 20 + k * 30:][:30]
    row = {}
    reading = ke.kana_to_hiragana(p[9:20].split(b"\0")[0].decode("cp932")).strip()
    if reading:
        row["reading"] = reading
    row["stats"] = dict(zip(sango.SAN4_STATS, a[2:7]))
    skills = _skills(a)
    if skills:
        row["skills"] = {"特殊能力": skills}
    return row
