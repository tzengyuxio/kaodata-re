"""Every face size of one person in 信長の野望・大志 PK and 新生 PK (Steam), as raw RGBA -> samples/sizes/<id>/.

    python sizes_nobu15_16.py [FACE]   # default face 0, 織田信長

Both games keep faces in res_face.bin: an outer LINK whose entries are 7000-cell LINKs, one per size (see
notes/nobu15.md, notes/nobu16.md). Each cell is a GT1G0600 texture (BC3, format 0x5B, pixels from +0x38), cropped to
the cell's rectangle. A cell whose rectangle is 8x8 is empty.

    nobu15pk-win  RES_PK/res_face.bin, cells LWC compressed; PK replacements in entries 22-28 (+22 of the base entry)
    nobu16pk-win  RES/res_face.bin, cells in the "01 01" LZ4 wrapper; PK replacements in RES_PK/res_pk.bin 386-392
"""
import json
import os
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "../../dekoei"))
import ls11  # noqa: E402

GAMES = os.path.join(HERE, "../../games/steam")
OUT = os.path.join(HERE, "samples/sizes")

# id -> (title, base file, PK file, PK entry offset, [(entry, label, note)] largest first)
SETS = {
    "nobu15pk-win": ("信長の野望 大志 PK", "628890/RES_PK/res_face.bin", "628890/RES_PK/res_face.bin", 22, [
        (1, "tokudai", "特大 717×1020，res_face.bin 第 1 項，特定事件用"),
        (0, "dai", "大 360×360，第 0 項，情報畫面、會話、戰法"),
        (2, "chu", "中 306×180，第 2 項，主畫面"),
        (3, "sho", "小 162×162，第 3 項，外交畫面"),
        (6, "eye", "EYE 342×45，第 6 項，決戰的部隊列表"),
        (4, "gokusho", "極小 72×72，第 4 項，圖示"),
    ]),
    "nobu16pk-win": ("信長の野望 新生 PK", "1336980/RES/res_face.bin", "1336980/RES_PK/res_pk.bin", 386, [
        (2, "tokudai0", "特大 717×1020 第 0 組，res_face.bin 第 2 項，事件"),
        (3, "tokudai1", "特大 717×1020 第 1 組，第 3 項"),
        (0, "dai0", "大 512×512 第 0 組，第 0 項，情報畫面、演出"),
        (1, "dai1", "大 512×512 第 1 組，第 1 項"),
        (4, "chu", "中 306×180，第 4 項，選擇武將"),
        (6, "sho", "小 176×272，第 6 項，訊息"),
        (5, "gokusho", "極小 72×72，第 5 項，部隊列表"),
    ]),
}


def lz4_block(src: bytes, size: int) -> bytes:
    """A raw LZ4 block (no frame), decoded to size bytes."""
    out, i = bytearray(), 0
    while i < len(src):
        tok = src[i]
        i += 1
        n = tok >> 4
        if n == 15:
            while src[i] == 255:
                n += 255
                i += 1
            n += src[i]
            i += 1
        out += src[i:i + n]
        i += n
        if i >= len(src) or len(out) >= size:
            break
        back = src[i] | src[i + 1] << 8
        i += 2
        m = tok & 15
        if m == 15:
            while src[i] == 255:
                m += 255
                i += 1
            m += src[i]
            i += 1
        s = len(out) - back
        for k in range(m + 4):  # the match may overlap what it writes
            out.append(out[s + k])
    assert len(out) == size, (len(out), size)
    return bytes(out)


def unpack(c: bytes) -> bytes:
    if c[:4] == b"LWC\x1a":
        return ls11.lwc_decode(c)
    assert c[:2] == b"\x01\x01", c[:8].hex()
    size, packed = struct.unpack_from("<QQ", c, 8)
    return lz4_block(c[0x18:0x18 + packed], size)


def entries(f: bytes) -> list[bytes]:
    n = struct.unpack_from("<I", f, 4)[0]
    return [f[o:o + s] for o, s in (struct.unpack_from("<II", f, 0x10 + 8 * i) for i in range(n))]


def cell(link: bytes, i: int):
    """(w, h, data) of cell i of a 7000-cell LINK."""
    rects = struct.unpack_from("<I", link, 0x10)[0]
    x, y, w, h = struct.unpack_from("<4H", link, rects + 12 * i)
    assert (x, y) == (0, 0)
    o, s = struct.unpack_from("<II", link, 0x20 + 8 * i)
    return w, h, link[o:o + s]


def texture(t: bytes) -> Image.Image:
    """The one BC3 texture of a GT1G0600 blob."""
    assert t[:8] == b"GT1G0600" and struct.unpack_from("<I", t, 0x10)[0] == 1
    o = struct.unpack_from("<I", t, 0x0C)[0]
    o += struct.unpack_from("<I", t, o)[0]
    fmt, dim = t[o + 1], t[o + 2]
    assert fmt == 0x5B, hex(fmt)
    w, h = 1 << (dim & 15), 1 << (dim >> 4)
    p = o + 8 + (struct.unpack_from("<I", t, o + 8)[0] if t[o + 7] & 0x10 else 0)
    assert p == 0x38
    return Image.frombytes("RGBA", (w, h), t[p:p + w * h], "bcn", 3)


def face(link: bytes, i: int):
    w, h, c = cell(link, i)
    if (w, h) == (8, 8):
        return None
    return texture(unpack(c)).crop((0, 0, w, h))


def main(n: int):
    for gid, (title, base, pk, pk_off, sizes) in SETS.items():
        a = entries(open(os.path.join(GAMES, base), "rb").read())
        b = entries(open(os.path.join(GAMES, pk), "rb").read())
        folder = os.path.join(OUT, gid)
        os.makedirs(folder, exist_ok=True)
        notes = {}
        for k, (e, label, note) in enumerate(sizes, 1):
            im = face(b[pk_off + e], n)
            if im is not None:
                note += "（PK 換過的臉）"
            else:
                im = face(a[e], n)
            if im is None:
                print(gid, label, "empty")
                continue
            im.save(os.path.join(folder, f"{k:02d}_{label}.png"))
            notes[label] = note
            print(gid, label, im.size)
        with open(os.path.join(folder, "info.json"), "w", encoding="utf-8") as fp:
            json.dump({"title": title, "person": f"織田信長 (face {n})", "notes": notes}, fp, ensure_ascii=False,
                      indent=1)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
