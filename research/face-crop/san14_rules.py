"""三國志14 PK: candidate 4:5 crops of the 636x900 face_NNNN_a art, made from the box of the 484x512 face_NNNN_ctr
on it, beside 三國志13's 96x120 (data/san13_a_boxes.json) of the same people -> samples/san14_rules.png.

    python san14_rules.py

Candidate (s, t): a 4:5 box of height s * h (h the ctr box's height), centered on the ctr box, its top moved down
by t of the height lost (t = 0.25 is what 三國志13's rule does with its square box; a smaller t sits higher).
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import san13_faces
import sizes_san14
from align import align

HERE = os.path.dirname(os.path.abspath(__file__))
sango = san13_faces.sango
PEOPLE = {"張飛": 1, "関羽": 2, "呂布": 3, "趙雲": 9, "典韋": 13, "劉備": 36, "諸葛亮": 45, "曹操": 60, "孫権": 64,
          "貂蝉": 566}
CANDIDATES = [(0.6, 0.25), (0.6, 0.08)]
CROP = (96, 120)


def art_and_ctr(num):
    ims = sizes_san14.face(num)
    pre = f"face_{num:04d}_"
    # the three layers' RGB agree where they overlap; the first layer's RGB is the whole picture
    ctr = ims[pre + "ctr"]
    if ctr.height != 512:  # a ctr whose file also holds a 1024 texture (face_0001_ctr…) is cut from the wrong one
        print(f"  ctr of {num} is {ctr.size}")
    return ims[pre + "a"].convert("RGB").convert("RGBA"), ctr


def cut(im, x, y, w, h):
    return im.convert("RGB").resize(CROP, Image.LANCZOS, box=(x, y, x + w, y + h))


def main():
    data = sango.load_san13_persons(san13_faces.GAME)
    item13 = {data["names"][k][0]: sango.san13_face_item(v[0]) for k, v in data["pictures"].items()}
    with open(os.path.join(HERE, "data/san13_a_boxes.json")) as f:
        boxes13 = json.load(f)["faces"]
    arts13 = {}
    rows, found = [], {}
    for name, num in PEOPLE.items():
        art, ctr = art_and_ctr(num)
        b = align(art, ctr, np.arange(0.6, 1.5, 0.01), small_alpha=True)
        found[name] = b
        print(name, num, b, flush=True)
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        row = []
        i13 = item13.get(name)
        if i13 is not None:
            c = boxes13[str(i13)]["crop"]
            a13 = arts13.setdefault(i13, san13_faces.textures(san13_faces._item(8, i13))[0].crop((0, 0, 633, 900)))
            row.append(cut(a13, c["x"], c["y"], c["w"], c["h"]))
        else:
            row.append(Image.new("RGB", CROP, (40, 40, 40)))
        for s, t in CANDIDATES:
            ch = s * h
            cw = 0.8 * ch
            row.append(cut(art, x + (w - cw) / 2, y + (h - ch) * t, cw, ch))
        rows.append((name, row))
    with open(os.path.join(HERE, "samples/san14_ctr_boxes.json"), "w") as f:
        json.dump(found, f, ensure_ascii=False, indent=1)

    z, pad, top = 2, 8, 40
    font = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc", 16)
    cols = ["三國志13"] + [f"s={s} t={t}" for s, t in CANDIDATES]
    W = 80 + len(cols) * (CROP[0] * z + pad)
    H = top + len(rows) * (CROP[1] * z + pad)
    out = Image.new("RGB", (W, H), (72, 72, 72))
    d = ImageDraw.Draw(out)
    for j, c in enumerate(cols):
        d.text((80 + j * (CROP[0] * z + pad), 12), c, fill="#ffffff", font=font)
    for i, (name, row) in enumerate(rows):
        y = top + i * (CROP[1] * z + pad)
        d.text((8, y + 8), name, fill="#ffffff", font=font)
        for j, im in enumerate(row):
            out.paste(im.resize((CROP[0] * z, CROP[1] * z), Image.NEAREST), (80 + j * (CROP[0] * z + pad), y))
    out.save(os.path.join(HERE, "samples/san14_rules.png"))


if __name__ == "__main__":
    main()
