"""信長の野望・戦国群雄伝 (nobu3-pc98) for koei-wiki: persons (koei-persons/1) and places (koei-places/1). The data
is the PC-98 scenarios; name is the DOS 中文版's (nobu3-dos beside it, the same records in the same slots), nameJa the
PC-98 Japanese. Field sources and how sure they are: notes/nobu3.md「人物欄位」「地理」「koei-wiki 匯出」."""
import os
import struct
import unicodedata

import koei_games

# SNDATA1/2.CIM (PC-98 and DOS alike): +4 u16 year; lords from 0x4C (46 bytes: +0 the lord's person pointer, 0 ends);
# 38 國 from 0x722 (41 bytes: +2 name 9 bytes, +27 lord pointer, +29 城主 pointer, +31 7 neighbours: low 6 bits
# the 國 (0-based), FF none); persons from 0xD38 (PC-98 38 bytes, DOS 44: names 9 + 7, DOS 11 + 11; the fields
# below are PC-98 offsets, DOS + 6): +16 年齢 in the debut year, +17 壽命 (age at death), +18-21 政治力 戦闘力
# 魅力 野望, +23 (義理?), +26 debut year - 1560 in both scenarios (1582: 22 for everyone present), +27 u16 face code, +29 國, +30 lord (index of the lord
# table, FF 浪人), +31 忠誠度. Pointers are load addresses: person k = 0xD78 + size k, lord k = 0x8E + 46 k.
NOBU3_LORDS, NOBU3_PROVINCES, NOBU3_PERSONS, NOBU3_PROVINCE_COUNT = 0x4C, 0x722, 0xD38, 38
NOBU3_BASE = 1560
NOBU3_LABELS = ["政治力", "戦闘力", "魅力", "野望"]


def _read(game_dir, n):
    with open(os.path.join(game_dir, f"SNDATA{n}.CIM"), "rb") as f:
        return f.read()


def _ja(b):
    return unicodedata.normalize("NFKC", b.split(b"\0")[0].decode("cp932"))


def _scenario(game_dir, n):
    """(year, [(slot, record, zh name)], {lord index: slot}, {province: (lord slot, 城主 slot)})."""
    p, d = _read(game_dir, n), _read(os.path.join(game_dir, "..", "nobu3-dos"), n)
    year = struct.unpack_from("<H", p, 4)[0]
    people = []
    for k, o in enumerate(range(NOBU3_PERSONS, len(p) - 37, 38)):
        if p[o]:
            q = d[NOBU3_PERSONS + 44 * k:][:44]
            zh = koei_games.koei_tw_name(q[:11].split(b"\0")[0]) + koei_games.koei_tw_name(q[11:22].split(b"\0")[0])
            people.append((k, p[o:o + 38], zh))
    lords, i = {}, 0
    while ptr := struct.unpack_from("<H", p, NOBU3_LORDS + 46 * i)[0]:
        lords[i] = (ptr - 0xD78) // 38
        i += 1
    rule = {}
    for c in range(NOBU3_PROVINCE_COUNT):
        lord, castellan = struct.unpack_from("<HH", p, NOBU3_PROVINCES + 41 * c + 27)
        rule[c] = ((lord - 0x8E) // 46 if lord else None, (castellan - 0xD78) // 38 if castellan else None)
    return year, people, lords, rule


def persons(game_dir):
    # ids as build_nobu3_pc98: scenario 1 then 2, one person per (name, face code)
    ids, rows, scenarios = {}, [], [_scenario(game_dir, n) for n in (1, 2)]
    for year, people, _, _ in scenarios:
        for k, r, zh in people:
            key = (_ja(r[:9]) + _ja(r[9:16]), struct.unpack_from("<H", r, 27)[0])
            if key not in ids:
                ids[key] = len(rows)
                age, life, debut = r[16], r[17], r[26]
                born = NOBU3_BASE + debut - age
                row = {"id": len(rows), "name": zh}
                if zh != key[0]:
                    row["nameJa"] = key[0]
                row.update({"born": born, "died": born + life, **({"debut": NOBU3_BASE + debut} if NOBU3_BASE + debut > year else {}),
                            "stats": dict(zip(NOBU3_LABELS, r[18:22])), "hidden": {"寿命": life, "義理": r[23]},
                            "scenarios": [], "uncertain": ["hidden.義理"],
                            "notes": "生年＝1560＋登場年差（+26）－登場時年齢（+16），歿年＝生年＋寿命（+17，死亡時的年齢）。"
                                     "義理是 +23 的推定名稱（謙信 100、松永 4），沒讀程式；另外兩個隱藏值 +22、+24 意義不明，沒有輸出。"
                                     "能力與寿命取第一次出現的劇本（劇本 2 有人不同，例如信長的寿命 60→70）。"})
                rows.append(row)
    slot_id = []
    for year, people, lords, rule in scenarios:
        slot_id.append({k: ids[(_ja(r[:9]) + _ja(r[9:16]), struct.unpack_from("<H", r, 27)[0])] for k, r, _ in people})
    for n, ((year, people, lords, rule), sid) in enumerate(zip(scenarios, slot_id), 1):
        castellans = {c for _, c in rule.values() if c is not None}
        heads = set(lords.values())
        for k, r, _ in people:
            s = {"scenario": n, "year": year}
            if r[30] != 0xFF:
                s["lord"] = sid[lords[r[30]]]
            s["location"] = r[29] + 1
            s["status"] = "大名" if k in heads else "城主" if k in castellans else "家臣" if r[30] != 0xFF else "浪人"
            if r[30] != 0xFF:
                s["loyalty"] = r[31]
            if NOBU3_BASE + r[26] > year:
                s["status"] = "未登場"
            rows[sid[k]]["scenarios"].append(s)
    for row in rows:
        if any(s["status"] == "未登場" for s in row["scenarios"]):
            row["notes"] += "「未登場」是這邊的寫法：劇本開始時還沒登場，到 debut 那年才以 lord、location 登場。"
    return rows


def places(game_dir, out_dir):
    p, d = _read(game_dir, 1), _read(os.path.join(game_dir, "..", "nobu3-dos"), 1)
    rows = []
    for c in range(NOBU3_PROVINCE_COUNT):
        r, q = p[NOBU3_PROVINCES + 41 * c:][:41], d[NOBU3_PROVINCES + 41 * c:][:41]
        ja, zh = _ja(r[2:11]), koei_games.koei_tw_name(q[2:11].split(b"\0")[0])
        row = {"id": c + 1, "name": zh}
        if zh != ja:
            row["nameJa"] = ja
        row.update({"level": "國", "adjacent": [(b & 0x3F) + 1 for b in r[31:38] if b != 0xFF],
                    "notes": "國號照遊戲從 1 起算。鄰國的高 2 bit 是進攻方向（布陣區），沒有輸出。沒有地方分類，也沒找到大地圖座標。"
                             "戰場圖 HEXDATA.DAT 每國一張野戰、一張攻城（打哪一國用那一國的），圖塊沒解，沒有輸出圖。"})
        rows.append(row)
    return rows
