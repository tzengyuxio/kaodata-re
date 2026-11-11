"""信長の野望・創造 with PK (nobu14pk-win, Steam 292990 + DLC 344120, Traditional Chinese only) for koei-wiki: persons
(koei-persons/1), 城 and 國 (koei-places/1) and 列伝. game_dir is the Steam depot (games/steam/292990-tchinese/depot).
SCENARIO_PK/sceda??.n14 and fixdata.n14 are each one LWC block after a text header; the decoded data is a run of
(u32 key, u32 count) sections. Layouts and evidence: notes/nobu14.md."""
import os
import re
import struct

import ls11

SCENARIOS = ["02", "03", "04", "05", "06", "07", "16", "17", "18", "19"]  # PK; 01 is the tutorial
MAIN = "02"  # names, stats and relations come from 1551 繼承家督
PERSONS = (22, 3622)
HOUSES = (23, 120)
CASTLE_NAMES = (10, 601)  # 42 bytes: name 13, reading 19 ("dummy"), 10
SITES = (11, 1500)  # 拠点, 21 bytes: +0 u16 國, +2 u32 x, +6 u32 y, +10 u16 kind (3 = castle), +14 u16 castle id
SENPO = (2, 103)  # fixdata: 戦法, 139 bytes (name 13 at +0)
GROWTH = (19, 109)  # fixdata: 成長型, 263 bytes
PROVINCES = (15, 76)  # fixdata: 國, 30 bytes (name 11 at +0); 本城 k is in 國 k
HONJOU = 76  # castles 0-75 are the 本城 of 國 0-75; 76-89 are unused or "0"
ITEMS = (13, 160)  # fixdata: 家宝 names, 42 bytes (name 13, reading 19 "dummy", 10 zero)
# scenario: 160 家宝 x 17 bytes right after the 75 城郭 records of section 13: u16 holder 家, u16 holder person, u32
# 細類 (0-53: 茶入, 茶碗, 釜…, 刀, 槍, 鉄砲, 甲冑, 兜, 書, 絵, 南蛮品), u32 等級 1-10, u32 種類 (KINDS), u8 flags
KINDS = ["茶具", "武具", "名馬", "書", "繪畫", "香具", "南蠻物", "唐物"]  # NOBU14PK.exe strings, in this order
PROVINCE_ID = 1000  # place id of 國 k
YEAR, TITLE = 0x498, 0x1C5  # scenario header: u16 year, scenario name
HOUSE_TAIL = 3354  # a 家 record ends with a fixed part of this size; its first u16 is the 当主 slot
# Traditional Chinese names put Japanese kanji on these Big5 codes (as 大志, notes/nobu15.md「繁中外字」, plus A275)
GAIJI = {0xA263: "雫", 0xA265: "籾", 0xA268: "簗", 0xA26D: "鑓", 0xA26E: "垪", 0xA26F: "梶", 0xA270: "榊",
         0xA271: "畠", 0xA272: "樋", 0xA273: "樫", 0xA275: "条", 0xA278: "坂", 0xA279: "宍", 0xA27A: "誾",
         0xF9DA: "恒"}
# +42 of the person record (scenario 02 counts): 7 serving a 家, 3 浪人 on the map, 8 浪人 not yet placed (most with no
# 所在), 1 born but not of age, 0 not born yet, 6 姫
STATUS = {7: "家臣", 3: "浪人", 8: "浪人", 6: "姫"}


def text(b):
    b = b.split(b"\0")[0]
    out, i = [], 0
    while i < len(b):
        if b[i] >= 0x81 and i + 1 < len(b):
            code = b[i] << 8 | b[i + 1]
            out.append(GAIJI.get(code) or b[i:i + 2].decode("cp950", "replace"))
            i += 2
        else:
            out.append(chr(b[i]))
            i += 1
    return "".join(out)


def _decode(path):
    with open(path, "rb") as f:
        raw = f.read()
    return raw, ls11.lwc_decode(raw[raw.index(b"LWC\x1a"):])


def _section(data, key):
    return data.index(struct.pack("<2I", *key)) + 8


def scenario(game_dir, s):
    raw, data = _decode(os.path.join(game_dir, "SCENARIO_PK", _name(game_dir, s)))
    return struct.unpack_from("<H", raw, YEAR)[0], text(raw[TITLE:TITLE + 40]), data


def _name(game_dir, s):
    for n in os.listdir(os.path.join(game_dir, "SCENARIO_PK")):
        if n.lower() == f"sceda{s}.n14":
            return n
    raise FileNotFoundError(f"SCENARIO_PK/sceda{s}.n14")


def fixdata(game_dir):
    return _decode(os.path.join(game_dir, "SCENARIO_PK", "fixdata.n14"))[1]


def persons_raw(data):
    """[(name, [4 lists], fixed 96 bytes)] of the 3622 slots: name 11 + 11, readings 19 + 19, 諱 11 + reading 19,
    four "u32 n + n u16" lists (2 親愛, 3 嫌悪 【推】, 4 戦法), then 96 bytes"""
    p, out = _section(data, PERSONS), []
    for _ in range(PERSONS[1]):
        name = text(data[p:p + 11]) + text(data[p + 11:p + 22])
        q, lists = p + 90, []
        for _ in range(4):
            n, = struct.unpack_from("<I", data, q)
            lists.append(list(struct.unpack_from(f"<{n}H", data, q + 4)))
            q += 4 + 2 * n
        out.append((name, lists, data[q:q + 96]))
        p = q + 96
    return out, p


def surnames(data):
    """the 姓 field (first 11 bytes) of each of the slots of persons_raw"""
    p, out = _section(data, PERSONS), []
    for _ in range(PERSONS[1]):
        out.append(text(data[p:p + 11]))
        q = p + 90
        for _ in range(4):
            q += 4 + 2 * struct.unpack_from("<I", data, q)[0]
        p = q + 96
    return out


def houses(data, people):
    """{家 id: 当主 slot}: records start right after the persons; named ones carry "dummy" as reading at +13"""
    start, end = persons_raw(data)[1] + 8, _section(data, (24, 376)) - 8
    starts, i = [], start
    while True:
        i = data.find(b"dummy\0", i, end)
        if i < 0:
            break
        starts.append(i - 13)
        i += 6
    lords = {}
    for a, b in zip(starts, starts[1:] + [None]):
        hid, = struct.unpack_from("<H", data, a + 0x5B)
        if b is None:  # the last named 家 is followed by unnamed records; find its lord by the person table instead
            continue
        lord, = struct.unpack_from("<H", data, b - HOUSE_TAIL)
        if lord < len(people) and _u16(people[lord][2], 10) == hid:
            lords[hid] = lord
    return lords


def _u16(t, o):
    return struct.unpack_from("<H", t, o)[0]


def castles(data):
    """{castle id: (name, 國, x, y)} of the castles in this scenario (拠点 of kind 3)"""
    base, sites = _section(data, CASTLE_NAMES), _section(data, SITES)
    out = {}
    for k in range(SITES[1]):
        prov, x, y, kind, _, cid = struct.unpack_from("<HIIHHH", data, sites + 21 * k)
        if kind == 3:
            out[cid] = (text(data[base + 42 * cid:base + 42 * cid + 13]), prov, x, y)
    return out


def _table(fix, key, size, n=13):
    base = _section(fix, key)
    return [text(fix[base + size * i:base + size * i + n]) for i in range(key[1])]


def places(game_dir, out_dir):
    fix = fixdata(game_dir)
    provinces = _table(fix, PROVINCES, 30, 11)
    seen = {}
    for s in SCENARIOS:
        _, _, data = scenario(game_dir, s)
        for cid, v in castles(data).items():
            seen.setdefault(cid, (v, []))[1].append(s)
    rows = []
    for cid in sorted(seen):
        (name, prov, x, y), ss = seen[cid]
        row = {"id": cid, "name": name, "level": "本城" if cid < HONJOU else "支城", "province": provinces[prov],
               "pos": {"x": x, "y": y, "grid": "nobu14-map"}, "uncertain": ["level", "pos"]}
        notes = (f"城號 {cid}（人物所在 +18 用的號碼）；國、座標取段 11 的拠点表（國 +0、x +2、y +6），座標的單位與原點沒對。"
                 "本城、支城是這邊依城號分的（0–75 是各國的本城）。")
        if len(ss) < len(SCENARIOS):
            notes += "只出現在劇本 " + "、".join(ss) + "。"
        row["notes"] = notes
        rows.append(row)
    for k, name in enumerate(provinces):
        rows.append({"id": PROVINCE_ID + k, "name": name, "level": "國",
                     "notes": f"國號 {k}（place id 是國號＋1000）；本城是城號 {k}。相鄰沒找到。"})
    return rows


def persons(game_dir):
    fix = fixdata(game_dir)
    senpo = _table(fix, SENPO, 139)
    growth = _table(fix, GROWTH, 263)
    provinces = _table(fix, PROVINCES, 30, 11)
    scen = {s: scenario(game_dir, s) for s in SCENARIOS}
    recs = {s: persons_raw(scen[s][2])[0] for s in SCENARIOS}
    lords = {s: houses(scen[s][2], recs[s]) for s in SCENARIOS}
    main = recs[MAIN]
    family = surnames(scen[MAIN][2])
    people = [k for k, r in enumerate(main) if r[0] and r[0] != "預備預備"]  # 44 spare slots
    known = set(people)
    fathers = {k: _u16(main[k][2], 2) for k in people}
    rows = []
    for k in people:
        name, lists, t = main[k]
        row = {"id": k, "name": name}
        if family[k] and name.startswith(family[k]) and family[k] != name:
            row["familyName"] = family[k]
        row.update({"born": _u16(t, 31), "died": _u16(t, 35),
                    "stats": {"統率": t[38], "武勇": t[39], "知略": t[40], "政治": t[41]},
                    "hidden": {"創造性": t[37]}})
        if _u16(t, 22) != 0xFFFF:
            row["hidden"]["血族"] = _u16(t, 22)
        for key, lst in (("親愛武將", lists[1]), ("嫌惡武將", lists[2])):
            v = [main[x][0] for x in lst if x < len(main) and main[x][0]]
            if v:
                row["hidden"][key] = v
        if lists[3]:
            row["skills"] = {"戦法": [senpo[v] for v in lists[3]]}
        row["game"] = {"成長型": growth[t[46]], "出身": provinces[t[47]]}
        relations = {}
        father = fathers[k]
        if father in known:
            relations["father"] = [father]
        children = [j for j, v in fathers.items() if v == k]
        if children:
            relations["children"] = children
        siblings = [j for j, v in fathers.items() if j != k and father != 0xFFFF and v == father]
        if siblings:
            relations["siblings"] = siblings
        spouses = list(dict.fromkeys(_u16(recs[s][k][2], 6) for s in SCENARIOS
                                     if _u16(recs[s][k][2], 6) != 0xFFFF))
        if [v for v in spouses if v in known]:
            relations["spouse"] = [v for v in spouses if v in known]
        if relations:
            row["relations"] = relations
        row["scenarios"] = []
        for s in SCENARIOS:
            year, title, _ = scen[s]
            ts = recs[s][k][2]
            st, house, loc = ts[42], _u16(ts, 10), _u16(ts, 18)
            sc = {"scenario": int(s), "year": year}
            if st in STATUS and (st != 8 or ts[14] == 3):
                if st == 7 and house in lords[s]:
                    sc["lord"] = lords[s][house]
                sc["status"] = "大名" if sc.get("lord") == k else STATUS[st]
                if loc != 0xFFFF:
                    sc["location"] = loc
            elif st in (0, 1, 8) and _u16(ts, 35) >= year and _u16(ts, 33) >= year:  # dead or gone: not listed
                sc["status"] = "未登場"
                sc["debut"] = _u16(ts, 33)
            else:
                continue
            row["scenarios"].append(sc)
        others = list(dict.fromkeys(recs[s][k][0] for s in SCENARIOS if recs[s][k][0] != name))
        row["uncertain"] = ["hidden.創造性", "hidden.親愛武將", "hidden.嫌惡武將", "relations.spouse",
                            "scenarios.status", "scenarios.debut"]
        row["notes"] = ("名字與固定欄位取劇本 02（1551），scenarios 是 PK 的 10 個劇本。欄位都是從資料推的，沒有讀程式："
                        "生年 +31、登場年 +33、歿年 +35、創造性 +37（0–100，信長 100）、能力 +38–41、成長型 +46、"
                        "出身國 +47、父 +2、配偶 +6、所屬家 +10、所在城 +18、血族 +22；戦法是第 4 個陣列。"
                        "status 依 +42：7 仕官（所屬家的当主是自己時寫大名）、3 與在地圖上的 8 是浪人、6 是姫、"
                        "0／1 與不在地圖上的 8 是未登場（debut 用 +33），劇本年已過世的不列。"
                        + ("其他劇本的名字：" + "、".join(others) + "。" if others else ""))
        rows.append(row)
    return rows


def _items_raw(data):
    p = data.index(struct.pack("<2I", 14, 160)) + 8  # section 14 holds the count 160 only; the records follow it
    return [struct.unpack_from("<HHIIIB", data, p + 17 * i) for i in range(ITEMS[1])]


def _strings(path):
    """the strings of an N14F message file"""
    with open(path, "rb") as f:
        d = f.read()
    st, = struct.unpack_from("<I", d, 4)
    cnt, _ = struct.unpack_from("<2I", d, st)
    offs = struct.unpack_from(f"<{cnt + 1}I", d, st + 8)
    base = st + 8 + 4 * (cnt + 1)
    return [text(d[base + offs[i]:base + offs[i + 1]]) for i in range(cnt)]


def items(game_dir):
    """koei-items/1 rows: names from fixdata, the rest from each scenario; descriptions are MSG_PK/
    kahou_retsuden01-04_0.n14 (name / text pairs in item order)"""
    names = _table(fixdata(game_dir), ITEMS, 42)
    texts = []
    for k in range(1, 5):
        ss = _strings(os.path.join(game_dir, "MSG_PK", f"kahou_retsuden{k:02d}_0.n14"))[2:]
        texts += [(ss[i], ss[i + 1].replace("\\n", "")) for i in range(0, len(ss) - 1, 2)]
    assert len(texts) == ITEMS[1], len(texts)
    holders, base = {}, None
    for s in SCENARIOS:
        _, _, data = scenario(game_dir, s)
        people, _ = persons_raw(data)
        house_names = _house_names(data)
        raw = _items_raw(data)
        base = base or raw
        for i, (house, person, *_rest) in enumerate(raw):
            if person != 0xFFFF:
                holders.setdefault(i, []).append({"scenario": int(s), "person": person})
            elif house != 0xFFFF:
                holders.setdefault(i, []).append({"scenario": int(s), "other": house_names.get(house, f"家 {house}")})
    rows = []
    for i, name in enumerate(names):
        _, _, sub, grade, kind, _ = base[i]
        title, body = texts[i]
        row = {"id": i, "name": name, "kind": KINDS[kind], "grade": str(grade), "description": body,
               "holders": holders.get(i, []), "uncertain": ["grade"],
               "notes": f"細類號 {sub}（同一細類的名稱沒找到）；grade 是等級欄的原值 1–10，和畫面上「一等級」…「十等級」"
                        "哪一端對應沒確認。持有者取各劇本開局：持有人欄（+2）有值時是人物，否則是持有的家（+0）。"}
        if title != name:
            row["notes"] += f"說明的標題寫成「{title}」。"
        rows.append(row)
    return rows


def _house_names(data):
    start, end = persons_raw(data)[1] + 8, _section(data, (24, 376)) - 8
    out, i = {}, start
    while True:
        i = data.find(b"dummy\0", i, end)
        if i < 0:
            return out
        out[_u16(data, i - 13 + 0x5B)] = text(data[i - 13:i])
        i += 6


def house_names(game_dir):
    """{血族 (person +22, also the 家紋 number): [names]}: the 家 of every PK scenario keyed by their 当主's 血族, most
    frequent first (the 家 ids at +0x5B change between scenarios, the 血族 do not)"""
    count = {}
    for s in SCENARIOS:
        _, _, data = scenario(game_dir, s)
        people = persons_raw(data)[0]
        names = _house_names(data)
        for hid, lord in houses(data, people).items():
            c = count.setdefault(_u16(people[lord][2], 22), {})
            c[names[hid]] = c.get(names[hid], 0) + 1
    return {h: sorted(c, key=lambda n: (-c[n], len(n))) for h, c in count.items()}


def house_surnames(game_dir):
    """{血族: most common 姓 of its persons} in the main scenario"""
    _, _, data = scenario(game_dir, MAIN)
    p, count = _section(data, PERSONS), {}
    for _ in range(PERSONS[1]):
        sei = text(data[p:p + 11])
        q = p + 90
        for _ in range(4):
            q += 4 + 2 * struct.unpack_from("<I", data, q)[0]
        if sei and not sei.startswith("預備"):
            c = count.setdefault(_u16(data, q + 22), {})
            c[sei] = c.get(sei, 0) + 1
        p = q + 96
    return {h: max(c, key=c.get) for h, c in count.items()}


def _retsuden(game_dir):
    """(name, text) of MSG_PK/bushou_retsuden01-40_0.n14: N14F, read as N12F (wiki_nobu12.msg_entries) but Big5 with
    the GAIJI codes: tokens split by ',\\n' show string nnn ('&,MSGnnn') or end a box ('(,'). Each string is its own
    box: a name (at most 8 characters, no 。) starts an entry, the text follows in one or two boxes"""
    out = []
    for k in range(1, 41):
        with open(os.path.join(game_dir, "MSG_PK", f"bushou_retsuden{k:02d}_0.n14"), "rb") as f:
            d = f.read()
        st, n = struct.unpack_from("<2I", d, 4)
        cnt, first = struct.unpack_from("<2I", d, st)
        offs = struct.unpack_from(f"<{cnt + 1}I", d, st + 8)
        base = st + 8 + 4 * (cnt + 1)
        strings = [text(d[base + offs[i]:base + offs[i + 1]]) for i in range(cnt)]
        boxes = [[]]
        for t in d[0x14 + 4 * n:st].split(b",\n"):
            if t.startswith(b"&,MSG"):
                boxes[-1].append(strings[int(t[5:]) - first])
            elif t.startswith(b"(,"):
                boxes.append([])
        for box in boxes:  # every string is a box of its own; a long text takes two
            for t in box:
                if t in ("", "Error"):
                    continue
                if len(t) <= 8 and "。" not in t and "\\n" not in t:
                    out.append([t, ""])
                else:
                    out[-1][1] += t.replace("\\n", "")
    return out


def _bios(game_dir):
    """{slot: (name, text)}: the entries follow the slot order of scenario 02, skipping slots without one"""
    names = [set() for _ in range(PERSONS[1])]  # a slot's names change across scenarios (石川信直 → 南部信直)
    for s in SCENARIOS:
        for k, r in enumerate(persons_raw(scenario(game_dir, s)[2])[0]):
            names[k].add(r[0])
    entries = [e for e in _retsuden(game_dir) if e[0] != "NoName"]  # 75 placeholders with no text of a person
    where = {}
    for j, ns in enumerate(names):
        for n in ns:
            where.setdefault(n, []).append(j)
    hits, k = [], 0
    for name, _ in entries:  # by name; a name on several slots takes the first one after the previous entry's
        js = where.get(name, [])
        if not js and "?" in name:  # the game's text lacks the glyph (蠣崎公?)
            pat = re.compile(re.escape(name).replace(r"\?", "."))
            js = sorted(j for n, v in where.items() if len(n) == len(name) and pat.fullmatch(n) for j in v)
        hit = next((j for j in js if j >= k), js[0] if js else None)
        hits.append(hit)
        k = hit + 1 if hit is not None else k
    out = {}
    for e, (name, body) in enumerate(entries):
        hit = hits[e]
        if hit is None:  # renamed in play or written differently (蘆名盛重, 津輕信牧): next to the neighbours
            before = hits[e - 1] + 1 if e and hits[e - 1] is not None else None
            after = hits[e + 1] - 1 if e + 1 < len(hits) and hits[e + 1] is not None else None
            hit = before if before is not None and before not in out else after
            if hit is None or hit in out or not names[hit] - {""}:
                SKIPPED.append(name)
                continue
        out[hit] = (name, body)
    return out


def bios(game_dir):
    return {k: [("單段", body)] for k, (_, body) in _bios(game_dir).items()}


def bio_names(game_dir):
    return {k: name for k, (name, _) in _bios(game_dir).items()}


BIO_LANG = "zh-Hant"
SKIPPED = []  # 列伝 entries without a slot, filled by _bios
