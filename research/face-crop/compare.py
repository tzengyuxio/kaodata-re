"""The same 20 people in 三國志11, 12 and 13 side by side -> samples/compare/ (not version-controlled).

    python compare.py       # samples/compare.png
    python compare.py v2    # samples/compare_v2.png: the 三國志13 box made smaller (V2_SHRINK)

samples/compare/<n>_<name>_san1x.png, all 64x80: 三國志11's own (left-facing small face), and the crops of 三國志12
(data/san12_boxes.json) and 三國志13 (the 72x72 box of each picture, found here, made 4:5 with its top kept);
samples/compare.png: a contact sheet. Each person takes their first face
(scenario 0 of 三國志11/12, the first picture of 三國志13).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import san12_boxes
import san13_faces
from align import align
from samples import crops, load

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "samples")
sango = san13_faces.sango
SAN11_GAME = os.path.join(HERE, "../../games/san11pk-win/")
SAN12_SCENARIO = "PK/Scenario/Scenario0.dat"
BOXES = os.path.join(OUT, "compare_boxes.json")  # the 三國志13 boxes found, so a rerun skips the matching
# v2: the 三國志13 box made smaller by this factor, keeping its horizontal center and moving its top down by a
# quarter of what the width loses, so the face fills the crop about as much as in 三國志11/12
V2_SHRINK = 0.8
PEOPLE = ["曹操", "劉備", "孫堅", "関羽", "張飛", "趙雲", "諸葛亮", "呂布", "貂蝉", "周瑜",
          "司馬懿", "孫策", "馬超", "黄忠", "夏侯惇", "典韋", "袁紹", "董卓", "陸遜", "甘寧"]


def faces():
    """name -> (三國志11 64x80, 三國志12 face, 三國志13 picture item)."""
    san11 = {p["name"]: p["face"] for p in sango.load_san11_persons(SAN11_GAME + "Scen000.s11") if p["name"]}
    san12 = {p["name"]: p["face"] for p in sango.load_san12_persons(san12_boxes.GAME + SAN12_SCENARIO) if p["name"]}
    data = sango.load_san13_persons(san13_faces.GAME)
    san13 = {data["names"][k][0]: sango.san13_face_item(v[0]) for k, v in data["pictures"].items()}
    small11 = sango.load_san11_small_faces(SAN11_GAME + sango.SAN11_FACE_FILE)
    return {n: (Image.frombytes("RGBA", (64, 80), small11[san11[n]]).convert("RGB"), san12[n], san13[n])
            for n in PEOPLE}


def box13(i13, cache):
    if str(i13) not in cache:
        big = san13_faces.large(i13)
        cache[str(i13)] = align(big, san13_faces.small(i13), np.arange(2.5, 8.0, 0.02), small_alpha=True)
    b = cache[str(i13)]
    return b["x"], b["y"], b["w"]


def main(version):
    shrink = V2_SHRINK if version == "v2" else 1
    suffix = f"_{version}" if version else ""
    os.makedirs(os.path.join(OUT, "compare" + suffix), exist_ok=True)
    cache = {}
    if os.path.exists(BOXES):
        with open(BOXES) as f:
            cache = json.load(f)
    boxes12 = load("san12_boxes.json")["faces"]
    large12 = san12_boxes.faces("KAO_W_L")
    rows = []
    for n, (name, (s11, f12, i13)) in enumerate(faces().items()):
        b = boxes12[str(f12)]
        c12 = crops(san12_boxes.image(large12[f12]), (b["x"], b["y"], b["w"], b["h"]))[0]
        x, y, w = box13(i13, cache)
        d = w * (1 - shrink)
        x, y, w = x + d / 2, y + d / 4, w - d
        c13 = crops(san13_faces.large(i13), (x, y, w, w * 1.25))[0]
        print(name, f12, i13, flush=True)
        stem = os.path.join(OUT, "compare" + suffix, f"{n:02d}_{name}")
        for game, im in (("san11", s11), ("san12", c12), ("san13", c13)):
            im.save(f"{stem}_{game}.png")
        rows.append((name, [s11, c12, c13]))
    with open(BOXES, "w") as f:
        json.dump(cache, f)
    sheet(rows, os.path.join(OUT, f"compare{suffix}.png"))


def sheet(rows, path):
    """Columns: 三國志11, 12, 13 at 64x80, twice actual size; four people per row."""
    heads = ["11", "12", "13"]
    xs = [64, 200, 336]
    font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 14)
    half, per = 480, 4
    out = Image.new("RGB", (per * half, 24 + (len(rows) + per - 1) // per * 166), (90, 90, 90))
    draw = ImageDraw.Draw(out)
    for side in range(per):
        for x, t in zip(xs, heads):
            draw.text((side * half + x, 4), t, font=font, fill=(255, 255, 255))
    for k, (name, images) in enumerate(rows):
        ox, oy = k % per * half, 24 + k // per * 166
        draw.text((ox + 4, oy + 70), name, font=font, fill=(255, 255, 255))
        for x, im in zip(xs, images):
            out.paste(im.resize((128, 160), Image.NEAREST), (ox + x, oy))
    out.save(path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
