"""太閤立志伝 (taikoh-pc98) for koei-wiki: persons (koei-persons/1) and castles (koei-places/1). The PC-98 version is
the main dataset (the original release); names are the DOS Chinese version's (../taikoh-dos: the same records in the
same order, the same face codes), the PC-98 ones go to nameJa. id is the kaodata taikoh-pc98 id: the 241 people of
MAIN.EXE DGROUP 0xB8C, then TBS.DAT's 472 (one character per name), then the 27 women with a face. The game has one
start, written as scenario 1 (no year: the date is a DGROUP variable, 「15%2d年」). Field sources: notes/taikoh.md
「koei-wiki 匯出」."""
import os

import koei_games as kg

DATASET = "taikoh-pc98"
PERSON = kg.TAIKOH_DOS_PERSON
# MAIN.EXE 0x5BD1C: the 身分 names; person +42 indexes them (8 大名, 0 浪人 with clan 0xFF)
RANKS = "浪人 足軽頭 物頭 目付 奉行 中老 家老 宿老 大名".split()
# MAIN.EXE 0x5BDE6: 外交力 内政力 魅  力 統率力 武  力 野　心, in the order of person +51..+56 (🟡, from the values:
# 上杉謙信 野心 21, 織田信長 統率 100 / 野心 100)
STATS = ("外交力", "内政力", "魅力", "統率力", "武力", "野心")
# DGROUP 0x4E64 (MAIN.EXE 0x5A9F4): 123 castles x 24 bytes: +0 name (8 bytes), +9 城主 (person index),
# +10 daimyo (clan index); the person +41 is the castle the person is in (0xFF none)
CASTLES, N_CASTLES, CASTLE = 0x5A9F4, 123, 24


def _people(game_dir):
    """[(kaodata id, PC-98 record, Chinese name, Japanese name)] for the 241 + TBS.DAT people, one per name."""
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        main = f.read()
    with open(os.path.join(game_dir, "TBS.DAT"), "rb") as f:
        tbs = f.read()
    o = kg.TAIKOH_PC98_DGROUP + 0xB8C
    recs = [main[o + i * PERSON:][:PERSON] for i in range(241)] + \
        [tbs[i * PERSON:][:PERSON] for i in range(len(tbs) // PERSON)]
    dos = os.path.join(game_dir, "..", "taikoh-dos")
    zh = kg.load_taikoh_dos_persons(os.path.join(dos, "MAIN.EXE"), os.path.join(dos, "TBS.DAT"))
    ja = kg.load_taikoh_pc98_persons(os.path.join(game_dir, "MAIN.EXE"), os.path.join(game_dir, "TBS.DAT"))
    assert [c for _, c in zh] == [c for _, c in ja] and len(ja) == len(recs)
    out, seen_ja, seen_zh = [], set(), set()
    for r, (name_zh, _), (name_ja, _) in zip(recs, zh, ja):
        assert (name_ja in seen_ja) == (name_zh in seen_zh)  # the two versions merge the same records
        if name_ja in seen_ja:
            continue
        seen_ja.add(name_ja)
        seen_zh.add(name_zh)
        out.append((len(out), r, name_zh, name_ja))
    return main, out


def _heads(people):
    """clan index -> kaodata id of its 大名 (one per clan)."""
    heads = {}
    for i, r, _, _ in people[:241]:
        if r[42] == 8:
            assert r[40] not in heads
            heads[r[40]] = i
    return heads


def persons(game_dir):
    main, people = _people(game_dir)
    heads = _heads(people)
    rows = []
    for i, r, name_zh, name_ja in people:
        row = {"id": i, "name": name_zh}
        if name_ja != name_zh:
            row["nameJa"] = name_ja
        row["stats"] = dict(zip(STATS, r[51:57]))
        more = {"身分": RANKS[r[42]]}
        if r[43] | r[44]:
            more["知行"] = r[43] | r[44] << 8
        row["more"] = more
        uncertain = [f"stats.{k}" for k in STATS] + (["more.知行"] if "知行" in more else [])
        if i < 241:
            s = {"scenario": 1, "status": RANKS[r[42]]}
            if r[40] in heads:
                s["lord"] = heads[r[40]]
            if r[41] < N_CASTLES:
                s["location"] = r[41]
            row["scenarios"] = [s]
            row["notes"] = "開局就在的人（MAIN.EXE 的 241 人）；身分、所屬、所在是開局時的值。"
        else:
            row["scenarios"] = [{"scenario": 1, "status": "未登場"}]
            row["notes"] = ("TBS.DAT 的人（遊戲中途登場）；登場的時機沒追，所以沒有 debut；身分、知行、能力是記錄裡的值。"
                            "scenario 的 status 寫未登場（遊戲沒有稱呼）。")
        row["uncertain"] = uncertain
        rows.append(row)
    dos = os.path.join(game_dir, "..", "taikoh-dos", "MAIN.EXE")
    zh_women = kg.load_taikoh_dos_women(dos)
    ja_women = kg.load_taikoh_pc98_women(os.path.join(game_dir, "MAIN.EXE"))
    for (name_zh, face), (name_ja, face_ja) in zip(zh_women, ja_women):
        assert face == face_ja
        if face == 0xFF:
            continue
        row = {"id": len(rows), "name": name_zh}
        if name_ja != name_zh:
            row["nameJa"] = name_ja
        row["more"] = {"性別": "女"}
        row["notes"] = "女性（MAIN.EXE DGROUP 0x776 的表，只有名字和頭像）。"
        rows.append(row)
    return rows


def places(game_dir, out_dir):
    main, people = _people(game_dir)
    heads = _heads(people)
    zh_main = open(os.path.join(game_dir, "..", "taikoh-dos", "MAIN.EXE"), "rb").read()
    # the DOS Chinese MAIN.EXE keeps the same table at the same DGROUP offset
    zh_base = kg.TAIKOH_DOS_DGROUP + (CASTLES - kg.TAIKOH_PC98_DGROUP)
    rows = []
    for k in range(N_CASTLES):
        c = main[CASTLES + k * CASTLE:][:CASTLE]
        name_ja = c[:8].split(b"\0")[0].decode("cp932")
        name_zh = kg.koei_tw_name(zh_main[zh_base + k * CASTLE:][:8])
        row = {"id": k, "name": name_zh}
        if name_ja != name_zh:
            row["nameJa"] = name_ja
        row["level"] = "城"
        s = {"scenario": 1}
        if c[10] in heads:
            s["lord"] = heads[c[10]]
        row["scenarios"] = [s]
        if c[9] < 241:
            row["game"] = {"城主": c[9]}
        row["uncertain"] = ["level"]
        row["notes"] = ("城表（MAIN.EXE 0x5A9F4，123 筆 × 24 bytes）；level 的「城」是推定（遊戲有「城主」「城攻め」等詞）；"
                        "scenarios 的 lord 是開局時所屬大名，game.城主 是開局時的城主（人物 id）；沒有地圖座標與相鄰。")
        rows.append(row)
    return rows
