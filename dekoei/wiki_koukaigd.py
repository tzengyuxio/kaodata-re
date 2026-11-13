"""大航海時代外傳 for koei-wiki (koei-persons/1, koei-places/1): dataset koukaigd-win, the Chinese Windows version
(no Japanese version here, so no nameJa). Field sources are in notes/koukaigd.md「koei-wiki 匯出」.

- Persons: kaodata ids in the order build_koukaigd_win makes them: the two protagonists, the mates of both
  koukaiGD.exe tables (same name kept once), the 20 Sdata.dat event people, the six 大航海時代II heroes (script only),
  the 30 tavern women, and the two records after the event table. The game has two starts, one per protagonist,
  each with its own mate table (0x416190 copies table [0x4BFDA1]); scenarios 1 and 2 are those starts.
- Places: the 130 ports of Sdata.dat 0x6BCD (100-129 are 補給港); the port window prints "%s港" or 補給港 and the
  market name with 地區 (exe file 0x75E1C). Worldmap.lzw is byte-identical to 大航海時代II's.
"""
import os
import struct

from PIL import Image

import koei_games as kg
import koukai2_extras as x
from kaodata_export import KOUKAIGD_WIN_EXTRA_FACES, KOUKAIGD_WIN_II_HEROES
from koei_stats import KOUKAIGD_NATIONS, KOUKAIGD_SKILLS, KOUKAIGD_STATS
from koukaigd_extras import GD_LAYOUT, fixed, gd_labels
from ls11 import ls11_decode_parts

DATASET = "koukaigd-win"
WORLD_W, WORLD_H = 2160, 1080  # Worldmap.lzw cells (= 大航海時代II); port +0 / +2 are in these cells
RANKS = (0x59FC8, 11, 7)  # exe file offset of the 職位 names: (none) 提督 船長 助手 會計 水手長 航海士
KINGS = range(10, 16)  # event records 10-15 (瑪努埃爾1世 ... 耐普爾總督) follow the nation table
PROTAGONISTS = ("米蘭塔", "薩爾巴多爾")


def _read(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return f.read()


def _port_names(sd):
    return [x.cstr(sd[GD_LAYOUT["ports"] + 22 * k + 4:][:17], "big5") for k in range(x.N_PORTS)]


def _mate(r, ranks):
    """Fields of a 27-byte mate record (大航海時代II's record without the names, offsets - 24)."""
    stats = dict(zip(KOUKAIGD_STATS[:7], r[4:11]))
    more = {"年齡": r[18], "國籍": KOUKAIGD_NATIONS[r[25] & 0xF], "航海水平": r[12],
            "航海經驗": struct.unpack_from("<H", r, 14)[0], "戰鬥水平": r[13],
            "戰鬥經驗": struct.unpack_from("<H", r, 16)[0]}
    if r[0x16]:
        more["職位"] = ranks[r[0x16]]
    skills = [n for k, n in enumerate(KOUKAIGD_SKILLS) if r[24] & (0x10 >> k)]
    return stats, more, skills, {"運氣": r[0xB], "忠誠": r[0x13]}


def persons(game_dir):
    exe, sd = _read(game_dir, "koukaiGD.exe"), _read(game_dir, "Sdata.dat")
    ranks = fixed(exe, *RANKS)
    ports = _port_names(sd)
    names = kg.load_koukaigd_win_mates(os.path.join(game_dir, "koukaiGD.exe"))
    recs = [[exe[start + s * 27:][:27] for s in range(120)] for start in kg.KOUKAIGD_WIN_MATES]

    # every mate name -> {table: record}; protagonist t is the empty slot t of table t, named in the other table
    by_name = {}
    for t in (0, 1):
        for s, (name, _) in enumerate(names[t]):
            if name is not None:
                by_name.setdefault(name, {})[t] = recs[t][s]
    heroes = [names[1 - t][t][0] for t in (0, 1)]
    for t, name in enumerate(heroes):
        by_name[name][t] = recs[t][t]

    rows = []

    def mate_row(name, hero=None):
        tables = by_name[name]
        stats, more, skills, hidden = _mate(tables[hero if hero is not None else min(tables)], ranks)
        row = {"id": len(rows), "name": name, "stats": stats, "more": more}
        if skills:
            row["skills"] = {"技能": skills}
        row["hidden"] = hidden
        scen = []
        for t in sorted(tables):
            r = tables[t]
            s = {"scenario": t + 1}
            if t != hero:
                if r[0x16]:
                    s["status"] = ranks[r[0x16]]
                if r[0x15] != 0xFF:
                    s["location"] = r[0x15]
            scen.append(s)
        row["scenarios"] = scen
        row["uncertain"] = ["hidden.運氣", "hidden.忠誠"]
        notes = ["scenario 1、2 是選米蘭塔、薩爾巴多爾開局時的狀態（兩人各用一張航海士表）；location 是開局時在酒館的港口。"]
        if hero is not None:
            notes.append(f"主角：劇本 {hero + 1} 由玩家操作，頂層的值取玩家記錄；"
                         f"劇本 {2 - hero} 是另一位主角的航海士。")
        elif len(tables) == 1:
            notes.append(f"只在劇本 {min(tables) + 1} 的航海士表裡。")
        elif tables[0] != tables[1]:
            notes.append("兩個劇本的記錄不同，頂層的值取劇本 1。")
        row["notes"] = "".join(notes)
        rows.append(row)

    seen = set()
    for t, name in enumerate(heroes):
        mate_row(name, hero=t)
        seen.add(name)
    for t in (0, 1):
        for name, _ in names[t]:
            if name is not None and name not in seen:
                seen.add(name)
                mate_row(name)

    for k, (name, _) in enumerate(kg.load_koukaigd_win_events(os.path.join(game_dir, "Sdata.dat"))):
        row = {"id": len(rows), "name": name}
        if k in KINGS:
            row["more"] = {"國籍": KOUKAIGD_NATIONS[k - KINGS[0]]}
            row["uncertain"] = ["more.國籍"]
            row["notes"] = "國王或總督。國籍是推定：事件人物表 10–15 號的順序和國名表相同（大航海時代II 同）。"
        else:
            row["notes"] = "事件人物，遊戲只存名字和頭像。"
        rows.append(row)
    for name in KOUKAIGD_WIN_II_HEROES:
        rows.append({"id": len(rows), "name": name,
                     "notes": "大航海時代II 的主角，外傳只在劇本事件登場，沒有人物記錄；名字取劇本對白（Snr1.mes、Snr2.mes）的發言人。"})
    t0, count, size = kg.KOUKAIGD_WIN_TAVERN
    for k, (name, _) in enumerate(kg.load_koukaigd_win_tavern(os.path.join(game_dir, "Sdata.dat"))):
        r = sd[t0 + k * size:][:size]
        rows.append({"id": len(rows), "name": name, "more": {"年齡": r[13]}, "game": {"所在港": ports[r[14]]},
                     "uncertain": ["more.年齡"], "notes": "酒館女性，遊戲存名字、年齡和所在港。"})
    for name, _ in kg.load_koukaigd_win_events(os.path.join(game_dir, "Sdata.dat"), extra=True):
        rows.append({"id": len(rows), "name": name,
                     "notes": f"事件人物表後的一筆，只存名字；頭像取劇本用的 {KOUKAIGD_WIN_EXTRA_FACES[name]}。"})
    return rows


def places(game_dir, out_dir):
    exe, sd = _read(game_dir, "koukaiGD.exe"), _read(game_dir, "Sdata.dat")
    lb = gd_labels(exe)
    world = os.path.join(out_dir, "world")
    os.makedirs(world, exist_ok=True)
    g, _ = x.world(ls11_decode_parts(_read(game_dir, "Worldmap.lzw")))
    img = Image.new("RGB", (WORLD_W, WORLD_H))
    img.putdata([(40, 70, 140) if v else (120, 160, 90) for line in g for v in line])
    img.save(os.path.join(world, "world.png"))

    rows = []
    for k, name in enumerate(_port_names(sd)):
        o = GD_LAYOUT["ports"] + 22 * k
        px, py = struct.unpack_from("<HH", sd, o)
        nation = sd[o + 0x15] & 7
        row = {"id": k, "name": name, "level": "港" if k < x.N_REAL_PORTS else "補給港",
               "pos": {"x": px, "y": py, "grid": "pixel", "w": WORLD_W, "h": WORLD_H}}
        game = {}
        if nation < 6:
            game["同盟"] = lb.nations[nation]
        if k < x.N_REAL_PORTS:
            s = sd[GD_LAYOUT["port_state"] + GD_LAYOUT["port_state_size"] * k:][:GD_LAYOUT["port_state_size"]]
            row["region"] = lb.markets[s[33]]
            game.update({"商業價值": struct.unpack_from("<H", s, 0)[0], "工業價值": struct.unpack_from("<H", s, 4)[0],
                         "支持度": dict(zip(lb.nations[:6], s[8:14]))})
            row["uncertain"] = ["game.商業價值", "game.工業價值", "game.支持度"]
            row["notes"] = "值是開局時的（兩位主角的開局相同）。"
        else:
            row["notes"] = "補給港：沒有港口狀態記錄。"
        if game:
            row["game"] = game
        rows.append(row)
    return rows
