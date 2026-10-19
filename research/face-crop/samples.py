"""Crop 4:5 faces with the found boxes into samples/ (not version-controlled), for checking by eye.

    python samples.py

samples/san12/<face>_<w>x<h>.png, samples/san13/<picture>_<w>x<h>.png: the crops at 64x80 and 96x120 (Lanczos), opaque;
samples/san12.png, san13.png: contact sheets, per face the game's small face (enlarged), then the 96x120 crop.
SAN12 takes the 30 faces of the earlier sample; SAN13 the pictures in data/san13_boxes.json. The SAN13 4:5 box is
the 72x72 box with its top kept and its height made 1.25 times the width.
"""
import json
import os

from PIL import Image, ImageDraw

import san12_boxes
import san13_faces

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "samples")
SIZES = [(64, 80), (96, 120)]
SAN12_SAMPLE = [0, 23, 46, 72, 95, 119, 150, 173, 200, 229, 257, 297, 330, 363, 400, 434, 470, 518, 561, 636, 726,
                902, 1003, 1115, 1212, 1235, 1258, 1601, 1814, 1837]


def load(name):
    with open(os.path.join(HERE, "data", name)) as f:
        return json.load(f)


def crops(big, box):
    """The alpha is dropped: the pictures keep their painted background under it."""
    x, y, w, h = box
    big = big.convert("RGB")
    return [big.resize(size, Image.LANCZOS, box=(x, y, x + w, y + h)) for size in SIZES]


def sheet(rows, path):
    """rows: (label, small image, 96x120 crop)."""
    cols = 6
    out = Image.new("RGBA", (cols * 200, (len(rows) + cols - 1) // cols * 140), (90, 90, 90, 255))
    draw = ImageDraw.Draw(out)
    for k, (label, small, crop) in enumerate(rows):
        x, y = k % cols * 200, k // cols * 140
        small = small.resize((96, 96 * small.height // small.width), Image.NEAREST)
        out.alpha_composite(small, (x, y))
        out.paste(crop, (x + 100, y))
        draw.text((x + 2, y + 123), label, fill=(255, 255, 255, 255))
    out.save(path)


def main():
    for d in ("san12", "san13"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    boxes = load("san12_boxes.json")["faces"]
    large, small = san12_boxes.faces("KAO_W_L"), san12_boxes.faces("KAO_F_M")
    rows = []
    for i in SAN12_SAMPLE:
        b = boxes[str(i)]
        images = crops(san12_boxes.image(large[i]), (b["x"], b["y"], b["w"], b["h"]))
        for (w, h), im in zip(SIZES, images):
            im.save(os.path.join(OUT, "san12", f"{i:04d}_{w}x{h}.png"))
        rows.append((f"{i} rmse {b['rmse']:.0f}", san12_boxes.image(small[i]), images[1]))
    sheet(rows, os.path.join(OUT, "san12.png"))

    rows = []
    for i, b in load("san13_boxes.json")["pictures"].items():
        b, i = b["s72"], int(i)
        images = crops(san13_faces.large(i), (b["x"], b["y"], b["w"], b["w"] * 1.25))
        for (w, h), im in zip(SIZES, images):
            im.save(os.path.join(OUT, "san13", f"{i:04d}_{w}x{h}.png"))
        rows.append((f"{i} rmse {b['rmse']:.0f}", san13_faces.small(i), images[1]))
    sheet(rows, os.path.join(OUT, "san13.png"))


if __name__ == "__main__":
    main()
