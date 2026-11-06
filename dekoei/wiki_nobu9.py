"""信長の野望・嵐世記 with PK (nobu9pk-win) for koei-wiki: persons (koei-persons/1), 国 and 城 (koei-places/1) and
列伝 (RETSUDEN.NB9). SCEDA??.NB9 decoded with koei_games.nobu9_win_data; the tables are typed records (u32 1, u16 id,
u16 type, u32) followed by the name: notes/nobu9.md「人物欄位」「地理」「列伝」「koei-wiki 匯出」."""
import os
import re
import struct

import koei_games

SCENARIOS = ["01", "02", "03", "04", "05", "08", "09", "10", "11", "12", "13", "14"]  # SCEDA??.NB9 that exist
REGION, PROVINCE, CASTLE = 16, 26, 28  # record types: 地方 (11), 国 (77: 0-53 land, 54-76 sea), 城 (135)
LAND = 54
PROVINCE_ID = 1000  # place id of 国 k is 1000 + k; 城 n keeps its number 0-134
NONE = 0xFFFF
TYPED = re.compile(rb"\x01\0\0\0(..)(..)(....)(?=[\x81-\x9f\xe0-\xfc][\x40-\xfc])", re.S)


def _typed(data, kind):
    """{id: offset of the name} of the records of one type."""
    out = {}
    for m in TYPED.finditer(data):
        i, t = struct.unpack("<HH", m.group(1) + m.group(2))
        if t == kind and struct.unpack("<I", m.group(3))[0] < 16:
            out[i] = m.end()
    return out


def _text(data, o, n):
    return data[o:o + n].split(b"\0")[0].decode("cp932")


def _refs(data, o):
    """(list of (id, type) refs, offset after it): u32 count, count x (u16 id, u16 type)."""
    n = struct.unpack_from("<I", data, o)[0]
    return [struct.unpack_from("<HH", data, o + 4 + 4 * j) for j in range(n)], o + 4 + 4 * n


def places(game_dir, out_dir):
    with open(os.path.join(game_dir, "Nobunaga9WPK.exe"), "rb") as f:
        exe = f.read()
    datas = [koei_games.nobu9_win_data(os.path.join(game_dir, f"SCEDA{s}.NB9"), exe) for s in SCENARIOS]
    data = datas[0]
    regions = {i: _text(data, o, 8) for i, o in _typed(data, REGION).items()}
    provinces = _typed(data, PROVINCE)
    castle_names = [{i: (_text(d, o, 10), _text(d, o + 10, 30)) for i, o in _typed(d, CASTLE).items()} for d in datas]
    rows, province_of = [], {}
    for k in range(len(provinces)):
        o = provinces[k]
        # +0 name 10, +10 reading, +0x2C 地方 (id, 16; sea none), then 6 land neighbours, 3 sea neighbours, 城 list
        region = struct.unpack_from("<HH", data, o + 0x2C)[0]
        land, p = _refs(data, o + 0x30)
        sea, p = _refs(data, p)
        castles, _ = _refs(data, p)
        for c, _ in castles:
            if c != NONE:
                province_of[c] = k
        row = {"id": PROVINCE_ID + k, "name": _text(data, o, 10), "reading": _text(data, o + 10, 30),
               "level": "国" if k < LAND else "海"}
        if region != NONE:
            row["region"] = regions[region]
        row["adjacent"] = [PROVINCE_ID + a for a, t in land + sea if a != NONE]
        row["notes"] = f"国號 {k}（place id 是国號＋1000）。相鄰是国記錄的陸上 6 格加海上 3 格。"
        if k >= LAND:
            row["uncertain"] = ["level"]
            row["notes"] += "国表 54–76 是海（海峡、灘、湾），遊戲裡這類的稱呼沒找到，「海」是這邊的分類；沒有地方。"
        rows.append(row)
    for n in sorted(castle_names[0]):
        name, reading = castle_names[0][n]
        k = province_of[n]
        o = provinces[k]
        row = {"id": n, "name": name, "reading": reading, "level": "城", "province": _text(data, o, 10),
               "region": regions[struct.unpack_from("<HH", data, o + 0x2C)[0]]}
        assert struct.unpack_from("<HH", data, _typed(data, CASTLE)[n] + 0x2C) == (k, PROVINCE)
        others = {}
        for s, names in zip(SCENARIOS[1:], castle_names[1:]):
            if names[n][0] != name:
                others.setdefault(names[n][0], []).append(s)
        notes = f"城號 {n}。名稱取劇本 01（1534 年）。城與城的相鄰、大地圖座標沒找到，沒有給。"
        if others:
            notes += "其他劇本的名稱：" + "、".join(f"{m}（劇本 {'、'.join(ss)}）" for m, ss in others.items()) + "。"
        row["notes"] = notes
        rows.append(row)
    return rows


# ---------------------------------------------------------------- persons and 列伝

# person record offsets from the surname: notes/nobu9.md「人物欄位（koei-wiki 用）」. 0-1449 are the 武将, 30000-30014
# the PK 史実武将 (the kaodata characters); 20000- are the 姫
OFFICERS, HISTORICAL, PRINCESS = 1450, range(30000, 30100), 20000
# the scenario year is not in the header: in each scenario the latest 元服年 of the people with a 勢力 equals the
# earliest 歿年 among them (01-05 agree with notes/nobu9.md「能力」, the PK ones with their header text)
YEARS = {"01": 1534, "02": 1556, "03": 1570, "04": 1582, "05": 1582, "08": 1545, "09": 1560, "10": 1573, "11": 1585,
         "12": 1599, "13": 1599, "14": 1614}
MAIN = "14"  # the latest names, as kaodata
ARMS = ["槍", "弓", "騎馬", "鉄砲", "大砲", "荷駄"]  # +0xDC 兵種 (6 なし), EXE 0x9843b0
BIO_LANG = "ja"


def _u32(data, o):
    return struct.unpack_from("<I", data, o)[0]


def _scenario_data(game_dir):
    with open(os.path.join(game_dir, "Nobunaga9WPK.exe"), "rb") as f:
        exe = f.read()
    return {s: koei_games.nobu9_win_data(os.path.join(game_dir, f"SCEDA{s}.NB9"), exe) for s in SCENARIOS}


def _ids(game_dir, main):
    records = dict(koei_games.nobu9_win_records(main))
    return records, [*range(OFFICERS), *sorted(i for i in records if i in HISTORICAL)]


def _name(data, o):
    return _text(data, o, 10) + _text(data, o + 24, 10)


def _bio_pairs(game_dir):
    """the (title, body) pairs of RETSUDEN.NB9 in order (pair k is 武将 k): LS11 parts 1-41, each a u16 offset table A
    whose first entry points at a second table B; the entries start at A[1:] and B (B ends where its offsets stop
    growing)"""
    import ls11
    with open(os.path.join(game_dir, "RETSUDEN.NB9"), "rb") as f:
        parts = ls11.ls11_decode_parts(f.read())
    entries = []
    for p in parts[1:]:
        a = struct.unpack_from(f"<{struct.unpack_from('<H', p)[0] // 2}H", p)
        b = []
        for v in struct.unpack_from(f"<{(a[1] - a[0]) // 2}H", p, a[0]):
            if v > len(p) or v <= (b[-1] if b else a[-1]):
                break
            b.append(v)
        starts = sorted({*a[1:], *b}) + [len(p)]
        entries += [p[x:y].rstrip(b"\0") for x, y in zip(starts, starts[1:])]
    return [(entries[2 * k], entries[2 * k + 1]) for k in range(OFFICERS)]


def bios(game_dir):
    from wiki_nobu10 import bio_entry
    return {k: [("單段", bio_entry(raw)[2])] for k, raw in enumerate(_bio_pairs(game_dir))}


def bio_names(game_dir):
    main = _scenario_data(game_dir)[MAIN]
    records, ids = _ids(game_dir, main)
    return {i: _name(main, records[i]) for i in ids}


def persons(game_dir):
    from wiki_nobu10 import bio_entry
    datas = _scenario_data(game_dir)
    records = {s: dict(koei_games.nobu9_win_records(d)) for s, d in datas.items()}
    main = datas[MAIN]
    _, ids = _ids(game_dir, main)
    people = set(ids)
    provinces = {i: _text(main, o, 10) for i, o in _typed(main, PROVINCE).items()}
    titles = [bio_entry(raw)[0] for raw in _bio_pairs(game_dir)]
    order = sorted(SCENARIOS, key=lambda s: (YEARS[s], s))

    def field(s, i, o):
        return _u32(datas[s], records[s][i] + o)

    def person(v):
        return v if v in people else None

    def father(i):  # +0x7A (person, type 0); 0x8000 | n when the father is not in the data
        v = field(MAIN, i, 0x7A)
        return person(v & 0xFFFF) if v >> 16 == 0 and v & 0xFFFF < 0x8000 else None

    fathers = {i: father(i) for i in ids}
    princesses = {}
    for s in SCENARIOS:
        for i, o in records[s].items():
            if i // 1000 == PRINCESS // 1000:
                princesses.setdefault(i, _name(datas[s], o))
    # the 大名 of each 勢力: the one person of the 勢力 whose 主君 (+0xAC) is 0xFFFF
    heads = {}
    for s in SCENARIOS:
        for i in ids:
            force, lord = field(s, i, 0x8C) & 0xFFFF, field(s, i, 0xAC)
            if force != NONE and lord == 0xFFFFFFFF:
                assert (s, force) not in heads
                heads[s, force] = i
    rows = []
    for i in ids:
        d, o = main, records[MAIN][i]
        row = {"id": i, "name": _name(d, o), "reading": _text(d, o + 34, 18) + _text(d, o + 52, 18),
               "born": _u32(d, o + 0x5E), "died": _u32(d, o + 0x66)}
        notes = [f"姓名、讀音取劇本 {MAIN}（{YEARS[MAIN]} 年）。"]
        uncertain = ["hidden.元服年", "relations.clan", "game.出身国", "game.兵種", "scenarios.lord", "scenarios.status",
                     "scenarios.loyalty", "scenarios.year"]
        # 政治 / 統率 / 知略 / 野望 grow in the scenarios where the person is active; the other records hold the base
        # value (the same in every scenario)
        stats = next(struct.unpack_from("<I4xI4xI4xI", datas[s], records[s][i] + 0xB0) for s in order
                     if not field(s, i, 0x62) <= YEARS[s] <= field(s, i, 0x66))
        row["stats"] = dict(zip(["政治", "統率", "知略", "野望"], stats))
        row["hidden"] = {"元服年": _u32(d, o + 0x62)}
        relations = {}
        if fathers[i] is not None:
            relations["father"] = [fathers[i]]
        children = [j for j, f in fathers.items() if f == i]
        if children:
            relations["children"] = children
        siblings = [j for j, f in fathers.items() if j != i and f is not None and f == fathers[i]]
        if siblings:
            relations["siblings"] = siblings
        if i < OFFICERS:
            relations["clan"] = _u32(d, o + 0x6A)
        if relations:
            row["relations"] = relations
        wives = sorted({field(s, i, 0x7E) & 0xFFFF for s in SCENARIOS} - {NONE})
        if wives:
            notes.append("配偶者（+0x7E，姫不是 kaodata 人物，沒有 id）：" +
                         "、".join(princesses.get(w, f"編號 {w}") for w in wives) + "。")
        game = {}
        tsusho = _text(d, o + 10, 14)
        if tsusho:
            game["通称"] = tsusho
        origin = field(MAIN, i, 0x76)
        if origin >> 16 == PROVINCE and origin & 0xFFFF in provinces:
            game["出身国"] = provinces[origin & 0xFFFF]
        row["scenarios"] = []
        for s in order if i < OFFICERS else []:
            year, force, castle = YEARS[s], field(s, i, 0x8C) & 0xFFFF, field(s, i, 0x94) & 0xFFFF
            genpuku, died = field(s, i, 0x62), field(s, i, 0x66)
            if died < year:
                continue
            sc = {"scenario": int(s), "year": year}
            if genpuku > year:
                sc["status"], sc["debut"] = "未登場", genpuku
            elif force != NONE:
                sc["status"] = "大名" if heads[s, force] == i else "家臣"
                sc["lord"] = heads[s, force]
                if heads[s, force] != i:
                    sc["loyalty"] = field(s, i, 0xE0)
            elif castle != NONE:
                sc["status"] = "浪人"
            else:
                continue
            if castle != NONE:
                sc["location"] = castle
            row["scenarios"].append(sc)
            arm = field(s, i, 0xDC)
            if sc["status"] != "未登場" and arm < len(ARMS):
                game["兵種"] = ARMS[arm]
        if game:
            row["game"] = game
        if not row["scenarios"]:
            del row["scenarios"]
        if i in HISTORICAL:
            notes.append("PK 的史實武將（用 KaoCG2 的臉，推測是任務模式的獎品）；劇本裡的記錄沒有勢力，沒有列 scenarios。生歿年、元服年照存的值，和史實不同（北条早雲存 1520–1550）。")
            uncertain = ["hidden.元服年"]
        else:
            notes.append("scenarios 列 12 個劇本中還沒死的人：元服年在劇本年之後是未登場（debut 是元服年，location 是登場的城），"
                         "有勢力的是大名或家臣，沒有勢力而有居城的是浪人；遊戲裡的身分名稱沒找到，status 是推的。"
                         "lord 是同勢力裡主君（+0xAC）為空的那個人（每個勢力剛好一人）。劇本年由人物的元服年與歿年推出。"
                         "兵種取最後一個登場的劇本。")
            if titles[i] not in (row["name"], _text(d, o, 10) + tsusho + _text(d, o + 24, 10)):
                notes.append(f"列伝標題寫「{titles[i]}」。")
        notes.append("能力是原始值（未登場、已死的記錄存的值，各劇本相同；登場中的依劇本年成長過）；"
                     "4Gamer 試玩版截圖顯示的政治、統率、知略是存值的一半，發售版未確認。")
        row["uncertain"] = uncertain
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows
