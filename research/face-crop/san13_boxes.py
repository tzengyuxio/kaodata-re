"""三國志13 PK: the boxes of the 72x72, 96x96 and 186x90 faces on the 1024x1024 picture -> data/san13_boxes.json.

    python san13_boxes.py            # the 30-picture sample (about 4 minutes)
    python san13_boxes.py 5 101 ...  # these pictures, printed only
"""
import json
import os
import sys

import numpy as np

import san13_faces as faces
from align import align, rounded

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/san13_boxes.json")


def boxes(i: int) -> dict:
    big = faces.large(i)
    return {
        # the 72x72 has a transparent background, so its own alpha weights the match too
        "s72": rounded(align(big, faces.small(i), np.arange(2.5, 8.0, 0.02), small_alpha=True)),
        "s96": rounded(align(big, faces.medium(i), np.arange(2.5, 8.0, 0.02), min_cover=0.3)),
        "m186": rounded(align(big, faces.strip(i), np.arange(2.5, 6.5, 0.02), min_cover=0.3)),
    }


def main(ids):
    sample = not ids
    if sample:
        n = faces.count()
        ids = list(range(5, n, n // 30))[:30]
    out = {}
    for i in ids:
        out[i] = boxes(i)
        print(i, out[i], flush=True)
    if sample:
        with open(OUT, "w") as f:
            json.dump({"about": "boxes (x, y, w, h) on the 1024x1024 kao_l picture that resized to 72x72 (kao_s), "
                                "96x96 (kao_ss) and 186x90 (kao_m) match them; rmse on 0-255; keys are picture "
                                "indexes (items of pk/DATA0.S13 entries 13, 20, 22, 18)",
                       "pictures": {str(i): b for i, b in out.items()}}, f, ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]])
