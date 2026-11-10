"""項劉記 (DOS, Chinese): the 39 places and the world map, written under --out (notes/kouryuuki.md「地點與地圖」).

- MAIN.EXE (PKLITE; offsets in the unpacked image, DGROUP at 0x3A870):
  - Places: 39 records of 19 bytes at DGROUP 0x4168: +0 name (6 bytes, KOEI Taiwan code), +17 u16 cell
    (x = cell % 55, y = cell // 55). The PC-98 MAIN.EXE has the same table at file 0x47628 with a Shift-JIS name
    and a half-width kana reading at +7.
  - Palettes: DGROUP 0x5E5A, 4 x 16 colours of 4-bit B, R, G; season n = min((month - 1) // 3, 3) (0x53FB).
- SNDTn.KR1: 55 x 44 u16 cells from 0x39C; high byte & 0xF = terrain / place code, high byte >> 4 = map
  overlay (< 13 is drawn, 0x77EF).
- MAP.KR1: 88 rows x 165 bytes, one 16 x 16 tile per byte, a cell is 3 x 2 tiles (48 x 32 pixels) (0x5493).
- GRP4.KR1 (loaded after MAP.KR1 in the same segment), every picture in rows of 4-byte groups (planes 0-3 of
  8 pixels, bit 7 leftmost):
  - 0x0000: 10 place pictures of 48 x 32 (0x300 bytes), picked by place code, colour 0 transparent (0x55B9).
  - 0x1E00: 246 tiles of 16 x 16 (128 bytes) for map bytes 10-255; bytes below 10 use tile 0 (0x5527).
  - 0x9900: 13 overlays of 48 x 32, colour 0 transparent (0x558E).
"""
import csv
import os
from collections import deque

import click
from PIL import Image

import pklite
from koei_games import koei_tw_name

W, H = 55, 44
DGROUP = 0x3A870
PLACES = DGROUP + 0x4168
PALETTES = DGROUP + 0x5E5A
PC98_PLACES = 0x47628
PC98_GAIJI = {0xEBE9: "陘", 0xEBD6: "淄", 0xEBE7: "滎", 0xEBEB: "睢", 0xEBC6: "翟", 0xEBEC: "盱", 0xEBDF: "眙",
              0xEBEA: "邾"}
SEASONS = ["spring", "summer", "autumn", "winter"]
PASSABLE = (10, 11)


def _csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def grid(game_dir, n):
    s = open(os.path.join(game_dir, f"SNDT{n}.KR1"), "rb").read()
    return [int.from_bytes(s[0x39C + 2 * i:0x39C + 2 * i + 2], "little") for i in range(W * H)]


def pc98_names(path):
    exe = open(path, "rb").read()
    out = []
    for i in range(39):
        r = exe[PC98_PLACES + i * 19:PC98_PLACES + i * 19 + 19]
        raw, name = r[:6].split(b"\0")[0], ""
        for j in range(0, len(raw), 2):
            code = int.from_bytes(raw[j:j + 2], "big")
            name += PC98_GAIJI.get(code) or raw[j:j + 2].decode("cp932")
        out.append((name, r[7:14].split(b"\0")[0].decode("cp932")))
    return out


def adjacency(cells, codes):
    """Places whose regions touch, growing every place at once over passable cells (a guess, the game has no
    adjacency table)."""
    owner = {c: i for i, c in enumerate(cells)}
    q = deque(cells)
    while q:
        c = q.popleft()
        x, y = c % W, c // W
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            n = ny * W + nx
            if 0 <= nx < W and 0 <= ny < H and n not in owner and codes[n] in PASSABLE:
                owner[n] = owner[c]
                q.append(n)
    adj = [set() for _ in cells]
    for c, i in owner.items():
        x, y = c % W, c // W
        for nx, ny in ((x + 1, y), (x, y + 1)):
            j = owner.get(ny * W + nx) if nx < W and ny < H else None
            if j is not None and j != i:
                adj[i].add(j)
                adj[j].add(i)
    return [sorted(a) for a in adj]


def places(game_dir, pc98_dir, img, out):
    grids = [grid(game_dir, n) for n in range(1, 5)]
    codes = [[(v >> 8) & 0xF for v in g] for g in grids]
    rows = []
    for i in range(39):
        r = img[PLACES + i * 19:PLACES + i * 19 + 19]
        rows.append((i, koei_tw_name(r[:6]), int.from_bytes(r[17:19], "little"), r[14:17]))
    cells = [r[2] for r in rows]
    adj = adjacency(cells, codes[0])
    ja = pc98_names(os.path.join(pc98_dir, "MAIN.EXE")) if pc98_dir else [("", "")] * 39
    out_rows = []
    for (i, zh, cell, raw), (name_ja, kana), a in zip(rows, ja, adj):
        sc = [c[cell] for c in codes]
        out_rows.append((i, zh, name_ja, kana, "関" if sc[0] == 4 else "城", cell % W, cell // W, *sc,
                         raw.hex(" "), " ".join(rows[j][1] for j in a)))
    _csv(f"{out}/places.csv", ["id", "name_zh", "name_ja", "kana", "kind", "x", "y", "code_s1", "code_s2",
                               "code_s3", "code_s4", "raw_14_16", "adjacent_guess"], out_rows)
    return rows, grids[0]


def palette(img, season):
    p = img[PALETTES + season * 0x30:PALETTES + season * 0x30 + 0x30]
    pal = []
    for i in range(16):
        b, r, g = (v << 2 for v in p[i * 3:i * 3 + 3])
        pal += [(r << 2) | (r >> 4), (g << 2) | (g >> 4), (b << 2) | (b >> 4)]
    return pal


def world_map(game_dir, cells_grid, img, out, rows):
    g = open(os.path.join(game_dir, "GRP4.KR1"), "rb").read()
    m = open(os.path.join(game_dir, "MAP.KR1"), "rb").read()
    im = Image.new("P", (W * 48, H * 32))
    px = im.load()

    def blit(o, w, h, X, Y, mask):
        for r in range(h):
            for c in range(w):
                b = g[o + (r * w + c) * 4:o + (r * w + c) * 4 + 4]
                for x in range(8):
                    v = sum(((b[q] >> (7 - x)) & 1) << q for q in range(4))
                    if v or not mask:
                        px[X + c * 8 + x, Y + r] = v

    for ty in range(H * 2):
        for tx in range(W * 3):
            blit(0x1E00 + max(m[ty * 165 + tx] - 10, 0) * 128, 2, 16, tx * 16, ty * 16, False)
    for c, v in enumerate(cells_grid):
        x, y = c % W * 48, c // W * 32
        if v >> 12 < 13:
            blit(0x9900 + (v >> 12) * 0x300, 6, 32, x, y, True)
        if (v >> 8) & 0xF < 10:
            blit(((v >> 8) & 0xF) * 0x300, 6, 32, x, y, True)
    os.makedirs(f"{out}/map", exist_ok=True)
    for s, name in enumerate(SEASONS):
        im.putpalette(palette(img, s))
        im.convert("RGB").save(f"{out}/map/world_{name}.png")
    im.putpalette(palette(img, 0))
    im.convert("RGB").save(f"{out}/map/world.png")

    from places_export import label_world_map
    labelled = label_world_map(f"{out}/map/world.png",
                               [{"id": i, "name": zh, "pos": {"x": cell % W * 48 + 24, "y": cell // W * 32 + 16}}
                                for i, zh, cell, _ in rows], 24)
    labelled.save(f"{out}/map/world_places.png")


@click.command("kouryuuki-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="game files (games/kouryuuki-dos)")
@click.option("--pc98-dir", type=click.Path(), default=None,
              help="PC-98 files for the Japanese names (default: ../kouryuuki-pc98 next to --game-dir, if present)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/kouryuuki-dos/extract)")
def kouryuuki_extras(game_dir, pc98_dir, out):
    """項劉記 (DOS): the 39 places (with PC-98 names) and the world map in four seasons."""
    if pc98_dir is None:
        guess = os.path.join(os.path.dirname(os.path.abspath(game_dir)), "kouryuuki-pc98")
        pc98_dir = guess if os.path.exists(os.path.join(guess, "MAIN.EXE")) else None
    img = pklite.depklite(open(os.path.join(game_dir, "MAIN.EXE"), "rb").read())
    rows, g1 = places(game_dir, pc98_dir, img, out)
    world_map(game_dir, g1, img, out, rows)
    click.echo(f"{len(rows)} places, world map {W * 48}x{H * 32} in 4 seasons -> {out}")


if __name__ == "__main__":
    kouryuuki_extras()
