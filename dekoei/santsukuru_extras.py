"""三国志ツクール (Steam 397720): event pictures, screens, the 戦利品 pictures and sample items, the strategy map
and its 41 州, the manual pages and the message texts, extracted for archiving.

See notes/santsukuru.md「事件、插圖、道具」. Usage (from dekoei/):
    dekoei.py santsukuru-extras --game-dir ../games/santsukuru-win --out ../games/santsukuru-win/extract
"""
import colorsys
import csv
import io
import os
import struct

import click
from PIL import Image, ImageDraw, ImageFont

# LINKDATA items (notes/santsukuru.md「封裝」)
MESSAGES = 135      # 3110 CRLF lines of Shift-JIS: the game's messages, menus and editor texts
BGM_TITLES = 134    # XL table, 66 rows (曲名, 出典); the music itself is not kept
ITEM_PICTURES = 137  # 367 BMPs of 120x120 back to back, then one category byte per picture
FUNERAL = 138       # a single 464x288 BMP (葬儀 still)
KOEI_LOGO = 148     # a single 1280x720 BMP
MANUAL = 149        # "count, (offset, size)" archive of 11 BMPs of 1280x720: the in-game manual pages
PROVINCE_MASKS = 139  # "HMMP": 82 records (u16 x, y, w, h + a 1-bit mask, rows 32-bit aligned), two per 州
SCENARIO = 151      # the sample scenario 『三国志ツクール』シナリオ
ATLASES = range(140, 147)  # TLSK1100 texture atlases with named pictures
DLC_ATLAS = "RES/D01128J.bin"  # TLSK UI pictures of DLC 413590
# 戦利品ＣＧ categories: the editor's list 車馬 武具 書物 宝物 茶器 (MESSAGES lines 2217-2221); 5 has no name there
PICTURE_KINDS = {0: "車馬", 1: "武具", 2: "書物", 3: "宝物", 4: "茶器"}
# sample scenario: 100 item slots of 38 bytes from 0x1303E: u8 kind, u8 value, u16 picture (ITEM_PICTURES index),
# u8 used, name 13, reading 20 (half-width kana, NUL ended); kind 0xFF is an empty slot
ITEMS = (0x1303E, 38, 100)
# where a TLSK picture goes, by name prefix (first match); the rest go to ui/<atlas>/
ROUTES = [("strategy_stil", "eventcg/still"), ("btl_result_stil", "eventcg/still"), ("event_", "eventcg/ending"),
          ("end_", "eventcg/ending"), ("sentou_", "eventcg/effects"), ("senryaku_", "eventcg/effects"),
          ("stg_map", "map/atlas"), ("title_", "eventcg/screens"), ("shoki_bg", "eventcg/screens"),
          ("stg_bg", "eventcg/screens"), ("btl_bg", "eventcg/screens"), ("0", "eventcg/screens")]


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def save(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


class Linkdata:
    def __init__(self, game_dir):
        with open(os.path.join(game_dir, "LINKDATA.IDX"), "rb") as f:
            self.idx = f.read()
        self.path = os.path.join(game_dir, "LINKDATA0.BIN")

    def __getitem__(self, i):
        pos, size, _, _ = struct.unpack_from("<4Q", self.idx, 32 * i)
        with open(self.path, "rb") as f:
            f.seek(pos)
            return f.read(size)


def bmp(b):
    return Image.open(io.BytesIO(b)).convert("RGB")


def table(b):
    """A "u32 count, count x (u32 offset, u32 size)" archive."""
    n = struct.unpack_from("<I", b)[0]
    v = struct.unpack_from(f"<{2 * n}I", b, 4)
    return [b[v[2 * k]:v[2 * k] + v[2 * k + 1]] for k in range(n)]


def tlsk(b):
    """[(name, RGBA image)] of a TLSK1100 atlas: u32 count at +8; from 0x40 (u32 name length, u32 offset) per
    picture, then the names back to back (NUL ended). A picture: u16 w, h at +4, u32 size at +0x1C, u32 stride
    at +0x20, B G R A pixels from +0x48."""
    assert b[:8] == b"TLSK1100"
    n = struct.unpack_from("<I", b, 8)[0]
    p, out = 0x40 + 8 * n, []
    for k in range(n):
        ln, pos = struct.unpack_from("<II", b, 0x40 + 8 * k)
        name = b[p:p + ln].decode("cp932")
        p += ln + 1
        w, h = struct.unpack_from("<HH", b, pos + 4)
        size, stride = struct.unpack_from("<II", b, pos + 0x1C)
        out.append((name, Image.frombytes("RGBA", (w, h), b[pos + 0x48:pos + 0x48 + size], "raw", "BGRA", stride)))
    return out


def xl(b):
    """Rows of an XL table whose columns are all strings (type 0)."""
    ncol, nrow, width, head = struct.unpack_from("<HHHI", b, 6)
    rows = []
    for r in range(nrow):
        rows.append([b[head + v:b.index(b"\0", head + v)].decode("cp932")
                     for v in struct.unpack_from(f"<{ncol}i", b, head + r * width)])
    return rows


def pictures(ld, game_dir, out):
    counts = {}

    def put(folder, name, im):
        save(im, os.path.join(out, folder, name + ".png"))
        counts[folder] = counts.get(folder, 0) + 1

    for i in ATLASES:
        for name, im in tlsk(ld[i]):
            folder = next((f for pre, f in ROUTES if name.startswith(pre)), f"ui/{i}")
            put(folder, name, im)
    with open(os.path.join(game_dir, DLC_ATLAS), "rb") as f:
        for name, im in tlsk(f.read()):
            put("ui/dlc413590", name, im)
    put("eventcg/still", "funeral", bmp(ld[FUNERAL]))
    put("eventcg/screens", "koei_logo", bmp(ld[KOEI_LOGO]))
    for k, page in enumerate(table(ld[MANUAL])):
        put("manual", f"{k:02d}", bmp(page))
    return counts


def items(ld, out):
    b = ld[ITEM_PICTURES]
    p, ims = 0, []
    while b[p:p + 2] == b"BM":
        size = struct.unpack_from("<I", b, p + 2)[0]
        ims.append(bmp(b[p:p + size]))
        p += size
    kinds = b[p:]
    assert len(kinds) == len(ims)
    for k, im in enumerate(ims):
        save(im, os.path.join(out, "items", "pictures", f"{k:03d}.png"))
    write_csv(os.path.join(out, "items", "pictures.csv"), ["picture", "file", "category", "categoryName"],
              [[k, f"{k:03d}.png", c, PICTURE_KINDS.get(c, "")] for k, c in enumerate(kinds)])
    s = ld[SCENARIO]
    start, size, count = ITEMS
    rows = []
    for k in range(count):
        r = s[start + size * k:][:size]
        kind, value, pic, used = struct.unpack_from("<BBHB", r)
        if kind == 0xFF:
            continue
        name = r[5:18].split(b"\0")[0].decode("cp932")
        reading = r[18:38].split(b"\0")[0].decode("cp932")
        rows.append([k, name, reading, kind, value, pic, f"{pic:03d}.png", PICTURE_KINDS.get(kinds[pic], ""), used])
    write_csv(os.path.join(out, "items", "items.csv"),
              ["slot", "name", "reading", "kind", "value", "picture", "file", "pictureCategory", "used"], rows)
    return len(ims), len(rows)


def provinces(ld, game_dir, out):
    """41 州: name and scenario position from the sample scenario, the box from HMMP, filled with the atlas's
    stg_map_area_mask_NN (alpha) on the strategy map. HMMP's own 1-bit masks do not fit the borders (not used)."""
    from places_export import santsukuru_provinces
    b = ld[PROVINCE_MASKS]
    assert b[8:12] == b"HMMP"
    offs = struct.unpack_from("<82I", b, 16)
    names = santsukuru_provinces(game_dir)
    atlas = dict(tlsk(ld[142]))
    base = atlas["stg_map"].convert("RGBA")
    over = Image.new("RGBA", base.size, (0, 0, 0, 0))
    rows, boxes = [], []
    for k in range(41):
        x, y, w, h = struct.unpack_from("<4H", b, 8 + offs[2 * k])
        mask = atlas[f"stg_map_area_mask_{k + 1:02d}"]
        w, h = mask.size  # HMMP's w is sometimes rounded up to 32 bits; the atlas has the real size
        col = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(k * 0.381 % 1, 0.6, 1)) + (130,)
        over.paste(Image.new("RGBA", (w, h), col), (x, y), mask.getchannel("A"))
        name, sx, sy, adj = names[k]
        rows.append([k + 1, name, x, y, w, h, sx, sy, " ".join(str(a + 1) for a in adj)])
        boxes.append((k + 1, name, x + w // 2, y + h // 2))
    im = Image.alpha_composite(base, over)
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 12)
    for n, name, cx, cy in boxes:
        draw.text((cx, cy), f"{n}{name}", fill=(0, 0, 0), font=font, anchor="mm", stroke_width=2,
                  stroke_fill=(255, 255, 255))
    save(im, os.path.join(out, "map", "provinces.png"))
    save(base, os.path.join(out, "map", "stg_map.png"))
    write_csv(os.path.join(out, "map", "provinces.csv"),
              ["province", "name", "maskX", "maskY", "maskW", "maskH", "scenarioX", "scenarioY", "neighbours"], rows)
    return len(rows)


def texts(ld, out):
    lines = ld[MESSAGES].decode("cp932").split("\r\n")
    write_csv(os.path.join(out, "text", "messages.csv"), ["line", "text"], [[k, t] for k, t in enumerate(lines)])
    bgm = xl(ld[BGM_TITLES])
    write_csv(os.path.join(out, "tables", "bgm_titles.csv"), ["track", "title", "source"],
              [[k, *r] for k, r in enumerate(bgm)])
    return len(lines), len(bgm)


@click.command("santsukuru-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam install (397720)")
@click.option("--out", required=True, type=click.Path())
def santsukuru_extras(game_dir, out):
    """三国志ツクール: event pictures, screens, item pictures and sample items, the 41 州 map, manual, messages."""
    ld = Linkdata(game_dir)
    print("pictures:", pictures(ld, game_dir, out))
    n, i = items(ld, out)
    print(f"{n} item pictures, {i} sample items")
    print(f"{provinces(ld, game_dir, out)} provinces")
    m, t = texts(ld, out)
    print(f"{m} message lines, {t} BGM titles")


if __name__ == "__main__":
    santsukuru_extras()
