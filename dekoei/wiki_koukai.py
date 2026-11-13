"""大航海時代 for koei-wiki (koei-persons/1, koei-places/1): dataset koukai-pc98, names from the Chinese DOS version
koukai-dos (the same records in the same order), the Japanese ones in nameJa. Field sources are in
notes/koukai.md「koei-wiki 匯出」.

- Persons: kaodata ids (build_koukai_dos): men 0-40, women 41-61 of SHINARIO.CIM. The game has one start and no
  scenarios, so there is no scenarios field. The kings (portraits 1-3) have no person record and are not listed.
- Places: the 70 ports of SHINARIO.CIM 0x1766 (koukai_extras.ports). MAIN.EXE image 0x134BA draws the port window:
  economy record DS:0xDDC + 18n (SHINARIO.CIM 0xD9A, ports 0-49) +0/+2/+4/+6 u16 経済価値, 経済投資額, 工業価値,
  工業投資額, +8..+10 支持率 of ポルトガル, イスパニア, イスラム (names DS:0x1EA4), +0xB 物価 - 50 (%);
  port record +0x13 & 3 picks 中立港 / ポルトガル同盟港 / イスパニア同盟港 / イスラム同盟港 (DS:0x355C).
"""
import os
import struct

from PIL import Image

import koei_games
import koei_stats
import koukai_extras

DATASET = "koukai-pc98"
ALLIANCE = ["中立港", "ポルトガル同盟港", "イスパニア同盟港", "イスラム同盟港"]
SUPPORT = ["ポルトガル", "イスパニア", "イスラム"]
WORLD_W, WORLD_H = 1008, 504  # world.png: each NEWGAME.DAT map byte as 2 x 2 points; port x, y are in these points


def _dos(game_dir):
    return os.path.join(game_dir, "..", "koukai-dos")


def persons(game_dir):
    shinario = os.path.join(game_dir, "SHINARIO.CIM")
    men, women = koei_games.load_koukai_pc98_people(shinario)
    men_zh, women_zh = koei_games.load_koukai_dos_people(os.path.join(_dos(game_dir), "SHINARIO.CIM"))
    assert len(men) == len(men_zh) == 41 and len(women) == len(women_zh) == 21
    data = open(shinario, "rb").read()
    stats = {row[0]: row for row in koei_stats.load_koukai_stats(shinario, "pc98")}
    off = koei_stats.KOUKAI_MEN_OFFSET["pc98"]
    table = koei_stats.KOUKAI_STAT_TABLE["pc98"]
    rows = []
    for i, ((ja, _, _, nation), (zh, *_)) in enumerate(zip(men, men_zh)):
        m = data[off + i * 20:off + i * 20 + 20]
        row = {"id": i, "name": zh, **({"nameJa": ja} if ja != zh else {})}
        more = {"国籍": koei_stats.KOUKAI_NATIONS[nation], "戦闘Lv": m[0xF], "航海Lv": m[0x10]}
        if i in stats:
            s = stats[i]
            row["stats"] = dict(zip(koei_stats.KOUKAI_STATS[1:6], s[3:8]))
            t = data[table + i * 10:table + i * 10 + 10]
            more = {"年齢": s[2], **more, "戦闘経験": struct.unpack_from("<H", t, 6)[0],
                    "航海経験": struct.unpack_from("<H", t, 8)[0]}
            row["notes"] = "主人公。" if i == 0 else "航海士（可以招為同伴）。"
        else:
            row["notes"] = "沒有能力記錄（遊戲只存 1–20 號航海士與主人公的能力）；他國與海賊艦隊的提督。"
        row["more"] = more
        rows.append(row)
    for i, (ja, zh) in enumerate(zip(women, women_zh)):
        rows.append({"id": 41 + i, "name": zh, **({"nameJa": ja} if ja != zh else {}),
                     "notes": "女性人物，遊戲只存名字（頭像 13＋序號）。"})
    rows[4]["notes"] += "中文名「亞米洯斯」的「洯」沒有和遊戲畫面核對。"
    return rows


def places(game_dir, out_dir):
    cim = open(os.path.join(game_dir, "SHINARIO.CIM"), "rb").read()
    dos = open(os.path.join(_dos(game_dir), "SHINARIO.CIM"), "rb").read()
    world = os.path.join(out_dir, "world")
    os.makedirs(world, exist_ok=True)
    m = koukai_extras.world(open(os.path.join(game_dir, "NEWGAME.DAT"), "rb").read())
    img = Image.new("RGB", (WORLD_W, WORLD_H))
    colours = [tuple(int(c[k:k + 2], 16) for k in (1, 3, 5)) for c in koukai_extras.DIGITAL]
    for y, line in enumerate(m):
        for x, c in enumerate(line):
            img.paste(colours[4] if c == 0 else colours[1] if c <= 3 else colours[3], (x * 2, y * 2, x * 2 + 2, y * 2 + 2))
    img.save(os.path.join(world, "world.png"))

    rows = []
    for i, ja, *_, x, y, flag in koukai_extras.ports(cim):
        zh = koei_games.koei_tw_name(dos[0x1786 + i * 20:0x1786 + i * 20 + 15])
        assert dos[0x1786 + i * 20 + 15:0x1786 + i * 20 + 20] == cim[0x1766 + i * 20 + 15:0x1766 + i * 20 + 20]
        row = {"id": i, "name": zh, **({"nameJa": ja} if ja != zh else {}), "level": "港",
               "pos": {"x": x, "y": y, "grid": "pixel", "w": WORLD_W, "h": WORLD_H}, "uncertain": ["pos"]}
        if i < 50:
            e = cim[0xD9A + i * 18:0xD9A + i * 18 + 18]
            v = struct.unpack_from("<4H", e)
            row["game"] = {"同盟": ALLIANCE[flag & 3], "経済価値": v[0], "経済投資額": v[1], "工業価値": v[2],
                           "工業投資額": v[3], "支持率": dict(zip(SUPPORT, e[8:11])), "物価": e[11] + 50}
            row["notes"] = "值是開局時的；物価是百分比。"
        else:
            row["notes"] = "沒有經濟記錄（50–69 號），所以沒有經濟、同盟、支持率的值。"
        rows.append(row)
    return rows
