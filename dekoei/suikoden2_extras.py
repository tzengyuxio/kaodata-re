"""水滸傳 天導108星 (SUIKO2.EXE, Win 中文版): faces, pictures, sprites, ground textures and the 41 州 maps, written
under --out (notes/suikoden2.md). Addresses are SUIKO2.EXE VAs.

- Palette: RT_RCDATA 117 (file offset 0x12F388), 256 triples stored B,R,G; colour 0 is the green key.
- Picture files (LS11): b"\\x2a\\x38", u16 width, u16 height, 8bpp pixels. KAO 368 faces 216x160, KAOBACK 45
  backgrounds 344x160, CG 22, EVENT 19, ITEM 49.
- Table files (IMAGE.SK2, BGIMAGE.SK2, PATSEQ.SK2 is different): u32 N, N+1 u32 offsets, item k (1-based) is
  data[off[k-1]:off[k]] (0x4d69b0, 0x4478f0). IMAGE: 4006 sprites; BGIMAGE: 79 raw 64x64 ground textures.
- Sprite: s16 x0, s16 y0, u16 w, u16 h (box around the hotspot), then records {u16 len, s16 dx, s16 dy, len pixels};
  dx, dy move the start relative to the previous record, starting from the hotspot; len 0 ends.
- CHIKEI%02d.SK2 (scenarios 1-3): 0xC3-byte parameter header (0x460590), then 41 records of 12112 bytes: u16 州 id,
  7 u16 州 state values, 63 rows x 32 cells x 6 bytes (0x4608f0). The map drawing below follows 0x448160 (vertex
  grid), 0x449b60 (heights), 0x449ae0 (shading), 0x44aa30 (texture), 0x44a6d0 (projection), 0x44ab20/0x44af20
  (triangles), 0x449190 (fill) and 0x4d9740/0x44bd00 (facility and tree sprites); see the notes for what is
  inferred.
"""
import csv
import math
import os
import struct

import click
from PIL import Image

from ls11 import ls11_decode_parts

PALETTE = 0x12F388  # RT_RCDATA 117
PICTURES = ["KAO", "KAOBACK", "CG", "EVENT", "ITEM"]
COLS = 32               # 州 width (CMNDATA); all 41 are 32
W = H = 2 * COLS + 1    # vertex grid (0x448160)
ROWS = 2 * COLS - 1     # 0x4b49c0
RECORD = 12112
# cell type (b0) -> BGPAT category (vtable +0x84 of each cell class, 0x460c90)
CATEGORY = {1: 9, 2: 8, 3: 7, 4: 6, 5: 5, 6: 3, 7: 2, 8: 1, 10: 4}


def palette(exe):
    p = exe[PALETTE:PALETTE + 768]
    return b"".join(bytes((p[3 * i + 1], p[3 * i + 2], p[3 * i])) for i in range(256))


def pictures(data):
    if data[:4] == b"LS11":
        data = b"".join(ls11_decode_parts(data))
    p, out = 0, []
    while p < len(data):
        assert data[p:p + 2] == b"\x2a\x38", hex(p)
        w, h = data[p + 2] | data[p + 3] << 8, data[p + 4] | data[p + 5] << 8
        out.append((w, h, data[p + 6:p + 6 + w * h]))
        p += 6 + w * h
    return out


def table(data):
    n = struct.unpack_from("<I", data)[0]
    offs = struct.unpack_from(f"<{n + 1}I", data, 4)
    return [data[offs[i]:offs[i + 1]] for i in range(n)]


def sprite(b):
    """-> (x0, y0, w, h, {(x, y): colour}) with (x, y) relative to the hotspot."""
    x0, y0, w, h = struct.unpack_from("<hhHH", b)
    p, x, y, px = 8, 0, 0, {}
    while p + 6 <= len(b):
        ln, dx, dy = struct.unpack_from("<Hhh", b, p)
        p += 6
        if ln == 0:
            break
        x, y = x + dx, y + dy
        for i in range(ln):
            px[(x + i, y)] = b[p + i]
        p += ln
    return x0, y0, w, h, px


def bgpat(data):
    """40 rows of 12 texture ids; row = season*10 + category."""
    w, h = struct.unpack_from("<HH", data)
    v = struct.unpack_from(f"<{w * h}H", data, 4)
    return [v[r * h:(r + 1) * h] for r in range(w)]


def patseq(data, i):
    """PATSEQ.SK2: u32 offset[10]; item i is u16 w, u16 h, then w rows of h u16 sprite ids."""
    o = struct.unpack_from("<10I", data)[i]
    w, h = struct.unpack_from("<HH", data, o)
    v = struct.unpack_from(f"<{w * h}H", data, o + 4)
    return [v[r * h:(r + 1) * h] for r in range(w)]


def province_names(cmndata):
    """CMNDATA.SK2 0x3D5A: 41 x 226 bytes, u16 id then the Big5 name (8 bytes)."""
    names = {}
    for k in range(41):
        o = 0x3D5A + 226 * k
        names[struct.unpack_from("<H", cmndata, o)[0]] = cmndata[o + 2:o + 10].split(b"\0")[0].decode("big5")
    return names


def load_map(chikei, n):
    o = 0xC3 + (n - 1) * RECORD
    assert struct.unpack_from("<H", chikei, o)[0] == n
    o += 16
    return [[chikei[o + (r * COLS + c) * 6:o + (r * COLS + c) * 6 + 6] for c in range(COLS)] for r in range(ROWS)]


def heights(cells):
    """0x449b60: cell centres from b1, the other vertices averaged, then the centres smoothed once."""
    h = [[0] * W for _ in range(H)]
    g = lambda x, y: h[y][x] if 0 <= x < W and 0 <= y < H else 0
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if (x + y) & 1 == 0:
                h[y][x] = ((cells[y - 1][(x - 1) >> 1][1] & 0xF) - 5) * 15
    for y in range(2, H - 2):
        for x in range(2, W - 2):
            if (x + y) & 1:
                h[y][x] = (g(x, y + 1) + g(x, y - 1) + g(x - 1, y) + g(x + 1, y)) >> 2
    d3 = lambda s: int(s / 3)  # C division truncates toward zero
    for x in range(2, W - 2, 2):
        h[1][x] = d3(g(x, 2) + g(x - 1, 1) + g(x + 1, 1))
        h[H - 2][x] = d3(g(x, H - 3) + g(x - 1, H - 2) + g(x + 1, H - 2))
    for x in range(1, W - 1, 2):
        h[0][x] = g(x, 1)
        h[H - 1][x] = g(x, H - 2)
    for y in range(2, H - 2, 2):
        h[y][1] = d3(g(1, y + 1) + g(1, y - 1) + g(2, y))
        h[y][W - 2] = d3(g(W - 2, y + 1) + g(W - 2, y - 1) + g(W - 3, y))
    for y in range(1, H - 1, 2):
        h[y][0] = g(1, y)
        h[y][W - 1] = g(W - 2, y)
    h[0][0], h[H - 1][0] = g(1, 1), g(1, H - 2)
    h[H - 1][W - 1], h[0][W - 1] = g(W - 2, H - 2), g(W - 2, 1)
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if (x + y) & 1 == 0:
                h[y][x] = (g(x, y + 1) + g(x, y - 1) + g(x - 1, y) + g(x + 1, y)) >> 2
    return h


def shades(h):
    """0x449ae0: light from (1,1,1)/sqrt(3), 12 levels."""
    g = lambda x, y: h[y][x] if 0 <= x < W and 0 <= y < H else 0
    s = [[0] * W for _ in range(H)]
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if (x + y) & 1:
                continue
            a = g(x - 1, y) - g(x, y - 1)
            b = g(x, y + 1) - g(x - 1, y)
            c = g(x + 1, y) - g(x, y + 1)
            d = g(x, y - 1) - g(x + 1, y)
            nx = ((c - d) * 32.0 + (b - a) * 32.0) * 0.5
            ny = ((d + c) * -32.0 + (b + a) * 32.0) * 0.5
            nz = -2048.0
            v = -(nx + ny + nz) / (math.sqrt(3.0) * math.sqrt(nx * nx + ny * ny + nz * nz))
            s[y][x] = int(max(0.0, v) * 11.9)
    return s


def triangle(img, w, hgt, pts, tex):
    """0x449190: flat scanline fill, texture addressed by screen row and x - minx."""
    (x0, y0), (x1, y1), (x2, y2) = sorted(pts, key=lambda p: p[1])
    if y2 - y0 <= 0:
        return
    minx = min(x0, x1, x2)
    ix = lambda xa, ya, xb, yb, y: xa + int((y - ya) * (xb - xa) / (yb - ya))
    for y in range(max(y0, 0), min(y2, hgt)):
        xl = ix(x0, y0, x2, y2, y)
        xs = ix(x0, y0, x1, y1, y) if y < y1 else ix(x1, y1, x2, y2, y)
        a, b = max(min(xl, xs), 0), min(max(xl, xs), w)
        rowoff = (y & 63) * 64 - minx
        for x in range(a, b):
            img[y * w + x] = tex[rowoff + x] if 0 <= rowoff + x < 4096 else 0x40


def objects(cells, season, fac, veg, tree_group=0, levels=(5, 0, 0, 0)):
    """(depth, Y, X, layer, sprite id) anchored at the cell-centre vertex (X, Y) (0x4d6f90, 0x4d71c0)."""
    out = []
    for r in range(ROWS):
        for c in range(COLS - (r & 1)):
            t, _, _, _, sub, extra = cells[r][c]
            X, Y = 2 * c + 1 + (r & 1), r + 1
            if 11 <= t <= 24 and sub == 1:  # facility (inferred: kind = b0 - 8, drawn on sub-cell 1)
                kind = t - 8
                row = fac[season * 17 + kind]
                if kind in (5, 6):
                    ids = [row[levels[0]]]
                elif kind == 3:
                    ids = [row[0], row[6], row[12], row[18]]
                elif kind == 4:
                    ids = [row[0], row[6], row[12 + levels[0]], row[18]]
                else:
                    ids = [row[levels[0]], row[6 + levels[1]], row[12 + levels[2]], row[18 + levels[3]]]
                out += [(Y * 8, Y, X, k, s) for k, s in enumerate(ids) if s]
            if extra == 2:  # grown tree (inferred), growth 1000 -> stage 4
                s = veg[season * 3 + tree_group][1000 * 5 // 1001]
                if s:
                    out.append((Y * 8, Y, X, 0, s))
            if t == 4:  # ground decal, depth -10000
                s = veg[season * 3 + 2][0]
                if s:
                    out.append((-10000, Y, X, 0, s))
    return sorted(out)


def render_map(cells, pat, textures, sprites, fac, veg, month):
    h = heights(cells)
    sh = shades(h)
    season = (month - 1) // 3  # 0x4587c0
    top = 160                  # room for heights up to (15-5)*15
    w, hgt = W * 32, H * 16 + top + 64
    img = bytearray(w * hgt)
    P = lambda x, y: (x * 32, y * 16 - h[y][x] + top)  # 0x44a6d0, view 0

    def tid(c, r):  # 0x44aa30
        cell = cells[r][c]
        cat = CATEGORY.get(cell[0], 0)
        row = pat[season * 10 + cat]
        if cat == 0:
            return row[cell[2] // 10]
        if cat == 8:
            return row[1]  # flag 0x80 of +0x15 is clear at load
        return row[sh[r + 1][(r & 1) + 1 + c * 2]]

    for y in range(H):  # 0x44af20
        for x in range(W):
            if (x + y) & 1:
                continue
            if x == 0 and y == 0:
                tris = [((P(0, 0), P(0, 1), P(1, 0)), tid(0, 0))]
            elif x == 0 and y == H - 1:
                tris = [((P(0, y), P(0, y - 1), P(1, y)), tid(0, y - 2))]
            elif x == W - 1 and y == 0:
                tris = [((P(x, 0), P(x - 1, 0), P(x, 1)), tid((x - 2) >> 1, 0))]
            elif x == W - 1 and y == H - 1:
                tris = [((P(x, y), P(x - 1, y), P(x, y - 1)), tid((x - 2) >> 1, y - 2))]
            elif y == 0:
                tris = [((P(x, 1), P(x - 1, 0), P(x + 1, 0)), tid(x >> 1, 0))]
            elif y == H - 1:
                tris = [((P(x, y - 1), P(x - 1, y), P(x + 1, y)), tid(x >> 1, y - 2))]
            elif x == 0:
                tris = [((P(1, y), P(0, y - 1), P(0, y + 1)), tid(0, y))]
            elif x == W - 1:
                tris = [((P(x - 1, y), P(x, y - 1), P(x, y + 1)), tid((x - 2) >> 1, y))]
            else:
                t = tid((x - 1) >> 1, y - 1)
                tris = [((P(x, y - 1), P(x - 1, y), P(x + 1, y)), t), ((P(x, y + 1), P(x - 1, y), P(x + 1, y)), t)]
            for pts, t in tris:
                if t:
                    triangle(img, w, hgt, pts, textures[t - 1])
    for _, Y, X, _, s in objects(cells, season, fac, veg):
        ax, ay = P(X, Y)
        for (dx, dy), c in sprites[s][4].items():
            px, py = ax + dx, ay + dy
            if c and 0 <= px < w and 0 <= py < hgt:
                img[py * w + px] = c
    return Image.frombytes("P", (w, hgt), bytes(img))


def save(im, pal, path):
    im.putpalette(pal)
    im.save(path, transparency=0)


@click.command("suikoden2-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="game files (games/suikoden2-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/suikoden2-win/extract)")
@click.option("--scenario", default=1, type=click.IntRange(1, 3), help="CHIKEI file for the 州 maps")
@click.option("--month", default=4, type=click.IntRange(1, 12), help="month of the 州 maps (season = (month-1)//3)")
def suikoden2_extras(game_dir, out, scenario, month):
    """Faces, pictures, sprites, ground textures and 州 maps of 水滸傳 天導108星 (Win)."""
    def read(name):
        return open(os.path.join(game_dir, name), "rb").read()

    def folder(name):
        os.makedirs(os.path.join(out, name), exist_ok=True)
        return os.path.join(out, name)

    pal = palette(read("SUIKO2.EXE"))
    for name in PICTURES:
        pics = pictures(read(f"{name}.SK2"))
        for i, (w, h, px) in enumerate(pics):
            save(Image.frombytes("P", (w, h), px), pal, os.path.join(folder(name.lower()), f"{i:03d}.png"))
        print(f"{name}.SK2: {len(pics)} pictures")

    textures = table(read("BGIMAGE.SK2"))
    for k, t in enumerate(textures, 1):
        save(Image.frombytes("P", (64, 64), t), pal, os.path.join(folder("textures"), f"{k:02d}.png"))
    print(f"BGIMAGE.SK2: {len(textures)} textures")

    sprites = [None] + [sprite(b) for b in table(read("IMAGE.SK2"))]
    with open(os.path.join(folder("sprites"), "sprites.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["id", "x0", "y0", "w", "h"])
        for k, (x0, y0, w, h, px) in enumerate(sprites[1:], 1):
            im = Image.new("P", (max(w, 1), max(h, 1)))
            for (x, y), c in px.items():
                if 0 <= x - x0 < w and 0 <= y - y0 < h:
                    im.putpixel((x - x0, y - y0), c)
            save(im, pal, os.path.join(out, "sprites", f"{k:04d}.png"))
            wr.writerow([k, x0, y0, w, h])
    print(f"IMAGE.SK2: {len(sprites) - 1} sprites")

    names = province_names(read("CMNDATA.SK2"))
    chikei = read(f"CHIKEI{scenario:02d}.SK2")
    pat, ps = bgpat(read("BGPAT.SK2")), read("PATSEQ.SK2")
    fac, veg = patseq(ps, 1), patseq(ps, 2)  # loaded to 0x533420 and 0x530480
    with open(os.path.join(folder("map"), "provinces.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["id", "name", "file"])
        for n in range(1, 42):
            file = f"{n:02d}.png"
            save(render_map(load_map(chikei, n), pat, textures, sprites, fac, veg, month), pal,
                 os.path.join(out, "map", file))
            wr.writerow([n, names[n], file])
    print(f"CHIKEI{scenario:02d}.SK2: 41 州 maps, month {month}")
