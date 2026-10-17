import os
import shutil
import struct

import click
from PIL import Image

from utils import unpack_npk

# GRAPHIC-style archives: an OFS file of u32 offsets into a DAT file
CELT_ARCHIVES = [
    ("graphic", "GRAPHOFS.DAT", "GRAPHIC.DAT", "CELT01.PAL"),
    ("wsys", "WSYSOFS.DAT", "WSYSGRAP.DAT", "CELT01.PAL"),
    ("cgraphic", "CGRAPOFS.DAT", "CGRAPHIC.DAT", "CELT01.PAL"),
    ("anm", "ANMGRPOF.DAT", "ANMGRP.DAT", "CELT01.PAL"),
    ("opening", "OGRAPOFS.DAT", "OGRAPHIC.DAT", "OP_05.PAL"),
    ("ending", "EGRAPOFS.DAT", "EGRAPHIC.DAT", "ED_03.PAL"),
]
CELT_TILES = ["NORTH", "EAST", "SOUTH", "WEST"]


def celt_palette(raw: bytes) -> list[int]:
    """16 colours, each u16: G (bits 15-10), R (9-5), B (4-0)."""
    pal = []
    for v, in struct.iter_unpack("<H", raw):
        pal += [(v >> 5 & 31) * 255 // 31, (v >> 10) * 255 // 63, (v & 31) * 255 // 31]
    return pal


def celt_planar(raw: bytes, width: int, height: int) -> bytes:
    """4 bpp: every 8 px are 4 bytes, planes 0-3."""
    px = bytearray()
    for y in range(height):
        row = raw[y * width // 2:(y + 1) * width // 2]
        for x in range(width):
            g, k = x // 8 * 4, 7 - x % 8
            px.append(sum((row[g + p] >> k & 1) << p for p in range(4)))
    return bytes(px)


def celt_entry(data: bytes) -> list[tuple[int, int, bytes]]:
    """One archive entry: "B" raw, "N" NPK or "A" n raw frames; header kind, bpp/frames, u16 width in bytes, u16 height."""
    kind, n = data[0], data[1]
    w, h = struct.unpack("<HH", data[2:6])
    width = w * 2
    if kind == ord("N"):
        return [(width, h, unpack_npk(data[6:], width, h)[:width * h])]
    if kind == ord("B"):
        return [(width, h, celt_planar(data[6:6 + w * h], width, h))]
    assert kind == ord("A"), kind
    return [(width, h, celt_planar(data[6 + f * w * h:6 + (f + 1) * w * h], width, h)) for f in range(n)]


def celt_read(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return f.read()


@click.group()
def celt():
    """ケルトの聖戦 / 魔眼邪神 / Celtic Tales: Balor of the Evil Eye

    \b
    Windows 日文版（CD 的 CELTWIN/ 以 SZDD 解開後的檔名）:
        GRAPHIC.DAT     頭像、物品、戰鬥動作、畫面元件（GRAPHOFS.DAT 索引）
        WSYSGRAP.DAT    視窗元件
        CGRAPHIC.DAT    其他畫面
        ANMGRP.DAT      地圖上的人物動畫
        *GRP.DAT        地圖拼塊（*MSK.DAT 遮罩、*OFS.DAT 索引）
        OGRAPHIC.DAT    開場（CD 的 CELTCDDT/）
        EGRAPHIC.DAT    結局（CD 的 CELTCDDT/）
        *.PAL           16 色色盤
        *.KOB           MIDI（1 byte 前綴後 XOR 0xF0）
    """
    pass


@click.command(help="拆出所有圖檔")
@click.option("--game-dir", required=True, help="遊戲目錄")
@click.option("--out", required=True, help="輸出目錄")
def celt_art(game_dir, out):
    """
    ./dekoei.py celt art --game-dir ../games/celt-win --out ../games/celt-win/extract
    """
    for sub, ofs, dat, pal in CELT_ARCHIVES:
        # OGRAPHIC/EGRAPHIC and their palettes are only in the CD's CELTCDDT/
        missing = [n for n in (ofs, dat, pal) if not os.path.exists(os.path.join(game_dir, n))]
        if missing:
            print(f"{sub}: skipped, missing {', '.join(missing)}")
            continue
        data, index = celt_read(game_dir, dat), celt_read(game_dir, ofs)
        palette = celt_palette(celt_read(game_dir, pal))
        offsets = list(struct.unpack(f"<{len(index) // 4}I", index)) + [len(data)]
        os.makedirs(os.path.join(out, sub), exist_ok=True)
        count = 0
        for i, (a, b) in enumerate(zip(offsets, offsets[1:])):
            if b - a < 6:
                continue
            frames = celt_entry(data[a:b])
            for f, (w, h, px) in enumerate(frames):
                im = Image.frombytes("P", (w, h), px)
                im.putpalette(palette)
                name = f"{i:04d}.png" if len(frames) == 1 else f"{i:04d}_{f:02d}.png"
                im.save(os.path.join(out, sub, name))
                count += 1
        print(f"{sub}: {count} images ({pal})")

    # isometric map tiles: 32 px wide, 4 bpp, with a 1 bpp mask (1 = opaque); the offsets come out one short at
    # each 64 KB (65535, 131070, ...): the pixels are at the offset as stored, the size is rounded up to whole rows
    # and the mask is at the corrected offset / 4, less one per 64 KB (found by checking the tiles)
    palette = celt_palette(celt_read(game_dir, "CELT01.PAL"))
    for side in CELT_TILES:
        grp = celt_read(game_dir, f"{side}GRP.DAT")
        msk = celt_read(game_dir, f"{side}MSK.DAT").ljust(len(grp) // 4 + 4, b"\0")
        index = celt_read(game_dir, f"{side}OFS.DAT")
        offsets = list(struct.unpack(f"<{len(index) // 4}I", index))
        sub = os.path.join(out, "tiles", side.lower())
        os.makedirs(sub, exist_ok=True)
        for i, (a, b) in enumerate(zip(offsets, offsets[1:])):
            h = (b - a + 15) // 16
            px = celt_planar(grp[a:a + 16 * h].ljust(16 * h, b"\0"), 32, h)
            fixed = a + a // 0xFFFF
            m = fixed // 4 - fixed // 0x10000
            rgba = bytearray()
            for y in range(h):
                for x in range(32):
                    c = px[y * 32 + x]
                    opaque = msk[m + y * 4 + x // 8] >> (7 - x % 8) & 1
                    rgba += bytes(palette[c * 3:c * 3 + 3]) + bytes([255 if opaque else 0])
            Image.frombytes("RGBA", (32, h), bytes(rgba)).save(os.path.join(sub, f"{i:03d}.png"))
        print(f"tiles/{side.lower()}: {len(offsets) - 1} tiles")

    # palettes as 16-colour swatches
    sub = os.path.join(out, "palettes")
    os.makedirs(sub, exist_ok=True)
    for name in sorted(os.listdir(game_dir)):
        if name.upper().endswith(".PAL"):
            im = Image.frombytes("P", (16, 1), bytes(range(16)))
            im.putpalette(celt_palette(celt_read(game_dir, name)))
            im.resize((256, 16), Image.NEAREST).save(os.path.join(sub, name[:-4] + ".png"))

    # icons and the CD-only movie as they are
    sub = os.path.join(out, "misc")
    os.makedirs(sub, exist_ok=True)
    for name in sorted(os.listdir(game_dir)):
        if name.upper().endswith((".ICO", ".AVI")):
            shutil.copyfile(os.path.join(game_dir, name), os.path.join(sub, name))


@click.command(help="把 *.KOB 轉成 MIDI")
@click.option("--game-dir", required=True, help="遊戲目錄")
@click.option("--out", required=True, help="輸出目錄")
def celt_music(game_dir, out):
    """
    ./dekoei.py celt music --game-dir ../games/celt-win --out ../games/celt-win/extract/music
    """
    os.makedirs(out, exist_ok=True)
    for name in sorted(os.listdir(game_dir)):
        if name.upper().endswith(".KOB"):
            midi = bytes(b ^ 0xF0 for b in celt_read(game_dir, name)[1:])
            assert midi[:4] == b"MThd", name
            with open(os.path.join(out, name[:-4] + ".mid"), "wb") as f:
                f.write(midi)
            print(name, "->", name[:-4] + ".mid")


celt.add_command(celt_art, "art")
celt.add_command(celt_music, "music")
