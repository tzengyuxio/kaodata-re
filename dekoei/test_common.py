import csv
import random
import struct

from PIL import Image

from common import cstr, fold_kana, read_file, u16, u32, write_csv, write_dict_csv
from gfx import decode_planar, gt1g_count, gt1g_header, gt1g_texture, texture_image


def test_u16_u32():
    b = bytes([0x34, 0x12, 0x78, 0x56, 0xFF])
    assert u16(b, 0) == 0x1234
    assert u16(b, 1) == 0x7812
    assert u32(b, 0) == 0x56781234


def test_read_file(tmp_path):
    (tmp_path / "A.DAT").write_bytes(b"\x01\x02")
    assert read_file(tmp_path, "A.DAT") == b"\x01\x02"
    assert read_file(tmp_path / "A.DAT") == b"\x01\x02"


def test_cstr():
    assert cstr("織田信長".encode("cp932") + b"\0junk\0") == "織田信長"
    assert cstr("劉備".encode("big5") + b"\0", "big5") == "劉備"
    assert cstr(b"\x82\xa0\x82\0", errors="replace") == "あ�"
    assert cstr("ｵﾀﾞ\0".encode("cp932"), nfkc=True) == "オダ"
    assert cstr(b"abc") == "abc"


def test_fold_kana():
    assert fold_kana("ｵﾀﾞﾉﾌﾞﾅｶﾞ") == "おだのぶなが"
    assert fold_kana("ｵﾀﾞ", katakana=True) == "オダ"
    assert fold_kana("ｰ") == "ー"
    assert fold_kana("ｹ") == "け"
    assert fold_kana("漢字") == "漢字"


def test_write_csv(tmp_path):
    path = tmp_path / "sub" / "t.csv"
    assert write_csv(str(path), ["a", "b"], [(1, "x"), (2, "y")]) == 2
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and raw.endswith(b"2,y\r\n")
    assert list(csv.reader(open(path, encoding="utf-8-sig"))) == [["a", "b"], ["1", "x"], ["2", "y"]]


def test_write_dict_csv(tmp_path):
    path = str(tmp_path / "d.csv")
    write_dict_csv(path, [{"a": 1}, {"a": 2, "b": 3}])
    assert list(csv.reader(open(path, encoding="utf-8-sig"))) == [["a", "b"], ["1", ""], ["2", "3"]]
    write_dict_csv(path, [{"a": 1, "c": 9}], ["a"])
    assert list(csv.reader(open(path, encoding="utf-8-sig"))) == [["a"], ["1"]]


def _planar_reference(data, w, h, planes):
    """Bit by bit: pixel x of row y takes bit (7 - x % 8) of byte (y * w // 8 + x // 8) * planes + p as bit p."""
    return bytearray(sum(((data[(y * w // 8 + x // 8) * planes + p] >> (7 - x % 8)) & 1) << p for p in range(planes))
                     for y in range(h) for x in range(w))


def test_decode_planar():
    rnd = random.Random(1)
    for planes, w, h in ((3, 64, 40), (4, 32, 24), (4, 96, 8), (1, 16, 2)):
        data = bytes(rnd.randrange(256) for _ in range(w * h // 8 * planes + 5))
        assert decode_planar(data, 0, w, h, planes) == _planar_reference(data, w, h, planes)
        assert decode_planar(b"\0\0\0" + data, 3, w, h, planes) == _planar_reference(data, w, h, planes)


def _gt1g(fmt, log2w, log2h, px, extra=b""):
    """A one-texture GT1G0600 set: header, table at 0x20, texture header, optional extra header, pixels."""
    head = bytearray(b"GT1G0600" + bytes(24))
    struct.pack_into("<I", head, 0x0C, 0x20)
    struct.pack_into("<I", head, 0x10, 1)
    table = struct.pack("<I", 4)
    tex = bytes([0, fmt, log2h << 4 | log2w, 0, 0, 0, 0, 0x10 if extra else 0])
    return bytes(head) + table + tex + (struct.pack("<I", 4 + len(extra)) + extra if extra else b"") + px


def test_gt1g_bgra():
    px = bytes([10, 20, 30, 40]) * 8  # B, G, R, A
    t = _gt1g(0x01, 2, 1, px)
    assert gt1g_header(t) == (0x01, 4, 2, 0x20 + 4 + 8)
    im = gt1g_texture(t)
    assert im.size == (4, 2) and im.getpixel((0, 0)) == (30, 20, 10, 40)
    t = _gt1g(0x01, 2, 1, px, extra=b"\xAA" * 8)
    assert gt1g_texture(t).getpixel((3, 1)) == (30, 20, 10, 40)


def test_texture_bc1():
    # one 4x4 BC1 block: colour 0 = white, colour 1 = black, all indexes 0
    block = struct.pack("<HHI", 0xFFFF, 0x0000, 0)
    im = texture_image(0x06, 4, 4, block + b"extra")
    assert im.getpixel((2, 2)) == (255, 255, 255, 255)
    assert texture_image(0x59, 4, 4, block).tobytes() == im.tobytes()
    assert isinstance(im, Image.Image)


def test_gt1g_sized():
    # dim 0: width and height are the u32s at +0x14 of the texture header (+0xC of the extra header)
    extra = bytes(8) + struct.pack("<2I", 3, 2)
    t = _gt1g(0x01, 0, 0, bytes([1, 2, 3, 4]) * 6, extra=extra)
    assert gt1g_count(t) == 1
    assert gt1g_header(t)[1:3] == (3, 2)
    assert gt1g_texture(t).size == (3, 2)
