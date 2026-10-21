"""信長の野望 天下創世 PK, 革新 PK, 天道 PK (Steam): one person's face at every size the game stores, as raw RGBA PNGs
for sizes.py -> samples/sizes/<id>/<NN>_<label>.png and info.json.

    python sizes_nobu11_13.py            # 織田信長, face 0 in all three games

    nobu11pk-win  grp/KAO_S/M/L.N11  56x70 / 96x120 / 240x240, F11N of 8-bit T11N with their own palette
    nobu12pk-win  Grp/KAO_S/M/L.N12  56x70 / 96x120 / 240x240, F11N of BGRA T11N
    nobu13pk-win  grp/KAO_S/M/L.N13  60x60 / 96x120 / 240x240, LINK of GT1G0600 BGRA (koei_games.load_nobu13_win_kao)
"""
import json
import os
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "../../dekoei"))
import koei_games  # noqa: E402

STEAM = os.path.join(HERE, "../../games/steam")
OUT = os.path.join(HERE, "samples/sizes")
FACE = 0  # 織田信長: slot 339 / 338 / 338 of the persons, face 0 (nobu13 face code 0 -> entry 0)


def f11n_face(path: str, i: int) -> Image.Image:
    """Entry i of an F11N archive: 'T11N', u32 width, height, texture width, height, u16 format (9: 256 x B, G, R, X
    palette then 8-bit pixels; 0x21: B, G, R, A pixels), cropped to width x height from the top left."""
    with open(path, "rb") as f:
        head = f.read(0x14 + 20 * (i + 1))
        assert head[:4] == b"F11N"
        offset, = struct.unpack_from("<I", head, 0x14 + 20 * i + 8)
        f.seek(offset)
        t = f.read(22)
        assert t[:4] == b"T11N"
        w, h, tw, th = struct.unpack_from("<4I", t, 4)
        if t[20] == 9:
            pal = f.read(1024)
            im = Image.frombytes("P", (tw, th), f.read(tw * th))
            im.putpalette(bytes(v for c in range(256) for v in (pal[4 * c + 2], pal[4 * c + 1], pal[4 * c])))
            im = im.convert("RGBA")
        else:
            assert t[20] == 0x21
            im = Image.frombytes("RGBA", (tw, th), f.read(tw * th * 4), "raw", "BGRA")
    return im.crop((0, 0, w, h))


def link_face(path: str, i: int) -> Image.Image:
    w, h, rgba = koei_games.load_nobu13_win_kao(path)[i]
    return Image.frombytes("RGBA", (w, h), rgba)


GAMES = {
    "nobu11pk-win": ("信長の野望 天下創世 PK", "628140/grp/KAO_{}.N11", f11n_face, "8 bit 自帶色盤"),
    "nobu12pk-win": ("信長の野望 革新 PK", "363090/Grp/KAO_{}.N12", f11n_face, "BGRA"),
    "nobu13pk-win": ("信長の野望 天道 PK", "363110/grp/KAO_{}.N13", link_face, "BGRA"),
}


def main():
    for gid, (title, pattern, read, depth) in GAMES.items():
        folder = os.path.join(OUT, gid)
        os.makedirs(folder, exist_ok=True)
        notes = {}
        for n, s in enumerate("LMS", 1):
            label = f"KAO_{s}"
            name = pattern.format(s)
            im = read(os.path.join(STEAM, name), FACE)
            im.save(os.path.join(folder, f"{n}_{label}.png"))
            notes[label] = f"{os.path.basename(name)} 第 {FACE} 項，{depth}"  # short: sizes.py does not wrap
            print(gid, label, im.size, flush=True)
        with open(os.path.join(folder, "info.json"), "w", encoding="utf-8") as fp:
            json.dump({"title": title, "person": f"織田信長 (face {FACE})", "notes": notes}, fp, ensure_ascii=False,
                      indent=1)


if __name__ == "__main__":
    main()
