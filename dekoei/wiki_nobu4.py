"""信長の野望・武将風雲録 (nobu4-pc98) for koei-wiki: persons (koei-persons/1) and places (koei-places/1). The data
is the PC-98 scenarios; name is the DOS 中文版's (nobu4-dos beside it, byte-identical files apart from the names),
nameJa the PC-98 Japanese. Field sources and how sure they are: notes/nobu4.md「人物欄位」「地理」「koei-wiki 匯出」."""
import os
import struct

import koei_games
from kaodata_export import NOBU4_DOS_NAME_PICK, NOBU4_PC98_ALIASES

# SNDATAn.CIM: +1 year - 1476; 48 國 from 0x4 (45 bytes: +4 name 4 bytes, +30 7 neighbours, low 6 bits the 國
# (0-based), FF ends); lords from 0xB90 (32 bytes: +0 the lord's pointer, +31 lord number); persons from 0x1192
# (33 bytes from the surname: +14 born - 1476, +15-19 政治力 戦闘力 教養 魅力 野望, +20 (義理?), +21 u16 face code,
# +23 bits 6-7 寿命 (0-3), +24 bit 4 大名, low 4 bits the 一門 group of the scenario, +26 國, +27 lord number (FF
# 浪人), +28 忠誠度). Pointers minus 0x40 are file offsets of a surname. SNDATAnT.CIM: later arrivals, 28 bytes: +0
# debut - 1476, +1 lord number, +2 國, +3 names, +17 born - 1476, +18-22 the five, +23 (義理?), +24 u16 face code,
# +26 bits 6-7 寿命.
NOBU4_PROVINCES, NOBU4_LORDS, NOBU4_PERSONS, NOBU4_PROVINCE_COUNT = 0x4, 0xB90, 0x1192, 48
# the PC-98 dataset names 松平元康 after his later name (NOBU4_PC98_ALIASES); the Chinese name follows it
NOBU4_ZH_ALIASES = {"松平元康": "德川家康"}
NOBU4_LABELS = ["政治力", "戦闘力", "教養", "魅力", "野望"]
NOBU4_NOTES = ("義理是 +20 的推定名稱（謙信 253、松永 0），寿命是 0–3 的等級（+23 bit 6–7），都沒讀程式。一門編號（+24 低 4 bit）"
               "只在同一劇本內有效、16 組重複使用，沒有輸出。身分只分得出大名、浪人，城主與軍師沒找到欄位。")


def _read(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return f.read()


def _scenario(game_dir, n):
    """(year, main [(record, offset)], arrivals [record], {lord number: offset of the lord's record})."""
    d = _read(game_dir, f"SNDATA{n}.CIM")
    main = []
    for o in range(NOBU4_PERSONS, len(d) - 32, 33):
        if d[o] < 0x20:  # scenario 2 ends with a record starting 0x01
            break
        main.append((d[o:o + 33], o))
    t = _read(game_dir, f"SNDATA{n}T.CIM")
    arrivals = [t[o:o + 28] for o in range(0, len(t) - 27, 28) if t[o + 3]]
    lords = {}
    for i in range(NOBU4_PROVINCE_COUNT):
        r = d[NOBU4_LORDS + 32 * i:][:32]
        ptr = struct.unpack_from("<H", r)[0]
        if ptr:
            lords[r[31]] = ptr - 0x40
    return 1476 + d[1], main, arrivals, lords


def _zh_names(game_dir):
    """face code -> DOS name, as build_nobu4_dos picks it."""
    out = {}
    for table in koei_games.load_nobu4_dos_people(os.path.join(game_dir, "..", "nobu4-dos")):
        for name, code in table:
            name = NOBU4_DOS_NAME_PICK.get(code, name)
            out.setdefault(code, NOBU4_ZH_ALIASES.get(name, name))
    return out


def persons(game_dir):
    zh = _zh_names(game_dir)
    rows, ids = [], {}

    def person(name, code, born, values, giri, life):
        if code in ids:
            return ids[code]
        ja = NOBU4_PC98_ALIASES.get(name, name)
        row = {"id": len(rows), "name": zh.get(code, ja)}
        if row["name"] != ja:
            row["nameJa"] = ja
        row.update({"born": born, "stats": dict(zip(NOBU4_LABELS, values)), "hidden": {"義理": giri, "寿命": life},
                    "scenarios": [], "uncertain": ["hidden.義理", "hidden.寿命"], "notes": NOBU4_NOTES})
        ids[code] = len(rows)
        rows.append(row)
        return ids[code]

    # ids as build_nobu4_dos(pc98=True): SNDATA1, 1T, 2, 2T, 3, 3T, one person per face code
    names = koei_games.load_nobu4_pc98_people(game_dir)
    scenarios = [_scenario(game_dir, n) for n in (1, 2, 3)]
    for n, (year, main, arrivals, lords) in enumerate(scenarios):
        for (name, code), (r, _) in zip(names[2 * n], main):
            person(name, code, 1476 + r[14], r[15:20], r[20], r[23] >> 6)
        for (name, code), r in zip(names[2 * n + 1], arrivals):
            person(name, code, 1476 + r[17], r[18:23], r[23], r[26] >> 6)
    for n, ((year, main, arrivals, lords), people) in enumerate(zip(scenarios, names[0::2]), 1):
        at = {o: ids[code] for (_, code), (_, o) in zip(people, main)}
        for (_, code), (r, _) in zip(people, main):
            s = {"scenario": n, "year": year}
            if r[27] != 0xFF:
                s["lord"] = at[lords[r[27]]]
            s["location"] = r[26] + 1
            s["status"] = "大名" if r[24] & 0x10 else "浪人" if r[27] == 0xFF else "家臣"
            if r[27] != 0xFF:
                s["loyalty"] = r[28]
            rows[ids[code]]["scenarios"].append(s)
        for (_, code), r in zip(names[2 * n - 1], arrivals):
            row = rows[ids[code]]
            row.setdefault("debut", 1476 + r[0])
            s = {"scenario": n, "year": year, "location": r[2] + 1, "status": "未登場"}
            if r[1] != 0xFF:
                s["lord"] = at[lords[r[1]]]
            row["scenarios"].append(s)
            if "「未登場」" not in row["notes"]:
                row["notes"] += "「未登場」是這邊的寫法：後登場表（SNDATAnT）的人，到 debut 那年才以 lord、location 登場。"
    return rows


def places(game_dir, out_dir):
    p, d = _read(game_dir, "SNDATA1.CIM"), _read(os.path.join(game_dir, "..", "nobu4-dos"), "SNDATA1.CIM")
    rows = []
    for c in range(NOBU4_PROVINCE_COUNT):
        r, q = p[NOBU4_PROVINCES + 45 * c:][:45], d[NOBU4_PROVINCES + 45 * c:][:45]
        ja, zh = koei_games.nobu4_pc98_name(r[4:9]), koei_games.nobu4_name(q[4:9])
        row = {"id": c + 1, "name": zh}
        if zh != ja:
            row["nameJa"] = ja
        row.update({"level": "國", "adjacent": [(b & 0x3F) + 1 for b in r[30:37].split(b"\xff")[0]],
                    "notes": "國號照遊戲從 1 起算，3 個劇本相同。鄰國的高 2 bit 是進攻路線的種類（決定野戰圖），沒有輸出。"
                             "沒有讀音、地方與大地圖座標。戰場圖 HEXDATA.DAT：城圖每國一張，野戰圖依守方國與路線種類選，"
                             "圖塊與色盤沒解，沒有輸出圖。"})
        rows.append(row)
    return rows
