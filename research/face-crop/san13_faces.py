"""三國志13 PK (Steam) faces from pk/DATA0/1.S13, by picture index (the item of each face entry).

    kao_a  item 8   633x900 in three layers (body, a lower piece, head), each at the top left of a 1024 texture
    kao_l  item 13  1024x1024
    kao_m  item 18  186x90 (in 256x128)
    kao_s  item 20  72x72 (in 128x128)
    kao_ss item 22  96x96 atlas: 2048x1024 textures of 20 x 10 cells (the last one 1024x1024, 10 x 10), pitch 100
"""
import os
import struct
import sys

from PIL import Image

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../dekoei"))
import sango  # noqa: E402

GAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../games/san13pk-win/")
BCN = {6: 1, 8: 3}  # GT1G format -> PIL "bcn" decoder number (DXT1, BC3)


def textures(t: bytes) -> list[Image.Image]:
    """Every texture of a GT1G0600 blob."""
    header, n = struct.unpack_from("<II", t, 0x0C)
    out = []
    for k in range(n):
        o = header + struct.unpack_from("<I", t, header + 4 * k)[0]
        fmt, dim = t[o + 1], t[o + 2]
        w, h = 1 << (dim & 15), 1 << (dim >> 4)
        extra = struct.unpack_from("<I", t, o + 8)[0] if t[o + 7] & 0x10 else 0
        p = o + 8 + extra
        size = w * h if fmt == 8 else w * h // 2  # BC3 is 1 byte per pixel, DXT1 half a byte
        out.append(Image.frombytes("RGBA", (w, h), t[p:p + size], "bcn", BCN[fmt]))
    return out


_items, _atlas = {}, []


def _item(entry: int, i: int) -> bytes:
    if entry not in _items:
        _items[entry] = sango.san13_items(sango.san13_entry(GAME, entry))
    t = _items[entry][i]
    # a few items (kao_l 507) are "zp1\x02", not zlib, and not decoded yet
    assert t[:4] != b"zp1\x02", f"item {i} of entry {entry} is zp1\\x02"
    return sango.san13_unzip(t)


def count() -> int:
    return len(sango.san13_items(sango.san13_entry(GAME, 20)))


def large(i: int) -> Image.Image:
    return textures(_item(13, i))[0]


def strip(i: int) -> Image.Image:
    return textures(_item(18, i))[0].crop((0, 0, 186, 90))


def small(i: int) -> Image.Image:
    return textures(_item(20, i))[0].crop((0, 0, 72, 72))


def medium(i: int) -> Image.Image:
    if not _atlas:
        _atlas.extend(textures(sango.san13_entry(GAME, 22)))
    t, r = divmod(i, 200) if i < 1400 else (7, i - 1400)
    y, x = divmod(r, 20 if t < 7 else 10)
    return _atlas[t].crop((x * 100, y * 100, x * 100 + 96, y * 100 + 96))
