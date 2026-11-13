"""太閤立志傳IV (taikoh4-win, Windows Chinese) for koei-wiki: persons (koei-persons/1).

id is the kaodata taikoh4-win person id, and name is the kaodata name (scenario 3). The three scenarios are SNR1-3.TR_
(koei_games.taikoh4_win_scenario), copied from the ISO's GAME/SNR to games/taikoh4-win. Part 8 of a scenario holds the person records: person p
(2-651) is the 48 bytes at 48 * (p - 2) + 0x26. All fields below were told from the values, not from code:
+6..+10 統率 武力 內政 外交 魅力 (the same in all scenarios), +13 the scenario status (low nibble 0 is the head of a
clan, 4 is not on the map), +16 the clan (61 none). Field sources: notes/taikoh4.md「koei-wiki 匯出」."""
import os

import kaodata_export as ke
import koei_games as kg

DATASET = "taikoh4-win"
STATS = ("統率", "武力", "內政", "外交", "魅力")  # TAIKOU4.EXE 0x1F4C5C
RECORD, RECORDS, FIRST = 48, 650, 0x26
NO_CLAN = 61
# from the scenario texts (part 0): after 桶狹間; 謙信 marching on 能登 and 尼子 revived by 秀吉 (1577, inferred);
# after 秀吉's death
YEARS = {1: 1560, 2: 1577, 3: 1598}


def _raw(game_dir, k):
    path = os.path.join(game_dir, f"SNR{k}.TR_")
    with open(path, "rb") as f:
        return f.read()


def _record(part8, p):
    if not 2 <= p < RECORDS + 2:
        return None
    r = part8[RECORD * (p - 2) + FIRST:][:RECORD]
    return r if len(r) == RECORD else None


def persons(game_dir):
    with open(os.path.join(game_dir, "TAIKOU4.EXE"), "rb") as f:
        exe = f.read()
    raws = {k: _raw(game_dir, k) for k in YEARS}
    part8 = {k: kg.taikoh4_win_scenario(raw, exe)[8] for k, raw in raws.items()}
    names_by = {k: [n for n, _, _ in kg.load_taikoh4_win_persons(raw, exe)] for k, raw in raws.items()}
    names = names_by[3]
    rows = []
    for p, name in enumerate(names):
        if p == 1 or 600 <= p < 650 or p in ke.TAIKOH4_WIN_TOWNSFOLK or p == ke.TAIKOH4_WIN_NEW:
            continue  # the same persons as the kaodata dataset
        row = {"id": p, "name": name or ke.TAIKOH4_WIN_PROTAGONIST}
        recs = {k: _record(part8[k], p) for k in YEARS}
        r = recs[3]
        notes = []
        if r and any(r[6:11]):
            row["stats"] = dict(zip(STATS, r[6:11]))
        scenarios = []
        for k, rec in recs.items():
            if rec and any(rec[6:11]) and rec[16] != NO_CLAN and rec[13] & 0xF == 0:
                scenarios.append({"scenario": k, "year": YEARS[k], "lord": p, "status": "大名"})
        if scenarios:
            row["scenarios"] = scenarios
        uncertain = []
        if "stats" in row:
            uncertain.append("stats")
        if scenarios:
            uncertain += ["scenarios.status", "scenarios.year"]
        older = {}
        for k in (1, 2):
            if names_by[k][p] and names_by[k][p] != name:
                older.setdefault(names_by[k][p], []).append(str(k))
        if older:
            notes.append("、".join(f"劇本 {'、'.join(ks)} 叫{n}" for n, ks in older.items()) + "。")
        if p == 0:
            notes.append("主角，名字由玩家決定，預設木下藤吉郎；劇本資料沒有他的能力。")
        if uncertain:
            row["uncertain"] = uncertain
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows
