"""三國志 (san1-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san1-pc98 id (1-255, the FC order).
Names and readings come from the PC-98 SAVEDATA slot 0 (the PC-98 scenario files are encoded); everything else from
the 5 scenarios of the DOS English SINADATA.DAT (12490 bytes each, the 255 x 32-byte s1_format records at +4326),
whose face codes match the PC-98 persons one by one. Field sources: notes/san1.md「koei-wiki 匯出」,
notes/san-attributes.md「三國志（I，san1）」."""
import os

import kaodata_export as ke
import san1
from places_export import BATTLE, _areas, _save

SCENARIO_SIZE = 12490
# DOS SANMAIN strings (PC-98 SANMAIN.EXE): 君主, 現役武将, 在野武将 (the 「将数」 summary screen)
RULER, SERVING, FREE = "君主", "現役武将", "在野武将"


def _scenarios(game_dir):
    with open(os.path.join(game_dir, "..", "san1-dos", "SINADATA.DAT"), "rb") as f:
        data = f.read()
    out = []
    for k in range(5):
        s = data[k * SCENARIO_SIZE:(k + 1) * SCENARIO_SIZE]
        assert s[0] == k + 1
        year = int.from_bytes(s[8:10], "little")  # 189 195 201 208 215
        out.append((year, [s[san1.DOS_PERSONS + i * 32:][:32] for i in range(255)]))
    return out


def persons(game_dir):
    with open(os.path.join(game_dir, "SAVEDATA"), "rb") as f:
        save = f.read()
    by_id = {i: (name, st) for i, name, st in stats(game_dir)}
    scen = _scenarios(game_dir)
    rows = []
    for i in range(255):
        pid = i + 1
        name, st = by_id[pid]
        rec = save[san1.PC98_PERSONS + i * san1.PC98_PERSON_SIZE:][:san1.PC98_PERSON_SIZE]
        row = {"id": pid, "name": name}
        reading = ke.kana_to_hiragana(rec[:8].split(b"\0")[0].decode("cp932").strip())
        if reading:
            row["reading"] = reading
        # the ruler of each nation in each scenario
        out, first = [], None
        for k, (year, P) in enumerate(scen):
            p = P[i]
            if not p[24]:  # no 國: not on the map in this scenario
                continue
            first = k if first is None else first
            rulers = {q[25]: j + 1 for j, q in enumerate(P) if q[19] & 2}
            s = {"scenario": k + 1, "year": year, "location": p[24]}
            if p[19] & 2:
                s["status"] = RULER
                s["lord"] = pid
            elif p[25]:
                s["status"] = SERVING
                s["lord"] = rulers[p[25]]
                s["loyalty"] = p[18]
            else:
                s["status"] = FREE
            out.append(s)
        if first is not None:
            year, P = scen[first]
            row["born"] = year - P[i][12]
        row["stats"] = st
        if first is not None:
            row["more"] = {"年齢": scen[first][1][i][12]}
        if out:
            row["scenarios"] = out
        if any("loyalty" in x for x in out):
            row["uncertain"] = ["scenarios.loyalty"]
        notes = []
        if first is not None:
            notes.append(f"born 是劇本年減年齢（五個劇本算出來都一樣）；more.年齢取劇本 {first + 1}（第一個登場的劇本）。")
        if not out:
            notes.append("五個劇本開始時都不在地圖上。")
        if ke.yoshikawa_note(row["name"]):
            notes.append(ke.yoshikawa_note(row["name"]))
        if pid in ke.SAN1_PC98_NAME_HISTORICAL:
            notes.append(f"史書寫法 {ke.SAN1_PC98_NAME_HISTORICAL[pid]}。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows


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


# World map (san1.world_map, 320 x 400): PACKDATA block 0 (decrypted, notes/san1.md「磁碟 A 的加密」), each 國 one
# white area with the game's number. SAN1_MAP_POS is the point of each 國 (1-58) farthest from its border; the
# areas were matched to numbers by reading the digit glyphs, and the 5 numbers whose digits touch a border line
# by the adjacency (the only assignment where all 140 game neighbour pairs touch on the map).
SAN1_WORLD, SAN1_MAP_W, SAN1_MAP_H = "PACKDATA-000.png", 320, 400


SAN1_MAP_POS = [(291, 46), (256, 57), (214, 71), (193, 90), (181, 130), (224, 113), (207, 144), (274, 111), (232, 122),
                (239, 166), (253, 171), (225, 138), (173, 176), (160, 77), (115, 96), (157, 103), (146, 112),
                (163, 141), (129, 131), (172, 155), (118, 163), (82, 140), (88, 180), (73, 100), (24, 149), (40, 87),
                (13, 42), (240, 211), (232, 188), (201, 206), (252, 253), (234, 231), (189, 242), (206, 253),
                (225, 301), (189, 285), (155, 211), (132, 204), (171, 236), (111, 228), (158, 254), (132, 256),
                (166, 313), (131, 284), (105, 211), (91, 240), (66, 232), (39, 239), (64, 253), (14, 277), (92, 276),
                (20, 304), (41, 326), (25, 337), (101, 325), (212, 328), (161, 336), (53, 372)]


SAN1_MAP_CORNERS = {(17, 21), (21, 17)}  # meet at one point where 19 joins them; not neighbours in the game


def places(game_dir, out_dir):
    with open(os.path.join(game_dir, "SAVEDATA"), "rb") as f:
        data = f.read()
    shots = os.path.join(game_dir, "..", "..", "captures", "screenshots", "san1-pc98")
    cells = san1.load_san1_pc98_battle_maps(os.path.join(game_dir, "SAVEDATA"))
    tiles = san1.battle_tiles([(san1.np2kai_capture_screen(os.path.join(shots, f)), cells[n - 1])
                               for f, n in SAN1_CAPTURES])
    _save([san1.render_battle_map(c, tiles) for c in cells], out_dir, [f"{n:02d}.png" for n in range(1, 59)])
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    san1.world_map(game_dir).save(os.path.join(out_dir, "world", SAN1_WORLD))
    rows = []
    for n in range(1, 59):
        o = SAN1_PC98_STATES + SAN1_PC98_STATE_SIZE * (n - 1)
        province = [p for p, first in SAN1_PROVINCES if first <= n][-1]
        rows.append({"id": n, "name": None, "level": "國", "province": province,
                     "adjacent": [b for b in data[o:o + 9] if b],
                     "battlemaps": [{"file": f"{n:02d}.png", "role": BATTLE}],
                     "pos": {"x": SAN1_MAP_POS[n - 1][0], "y": SAN1_MAP_POS[n - 1][1], "grid": "pixel",
                             "w": SAN1_MAP_W, "h": SAN1_MAP_H},
                     "uncertain": ["province"],
                     "notes": "國只有號碼。所屬州取自 FC 版的國表（PC-98 的檔裡沒找到），州名寫法也照 FC；"
                              "4 國冀州、10 國徐州和 PC-98 畫面相同。戰場圖的地形圖塊是從 PC-98 截圖切的。"
                              f"pos 是大地圖 world/{SAN1_WORLD}（320×400，遊戲的國號畫在圖上）上這一國白色區塊裡"
                              "離國界最遠的點；PC-88 V1 版的大地圖資料和 PC-98 byte 相同，pos 也適用。"})
    return rows


def world_check(game_dir, rows):
    """Each 國 pos is on a white area of its own, every white area has a 國, and the areas touch (within 4 px)
    exactly as the adjacency says, except the one-point contact SAN1_MAP_CORNERS."""
    im = san1.world_map(game_dir)
    w, h = im.size
    lab = _areas(im, 7)
    area = {lab[r["pos"]["y"] * w + r["pos"]["x"]]: r["id"] for r in rows}
    checked, bad = len(rows), [f"{r['id']}: pos not on a white area" for r in rows
                               if not lab[r["pos"]["y"] * w + r["pos"]["x"]]]
    checked += 1
    if len(area) != len(rows) or len(set(lab) - {0}) != len(rows):
        bad.append(f"{len(area)} 國 on {len(set(lab) - {0})} white areas")
    touch = set()
    for y in range(h):
        for x in range(w):
            a = area.get(lab[y * w + x])
            if a is None:
                continue
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    u, v = x + dx, y + dy
                    b = area.get(lab[v * w + u]) if 0 <= u < w and 0 <= v < h else None
                    if b and b != a and (a, b) not in SAN1_MAP_CORNERS:
                        touch.add((a, b))
    for r in rows:
        checked += 1
        if sorted(b for a, b in touch if a == r["id"]) != sorted(r["adjacent"]):
            bad.append(f"{r['id']}: map neighbours differ from adjacent")
    return checked, bad


# 三國志 (I) PC-98: the scenario files are encoded and SAVEDATA is a game in progress (its values have moved: 劉備 知力
# 100), so the values are the DOS SINADATA.DAT scenario 1 ones: 255 x 32-byte records from 4326 (s1_format), 身体 知力
# 武力 カリスマ 運勢 at +13-17. Same person order and face codes as PC-98 (255/255), the same values in all 5 scenarios,
# and they match the PC-98 ruler screen (status-screens/san1-pc98-cap-01.png, 8 rulers)
SAN1_STATS = ["身体", "知力", "武力", "カリスマ", "運勢"]


def stats(game_dir, dos_dir=None):
    dos_dir = dos_dir or os.path.join(game_dir, "..", "san1-dos")
    with open(os.path.join(dos_dir, "SINADATA.DAT"), "rb") as f:
        data = f.read()
    pc98 = san1.load_san1_pc98_persons(os.path.join(game_dir, "SAVEDATA"))
    dos = san1.load_san1_dos_persons(os.path.join(dos_dir, "SINADATA.DAT"))
    out = []
    for i, ((code, name), (dos_code, _)) in enumerate(zip(pc98, dos)):
        assert code == dos_code
        rec = data[san1.DOS_PERSONS + i * 32:san1.DOS_PERSONS + (i + 1) * 32]
        out.append((i + 1, name, dict(zip(SAN1_STATS, rec[13:18]))))
    return out
