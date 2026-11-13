"""三國志III (san3-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san3-pc98 id (531 people, scenarios
1-6 deduplicated by face code, kaodata_export.san3_characters). The data comes from the PC-98 SNDATA?B.CIM (600 x 62
bytes); name is the DOS Chinese version's spelling of the same face code (the two sets of face codes are the same, one
to one), nameJa the PC-98 one. Field sources: notes/san3.md「koei-wiki 匯出」, notes/san-attributes.md「三國志III」."""
import os
import struct

import kaodata_export as ke
import san3
import wiki_stats

# SNDATA?.CIM +2 u16 is the year before the start: scenario 1 stores 188 and starts in 189 January (capture main_005)
# PC-98 MAIN.EXE DGROUP 0x27FE: the 身分 names by +16; 0x8124 shows 太守 instead for a city's governor (not exported)
RANKS = {0: "君主", 1: "軍師", 2: "将軍", 3: "武官", 4: "文官", 5: "在野"}
HIDDEN, ABSENT = 6, 7  # 6: put in the city's second list (MAIN.EXE 0x97B3), 「未発見武将」 (🟡); 7: not on the map
# PC-98 scenario 1 gives 車胄 楊懐's face code 0x82CB (DOS: 0x9831): that record is 車胄, not 楊懐
SAME_CODE = {(1, 0x82CB, "車胄"): 0x9831}


def persons(game_dir):
    chars = ke.san3_characters(game_dir, True)
    zh = dict(ke.san3_characters(os.path.join(game_dir, "..", "san3-dos")))
    assert set(zh) == {c for c, _ in chars}
    cid = {c: i for i, (c, _) in enumerate(chars)}
    stats = {i: st for i, _, st in wiki_stats.stats_san3_pc98(game_dir)}
    scen = []  # per scenario: (year, {character id: record})
    for k in range(1, 7):
        with open(os.path.join(game_dir, f"SNDATA{k}.CIM"), "rb") as f:
            year = struct.unpack_from("<H", f.read(4), 2)[0] + 1
        with open(os.path.join(game_dir, f"SNDATA{k}B.CIM"), "rb") as f:
            data = f.read()
        recs = {}
        for i in range(600):
            r = data[i * san3.PC98_RECORD_SIZE:(i + 1) * san3.PC98_RECORD_SIZE]
            if r[0x31:0x37] == bytes(6):
                continue
            code = struct.unpack_from("<H", r, 2)[0]
            code = SAME_CODE.get((k, code, san3.decode_pc98_name(r[0x31:0x37])), code)
            assert cid[code] not in recs
            recs[cid[code]] = r
        scen.append((year, recs))
    rulers = [{r[27]: i for i, r in recs.items() if r[16] == 0} for _, recs in scen]

    rows = []
    for i, (code, name_ja) in enumerate(chars):
        row = {"id": i, "name": zh[code]}
        if name_ja != zh[code]:
            row["nameJa"] = name_ja
        rec = next(recs[i] for _, recs in scen if i in recs)
        row["born"] = rec[37]
        row["stats"] = stats[i]
        out, first = [], None
        for k, (year, recs) in enumerate(scen):
            r = recs.get(i)
            if r is None or r[16] == ABSENT:
                continue
            first = k if first is None else first
            s = {"scenario": k + 1, "year": year, "month": 1, "location": r[26],
                 "status": "未発見" if r[16] == HIDDEN else RANKS[r[16]]}
            if r[16] == 0:
                s["lord"] = i
            elif r[16] < 5 and r[27] in rulers[k]:
                s["lord"] = rulers[k][r[27]]
                s["loyalty"] = r[25]
            out.append(s)
        if first is not None:
            row["more"] = {"年齢": scen[first][0] - row["born"]}
        row["hidden"] = {"相性": rec[23], "義理": rec[24]}
        if rec[31] != 0xFF:
            row["relations"] = {"clan": rec[31]}
        if out:
            row["scenarios"] = out
        row["uncertain"] = ["hidden.相性", "hidden.義理"] + (["relations.clan"] if "relations" in row else []) + \
            (["scenarios.status"] if any(s["status"] == "未発見" for s in out) else [])
        notes = []
        if first is not None and first:
            notes.append(f"more.年齢取劇本 {first + 1}（第一個在地圖上的劇本）。")
        if not out:
            notes.append("六個劇本開始時都不在地圖上（身分 7）；遊戲中途怎麼登場沒追。")
        if any(s["status"] == "未発見" for s in out):
            notes.append("「未発見」是身分 6：在城裡但還沒被找到的在野武將（遊戲有「未発見武将」一詞，對應是推定）。")
        if code in ke.SAN3_NAME_HISTORICAL:
            notes.append(f"中文版寫法的史書寫法 {ke.SAN3_NAME_HISTORICAL[code]}。")
        if code in ke.SAN3_PC98_NAME_HISTORICAL:
            notes.append(f"日文版寫法的史書寫法 {ke.SAN3_PC98_NAME_HISTORICAL[code]}。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows
