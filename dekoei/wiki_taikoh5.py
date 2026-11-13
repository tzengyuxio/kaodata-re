"""太閤立志伝V DX (taikoh5dx-win) for koei-wiki: persons (koei-persons/1). Steam DX release; names are the Chinese ones
(SNR5_TW.TR5, the only Chinese scenario file), the Japanese ones (SNR5_JP.TR5) go to nameJa. id is the kaodata
taikoh5dx-win id: the person record number (kaodata_export.TAIKOH5DX_WIN_PEOPLE: officers 0-959 and the fixed people
1160-1243 with a face of their own). No scenarios and no places: the per-scenario allegiance, rank and location are
not decoded yet. Field sources: notes/taikoh5.md 「koei-wiki 匯出」."""
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
# SNR segment 13: 12 bytes a person, the first 1000: +0 death year - 1500, +4 u32 師匠, +8 u32 正室 (record numbers;
# the wife is left out while she is dead or not married yet, so both are joined over the scenarios)
LIFE_REC, LIFE_N, DIED = 12, 1000, 1500
FICTION = 7  # SNR7 夢幻: everyone dies in 1614, no wives or masters


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
        if i >= 960 and kind in ke.TAIKOH5DX_WIN_WOMEN:
            row["more"] = {"性別": "女"}
        if i in spouses:
            row["relations"] = {"spouse": sorted(spouses[i])}
        if i in masters:
            assert len(masters[i]) == 1
            row["game"] = {"師匠": masters[i].pop()}
        others = list(dict.fromkeys(sc[i][0] for sc in names if sc[i][0] != name_ja))
        if others:
            notes.append("其他劇本的日文寫法：" + "、".join(others))
        if uncertain:
            row["uncertain"] = uncertain
        if notes:
            row["notes"] = "；".join(notes)
        rows.append(row)
    return rows
