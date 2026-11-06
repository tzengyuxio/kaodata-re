"""信長の野望・革新 with PK (nobu12pk-win) for koei-wiki: persons (koei-persons/1), 国、城／港／館 and the 諸勢力
(koei-places/1), and 列伝. Each sceda??.n12 is one LWC block (ls11.lwc_decode); its sections start with the u32 pair
(section, count). The 列伝 are Msg/Bfile01-22.n12 (N12F message files, hard-linked from the Steam install):
notes/nobu12.md「人物欄位」「地理」「列伝」「koei-wiki 匯出」."""
import os
import struct

import ls11

SCENARIOS = ["01", "02", "03", "04", "05", "10", "11", "12"]
# section 8: 225 拠点 names (42 bytes: name 13, reading 29); slots 0-179 are 城／港／館 (47 empty), 180-224 the 諸勢力
# (国人衆、水軍衆、寺、忍者衆、商人衆). Section 10: 60 国 (30 bytes: name 11, reading 19). Section 11: one record per
# non-empty slot 0-179: name 11 + reading 21, u32 n + n u16 (list A, 🟡 section 9 facilities), u32 m + m u16 adjacent
# slots, u16 国, u16 slot (0xFFFF: not in this scenario), u8, 4 x u32 box x0 y0 x1 y1, u8, then 0-2 blocks of 62 bytes.
NAMES, PROVINCES, CASTLES = (8, 225), (10, 60), (11, 180)
NAMES_AT = 0x9BA6  # person names: 1940 x 213 bytes (koei_games.NOBU12_WIN_NAMES)
FORCES = 180  # first 諸勢力 slot
PROVINCE_ID = 1000  # place id of 国 k is 1000 + k; 拠点 slots keep their number 0-224
LEVELS = ["御所", "御坊", "城", "港", "館", "国人衆", "水軍衆", "忍者衆", "商人衆", "寺"]  # name endings = level
# scenario year: u16 at 0x2A0 of the file header (1555, 1561, 1570, 1582, 1557, 1582, 1600, 1603; the 1555 … 1582
# agree with the scenario texts)
YEAR = 0x2A0
MAIN = "12"  # the names of kaodata (after 関ヶ原)
OFFICERS = 1100  # slots 0-1099 are the kaodata characters
COUNT = 1940
OFFICES = (14, 250)  # 官位: 250 x 50 bytes, name 15 at +0
FACTIONS = (0x14, 0x3C)
# 固有戦法 (body +20): NOBU12PK.exe around 0x754E2C (啄木鳥) lists them backwards from 水雷 to 槍衾; index 0 is 槍衾
TACTICS = ["槍衾", "槍突撃", "槍車", "乱戦", "強襲", "千成衾", "先駆け", "突進", "突撃", "啄木鳥", "乗崩", "車懸り", "斉射",
           "火矢", "連射", "三矢訓", "早撃ち", "二段撃", "三段撃", "捨て奸", "組撃ち", "釣瓶撃", "鼓舞", "威圧", "罵声", "篭絡",
           "同士討", "治療", "火牛計", "つぶて", "石落し", "投焙烙", "水雷"]
ORIGINS = ["武士", "公家", "僧侶", "商人", "海賊", "忍者", "剣豪", "庶民"]  # t4; NOBU12PK.exe 0x753BF8
ARMS = ["足軽", "騎馬", "弓", "鉄砲", "計略", "兵器", "水軍", "築城", "内政"]
GRADES = "DCBAS"
BIO_LANG = "ja"


def _data(game_dir, s):
    with open(os.path.join(game_dir, f"sceda{s}.n12"), "rb") as f:
        p = f.read()
    return ls11.lwc_decode(p[p.index(b"LWC\x1a"):])


def _text(data, o, n):
    return data[o:o + n].split(b"\0")[0].decode("cp932")


def _section(data, key):
    return data.index(struct.pack("<2I", *key)) + 8


def _named(data, p):
    """A section 11 record starts at p: Shift-JIS name, then a hiragana reading at +11."""
    if not (0x81 <= data[p] <= 0x9F or 0xE0 <= data[p] <= 0xEA):
        return False
    r = data[p + 11:p + 32].split(b"\0")[0]
    return len(r) >= 4 and len(r) % 2 == 0 and all(r[i] == 0x82 for i in range(0, len(r), 2))


def _scenario(data):
    base = _section(data, NAMES)
    names = [(_text(data, base + 42 * i, 13), _text(data, base + 42 * i + 13, 29)) for i in range(NAMES[1])]
    slots = [i for i in range(FORCES) if names[i][0]]
    p, castles = _section(data, CASTLES), {}
    for s in slots:
        assert _named(data, p), s
        q = p + 32
        q += 4 + 2 * struct.unpack_from("<I", data, q)[0]
        m = struct.unpack_from("<I", data, q)[0]
        adjacent = list(struct.unpack_from(f"<{m}H", data, q + 4))
        q += 4 + 2 * m
        province, slot, _, x0, y0, x1, y1, _ = struct.unpack_from("<HHB4IB", data, q)
        assert slot in (s, 0xFFFF), s
        castles[s] = (adjacent, province, slot != 0xFFFF, (x0, y0, x1, y1))
        q += 22
        while s != slots[-1] and not _named(data, q):
            q += 62
        p = q
    return names, castles


def _level(name):
    return next(e for e in LEVELS if name.endswith(e))


def places(game_dir, out_dir):
    datas = [_data(game_dir, s) for s in SCENARIOS]
    scenarios = [_scenario(d) for d in datas]
    data = datas[0]
    base = _section(data, PROVINCES)
    provinces = [(_text(data, base + 30 * k, 11), _text(data, base + 30 * k + 11, 19)) for k in range(PROVINCES[1])]
    names, castles = scenarios[0]
    w = max(b[2] for _, _, _, b in castles.values())
    h = max(b[3] for _, _, _, b in castles.values())
    rows = []
    for k, (name, reading) in enumerate(provinces):
        rows.append({"id": PROVINCE_ID + k, "name": name, "reading": reading, "level": "国",
                     "notes": f"国號 {k}（place id 是国號＋1000）。国的相鄰與地方沒找到。"})
    for s, (name, reading) in enumerate(names):
        if not name:
            continue
        row = {"id": s, "name": name, "reading": reading, "level": _level(name)}
        others = {}
        for scenario, (n, _) in zip(SCENARIOS[1:], scenarios[1:]):
            if n[s][0] != name:
                others.setdefault(n[s][0], []).append(scenario)
        if s < FORCES:
            adjacent, province, _, (x0, y0, x1, y1) = castles[s]
            row["province"] = provinces[province][0]
            row["adjacent"] = adjacent
            row["pos"] = {"x": (x0 + x1) // 2, "y": (y0 + y1) // 2, "grid": "pixel", "w": w, "h": h}
            row["uncertain"] = ["pos"]
            present = [sc for sc, (_, c) in zip(SCENARIOS, scenarios) if c[s][2]]
            notes = f"拠点號 {s}。名稱取劇本 01（1555 年），level 是名稱的字尾。pos 是段 11 外框 ({x0}, {y0})–({x1}, " \
                    f"{y1}) 的中心；東西南北的方向和城的地理位置相符，單位沒確認。"
            if not present:
                notes += "8 個劇本的拠点 id 都是 0xFFFF（劇本開始時不存在），推定是遊戲中才能築的城【推】。"
            elif len(present) < len(SCENARIOS):
                notes += "出現在劇本 " + "、".join(present) + "。"
        else:
            notes = f"拠点號 {s}，諸勢力的拠点，level 是名稱的字尾。段 11 沒有這類的記錄，所屬国、相鄰、位置沒找到。"
        if others:
            notes += "其他劇本的名稱：" + "、".join(f"{m}（劇本 {'、'.join(ss)}）" for m, ss in others.items()) + "。"
        row["notes"] = notes
        rows.append(row)
    return rows


def _persons(data):
    """{slot: record} of every slot: the four lists (親愛, 嫌悪, 戦法, 家宝), the 11 u16 of the body front (slot,
    実父, 養父, 配偶者, -, 官位, 役職?, 所属勢力, -, -, 固有戦法), the 9 適性, the 所在拠点 (None in a 174-byte body)
    and the 23 u32 of the tail (t0-t22, notes/nobu12.md「人物欄位」)."""

    def head(p, slot):
        lists = []
        for k in range(4):
            n, = struct.unpack_from("<I", data, p)
            if (k < 2 and n != 3) or n >= 32:
                return None
            lists.append(list(struct.unpack_from(f"<{n}H", data, p + 4)))
            p += 4 + 2 * n
        return (p, lists) if struct.unpack_from("<H", data, p)[0] in (slot, 0xFFFF) else None

    p = data.index(struct.pack("<2I", 0x13, COUNT), 0x80000) + 8
    out = {}
    for slot in range(COUNT - 1):
        b, lists = head(p, slot)
        e = b + 170
        while head(e, slot + 1) is None:
            e += 1
        assert e - b in (174, 176), slot
        out[slot] = {"lists": [[v for v in x if v != 0xFFFF] for x in lists[:2]] + lists[2:],
                     "front": struct.unpack_from("<11H", data, b), "apt": struct.unpack_from("<9I", data, b + 42),
                     "location": struct.unpack_from("<H", data, b + 82)[0] if e - b == 176 else None,
                     "t": struct.unpack_from("<23I", data, e - 92)}
        p = e
    return out


def faction_lords(data, key, serves):
    """{勢力: 当主 slot} of the 勢力 section key (section 20 here, 21 in 天道): after the key 08 00 00 00 c ff x 14 01
    00 00 00 c come u32 n + n u16 members, 8 bytes, u32 k + k u16 wives, two lists of u32 m + m x 6 bytes, three
    lists of u32 k + k u16 (the last one is empty but in 天道 劇本 11 豊臣家), u16 当主. Kept only when serves(slot,
    c): the 当主 serves and his own 所属勢力 is c."""
    q0 = _section(data, key)
    out = {}
    for c in range(key[1]):
        q = data.find(struct.pack("<IH", 8, c) + b"\xff" * 14 + struct.pack("<IH", 1, c), q0)
        if q < 0:
            continue
        q0 = q = q + 26
        for size in (2, 0, 2, 6, 6, 2, 2, 2):  # 0: the 8 bytes after the members
            q += 8 if size == 0 else 4 + size * struct.unpack_from("<I", data, q)[0]
        lord = struct.unpack_from("<H", data, q)[0]
        if serves(lord, c):
            out[c] = lord
    return out


def _lords(data, recs):
    return faction_lords(data, FACTIONS,
                         lambda v, c: v in recs and recs[v]["front"][7] == c and recs[v]["t"][1] == 7)


def _offices(data):
    base = _section(data, OFFICES)
    return [_text(data, base + 50 * i, 15) for i in range(OFFICES[1])]


def _year(game_dir, s):
    with open(os.path.join(game_dir, f"sceda{s}.n12"), "rb") as f:
        return struct.unpack_from("<H", f.read(YEAR + 2), YEAR)[0]


def _names(data):
    return [_text(data, NAMES_AT + 213 * k, 11) + _text(data, NAMES_AT + 213 * k + 11, 11) for k in range(COUNT)], \
        [_text(data, NAMES_AT + 213 * k + 22, 19) + _text(data, NAMES_AT + 213 * k + 41, 19) for k in range(COUNT)]


def _bio_entries(game_dir):
    """[(name, text)] of Msg/Bfile01-22.n12 in order (entry k is slot k)"""
    return msg_entries([os.path.join(game_dir, "Msg", f"Bfile{k:02d}.n12") for k in range(1, 23)])


def msg_entries(paths):
    """(name, text) of N12F / N13F message files: +4 u32 string table, +8 u32 n, n u32 from 0x14, then tokens split
    by ',\\n' up to the string table; '&,MSGnnn' shows string nnn, '(,Fnc000' ends a box. The table is u32 count, u32
    first number, count + 1 u32 offsets (cp932 strings between them). Boxes alternate name / text; one box of
    Bfile09.n12 holds the name and the text. A text line ends with a literal '\\n' (the box width), dropped here."""
    out = []
    for path in paths:
        with open(path, "rb") as f:
            d = f.read()
        st, n = struct.unpack_from("<2I", d, 4)
        cnt, first = struct.unpack_from("<2I", d, st)
        offs = struct.unpack_from(f"<{cnt + 1}I", d, st + 8)
        base = st + 8 + 4 * (cnt + 1)
        strings = [d[base + offs[k]:base + offs[k + 1]].decode("cp932") for k in range(cnt)]
        boxes = [[]]
        for t in d[0x14 + 4 * n:st].split(b",\n"):
            if t.startswith(b"&,MSG"):
                boxes[-1].append(strings[int(t[5:]) - first])
            elif t.startswith(b"(,"):
                boxes.append([])
        boxes = [b for b in boxes if b]
        k = 0
        while k < len(boxes):
            name, text = boxes[k][0], boxes[k][1:]
            if not text:
                k += 1
                text = boxes[k]
            out.append((name, "".join(x.replace("\\n", "") for x in text)))
            k += 1
    return out


def bios(game_dir):
    return {k: [("單段", text)] for k, (_, text) in enumerate(_bio_entries(game_dir))}


def bio_names(game_dir):
    names, _ = _names(_data(game_dir, MAIN))
    return {k: names[k] for k in range(OFFICERS)}


def persons(game_dir):
    datas = {s: _data(game_dir, s) for s in SCENARIOS}
    recs = {s: _persons(d) for s, d in datas.items()}
    lords = {s: _lords(d, recs[s]) for s, d in datas.items()}
    years = {s: _year(game_dir, s) for s in SCENARIOS}
    main, names = recs[MAIN], _names(datas[MAIN])
    offices = _offices(datas[MAIN])
    bio_names_ = {k: n for k, (n, _) in enumerate(_bio_entries(game_dir))}
    people = range(OFFICERS)

    def ref(v):
        return v if v < OFFICERS else None

    def label(v):
        return f"{names[0][v]}（槽 {v}）"

    fathers = {i: main[i]["front"][1] for i in people}
    rows = []
    for i in people:
        r = main[i]
        f, t = r["front"], r["t"]
        row = {"id": i, "name": names[0][i], "reading": names[1][i], "born": t[8], "died": t[10],
               "stats": {"統率": t[13], "武勇": t[14], "知略": t[15], "政治": t[16]},
               "hidden": {"相性": t[7], "義理": t[18]},
               "aptitude": {a: GRADES[v] for a, v in zip(ARMS, r["apt"])}}
        notes = ["名字取劇本 12（1603），其他欄位 8 個劇本相同的取劇本 12；scenarios 是 8 個劇本。"
                 "欄位都是從資料推的，沒有讀程式。"]
        if i in bio_names_ and bio_names_[i] != row["name"]:
            notes.append(f"列伝寫「{bio_names_[i]}」。")
        notes.append(f"元服年 {t[9]}。")
        if f[1] != 0xFFFF and ref(f[1]) is None:
            notes.append(f"実父：{label(f[1])}，不是 kaodata 人物。")
        skills = {}
        if f[10] != 0xFFFF:
            skills["固有戦法"] = [TACTICS[f[10]]]
        if skills:
            row["skills"] = skills
        row["game"] = {"出自": ORIGINS[t[4]]}
        office = [(s, recs[s][i]["front"][5]) for s in SCENARIOS if recs[s][i]["front"][5] != 0xFFFF]
        if office:
            row["game"]["官位"] = offices[office[-1][1]]
            notes.append(f"官位（+10）依劇本變，取有官位的最後一個劇本（{office[-1][0]}）。")
        for k, key in ((0, "親愛武将"), (1, "嫌悪武将")):
            if r["lists"][k]:
                row["hidden"][key] = [names[0][v] for v in r["lists"][k]]
        relations = {}
        if ref(f[1]) is not None:
            relations["father"] = [f[1]]
        children = [j for j, v in fathers.items() if v == i]
        if children:
            relations["children"] = children
        siblings = [j for j, v in fathers.items() if j != i and f[1] != 0xFFFF and v == f[1]]
        if siblings:
            relations["siblings"] = siblings
        spouses = list(dict.fromkeys(recs[s][i]["front"][3] for s in SCENARIOS if recs[s][i]["front"][3] != 0xFFFF))
        if [v for v in spouses if ref(v) is not None]:
            relations["spouse"] = [v for v in spouses if ref(v) is not None]
        others = [v for v in spouses if ref(v) is None]
        if others:
            notes.append("配偶者（+6）：" + "、".join(label(v) for v in others) + "，不是 kaodata 人物。")
        relations["clan"] = t[0]
        row["relations"] = relations
        if f[2] != 0xFFFF:
            notes.append(f"養父（+4）：{label(f[2])}。")
        row["scenarios"] = []
        missing = []
        for s in SCENARIOS:
            rs = recs[s][i]
            ts, y = rs["t"], years[s]
            sc = {"scenario": int(s), "year": y}
            faction = rs["front"][7]
            if ts[1] == 7 or ts[1] == 2:
                if ts[1] == 7 and faction in lords[s]:
                    sc["lord"] = lords[s][faction]
                sc["location"] = rs["location"]
                sc["status"] = "大名" if sc.get("lord") == i else "家臣" if ts[1] == 7 else "浪人"
                if sc["status"] == "家臣":
                    sc["loyalty"] = ts[19]
            elif ts[1] in (0, 1) or (ts[1] == 8 and ts[10] >= y and ts[9] > y):
                sc["status"] = "未登場"
                sc["debut"] = ts[9]
            else:
                if ts[10] > y:
                    missing.append(s)
                continue
            row["scenarios"].append(sc)
        if missing:
            notes.append("劇本 " + "、".join(missing) + " 在世、已元服，但記錄是浪人／未登場（t1＝8）且沒有所在拠点，"
                         "推定是事件才登場，登場年不明，沒有列。")
        row["uncertain"] = ["aptitude", "hidden.親愛武将", "hidden.嫌悪武将", "scenarios.status", "scenarios.debut",
                            "scenarios.loyalty"]
        notes.append("status 依 t1：7＝家臣（所属勢力的当主是自己時寫大名）、2＝浪人、0／1 與未元服的 8＝未登場，"
                     "debut 用元服年；這些對應是推定。lord 是所属勢力（+14）在段 20 的当主。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows
