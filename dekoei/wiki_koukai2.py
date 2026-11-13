"""大航海時代II for koei-wiki (koei-persons/1, koei-places/1): dataset koukai2-pc98 (Japanese only, no Chinese
version). Field sources are in notes/koukai2.md「koei-wiki 匯出」.

- Persons: kaodata ids (build_koukai2_pc98): mates 0-119, event people 120-139, tavern women 140-169 of DATA1.LZW
  part 15 (the start state). The six heroes share this one start state, so there is no scenarios field; the start
  port of a mate (+45) and of a tavern woman (+0xE, MAIN.EXE image 0x26A5B compares it with the current port) is
  game.所在港. The faces only drawn by the scenario scripts (KOUKAI2_PC98_EVENT_FACES) have no person id and are not
  listed.
- Places: the 130 ports of 0x52B0 (100-129 are 補給港). MAIN.EXE image 0x7AFD draws the port window title: port
  state +0x21 picks MESSAGE.DAT 0x181 + n followed by「地方」, a supply port shows「補給港」instead.
"""
import os
import struct

from PIL import Image

import koei_games
import koukai2_extras as x
from koei_stats import KOUKAI2_NATIONS, KOUKAI2_SKILLS, KOUKAI2_STATS
from ls11 import ls11_decode_parts

DATASET = "koukai2-pc98"
WORLD_W, WORLD_H = 2160, 1080  # WORLDMAP.LZW cells; port +0 / +2 are in these cells
KINGS = range(130, 136)  # event records in the order of the nation table (DS:0x8B0)


def _state(game_dir):
    return ls11_decode_parts(open(os.path.join(game_dir, "DATA1.LZW"), "rb").read())[15]


def _port_names(st):
    return [x.cstr(st[x.II_LAYOUT["ports"] + 22 * k + 4:][:17]) for k in range(x.N_PORTS)]


def persons(game_dir):
    st = _state(game_dir)
    exe = open(os.path.join(game_dir, "MAIN.EXE"), "rb").read()
    ranks = x.ds_strings(exe, 0x8A2, 7)
    ports = _port_names(st)
    mates, events, tavern = koei_games.load_koukai2_pc98_people(os.path.join(game_dir, "DATA1.LZW"))
    start, _, size = koei_games.KOUKAI2_PC98_MATES
    rows = []
    for i, (name, _, _) in enumerate(mates):
        r = st[start + i * size:][:size]
        o = 28
        row = {"id": i, "name": name, "stats": dict(zip(KOUKAI2_STATS[:7], r[o:o + 7]))}
        more = {"年齢": r[42], "国籍": KOUKAI2_NATIONS[r[49] & 0xF], "航海Lv": r[36],
                "航海経験": struct.unpack_from("<H", r, 38)[0], "戦闘Lv": r[37],
                "戦闘経験": struct.unpack_from("<H", r, 40)[0]}
        if r[46]:
            more["役職"] = ranks[r[46]]
        row["more"] = more
        skills = [n for k, n in enumerate(KOUKAI2_SKILLS) if r[48] & (0x10 >> k)]
        if skills:
            row["skills"] = {"技能": skills}
        row["hidden"] = {"運": r[35], "忠誠": r[43]}
        if r[45] != 0xFF:
            row["game"] = {"所在港": ports[r[45]]}
        row["uncertain"] = ["hidden.運", "hidden.忠誠"]
        row["notes"] = ("主人公（六人中選一人玩）。" if i < 6 else
                        "艦隊提督（開局時率領艦隊）。" if r[46] == 1 else "航海士（可以在酒館招為同伴）。")
        rows.append(row)
    for k, (name, _) in enumerate(events):
        i = 120 + k
        row = {"id": i, "name": name}
        if i in KINGS:
            row["more"] = {"国籍": KOUKAI2_NATIONS[i - 130]}
            row["uncertain"] = ["more.国籍"]
            row["notes"] = "國王或總督。國籍是推定：事件人物表 130–135 號的順序和國名表相同。"
        else:
            row["notes"] = "事件人物，遊戲只存名字和頭像。"
        rows.append(row)
    t0, _, tsize = koei_games.KOUKAI2_PC98_TAVERN
    for k, (name, _) in enumerate(tavern):
        r = st[t0 + k * tsize:][:tsize]
        rows.append({"id": 140 + k, "name": name, "game": {"所在港": ports[r[0xE]]},
                     "notes": "酒館女性，遊戲只存名字和所在港。"})
    return rows


def places(game_dir, out_dir):
    st = _state(game_dir)
    lb = x.ii_labels(game_dir)
    world = os.path.join(out_dir, "world")
    os.makedirs(world, exist_ok=True)
    g, _ = x.world(ls11_decode_parts(open(os.path.join(game_dir, "WORLDMAP.LZW"), "rb").read()))
    img = Image.new("RGB", (WORLD_W, WORLD_H))
    img.putdata([(40, 70, 140) if v else (120, 160, 90) for line in g for v in line])
    img.save(os.path.join(world, "world.png"))

    rows = []
    for k, name in enumerate(_port_names(st)):
        o = x.II_LAYOUT["ports"] + 22 * k
        px, py = struct.unpack_from("<HH", st, o)
        nation = st[o + 0x15] & 7
        row = {"id": k, "name": name, "level": "港" if k < x.N_REAL_PORTS else "補給港",
               "pos": {"x": px, "y": py, "grid": "pixel", "w": WORLD_W, "h": WORLD_H}}
        game = {}
        if nation < 6:
            game["同盟"] = lb.nations[nation]
        if k < x.N_REAL_PORTS:
            s = st[x.II_LAYOUT["port_state"] + 37 * k:][:37]
            row["region"] = lb.markets[s[33]]
            game.update({"商業価値": struct.unpack_from("<H", s, 0)[0], "工業価値": struct.unpack_from("<H", s, 4)[0],
                         "支持率": dict(zip(lb.nations[:6], s[8:14]))})
            row["uncertain"] = ["game.工業価値", "game.支持率"]
            row["notes"] = "值是開局時的。"
        else:
            row["notes"] = "補給港：沒有港口狀態記錄，遊戲不顯示地方。"
        if game:
            row["game"] = game
        rows.append(row)
    return rows
