"""信長の野望・武将風雲録 (nobu4-pc98) for koei-wiki: persons (koei-persons/1) and places (koei-places/1). The data
is the PC-98 scenarios; name is the DOS 中文版's (nobu4-dos beside it, byte-identical files apart from the names),
nameJa the PC-98 Japanese. Field sources and how sure they are: notes/nobu4.md「人物欄位」「地理」「koei-wiki 匯出」."""
import os
import struct

from PIL import Image

import genpei
import koei_games
from kaodata_export import NOBU4_DOS_NAME_PICK, NOBU4_PC98_ALIASES
from wiki_nobu3 import PC98_DIGITAL

# SNDATAn.CIM: +1 year - 1476; 48 國 from 0x4 (45 bytes: +4 name 4 bytes, +30 7 neighbours, low 6 bits the 國
# (0-based), FF ends); lords from 0xB90 (32 bytes: +0 the lord's pointer, +31 lord number); persons from 0x1192
# (33 bytes from the surname: +14 born - 1476, +15-19 政治力 戦闘力 教養 魅力 野望, +20 (義理?), +21 u16 face code,
# +23 bits 6-7 寿命 (0-3), +24 bit 4 大名, low 4 bits the 一門 group of the scenario, +26 國, +27 lord number (FF
# 浪人), +28 忠誠度). Pointers minus 0x40 are file offsets of a surname. SNDATAnT.CIM: later arrivals, 28 bytes: +0
# debut - 1476, +1 lord number, +2 國, +3 names, +17 born - 1476, +18-22 the five, +23 (義理?), +24 u16 face code,
# +26 bits 6-7 寿命.
NOBU4_PROVINCES, NOBU4_LORDS, NOBU4_PERSONS, NOBU4_PROVINCE_COUNT = 0x4, 0xB90, 0x1192, 48
# the PC-98 dataset names 松平元康 after his later name (NOBU4_PC98_ALIASES); the Chinese name follows it
NOBU4_ZH_ALIASES = {"松平元康": "德川家康"}
# HEXDATA.DAT battle maps (PC-98 MAIN.EXE image addresses; the DOS file is the same): field maps 20 x 7 from 0
# (140 each), castle 13 x 11 from 7280 (143 each) with a second layer from 31036. Startup (0x3F8E) loads 0x3FC0
# bytes from file 0x397C: 32x32 tiles of 3 interleaved planes (byte k = bit k), 0x180 each. A cell v = byte & 0xF
# draws tile v - 1 (0x1A002-0x1A114), odd columns 16 px lower (0x19C60). "Above" (0x19ED0): the cell above exists
# and is not 0, 0xB or 0xD. Field: 0xB above +4 tiles, 0xD above +1, 0xA right of column 10 +6; there are 3
# weather sets 0xF00 apart ([0x42FC]), set 1 is drawn. Castle: 0 is two 32x16 pieces chosen by the second layer
# (k = low 4 bits, 7 above -> 0x10) through the byte table at DS:0x41FC (image 0x37990 + 0x41FC), piece p at
# NOBU4_PIECES.get(p, 0x3900 + 0xC0 p); 0xD is 0x3600 (+0x180 above). Field cells with v 0 have no tile (drawn as
# plain here). The half cells left open at the top of odd and the bottom of even columns are filled as in
# _battle_map (matched against captures; castle bottom cells next to 0xD still differ).
NOBU4_TILES, NOBU4_PIECE_TABLE = 0x397C, 0x37990 + 0x41FC
# battle screens: the digital 8 colours with white as #FFFFCF (captures/screenshots/nobu4-pc98, guest os_025-028)
NOBU4_BATTLE_PALETTE = PC98_DIGITAL[:21] + [255, 255, 207]
NOBU4_PIECES = {13: 0x3600, 50: 0x480, 100: 0x900, 200: 0x3780}
NOBU4_LABELS = ["政治力", "戦闘力", "教養", "魅力", "野望"]
NOBU4_NOTES = ("義理是 +20 的推定名稱（謙信 253、松永 0），寿命是 0–3 的等級（+23 bit 6–7），都沒讀程式。一門編號（+24 低 4 bit）"
               "只在同一劇本內有效、16 組重複使用，沒有輸出。身分只分得出大名、浪人，城主與軍師沒找到欄位。")


def _read(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return f.read()


def _scenario(game_dir, n):
    """(year, main [(record, offset)], arrivals [record], {lord number: offset of the lord's record})."""
    d = _read(game_dir, f"SNDATA{n}.CIM")
    main = []
    for o in range(NOBU4_PERSONS, len(d) - 32, 33):
        if d[o] < 0x20:  # scenario 2 ends with a record starting 0x01
            break
        main.append((d[o:o + 33], o))
    t = _read(game_dir, f"SNDATA{n}T.CIM")
    arrivals = [t[o:o + 28] for o in range(0, len(t) - 27, 28) if t[o + 3]]
    lords = {}
    for i in range(NOBU4_PROVINCE_COUNT):
        r = d[NOBU4_LORDS + 32 * i:][:32]
        ptr = struct.unpack_from("<H", r)[0]
        if ptr:
            lords[r[31]] = ptr - 0x40
    return 1476 + d[1], main, arrivals, lords


def _zh_names(game_dir):
    """face code -> DOS name, as build_nobu4_dos picks it."""
    out = {}
    for table in koei_games.load_nobu4_dos_people(os.path.join(game_dir, "..", "nobu4-dos")):
        for name, code in table:
            name = NOBU4_DOS_NAME_PICK.get(code, name)
            out.setdefault(code, NOBU4_ZH_ALIASES.get(name, name))
    return out


def persons(game_dir):
    zh = _zh_names(game_dir)
    rows, ids = [], {}

    def person(name, code, born, values, giri, life):
        if code in ids:
            return ids[code]
        ja = NOBU4_PC98_ALIASES.get(name, name)
        row = {"id": len(rows), "name": zh.get(code, ja)}
        if row["name"] != ja:
            row["nameJa"] = ja
        row.update({"born": born, "stats": dict(zip(NOBU4_LABELS, values)), "hidden": {"義理": giri, "寿命": life},
                    "scenarios": [], "uncertain": ["hidden.義理", "hidden.寿命"], "notes": NOBU4_NOTES})
        ids[code] = len(rows)
        rows.append(row)
        return ids[code]

    # ids as build_nobu4_dos(pc98=True): SNDATA1, 1T, 2, 2T, 3, 3T, one person per face code
    names = koei_games.load_nobu4_pc98_people(game_dir)
    scenarios = [_scenario(game_dir, n) for n in (1, 2, 3)]
    for n, (year, main, arrivals, lords) in enumerate(scenarios):
        for (name, code), (r, _) in zip(names[2 * n], main):
            person(name, code, 1476 + r[14], r[15:20], r[20], r[23] >> 6)
        for (name, code), r in zip(names[2 * n + 1], arrivals):
            person(name, code, 1476 + r[17], r[18:23], r[23], r[26] >> 6)
    for n, ((year, main, arrivals, lords), people) in enumerate(zip(scenarios, names[0::2]), 1):
        at = {o: ids[code] for (_, code), (_, o) in zip(people, main)}
        for (_, code), (r, _) in zip(people, main):
            s = {"scenario": n, "year": year}
            if r[27] != 0xFF:
                s["lord"] = at[lords[r[27]]]
            s["location"] = r[26] + 1
            s["status"] = "大名" if r[24] & 0x10 else "浪人" if r[27] == 0xFF else "家臣"
            if r[27] != 0xFF:
                s["loyalty"] = r[28]
            rows[ids[code]]["scenarios"].append(s)
        for (_, code), r in zip(names[2 * n - 1], arrivals):
            row = rows[ids[code]]
            row.setdefault("debut", 1476 + r[0])
            s = {"scenario": n, "year": year, "location": r[2] + 1, "status": "未登場", "debut": 1476 + r[0]}
            if r[1] != 0xFF:
                s["lord"] = at[lords[r[1]]]
            row["scenarios"].append(s)
            if "「未登場」" not in row["notes"]:
                row["notes"] += "「未登場」是這邊的寫法：後登場表（SNDATAnT）的人，到 debut 那年才以 lord、location 登場。"
    return rows


def _battle_map(hexdata, table, n, castle):
    w, h = (13, 11) if castle else (20, 7)
    cells = hexdata[7280 + 143 * n:][:143] if castle else hexdata[140 * n:][:140]
    layer2 = hexdata[31036 + 143 * n:][:143]
    im = Image.new("P", (32 * w, 32 * h + 16))
    im.putpalette(NOBU4_BATTLE_PALETTE)

    def block(off, height):
        px = genpei.decode_planar(hexdata, NOBU4_TILES + off, 32, height, 3)
        return Image.frombytes("P", (32, height), bytes(px))

    for i in range(w * h):
        c, r = i % w, i // w
        v, x, y = cells[i] & 0xF, 32 * c, 32 * r + (16 if c & 1 else 0)
        above = r > 0 and cells[i - w] & 0xF not in (0, 0xB, 0xD)
        if castle and v == 0:
            k = 0x10 if layer2[i] & 0xF == 7 and above else layer2[i] & 0xF
            tile = Image.new("P", (32, 32))
            for half in (0, 1):
                p = table[2 * k + half]
                tile.paste(block(NOBU4_PIECES.get(p, 0x3900 + 0xC0 * p), 16), (0, 16 * half))
        else:
            off = 0x180 * (v - 1)
            if castle and v == 0xD:
                off = 0x3600 + (0x180 if above else 0)
            elif not castle:
                off += (0x600 if v == 0xB and above else 0) + (0x180 if v == 0xD and above else 0) + \
                    (0x900 if v == 0xA and c > 10 else 0)
            tile = block(0x180 * 6 if off < 0 else off, 32)
        im.paste(tile, (x, y))
        # the half cells left open by the odd-column offset: at the top, the lower half of the cell's tile (field)
        # or the upper half of the tile to its left (castle); at the bottom, the upper half of the cell's tile (field 0xD: the
        # plain tile v - 1)
        if c & 1 and r == 0:
            im.paste(left.crop((0, 0, 32, 16)) if castle else tile.crop((0, 16, 32, 32)), (x, 0))
        elif not c & 1 and r == h - 1:
            im.paste(block(0x180 * (v - 1), 16) if v == 0xD and not castle else tile.crop((0, 0, 32, 16)), (x, y + 32))
        left = tile
    return im


def places(game_dir, out_dir):
    p, d = _read(game_dir, "SNDATA1.CIM"), _read(os.path.join(game_dir, "..", "nobu4-dos"), "SNDATA1.CIM")
    hexdata = _read(game_dir, "HEXDATA.DAT")
    exe = _read(game_dir, "MAIN.EXE")
    table = exe[struct.unpack_from("<H", exe, 8)[0] * 16 + NOBU4_PIECE_TABLE:][:34]
    for kind in ("field", "castle"):
        os.makedirs(os.path.join(out_dir, kind), exist_ok=True)
    # map files are named map number + 1: field 01-48 the 國, 50-52 the shared maps 49-51 (route kinds 1-3);
    # castle 01-48 the 國, 49 安土 (近江 under flags)
    for n in list(range(48)) + [49, 50, 51]:
        _battle_map(hexdata, table, n, False).save(os.path.join(out_dir, f"field/{n + 1:02d}.png"))
    for n in range(49):
        _battle_map(hexdata, table, n, True).save(os.path.join(out_dir, f"castle/{n + 1:02d}.png"))
    routes = [[(b & 0x3F, b >> 6) for b in p[NOBU4_PROVINCES + 45 * c + 30:][:7].split(b"\xff")[0]]
              for c in range(NOBU4_PROVINCE_COUNT)]
    users = {}
    for c, rs in enumerate(routes):
        for _, t in rs:
            users.setdefault(t, set()).add(c + 1)
    rows = []
    for c in range(NOBU4_PROVINCE_COUNT):
        r, q = p[NOBU4_PROVINCES + 45 * c:][:45], d[NOBU4_PROVINCES + 45 * c:][:45]
        ja, zh = koei_games.nobu4_pc98_name(r[4:9]), koei_games.nobu4_name(q[4:9])
        row = {"id": c + 1, "name": zh}
        if zh != ja:
            row["nameJa"] = ja
        maps = [{"file": f"castle/{c + 1:02d}.png", "role": "攻城"}]
        if c == 24:
            maps.append({"file": "castle/49.png", "role": "攻城"})
        for a, t in routes[c]:
            m = {"file": f"field/{(c if t == 0 else 48 + t) + 1:02d}.png", "role": "野戰", "from": a + 1}
            if t:
                m["sharedWith"] = sorted(users[t] - {c + 1})
            maps.append(m)
        row.update({"level": "國", "adjacent": [a + 1 for a, _ in routes[c]], "battlemaps": maps,
                    "uncertain": ["battlemaps"],
                    "notes": "國號照遊戲從 1 起算，3 個劇本相同。沒有讀音、地方與大地圖座標。"
                             "戰場圖 HEXDATA.DAT：城圖每國一張（13×11 格）；野戰圖（14×10 格）看攻方從哪一國來，"
                             "守方相鄰表那一格的路線種類是 0 用守方自己那張，1、2、3 用共用的 50、51、52 號圖"
                             "（推定是平地、山地、海上；種類 3 在某個條件下改成不打野戰、直接攻城）。"
                             + ("近江另有安土城圖（castle/49.png），開局後滿足條件才用。" if c == 24 else "")
                             + "類比色盤沒找到，圖是用 PC-98 數位 8 色畫的，顏色不是遊戲畫面的顏色；野戰用天候第 1 組圖塊。"})
        rows.append(row)
    return rows
