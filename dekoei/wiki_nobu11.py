"""信長の野望・天下創世 with PK (nobu11pk-win) for koei-wiki: persons (koei-persons/1), 列伝 (msg/Bfile??.n11)
and 地方, 國, 拠点 (koei-places/1). scenario/DBSCEDA??.N11 decode (LWC) to a database of serial-numbered records:
+0 of every record is a global u16 serial and references are serials (0xFFFF none); the table offsets and serial
ranges are the same in all 7 scenarios. Fields and evidence: notes/nobu11.md「人物欄位」「地理」「列伝」「koei-wiki 匯出」."""
import os

from ls11 import lwc_decode

# (first serial, count, record size, offset in the decoded DBSCEDA)
BASES, PROVINCES, REGIONS = (0xB1, 100, 18297, 0xB072), (0xACA, 64, 42, 0x225F70), (0xB0A, 12, 20, 0x2269F0)
ROADS, NAMES = (0xA21, 169, 22, 0x2250EA), (0xFBA, 255, 40, 0x239350)
# 拠点: +2 castle name serial (name table: +2 name 11, +13 reading 27), +15338 / +15339 map x / y, +15342 國 serial.
# 國: +2 name 9, +11 reading 17, +28 neighbours 6 x u16, +40 地方 serial. 地方: +2 name 5, +7 reading 13.
# 街道: +3 kind (0-5), +4 / +13 the two 拠点
SCENARIOS = [(1, 1551), (2, 1560), (3, 1570), (4, 1582), (8, 1584), (9, 1590), (10, 1599)]  # (DBSCEDA number, year)
LEVELS = ("御所", "御坊", "館", "城")  # by the name's ending
PROVINCE_ID, REGION_ID = 1000, 2000  # place id: 拠点 = slot 0-99, 國 = 1000 + 國號, 地方 = 2000 + 地方號
# 國 adjacencies that are one-way in the game data (國號 pairs): 能登 lists 加賀 but 加賀 does not list 能登, and 加賀
# lists 伊勢, which does not list 加賀 (伊勢 is 29, 能登 19: probably a typo in 加賀's list)
ONE_WAY = [(19, 20), (20, 29)]


def _u16(b, o):
    return b[o] | b[o + 1] << 8


def _text(b):
    return b.split(b"\0")[0].decode("cp932")


def _database(game_dir, n):
    with open(os.path.join(game_dir, f"DBSCEDA{n:02d}.N11"), "rb") as f:
        packed = f.read()
    return lwc_decode(packed[packed.index(b"LWC\x1a"):])


def _table(db, spec):
    first, count, size, start = spec
    rows = [db[start + size * k:][:size] for k in range(count)]
    assert all(_u16(r, 0) == first + k for k, r in enumerate(rows))
    return rows


def _castle_names(db):
    names = _table(db, NAMES)
    return [(_text(names[_u16(b, 2) - NAMES[0]][2:13]), _text(names[_u16(b, 2) - NAMES[0]][13:40]))
            for b in _table(db, BASES)]


def places(game_dir, out_dir):
    dbs = {n: _database(game_dir, n) for n, _ in SCENARIOS}
    main = dbs[SCENARIOS[0][0]]
    regions = _table(main, REGIONS)
    provinces = _table(main, PROVINCES)
    bases = _table(main, BASES)
    names = {n: _castle_names(db) for n, db in dbs.items()}
    adjacent = {k: [] for k in range(100)}
    for r in _table(main, ROADS):
        a, b = _u16(r, 4) - BASES[0], _u16(r, 13) - BASES[0]
        adjacent[a].append(b)
        adjacent[b].append(a)
    one_way = {a for pair in ONE_WAY for a in pair}
    rows = []
    for k, r in enumerate(regions):
        rows.append({"id": REGION_ID + k, "name": _text(r[2:7]), "reading": _text(r[7:20]), "level": "地方",
                     "notes": f"地方號 {k}（place id 是地方號＋2000）。"})
    for k, r in enumerate(provinces):
        row = {"id": PROVINCE_ID + k, "name": _text(r[2:11]), "reading": _text(r[11:28]), "level": "國",
               "region": _text(regions[_u16(r, 40) - REGIONS[0]][2:7]),
               "adjacent": [PROVINCE_ID + _u16(r, 28 + 2 * j) - PROVINCES[0] for j in range(6)
                            if _u16(r, 28 + 2 * j) != 0xFFFF],
               "notes": f"國號 {k}（place id 是國號＋1000）。相鄰取國記錄 +28 起的 6 格，7 個劇本相同。"}
        if k in one_way:
            row["notes"] += "遊戲資料的相鄰在能登→加賀、加賀→伊勢是單向的（加賀的表裡寫伊勢、沒寫能登，" \
                            "推測是把能登寫成伊勢），照原樣輸出。"
        rows.append(row)
    for k, b in enumerate(bases):
        name, reading = names[SCENARIOS[0][0]][k]
        province = provinces[_u16(b, 15342) - PROVINCES[0]]
        row = {"id": k, "name": name, "reading": reading, "level": next(s for s in LEVELS if name.endswith(s)),
               "province": _text(province[2:11]), "region": _text(regions[_u16(province, 40) - REGIONS[0]][2:7]),
               "adjacent": adjacent[k], "pos": {"x": b[15338], "y": b[15339], "grid": "square"},
               "uncertain": ["pos"]}
        notes = f"拠点槽 {k}。名稱取劇本 01（1551 年）。相鄰取街道表（169 條，7 個劇本相同），照街道表的順序。" \
                "pos 是拠点 +15338、+15339 的格座標，和街道連線的遠近一致，但沒有和地圖圖檔對過。"
        others = [f"{year} 年 {names[n][k][0]}" for n, year in SCENARIOS[1:] if names[n][k][0] != name]
        if others:
            notes += "其他劇本的名稱：" + "、".join(others) + "。"
        row["notes"] = notes
        rows.append(row)
    return rows


# persons and 列伝 (koei-persons/1). Person records: 2016 x 123 bytes from serial 0x241; slot k = serial - 0x241,
# named slots 0-1215. The kaodata characters (the ids here) are the officer slots 0-999 and 1112-1211 (PK); 1000-1082
# are 姫 and 1083-1111, 1212-1215 forebears, kept out like the other generations (named in notes when referenced).
# Field layout: notes/nobu11.md「人物記錄」, from CBushou::Serialize (Nobunaga11WPK.exe VA 0x4066C0).
PERSONS, CLANS, FIEFS = (0x241, 2016, 123, 0x1E884A), (0x4D, 100, 432, 0x7B2), (0x115, 100, 1227, 0x1C9BB6)
NAMED = 1216
OFFICERS = [*range(1000), *range(1112, 1212)]
MAIN = 10  # DBSCEDA10 (1599) has the latest names, as kaodata
ORIGINS = ["守護", "守護代", "国人", "重臣", "武士", "高家", "一向宗", "僧侶", "切支丹", "商人", "海賊", "忍者", "剣豪",
           "庶民", "なし"]
FAITHS = ["神仏", "一向宗", "基督教"]
SKILLS = ["突撃", "斉射", "槍衾", "鼓舞", "収拾", "威圧", "軍師", "神速", "鉄壁", "軍神", "突撃参", "突撃弐", "突撃壱",
          "斉射参", "斉射弐", "斉射壱", "槍衾参", "槍衾弐", "槍衾壱"]
RANKS = ["大名", "宿老", "家老", "中老", "侍大将", "足軽大将", "足軽番頭", "足軽組頭"]
# 状態 (+62 bits 6-9): 0 一般武将, 1 姫, 2 浪人, 3 隠居, 4 元服前, 5 未誕生, 6 死亡, 7 仮死, 8 捕虜
STATES = ["一般武将", "姫", "浪人", "隠居", "元服前", "未誕生", "死亡", "仮死", "捕虜"]
BIO_KEY = bytes([0x97, 0x9E, 0x79, 0xE9])
BIO_LANG = "ja"


def _state(r):
    return _u16(r, 62) >> 6 & 15


def _person_name(r):
    return _text(r[2:11]) + _text(r[28:37])


def _persons(db):
    return _table(db, PERSONS)[:NAMED]


def _slot(serial):
    return None if serial == 0xFFFF else serial - PERSONS[0]


def _bio_entries(path):
    """the strings of one msg/Bfile??.n11: 'N11F', u32 end of the script, then XOR BIO_KEY from there to the end: u32
    count, u32 first message number, count + 1 u32 offsets from the text start, Shift-JIS text"""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"N11F"
    end = _u16(data, 4) | _u16(data, 6) << 16
    x = bytes(b ^ BIO_KEY[i % 4] for i, b in enumerate(data[end:]))
    count = int.from_bytes(x[:4], "little")
    offsets = [int.from_bytes(x[8 + 4 * i:12 + 4 * i], "little") for i in range(count + 1)]
    text = 8 + 4 * (count + 1)
    return [x[text + offsets[i]:text + offsets[i + 1]].decode("cp932") for i in range(count)]


def _bio_raw(game_dir):
    """{slot: (title, text)}: entry idx (slot, minus 112 from slot 1112) is Bfile idx // 50 + 1, strings 2 + 5 *
    (idx % 50): the title and 4 lines ending in a literal '\\n' (CBushou::GetRetsuden, VA 0x405C90)"""
    files = {}
    out = {}
    for slot in OFFICERS:
        idx = slot - 112 if slot >= 1112 else slot
        n = idx // 50 + 1
        if n not in files:
            files[n] = _bio_entries(os.path.join(game_dir, f"Bfile{n:02d}.n11"))
        e = files[n][2 + 5 * (idx % 50):][:5]
        out[slot] = e[0], "".join(line.replace("\\n", "") for line in e[1:])
    return out


def bios(game_dir):
    return {slot: [("單段", text)] for slot, (_, text) in _bio_raw(game_dir).items()}


def bio_names(game_dir):
    persons = _persons(_database(game_dir, MAIN))
    return {slot: _person_name(persons[slot]) for slot in OFFICERS}


def _base_stats(scenarios, slot):
    """(政治, 采配, 知略, 教養) before growth: the values of a scenario where the person is 未誕生 or 死亡 with all 4
    experience bytes 0 (the values grow by scenario year; unborn and dead persons hold the original ones), or None"""
    for _, persons in scenarios:
        r = persons[slot]
        if _state(r) in (5, 6) and not any(r[75:82:2]):
            return tuple(r[74:82:2])
    return None


def persons(game_dir):
    dbs = {n: _database(game_dir, n) for n, _ in SCENARIOS}
    scenarios = [(n, _persons(db)) for n, db in dbs.items()]
    heads = {n: [_slot(_u16(c, 4)) for c in _table(db, CLANS)] for n, db in dbs.items()}
    lords = {n: [_slot(_u16(f, 4)) for f in _table(db, FIEFS)] for n, db in dbs.items()}
    main = dict(scenarios)[MAIN]
    names = {k: _person_name(r) for k, r in enumerate(main)}
    officers = set(OFFICERS)
    bio = _bio_raw(game_dir)
    fathers = {k: _slot(_u16(main[k], 68)) for k in OFFICERS}

    def named(k):
        return f"{names[k]}（槽 {k}）"

    rows = []
    for k in OFFICERS:
        r = main[k]
        notes = ["人物與劇本 10（DBSCEDA10，1599 年）的名字同 kaodata；欄位取自 CBushou::Serialize 與 getter。"]
        row = {"id": k, "name": names[k], "reading": _text(r[11:28]) + _text(r[37:54]), "born": _u16(r, 56),
               "died": _u16(r, 60)}
        row["debut"] = _u16(r, 58)
        base = _base_stats(scenarios, k)
        if base is None:
            base = tuple(dict(scenarios)[SCENARIOS[0][0]][k][74:82:2])
            notes.append("7 個劇本都在世，stats 是劇本 1（1551 年）的值（已含成長，不是原始值）。")
            row.setdefault("uncertain", []).append("stats")
        row["stats"] = dict(zip(("政治", "采配", "知略", "教養"), base))
        row["more"] = {"勲功": _u16(r, 106)}
        row["hidden"] = {"相性": r[103], "義理": r[104]}
        skills = [SKILLS[s] for s in r[82:85] if s < len(SKILLS)]
        if skills:
            row["skills"] = {"合戦特技": skills}
        relations = {}
        if fathers[k] in officers:
            relations["father"] = [fathers[k]]
        children = [j for j, f in fathers.items() if f == k]
        if children:
            relations["children"] = children
        siblings = [j for j, f in fathers.items() if j != k and f is not None and f == fathers[k]]
        if siblings:
            relations["siblings"] = siblings
        spouse = _slot(_u16(r, 72))
        if spouse in officers:
            relations["spouse"] = [spouse]
        if _u16(r, 66) != 0xFFFF:
            relations["clan"] = _u16(r, 66)
        if relations:
            row["relations"] = relations
        if fathers[k] is not None and fathers[k] not in officers:
            notes.append(f"実父（+68）：{named(fathers[k])}，不是 kaodata 的人物。")
        adoptive = _slot(_u16(r, 70))
        if adoptive is not None:
            notes.append(f"養父（+70）：{named(adoptive)}。")
        if spouse is not None and spouse not in officers:
            notes.append(f"配偶者（+72）：{named(spouse)}，不是 kaodata 的人物（姫）。")
        game = {"出自": ORIGINS[r[64]], "信仰": FAITHS[r[65]], "性別": "女" if _u16(r, 62) & 1 else "男"}
        if _u16(r, 62) & 4:
            game["有名"] = True
        for key, off in (("親友武将", 99), ("敵対武将", 101)):
            other = _slot(_u16(r, off))
            if other is not None:
                game[key] = names[other]
        row["game"] = game
        row["scenarios"] = []
        others, spellings = [], {}
        for n, year in SCENARIOS:
            rs = dict(scenarios)[n][k]
            state = _state(rs)
            if state == 6:
                continue
            sc = {"scenario": n, "year": year}
            clan, fief, base_ = _u16(rs, 85), _u16(rs, 87), _u16(rs, 89)
            if clan != 0xFFFF and heads[n][clan - CLANS[0]] in officers:
                sc["lord"] = heads[n][clan - CLANS[0]]
            if fief != 0xFFFF:
                sc["location"] = fief - FIEFS[0]
            elif base_ != 0xFFFF:
                sc["location"] = base_ - BASES[0]
            if state in (4, 5):
                sc["status"] = "未登場"
                sc["debut"] = _u16(rs, 58)
            elif state == 0:
                if heads[n][clan - CLANS[0]] == k:
                    sc["status"] = "大名"
                elif fief != 0xFFFF and lords[n][fief - FIEFS[0]] == k:
                    sc["status"] = "城主"
                else:
                    sc["status"] = "家臣"
                sc["rank"] = RANKS[rs[108]]
                sc["loyalty"] = rs[105]
            elif state < len(STATES):
                sc["status"] = STATES[state]
            else:
                others.append(f"劇本 {n} 的状態是 {state}（表外，意義沒查）")
            if _person_name(rs) != names[k]:
                spellings.setdefault(_person_name(rs), []).append(str(year))
            row["scenarios"].append(sc)
        others += [f"{'、'.join(years)} 年叫 {name}" for name, years in spellings.items()]
        if others:
            notes.append("；".join(others) + "。")
        row["uncertain"] = row.get("uncertain", []) + ["skills.合戦特技", "scenarios.status", "scenarios.rank"]
        notes.append("status 是状態（+62 bit 6–9）加上勢力當主（大名）、領地城主（城主）推的；元服前、未誕生寫「未登場」，"
                     "debut 是登場年（+58）；rank 是身分（+108），宿老、家老只有 1590 年各 1 人（豊臣秀長、直江兼続），名稱照 EXE 字串的順序推。合戦特技的號碼與名稱是照 EXE "
                     "字串的排列推的。")
        if bio[k][0].split()[0] != names[k]:
            notes.append(f"列伝的標題寫「{bio[k][0].split()[0]}」。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows
