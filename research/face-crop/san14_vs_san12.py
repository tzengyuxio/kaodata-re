"""三國志14 PK vs 三國志12 PK: people drawn with the same picture in both. 三國志12's 360x512 KAO_W_L is matched on
三國志14's 636x900 face_NNNN_a art, its 4:5 crop (data/san12_boxes.json) carried over, and that box written in terms
of the 三國志14 ctr box (x, y, w, h) as san14_boxes.py's rule: height s * h, top t of the height lost, and the
center's offset dx in units of w -> samples/san14_vs_san12.png (三國志12, 三國志14 now, 三國志14 with 三國志12's box).

    python san14_vs_san12.py [face ...]   # face numbers, the same in both games (default: 楊奉 伊籍 袁尚 曹叡 華雄),
                                          # or "N12:N14" pairs
    python san14_vs_san12.py --names      # every person in both datasets (kaodata data/), by name
"""
import json
import os
import statistics
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import san12_boxes
import san14_boxes
from align import align, rounded

HERE = os.path.dirname(os.path.abspath(__file__))
PEOPLE = {0: "楊奉", 31: "伊籍", 34: "袁尚", 59: "曹叡", 8: "華雄"}
CROP = (96, 120)


def cut(im, b):
    return im.convert("RGB").resize(CROP, Image.LANCZOS, box=(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]))


def by_name():
    """(san12 face, san14 face, name) of the people in both datasets (kaodata data/), by name."""
    def faces(d):
        with open(os.path.expanduser(f"~/works/kaodata/data/{d}/dataset.json")) as f:
            m = json.load(f)
        return {c["name"]: int(m["portraits"][c["face"]["portrait"]]["code"], 16) for c in m["characters"]}
    f12, f14 = faces("san12pk-win"), faces("san14pk-win")
    return [(f12[n], f14[n], n) for n in sorted(f12) if n in f14]


_large12 = {}


def relation(pair):
    """(found entry, the three 96x120 cuts) for one (san12 face, san14 face, name)."""
    n12, num, name = pair
    if not _large12:
        _large12.update(san12_boxes.faces("KAO_W_L"))
    with open(os.path.join(HERE, "data/san12_boxes.json")) as f:
        b12 = json.load(f)["faces"][str(n12)]
    with open(os.path.join(HERE, "data/san14_boxes.json")) as f:
        b14 = json.load(f)["faces"][f"{num:04d}"]
    art12 = san12_boxes.image(_large12[n12])
    art14 = san14_boxes.art(f"{num:04d}")
    # the figure only (三國志12's alpha), so the two backgrounds do not count
    m = rounded(align(art14, art12, np.arange(1.0, 3.0, 0.02), min_cover=0.3, small_alpha=True))
    # 三國志12's 4:5 crop is its 48x60 box itself
    box = {"x": m["x"] + b12["x"] * m["scale"], "y": m["y"] + b12["y"] * m["scale"],
           "w": b12["w"] * m["scale"], "h": b12["h"] * m["scale"]}
    c = b14["ctr"]
    rel = {"s": box["h"] / c["h"], "t": (box["y"] - c["y"]) / (c["h"] - box["h"]),
           "dx": (box["x"] + box["w"] / 2 - c["x"] - c["w"] / 2) / c["w"]}
    entry = {"name": name, "san12": n12, "base": b14["base"], "match": m,
             "box": {k: round(v, 3) for k, v in box.items()}, "rel": {k: round(v, 4) for k, v in rel.items()}}
    return entry, [cut(art12, b12), cut(art14, b14["crop"]), cut(art14, box)]


def main(args):
    if args == ["--names"]:
        pairs = by_name()
    else:
        pairs = [(int(a.split(":")[0]), int(a.split(":")[-1]), PEOPLE.get(int(a.split(":")[-1]), ""))
                 for a in args] or [(n, n, name) for n, name in PEOPLE.items()]
    with Pool() as pool:
        results = pool.map(relation, pairs, chunksize=2)
    rows, found = [], {}
    for (n12, num, name), (entry, cuts) in zip(pairs, results):
        found[f"{num:04d}"] = entry
        print(name, n12, num, "rmse", entry["match"]["rmse"], "scale", entry["match"]["scale"], entry["rel"])
        # rmse > 25: not the same picture; the sheet shows the first 20 matched
        if entry["match"]["rmse"] <= 25 and entry["base"] == "a" and len(rows) < 20:
            rows.append((f"{name} {num}", cuts))
    for k in ("s", "t", "dx"):
        v = [f["rel"][k] for f in found.values() if f["match"]["rmse"] <= 25 and f["base"] == "a"]
        print(k, len(v), "median", round(statistics.median(v), 4), "quartiles",
              [round(q, 4) for q in statistics.quantiles(v)], "range", min(v), max(v))
    with open(os.path.join(HERE, "samples/san14_vs_san12.json"), "w") as f:
        json.dump(found, f, ensure_ascii=False, indent=1)

    z, pad, top, left = 2, 8, 40, 110
    font = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc", 16)
    cols = ["三國志12", "三國志14 現在", "三國志14 照12的框"]
    out = Image.new("RGB", (left + len(cols) * (CROP[0] * z + pad), top + len(rows) * (CROP[1] * z + pad)),
                    (72, 72, 72))
    d = ImageDraw.Draw(out)
    for j, c in enumerate(cols):
        d.text((left + j * (CROP[0] * z + pad), 12), c, fill="#ffffff", font=font)
    for i, (name, row) in enumerate(rows):
        y = top + i * (CROP[1] * z + pad)
        d.text((8, y + 8), name, fill="#ffffff", font=font)
        for j, im in enumerate(row):
            out.paste(im.resize((CROP[0] * z, CROP[1] * z), Image.NEAREST), (left + j * (CROP[0] * z + pad), y))
    out.save(os.path.join(HERE, "samples/san14_vs_san12.png"))


if __name__ == "__main__":
    main(sys.argv[1:])
