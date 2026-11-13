"""三國志 (san1-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san1-pc98 id (1-255, the FC order).
Names and readings come from the PC-98 SAVEDATA slot 0 (the PC-98 scenario files are encoded); everything else from
the 5 scenarios of the DOS English SINADATA.DAT (12490 bytes each, the 255 x 32-byte s1_format records at +4326),
whose face codes match the PC-98 persons one by one. Field sources: notes/san1.md「koei-wiki 匯出」,
notes/san-attributes.md「三國志（I，san1）」."""
import os

import kaodata_export as ke
import san1
import wiki_stats

SCENARIO_SIZE = 12490
# DOS SANMAIN strings (PC-98 SANMAIN.EXE): 君主, 現役武将, 在野武将 (the 「将数」 summary screen)
RULER, SERVING, FREE = "君主", "現役武将", "在野武将"


def _scenarios(game_dir):
    with open(os.path.join(game_dir, "..", "san1-dos", "SINADATA.DAT"), "rb") as f:
        data = f.read()
    out = []
    for k in range(5):
        s = data[k * SCENARIO_SIZE:(k + 1) * SCENARIO_SIZE]
        assert s[0] == k + 1
        year = int.from_bytes(s[8:10], "little")  # 189 195 201 208 215
        out.append((year, [s[san1.DOS_PERSONS + i * 32:][:32] for i in range(255)]))
    return out


def persons(game_dir):
    with open(os.path.join(game_dir, "SAVEDATA"), "rb") as f:
        save = f.read()
    stats = {i: (name, st) for i, name, st in wiki_stats.stats_san1_pc98(game_dir)}
    scen = _scenarios(game_dir)
    rows = []
    for i in range(255):
        pid = i + 1
        name, st = stats[pid]
        rec = save[san1.PC98_PERSONS + i * san1.PC98_PERSON_SIZE:][:san1.PC98_PERSON_SIZE]
        row = {"id": pid, "name": name}
        reading = ke.kana_to_hiragana(rec[:8].split(b"\0")[0].decode("cp932").strip())
        if reading:
            row["reading"] = reading
        # the ruler of each nation in each scenario
        out, first = [], None
        for k, (year, P) in enumerate(scen):
            p = P[i]
            if not p[24]:  # no 國: not on the map in this scenario
                continue
            first = k if first is None else first
            rulers = {q[25]: j + 1 for j, q in enumerate(P) if q[19] & 2}
            s = {"scenario": k + 1, "year": year, "location": p[24]}
            if p[19] & 2:
                s["status"] = RULER
                s["lord"] = pid
            elif p[25]:
                s["status"] = SERVING
                s["lord"] = rulers[p[25]]
                s["loyalty"] = p[18]
            else:
                s["status"] = FREE
            out.append(s)
        if first is not None:
            year, P = scen[first]
            row["born"] = year - P[i][12]
        row["stats"] = st
        if first is not None:
            row["more"] = {"年齢": scen[first][1][i][12]}
        if out:
            row["scenarios"] = out
        if any("loyalty" in x for x in out):
            row["uncertain"] = ["scenarios.loyalty"]
        notes = []
        if first is not None:
            notes.append(f"born 是劇本年減年齢（五個劇本算出來都一樣）；more.年齢取劇本 {first + 1}（第一個登場的劇本）。")
        if not out:
            notes.append("五個劇本開始時都不在地圖上。")
        if ke.yoshikawa_note(row["name"]):
            notes.append(ke.yoshikawa_note(row["name"]))
        if pid in ke.SAN1_PC98_NAME_HISTORICAL:
            notes.append(f"史書寫法 {ke.SAN1_PC98_NAME_HISTORICAL[pid]}。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows
