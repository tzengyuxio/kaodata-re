"""三國志III (san3-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san3-pc98 id (531 people, scenarios
1-6 deduplicated by face code, kaodata_export.san3_characters). The data comes from the PC-98 SNDATA?B.CIM (600 x 62
bytes); name is the DOS Chinese version's spelling of the same face code (the two sets of face codes are the same, one
to one), nameJa the PC-98 one. Field sources: notes/san3.md「koei-wiki 匯出」, notes/san-attributes.md「三國志III」."""
import os
import struct

import kaodata_export as ke
import san3
from places_export import BATTLE, _areas, _reading, _save, _text
from kaodata_export import SAN3_INPUTS
from kaodata_export import san3_characters

# SNDATA?.CIM +2 u16 is the year before the start: scenario 1 stores 188 and starts in 189 January (capture main_005)
# PC-98 MAIN.EXE DGROUP 0x27FE: the 身分 names by +16; 0x8124 shows 太守 instead for a city's governor (not exported)
RANKS = {0: "君主", 1: "軍師", 2: "将軍", 3: "武官", 4: "文官", 5: "在野"}
HIDDEN, ABSENT = 6, 7  # 6: put in the city's second list (MAIN.EXE 0x97B3), 「未発見武将」 (🟡); 7: not on the map
# PC-98 scenario 1 gives 車胄 楊懐's face code 0x82CB (DOS: 0x9831): that record is 車胄, not 楊懐
SAME_CODE = {(1, 0x82CB, "車胄"): 0x9831}
# the DOS Chinese version gives these four another person's name (孔秀, 蔡陽, and 張闓/張顗 swapped); the PC-98 names
# are right, so name takes the historical spelling instead (notes/san3.md「人物」)
ZH_OTHER_PERSON = {0xC1, 0xC02B, 0x96D9, 0x9C95}


def zh_variants(dos_dir, zh):
    """face code -> [(spelling, [scenario numbers])] for the DOS Chinese spellings other than zh[code] (the one name
    takes; koei-wiki 遊戲/三國志III/人名勘誤 lists the same ones)."""
    out = {}
    for k, file in enumerate(SAN3_INPUTS[2:], 1):
        for p in san3.load_san3_persons(os.path.join(dos_dir, file)):
            name = p["name"].strip()  # 臧霸 has a trailing space in scenario 4
            if name != zh[p.face]:
                out.setdefault(p.face, {}).setdefault(name, []).append(k)
    return {code: list(v.items()) for code, v in out.items()}


def persons(game_dir):
    chars = ke.san3_characters(game_dir, True)
    zh = dict(ke.san3_characters(os.path.join(game_dir, "..", "san3-dos")))
    variants = zh_variants(os.path.join(game_dir, "..", "san3-dos"), zh)
    assert set(zh) == {c for c, _ in chars}
    cid = {c: i for i, (c, _) in enumerate(chars)}
    by_id = {i: st for i, _, st in stats(game_dir)}
    scen = []  # per scenario: (year, {character id: record})
    for k in range(1, 7):
        with open(os.path.join(game_dir, f"SNDATA{k}.CIM"), "rb") as f:
            year = struct.unpack_from("<H", f.read(4), 2)[0] + 1
        with open(os.path.join(game_dir, f"SNDATA{k}B.CIM"), "rb") as f:
            data = f.read()
        recs = {}
        for i in range(600):
            r = data[i * san3.PC98_RECORD_SIZE:(i + 1) * san3.PC98_RECORD_SIZE]
            if r[0x31:0x37] == bytes(6):
                continue
            code = struct.unpack_from("<H", r, 2)[0]
            code = SAME_CODE.get((k, code, san3.decode_pc98_name(r[0x31:0x37])), code)
            assert cid[code] not in recs
            recs[cid[code]] = r
        scen.append((year, recs))
    rulers = [{r[27]: i for i, r in recs.items() if r[16] == 0} for _, recs in scen]

    rows = []
    for i, (code, name_ja) in enumerate(chars):
        row = {"id": i, "name": ke.SAN3_NAME_HISTORICAL[code] if code in ZH_OTHER_PERSON else zh[code]}
        if name_ja != row["name"]:
            row["nameJa"] = name_ja
        rec = next(recs[i] for _, recs in scen if i in recs)
        row["born"] = rec[37]
        row["stats"] = by_id[i]
        out, first = [], None
        for k, (year, recs) in enumerate(scen):
            r = recs.get(i)
            if r is None or r[16] == ABSENT:
                continue
            first = k if first is None else first
            s = {"scenario": k + 1, "year": year, "month": 1, "location": r[26],
                 "status": "未発見" if r[16] == HIDDEN else RANKS[r[16]]}
            if r[16] == 0:
                s["lord"] = i
            elif r[16] < 5 and r[27] in rulers[k]:
                s["lord"] = rulers[k][r[27]]
                s["loyalty"] = r[25]
            out.append(s)
        if first is not None:
            row["more"] = {"年齢": scen[first][0] - row["born"]}
        row["hidden"] = {"相性": rec[23], "義理": rec[24]}
        if rec[31] != 0xFF:
            row["relations"] = {"clan": rec[31]}
        if out:
            row["scenarios"] = out
        row["uncertain"] = ["hidden.相性", "hidden.義理"] + (["relations.clan"] if "relations" in row else []) + \
            (["scenarios.status"] if any(s["status"] == "未発見" for s in out) else [])
        notes = []
        if first is not None and first:
            notes.append(f"more.年齢取劇本 {first + 1}（第一個在地圖上的劇本）。")
        if not out:
            notes.append("六個劇本開始時都不在地圖上（身分 7）；遊戲中途怎麼登場沒追。")
        if any(s["status"] == "未発見" for s in out):
            notes.append("「未発見」是身分 6：在城裡但還沒被找到的在野武將（遊戲有「未発見武将」一詞，對應是推定）。")
        if ke.yoshikawa_note(row["name"]):
            notes.append(ke.yoshikawa_note(row["name"]))
        elif code in ZH_OTHER_PERSON:
            notes.append(f"中文版寫成別人的名字「{zh[code]}」，name 改用史書寫法。")
        elif code in ke.SAN3_NAME_HISTORICAL:
            notes.append(f"中文版寫法的史書寫法 {ke.SAN3_NAME_HISTORICAL[code]}。")
        for spelling, ks in variants.get(code, []):
            notes.append(f"中文版劇本 {'、'.join(map(str, ks))} 寫作「{spelling}」。")
        if code in ke.SAN3_PC98_NAME_HISTORICAL and not ke.yoshikawa_note(row["name"]):
            notes.append(f"日文版寫法的史書寫法 {ke.SAN3_PC98_NAME_HISTORICAL[code]}。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows


##############################################################################
# 三國志III PC-98: location ids 0-45 are 州, 46-67 據點 (MAIN.EXE image 0x5D06 / 0x5D11). Names in SNDATA1.CIM:
# 州 records from 0x163 (0x4A bytes, name 7 + reading), 據點 from 0xE7C (25 bytes). Hex grid 15 x 16 at
# MAIN.EXE 0x53431 (location id, 0x80 road, 0xFF none), the step table at 0x53418 (0x70C4 / 0x7261). The battle
# map is HEXDATA.DAT map (location id) (0x2EF8B / 0x3847C).
SAN3_GAIJI = {6: "鄴", 16: "下邳", 19: "譙", 60: "涪城"}  # names with gaiji, by location id


# World map (san3.render_san3_world_map, 640 x 400): each 州 has a black 8 x 8 square (filled with the owner's
# colour in play) and each 據點 a blue number box; SAN3_MAP_POS is the centre of that square or box, picked by
# reading the game's numbers (1-68) printed beside them.
SAN3_MAP_W, SAN3_MAP_H, SAN3_SQUARE, SAN3_BOX = 640, 400, 0, 1


SAN3_MAP_POS = [(588, 30), (492, 46), (420, 36), (364, 62), (452, 80), (428, 102), (380, 122), (500, 114), (412, 138),
                (388, 164), (316, 168), (306, 133), (244, 124), (228, 96), (180, 124), (140, 52), (468, 192),
                (444, 176), (364, 186), (404, 186), (388, 212), (308, 194), (268, 194), (276, 220), (228, 190),
                (356, 228), (316, 244), (260, 260), (308, 268), (300, 292), (235, 289), (420, 212), (452, 214),
                (476, 232), (468, 260), (412, 248), (388, 276), (204, 164), (164, 170), (156, 204), (116, 236),
                (212, 220), (172, 252), (100, 308), (60, 284), (316, 318), (526, 31), (143, 144), (357, 245),
                (456, 58), (396, 116), (334, 153), (401, 166), (200, 136), (192, 112), (164, 104), (484, 195),
                (302, 220), (247, 237), (423, 228), (111, 198), (428, 266), (331, 275), (333, 179), (280, 115),
                (252, 160), (342, 119), (178, 194)]


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


def _boxes(im, colour):
    """Bounding box (x0, y0, x1, y1) and pixel count of each 4-connected area of one colour, by label."""
    w = im.size[0]
    lab, out = _areas(im, colour), {}
    for i, a in enumerate(lab):
        if a:
            x, y = i % w, i // w
            x0, y0, x1, y1, n = out.get(a, (x, y, x, y, 0))
            out[a] = (min(x0, x), min(y0, y), max(x1, x), max(y1, y), n + 1)
    return out


def world_check(game_dir, rows):
    """Each 州 pos is inside its own black 8 x 8 square, each 據點 pos inside its own blue number box, and the map
    has no other squares or boxes."""
    im = san3.render_san3_world_map(game_dir)
    squares = [b for b in _boxes(im, SAN3_SQUARE).values() if b[2] - b[0] == b[3] - b[1] == 7 and b[4] == 64]
    boxes = [b for b in _boxes(im, SAN3_BOX).values() if b[3] - b[1] == 8 and 10 <= b[2] - b[0] <= 12]
    bad, used = [], set()
    for r in rows:
        x, y = r["pos"]["x"], r["pos"]["y"]
        hit = [b for b in (squares if r["level"] == "州" else boxes) if b[0] <= x <= b[2] and b[1] <= y <= b[3]]
        if len(hit) != 1 or hit[0] in used:
            bad.append(f"{r['id']}: pos not on a {r['level']} mark of its own")
        used.update(hit)
    if len(squares) + len(boxes) != len(rows):
        bad.append(f"{len(squares)} squares and {len(boxes)} boxes on the map for {len(rows)} places")
    return len(rows), bad


def places(game_dir, out_dir):
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    san3.render_san3_world_map(game_dir).save(os.path.join(out_dir, "world", "MAPDATA-spring.png"))
    _save(san3.render_san3_battle_maps(game_dir), out_dir, [f"{n:02d}.png" for n in range(1, 69)])
    names, readings, _, adjacent = san3_places(game_dir)
    rows = []
    for v in range(68):
        row = {"id": v, "name": names[v], "reading": readings[v], "level": "州" if v < 46 else "據點",
               "adjacent": adjacent(v), "battlemaps": [{"file": f"{v + 1:02d}.png", "role": BATTLE}],
               "pos": {"x": SAN3_MAP_POS[v][0], "y": SAN3_MAP_POS[v][1], "grid": "pixel", "w": SAN3_MAP_W,
                       "h": SAN3_MAP_H}}
        if v >= 46:
            row["uncertain"] = ["level"]
            row["notes"] = ("「據點」是這邊的分類，遊戲裡的稱呼沒查到；46–67 號包括 5 個関、渡口、山與古戰場。"
                            "遊戲的程式用同一套地點號處理州與據點。")
        rows.append(row)
    for row in rows:
        row["notes"] = (row.get("notes", "") + "相鄰是大地圖六角格上沿道路走得到的地點（遊戲每次實際走哪幾個方向沒查）。"
                        "pos 是大地圖 world/MAPDATA-spring.png（640×400）上的像素：州是編號旁的黑色方塊"
                        "（遊戲中塗成勢力色）中心，據點是藍色編號框的中心。")
    return rows


# 三國志III PC-98: SNDATA?B.CIM, 600 x 62-byte records (the first 43 bytes are the DOS s3_format), face code u16 at
# +2; 陸指 水指 武力 知力 政治 魅力 at +17-22 (武力 without items). The builder (san3_characters) takes scenarios 1-6
# in order and keeps each face code once (named by its most common spelling); the values are from the first record
# with that code and name. 0x82CB is both 車胄 (scenario 1) and 楊懐 (1-4): the character is 楊懐, with 楊懐's values.
# Only 劉表 changes between scenarios (水指 67 -> 25, 武力 70 -> 67 from scenario 2); scenario 1 is kept
SAN3_STATS = ["陸指", "水指", "武力", "知力", "政治", "魅力"]


def stats(game_dir):
    first = {}
    for name in SAN3_INPUTS[2:]:
        with open(os.path.join(game_dir, name), "rb") as f:
            data = f.read()
        for i in range(600):
            rec = data[i * san3.PC98_RECORD_SIZE:(i + 1) * san3.PC98_RECORD_SIZE]
            if rec[0x31:0x37] != bytes(6):
                key = struct.unpack_from("<H", rec, 2)[0], san3.decode_pc98_name(rec[0x31:0x37])
                first.setdefault(key, dict(zip(SAN3_STATS, rec[17:23])))
    return [(i, name, first[code, name]) for i, (code, name) in enumerate(san3_characters(game_dir, True))]
