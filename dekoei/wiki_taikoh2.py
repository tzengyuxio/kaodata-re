"""太閤立志伝II (taikoh2-pc98) for koei-wiki: persons (koei-persons/1). The PC-98 version is the main dataset (the
original release); names are the Windows Chinese version's (../taikoh2-win: the same BSDATA records by person
number), the PC-98 ones go to nameJa. id is the kaodata taikoh2-pc98 id: BSDATA1.TR2 people below 695 in file order
(466 「この人削除」 takes the BSDATA2 name), then the masters and women with a face. BSDATA1 and BSDATA2 are the two
starts, written as scenarios 1 and 2 (no year: not found in the files). No places: the location byte indexes a table
not found yet. Field sources: notes/taikoh2.md 「koei-wiki 匯出」."""
import os

import koei_games as kg

DATASET = "taikoh2-pc98"
PEOPLE = 695  # BSDATA 695-699 are placeholders
# MAIN.EXE 0x30DC0: the 身分 names; record +57 & 7 indexes them (7 大名, one per clan)
RANKS = "浪人 足軽頭 物頭 侍大将 部将 家老 宿老 大名".split()
# MAIN.EXE 0x3C240 status window order; record +22..+26 (🟡: 上杉謙信 武力 100, 柴田勝家 外交 31, 木下藤吉郎 魅力 97)
STATS = ("統率力", "武力", "内政力", "外交力", "魅力")
BORN = 1490  # record +39 & 0x7F + 1490 (織田信長 1534, 武田信玄 1521, 毛利元就 1497)
ABSENT = 0x80  # record +39 bit 7: not on the map in this start (dead, or not appeared yet)
CLAN, RANK = 48, 57  # 0xFF clan = none


def _records(path):
    with open(path, "rb") as f:
        data = f.read()
    return {int.from_bytes(data[o + 16:o + 18], "little"): data[o:o + kg.TAIKOH2_WIN_PERSON]
            for o in range(0, len(data), kg.TAIKOH2_WIN_PERSON)}


def _names(game_dir, decode):
    first = kg.load_taikoh2_win_persons(os.path.join(game_dir, "BSDATA1.TR2"), decode)
    second = dict(kg.load_taikoh2_win_persons(os.path.join(game_dir, "BSDATA2.TR2"), decode))
    deleted = {kg._big5: "這個人削除", kg._taikoh2_pc98_sjis: "この人削除"}[decode]
    return [(n, second[n] if name == deleted else name) for n, name in first if n < PEOPLE]


def persons(game_dir):
    win = os.path.join(game_dir, "..", "taikoh2-win")
    ja = _names(game_dir, kg._taikoh2_pc98_sjis)
    zh = dict(_names(win, kg._big5))
    starts = [_records(os.path.join(game_dir, f"BSDATA{k}.TR2")) for k in (1, 2)]
    ids = {n: i for i, (n, _) in enumerate(ja)}
    heads = []
    for recs in starts:
        h = {}
        for n, r in recs.items():
            if n < PEOPLE and r[RANK] & 7 == 7 and not r[39] & ABSENT:
                assert r[CLAN] not in h
                h[r[CLAN]] = ids[n]
        heads.append(h)
    rows = []
    for i, (n, name_ja) in enumerate(ja):
        r = starts[1][n]  # BSDATA2 also holds the person deleted from BSDATA1
        row = {"id": i, "name": zh[n]}
        if name_ja != zh[n]:
            row["nameJa"] = name_ja
        row["born"] = BORN + (r[39] & 0x7F)
        row["stats"] = dict(zip(STATS, r[22:27]))
        scenarios, seen = [], False
        for k, (recs, h) in enumerate(zip(starts, heads), 1):
            s = recs[n]
            if s[39] & ABSENT:
                if not seen:
                    scenarios.append({"scenario": k, "status": "未登場"})
                continue
            seen = True
            e = {"scenario": k, "status": RANKS[s[RANK] & 7]}
            if s[CLAN] in h:
                e["lord"] = h[s[CLAN]]
            scenarios.append(e)
        row["scenarios"] = scenarios
        row["uncertain"] = ["born"] + [f"stats.{k}" for k in STATS]
        row["notes"] = ("身分、所屬是兩個開局（BSDATA1、BSDATA2）各自的值；記錄標為不在場、之前也沒出場過的寫未登場，"
                        "出場過後不在場的（死亡或退場，遊戲沒寫）不列。沒有所在地。")
        rows.append(row)
    exe = os.path.join(game_dir, "MAIN.EXE")
    others_ja = kg.load_taikoh2_win_others(exe, os.path.join(game_dir, "SNDATA1.TR2"), kg.TAIKOH2_PC98_NAMES,
                                           kg._taikoh2_pc98_sjis, kg.TAIKOH2_PC98_KEY)
    others_zh = kg.load_taikoh2_win_others(os.path.join(win, "Taik2w95.exe"), os.path.join(win, "SNDATA1.TR2"))
    for (n, name_ja, face), (n_zh, name_zh, face_zh) in zip(others_ja, others_zh):
        assert n == n_zh and face == face_zh
        if face == 0xFFFF:
            continue
        row = {"id": len(rows), "name": name_zh}
        if name_ja != name_zh:
            row["nameJa"] = name_ja
        if n >= 2000:
            row["more"] = {"性別": "女"}
        row["notes"] = ("師匠（1000 號起）" if n < 2000 else "女性（2000 號起）") + "：只有名字和頭像（MAIN.EXE 與 SNDATA1.TR2）。"
        rows.append(row)
    return rows
