"""The PC-98 inputs of reel.py: the strategic map (MAPDATA.DAT from 0, 296 x 400, 3 bpp, digital 8 colours) and
司馬懿's face. Run from anywhere; writes next to this file."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "dekoei"))
GAME = os.path.join(REPO, "games/san2-pc98")

from PIL import Image  # noqa: E402

import san2  # noqa: E402
from kaodata_export import SAN2_JP_PALETTE, san2_jp_pixels  # noqa: E402
from utils import color_codes_to_palette, data_to_image  # noqa: E402

pal = color_codes_to_palette(["#000000", "#00FF00", "#FF0000", "#FFFF00", "#0000FF", "#00FFFF", "#FF00FF", "#FFFFFF"])
with open(os.path.join(GAME, "MAPDATA.DAT"), "rb") as f:
    data_to_image(f.read()[:296 * 400 * 3 // 8], 296, 400, pal).save(os.path.join(HERE, "pc98_map.png"))

code = next(c for c, n in san2.load_san2_jp_persons(GAME, False) if n == "司馬懿")
kao = b"".join(open(os.path.join(GAME, n), "rb").read()[:k * san2.JP_FACE] for n, k in san2.JP_FACE_FILES)
w, h, px = san2_jp_pixels(kao[(code - 1) * san2.JP_FACE:code * san2.JP_FACE], True)
rgb = [tuple(int(x[k:k + 2], 16) for k in (1, 3, 5)) for x in SAN2_JP_PALETTE]
im = Image.new("RGB", (w, h))
im.putdata([rgb[p] for p in px])
im.save(os.path.join(HERE, "pc98_司馬懿.png"))
