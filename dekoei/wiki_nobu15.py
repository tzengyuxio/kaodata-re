"""信長の野望・大志 with PK (nobu15pk-win, Steam 628890) for koei-wiki: persons (koei-persons/1), 城・國・地方
(koei-places/1), 列伝 and 家宝 (koei-items/1). game_dir is the Steam install (games/steam/628890) or a directory with
the same SCENARIO_PK_JP/_TC, MSG_PK_JP and fixdata files. Layouts and evidence: notes/nobu15.md.

- SCENARIO_PK_{JP,TC}/sceda??.n15 and fixdata.n15: a text header, then one LWC block; the decoded data is a run of
  (u32 key, u32 count) sections, found here by those 8 bytes. Header: +0x1BD scenario name, +0x199E u16 start year.
- Persons (key 0, 3952 variable records): 姓 11, 名 11, readings 19 + 19, 諱 11 + reading 19, four "u32 n + n u16"
  lists, then 101 fixed bytes (PK): +4 father, +6 adoptive father, +8 spouse, +11 勢力, +14 3 on the map, +18 castle,
  +22 家 (clan), +32 born, +34 debut, +36 died, +39 status, +44 成長型 (fixdata key 16 row), +46-+70 skill bits,
  +74 mother, +81-85 統率 武勇 知略 内政 外政, +97 野心.
- Skills: fixdata key 15 (200 x 290 bytes: name 9, reading, +36 kind) numbers the bits of fixed +46-+70; kind 0-5 are
  個性, 6 作戦, 7 戦法, 8 補佐効果 (PK), 255 unused.
- 勢力 records (key 1, 147 variable records named "…家"): +36 u32 1, +40 u16 勢力 id, +42 u32 n + n u16, 8 bytes,
  u32 m + m u16, 8 bytes, then u16 当主 slot. Records after the named ones change layout, so each is found by its name.
"""
import os
import re
import struct

import ls11
from nobu15_extras import _n15a

SCENARIOS = ["02", "03", "04", "05", "06", "07", "08", "10", "11", "12", "13", "14"]  # PK; 01 is the tutorial
MAIN = "02"
PERSONS = 3952
FIXED = 101
CASTLES = (21, 350, 105)  # name 26, +26 u16 拠点, +28 u16 castle id
PROVINCES = {"JP": (10, 71, 32), "TC": (10, 71, 13)}  # JP: name 11, reading 19, +30 東中西, +31 地方; TC: name 11, +12 地方
REGIONS = {"JP": (12, 12, 36), "TC": (12, 12, 17)}  # JP: name 7, reading 19, u32 6, 6 adjacent (0xFF ends)
YEAR, TITLE = 0x199E, 0x1BD
PROVINCE_ID, REGION_ID = 1000, 2000
STATS = ["統率", "武勇", "知略", "内政", "外政"]
GROWTH, GROWTH_AT, AMBITION_AT = (16, 109, 16), 44, 97  # 成長型 table (name 15); person +44 row, +97 野心
# person +86 u8: the 志 type (one per person or house, not a fixdata key 6 row); only the types checked against the
# official guide (織田 pages) and screenshots are named, the type -> name table is not found
SHI_AT, SHI = 86, {13: "領地保全", 14: "家名存続", 15: "所領拡大", 16: "天下統一", 46: "家督継承", 21: "天下布武",
                   52: "天が下知る"}
SKILLS, SKILL_BITS = (15, 200, 290), 46  # fixdata key 15; bit k of fixed +46-+70 is skill k
SKILL_KINDS = {0: "個性", 1: "個性", 2: "個性", 3: "個性", 4: "個性", 5: "個性", 6: "作戦", 7: "戦法", 8: "補佐効果"}
# +39 (scenario 02 counts): 7 serving a 勢力, 3 浪人, 6 姫, 0 not born yet, 1 born but not yet out (with or
# without a 勢力 at +11), 8 off the map (dead, or alive elsewhere like 武田信虎), 9 one case (上杉景虎)
STATUS = {7: "家臣", 3: "浪人", 6: "姫"}
ENC = {"JP": "cp932", "TC": "cp950"}
# 繁中版 puts Japanese kanji on these Big5 codes (notes/nobu15.md「繁中外字」); 日文版 writes 誾 as 0x84A1
GAIJI = {"TC": {0xA24C: "瀞", 0xA263: "雫", 0xA265: "籾", 0xA268: "簗", 0xA26C: "畑", 0xA26D: "鑓", 0xA26E: "垪",
                0xA26F: "梶", 0xA270: "榊", 0xA271: "畠", 0xA272: "樋", 0xA273: "樫", 0xA278: "坂", 0xA279: "宍",
                0xA27A: "誾", 0xA2A8: "圀", 0xF9DA: "恒"},
         "JP": {0x84A1: "誾"}}
DUMMY = ("ダミーダミー", "")


def text(b, lang):
    b = b.split(b"\0")[0]
    out, i = [], 0
    while i < len(b):
        if b[i] >= 0x81 and i + 1 < len(b):
            code = b[i] << 8 | b[i + 1]
            out.append(GAIJI[lang].get(code) or b[i:i + 2].decode(ENC[lang], "replace"))
            i += 2
        else:
            out.append(chr(b[i]))
            i += 1
    return "".join(out)


def _decode(path):
    with open(path, "rb") as f:
        raw = f.read()
    return raw, ls11.lwc_decode(raw[raw.index(b"LWC\x1a"):])


def _key(data, key, count):
    return data.index(struct.pack("<2I", key, count)) + 8


def scenario(game_dir, s, lang="JP"):
    raw, data = _decode(os.path.join(game_dir, f"SCENARIO_PK_{lang}", f"sceda{s}.n15"))
    return struct.unpack_from("<H", raw, YEAR)[0], text(raw[TITLE:TITLE + 60], lang), data


def fixdata(game_dir, lang="JP"):
    return _decode(os.path.join(game_dir, f"SCENARIO_PK_{lang}", "fixdata.n15"))[1]


def persons_raw(data, lang):
    """[(name, reading, lists, fixed)] of the 3952 slots, and the end of the table"""
    p, out = _key(data, 0, PERSONS), []
    for _ in range(PERSONS):
        name = text(data[p:p + 11], lang) + text(data[p + 11:p + 22], lang)
        reading = text(data[p + 22:p + 41], lang) + text(data[p + 41:p + 60], lang)
        q, lists = p + 90, []
        for _ in range(4):
            n, = struct.unpack_from("<I", data, q)
            lists.append(struct.unpack_from(f"<{n}H", data, q + 4))
            q += 4 + 2 * n
        out.append((name, reading, lists, data[q:q + FIXED]))
        p = q + FIXED
    return out, p


def _u16(t, o):
    return struct.unpack_from("<H", t, o)[0]


def lords(data, people, end, lang):
    """{勢力 id: (name, 当主 slot)}; a record is accepted when its 当主's +11 is that 勢力"""
    stop = data.index(struct.pack("<2I", 1 + 1, 147), end)
    ie, out = "家".encode(ENC[lang]), {}
    for m in re.finditer(re.escape(ie) + b"\0", data[end:stop]):
        e = end + m.start()
        for q in range(e - 10, e + 1, 2):
            if data[q + 36:q + 40] != b"\1\0\0\0":
                continue
            f, = struct.unpack_from("<H", data, q + 40)
            n1, = struct.unpack_from("<I", data, q + 42)
            if n1 > 400:
                continue
            lst = q + 46 + 2 * n1
            n2, = struct.unpack_from("<I", data, lst + 8)
            if n2 > 400:
                continue
            lord, = struct.unpack_from("<H", data, lst + 12 + 2 * n2 + 8)
            if lord < PERSONS and people[lord][3][11] == f:
                out[f] = (text(data[q:e + 2], lang), lord)
                break
    return out


def _castles(data, lang):
    """{castle id: name} of the named castles"""
    p, n, size = CASTLES
    base, out = _key(data, p, n), {}
    for k in range(n):
        r = data[base + size * k:base + size * (k + 1)]
        name = text(r[:26], lang)
        if name:
            out[_u16(r, 28)] = name
    return out


def _records(data, spec):
    key, n, size = spec
    base = _key(data, key, n)
    return [data[base + size * k:base + size * (k + 1)] for k in range(n)]


def places(game_dir, out_dir):
    fj, ft = fixdata(game_dir, "JP"), fixdata(game_dir, "TC")
    regions_j, regions_t = _records(fj, REGIONS["JP"]), _records(ft, REGIONS["TC"])
    provs_j, provs_t = _records(fj, PROVINCES["JP"]), _records(ft, PROVINCES["TC"])
    region_names = [text(r[:7], "TC") for r in regions_t]
    rows = []
    for k, (rj, rt) in enumerate(zip(regions_j, regions_t)):
        name, ja = text(rt[:7], "TC"), text(rj[:7], "JP")
        raw = [REGION_ID + a for a in rj[30:36] if a != 0xFF]
        assert raw == [REGION_ID + a for a in rt[11:17] if a != 0xFF]
        adj = list(dict.fromkeys(raw))
        row = {"id": REGION_ID + k, "name": name, "reading": text(rj[7:26], "JP"), "level": "地方", "adjacent": adj,
               "notes": f"地方號 {k}（place id 是地方號＋2000）；相鄰取 fixdata key 12 的地方記錄。"}
        if adj != raw:  # 甲信 lists 北陸 twice and not 東海, while 東海 lists 甲信
            row["notes"] += "遊戲資料把同一個地方列了兩次，這裡只留一次；東海列了甲信，甲信卻沒列東海（日文、繁中版相同）。"
        if ja != name:
            row["nameJa"] = ja
        rows.append(row)
    by_id = {r["id"]: r for r in rows}
    for r in rows:
        for a in r["adjacent"]:
            if r["id"] not in by_id[a]["adjacent"]:
                r["notes"] += f"這裡列了{by_id[a]['name']}，{by_id[a]['name']}卻沒列這裡（遊戲資料如此）。"
    for k, (rj, rt) in enumerate(zip(provs_j, provs_t)):
        name, ja = text(rt[:11], "TC"), text(rj[:11], "JP")
        row = {"id": PROVINCE_ID + k, "name": name, "reading": text(rj[11:30], "JP"), "level": "國",
               "region": region_names[rj[31]],
               "notes": f"國號 {k}（place id 是國號＋1000）；所屬地方取 fixdata key 10 +31。國的相鄰、城屬於哪一國都沒找到。"}
        if ja != name:
            row["nameJa"] = ja
        rows.append(row)
    seen = {}
    for s in SCENARIOS:
        cj = _castles(scenario(game_dir, s, "JP")[2], "JP")
        ct = _castles(scenario(game_dir, s, "TC")[2], "TC")
        for cid, name in ct.items():
            seen.setdefault(cid, [name, cj.get(cid, name), []])[2].append(s)
    for cid in sorted(seen):
        name, ja, ss = seen[cid]
        row = {"id": cid, "name": name, "level": "城", "uncertain": ["level"],
               "notes": f"城號 {cid}（人物所在 +18 用的號碼，劇本 key 21 記錄 +28）；遊戲裡城、館等的分類沒找到，level 一律寫城。"}
        if ja != name:
            row["nameJa"] = ja
        if len(ss) < len(SCENARIOS):
            row["notes"] += "只出現在劇本 " + "、".join(ss) + "。"
        rows.append(row)
    return rows


def skill_table(game_dir):
    """[(name, kind or None)] of the 200 skills (Japanese)"""
    return [(text(r[:9], "JP"), SKILL_KINDS.get(r[36])) for r in _records(fixdata(game_dir, "JP"), SKILLS)]


def _skills(t, table):
    out = {}
    for k, (name, kind) in enumerate(table):
        if t[SKILL_BITS + k // 8] >> (k % 8) & 1:
            assert kind, (k, name)
            out.setdefault(kind, []).append(name)
    return out


def _load(game_dir):
    scen, recs, lord = {}, {}, {}
    for s in SCENARIOS:
        year, title, data = scenario(game_dir, s, "JP")
        people, end = persons_raw(data, "JP")
        scen[s], recs[s], lord[s] = (year, title), people, lords(data, people, end, "JP")
    return scen, recs, lord


def persons(game_dir):
    scen, recs, lord = _load(game_dir)
    tc = persons_raw(scenario(game_dir, MAIN, "TC")[2], "TC")[0]
    main = recs[MAIN]
    people = [k for k, r in enumerate(main) if r[0] not in DUMMY]
    known = set(people)
    fathers = {k: _u16(main[k][3], 4) for k in people}
    table = skill_table(game_dir)
    growth = [text(r[:15], "JP") for r in _records(fixdata(game_dir, "JP"), GROWTH)]
    mothers = {k: _u16(main[k][3], 74) for k in people}
    rows = []
    for k in people:
        name_ja, reading, lists, t = main[k]
        name = tc[k][0] or name_ja
        row = {"id": k, "name": name}
        if name_ja != name:
            row["nameJa"] = name_ja
        if reading:
            row["reading"] = reading
        row.update({"born": _u16(t, 32), "died": _u16(t, 36), "stats": dict(zip(STATS, t[81:86]))})
        row["more"] = {"野心": t[AMBITION_AT]}
        if t[SHI_AT] in SHI:
            row["more"]["志"] = SHI[t[SHI_AT]]
        if growth[t[GROWTH_AT]]:
            row["hidden"] = {"成長型": growth[t[GROWTH_AT]]}
        skills = _skills(t, table)
        if skills:
            row["skills"] = {kind: skills[kind] for kind in ("個性", "戦法", "作戦", "補佐効果") if kind in skills}
        relations = {}
        for key, v in (("father", fathers[k]), ("mother", mothers[k])):
            if v in known:
                relations[key] = [v]
        children = [j for j in people if j != k and k in (fathers[j], mothers[j])]
        if children:
            relations["children"] = children
        f = fathers[k]
        siblings = [j for j in people if j != k and f != 0xFFFF and fathers[j] == f]
        if siblings:
            relations["siblings"] = siblings
        spouses = list(dict.fromkeys(_u16(recs[s][k][3], 8) for s in SCENARIOS))
        spouses = [v for v in spouses if v in known]
        if spouses:
            relations["spouse"] = spouses
        relations["clan"] = _u16(t, 22)
        row["relations"] = relations
        row["scenarios"] = []
        for s in SCENARIOS:
            year, _ = scen[s]
            ts = recs[s][k][3]
            st, force, loc = ts[39], ts[11], _u16(ts, 18)
            sc = {"scenario": int(s), "year": year}
            if st in STATUS:
                if st == 7 and force in lord[s]:
                    sc["lord"] = lord[s][force][1]
                sc["status"] = "大名" if sc.get("lord") == k else STATUS[st]
                if _u16(ts, 14) == 3:
                    sc["location"] = loc
            elif st in (0, 1) and _u16(ts, 34) >= year:
                sc["status"] = "未登場"
                sc["debut"] = _u16(ts, 34)
            else:
                continue
            row["scenarios"].append(sc)
        names = list(dict.fromkeys(recs[s][k][0] for s in SCENARIOS if recs[s][k][0] != name_ja))
        adoptive = _u16(t, 6)
        row["uncertain"] = ["relations.mother", "relations.spouse", "relations.clan", "scenarios.status",
                            "scenarios.debut"]
        row["notes"] = ("名字與固定欄位取劇本 02（1545）的日文版，name 用繁中版同一槽；scenarios 是 PK 的 12 個劇本。"
                        "能力 +81–85 對過明智光秀、岡国高的武將情報截圖（五項全同）；skills 是 +46–+70 的位元（位元號＝fixdata "
                        "key 15 的序號），個性、戦法、作戦用本體劇本對過兩人的截圖，PK 改了部分人的戦法（明智光秀 逆撫で→麒麟児）；"
                        "補佐効果是 PK 加的，分類照記錄 +36。野心 +97 對過兩人的截圖（光秀 10、岡国高 4），劇本 02 的值。"
                        "成長型 +44 是 fixdata key 16 的列號（本多忠勝→本多忠勝型、毛利元就→毛利元就型）。"
                        "志是 +86 的種類號，只寫出對過證據的 7 種（一般武將的領地保全、家名存続、所領拡大、天下統一、家督継承，信長 天下布武、"
                        "光秀 天が下知る：攻略本的織田家武將頁與截圖），其他大名、名將各有自己的號，號↔名稱的表還沒找到；気質還沒找到。其餘欄位是從資料推的：生年 +32、"
                        "登場年 +34、歿年 +36、父 +4、母 +74、配偶 +8（各劇本）、家 +22（relations.clan）、勢力 +11、"
                        "所在城 +18。status 依 +39：7 仕官（勢力的当主是自己時寫大名）、3 浪人、6 姫，0／1 是未登場"
                        "（debut 用 +34），8 是不在地圖上（多半已死），不列。"
                        + (f"養父是槽 {adoptive}（{main[adoptive][0]}）。" if adoptive in known else "")
                        + ("其他劇本的名字：" + "、".join(names) + "。" if names else ""))
        rows.append(row)
    return rows


def house_names(game_dir, lang="JP"):
    """{家 number (person +22, also the 家紋 number): [names]}: the 勢力 names of every PK scenario, keyed by their
    当主's 家, most frequent first"""
    count = {}
    for s in SCENARIOS:
        _, _, data = scenario(game_dir, s, lang)
        people, end = persons_raw(data, lang)
        for name, lord in lords(data, people, end, lang).values():
            c = count.setdefault(_u16(people[lord][3], 22), {})
            c[name] = c.get(name, 0) + 1
    return {h: sorted(c, key=lambda n: (-c[n], len(n))) for h, c in count.items()}


def house_surnames(game_dir, lang="JP"):
    """{家 number: most common 姓 of the persons of that 家} from the main scenario (to name the 家 that never lead a 勢力)"""
    _, _, data = scenario(game_dir, MAIN, lang)
    p, count = _key(data, 0, PERSONS), {}
    for _ in range(PERSONS):
        sei = text(data[p:p + 11], lang)
        q = p + 90
        for _ in range(4):
            q += 4 + 2 * struct.unpack_from("<I", data, q)[0]
        h = _u16(data, q + 22)
        if sei and sei != DUMMY[0][:3]:
            c = count.setdefault(h, {})
            c[sei] = c.get(sei, 0) + 1
        p = q + FIXED
    return {h: max(c, key=c.get) for h, c in count.items()}


def _bios(game_dir):
    """列伝: MSG_PK_JP/bushou_retsuden01-48_0.bin, pair k is slot k (2 leading strings are '' and 'Error')"""
    pairs = []
    for k in range(1, 49):
        ss = _n15a(os.path.join(game_dir, "MSG_PK_JP", f"bushou_retsuden{k:02d}_0.bin"), "cp932")[2:]
        pairs += [(ss[i], ss[i + 1]) for i in range(0, len(ss) - 1, 2)]
    names = [r[0] for r in persons_raw(scenario(game_dir, MAIN, "JP")[2], "JP")[0]]
    out = {}
    for k, (name, body) in enumerate(pairs):
        body = body.replace("\\n", "").replace("\n", "")
        if name == "NoName" or not body or k >= PERSONS or names[k] in DUMMY:
            continue
        out[k] = (name, body)
    return out


def bios(game_dir):
    return {k: [("單段", body)] for k, (_, body) in _bios(game_dir).items()}


def bio_names(game_dir):
    return {k: name for k, (name, _) in _bios(game_dir).items()}


BIO_LANG = "ja"
