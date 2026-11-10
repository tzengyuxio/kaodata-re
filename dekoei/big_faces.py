"""The large face pictures of 三國志VIII-14 PK for the game library (re-common §11): for every kaodata portrait, the
BASE picture (the one with the widest view, kaodata spec §6.5) and, where the game has a bigger one, the largest
size, lossless, to games/<id>/extract/faces/{base,large}/NNNN.png (NNNN = the kaodata portrait index, as faces.csv
of scripts/archive.py) and faces/index.csv.

    ../.venv/bin/python big_faces.py san13pk-win --game-dir ../games/san13pk-win

The BASE is what the kaodata builder picks (notes/kaodata-datasets.md「BASE」): 三國志VIII-X indexed, rendered with
the reference renderer; 11-14 full colour, which the builder stores as lossy WebP, so art_webp is swapped for PNG
here. The largest size: 三國志13 kao_l (1024x1024, sango.san13_large), 14 face_NNNN_unique (1024x1024); in VIII-12
the BASE is also the largest picture.
"""
import csv
import io
import os
import sys

import click
from PIL import Image

import kaodata_export as ke
import sango


def _png(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _bases(dataset, game_dir):
    """meta, [BASE image of portrait i]"""
    webp = ke.art_webp
    ke.art_webp = _png  # the builders call art_webp(im) for full-colour BASE pictures
    try:
        meta, blobs = ke.DATASETS[dataset](game_dir)
    finally:
        ke.art_webp = webp
    if "artFiles" in meta:
        arts = [Image.open(io.BytesIO(b)) for b in meta["artFiles"]]
    else:
        shared = meta["palettes"][0]["colors"] if meta["palettes"] else None
        arts = {}
        for key, img, pal in ke.display_entries(meta, blobs):
            if key.startswith("art:"):
                colors = shared if pal is None else ke.portrait_palette(meta, blobs, pal)
                arts[int(key[4:])] = Image.frombytes("RGBA", img[:2], ke.to_rgba(img, colors, False))
    return meta, [arts[p["art"]] for p in meta["portraits"]]


def _largest(dataset, game_dir, meta):
    """[largest picture of portrait i] where it is bigger than the BASE, else None"""
    if dataset == "san13pk-win":
        return [sango.san13_large(game_dir, i, alpha=True) for i in range(len(meta["portraits"]))]
    if dataset == "san14pk-win":
        import json
        sprites = sango.san14_face_sprites(game_dir)
        with open(ke.SAN14PK_WIN_BOXES) as f:
            keys = sorted(json.load(f)["faces"], key=lambda k: (int(k[:4]), k))  # portrait order of the builder
        return [sango.san14_sprite(game_dir, sprites[f"face_{k}_unique"]) for k in keys]
    return None


@click.command()
@click.argument("dataset", type=click.Choice(["san8pk-win", "san9pk-win", "san10pk-win", "san11pk-win", "san12pk-win",
                                              "san13pk-win", "san14pk-win"]))
@click.option("--game-dir", "game_dir", required=True)
@click.option("--out", "out", help="預設 <game-dir>/extract/faces")
def main(dataset, game_dir, out):
    out = out or os.path.join(game_dir, "extract", "faces")
    meta, bases = _bases(dataset, game_dir)
    large = _largest(dataset, game_dir, meta)
    assert large is None or len(large) == len(bases)
    os.makedirs(os.path.join(out, "base"), exist_ok=True)
    if large:
        os.makedirs(os.path.join(out, "large"), exist_ok=True)
    rows = []
    for i, (p, im) in enumerate(zip(meta["portraits"], bases)):
        im.save(os.path.join(out, "base", f"{i:04d}.png"))
        row = [i, p.get("code", ""), f"{im.width}x{im.height}", ""]
        if large:
            large[i].save(os.path.join(out, "large", f"{i:04d}.png"))
            row[3] = f"{large[i].width}x{large[i].height}"
        rows.append(row)
    with open(os.path.join(out, "index.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["portrait", "code", "base", "large"])
        w.writerows(rows)
    click.echo(f"{dataset}: {len(rows)} portraits, base {rows[0][2]}" + (f", large {rows[0][3]}" if large else ""))


if __name__ == "__main__":
    sys.exit(main())
