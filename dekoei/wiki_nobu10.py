"""信長の野望・蒼天録 with PK (nobu10pk-win) for koei-wiki: 地方, 國 and 城 (koei-places/1). The tables are at the same
offsets in all 11 Scenario/SCEDAT??.NBX (plain Shift-JIS); the castle map positions are DATA/GMAP_POS.NBX. Fields and
evidence: notes/nobu10.md「地理」「koei-wiki 匯出」."""
import os
import struct

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
