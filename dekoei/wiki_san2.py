"""三國志II (san2-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san2-pc98 id: scenarios 1-6 then
TAIKI.DAT, deduplicated by face code (san2.load_san2_jp_persons). Names are the DOS Chinese release's (san2-dos, same
ids and face codes), the PC-98 ones go to nameJa. Layout and evidence: notes/san2.md「koei-wiki 匯出」,
notes/san-attributes.md「三國志II」.

SNDATAn.CIM (0x33AF bytes): u16 year at +2 (the game shows it + 1), 255 person records of 43 bytes from 0x16, 16
factions of 41 bytes from 0x2AF2, 41 provinces of 35 bytes from 0x2D82. Pointers are run-time offsets: person slot
s is at 88 + 43 s, province p (1-41) at 0x2DC4 + 35 (p - 1)."""
import os
import struct

import kaodata_export as ke
import san2
from san_person import s2_format, s2_format_taiki

DATASET = "san2-pc98"
SIZE, PERSONS, SLOTS, BASE = 43, 0x16, 255, 88
FACTIONS, FACTION_SIZE = 0x2AF2, 41  # u16 君主, u16 capital province, u16 軍師 (pointers)
PROVINCES, PROVINCE_SIZE, PROVINCE_BASE = 0x2D82, 35, 0x2DC4  # +2 現役 chain, +6 在野 chain, +16 owner faction
HIDDEN = [(7, "義理"), (8, "人徳"), (9, "野望"), (15, "相性")]


def u16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def _scenario(d):
    """{slot: (record, status, location, faction)} and the faction rulers {faction: slot}."""
    rec = [d[PERSONS + s * SIZE:PERSONS + (s + 1) * SIZE] for s in range(SLOTS)]
    slot = lambda p: (p - BASE) // SIZE  # noqa: E731
    rulers, advisors = {}, set()
    for f in range(16):
        r = d[FACTIONS + f * FACTION_SIZE:][:6]
        if u16(r, 0):
            rulers[f] = slot(u16(r, 0))
            if u16(r, 4):
                advisors.add(slot(u16(r, 4)))
    out = {}
    for k in range(41):
        prov = d[PROVINCES + k * PROVINCE_SIZE:][:PROVINCE_SIZE]
        for chain, at in (("現役", 2), ("在野", 6)):
            p, first = u16(prov, at), True
            while p:
                s = slot(p)
                faction = rec[s][10]
                assert (faction == 255) == (chain == "在野") and s not in out
                if chain == "在野":
                    status = "在野"
                elif rulers.get(faction) == s:
                    status = "君主"
                elif s in advisors:
                    status = "軍師"
                elif first:
                    assert prov[16] == faction
                    status = "太守"
                else:
                    status = "現役"
                out[s] = (rec[s], status, k + 1, faction)
                p, first = u16(rec[s], 0), False
    assert len(out) == next(s for s in range(SLOTS) if rec[s][28:32] == bytes(4))
    return out, rulers


def persons(game_dir):
    jp = san2.load_san2_jp_persons(game_dir)
    face_id = {face: i for i, (face, _) in enumerate(jp)}
    dos = san2.load_san2_persons(os.path.join(game_dir, "..", "san2-dos", "SCENARIO.DAT"),
                                 os.path.join(game_dir, "..", "san2-dos", "TAIKI.DAT"))
    assert [p.face for p in dos] == [f for f, _ in jp]
    first = {}  # id -> the first record (scenario order, then TAIKI)
    scen = []
    for n in range(1, 7):
        with open(os.path.join(game_dir, f"SNDATA{n}.CIM"), "rb") as f:
            d = f.read()
        people, rulers = _scenario(d)
        year = u16(d, 2) + 1
        by_id = {}
        for s, (r, status, location, faction) in people.items():
            i = face_id[u16(r, 26)]
            first.setdefault(i, r)
            by_id[i] = (r, status, location, faction)
        lord_of = {f: face_id[u16(people[s][0], 26)] for f, s in rulers.items()}
        scen.append((year, by_id, lord_of))
    taiki = {}
    with open(os.path.join(game_dir, "TAIKI.DAT"), "rb") as f:
        t = f.read()
    tsize = struct.calcsize(s2_format_taiki)
    for k in range(420):
        r = t[6 + k * tsize:6 + (k + 1) * tsize]
        if r[31:35] == bytes(4):
            break
        i = face_id[u16(r, 29)]
        taiki.setdefault(i, r)
        first.setdefault(i, r[3:])
    assert struct.calcsize(s2_format) == SIZE and len(first) == len(jp)

    rows = []
    for i, (face, name_ja) in enumerate(jp):
        r = first[i]
        name = dos[i]["name"]
        row = {"id": i, "name": name}
        if name_ja != name:
            row["nameJa"] = name_ja
        reading = ke.kana_to_hiragana(r[35:42].split(b"\0")[0].decode("cp932")).strip()
        if reading:
            row["reading"] = reading
        row["born"] = r[25]
        if i in taiki:
            row["debut"] = taiki[i][0]
        row["stats"] = {"知力": r[4], "武力": r[5], "魅力": r[6]}
        row["hidden"] = {**{k: r[o] for o, k in HIDDEN}, "親族": u16(r, 16)}
        out = []
        for n, (year, by_id, lord_of) in enumerate(scen):
            s = {"scenario": n + 1, "year": year}
            if i in by_id:
                rec, status, location, faction = by_id[i]
                s["status"] = status
                if faction != 255:
                    s["lord"] = lord_of[faction]
                s["location"] = location
                if status not in ("君主", "在野"):
                    s["loyalty"] = rec[11]
            elif i in taiki and taiki[i][0] >= year:
                s.update({"status": "未登場", "debut": taiki[i][0]})
                if 1 <= taiki[i][2] <= 41:
                    s["location"] = taiki[i][2]
            else:
                continue
            out.append(s)
        row["scenarios"] = out
        uncertain = ["hidden"]
        if i in taiki:
            uncertain.append("debut")
        if any(s["status"] == "未登場" for s in out):
            uncertain.append("scenarios.debut")
            if any(s["status"] == "未登場" and "location" in s for s in out):
                uncertain.append("scenarios.location")
        if any(s["status"] in ("太守", "軍師") for s in out):
            uncertain.append("scenarios.status")
        row["uncertain"] = uncertain
        notes = []
        if ke.yoshikawa_note(row["name"]):
            notes.append(ke.yoshikawa_note(row["name"]))
        elif i in ke.SAN2_NAME_HISTORICAL:
            notes.append(f"中文版寫法有誤，史書寫法 {ke.SAN2_NAME_HISTORICAL[i]}。")
        if i in ke.SAN2_JP_NAME_HISTORICAL and ke.SAN2_JP_NAME_HISTORICAL[i] != ke.SAN2_NAME_HISTORICAL.get(i):
            notes.append(f"日文版寫法有誤，史書寫法 {ke.SAN2_JP_NAME_HISTORICAL[i]}。")
        if i in taiki and not any(s["status"] != "未登場" for s in out):
            notes.append("只在 TAIKI.DAT（後登場武將表），不在任何劇本的初始資料。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows
