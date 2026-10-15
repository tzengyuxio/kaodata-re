"""Export datasets in the kaodata unified format (kaodata/1).

Spec: docs/data-format.md of the kaodata website repo. Each dataset is written
as dataset.json + its pixel blobs (raw deflate, named in "blobs") +
checksums.json; the checksums
come from the reference renderer below, which implements spec §6.
"""
import hashlib
import json
import os
import struct
import subprocess
import unicodedata
import zlib
from collections import Counter

import click
from PIL import Image

import genpei
import koei_games
import liberty
import ls11
import pc88
from pc88 import brg_pixels
import san1
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


def blit(dst: bytearray, dw: int, dh: int, src: tuple[int, int, bytes], x: int, y: int, blend: str | None = None) -> None:
    sw, sh, data = src
    for sy in range(sh):
        dy = y + sy
        if not 0 <= dy < dh:
            continue
        for sx in range(sw):
            dx = x + sx
            c = data[sy * sw + sx]
            if 0 <= dx < dw and c != TRANSPARENT:
                d = dst[dy * dw + dx]
                if blend and d != TRANSPARENT:
                    c = c ^ d if blend == "xor" else c | d
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
        blit(canvas, cw, ch, get_image(meta, blobs, img), x, y, slot.get("blend"))
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
# PC-98: the same Mainpal/Montage/Haikei/Kaodata files; MAIN.EXE is not packed and has the composition table at
# file 0x5DAF4; SNDATA.GP has the same layout and face codes
GENPEI_PC98_MONTAGE_TABLE = 0x5DAF4
# PC-98 393 is written 宗商人, a look-alike typo of 宋商人 (the Song merchant; DOS has it right)
GENPEI_NAME_HISTORICAL = {"宗商人": "宋商人"}


def build_genpei(game_dir: str, pc98: bool = False) -> tuple[dict, list[bytes]]:
    files = {}
    for name in GENPEI_INPUTS:
        with open(os.path.join(game_dir, name.upper() if pc98 else name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    palette = genpei.load_mainpal(files["Mainpal.pld"], 0)
    variants = []
    table = (genpei.montage_types(files["Main.exe"], GENPEI_PC98_MONTAGE_TABLE) if pc98 else
             genpei.montage_types(genpei.unpack_main_exe(files["Main.exe"])))
    for t, layers in enumerate(table):
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
        if ch["name"] in GENPEI_NAME_HISTORICAL:
            ch["nameHistorical"] = GENPEI_NAME_HISTORICAL[ch["name"]]
        code = g["face"]
        if code < len(portraits):
            ch["face"] = {"portrait": code, "bg": (g["id"] >> 1) % 5}
        elif code >= 0x4000 and code != 0xFFFF:
            ch["face"] = {"variant": (code >> 14) - 1,
                          "parts": [code >> 8 & 7, code >> 11 & 7, code >> 4 & 15, code & 15],
                          "bg": (g["id"] >> 1) % 5, "code": f"{code:04X}"}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "genpei-pc98" if pc98 else "genpei-dos", "game": "GENPEI",
        "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "源平合戦", "zh": "源平合戰"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n.upper() if pc98 else n, "sha1": hashlib.sha1(files[n]).hexdigest()}
                              for n in GENPEI_INPUTS]},
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
    317: "龐羲", 332: "毌丘儉",
}
# KAODATA portraits no character uses (0-based), per koei-wiki 遊戲/三國志II/人物顏
SAN2_PORTRAIT_GROUPS = {
    27: "特殊人物", 177: "特殊人物", 190: "特殊人物",
    **{i: "新君主" for i in range(191, 203)},  # age x sex x civil/military
    **{i: "女兒" for i in range(203, 219)},  # daughters of factions 0-15 (marriage diplomacy)
}
SAN2_PORTRAIT_NAMES = {27: "華佗", 177: "司馬徽", 190: "許子將"}
# PC-98 / X68000 (Japanese): full-height faces, nose and mouth swapped compared with DOS
SAN2_JP_INPUTS = ["KAODATA1.DAT", "KAODATA2.DAT", "KAODATA3.DAT"] + [f"SNDATA{i}.CIM" for i in range(1, 7)] + ["TAIKI.DAT"]
# the default 8-colour digital palette (PC-98) / text palette at $9F88E of MAIN.Z (X68000), all channels 0 or max
SAN2_JP_PALETTE = ["#000000", "#00ff00", "#ff0000", "#ffff00", "#0000ff", "#00ffff", "#ff00ff", "#ffffff"]
SAN2_JP_SLOTS = [("top", "上"), ("bottom", "下"), ("eyes", "眼"), ("nose", "鼻"), ("mouth", "口")]
SAN2_JP_PORTRAIT_NAMES = {27: "華陀", 177: "司馬徽", 190: "許子将"}
# misspelt names in the Japanese release (the SAN2_NAME_HISTORICAL ones it shares, plus 粱剛), by character id
SAN2_JP_NAME_HISTORICAL = {
    67: "張咨", 122: "雷銅", 167: "桓階", 181: "陳紀", 218: "李堪", 258: "歩騭", 260: "蔡中", 264: "向挙", 284: "向寵",
    297: "鮑隆", 306: "朶思大王", 315: "金環三結", 319: "董荼那", 322: "沙摩柯",
    125: "梁剛", 317: "龐羲", 332: "毌丘倹",
}


def san2_pixels(raw: bytes, opaque: bool) -> tuple[int, int, bytes]:
    """3bpp half-height rows (24 bytes each) -> full-height 64-wide indexes; 0 -> 255 unless opaque."""
    px = bytes(c if opaque or c else TRANSPARENT for c in utils.to_3bpp_indexes(raw))
    rows = [px[i:i + 64] for i in range(0, len(px), 64)]
    return 64, 2 * len(rows), b"".join(r + r for r in rows)


def san2_jp_pixels(raw: bytes, opaque: bool) -> tuple[int, int, bytes]:
    """3bpp full-height rows (24 bytes each, first byte = bit 2 as in DOS); 0 -> 255 unless opaque."""
    return 64, len(raw) // 24, bytes(c if opaque or c else TRANSPARENT for c in utils.to_3bpp_indexes(raw))


def build_san2_jp(game_dir: str, platform: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SAN2_JP_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for head in range(8):
        parts = {}
        for area, (slot, _) in enumerate(SAN2_JP_SLOTS):
            items = [store.add(*san2_jp_pixels(san2.jp_montage_record(files["KAODATA3.DAT"], head, area, rec), area < 2))
                     for rec in range(4)]
            parts[slot] = {"at": [0, san2.JP_MONTAGE_AREAS[area][2]], "items": items}
        variants.append({"id": str(head), "label": f"類型 {head}", "parts": parts})

    kao = b"".join(files[name][:count * san2.JP_FACE] for name, count in san2.JP_FACE_FILES)
    portraits = [{"img": store.add(*san2_jp_pixels(kao[i:i + san2.JP_FACE], True), blob=1),
                  "code": f"{i // san2.JP_FACE + 1:04X}"} for i in range(0, len(kao), san2.JP_FACE)]
    for i, group in SAN2_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in SAN2_JP_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    characters = []
    for cid, (code, name) in enumerate(san2.load_san2_jp_persons(game_dir, platform == "X68")):
        ch = {"id": cid, "name": name}
        if cid in SAN2_JP_NAME_HISTORICAL:
            ch["nameHistorical"] = SAN2_JP_NAME_HISTORICAL[cid]
        if san2.is_montage_code(code):
            ch["face"] = {"variant": code & 7, "parts": [code >> s & 3 for s in san2.MONTAGE_SHIFTS],
                          "code": f"{code:04X}"}
        elif 1 <= code <= len(portraits):
            ch["face"] = {"portrait": code - 1}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": f"san2-{platform.lower()}", "game": "SAN2", "platform": platform,
        "title": {"ja": "三國志II", "zh": "三國志II"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SAN2_JP_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": platform.lower(), "label": platform, "colors": SAN2_JP_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": i, "label": label} for i, label in SAN2_JP_SLOTS],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


SAN2_PC88_INPUTS = ["KAODATA.DAT"] + [f"SNDATA{i}.CIM" for i in range(1, 7)] + ["TAIKI.DAT"]


def build_san2_pc88(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SAN2_PC88_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    kao = files["KAODATA.DAT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for head in range(8):
        parts = {}
        for area, (slot, _) in enumerate(SAN2_JP_SLOTS):
            items = [store.add(*san2_pixels(san2.pc88_montage_record(kao, head, area, rec), area < 2)) for rec in range(4)]
            parts[slot] = {"at": [0, san2.PC88_MONTAGE_AREAS[area][2] // 24 * 2], "items": items}
        variants.append({"id": str(head), "label": f"類型 {head}", "parts": parts})

    portraits = [{"img": store.add(*san2_pixels(kao[i:i + SAN2_FACE], True), blob=1), "code": f"{i // SAN2_FACE + 1:04X}"}
                 for i in range(0, san2.PC88_MONTAGE_OFFSET, SAN2_FACE)]
    for i, group in SAN2_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in SAN2_JP_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    def face(code):
        if san2.is_montage_code(code):
            return {"variant": code & 7, "parts": [code >> s & 3 for s in san2.MONTAGE_SHIFTS], "code": f"{code:04X}"}
        return {"portrait": code - 1}

    # five persons have another composite code in some scenarios: one character, the later code as an expression
    characters, by_name = [], {}
    for code, name, sources in san2.load_san2_pc88_persons(game_dir):
        label = "、".join(dict.fromkeys(f"劇本 {s}" if s.isdigit() else s for s in sources))
        if name in by_name:
            by_name[name].setdefault("expressions", []).append({**face(code), "label": label})
            continue
        ch = by_name[name] = {"id": len(characters), "name": name}
        if ch["id"] in SAN2_JP_NAME_HISTORICAL:
            ch["nameHistorical"] = SAN2_JP_NAME_HISTORICAL[ch["id"]]
        ch["face"] = face(code)
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "san2-pc88", "game": "SAN2", "platform": "PC88",
        "title": {"ja": "三國志II", "zh": "三國志II"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SAN2_PC88_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc88", "label": "PC88", "colors": SAN2_JP_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": i, "label": label} for i, label in SAN2_JP_SLOTS],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]

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
# historical spelling by face code: another person's name (identity from city) or a misspelling,
# per koei-wiki 遊戲/三國志III/人名勘誤 (see notes/san3.md)
SAN3_NAME_HISTORICAL = {
    0xC1: "孔伷", 0xC02B: "蔡邕", 0x96D9: "張顗", 0x9C95: "張闓", 0xC4E8: "桓階", 0xDCB3: "劉璝", 0x8AA8: "于糜",
    0xC860: "閻象", 0xCCF9: "笮融", 0xCC33: "向舉", 0x8699: "全琮", 0xCE79: "龐羲", 7: "王粲", 72: "沙摩柯",
    38: "毌丘儉", 49: "金環三結", 135: "董荼那", 112: "朵思大王", 0x8284: "曹羲", 0x8EBB: "孫冀",
}
SAN3_PC98_NAME_HISTORICAL = {
    0xC4E8: "桓階", 0x8AA8: "于糜", 86: "鍾繇", 0x96A5: "鍾進", 53: "鍾会", 0x9512: "梁剛", 76: "諸葛瑾",
    0xCC33: "向挙", 0xCE79: "龐羲", 72: "沙摩柯", 38: "毌丘倹", 49: "金環三結", 135: "董荼那", 112: "朶思大王",
}
# event characters (MAIN.EXE DGROUP 0x2FB6 names / 0x2FCA codes) and 貂蟬 (連環計 sets face 307)
SAN3_PORTRAIT_NAMES = {27: "華佗", 177: "司馬徽", 190: "許子將", 223: "獻帝", 224: "吉平", 225: "于吉", 226: "左慈",
                       227: "管輅", 228: "紫虛上人", 229: "李意", 306: "貂蟬"}
# PC-98: palette at DGROUP 0x2A3A of MAIN.EXE (B, R, G, 4 bits each), widened as v * 17; names as the game spells them
SAN3_PC98_PALETTE = ["#000000", "#0044FF", "#FF5500", "#FF55DD", "#11BB55", "#00CCFF", "#FFEE00", "#FFFFFF"]
SAN3_PC98_PORTRAIT_NAMES = {27: "華佗", 177: "司馬徽", 190: "許子将", 223: "献帝", 224: "吉平", 225: "干吉", 226: "左慈",
                            227: "管輅", 228: "紫虚上人", 229: "李意", 306: "貂蝉"}
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


def san3_characters(game_dir: str, pc98: bool = False) -> list[tuple[int, str]]:
    """(face code, name) per person: scenarios 1-6 in order, deduplicated by face code."""
    spellings: dict[int, Counter] = {}
    for name in SAN3_INPUTS[2:]:
        path = os.path.join(game_dir, name)
        persons = san3.load_san3_pc98_persons(path) if pc98 else \
            [(p.face, p["name"].strip()) for p in san3.load_san3_persons(path)]
        for code, person_name in persons:
            spellings.setdefault(code, Counter())[person_name] += 1
    pick = {} if pc98 else SAN3_NAME_PICK
    return [(code, pick.get(code) or names.most_common(1)[0][0]) for code, names in spellings.items()]


def build_san3(game_dir: str, pc98: bool = False) -> tuple[dict, list[bytes]]:
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
    for i, name in (SAN3_PC98_PORTRAIT_NAMES if pc98 else SAN3_PORTRAIT_NAMES).items():
        portraits[i]["name"] = name

    characters = []
    for cid, (code, name) in enumerate(san3_characters(game_dir, pc98)):
        ch = {"id": cid, "name": name}
        historical = SAN3_PC98_NAME_HISTORICAL if pc98 else SAN3_NAME_HISTORICAL
        if code in historical:
            ch["nameHistorical"] = historical[code]
        if san3.is_montage_code(code):
            ch["face"] = {"variant": san3.montage_head(code), "parts": san3.montage_parts(code), "code": f"{code:04X}"}
        elif 1 <= code <= len(portraits):
            ch["face"] = {"portrait": code - 1}
        else:
            raise ValueError(f"{name}: face code {code:#06x} out of range")
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "san3-pc98" if pc98 else "san3-dos", "game": "SAN3", "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "三國志III", "zh": "三國志III"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SAN3_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": SAN3_PC98_PALETTE} if pc98 else
                     {"id": "vga", "label": "VGA", "colors": SAN3_PALETTE}],
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
# historical spelling by face code; the DOS release also writes 孔秀 (another person) for 孔伷
SAN4_NAME_HISTORICAL = {0x38: "孔伷", 199: "盧植", 0xE85A: "龐羲", 135: "沙摩柯", 0xE56A: "吳綱"}
SAN4_PC98_NAME_HISTORICAL = {199: "盧植", 0xE85A: "龐羲", 135: "沙摩柯", 0xE56A: "呉綱"}
# PC-98: the same palette bytes as DOS (DGROUP 0xF70), widened as v * 17; names as the game spells them.
# 1.0 speaks as 童子 with 336 and picks 335 for 舉兵 (swapped, PK fixed it); labelled by the pictures here
SAN4_PC98_PALETTE = ["#332200", "#224488", "#BB4422", "#CC8855", "#447722", "#448899", "#DDBB88", "#DDDDBB"]
# PC-98 PK: the game shows faces from KAODATAP.S4 (0-339 = KAODATA.S4, 340-456 = the NBDATA.SUI 水滸伝
# officers); the new-officer picker offers KAODATA2.S4 as codes 340-659 (0-149 三國志III, 150-319 水滸伝).
# Picker faces not in KAODATAP, in KAODATA2 order, named as in 三國志III PC-98 / 水滸伝 PC-98 (- = no name)
SAN4PK_INPUTS = SAN4_INPUTS + ["KAODATAP.S4", "KAODATA2.S4", "NBDATA.SUI"]
SAN4PK_SHOWN = 457
SAN4PK_EXTRA_NAMES = (
    "伊籍 袁紹 袁譚 諸葛誕 華歆 賈詡 郭嘉 郝昭 郭図 夏侯淵 夏侯惇 夏侯覇 華佗 華雄 関羽 甘寧 関平 顔良 姜維 許褚 魏延 鐘会 虞翻 "
    "厳顔 黄蓋 公孫瓚 黄忠 周倉 周瑜 諸葛謹 諸葛亮 審配 司馬懿 司馬師 司馬昭 周泰 荀彧 荀攸 徐晃 徐庶 曹叡 曹昂 曹彰 曹植 曹操 "
    "曹丕 沮授 孫堅 孫乾 孫権 孫策 太史慈 趙雲 張紘 張郃 張昭 張飛 張遼 陳宮 陳羣 程昱 程普 田豊 鄧芝 董卓 馬超 馬騰 馬良 鄧艾 "
    "文醜 龐統 龐徳 孟獲 劉表 劉備 呂布 陸遜 李儒 徐盛 馬岱 王允 辛評 劉封 王平 献帝" + " -" * 64 + " 貂蝉 "
    "朱貴 袁朗 王煥 王慶 王倫 丘岳 喬冽 許貫忠 寇烕 扈成 蔡京 崔道成 宿元景 祝龍 蕭嘉穂 蒋忠 任原 西門慶 石宝 曾塗 段三娘 張叔夜 "
    "張文遠 田虎 鄧元覚 童貫 裴如海 白秀英 潘金蓮 潘功雲 馬霊 費保 聞煥章 卞祥 方杰 包道乙 龐万春 方臘 楊戩 欒廷玉 李鬼 李瑞蘭 "
    "葉清 祝彪 褚享 方瓊 呂師嚢 孫安 張開 山士奇 銭振鵬 徽宗皇帝 金国太宗").split()
SAN4PK_EXTRA_GROUPS = ["挑臉追加（三國志III）"] * 150 + ["挑臉追加（水滸傳）"] * 53
# DOS PK (Chinese): the same faces, named as in 三國志III DOS / 水滸傳 DOS (matched by face number)
SAN4PK_DOS_EXTRA_NAMES = (
    "伊籍 袁紹 袁譚 諸葛誕 華歆 賈詡 郭嘉 郝昭 郭圖 夏侯淵 夏侯惇 夏侯霸 華佗 華雄 關羽 甘寧 關平 顏良 姜維 許褚 魏延 鍾會 虞翻 "
    "嚴顏 黃蓋 公孫瓚 黃忠 周倉 周瑜 諸葛瑾 諸葛亮 審配 司馬懿 司馬師 司馬昭 周泰 荀彧 荀攸 徐晃 徐庶 曹叡 曹昂 曹彰 曹植 曹操 "
    "曹丕 沮授 孫堅 孫乾 孫權 孫策 太史慈 趙雲 張紘 張郃 張昭 張飛 張遼 陳宮 陳群 程昱 程普 田豐 鄧芝 董卓 馬超 馬騰 馬良 鄧艾 "
    "文醜 龐統 龐德 孟獲 劉表 劉備 呂布 陸遜 李儒 徐盛 馬岱 王允 辛評 劉封 王平 獻帝" + " -" * 64 + " 貂蟬 "
    "朱貴 袁朗 王煥 王慶 王倫 丘岳 喬冽 許貫忠 寇威 扈成 蔡京 崔道成 宿元景 祝龍 蕭嘉穗 蔣忠 任原 西門慶 石寶 曾塗 段三娘 張叔夜 "
    "張文遠 田虎 鄧元覺 童貫 裴如海 白秀英 潘金蓮 潘巧雲 馬靈 費保 聞煥章 卞祥 方杰 包道乙 龐萬春 方腊 楊戩 欒廷玉 李鬼 李瑞蘭 "
    "葉清 祝彪 諸享 方瓊 呂師囊 孫安 張開 山士奇 錢振鵬 徽宗皇帝 金國太宗").split()
# DOS PK: scenario 10 misspells three names that scenarios 1-9 have right
SAN4PK_DOS_NAME_FIX = {"惇于瓊": "淳于瓊", "鐘會": "鍾會", "鐘繇": "鍾繇"}
# DOS PK fixed 劉瞱, 蘆植, 沙摩可, 吳鋼; 孔秀 and 龐義 remain
SAN4PK_DOS_NAME_HISTORICAL = {0x38: "孔伷", 0xE85A: "龐羲"}
# NBDATA.SUI: DOS writes 彭汜 for 彭玘 (玘 is a PC-98 PK gaiji)
SAN4PK_DOS_SUIKODEN_HISTORICAL = {"彭汜": "彭玘"}
SAN4_PC98_PORTRAIT_NAMES = {250: "華佗", 251: "馬鈞", 252: "司馬徽", 253: "許子将", 254: "干吉", 255: "左慈",
                            256: "管輅", 257: "普浄", 333: "密偵", 334: "兵士", 335: "童子", 338: "貂蝉", 339: "献帝"}


def build_san4(game_dir: str, pc98: bool = False, pk: bool = False) -> tuple[dict, list[bytes]]:
    inputs = SAN4PK_INPUTS if pk else SAN4_INPUTS
    files = {}
    for name in inputs:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    # PK: the picker faces borrowed from 三國志III / 水滸伝 go in their own blob
    store = ImageStore(["pixels.bin", "portraits.bin"] + (["extra.bin"] if pk else []))

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
    for i, name in (SAN4_PC98_PORTRAIT_NAMES if pc98 else SAN4_PORTRAIT_NAMES).items():
        portraits[i]["name"] = name
    if pk:
        shown = [bytes(genpei.decode_planar(files["KAODATAP.S4"], i * 1920, 64, 80, 3)) for i in range(SAN4PK_SHOWN)]
        portraits += [{"img": store.add(64, 80, px, blob=1), "code": f"{i:04X}", "group": "水滸傳檔案"}
                      for i, px in enumerate(shown) if i >= len(faces)]
        picker = [bytes(genpei.decode_planar(files["KAODATA2.S4"], i * 1920, 64, 80, 3))
                  for i in range(len(files["KAODATA2.S4"]) // 1920)]
        extra = [px for px in picker if px not in shown[len(faces):]]
        extra = list(zip(extra, SAN4PK_EXTRA_NAMES if pc98 else SAN4PK_DOS_EXTRA_NAMES, SAN4PK_EXTRA_GROUPS,
                         strict=True))
        # 水滸伝 extras first, next to the 水滸伝 officers 340-456
        for px, name, group in extra[150:] + extra[:150]:
            portraits.append({"img": store.add(64, 80, px, blob=2), "group": group, **({} if name == "-" else {"name": name})})
        # everything after the base game's KAODATA.S4 faces is added by the PK
        for p in portraits[len(faces):]:
            p["pk"] = True

    characters = []
    # scenarios 1-6 in order; 羌族、烏丸族、山越族、南蠻族 share one face code, so key on the name too
    seen = set()
    for _, name, code in sango.load_san4_persons(os.path.join(game_dir, "SNDATA.S4"),
                                                  os.path.join(game_dir, "TAIKI.S4"), pc98):
        if pk and not pc98:
            name = SAN4PK_DOS_NAME_FIX.get(name, name)
        if (code, name) in seen:
            continue
        seen.add((code, name))
        ch = {"id": len(characters), "name": name}
        historical = (SAN4_PC98_NAME_HISTORICAL if pc98 else
                      SAN4PK_DOS_NAME_HISTORICAL if pk else SAN4_NAME_HISTORICAL)
        if code in historical:
            ch["nameHistorical"] = historical[code]
        if code & 0x8000:
            ch["face"] = {"variant": code & 15, "parts": sango.san4_montage_parts(code), "code": f"{code:04X}"}
        else:
            ch["face"] = {"portrait": code}
        characters.append(ch)
    if pk:
        # the 水滸伝 officers registered from NBDATA.SUI follow the scenario persons
        characters += [{"id": len(characters) + i, "name": name, "face": {"portrait": code}, "pk": True,
                        **({"nameHistorical": SAN4PK_DOS_SUIKODEN_HISTORICAL[name]}
                           if not pc98 and name in SAN4PK_DOS_SUIKODEN_HISTORICAL else {})}
                       for i, (name, code) in
                       enumerate(sango.load_san4pk_suikoden(os.path.join(game_dir, "NBDATA.SUI"), pc98))]

    meta = {
        "format": FORMAT, "id": ("san4pk-" if pk else "san4-") + ("pc98" if pc98 else "dos"),
        "game": "SAN4PK" if pk else "SAN4", "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "三國志IV with パワーアップキット", "zh": "三國志IV 威力加強版"} if pk else
                 {"ja": "三國志IV", "zh": "三國志IV"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in inputs]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": SAN4_PC98_PALETTE} if pc98 else
                     {"id": "vga", "label": "VGA", "colors": SAN4_PALETTE}],
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


SAN5PK_INPUTS = ["KAODATA.S5", "KAOEX.S5", "SNDATA.S5", "TAIKI.S5"]
# DGROUP 0x5C94 of MAIN.EXE (B, R, G, 4 bits each), colours 8-15 are the faces; widened as (v << 4) | (v >> 2)
SAN5PK_PALETTE = ["#202010", "#104171", "#B23000", "#B27141", "#206110", "#618292", "#E3A282", "#E3D3C3"]
# speakers without a person record; names from the MAIN.EXE list at DGROUP 0x8E7A (see notes/san5.md)
SAN5PK_PORTRAIT_NAMES = {500: "獻帝", 501: "貂蟬", 502: "民眾", 503: "民眾", 504: "民眾", 505: "民眾", 506: "使者",
                         507: "士兵"}
# faces offered when registering a new officer (overlay 16 picker), by sex; 733-782 follow each range
SAN5PK_PORTRAIT_GROUPS = {
    **{i: "事件人物" for i in SAN5PK_PORTRAIT_NAMES},
    **{i: "新武將（男）" for i in [*range(508, 625), *range(733, 758)]},
    **{i: "新武將（女）" for i in [*range(625, 733), *range(758, 783)]},
}
# KAOEX.S5: extra faces offered by the PK face picker as codes 783-1164 (0-159 are 三國志IV faces)
SAN5PK_EXTRA_GROUP = "追加頭像"
# PC-98: the same palette bytes as DOS (DGROUP 0x910), widened as v * 17; names as the game spells them
SAN5PK_PC98_PALETTE = ["#222211", "#114477", "#BB3300", "#BB7744", "#226611", "#668899", "#EEAA88", "#EEDDCC"]
SAN5PK_PC98_PORTRAIT_NAMES = {500: "献帝", 501: "貂蝉", 502: "民衆", 503: "民衆", 504: "民衆", 505: "民衆",
                              506: "使者", 507: "兵士"}
# 盧植 is 蘆植 in scenarios 1-2 and 盧植 in 8, 9, 12
SAN5PK_PC98_NAME_PICK = {199: "盧植"}
# historical spelling by face code
SAN5PK_NAME_HISTORICAL = {56: "孔伷", 467: "龐羲"}
SAN5PK_PC98_NAME_HISTORICAL = {467: "龐羲"}
# base game (PC-98): no KAOEX.S5; 7 scenarios whose SNDATA person table ends 64 bytes before the end
SAN5_PC98_INPUTS = ["KAODATA.S5", "SNDATA.S5", "TAIKI.S5"]
SAN5_PC98_SNDATA_TAIL = 64
SAN5_FACES = 733  # faces in the base game's KAODATA.S5; the PK appends 733-782 and KAOEX.S5


def build_san5pk(game_dir: str, pc98: bool = False, pk: bool = True) -> tuple[dict, list[bytes]]:
    """pk=False: the base game (PC-98 only), without KAOEX.S5 and the PK faces 733-782."""
    inputs = SAN5PK_INPUTS if pk else SAN5_PC98_INPUTS
    files = {}
    for name in inputs:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    # KAOEX.S5 (borrowed faces) goes in its own blob
    store = ImageStore(["portraits.bin", "extra.bin"] if pk else ["portraits.bin"])

    kao = files["KAODATA.S5"] + files.get("KAOEX.S5", b"")
    portraits = [{"img": store.add(*san3_pixels(kao[i:i + sango.SAN5_FACE], True),
                                   blob=int(i >= len(files["KAODATA.S5"]))),
                  "code": f"{i // sango.SAN5_FACE:04X}"} for i in range(0, len(kao), sango.SAN5_FACE)]
    for i, group in SAN5PK_PORTRAIT_GROUPS.items():
        if i < len(portraits):
            portraits[i]["group"] = group
    for p in portraits[len(files["KAODATA.S5"]) // sango.SAN5_FACE:]:
        p["group"] = SAN5PK_EXTRA_GROUP
    for i, name in (SAN5PK_PC98_PORTRAIT_NAMES if pc98 else SAN5PK_PORTRAIT_NAMES).items():
        portraits[i]["name"] = name
    if pk:
        for p in portraits[SAN5_FACES:]:
            p["pk"] = True

    characters = []
    # scenarios 1-12 in order, deduplicated by face code (one name per code)
    seen = set()
    pick = SAN5PK_PC98_NAME_PICK if pc98 else {}
    for _, name, code in sango.load_san5_persons(os.path.join(game_dir, "SNDATA.S5"),
                                                  os.path.join(game_dir, "TAIKI.S5"), pc98,
                                                  tail=1100 if pk else SAN5_PC98_SNDATA_TAIL):
        if code in seen:
            continue
        seen.add(code)
        ch = {"id": len(characters), "name": pick.get(code, name)}
        historical = SAN5PK_PC98_NAME_HISTORICAL if pc98 else SAN5PK_NAME_HISTORICAL
        if code in historical:
            ch["nameHistorical"] = historical[code]
        ch["face"] = {"portrait": code}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": ("san5pk" if pk else "san5") + ("-pc98" if pc98 else "-dos"),
        "game": "SAN5PK" if pk else "SAN5", "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "三國志V with パワーアップキット", "zh": "三國志V 威力加強版"} if pk
        else {"ja": "三國志V", "zh": "三國志V"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in inputs]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": SAN5PK_PC98_PALETTE} if pc98 else
                     {"id": "vga", "label": "VGA", "colors": SAN5PK_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- SAN1 (PC-98, DOS)

SAN1_PC98_INPUTS = ["PICDATA.DAT", "SAVEDATA"]
SAN1_DOS_INPUTS = ["PICDATA.DAT", "SINADATA.DAT"]
# misspelt names (checked against san1-fc), by character id
SAN1_PC98_NAME_HISTORICAL = {18: "于禁", 22: "荀攸", 62: "許攸", 89: "蔡中", 119: "雷銅", 127: "李堪", 155: "諸葛瑾",
                             205: "邢道栄", 206: "鮑隆", 229: "沙摩柯", 239: "向寵"}
# DOS (English): Chinese names by character id (the PC-98 names with SAN1_PC98_NAME_HISTORICAL, in traditional glyphs)
SAN1_DOS_NAME_ZH = """
曹操 孫堅 劉備 袁紹 袁術 劉表 董卓 劉焉 馬騰 公孫瓚 夏侯惇 夏侯淵 曹仁 曹洪 曹昂
荀彧 程昱 于禁 典韋 陳宮 劉曄 荀攸 樂進 李典 曹丕 曹植 曹叡 曹休 曹真 曹純
黃蓋 孫策 周瑜 孫權 韓當 程普 朱治 蔣欽 周泰 孫翊 孫瑜 孫桓 關羽 張飛 曹豹
劉禪 孫乾 關平 關興 劉永 劉理 張苞 劉封 關索 陳琳 顏良 文醜 田豐 審配 沮授
郭圖 許攸 高覽 張郃 袁譚 袁熙 袁尚 袁胤 呂範 張勳 紀靈 雷薄 陳紀 梁紀 李豐
梁剛 陳蘭 黃祖 韓遂 蒯越 蔡瑁 呂公 劉琦 劉琮 甘寧 王粲 張允 蔡和 蔡中 李儒
呂布 李肅 李傕 蔡邕 郭汜 張濟 賈詡 華雄 樊稠 徐榮 胡軫 趙岑 董旻 張松 法正
孟達 黃權 王累 鄧賢 張任 劉璋 楊懷 高沛 劉巴 劉璝 劉循 吳懿 吳蘭 雷銅 嚴顏
馬超 馬休 馬鐵 馬岱 侯選 程銀 李堪 張橫 梁興 成宜 馬玩 楊秋 龐德 許褚 劉繇
陶謙 陳登 陳珪 糜竺 徐晃 孔融 劉岱 張邈 鮑信 趙雲 韓暹 楊奉 太史慈 張昭 張紘
陳武 虞翻 王朗 魯肅 諸葛瑾 呂蒙 陸遜 陳群 朱儁 楊彪 宋憲 魏續 侯成 張遼 張繡
周倉 廖化 顧雍 呂曠 呂翔 郭嘉 伊籍 徐庶 諸葛亮 司馬懿 糜芳 魏延 簡雍 蔣幹 步騭
薛綜 陸績 嚴畯 闞澤 傅幹 丁奉 潘璋 毛玠 龐統 呂虔 徐盛 凌統 馬延 張顗 陳矯
牛金 陳嬉 馬良 馬謖 金旋 韓玄 趙範 劉度 劉延 邢道榮 鮑隆 陳應 鞏志 黃忠 宋謙
朱靈 文聘 華歆 張既 張魯 閻圃 張衛 鍾繇 鍾進 楊修 楊松 夏侯德 夏侯尚 滿寵 傅士仁
賈逵 許靖 吳班 沙摩柯 孟獲 雍闓 高定 朱褒 呂凱 孟優 郭攸之 費禕 董允 向寵 譙周
鄧芝 夏侯楙 姜維 郭淮 辛毗 司馬昭 司馬師 蔣琬 郝昭 朱桓 全琮 王雙 王平 李嚴 楊儀
""".split()
SAN1_PC98_SLOTS = [("top", "上"), ("middle", "中"), ("bottom", "下")]
# PICDATA faces 0-64 are the characters; 65 repeats 64, 66-83 are daughters (marriage diplomacy)
SAN1_PC98_PORTRAITS = 84
SAN1_PC98_PORTRAIT_GROUPS = {65: "未使用", **{i: "姫" for i in range(66, 84)}}
# DOS: daughters are 0x42 + (faction mod 16); 82 and 83 repeat 81
SAN1_DOS_PORTRAIT_GROUPS = {65: "未使用", **{i: "女兒" for i in range(66, 82)}, 82: "未使用", 83: "未使用"}
# EGA: the faces' two planes are colour bits 1 and 2, palette registers 2, 4, 6 = 0x12, 0x14, 0x16 (MAIN.EXE DGROUP 0x1BC)
SAN1_DOS_PALETTE = ["#000000", "#55ff55", "#ff5555", "#ffff55"]


def san1_rows(pic: bytes, face: int, rows: tuple[int, int], dos: bool) -> tuple[int, int, bytes]:
    """Half-height rows [a, b) of a PICDATA face, line-doubled."""
    a, b = rows
    size, row = (san1.DOS_FACE, 12) if dos else (san1.PC98_FACE, 18)
    raw = pic[face * size + a * row:face * size + b * row]
    px = bytes((utils.to_2bpp_indexes if dos else utils.to_3bpp_indexes)(raw))
    return 48, 2 * (b - a), b"".join(px[i:i + 48] * 2 for i in range(0, len(px), 48))


def build_san1(game_dir: str, dos: bool = False) -> tuple[dict, list[bytes]]:
    inputs = SAN1_DOS_INPUTS if dos else SAN1_PC98_INPUTS
    files = {}
    for name in inputs:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    pic = files["PICDATA.DAT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for group in range(6, 11):
        first = san1.pc98_composite_group(group << 12)
        parts = {}
        for (slot, _), rows in zip(SAN1_PC98_SLOTS, san1.PC98_BANDS):
            parts[slot] = {"at": [0, 2 * rows[0]], "items": [store.add(*san1_rows(pic, first + i, rows, dos))
                                                             for i in range(5)]}
        variants.append({"id": str(group), "label": f"類型 {group - 6}", "parts": parts})

    portraits = [{"img": store.add(*san1_rows(pic, i, (0, san1.PC98_FACE_ROWS), dos), blob=1), "code": f"{i:04X}"}
                 for i in range(SAN1_PC98_PORTRAITS)]
    for i, group in (SAN1_DOS_PORTRAIT_GROUPS if dos else SAN1_PC98_PORTRAIT_GROUPS).items():
        portraits[i]["group"] = group

    characters = []
    persons = (san1.load_san1_dos_persons(os.path.join(game_dir, "SINADATA.DAT")) if dos else
               san1.load_san1_pc98_persons(os.path.join(game_dir, "SAVEDATA")))
    # 1-based like san1-fc (same order)
    for cid, (code, name) in enumerate(persons, 1):
        ch = {"id": cid, "name": name}
        if dos:
            ch["nameZh"] = SAN1_DOS_NAME_ZH[cid - 1]
        elif cid in SAN1_PC98_NAME_HISTORICAL:
            ch["nameHistorical"] = SAN1_PC98_NAME_HISTORICAL[cid]
        if san1.is_pc98_composite(code):
            ch["face"] = {"variant": (code >> 12) - 6, "parts": san1.pc98_composite_parts(code), "code": f"{code:04X}"}
        else:
            ch["face"] = {"portrait": code}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "san1-dos" if dos else "san1-pc98", "game": "SAN1", "platform": "DOS" if dos else "PC98",
        "title": {"ja": "三國志", "zh": "三國志"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in inputs]},
        "display": {"scale": 6},
        "palettes": [{"id": "ega", "label": "EGA", "colors": SAN1_DOS_PALETTE} if dos else
                     {"id": "pc98", "label": "PC98", "colors": SAN2_JP_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [48, 80],
            "slots": [{"id": i, "label": label} for i, label in SAN1_PC98_SLOTS],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- SAN1 (PC-88 V1)

SAN1_PC88_INPUTS = ["DISK_A.D88", "DISK_B.D88"]
# portrait codes used by SN1.EXT; disk B track 8 slot 4 repeats 43 (劉表) and is left out
SAN1_PC88_CODES = [*range(30), 43]
# group 8 has only parts 0-2 (track 8 slots 3-4 are portraits)
SAN1_PC88_GROUP_PARTS = {8: 3}


def build_san1_pc88(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SAN1_PC88_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    disk_b = pc88.d88_image(files["DISK_B.D88"])
    sn1 = pc88.cpm_files(pc88.d88_image(files["DISK_A.D88"]))["SN1.EXT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for group in range(6, 11):
        faces = [san1.pc88_face(disk_b, group, i) for i in range(SAN1_PC88_GROUP_PARTS.get(group, 5))]
        parts = {}
        for (slot, _), rows in zip(SAN1_PC98_SLOTS, san1.PC98_BANDS):
            parts[slot] = {"at": [0, 2 * rows[0]], "items": [store.add(*san1_rows(face, 0, rows, False)) for face in faces]}
        variants.append({"id": str(group), "label": f"類型 {group - 6}", "parts": parts})

    full = (0, san1.PC98_FACE_ROWS)
    portraits = [{"img": store.add(*san1_rows(san1.pc88_face_by_code(disk_b, c), 0, full, False), blob=1),
                  "code": f"{c:04X}"} for c in SAN1_PC88_CODES]
    for i in range(san1.PC88_DAUGHTERS):
        face = san1.pc88_face(disk_b, san1.PC88_DAUGHTER_TRACK + i // 5, i % 5)
        portraits.append({"img": store.add(*san1_rows(face, 0, full, False), blob=1), "group": "姫"})
    portrait_of = {c: i for i, c in enumerate(SAN1_PC88_CODES)}

    characters = []
    for cid, (code, name) in enumerate(san1.load_san1_pc88_persons(sn1), 1):
        ch = {"id": cid, "name": name}
        if cid in SAN1_PC98_NAME_HISTORICAL:
            ch["nameHistorical"] = SAN1_PC98_NAME_HISTORICAL[cid]
        if san1.is_pc98_composite(code):
            ch["face"] = {"variant": (code >> 12) - 6, "parts": san1.pc98_composite_parts(code), "code": f"{code:04X}"}
        else:
            ch["face"] = {"portrait": portrait_of[code]}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "san1-pc88", "game": "SAN1", "platform": "PC88",
        "title": {"ja": "三國志", "zh": "三國志"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SAN1_PC88_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc88", "label": "PC88", "colors": SAN2_JP_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [48, 80],
            "slots": [{"id": i, "label": label} for i, label in SAN1_PC98_SLOTS],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- SUIKODEN (PC-98)

SUIKODEN_PC98_INPUTS = ["KAO98.DAT", "SUIDATA1.CIM"]
SUIKODEN_PC88_INPUTS = ["KAODATA.DAT", "SUIDATA1.CIM"]
SUIKODEN_PC98_FACE = 1920  # 64x80 full height, 3bpp
# faces 255-259 have no person; identified against suikoden-fc
SUIKODEN_PC98_PORTRAIT_GROUPS = {255: "施設", 256: "施設", 257: "施設", 258: "特殊人物", 259: "特殊人物"}
SUIKODEN_PC98_PORTRAIT_NAMES = {255: "造船所", 256: "雑貨屋", 257: "武器屋", 258: "徽宗皇帝", 259: "金国太宗"}
# misspelt names (the Chinese DOS release has them right), by character id
SUIKODEN_PC98_NAME_HISTORICAL = {35: "盧俊義", 128: "馬麟", 210: "成貴", 254: "潘巧雲"}


def build_suikoden_pc98(game_dir: str, pc88: bool = False) -> tuple[dict, list[bytes]]:
    """pc88=True: the PC-88 version (KAODATA.DAT: 258 64x40 faces, B, R, G per 8 pixels; 19-byte person records)."""
    inputs = SUIKODEN_PC88_INPUTS if pc88 else SUIKODEN_PC98_INPUTS
    files = {}
    for name in inputs:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    if pc88:
        kao = files["KAODATA.DAT"]
        portraits = [{"img": store.add(64, 80, brg_pixels(kao[i:i + 960], 8)), "code": f"{i // 960:04X}"}
                     for i in range(0, len(kao), 960)]
    else:
        kao = files["KAO98.DAT"]
        portraits = [{"img": store.add(*san2_jp_pixels(kao[i:i + SUIKODEN_PC98_FACE], True)),
                      "code": f"{i // SUIKODEN_PC98_FACE:04X}"} for i in range(0, len(kao), SUIKODEN_PC98_FACE)]
    # PC-88 has no 258, 259
    for i, group in SUIKODEN_PC98_PORTRAIT_GROUPS.items():
        if i < len(portraits):
            portraits[i]["group"] = group
    for i, name in SUIKODEN_PC98_PORTRAIT_NAMES.items():
        if i < len(portraits):
            portraits[i]["name"] = name

    # the four scenarios have the same names and faces
    characters = [{"id": cid, "name": name, "face": {"portrait": code}} for cid, (code, name) in
                  enumerate(koei_games.load_suikoden_pc98_persons(os.path.join(game_dir, "SUIDATA1.CIM"), pc88))]
    for ch in characters:
        if ch["id"] in SUIKODEN_PC98_NAME_HISTORICAL:
            ch["nameHistorical"] = SUIKODEN_PC98_NAME_HISTORICAL[ch["id"]]

    meta = {
        "format": FORMAT, "id": "suikoden-pc88" if pc88 else "suikoden-pc98", "game": "SUIKODEN",
        "platform": "PC88" if pc88 else "PC98",
        "title": {"ja": "水滸伝・天命の誓い", "zh": "水滸傳・天命之誓"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in inputs]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc88", "label": "PC88", "colors": NOBU2_PC88_PALETTE} if pc88 else
                     {"id": "pc98", "label": "PC98", "colors": SAN2_JP_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
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


# ---------------------------------------------------------------- SUIKODEN (DOS, Chinese)

SUIKODEN_DOS_INPUTS = ["KAOIBM.DAT", "SUIDATA1.CIM"]
# faces 255-259 have no person; MAIN.EXE draws them with constant face numbers (see notes/koei-games.md)
SUIKODEN_DOS_PORTRAIT_GROUPS = {255: "設施", 256: "設施", 257: "設施", 258: "特殊人物", 259: "特殊人物"}
SUIKODEN_DOS_PORTRAIT_NAMES = {255: "造船所", 256: "雜貨店", 257: "兵工廠", 258: "徽宗皇帝", 259: "金國太宗"}
# misspelt names, against the novel, by character id
SUIKODEN_DOS_NAME_HISTORICAL = {115: "黃文燁", 127: "彭玘", 133: "縻貹", 154: "党世英", 180: "湯隆", 185: "党世雄",
                                217: "時遷", 227: "梁世傑"}


def build_suikoden_dos(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SUIKODEN_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    kao = files["KAOIBM.DAT"]
    portraits = [{"img": store.add(*san2_pixels(kao[i:i + SAN2_FACE], True)), "code": f"{i // SAN2_FACE:04X}"}
                 for i in range(0, len(kao), SAN2_FACE)]
    for i, group in SUIKODEN_DOS_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in SUIKODEN_DOS_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    characters = []
    # the four scenarios have the same names and faces
    for cid, (code, name) in enumerate(koei_games.load_suikoden_dos_persons(os.path.join(game_dir, "SUIDATA1.CIM"))):
        ch = {"id": cid, "name": name}
        if cid in SUIKODEN_DOS_NAME_HISTORICAL:
            ch["nameHistorical"] = SUIKODEN_DOS_NAME_HISTORICAL[cid]
        ch["face"] = {"portrait": code}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "suikoden-dos", "game": "SUIKODEN", "platform": "DOS",
        "title": {"ja": "水滸伝・天命の誓い", "zh": "水滸傳・天命之誓"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SUIKODEN_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "ega", "label": "EGA", "colors": SAN2_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- KOURYUUKI (DOS, Chinese)

KOURYUUKI_DOS_INPUTS = ["KAO.KR1", "MAIN.EXE"]
KOURYUUKI_DOS_FACE = 1920  # 64x80 full height, byte k = bit k
# MAIN.EXE DGROUP 0x5E5A (set at start-up through GRPDRV fn 15h): 4-bit B, R, G, written to the DAC as v << 2
KOURYUUKI_DOS_PALETTE = ["#000000", "#0030a2", "#c34100", "#b27171", "#418200", "#82a2b2", "#e3a251", "#f3e3d3"]
# faces 92-96 have no person; names from MAIN.EXE DGROUP 0x7D6E
KOURYUUKI_DOS_PORTRAIT_GROUPS = {92: "長老", 93: "長老", 94: "士兵", 95: "士兵", 96: "事件人物"}
KOURYUUKI_DOS_PORTRAIT_NAMES = {96: "虞姬"}
KOURYUUKI_DOS_NAME_HISTORICAL = {79: "臧荼", 80: "司馬卬", 82: "靳彊"}


def build_kouryuuki_dos(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in KOURYUUKI_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    kao = files["KAO.KR1"]
    portraits = [{"img": store.add(64, 80, bytes(genpei.decode_planar(kao, i, 64, 80, 3))),
                  "code": f"{i // KOURYUUKI_DOS_FACE:04X}"} for i in range(0, len(kao), KOURYUUKI_DOS_FACE)]
    for i, group in KOURYUUKI_DOS_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in KOURYUUKI_DOS_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    characters = []
    # face = person number (MAIN.EXE reads KAO.KR1 at face * 0x780)
    for cid, name in enumerate(koei_games.load_kohryuki_dos_names(os.path.join(game_dir, "MAIN.EXE"))):
        ch = {"id": cid, "name": name}
        if cid in KOURYUUKI_DOS_NAME_HISTORICAL:
            ch["nameHistorical"] = KOURYUUKI_DOS_NAME_HISTORICAL[cid]
        ch["face"] = {"portrait": cid}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "kouryuuki-dos", "game": "KOURYUUKI", "platform": "DOS",
        "title": {"ja": "項劉記", "zh": "項劉記"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in KOURYUUKI_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "vga", "label": "VGA", "colors": KOURYUUKI_DOS_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- EUROPE (DOS, Chinese)

EUROPE_DOS_INPUTS = ["FACE.DAT", "SCEDATA", "MAIN.EXE"]
EUROPE_DOS_FACE = 1920  # 64x80 full height, byte k = bit k
# MAIN.EXE DGROUP 0x56B6: colours 0-7, 4-bit B, R, G, written to the DAC as v << 2
EUROPE_DOS_PALETTE = ["#000000", "#104192", "#d33030", "#d371b2", "#419241", "#71b2b2", "#f3c361", "#f3f3f3"]
# faces 106-117 are the generic replacement commanders (MAIN.EXE DGROUP 0x57BA), 118-119 event characters
EUROPE_DOS_PORTRAIT_GROUPS = {**{i: "替補指揮官（軸心國）" for i in range(106, 112)},
                              **{i: "替補指揮官（聯合軍）" for i in range(112, 118)}, 118: "事件人物", 119: "事件人物"}
EUROPE_DOS_PORTRAIT_NAMES = {118: "村姑", 119: "修女"}


def build_europe_dos(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in EUROPE_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    face = files["FACE.DAT"]
    portraits = [{"img": store.add(64, 80, bytes(genpei.decode_planar(face, i, 64, 80, 3))),
                  "code": f"{i // EUROPE_DOS_FACE:04X}"} for i in range(0, len(face), EUROPE_DOS_FACE)]
    for i, group in EUROPE_DOS_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in EUROPE_DOS_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    # face = person number: commanders 0-93 from the scenarios, leaders 94-105 from MAIN.EXE
    names = koei_games.load_europe_dos_names(os.path.join(game_dir, "SCEDATA"), os.path.join(game_dir, "MAIN.EXE"))
    characters = [{"id": cid, "name": names[cid], "face": {"portrait": cid}} for cid in sorted(names)]

    meta = {
        "format": FORMAT, "id": "europe-dos", "game": "EUROPE", "platform": "DOS",
        "title": {"ja": "ヨーロッパ戦線", "zh": "歐陸戰線"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in EUROPE_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "vga", "label": "VGA", "colors": EUROPE_DOS_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- LIBERTY (DOS, Chinese)

LIBERTY_DOS_INPUTS = ["FACE.IDX", "MAIN.EXE"]
# MAIN.EXE DGROUP 0x1E12: colours 0-7 (same in all four palettes), 4-bit B, R, G, written to the DAC as v << 2
LIBERTY_DOS_PALETTE = ["#000000", "#104192", "#b25110", "#a27171", "#417100", "#82a2b2", "#e3b292", "#f3e3d3"]
# faces 250-293 = 250 + side * 22 + slot (MAIN.EXE 0x9101): slots 0-19 state delegates / governors and
# ministers (named after the initial office holders), 20-21 supply officers
LIBERTY_DOS_SIDES = ["大陸會議", "英國"]
LIBERTY_DOS_SUPPLY = {20: "彈藥補給官", 21: "糧食補給官"}
LIBERTY_DOS_PORTRAITS = {294: ("傳令", "大陸會議傳令"), 295: ("傳令", "英國傳令"), 296: ("海軍", "同盟國海軍軍官"),
                         297: ("海軍", "同盟國海軍軍官"), 298: ("傭兵", "雇傭兵隊長")}
# the Chinese name is another person's, by character id
LIBERTY_DOS_NAME_HISTORICAL = {82: "托馬斯・蓋奇", 191: "伊斯雷爾・帕特南"}
# PC-98: the same FACE.IDX; the same 4-bit table (MAIN.EXE file 0x3945A) on the analog palette, as v * 17
LIBERTY_PC98_PALETTE = ["#000000", "#114499", "#bb5511", "#aa7777", "#447700", "#88aabb", "#eebb99", "#ffeedd"]
LIBERTY_PC98_SIDES = ["大陸会議", "英国"]
LIBERTY_PC98_SUPPLY = {20: "弾薬補給担当", 21: "食糧補給担当"}  # MAIN.EXE office names
LIBERTY_PC98_PORTRAITS = {294: ("伝令", "大陸会議伝令"), 295: ("伝令", "英国伝令"), 296: ("海軍", "同盟国海軍士官"),
                          297: ("海軍", "同盟国海軍士官"), 298: ("傭兵", "傭兵隊長")}


def build_liberty_dos(game_dir: str, pc98: bool = False) -> tuple[dict, list[bytes]]:
    """pc98=True: the Japanese PC-98 original (Shift-JIS names, PC-98 palette)."""
    sides, supply, specials, historical = ((LIBERTY_PC98_SIDES, LIBERTY_PC98_SUPPLY, LIBERTY_PC98_PORTRAITS, {}) if pc98
                                           else (LIBERTY_DOS_SIDES, LIBERTY_DOS_SUPPLY, LIBERTY_DOS_PORTRAITS,
                                                 LIBERTY_DOS_NAME_HISTORICAL))
    files = {}
    for name in LIBERTY_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    portraits = [{"img": store.add(64, 80, px), "code": f"{i:04X}"}
                 for i, px in enumerate(liberty.load_liberty_faces(os.path.join(game_dir, "FACE.IDX")))]
    load = liberty.load_liberty_pc98_names if pc98 else liberty.load_liberty_dos_names
    persons, officials = load(os.path.join(game_dir, "MAIN.EXE"))
    for side, label in enumerate(sides):
        for slot in range(22):
            portraits[250 + side * 22 + slot].update(group=label, name=supply.get(slot) or officials[side * 22 + slot])
    for i, (group, name) in specials.items():
        portraits[i].update(group=group, name=name)

    characters = []
    # face = person number (MAIN.EXE 0x78A9)
    for cid, name in enumerate(persons):
        ch = {"id": cid, "name": name}
        if cid in historical:
            ch["nameHistorical"] = historical[cid]
        ch["face"] = {"portrait": cid}
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "liberty-pc98" if pc98 else "liberty-dos", "game": "LIBERTY",
        "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "独立戦争 Liberty or Death", "zh": "獨立戰爭"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in LIBERTY_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": LIBERTY_PC98_PALETTE} if pc98 else
                     {"id": "vga", "label": "VGA", "colors": LIBERTY_DOS_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- KOUKAI (DOS, Chinese)

KOUKAI_DOS_INPUTS = ["KAO.PUT", "SHINARIO.CIM"]
# KAO.PUT: four composite part sets (one per nation, 0x2E80 bytes each), then 34 portraits from 0xBA00;
# all 64x40 half-height, 3bpp as SAN2 DOS
KOUKAI_DOS_NATION = 0x2E80
KOUKAI_DOS_PORTRAITS = 0xBA00
# (slot, label, offset in the set, record size, count, half-height row); MAIN.EXE 0x9CD6 copies top and
# bottom, then ORs in eyes, nose and mouth (they never overlap set pixels, so 0 = transparent is exact)
KOUKAI_DOS_SLOTS = [("top", "上", 0x0000, 0x1F8, 8, 0), ("bottom", "下", 0x2040, 0x1C8, 8, 21),
                    ("eyes", "眼", 0x0FC0, 0x0C0, 8, 10), ("nose", "鼻", 0x15C0, 0x0C0, 4, 16),
                    ("mouth", "口", 0x18C0, 0x0F0, 8, 22)]
KOUKAI_DOS_NATIONS = ["葡萄牙", "西班牙", "土耳其", "海盜"]
KOUKAI_DOS_WOMEN_PORTRAIT = 13  # woman i -> portrait 13 + i (MAIN.EXE 0x9F7E)
# portraits 1-12 have no character; named by appearance against koukai-fc
KOUKAI_DOS_PORTRAIT_GROUPS = {1: "國王", 2: "國王", 3: "國王", 8: "特殊人物",
                              **{i: "設施" for i in (4, 5, 6, 7, 9, 10, 11, 12)}}
KOUKAI_DOS_PORTRAIT_NAMES = {1: "葡萄牙國王", 2: "西班牙國王", 3: "土耳其國王", 4: "道具店", 5: "造船廠", 6: "交易所",
                             7: "酒館", 8: "老航海士", 9: "港口", 10: "王宮", 11: "教會", 12: "旅館"}
# PC-98: the same layout at double height (MAIN.EXE 0x7292 composes a 1920-byte face; portraits from 0x17400,
# 0x749C), drawn byte 0/1/2 to B/R/G with the standard digital colours; DOS redrew the faces at 64x40
KOUKAI_PC98_NATIONS = ["ポルトガル", "イスパニア", "イスラム", "海賊"]  # MAIN.EXE nation names
KOUKAI_PC98_PORTRAIT_GROUPS = {1: "国王", 2: "国王", 3: "国王", 8: "特殊人物",
                               **{i: "施設" for i in (4, 5, 6, 7, 9, 10, 11, 12)}}
KOUKAI_PC98_PORTRAIT_NAMES = {1: "ポルトガル国王", 2: "イスパニア国王", 3: "イスラム国王", 4: "道具屋", 5: "造船所",
                              6: "交易所", 7: "酒場", 8: "老航海士", 9: "港", 10: "王宮", 11: "教会", 12: "宿屋"}


def koukai_dos_parts(b0: int, b1: int) -> list[int]:
    """Face bytes 0x11, 0x12 of a man -> part per slot (MAIN.EXE 0x9ED9)."""
    return [b1 & 7, b1 >> 3 & 7, b0 & 7, b1 >> 6, b0 >> 4 & 7]


def build_koukai_dos(game_dir: str, pc98: bool = False) -> tuple[dict, list[bytes]]:
    """pc98=True: the PC-98 original (full-height faces, Shift-JIS names)."""
    scale, pixels = (2, san2_jp_pixels) if pc98 else (1, san2_pixels)
    files = {}
    for name in KOUKAI_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    kao = files["KAO.PUT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for nation, label in enumerate(KOUKAI_PC98_NATIONS if pc98 else KOUKAI_DOS_NATIONS):
        base = nation * KOUKAI_DOS_NATION * scale
        parts = {}
        for slot, _, offset, size, count, row in KOUKAI_DOS_SLOTS:
            offset, size = offset * scale, size * scale
            items = [store.add(*pixels(kao[base + offset + i * size:base + offset + (i + 1) * size],
                                       slot in ("top", "bottom"))) for i in range(count)]
            parts[slot] = {"at": [0, 2 * row], "items": items}
        variants.append({"id": str(nation), "label": label, "parts": parts})

    face_size = SAN2_FACE * scale
    portraits = [{"img": store.add(*pixels(kao[i:i + face_size], True), blob=1),
                  "code": f"{(i - KOUKAI_DOS_PORTRAITS * scale) // face_size:04X}"}
                 for i in range(KOUKAI_DOS_PORTRAITS * scale, len(kao), face_size)]
    for i, group in (KOUKAI_PC98_PORTRAIT_GROUPS if pc98 else KOUKAI_DOS_PORTRAIT_GROUPS).items():
        portraits[i]["group"] = group
    for i, name in (KOUKAI_PC98_PORTRAIT_NAMES if pc98 else KOUKAI_DOS_PORTRAIT_NAMES).items():
        portraits[i]["name"] = name

    load = koei_games.load_koukai_pc98_people if pc98 else koei_games.load_koukai_dos_people
    men, women = load(os.path.join(game_dir, "SHINARIO.CIM"))
    characters = []
    # men 0-40, then the women from 41 (as koukai-fc, which has no character for the last woman)
    for cid, (name, b0, b1, nation) in enumerate(men):
        if b0 == 0xFF:
            face = {"portrait": b1}
        else:
            face = {"variant": nation, "parts": koukai_dos_parts(b0, b1), "code": f"{b1 << 8 | b0:04X}"}
        characters.append({"id": cid, "name": name, "face": face})
    characters += [{"id": len(men) + i, "name": name, "face": {"portrait": KOUKAI_DOS_WOMEN_PORTRAIT + i}}
                   for i, name in enumerate(women)]

    meta = {
        "format": FORMAT, "id": "koukai-pc98" if pc98 else "koukai-dos", "game": "KOUKAI",
        "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "大航海時代", "zh": "大航海時代"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in KOUKAI_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": SAN2_JP_PALETTE} if pc98 else
                     {"id": "ega", "label": "EGA", "colors": SAN2_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot[0], "label": slot[1]} for slot in KOUKAI_DOS_SLOTS],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


GENGHIS_DOS_INPUTS = ["KAO.DAT", "MONTER.DAT", "MDATA.CIM", "SDATA.CIM"]
# MONTER.DAT: 4 types x 0x15C0 bytes; per type 4 items of each slot. slot -> (label, offset, first row, rows)
GENGHIS_DOS_SLOTS = {"top": ("上", 0, 0, 19), "bottom": ("下", 0x720, 19, 21), "eyes": ("眼", 0xF00, 12, 7),
                     "nose": ("鼻", 0x11A0, 19, 6), "mouth": ("口", 0x13E0, 25, 5)}
GENGHIS_DOS_TYPE = 0x15C0
GENGHIS_DOS_XOR = ("eyes", "nose", "mouth")  # XORed onto the head (MAIN.EXE 0x5C94)
GENGHIS_DOS_SKIN = 4  # plane-0-only pixels of top/bottom, recoloured by code bits 12-14 (MAIN.EXE 0x955)
GENGHIS_DOS_NAME_HISTORICAL = {
    "菲利浦一世": "菲利浦二世",  # Philip II Augustus (FC フィリップ2せい); wrong regnal number
    "北鞗政子": "北條政子",      # typo
    "偪山重忠": "畠山重忠",      # 畠 missing from the font
    "斡鄰勒": "脫斡鄰勒",        # 少字 (Toghrul)
    "江宗": "襄宗",              # English "Chiang Tsung" = Xi Xia Xiangzong (inferred)
    "摩柯末": "摩訶末",          # 《元史》
}
GENGHIS_PC88_NAME_HISTORICAL = {"江宗": "襄宗"}  # as GENGHIS_DOS_NAME_HISTORICAL; the others are right on PC-88


def build_genghis_dos(game_dir: str, pc88: bool = False) -> tuple[dict, list[bytes]]:
    """Also the PC-88 original (`pc88`): KAO.DAT and MONTER.DAT are the same files, the people tables differ."""
    files = {}
    for name in GENGHIS_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    mon = files["MONTER.DAT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])
    cache = {}

    def part(v, slot, i, colour):
        _, offset, _, rows = GENGHIS_DOS_SLOTS[slot]
        o = v * GENGHIS_DOS_TYPE + offset + i * rows * 24
        px = utils.to_3bpp_indexes(mon[o:o + rows * 24])
        if slot not in GENGHIS_DOS_XOR:
            px = [colour if p == GENGHIS_DOS_SKIN else p for p in px]
        rows = [bytes(px[r * 64:(r + 1) * 64]) for r in range(rows)]
        img = b"".join(r + r for r in rows)  # half-height rows doubled
        if img not in cache:  # most colours don't touch a part, so variants share images
            cache[img] = store.add(64, len(img) // 64, img)
        return cache[img]

    variants = []
    for c in range(8):
        # code bits 12-14 are a colour number with bit k -> plane k; to_3bpp_indexes puts plane 0 in bit 2
        colour = (c & 1) << 2 | (c & 2) | (c >> 2) & 1
        for v in range(4):
            parts = {slot: {"at": [0, 2 * row], "items": [part(v, slot, i, colour) for i in range(4)]}
                     for slot, (_, _, row, _) in GENGHIS_DOS_SLOTS.items()}
            variants.append({"id": f"{v}-{c}", "label": f"類型 {v}／色 {c}", "parts": parts})

    kao = files["KAO.DAT"]
    portraits = [{"img": store.add(*san2_pixels(kao[i:i + SAN2_FACE], True), blob=1),
                  "code": f"{i // SAN2_FACE:04X}"} for i in range(0, len(kao), SAN2_FACE)]

    def face(code):
        if code & 0x8000:
            return {"variant": (code >> 12 & 7) * 4 + (code >> 10 & 3),
                    "parts": [code >> 8 & 3, code >> 6 & 3, code >> 4 & 3, code >> 2 & 3, code & 3],
                    "code": f"{code:04X}"}
        return {"portrait": code}

    load = koei_games.load_genghis_pc88_people if pc88 else koei_games.load_genghis_dos_people
    name_historical = GENGHIS_PC88_NAME_HISTORICAL if pc88 else GENGHIS_DOS_NAME_HISTORICAL
    m = load(os.path.join(game_dir, "MDATA.CIM"))
    s = load(os.path.join(game_dir, "SDATA.CIM"))
    assert m["woman"] == s["woman"]
    # genghis-fc order: Mongol rulers, family, sons; world rulers, family, sons; women;
    # then the generals (not in FC), Mongol then world; a name already listed is skipped
    order = [m["ruler"], m["family"], m["son"], s["ruler"], s["family"], s["son"], m["woman"],
             m["general"], s["general"]]
    characters, seen = [], {}
    for table in order:
        for name, faces in table:
            if name in seen:
                assert seen[name] == faces, name
                continue
            seen[name] = faces
            ch = {"id": len(characters), "name": name}
            if name in name_historical:
                ch["nameHistorical"] = name_historical[name]
            ch["face"] = face(faces[0])
            extra = []
            for f, label in zip(faces[1:], ("笑", "哭")):  # women: normal, smile, cry
                if f != faces[0] and f not in [e["portrait"] for e in extra]:
                    extra.append({"portrait": f, "label": label})
            if extra:
                ch["face"]["label"] = "平常"
                ch["expressions"] = extra
            characters.append(ch)

    meta = {
        "format": FORMAT, "id": "genghis-pc88" if pc88 else "genghis-dos", "game": "GENGHIS",
        "platform": "PC88" if pc88 else "DOS",
        "title": {"ja": "蒼き狼と白き牝鹿・ジンギスカン", "zh": "蒼狼與白鹿・成吉思汗"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in GENGHIS_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc88", "label": "PC88", "colors": SAN2_JP_PALETTE} if pc88 else
                     {"id": "ega", "label": "EGA", "colors": SAN2_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "xor"} if slot in GENGHIS_DOS_XOR else {})}
                      for slot, (label, *_) in GENGHIS_DOS_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "$variant", "hi": 15, "lo": 10, "base": 32},  # 1 ccc vv: variant = c * 4 + v
                {"of": "top", "hi": 9, "lo": 8}, {"of": "bottom", "hi": 7, "lo": 6},
                {"of": "eyes", "hi": 5, "lo": 4}, {"of": "nose", "hi": 3, "lo": 2},
                {"of": "mouth", "hi": 1, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


NOBU3_DOS_INPUTS = ["KAODATA.DAT", "SNDATA1.CIM", "SNDATA2.CIM"]
NOBU3_DOS_PORTRAITS = 177  # then the composite parts at 0x297C0
NOBU3_DOS_PARTS = 0x297C0
# slot -> (label, offset from NOBU3_DOS_PARTS, first half-height row, rows); 4 items each (MAIN.EXE 0x588C)
NOBU3_DOS_SLOTS = {"top": ("上", 0, 0, 18), "bottom": ("下", 0x6C0, 18, 22), "eyes": ("眼", 0xF00, 13, 5),
                   "nose": ("鼻", 0x10E0, 18, 6), "mouth": ("口", 0x1320, 24, 9)}
NOBU3_DOS_XOR = ("eyes", "nose", "mouth")
NOBU3_DOS_NAME_FIX = {"齊籐朝信": "齊藤朝信", "羽祡秀吉": "羽柴秀吉"}  # typos where another scenario has it right
NOBU3_DOS_NAME_HISTORICAL = {
    "田山義綱": "畠山義綱", "田山義慶": "畠山義慶", "北田具教": "北畠具教", "北田具房": "北畠具房",
    "北田政成": "北畠政成", "高田定吉": "高畠定吉",  # 畠 missing from the font
    "神原康政": "榊原康政", "並和康忠": "垪和康忠",  # 榊, 垪 missing from the font
    "今川氏貞": "今川氏真", "北庄秀綱": "本庄秀綱", "溫井景龍": "溫井景隆", "森下通興": "森下通與",
    "溥生氏鄉": "蒲生氏鄉", "著尾高春": "箸尾高春", "肉戶隆家": "宍戶隆家", "九鬼嘉窿": "九鬼嘉隆",
    "小早川窿景": "小早川隆景", "羽祡秀長": "羽柴秀長",
}
NOBU3_DOS_PRINCESSES = range(157, 177)  # marriage: 0x9D + rand(20)


def build_nobu3_dos(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in NOBU3_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    kao = files["KAODATA.DAT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    # KAODATA has four part sets, but MAIN.EXE always reads the first (code bits 0-1 are unused)
    parts = {}
    for slot, (_, offset, row, rows) in NOBU3_DOS_SLOTS.items():
        size = rows * 24
        o = NOBU3_DOS_PARTS + offset
        parts[slot] = {"at": [0, 2 * row],
                       "items": [store.add(*san2_pixels(kao[o + i * size:o + (i + 1) * size], True)) for i in range(4)]}

    portraits = [{"img": store.add(*san2_pixels(kao[i * SAN2_FACE:(i + 1) * SAN2_FACE], True), blob=1),
                  "code": f"{i:04X}"} for i in range(NOBU3_DOS_PORTRAITS)]
    for i in NOBU3_DOS_PRINCESSES:
        portraits[i]["group"] = "公主"

    # scenario 1 then 2 (ids 0-239 as nobu3-fc); one character per name and face code, as nobu3-fc
    characters, seen = [], set()
    for table in koei_games.load_nobu3_dos_people(game_dir):
        for name, code in table:
            name = NOBU3_DOS_NAME_FIX.get(name, name)
            if (name, code) in seen:
                continue
            seen.add((name, code))
            ch = {"id": len(characters), "name": name}
            if name in NOBU3_DOS_NAME_HISTORICAL:
                ch["nameHistorical"] = NOBU3_DOS_NAME_HISTORICAL[name]
            if code & 0x8000:
                ch["face"] = {"variant": 0, "parts": [code >> 2 & 3, code >> 4 & 3, code >> 6 & 3, code >> 8 & 3,
                                                      code >> 10 & 3], "code": f"{code:04X}"}
            else:
                ch["face"] = {"portrait": code}
            characters.append(ch)

    meta = {
        "format": FORMAT, "id": "nobu3-dos", "game": "NOBU3", "platform": "DOS",
        "title": {"ja": "信長の野望・戦国群雄伝", "zh": "信長之野望・戰國群雄傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in NOBU3_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "ega", "label": "EGA", "colors": SAN2_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "xor"} if slot in NOBU3_DOS_XOR else {})}
                      for slot, (label, *_) in NOBU3_DOS_SLOTS.items()],
            "variants": [{"id": "0", "label": "組合臉", "parts": parts}],
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "$variant", "hi": 15, "lo": 15, "base": 1},  # bit 15 marks a composite
                {"of": "mouth", "hi": 11, "lo": 10}, {"of": "nose", "hi": 9, "lo": 8},
                {"of": "eyes", "hi": 7, "lo": 6}, {"of": "bottom", "hi": 5, "lo": 4},
                {"of": "top", "hi": 3, "lo": 2}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


NOBU4_DOS_INPUTS = ["KAODATA.DAT", "MONDATA.DAT", "SNDATA1.CIM", "SNDATA1T.CIM", "SNDATA2.CIM", "SNDATA2T.CIM",
                    "SNDATA3.CIM", "SNDATA3T.CIM"]
NOBU4_DOS_PALETTE = ["#000000", "#00aa00", "#aa0000", "#ffff00", "#0000aa", "#00aaaa", "#aa00aa", "#ffffff"]
NOBU4_DOS_TYPE = 0x5A90  # MONDATA.DAT bytes per head type
# slot -> (label, offset in type, items, first row, rows); eyes, nose and mouth are XORed on (MAIN.EXE 0x6E9C)
NOBU4_DOS_SLOTS = {"top": ("上", 0, 8, 0, 40), "bottom": ("下", 0x1E00, 8, 40, 40), "eyes": ("眼", 0x3C00, 8, 22, 16),
                   "nose": ("鼻", 0x5580, 3, 32, 18), "mouth": ("口", 0x4800, 8, 46, 18)}
NOBU4_DOS_XOR = ("eyes", "nose", "mouth")
NOBU4_DOS_TYPES = ["甲冑", "正面", "側面", "斜側"]
# face code -> name, where scenarios spell one person differently (the others are typos)
NOBU4_DOS_NAME_PICK = {0x9652: "遠藤基信", 0xBC: "服部半藏", 0x57: "真田昌幸", 0x86: "小早川秀包", 0xC045: "大友親盛",
                       0x7E: "柳生宗矩"}
NOBU4_DOS_NAME_HISTORICAL = {
    "田山義綱": "畠山義綱", "田山義慶": "畠山義慶",  # 畠 missing from the font
    "北田具教": "北畠具教", "北田具房": "北畠具房", "北田政成": "北畠政成",
    "神原康政": "榊原康政",  # 榊 missing from the font
    "管沼定村": "菅沼定村", "肉戶隆家": "宍戶隆家", "四天王政孝": "四王天政孝",
}
# portraits no character uses, shown by constant codes (MAIN.EXE call sites of 0x714A)
NOBU4_DOS_PORTRAITS = {139: ("今井宗久", "特殊人物"), 140: ("千利休", "特殊人物"), 273: ("澤彥", "特殊人物"),
                       274: ("朝廷使者", "特殊人物"), 275: ("路易斯・弗羅伊斯", "特殊人物"), 296: ("義姬", "特殊人物"),
                       297: ("田山義繼", "特殊人物")}
NOBU4_DOS_PRINCESSES = range(276, 296)  # 0x114 + rand(20)
# PC-98: the same KAODATA / MONDATA; MAIN.EXE draws byte 0/1/2 to the B/R/G planes (byte k = plane k) and fades
# in DS:0x39DA (B, R, G) with colours 1, 3 and 7 set to blue 0xC (0x4646); the same constant face codes
NOBU4_PC98_PALETTE = ["#000000", "#0000cc", "#ff0000", "#ff00cc", "#00ff00", "#00ffff", "#ffff00", "#ffffcc"]
NOBU4_PC98_PORTRAITS = {139: "今井宗久", 140: "千利休", 273: "沢彦", 274: "朝廷使者", 275: "ルイス＝フロイス",
                        296: "義姫", 297: "畠山義継"}
# aliases sharing a face code; one character under the best-known name, as nobu5-pc98 and nobu6-pc98
NOBU4_PC98_ALIASES = {"松平元康": "徳川家康"}
# the only DOS typo the Japanese original shares
NOBU4_PC98_NAME_HISTORICAL = {"四天王政孝": "四王天政孝"}


def build_nobu4_dos(game_dir: str, pc98: bool = False) -> tuple[dict, list[bytes]]:
    """pc98=True: the PC-98 version (Shift-JIS names, PC-98 palette and plane order)."""
    pixels = (lambda raw: bytes(genpei.decode_planar(raw, 0, 64, len(raw) // 24, 3))) if pc98 else \
        (lambda raw: bytes(utils.to_3bpp_indexes(raw)))
    files = {}
    for name in NOBU4_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    mon = files["MONDATA.DAT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for v, label in enumerate(NOBU4_DOS_TYPES):
        parts = {}
        for slot, (_, offset, count, row, rows) in NOBU4_DOS_SLOTS.items():
            size = rows * 24
            items = [store.add(64, rows, pixels(
                mon[v * NOBU4_DOS_TYPE + offset + i * size:v * NOBU4_DOS_TYPE + offset + (i + 1) * size]))
                for i in range(count)]
            parts[slot] = {"at": [0, row], "items": items}
        variants.append({"id": str(v), "label": label, "parts": parts})

    kao = files["KAODATA.DAT"]
    portraits = [{"img": store.add(64, 80, pixels(kao[i:i + 1920]), blob=1),
                  "code": f"{i // 1920:04X}"} for i in range(0, len(kao), 1920)]
    for i, (name, group) in NOBU4_DOS_PORTRAITS.items():
        if pc98:
            name, group = NOBU4_PC98_PORTRAITS[i], "事件人物"
        portraits[i].update(name=name, group=group)
    for i in NOBU4_DOS_PRINCESSES:
        portraits[i]["group"] = "姫" if pc98 else "公主"

    # scenario 1, its later arrivals, then scenarios 2 and 3 (as nobu4-fc for ids 0-249);
    # one character per face code
    characters, seen = [], set()
    people = koei_games.load_nobu4_pc98_people(game_dir) if pc98 else koei_games.load_nobu4_dos_people(game_dir)
    for table in people:
        for name, code in table:
            if code in seen:
                continue
            seen.add(code)
            name = NOBU4_PC98_ALIASES.get(name, name) if pc98 else NOBU4_DOS_NAME_PICK.get(code, name)
            ch = {"id": len(characters), "name": name}
            historical = NOBU4_PC98_NAME_HISTORICAL if pc98 else NOBU4_DOS_NAME_HISTORICAL
            if name in historical:
                ch["nameHistorical"] = historical[name]
            if code < 0x4000:
                ch["face"] = {"portrait": code}
            else:
                ch["face"] = {"variant": code & 3,
                              "parts": [code >> 2 & 7, code >> 5 & 7, code >> 8 & 7, (code >> 14) - 1, code >> 11 & 7],
                              "code": f"{code:04X}"}
            characters.append(ch)

    meta = {
        "format": FORMAT, "id": "nobu4-pc98" if pc98 else "nobu4-dos", "game": "NOBU4",
        "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "信長の野望・武将風雲録", "zh": "信長之野望・武將風雲錄"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in NOBU4_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": NOBU4_PC98_PALETTE} if pc98 else
                     {"id": "vga", "label": "VGA", "colors": NOBU4_DOS_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "xor"} if slot in NOBU4_DOS_XOR else {})}
                      for slot, (label, *_) in NOBU4_DOS_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "nose", "hi": 15, "lo": 14, "base": 1}, {"of": "mouth", "hi": 13, "lo": 11},
                {"of": "eyes", "hi": 10, "lo": 8}, {"of": "bottom", "hi": 7, "lo": 5},
                {"of": "top", "hi": 4, "lo": 2}, {"of": "$variant", "hi": 1, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


NOBU4_PC88_INPUTS = ["KAODATA.DAT", "SNDATA1.CIM", "SNDATA2.CIM", "GAIJI.CIM"]
NOBU4_PC88_FACES = 285  # 64x40, B, R, G per 8 pixels; composites follow, 4 types x 0x2D48 bytes
NOBU4_PC88_TYPE = 0x2D48
# MAIN.COM 0x2EEB builds the face in a 960-byte buffer: top, bottom copied; eyes, mouth, nose XORed
NOBU4_PC88_SLOTS = {"top": ("上", 0, 8, 0, 20), "bottom": ("下", 0xF00, 8, 20, 20), "eyes": ("眼", 0x1E00, 8, 11, 8),
                    "nose": ("鼻", 0x2AC0, 3, 16, 9), "mouth": ("口", 0x2400, 8, 23, 9)}
NOBU4_PC88_PORTRAITS = {139: "今井宗久", 140: "千利休", 273: "沢彦", 274: "朝廷使者"}
NOBU4_PC88_PRINCESSES = range(275, 285)


def build_nobu4_pc88(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in NOBU4_PC88_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    kao = files["KAODATA.DAT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for v, label in enumerate(NOBU4_DOS_TYPES):
        base = NOBU4_PC88_FACES * 960 + v * NOBU4_PC88_TYPE
        parts = {}
        for slot, (_, offset, count, row, rows) in NOBU4_PC88_SLOTS.items():
            size = rows * 24
            items = [store.add(64, rows * 2, pc88.brg_pixels(kao[base + offset + i * size:base + offset + (i + 1) * size], 8))
                     for i in range(count)]
            parts[slot] = {"at": [0, row * 2], "items": items}
        variants.append({"id": str(v), "label": label, "parts": parts})

    portraits = [{"img": store.add(64, 80, pc88.brg_pixels(kao[i * 960:(i + 1) * 960], 8), blob=1), "code": f"{i:04X}"}
                 for i in range(NOBU4_PC88_FACES)]
    for i, name in NOBU4_PC88_PORTRAITS.items():
        portraits[i].update(name=name, group="事件人物")
    for i in NOBU4_PC88_PRINCESSES:
        portraits[i]["group"] = "姫"

    # scenario 1, then scenario 2 (no later arrivals); ids 0-249 as nobu4-fc
    characters, seen = [], set()
    for table in koei_games.load_nobu4_pc88_people(game_dir):
        for name, code in table:
            if code in seen:
                continue
            seen.add(code)
            ch = {"id": len(characters), "name": NOBU4_PC98_ALIASES.get(name, name)}
            if code < 0x4000:
                ch["face"] = {"portrait": code}
            else:
                ch["face"] = {"variant": code & 3,
                              "parts": [code >> 2 & 7, code >> 5 & 7, code >> 8 & 7, (code >> 14) - 1, code >> 11 & 7],
                              "code": f"{code:04X}"}
            characters.append(ch)
    # the PC-98 scenario 3 and later-arrival people's faces are on the disk but no PC-88 record uses them
    used = {c["face"]["portrait"] for c in characters if "portrait" in c["face"]}
    for i in range(NOBU4_PC88_FACES):
        if i not in used and "group" not in portraits[i]:
            portraits[i]["group"] = "未使用"

    meta = {
        "format": FORMAT, "id": "nobu4-pc88", "game": "NOBU4", "platform": "PC88",
        "title": {"ja": "信長の野望・武将風雲録", "zh": "信長之野望・武將風雲錄"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in NOBU4_PC88_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc88", "label": "PC88", "colors": NOBU2_PC88_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "xor"} if slot in NOBU4_DOS_XOR else {})}
                      for slot, (label, *_) in NOBU4_PC88_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "nose", "hi": 15, "lo": 14, "base": 1}, {"of": "mouth", "hi": 13, "lo": 11},
                {"of": "eyes", "hi": 10, "lo": 8}, {"of": "bottom", "hi": 7, "lo": 5},
                {"of": "top", "hi": 4, "lo": 2}, {"of": "$variant", "hi": 1, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- TAIKOH (太閤立志傳, DOS, Chinese)

TAIKOH_DOS_INPUTS = ["MAIN.EXE", "TBS.DAT", "KAO.PUT", "MONTA.PUT", "HIME.PUT"]
TAIKOH_DOS_PALETTE = 0x8468  # DGROUP: 8 x (B, R, G), 4 bits each, written to the DAC as v << 2 (MAIN.EXE 0x90F0)
TAIKOH_DOS_TYPE = 0x5A90  # MONTA.PUT bytes per head type
# slot -> (label, offset in type, items, first row, rows); eyes, nose and mouth are ORed on (MAIN.EXE 0x86D5)
TAIKOH_DOS_SLOTS = {"top": ("上", 0, 8, 0, 40), "bottom": ("下", 0x1E00, 8, 40, 40), "eyes": ("眼", 0x3C00, 8, 22, 16),
                    "nose": ("鼻", 0x5580, 3, 32, 18), "mouth": ("口", 0x4800, 8, 46, 18)}
TAIKOH_DOS_OR = ("eyes", "nose", "mouth")
TAIKOH_DOS_TYPES = ["甲冑", "正面", "側面", "斜側"]
TAIKOH_DOS_HIME = 0x1000  # HIME.PUT face codes, kept apart from KAO.PUT's
TAIKOH_PC98_PALETTE = 0x7E96  # DGROUP: the same 8 x (B, R, G) table, 4 bits each, used as v * 17
TAIKOH_DOS_NAME_HISTORICAL = {
    "田山義綱": "畠山義綱", "田山義慶": "畠山義慶", "北田具教": "北畠具教", "北田具房": "北畠具房",
    "北田政成": "北畠政成", "神原忠政": "榊原忠政", "神原康政": "榊原康政", "坪和氏續": "垪和氏續",
    "坪和康忠": "垪和康忠", "脅阪安治": "脇坂安治",  # 畠, 榊, 垪, 脇 missing from the font
    "常束正家": "長束正家", "突戶隆家": "宍戶隆家", "桶口直房": "樋口直房",
}


def build_taikoh_dos(game_dir: str, pc98: bool = False) -> tuple[dict, list[bytes]]:
    """pc98=True: the Japanese PC-98 original. The same KAO/HIME/MONTA.PUT, drawn byte 0/1/2 to the B/R/G planes
    (byte k = bit k); the same B, R, G table at DGROUP 0x7E96 (MAIN.EXE 0x61D8) on the analog palette."""
    pixels = (lambda raw: bytes(genpei.decode_planar(raw, 0, 64, len(raw) // 24, 3))) if pc98 else \
        (lambda raw: bytes(utils.to_3bpp_indexes(raw)))
    files = {}
    for name in TAIKOH_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    mon = files["MONTA.PUT"]
    variants = []
    for v, label in enumerate(TAIKOH_DOS_TYPES):
        parts = {}
        for slot, (_, offset, count, row, rows) in TAIKOH_DOS_SLOTS.items():
            size = rows * 24
            base = v * TAIKOH_DOS_TYPE + offset
            items = [store.add(64, rows, pixels(mon[base + i * size:base + (i + 1) * size])) for i in range(count)]
            parts[slot] = {"at": [0, row], "items": items}
        variants.append({"id": str(v), "label": label, "parts": parts})

    kao, hime = files["KAO.PUT"], files["HIME.PUT"]
    portraits = [{"img": store.add(64, 80, pixels(kao[i:i + 1920]), blob=1),
                  "code": f"{i // 1920:04X}"} for i in range(0, len(kao), 1920)]
    first_hime = len(portraits)
    portraits += [{"img": store.add(64, 80, pixels(hime[i:i + 1920]), blob=1),
                   "code": f"{TAIKOH_DOS_HIME | i // 1920:04X}"} for i in range(0, len(hime), 1920)]

    # people at the start of a game, then those TBS.DAT brings in later; one character per name
    characters, seen = [], set()
    load = koei_games.load_taikoh_pc98_persons if pc98 else koei_games.load_taikoh_dos_persons
    persons = load(os.path.join(game_dir, "MAIN.EXE"), os.path.join(game_dir, "TBS.DAT"))
    for name, code in persons:
        if name in seen:
            continue
        seen.add(name)
        ch = {"id": len(characters), "name": name}
        if not pc98 and name in TAIKOH_DOS_NAME_HISTORICAL:
            ch["nameHistorical"] = TAIKOH_DOS_NAME_HISTORICAL[name]
        if code < 0x4000:  # MAIN.EXE 0x8924
            ch["face"] = {"portrait": code}
        else:
            ch["face"] = {"variant": code & 3,
                          "parts": [code >> 11 & 7, code >> 8 & 7, code >> 5 & 7, (code >> 14) - 1, code >> 2 & 7],
                          "code": f"{code:04X}"}
        characters.append(ch)
    women = koei_games.load_taikoh_pc98_women if pc98 else koei_games.load_taikoh_dos_women
    for name, face in women(os.path.join(game_dir, "MAIN.EXE")):
        if face != 0xFF:
            characters.append({"id": len(characters), "name": name, "face": {"portrait": first_hime + face}})

    used = {c["face"]["portrait"] for c in characters if "portrait" in c["face"]}
    for i, p in enumerate(portraits[:first_hime]):
        if i not in used:
            p["group"] = "其他頭像"

    main = files["MAIN.EXE"]
    if pc98:
        pal = main[koei_games.TAIKOH_PC98_DGROUP + TAIKOH_PC98_PALETTE:][:24]
        colours = ["#" + "".join(f"{v * 17:02x}" for v in (pal[i + 1], pal[i + 2], pal[i])) for i in range(0, 24, 3)]
    else:
        pal = main[koei_games.TAIKOH_DOS_DGROUP + TAIKOH_DOS_PALETTE:][:24]
        colours = ["#" + "".join(f"{v << 4 | v >> 2:02x}" for v in (pal[i + 1], pal[i + 2], pal[i]))
                   for i in range(0, 24, 3)]

    meta = {
        "format": FORMAT, "id": "taikoh-pc98" if pc98 else "taikoh-dos", "game": "TAIKOH",
        "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "太閤立志伝", "zh": "太閤立志傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in TAIKOH_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": colours} if pc98 else
                     {"id": "vga", "label": "VGA", "colors": colours}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "or"} if slot in TAIKOH_DOS_OR else {})}
                      for slot, (label, *_) in TAIKOH_DOS_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "nose", "hi": 15, "lo": 14, "base": 1}, {"of": "top", "hi": 13, "lo": 11},
                {"of": "bottom", "hi": 10, "lo": 8}, {"of": "eyes", "hi": 7, "lo": 5},
                {"of": "mouth", "hi": 4, "lo": 2}, {"of": "$variant", "hi": 1, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- PROGEN (PC-98)

PROGEN_PC98_INPUTS = ["KAO.LZW", "MAIN.EXE"]
PROGEN_PC98_PALETTE = 0x67BA  # MAIN.EXE DS: 8 words, 4-bit B (bits 0-3), R (4-7), G (8-11); 0x8B8A sets colours 0-7
# composite parts follow the LS11 data of KAO.LZW, read raw by 0xCF6A: per variant 4 slots x 4 parts,
# each part rows x (3 planes x width bytes); all are ORed into a cleared 64x80 buffer
PROGEN_PC98_VARIANTS = [0x36FA3, 0x3A423]  # code bits 15-14 == 2 -> second set, else first
PROGEN_PC98_SLOTS = {"top": ("頭盔上", 8, 40, 0), "bottom": ("頭盔下", 8, 40, 40), "eyes": ("眼", 6, 32, 16),
                     "mouth": ("口", 6, 48, None)}
PROGEN_PC98_MOUTH_ROW = [32, 16]
PROGEN_PC98_OR = {"eyes", "mouth"}
# faces no person record uses: shop and facility people (0x7968 table, fixed codes passed to 0xD1D2),
# those only named by the O<n> command of EVENT.EVT, and two never shown
PROGEN_PC98_FACILITY = {83, *range(107, 118)}
PROGEN_PC98_UNUSED = {72, 106}


def progen_pc98_pixels(data: bytes, width: int, rows: int) -> bytes:
    """rows x (3 planes x width bytes), MSB = leftmost pixel, plane q = colour bit q."""
    out = bytearray(width * 8 * rows)
    for r in range(rows):
        for q in range(3):
            for c in range(width):
                b = data[(r * 3 + q) * width + c]
                for i in range(8):
                    out[r * width * 8 + c * 8 + i] |= (b >> (7 - i) & 1) << q
    return bytes(out)


def build_progen_pc98(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in PROGEN_PC98_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    kao = files["KAO.LZW"]
    variants = []
    for v, base in enumerate(PROGEN_PC98_VARIANTS):
        parts = {}
        for slot, (_, width, rows, row) in PROGEN_PC98_SLOTS.items():
            size = width * 3 * rows
            items = [store.add(width * 8, rows, progen_pc98_pixels(kao[base + i * size:], width, rows))
                     for i in range(4)]
            parts[slot] = {"at": [0, PROGEN_PC98_MOUTH_ROW[v] if row is None else row], "items": items}
            base += 4 * size
        variants.append(parts)
    # code bits 15-14: 1 and 3 draw the first set, 2 the second
    variants = [{"id": str(k + 1), "label": f"類型{k + 1}", "parts": parts}
                for k, parts in enumerate([variants[0], variants[1], variants[0]])]

    portraits = [{"img": store.add(64, 80, progen_pc98_pixels(face, 8, 80), blob=1), "code": f"{i:04X}"}
                 for i, face in enumerate(ls11.ls11_decode_parts(kao))]

    characters = []
    for code, name in koei_games.load_progen_pc98_persons(os.path.join(game_dir, "MAIN.EXE")):
        ch = {"id": len(characters), "name": name}
        if code < 0x4000:  # 0xD088
            ch["face"] = {"portrait": code}
        else:
            ch["face"] = {"variant": (code >> 14) - 1, "parts": [code & 3, code >> 2 & 3, code >> 4 & 3, code >> 6 & 3],
                          "code": f"{code:04X}"}
        characters.append(ch)

    used = {c["face"]["portrait"] for c in characters if "portrait" in c["face"]}
    for i, p in enumerate(portraits):
        if i in PROGEN_PC98_UNUSED:
            p["group"] = "未使用"
        elif i in PROGEN_PC98_FACILITY and i not in used:
            p["group"] = "設施人物"
        elif i not in used:
            p["group"] = "事件人物"

    pal = files["MAIN.EXE"][koei_games.PROGEN_PC98_DGROUP + PROGEN_PC98_PALETTE:][:16]
    colours = []
    for i in range(0, 16, 2):
        w = int.from_bytes(pal[i:i + 2], "little")
        colours.append("#" + "".join(f"{(w >> s & 15) * 17:02x}" for s in (4, 8, 0)))

    meta = {
        "format": FORMAT, "id": "progen-pc98", "game": "PROGEN", "platform": "PC98",
        "title": {"ja": "プロジェネター"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in PROGEN_PC98_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": colours}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "or"} if slot in PROGEN_PC98_OR else {})}
                      for slot, (label, *_) in PROGEN_PC98_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "$variant", "hi": 15, "lo": 14, "base": 1}, {"of": "mouth", "hi": 7, "lo": 6},
                {"of": "eyes", "hi": 5, "lo": 4}, {"of": "bottom", "hi": 3, "lo": 2}, {"of": "top", "hi": 1, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- ROYAL (PC-98)

ROYAL_PC98_INPUTS = ["KAODATA.DAT", "MAIN.EXE"]
ROYAL_PC98_FACE = 1920  # 64x80, 3 bytes per 8 px, byte k = plane k
# MAIN.EXE DS:0x189E, 8 x (B, R, G) 4 bits each: faded in (0xDAA) when analog RGB was chosen at start
ROYAL_PC98_ANALOG = 0x189E
ROYAL_PC98_DIGITAL = ["#000000", "#0000ff", "#ff0000", "#ff00ff", "#00ff00", "#00ffff", "#ffff00", "#ffffff"]
ROYAL_PC98_ADVISORS = range(64, 68)  # 0x6A4C, 0x10890: 0x40 + advisor
ROYAL_PC98_UNITS = 68  # 0x8460: 0x44 + unit type


def build_royal_pc98(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in ROYAL_PC98_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    kao = files["KAODATA.DAT"]
    portraits = [{"img": store.add(64, 80, bytes(genpei.decode_planar(kao, i, 64, 80, 3))),
                  "code": f"{i // ROYAL_PC98_FACE:04X}"} for i in range(0, len(kao), ROYAL_PC98_FACE)]
    lords, units = koei_games.load_royal_pc98_names(os.path.join(game_dir, "MAIN.EXE"))
    for i in ROYAL_PC98_ADVISORS:
        portraits[i]["group"] = "相談役"
    # same groups as royal-fc, whose 91 faces are in the same order
    for i, name in enumerate(units, ROYAL_PC98_UNITS):
        portraits[i].update(group="第5部隊", name=name)

    # 0x59C: a lord's face is its index
    characters = [{"id": i, "name": name, "reading": kana_to_hiragana(name), "face": {"portrait": i}}
                  for i, name in enumerate(lords)]

    pal = files["MAIN.EXE"][koei_games.ROYAL_PC98_DGROUP + ROYAL_PC98_ANALOG:][:24]
    analog = ["#" + "".join(f"{v * 17:02x}" for v in (pal[i + 1], pal[i + 2], pal[i])) for i in range(0, 24, 3)]

    meta = {
        "format": FORMAT, "id": "royal-pc98", "game": "ROYAL", "platform": "PC98",
        "title": {"ja": "ロイヤルブラッド", "zh": "魔法皇冠"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in ROYAL_PC98_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "analog", "label": "類比 RGB", "colors": analog},
                     {"id": "digital", "label": "數位 8 色", "colors": ROYAL_PC98_DIGITAL}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- ISHIN (PC-98)

ISHIN_PC98_INPUTS = ["KAODAT.DAT", "MONDAT.DAT", "ISIN.EXE", "SHINARIO.DAT"]
ISHIN_PC98_FACE = 720  # 48x40, 3 bytes per 8 px, byte k = plane k; shown line-doubled (200-line mode)
ISHIN_PC98_CROWD = 105  # KAODAT 0x12750: face 0x2CA, for ids 450-713 (0x2F2D)
ISHIN_PC98_MASK = 0x12A20  # KAODAT: 48x40 1 bpp, ANDed over every face (0x4BD0), so the corners are colour 0
ISHIN_PC98_PALETTE = ["#000000", "#0000ff", "#ff0000", "#ff00ff", "#00ff00", "#00ffff", "#ffff00", "#ffffff"]
# MONDAT.DAT layers in drawing order (0x3BBC decodes the 6-byte record into w0-w15):
# slot -> (label, offset, parts, rows, y, field, y-offset field); a part is a 1 bpp mask (rows x 6 bytes),
# then the picture (rows x 18 bytes), drawn as (screen AND mask) OR picture
ISHIN_PC98_LAYERS = {
    "back": ("背景", 0x0000, 8, 40, 0, 0, None),
    "mage": ("髷", 0x1680, 4, 40, 0, 1, None),  # 10 = none
    "head": ("頭", 0x2580, 10, 40, 0, 2, None),
    "clothes": ("衣", 0x4B00, 10, 40, 0, 3, None),
    "eyes": ("眼", 0x7080, 10, 6, 14, 4, 9),
    "mouth": ("口", 0x7620, 10, 6, 23, 5, 10),
    "nose": ("鼻", 0x7BC0, 10, 9, 15, 6, 11),
    "brows": ("眉", 0x8430, 10, 5, 10, 7, 12),
    "hair": ("髮", 0x88E0, 10, 40, 0, 8, None),  # 10 = none
    "beard": ("鬍", 0xAE60, 1, 20, 20, 14, 13),  # drawn when w14 is set
    "band": ("鉢卷", 0xB040, 1, 40, 0, 15, None),  # drawn when w15 is set
}
ISHIN_PC98_SHIFTS = range(-2, 2)  # y-offset fields are 2 bits - 2


def ishin_pc98_fields(rec: bytes) -> list[int]:
    """0x3BBC: w0-w8 are nibbles (high first), w9-w13 y offsets, w14 beard, w15 head band."""
    return ([b >> s & 15 for b in rec[:5] for s in (4, 0)][:9]
            + [(rec[4] >> 2 & 3) - 2, (rec[4] & 3) - 2]
            + [(rec[5] >> s & 3) - 2 for s in (6, 4, 2)] + [rec[5] >> 1 & 1, rec[5] & 1])


def build_ishin_pc98(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in ISHIN_PC98_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])
    kao, mon = files["KAODAT.DAT"], files["MONDAT.DAT"]
    mask = [kao[ISHIN_PC98_MASK + i // 8] >> (7 - i % 8) & 1 for i in range(48 * 40)]

    def doubled(px: list[int], rows: int, blob: int = 0) -> int:
        return store.add(48, rows * 2, bytes(c for r in range(rows) for _ in range(2) for c in px[r * 48:r * 48 + 48]), blob)

    portraits = []
    for i in range(0, ISHIN_PC98_MASK, ISHIN_PC98_FACE):
        px = [c if m else 0 for c, m in zip(genpei.decode_planar(kao, i, 48, 40, 3), mask)]
        face = i // ISHIN_PC98_FACE
        portraits.append({"img": doubled(px, 40, 1), **({} if face == ISHIN_PC98_CROWD else {"code": f"FF{face:02X}00000000"})})
    portraits[ISHIN_PC98_CROWD]["group"] = "一般人物"

    # composite parts; the corners the mask clears are colour 0 in the background and left out of the others
    none = store.add(1, 1, bytes([TRANSPARENT]))
    parts = {}
    for slot, (_, offset, count, rows, y, _, shift) in ISHIN_PC98_LAYERS.items():
        items = []
        for k in range(count):
            if slot == "back":
                px = genpei.decode_planar(mon, offset + k * ISHIN_PC98_FACE, 48, 40, 3)
                items.append(doubled([c if m else 0 for c, m in zip(px, mask)], 40))
                continue
            o = offset + k * rows * 24
            pic = genpei.decode_planar(mon, o + rows * 6, 48, rows, 3)
            keep = [mon[o + i // 8] >> (7 - i % 8) & 1 for i in range(48 * rows)]
            for dy in ISHIN_PC98_SHIFTS if shift is not None else [0]:
                top = y + dy  # a kept pixel with colour is colour 7 in both parts that have one, so OR = copy
                px = [TRANSPARENT if (keep[i] and not c) or top + i // 48 >= 40 or not mask[(top + i // 48) * 48 + i % 48]
                      else c for i, c in enumerate(pic)]
                items.append({"img": doubled(px, rows), "at": [0, top * 2]})
        if slot in ("mage", "hair"):
            items.append(none)
        elif slot in ("beard", "band"):
            items.insert(0, none)
        parts[slot] = {"items": items}

    def composite(rec: bytes) -> dict:
        w = ishin_pc98_fields(rec)
        picks = []
        for slot, (_, _, count, _, _, field, shift) in ISHIN_PC98_LAYERS.items():
            if slot == "beard":
                picks.append(w[field] and 1 + w[shift] + 2)
            elif slot == "band":
                picks.append(w[field])
            elif shift is not None:
                picks.append(w[field] * len(ISHIN_PC98_SHIFTS) + w[shift] + 2)
            else:
                picks.append(min(w[field], count))  # 10 = none, the last item
        return {"variant": 0, "parts": picks, "code": rec.hex().upper()}

    def face(rec: bytes) -> dict:
        return {"portrait": rec[1]} if rec[0] == 0xFF else composite(rec)

    characters = []
    for name, recs in koei_games.load_ishin_pc98_persons(os.path.join(game_dir, "ISIN.EXE"),
                                                         os.path.join(game_dir, "SHINARIO.DAT")):
        ch = {"id": len(characters), "name": name, "face": face(recs[0])}
        # a few people have another face in a later scenario
        looks = []
        for s, rec in enumerate(recs):
            if looks and looks[-1][0] == rec:
                looks[-1][1].append(s + 1)
            else:
                looks.append((rec, [s + 1]))
        if len(looks) > 1:
            ch["face"]["label"] = "劇本" + "、".join(map(str, looks[0][1]))
            ch["expressions"] = [{**face(rec), "label": "劇本" + "、".join(map(str, ss))} for rec, ss in looks[1:]]
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "ishin-pc98", "game": "ISHIN", "platform": "PC98",
        "title": {"ja": "維新の嵐", "zh": "維新之嵐"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in ISHIN_PC98_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": ISHIN_PC98_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [48, 80],
            "slots": [{"id": slot, "label": label} for slot, (label, *_) in ISHIN_PC98_LAYERS.items()],
            "variants": [{"id": "0", "label": "類型 0", "parts": parts}],
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- TK (PC-98)

TK_PC98_INPUTS = ["RENPIC.DAT", "RENMAIN.EXE"]
TK_PC98_FACE = 720  # 40x48, 3 bytes per 8 px, byte k = plane k (0xE644 reads one, 0x14dd:0x115 draws it)
TK_PC98_ARMY = 40  # 0xE644: faces 40 (Japan) and 41 (the Allies) are the side's 陸軍参謀 (0x19F34)
TK_PC98_PALETTE = ["#000000", "#0000ff", "#ff0000", "#ff00ff", "#00ff00", "#00ffff", "#ffff00", "#ffffff"]


def build_tk_pc98(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in TK_PC98_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    pic = files["RENPIC.DAT"]
    # the 288 bytes after the 42 faces are 32x24 icons (0x12410)
    portraits = [{"img": store.add(40, 48, bytes(genpei.decode_planar(pic, i * TK_PC98_FACE, 40, 48, 3)))}
                 for i in range(TK_PC98_ARMY + 2)]
    for i in (TK_PC98_ARMY, TK_PC98_ARMY + 1):
        portraits[i].update(group="陸軍", name="陸軍参謀")

    # 0xE644: a face is the admiral's record index ((record - DS:0xC6FC) / 19)
    characters = [{"id": i, "name": name, "face": {"portrait": i}}
                  for i, name in enumerate(koei_games.load_tk_pc98_names(os.path.join(game_dir, "RENMAIN.EXE")))]

    meta = {
        "format": FORMAT, "id": "tk-pc98", "game": "TK", "platform": "PC98",
        "title": {"ja": "提督の決断", "zh": "提督之決斷"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in TK_PC98_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": TK_PC98_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- TK2 (PC-98)

TK2_PC98_INPUTS = ["KAO.TK2", "MAIN.EXE", "ARDATA", "GRDATA", "SJDATA"]
TK2_PC98_FACE = 1152  # 48x64, 3 bytes per 8 px, byte k = plane k (0x2A9D2 reads face n at n * 0x480)
# MAIN.EXE file 0x657F0 (PK: 0x3D860 of the unpacked main.exe): 8 x (B, R, G) 4 bits each, the face colours
# (the same table appears again after it)
TK2_PC98_PALETTE = 0x657F0
TK2PK_PC98_PALETTE = 0x3D860
# faces: per side 30 admirals then 15 generals (KAIGI.EXE 0x989B adds 45 for the Allies), then 9 heads of state
# faces only drawn by message boxes (0x31DAA): MAIN.EXE 0x331FA, 0x3304C, 0x32900, 0x32109 / 0x32235
TK2_PC98_OTHERS = {99: "M.L.ケソン", 100: "ホー・チ・ミン", 101: "加来止男", 102: "J.C.リーチ"}


def build_tk2_pc98(game_dir: str, pk: bool = False) -> tuple[dict, list[bytes]]:
    inputs = ["KAO.TK2", "PACK.LZW", "GRDATA", "SJDATA"] if pk else TK2_PC98_INPUTS
    files = {}
    for name in inputs:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    # the PK disk's PACK.LZW replaces main.exe and ardata (two Allied names fixed) when installed over the base game
    if pk:
        pack = ls11.lw11_decode_files(files["PACK.LZW"])
        exe, ardata = pack["MAIN.EXE"], pack["ARDATA"]
    else:
        exe, ardata = files["MAIN.EXE"], files["ARDATA"]
    store = ImageStore(["portraits.bin"])

    kao = files["KAO.TK2"]
    portraits = [{"img": store.add(48, 64, bytes(genpei.decode_planar(kao, i, 48, 64, 3)))}
                 for i in range(0, len(kao), TK2_PC98_FACE)]
    for i, name in TK2_PC98_OTHERS.items():
        portraits[i].update(group="事件人物", name=name)

    # admiral a: face a + 15 for the Allies (0x2F33D); general g: 30 + g + 15 for the Allies (0x1F42D);
    # so each side's admirals and generals are 45 faces in a row, ordered here by face
    admirals, generals, leaders = koei_games.load_tk2_pc98_names(ardata, files["GRDATA"], files["SJDATA"])
    names = admirals[:30] + generals[:15] + admirals[30:] + generals[15:] + leaders
    characters = [{"id": i, "name": name, "face": {"portrait": i}} for i, name in enumerate(names)]

    pal = exe[TK2PK_PC98_PALETTE if pk else TK2_PC98_PALETTE:][:24]
    colors = ["#" + "".join(f"{v * 17:02x}" for v in (pal[i + 1], pal[i + 2], pal[i])) for i in range(0, 24, 3)]

    meta = {
        "format": FORMAT, "id": "tk2pk-pc98" if pk else "tk2-pc98", "game": "TK2PK" if pk else "TK2", "platform": "PC98",
        "title": {"ja": "提督の決断II パワーアップキット", "zh": "提督之決斷II 威力加強版"} if pk
        else {"ja": "提督の決断II", "zh": "提督之決斷II"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in inputs]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": colors}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- TK3 (PC-98)

TK3_PC98_INPUTS = ["KAODATA.TK3", "MAIN.EXE", "MESSAGE.TK3"]
TK3PK_PC98_INPUTS = TK3_PC98_INPUTS + ["KAODATA2.TK3", "SNDATA2.TK3"]
TK3_PC98_PEOPLE = 0x538BE  # MAIN.EXE people table (PK: 0x5291E); face = record index 0-110
TK3PK_PC98_PEOPLE = 0x5291E
# MAIN.EXE 16 x (B, R, G) 4 bits each, set by root 0x2A6C4 from DS 0x36C5:0x0A0A (PK: file 0x3E6BA)
TK3_PC98_PALETTE = 0x3F65A
TK3PK_PC98_PALETTE = 0x3E6BA
TK3_PC98_LEADER_FACES = 141  # the 24 heads of state, in MESSAGE order
TK3_PC98_DOENITZ = (78, 152)  # K・デーニッツ: admiral record, and his face among the heads of state
# SNDATA2.TK3 (PK) scenario tables with people of their own (record index, face):
# ロンメル etc. at 0x238FF records 106-110, ジューコフ and ワシレフスキー at 0x3BBD9 records 109-110
TK3PK_PC98_SCENARIO_PEOPLE = [(0x238FF, range(106, 111)), (0x3BBD9, range(109, 111))]
# faces 111-140: 30 faces for 軍人登録 (GUNJIN.TK3 holds 30 records of 78 bytes)
TK3_PC98_REGISTERED = range(111, 141)
# faces shown by EVENTSEQ.TK3 (op 2), named from the caption that follows (op 8)
TK3_PC98_EVENT_PEOPLE = {
    165: "永野修身", 168: "E・J・キング", 174: "マレーネ・ディートリッヒ", 175: "ヨセフ・ゲッペルス",
    176: "アーニー・パイル", 177: "有賀幸作", 178: "寺内正道", 179: "日本軍パイロット",
    180: "ジョン・W・ミッチェル", 183: "デイヨー",
}
TK3PK_PC98_EVENT_PEOPLE = {204: "木梨鷹一"}  # PK event 79, 伊19 艦長
# staff officers: 181 and 182 in events, then 作戦, 砲術, 航空, 航海, 情報, 補給 for each side
# (194 is never shown by an event)
TK3_PC98_STAFF = {181: "日本軍参謀", 182: "アメリカ軍参謀",
                  **{185 + i: "日本軍" + s for i, s in enumerate(["作戦参謀", "砲術参謀", "航空参謀", "航海参謀", "情報参謀", "補給参謀"])},
                  **{191 + i: "アメリカ軍" + s for i, s in enumerate(["作戦参謀", "砲術参謀", "航空参謀", "航海参謀", "情報参謀", "補給参謀"])}}


def tk3_pc98_face(data: bytes) -> bytes:
    """64x80, 4 planes interleaved per byte: byte (y * 8 + x // 8) * 4 + q is plane q, MSB = leftmost."""
    out = bytearray(64 * 80)
    for i in range(64 * 80 // 8):
        planes = data[i * 4:i * 4 + 4]
        for b in range(8):
            out[i * 8 + b] = sum(((p >> (7 - b)) & 1) << q for q, p in enumerate(planes))
    return bytes(out)


def build_tk3_pc98(game_dir: str, pk: bool = False) -> tuple[dict, list[bytes]]:
    inputs = TK3PK_PC98_INPUTS if pk else TK3_PC98_INPUTS
    files = {}
    for name in inputs:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    exe = files["MAIN.EXE"]
    store = ImageStore(["portraits.bin"])

    faces = ls11.ls11_decode_parts(files["KAODATA.TK3"])
    base_faces = len(faces)
    if pk:
        faces += ls11.ls11_decode_parts(files["KAODATA2.TK3"])
    portraits = [{"img": store.add(64, 80, tk3_pc98_face(data))} for data in faces]
    for i in TK3_PC98_REGISTERED:
        portraits[i]["group"] = "登録軍人"
    for i, name in {**TK3_PC98_EVENT_PEOPLE, **(TK3PK_PC98_EVENT_PEOPLE if pk else {})}.items():
        portraits[i].update(group="事件人物", name=name)
    for i, name in TK3_PC98_STAFF.items():
        portraits[i].update(group="参謀", name=name)
    for i in (166, 167, 169, 170, 171, 172, 173, 184):  # not found in events or code
        portraits[i]["group"] = "不明"
    for p in portraits[base_faces:]:  # KAODATA2.TK3
        p["pk"] = True

    people = koei_games.load_tk3_pc98_persons(exe, TK3PK_PC98_PEOPLE if pk else TK3_PC98_PEOPLE)
    if pk:
        for offset, records in TK3PK_PC98_SCENARIO_PEOPLE:
            people += koei_games.load_tk3_pc98_persons(files["SNDATA2.TK3"], offset)[records.start:records.stop]
    leaders = koei_games.load_tk3_pc98_leaders(files["MESSAGE.TK3"])
    people += [(name, TK3_PC98_LEADER_FACES + i) for i, name in enumerate(leaders)]
    admiral, leader = TK3_PC98_DOENITZ
    characters = []
    for name, face in people:
        if face == leader:
            continue
        ch = {"id": face, "name": name, "face": {"portrait": face}, **({"pk": True} if face >= base_faces else {})}
        if face == admiral:
            ch["face"]["label"] = "提督"
            ch["expressions"] = [{"portrait": leader, "label": "総統"}]
        characters.append(ch)

    pal = exe[TK3PK_PC98_PALETTE if pk else TK3_PC98_PALETTE:][:48]
    colors = ["#" + "".join(f"{v * 17:02x}" for v in (pal[i + 1], pal[i + 2], pal[i])) for i in range(0, 48, 3)]

    meta = {
        "format": FORMAT, "id": "tk3pk-pc98" if pk else "tk3-pc98", "game": "TK3PK" if pk else "TK3", "platform": "PC98",
        "title": {"ja": "提督の決断III パワーアップキット", "zh": "提督之決斷III 威力加強版"} if pk
        else {"ja": "提督の決断III", "zh": "提督之決斷III"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in inputs]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": colors}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- NOBU5 (PC-98)

NOBU5_PC98_INPUTS = ["KAO.NB5", "MAIN.EXE", "SN1.NB5", "S1T.NB5", "SN2.NB5", "S2T.NB5", "SN3.NB5", "S3T.NB5"]
NOBU5_PC98_INDEX = 0x40630  # MAIN.EXE 930 u16 offsets of KAO.NB5 in 20-byte units (es:0x0780, loader 0x351C)
NOBU5_PC98_FACES = 929
# MAIN.EXE 16-colour table at file 0x41306, 16 x (B, R, G) 4 bits each (GRPDRV func 0x16);
# faces are drawn with the E plane set (GRPDRV func 0x0F, dl=1, dh=0xFF), so they use colours 8-15
NOBU5_PC98_PALETTE = 0x4131E
NOBU5_PC98_PRINCESSES = range(878, 914)  # 878 + index of the princess table (MAIN.EXE 0xAB30, 0xAC90, 0x14F3B)
# event faces: pushed together with a name (STR1.NB5 captions, MAIN.EXE 0x88DA / 0x8946 name lists, [0x89C4]),
# 925 and 926 drawn by the game without a name
NOBU5_PC98_EVENT_PEOPLE = {917: "ルイス＝フロイス", 918: "オルガンティーノ", 919: "ヴァリニャーノ", 920: "彌助",
                           925: None, 926: None}
# no person record and no call site found (914-928 apart from the above are more special faces)
NOBU5_PC98_UNKNOWN = [139, 140, *range(820, 878), 914, 915, 916, 921, 922, 923, 924, 927, 928]
# aliases sharing a face code (renamed in later scenarios); one character under the best-known name
NOBU5_PC98_ALIASES = {"長尾景虎": "上杉謙信", "武田晴信": "武田信玄", "松平元康": "徳川家康"}


def build_nobu5_pc98(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in NOBU5_PC98_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    exe, kao = files["MAIN.EXE"], files["KAO.NB5"]
    store = ImageStore(["portraits.bin"])

    index = struct.unpack_from(f"<{NOBU5_PC98_FACES + 1}H", exe, NOBU5_PC98_INDEX)
    portraits = [{"img": store.add(64, 80, nobu_pc98_face(kao[a * 20:b * 20])), "code": f"{i:04X}"}
                 for i, (a, b) in enumerate(zip(index, index[1:]))]
    for i, name in zip(NOBU5_PC98_PRINCESSES, koei_games.load_nobu5_pc98_princesses(files["SN1.NB5"])):
        portraits[i]["group"] = "姫"
        if name:
            portraits[i]["name"] = name
    for i, name in NOBU5_PC98_EVENT_PEOPLE.items():
        portraits[i].update(group="事件人物", **({"name": name} if name else {}))
    for i in NOBU5_PC98_UNKNOWN:
        portraits[i]["group"] = "不明"

    # scenario 1, its later arrivals, then scenarios 2 and 3 (as nobu4-dos); one character per face code
    characters, seen = [], set()
    for n in "123":
        for table in (koei_games.load_nobu5_pc98_scenario(files[f"SN{n}.NB5"]),
                      koei_games.load_nobu5_pc98_arrivals(files[f"S{n}T.NB5"])):
            for name, face in table:
                if face in seen:
                    continue
                seen.add(face)
                characters.append({"id": len(characters), "name": NOBU5_PC98_ALIASES.get(name, name),
                                   "face": {"portrait": face}})

    pal = exe[NOBU5_PC98_PALETTE:][:24]
    colors = ["#" + "".join(f"{v * 17:02x}" for v in (pal[i + 1], pal[i + 2], pal[i])) for i in range(0, 24, 3)]

    meta = {
        "format": FORMAT, "id": "nobu5-pc98", "game": "NOBU5", "platform": "PC98",
        "title": {"ja": "信長の野望・覇王伝", "zh": "信長之野望・霸王傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in NOBU5_PC98_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": colors}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- NOBU6 (PC-98)

NOBU6_PC98_INPUTS = ["KAODATA.NB6", "MONDATA.NB6", "MAIN.EXE", "SNDATA.NB6", "TAIKI.NB6"]
# MAIN.EXE: 16-colour palettes from file 0x3870C, 48 bytes each (B, R, G, 4 bits each); colours 0-7 change
# with the season, 8-15 are the faces and the same in all of them
NOBU6_PC98_PALETTE = 0x38724
# MONDATA.NB6 composite faces: 19 types of 6 LS11 parts each (0x11914 loads parts 6t..6t+5), drawn by 0x119E0
# into a 64x80 canvas: top at row 0, bottom below it, then eyes and mouth as 1 bpp mask (8 bytes a row) +
# picture, (screen AND mask) OR picture. Per-type tables in MAIN.EXE (segment 0x309B):
NOBU6_PC98_HEIGHTS = 0x39D24  # 0x2F74: rows of top, bottom, eyes, mouth (4 bytes per type)
NOBU6_PC98_EYES_ROW = 0x39D70  # 0x2FC0
NOBU6_PC98_MOUTH_ROW = 0x39D84  # 0x2FD4
NOBU6_PC98_TYPES = 19  # persons use 0-15
# slot -> (label, code shift); each field is 2 bits, type = code & 0x1F, bit 15 marks a composite
NOBU6_PC98_SLOTS = {"top": ("上", 5), "bottom": ("下", 7), "eyes": ("眼", 9), "mouth": ("口", 11)}
# faces without a person record: the game fills the scratch person 0x213 with a name and one of these
NOBU6_PC98_PORTRAITS = {
    # 0x514C4: merchant n gets face 379 + n, name from DS:0x1108
    **dict(zip(range(379, 389), ["神屋宗湛", "島井宗室", "津田宗及", "今井宗久", "呂宋助左衛門", "小西隆佐",
                                  "末吉孫左衛門", "茶屋四郎次郎", "角倉了以", "灰屋紹由"])),
    389: "フランシスコ・ザビエル",  # 0x93C87
    # 0x5E367: 394 + n, names from DS:0x28EC / 0x28F2
    394: "山科言継", 395: "観修寺晴豊", 396: "菊亭晴季",
    # 0x66119: 397 + n, names from DS:0x1FD4 / 0x1FEC
    **dict(zip(range(397, 409), ["住吉屋宗無", "長谷川宗仁", "武野紹鴎", "千利休", "宝蔵院胤栄", "小野忠明",
                                  "塚原卜伝", "柳生石舟斎", "快川紹喜", "沢庵宗彭", "木食応其", "西笑承兌"])),
    409: "農民",  # 0x803F3: surname 農民, a random given name from DS:0x2B0C
}
NOBU6_PC98_UNKNOWN = range(390, 394)  # Westerners; no code or data found that shows them
# aliases sharing a face code (renamed in later scenarios); one character under the best-known name
NOBU6_PC98_ALIASES = {"松平元康": "徳川家康", "武田晴信": "武田信玄", "長尾景虎": "上杉謙信", "上杉政虎": "上杉謙信",
                      "大友義鎮": "大友宗麟", "長尾景信": "上杉景信",
                      # the later scenarios use the 真田十勇士 names of the same men
                      "三好清海": "三好政康", "三好伊三": "三好政勝", "根津甚八": "浅井井頼"}


def nobu_pc98_face(data: bytes) -> bytes:
    """KAO.NB5 / KAODATA.NB6 face (覇王伝 MAIN.EXE 0x341F, 天翔記 0x11762): u16 width, u16 height, then nibbles (high first) from a byte
    stream where FE n repeats the previous byte n times (FE 01 = FE, FE 00 = 256 times).

    Each row starts with a mode: 0-7 copies from x - (mode + 1), 8-15 from row y - (mode - 7). Then per
    pixel: 0-7 is the colour, 10ab copies a + 2 pixels, 11ab n copies (ab << 4) + n + 6 pixels."""
    pos = last = rep = 0
    half = None

    def byte() -> int:
        nonlocal pos, last, rep
        if not rep:
            b = data[pos]
            pos += 1
            if b != 0xFE:
                last = b
                return b
            n = data[pos]
            pos += 1
            if n == 1:
                last = 0xFE
                return 0xFE
            rep = n or 0x100
        rep -= 1
        return last

    def nibble() -> int:
        nonlocal half
        if half is None:
            b = byte()
            half = b & 15
            return b >> 4
        v, half = half, None
        return v

    w, h = data[0] | data[1] << 8, data[2] | data[3] << 8
    pos = 4
    out = bytearray(w * h)
    for y in range(h):
        mode = nibble()
        run = 0
        for x in range(w):
            if not run:
                c = nibble()
                if not c & 8:
                    out[y * w + x] = c
                    continue
                run = ((c & 3) << 4) + nibble() + 6 if c & 4 else (c & 3) + 2
            out[y * w + x] = out[(y - mode + 7) * w + x if mode & 8 else y * w + x - mode - 1]
            run -= 1
    return bytes(out)


def build_nobu6_pc98(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in NOBU6_PC98_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    exe = files["MAIN.EXE"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    mon = ls11.ls11_decode_parts(files["MONDATA.NB6"])
    variants = []
    for t in range(NOBU6_PC98_TYPES):
        heights = exe[NOBU6_PC98_HEIGHTS + t * 4:][:4]
        rows = [0, heights[0], exe[NOBU6_PC98_EYES_ROW + t], exe[NOBU6_PC98_MOUTH_ROW + t]]
        parts = {}
        for k, slot in enumerate(NOBU6_PC98_SLOTS):
            h = heights[k]
            if k < 2:
                items = [store.add(64, h, bytes(genpei.decode_planar(mon[6 * t + k], i * h * 24, 64, h, 3)))
                         for i in range(4)]
            else:
                # kept screen pixels are transparent; the 3 kept pixels with colour (type 3 mouth 0) are the
                # same colour as every top and bottom under them, so OR = copy
                mask, pic = mon[6 * t + 2 * k - 2], mon[6 * t + 2 * k - 1]
                items = []
                for i in range(4):
                    px = genpei.decode_planar(pic, i * h * 24, 64, h, 3)
                    items.append(store.add(64, h, bytes(
                        TRANSPARENT if mask[i * h * 8 + j // 8] >> (7 - j % 8) & 1 and not c else c
                        for j, c in enumerate(px))))
            parts[slot] = {"at": [0, rows[k]], "items": items}
        variants.append({"id": str(t), "label": f"類型 {t}", "parts": parts})

    faces = sango.san5_parts(os.path.join(game_dir, "KAODATA.NB6"))  # u16 count, (u32 offset, u16 size) each
    portraits = [{"img": store.add(64, 80, nobu_pc98_face(data), blob=1), "code": f"{i:04X}"}
                 for i, data in enumerate(faces)]
    for i, name in NOBU6_PC98_PORTRAITS.items():
        portraits[i].update(group="事件人物", name=name)
    for i in NOBU6_PC98_UNKNOWN:
        portraits[i]["group"] = "不明"

    # one character per face code, in order of first appearance (only aliases share a code)
    names = {}
    for name, code in koei_games.load_nobu6_pc98_persons(files["SNDATA.NB6"], files["TAIKI.NB6"]):
        names.setdefault(code, NOBU6_PC98_ALIASES.get(name, name))
    characters = []
    for code, name in names.items():
        if code & 0x8000:
            face = {"variant": code & 0x1F, "parts": [code >> shift & 3 for _, shift in NOBU6_PC98_SLOTS.values()],
                    "code": f"{code:04X}"}
        else:
            face = {"portrait": code}
        characters.append({"id": len(characters), "name": name, "face": face})

    pal = exe[NOBU6_PC98_PALETTE:][:24]
    colors = ["#" + "".join(f"{v * 17:02x}" for v in (pal[i + 1], pal[i + 2], pal[i])) for i in range(0, 24, 3)]

    meta = {
        "format": FORMAT, "id": "nobu6-pc98", "game": "NOBU6", "platform": "PC98",
        "title": {"ja": "信長の野望・天翔記", "zh": "信長之野望・天翔記"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in NOBU6_PC98_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": colors}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label} for slot, (label, _) in NOBU6_PC98_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "mouth", "hi": 15, "lo": 11, "base": 16},  # 1 00 mm: bit 15 marks a composite
                {"of": "eyes", "hi": 10, "lo": 9}, {"of": "bottom", "hi": 8, "lo": 7},
                {"of": "top", "hi": 6, "lo": 5}, {"of": "$variant", "hi": 4, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- NOBU2 (信長の野望・全国版, PC-88)

NOBU2_PC88_INPUTS = ["DISK_A.D88", "DISK_B.D88"]
# Disk B (linear image), read by ODAMAIN 0x38F2 / 0x39B3: B, R, G bytes per 8 pixels, 200-line rows
NOBU2_PC88_LORD_FACES = 0x13D00  # 53 lords, 64x40
NOBU2_PC88_WOMEN = 0x20400  # 20 women, 88x48
NOBU2_PC88_WOMEN_COUNT = 20
NOBU2_PC88_PARTS = 0x3100  # composite: 4 faces whose row bands are mixed for successors
# slot -> (label, first row, rows); the code byte holds the four 2-bit face selectors, slot 0 lowest
NOBU2_PC88_SLOTS = {"head": ("頭", 0, 14), "eyes": ("眼", 14, 5), "nose": ("鼻", 19, 5), "mouth": ("口", 24, 16)}
NOBU2_PC88_PALETTE = ["#000000", "#0000ff", "#ff0000", "#ff00ff", "#00ff00", "#00ffff", "#ffff00", "#ffffff"]
NOBU2_PC88_NAME_HISTORICAL = {"別所長冶": "別所長治"}


def build_nobu2_pc88(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in NOBU2_PC88_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    disk_b = pc88.d88_image(files["DISK_B.D88"])
    data50s = pc88.cpm_files(pc88.d88_image(files["DISK_A.D88"]))["DATA50S.DAT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    parts = {}
    for slot, (_, row, rows) in NOBU2_PC88_SLOTS.items():
        items = []
        for i in range(4):
            o = NOBU2_PC88_PARTS + i * 960 + row * 24
            items.append(store.add(64, rows * 2, pc88.brg_pixels(disk_b[o:o + rows * 24], 8)))
        parts[slot] = {"at": [0, row * 2], "items": items}

    portraits = []
    for i in range(koei_games.NOBU2_PC88_LORDS):
        o = NOBU2_PC88_LORD_FACES + i * 960
        portraits.append({"img": store.add(64, 80, pc88.brg_pixels(disk_b[o:o + 960], 8), blob=1)})
    for i in range(NOBU2_PC88_WOMEN_COUNT):
        o = NOBU2_PC88_WOMEN + i * 1584
        portraits.append({"img": store.add(88, 96, pc88.brg_pixels(disk_b[o:o + 1584], 11), blob=1), "group": "姫"})

    # ids follow nobu2-fc (the same lord order)
    characters = []
    for i, name in enumerate(koei_games.load_nobu2_pc88_names(data50s)):
        ch = {"id": i, "name": name, "face": {"portrait": i}}
        if name in NOBU2_PC88_NAME_HISTORICAL:
            ch["nameHistorical"] = NOBU2_PC88_NAME_HISTORICAL[name]
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "nobu2-pc88", "game": "NOBU2", "platform": "PC88",
        "title": {"ja": "信長の野望・全国版", "zh": "信長之野望・全國版"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in NOBU2_PC88_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc88", "label": "PC88", "colors": NOBU2_PC88_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label} for slot, (label, *_) in NOBU2_PC88_SLOTS.items()],
            "variants": [{"id": "0", "label": "後継者", "parts": parts}],
            "code": {"kind": "bitfield", "bits": 8, "fields": [
                {"of": "mouth", "hi": 7, "lo": 6}, {"of": "nose", "hi": 5, "lo": 4},
                {"of": "eyes", "hi": 3, "lo": 2}, {"of": "head", "hi": 1, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- NOBU3 (PC-98)

NOBU3_PC98_INPUTS = ["ORGKAO1.DAT", "ORGKAO2.DAT", "ORGKAO3.DAT", "MONKAO.DAT", "SNDATA1.CIM", "SNDATA2.CIM"]
NOBU3_PC98_SET = 0x2D00  # MONKAO.DAT: 4 part sets, picked by face code bits 0-1 (MAIN.EXE 0x45B8)
# the default digital palette (MAIN.EXE DS:0x5618 holds the port A8-AE bytes 37 15 26 04, only flashed)
NOBU3_PC98_PALETTE = TK_PC98_PALETTE


def build_nobu3_pc98(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in NOBU3_PC98_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    kao = files["ORGKAO1.DAT"] + files["ORGKAO2.DAT"] + files["ORGKAO3.DAT"]
    mon = files["MONKAO.DAT"]
    store = ImageStore(["pixels.bin", "portraits.bin"])

    # the DOS layout at full height: offsets and rows doubled, 24 bytes a row, byte k = plane k
    variants = []
    for v in range(4):
        parts = {}
        for slot, (_, offset, row, rows) in NOBU3_DOS_SLOTS.items():
            size = rows * 48
            o = v * NOBU3_PC98_SET + 2 * offset
            parts[slot] = {"at": [0, 2 * row], "items": [
                store.add(64, 2 * rows, bytes(genpei.decode_planar(mon, o + i * size, 64, 2 * rows, 3)))
                for i in range(4)]}
        variants.append({"id": str(v), "label": f"類型 {v}", "parts": parts})

    portraits = [{"img": store.add(64, 80, bytes(genpei.decode_planar(kao, i * sango.SAN5_FACE, 64, 80, 3)), blob=1),
                  "code": f"{i:04X}"} for i in range(NOBU3_DOS_PORTRAITS)]
    for i in NOBU3_DOS_PRINCESSES:  # MAIN.EXE 0x10CBE: marriage shows 0x9D + rand(20)
        portraits[i]["group"] = "姫"

    # as nobu3-dos: scenario 1 then 2, one character per name and face code
    characters, seen = [], set()
    for table in koei_games.load_nobu3_pc98_people(game_dir):
        for name, code in table:
            if (name, code) in seen:
                continue
            seen.add((name, code))
            if code & 0x8000:
                face = {"variant": code & 3, "parts": [code >> 2 & 3, code >> 4 & 3, code >> 6 & 3, code >> 8 & 3,
                                                       code >> 10 & 3], "code": f"{code:04X}"}
            else:
                face = {"portrait": code}
            characters.append({"id": len(characters), "name": name, "face": face})

    meta = {
        "format": FORMAT, "id": "nobu3-pc98", "game": "NOBU3", "platform": "PC98",
        "title": {"ja": "信長の野望・戦国群雄伝", "zh": "信長之野望・戰國群雄傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in NOBU3_PC98_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": NOBU3_PC98_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "xor"} if slot in NOBU3_DOS_XOR else {})}
                      for slot, (label, *_) in NOBU3_DOS_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "mouth", "hi": 15, "lo": 10, "base": 32},  # 1 000 mm: bit 15 marks a composite
                {"of": "nose", "hi": 9, "lo": 8}, {"of": "eyes", "hi": 7, "lo": 6},
                {"of": "bottom", "hi": 5, "lo": 4}, {"of": "top", "hi": 3, "lo": 2},
                {"of": "$variant", "hi": 1, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]



NOBU3_PC88_INPUTS = ["KAODATA.DAT", "SNDATA1.CIM", "SNDATA2.CIM"]
NOBU3_PC88_SET = 0x1680  # KAODATA.DAT part set picked by face code bits 0-1 (MAIN.COM 0x2F8F)
# PC-88 typos (the PC-98 and DOS releases have them right)
NOBU3_PC88_NAME_HISTORICAL = {"河野道宣": "河野通宣", "河野道直": "河野通直", "萩野直正": "荻野直正", "萩清誉": "荻清誉",
                              "山内隆道": "山内隆通"}


def build_nobu3_pc88(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in NOBU3_PC88_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    kao = files["KAODATA.DAT"]  # the same file as nobu3-dos
    store = ImageStore(["pixels.bin", "portraits.bin"])

    variants = []
    for v in range(4):
        parts = {}
        for slot, (_, offset, row, rows) in NOBU3_DOS_SLOTS.items():
            size = rows * 24
            o = NOBU3_DOS_PARTS + v * NOBU3_PC88_SET + offset
            parts[slot] = {"at": [0, 2 * row],
                           "items": [store.add(*san2_pixels(kao[o + i * size:o + (i + 1) * size], True)) for i in range(4)]}
        variants.append({"id": str(v), "label": f"類型 {v}", "parts": parts})

    portraits = [{"img": store.add(*san2_pixels(kao[i * SAN2_FACE:(i + 1) * SAN2_FACE], True), blob=1),
                  "code": f"{i:04X}"} for i in range(NOBU3_DOS_PORTRAITS)]
    for i in NOBU3_DOS_PRINCESSES:
        portraits[i]["group"] = "姫"

    # as nobu3-pc98: scenario 1 then 2, one character per name and face code
    characters, seen = [], set()
    for table in koei_games.load_nobu3_pc98_people(game_dir, pc88=True):
        for name, code in table:
            if (name, code) in seen:
                continue
            seen.add((name, code))
            ch = {"id": len(characters), "name": name}
            if name in NOBU3_PC88_NAME_HISTORICAL:
                ch["nameHistorical"] = NOBU3_PC88_NAME_HISTORICAL[name]
            if code & 0x8000:
                ch["face"] = {"variant": code & 3, "parts": [code >> 2 & 3, code >> 4 & 3, code >> 6 & 3, code >> 8 & 3,
                                                             code >> 10 & 3], "code": f"{code:04X}"}
            else:
                ch["face"] = {"portrait": code}
            characters.append(ch)

    meta = {
        "format": FORMAT, "id": "nobu3-pc88", "game": "NOBU3", "platform": "PC88",
        "title": {"ja": "信長の野望・戦国群雄伝", "zh": "信長之野望・戰國群雄傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in NOBU3_PC88_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc88", "label": "PC88", "colors": SAN2_JP_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "xor"} if slot in NOBU3_DOS_XOR else {})}
                      for slot, (label, *_) in NOBU3_DOS_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "bitfield", "bits": 16, "fields": [
                {"of": "mouth", "hi": 15, "lo": 10, "base": 32},  # 1 000 mm: bit 15 marks a composite
                {"of": "nose", "hi": 9, "lo": 8}, {"of": "eyes", "hi": 7, "lo": 6},
                {"of": "bottom", "hi": 5, "lo": 4}, {"of": "top", "hi": 3, "lo": 2},
                {"of": "$variant", "hi": 1, "lo": 0}]},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]

# ---------------------------------------------------------------- TAIKOH2 (Windows, Chinese)

TAIKOH2_WIN_INPUTS = ["Taik2w95.exe", "FACE.LZW", "EXTFACE.PK8", "BSDATA1.TR2", "BSDATA2.TR2", "SNDATA1.TR2"]
TAIKOH2_WIN_PALETTE = 0x5003D8 + 4 * 48  # Taik2w95.exe palette 4: 16 x (B, R, G), 4 bits each, set as v << 4
TAIKOH2_WIN_EXTFACE = 451  # 0x492A10 loads EXTFACE.PK8 instead of this FACE.LZW face
TAIKOH2_WIN_PEOPLE = 695  # BSDATA 695-699 are 姓0695名0695 etc.
TAIKOH2_WIN_DELETED = "這個人削除"  # BSDATA1 466; BSDATA2 has 黑田職高 there
# 0x4A0AC0: when the protagonist (木下藤吉郎, 明智光秀 or 柴田勝家) takes a new name, the face changes
TAIKOH2_WIN_LATER = {16: 695, 364: 743, 1: 744}
# faces with no person record (0x502A30 主角相貌 choices; 0x4A108D, 0x46B4E8, 0x4482E5, 0x4915F3)
TAIKOH2_WIN_PORTRAIT_NAMES = {739: "城守備", 740: "士兵", 741: "弟子", 742: "山賊"}
TAIKOH2_WIN_PICKER = range(729, 739)
TAIKOH2_WIN_NAME_HISTORICAL = {
    "田山義續": "畠山義續", "田山義綱": "畠山義綱", "北田具教": "北畠具教", "北田具房": "北畠具房",
    "北田政成": "北畠政成", "神原康政": "榊原康政", "坪和氏續": "垪和氏續", "脅阪安治": "脇坂安治",
    "木脅祐昌": "木脇祐昌", "稻井教業": "籾井教業",  # 畠, 榊, 垪, 脇, 籾 are not in Big5
    "排鄉家嘉": "拜鄉家嘉", "穴戶隆家": "宍戶隆家", "六角承偵": "六角承禎", "稻留祐直": "稻富祐直",
    "鯰貝宗重": "鮎貝宗重", "鯰川盛長": "鮎川盛長", "門註所鑑豐": "問註所鑑豐", "蒲地鑑盛": "蒲池鑑盛",
}
# PC-98 (Japanese): same files and faces; names are Shift-JIS, the rest is in MAIN.EXE
TAIKOH2_PC98_INPUTS = ["MAIN.EXE"] + TAIKOH2_WIN_INPUTS[1:]
TAIKOH2_PC98_PALETTE = 0x6D400  # MAIN.EXE: the first 8 colours of every palette, same as TAIKOH2_WIN_PALETTE
TAIKOH2_PC98_DELETED = "この人削除"
TAIKOH2_PC98_PORTRAIT_NAMES = {739: "城守備", 740: "兵士", 741: "弟子", 742: "山賊"}
TAIKOH2_PC98_NAME_HISTORICAL = {"六角承偵": "六角承禎", "稲留祐直": "稲富祐直", "門註所鑑豊": "問註所鑑豊",
                                "蒲地鑑盛": "蒲池鑑盛"}


def build_taikoh2_win(game_dir: str, pc98: bool = False) -> tuple[dict, list[bytes]]:
    inputs = TAIKOH2_PC98_INPUTS if pc98 else TAIKOH2_WIN_INPUTS
    decode = koei_games._taikoh2_pc98_sjis if pc98 else koei_games._big5
    deleted = TAIKOH2_PC98_DELETED if pc98 else TAIKOH2_WIN_DELETED
    historical = TAIKOH2_PC98_NAME_HISTORICAL if pc98 else TAIKOH2_WIN_NAME_HISTORICAL
    files = {}
    for name in inputs:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    def face(data: bytes) -> int:  # u16 width, u16 height, then 3-bit NPK
        return store.add(64, 80, utils.unpack_npk_3bits(data[4:], 64, 80))

    faces = ls11.ls11_decode_parts(files["FACE.LZW"])
    portraits = [{"img": face(files["EXTFACE.PK8"] if i == TAIKOH2_WIN_EXTFACE else data), "code": f"{i:04X}"}
                 for i, data in enumerate(faces)]
    portraits.append({"img": face(faces[TAIKOH2_WIN_EXTFACE]), "group": "未使用"})  # never shown

    characters = []
    second = koei_games.load_taikoh2_win_persons(os.path.join(game_dir, "BSDATA2.TR2"), decode)
    for number, name in koei_games.load_taikoh2_win_persons(os.path.join(game_dir, "BSDATA1.TR2"), decode):
        if number >= TAIKOH2_WIN_PEOPLE:
            continue
        if name == deleted:
            name = second[number][1]
        ch = {"id": len(characters), "name": name, "face": {"portrait": number}}
        if number in TAIKOH2_WIN_LATER:
            ch["face"]["label"] = "前期"
            ch["expressions"] = [{"portrait": TAIKOH2_WIN_LATER[number], "label": "後期"}]
        if name in historical:
            ch["nameHistorical"] = historical[name]
        characters.append(ch)
    exe, sndata = os.path.join(game_dir, inputs[0]), os.path.join(game_dir, "SNDATA1.TR2")
    if pc98:
        others = koei_games.load_taikoh2_win_others(exe, sndata, koei_games.TAIKOH2_PC98_NAMES, decode,
                                                    koei_games.TAIKOH2_PC98_KEY)
    else:
        others = koei_games.load_taikoh2_win_others(exe, sndata)
    characters += [{"id": len(characters) + i, "name": name, "face": {"portrait": code}}
                   for i, (_, name, code) in enumerate(c for c in others if c[2] != 0xFFFF)]

    for i in TAIKOH2_WIN_PICKER:
        portraits[i]["group"] = "主角相貌"
    for i, name in (TAIKOH2_PC98_PORTRAIT_NAMES if pc98 else TAIKOH2_WIN_PORTRAIT_NAMES).items():
        portraits[i].update(name=name, group="一般人物")
    used = {look["portrait"] for ch in characters for look in [ch["face"]] + ch.get("expressions", [])}
    assert all(i in used or "group" in p for i, p in enumerate(portraits))

    if pc98:
        pal = files["MAIN.EXE"][TAIKOH2_PC98_PALETTE:][:24]
    else:
        pal = files["Taik2w95.exe"][TAIKOH2_WIN_PALETTE - koei_games.TAIKOH2_WIN_DATA:][:24]
    scale = 17 if pc98 else 16  # 4-bit analog palette on the PC-98; Taik2w95.exe sets v << 4
    colours = ["#" + "".join(f"{v * scale:02x}" for v in (pal[i + 1], pal[i + 2], pal[i])) for i in range(0, 24, 3)]

    meta = {
        "format": FORMAT, "id": "taikoh2-pc98" if pc98 else "taikoh2-win", "game": "TAIKOH2",
        "platform": "PC98" if pc98 else "WIN",
        "title": {"ja": "太閤立志伝II", "zh": "太閤立志傳II"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in inputs]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": colours} if pc98 else
                     {"id": "win", "label": "Windows", "colors": colours}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- AIR2 (DOS, Chinese)

# face sheets in resource order; group names from the Chinese AM2IBM.EXE (幹部職員一覽, 秘書, 廠商名)
AIR2_DOS_FACES = [("SEC1.GDT", "秘書"), ("SEC2.GDT", "秘書"), ("STAFF1.GDT", "幹部職員"), ("STAFF2.GDT", "幹部職員"),
                  ("STAFF3.GDT", "幹部職員"), ("STAFF4.GDT", "幹部職員"), ("STAFF5.GDT", "幹部職員"),
                  ("MAKFACE.GDT", "廠商"), ("CITYFACE.GDT", "城市")]
AIR2_DOS_FACE = 16 + 64 * 80 // 2  # 16-byte GDT header, then 4 byte-interleaved planes
# AM2IBM.EXE DGROUP 0x7FA0: 16 colours, 4-bit G, R, B, written to the DAC as v << 2
AIR2_DOS_PALETTE = ["#000000", "#6182b2", "#f3d300", "#30a261", "#d3a282", "#c37151", "#b2b2b2", "#f3f330",
                    "#000000", "#204182", "#f35100", "#107141", "#f3c3a2", "#82a2d3", "#828282", "#f3f3f3"]


def build_air2_dos(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name, _ in AIR2_DOS_FACES:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    # no face codes or person names: each sheet is loaded by file
    portraits = [{"img": store.add(64, 80, bytes(genpei.decode_planar(files[name], i + 16, 64, 80, 4))),
                  "group": group}
                 for name, group in AIR2_DOS_FACES for i in range(0, len(files[name]), AIR2_DOS_FACE)]

    meta = {
        "format": FORMAT, "id": "air2-dos", "game": "AIR2", "platform": "DOS",
        "title": {"ja": "エアーマネジメントII 航空王をめざせ", "zh": "航空霸業II"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n, _ in AIR2_DOS_FACES]},
        "display": {"scale": 6},
        "palettes": [{"id": "vga", "label": "VGA", "colors": AIR2_DOS_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": [],
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- SAN6 PK (Windows, Chinese)

SAN6PK_WIN_INPUTS = ["KAODATA.S6", "PALETTE.S6"] + [f"SNDATA{n:02}.S6" for n in range(1, 24)]
# face 0 is a blank placeholder (new-officer slots); 521-538 are byte copies of the tribe faces 541-550
SAN6PK_WIN_SKIP = {0, *range(521, 539)}
# speakers without a person slot: SAN6.EXE event calls push (face, given, surname) — see notes/san6.md
SAN6PK_WIN_PORTRAIT_NAMES = {
    651: "華佗", 652: "司馬徽", 653: "許劭", 654: "于吉", 655: "左慈", 656: "管輅", 657: "紫虛上人", 658: "南華老仙",
    659: "獻帝", 660: "貂蟬", 661: "百姓", 662: "士兵", 663: "童子", 664: "靈帝", 665: "少帝", 666: "百姓", 667: "老人",
    668: "徐庶之母", 669: "使者", 670: "士兵", 671: "武將", 672: "武將", 673: "侍女", 674: "蔡夫人",
}
# no person or event uses these; grouped by the pictures
SAN6PK_WIN_PORTRAIT_GROUPS = {
    **{i: "事件人物" for i in SAN6PK_WIN_PORTRAIT_NAMES},
    **{i: "其他頭像（男）" for i in [*range(551, 621), *range(675, 684)]},
    **{i: "其他頭像（女）" for i in [*range(621, 651), 684]},
}
SAN6PK_WIN_NAME_HISTORICAL = {"孔冑": "孔伷", "士變": "士燮"}
# faces used by characters are split over 4 blobs (about 1 MB each); the grouped, unused ones go last in extra.bin
SAN6PK_WIN_BLOBS = ["portraits.bin", "portraits2.bin", "portraits3.bin", "portraits4.bin", "extra.bin"]


def build_san6pk_win(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SAN6PK_WIN_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(SAN6PK_WIN_BLOBS)

    persons = sango.load_san6_persons(game_dir)
    used = sorted({code for _, _, code in persons})
    faces = sango.load_san6_faces(os.path.join(game_dir, "KAODATA.S6"))
    portraits, index = [], {}
    for code, px in enumerate(faces):
        if code in SAN6PK_WIN_SKIP:
            continue
        index[code] = len(portraits)
        blob = used.index(code) * 4 // len(used) if code in used else 4
        p = {"img": store.add(96, 120, px, blob=blob), "code": f"{code:04X}"}
        if code in SAN6PK_WIN_PORTRAIT_GROUPS:
            p["group"] = SAN6PK_WIN_PORTRAIT_GROUPS[code]
        if code in SAN6PK_WIN_PORTRAIT_NAMES:
            p["name"] = SAN6PK_WIN_PORTRAIT_NAMES[code]
        portraits.append(p)

    # person slots in game order; the four 武將 slots of each tribe share one name and face
    characters, seen = [], set()
    for _, name, code in persons:
        if (name, code) in seen:
            continue
        seen.add((name, code))
        ch = {"id": len(characters), "name": name, "face": {"portrait": index[code]}}
        if name in SAN6PK_WIN_NAME_HISTORICAL:
            ch["nameHistorical"] = SAN6PK_WIN_NAME_HISTORICAL[name]
        characters.append(ch)

    meta = {
        "format": FORMAT, "id": "san6pk-win", "game": "SAN6PK", "platform": "WIN",
        "title": {"ja": "三國志VI with パワーアップキット", "zh": "三國志VI 威力加強版"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SAN6PK_WIN_INPUTS]},
        "display": {"scale": 4},
        "palettes": [{"id": "win", "label": "Windows", "colors": sango.load_san6_palette(os.path.join(game_dir, "PALETTE.S6"))}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- KOUMEI (Windows, Chinese)

KOUMEI_WIN_INPUTS = ["KAO.E2", "PALET.E2", "BAKDATA.E2"]
# BAKDATA names that are troops or unnamed townsfolk, not characters
KOUMEI_WIN_TROOPS = {"運糧隊", "軍樂隊", "物資隊", "步兵隊", "弓兵隊", "騎兵隊", "戰車隊", "砲車隊", "弓騎兵", "虎兵團",
                     "象兵團", "蛇兵團", "南蠻兵", "藤甲兵", "北狄兵", "羌族兵", "士兵", "賊"}
KOUMEI_WIN_FOLK = {"首", "武術家", "老婦", "民", "旅客", "男孩", "童子", "女孩", "美人", "商人", "道具屋", "武器屋", "宮吏",
                   "老翁", "仙人", "文官", "武官", "使者", "幻術師", "官差"}
# ages shown by the faces of people with several (the ending shows them young), by face code
KOUMEI_WIN_AGES = {4: "壯年", 261: "少年", 262: "青年", 165: "壯年", 266: "嬰兒", 267: "幼年", 268: "少年",
                   72: "壯年", 263: "青年", 115: "壯年", 264: "少年", 265: "青年", 5: "壯年", 269: "青年",
                   270: "青年", 271: "壯年", 134: "少女"}
KOUMEI_WIN_NAME_HISTORICAL = {"沙摩可": "沙摩柯", "劉貴": "劉璝", "粱緒": "梁緒", "秦郎": "秦朗", "金環結": "金環三結",
                              "董茶那": "董荼那", "朵思王": "朵思大王", "木鹿王": "木鹿大王", "帶來": "帶來洞主"}


def build_koumei_win(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in KOUMEI_WIN_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])
    faces = ls11.ls11_decode_parts(files["KAO.E2"])
    portraits = [{"img": store.add(64, 80, px), "code": f"{i:04X}"} for i, px in enumerate(faces)]

    records = sango.load_koumei_persons(os.path.join(game_dir, "BAKDATA.E2"))
    generic = KOUMEI_WIN_TROOPS | KOUMEI_WIN_FOLK
    users = {}  # face code -> names, in file order
    for name, code in records:
        if name not in users.setdefault(code, []):
            users[code].append(name)
    faces_of = {}
    for name, code in records:
        if name not in generic and code not in faces_of.setdefault(name, []):
            faces_of[name].append(code)
    # face = the first one in game order; later ages (the ending) follow as expressions
    characters = []
    for name, codes in faces_of.items():
        looks = [{"portrait": c, **({"label": KOUMEI_WIN_AGES[c]} if len(codes) > 1 else {})} for c in codes]
        ch = {"id": len(characters), "name": name, "face": looks[0]}
        if len(looks) > 1:
            ch["expressions"] = looks[1:]
        if name in KOUMEI_WIN_NAME_HISTORICAL:
            ch["nameHistorical"] = KOUMEI_WIN_NAME_HISTORICAL[name]
        characters.append(ch)
    person_faces = {c for codes in faces_of.values() for c in codes}
    for code, names in users.items():
        if code not in person_faces:
            portraits[code].update(name=names[0], group="部隊" if names[0] in KOUMEI_WIN_TROOPS else "一般人物")
    for i, p in enumerate(portraits):
        if i not in users:
            p["group"] = "未使用"

    meta = {
        "format": FORMAT, "id": "koumei-win", "game": "KOUMEI", "platform": "WIN",
        "title": {"ja": "三國志孔明伝", "zh": "三國志孔明傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in KOUMEI_WIN_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "win", "label": "Windows", "colors": sango.load_koumei_palette(os.path.join(game_dir, "PALET.E2"))}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- EIKETSU (DOS, Chinese)

EIKETSU_DOS_INPUTS = ["FACEDAT.R3", "BAKDATA.R3"]
# MAIN.EXE DGROUP 0xB0A (B, R, G, 4 bits each, set through GRPDRV); faces use colours 0-7
EIKETSU_DOS_PALETTE = ["#000000", "#2041A2", "#E36100", "#C371A2", "#00B271", "#82C3F3", "#F3C351", "#F3F3F3"]
# BAKDATA names that are troops or unnamed townsfolk, not characters
EIKETSU_DOS_TROOPS = {"步兵隊", "弓兵隊", "騎兵隊", "賊兵", "軍樂隊", "運輸隊", "異民族"}
EIKETSU_DOS_FOLK = {"猛獸師", "妖術師", "武術家", "民眾", "宮吏", "農民", "商人", "旅客", "女子", "官差", "使者", "文官",
                    "武官", "夫人", "少女", "？？？", "道具屋", "童子"}
EIKETSU_DOS_NAME_HISTORICAL = {"沙摩可": "沙摩柯", "劉貴": "劉璝"}
# PC-98: the same FACEDAT.R3; its TFDED.COM writes planes 0-2 to B, R, G (table at 0x6B6), so the same indexes;
# the same B, R, G table (MAIN.EXE file 0x359AC) on the analog palette, as v * 17
EIKETSU_PC98_PALETTE = ["#000000", "#2244aa", "#ee6600", "#cc77aa", "#00bb77", "#88ccff", "#ffcc55", "#ffffff"]
EIKETSU_PC98_TROOPS = {"歩兵隊", "弓兵隊", "騎兵隊", "賊兵", "軍楽隊", "輸送隊", "異民族"}
EIKETSU_PC98_FOLK = {"猛獣師", "妖術師", "武道家", "民衆", "宮使い", "農民", "商人", "旅人", "女の子", "役人", "使者", "文官",
                     "武官", "夫人", "若い女", "？？？", "道具屋", "童子"}
EIKETSU_PC98_NAME_HISTORICAL = {"沙摩可": "沙摩柯", "歩鷙": "歩騭", "宋謙": "宋憲", "蔡仲": "蔡中"}  # 謙, 仲: plain Shift-JIS


def build_eiketsu_dos(game_dir: str, pc98: bool = False) -> tuple[dict, list[bytes]]:
    """pc98=True: the Japanese PC-98 original (Shift-JIS names, PC-98 palette)."""
    troops, folk, historical = ((EIKETSU_PC98_TROOPS, EIKETSU_PC98_FOLK, EIKETSU_PC98_NAME_HISTORICAL) if pc98 else
                                (EIKETSU_DOS_TROOPS, EIKETSU_DOS_FOLK, EIKETSU_DOS_NAME_HISTORICAL))
    files = {}
    for name in EIKETSU_DOS_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])
    faces = koei_games.load_eiketsu_dos_faces(os.path.join(game_dir, "FACEDAT.R3"))
    portraits = [{"img": store.add(64, 80, px), "code": f"{i:04X}"} for i, px in enumerate(faces)]

    load = koei_games.load_eiketsu_pc98_persons if pc98 else koei_games.load_eiketsu_dos_persons
    records = load(os.path.join(game_dir, "BAKDATA.R3"))
    generic = troops | folk
    characters, users = [], {}  # users: face code -> names, in file order
    for name, code in records:
        if name not in users.setdefault(code, []):
            users[code].append(name)
        if name in generic:
            continue
        ch = {"id": len(characters), "name": name, "face": {"portrait": code}}
        if name in historical:
            ch["nameHistorical"] = historical[name]
        characters.append(ch)
    person_faces = {c["face"]["portrait"] for c in characters}
    for code, names in users.items():
        if code not in person_faces:
            portraits[code].update(name=names[0], group="部隊" if names[0] in troops else "一般人物")
    for i, p in enumerate(portraits):
        if i not in users:
            p["group"] = "未使用"

    meta = {
        "format": FORMAT, "id": "eiketsu-pc98" if pc98 else "eiketsu-dos", "game": "EIKETSU",
        "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "三國志英傑伝", "zh": "三國志英傑傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in EIKETSU_DOS_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": EIKETSU_PC98_PALETTE} if pc98 else
                     {"id": "vga", "label": "VGA", "colors": EIKETSU_DOS_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- KOUKAI GAIDEN (Win, Chinese)

KOUKAIGD_WIN_INPUTS = ["Kao.lzw", "Monkao.dat", "koukaiGD.exe", "Sdata.dat"]
KOUKAIGD_WIN_PORTRAITS = 157  # Kao.lzw parts; the rest are 48x48 discovery pictures
# exe file 0x5D780 (B, R, G, 4 bits each); faces use colours 0-7
KOUKAIGD_WIN_PALETTE = ["#000000", "#0041D3", "#D34100", "#D361A2", "#00A261", "#00A2F3", "#F3A261", "#F3E3D3"]
# Monkao.dat: 7 raw part types of 0x60C0 bytes after the LS11 data; rows are 24 bytes, byte k = bit k
KOUKAIGD_WIN_PARTS = 0x476A2
KOUKAIGD_WIN_TYPE = 0x60C0
KOUKAIGD_WIN_TYPES = 7
# slot -> (label, offset in the type, item bytes, count, first row, code shift, code mask) (exe 0x434580);
# top and bottom are copied, then eyes, nose and mouth are ORed in (0x434660)
KOUKAIGD_WIN_SLOTS = {"top": ("上", 0, 0x318, 8, 0, 0, 7), "bottom": ("下", 0x18C0, 0x468, 8, 33, 3, 7),
                      "eyes": ("眼", 0x3C00, 0x1B0, 8, 21, 8, 7), "nose": ("鼻", 0x4980, 0x240, 4, 29, 6, 3),
                      "mouth": ("口", 0x5280, 0x1C8, 8, 45, 11, 7)}
KOUKAIGD_WIN_OR = ("eyes", "nose", "mouth")
# portraits 0-5 are the six heroes of 大航海時代II, who appear in the scenario events; names as the
# speakers in Snr1.mes / Snr2.mes (阿蘭•維斯特 is Al Vezas, "在奧斯曼帝國做生意")
KOUKAIGD_WIN_II_HEROES = ["約翰•法雷爾", "卡特琳娜•艾蘭茨", "奧托•斯賓諾拉", "恩斯特•洛佩斯", "皮耶德•康迪", "阿蘭•維斯特"]
# faces only the scenario scripts show (Snr1/Snr2.dat `c0 <side> cc <face>` before a line), named after the
# speaker; None: an unnamed speaker (152, 153 the heroine's father and mother, 156 劉魁星's mother)
KOUKAIGD_WIN_SCRIPT_FACES = {
    36: "馬休", 58: "雅各布•威爾維克", 88: "希爾頓", 135: "基爾•迪•洛伽", 136: "約克", 137: "里貝卡•卡特蘭德",
    139: "潮見風吉", 140: "劉魁星", 142: "羅德里格斯•比戈爾", 143: "岡薩雷斯•比戈爾", 150: "卡秋帕",
    151: "蒂諾卡托", 152: None, 153: None, 154: "艾絲米拉達", 155: "何塞", 156: None,
}
# the two Sdata.dat event records after the table: their portrait byte is 0x10, the scripts show these faces
KOUKAIGD_WIN_EXTRA_FACES = {"加斯帕爾•比利": 138, "長谷平藏": 141}


def build_koukaigd_win(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in KOUKAIGD_WIN_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    mon = files["Monkao.dat"]
    variants = []
    for v in range(KOUKAIGD_WIN_TYPES):
        parts = {}
        for slot, (_, offset, size, count, row, _, _) in KOUKAIGD_WIN_SLOTS.items():
            base = KOUKAIGD_WIN_PARTS + v * KOUKAIGD_WIN_TYPE + offset
            items = [store.add(64, size // 24, bytes(genpei.decode_planar(mon, base + i * size, 64, size // 24, 3)))
                     for i in range(count)]
            parts[slot] = {"at": [0, row], "items": items}
        variants.append({"id": str(v), "label": f"類型 {v + 1}", "parts": parts})

    kao = ls11.ls11_decode_parts(files["Kao.lzw"])[:KOUKAIGD_WIN_PORTRAITS]
    portraits = [{"img": store.add(64, 80, bytes(genpei.decode_planar(p, 0, 64, 80, 3)), blob=1), "code": f"{i:04X}"}
                 for i, p in enumerate(kao)]

    def face(code, variant=0):
        if code & 0xC000 == 0:
            return {"portrait": code}
        return {"variant": variant, "parts": [code >> shift & mask for *_, shift, mask in KOUKAIGD_WIN_SLOTS.values()],
                "code": f"{code:04X}"}

    tables = koei_games.load_koukaigd_win_mates(os.path.join(game_dir, "koukaiGD.exe"))
    # protagonist t plays with table t, where slot t is the empty player record; the other table names them
    people = [(tables[1 - t][t][0], tables[t][t][1]) for t in (0, 1)]
    people += [row for table in tables for row in table if row[0] is not None]
    people += koei_games.load_koukaigd_win_events(os.path.join(game_dir, "Sdata.dat"))
    people += [(name, i) for i, name in enumerate(KOUKAIGD_WIN_II_HEROES)]
    tavern = koei_games.load_koukaigd_win_tavern(os.path.join(game_dir, "Sdata.dat"))
    characters, seen = [], set()
    # appended after everyone else, so the earlier ids stay
    extra = [(name, KOUKAIGD_WIN_EXTRA_FACES[name])
             for name, _ in koei_games.load_koukaigd_win_events(os.path.join(game_dir, "Sdata.dat"), extra=True)]
    for name, code in people + tavern + extra:
        # same-name mates in the two tables share their code; two tavern women are both 安娜
        if name in seen and (name, code) not in tavern:
            continue
        seen.add(name)
        ch = {"id": len(characters), "name": name, "face": face(code)}
        if "variant" in ch["face"]:
            # the type is not in the code: the game takes it from the fleet, or at random (exe 0x434500)
            ch["face"]["label"] = variants[0]["label"]
            ch["expressions"] = [{**face(code, v), "label": variants[v]["label"]} for v in range(1, KOUKAIGD_WIN_TYPES)]
        characters.append(ch)
    used = {c["face"]["portrait"] for c in characters if "portrait" in c["face"]}
    for i, p in enumerate(portraits):
        if i in KOUKAIGD_WIN_SCRIPT_FACES:
            p.update(group="事件人物", **({"name": KOUKAIGD_WIN_SCRIPT_FACES[i]} if KOUKAIGD_WIN_SCRIPT_FACES[i] else {}))
        elif i not in used:
            p["group"] = "其他頭像"

    meta = {
        "format": FORMAT, "id": "koukaigd-win", "game": "KOUKAIGD", "platform": "WIN",
        "title": {"ja": "大航海時代外伝", "zh": "大航海時代外傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in KOUKAIGD_WIN_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "win", "label": "Windows", "colors": KOUKAIGD_WIN_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "or"} if slot in KOUKAIGD_WIN_OR else {})}
                      for slot, (label, *_) in KOUKAIGD_WIN_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- KOUKAI2 (PC-98)

# KAO.LZW is byte-identical to Monkao.dat of 大航海時代外伝: 128 faces, then the 7 part types (KOUKAIGD_WIN_*)
KOUKAI2_PC98_INPUTS = ["KAO.LZW", "MAIN.EXE", "DATA1.LZW"]
KOUKAI2_PC98_PORTRAITS = 128  # the rest of the LS11 parts are 48x48 discovery pictures
# MAIN.EXE 0x42BF8 (B, R, G, 4 bits each), colours 0-7; same values as KOUKAIGD_WIN_PALETTE
KOUKAI2_PC98_PALETTE = ["#000000", "#0044dd", "#dd4400", "#dd66aa", "#00aa66", "#00aaff", "#ffaa66", "#ffeedd"]
# the type is the low nibble of person record +0x31 (0x6FD0), which follows the nationality; MAIN.EXE 0x3A17F
KOUKAI2_PC98_TYPES = ["ポルトガル", "イスパニア", "オスマン帝国", "イギリス", "イタリア", "オランダ", "海賊"]
# faces only drawn by the scenario scripts (SNRDAT.LZW: c0 0n cc <face> c8 <message>); names from the § speaker
# labels and the dialogue in SNRMES.LZW. 92 is not used by any script
KOUKAI2_PC98_EVENT_FACES = {18: "フェレロ公爵", 19: "フェレロ公爵夫人", 21: "アルベルト皇太子", 22: "ファブリス・フェレロ",
                            23: "マルティネス侯爵", 25: "エゼキエル", 59: "手下", 93: "シャイロック頭取",
                            94: "タファリ１世", 95: "メコンベ", 96: "プレット・ペロー"}


def build_koukai2_pc98(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in KOUKAI2_PC98_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["pixels.bin", "portraits.bin"])

    kao = files["KAO.LZW"]
    variants = []
    for v, label in enumerate(KOUKAI2_PC98_TYPES):
        parts = {}
        for slot, (_, offset, size, count, row, _, _) in KOUKAIGD_WIN_SLOTS.items():
            base = KOUKAIGD_WIN_PARTS + v * KOUKAIGD_WIN_TYPE + offset
            items = [store.add(64, size // 24, bytes(genpei.decode_planar(kao, base + i * size, 64, size // 24, 3)))
                     for i in range(count)]
            parts[slot] = {"at": [0, row], "items": items}
        variants.append({"id": str(v), "label": label, "parts": parts})

    faces = ls11.ls11_decode_parts(kao)[:KOUKAI2_PC98_PORTRAITS]
    portraits = [{"img": store.add(64, 80, bytes(genpei.decode_planar(p, 0, 64, 80, 3)), blob=1), "code": f"{i:04X}"}
                 for i, p in enumerate(faces)]

    mates, events, tavern = koei_games.load_koukai2_pc98_people(os.path.join(game_dir, "DATA1.LZW"))
    characters = []
    for name, code, variant in mates:
        if code & 0xC000:
            face = {"variant": variant, "parts": [code >> shift & mask for *_, shift, mask in KOUKAIGD_WIN_SLOTS.values()],
                    "code": f"{code:04X}"}
        else:
            face = {"portrait": code}
        characters.append({"id": len(characters), "name": name, "face": face})
    characters += [{"id": len(characters) + i, "name": name, "face": {"portrait": face}}
                   for i, (name, face) in enumerate(events + tavern)]
    for i, name in KOUKAI2_PC98_EVENT_FACES.items():
        portraits[i].update(name=name, group="事件人物")
    used = {c["face"]["portrait"] for c in characters if "portrait" in c["face"]}
    for i, p in enumerate(portraits):
        if i not in used and "group" not in p:
            p["group"] = "未使用"

    meta = {
        "format": FORMAT, "id": "koukai2-pc98", "game": "KOUKAI2", "platform": "PC98",
        "title": {"ja": "大航海時代II", "zh": "大航海時代II"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in KOUKAI2_PC98_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": KOUKAI2_PC98_PALETTE}],
        "blobs": store.names,
        "images": store.refs,
        "composite": {
            "canvas": [64, 80],
            "slots": [{"id": slot, "label": label, **({"blend": "or"} if slot in KOUKAIGD_WIN_OR else {})}
                      for slot, (label, *_) in KOUKAIGD_WIN_SLOTS.items()],
            "variants": variants,
            "code": {"kind": "tuple"},
        },
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- KOUKAI3 (Win, Chinese)

KOUKAI3_WIN_INPUTS = ["MALE.CDS", "FEMALE.CDS", "CDS95.EXE.pec2bac", "OCEAN.CDS"]
# person records 0-245 are people; 246-270 are troops, tribes and fleets (not characters, their faces are
# named after them), 271-274 sea monsters without a face, 275-280 placeholders
KOUKAI3_WIN_PEOPLE = 246
KOUKAI3_WIN_GROUPS = 271
# blob per face set: male faces some character uses are split over two blobs, the other male faces go last
KOUKAI3_WIN_BLOBS = ["portraits.bin", "portraits2.bin", "female.bin", "extra.bin"]


def build_koukai3_win(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in KOUKAI3_WIN_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(KOUKAI3_WIN_BLOBS)
    exe = os.path.join(game_dir, "CDS95.EXE.pec2bac")
    persons = koei_games.load_koukai3_win_persons(exe)

    # colours 10-73 are the face palette; a few female faces also use 74, the first colour of the sea
    # scene palette (OCEAN.CDS part 1, loaded from colour 74), as in the old koukai3 face output
    colours = [(0, 0, 0)] * 10 + koei_games.load_koukai3_win_face_palette(exe)
    b, r, g = ls11.ls11_decode_parts(files["OCEAN.CDS"])[1][:3]
    colours.append((r, g, b))

    # face code as the game builds it (0x46C350): sex << 12 | face
    used = sorted({sex << 12 | face for _, face, sex in persons[:KOUKAI3_WIN_PEOPLE]})
    portraits, index = [], {}
    for sex, name in enumerate(("MALE.CDS", "FEMALE.CDS")):
        for face, px in enumerate(ls11.ls11_decode_parts(files[name])):
            code = sex << 12 | face
            blob = 2 if sex else used.index(code) * 2 // len(used) if code in used else 3
            index[code] = len(portraits)
            portraits.append({"img": store.add(80, 96, px, blob=blob), "code": f"{code:04X}"})

    characters = [{"id": i, "name": name, "face": {"portrait": index[sex << 12 | face]}}
                  for i, (name, face, sex) in enumerate(persons[:KOUKAI3_WIN_PEOPLE])]
    for name, face, sex in persons[KOUKAI3_WIN_PEOPLE:KOUKAI3_WIN_GROUPS]:
        p = portraits[index[sex << 12 | face]]
        if sex << 12 | face not in used and "name" not in p:
            p.update(name=name, group="部隊")
    for code, i in index.items():
        if code not in used and "group" not in portraits[i]:
            portraits[i]["group"] = "其他頭像（女）" if code >> 12 else "其他頭像（男）"

    meta = {
        "format": FORMAT, "id": "koukai3-win", "game": "KOUKAI3", "platform": "WIN",
        "title": {"ja": "大航海時代III Costa del Sol", "zh": "大航海時代III"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in KOUKAI3_WIN_INPUTS]},
        "display": {"scale": 4},
        "palettes": [{"id": "win", "label": "Windows", "colors": [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in colours]}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]



# ---------------------------------------------------------------- NOBU7 (Win, Chinese)

NOBU7_WIN_INPUTS = ["Kaodata.nb7", "Grppal.nb7", "Sndata05.nb7"]
# Kaodata.nb7: u32 count, then count x (u32 offset, u32 size, u32 width, u32 height); raw 8-bit pixels,
# offsets counted from the end of the table
NOBU7_WIN_PEOPLE = 716  # person ids 1-716; 717-732 are the unnamed 姬一-十六, 733-744 share the generic face 740
NOBU7_WIN_PRINCESSES = range(716, 740)
NOBU7_WIN_FOLK = 740
NOBU7_WIN_BLOBS = ["portraits.bin", "portraits2.bin"]


def build_nobu7_win(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in NOBU7_WIN_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(NOBU7_WIN_BLOBS)

    kao = files["Kaodata.nb7"]
    count, = struct.unpack_from("<I", kao)
    base = 4 + count * 16
    portraits = []
    for i in range(count):
        offset, size, w, h = struct.unpack_from("<4I", kao, 4 + i * 16)
        portraits.append({"img": store.add(w, h, kao[base + offset:base + offset + size], blob=i * len(NOBU7_WIN_BLOBS) // count),
                          "code": f"{i:04X}"})

    # scenario 5 names (德川家康, 上杉謙信 rather than scenario 1's 松平元康, 長尾景虎)
    persons = sorted(koei_games.load_nobu7_win_persons(os.path.join(game_dir, "Sndata05.nb7")))
    characters = [{"id": i, "name": surname + given, "face": {"portrait": face}}
                  for i, (_, surname, given, face) in enumerate(persons[:NOBU7_WIN_PEOPLE])]
    used = {face for *_, face in persons[:NOBU7_WIN_PEOPLE]}
    for i in NOBU7_WIN_PRINCESSES:
        portraits[i]["group"] = "公主"
    portraits[NOBU7_WIN_FOLK].update(name="農民", group="其他頭像")
    for i, p in enumerate(portraits):
        if i not in used and "group" not in p:
            p["group"] = "其他頭像"

    # Grppal.nb7 part 0: B, R, G triplets; faces use colours 10-245 (kept), 0-9 are filler
    pal = ls11.ls11_decode_parts(files["Grppal.nb7"])[0]
    colours = ["#000000"] * 10 + [f"#{pal[i + 1]:02X}{pal[i + 2]:02X}{pal[i]:02X}" for i in range(30, 246 * 3, 3)]

    meta = {
        "format": FORMAT, "id": "nobu7-win", "game": "NOBU7", "platform": "WIN",
        "title": {"ja": "信長の野望・将星録", "zh": "信長之野望・將星錄"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in NOBU7_WIN_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "win", "label": "Windows", "colors": colours}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- EIKETSU3 (毛利元就傳, Win, Chinese)

EIKETSU3_WIN_INPUTS = ["KAO.E3", "PMPALET.E3", "DATA.E3"]
# DATA.E3 records: 0-199 officers and event people, 200-247 retainers with generated names sharing 8 faces,
# 248-499 generic NPCs, 500-791 troops, 792-799 event people
EIKETSU3_WIN_PEOPLE = list(range(200)) + list(range(792, 800))
EIKETSU3_WIN_TROOPS = set(range(272, 296)) | set(range(500, 792))  # 士兵, troop units
EIKETSU3_WIN_RETAINERS = range(200, 248)
# childhood or earlier names of the same person (same face, or the young face of their set)
EIKETSU3_WIN_ALIASES = {"少輔太郎": "毛利隆元", "少輔次郎": "吉川元春", "德壽丸": "小早川隆景", "竹千代": "德川家康",
                        "松平元康": "德川家康", "竹若丸": "安國寺惠瓊", "夫人": "妙姬"}
# no record uses the older faces; they follow the record's face in KAO.E3 (matched by eye, the EXE draws
# whatever face the person object holds)
EIKETSU3_WIN_LOOKS = {
    "毛利元就": [(0, "少年"), (1, "青年"), (2, "壯年"), (3, "老年")],
    "毛利隆元": [(4, "少年"), (5, "青年"), (6, "壯年")],
    "吉川元春": [(7, "少年"), (8, "青年"), (9, "壯年")],
    "小早川隆景": [(10, "少年"), (11, "青年"), (12, "壯年")],
    "毛利輝元": [(13, "青年"), (14, "壯年")],
    "陶晴賢": [(15, "青年"), (16, "壯年")],
    "山中鹿之介": [(17, "青年"), (18, "壯年"), (19, "頭巾")],
    "織田信長": [(20, "青年"), (21, "壯年"), (22, "老年")],
    "德川家康": [(23, "少年"), (24, "青年"), (25, "壯年")],
    "安國寺惠瓊": [(26, "少年"), (27, "青年")],
    "妙姬": [(29, "青年"), (30, "壯年")],
}
EIKETSU3_WIN_PAIRS = range(42, 74, 2)  # face + 1 is the same officer, older
EIKETSU3_WIN_NAME_HISTORICAL = {"神原康政": "榊原康政", "佐佐成正": "佐佐成政", "下間賴簾": "下間賴廉"}
EIKETSU3_WIN_FACE = 112
# faces some character uses go first; the grouped ones go to extra.bin
EIKETSU3_WIN_BLOBS = ["portraits.bin", "extra.bin"]


def build_eiketsu3_win(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in EIKETSU3_WIN_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    faces = ls11.ls11_decode_parts(files["KAO.E3"])
    records = koei_games.load_eiketsu3_win_persons(os.path.join(game_dir, "DATA.E3"))

    characters, by_name = [], {}
    for i in EIKETSU3_WIN_PEOPLE:
        name, code = records[i]
        name = EIKETSU3_WIN_ALIASES.get(name, name)
        if name in by_name:
            continue
        looks = EIKETSU3_WIN_LOOKS.get(name)
        if looks is None and code in EIKETSU3_WIN_PAIRS:
            looks = [(code, "青年"), (code + 1, "壯年")]
        ch = by_name[name] = {"id": len(characters), "name": name, "face": {"portrait": code}}
        if looks:  # listed young to old; faceAt keeps the record's face in its place
            ch["face"]["label"] = dict(looks)[code]
            ch["expressions"] = [{"portrait": p, "label": label} for p, label in looks if p != code]
            if [p for p, _ in looks].index(code):
                ch["faceAt"] = [p for p, _ in looks].index(code)
        if name in EIKETSU3_WIN_NAME_HISTORICAL:
            ch["nameHistorical"] = EIKETSU3_WIN_NAME_HISTORICAL[name]
        characters.append(ch)

    # faces only retainers, NPCs or troops use take the first role name (digits dropped)
    portraits = [{"code": f"{i:04X}"} for i in range(len(faces))]
    person_faces = {look["portrait"] for ch in characters for look in [ch["face"]] + ch.get("expressions", [])}
    for i, (name, code) in enumerate(records):
        p = portraits[code]
        if code in person_faces or "name" in p:
            continue
        if i in EIKETSU3_WIN_RETAINERS:
            p.update(name="一般武將", group="一般人物")
        elif i not in EIKETSU3_WIN_PEOPLE:
            p.update(name=name.rstrip("0123456789"), group="部隊" if i in EIKETSU3_WIN_TROOPS else "一般人物")
    for i, p in enumerate(portraits):
        if i not in person_faces and "group" not in p:
            p["group"] = "未使用"

    store = ImageStore(EIKETSU3_WIN_BLOBS)
    for i in sorted(person_faces) + [i for i in range(len(faces)) if i not in person_faces]:
        # colour 0 is the background (shown as magenta filler), 255 is transparent in kaodata
        px = bytes(faces[i]).replace(b"\0", b"\xff")
        portraits[i]["img"] = store.add(EIKETSU3_WIN_FACE, EIKETSU3_WIN_FACE, px, blob=int(i not in person_faces))
    portraits = [{"img": p.pop("img"), **p} for p in portraits]

    # PMPALET.E3 part 0 (B, R, G; the map palettes agree on colours 10-174, which the faces use)
    pal = ls11.ls11_decode_parts(files["PMPALET.E3"])[0]
    colours = ["#000000"] * 10 + [f"#{pal[i + 1]:02X}{pal[i + 2]:02X}{pal[i]:02X}" for i in range(30, 175 * 3, 3)]

    meta = {
        "format": FORMAT, "id": "eiketsu3-win", "game": "EIKETSU3", "platform": "WIN",
        "title": {"ja": "毛利元就 誓いの三矢", "zh": "毛利元就傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in EIKETSU3_WIN_INPUTS]},
        "display": {"scale": 4},
        "palettes": [{"id": "win", "label": "Windows", "colors": colours}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- EIKETSU4 (織田信長傳, Win, Chinese)

EIKETSU4_WIN_INPUTS = ["KAO.E4", "PMPALET.E4", "DATA.E4"]
# DATA.E4 records: 0-184 officers, 185-199 and 640-644 empty (沒有), 200-521 troops, 522-602 generic NPCs,
# 603-639 event people
EIKETSU4_WIN_TROOPS = range(200, 522)
EIKETSU4_WIN_FOLK = range(522, 603)
EIKETSU4_WIN_NOT_PEOPLE = {"沒有", "居民3", "居民4", "農民3", "農民4", "刑人", "床上病人上", "床上病人下"}
# other names of the same person (same face, or an age of the same face set)
EIKETSU4_WIN_ALIASES = {"織田信長2": "織田信長", "織田信長3": "織田信長", "織田信長4": "織田信長", "織田信長5": "織田信長",
                        "織田信長6": "織田信長", "織田信長7": "織田信長", "木下藤吉郎": "羽柴秀吉", "松平元康": "德川家康",
                        "長尾景虎": "上杉謙信", "阿濃": "歸蝶", "打大鼓的濃姬": "歸蝶", "千宗易": "千利休"}
EIKETSU4_WIN_LOOKS = {0: "青年", 1: "壯年", 5: "羽柴秀吉", 4: "木下藤吉郎"}
# 榊 and 畠 are not in Big5
EIKETSU4_WIN_NAME_HISTORICAL = {"神原康政": "榊原康政", "北田具教": "北畠具教", "田山義慶": "畠山義慶"}


def build_eiketsu4_win(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in EIKETSU4_WIN_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])
    faces = ls11.ls11_decode_parts(files["KAO.E4"])
    portraits = [{"img": store.add(64, 80, px), "code": f"{i:04X}"} for i, px in enumerate(faces)]

    records = koei_games.load_eiketsu4_win_persons(os.path.join(game_dir, "DATA.E4"))
    faces_of = {}  # person -> faces, in record order
    for i, (name, code) in enumerate(records):
        if i in EIKETSU4_WIN_TROOPS or i in EIKETSU4_WIN_FOLK or name in EIKETSU4_WIN_NOT_PEOPLE:
            continue
        codes = faces_of.setdefault(EIKETSU4_WIN_ALIASES.get(name, name), [])
        if code not in codes:
            codes.append(code)
    characters = []
    for name, codes in faces_of.items():
        looks = [{"portrait": c, **({"label": EIKETSU4_WIN_LOOKS[c]} if len(codes) > 1 else {})} for c in codes]
        ch = {"id": len(characters), "name": name, "face": looks[0]}
        if len(looks) > 1:
            ch["expressions"] = looks[1:]
        if name in EIKETSU4_WIN_NAME_HISTORICAL:
            ch["nameHistorical"] = EIKETSU4_WIN_NAME_HISTORICAL[name]
        characters.append(ch)

    # faces only troops or NPCs use take the first role name (digits dropped)
    person_faces = {c for codes in faces_of.values() for c in codes}
    for i, (name, code) in enumerate(records):
        if code not in person_faces and name != "沒有" and "name" not in portraits[code]:
            portraits[code].update(name=name.rstrip("0123456789"),
                                   group="部隊" if i in EIKETSU4_WIN_TROOPS else "一般人物")
    used = {code for _, code in records}
    for i, p in enumerate(portraits):
        if i not in used:
            p["group"] = "未使用"

    # PMPALET.E4 part 0 (B, R, G; most map palettes share colours 10-143, which the faces use)
    pal = ls11.ls11_decode_parts(files["PMPALET.E4"])[0]
    colours = ["#000000"] * 10 + [f"#{pal[i + 1]:02X}{pal[i + 2]:02X}{pal[i]:02X}" for i in range(30, 144 * 3, 3)]

    meta = {
        "format": FORMAT, "id": "eiketsu4-win", "game": "EIKETSU4", "platform": "WIN",
        "title": {"ja": "織田信長伝", "zh": "織田信長傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in EIKETSU4_WIN_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "win", "label": "Windows", "colors": colours}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- EIKETSU5 (三國志曹操傳, Win, Chinese)

EIKETSU5_WIN_INPUTS = ["FACE.E5", "PMPALET.E5", "DATA.E5"]
# DATA.E5 records: 0-161 officers and event people, 162-173 their other looks, 174-209 generic NPCs and
# props, 210-511 troops. EKD5.EXE 0x407597 draws FACE.E5 part code + 7, except for these records,
# whose looks depend on story flags (0 曹操: parts 0-7)
EIKETSU5_WIN_LOOKS = {
    0: [(0, "青年"), (1, "青年2"), (2, "青年3"), (3, "青年4"), (4, "壯年"), (5, "壯年2"), (6, "壯年3"), (7, "壯年4")],
    1: [(223, "雙眼"), (224, "中箭"), (8, "獨眼")],  # 夏侯惇
    4: [(12, "青年"), (227, "壯年")],  # 曹彰
    8: [(21, "稱帝前"), (226, "稱帝後")],  # 曹丕
    35: [(42, "黃底"), (214, "紫底")],  # 諸葛亮, same face on another background; 諸葛亮1-4 (records 170-173) use 214
}
EIKETSU5_WIN_TROOPS = set(range(181, 189)) | set(range(210, 512))  # 士兵, 黃巾賊, troop units
EIKETSU5_WIN_PROPS = {"赤兔馬", "馬", "白馬", "大旗", "鏡台", "關羽首級"}
EIKETSU5_WIN_NAME_HISTORICAL = {"沙摩可": "沙摩柯", "費褘": "費禕"}


def build_eiketsu5_win(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in EIKETSU5_WIN_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])
    faces = ls11.ls11_decode_parts(files["FACE.E5"])
    portraits = [{"img": store.add(64, 80, px), "code": f"{i:04X}"} for i, px in enumerate(faces)]

    records = koei_games.load_eiketsu5_win_persons(os.path.join(game_dir, "DATA.E5"))
    characters, by_name = [], {}
    for i, (name, code) in enumerate(records[:174]):
        if name in EIKETSU5_WIN_PROPS:
            continue
        base = name.rstrip("0123456789")
        if base != name:  # 劉備99 etc. (faded looks) and 諸葛亮1-4
            ch = by_name[base]
            looks = [ch["face"]] + ch.get("expressions", [])
            if all(look["portrait"] != code + 7 for look in looks):
                ch.setdefault("expressions", []).append({"portrait": code + 7, "label": "虛影"})
                ch["face"].setdefault("label", "通常")
            continue
        looks = [{"portrait": p, "label": label} for p, label in EIKETSU5_WIN_LOOKS.get(i, [(code + 7, None)])]
        looks = [{k: v for k, v in look.items() if v is not None} for look in looks]
        ch = by_name[name] = {"id": len(characters), "name": name, "face": looks[0]}
        if len(looks) > 1:
            ch["expressions"] = looks[1:]
        if name in EIKETSU5_WIN_NAME_HISTORICAL:
            ch["nameHistorical"] = EIKETSU5_WIN_NAME_HISTORICAL[name]
        characters.append(ch)

    # faces only NPCs or troops use take the first role name (digits dropped)
    person_faces = {look["portrait"] for ch in characters for look in [ch["face"]] + ch.get("expressions", [])}
    for i, (name, code) in enumerate(records[174:], 174):
        p = portraits[code + 7]
        if name not in EIKETSU5_WIN_PROPS and code + 7 not in person_faces and "name" not in p:
            p.update(name=name.rstrip("0123456789"), group="部隊" if i in EIKETSU5_WIN_TROOPS else "一般人物")
    for i, p in enumerate(portraits):
        if i not in person_faces and "group" not in p:
            p["group"] = "未使用"

    # PMPALET.E5 part 40 (B, R, G); parts 0-39 leave colours 174-178 unset, all others agree on 10-178
    pal = ls11.ls11_decode_parts(files["PMPALET.E5"])[40]
    colours = ["#000000"] * 10 + [f"#{pal[i + 1]:02X}{pal[i + 2]:02X}{pal[i]:02X}" for i in range(30, 179 * 3, 3)]

    meta = {
        "format": FORMAT, "id": "eiketsu5-win", "game": "EIKETSU5", "platform": "WIN",
        "title": {"ja": "三國志曹操伝", "zh": "三國志曹操傳"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in EIKETSU5_WIN_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "win", "label": "Windows", "colors": colours}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


# ---------------------------------------------------------------- GENGHIS4 PK (Win, Chinese)

GENGHIS4PK_WIN_INPUTS = ["MENPUK.BMP", "WOMENPUK.bmp", "SCEDAT1.CK", "SCEDAT2.CK", "SCEDAT3.CK", "SCEDAT4.CK"]
# CKW95.EXE 0x46BA30 / 0x46BAB0: 64x80 cells, men 20 x 34 (face clamped to 0x2A7), women 14 x 13
# (face clamped to 0xB5)
GENGHIS4PK_WIN_SHEETS = [("MENPUK.BMP", 20, 0x2A7), ("WOMENPUK.bmp", 14, 0xB5)]
# the sheets leave the Windows static colours (0-9, 246-255) magenta; faces use 0, 5 and 255
GENGHIS4PK_WIN_STATIC = {0: (0, 0, 0), 1: (128, 0, 0), 2: (0, 128, 0), 3: (128, 128, 0), 4: (0, 0, 128),
                         5: (128, 0, 128), 6: (0, 128, 128), 7: (192, 192, 192), 8: (192, 220, 192),
                         9: (166, 202, 240), 246: (255, 251, 240), 247: (160, 160, 164), 248: (128, 128, 128),
                         249: (255, 0, 0), 250: (0, 255, 0), 251: (255, 255, 0), 252: (0, 0, 255),
                         253: (255, 0, 255), 254: (0, 255, 255), 255: (255, 255, 255)}
GENGHIS4PK_WIN_WHITE = 254  # colour 255 (white) moves here, 255 being transparent; 254 is unused
GENGHIS4PK_WIN_BLOBS = ["portraits.bin", "portraits2.bin", "female.bin"]


def build_genghis4pk_win(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in GENGHIS4PK_WIN_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()

    sheets, cells, blank = [], [], set()  # cells: (sex, face, pixels)
    for sex, (name, cols, _) in enumerate(GENGHIS4PK_WIN_SHEETS):
        im = Image.open(os.path.join(game_dir, name))
        sheets.append(im.getpalette())
        w, h = im.size
        px = im.tobytes().replace(b"\xff", bytes([GENGHIS4PK_WIN_WHITE]))
        count = w // 64 * (h // 80)
        for i in range(count):
            x, y = i % cols * 64, i // cols * 80
            cells.append((sex, i, b"".join(px[(y + r) * w + x:(y + r) * w + x + 64] for r in range(80))))
        # the patterned filler cells all equal the last one (men 616-617, 664-679; women 159, 175-181)
        blank |= {(sex, i) for _, i, cell in cells[-count:] if cell == cells[-1][2]}
    assert sheets[0] == sheets[1]

    # scenarios 1-4, men then women; one character per (sex, name, face)
    people, seen = [], set()
    for k in range(1, 5):
        for sex, persons in enumerate(koei_games.load_genghis4_win_persons(os.path.join(game_dir, f"SCEDAT{k}.CK"))):
            for name, face in persons:
                face = min(face, GENGHIS4PK_WIN_SHEETS[sex][2])
                if (sex, name, face) not in seen:
                    seen.add((sex, name, face))
                    people.append((name, (sex, face)))
    used = {key for _, key in people}

    # blank filler cells nobody uses are left out
    store = ImageStore(GENGHIS4PK_WIN_BLOBS)
    portraits, index = [], {}
    men = sum(1 for sex, _, _ in cells if sex == 0)
    for sex, i, cell in cells:
        if (sex, i) in blank and (sex, i) not in used:
            continue
        index[sex, i] = len(portraits)
        p = {"img": store.add(64, 80, cell, blob=2 if sex else i * 2 // men), "code": f"{sex << 12 | i:04X}"}
        if (sex, i) not in used:
            p["group"] = "其他頭像（女）" if sex else "其他頭像（男）"
        portraits.append(p)
    characters = [{"id": k, "name": name, "face": {"portrait": index[key]}} for k, (name, key) in enumerate(people)]

    pal = sheets[0]
    colours = [GENGHIS4PK_WIN_STATIC.get(i, tuple(pal[i * 3:i * 3 + 3])) for i in range(255)]
    colours[GENGHIS4PK_WIN_WHITE] = GENGHIS4PK_WIN_STATIC[255]

    meta = {
        "format": FORMAT, "id": "genghis4pk-win", "game": "GENGHIS4PK", "platform": "WIN",
        "title": {"ja": "チンギスハーン・蒼き狼と白き牝鹿IV パワーアップキット", "zh": "成吉思汗 蒼狼與白鹿IV 威力加強版"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in GENGHIS4PK_WIN_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "win", "label": "Windows", "colors": [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in colours]}],
        "blobs": store.names,
        "images": store.refs,
        "portraits": portraits,
        "characters": characters,
    }
    return meta, [bytes(b) for b in store.blobs]


DATASETS = {"genpei-dos": build_genpei, "genpei-pc98": lambda game_dir: build_genpei(game_dir, pc98=True), "san2-dos": build_san2,
            "san2-pc98": lambda game_dir: build_san2_jp(game_dir, "PC98"),
            "san2-x68": lambda game_dir: build_san2_jp(game_dir, "X68"), "san2-pc88": build_san2_pc88, "san3-dos": build_san3,
            "san3-pc98": lambda game_dir: build_san3(game_dir, pc98=True), "lempe-dos": build_lempe,
            "san4pk-dos": lambda game_dir: build_san4(game_dir, pk=True),
            "san4pk-pc98": lambda game_dir: build_san4(game_dir, pc98=True, pk=True),
            "san5pk-dos": build_san5pk, "san5pk-pc98": lambda game_dir: build_san5pk(game_dir, pc98=True),
            "san5-pc98": lambda game_dir: build_san5pk(game_dir, pc98=True, pk=False),
            "san1-pc98": build_san1, "san1-pc88": build_san1_pc88, "san1-dos": lambda game_dir: build_san1(game_dir, dos=True),
            "suikoden-pc98": build_suikoden_pc98,
            "suikoden-pc88": lambda game_dir: build_suikoden_pc98(game_dir, pc88=True), "suikoden-dos": build_suikoden_dos,
            "kouryuuki-dos": build_kouryuuki_dos, "europe-dos": build_europe_dos, "liberty-dos": build_liberty_dos,
            "liberty-pc98": lambda game_dir: build_liberty_dos(game_dir, pc98=True),
            "koukai-dos": build_koukai_dos, "koukai-pc98": lambda game_dir: build_koukai_dos(game_dir, pc98=True),
            "genghis-dos": build_genghis_dos,
            "nobu3-dos": build_nobu3_dos, "nobu4-dos": build_nobu4_dos, "air2-dos": build_air2_dos,
            "taikoh-dos": build_taikoh_dos, "taikoh-pc98": lambda game_dir: build_taikoh_dos(game_dir, pc98=True),
            "taikoh2-win": build_taikoh2_win, "taikoh2-pc98": lambda game_dir: build_taikoh2_win(game_dir, pc98=True),
            "progen-pc98": build_progen_pc98,
            "royal-pc98": build_royal_pc98, "ishin-pc98": build_ishin_pc98,
            "tk-pc98": build_tk_pc98, "tk2-pc98": build_tk2_pc98,
            "tk2pk-pc98": lambda game_dir: build_tk2_pc98(game_dir, pk=True),
            "nobu2-pc88": build_nobu2_pc88, "nobu3-pc98": build_nobu3_pc98, "nobu3-pc88": build_nobu3_pc88,
            "genghis-pc88": lambda game_dir: build_genghis_dos(game_dir, pc88=True), "nobu4-pc98": lambda game_dir: build_nobu4_dos(game_dir, pc98=True),
            "nobu4-pc88": build_nobu4_pc88,
            "nobu5-pc98": build_nobu5_pc98, "nobu6-pc98": build_nobu6_pc98,
            "tk3-pc98": build_tk3_pc98, "tk3pk-pc98": lambda game_dir: build_tk3_pc98(game_dir, pk=True),
            "san6pk-win": build_san6pk_win, "koumei-win": build_koumei_win, "eiketsu-dos": build_eiketsu_dos,
            "eiketsu-pc98": lambda game_dir: build_eiketsu_dos(game_dir, pc98=True),
            "koukai2-pc98": build_koukai2_pc98, "koukaigd-win": build_koukaigd_win, "koukai3-win": build_koukai3_win,
            "nobu7-win": build_nobu7_win,
            "eiketsu3-win": build_eiketsu3_win,
            "eiketsu4-win": build_eiketsu4_win,
            "eiketsu5-win": build_eiketsu5_win,
            "genghis4pk-win": build_genghis4pk_win}


@click.command(help=f"匯出 kaodata 統一格式資料集 (DATASET: {', '.join(DATASETS)})")
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
