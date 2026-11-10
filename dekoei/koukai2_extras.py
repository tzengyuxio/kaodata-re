"""大航海時代II (PC-98): ports, markets, trade goods, items, discoveries, ships, the world map and the 48x48 pictures,
written under --out (notes/koukai2.md「港口、交易品、道具、地圖」).

- Names and labels come from MAIN.EXE's data segment (DS:0 = file 0x39F00): near pointer tables to cp932 strings.
- Game state: DATA1.LZW (LS11) part 15, loaded at DS:0xCEC. All table offsets below are offsets in that part.
  Ports 0x52B0 (130 x 22; 100–129 are supply ports), port state 0x5DDC (100 x 37), markets 0x6C50 (13 x 128),
  ship instances 0x4BEE (22 bytes; 40 + type is the shipyard sample), ship types 0x5184 (25 x 12),
  discovery places 0x72E8 (100 x 7), items 0x75A4 (100 x 20).
- COLONY.DAT (in DATA2.LZW, LW11): 100 discoveries x 177 bytes (name, picture, description). ITEM.MES: 100 x 145.
- KAO.LZW parts 128–255: 48x48 3bpp pictures; 0–84 discoveries, 85–127 items (0x55 + item +0xF).
- WORLDMAP.LZW: three LS11 parts of 720 x 1080 cells (2160 x 1080 in all), see world().
"""
import csv
import os
import struct

import click
from PIL import Image, ImageDraw

from genpei import decode_planar
from kaodata_export import KOUKAI2_PC98_PALETTE
from ls11 import ls11_decode_parts, lw11_decode_files

DS = 0x39F00  # MAIN.EXE file offset of DS:0
STATE_DS = 0xCEC  # DS address of DATA1.LZW part 15

N_PORTS, N_REAL_PORTS, N_MARKETS, N_DISCOVERIES, N_ITEMS = 130, 100, 13, 100, 100

# Where the tables are in the game state, and the record layouts that differ between versions.
II_LAYOUT = dict(
    encoding="cp932", ports=0x52B0, port_state=0x5DDC, markets=0x6C50, ships=0x4BEE, ship_types=0x5184,
    port_state_size=37, n_ship_types=25, places=0x72E8,
    items=0x75A4, item_size=20, item_name=15, item_picture=0xF, item_price=0x10, item_power=0x12, item_kind=0x13,
    item_picture_base=0x55, colony_name=15, colony_picture=15, colony_text=16)


def ds_strings(exe, table, n, encoding="cp932"):
    """n near pointers at DS:table -> NUL-terminated strings."""
    out = []
    for p in struct.unpack_from(f"<{n}H", exe, DS + table):
        e = exe.index(b"\0", DS + p)
        out.append(exe[DS + p:e].decode(encoding))
    return out


def cstr(b, encoding="cp932"):
    return b.split(b"\0", 1)[0].decode(encoding, "replace")


def message(data, i, encoding="cp932"):
    """MESSAGE.DAT: big-endian u16 offset table, the count is the first offset / 2."""
    n = struct.unpack_from(">H", data, 0)[0] // 2
    offs = list(struct.unpack_from(f">{n}H", data, 0)) + [len(data)]
    return data[offs[i]:offs[i + 1]].split(b"\0", 1)[0].decode(encoding, "replace")


def world(parts):
    """2160 x 1080 cells (1 = sea) and {(x, y): code} of the special 2 x 2 sub-cells.
    Per part: 1350 u16 block offsets (from byte 2700), 30 x 45 blocks of 24 x 24 cells. A 1-byte block is uniform
    (bit 0: 1 sea). Otherwise the fill byte (0x78-0x7D): bit 2 set → the whole block is bit 0; bit 2 clear → the
    block is split in two halves (bit 1 clear: left / right, set: top / bottom), the first half is bit 0 and the
    second the opposite. Then an 18-byte mask of 12 x 12 sub-cells (2 x 2 cells, MSB first) and one byte per set bit:
    below 0x10 its bits 3..0 are the TL, TR, BL, BR cells (1 = land); 0x10 and above is a land sub-cell with a code
    (0x10 port, 0x11 discovery, 0x12 supply port, others unknown)."""
    g = [bytearray(2160) for _ in range(1080)]
    special = {}
    for p, d in enumerate(parts):
        offs = list(struct.unpack_from("<1350H", d, 0)) + [len(d) - 2700]
        for b in range(1350):
            blk = d[2700 + offs[b]:2700 + offs[b + 1]]
            bx, by = p * 720 + (b % 30) * 24, (b // 30) * 24
            f, a = blk[0], blk[0] & 1
            for y in range(24):
                if len(blk) == 1 or f & 4:
                    row = bytes([a]) * 24
                elif f & 2:
                    row = bytes([a if y < 12 else 1 - a]) * 24
                else:
                    row = bytes([a]) * 12 + bytes([1 - a]) * 12
                g[by + y][bx:bx + 24] = row
            if len(blk) == 1:
                continue
            mask, vals, k = blk[1:19], blk[19:], 0
            for s in range(144):
                if mask[s >> 3] >> (7 - (s & 7)) & 1:
                    v = vals[k]
                    k += 1
                    sx, sy = bx + (s % 12) * 2, by + (s // 12) * 2
                    if v >= 0x10:
                        special[(sx, sy)] = v
                    for c in range(4):
                        g[sy + (c >> 1)][sx + (c & 1)] = 0 if v >= 0x10 else 1 - ((v >> (3 - c)) & 1)
    return g, special


def _csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class Labels:
    """The name lists one game version needs."""

    def __init__(self, goods, categories, bounds, drinks, drink_prices, nations, item_kinds, discovery_kinds,
                 markets):
        self.goods, self.categories, self.bounds = goods, categories, bounds
        self.drinks, self.drink_prices, self.nations = drinks, drink_prices, nations
        self.item_kinds, self.discovery_kinds, self.markets = item_kinds, discovery_kinds, markets

    def category(self, g):
        return next(i for i, b in enumerate(self.bounds) if g < b)

    def good(self, g):
        return "" if g == 0xFF else self.goods[g]


def ii_labels(game_dir):
    exe = open(os.path.join(game_dir, "MAIN.EXE"), "rb").read()
    msg = open(os.path.join(game_dir, "MESSAGE.DAT"), "rb").read()
    return Labels(
        goods=ds_strings(exe, 0x7AE, 46), categories=ds_strings(exe, 0x814, 10), bounds=list(exe[DS + 0x80A:DS + 0x814]),
        drinks=ds_strings(exe, 0x828, 14), drink_prices=list(exe[DS + 0x844:DS + 0x852]),
        nations=ds_strings(exe, 0x8B0, 7), item_kinds=ds_strings(exe, 0x934, 14),
        discovery_kinds=ds_strings(exe, 0x924, 8), markets=[message(msg, 0x181 + i) for i in range(N_MARKETS)])


def write_tables(st, colony, item_mes, lb: Labels, out, lay):
    """st: the game state (DATA1 part 15 / Sdata.dat). Returns (ports, discoveries) as [(x, y, name)] for the map."""
    encoding, item_size, item_name = lay["encoding"], lay["item_size"], lay["item_name"]
    PORTS, PORT_STATE, MARKETS, ITEMS = lay["ports"], lay["port_state"], lay["markets"], lay["items"]
    item_names = [cstr(st[ITEMS + item_size * i:ITEMS + item_size * i + item_name], encoding) for i in range(N_ITEMS)]
    ports = []
    rows = []
    for k in range(N_PORTS):
        o = PORTS + 22 * k
        x, y = struct.unpack_from("<HH", st, o)
        name, flags = cstr(st[o + 4:o + 0x15], encoding), st[o + 0x15]
        ports.append((x, y, name))
        row = [k, name, x, y, flags & 7, lb.nations[flags & 7] if flags & 7 < 6 else "", f"{flags:02X}"]
        if k < N_REAL_PORTS:
            s = PORT_STATE + lay["port_state_size"] * k
            eco, eco_acc, ind, ind_acc = struct.unpack_from("<4H", st, s)
            support = list(st[s + 8:s + 14])
            rates = list(st[s + 14:s + 24])
            sp_price, sp_good, sp_level, area = struct.unpack_from("<HBBB", st, s + 24)
            shop = [item_names[i] for i in st[s + 29:s + 33] if i != 0xFF]
            market, b34, b35, drink = st[s + 33:s + 37]
            row += [eco, eco_acc, ind, ind_acc, " ".join(map(str, support)), " ".join(map(str, rates)),
                    lb.good(sp_good), sp_price if sp_good != 0xFF else "", sp_level if sp_good != 0xFF else "", area,
                    " ".join(shop), market, lb.markets[market], b34, b35,
                    lb.drinks[drink], lb.drink_prices[drink]] + list(st[s + 37:s + lay["port_state_size"]])
        rows.append(row)
    _csv(os.path.join(out, "tables", "ports.csv"),
         ["id", "name", "x", "y", "nation", "nation_name", "flags", "economy", "economy_acc", "industry",
          "industry_acc", "support", "price_rates", "specialty", "specialty_price", "specialty_level", "area",
          "shop_items", "market", "market_name", "b34", "b35", "drink", "drink_price"]
         + [f"b{i}" for i in range(37, lay["port_state_size"])], rows)

    _csv(os.path.join(out, "tables", "goods.csv"), ["id", "name", "category", "category_name"],
         [[g, n, lb.category(g), lb.categories[lb.category(g)]] for g, n in enumerate(lb.goods)])

    sell, slots = [], []
    for m in range(N_MARKETS):
        o = MARKETS + 128 * m
        prices = struct.unpack_from("<46H", st, o)
        sell += [[m, lb.markets[m], g, lb.goods[g], p] for g, p in enumerate(prices)]
        buy = struct.unpack_from("<9H", st, o + 92)
        for i in range(9):
            g = st[o + 110 + i]
            if g != 0xFF:
                slots.append([m, lb.markets[m], i, g, lb.goods[g], buy[i], st[o + 119 + i]])
    _csv(os.path.join(out, "tables", "market_sell.csv"), ["market", "market_name", "good", "good_name", "price"], sell)
    _csv(os.path.join(out, "tables", "market_goods.csv"),
         ["market", "market_name", "slot", "good", "good_name", "base_price", "level"], slots)

    _csv(os.path.join(out, "tables", "drinks.csv"), ["id", "name", "price"],
         [[i, n, lb.drink_prices[i]] for i, n in enumerate(lb.drinks)])

    rows = []
    for t in range(lay["n_ship_types"]):
        o = lay["ship_types"] + 12 * t
        b0, dur, turn, power, crew10, sailors, cargo, guns, b9, price = struct.unpack_from("<6BH2BH", st, o)
        sample = lay["ships"] + 22 * (40 + t)
        rows.append([t, cstr(st[sample:sample + 15], encoding), dur, turn, power, crew10 * 10, sailors, cargo, guns,
                     price, b0, b9])
    _csv(os.path.join(out, "tables", "ships.csv"),
         ["id", "name", "durability", "turning", "propulsion", "max_crew", "min_sailors", "capacity", "max_guns",
          "price_base", "b0", "b9"], rows)

    rows = []
    for i in range(N_ITEMS):
        o = ITEMS + item_size * i
        name = cstr(st[o:o + item_name], encoding)
        pic, power, kind = st[o + lay["item_picture"]], st[o + lay["item_power"]], st[o + lay["item_kind"]]
        price = struct.unpack_from("<H", st, o + lay["item_price"])[0]
        rows.append([i, name, kind & 0xF, lb.item_kinds[kind & 0xF], power, price, lay["item_picture_base"] + pic,
                     cstr(item_mes[145 * i:145 * (i + 1)], encoding).replace("\n", " ")])
    _csv(os.path.join(out, "tables", "items.csv"),
         ["id", "name", "kind", "kind_name", "power", "price", "picture", "description"], rows)

    discoveries, rows = [], []
    for i in range(N_DISCOVERIES):
        c = colony[177 * i:177 * (i + 1)]
        x, y, b4, value, kind = struct.unpack_from("<HHBBB", st, lay["places"] + 7 * i)
        name = cstr(c[:lay["colony_name"]], encoding)
        if (x, y) not in ((0, 0), (1, 0)):
            discoveries.append((x, y, name))
        rows.append([i, name, kind & 7, lb.discovery_kinds[kind & 7], x, y, value, b4, c[lay["colony_picture"]],
                     cstr(c[lay["colony_text"]:], encoding).replace("\n", " ")])
    _csv(os.path.join(out, "tables", "discoveries.csv"),
         ["id", "name", "kind", "kind_name", "x", "y", "value", "b4", "picture", "description"], rows)
    return ports, discoveries


def write_pictures(pictures, out):
    """pictures: the 864-byte 48x48 3bpp pictures, discoveries first, then items."""
    pal = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in KOUKAI2_PC98_PALETTE]
    flat = [v for c in pal for v in c]
    os.makedirs(os.path.join(out, "pictures"), exist_ok=True)
    for i, data in enumerate(pictures):
        im = Image.frombytes("P", (48, 48), bytes(decode_planar(data, 0, 48, 48, 3)))
        im.putpalette(flat)
        im.save(os.path.join(out, "pictures", f"{i:03d}.png"))


def write_map(map_parts, ports, discoveries, out):
    g, special = world(map_parts)
    im = Image.new("RGB", (2160, 1080))
    sea, land = (40, 70, 140), (120, 160, 90)
    im.putdata([sea if v else land for row in g for v in row])
    dr = ImageDraw.Draw(im)
    for (x, y), v in special.items():
        if v > 0x12:
            dr.rectangle([x, y, x + 1, y + 1], fill=(90, 120, 60))
    os.makedirs(os.path.join(out, "map"), exist_ok=True)
    im.save(os.path.join(out, "map", "world.png"))
    for x, y, _ in discoveries:
        dr.rectangle([x - 2, y - 2, x + 3, y + 3], outline=(255, 230, 0))
    for k, (x, y, _) in enumerate(ports):
        dr.rectangle([x - 1, y - 1, x + 2, y + 2], fill=(220, 30, 30) if k < N_REAL_PORTS else (255, 140, 200))
        dr.text((x + 4, y - 5), str(k), fill=(255, 255, 255))
    im.save(os.path.join(out, "map", "world_ports.png"))

    def code(x, y):
        return special.get((x & ~1, y & ~1))

    p_ok = sum(code(x, y) == (0x10 if k < N_REAL_PORTS else 0x12) for k, (x, y, _) in enumerate(ports))
    d_ok = sum(code(x, y) == 0x11 for x, y, _ in discoveries)
    n = {v: list(special.values()).count(v) for v in (0x10, 0x11, 0x12)}
    print(f"ports on a port sub-cell (0x10 / 0x12 supply): {p_ok}/{len(ports)}; map has {n[0x10]} + {n[0x12]}")
    print(f"discoveries on a 0x11 sub-cell: {d_ok}/{len(discoveries)}; map has {n[0x11]}")


@click.command("koukai2-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="game files (games/koukai2-pc98)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/koukai2-pc98/extract)")
def koukai2_extras(game_dir, out):
    """Ports, markets, goods, items, discoveries, ships, world map and pictures of 大航海時代II (PC-98)."""
    def read(name):
        return open(os.path.join(game_dir, name), "rb").read()

    st = ls11_decode_parts(read("DATA1.LZW"))[15]
    colony = lw11_decode_files(read("DATA2.LZW"))["COLONY.DAT"]
    ports, discoveries = write_tables(st, colony, read("ITEM.MES"), ii_labels(game_dir), out, II_LAYOUT)
    write_pictures(ls11_decode_parts(read("KAO.LZW"))[128:256], out)
    write_map(ls11_decode_parts(read("WORLDMAP.LZW")), ports, discoveries, out)
