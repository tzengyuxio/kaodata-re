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
from collections import Counter

import click

import genpei
import koei_games
import san2
import san3
import sango
import utils

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
    def face_display(face):
        if "portrait" in face:
            return portrait_display(meta, blobs, face["portrait"], face.get("bg"))
        return compose_display(meta, blobs, face)

    for ch in meta["characters"]:
        face = ch.get("face")
        if face is None:
            continue
        yield f"ch:{ch['id']}", face_display(face)
        for k, expr in enumerate(ch.get("expressions", []), 1):
            yield f"ch:{ch['id']}/{k}", face_display(expr)
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


# ---------------------------------------------------------------- SAN2 (DOS, Chinese)

SAN2_INPUTS = ["KAODATA.DAT", "MONTAGE.DAT", "SCENARIO.DAT", "TAIKI.DAT"]
SAN2_PALETTE = ["#000000", "#55ff55", "#ff5555", "#ffff55", "#5555ff", "#55ffff", "#ff55ff", "#ffffff"]  # EGA
# montage areas in drawing order; nose and mouth are named by where the game draws them
SAN2_SLOTS = [("top", "上"), ("bottom", "下"), ("eyes", "眼"), ("mouth", "口"), ("nose", "鼻")]
SAN2_FACE = 960  # 64x40 half-height, 3bpp
# historical spelling where the game's name differs, by character id (checked against the
# faction field and san2-fc; 南蠻 names follow 三國演義)
SAN2_NAME_HISTORICAL = {
    31: "張顗", 61: "蔡瑁", 67: "張咨", 98: "趙範", 121: "劉璝", 122: "雷銅", 157: "于禁", 164: "夏侯楙",
    167: "桓階", 181: "陳紀", 218: "李堪", 220: "廖化", 249: "嚴畯", 258: "步騭", 260: "蔡中", 264: "向舉",
    284: "向寵", 297: "鮑隆", 306: "朵思大王", 308: "阿會喃", 315: "金環三結", 319: "董荼那", 322: "沙摩柯",
    332: "毌丘儉",
}
# KAODATA portraits no character uses (0-based), per koei-wiki 遊戲/三國志II/人物顏
SAN2_PORTRAIT_GROUPS = {
    27: "特殊人物", 177: "特殊人物", 190: "特殊人物",
    **{i: "新君主" for i in range(191, 203)},  # age x sex x civil/military
    **{i: "女兒" for i in range(203, 219)},  # daughters of factions 0-15 (marriage diplomacy)
}
SAN2_PORTRAIT_NAMES = {27: "華佗", 177: "司馬徽", 190: "許子將"}


def san2_pixels(raw: bytes, opaque: bool) -> tuple[int, int, bytes]:
    """3bpp half-height rows (24 bytes each) -> full-height 64-wide indexes; 0 -> 255 unless opaque."""
    px = bytes(c if opaque or c else TRANSPARENT for c in utils.to_3bpp_indexes(raw))
    rows = [px[i:i + 64] for i in range(0, len(px), 64)]
    return 64, 2 * len(rows), b"".join(r + r for r in rows)


def build_san2(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SAN2_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for head in range(8):
        parts = {}
        for area, (slot, _) in enumerate(SAN2_SLOTS):
            items = []
            for rec in range(4):
                w, h, px = san2_pixels(san2.montage_record(files["MONTAGE.DAT"], head, area, rec), area < 2)
                items.append(store.add(w, h, px))
            parts[slot] = {"at": [0, san2.MONTAGE_AREAS[area][2] // 24 * 2], "items": items}
        variants.append({"id": str(head), "label": f"類型 {head}", "parts": parts})

    kao = files["KAODATA.DAT"]
    portraits = [{"img": store.add(*san2_pixels(kao[i:i + SAN2_FACE], True), blob=1), "code": f"{i // SAN2_FACE + 1:04X}"}
                 for i in range(0, len(kao), SAN2_FACE)]
    for i, group in SAN2_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in SAN2_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    characters = []
    for p in san2.load_san2_persons(os.path.join(game_dir, "SCENARIO.DAT"), os.path.join(game_dir, "TAIKI.DAT")):
        ch = {"id": p.id, "name": p["name"]}
        if p.id in SAN2_NAME_HISTORICAL:
            ch["nameHistorical"] = SAN2_NAME_HISTORICAL[p.id]
        code = p.face
        if san2.is_montage_code(code):
            ch["face"] = {"variant": code & 7, "parts": [code >> s & 3 for s in san2.MONTAGE_SHIFTS],
                          "code": f"{code:04X}"}
        elif 1 <= code <= len(portraits):
            ch["face"] = {"portrait": code - 1}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "san2-dos", "game": "SAN2", "platform": "DOS",
        "title": {"ja": "三國志II", "zh": "三國志II"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SAN2_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "ega", "label": "EGA", "colors": SAN2_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": i, "label": label} for i, label in SAN2_SLOTS],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


SAN3_INPUTS = ["KAODATA.DAT", "MONTAGE.DAT"] + [f"SNDATA{i}B.CIM" for i in range(1, 7)]
# DAC palette at DGROUP 0x322E of MAIN.EXE, colours 0-7, 6-bit values widened as (v << 2) | (v >> 4)
SAN3_PALETTE = ["#000000", "#0041F3", "#F35100", "#F351D3", "#10B251", "#00C3F3", "#F3E300", "#F3F3F3"]
SAN3_SLOTS = [("top", "上"), ("bottom", "下"), ("eyes", "眼"), ("nose", "鼻"), ("mouth", "口")]
SAN3_FACE = 1920  # 64x80, 3bpp
# spelling when the scenarios tie (陳群 3 times, 陳韋 3 times)
SAN3_NAME_PICK = {0x7E: "陳群"}
# the game uses another person's name for these, by face code (identity from city, see notes/san3.md)
SAN3_NAME_HISTORICAL = {0xC1: "孔伷", 0xC02B: "蔡邕", 0x96D9: "張顗", 0x9C95: "張闓"}
# event characters (MAIN.EXE DGROUP 0x2FB6 names / 0x2FCA codes) and 貂蟬 (連環計 sets face 307)
SAN3_PORTRAIT_NAMES = {27: "華佗", 177: "司馬徽", 190: "許子將", 223: "獻帝", 224: "吉平", 225: "于吉", 226: "左慈",
                       227: "管輅", 228: "紫虛上人", 229: "李意", 306: "貂蟬"}
# new rulers / new officers offered by the face picker at 0x116E3, by sex
SAN3_PORTRAIT_GROUPS = {
    **{i: "事件人物" for i in SAN3_PORTRAIT_NAMES},
    **{i: "新君主（男）" for i in range(230, 238)},
    **{i: "新君主（女）" for i in range(238, 246)},
    **{i: "新武將（男）" for i in range(246, 276)},
    **{i: "新武將（女）" for i in range(276, 306)},
}


def san3_pixels(raw: bytes, opaque: bool) -> tuple[int, int, bytes]:
    """3bpp planar rows (24 bytes each, byte k = bit k); 0 -> 255 unless opaque."""
    h = len(raw) // 24
    px = genpei.decode_planar(raw, 0, 64, h, 3)
    return 64, h, bytes(c if opaque or c else TRANSPARENT for c in px)


def san3_characters(game_dir: str) -> list[tuple[int, str]]:
    """(face code, name) per person: scenarios 1-6 in order, deduplicated by face code."""
    spellings: dict[int, Counter] = {}
    for name in SAN3_INPUTS[2:]:
        for p in san3.load_san3_persons(os.path.join(game_dir, name)):
            spellings.setdefault(p.face, Counter())[p["name"].strip()] += 1
    return [(code, SAN3_NAME_PICK.get(code) or names.most_common(1)[0][0]) for code, names in spellings.items()]


def build_san3(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SAN3_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for head in range(len(files["MONTAGE.DAT"]) // san3.MONTAGE_HEAD_SIZE):
        parts = {}
        for area, (slot, _) in enumerate(SAN3_SLOTS):
            items = [store.add(*san3_pixels(san3.montage_record(files["MONTAGE.DAT"], head, area, rec), area < 2))
                     for rec in range(san3.MONTAGE_RECORDS[area])]
            parts[slot] = {"at": [0, san3.MONTAGE_AREAS[area][2] // 24], "items": items}
        variants.append({"id": str(head), "label": f"類型 {head}", "parts": parts})

    kao = files["KAODATA.DAT"]
    portraits = [{"img": store.add(*san3_pixels(kao[i:i + SAN3_FACE], True), blob=1), "code": f"{i // SAN3_FACE + 1:04X}"}
                 for i in range(0, len(kao), SAN3_FACE)]
    for i, group in SAN3_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in SAN3_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    characters = []
    for cid, (code, name) in enumerate(san3_characters(game_dir)):
        ch = {"id": cid, "name": name}
        if code in SAN3_NAME_HISTORICAL:
            ch["nameHistorical"] = SAN3_NAME_HISTORICAL[code]
        if san3.is_montage_code(code):
            ch["face"] = {"variant": san3.montage_head(code), "parts": san3.montage_parts(code), "code": f"{code:04X}"}
        else:
            ch["face"] = {"portrait": code - 1}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "san3-dos", "game": "SAN3", "platform": "DOS",
        "title": {"ja": "三國志III", "zh": "三國志III"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SAN3_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "vga", "label": "VGA", "colors": SAN3_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": i, "label": label} for i, label in SAN3_SLOTS],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


SAN4_INPUTS = ["KAODATA.S4", "MONDATA.S4", "SNDATA.S4", "TAIKI.S4"]
# DGROUP 0xF52 of MAIN.EXE (B, R, G, 4 bits each), colours 8-15 are the faces; widened as (v << 4) | (v >> 2)
SAN4_PALETTE = ["#302000", "#204182", "#B24120", "#C38251", "#417120", "#418292", "#D3B282", "#D3D3B2"]
SAN4_SLOTS = [("top", "上"), ("bottom", "下"), ("eyes", "眼"), ("mouth", "口")]
# named speakers: DGROUP 0x127E event table, overlay 2 event scripts (see notes/san4.md)
SAN4_PORTRAIT_NAMES = {250: "華佗", 251: "馬鈞", 252: "司馬徽", 253: "許子將", 254: "于吉", 255: "左慈", 256: "管輅",
                       257: "普淨", 333: "密探", 334: "士兵", 335: "書僮", 338: "貂蟬", 339: "獻帝"}
# new rulers / new officers offered by the face picker (overlay 1), by sex; 舉兵 event (DGROUP 0x7CEE)
SAN4_PORTRAIT_GROUPS = {
    **{i: "事件人物" for i in SAN4_PORTRAIT_NAMES},
    **{i: "新君主（男）" for i in range(258, 264)},
    **{i: "新君主（女）" for i in range(264, 270)},
    **{i: "新武將（男）" for i in range(270, 300)},
    **{i: "新武將（女）" for i in range(300, 330)},
    **{i: "舉兵事件" for i in (330, 331, 332, 336, 337)},
}


def build_san4(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SAN4_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    mon = files["MONDATA.S4"]
    variants = []
    for head in range(len(mon) // sango.SAN4_MONTAGE_HEAD_SIZE):
        parts = {}
        for area, (slot, _) in enumerate(SAN4_SLOTS):
            items = []
            for rec in range(sango.SAN4_MONTAGE_AREAS[area][2]):
                w, h, px = sango.san4_montage_record(mon, head, area, rec)
                # the game ORs eyes and mouth over the face, the same as colour 0 being transparent
                items.append(store.add(w, h, bytes(c if area < 2 or c else TRANSPARENT for c in px)))
            parts[slot] = {"at": [0, sango.SAN4_MONTAGE_ROWS[area][head]], "items": items}
        variants.append({"id": str(head), "label": f"類型 {head}", "parts": parts})

    faces = sango.load_san4_faces(os.path.join(game_dir, "KAODATA.S4"))
    portraits = [{"img": store.add(*face, blob=1), "code": f"{i:04X}"} for i, face in enumerate(faces)]
    for i, group in SAN4_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in SAN4_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    characters = []
    # scenarios 1-6 in order; 羌族、烏丸族、山越族、南蠻族 share one face code, so key on the name too
    seen = set()
    for _, name, code in sango.load_san4_persons(os.path.join(game_dir, "SNDATA.S4"),
                                                  os.path.join(game_dir, "TAIKI.S4")):
        if (code, name) in seen:
            continue
        seen.add((code, name))
        ch = {"id": len(characters), "name": name}
        if code & 0x8000:
            ch["face"] = {"variant": code & 15, "parts": sango.san4_montage_parts(code), "code": f"{code:04X}"}
        else:
            ch["face"] = {"portrait": code}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "san4-dos", "game": "SAN4", "platform": "DOS",
        "title": {"ja": "三國志IV", "zh": "三國志IV"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SAN4_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "vga", "label": "VGA", "colors": SAN4_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": i, "label": label} for i, label in SAN4_SLOTS],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


LEMPE_INPUTS = ["KAODATA.DAT", "NPDATA.CIM"]
# correct name where the Chinese release names a different person than the English one
# (identity from the English and Japanese names, see koei-wiki 拿破崙/人物資料 mapping)
LEMPE_NAME_HISTORICAL = {
    25: "米約", 52: "古爾戈", 77: "薩默塞特", 104: "烏瓦羅夫", 109: "戈爾恰科夫", 121: "沃龍佐夫", 138: "烏迪諾",
    150: "奧特", 160: "普羅韋拉", 165: "呂西尼昂", 175: "貝爾格",
}
# face numbers past the person byte, passed to the face routine by MAIN.EXE (see notes/lempe.md)
LEMPE_PORTRAIT_GROUPS = {257: "事件人物", 258: "事件人物", 259: "事件人物"}
LEMPE_PORTRAIT_NAMES = {257: "約瑟芬", 258: "瑪麗路易斯", 259: "尼爾森"}
# Napoleon (character 0) by rank: <=5, 6, 7; labels are the Chinese MAIN.EXE titles
LEMPE_NAPOLEON_FACES = [(0, "司令官"), (255, "第一執政"), (256, "皇帝")]


def build_lempe(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in LEMPE_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    kao = files["KAODATA.DAT"]
    portraits = [{"img": store.add(*san2_pixels(kao[i:i + SAN2_FACE], True)), "code": f"{i // SAN2_FACE:04X}"}
                 for i in range(0, len(kao), SAN2_FACE)]
    for i, group in LEMPE_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in LEMPE_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    characters = []
    # the five scenarios list the same 255 people in the same order
    for p in koei_games.load_lempe_persons(os.path.join(game_dir, "NPDATA.CIM")):
        ch = {"id": p.id, "name": p["name"]}
        if p.id in LEMPE_NAME_HISTORICAL:
            ch["nameHistorical"] = LEMPE_NAME_HISTORICAL[p.id]
        ch["face"] = {"portrait": p.face}
        if p.id == 0:
            (_, label), *rest = LEMPE_NAPOLEON_FACES
            ch["face"]["label"] = label
            ch["expressions"] = [{"portrait": i, "label": label} for i, label in rest]
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "lempe-dos", "game": "LEMPE", "platform": "DOS",
        "title": {"ja": "ランペルール", "zh": "拿破崙"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in LEMPE_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "ega", "label": "EGA", "colors": SAN2_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


DATASETS = {"genpei-dos": build_genpei, "san2-dos": build_san2, "san3-dos": build_san3, "lempe-dos": build_lempe,
            "san4-dos": build_san4}


@click.command(help="匯出 kaodata 統一格式資料集 (DATASET: genpei-dos, san2-dos, san3-dos, san4-dos, lempe-dos)")
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
