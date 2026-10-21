"""Every stored size of one face (関羽, face 2 in all three) of 三國志VIII / IX / X PK (Steam) -> samples/sizes/<id>/.

    san8pk-win   g_maindy.s8 (KOEI archive) item n: 160x180, item 846 + n: 64x80; palette p_main.s8 item 4 (RGBX)
    san9pk-win   G_FaceL.s9 240x240, G_FaceS.s9 64x80, G_FaceT.s9 32x40 (PK faces 786- in G_Fac?PK.s9);
                 u32 file size, then per face u32 size, u32 pitch, u32 w, u32 h and 8-bit pixels; palette P_Face.s9 #0
    san10pk-win  Grp/GrpFaceL.s10 240x240, GrpFaceS.s10 64x80, GrpFaceT.s10 32x40 (SAN10GRP), each entry with its
                 own BGRX palette; D_FacTbl.s10 table 0 maps the face code to the entry (L and T have the same order)

Colour 0 is the key colour (green) in all three; pixels using it would be transparent, but no face uses it.

    python sizes_san8_10.py
"""
import json
import os
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "../../dekoei"))
import sango  # noqa: E402

STEAM = os.path.join(HERE, "../../games/steam")
OUT = os.path.join(HERE, "samples/sizes")
NAME = "関羽"


def rgba(w, h, px, rgb):
    """8-bit pixels + 256 x (r, g, b) -> RGBA, colour 0 transparent."""
    im = Image.frombytes("P", (w, h), px[:w * h])
    im.putpalette([c for col in rgb for c in col])
    a = Image.frombytes("L", (w, h), bytes(0 if p == 0 else 255 for p in px[:w * h]))
    out = im.convert("RGBA")
    out.putalpha(a)
    return out, px[:w * h].count(0)


def face_of(persons):
    return next(p["face"] for p in persons if p["name"] == NAME)


def san8():
    game = os.path.join(STEAM, "628040")
    face = face_of(sango.load_san8_persons(os.path.join(game, "D_Sce.s8")))
    with open(os.path.join(game, "g_maindy.s8"), "rb") as f:
        items = sango.koei_archive(f.read())
    with open(os.path.join(game, "p_main.s8"), "rb") as f:
        pal = sango.koei_archive(f.read())[4]
    rgb = [tuple(pal[i * 4:i * 4 + 3]) for i in range(256)]
    n = sango.SAN8_FACES
    return face, [("160x180", 160, 180, items[face], rgb, f"g_maindy.s8 第 {face} 項"),
                  ("64x80", 64, 80, items[n + face], rgb, f"g_maindy.s8 第 {n + face} 項")]


def san9_file(path, k):
    """Face k of a SAN9 face file: (w, h, pixels)."""
    with open(path, "rb") as f:
        data = f.read()
    o = 4
    for _ in range(k):
        o += struct.unpack_from("<I", data, o)[0]
    size, pitch, w, h = struct.unpack_from("<4I", data, o)
    assert pitch == w and size == 16 + w * h
    return w, h, data[o + 16:o + size]


def san9():
    game = os.path.join(STEAM, "628050")
    face = face_of(sango.load_san9_persons(game))
    assert face < 786  # PK faces would be in G_Fac?PK.s9
    normal, _ = sango.load_san9_palettes(os.path.join(game, "P_Face.s9"))
    rgb = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in normal]
    out = []
    for label in ["FaceL", "FaceS", "FaceT"]:
        w, h, px = san9_file(os.path.join(game, f"G_{label}.s9"), face)
        out.append((label, w, h, px, rgb, f"G_{label}.s9 第 {face} 張"))
    return face, out


def san10():
    game = os.path.join(STEAM, "628060")
    face = face_of(sango.load_san10_persons(os.path.join(game, "San10WPK.exe"),
                                            os.path.join(game, "Scenario/ScePK000.s10")))
    entry = sango.load_san10_face_table(os.path.join(game, "D_FacTbl.s10"))[face]
    out = []
    for label in ["FaceL", "FaceS", "FaceT"]:
        w, h, px, bgrx = sango.load_san10_grp(os.path.join(game, f"Grp/Grp{label}.s10"))[entry]
        rgb = [(bgrx[i * 4 + 2], bgrx[i * 4 + 1], bgrx[i * 4]) for i in range(256)]
        out.append((label, w, h, px, rgb, f"Grp{label}.s10 第 {entry} 項"))
    return face, out


GAMES = {"san8pk-win": ("三國志VIII PK", san8), "san9pk-win": ("三國志IX PK", san9), "san10pk-win": ("三國志X PK", san10)}

if __name__ == "__main__":
    for gid, (title, fn) in GAMES.items():
        face, sizes = fn()
        folder = os.path.join(OUT, gid)
        os.makedirs(folder, exist_ok=True)
        notes = {}
        for k, (label, w, h, px, rgb, note) in enumerate(sizes, 1):
            im, keyed = rgba(w, h, px, rgb)
            im.save(os.path.join(folder, f"{k}_{label}.png"))
            notes[label] = note + (f"，{keyed} 點是去背色" if keyed else "")
            print(gid, label, w, h, "key pixels", keyed)
        with open(os.path.join(folder, "info.json"), "w", encoding="utf-8") as f:
            json.dump({"title": title, "person": f"{NAME} (face {face})", "notes": notes}, f, ensure_ascii=False,
                      indent=1)
