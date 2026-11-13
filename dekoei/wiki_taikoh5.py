"""太閤立志伝V DX (taikoh5dx-win) for koei-wiki: persons (koei-persons/1). Steam DX release; names are the Chinese ones
(SNR5_TW.TR5, the only Chinese scenario file), the Japanese ones (SNR5_JP.TR5) go to nameJa. id is the kaodata
taikoh5dx-win id: the person record number (kaodata_export.TAIKOH5DX_WIN_PEOPLE: officers 0-959 and the fixed people
1160-1243 with a face of their own). scenarios: the 大名家 (segment 1) and each person's 家 and 身分 (segment 14);
no location and no places (the castle numbers are not matched to names yet). Field sources: notes/taikoh5.md
「koei-wiki 匯出」."""
import os
import struct

import kaodata_export as ke
import koei_games as kg

DATASET = "taikoh5dx-win"
NONE = 1305  # the "no person" record number
# Taiko5DX.exe 0xb27774: 統率 武力 政務 知謀 魅力 ...; SNR segment 14 (36 bytes a person, the first 1162) +14..+18
# (🟡, from the values: 織田信長 96 70 97 91 99, 前田慶次 武力 88 政務 2, 石田三成 政務 98)
STATS = ("統率", "武力", "政務", "知謀", "魅力")
STATS_AT, STATS_REC, STATS_N = 14, 36, 1162
# SNR segment 13: 12 bytes a person, the first 1000: +0 death year - 1500, +4 u32 師匠 (relations.master), +8 u32 正室 (record numbers;
# the wife is left out while she is dead or not married yet, so both are joined over the scenarios)
LIFE_REC, LIFE_N, DIED = 12, 1000, 1500
FICTION = 7  # SNR7 夢幻: everyone dies in 1614, no wives or masters
# segment 0 of each scenario: the era year in the intro text (天文廿三年 … 天正十二年); 夢幻 has none
YEARS = {0: 1554, 1: 1560, 2: 1568, 3: 1575, 4: 1582, 5: 1598, 6: 1549, 8: 1584}
CHRONO = sorted(YEARS, key=YEARS.get)
# segment 1: 70 大名家 of 20 bytes, +2 u16 the head (record number, 1305 none); every head's own 家 is that 家
CLAN_REC, CLANS = 20, 70
# segment 14 +19 the 家 (< 70 a 大名家, 70-120 merchants, ninja, pirates and other groups, 121 none),
# +21 low 3 bits the 身分 (0 head, 1 retainer, 2 retainer of a retainer, 4 not on the map; bit 3 unknown),
# +24 u16 the direct master of a 陪臣
NO_CLAN = 121


def persons(game_dir):
    jp = os.path.join(game_dir, ke.TAIKOH5DX_WIN_SCENARIOS[ke.TAIKOH5DX_WIN_NAMES_FROM])
    ja = kg.load_taikoh5_win_persons(jp)
    zh = kg.load_taikoh5_win_persons(os.path.join(game_dir, "SNR5_TW.TR5"), tw=True)
    names = [kg.load_taikoh5_win_persons(os.path.join(game_dir, n)) for n in ke.TAIKOH5DX_WIN_SCENARIOS]
    part = kg._taikoh5_win_part(jp, 15)
    readings = [" ".join(ke.kana_to_hiragana(k) for k in (part[o:o + 10].split(b"\0")[0].decode("cp932"),
                                                          part[o + 10:o + 21].split(b"\0")[0].decode("cp932")) if k)
                for o in range(0, len(part), kg.TAIKOH5_WIN_READING)]
    stats = kg._taikoh5_win_part(jp, 14)
    life = kg._taikoh5_win_part(jp, 13)
    lives = [kg._taikoh5_win_part(os.path.join(game_dir, n), 13)
             for k, n in enumerate(ke.TAIKOH5DX_WIN_SCENARIOS) if k != FICTION]
    people = set(ke.TAIKOH5DX_WIN_PEOPLE)

    spouses, masters = {}, {}
    for i in people:
        for lf in lives if i < LIFE_N else ():
            m, w = struct.unpack_from("<II", lf, i * LIFE_REC + 4)
            if w != NONE:
                assert w in people
                spouses.setdefault(i, set()).add(w)
                spouses.setdefault(w, set()).add(i)
            if m != NONE:
                assert m in people
                masters.setdefault(i, set()).add(m)

    scen = {}
    for k, n in enumerate(ke.TAIKOH5DX_WIN_SCENARIOS):
        path = os.path.join(game_dir, n)
        clans = kg._taikoh5_win_part(path, 1)
        heads = [struct.unpack_from("<H", clans, c * CLAN_REC + 2)[0] for c in range(CLANS)]
        seg = kg._taikoh5_win_part(path, 14)
        scen[k] = (heads, seg)

    def scenarios(i):
        odd = False
        status = {}
        for k, (heads, seg) in scen.items():
            r = seg[i * STATS_REC:][:STATS_REC]
            clan, code = r[19], r[21] & 7
            s = {"scenario": k + 1, **({"year": YEARS[k]} if k in YEARS else {})}
            if code == 4:
                s["status"] = None  # filled below: 未登場 or 不在
            elif clan == NO_CLAN:
                if code == 1:
                    s["status"] = "浪人"
                    odd = True
            elif clan < CLANS:
                assert heads[clan] in people
                s["lord"] = heads[clan]
                s["status"] = "大名" if heads[clan] == i else {1: "家臣", 2: "陪臣"}.get(code)
                odd |= s["status"] in ("家臣", "陪臣")
                if s["status"] is None:
                    del s["status"]
            status[k] = s
        seen = False
        for k in CHRONO:
            s = status[k]
            if "status" in s and s["status"] is None:
                s["status"] = "不在" if seen else "未登場"
            else:
                seen = True
        if FICTION in status and status[FICTION].get("status", "") is None:
            status[FICTION]["status"] = "不在"
        out = [status[k] for k in sorted(status)]
        return out, odd

    rows = []
    for i in ke.TAIKOH5DX_WIN_PEOPLE:
        name_ja, kind = ja[i][0], ja[i][1]
        row = {"id": i, "name": zh[i][0]}
        if name_ja != zh[i][0]:
            row["nameJa"] = name_ja
        row["reading"] = readings[i].replace(" ", "") if all("ァ" <= c <= "ー" for c in name_ja) else readings[i]
        uncertain, notes = [], []
        if i < LIFE_N:
            row["died"] = DIED + life[i * LIFE_REC]
            uncertain.append("died")
        if i < STATS_N:
            v = stats[i * STATS_REC + STATS_AT:][:len(STATS)]
            if any(v):
                row["stats"] = dict(zip(STATS, v))
                uncertain += [f"stats.{k}" for k in STATS]
        if i < STATS_N:
            row["scenarios"], odd = scenarios(i)
            if odd:
                uncertain.append("scenarios.status")
        if i >= 960 and kind in ke.TAIKOH5DX_WIN_WOMEN:
            row["more"] = {"性別": "女"}
        if i in spouses:
            row["relations"] = {"spouse": sorted(spouses[i])}
        if i in masters:
            assert len(masters[i]) == 1
            row.setdefault("relations", {})["master"] = [masters[i].pop()]
        others = list(dict.fromkeys(sc[i][0] for sc in names if sc[i][0] != name_ja))
        if others:
            notes.append("其他劇本的日文寫法：" + "、".join(others))
        if uncertain:
            row["uncertain"] = uncertain
        if notes:
            row["notes"] = "；".join(notes)
        rows.append(row)
    return rows
