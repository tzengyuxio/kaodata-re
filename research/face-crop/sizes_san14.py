"""三國志14 PK (Steam) faces from 0002/ScreenLayout.rdb, every stored size of one face, for sizes.py.

    face_NNNN_unique  1024x1024 texture, sprite covers it all
    face_NNNN_a       2048x1024 texture holding three 636x900 sprites side by side: layers of one picture,
                      _a body (head cut out), _b a lower piece (belt), _c the head; where they overlap the
                      pixels agree, so they stack at the same origin (saved as "medium", layers in layers/)
    face_NNNN_ctr     512x512 texture, sprite covers the left 484x512

Texture names come from the sprite definition (type 0xF20DE437) stored right after each texture
(type 0xAFBEC60C) in the .rdb.bin files; see notes/san14.md.

    python sizes_san14.py [FACE]    (default 2, 関羽)
"""
import json
import os
import re
import struct
import sys
import zlib

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(HERE, "../../games/steam/872410/0002/")
OUT = os.path.join(HERE, "samples/sizes/san14pk-win")
TEXTURE, SPRITES = 0xAFBEC60C, 0xF20DE437
BCN = {0x5B: 3}  # GT1G format -> PIL "bcn" decoder number (BC3)


def entries(rdb: str) -> list[tuple[int, int, int, tuple[int, int, int]]]:
    """(ktid, type, file size, (bin number or -1, offset, stored size)) of every entry with a location."""
    idx = open(rdb, "rb").read()
    n = struct.unpack_from("<I", idx, 0x10)[0]
    p, out = 0x20, []
    for _ in range(n):
        assert idx[p:p + 8] == b"IDRK0000"
        size, slen, fsize = struct.unpack_from("<QQQ", idx, p + 8)
        ktid, typ = struct.unpack_from("<II", idx, p + 0x24)
        # the location string "offset@size[#bin]" (hex) ends the entry
        m = re.fullmatch(r"([0-9a-f]+)@([0-9a-f]+)(?:#([0-9a-f]+))?",
                         idx[p + size - slen:p + size].rstrip(b"\0").decode())
        if m:
            out.append((ktid, typ, fsize, (int(m[3], 16) if m[3] else -1, int(m[1], 16), int(m[2], 16))))
        p = (p + size + 3) & ~3
    return out


_files = {}


def read(rdb: str, fsize: int, loc: tuple[int, int, int]) -> bytes:
    """One file: an IDRK header, then u32 length + zlib chunks (a zero length is skipped)."""
    b, off, size = loc
    name = rdb + ".bin" + ("" if b < 0 else str(b))
    f = _files.setdefault(name, open(name, "rb"))
    f.seek(off)
    raw = f.read(size)
    total, comp = struct.unpack_from("<QQ", raw, 8)
    q, out = total - comp, b""
    while len(out) < fsize:
        k = struct.unpack_from("<I", raw, q)[0]
        q += 4
        if k:
            out += zlib.decompress(raw[q:q + k])
            q += k
    return out


def sprites(t: bytes) -> list[tuple[str, tuple[float, float, float, float]]]:
    """(name, (u0, v0, u1, v1)) of a sprite definition: u32 count, then 64-byte name + 10 u32 each.

    The 10 u32 are 0, four corners (u, v) as floats (top left, top right, bottom left, bottom right), 1.
    """
    out = []
    for i in range(struct.unpack_from("<I", t, 0)[0]):
        r = t[4 + 104 * i:4 + 104 * (i + 1)]
        c = struct.unpack_from("<8f", r, 68)
        out.append((r[:64].split(b"\0")[0].decode(), (c[0], c[1], c[6], c[7])))
    return out


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
        out.append(Image.frombytes("RGBA", (w, h), t[p:p + w * h], "bcn", BCN[fmt]))  # BC3: 1 byte per pixel
    return out


def face(num: int) -> dict[str, Image.Image]:
    """Every sprite of face_NNNN_* (not the second faces face_NNNNb_*), cut from its texture."""
    rdb = GAME + "ScreenLayout.rdb"
    es = entries(rdb)
    texs = sorted((e[3][0], e[3][1], e) for e in es if e[1] == TEXTURE)
    want = re.compile(rf"face_{num:04d}_")
    out = {}
    for e in es:
        if e[1] != SPRITES:
            continue
        sp = sprites(read(rdb, e[2], e[3]))
        if not any(want.match(s) for s, _ in sp):
            continue
        # the texture is the one stored right before its sprite definition
        b, off = e[3][0], e[3][1]
        tex = max(t for t in texs if t[0] == b and t[1] < off)[2]
        ims = textures(read(rdb, tex[2], tex[3]))
        im = ims[0]
        print(f"{[s for s, _ in sp]}: {len(ims)} texture(s) {[i.size for i in ims]}, using {im.size}")
        for name, (u0, v0, u1, v1) in sp:
            box = (round(u0 * im.width), round(v0 * im.height), round(u1 * im.width), round(v1 * im.height))
            out[name] = im.crop(box)
            print(f"  {name} {box} -> {out[name].size}, alpha bbox {out[name].getchannel('A').getbbox()}")
    return out


if __name__ == "__main__":
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    ims = face(num)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "layers"), exist_ok=True)
    pre = f"face_{num:04d}_"
    medium = Image.new("RGBA", ims[pre + "a"].size)
    for k in "abc":
        ims[pre + k].save(os.path.join(OUT, "layers", f"{k}.png"))
        medium = Image.alpha_composite(medium, ims.pop(pre + k))
    ims[pre + "medium"] = medium
    labels = sorted(ims, key=lambda k: (-ims[k].width * ims[k].height, k))
    for i, name in enumerate(labels, 1):
        ims[name].save(os.path.join(OUT, f"{i:02d}_{name[len(pre):]}.png"))
