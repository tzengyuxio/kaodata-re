"""Every face size of one person (関羽) as the game stores it, for sizes.py -> samples/sizes/<id>/<NN>_<label>.png.

    python sizes_san11_13.py   # san11pk-win, san12pk-win, and kao_a of san13pk-win

    san11pk-win  media/face/San11Face00.fce: entry k 240x240, entry 2200 + 2k + d 64x80 (d 0 left, 1 right), 24 bit
    san12pk-win  Data/KAO_W_L, KAO_W_S, KAO_F_M, KAO_F_S.S12: item k, 32 bit BGRA cropped by the rect table
    san13pk-win  kao_a (item 8 of pk/DATA0.S13) only; the other four sizes are already there (san13_faces.py)

kao_a is three BC3 textures (body, a lower piece, head), each holding its part at the top left of a 1024x1024; the
parts overlap with the same RGB where they do (they are cut from one 633x900 picture), so they are stacked at 0, 0.
"""
import json
import os
import struct

from PIL import Image

import san13_faces

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "samples/sizes")
SAN11 = os.path.join(HERE, "../../games/san11pk-win/San11Face00.fce")
SAN12 = os.path.join(HERE, "../../games/san12pk-win/")
SAN11_FACE = 2  # 関羽's face code (Scen*.s11 +0x35)
SAN12_FACE = 2  # 関羽's face number (Scenario bit 482)
SAN13_PICTURE = 137  # 関羽's first picture
SAN12_FILES = [("kao_w_l", "Data/KAO_W_L.S12"), ("kao_w_s", "Data/KAO_W_S.S12"), ("kao_f_m", "Data/KAO_F_M.S12"),
               ("kao_f_s", "Data/KAO_F_S.S12")]


def san11_entry(data: bytes, slot: int) -> Image.Image:
    """A WFTX0010 entry of the .fce as RGBA (24 bit has no alpha)."""
    n1, n2 = struct.unpack_from("<II", data, 12)
    start, size = struct.unpack_from("<II", data, 20 + 4 * n1 + 8 * slot)
    assert size and data[start:start + 8] == b"WFTX0010"
    w, h, bpp = struct.unpack_from("<HHB", data, start + 16)
    assert bpp == 24
    return Image.frombytes("RGB", (w, h), data[start + 24:start + 24 + w * h * 3], "raw", "BGR").convert("RGBA")


def san12_item(path: str, k: int) -> Image.Image:
    """Item k of a KAO_*.S12 LINK, cropped by its rect; alpha as stored."""
    with open(path, "rb") as f:
        head = f.read(0x20)
        assert head[:4] == b"LINK"
        rects = struct.unpack_from("<I", head, 0x10)[0]
        f.seek(0x20 + 8 * k)
        start, size = struct.unpack("<II", f.read(8))
        f.seek(rects + 12 * k)
        x, y, w, h = struct.unpack("<4H", f.read(8))
        f.seek(start)
        t = f.read(size)
    assert t[:8] == b"GT1G0500"
    width, height = 1 << (t[0x26] & 15), 1 << (t[0x26] >> 4)
    im = Image.frombytes("RGBA", (width, height), t[0x2C:0x2C + width * height * 4], "raw", "BGRA")
    return im.crop((x, y, x + w, y + h))


def kao_a(i: int) -> Image.Image:
    out = Image.new("RGBA", (633, 900))
    for layer in san13_faces.textures(san13_faces._item(8, i)):
        out = Image.alpha_composite(out, layer.crop((0, 0, 633, 900)))
    return out


def save(gid, ims, info=None):
    folder = os.path.join(OUT, gid)
    os.makedirs(folder, exist_ok=True)
    for name, im in ims.items():
        im.save(os.path.join(folder, name + ".png"))
        print(gid, name, im.size)
    if info:
        with open(os.path.join(folder, "info.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=1)


def main():
    with open(SAN11, "rb") as f:
        data = f.read()
    left = 2200 + 2 * SAN11_FACE if SAN11_FACE < 1100 else 4400 + 2 * (SAN11_FACE - 1100)
    save("san11pk-win", {"1_face_l": san11_entry(data, SAN11_FACE), "2_face_s_left": san11_entry(data, left),
                         "3_face_s_right": san11_entry(data, left + 1)},
         {"title": "三國志11 PK", "person": f"関羽 (face {SAN11_FACE})",
          "notes": {"face_l": f"San11Face00.fce 第 {SAN11_FACE} 項，24 bit 無 alpha",
                    "face_s_left": f"第 {left} 項（朝左），24 bit",
                    "face_s_right": f"第 {left + 1} 項（朝右，重畫的，不是鏡像）"}})

    save("san12pk-win", {f"{n}_{label}": san12_item(os.path.join(SAN12, path), SAN12_FACE)
                         for n, (label, path) in enumerate(SAN12_FILES, 1)},
         {"title": "三國志12 PK", "person": f"関羽 (face {SAN12_FACE})",
          "notes": {label: f"{os.path.basename(path)} 第 {SAN12_FACE} 項，32 bit BGRA，依 rect 表裁"
                    for label, path in SAN12_FILES}})

    # only kao_a is new here; the other four files and their notes are kept
    save("san13pk-win", {"0_kao_a": kao_a(SAN13_PICTURE)},
         {"title": "三國志13 PK", "person": f"関羽 (picture {SAN13_PICTURE})",
          "notes": {"kao_a": "pk/DATA0.S13 第 8 項，身體＋下半身＋頭三層 BC3 疊在 (0,0)",
                    "kao_l": "第 13 項，1024×1024 BC3",
                    "kao_m": "第 18 項，186×90（256×128 DXT1），有背景",
                    "kao_ss": "第 22 項，96×96 圖集的一格，有背景",
                    "kao_s": "第 20 項，72×72（128×128 BC3）"}})


if __name__ == "__main__":
    main()
