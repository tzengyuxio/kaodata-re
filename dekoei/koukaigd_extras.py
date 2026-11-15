"""大航海時代外傳 (Win, Traditional Chinese): ports, markets, trade goods, items, discoveries, ships, the world map and
the 48x48 pictures, written under --out (notes/koukaigd.md「港口、交易品、道具、地圖」). Same tables as 大航海時代II
(koukai2_extras), at other offsets and with Big5 text.

- Labels: koukaiGD.exe .data (file offset = VA - 0x401000), fixed-width Big5 string arrays; the market names are
  messages 0x181 + market of the exe's message table (VA 0x45F840, 8 bytes each, 0x42F2C0; shown at 0x427FCF), the
  same numbers as II's MESSAGE.DAT (Message.dat here is a Japanese leftover and is not used).
- Game state: Sdata.dat (= Data1.lzw part 15), read field by field into globals by 0x415320, so the offsets and sizes
  come from that list: ship types 0x3D9B (32 x 12: II's 25 and 7 sea fortresses), ship instances 0x3F1B (72 x 22),
  items 0x4B09 (100 x 22), discovery places 0x53A1 (100 x 7), markets 0x5675 (13 x 128), port state 0x5CF5
  (100 x 38: II's 37 bytes and one more), ports 0x6BCD (130 x 22). Record sizes: the accessors at 0x43BC70-0x43BDC0.
- Port state +34 is the shipyard kind (row of SHIPYARDS, 0x41A1E3 / 0x42A51A), +35 the days until an ordered ship is
  done (0xFF none, 0x42B106), +37 the affinity group (row of AFFINITY, 0x4026EB). Ship type +0 is the industry / 10
  a shipyard needs to build it (0x41A1FC).
- Colony.dat: 100 x 177 (name 21 bytes, +21 picture, +22 description). Item.mes: 100 x 145.
- Kao.lzw parts 157–321: 165 pictures; 0–103 discoveries, 104–164 items (item +19 + 0x68, 0x43493C).
- Worldmap.lzw is byte-identical to 大航海時代II's WORLDMAP.LZW.
"""
import os
import struct

import click

from koukai2_extras import Labels, _csv, cstr, write_map, write_pictures, write_tables
from ls11 import ls11_decode_parts

DATA = 0x401000  # .data: VA - file offset

GD_LAYOUT = dict(
    encoding="big5", ports=0x6BCD, port_state=0x5CF5, port_state_size=38, markets=0x5675, ships=0x3F1B,
    ship_types=0x3D9B, n_ship_types=32, places=0x53A1,
    items=0x4B09, item_size=22, item_name=17, item_price=17, item_picture=19, item_power=20, item_kind=21,
    item_picture_base=0x68, colony_name=21, colony_picture=21, colony_text=22,
    rename={"b34": "shipyard", "b35": "build_days", "b37": "affinity", "b0": "industry_req"})
AFFINITY = 0x45A0F8  # VA: 15 groups x 6 s32, the % a nation's support gain is multiplied by (0x4026EB)
SHIPYARDS = 0x45F418  # VA: 11 shipyard kinds x 8 ship types (0xFF empty), the ships a shipyard builds (0x42A51D)


def fixed(exe, offset, stride, n):
    return [exe[offset + stride * i:offset + stride * (i + 1)].split(b"\0", 1)[0].decode("big5") for i in range(n)]


def gd_labels(exe):
    markets = []
    for i in range(13):
        va = struct.unpack_from("<I", exe, 0x5F44C + 8 * i)[0]
        o = va - DATA
        markets.append(exe[o:exe.index(b"\0", o)].decode("big5"))
    return Labels(
        goods=fixed(exe, 0x59B80, 11, 46), categories=fixed(exe, 0x59D90, 7, 10), bounds=list(exe[0x59D80:0x59D8A]),
        drinks=fixed(exe, 0x59DD8, 11, 14), drink_prices=list(exe[0x59E78:0x59E86]),
        nations=fixed(exe, 0x5A050, 13, 7), item_kinds=fixed(exe, 0x5A260, 9, 14),
        discovery_kinds=fixed(exe, 0x5A228, 7, 8), markets=markets)


def write_gd_tables(exe, st, lb: Labels, out):
    """The two exe tables that port state +37 and +34 index (tables/affinity.csv, tables/shipyards.csv)."""
    rows = []
    for g in range(15):
        rows.append([g] + list(struct.unpack_from("<6i", exe, AFFINITY - DATA + 24 * g)))
    _csv(os.path.join(out, "tables", "affinity.csv"), ["group"] + lb.nations[:6], rows)
    rows = []
    for k in range(11):
        for slot, t in enumerate(exe[SHIPYARDS - DATA + 8 * k:SHIPYARDS - DATA + 8 * k + 8]):
            if t != 0xFF:
                sample = GD_LAYOUT["ships"] + 22 * (40 + t)
                rows.append([k, slot, t, cstr(st[sample:sample + 15], "big5")])
    _csv(os.path.join(out, "tables", "shipyards.csv"), ["shipyard", "slot", "ship_type", "ship_name"], rows)


@click.command("koukaigd-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="game files (games/koukaigd-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/koukaigd-win/extract)")
def koukaigd_extras(game_dir, out):
    """Ports, markets, goods, items, discoveries, ships, world map and pictures of 大航海時代外傳 (Win)."""
    def read(name):
        return open(os.path.join(game_dir, name), "rb").read()

    exe, st = read("koukaiGD.exe"), read("Sdata.dat")
    labels = gd_labels(exe)
    ports, discoveries = write_tables(st, read("Colony.dat"), read("Item.mes"), labels, out, GD_LAYOUT)
    write_gd_tables(exe, st, labels, out)
    write_pictures(ls11_decode_parts(read("Kao.lzw"))[157:], out)
    write_map(ls11_decode_parts(read("Worldmap.lzw")), ports, discoveries, out)
