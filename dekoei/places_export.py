"""Places (provinces, cities, passes...) of 三國志 I-14 and 水滸傳 for koei-wiki: one JSONL line per place in
<out>/<dataset>.jsonl and the battle maps as PNG in <out>/<dataset>/, in the koei-places/1 format
(koei-wiki docs/places-format.mkdn). Where each table comes from and how sure it is: notes/san-maps.md, and for
水滸傳 notes/koei-games.md「州與戰場地圖」."""
import json
import os
import unicodedata

import click
from PIL import Image, ImageDraw, ImageFont

from wiki_datasets import datasets, module

# A map the attacked place uses whatever kind of battle it is (I-III have one kind of battle)
BATTLE = "戰場"


def _text(b: bytes, fix: dict = None) -> str:
    """Shift-JIS up to the first NUL; fix maps a two-byte gaiji code to its character."""
    b = b.split(b"\0")[0]
    out, i = "", 0
    while i < len(b):
        code = int.from_bytes(b[i:i + 2], "big")
        if fix and code in fix:
            out, i = out + fix[code], i + 2
            continue
        n = 2 if 0x81 <= b[i] <= 0x9F or 0xE0 <= b[i] <= 0xFC else 1
        out, i = out + b[i:i + n].decode("cp932"), i + n
    return out.strip()


def _reading(b: bytes) -> str:
    """Half-width katakana reading as full-width katakana."""
    return unicodedata.normalize("NFKC", _text(b))


def _save(maps, out_dir, names):
    os.makedirs(out_dir, exist_ok=True)
    for im, name in zip(maps, names):
        im.save(os.path.join(out_dir, name))


def _areas(im, colour):
    """4-connected areas of one colour: label per pixel (0 = other colour)."""
    w, h = im.size
    px, lab, n = im.tobytes(), [0] * (w * h), 0
    for i in range(w * h):
        if px[i] == colour and not lab[i]:
            n += 1
            lab[i], stack = n, [i]
            while stack:
                j = stack.pop()
                x, y = j % w, j // w
                for u, v in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    k = v * w + u
                    if 0 <= u < w and 0 <= v < h and px[k] == colour and not lab[k]:
                        lab[k] = n
                        stack.append(k)
    return lab


def _gaiji(s: str, table: dict) -> str:
    """Replace the private-use characters (gaiji) of a decoded string through table {code point: char}."""
    return "".join(table.get(ord(c), c) for c in s)


# Place-name gaiji of the Windows games (Shift-JIS F0xx = U+E0xx), read off the readings and the other
# generations' names: 鄴 下邳 譙 涪 并州 兗州 臨淄 鄱陽
PLACE_GAIJI = {0xE02D: "鄴", 0xE020: "邳", 0xE018: "譙", 0xE02A: "涪", 0xE024: "并", 0xE00B: "兗", 0xE022: "淄",
               0xE030: "鄱"}


def _bmp_png(src, out_dir, name):
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    with Image.open(src) as im:
        im.save(os.path.join(out_dir, name))


def check(rows, out_dir, one_way=()):
    """koei-places/1 checks: references exist, battle map files exist, from is adjacent, adjacency is two-way
    (except one_way, the (from, to) pairs the game itself has one-way, which the notes explain). Returns (checked, [problems])."""
    ids = {r["id"] for r in rows}
    assert len(ids) == len(rows), "duplicate id"
    checked, bad = 0, []
    for r in rows:
        refs = r.get("adjacent", []) + ([r["parentCity"]] if "parentCity" in r else []) + \
            [x for m in r.get("battlemaps", []) for x in m.get("sharedWith", []) + ([m["from"]] if "from" in m else [])]
        for x in refs:
            checked += 1
            if x not in ids:
                bad.append(f"{r['id']}: no place {x}")
        for m in r.get("battlemaps", []):
            checked += 1
            if not os.path.exists(os.path.join(out_dir, m["file"])):
                bad.append(f"{r['id']}: no file {m['file']}")
            if "from" in m:
                checked += 1
                if m["from"] not in r.get("adjacent", []):
                    bad.append(f"{r['id']}: from {m['from']} not adjacent")
    # world/ maps: pos.w x pos.h must scale to every map by one whole factor, and each pos lies inside
    world = os.path.join(out_dir, "world")
    sizes = [Image.open(os.path.join(world, f)).size for f in sorted(os.listdir(world))] if os.path.isdir(world) else []
    for r in rows:
        p = r.get("pos")
        if not sizes or not p:
            continue
        checked += 1
        if "w" not in p or not all(w % p["w"] == 0 and h % p["h"] == 0 and w // p["w"] == h // p["h"]
                                   for w, h in sizes):
            bad.append(f"{r['id']}: pos w/h do not match the world map {sizes}")
        elif not (0 <= p["x"] < p["w"] and 0 <= p["y"] < p["h"]):
            bad.append(f"{r['id']}: pos {p['x']},{p['y']} outside {p['w']}x{p['h']}")
    by_id = {r["id"]: r for r in rows}
    for r in rows:
        for x in r.get("adjacent", []):
            checked += 1
            if x in by_id and r["id"] not in by_id[x].get("adjacent", []) and (r["id"], x) not in one_way:
                bad.append(f"{r['id']} -> {x} one-way")
    return checked, bad


@click.command()
@click.argument("dataset", type=click.Choice(datasets("places")))
@click.option("--game-dir", "game_dir", required=True)
@click.option("--out", "out", required=True, help="輸出目錄（寫 <dataset>.jsonl 與 <dataset>/ 的戰場圖）")
def places_export(dataset, game_dir, out):
    """匯出三國志各代與水滸傳的地點與戰場圖（koei-places/1，給 koei-wiki）

    dekoei.py places-export san3-pc98 --game-dir ../games/san3-pc98 --out ../export/koei-wiki/places
    """
    map_dir = os.path.join(out, dataset)
    m = module(dataset, "places")
    rows = [{"dataset": dataset, **r} for r in m.places(game_dir, map_dir)]
    with open(os.path.join(out, f"{dataset}.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    checked, bad = check(rows, map_dir, getattr(m, "PLACES_ONE_WAY", ()))
    world = getattr(m, "world_check", None)
    if world:
        c, b = world(game_dir, rows)
        checked, bad = checked + c, bad + b
    for b in bad:
        print(b)
    maps = sum(len(files) for _, _, files in os.walk(map_dir))
    print(f"{dataset}: {len(rows)} places, {maps} maps; {checked} checked, {len(bad)} mismatched")


LABEL_FONT = os.path.expanduser("~/Library/Fonts/Sarasa-SuperTTC.ttc")
LABEL_FACE = ("Sarasa Gothic J", "SemiBold")
LABEL_NUDGES = (0, -12, 12, -24, 24, -36, 36, -48, 48)
LABEL_NUDGES_FAR = tuple(n for k in range(0, 13) for n in ((-6 * k, 6 * k) if k else (0,)))  # number-only labels


def label_world_map(src, rows, icon_half, gap=2, size=20, scale=1, first=0, dots=False):
    """Draw an "id name" label for each place with a pos on the world map src (koei-wiki convention): white
    rounded box, black border and text. Each label goes below the icon (centred), else right of it (vertically
    centred), else above it, trying LABEL_NUDGES along the side; a spot is refused if it leaves the map or overlaps
    an icon box (pos ± icon_half) or an earlier label. Labels are placed top to bottom, then left to right. scale > 1
    enlarges the map (nearest neighbour) and pos by that factor first; icon_half is in enlarged pixels. The label number
    is id + first (1 where the game itself numbers from 1). dots=True is for maps without place icons (the 大航海
    schematics): each pos gets a red dot of radius icon_half, and a label that has no free spot shrinks to the number
    alone (the full list is on the wiki page)."""
    face = next((i for i in range(1000) if ImageFont.truetype(LABEL_FONT, size, index=i).getname() == LABEL_FACE),
                None)
    font = ImageFont.truetype(LABEL_FONT, size, index=face)
    im = Image.open(src).convert("RGB")
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    d = ImageDraw.Draw(im)
    rows = sorted(({**r, "pos": {"x": r["pos"]["x"] * scale, "y": r["pos"]["y"] * scale}} for r in rows if r.get("pos")),
                  key=lambda r: (r["pos"]["y"], r["pos"]["x"]))
    icons = [(r["pos"]["x"] - icon_half, r["pos"]["y"] - icon_half,
              r["pos"]["x"] + icon_half, r["pos"]["y"] + icon_half) for r in rows]

    def free(b, taken):
        return b[0] >= 0 and b[1] >= 0 and b[2] <= im.width and b[3] <= im.height and \
            not any(b[0] < q[2] and q[0] < b[2] and b[1] < q[3] and q[1] < b[3] for q in taken)

    if dots:
        for r in rows:
            x, y = r["pos"]["x"], r["pos"]["y"]
            d.ellipse((x - icon_half, y - icon_half, x + icon_half, y + icon_half), fill="red", outline="black")
    placed = []
    for r in rows:
        x, y = r["pos"]["x"], r["pos"]["y"]
        for text, nudges in [(f"{r['id'] + first} {r['name']}", LABEL_NUDGES)] + \
                ([(f"{r['id'] + first}", LABEL_NUDGES_FAR)] if dots else []):
            left, top, right, bottom = d.textbbox((0, 0), text, font=font)
            w, h = right - left + 10, bottom - top + 4
            spots = [(x - w // 2 + n, y + icon_half + gap) for n in nudges] + \
                [(x + icon_half + gap, y - h // 2 + n) for n in nudges] + \
                [(x - w // 2 + n, y - icon_half - gap - h) for n in nudges] + \
                [(x - icon_half - gap - w, y - h // 2 + n) for n in nudges if nudges is LABEL_NUDGES_FAR]
            box = next(((x0, y0, x0 + w, y0 + h) for x0, y0 in spots
                        if free((x0, y0, x0 + w, y0 + h), placed + icons)), None)
            if box:
                break
        if box is None:
            raise click.ClickException(f"no free spot for label {text}")
        placed.append(box)
        d.rounded_rectangle(box, radius=4, fill="white", outline="black")
        d.text((box[0] + 5 - left, box[1] + 2 - top), text, font=font, fill="black")
    return im


# dataset -> (world map file, half the size of a city icon around pos, enlargement)
LABELLED_MAPS = {"san4pk-pc98": ("MAINMAP.png", 24, 1), "kouryuuki-dos": ("world-spring.png", 24, 1),
                 "genpei-pc98": ("world-spring.png", 24, 2), "lempe-pc98": ("world.png", 24, 3)}
# label numbers start here instead of 0 where the map itself prints id + 1
LABEL_FIRST = {"lempe-pc98": 1}
# 大航海 world maps are schematics without port icons: draw dots, smaller text, number-only labels where crowded
LABELLED_MAPS.update({"koukai-pc98": ("world.png", 3, 2), "koukai2-pc98": ("world.png", 3, 1),
                      "koukai3-win": ("world.png", 3, 2), "koukai4pk-win": ("world.png", 3, 1),
                      "koukaigd-win": ("world.png", 3, 1)})
LABEL_DOTS = {"koukai-pc98", "koukai2-pc98", "koukai3-win", "koukai4pk-win", "koukaigd-win"}


@click.command()
@click.argument("dataset", type=click.Choice(list(LABELLED_MAPS)))
@click.option("--places", "places", required=True, help="places-export 的輸出目錄（讀 <dataset>.jsonl 與 world/ 的大地圖）")
def places_label(dataset, places):
    """在 places-export 的大地圖上標「編號 名稱」，寫 <dataset>/world/<圖名>-labelled.png（給 koei-wiki）

    dekoei.py places-label san4pk-pc98 --places ../export/koei-wiki/places
    """
    name, icon_half, scale = LABELLED_MAPS[dataset]
    with open(os.path.join(places, f"{dataset}.jsonl"), encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    world = os.path.join(places, dataset, "world")
    out = os.path.join(world, name.replace(".png", "-labelled.png"))
    dots = {"dots": True, "size": 16} if dataset in LABEL_DOTS else {}
    label_world_map(os.path.join(world, name), rows, icon_half, scale=scale, first=LABEL_FIRST.get(dataset, 0),
                    **dots).save(out)
    print(f"{dataset}: {sum(1 for r in rows if r.get('pos'))} labels -> {out}")
