"""信長の野望・全国版 DOS 英文版 (nobu2-dos) for koei-wiki: places (koei-places/1) with the 50 battle maps.

The 國 table is the PC-88 one (games/nobu2-dos/PC88_DISK_A.D88, as build_nobu2_dos does for the names; the DOS
MAIN.EXE 50-國 neighbour table is byte-identical, notes/nobu2.md「地理」); the English names are DATA50N.DAT 0x3A
(14 bytes each). The battle maps are HEXMAP.50 (11 x 5 cells, one map per 國) drawn with hex tiles cut from DOS
screenshots (captures/screenshots/nobu2-dos, see index.md there): the tiles were not found in the game files.
Where the tiles come from and how they were checked: notes/nobu2.md「戰場」."""
import os
from collections import Counter

from PIL import Image

import wiki_nobu2

CAPTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "captures", "screenshots", "nobu2-dos")
# (capture, map number, cells covered by units or the cursor): 尾張 before deployment, 下野 during an AI battle
# (castle and town covered), 伊勢志摩 before deployment (the only one with 場外 cells)
TILE_SOURCES = [("main_001.png", 24, ""), ("main_025.png", 0, "")] + \
    [(f"main_0{n}.png", 11, "3,5;1,5") for n in range(18, 24)] + \
    [("main_030.png", 25, "0,5;1,4;1,5;1,6;2,3;2,4;2,6;3,3;3,4;3,5;1,7;2,8;2,9;3,9;0,8;1,8;2,7")]
# hex layout of the 640x400 screen: cell (0, 0) centred at (215, 32), columns 40 apart, rows 64, odd columns 32
# lower; the map area starts at x 192. A cell's hexagon has its top and bottom edges 16 px from the centre
# column (A) and its side corners 24 px (40 - A).
X0, Y0, DX, DY, LEFT, A, EDGE = 215, 32, 40, 64, 192, 16, 0.1
COLS, ROWS, WIDTH, HEIGHT = 11, 5, 448, 352
NAMES_EN = 0x3A


def _centre(r, c):
    return X0 + DX * c, Y0 + DY * r + (DY // 2 if c & 1 else 0)


def _owners():
    """screen pixel -> the cell whose hexagon holds it; pixels on the map border go to the map cell"""
    owners = {}
    for x in range(LEFT, LEFT + WIDTH):
        for y in range(HEIGHT):
            best = None
            c0, r0 = (x - X0 + DX // 2) // DX, (y - Y0) // DY
            for c in range(c0 - 1, c0 + 2):
                for r in range(r0 - 1, r0 + 2):
                    cx, cy = _centre(r, c)
                    ady, adx = abs(y - cy), abs(x - cx)
                    d = max(ady / 32, adx / ((DX - A) - (DX - 2 * A) * min(ady, 32) / 32))
                    if 0 <= r < ROWS and 0 <= c < COLS:
                        d -= EDGE
                    if best is None or d < best[0]:
                        best = (d, r, c)
            if 0 <= best[1] < ROWS and 0 <= best[2] < COLS:
                owners[x, y] = best[1], best[2]
    return owners


def _tiles(hexmap, owners):
    """terrain code -> {(dx, dy) from the cell centre: colour}, the most common colour over all source cells"""
    votes = {}
    for name, n, skip in TILE_SOURCES:
        skip = {tuple(map(int, s.split(","))) for s in skip.split(";") if s}
        px = Image.open(os.path.join(CAPTURES, name)).convert("RGB").load()
        for (x, y), (r, c) in owners.items():
            if (r, c) not in skip:
                cx, cy = _centre(r, c)
                votes.setdefault(hexmap[55 * n + 11 * r + c], {}).setdefault((x - cx, y - cy), Counter())[px[x, y]] += 1
    return {code: {k: v.most_common(1)[0][0] for k, v in d.items()} for code, d in votes.items()}


def battle_maps(game_dir):
    with open(os.path.join(game_dir, "HEXMAP.50"), "rb") as f:
        hexmap = f.read()
    owners = _owners()
    tiles = _tiles(hexmap, owners)
    maps = []
    for n in range(50):
        im = Image.new("RGB", (WIDTH, HEIGHT))
        px = im.load()
        for (x, y), (r, c) in owners.items():
            cx, cy = _centre(r, c)
            px[x - LEFT, y] = tiles[hexmap[55 * n + 11 * r + c]].get((x - cx, y - cy), (0, 0, 0))
        maps.append(im)
    return maps


def places(game_dir, out_dir):
    rows = wiki_nobu2.places(game_dir, out_dir, disk="PC88_DISK_A.D88")
    with open(os.path.join(game_dir, "DATA50N.DAT"), "rb") as f:
        data50n = f.read()
    regions = wiki_nobu2._disk(game_dir, "PC88_DISK_A.D88")["DATA50N.DAT"][wiki_nobu2.NOBU2_REGIONS:]
    os.makedirs(out_dir, exist_ok=True)
    for k, im in enumerate(battle_maps(game_dir)):
        im.save(os.path.join(out_dir, f"{k + 1:02d}.png"))
    for k, row in enumerate(rows):
        en = data50n[NAMES_EN + 14 * k:][:14].split(b"\0")[0].decode("ascii")
        row["battlemaps"] = [{"file": f"{k + 1:02d}.png", "role": "戰場"}]
        row["notes"] = (f"DOS 英文版，遊戲裡寫「{en}」；name 用 PC-88 版的漢字（同 kaodata 的 nobu2-dos）。"
                        f"地方號 {regions[k]}（1–7，東北到九州）。"
                        "這是 50 國劇本的國，17 國劇本另有一組國，沒有匯出。戰場圖是 HEXMAP.50 的那一國（打哪一國用那一國的圖），"
                        "11×5 格，圖塊從 DOS 版截圖切出（EGA 16 色）：尾張、蝦夷、伊勢志摩三張和截圖比對，除了部隊所在的格子與"
                        "地圖外框的線條，逐點相同。DOS 版是重畫的美術，和 PC-88 版的畫面不同。")
    return rows
