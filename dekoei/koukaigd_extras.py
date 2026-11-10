"""大航海時代外傳 (Win, Traditional Chinese): ports, markets, trade goods, items, discoveries, ships, the world map and
the 48x48 pictures, written under --out (notes/koukaigd.md「港口、交易品、道具、地圖」). Same tables as 大航海時代II
(koukai2_extras), at other offsets and with Big5 text.

- Labels: koukaiGD.exe .data (file offset = VA - 0x401000), fixed-width Big5 string arrays; the market names are a
  pointer table (Message.dat is a Japanese leftover and is not used).
- Game state: Sdata.dat (= Data1.lzw part 15). Ship types 0x3D9B (32 x 12: II's 25 and 7 sea fortresses),
  ship instances 0x3F1B, items 0x4B09 (100 x 22), discovery places 0x53A1, markets 0x5675, port state 0x5CF5
  (100 x 38: II's 37 bytes and one more), ports 0x6BCD.
- Colony.dat: 100 x 177 (name 21 bytes, +21 picture, +22 description). Item.mes: 100 x 145.
- Kao.lzw parts 157–321: 165 pictures; 0–103 discoveries, 104–164 items (item +19 + 0x68, 0x43493C).
- Worldmap.lzw is byte-identical to 大航海時代II's WORLDMAP.LZW.
"""
import os
import struct

import click

from koukai2_extras import Labels, write_map, write_pictures, write_tables
from ls11 import ls11_decode_parts

DATA = 0x401000  # .data: VA - file offset

GD_LAYOUT = dict(
    encoding="big5", ports=0x6BCD, port_state=0x5CF5, port_state_size=38, markets=0x5675, ships=0x3F1B,
    ship_types=0x3D9B, n_ship_types=32, places=0x53A1,
    items=0x4B09, item_size=22, item_name=17, item_price=17, item_picture=19, item_power=20, item_kind=21,
    item_picture_base=0x68, colony_name=21, colony_picture=21, colony_text=22)


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


@click.command("koukaigd-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="game files (games/koukaigd-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/koukaigd-win/extract)")
def koukaigd_extras(game_dir, out):
    """Ports, markets, goods, items, discoveries, ships, world map and pictures of 大航海時代外傳 (Win)."""
    def read(name):
        return open(os.path.join(game_dir, name), "rb").read()

    ports, discoveries = write_tables(read("Sdata.dat"), read("Colony.dat"), read("Item.mes"),
                                      gd_labels(read("koukaiGD.exe")), out, GD_LAYOUT)
    write_pictures(ls11_decode_parts(read("Kao.lzw"))[157:], out)
    write_map(ls11_decode_parts(read("Worldmap.lzw")), ports, discoveries, out)
