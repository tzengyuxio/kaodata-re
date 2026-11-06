"""信長の野望・天道 with PK (nobu13pk-win) for koei-wiki: persons (koei-persons/1), 本城、支城 and 海域
(koei-places/1), and 列伝. Each sceda??.n13 is one LWC block (ls11.lwc_decode); its sections start with the u32 pair
(section, count). The 列伝 are msg/Bfile01-27.n13 (N13F, as N12F; hard-linked from the Steam install):
notes/nobu13.md「人物欄位」「地理」「列伝」「koei-wiki 匯出」."""
import os
import struct

import koei_games
import ls11
from wiki_nobu12 import ORIGINS, faction_lords, msg_entries

SCENARIOS = [f"{k:02d}" for k in range(1, 12)] + [f"{k:02d}" for k in range(21, 32)]
# section 8: 264 names (42 bytes: name 13, reading 29); entry i < 66 is the castle name of 本城 i in that scenario (駿府館
# → 駿府城). Section 9: 568 map nodes: name 11 + reading 21, u32 n + n u16 (list A), u32 m + m x (u16 adjacent node,
# u32 weight 0), u16 本城 (itself for 0-65), u16. Section 10: 6 海域: name 9 + reading 19, u32 n + n u16 nodes, u32 4
# + 4 u32, u16.
NAMES, NODES, SEAS = (8, 264), (9, 568), (10, 6)
CASTLES = 66  # nodes 0-65 are 本城, 66-567 支城
SEA_ID = 1000  # place id of 海域 k is 1000 + k; nodes keep their number 0-567
YEAR = 0x22E  # scenario year: u16 of the file header
MAIN, FIRST = "11", "01"  # kaodata names: scenario 11, but slots 1190 and 1191 take scenario 1's
FIRST_NAMES = {1190, 1191}
OFFICES, FACTIONS = (15, 250), (0x15, 0x42)  # 官位 250 x 50 bytes (name 15 at +0); 勢力 66
BIO_LANG = "ja"


def _data(game_dir, s):
    with open(os.path.join(game_dir, f"sceda{s}.n13"), "rb") as f:
        p = f.read()
    return ls11.lwc_decode(p[p.index(b"LWC\x1a"):])


def _text(data, o, n):
    return data[o:o + n].split(b"\0")[0].decode("cp932")


def _section(data, key):
    return data.index(struct.pack("<2I", *key)) + 8


def _scenario(data):
    """(castle names of 本城 0-65, [(name, reading, [adjacent], 本城)] of the nodes)"""
    base = _section(data, NAMES)
    castles = [(_text(data, base + 42 * i, 13), _text(data, base + 42 * i + 13, 29)) for i in range(CASTLES)]
    p, nodes = _section(data, NODES), []
    for _ in range(NODES[1]):
        name, reading = _text(data, p, 11), _text(data, p + 11, 21)
        q = p + 32
        q += 4 + 2 * struct.unpack_from("<I", data, q)[0]
        m = struct.unpack_from("<I", data, q)[0]
        adjacent = [struct.unpack_from("<H", data, q + 4 + 6 * j)[0] for j in range(m)]
        q += 4 + 6 * m
        nodes.append((name, reading, adjacent, struct.unpack_from("<H", data, q)[0]))
        p = q + 4
    return castles, nodes


def _seas(data):
    p, out = _section(data, SEAS), []
    for _ in range(SEAS[1]):
        name, reading = _text(data, p, 9), _text(data, p + 9, 19)
        n = struct.unpack_from("<I", data, p + 28)[0]
        nodes = list(struct.unpack_from(f"<{n}H", data, p + 32))
        p += 32 + 2 * n
        p += 4 + 4 * struct.unpack_from("<I", data, p)[0] + 2
        out.append((name, reading, nodes))
    return out


def places(game_dir, out_dir):
    datas = [_data(game_dir, s) for s in SCENARIOS]
    scenarios = [_scenario(d) for d in datas]
    castles, nodes = scenarios[0]
    rows = []
    for i, (node, reading, adjacent, parent) in enumerate(nodes):
        name, read = castles[i] if i < CASTLES else (node, reading)
        row = {"id": i, "name": name, "reading": read, "level": "本城" if i < CASTLES else "支城"}
        if i >= CASTLES:
            row["parentCity"] = parent
        row["adjacent"] = adjacent
        row["uncertain"] = ["level"]
        others = {}
        for s, (c, n) in zip(SCENARIOS[1:], scenarios[1:]):
            other = c[i][0] if i < CASTLES else n[i][0]
            if other != name:
                others.setdefault(other, []).append(s)
        if i < CASTLES:
            notes = f"節點號 {i}（人物所在拠点用的號碼）。名稱是段 8 的城名，取劇本 01（1546 年）；地圖節點的地名是「{node}」。"
        else:
            notes = f"節點號 {i}。所屬本城取段 9。"
        notes += "「本城」「支城」是這邊的分類，遊戲畫面上的稱呼沒對過。國、大地圖座標沒找到。"
        if others:
            notes += "其他劇本的名稱：" + "、".join(f"{m}（劇本 {'、'.join(ss)}）" for m, ss in others.items()) + "。"
        row["notes"] = notes
        rows.append(row)
    for k, (name, reading, linked) in enumerate(_seas(datas[0])):
        rows.append({"id": SEA_ID + k, "name": name, "reading": reading, "level": "海域",
                     "notes": f"海域號 {k}（place id 是海域號＋1000）。段 10 記錄連到的節點："
                              + "、".join(f"{nodes[n][0]}（{n}）" for n in linked)
                              + "；節點那邊沒有反向的記錄，所以沒放進 adjacent。"})
    return rows


def _officers(slots):
    """the kaodata characters (as build_nobu13pk_win): named slots 0-1360 and 2290-2305 with a face (code 0 is 織田信長's,
    slot 338)"""
    return [k for k in [*range(0, 1361), *range(2290, 2306)]
            if slots[k][0] and (struct.unpack_from("<H", slots[k][2], slots[k][3] + 68)[0] or k == 338)]


def _lists(data, q_end, name_at):
    p, lists = name_at + 213, []
    for _ in range(4):
        n, = struct.unpack_from("<I", data, p)
        lists.append(list(struct.unpack_from(f"<{n}H", data, p + 4)))
        p += 4 + 2 * n
    assert p == q_end
    return lists


def _slots(game_dir, s):
    """[(name, reading, lists, tail)] of the 2600 slots of one scenario"""
    raw = koei_games.nobu13_win_slots(os.path.join(game_dir, f"sceda{s}.n13"))
    out, data = [], raw[0][2]
    name_at = data.index(struct.pack("<2I", 0x14, koei_games.NOBU13_WIN_SLOTS)) + 8
    for name, reading, _, q in raw:
        out.append((name, reading, _lists(data, q, name_at), data[q:q + 137]))
        name_at = q + 137
    return out


def _u16(t, o):
    return struct.unpack_from("<H", t, o)[0]


def _u32(t, o):
    return struct.unpack_from("<I", t, o)[0]


def _year(game_dir, s):
    with open(os.path.join(game_dir, f"sceda{s}.n13"), "rb") as f:
        return struct.unpack_from("<H", f.read(YEAR + 2), YEAR)[0]


def _names(game_dir):
    main, first = koei_games.load_nobu13_win_persons(os.path.join(game_dir, f"sceda{MAIN}.n13")), \
        koei_games.load_nobu13_win_persons(os.path.join(game_dir, f"sceda{FIRST}.n13"))
    return {k: (first if k in FIRST_NAMES else main)[k][:2] for k in range(len(main))}


def _bios(game_dir):
    """{slot: (name, text)}: the 1328 entries of msg/Bfile01-27.n13 are the officers below 1361 in order; one name
    field also holds the reading and the years (「春日元忠 ｶｽｶﾞﾓﾄﾀﾀﾞ ????～1608」), cut at the space"""
    entries = msg_entries([os.path.join(game_dir, "msg", f"Bfile{k:02d}.n13") for k in range(1, 28)])
    slots = koei_games.nobu13_win_slots(os.path.join(game_dir, f"sceda{MAIN}.n13"))
    officers = [k for k in _officers(slots) if k < 1361]
    assert len(officers) == len(entries)
    return {k: (name.split(" ")[0], text) for k, (name, text) in zip(officers, entries)}


def bios(game_dir):
    return {k: [("單段", text)] for k, (_, text) in _bios(game_dir).items()}


def bio_names(game_dir):
    names = _names(game_dir)
    return {k: names[k][0] for k in _bios(game_dir)}


def persons(game_dir):
    recs = {s: _slots(game_dir, s) for s in SCENARIOS}
    datas = {s: _data(game_dir, s) for s in SCENARIOS}
    years = {s: _year(game_dir, s) for s in SCENARIOS}
    lords = {s: faction_lords(datas[s], FACTIONS, lambda v, c, r=recs[s]: v < len(r) and _u16(r[v][3], 12) == c
                              and _u32(r[v][3], 48) == 7) for s in SCENARIOS}
    names = _names(game_dir)
    officers = _officers(koei_games.nobu13_win_slots(os.path.join(game_dir, f"sceda{MAIN}.n13")))
    people = set(officers)
    main = recs[MAIN]
    base = _section(datas[MAIN], OFFICES)
    offices = [_text(datas[MAIN], base + 50 * i, 15) for i in range(OFFICES[1])]
    bio = _bios(game_dir)

    def label(v):
        return f"{names[v][0]}（槽 {v}）" if v < len(names) and names[v][0] else f"槽 {v}"

    fathers = {i: _u16(main[i][3], 0) for i in officers}
    rows = []
    for i in officers:
        lists, t = main[i][2], main[i][3]
        row = {"id": i, "name": names[i][0], "reading": names[i][1], "born": _u32(t, 76), "died": _u32(t, 84),
               "stats": {"統率": _u32(t, 96), "武勇": _u32(t, 100), "知略": _u32(t, 104), "政治": _u32(t, 108)},
               "hidden": {"相性": _u32(t, 72), "義理": _u32(t, 116)}}
        notes = [f"名字取劇本 {'1' if i in FIRST_NAMES else '11'}（同 kaodata），其他欄位取劇本 11；scenarios 是 22 個劇本。"
                 "欄位都是從資料推的，沒有讀程式。"]
        if i in bio and bio[i][0] != row["name"]:
            notes.append(f"列伝寫「{bio[i][0]}」。")
        notes.append(f"元服年 {_u32(t, 80)}。")
        for k, key in ((0, "親愛武将"), (1, "嫌悪武将")):
            v = [names[x][0] for x in lists[k] if x != 0xFFFF]
            if v:
                row["hidden"][key] = v
        row["game"] = {"出自": ORIGINS[_u32(t, 60)]}
        office = [(s, _u16(recs[s][i][3], 8)) for s in SCENARIOS if _u16(recs[s][i][3], 8) != 0xFFFF]
        if office:
            row["game"]["官位"] = offices[office[-1][1]]
            notes.append(f"官位（+8）依劇本變，取有官位的最後一個劇本（{office[-1][0]}）。")
        relations = {}
        father = fathers[i]
        if father in people:
            relations["father"] = [father]
        elif father != 0xFFFF:
            notes.append(f"実父：{label(father)}，不是 kaodata 人物。")
        children = [j for j, v in fathers.items() if v == i]
        if children:
            relations["children"] = children
        siblings = [j for j, v in fathers.items() if j != i and father != 0xFFFF and v == father]
        if siblings:
            relations["siblings"] = siblings
        spouses = list(dict.fromkeys(_u16(recs[s][i][3], 4) for s in SCENARIOS if _u16(recs[s][i][3], 4) != 0xFFFF))
        if [v for v in spouses if v in people]:
            relations["spouse"] = [v for v in spouses if v in people]
        others = [v for v in spouses if v not in people]
        if others:
            notes.append("配偶者（+4）：" + "、".join(label(v) for v in others) + "，不是 kaodata 人物。")
        relations["clan"] = _u16(t, 44)
        row["relations"] = relations
        adoptive = _u16(t, 2)
        if adoptive != 0xFFFF:
            notes.append(f"養父?（+2）：{label(adoptive)}。")
        row["scenarios"] = []
        missing = []
        for s in SCENARIOS:
            ts, y = recs[s][i][3], years[s]
            status, of_age, died = _u32(ts, 48), _u32(ts, 80), _u32(ts, 84)
            sc = {"scenario": int(s), "year": y}
            if status in (7, 2):
                faction = _u16(ts, 12)
                if status == 7 and faction in lords[s]:
                    sc["lord"] = lords[s][faction]
                sc["location"] = _u16(ts, 42)
                sc["status"] = "大名" if sc.get("lord") == i else "家臣" if status == 7 else "浪人"
                if sc["status"] == "家臣":
                    sc["loyalty"] = _u32(ts, 120)
            elif status in (0, 1) or (status == 8 and died >= y and of_age > y):
                sc["status"] = "未登場"
                sc["debut"] = of_age
            else:
                if died > y:
                    missing.append(s)
                continue
            row["scenarios"].append(sc)
        if missing:
            notes.append("劇本 " + "、".join(missing) + " 在世、已元服，但狀態是 8（浪人／未登場），推定是事件才登場，"
                         "登場年不明，沒有列。")
        row["uncertain"] = ["relations.spouse", "hidden.親愛武将", "hidden.嫌悪武将", "scenarios.year", "scenarios.status",
                            "scenarios.debut", "scenarios.loyalty"]
        notes.append("status 依狀態（+48）：7＝家臣（所属勢力的当主是自己時寫大名）、2＝浪人、0／1 與未元服的 8＝未登場，"
                     "debut 用元服年；這些對應是推定。lord 是所属勢力（+12）在段 21 的当主。year 是檔頭 0x22E，"
                     "架空劇本（06、08、11、21–31 的一部分）裡有比 year 晚元服的人在仕官。"
                     "適性（+18 的 5 個值）兵科順序沒對，沒有給。")
        if i not in bio:
            notes.append("沒有列伝。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows
