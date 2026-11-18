"""大航海時代 (PC-98): ports, trade goods, items, ships, fleets and the world map, written under --out
(notes/koukai.md「港口、交易品、道具、地圖」). Only static tables; field meanings marked 🟡 there are guesses.

- SHINARIO.CIM (loaded at DS:0x42 of MAIN.EXE):
  - Items: 31 records of 15 bytes at 0xA8: +0 name (13 bytes, Shift-JIS), +13 u16 price.
  - Fleets: 21 records of 17 bytes at 0xC34: +0 bx, by, fx, fy (position, same units as the ports), the rest raw.
  - Port economy: 50 records of 18 bytes at 0xD9A (ports 0-49): +0 u32, +4 u32, +8/+9/+10 shares of three nations
    (%, 🟡), +11..+13 raw, +14..+17 the four item ids sold by the port's item shop.
  - Ports with an item shop: port +19 bit 2 (MAIN.EXE 0xF0DA builds the town facility mask; facility 1 is the
    item shop 0x10EA0, buy 0x10734 lists economy +14..+17 and charges item +13).
  - Flagship ヘルメス at 0x12C6 and 6 ship templates at 0x132F, 21 bytes: +0 name (15 bytes), +15 u16, +17 u8,
    +18 u16, +20 u8 (meanings unknown).
  - Ports: 70 records of 20 bytes at 0x1766: +0 name (15 bytes), +15 bx, +16 by, +17 fx, +18 fy, +19 flag.
    Position in half map bytes: x = bx * 14 + fx, y = by * 14 + fy.
- MAIN.EXE (DGROUP at file 0x40910): trade goods = 26 near pointers at DS:0x1EAC; shipyard names = 6 NUL-padded
  strings at DS:0xC7D4; item kind and rank = 31 x 2 bytes at DS:0x22CA (selling is refused when 150 x rank exceeds
  the port's economy +0, the sell price is half the price). What each kind does is in ITEM_EFFECTS (by item id
  for kind 0, by kind otherwise; notes/koukai.md「道具的效果」).
- NEWGAME.DAT: u16 offset of section B, u16 offset of section C; section A from offset 4 is 288 x 5 bytes
  (u16 group, 3 bytes ?) for a 24 x 12 grid of groups; section B is 9 u16 block numbers per group (3 x 3);
  section C is 49-byte blocks (7 x 7 terrain codes, 0 = sea). The world is 504 x 252 bytes.
- STIZU.DAT: the 「MAPA DE MUNDO」 picture, 640 x 400, three 32000-byte planes in turn (B, R, G), bit 7 leftmost.
"""
import os
import struct

import click
from PIL import Image, ImageDraw
from common import write_csv

DIGITAL = ["#000000", "#00ff00", "#ff0000", "#ffff00", "#0000ff", "#00ffff", "#ff00ff", "#ffffff"]
DGROUP = 0x40910
# Effects of held items, by id for kind 0 (bits of fleet 0 +0xB tested directly) and by kind for 1-4 (rank of the
# best held item of that kind, MAIN.EXE 0x41D4). Bonuses only apply to ships whose captain is the hero (man 0).
ITEM_EFFECTS = {
    0: "監視：看整個畫面（沒有時只能看相鄰 1 格）；航行時發現畫面內所有港口（沒有時只發現相鄰的）",
    1: "測量：顯示現在位置（緯度、經度）",
    2: "情報→地形 要有它才有作用（沒有時「別に異常はありやせんぜ」）",
    "kind1": "主人公的船被砲擊時，傷害減少 10%×等級",
    "kind2": "主人公的船斬り込み時，殺傷力×(1＋等級/8)",
    "kind3": "主人公的船砲擊時，威力×(1＋等級/8)（上限 100）",
    "kind4": "財宝：可在道具屋賣（半價）、送給王女（贈り物をする，好感固定 +40）",
}


def _name(b):
    return b.split(b"\0")[0].decode("cp932")


def ports(cim):
    out = []
    for i in range(70):
        r = cim[0x1766 + i * 20:0x1766 + i * 20 + 20]
        bx, by, fx, fy, flag = r[15:20]
        out.append((i, _name(r[:15]), bx, by, fx, fy, bx * 14 + fx, by * 14 + fy, flag))
    return out


def tables(game_dir, out):
    cim = open(os.path.join(game_dir, "SHINARIO.CIM"), "rb").read()
    exe = open(os.path.join(game_dir, "MAIN.EXE"), "rb").read()
    pts = ports(cim)
    rows = []
    for p in pts:
        e = []
        if p[0] < 50:
            r = cim[0xD9A + p[0] * 18:0xD9A + p[0] * 18 + 18]
            e = [*struct.unpack_from("<II", r), r[8], r[9], r[10], r[11:].hex(" ")]
        rows.append([*p, *e])
    write_csv(f"{out}/tables/ports.csv", ["id", "name", "bx", "by", "fx", "fy", "x", "y", "flag",
                                     "u32_0", "u32_4", "share_a", "share_b", "share_c", "raw_11"], rows)
    goods = struct.unpack_from("<26H", exe, DGROUP + 0x1EAC)
    write_csv(f"{out}/tables/goods.csv", ["id", "name"], [(i, exe[DGROUP + q:exe.index(b"\0", DGROUP + q)].decode("cp932")) for i, q in enumerate(goods)])
    items = [_name(cim[0xA8 + i * 15:0xA8 + i * 15 + 13]) for i in range(31)]
    shops = [(p[0], p[1], cim[0xD9A + p[0] * 18 + 14:0xD9A + p[0] * 18 + 18]) for p in pts[:50] if p[8] & 4]
    irows = []
    for i, name in enumerate(items):
        price = struct.unpack_from("<H", cim, 0xA8 + i * 15 + 13)[0]
        kind, rank = exe[DGROUP + 0x22CA + i * 2:DGROUP + 0x22CA + i * 2 + 2]
        sold = [s for s in shops if i in s[2]]
        effect = ITEM_EFFECTS[i] if kind == 0 else ITEM_EFFECTS[f"kind{kind}"]
        irows.append((i, name, price, price // 2, kind, rank, " ".join(str(s[0]) for s in sold),
                      "、".join(s[1] for s in sold), effect))
    write_csv(f"{out}/items/items.csv", ["id", "name", "price", "sell", "kind", "rank", "ports", "port_names", "effect"], irows)
    write_csv(f"{out}/items/shops.csv", ["port", "name", *(f"item{k}" for k in range(4)), *(f"name{k}" for k in range(4))], [(p, n, *lst, *(items[b] for b in lst)) for p, n, lst in shops])
    ships = []
    for i, a in [("flagship", 0x12C6), *((k, 0x132F + k * 21) for k in range(6))]:
        r = cim[a:a + 21]
        ships.append((i, _name(r[:15]), *struct.unpack_from("<H", r, 15), r[17], *struct.unpack_from("<H", r, 18), r[20]))
    write_csv(f"{out}/ships/ship_types.csv", ["id", "name", "u16_15", "u8_17", "u16_18", "u8_20"], ships)
    yard = exe[DGROUP + 0xC7D4:DGROUP + 0xC7D4 + 54].split(b"\0")
    write_csv(f"{out}/ships/shipyard.csv", ["id", "name"], enumerate(s.decode("cp932") for s in yard if s))
    fleets = []
    for i in range(21):
        r = cim[0xC34 + i * 17:0xC34 + i * 17 + 17]
        fleets.append((i, *r[:4], r[0] * 14 + r[2], r[1] * 14 + r[3], r[4:].hex(" ")))
    write_csv(f"{out}/tables/fleets.csv", ["id", "bx", "by", "fx", "fy", "x", "y", "raw_4"], fleets)
    return pts


def world(data):
    a, b = struct.unpack_from("<HH", data, 0)
    groups = [struct.unpack_from("<H", data, 4 + 5 * k)[0] for k in range(288)]
    blocks = struct.unpack_from(f"<{(b - a) // 2}H", data, a)
    terrain = data[b:]
    m = [[0] * 504 for _ in range(252)]
    for k, g in enumerate(groups):
        cx, cy = k % 24, k // 24
        for s in range(9):
            blk = blocks[g * 9 + s]
            for t in range(49):
                m[cy * 21 + (s // 3) * 7 + t // 7][cx * 21 + (s % 3) * 7 + t % 7] = terrain[blk * 49 + t]
    return m


def world_map(game_dir, out, pts):
    m = world(open(os.path.join(game_dir, "NEWGAME.DAT"), "rb").read())
    img = Image.new("RGB", (1008, 504))
    px = img.load()
    for y, row in enumerate(m):
        for x, c in enumerate(row):
            col = DIGITAL[4] if c == 0 else DIGITAL[1] if c <= 3 else DIGITAL[3]
            rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
            for dy in (0, 1):
                for dx in (0, 1):
                    px[x * 2 + dx, y * 2 + dy] = rgb
    os.makedirs(f"{out}/map", exist_ok=True)
    img.save(f"{out}/map/world.png")
    d = ImageDraw.Draw(img)
    for p in pts:
        x, y = p[6], p[7]
        d.rectangle([x - 2, y - 2, x + 2, y + 2], outline="#ff0000" if p[0] < 50 else "#ff00ff")
    img.save(f"{out}/map/world_ports.png")

    s = open(os.path.join(game_dir, "STIZU.DAT"), "rb").read()
    pic = Image.new("P", (640, 400))
    pic.putpalette([int(c[i:i + 2], 16) for c in DIGITAL for i in (1, 3, 5)])
    pp = pic.load()
    for y in range(400):
        for x in range(640):
            o, bit = y * 80 + x // 8, 7 - x % 8
            b, r, g = ((s[k * 32000 + o] >> bit) & 1 for k in range(3))
            pp[x, y] = b << 2 | r << 1 | g
    pic.save(f"{out}/map/STIZU.png")


@click.command("koukai-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="game files (games/koukai-pc98)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/koukai-pc98/extract)")
def koukai_extras(game_dir, out):
    """大航海時代 (PC-98): ports, goods, items, ships, fleets and the world map."""
    pts = tables(game_dir, out)
    world_map(game_dir, out, pts)
    shops = sum(p[8] & 4 > 0 for p in pts[:50])
    click.echo(f"{len(pts)} ports, 26 goods, 31 items ({shops} item shops), 7 ship types, 21 fleets, map 504x252 -> {out}")


if __name__ == "__main__":
    koukai_extras()
