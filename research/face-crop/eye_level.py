"""Where the eyes sit in a 4:5 face crop: OpenCV's Haar eye detector on the crop scaled up 4x, the median of the
detected eye centers' heights as a share of the crop height.

    python eye_level.py   # every 5th face of 三國志13's 96x120 export (kaodata data/) and of 三國志14's s = 0.6 box
                          # (data/san14_boxes.json) at t = 0.25: the t that puts 三國志14's eyes at 三國志13's height

Used to place 三國志14's crop (the user's idea, 2026-10-21): its ctr face frames head to chest, so its 4:5 box is
shrunk to 0.6 and moved up until the eyes sit where they do in 三國志13. 2026-10-21: san13 median 0.408 (294 faces),
san14 median t 0.118 (295 faces) -> T = 0.12 in san14_boxes.py.
"""
import json
import os
import statistics

import cv2
import numpy as np
from PIL import Image

import san14_boxes

HERE = os.path.dirname(os.path.abspath(__file__))
CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
SAN13 = os.path.expanduser("~/works/kaodata/data/san13pk-win/faces")


def eye_level(im: Image.Image):
    """Median height of the eyes found (share of the crop height), or None."""
    g = cv2.cvtColor(np.asarray(im.convert("RGB").resize((im.width * 4, im.height * 4), Image.LANCZOS)),
                     cv2.COLOR_RGB2GRAY)
    h = g.shape[0]
    eyes = CASCADE.detectMultiScale(g, 1.05, 5, minSize=(h // 14, h // 14), maxSize=(h // 3, h // 3))
    # eyes are in the upper two thirds of a face crop
    ys = [(y + eh / 2) / h for x, y, ew, eh in eyes if (y + eh / 2) / h < 0.67]
    return statistics.median(ys) if ys else None


def main():
    names = sorted(os.listdir(SAN13))
    levels13 = [v for v in (eye_level(Image.open(os.path.join(SAN13, n))) for n in names[::5]) if v is not None]
    e13 = statistics.median(levels13)
    print(f"san13: {len(levels13)} of {len(names[::5])} with eyes, median {e13:.3f}")
    with open(os.path.join(HERE, "data/san14_boxes.json")) as f:
        boxes = json.load(f)["faces"]
    ts = []
    keys = [k for k in sorted(boxes) if boxes[k]["base"] == "a"][::5]
    for key in keys:
        art = san14_boxes.art(key).convert("RGB")
        b = boxes[key]["ctr"]
        s, t = 0.6, 0.25
        ch = s * b["h"]
        cw = 0.8 * ch
        top = b["y"] + (b["h"] - ch) * t
        e = eye_level(art.resize((96, 120), Image.LANCZOS, box=(b["x"] + (b["w"] - cw) / 2, top,
                                                                   b["x"] + (b["w"] + cw) / 2, top + ch)))
        if e is None:
            continue
        # moving the top by d px moves the eyes by -d / ch of the crop
        ts.append(t + (e - e13) * ch / (b["h"] - ch))
    print(f"san14: {len(ts)} of {len(keys)} with eyes, quartiles {statistics.quantiles(ts)}")
    print(f"median t {statistics.median(ts):.3f}")


if __name__ == "__main__":
    main()
