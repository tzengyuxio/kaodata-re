"""Copy one dataset's results into the game library (re-common §11), so games/<id>/ and games/steam/<appid>/ can be
removed later.

Usage (from the repo root, after re-running the exports):
  .venv/bin/python scripts/archive.py DATASET [--library DIR]     (default ~/game-library)

What goes where (<lib> = <library>/koei/<dataset>/):
  kaodata export (~/works/kaodata/data-local/<id>) -> <lib>/kaodata/          as delivered (kaodata/1)
    and its portraits, rendered by the reference renderer    -> <lib>/faces.cbz + faces.csv (index, code, group,
                                                                who uses it)
  export/koei-wiki/{persons,places,stats}/<id>.jsonl, export/koei-wiki/<id>.jsonl (biographies)
                                                           -> <lib>/wiki/{persons,places,stats,biographies}.jsonl
  export/koei-wiki/places/<id>/ (battle maps)              -> <lib>/wiki/battlemaps.cbz
  export/koei-wiki/events/<id>.jsonl + <id>/               -> <lib>/wiki/events.jsonl + events.cbz
  games/<id>/extract/                                      -> <lib>/   files as they are, a folder of only images
                                                              -> <folder>.cbz (stored zip), other folders the same
                                                              rules one level down
  captures/screenshots/<id>/                               -> <lib>/captures/
  games/steam/<appid>/ (original install)                  -> <library>/_original/win/<id>/ as hard links, and the
                                                              sha1 of every file in _original/win/SHA1SUMS.txt
Files already in the library are overwritten, nothing there is deleted. The game's README.md in the library and its
row in koei.md are written by hand; the script prints what it copied.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "dekoei"))
KAODATA = os.path.expanduser("~/works/kaodata/data-local")
WIKI = os.path.join(ROOT, "export", "koei-wiki")
# dataset -> Steam appid (notes/steam.md)
GAMES = {
    "san10pk-win": 628060, "san11pk-win": 628070, "san12pk-win": 628080, "san13pk-win": 363150,
    "san14pk-win": 872410,
    "nobu9pk-win": 628120, "nobu10pk-win": 628130, "nobu11pk-win": 628140, "nobu12pk-win": 363090,
    "nobu13pk-win": 363110,
}
IMAGES = (".png", ".gif", ".jpg", ".webp")


def write_cbz(dst: str, entries) -> int:
    """entries: (name, bytes or source path); stored, not deflated."""
    n = 0
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as z:
        for name, data in entries:
            if isinstance(data, str):
                z.write(data, name)
            else:
                z.writestr(name, data)
            n += 1
    return n


def folder_entries(src: str):
    for base, dirs, files in os.walk(src):
        dirs.sort()
        for f in sorted(files):
            if f != ".DS_Store":
                path = os.path.join(base, f)
                yield os.path.relpath(path, src), path


def copy_tree(src: str, dst: str) -> None:
    """Files as they are; a folder holding only images (at any depth) becomes <folder>.cbz."""
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        path = os.path.join(src, name)
        if name == ".DS_Store":
            continue
        if os.path.isfile(path):
            shutil.copy2(path, os.path.join(dst, name))
        elif all(rel.lower().endswith(IMAGES) for rel, _ in folder_entries(path)):
            print(f"  {os.path.relpath(dst, args.library)}/{name}.cbz: "
                  f"{write_cbz(os.path.join(dst, name + '.cbz'), folder_entries(path))} images")
        else:
            copy_tree(path, os.path.join(dst, name))


def faces(dataset: str, game_dir: str, lib: str) -> None:
    """Render every portrait (pt:i) of the dataset with the kaodata reference renderer."""
    import kaodata_export as ke
    meta, blobs = ke.DATASETS[dataset](game_dir)
    shared = meta["palettes"][0]["colors"] if meta["palettes"] else None
    users = {}
    for ch in meta["characters"]:
        face = ch.get("face", {})
        for f in [face, *ch.get("expressions", [])]:
            if "portrait" in f:
                users.setdefault(f["portrait"], []).append(ch["name"])
    entries, rows = [], []
    for key, img, pal in ke.display_entries(meta, blobs):
        if not key.startswith("pt:"):
            continue
        i = int(key[3:])
        if pal == "rgba":
            im = Image.frombytes("RGBA", _rgba_size(meta, i), img)
        else:
            colors = shared if pal is None else ke.portrait_palette(meta, blobs, pal)
            im = Image.frombytes("RGBA", img[:2], ke.to_rgba(img, colors, meta.get("opaque", False)))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        entries.append((f"{i:04d}.png", buf.getvalue()))
        p = meta["portraits"][i]
        rows.append([i, f"{i:04d}.png", p.get("code", ""), p.get("name", ""), p.get("group", ""),
                     " ".join(users.get(i, []))])
    print(f"  faces.cbz: {write_cbz(os.path.join(lib, 'faces.cbz'), entries)} portraits")
    with open(os.path.join(lib, "faces.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["portrait", "file", "code", "name", "group", "characters"])
        w.writerows(rows)


def _rgba_size(meta: dict, i: int) -> tuple[int, int]:
    ref = meta["images"][meta["portraits"][i]["img"]]
    return (ref["w"], ref["h"]) if isinstance(ref, dict) else (ref[1], ref[2])


def wiki(dataset: str, lib: str) -> None:
    out = os.path.join(lib, "wiki")
    os.makedirs(out, exist_ok=True)
    for src, name in [(f"persons/{dataset}.jsonl", "persons.jsonl"), (f"places/{dataset}.jsonl", "places.jsonl"),
                      (f"stats/{dataset}.jsonl", "stats.jsonl"), (f"{dataset}.jsonl", "biographies.jsonl"),
                      (f"events/{dataset}.jsonl", "events.jsonl")]:
        if os.path.exists(os.path.join(WIKI, src)):
            shutil.copy2(os.path.join(WIKI, src), os.path.join(out, name))
            print(f"  wiki/{name}")
    for src, name in [(f"places/{dataset}", "battlemaps.cbz"), (f"events/{dataset}", "events.cbz")]:
        if os.path.isdir(os.path.join(WIKI, src)):
            print(f"  wiki/{name}: {write_cbz(os.path.join(out, name), folder_entries(os.path.join(WIKI, src)))}")


def sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def original(dataset: str, appid: int, library: str) -> None:
    src = os.path.join(ROOT, "games", "steam", str(appid))
    base = os.path.join(library, "_original", "win")
    dst = os.path.join(base, dataset)
    lines = []
    for rel, path in folder_entries(src):
        target = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if not (os.path.exists(target) and os.path.samefile(path, target)):
            if os.path.exists(target):
                os.remove(target)
            os.link(path, target)
        lines.append(f"{sha1(path)}  {dataset}/{rel}")
    sums = os.path.join(base, "SHA1SUMS.txt")
    old = open(sums, encoding="utf-8").read().splitlines() if os.path.exists(sums) else []
    keep = [x for x in old if x.split("  ", 1)[1].split("/")[0] != dataset]
    with open(sums, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(keep + lines, key=lambda x: x.split("  ", 1)[1])) + "\n")
    print(f"  _original/win/{dataset}/: {len(lines)} files (hard links)")


def main() -> None:
    global args
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("dataset", choices=sorted(GAMES))
    p.add_argument("--library", default=os.path.expanduser("~/game-library"))
    p.add_argument("--skip-original", action="store_true", help="do not link and hash the original install")
    args = p.parse_args()
    ds = args.dataset
    lib = os.path.join(args.library, "koei", ds)
    os.makedirs(lib, exist_ok=True)
    print(f"{ds} -> {lib}")
    if os.path.isdir(os.path.join(KAODATA, ds)):
        shutil.copytree(os.path.join(KAODATA, ds), os.path.join(lib, "kaodata"), dirs_exist_ok=True)
        print("  kaodata/")
        faces(ds, os.path.join(ROOT, "games", ds), lib)
    wiki(ds, lib)
    if os.path.isdir(os.path.join(ROOT, "games", ds, "extract")):
        copy_tree(os.path.join(ROOT, "games", ds, "extract"), lib)
    if os.path.isdir(os.path.join(ROOT, "captures", "screenshots", ds)):
        shutil.copytree(os.path.join(ROOT, "captures", "screenshots", ds), os.path.join(lib, "captures"),
                        dirs_exist_ok=True)
        print("  captures/")
    if not args.skip_original:
        original(ds, GAMES[ds], args.library)
    if not os.path.exists(os.path.join(lib, "README.md")):
        print("  README.md is missing (write it by hand)")


if __name__ == "__main__":
    main()
