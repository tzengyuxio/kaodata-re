"""三國志12 PK: the box of every 48x60 KAO_F_M face on its 360x512 KAO_W_L picture -> data/san12_boxes.json.

    python san12_boxes.py [face ...]   # no faces: all 933 (about 12 minutes)
"""
import json
import os
import sys

import numpy as np
from PIL import Image

from align import align, rounded

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "../../dekoei"))
import sango  # noqa: E402

GAME = os.path.join(HERE, "../../games/san12pk-win/")
OUT = os.path.join(HERE, "data/san12_boxes.json")


def faces(size: str) -> dict:
    return sango.load_san12_faces(GAME, [(f.replace("KAO_F_M", size), d) for f, d in sango.SAN12_FACE_FILES])


def image(face) -> Image.Image:
    return Image.frombytes("RGBA", face[:2], face[2])


def main(ids):
    large, small = faces("KAO_W_L"), faces("KAO_F_M")
    ids = ids or sorted(small)
    boxes = {}
    for i in ids:
        boxes[i] = rounded(align(image(large[i]), image(small[i]), np.arange(1.2, 4.0, 0.02)))
        print(i, boxes[i], flush=True)
    if len(ids) == len(small):
        with open(OUT, "w") as f:
            json.dump({"about": "box (x, y, w, h) on the 360x512 KAO_W_L picture that resized to 48x60 matches "
                                "KAO_F_M; rmse on 0-255; keys are face numbers",
                       "faces": {str(i): b for i, b in boxes.items()}}, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]])
