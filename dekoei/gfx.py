"""Picture formats shared by several games: interleaved bit planes and the GT1G texture sets of the Windows-era
titles (docs/backlog/code-consolidation.md)."""
import struct

from PIL import Image


def decode_planar(data: bytes, offset: int, w: int, h: int, planes: int) -> bytearray:
    """Byte-interleaved planes: every `planes` bytes hold 8 pixels, byte k = bit k, MSB leftmost.
    (utils.to_3bpp_indexes is the other order: its first byte is bit 2.)"""
    out = bytearray(w * h)
    pos = offset
    for i in range(w * h // 8):
        for p in range(planes):
            b = data[pos + p]
            if b:
                for k in range(8):
                    if b & (0x80 >> k):
                        out[i * 8 + k] |= 1 << p
        pos += planes
    return out


# GT1G texture formats: block-compressed (Pillow's "bcn" decoder number) or 0x01, 32-bit B, G, R, A
GT1G_BCN = {0x06: 1, 0x07: 2, 0x08: 3, 0x59: 1, 0x5B: 3}


def texture_image(fmt: int, w: int, h: int, px: bytes) -> Image.Image:
    """RGBA image of one GT1G texture's pixels. Format 0x01 is B, G, R, A (checked against the pictures of 信長16,
    大航海IV and 三國志14)."""
    if fmt in GT1G_BCN:
        n = GT1G_BCN[fmt]
        return Image.frombytes("RGBA", (w, h), px[:w * h // 2 if n == 1 else w * h], "bcn", n)
    if fmt == 0x01:
        return Image.frombytes("RGBA", (w, h), px[:4 * w * h], "raw", "BGRA")
    raise ValueError(f"texture format {fmt:#x}")


def gt1g_header(t: bytes, k: int = 0) -> tuple[int, int, int, int]:
    """(format, width, height, pixel offset) of texture k of a GT1G set: +0xC the offset of a table of u32 header
    offsets (+0x10 the count); each 8-byte header has +1 the format, +2 log2 height << 4 | log2 width, and +7 bit 4 set
    when an extra header follows (its size the next u32)."""
    assert t[:4] == b"GT1G", t[:8]  # GT1G0600; 三國志14 also has GT1G4600 with the same layout
    table = struct.unpack_from("<I", t, 0x0C)[0]
    o = table + struct.unpack_from("<I", t, table + 4 * k)[0]
    fmt, dim = t[o + 1], t[o + 2]
    start = o + 8 + (struct.unpack_from("<I", t, o + 8)[0] if t[o + 7] & 0x10 else 0)
    if dim == 0:  # not a power of two (大航海IV, 太閤V): u32 width and height at +0x14 of the extra header
        return fmt, *struct.unpack_from("<2I", t, o + 0x14), start
    return fmt, 1 << (dim & 15), 1 << (dim >> 4), start


def gt1g_count(t: bytes) -> int:
    return struct.unpack_from("<I", t, 0x10)[0]


def gt1g_texture(t: bytes, k: int = 0) -> Image.Image:
    """Texture k (its top mip) of a GT1G set as RGBA."""
    fmt, w, h, start = gt1g_header(t, k)
    return texture_image(fmt, w, h, t[start:])
