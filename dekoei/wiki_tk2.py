"""提督の決断II (tk2pk-pc98; tk2-pc98 reads the same files) for koei-wiki: persons (koei-persons/1). id is the kaodata
id: per side 30 admirals then 15 generals by face (Japan 0-44, the Allies 45-89), then the 9 heads of state 90-98.
Only the Japanese release exists. Field sources: notes/koei-games.md「提督の決断II」「koei-wiki 匯出」.

Records (10 scenarios each, the names the same in all):
- ARDATA 60 x 17 bytes: +0 name (13), +13 国籍, +14 海戦, +15 空戦, +16 flags (bit 0 on the roll).
- GRDATA 30 x 18 bytes: +0 name (13), +13 国籍, +14 陸戦, +15 空戦, +16 unknown, +17 flags (bit 0 on the roll).
- SJDATA 9 x 31 bytes: +0 name (13), +13 ordinal, +14 役職 (15), +29 unknown, +30 flags.
MAIN.EXE 0x149F0 (admiral list) / 0x14BAE (general list) print 階級 (DS:0x4E46 少将 中将 大将 元帥) from
(+14 + +15) / 60, then +14 and +15 under 海戦 (陸戦) and 空戦, and 国籍 from +13 (DS:0x4CC 日 米 英 蘭 豪 ソ 中 泰)."""
import os
import unicodedata

import ls11

DATASET = "tk2pk-pc98"
ADMIRALS, GENERALS, LEADERS = (17, 60), (18, 30), (31, 9)  # record size, count per scenario
SCENARIOS = 10
NATIONS = "日米英蘭豪ソ中泰"
RANKS = ("少将", "中将", "大将", "元帥")
# KAIGI.EXE 0x34442: the scenario list's start dates, in scenario order
DATES = [(1941, 12), (1941, 11), (1942, 5), (1944, 3), (1941, 12), (1942, 6), (1942, 8), (1944, 5), (1944, 10),
         (1945, 2)]


def _text(raw):
    return unicodedata.normalize("NFKC", raw.split(b"\0")[0].decode("cp932"))


def _read(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return f.read()


def _people(data, size, count, first, last):
    """[(record index, [record per scenario])] of records first..last-1."""
    return [(i, [data[k * size * count + i * size:][:size] for k in range(SCENARIOS)]) for i in range(first, last)]


def _officer(recs, kind, stat):
    family, _, given = _text(recs[0][:13]).partition(" ")
    row = {"name": family + given if given else family}
    if given:
        row["familyName"] = family
    s0 = recs[0]
    row["stats"] = {stat: s0[14], "空戦": s0[15]}
    row["more"] = {"区分": kind, "国籍": NATIONS[s0[13]]}
    out, absent, seen = [], False, False
    for k, r in enumerate(recs):
        year, month = DATES[k]
        s = {"scenario": k + 1, "year": year, "month": month, "rank": RANKS[min((r[14] + r[15]) // 60, 3)],
             "stats": {stat: r[14], "空戦": r[15]}}
        if not (r[16] if kind == "提督" else r[17]) & 1:
            s["status"] = "不在" if seen else "未登場"
            absent = True
        else:
            seen = True
        out.append(s)
    row["scenarios"] = out
    row["notes"] = (f"stats 是劇本 1 的值，各劇本不同（scenarios[].stats）。階級是遊戲把{stat}與空戦相加除以 60 算出的"
                    "（少将、中将、大将、元帥）。劇本順序與年月依 KAIGI.EXE 的劇本清單，和提督的生死對得上（推定）。"
                    + ("旗標 bit 0 為 0 的劇本寫 status：第一次在名單上之前寫「未登場」，之後寫「不在」（多半是已戰死；遊戲沒有稱呼，照使用者 2026-11-14 的規則）。" if absent else ""))
    return row


def persons(game_dir):
    pack = ls11.lw11_decode_files(_read(game_dir, "PACK.LZW"))
    ardata, grdata, sjdata = pack["ARDATA"], _read(game_dir, "GRDATA"), _read(game_dir, "SJDATA")
    admirals = [_officer(recs, "提督", "海戦") for _, recs in _people(ardata, *ADMIRALS, 0, 60)]
    generals = [_officer(recs, "将軍", "陸戦") for _, recs in _people(grdata, *GENERALS, 0, 30)]
    rows = [{"id": i, **row} for i, row in enumerate(admirals[:30] + generals[:15] + admirals[30:] + generals[15:])]
    for j in range(LEADERS[1]):
        r = sjdata[j * LEADERS[0]:][:LEADERS[0]]
        family, _, given = _text(r[:13]).partition(" ")
        row = {"id": 90 + j, "name": family + given if given else family}
        if given:
            row["familyName"] = family
        row["more"] = {"役職": _text(r[14:29])}
        row["notes"] = "SJDATA 的各國元首；役職各劇本相同，+29 的值（各劇本不同）意義未解。"
        rows.append(row)
    return rows
