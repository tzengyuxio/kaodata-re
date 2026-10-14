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
        else:
            ch["face"] = {"portrait": code - 1}
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
        portraits += [{"img": store.add(64, 80, px, blob=1), "code": f"{i:04X}"}
                      for i, px in enumerate(shown) if i >= len(faces)]
        picker = [bytes(genpei.decode_planar(files["KAODATA2.S4"], i * 1920, 64, 80, 3))
                  for i in range(len(files["KAODATA2.S4"]) // 1920)]
        extra = [px for px in picker if px not in shown[len(faces):]]
        for px, name, group in zip(extra, SAN4PK_EXTRA_NAMES, SAN4PK_EXTRA_GROUPS, strict=True):
            portraits.append({"img": store.add(64, 80, px, blob=2), "group": group, **({} if name == "-" else {"name": name})})

    characters = []
    # scenarios 1-6 in order; 羌族、烏丸族、山越族、南蠻族 share one face code, so key on the name too
    seen = set()
    for _, name, code in sango.load_san4_persons(os.path.join(game_dir, "SNDATA.S4"),
                                                  os.path.join(game_dir, "TAIKI.S4"), pc98):
        if (code, name) in seen:
            continue
        seen.add((code, name))
        ch = {"id": len(characters), "name": name}
        historical = SAN4_PC98_NAME_HISTORICAL if pc98 else SAN4_NAME_HISTORICAL
        if code in historical:
            ch["nameHistorical"] = historical[code]
        if code & 0x8000:
            ch["face"] = {"variant": code & 15, "parts": sango.san4_montage_parts(code), "code": f"{code:04X}"}
        else:
            ch["face"] = {"portrait": code}
        characters.append(ch)
    if pk:
        # the 水滸伝 officers registered from NBDATA.SUI follow the scenario persons
        characters += [{"id": len(characters) + i, "name": name, "face": {"portrait": code}} for i, (name, code) in
                       enumerate(sango.load_san4pk_suikoden(os.path.join(game_dir, "NBDATA.SUI")))]

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


def build_san5pk(game_dir: str, pc98: bool = False) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SAN5PK_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    # KAOEX.S5 (borrowed faces) goes in its own blob
    store = ImageStore(["portraits.bin", "extra.bin"])

    kao = files["KAODATA.S5"] + files["KAOEX.S5"]
    portraits = [{"img": store.add(*san3_pixels(kao[i:i + sango.SAN5_FACE], True),
                                   blob=int(i >= len(files["KAODATA.S5"]))),
                  "code": f"{i // sango.SAN5_FACE:04X}"} for i in range(0, len(kao), sango.SAN5_FACE)]
    for i, group in SAN5PK_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for p in portraits[len(files["KAODATA.S5"]) // sango.SAN5_FACE:]:
        p["group"] = SAN5PK_EXTRA_GROUP
    for i, name in (SAN5PK_PC98_PORTRAIT_NAMES if pc98 else SAN5PK_PORTRAIT_NAMES).items():
        portraits[i]["name"] = name

    characters = []
    # scenarios 1-12 in order, deduplicated by face code (one name per code)
    seen = set()
    pick = SAN5PK_PC98_NAME_PICK if pc98 else {}
    for _, name, code in sango.load_san5_persons(os.path.join(game_dir, "SNDATA.S5"),
                                                  os.path.join(game_dir, "TAIKI.S5"), pc98):
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
        "format": FORMAT, "id": "san5pk-pc98" if pc98 else "san5pk-dos", "game": "SAN5PK",
        "platform": "PC98" if pc98 else "DOS",
        "title": {"ja": "三國志V with パワーアップキット", "zh": "三國志V 威力加強版"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SAN5PK_INPUTS]},
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


# ---------------------------------------------------------------- SUIKODEN (PC-98)

SUIKODEN_PC98_INPUTS = ["KAO98.DAT", "SUIDATA1.CIM"]
SUIKODEN_PC98_FACE = 1920  # 64x80 full height, 3bpp
# faces 255-259 have no person; identified against suikoden-fc
SUIKODEN_PC98_PORTRAIT_GROUPS = {255: "施設", 256: "施設", 257: "施設", 258: "特殊人物", 259: "特殊人物"}
SUIKODEN_PC98_PORTRAIT_NAMES = {255: "造船所", 256: "雑貨屋", 257: "武器屋", 258: "徽宗皇帝", 259: "金国太宗"}


def build_suikoden_pc98(game_dir: str) -> tuple[dict, list[bytes]]:
    files = {}
    for name in SUIKODEN_PC98_INPUTS:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    store = ImageStore(["portraits.bin"])

    kao = files["KAO98.DAT"]
    portraits = [{"img": store.add(*san2_jp_pixels(kao[i:i + SUIKODEN_PC98_FACE], True)),
                  "code": f"{i // SUIKODEN_PC98_FACE:04X}"} for i in range(0, len(kao), SUIKODEN_PC98_FACE)]
    for i, group in SUIKODEN_PC98_PORTRAIT_GROUPS.items():
        portraits[i]["group"] = group
    for i, name in SUIKODEN_PC98_PORTRAIT_NAMES.items():
        portraits[i]["name"] = name

    # the four scenarios have the same names and faces
    characters = [{"id": cid, "name": name, "face": {"portrait": code}} for cid, (code, name) in
                  enumerate(koei_games.load_suikoden_pc98_persons(os.path.join(game_dir, "SUIDATA1.CIM")))]

    meta = {
        "format": FORMAT, "id": "suikoden-pc98", "game": "SUIKODEN", "platform": "PC98",
        "title": {"ja": "水滸伝・天命の誓い", "zh": "水滸傳・天命之誓"},
        "source": {"producer": "kaodata-re", "revision": revision(),
                   "inputs": [{"path": n, "sha1": hashlib.sha1(files[n]).hexdigest()} for n in SUIKODEN_PC98_INPUTS]},
        "display": {"scale": 6},
        "palettes": [{"id": "pc98", "label": "PC98", "colors": SAN2_JP_PALETTE}],
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


DATASETS = {"genpei-dos": build_genpei, "san2-dos": build_san2,
            "san2-pc98": lambda game_dir: build_san2_jp(game_dir, "PC98"),
            "san2-x68": lambda game_dir: build_san2_jp(game_dir, "X68"), "san3-dos": build_san3,
            "san3-pc98": lambda game_dir: build_san3(game_dir, pc98=True), "lempe-dos": build_lempe,
            "san4-dos": build_san4, "san4-pc98": lambda game_dir: build_san4(game_dir, pc98=True),
            "san4pk-pc98": lambda game_dir: build_san4(game_dir, pc98=True, pk=True),
            "san5pk-dos": build_san5pk, "san5pk-pc98": lambda game_dir: build_san5pk(game_dir, pc98=True),
            "san1-pc98": build_san1, "san1-dos": lambda game_dir: build_san1(game_dir, dos=True),
            "suikoden-pc98": build_suikoden_pc98, "suikoden-dos": build_suikoden_dos,
            "kouryuuki-dos": build_kouryuuki_dos, "europe-dos": build_europe_dos}


@click.command(help="匯出 kaodata 統一格式資料集 (DATASET: genpei-dos, san1-dos, san1-pc98, san2-dos, san2-pc98, san2-x68, san3-dos, san3-pc98, san4-dos, san4-pc98, san4pk-pc98, san5pk-dos, san5pk-pc98, suikoden-pc98, suikoden-dos, kouryuuki-dos, europe-dos, lempe-dos)")
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
