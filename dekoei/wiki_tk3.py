"""提督の決断III (tk3pk-pc98; tk3-pc98 reads the same MAIN.EXE table) for koei-wiki: persons (koei-persons/1). id is
the kaodata id, the face: 0-110 the MAIN.EXE people table (0-78 admirals, 79-94 Japanese generals, 95-110 Allied
generals), 197-203 the PK's German and Soviet generals (SNDATA2.TK3), 141-164 the heads of state (MESSAGE.TK3 part 0;
152 K.デーニッツ is admiral 78). Only the Japanese release exists. Field sources: notes/koei-games.md「提督の決断III」
「koei-wiki 匯出」.

The people records hold the name, +15 the nationality (MESSAGE.TK3 part 4: 1 日本 … 7 ドイツ) and +25 the face; the
abilities the game lists (MESSAGE.TK3 part 3: 階級 役職 任務 戦果 砲撃 水雷 航空 潜水 陸戦 勲章 性格) are not in these
records and were not found, so there are no stats."""

import kaodata_export as ke
import koei_games as kg
from common import read_file

DATASET = "tk3pk-pc98"
ADMIRALS = 79  # records 0-78; 79-110 are army generals
NATIONALITY = 15
SERVICE = ("海軍", "陸軍")  # MESSAGE.TK3 part 7, 144-145


def _nationality(data, offset, record, nations):
    return nations[data[offset + record * kg.TK3_PC98_RECORD + NATIONALITY] - 1]


def persons(game_dir):
    exe, message = read_file(game_dir, "MAIN.EXE"), read_file(game_dir, "MESSAGE.TK3")
    sndata2 = read_file(game_dir, "SNDATA2.TK3")
    nations = kg.tk3_pc98_messages(message, 4)
    rows = []
    for k, (name, face) in enumerate(kg.load_tk3_pc98_persons(exe, ke.TK3PK_PC98_PEOPLE)):
        rows.append({"id": face, "name": name, "more": {"軍籍": SERVICE[k >= ADMIRALS],
                                                         "国籍": _nationality(exe, ke.TK3PK_PC98_PEOPLE, k, nations)}})
    for offset, records in ke.TK3PK_PC98_SCENARIO_PEOPLE:
        people = kg.load_tk3_pc98_persons(sndata2, offset)
        for k in records:
            name, face = people[k]
            rows.append({"id": face, "name": name, "more": {"軍籍": "陸軍", "国籍": _nationality(sndata2, offset, k, nations)},
                         "notes": "パワーアップキットの劇本（SNDATA2.TK3）才有的將領。"})
    admiral, leader = ke.TK3_PC98_DOENITZ
    for j, name in enumerate(kg.load_tk3_pc98_leaders(message)):
        face = ke.TK3_PC98_LEADER_FACES + j
        if face == leader:
            next(r for r in rows if r["id"] == admiral)["notes"] = f"元首的頭像 {leader} 也是他（元首名單裡的 K.デーニッツ）。"
            continue
        rows.append({"id": face, "name": name, "notes": "MESSAGE.TK3 的各國元首名單；國籍與役職沒有對應的記錄。"})
    for r in (r for r in rows if "more" in r):
        r["notes"] = "能力（砲撃、水雷、航空、潜水、陸戦、階級、性格）不在人物表裡，還沒找到。" + r.get("notes", "")
    return sorted(rows, key=lambda r: r["id"])
