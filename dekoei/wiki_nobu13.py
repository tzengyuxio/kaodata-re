"""信長の野望・天道 with PK (nobu13pk-win) for koei-wiki: 本城、支城 and 海域 (koei-places/1). Each sceda??.n13 is one
LWC block (ls11.lwc_decode); its sections start with the u32 pair (section, count): notes/nobu13.md「地理」
「koei-wiki 匯出」."""
import os
import struct

import ls11

SCENARIOS = [f"{k:02d}" for k in range(1, 12)] + [f"{k:02d}" for k in range(21, 32)]
# section 8: 264 names (42 bytes: name 13, reading 29); entry i < 66 is the castle name of 本城 i in that scenario (駿府館
# → 駿府城). Section 9: 568 map nodes: name 11 + reading 21, u32 n + n u16 (list A), u32 m + m x (u16 adjacent node,
# u32 weight 0), u16 本城 (itself for 0-65), u16. Section 10: 6 海域: name 9 + reading 19, u32 n + n u16 nodes, u32 4
# + 4 u32, u16.
NAMES, NODES, SEAS = (8, 264), (9, 568), (10, 6)
CASTLES = 66  # nodes 0-65 are 本城, 66-567 支城
SEA_ID = 1000  # place id of 海域 k is 1000 + k; nodes keep their number 0-567


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
