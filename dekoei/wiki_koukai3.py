"""大航海時代III for koei-wiki (koei-persons/1, koei-places/1): dataset koukai3-win, the Chinese Windows version
(no Japanese version here, so no nameJa). All addresses are VAs of CDS95.EXE.pec2bac; field sources are in
notes/koukai3.md「koei-wiki 匯出」.

- Persons: kaodata ids = person records 0-245 (VA 0x4FB618, 0xCC bytes). The game has one start and no scenarios,
  and no record is a king or governor (jobs 國王, 總督 are never used by 0-245), so neither is listed.
- Places: the 226 cities (VA 0x4EF150, 0x88 bytes); level 港口 when facility bit 0 (港口) is set, else 城市; region
  is the 文化圈 (city +0x20, names VA 0x552128); pos is the WORLD.CDS cell (2500 x 1250).
"""
import os

from PIL import Image

import koei_games
import koei_stats
import koukai3_extras as kx

DATASET = "koukai3-win"
REGIONS = (0x552128, 11)  # 伊比利亞 ... 美洲; the game asks for 「都市的文化圈」 in the city list
WORLD_W, WORLD_H = 2500, 1250


def _exe(game_dir):
    return kx.Exe(os.path.join(game_dir, kx.EXE))


def _names(exe, table):
    return [exe.text(exe.words(va, 1, "I")[0]) for _, va in exe.records(table)]


def persons(game_dir):
    exe = _exe(game_dir)
    path = os.path.join(game_dir, kx.EXE)
    nations = _names(exe, kx.NATIONS)
    stars, bloods, jobs = exe.strings(kx.STAR_SIGNS), exe.strings(kx.BLOOD_TYPES), exe.strings(kx.JOBS)
    va0, _, size = koei_games.KOUKAI3_WIN_PERSONS
    attrs, skills, langs = koei_stats.KOUKAI3_WIN_ATTRS, koei_stats.KOUKAI3_WIN_SKILLS, koei_stats.KOUKAI3_WIN_LANGUAGES
    rows = []
    for slot, name, *v in koei_stats.load_koukai3_win_stats(path):
        a, (fame, notoriety), sk, lg = v[:6], v[6:8], v[8:21], v[21:35]
        nation, star, blood, job = exe.words(va0 + slot * size + 0x14, 4)
        row = {"id": slot, "name": name, "stats": dict(zip(attrs[:4], a[:4])),
               "more": {"國籍": nations[nation], "職業": jobs[job], "名聲": fame, "惡名": notoriety,
                        "星座": stars[star], "血型": bloods[blood]},
               "hidden": dict(zip(attrs[4:], a[4:]))}
        got = {"技能": {k: x for k, x in zip(skills, sk) if x}, "外語": {k: x for k, x in zip(langs, lg) if x}}
        if any(got.values()):
            row["skills"] = {k: list(d) for k, d in got.items() if d}
            row["game"] = {f"{k}等級": d for k, d in got.items() if d}
        row["uncertain"] = ["more.國籍", "more.職業", "more.星座", "more.血型"]
        rows.append(row)
    return rows


def places(game_dir, out_dir):
    exe = _exe(game_dir)
    nations, goods, cities = _names(exe, kx.NATIONS), _names(exe, kx.GOODS), _names(exe, kx.CITIES)
    regions, conditions = exe.strings(REGIONS), exe.strings(kx.CONDITIONS)
    capitals = {exe.words(va + 8, 1)[0] for _, va in exe.records(kx.NATIONS)}
    world = os.path.join(out_dir, "world")
    os.makedirs(world, exist_ok=True)
    im = Image.new("RGB", (WORLD_W, WORLD_H))
    im.putdata([kx.COLOURS[kx.terrain(c)] for c in kx.load_world(game_dir)])
    im.save(os.path.join(world, "world.png"))

    rows = []
    for i, va in exe.records(kx.CITIES):
        w = exe.words(va, 0x60 // 4)
        bits = exe.words(va + 0x60, 1, "H")[0]
        x, y, zone, region, nation, scale, rate, special, condition = w[1], w[2], w[7], w[8], w[9], w[10], w[11], \
            w[12], w[23]
        game = {"國家": nations[nation], "規模": scale, "行情": rate, "行情區": zone,
                **({"特產品": goods[special]} if 0 <= special < len(goods) else {}),
                "狀況": conditions[condition],
                "設施": [kx.FACILITY_KINDS[k] for k in range(12) if bits >> k & 1]}
        uncertain = ["game.特產品"] if "特產品" in game else []
        if i in capitals:
            game["首都"] = True
            uncertain.append("game.首都")
        row = {"id": i, "name": cities[i], "level": "港口" if bits & 1 else "城市",
               "region": regions[region], "pos": {"x": x, "y": y, "grid": "pixel", "w": WORLD_W, "h": WORLD_H},
               "game": game, **({"uncertain": uncertain} if uncertain else {}),
               "notes": "值是開局時的；行情是百分比；pos 是 WORLD.CDS 的格（world/world.png 一格一點）。"}
        rows.append(row)
    return rows


def world_check(game_dir, rows):
    """Every pos is on a town cell of WORLD.CDS, and every 港口 has sea within 3 cells."""
    cells = kx.load_world(game_dir)
    cls = lambda x, y: kx.terrain(cells[y * WORLD_W + x])
    checked, bad = 0, []
    for r in rows:
        x, y = r["pos"]["x"], r["pos"]["y"]
        checked += 1
        if cls(x, y) != "town":
            bad.append(f"{r['id']}: pos {x},{y} not on a town cell")
        if r["level"] == "港口":
            checked += 1
            if not any(cls(xx, yy) == "sea" for yy in range(max(0, y - 3), min(WORLD_H, y + 4))
                       for xx in range(max(0, x - 3), min(WORLD_W, x + 4))):
                bad.append(f"{r['id']}: port {x},{y} has no sea within 3 cells")
    return checked, bad
