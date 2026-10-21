"""Sheets of every face size a game has, for one person: the largest picture with a box for where each smaller one
sits on it (found by align.py), and every size at its own pixels side by side -> samples/sizes/<id>.png.

    python sizes.py san13pk-win nobu16pk-win ...   # these games; no argument: every samples/sizes/<id>/

Input: samples/sizes/<id>/<NN>_<label>.png, the raw images of one person as the game stores them (cropped to the
face, RGBA), plus an optional info.json {"title": ..., "person": ..., "notes": {label: text}, "base": label,
"nomatch": {label: why}}. The base is the largest image by area unless "base" names one; "nomatch" sizes get no box. A size that is not a scaled crop of the base (redrawn, mirrored) gets a high rmse; the box is still
drawn, dashed, and the sheet says so. The base itself is the left picture, not repeated among the tiles.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from align import align

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "samples/sizes")
COLORS = ["#ff3030", "#30c0ff", "#ffd000", "#40e040", "#ff60ff", "#ff9020", "#ffffff"]
BAD_RMSE = 30
BASE_H = 640
TILE_H = 240
BG = (72, 72, 72)


def font(size):
    for p in ["/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
              "/Library/Fonts/Arial Unicode.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def flatten(im):
    bg = Image.new("RGBA", im.size, BG + (255,))
    return Image.alpha_composite(bg, im.convert("RGBA")).convert("RGB")


def find_box(base, im):
    """The box of im on base; scales swept around the size ratio. A smaller size can still be finer than the base
    (新生's 512x512 is sharper than the face on its 717x1020), so the sweep goes below 1."""
    hi = min(base.width / im.width, base.height / im.height) * 1.02
    lo = max(0.5, hi * 0.15)
    alpha = np.asarray(im.convert("RGBA"))[..., 3]
    small_alpha = bool((alpha < 255).any())
    return align(base, im, np.geomspace(lo, hi, 60), min_cover=0.3, small_alpha=small_alpha)


def dashed(d, box, color, width):
    x0, y0, x1, y1 = box
    step = 10
    for a, b, horiz, c in [(x0, x1, True, y0), (x0, x1, True, y1), (y0, y1, False, x0), (y0, y1, False, x1)]:
        t = a
        while t < b:
            e = min(t + step, b)
            d.line([(t, c), (e, c)] if horiz else [(c, t), (c, e)], fill=color, width=width)
            t += 2 * step


def wrap(text, fnt, width):
    lines, cur = [], ""
    for ch in text:
        if cur and fnt.getlength(cur + ch) > width:
            lines.append(cur)
            cur = ""
        cur += ch
    return lines + [cur] if cur else lines


def sheet(gid):
    folder = os.path.join(ROOT, gid)
    info = {}
    if os.path.exists(os.path.join(folder, "info.json")):
        with open(os.path.join(folder, "info.json"), encoding="utf-8") as f:
            info = json.load(f)
    names = sorted(n for n in os.listdir(folder) if n.endswith(".png"))
    ims = {os.path.splitext(n)[0].split("_", 1)[1]: Image.open(os.path.join(folder, n)).convert("RGBA") for n in names}
    # info.json "base" picks the base when the largest by area is not the widest view (三國志13's kao_a)
    base_label = info.get("base") or max(ims, key=lambda k: ims[k].width * ims[k].height)
    base = ims[base_label]
    nomatch = info.get("nomatch", {})  # label -> why it is not matched (an overlay, a mirrored redraw…)
    boxes = {}
    for k, im in ims.items():
        if k != base_label:
            boxes[k] = None if k in nomatch else find_box(base, im)
            print(gid, k, boxes[k], flush=True)

    # the left picture spans the base and every box (a box may run past the base)
    s = BASE_H / base.height
    found = [b for b in boxes.values() if b]
    x0 = min([0] + [b["x"] for b in found])
    y0 = min([0] + [b["y"] for b in found])
    x1 = max([base.width] + [b["x"] + b["w"] for b in found])
    y1 = max([base.height] + [b["y"] + b["h"] for b in found])
    left = Image.new("RGB", (round((x1 - x0) * s) + 4, round((y1 - y0) * s) + 4), (56, 56, 56))
    left.paste(flatten(base).resize((round(base.width * s), BASE_H), Image.LANCZOS),
               (round(-x0 * s) + 2, round(-y0 * s) + 2))
    d = ImageDraw.Draw(left)
    colors = {k: COLORS[i % len(COLORS)] for i, k in enumerate(boxes)}
    n = len(boxes)
    for i, (k, b) in enumerate(boxes.items()):
        if b is None:
            continue
        r = [(b["x"] - x0) * s + 2, (b["y"] - y0) * s + 2, (b["x"] + b["w"] - x0) * s + 2,
             (b["y"] + b["h"] - y0) * s + 2]
        # earlier boxes are drawn wider, so a box that coincides with a later one still shows round it
        w = 3 + 3 * (n - 1 - i)
        if b["rmse"] > BAD_RMSE:
            dashed(d, r, colors[k], w)
        else:
            d.rectangle(r, outline=colors[k], width=w)

    f, fs = font(18), font(14)
    tiles = []
    for k in boxes:
        im = ims[k]
        z = max(1, round(TILE_H / im.height)) if im.height < TILE_H else TILE_H / im.height
        t = flatten(im).resize((round(im.width * z), round(im.height * z)),
                               Image.NEAREST if z >= 1 else Image.LANCZOS)
        b = boxes.get(k)
        head = f"{k}  {im.width}×{im.height}" + (f"  ×{z:.3g}" if z != 1 else "")
        cw = max(t.width, 240, round(f.getlength(head)))
        lines = []
        if k in nomatch:
            lines.append(f"not matched: {nomatch[k]}")
        elif b is None:
            lines.append("not matched")
        else:
            lines.append(f"box {b['w']:.0f}×{b['h']:.0f} @ ({b['x']:.0f},{b['y']:.0f})  rmse {b['rmse']:.0f}"
                         + ("  NO MATCH" if b["rmse"] > BAD_RMSE else ""))
        if info.get("notes", {}).get(k):
            lines.append(info["notes"][k])
        body = [w for line in lines for w in wrap(line, fs, cw)]
        tiles.append((t, head, body, colors[k], cw))

    pad = 16
    right_w = sum(cw for *_, cw in tiles) + pad * (len(tiles) + 1)
    W = left.width + right_w + pad
    text_h = max((60 + t.height + 34 + 19 * len(body) for t, _, body, _, _ in tiles), default=0)
    H = max(60 + left.height + pad, text_h + pad)
    out = Image.new("RGB", (W, H), BG)
    out.paste(left, (pad, 60))
    d = ImageDraw.Draw(out)
    d.text((pad, 14), f"{info.get('title', gid)}　{info.get('person', '')}　base {base_label} {base.width}×{base.height}",
           fill="#ffffff", font=font(24))
    x = left.width + 2 * pad
    for t, head, body, c, cw in tiles:
        out.paste(t, (x, 60))
        d.rectangle([x - 2, 58, x + t.width + 1, 61 + t.height], outline=c, width=2)
        y = 70 + t.height
        d.text((x, y), head, fill=c, font=f)
        y += 24
        for line in body:
            d.text((x, y), line, fill="#dddddd", font=fs)
            y += 19
        x += cw + pad
    out.save(os.path.join(ROOT, f"{gid}.png"))
    with open(os.path.join(folder, "boxes.json"), "w") as fp:
        json.dump({"base": base_label, "boxes": boxes}, fp, indent=1)


if __name__ == "__main__":
    ids = sys.argv[1:] or sorted(n for n in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, n)))
    for gid in ids:
        sheet(gid)
