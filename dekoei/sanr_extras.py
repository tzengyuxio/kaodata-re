"""三國志風雲再起 (SAN1.EXE, Win 中文版): every picture of the game, written under --out (notes/sanr.md).

- Picture files (*.SA1): a run of pictures, each b"\\x2a\\x38", u16 width, u16 height, then width*height 8bpp
  pixels. LS11 files split the run into parts of at most 32768 bytes, so the parts are joined before reading.
- Palette: MAINPAL.SA1, 256 triples stored B,R,G; picture colour i is MAINPAL entry i-10 (Windows keeps 0-9 for
  the system colours). Checked on the faces and TITLE.SA1 (picture only, no screenshot).
- KAO.SA1: 260 faces 96x128. MAINMAP.SA1: 58 pictures 72x84, the 272x352 maps (#174 city areas, #175 州) and a
  640x420 background. MAP.SA1: the 272x352 map with the 58 city numbers. HEXMAP.SA1: 58 battle maps 540x384.
"""
import os

import click
from PIL import Image

from ls11 import ls11_decode_parts

FILES = ["KAO", "MAINMAP", "MAP", "HEXMAP", "HEXANI", "ANIME", "TITLE", "MAINGRP", "COM_HEX", "HATA_HEX",
         "SONOHEX", "SONO2HEX", "KOEILOGO", "C1995"]


def palette(raw):
    """MAINPAL.SA1 -> PIL palette: colour i = entry i-10, each entry stored B,R,G."""
    out = bytearray()
    for i in range(256):
        b, r, g = raw[3 * ((i - 10) % 256):3 * ((i - 10) % 256) + 3]
        out += bytes((r, g, b))
    return bytes(out)


def pictures(data):
    """Split a run of pictures into (width, height, pixels)."""
    p, out = 0, []
    while p < len(data):
        assert data[p:p + 2] == b"\x2a\x38", hex(p)
        w, h = data[p + 2] | data[p + 3] << 8, data[p + 4] | data[p + 5] << 8
        out.append((w, h, data[p + 6:p + 6 + w * h]))
        p += 6 + w * h
    return out


def read_pictures(path):
    data = open(path, "rb").read()
    if data[:4] == b"LS11":
        data = b"".join(ls11_decode_parts(data))
    return pictures(data)


@click.command("sanr-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="game files (games/sanr-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/sanr-win/extract)")
def sanr_extras(game_dir, out):
    """Faces, maps, battle maps and the other pictures of 三國志風雲再起 (Win)."""
    pal = palette(open(os.path.join(game_dir, "MAINPAL.SA1"), "rb").read())
    for name in FILES:
        pics = read_pictures(os.path.join(game_dir, f"{name}.SA1"))
        folder = os.path.join(out, name.lower())
        os.makedirs(folder, exist_ok=True)
        for i, (w, h, px) in enumerate(pics):
            im = Image.frombytes("P", (w, h), px)
            im.putpalette(pal)
            im.save(os.path.join(folder, f"{i:03d}.png"))
        print(f"{name}.SA1: {len(pics)} pictures")
