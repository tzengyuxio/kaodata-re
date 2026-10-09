"""Export datasets in the kaodata unified format (kaodata/1).

Spec: docs/data-format.md of the kaodata website repo. Each dataset is written
as dataset.json + its pixel blobs (raw deflate, named in "blobs") +
checksums.json; the checksums
come from the reference renderer below, which implements spec §6.
"""
import hashlib
import json
import os
import subprocess
import unicodedata
import zlib

import click

import genpei

FORMAT = "kaodata/1"
TRANSPARENT = 255


# ---------------------------------------------------------------- reference renderer (spec §6)

def get_image(meta: dict, blobs: list[bytes], img: int) -> tuple[int, int, bytes]:
    offset, w, h, *rest = meta["images"][img]
    pixels = blobs[rest[0] if rest else 0]
    return w, h, pixels[offset:offset + w * h]


def blit(dst: bytearray, dw: int, dh: int, src: tuple[int, int, bytes], x: int, y: int) -> None:
    sw, sh, data = src
    for sy in range(sh):
        dy = y + sy
        if not 0 <= dy < dh:
            continue
        for sx in range(sw):
            dx = x + sx
            c = data[sy * sw + sx]
            if 0 <= dx < dw and c != TRANSPARENT:
                dst[dy * dw + dx] = c


def crop(src: tuple[int, int, bytes], rect) -> tuple[int, int, bytes]:
    sw, sh, data = src
    x, y, w, h = rect
    out = bytearray([TRANSPARENT]) * (w * h)
    for row in range(h):
        if 0 <= y + row < sh:
            for col in range(w):
                if 0 <= x + col < sw:
                    out[row * w + col] = data[(y + row) * sw + x + col]
    return w, h, bytes(out)


def over_background(meta: dict, blobs: list[bytes], shown: tuple[int, int, bytes], bg) -> tuple[int, int, bytes]:
    """Step 4: draw the windowed face over background `bg` (None = no background)."""
    if bg is None:
        return shown
    w, h, _ = shown
    out = bytearray([TRANSPARENT]) * (w * h)
    blit(out, w, h, get_image(meta, blobs, meta["backgrounds"][bg]), 0, 0)
    blit(out, w, h, shown, 0, 0)
    return w, h, bytes(out)


def compose_display(meta: dict, blobs: list[bytes], face: dict) -> tuple[int, int, bytes]:
    """Indexed display image of a composite face (steps 1-4)."""
    comp = meta["composite"]
    variant = comp["variants"][face["variant"]]
    cw, ch = comp["canvas"]
    canvas = bytearray([TRANSPARENT]) * (cw * ch)
    for slot, part in zip(comp["slots"], face["parts"]):
        sp = variant["parts"][slot["id"]]
        item = sp["items"][part]
        img, (x, y) = (item, sp.get("at", [0, 0])) if isinstance(item, int) else (item["img"], item["at"])
        blit(canvas, cw, ch, get_image(meta, blobs, img), x, y)
    shown = (cw, ch, bytes(canvas))
    if "window" in variant:
        shown = crop(shown, variant["window"])
    return over_background(meta, blobs, shown, face.get("bg"))


def portrait_display(meta: dict, blobs: list[bytes], index: int, bg=None) -> tuple[int, int, bytes]:
    """Portrait display: window crop, then background (if any)."""
    p = meta["portraits"][index]
    img = get_image(meta, blobs, p["img"])
    return over_background(meta, blobs, crop(img, p["window"]) if "window" in p else img, bg)


def to_rgba(src: tuple[int, int, bytes], colors: list[str]) -> bytes:
    rgb = [bytes.fromhex(c[1:]) for c in colors]
    return b"".join(b"\0\0\0\0" if c == TRANSPARENT else rgb[c] + b"\xff" for c in src[2])


def display_entries(meta: dict, blobs: list[bytes]):
    """(key, indexed display) for every face, as covered by checksums.json (spec §8)."""
    for ch in meta["characters"]:
        face = ch.get("face")
        if face is None:
            continue
        if "portrait" in face:
            yield f"ch:{ch['id']}", portrait_display(meta, blobs, face["portrait"], face.get("bg"))
        else:
            yield f"ch:{ch['id']}", compose_display(meta, blobs, face)
    for i in range(len(meta.get("portraits", []))):
        yield f"pt:{i}", portrait_display(meta, blobs, i)


def checksums(meta: dict, blobs: list[bytes]) -> dict:
    colors = meta["palettes"][0]["colors"]
    return {"algo": "sha256-rgba",
            "entries": {k: hashlib.sha256(to_rgba(img, colors)).hexdigest()
                        for k, img in display_entries(meta, blobs)}}


# ---------------------------------------------------------------- writer

class ImageStore:
    """Collects indexed images into named blobs (blob 0 = pixels.bin)."""

    def __init__(self, names: list[str]):
        self.names = names
        self.refs: list[list[int]] = []
        self.blobs = [bytearray() for _ in names]

    def add(self, w: int, h: int, px: bytes, blob: int = 0) -> int:
        assert len(px) == w * h
        self.refs.append([len(self.blobs[blob]), w, h] + ([blob] if blob else []))
        self.blobs[blob] += px
        return len(self.refs) - 1


def kana_to_hiragana(s: str) -> str:
    """Half-width katakana -> full-width hiragana (NFKC merges voiced marks)."""
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in unicodedata.normalize("NFKC", s))


def revision() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
                          cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()


def write_dataset(out_dir: str, meta: dict, blobs: list[bytes]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for name, pixels in zip(meta.get("blobs", ["pixels.bin"]), blobs):
        comp = zlib.compressobj(9, zlib.DEFLATED, -15)
        with open(os.path.join(out_dir, name), "wb") as f:
            f.write(comp.compress(pixels) + comp.flush())
    with open(os.path.join(out_dir, "dataset.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out_dir, "checksums.json"), "w", encoding="utf-8") as f:
        json.dump(checksums(meta, blobs), f, indent=1)


# ---------------------------------------------------------------- GENPEI (DOS)

GENPEI_INPUTS = ["Mainpal.pld", "Montage.gp", "Haikei.gp", "Kaodata.gp", "Main.exe", "Sndata.gp"]
GENPEI_VARIANT_LABELS = ["大鎧戴兜", "鎧", "直垂"]
GENPEI_SLOTS = [("body", "身"), ("head", "頭"), ("eyes", "眼"), ("mouth", "口")]
GENPEI_PART_COUNT = {"head": 8, "body": 8, "eyes": 16, "mouth": 16}


def build_genpei(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in GENPEI_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    palette = genpei.load_mainpal(files["Mainpal.pld"], 0)
    variants = []
    for t, layers in enumerate(genpei.montage_types(genpei.unpack_main_exe(files["Main.exe"]))):
        parts = {}
        for slot, _ in GENPEI_SLOTS:
            src, off, w, h, at = layers[slot]
            step = w * h * 3 // 8 + w * h // 8
            items = [store.add(w, h, genpei.masked_part(files[src], off + i * step, w, h))
                     for i in range(GENPEI_PART_COUNT[slot])]
            parts[slot] = {"at": list(at), "items": items}
        variants.append({"id": str(t + 1), "label": GENPEI_VARIANT_LABELS[t],
                         "window": [*layers["window"], 64, 80], "parts": parts})
    bw, bh, _ = genpei.HAIKEI_BG
    backgrounds = [store.add(bw, bh, bytes(px)) for px in genpei.load_backgrounds(files["Haikei.gp"])]
    portraits = [{"img": store.add(128, 160, px, blob=1), "window": [x, y, 64, 80]}
                 for px, (x, y) in genpei.load_kaodata(files["Kaodata.gp"])]

    # the face code of a general is the same in all four scenarios
    scenarios = [genpei.load_generals(files["Sndata.gp"], k) for k in range(4)]
    assert all(g["face"] == g0["face"] for s in scenarios[1:] for g, g0 in zip(s, scenarios[0]))
    characters = []
    # the game draws every face (Kaodata or montage) over background (id >> 1) % 5
    for g in scenarios[0]:
        ch = {"id": g["id"], "name": g["surname"] + g["given"],
              "reading": f"{kana_to_hiragana(g['surname_kana'])} {kana_to_hiragana(g['given_kana'])}".strip()}
        code = g["face"]
        if code < len(portraits):
            ch["face"] = {"portrait": code, "bg": (g["id"] >> 1) % 5}
        elif code >= 0x4000 and code != 0xFFFF:
            ch["face"] = {"variant": (code >> 14) - 1,
                          "parts": [code >> 8 & 7, code >> 11 & 7, code >> 4 & 15, code & 15],
                          "bg": (g["id"] >> 1) % 5, "code": f"{code:04X}"}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "genpei-dos", "game": "GENPEI", "platform": "DOS",
        "title": {"ja": "源平合戦", "zh": "源平合戰"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in GENPEI_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "main", "label": "Mainpal 第 0 組",
                      "colors": ["#%02x%02x%02x" % c for c in palette]}],
        "blobs": store.names,
        "images": store.refs,
        "backgrounds": backgrounds,
        "composite": {
            "canvas": [128, 160],
            "slots": [{"id": i, "label": label} for i, label in GENPEI_SLOTS],
            "variants": variants,
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "$variant", "hi": 15, "lo": 14, "base": 1},
                {"of": "head", "hi": 13, "lo": 11},
                {"of": "body", "hi": 10, "lo": 8},
                {"of": "eyes", "hi": 7, "lo": 4},
                {"of": "mouth", "hi": 3, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


DATASETS = {"genpei-dos": build_genpei}


@click.command(help="匯出 kaodata 統一格式資料集 (DATASET: genpei-dos)")
@click.argument("dataset", type=click.Choice(sorted(DATASETS)))
@click.option("--game-dir", required=True, type=click.Path(exists=True, file_okay=False), help="原版遊戲目錄")
@click.option("--out", "out_dir", required=True, help="輸出目錄")
def export(dataset, game_dir, out_dir):
    meta, blobs = DATASETS[dataset](game_dir)
    write_dataset(out_dir, meta, blobs)
    faces = [c["face"] for c in meta["characters"] if "face" in c]
    n_portrait = sum("portrait" in f for f in faces)
    print(f"{dataset}: {len(meta['characters'])} characters "
          f"({len(faces) - n_portrait} composite, {n_portrait} portrait), "
          f"{len(meta['portraits'])} portraits, {len(meta['images'])} images")
    for name, px in [*zip(meta["blobs"], blobs), ("dataset.json", None), ("checksums.json", None)]:
        raw = f"{len(px)} px -> " if px is not None else ""
        print(f"  {name}: {raw}{os.path.getsize(os.path.join(out_dir, name))} B")
