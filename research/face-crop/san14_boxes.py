"""三國志14 PK: the box of every 484x512 face_NNNN_ctr on its 636x900 face_NNNN_a art, and the 4:5 crop made from
it -> data/san14_boxes.json.

    python san14_boxes.py [key ...]   # no keys: all 1489 (1470 faces and 19 second faces "0001b"…), in parallel;
                                      # keys: redo those

The base is the RGB of the _a sprite (the _a/_b/_c layers share one whole picture with its background, differing
only in alpha), opaque; the 1024x1024 _unique (no background) for the 15 faces whose _a is not theirs.

The ctr face frames head to chest, so the 4:5 crop (the user's rule, 2026-10-21) is a box of height S * h centered
on the ctr box (x, y, w, h), its top moved down by T of the height lost:
(x + (w - 0.8 * S * h) / 2, y + T * (1 - S) * h, 0.8 * S * h, S * h). S and T are the medians of 三國志12's 96x120
crop carried over to the 383 people drawn with the same picture in both games (san14_vs_san12.py), so the two
games' faces are framed alike.
"""
import json
import os
import re
import sys
from multiprocessing import Pool

import numpy as np

from align import align, rounded

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "../../dekoei"))
import sango  # noqa: E402

GAME = os.path.join(HERE, "../../games/steam/872410/")
OUT = os.path.join(HERE, "data/san14_boxes.json")
S, T = 0.554, 0.065
_sprites = {}


def sprites():
    if not _sprites:
        _sprites.update(sango.san14_face_sprites(GAME))
    return _sprites


def keys() -> list[str]:
    return sorted(m[1] for n in sprites() if (m := re.fullmatch(r"face_(\d{4}b?)_ctr", n)))


def art(key: str):
    return sango.san14_sprite(GAME, sprites()[f"face_{key}_a"]).convert("RGB").convert("RGBA")


def crop(b: dict) -> dict:
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    return {"x": round(x + (w - 0.8 * S * h) / 2, 3), "y": round(y + T * (1 - S) * h, 3), "w": round(0.8 * S * h, 3),
            "h": round(S * h, 3)}


def boxes(key: str) -> dict:
    ctr = sango.san14_sprite(GAME, sprites()[f"face_{key}_ctr"])
    assert ctr.size == (484, 512), (key, ctr.size)
    base = art(key)
    if base.size != (636, 900):
        # the collaboration faces (5000-5007, 5100-5105) share a placeholder texture (a starfield and a 曹操 card)
        # for _a/_b/_c; their widest real picture is the 1024x1024 _unique
        base = sango.san14_sprite(GAME, sprites()[f"face_{key}_unique"]).convert("RGB").convert("RGBA")
        b = rounded(align(base, ctr, np.arange(0.8, 2.2, 0.02), small_alpha=True))
        return {"base": "unique", "ctr": b, "crop": crop(b)}
    b = rounded(align(base, ctr, np.arange(0.6, 1.15, 0.02), small_alpha=True))
    if b["rmse"] <= 30:
        return {"base": "a", "ctr": b, "crop": crop(b)}
    # a few ctr reach past the art's edge (0056, 0127, 0261, 1102): match their middle, the part the crop keeps
    s = center(base, ctr)
    if s["rmse"] <= 30:
        return {"base": "a", "ctr": s, "crop": crop(s)}
    unique = sango.san14_sprite(GAME, sprites()[f"face_{key}_unique"])
    u = rounded(align(unique.convert("RGB").convert("RGBA"), ctr, np.arange(0.8, 2.2, 0.02), small_alpha=True))
    if u["rmse"] <= 30:
        # 1023: _a is another person, ctr and _unique agree
        return {"base": "unique", "ctr": u, "crop": crop(u)}
    # 0992: ctr is another person, _a and _unique agree; place a ctr-sized box from _unique's box on the art, whose
    # height and top keep a fixed ratio to the ctr box (0002, 0036, 0500: w 0.533, top 0.134 of _unique's width)
    v = center(base, unique)
    w = 0.533 * v["w"]
    g = {"x": round(v["x"] + (v["w"] - w) / 2, 3), "y": round(v["y"] + 0.134 * v["w"], 3), "w": round(w, 3),
         "h": round(w * 512 / 484, 3), "scale": round(w / 484, 3), "rmse": None, "from": "unique", "unique": v}
    return {"base": "a", "ctr": g, "crop": crop(g)}


def center(base, small):
    """the box of small on base, matched by its middle half (small may reach past base's edge)"""
    sw, sh = small.size
    x0, y0 = sw // 4, sh // 32
    b = align(base, small.crop((x0, y0, sw - x0, y0 + sh * 3 // 5)), np.arange(0.3, 1.4, 0.01), small_alpha=True,
              min_cover=0.9)
    s = b["scale"]
    return rounded({"x": b["x"] - x0 * s, "y": b["y"] - y0 * s, "w": sw * s, "h": sh * s, "scale": s, "rmse": b["rmse"]})


def main(ids):
    full = not ids
    ids = ids or keys()
    with Pool() as pool:
        out = dict(zip(ids, pool.map(boxes, ids, chunksize=4)))
    for k in ids[:5] if full else ids:
        print(k, out[k])
    data = {"faces": {}}
    if os.path.exists(OUT):
        with open(OUT) as f:
            data = json.load(f)
    data["about"] = (f"box (x, y, w, h) on the 636x900 face_NNNN_a art (RGB of its _a sprite; the 1024x1024 "
                     f"face_NNNN_unique where base says so) that resized to 484x512 matches face_NNNN_ctr, and the "
                     f"4:5 crop of height {S}h centered on it, its top {T} of the height lost below the box's; rmse on "
                     f"0-255 (none: placed from _unique's box, ctr being another person); keys are face numbers "
                     f"(\"b\": second faces)")
    data["faces"].update(out)
    with open(OUT, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main(sys.argv[1:])
