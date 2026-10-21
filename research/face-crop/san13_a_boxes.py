"""三國志13 PK: the box of every 72x72 kao_s face on its 633x900 kao_a picture, and the 4:5 box cut from it ->
data/san13_a_boxes.json.

    python san13_a_boxes.py [picture-item ...]   # no items: all 1467 (in parallel, a few minutes); items: redo those

kao_a is three BC3 layers whose RGB are the same whole picture with its background (they differ only in alpha), so
the RGB of the first layer is the base, opaque. The 4:5 box is the user's rule (notes/san13.md, 2026-10-19), which
only scales with the box: (x + 0.1w, y + 0.05w, 0.8w, w).
"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

import san13_faces as faces
from align import align, rounded

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/san13_a_boxes.json")


def base(i: int):
    return faces.textures(faces._item(8, i))[0].crop((0, 0, 633, 900)).convert("RGB").convert("RGBA")


def boxes(i: int) -> dict:
    art = base(i)
    if np.asarray(art).std() < 3:
        # item 1266 (the last 新武將) has a blank kao_a; its 1024x1024 kao_l has the picture
        b = rounded(align(faces.large(i), faces.small(i), np.arange(2.5, 8.0, 0.02), small_alpha=True))
        name = "kao_l"
    else:
        b = rounded(align(art, faces.small(i), np.arange(2.0, 5.0, 0.02), small_alpha=True))
        name = "kao_a"
    x, y, w = b["x"], b["y"], b["w"]
    return {"base": name, "s72": b, "crop": {"x": round(x + 0.1 * w, 3), "y": round(y + 0.05 * w, 3), "w": round(0.8 * w, 3),
                               "h": round(w, 3)}}


def main(ids):
    full = not ids
    ids = ids or list(range(faces.count()))
    faces._item(8, 0), faces.small(0)  # load both entries before forking
    with Pool() as pool:
        out = dict(zip(ids, pool.map(boxes, ids, chunksize=8)))
    for i in ids[:5] if full else ids:
        print(i, out[i])
    if not full and os.path.exists(OUT):
        # some items: update them in the file
        with open(OUT) as f:
            data = json.load(f)
        data["faces"].update({str(i): b for i, b in out.items()})
        with open(OUT, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
    elif full:
        with open(OUT, "w") as f:
            json.dump({"about": "box (x, y, w, h) on the 633x900 kao_a picture (RGB of its first layer) that resized "
                                "to 72x72 matches kao_s (on the 1024x1024 kao_l where base says so: a blank kao_a), and the 4:5 crop (x + 0.1w, y + 0.05w, 0.8w, w); rmse on "
                                "0-255; keys are face items (items of pk/DATA0.S13 entries 8 and 20)",
                       "faces": {str(i): b for i, b in out.items()}}, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]])
