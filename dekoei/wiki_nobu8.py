"""信長の野望・烈風伝 with PK (nobu8pk-win) for koei-wiki: persons (koei-persons/1), 國 and 城 (koei-places/1) and
列伝. SCEDA00-09.NB8 (koei_games.nobu8_win_data removes the XOR) hold the 10 scenarios; BFILEMSG.NB8 the 列伝. The
fields come from the data only (no code read): notes/nobu8.md「人物欄位（全部）」「地理」「koei-wiki 匯出」."""
import os
import struct

import koei_games
import ls11
from wiki_nobu7 import _bio_index, biographies

PERSONS, COUNT, SIZE = koei_games.NOBU8_WIN_OFFICERS
PEOPLE = 900  # 0-899 are the kaodata characters; 900-917 the generic 姫武将 / 一向一揆 slots and dummies
PROVINCES, CASTLES, MAP = 0x40738, 0x40e38, 0x48658  # 64 x 0x1C, 320 x 0x5A, 170 x 200 cells of 10 bytes
MAP_W, MAP_H = 170, 200
PROVINCE_ID = 1000  # place id of 國 p is 1000 + p; 城 n keeps its number 0-319
# SCEDA0k.NB8 is scenario k + 1. The years are the Nobunaga8WPK.exe strings「1546年3月の勢力より開始」… (VA
# 0x868938-0x868a14, listed backwards); the order is checked by the names (木下 → 羽柴 → 豊臣秀吉, 松平元康 →
# 徳川家康) and 武田信玄 having no 居城 from 1577 on
YEARS = [1546, 1560, 1570, 1582, 1551, 1577, 1583, 1584, 1586, 1589]
MAIN = 9  # the latest names, as kaodata
ARMS = ["足軽", "騎馬", "鉄砲", "水軍"]
GRADES = "EDCBAS"
JOBS = ["忍者", "茶人", "剣豪", "僧侶"]  # +179 bits 0-3
TACTICS = ["三段", "騎突", "騎鉄", "焙烙"]  # +187 bits 0-3
BIO_LANG = "ja"


def _scenarios(game_dir):
    return [koei_games.nobu8_win_data(os.path.join(game_dir, f"SCEDA{k:02d}.NB8")) for k in range(10)]


def _name(data, k):
    o = PERSONS + SIZE * k
    return (data[o:o + 10].split(b"\0")[0] + data[o + 10:o + 20].split(b"\0")[0]).decode("cp932")


def _rec(data, k):
    return data[PERSONS + SIZE * k:][:SIZE]


def _u16(r, o):
    return struct.unpack_from("<H", r, o)[0]


def _ids(data):
    """{officer id: record index}"""
    return {_u16(_rec(data, k), 166): k for k in range(COUNT)}


def _bios(game_dir):
    with open(os.path.join(game_dir, "BFILEMSG.NB8"), "rb") as f:
        entries = biographies(ls11.ls11_decode_parts(f.read()), "cp932")
    names, born = {}, {}
    for data in _scenarios(game_dir):
        for i, k in _ids(data).items():
            if i < PEOPLE:
                names.setdefault(i, set()).add(_name(data, k))
                born[i] = _rec(data, k)[207] + 1450
    index, unmatched = _bio_index(entries, names, born)
    return entries, index, unmatched


def bios(game_dir):
    entries, index, _ = _bios(game_dir)
    return {i: [("單段", entries[p][4])] for i, p in index.items()}


def bio_names(game_dir):
    data = _scenarios(game_dir)[MAIN]
    return {i: _name(data, k) for i, k in _ids(data).items() if i < PEOPLE}


def persons(game_dir):
    scenarios = _scenarios(game_dir)
    main = scenarios[MAIN]
    all_ids = [_ids(data) for data in scenarios]
    ids = all_ids[MAIN]
    entries, index, _ = _bios(game_dir)

    def person(v):
        return v if v < PEOPLE else None

    fathers = {i: _u16(_rec(main, ids[i]), 168) for i in range(PEOPLE)}
    rows = []
    for i in range(PEOPLE):
        r = _rec(main, ids[i])
        row = {"id": i, "name": _name(main, ids[i])}
        notes = ["數值取自劇本 10（SCEDA09，1589）；scenarios 是 10 個劇本，有居城的才列。"
                 "這一代的欄位都是從資料推的，沒有讀程式。"]
        bio = entries[index[i]] if i in index else None
        if bio and bio[1]:
            row["reading"] = bio[1]
        row["born"] = r[207] + 1450
        if bio and bio[3]:
            row["died"] = bio[3]
            notes.append("歿年取自列伝的標頭（記錄裡沒有歿年）。")
        row["stats"] = {"政治": r[218], "戦闘": r[219], "采配": r[221], "知謀": r[220]}
        row["more"] = {"勲功": _u16(r, 176)}
        row["hidden"] = {"相性": r[209], "義理": r[223]}
        row["aptitude"] = {a: GRADES[(r[184 + j // 2] >> (4 * (j % 2))) & 15] for j, a in enumerate(ARMS)}
        tactics = [t for b, t in enumerate(TACTICS) if r[187] >> b & 1]
        if tactics:
            row["skills"] = {"戦法": tactics}
        relations = {}
        father = person(_u16(r, 168))
        if father is not None:
            relations["father"] = [father]
        children = [j for j, f in fathers.items() if person(f) == i]
        if children:
            relations["children"] = children
        siblings = [j for j, f in fathers.items() if j != i and f != 0xFFFF and f == _u16(r, 168)]
        if siblings:
            relations["siblings"] = siblings
        if r[222] != 0xFF:
            relations["clan"] = r[222]
        if relations:
            row["relations"] = relations
        adoptive = person(_u16(r, 170))
        if adoptive is not None:
            notes.append(f"養父（+170）：{_name(main, ids[adoptive])}（id {adoptive}）。")
        jobs = [t for b, t in enumerate(JOBS) if r[179] >> b & 1]
        if jobs:
            row["game"] = {"職業": jobs}
        row["scenarios"] = []
        for s, data in enumerate(scenarios):
            rs = _rec(data, all_ids[s][i])
            castle = _u16(rs, 232)
            if castle == 0xFFFF:
                continue
            sc = {"scenario": s + 1, "year": YEARS[s], "location": castle}
            lord = _u16(rs, 236)
            if lord != 0xFFFF and person(lord) is not None:
                sc["lord"] = lord
            sc["loyalty"] = rs[224]
            row["scenarios"].append(sc)
        row["uncertain"] = ["hidden.相性", "hidden.義理", "relations.clan", "scenarios.lord", "scenarios.loyalty",
                            "scenarios.year"]
        notes.append("主君（+236）0xFFFF 是大名或浪人，沒有填；家康、景勝的 +236 指向父親，原因未解。")
        if bio is None:
            notes.append("沒有列伝。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def _castles(data):
    """{城號: (name, 國號, (x, y) of the centre cell)} of one scenario: the centre is the cell whose byte 6 is the
    國 number (本城 5p) or 0x80 + n (支城 5p + 1 + n), byte 5 being the 國."""
    centres = {}
    for c in range(MAP_W * MAP_H):
        p, b = data[MAP + 10 * c + 5], data[MAP + 10 * c + 6]
        if b < 0x40:
            centres[5 * b] = (c % MAP_W, c // MAP_W)
        elif 0x80 <= b < 0x88:
            centres[5 * p + 1 + b - 0x80] = (c % MAP_W, c // MAP_W)
    out = {}
    for n in range(320):
        name = data[CASTLES + 0x5A * n:][:14].split(b"\0")[0].decode("cp932").strip()
        if name:
            out[n] = (name, n // 5, centres[n])
    return out


def places(game_dir, out_dir):
    scenarios = _scenarios(game_dir)
    main = scenarios[MAIN]
    names = [main[PROVINCES + 0x1C * p:][:10].split(b"\0")[0].decode("cp932") for p in range(64)]
    rows = []
    for p in range(64):
        r = main[PROVINCES + 0x1C * p:][:0x1C]
        rows.append({"id": PROVINCE_ID + p, "name": names[p], "level": "國",
                     "adjacent": [PROVINCE_ID + n for n in r[0x12:0x18] if n != 0xFF],
                     "notes": f"國號 {p}（place id 是國號＋1000）。相鄰取國記錄 +0x12–+0x17。"})
    castles = [_castles(data) for data in scenarios]
    for n in sorted({n for c in castles for n in c}):
        s = max(k for k, c in enumerate(castles) if n in c)
        name, p, (x, y) = castles[s][n]
        row = {"id": n, "name": name, "level": "本城" if n % 5 == 0 else "支城", "province": names[p],
               "pos": {"x": x, "y": y, "grid": "square", "w": MAP_W, "h": MAP_H}}
        others = sorted({c[n][0] for c in castles if n in c} - {name})
        present = [k + 1 for k, c in enumerate(castles) if n in c]
        notes = f"城號 {n}（國 {p} 的第 {n % 5 + 1} 格；第 1 格是本城）。名稱與 pos 取有這座城的最後一個劇本（劇本 {s + 1}）；" \
                "pos 是大地圖 170×200 格上的中心格，地圖是等角排列，列有錯位。城與城的相鄰（道路）沒解，沒有給。"
        if len(present) < 10:
            notes += "出現在劇本 " + "、".join(map(str, present)) + "。"
        if others:
            notes += "其他劇本的名稱：" + "、".join(others) + "。"
        row["notes"] = notes
        rows.append(row)
    return rows
