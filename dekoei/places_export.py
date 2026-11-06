"""Places (provinces, cities, passes...) of 三國志 I-14 and 水滸傳 for koei-wiki: one JSONL line per place in
<out>/<dataset>.jsonl and the battle maps as PNG in <out>/<dataset>/, in the koei-places/1 format
(koei-wiki docs/places-format.mkdn). Where each table comes from and how sure it is: notes/san-maps.md, and for
水滸傳 notes/koei-games.md「州與戰場地圖」."""
import importlib
import json
import os
import struct
import unicodedata

import click
from PIL import Image

import koei_games
import san1
import san2
import san3
import sango

# A map the attacked place uses whatever kind of battle it is (I-III have one kind of battle)
BATTLE = "戰場"


def _text(b: bytes, fix: dict = None) -> str:
    """Shift-JIS up to the first NUL; fix maps a two-byte gaiji code to its character."""
    b = b.split(b"\0")[0]
    out, i = "", 0
    while i < len(b):
        code = int.from_bytes(b[i:i + 2], "big")
        if fix and code in fix:
            out, i = out + fix[code], i + 2
            continue
        n = 2 if 0x81 <= b[i] <= 0x9F or 0xE0 <= b[i] <= 0xFC else 1
        out, i = out + b[i:i + n].decode("cp932"), i + n
    return out.strip()


def _reading(b: bytes) -> str:
    """Half-width katakana reading as full-width katakana."""
    return unicodedata.normalize("NFKC", _text(b))


def _save(maps, out_dir, names):
    os.makedirs(out_dir, exist_ok=True)
    for im, name in zip(maps, names):
        im.save(os.path.join(out_dir, name))


##############################################################################
# 三國志 (I) PC-98: 58 國 with numbers only. SAVEDATA slot k holds the 國 records (48 bytes, the neighbour list
# 9 bytes zero-ended at 404 + 22904 k + 48 (n - 1)); all 4 slots and the FC 國表 (ROM 0x3B211) agree. The 州 of
# each 國 is not found in the PC-98 files: it is the FC table's (15 州, 國 numbered in 州 order), and the
# screens battle-04 (冀州) and battle-10 (徐州) agree.
SAN1_PC98_STATES, SAN1_PC98_STATE_SIZE = 404, 48
SAN1_PROVINCES = [("幽州", 1), ("冀州", 4), ("兗州", 6), ("青州", 8), ("徐州", 10), ("予州", 12), ("代州", 14),
                  ("幷州", 16), ("司隷", 19), ("雍州", 21), ("涼州", 24), ("揚州", 28), ("荊州", 37), ("益州", 45),
                  ("交州", 55)]  # (name, first 國)
SAN1_CAPTURES = [("battle-04.png", 4), ("battle-10.png", 10)]


def places_san1_pc98(game_dir, out_dir):
    with open(os.path.join(game_dir, "SAVEDATA"), "rb") as f:
        data = f.read()
    shots = os.path.join(game_dir, "..", "..", "captures", "screenshots", "san1-pc98")
    cells = san1.load_san1_pc98_battle_maps(os.path.join(game_dir, "SAVEDATA"))
    tiles = san1.battle_tiles([(san1.np2kai_capture_screen(os.path.join(shots, f)), cells[n - 1])
                               for f, n in SAN1_CAPTURES])
    _save([san1.render_battle_map(c, tiles) for c in cells], out_dir, [f"{n:02d}.png" for n in range(1, 59)])
    rows = []
    for n in range(1, 59):
        o = SAN1_PC98_STATES + SAN1_PC98_STATE_SIZE * (n - 1)
        province = [p for p, first in SAN1_PROVINCES if first <= n][-1]
        rows.append({"id": n, "name": None, "level": "國", "province": province,
                     "adjacent": [b for b in data[o:o + 9] if b],
                     "battlemaps": [{"file": f"{n:02d}.png", "role": BATTLE}],
                     "uncertain": ["province"],
                     "notes": "國只有號碼。所屬州取自 FC 版的國表（PC-98 的檔裡沒找到），州名寫法也照 FC；"
                              "4 國冀州、10 國徐州和 PC-98 畫面相同。戰場圖的地形圖塊是從 PC-98 截圖切的。"})
    return rows


##############################################################################
# 三國志II PC-98: 41 州 with numbers only; adjacency from san2.SAN2_PROVINCE_HEX (checked against the
# HEXDATA.DAT deployment layer). The names are borrowed from 三国志ツクール: its sample scenario (LINKDATA item
# 151) has 41 州 records in the same order with the same adjacency (notes/santsukuru.md「範例劇本」).
SANTSUKURU_ITEM, SANTSUKURU_PROVINCES = 151, 0x125FD  # first 州 record (0x40 bytes, name at +0x30)
SANTSUKURU_GAIJI = {0xF06D: "鄴", 0xF060: "邳", 0xF070: "鄱"}  # read off the place names


def santsukuru_provinces(game_dir):
    """[(name, x, y, [neighbour 0-based])] of the 41 州 of the 三国志ツクール sample scenario."""
    with open(os.path.join(game_dir, "LINKDATA.IDX"), "rb") as f:
        f.seek(32 * SANTSUKURU_ITEM)
        offset, _, stored, _ = struct.unpack("<4Q", f.read(32))
    with open(os.path.join(game_dir, "LINKDATA0.BIN"), "rb") as f:
        f.seek(offset)
        data = f.read(stored)
    out = []
    for k in range(41):
        r = data[SANTSUKURU_PROVINCES + 0x40 * k:][:0x40]
        assert r[0x29] == k
        x, y = struct.unpack_from("<HH", r, 0x1D)
        out.append((_text(r[0x30:0x40], SANTSUKURU_GAIJI), x, y, [b for b in r[0x23:0x29] if b != 0xFF]))
    return out


def places_san2_pc98(game_dir, out_dir):
    maps, _ = san2.render_san2_battle_maps(os.path.join(game_dir, "HEXDATA.DAT"))
    _save(maps, out_dir, [f"{n:02d}.png" for n in range(1, 42)])
    where = {qr: k + 1 for k, qr in enumerate(san2.SAN2_PROVINCE_HEX)}
    borrowed = santsukuru_provinces(os.path.join(game_dir, "..", "santsukuru-win"))
    rows = []
    for k, (q, r) in enumerate(san2.SAN2_PROVINCE_HEX):
        adjacent = sorted(where[q + dq, r + dr] for dq, dr in san2.HEX_DIRS if (q + dq, r + dr) in where)
        name, _, _, tsukuru = borrowed[k]
        assert sorted(n + 1 for n in tsukuru) == adjacent, k + 1
        rows.append({"id": k + 1, "name": None, "nameBorrowed": {"name": name, "from": "santsukuru-win"},
                     "level": "州", "adjacent": adjacent,
                     "battlemaps": [{"file": f"{k + 1:02d}.png", "role": BATTLE}],
                     "pos": {"x": q, "y": r, "grid": "hex-axial"},
                     "uncertain": ["battlemaps"],
                     "notes": "州只有號碼，借用的名字來自三国志ツクール範例劇本（41 州的順序與相鄰關係和本作相同）。"
                              "pos 是把 41 州排成六角格的軸座標（由相鄰關係推出）。"
                              "從哪個鄰州進攻只換布陣位置、不換地圖，沒在遊戲裡確認。"})
    return rows


##############################################################################
# 三國志III PC-98: location ids 0-45 are 州, 46-67 據點 (MAIN.EXE image 0x5D06 / 0x5D11). Names in SNDATA1.CIM:
# 州 records from 0x163 (0x4A bytes, name 7 + reading), 據點 from 0xE7C (25 bytes). Hex grid 15 x 16 at
# MAIN.EXE 0x53431 (location id, 0x80 road, 0xFF none), the step table at 0x53418 (0x70C4 / 0x7261). The battle
# map is HEXDATA.DAT map (location id) (0x2EF8B / 0x3847C).
SAN3_GAIJI = {6: "鄴", 16: "下邳", 19: "譙", 60: "涪城"}  # names with gaiji, by location id


def san3_places(game_dir):
    with open(os.path.join(game_dir, "SNDATA1.CIM"), "rb") as f:
        sn = f.read()
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        exe = f.read()
    grid, dy = exe[0x53431:0x53431 + 240], exe[0x53418:0x53418 + 12]
    recs = [sn[0x163 + 0x4A * i:][:16] for i in range(46)] + [sn[0xE7C + 25 * k:][:16] for k in range(22)]
    names = [SAN3_GAIJI.get(i) or _text(r[:7]) for i, r in enumerate(recs)]
    readings = [_reading(r[7:16]) for r in recs]
    pos = {grid[i]: (i % 15, i // 15) for i in range(240) if grid[i] < 68}

    def adjacent(v):
        x, y = pos[v]
        out = []
        for k in range(6):
            cx, cy, w = x, y, None
            while True:
                nx, ny = cx + k % 3 - 1, cy + dy[6 * (cx & 1) + k] - 1
                if not (0 <= nx < 15 and 0 <= ny < 16):
                    w = None
                    break
                cx, cy, w = nx, ny, grid[ny * 15 + nx]
                if w != 0x80:
                    break
            if w is not None and w < 68:
                out.append(w)
        return out

    return names, readings, pos, adjacent


def places_san3_pc98(game_dir, out_dir):
    _save(san3.render_san3_battle_maps(game_dir), out_dir, [f"{n:02d}.png" for n in range(1, 69)])
    names, readings, pos, adjacent = san3_places(game_dir)
    rows = []
    for v in range(68):
        row = {"id": v, "name": names[v], "reading": readings[v], "level": "州" if v < 46 else "據點",
               "adjacent": adjacent(v), "battlemaps": [{"file": f"{v + 1:02d}.png", "role": BATTLE}],
               "pos": {"x": pos[v][0], "y": pos[v][1], "grid": "hex-offset", "w": 15, "h": 16}}
        if v >= 46:
            row["uncertain"] = ["level"]
            row["notes"] = ("「據點」是這邊的分類，遊戲裡的稱呼沒查到；46–67 號包括 5 個関、渡口、山與古戰場。"
                            "遊戲的程式用同一套地點號處理州與據點。")
        rows.append(row)
    for row in rows:
        row["notes"] = (row.get("notes", "") + "相鄰是大地圖六角格上沿道路走得到的地點（遊戲每次實際走哪幾個方向沒查）。"
                        "pos 是 15 × 16 的六角格，奇數欄錯半格。")
    return rows


##############################################################################
# 三國志IV PC-98 with PK: 43 cities at MAIN.EXE 0x4615D (base game 0x3EA7D, byte-identical; 29 bytes: name +3,
# reading +8, neighbours +15 0-based FF-ended). Field maps: the table at 0x3FC28 (base 0x3855A, byte-identical to
# the SFC table) gives map table[6 * defender + k] for the k-th neighbour attacking; siege map 46 + city.
SAN4PK_PC98_CITIES, SAN4PK_PC98_FIELD = 0x4615D, 0x3FC28
SAN4_GAIJI = {6: "鄴", 16: "下邳", 19: "譙"}


def places_san4pk_pc98(game_dir, out_dir):
    base = os.path.join(game_dir, "..", "san4-pc98", "MAIN.EXE")  # the palette offsets are the base game's
    _save(sango.render_san4_battle_maps(game_dir, palette_exe=base), out_dir, [f"{n:02d}.png" for n in range(1, 89)])
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        exe = f.read()
    recs = [exe[SAN4PK_PC98_CITIES + 29 * i:][:29] for i in range(43)]
    field = exe[SAN4PK_PC98_FIELD:][:43 * 6]
    adj = [[b for b in r[15:29] if b != 0xFF] for r in recs]
    users = {}
    for i in range(43):
        for k in range(len(adj[i])):
            users.setdefault(field[6 * i + k], set()).add(i)
    rows = []
    for i, r in enumerate(recs):
        maps = [{"file": f"{46 + i:02d}.png", "role": "攻城"}]
        for k, a in enumerate(adj[i]):
            m = {"file": f"{field[6 * i + k] + 1:02d}.png", "role": "野戰", "from": a}
            shared = sorted(users[field[6 * i + k]] - {i})
            if shared:
                m["sharedWith"] = shared
            maps.append(m)
        rows.append({"id": i, "name": SAN4_GAIJI.get(i) or _text(r[3:8]), "reading": _reading(r[8:15]),
                     "level": "都市", "adjacent": adj[i], "battlemaps": maps,
                     "notes": "讀的是 PC-98 PK 版；都市表、野戰表和本體 byte 相同。野戰圖依攻方從哪個鄰城來而定"
                              "（from），攻城圖是都市自己的。戰場圖的色盤種類與季節是遊戲執行時決定的，這裡用種類 0、季節 0。"})
    return rows


def _gaiji(s: str, table: dict) -> str:
    """Replace the private-use characters (gaiji) of a decoded string through table {code point: char}."""
    return "".join(table.get(ord(c), c) for c in s)


##############################################################################
# 三國志X PK (Steam 628060): the place table at San10WPK.exe 0x480C90 (.rdata, not encrypted by SteamStub; file
# offset = VA - 0x400000), 200 x 12 bytes: name VA, battle file VA, u32 kind (1 城門戦, 2 市街戦, 0 other). 0-49
# cities, 50-118 拠点, 119-143 市街戦 maps, 144-168 平地街道, 169-193 山地街道, 194-199 水路 maps (VA 0x602D00,
# 0x5F86B2). fieldmap.s10: hex cells (rows alternate 100 / 99 cells, x doubled) of 5 bytes: b0 city (50 none), b1
# road kind, b2 place (0-118, one cell each), b3 field map, b4 region bit. ScePK000.s10 0x5804: 69 x 7 bytes of
# 拠点 structures, +1 kind (3 関; all 18 scenarios have the same 8 関).
SAN10_PLACES, SAN10_PLACE_KINDS = 0x480C90, 200
SAN10_EXTRA_GAIJI = {0xE018: "譙", 0xE06B: "祁", 0xE06C: "嶲", 0xE02D: "鄴", 0xE020: "邳", 0xE022: "淄", 0xE024: "并",
                     0xE00B: "兗"}  # place-name gaiji, read off S10Gaiji.tte
SAN10_REGIONS = {62: "河北", 61: "中原", 59: "西北", 55: "巴蜀", 47: "楚", 31: "呉越"}  # b4 -> name (EXE 0x4F4030)
SAN10_MAP_LEVELS = [(119, "市街戦"), (144, "平地街道"), (169, "山地街道"), (194, "水路")]  # first entry, level


def san10_fieldmap(path):
    """{place: (x, row, city, region bits)} of fieldmap.s10 (VA 0x7BFD90) and the map size (2 W, 2 H - 1)."""
    with open(path, "rb") as f:
        d = f.read()
    n = d[0]
    assert d[1:1 + n] == b"San10MainMapEditor"
    p = 1 + n + 4
    w, h = d[p], d[p + 1]
    p += 1 + 0x41
    cells = {}
    for row in range(2 * h - 1):
        for x in range(row & 1, 2 * w - (row & 1), 2):
            b = d[p:p + 5]
            p += 5
            if b[2] != 0xFF:
                cells[b[2]] = (x, row, b[0], b[4])
    return cells, (2 * w, 2 * h - 1)


def places_san10pk_win(game_dir, out_dir):
    with open(os.path.join(game_dir, "San10WPK.exe"), "rb") as f:
        exe = f.read()
    gaiji = {**sango.SAN10_GAIJI, **SAN10_EXTRA_GAIJI}

    def s(va):
        o = va - 0x400000
        return _gaiji(exe[o:exe.index(b"\0", o)].decode("cp932"), gaiji)

    table = [struct.unpack_from("<3I", exe, SAN10_PLACES + 12 * i) for i in range(SAN10_PLACE_KINDS)]
    cells, (w, h) = san10_fieldmap(os.path.join(game_dir, "fieldmap.s10"))
    with open(os.path.join(game_dir, "ScePK000.s10"), "rb") as f:
        sce = f.read()
    gates = {50 + i for i in range(69) if sce[0x5804 + 7 * i + 1] == 3}
    rows = []
    for i, (name, _, _) in enumerate(table):
        row = {"id": i, "name": s(name)}
        if i < 119:
            x, y, city, bits = cells[i]
            row["level"] = "都市" if i < 50 else "関" if i in gates else "拠点"
            if i >= 50 and city < 50:
                row["parentCity"] = city
            row["region"] = SAN10_REGIONS[bits]
            row["pos"] = {"x": x, "y": y, "grid": "hex-doubled", "w": w, "h": h}
            row["uncertain"] = ["region"] + (["parentCity"] if "parentCity" in row else [])
            notes = ["地方是大地圖格子的地方位元，位元和地方名的對應照地理推定。"]
            if i >= 50:
                notes.append("所屬都市是大地圖上這個拠点那一格的所屬都市（沒有靜態表）。")
            if i in gates:
                notes.append("遊戲裡是拠点，工作物是関（18 個劇本都有）。")
            notes.append("沒有相鄰表，部隊在大地圖的六角格上沿街道走。pos 是大地圖六角格（列交錯，x 用兩倍寬座標）。"
                         "戰場圖晚點補（城門戰、拠点、市街戰、街道共 200 張）。")
            row["notes"] = "".join(notes)
        else:
            row["level"] = [lv for first, lv in SAN10_MAP_LEVELS if first <= i][-1]
            row["uncertain"] = ["level"]
            row["notes"] = ("不是地名，是地點表裡的戰場圖項目：市街戦是都市城門突破後的戰場，平地街道、山地街道、"
                            "水路是街道上遭遇時依那一格指定的戰場。level 是這邊照名稱的分類。")
        rows.append(row)
    return rows


##############################################################################
# 三國志11 PK (Steam 628070): media/scenario/Scenario.s11 (cp932): 42 cities from 0x5A (25 bytes: name 5,
# reading 13, +18 州, +19 six neighbour cities FF-padded), then 45 関 / 港 (26 bytes: name 7, reading 19; 42-51
# 関, 52-86 港), 12 州 from 0x906 (0x2C bytes: name 5, +38 地方), 6 地方 from 0xB16 (0x12 bytes). 関 and 港 have
# no city field: parentCity is the city whose territory shares the longest border with theirs on the 200 x 200
# map SHEX0008 (media/san11pkres.bin item 4791, 11 bytes a cell, +1 territory).
SAN11_EXTRA_GAIJI = {0xE02D: "鄴", 0xE020: "邳", 0xE00B: "兗", 0xE02A: "涪", 0xE030: "鄱"}  # from the readings
SAN11_SHEX_ITEM, SAN11_MAP = 4791, 200


def san11_borders(path):
    """{territory: Counter(other territory: border cells)} of SHEX0008."""
    from collections import Counter, defaultdict
    with open(path, "rb") as f:
        f.seek(0x10 + 8 * SAN11_SHEX_ITEM)
        offset, size = struct.unpack("<II", f.read(8))
        f.seek(offset)
        d = f.read(size)
    assert d[:8] == b"SHEX0008"
    n = SAN11_MAP
    terr = d[8 + 1::11][:n * n]
    border = defaultdict(Counter)
    for y in range(n):
        for x in range(n):
            a = terr[y * n + x]
            for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
                if 0 <= x + dx < n and 0 <= y + dy < n:
                    b = terr[(y + dy) * n + x + dx]
                    if a != b:
                        border[a][b] += 1
                        border[b][a] += 1
    return border


def places_san11pk_win(game_dir, out_dir):
    with open(os.path.join(game_dir, "Scenario.s11"), "rb") as f:
        sc = f.read()
    gaiji = {**sango.SAN11_GAIJI, **SAN11_EXTRA_GAIJI}

    def s(b):
        return _gaiji(b.split(b"\0")[0].decode("cp932"), gaiji)

    regions = [s(sc[0xB16 + 0x12 * k:][:5]) for k in range(6)]
    states = [(s(sc[0x906 + 0x2C * k:][:5]), regions[sc[0x906 + 0x2C * k + 38]]) for k in range(12)]
    border = san11_borders(os.path.join(game_dir, "san11pkres.bin"))
    rows = []
    for i in range(42):
        r = sc[0x5A + 25 * i:][:25]
        state, region = states[r[18]]
        rows.append({"id": i, "name": s(r[:5]), "reading": s(r[5:18]), "level": "都市", "province": state,
                     "region": region, "adjacent": [b for b in r[19:25] if b != 0xFF]})
    for k in range(45):
        i = 42 + k
        r = sc[0x474 + 26 * k:][:26]
        city = next(c for c, _ in border[i].most_common() if c < 42)
        rows.append({"id": i, "name": s(r[:7]), "reading": s(r[7:26]), "level": "関" if i < 52 else "港",
                     "parentCity": city, "province": rows[city]["province"], "region": rows[city]["region"],
                     "uncertain": ["parentCity", "province", "region"],
                     "notes": "関、港沒有所屬都市的欄位，parentCity 是大地圖上和它的領地接壤最長的都市（推定），"
                              "州、地方照那個都市。関、港沒有相鄰表。"})
    for row in rows:
        row["notes"] = row.get("notes", "") + "沒有戰場圖，野戰、攻城都在 200 × 200 格的大地圖上打。"
    return rows


##############################################################################
# 三國志14 PK (Steam 872410): 0010_TC/fixdataex.s14 and 0010_JP/fixdataex.s14 (one LWC block, UTF-16LE). 地方
# from 0x8 (20 bytes), 州 from 0x100 (32 bytes, +30 地方), cities from 0x3E8 (52 x 53 bytes; 1-46 cities, 47-51
# 異民族; +52 州). 地區 (the places) from 0x24824, 65 bytes, 1-343: +0 name, +10 reading (JP), +36 city, +37 u16
# seat cell (x = n % 220, y = n / 220), +47 eight u16 neighbour 地區 (0 empty). 地區 have no kind field: the terrain code of
# the seat cell in 0000/MapEx.bin (220 x 220 x 16 bytes after a 4-byte header, +4) tells 15 府, 16 都市, 17 關,
# 18 港 apart.
SAN14_AREAS, SAN14_MAP = 0x24824, 220
SAN14_LEVELS = {15: "府", 16: "都市", 17: "關", 18: "港"}
SAN14_TC_GAIJI = {0xE030: "坂"}  # 長坂 (the JP file has 坂)
# one-way neighbours in the game data itself (TC and JP alike): 羌, added by the PK, lists 陰平, which does not
# list it back
SAN14_ONE_WAY = {(341, 302): "羌（PK 新增）的相鄰有陰平，陰平的相鄰沒有羌，遊戲資料（繁中、日文版都一樣）本身就是單向的。"}


def places_san14pk_win(game_dir, out_dir):
    from ls11 import lwc_decode

    def load(lang):
        with open(os.path.join(game_dir, f"0010_{lang}", "fixdataex.s14"), "rb") as f:
            d = f.read()
        return lwc_decode(d[d.index(b"LWC\x1a"):])

    tc, jp = load("TC"), load("JP")
    with open(os.path.join(game_dir, "0000", "MapEx.bin"), "rb") as f:
        mp = f.read()

    def s(d, o, n):
        return d[o:o + 2 * n].decode("utf-16le").split("\0")[0]

    def names(o, n):
        t, j = _gaiji(s(tc, o, n), SAN14_TC_GAIJI), s(jp, o, n)
        if len(t) == len(j):  # the JP gaiji read off the TC name
            j = "".join(b if 0xE000 <= ord(a) < 0xF900 else a for a, b in zip(j, t))
        return t, j

    regions = [s(tc, 0x8 + 20 * k, 10) for k in range(12)]
    states = [(s(tc, 0x100 + 32 * k, 6), regions[tc[0x100 + 32 * k + 30]]) for k in range(23)]
    city_state = {c: states[tc[0x3E8 + 53 * c + 52]] for c in range(1, 52)}
    areas = []
    for i in range(1, 344):
        o = SAN14_AREAS + 65 * i
        tile = struct.unpack_from("<H", tc, o + 37)[0]
        areas.append((i, *names(o, 5), s(jp, o + 10, 10), tc[o + 36], tile, SAN14_LEVELS[mp[4 + 16 * tile + 4]],
                      [a for a in struct.unpack_from("<8H", tc, o + 47) if a]))
    city_area = {city: i for i, _, _, _, city, _, level, _ in areas if level == "都市"}
    rows = []
    for i, name, name_ja, reading, city, tile, level, adjacent in areas:
        state, region = city_state[city]
        row = {"id": i, "name": name}
        if name_ja != name:
            row["nameJa"] = name_ja
        row.update({"reading": reading, "level": level, "province": state, "region": region})
        if level != "都市":
            row["parentCity"] = city_area[city]
        row.update({"adjacent": adjacent, "pos": {"x": tile % SAN14_MAP, "y": tile // SAN14_MAP, "grid": "square",
                                                  "w": SAN14_MAP, "h": SAN14_MAP}})
        notes = ["地區沒有種類欄位，level 是看治所那一格的地形碼分的（都市、關、港、府四種）。"]
        if city >= 47 and level == "都市":
            notes.append("異民族（遊戲的都市表 47–51 號）。")
        notes.append("州、地方照所屬都市。pos 是治所在 220 × 220 格大地圖上的位置。"
                     "沒有戰場圖，戰鬥在大地圖上打。")
        notes += [n for pair, n in SAN14_ONE_WAY.items() if i in pair]
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


# Place-name gaiji of the Windows games (Shift-JIS F0xx = U+E0xx), read off the readings and the other
# generations' names: 鄴 下邳 譙 涪 并州 兗州 臨淄 鄱陽
PLACE_GAIJI = {0xE02D: "鄴", 0xE020: "邳", 0xE018: "譙", 0xE02A: "涪", 0xE024: "并", 0xE00B: "兗", 0xE022: "淄",
               0xE030: "鄱"}


##############################################################################
# 三國志V PC-98 with PK: 47 cities at MAIN.EXE 0x41C20 (base game 0x3F3A0, byte-identical; 32 bytes: name +0 5,
# reading +5 7, six neighbours +12 1-based FF-padded). HEXMAP.S5 / HEXGRP.S5 are the base game's (byte-identical);
# the battle palette offsets are the base game's MAIN.EXE ones (the PK has the same bytes elsewhere).
SAN5PK_PC98_CITIES = 0x41C20
SAN5_GAIJI = {7: "鄴", 17: "下邳", 20: "譙", 47: "鄱陽"}  # 1-based city numbers


def places_san5pk_pc98(game_dir, out_dir):
    import ls11
    pal = sango.san5_pc98_battle_palette(os.path.join(game_dir, "..", "san5-pc98", "MAIN.EXE"), 0)
    with open(os.path.join(game_dir, "HEXGRP.S5"), "rb") as f:
        tiles = sango.battle_tiles(ls11.ls11_decode_parts(f.read())[0])
    with open(os.path.join(game_dir, "HEXMAP.S5"), "rb") as f:
        maps = ls11.ls11_decode_parts(f.read())[:47]
    _save([sango.render_tile_layers(m, 50, 48, sango.SAN5_BATTLE_BASES, tiles, pal) for m in maps], out_dir,
          [f"{n:02d}.png" for n in range(1, 48)])
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        exe = f.read()
    rows = []
    for n in range(1, 48):
        r = exe[SAN5PK_PC98_CITIES + 32 * (n - 1):][:32]
        rows.append({"id": n, "name": SAN5_GAIJI.get(n) or _text(r[:5]), "reading": _reading(r[5:12]),
                     "level": "都市", "adjacent": [b for b in r[12:18] if b != 0xFF],
                     "battlemaps": [{"file": f"{n:02d}.png", "role": "攻城"}], "uncertain": ["battlemaps"],
                     "notes": "讀的是 PC-98 PK 版；都市表、戰場圖檔和本體 byte 相同。戰場 47 張，第 n 張推定是第 n 個"
                              "都市、打仗用守方都市的圖（照地形看圖判斷，讀取程式沒追）。這一代野戰與攻城在同一張圖上，"
                              "role 填攻城是這邊的分類。戰場色盤用第 0 組（遊戲用哪一組沒追）。"})
    return rows


##############################################################################
# 三國志VI 中文 PK: SNDATA01.S6 (Big5) 51 cities from 0x803A8 (0x68 bytes: name +0, SHIRO number +0x32 u16;
# 45-50 are the 外族) and 117 field places from 0x81994 (0x1E bytes: name +0, SENJOU number +0x18 u16). SAN6.EXE
# file 0x34F808: per city 6 x (i16 neighbour city, i16 field place), compared in order at RVA 0x25ADA9. The maps
# SENJOU0-39.S6 / SHIRO0-38.S6 are 1008 x 720 8-bit BMPs. Place ids here: cities 0-50, field place p is 51 + p
# (its MAPDATA.S6 part number).
SAN6_CITIES, SAN6_PLACES, SAN6_LINKS = 0x803A8, 0x81994, 0x34F808


def _bmp_png(src, out_dir, name):
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    with Image.open(src) as im:
        im.save(os.path.join(out_dir, name))


def places_san6pk_win(game_dir, out_dir):
    with open(os.path.join(game_dir, "SNDATA01.S6"), "rb") as f:
        sn = f.read()
    with open(os.path.join(game_dir, "SAN6.EXE"), "rb") as f:
        exe = f.read()

    def big5(b):
        return b.split(b"\0")[0].decode("big5").strip()

    cities = [(big5(sn[SAN6_CITIES + 0x68 * i:][:12]), struct.unpack_from("<H", sn, SAN6_CITIES + 0x68 * i + 0x32)[0])
              for i in range(51)]
    places = [(big5(sn[SAN6_PLACES + 0x1E * p:][:24]), struct.unpack_from("<H", sn, SAN6_PLACES + 0x1E * p + 0x18)[0])
              for p in range(117)]
    links = [[struct.unpack_from("<hh", exe, SAN6_LINKS + 0x18 * c + 4 * k) for k in range(6)] for c in range(51)]
    links = [[(nb, p) for nb, p in ls if nb >= 0] for ls in links]
    for _, s in cities:
        _bmp_png(os.path.join(game_dir, f"SHIRO{s}.S6"), out_dir, f"SHIRO{s}.png")
    for _, s in places:
        _bmp_png(os.path.join(game_dir, f"SENJOU{s}.S6"), out_dir, f"SENJOU{s}.png")
    shiro_users, senjou_users = {}, {}
    for c, (_, s) in enumerate(cities):
        shiro_users.setdefault(s, []).append(c)
    for p, (_, s) in enumerate(places):
        senjou_users.setdefault(s, []).append(51 + p)
    direction = "攻方、守方的方向（第一欄是守方、鄰城是攻方來處）是用古戰場的地理推定的，呼叫端沒追。"
    rows = []
    for c, (name, s) in enumerate(cities):
        maps = [{"file": f"SHIRO{s}.png", "role": "攻城"}]
        if len(shiro_users[s]) > 1:
            maps[0]["sharedWith"] = [x for x in shiro_users[s] if x != c]
        for nb, p in links[c]:
            maps.append({"file": f"SENJOU{places[p][1]}.png", "role": "野戰", "from": nb})
        rows.append({"id": c, "name": name, "level": "都市" if c < 45 else "外族", "adjacent": [nb for nb, _ in links[c]],
                     "battlemaps": maps, "uncertain": ["battlemaps"],
                     "notes": "攻城圖取都市記錄的 SHIRO 號；野戰圖依攻方從哪個鄰城來，查 SAN6.EXE 的鄰城表得到野戰地點，"
                              "再取地點的 SENJOU 號。" + direction + ("45–50 號是外族，遊戲的都市表裡和都市同列。" if c >= 45 else "")})
    for p, (name, s) in enumerate(places):
        users = sorted({c for c in range(51) for nb, q in links[c] if q == p})
        row = {"id": 51 + p, "name": name, "level": "野戰地點",
               "battlemaps": [{"file": f"SENJOU{s}.png", "role": "野戰"}], "uncertain": ["level"]}
        shared = [x for x in senjou_users[s] if x != 51 + p]
        if shared:
            row["battlemaps"][0]["sharedWith"] = shared
        row["notes"] = ("野戰地點的號碼是遊戲的地點號＋51（MAPDATA.S6 的段號）。「野戰地點」是這邊的分類。"
                        + ("名稱是「都市名＋數字」，像開發時的標記，不是地名。" if name[-1:].isdigit() or name[-1:] in "０１２３４５６７８９" else "")
                        + "用到這個地點的守方都市：" + "、".join(cities[c][0] for c in users) + "。")
        rows.append(row)
    return rows


##############################################################################
# 三國志VII PK: D_Sn001.s7 (sango.decode_san7_scenario; the 12 scenarios agree) 54 cities from 0x160FC (0x60
# bytes: name +0 6, reading +6 8, six neighbours +0x0E, road kinds +0x14, battlefields +0x1A, slot for slot) and
# 192 battlefields from 0x157C8 (10 bytes: name 8, G_YMap number +8). The field battle of a city attacked from
# its j-th neighbour is its j-th battlefield (the PK 歷史戰役 D_Camp*.s7 agree). G_YMap00-29.s7 are 1944 x 768
# 8-bit BMPs. Place ids here: cities 0-53, battlefield b is 54 + b.
SAN7_CITIES, SAN7_FIELDS = 0x160FC, 0x157C8
SAN7_ROADS = {0: "陸路", 1: "山路", 2: "渡河", 3: "海路", 4: "棧道"}  # guessed from the maps


def places_san7pk_win(game_dir, out_dir):
    with open(os.path.join(game_dir, "San7WPK.exe"), "rb") as f:
        exe = f.read()
    with open(os.path.join(game_dir, "D_Sn001.s7"), "rb") as f:
        sc = sango.decode_san7_scenario(exe, f.read())
    gaiji = {**sango.SAN7_GAIJI, **PLACE_GAIJI}

    def s(b):
        return _gaiji(b.split(b"\0")[0].decode("cp932").strip(), gaiji)

    fields = [(s(sc[SAN7_FIELDS + 10 * b:][:8]), sc[SAN7_FIELDS + 10 * b + 8]) for b in range(192)]
    cities = [sc[SAN7_CITIES + 0x60 * k:][:0x60] for k in range(54)]
    for m in sorted({m for _, m in fields}):
        _bmp_png(os.path.join(game_dir, f"G_YMap{m:02d}.s7"), out_dir, f"G_YMap{m:02d}.png")
    users = {}
    for b, (_, m) in enumerate(fields):
        users.setdefault(m, []).append(54 + b)
    rows = []
    for k, r in enumerate(cities):
        maps, adjacent, odd = [], [], []  # odd: (slot, battlefield) with no neighbour
        for j in range(6):
            nb, road, b = r[0x0E + j], r[0x14 + j], r[0x1A + j]
            if nb != 0xFF:
                adjacent.append(nb)
                if b != 0xFF:
                    maps.append({"file": f"G_YMap{fields[b][1]:02d}.png", "role": "野戰", "from": nb})
            elif b != 0xFF:
                odd.append((j, b))
        notes = "野戰圖是「守方都市第 j 格鄰城來犯，用守方第 j 格的戰場」，PK 歷史戰役的攻守方對得上。" \
                "沒有各都市專用的攻城圖（攻城用共用素材拼成）。"
        for j, b in odd:
            notes += f"第 {j + 1} 格有戰場（{fields[b][0]}）但沒有鄰城，遊戲資料本身如此，沒有輸出。"
        rows.append({"id": k, "name": s(r[:6]), "reading": _reading(r[6:0x0E]), "level": "都市", "adjacent": adjacent,
                     "battlemaps": maps, "notes": notes})
    owners = {}
    for k, r in enumerate(cities):
        for j in range(6):
            if r[0x1A + j] != 0xFF and r[0x0E + j] != 0xFF:
                owners.setdefault(r[0x1A + j], []).append((k, r[0x0E + j], r[0x14 + j]))
    for b, (name, m) in enumerate(fields):
        row = {"id": 54 + b, "name": name, "level": "戰場", "battlemaps": [{"file": f"G_YMap{m:02d}.png", "role": "野戰"}],
               "uncertain": ["level"]}
        shared = [x for x in users[m] if x != 54 + b]
        if shared:
            row["battlemaps"][0]["sharedWith"] = shared
        uses = "、".join(f"{s(cities[a][:6])}←{s(cities[n][:6])}" for a, n, _ in owners.get(b, []))
        row["notes"] = ("戰場的號碼是遊戲的戰場號＋54。「戰場」是這邊的分類；名稱多是関或古戰場。"
                        + (f"用到的戰線（守方←攻方）：{uses}。" if uses else "沒有都市用到這個戰場。")
                        + (f"路的種類推定是{SAN7_ROADS.get(owners[b][0][2], '不明')}。" if b in owners else ""))
        rows.append(row)
    return rows


##############################################################################
# 三國志VIII PK: D_Sce.s8 (plain): 16 州 from 0x22 (17 bytes, name +2), 50 cities from 0x7F3 (16 bytes: name
# +1 5, reading +6 7, 州 +13), 86 roads from 0xB22 (7 bytes: kind, city A, city B, A-end place, B-end place, FF FF);
# the 172 places are the road ends (D_YMap.s8 part k is place k). San8WPK.exe VA 0x5D8A00 finds the place of the
# city pair; place -> picture: file 0x363EF0, 172 x (u32 left, u32 right) into G_W01Map.s8 (left, 35 + right).
# Each half is 1008 x 648 in its own palette: half k (and 35 + k) uses p_main.s8 palette 174 + k (256 x RGBX; 209-243
# repeat 174-208), found by colour statistics and by eye, not in the code. Place ids here: cities 0-49, place k is
# 50 + k.
SAN8_STATES, SAN8_CITIES, SAN8_ROADS, SAN8_PICTURES, SAN8_PALETTES = 0x22, 0x7F3, 0xB22, 0x363EF0, 174


def san8_picture(halves, palettes, left, right):
    """The 2016 x 648 battle map of W01Map[left] + W01Map[35 + right], each half in palette 174 + its number."""
    out = Image.new("RGB", (2016, 648))
    for x, k in ((0, left), (1008, 35 + right)):
        im = Image.frombytes("P", (1008, len(halves[k]) // 1008), halves[k])
        im.putpalette(b"".join(palettes[SAN8_PALETTES + k % 35][4 * c:4 * c + 3] for c in range(256)))
        out.paste(im.convert("RGB"), (x, 0))
    return out


def places_san8pk_win(game_dir, out_dir):
    with open(os.path.join(game_dir, "D_Sce.s8"), "rb") as f:
        sce = f.read()
    exe_path = os.path.join(game_dir, "San8WPK.exe")
    with open(exe_path, "rb") as f:
        exe = f.read()
    gaiji = {**sango.SAN8_GAIJI, **PLACE_GAIJI}

    def s(b):
        return _gaiji(b.split(b"\0")[0].decode("cp932").strip(), gaiji)

    states = [s(sce[SAN8_STATES + 17 * k + 2:][:5]) for k in range(16)]
    cities = [sce[SAN8_CITIES + 16 * k:][:16] for k in range(50)]
    roads, o = [], SAN8_ROADS
    while sce[o + 5] == 0xFF:
        roads.append(sce[o:o + 5])
        o += 7
    pictures = struct.unpack_from("<344I", exe, SAN8_PICTURES)
    end = {}
    for kind, a, b, pa, pb in roads:
        end[pa], end[pb] = (a, b, kind), (b, a, kind)
    file = {p: f"W01Map_{pictures[2 * p]:02d}_{35 + pictures[2 * p + 1]:02d}.png" for p in end}
    with open(os.path.join(game_dir, "G_W01Map.s8"), "rb") as f:
        halves = sango.koei_archive(f.read())
    with open(os.path.join(game_dir, "p_main.s8"), "rb") as f:
        palettes = sango.koei_archive(f.read())
    os.makedirs(out_dir, exist_ok=True)
    for p in sorted(end, key=file.get):
        path = os.path.join(out_dir, file[p])
        if not os.path.exists(path):
            san8_picture(halves, palettes, pictures[2 * p], pictures[2 * p + 1]).save(path)
    users = {}
    for p in end:
        users.setdefault(file[p], []).append(50 + p)
    palette_note = "戰場圖的色盤是 p_main.s8 第 174＋（半張號 mod 35）組，用色彩統計和看圖找到，程式裡的出處沒追。"
    rows = []
    for k, r in enumerate(cities):
        adjacent, maps = [], []
        for _, a, b, pa, pb in roads:
            if k in (a, b):
                adjacent.append(b if a == k else a)
                maps.append({"file": file[pa if a == k else pb], "role": "野戰", "from": b if a == k else a})
        rows.append({"id": k, "name": s(r[1:6]), "reading": _reading(r[6:13]), "level": "都市",
                     "province": states[r[13]], "adjacent": adjacent, "battlemaps": maps, "uncertain": ["battlemaps"],
                     "notes": "相鄰是 D_Sce.s8 的道路表，照道路順序。戰場圖取道路在這個都市一端的地點；"
                              "遊戲用守方還是攻方那一端沒確認，所以標 uncertain。" + palette_note})
    for p in range(len(end)):
        a, b, kind = end[p]
        m = {"file": file[p], "role": "野戰"}
        shared = [x for x in users[file[p]] if x != 50 + p]
        if shared:
            m["sharedWith"] = shared
        rows.append({"id": 50 + p, "name": None, "level": "道路地點", "parentCity": a, "battlemaps": [m],
                     "uncertain": ["level"],
                     "notes": f"道路 {s(cities[a][1:6])}—{s(cities[b][1:6])} 的{s(cities[a][1:6])}端（號碼是遊戲的地點號＋50，"
                              f"也是 D_YMap.s8 的段號），道路種類碼 {kind}。這一代的 191 個戰場名和 172 個地點對不上，"
                              "所以不填名稱；「道路地點」是這邊的分類。戰場圖是 G_W01Map.s8 第 "
                              f"{pictures[2 * p]} 張（左）與第 {35 + pictures[2 * p + 1]} 張（右）拼成，172 個地點只有 43 種組合，"
                              "同組合的地形相同，差在布陣點和旗標。" + palette_note})
    return rows


##############################################################################
# 三國志12 PK: PK/Scenario/Scenario0.dat part 6 (sango.san12_decrypt) holds the 40 cities (248 bytes: name +4,
# 地方 the low 4 bits of +0x18, six u32 neighbours from +0x1C). The battle number is the city number (RVA 0x3E600),
# but the maps are 3D terrain: no PNG.
SAN12_REGIONS = ["河北", "中原", "西北", "呉越", "荊楚", "巴蜀"]


def places_san12pk_win(game_dir, out_dir):
    with open(os.path.join(game_dir, "PK", "Scenario", "Scenario0.dat"), "rb") as f:
        d = f.read()
    n = struct.unpack_from("<I", d, 4)[0]
    offsets = list(struct.unpack_from(f"<{n}I", d, 8)) + [len(d)]
    city = sango.san12_decrypt(d[offsets[6]:offsets[7]])
    rows = []
    for k in range(40):
        r = city[248 * k:][:248]
        rows.append({"id": k, "name": _gaiji(r[4:9].split(b"\0")[0].decode("cp932"), PLACE_GAIJI), "level": "都市",
                     "region": SAN12_REGIONS[struct.unpack_from("<I", r, 0x18)[0] & 0xF],
                     "adjacent": [x for x in struct.unpack_from("<6I", r, 0x1C) if x < 40],
                     "notes": "戰場號＝都市號（San12WPK.exe RVA 0x3E600），戰場推定用守方都市的地形；地形是 3D，沒有輸出圖。"
                              "沒有関、港。"})
    return rows


##############################################################################
# 三國志13 PK: names are strings 210 + id of the string tables (item 0 of item 0 of PK item 2, Japanese; 1416,
# Traditional Chinese); positions in node.stgn (PK item 450: 20-byte records, u16 id, x, y at +4, +8). XL
# tables of PK item 941: 1 cities (col 0 地方, col 1 州, cols 3-9 neighbours, col 10 itself), 2 関, 3 縣級地點 (col 1 id, cols
# 2-5 related cities), 22 battle numbers (col 18 stage: 0-15 btl_CSL, 16-26 btl_FLD, 27 btl_RIV, 28 btl_GAT). 14
# 州 names are strings 5222-5235. Field battles pick their map by the region code under the unit, not by place.
SAN13_REGIONS = ["河北", "中原", "西北", "巴蜀", "荊楚", "吳越"]
SAN13_STAGES = [f"btl_CSL_{i:02d}" for i in range(16)] + [f"btl_FLD_{i:02d}" for i in range(11)] + \
    ["btl_RIV_00", "btl_GAT_00"]
SAN13_PLACE_GAIJI_TC = {b"\xfa\x70": "坂"}  # 長坂 (the Japanese name)
_XL = {0: "I", 1: "i", 2: "h", 3: "B", 4: "i", 5: "H", 6: "b", 7: "f"}


def _xl_rows(b):
    _, _, cols, rows, size, header = struct.unpack_from("<6H", b, 2)
    fmt = "<" + "".join(_XL[t] for t in b[0x10:0x10 + cols])
    assert struct.calcsize(fmt) == size
    return [struct.unpack_from(fmt, b, header + r * size) for r in range(rows)]


def places_san13pk_win(game_dir, out_dir):
    def strings(item, enc, gaiji):
        return sango.san13_strings(sango.san13_items(sango.san13_items(sango.san13_entry(game_dir, item))[0])[0], enc,
                                   gaiji)

    tc = strings(sango.SAN13_NAMES_TC, "cp950", {**sango.SAN13_GAIJI_TC, **SAN13_PLACE_GAIJI_TC})
    jp = strings(sango.SAN13_NAMES, "cp932", {})
    # The Japanese names' gaiji (U+E0xx) read off the Chinese name of the same place, where both are as long
    gaiji = {}
    for i in range(210, 710):
        if len(jp[i]) == len(tc[i]):
            for c, d in zip(jp[i], tc[i]):
                if 0xE000 <= ord(c) < 0xF900:
                    assert gaiji.setdefault(ord(c), d) == d
    guessed = {i - 210 for i in range(210, 710) if len(jp[i]) != len(tc[i]) and any(ord(c) in gaiji for c in jp[i])}
    jp = [_gaiji(x, gaiji) for x in jp]
    tables = sango.san13_items(sango.san13_entry(game_dir, 941))
    cities, gates, counties, battles = (_xl_rows(sango.san13_unzip(tables[k])) for k in (1, 2, 3, 22))
    node = sango.san13_entry(game_dir, 450)
    n = struct.unpack_from("<I", node, 8)[0]
    pos = {}
    for i in range(n):
        pid, _, _, x, y = struct.unpack_from("<HBBII", node, 0x10 + 20 * i)
        pos[pid] = (x, y)
    states = [tc[5222 + i] for i in range(14)]
    county = {r[1]: r for r in counties if r[1] >= 0}
    gate_battle = {360 + i: gates[i][0] for i in range(len(gates))}
    rows = []
    for pid in range(500):
        name, name_ja = tc[210 + pid] if 210 + pid < len(tc) else "", jp[210 + pid] if 210 + pid < len(jp) else ""
        if not name and not name_ja:
            continue
        row = {"id": pid, "name": name or name_ja}
        notes, uncertain = [], []
        if name_ja and name_ja != row["name"]:
            row["nameJa"] = name_ja
            if pid in guessed:
                uncertain.append("nameJa")
                notes.append("日文版的名稱和繁中版不同，其中的外字是照別的地點的繁中名對出來的。")
        if pid < 60:
            row["level"] = "都市"
            row["region"], row["province"] = SAN13_REGIONS[cities[pid][0]], states[cities[pid][1]]
            row["adjacent"] = [c for c in cities[pid][3:10] if c < 60]
            notes.append(f"攻城圖是 {SAN13_STAGES[battles[pid][18]]}（3D，沒有輸出圖）。")
        elif pid < 300:
            row["level"] = "縣級地點"
            uncertain.append("level")
            notes.append("遊戲裡這類地點的稱呼沒找到，「縣級地點」是這邊的分類。")
            related = [c for c in county[pid][2:6] if c != 255] if pid in county else []
            if related:
                row["parentCity"] = related[0]
                uncertain.append("parentCity")
                notes.append("parentCity 取相關都市的第一個（推定是所屬）；相關都市："
                             + "、".join(tc[210 + c] for c in related) + "。")
        elif 360 <= pid < 380:
            row["level"] = "關"
            notes.append(f"關的戰場圖是 {SAN13_STAGES[battles[gate_battle[pid]][18]]}，8 關共用（3D，沒有輸出圖）。")
        elif 380 <= pid < 460:
            row["level"] = "港" if row["name"].endswith("港") else "渡口"
        else:
            row["level"] = "沖" if row["name"].endswith("沖") else "地點"
            if row["level"] == "地點":
                uncertain.append("level")
                notes.append("「地點」是這邊的分類（官渡、開封這類，遊戲裡的稱呼沒找到）。")
        if pid in pos:
            row["pos"] = {"x": pos[pid][0], "y": pos[pid][1], "grid": "world"}
        if uncertain:
            row["uncertain"] = uncertain
        notes.append("野戰看部隊所在位置的地域碼選圖，不看地點；水戰另有一張。pos 是 node.stgn 的世界座標。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


##############################################################################
# 三國志IX PK: names in M_MsgPK.s9 (LS11) part 0, items split by 05 05 05, (name, reading) pairs: 136-165 the 14
# 州 and 異民, 166-439 the 137 named places of the 200 bldg slots, 721-820 the 45 cities and 5 異民族; 959-975 the
# 17 facility kinds. D_Sce001.S9 (RIFF S9SC): `city` 50 x 56 bytes (+22 u16 州, +44/+46 x, y), `bldg` 200 x 28
# bytes (+6 u16 kind = fbld index, 0xFFFF a name only; +14 u16 city; +18/+20 x, y). No battle maps: battles are
# on the 200 x 200 map (`squa`).
SAN9_KIND_LEVEL = {0: "都市", 1: "港", 2: "関", 3: "関", 4: "関"}  # fbld index -> level (2-4 are 3 grades of 関)


def places_san9pk_win(game_dir, out_dir):
    import ls11
    with open(os.path.join(game_dir, "D_Sce001.S9"), "rb") as f:
        sce = f.read()

    def chunk(tag):
        i = sce.index(tag)
        return sce[i + 8:i + 8 + struct.unpack_from("<I", sce, i + 4)[0]]

    with open(os.path.join(game_dir, "M_MsgPK.s9"), "rb") as f:
        msg = ls11.ls11_decode_parts(f.read())[0].split(b"\x05\x05\x05")
    gaiji = {**sango.SAN9_GAIJI, **PLACE_GAIJI}

    def text(i):
        return "".join(gaiji.get(ord(c), c) for c in msg[i].decode("cp932")).strip()

    def reading(i):
        return unicodedata.normalize("NFKC", msg[i][2:-2].decode("cp932"))

    states = [text(136 + 2 * k) for k in range(15)]
    kinds = [text(959 + k) for k in range(17)]
    city, bldg = chunk(b"city"), chunk(b"bldg")
    rows = []
    for k in range(50):
        state, x, y = (struct.unpack_from("<H", city, 56 * k + o)[0] for o in (22, 44, 46))
        row = {"id": k, "name": text(721 + 2 * k), "reading": reading(722 + 2 * k),
               "level": "都市" if k < 45 else "異民族", "province": states[state],
               "pos": {"x": x, "y": y, "grid": "square", "w": 200, "h": 200},
               "notes": "沒有戰場圖，野戰、攻城都在 200 × 200 格的大地圖上打。沒有相鄰表。"}
        if k >= 45:
            row["uncertain"] = ["level"]
            row["notes"] += "「異民族」是這邊的稱呼（州表裡寫「異民」）。"
        rows.append(row)
    for k in range(137):
        kind, parent, x, y = (struct.unpack_from("<H", bldg, 28 * k + o)[0] for o in (6, 14, 18, 20))
        row = {"id": 50 + k, "name": text(166 + 2 * k), "reading": reading(167 + 2 * k),
               "level": SAN9_KIND_LEVEL.get(kind, kinds[kind] if kind < 17 else "地名"), "parentCity": parent,
               "pos": {"x": x, "y": y, "grid": "square", "w": 200, "h": 200},
               "notes": "號碼是 bldg 區塊的序號＋50。所屬都市是 bldg +14。"}
        if kind == 0xFFFF:
            row["uncertain"] = ["level"]
            row["notes"] += "這一筆只有地名、沒有設施，「地名」是這邊的分類。"
        rows.append(row)
    return rows


##############################################################################
# 水滸傳・天命之誓 DOS 中文版 (main dataset) with the PC-98 version beside it (../suikoden-pc98): 49 州 from the
# SUIDATA1.CIM 州 tables (koei_games.load_suikoden_provinces; FC, PC-98 and DOS have the same neighbours). The
# battle map is the attacked 州's, one per season; the DOS EGA tiles are not decoded, so the PNGs are the PC-98
# HEXMAP.DAT drawn with the PC-98 tiles (the DOS terrain and 州歸屬 layers decode to the same cells).
SUIKODEN_SEASONS = "春夏秋冬"


def places_suikoden_dos(game_dir, out_dir):
    pc98 = os.path.join(game_dir, "..", "suikoden-pc98")
    for season, label in enumerate(SUIKODEN_SEASONS):
        _save(koei_games.render_suikoden_battle_maps(pc98, season), os.path.join(out_dir, label),
              [f"{n:02d}.png" for n in range(1, 50)])
    zh = koei_games.load_suikoden_provinces(game_dir, dos=True)
    ja = koei_games.load_suikoden_provinces(pc98)
    with open(os.path.join(game_dir, "SUIDATA1.CIM"), "rb") as f:
        data = f.read()
    rows = []
    for k, ((name, cities, nb), (name_ja, cities_ja, _)) in enumerate(zip(zh, ja)):
        x, y = struct.unpack_from("<HH", data, koei_games.SUIKODEN_DOS_PROVINCES + 27 * k + 14)
        row = {"id": k + 1, "name": name}
        if name_ja != name.removesuffix("州"):
            row["nameJa"] = name_ja
        row.update({"level": "州", "cities": cities, "adjacent": [n + 1 for n in nb],
                    "battlemaps": [{"file": f"{s}/{k + 1:02d}.png", "role": BATTLE, "season": s}
                                   for s in SUIKODEN_SEASONS],
                    "pos": {"x": x, "y": y, "grid": "pixel"}, "uncertain": ["pos"],
                    "notes": "日文版（PC-98）的州表不寫「州」字。戰場圖是 PC-98 版的圖塊（中文版的 EGA 圖塊沒解，"
                             "兩版的地形與州歸屬相同）。pos 是州表 +14、+16（日文版 +8、+10）的值，看起來是大地圖上的位置，"
                             "沒有追程式，單位未確認。"})
        if cities != cities_ja:
            row["notes"] += f"城數：中文版 {cities}，日文版與 FC {cities_ja}；中文版的數字和戰場圖上的城格數一致。"
        rows.append(row)
    return rows


# (dataset, from, to) adjacencies that are one-way in the game data, explained in the rows' notes
ONE_WAY = {("san14pk-win", *pair) for pair in SAN14_ONE_WAY}
ONE_WAY |= {("nobu11pk-win", 1019, 1020), ("nobu11pk-win", 1020, 1029)}  # 加賀 lists 伊勢, not 能登 (wiki_nobu11)

DATASETS = {"san1-pc98": places_san1_pc98, "san2-pc98": places_san2_pc98, "san3-pc98": places_san3_pc98,
            "san4pk-pc98": places_san4pk_pc98, "san5pk-pc98": places_san5pk_pc98, "san6pk-win": places_san6pk_win,
            "san7pk-win": places_san7pk_win, "san8pk-win": places_san8pk_win, "san9pk-win": places_san9pk_win,
            "san10pk-win": places_san10pk_win,
            "san11pk-win": places_san11pk_win, "san12pk-win": places_san12pk_win, "san13pk-win": places_san13pk_win,
            "san14pk-win": places_san14pk_win, "suikoden-dos": places_suikoden_dos}
# 信長の野望: dataset -> module wiki_<game>.py with places(game_dir, out_dir)
MODULES = {"nobu2-pc88": "wiki_nobu2", "nobu2-dos": "wiki_nobu2_dos", "nobu3-pc98": "wiki_nobu3", "nobu4-pc98": "wiki_nobu4",
           "nobu5pk-win": "wiki_nobu5", "nobu6pk-pc98": "wiki_nobu6", "nobu7pk-win": "wiki_nobu7",
           "nobu8pk-win": "wiki_nobu8", "nobu9pk-win": "wiki_nobu9", "nobu10pk-win": "wiki_nobu10",
           "nobu11pk-win": "wiki_nobu11", "nobu12pk-win": "wiki_nobu12", "nobu13pk-win": "wiki_nobu13"}


def check(dataset, rows, out_dir):
    """koei-places/1 checks: references exist, battle map files exist, from is adjacent, adjacency is two-way
    (except the game's own one-way pairs in ONE_WAY, which the notes explain). Returns (checked, [problems])."""
    ids = {r["id"] for r in rows}
    assert len(ids) == len(rows), "duplicate id"
    checked, bad = 0, []
    for r in rows:
        refs = r.get("adjacent", []) + ([r["parentCity"]] if "parentCity" in r else []) + \
            [x for m in r.get("battlemaps", []) for x in m.get("sharedWith", []) + ([m["from"]] if "from" in m else [])]
        for x in refs:
            checked += 1
            if x not in ids:
                bad.append(f"{r['id']}: no place {x}")
        for m in r.get("battlemaps", []):
            checked += 1
            if not os.path.exists(os.path.join(out_dir, m["file"])):
                bad.append(f"{r['id']}: no file {m['file']}")
            if "from" in m:
                checked += 1
                if m["from"] not in r.get("adjacent", []):
                    bad.append(f"{r['id']}: from {m['from']} not adjacent")
    by_id = {r["id"]: r for r in rows}
    for r in rows:
        for x in r.get("adjacent", []):
            checked += 1
            if x in by_id and r["id"] not in by_id[x].get("adjacent", []) and (dataset, r["id"], x) not in ONE_WAY:
                bad.append(f"{r['id']} -> {x} one-way")
    return checked, bad


@click.command()
@click.argument("dataset", type=click.Choice(list(DATASETS) + list(MODULES)))
@click.option("--game-dir", "game_dir", required=True)
@click.option("--out", "out", required=True, help="輸出目錄（寫 <dataset>.jsonl 與 <dataset>/ 的戰場圖）")
def places_export(dataset, game_dir, out):
    """匯出三國志各代與水滸傳的地點與戰場圖（koei-places/1，給 koei-wiki）

    dekoei.py places-export san3-pc98 --game-dir ../games/san3-pc98 --out ../export/koei-wiki/places
    """
    map_dir = os.path.join(out, dataset)
    reader = importlib.import_module(MODULES[dataset]).places if dataset in MODULES else DATASETS[dataset]
    rows = [{"dataset": dataset, **r} for r in reader(game_dir, map_dir)]
    with open(os.path.join(out, f"{dataset}.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    checked, bad = check(dataset, rows, map_dir)
    for b in bad:
        print(b)
    maps = sum(len(files) for _, _, files in os.walk(map_dir))
    print(f"{dataset}: {len(rows)} places, {maps} maps; {checked} checked, {len(bad)} mismatched")
