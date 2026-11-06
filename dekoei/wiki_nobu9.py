"""信長の野望・嵐世記 with PK (nobu9pk-win) for koei-wiki: 国 and 城 (koei-places/1). SCEDA??.NB9 decoded with
koei_games.nobu9_win_data; the tables are typed records (u32 1, u16 id, u16 type, u32) followed by the name:
notes/nobu9.md「地理」「koei-wiki 匯出」."""
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
