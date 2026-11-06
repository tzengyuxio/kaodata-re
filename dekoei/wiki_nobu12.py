"""信長の野望・革新 with PK (nobu12pk-win) for koei-wiki: 国、城／港／館 and the 諸勢力 (koei-places/1). Each
sceda??.n12 is one LWC block (ls11.lwc_decode); its sections start with the u32 pair (section, count):
notes/nobu12.md「地理」「koei-wiki 匯出」."""
import os
import struct

import ls11

SCENARIOS = ["01", "02", "03", "04", "05", "10", "11", "12"]
# section 8: 225 拠点 names (42 bytes: name 13, reading 29); slots 0-179 are 城／港／館 (47 empty), 180-224 the 諸勢力
# (国人衆、水軍衆、寺、忍者衆、商人衆). Section 10: 60 国 (30 bytes: name 11, reading 19). Section 11: one record per
# non-empty slot 0-179: name 11 + reading 21, u32 n + n u16 (list A, 🟡 section 9 facilities), u32 m + m u16 adjacent
# slots, u16 国, u16 slot (0xFFFF: not in this scenario), u8, 4 x u32 box x0 y0 x1 y1, u8, then 0-2 blocks of 62 bytes.
NAMES, PROVINCES, CASTLES = (8, 225), (10, 60), (11, 180)
FORCES = 180  # first 諸勢力 slot
PROVINCE_ID = 1000  # place id of 国 k is 1000 + k; 拠点 slots keep their number 0-224
LEVELS = ["御所", "御坊", "城", "港", "館", "国人衆", "水軍衆", "忍者衆", "商人衆", "寺"]  # name endings = level


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
