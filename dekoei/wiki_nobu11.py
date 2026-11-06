"""信長の野望・天下創世 with PK (nobu11pk-win) for koei-wiki: 地方, 國 and 拠点 (koei-places/1). scenario/DBSCEDA??.N11
decode (LWC) to a database of serial-numbered records: +0 of every record is a global u16 serial and references are
serials (0xFFFF none); the table offsets and serial ranges are the same in all 7 scenarios. Fields and evidence:
notes/nobu11.md「地理」「koei-wiki 匯出」."""
import os

from ls11 import lwc_decode

# (first serial, count, record size, offset in the decoded DBSCEDA)
BASES, PROVINCES, REGIONS = (0xB1, 100, 18297, 0xB072), (0xACA, 64, 42, 0x225F70), (0xB0A, 12, 20, 0x2269F0)
ROADS, NAMES = (0xA21, 169, 22, 0x2250EA), (0xFBA, 255, 40, 0x239350)
# 拠点: +2 castle name serial (name table: +2 name 11, +13 reading 27), +15338 / +15339 map x / y, +15342 國 serial.
# 國: +2 name 9, +11 reading 17, +28 neighbours 6 x u16, +40 地方 serial. 地方: +2 name 5, +7 reading 13.
# 街道: +3 kind (0-5), +4 / +13 the two 拠点
SCENARIOS = [(1, 1551), (2, 1560), (3, 1570), (4, 1582), (8, 1584), (9, 1590), (10, 1599)]  # (DBSCEDA number, year)
LEVELS = ("御所", "御坊", "館", "城")  # by the name's ending
PROVINCE_ID, REGION_ID = 1000, 2000  # place id: 拠点 = slot 0-99, 國 = 1000 + 國號, 地方 = 2000 + 地方號
# 國 adjacencies that are one-way in the game data (國號 pairs): 能登 lists 加賀 but 加賀 does not list 能登, and 加賀
# lists 伊勢, which does not list 加賀 (伊勢 is 29, 能登 19: probably a typo in 加賀's list)
ONE_WAY = [(19, 20), (20, 29)]


def _u16(b, o):
    return b[o] | b[o + 1] << 8


def _text(b):
    return b.split(b"\0")[0].decode("cp932")


def _database(game_dir, n):
    with open(os.path.join(game_dir, f"DBSCEDA{n:02d}.N11"), "rb") as f:
        packed = f.read()
    return lwc_decode(packed[packed.index(b"LWC\x1a"):])


def _table(db, spec):
    first, count, size, start = spec
    rows = [db[start + size * k:][:size] for k in range(count)]
    assert all(_u16(r, 0) == first + k for k, r in enumerate(rows))
    return rows


def _castle_names(db):
    names = _table(db, NAMES)
    return [(_text(names[_u16(b, 2) - NAMES[0]][2:13]), _text(names[_u16(b, 2) - NAMES[0]][13:40]))
            for b in _table(db, BASES)]


def places(game_dir, out_dir):
    dbs = {n: _database(game_dir, n) for n, _ in SCENARIOS}
    main = dbs[SCENARIOS[0][0]]
    regions = _table(main, REGIONS)
    provinces = _table(main, PROVINCES)
    bases = _table(main, BASES)
    names = {n: _castle_names(db) for n, db in dbs.items()}
    adjacent = {k: [] for k in range(100)}
    for r in _table(main, ROADS):
        a, b = _u16(r, 4) - BASES[0], _u16(r, 13) - BASES[0]
        adjacent[a].append(b)
        adjacent[b].append(a)
    one_way = {a for pair in ONE_WAY for a in pair}
    rows = []
    for k, r in enumerate(regions):
        rows.append({"id": REGION_ID + k, "name": _text(r[2:7]), "reading": _text(r[7:20]), "level": "地方",
                     "notes": f"地方號 {k}（place id 是地方號＋2000）。"})
    for k, r in enumerate(provinces):
        row = {"id": PROVINCE_ID + k, "name": _text(r[2:11]), "reading": _text(r[11:28]), "level": "國",
               "region": _text(regions[_u16(r, 40) - REGIONS[0]][2:7]),
               "adjacent": [PROVINCE_ID + _u16(r, 28 + 2 * j) - PROVINCES[0] for j in range(6)
                            if _u16(r, 28 + 2 * j) != 0xFFFF],
               "notes": f"國號 {k}（place id 是國號＋1000）。相鄰取國記錄 +28 起的 6 格，7 個劇本相同。"}
        if k in one_way:
            row["notes"] += "遊戲資料的相鄰在能登→加賀、加賀→伊勢是單向的（加賀的表裡寫伊勢、沒寫能登，" \
                            "推測是把能登寫成伊勢），照原樣輸出。"
        rows.append(row)
    for k, b in enumerate(bases):
        name, reading = names[SCENARIOS[0][0]][k]
        province = provinces[_u16(b, 15342) - PROVINCES[0]]
        row = {"id": k, "name": name, "reading": reading, "level": next(s for s in LEVELS if name.endswith(s)),
               "province": _text(province[2:11]), "region": _text(regions[_u16(province, 40) - REGIONS[0]][2:7]),
               "adjacent": adjacent[k], "pos": {"x": b[15338], "y": b[15339], "grid": "square"},
               "uncertain": ["pos"]}
        notes = f"拠点槽 {k}。名稱取劇本 01（1551 年）。相鄰取街道表（169 條，7 個劇本相同），照街道表的順序。" \
                "pos 是拠点 +15338、+15339 的格座標，和街道連線的遠近一致，但沒有和地圖圖檔對過。"
        others = [f"{year} 年 {names[n][k][0]}" for n, year in SCENARIOS[1:] if names[n][k][0] != name]
        if others:
            notes += "其他劇本的名稱：" + "、".join(others) + "。"
        row["notes"] = notes
        rows.append(row)
    return rows
