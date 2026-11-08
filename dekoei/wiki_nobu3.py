"""信長の野望・戦国群雄伝 (nobu3-pc98) for koei-wiki: persons (koei-persons/1) and places (koei-places/1). The data
is the PC-98 scenarios; name is the DOS 中文版's (nobu3-dos beside it, the same records in the same slots), nameJa the
PC-98 Japanese. Field sources and how sure they are: notes/nobu3.md「人物欄位」「地理」「koei-wiki 匯出」."""
import os
import struct
import unicodedata

from PIL import Image

import genpei
import koei_games
from nobu4_extras import decode_pack

# SNDATA1/2.CIM (PC-98 and DOS alike): +4 u16 year; lords from 0x4C (46 bytes: +0 the lord's person pointer, 0 ends);
# 38 國 from 0x722 (41 bytes: +2 name 9 bytes, +27 lord pointer, +29 城主 pointer, +31 7 neighbours: low 6 bits
# the 國 (0-based), FF none); persons from 0xD38 (PC-98 38 bytes, DOS 44: names 9 + 7, DOS 11 + 11; the fields
# below are PC-98 offsets, DOS + 6): +16 年齢 in the debut year, +17 壽命 (age at death), +18-21 政治力 戦闘力
# 魅力 野望, +23 (義理?), +26 debut year - 1560 in both scenarios (1582: 22 for everyone present), +27 u16 face code, +29 國, +30 lord (index of the lord
# table, FF 浪人), +31 忠誠度. Pointers are load addresses: person k = 0xD78 + size k, lord k = 0x8E + 46 k.
NOBU3_LORDS, NOBU3_PROVINCES, NOBU3_PERSONS, NOBU3_PROVINCE_COUNT = 0x4C, 0x722, 0xD38, 38
NOBU3_BASE = 1560
NOBU3_LABELS = ["政治力", "戦闘力", "魅力", "野望"]
# HEXDATA.DAT (PC-98 MAIN.EXE image 0x1265 loads all of it): 32x32 tiles of 3 interleaved planes (byte k = bit k)
# from 0x1200, 0x180 each (0x150AD); maps from 0x46E0, 0x138 per 國: field 13 x 12 then castle at +0x9C (0xA02).
# Castle cells draw tile v & 0xF, field cells (v & 7) + 11 (0x143AC adds 11 when [0x57D0] is 0; bit 3 of field
# cells is taken as cleared, as on FC). The tile draw clears the red plane of a cell with bit 0x10 (0x150E2 calls
# 0x13D6C, which tests the bit, then zeroes every third tile byte from +1). In the data only the castle maps keep the
# bit for that: field cells with it are red in the capture (the field path clears it somewhere; not traced). Odd columns
# are 16 px lower. The game uses the digital 8 colours (bit 0 blue, 1 red, 2 green; checked against a capture).
NOBU3_TILES, NOBU3_MAPS = 0x1200, 0x46E0
PC98_DIGITAL = [0, 0, 0, 0, 0, 255, 255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 255, 255, 0, 255, 255, 255]

# MAPDATA.DAT: four 416 x 152 pictures in the PACKDATA run-length format (nobu4_extras.decode_pack; colour bits 0
# blue, 1 green, 2 red in that decoder's order): 0 all Japan without names, 1-3 the east, centre and west maps the
# game switches between. The screen draws every line twice (416 x 304). Each map has 38 (x, y) u16 points at
# DS:0x3C5A + 0x98 * map (MAIN.EXE image 0x55B4 returns x and y * 2; DGROUP is image 0x202F0, FFFF where the 國 is
# not on that map). On maps 1-3 the points are near the edge of the 國 (fill seeds); on map 0 near the middle.
NOBU3_MAP_POINTS, NOBU3_MAP_W, NOBU3_MAP_H = 0x202F0 + 0x3C5A, 416, 304
NOBU3_MAP_PALETTE = [0, 0, 0, 0, 0, 255, 0, 255, 0, 0, 255, 255, 255, 0, 0, 255, 0, 255, 255, 255, 0, 255, 255, 255]


def _read(game_dir, n):
    with open(os.path.join(game_dir, f"SNDATA{n}.CIM"), "rb") as f:
        return f.read()


def _ja(b):
    return unicodedata.normalize("NFKC", b.split(b"\0")[0].decode("cp932"))


def _scenario(game_dir, n):
    """(year, [(slot, record, zh name)], {lord index: slot}, {province: (lord slot, 城主 slot)})."""
    p, d = _read(game_dir, n), _read(os.path.join(game_dir, "..", "nobu3-dos"), n)
    year = struct.unpack_from("<H", p, 4)[0]
    people = []
    for k, o in enumerate(range(NOBU3_PERSONS, len(p) - 37, 38)):
        if p[o]:
            q = d[NOBU3_PERSONS + 44 * k:][:44]
            zh = koei_games.koei_tw_name(q[:11].split(b"\0")[0]) + koei_games.koei_tw_name(q[11:22].split(b"\0")[0])
            people.append((k, p[o:o + 38], zh))
    lords, i = {}, 0
    while ptr := struct.unpack_from("<H", p, NOBU3_LORDS + 46 * i)[0]:
        lords[i] = (ptr - 0xD78) // 38
        i += 1
    rule = {}
    for c in range(NOBU3_PROVINCE_COUNT):
        lord, castellan = struct.unpack_from("<HH", p, NOBU3_PROVINCES + 41 * c + 27)
        rule[c] = ((lord - 0x8E) // 46 if lord else None, (castellan - 0xD78) // 38 if castellan else None)
    return year, people, lords, rule


def persons(game_dir):
    # ids as build_nobu3_pc98: scenario 1 then 2, one person per (name, face code)
    ids, rows, scenarios = {}, [], [_scenario(game_dir, n) for n in (1, 2)]
    for year, people, _, _ in scenarios:
        for k, r, zh in people:
            key = (_ja(r[:9]) + _ja(r[9:16]), struct.unpack_from("<H", r, 27)[0])
            if key not in ids:
                ids[key] = len(rows)
                age, life, debut = r[16], r[17], r[26]
                born = NOBU3_BASE + debut - age
                row = {"id": len(rows), "name": zh}
                if zh != key[0]:
                    row["nameJa"] = key[0]
                row.update({"born": born, "died": born + life, **({"debut": NOBU3_BASE + debut} if NOBU3_BASE + debut > year else {}),
                            "stats": dict(zip(NOBU3_LABELS, r[18:22])), "hidden": {"寿命": life, "義理": r[23]},
                            "scenarios": [], "uncertain": ["hidden.義理"],
                            "notes": "生年＝1560＋登場年差（+26）－登場時年齢（+16），歿年＝生年＋寿命（+17，死亡時的年齢）。"
                                     "義理是 +23 的推定名稱（謙信 100、松永 4），沒讀程式；另外兩個隱藏值 +22、+24 意義不明，沒有輸出。"
                                     "能力與寿命取第一次出現的劇本（劇本 2 有人不同，例如信長的寿命 60→70）。"})
                rows.append(row)
    slot_id = []
    for year, people, lords, rule in scenarios:
        slot_id.append({k: ids[(_ja(r[:9]) + _ja(r[9:16]), struct.unpack_from("<H", r, 27)[0])] for k, r, _ in people})
    for n, ((year, people, lords, rule), sid) in enumerate(zip(scenarios, slot_id), 1):
        castellans = {c for _, c in rule.values() if c is not None}
        heads = set(lords.values())
        for k, r, _ in people:
            s = {"scenario": n, "year": year}
            if r[30] != 0xFF:
                s["lord"] = sid[lords[r[30]]]
            s["location"] = r[29] + 1
            s["status"] = "大名" if k in heads else "城主" if k in castellans else "家臣" if r[30] != 0xFF else "浪人"
            if r[30] != 0xFF:
                s["loyalty"] = r[31]
            if NOBU3_BASE + r[26] > year:
                s["status"] = "未登場"
                s["debut"] = NOBU3_BASE + r[26]
            rows[sid[k]]["scenarios"].append(s)
    for row in rows:
        if any(s["status"] == "未登場" for s in row["scenarios"]):
            row["notes"] += "「未登場」是這邊的寫法：劇本開始時還沒登場，到 debut 那年才以 lord、location 登場。"
    return rows


def _battle_map(hexdata, n, castle):
    cells = hexdata[NOBU3_MAPS + 0x138 * n + (0x9C if castle else 0):][:156]
    im = Image.new("P", (13 * 32, 12 * 32 + 16))
    im.putpalette(PC98_DIGITAL)
    for c, v in enumerate(cells):
        t = v & 0xF if castle else (v & 7) + 11
        raw = bytearray(hexdata[NOBU3_TILES + 0x180 * t:][:0x180])
        if castle and v & 0x10:
            raw[1::3] = bytes(0x80)
        tile = Image.frombytes("P", (32, 32), bytes(genpei.decode_planar(raw, 0, 32, 32, 3)))
        im.paste(tile, (32 * (c % 13), 32 * (c // 13) + (16 if c % 13 & 1 else 0)))
    return im


def world_maps(game_dir):
    """MAPDATA.DAT's four maps as on the screen (416 x 304, lines doubled)."""
    with open(os.path.join(game_dir, "MAPDATA.DAT"), "rb") as f:
        data = f.read()
    maps, pos = [], 0
    while pos < len(data):
        rows, w, h, used = decode_pack(data, pos)
        im = Image.new("P", (w, h))
        im.putpalette(NOBU3_MAP_PALETTE)
        im.putdata([v for row in rows for v in row])
        maps.append(im.resize((w, 2 * h), Image.NEAREST))
        pos += used
    return maps


def _map_points(game_dir, n):
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        exe = f.read()
    base = struct.unpack_from("<H", exe, 8)[0] * 16 + NOBU3_MAP_POINTS + 0x98 * n
    return [struct.unpack_from("<HH", exe, base + 4 * c) for c in range(NOBU3_PROVINCE_COUNT)]


def world_check(game_dir, rows):
    """Every 國 pos is a land pixel of map 0, and flooding the land pixels from it reaches no other 國's pos."""
    im = world_maps(game_dir)[0]
    px, w, h = im.load(), im.width, im.height
    region, checked, bad = {}, 0, []
    for r in rows:
        x, y = r["pos"]["x"], r["pos"]["y"]
        checked += 1
        if not (0 <= x < w and 0 <= y < h) or px[x, y] != 7:
            bad.append(f"{r['id']}: pos {x},{y} is not land")
            continue
        if (x, y) in region:
            bad.append(f"{r['id']}: pos {x},{y} shares a 國 with {region[x, y]}")
            continue
        todo = [(x, y)]
        while todo:
            q = todo.pop()
            if q in region or not (0 <= q[0] < w and 0 <= q[1] < h) or px[q] != 7:
                continue
            region[q] = r["id"]
            todo += [(q[0] + 1, q[1]), (q[0] - 1, q[1]), (q[0], q[1] + 1), (q[0], q[1] - 1)]
    return checked, bad


def places(game_dir, out_dir):
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    for n, im in enumerate(world_maps(game_dir)):
        im.save(os.path.join(out_dir, "world", f"MAPDATA-{n}.png"))
    points = _map_points(game_dir, 0)
    p, d = _read(game_dir, 1), _read(os.path.join(game_dir, "..", "nobu3-dos"), 1)
    with open(os.path.join(game_dir, "HEXDATA.DAT"), "rb") as f:
        hexdata = f.read()
    for kind in ("field", "castle"):
        os.makedirs(os.path.join(out_dir, kind), exist_ok=True)
    rows = []
    for c in range(NOBU3_PROVINCE_COUNT):
        r, q = p[NOBU3_PROVINCES + 41 * c:][:41], d[NOBU3_PROVINCES + 41 * c:][:41]
        ja, zh = _ja(r[2:11]), koei_games.koei_tw_name(q[2:11].split(b"\0")[0])
        row = {"id": c + 1, "name": zh}
        if zh != ja:
            row["nameJa"] = ja
        maps = []
        for kind, role in (("field", "野戰"), ("castle", "攻城")):
            file = f"{kind}/{c + 1:02d}.png"
            _battle_map(hexdata, c, kind == "castle").save(os.path.join(out_dir, file))
            maps.append({"file": file, "role": role})
        row.update({"level": "國", "adjacent": [(b & 0x3F) + 1 for b in r[31:38] if b != 0xFF], "battlemaps": maps,
                    "pos": {"x": points[c][0], "y": points[c][1] * 2, "grid": "pixel", "w": NOBU3_MAP_W,
                            "h": NOBU3_MAP_H},
                    "notes": "國號照遊戲從 1 起算。鄰國的高 2 bit 是進攻方向（布陣區），沒有輸出。沒有地方分類。"
                             "pos 是全國圖 world/MAPDATA-0.png（416×304，沒有國名）上的像素，取自遊戲的座標表"
                             "（MAIN.EXE DS:0x3C5A 第 0 組）；MAPDATA-1、2、3 是遊戲畫面切換的東、中、西三張分圖（有國名），"
                             "同一國在分圖上的位置不同，pos 不適用。"
                             "戰場圖 HEXDATA.DAT 每國一張野戰、一張攻城（打哪一國用那一國的），13×12 格，"
                             "遊戲用 PC-98 數位 8 色；信濃的兩張和遊戲截圖逐點相同（部隊與布陣標記除外）。"})
        rows.append(row)
    return rows
