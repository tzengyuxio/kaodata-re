"""信長の野望・蒼天録 with PK (nobu10pk-win) for koei-wiki: persons (koei-persons/1), 地方, 國 and 城 (koei-places/1) and
列伝. The tables are at the same offsets in all 11 Scenario/SCEDAT??.NBX (plain Shift-JIS); the castle map positions
are DATA/GMAP_POS.NBX, the 列伝 DATA/RETSUDEN.NBX. Fields and evidence: notes/nobu10.md「人物欄位」「地理」「列伝」
「koei-wiki 匯出」."""
import os
import re
import struct
import unicodedata

# SCEDAT??.NBX: 11 地方 x 19 bytes (+0 name 5, +5 reading 14), 64 國 x 39 (+0 name 9, +9 reading 17, +26 地方, +27
# neighbours x 6, 0xFE none), 250 城 x 56 (+1 name 9, +10 reading 17, +27 suffix kind, +28 國, +29 neighbours x 7, +37/+39
# u16 石高 / max, +41/+43 u16 商業 / max). The scenario year is the ASCII at 0x2C.
REGIONS, PROVINCES, CASTLES = (0x23C59, 11, 19), (0x23D2A, 64, 39), (0x246EA, 250, 56)
SCENARIOS = ["01", "02", "03", "04", "05", "06", "09", "10", "11", "12", "13"]
# The castle name suffixes (Nobunaga10WPK.exe 0x521228, name / reading pairs): kinds 0 城(じょう) 1 城(ぐすく) 2 館(やかた)
# 3 館(だて) … 15 の里. level is the suffix without「の」
SUFFIXES = ["城", "城", "館", "館", "御坊", "御堂", "御所", "寺", "社", "砦", "柵", "聖堂", "の村", "の町", "湊", "の里"]
# GMAP_POS.NBX starts with 250 (u32 x, u32 y): the castles' positions on the large map
PROVINCE_ID, REGION_ID = 1000, 2000  # place id: 城 = castle number 0-249, 國 = 1000 + 國號, 地方 = 2000 + 地方號


def _text(b):
    return b.split(b"\0")[0].decode("cp932")


def _table(data, spec):
    start, count, size = spec
    return [data[start + size * k:][:size] for k in range(count)]


def places(game_dir, out_dir):
    scenarios = {}
    for n in SCENARIOS:
        with open(os.path.join(game_dir, f"SCEDAT{n}.NBX"), "rb") as f:
            scenarios[n] = f.read()
    with open(os.path.join(game_dir, "GMAP_POS.NBX"), "rb") as f:
        gmap = f.read()
    main = scenarios[SCENARIOS[0]]
    year = {n: int(d[0x2C:0x30]) for n, d in scenarios.items()}
    regions = [(_text(r[:5]), _text(r[5:19])) for r in _table(main, REGIONS)]
    provinces = _table(main, PROVINCES)
    rows = []
    for k, (name, reading) in enumerate(regions):
        rows.append({"id": REGION_ID + k, "name": name, "reading": reading, "level": "地方",
                     "notes": f"地方號 {k}（place id 是地方號＋2000）。"})
    for k, r in enumerate(provinces):
        rows.append({"id": PROVINCE_ID + k, "name": _text(r[:9]), "reading": _text(r[9:26]), "level": "國",
                     "region": regions[r[26]][0], "adjacent": [PROVINCE_ID + n for n in r[27:33] if n != 0xFE],
                     "notes": f"國號 {k}（place id 是國號＋1000）。相鄰取國記錄 +27–+32，各劇本相同。"})
    tables = {n: _table(d, CASTLES) for n, d in scenarios.items()}
    for k, r in enumerate(tables[SCENARIOS[0]]):
        x, y = struct.unpack_from("<II", gmap, 8 * k)
        suffix = SUFFIXES[r[27]]
        stone, stone_max, trade, trade_max = struct.unpack_from("<4H", r, 37)
        row = {"id": k, "name": _text(r[1:10]), "reading": _text(r[10:27]), "level": suffix.removeprefix("の"),
               "province": _text(provinces[r[28]][:9]), "region": regions[provinces[r[28]][26]][0],
               "adjacent": [n for n in r[29:36] if n != 0xFE], "pos": {"x": x, "y": y, "grid": "pixel"},
               "uncertain": ["pos"]}
        notes = f"城號 {k}。名稱、種類取劇本 01（{year['01']} 年），遊戲裡顯示成「名稱＋{suffix}」。" \
                f"石高 {stone}／{stone_max}、商業 {trade}／{trade_max}（劇本 01，現值／上限）。" \
                "pos 是 GMAP_POS.NBX 的大地圖座標，和道路連線的遠近一致，但沒有和地圖圖檔對過。"
        others = []
        for n in SCENARIOS[1:]:
            o = tables[n][k]
            if (_text(o[1:10]), o[27]) != (_text(r[1:10]), r[27]):
                others.append(f"{year[n]} 年 {_text(o[1:10])}{SUFFIXES[o[27]]}")
        if others:
            notes += "其他劇本：" + "、".join(dict.fromkeys(others)) + "。"
        row["notes"] = notes
        rows.append(row)
    return rows


# ---------------------------------------------------------------- persons and 列伝

# 武将 records (koei_games.NOBU10_WIN_OFFICERS): record k is serial k (+120), the kaodata id; the second serial-0
# record is a blank. Field offsets: notes/nobu10.md「人物欄位（koei-wiki 用）」
OFFICERS, OFFICER_COUNT, OFFICER_SIZE = 0x27D9A, 1991, 122
PEOPLE = 1990
WOMEN, WOMAN_COUNT, WOMAN_SIZE = 0x63282, 208, 70
DAIMYO, DAIMYO_SIZE = 0x66b63, 309  # 大名家 k: u16 大名武将 serial, u8 本城
NONE8, NONE16 = 0xFE, 0xFFFE
MAIN = "06"  # the names kaodata uses
# +52 状態 (Nobunaga10WPK.exe table 0x520788); 10-12 are the 30 x 3 records 1900- (藤原秀衡, 北畠顕家 …) that no
# scenario places
STATES = ["未誕生", "元服前", "浪人", "一般", "城主", "軍団長", "大名", "隠居", "死亡"]
ORIGINS = ["武将", "国人", "一向宗", "旧仏教", "切支丹", "商人", "水軍", "忍者", "高家"]  # +56 出自
ARMS = ["足軽", "長槍", "騎馬", "鉄砲", "騎馬鉄砲"]  # +98 兵種
TACTICS = ["混乱", "罵声", "威圧", "離反", "虚報", "鼓舞", "治療", "収拾", "密偵", "焙烙", "破壊", "修復", "誘導", "挑発",
           "迎撃", "突入", "分断", "放火"]  # +107.. 策戦 bits (EXE 0x520828)
SPECIALS = ["哀願", "威圧", "茶湯", "剣豪", "農業", "商業", "改修", "登用", "弁舌", "天下布武"]  # +113 特技 (EXE 0x520870)
BIO_LANG = "ja"
KATA_TO_HIRA = {c: c - 0x60 for c in range(0x30A1, 0x30F7)}


def kana_text(s: str) -> str:
    """The message text as shown: half-width katakana is shown as hiragana, as katakana between ESC K and ESC H
    (ESC k, the reading of a title, is hiragana too); the other ESC codes are dropped."""
    out, kata = [], False
    for part in re.split(r"(\x1b.)", s):
        if len(part) == 2 and part[0] == "\x1b":
            kata = part[1] == "K"
            continue
        out.append(re.sub(r"[｡-ﾟ]+", lambda m: unicodedata.normalize("NFKC", m.group()) if kata else
                          unicodedata.normalize("NFKC", m.group()).translate(KATA_TO_HIRA), part))
    return "".join(out)


def bio_entry(raw: bytes) -> tuple[str, str | None, str]:
    """(title name, reading, text) of a (title, body) pair: the title is「name ESC k reading ESC H born～died」or the
    name alone; the body's line breaks are only the window's wrapping"""
    title, body = (b.split(b"\x05\x05\x05")[0].decode("cp932") for b in raw)
    m = re.match(r"([^\x1b ]+)\s*(?:\x1bk(.*?)\x1bH)?", title)
    text = re.sub(r"[\x00-\x1f]", "", kana_text(body)).strip()
    return m.group(1), kana_text(m.group(2)) if m.group(2) else None, text


def _bio_pairs(game_dir):
    """{officer serial: (title, body)}: 0-1499 are entries 2k, 2k + 1; 1600-1889 entries 2(k - 100); 1500-1599 and the
    1900- records have none"""
    with open(os.path.join(game_dir, "RETSUDEN.NBX"), "rb") as f:
        data = f.read()
    n, = struct.unpack_from("<H", data)
    offsets = list(struct.unpack_from(f"<{n}I", data, 2)) + [len(data)]
    entries = [data[a:b] for a, b in zip(offsets, offsets[1:])]
    out = {}
    for k in [*range(1500), *range(1600, 1890)]:
        e = 2 * (k if k < 1500 else k - 100)
        out[k] = (entries[e], entries[e + 1])
    return out


def _officers(data):
    return {struct.unpack_from("<H", r, 120)[0]: r
            for r in reversed(_table(data, (OFFICERS, OFFICER_COUNT, OFFICER_SIZE)))}  # the first serial 0 wins


def _name(r):
    return _text(r[:9]) + _text(r[26:35])


def _u16(r, o):
    return struct.unpack_from("<H", r, o)[0]


def bios(game_dir):
    return {k: [("單段", bio_entry(raw)[2])] for k, raw in _bio_pairs(game_dir).items()}


def bio_names(game_dir):
    with open(os.path.join(game_dir, f"SCEDAT{MAIN}.NBX"), "rb") as f:
        officers = _officers(f.read())
    return {k: _name(officers[k]) for k in range(PEOPLE)}


def persons(game_dir):
    scenarios = {}
    for n in SCENARIOS:
        with open(os.path.join(game_dir, f"SCEDAT{n}.NBX"), "rb") as f:
            scenarios[n] = f.read()
    officers = {n: _officers(d) for n, d in scenarios.items()}
    main = officers[MAIN]
    year = {n: int(d[0x2C:0x30]) for n, d in scenarios.items()}
    order = sorted(SCENARIOS, key=lambda n: (year[n], n))
    provinces = [_text(r[:9]) for r in _table(scenarios[MAIN], PROVINCES)]
    daimyo = {n: [_u16(d, DAIMYO + DAIMYO_SIZE * k) for k in range(256)] for n, d in scenarios.items()}
    wives = {}
    for r in _table(scenarios[MAIN], (WOMEN, WOMAN_COUNT, WOMAN_SIZE)):
        if _u16(r, 66) < PEOPLE:
            wives.setdefault(_u16(r, 66), []).append(_name(r))
    titles = {k: bio_entry(raw) for k, raw in _bio_pairs(game_dir).items()}

    def person(v):
        return v if v < PEOPLE else None

    fathers = {k: person(_u16(main[k], 69)) for k in range(PEOPLE)}
    rows = []
    for k in range(PEOPLE):
        r = main[k]
        row = {"id": k, "name": _name(r), "reading": _text(r[9:26]) + _text(r[35:52]),
               "born": _u16(r, 57), "died": _u16(r, 61)}
        notes = [f"姓名、讀音取劇本 {MAIN}（1582 年）。"]
        uncertain = ["hidden.相性Ａ", "hidden.相性Ｂ", "hidden.義理", "hidden.野心", "relations.clan", "game.出自",
                     "game.出身国", "game.兵種", "scenarios.lord"]
        # 政治 / 統率 / 知略 grow with the scenario year; the 未誕生, 元服前, 死亡 and 10-12 records keep the base value
        # (the same in every scenario, experience 0)
        base = next(((o[101], o[103], o[105]) for n in order for o in [officers[n][k]] if not 2 <= o[52] <= 7), None)
        if base:
            notes.append("能力是原始值（未誕生、元服前、死亡的記錄存的值，各劇本相同），已登場的人在劇本裡依劇本年成長過。")
        else:
            o = officers[order[0]][k]
            base = (o[101], o[103], o[105])
            notes.append(f"每個劇本都已登場，沒有原始值；能力取最早的劇本 {order[0]}（{year[order[0]]} 年）的值，已依劇本年成長過。")
            uncertain.append("stats")
        row["stats"] = dict(zip(["政治", "統率", "知略"], base))
        row["hidden"] = {"相性Ａ": r[75], "相性Ｂ": r[76], "義理": r[78], "野心": r[80]}
        skills = {}
        if r[113] < len(SPECIALS):
            skills["特技"] = [SPECIALS[r[113]]]
        bits = r[107] | r[108] << 8 | r[109] << 16
        tactics = [t for b, t in enumerate(TACTICS) if bits >> b & 1]
        if tactics:
            skills["策戦"] = tactics
        if skills:
            row["skills"] = skills
        relations = {}
        if fathers[k] is not None:
            relations["father"] = [fathers[k]]
        children = [j for j, f in fathers.items() if f == k]
        if children:
            relations["children"] = children
        siblings = [j for j, f in fathers.items() if j != k and f is not None and f == fathers[k]]
        if siblings:
            relations["siblings"] = siblings
        if _u16(r, 67) < NONE16:
            relations["clan"] = _u16(r, 67)
        if relations:
            row["relations"] = relations
        for label, o in (("義父", 71), ("養父", 73)):
            if person(_u16(r, o)) is not None:
                notes.append(f"{label}（+{o}）：{_name(main[_u16(r, o)])}（id {_u16(r, o)}）。")
        if k in wives:
            notes.append("妻（女性記錄的「夫」指向此人；女性不是 kaodata 人物，沒有 id）：" + "、".join(wives[k]) + "。")
        game = {}
        if r[56] < len(ORIGINS):
            game["出自"] = ORIGINS[r[56]]
        if r[60] < len(provinces):
            game["出身国"] = provinces[r[60]]
        active = [n for n in reversed(order) if 2 <= officers[n][k][52] <= 7]
        if active and officers[active[0]][k][98] < len(ARMS):
            game["兵種"] = ARMS[officers[active[0]][k][98]]
            notes.append(f"兵種取已登場的最後一個劇本（{active[0]}）。")
        if game:
            row["game"] = game
        row["scenarios"] = []
        for n in order:
            o = officers[n][k]
            state = o[52]
            if state == 8 or state >= len(STATES):
                continue
            sc = {"scenario": int(n), "year": year[n], "status": STATES[state]}
            if state == 0:
                sc["debut"] = _u16(o, 57)
            else:
                if o[83] != NONE8:
                    sc["location"] = o[83]
                if o[82] != NONE8 and person(daimyo[n][o[82]]) is not None:
                    sc["lord"] = daimyo[n][o[82]]
                if state in (3, 4, 5):
                    sc["loyalty"] = o[90]
            row["scenarios"].append(sc)
        if not row["scenarios"]:
            del row["scenarios"]
        if r[52] >= len(STATES):
            notes.append(f"状態是 {r[52]}（10–12，空位），沒有劇本放這個人；推測是 PK 的史實武將（登錄用），沒確認。")
        else:
            notes.append("scenarios 列 11 個劇本中沒有死亡的；未誕生的 debut 是生年。lord 是所属勢力（+82）的大名（大名家表）。")
        if k in titles:
            if titles[k][0] != row["name"]:
                notes.append(f"列伝標題寫「{titles[k][0]}」。")
        else:
            notes.append("沒有列伝。")
        row["uncertain"] = uncertain
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows
