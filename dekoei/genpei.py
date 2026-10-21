import math
import os
import struct
import click
from PIL import Image
from utils import (
    LITTLE_ENDIAN,
    unpack_npk,
    unpack_npk_3bits,
)

# Colours come from Mainpal.pld (load_mainpal); the colour tables measured from
# screenshots that used to be here did not match it (see notes/genpei.md).

@click.group()
def genpei():
    """源平合戰

    \b
    Kaodata.gp
    Montage.gp
    ENDDAT.GP
    HGROUND.GP          (8px_in_3bytes 時有 mask 的 pattern), 未解析
    HIKBACK.GP          單挑背景
    HKUMI.GP
    HUNITPAT.GP         單位圖案, 動畫, 8px_in_3bytes, 未解析
    OPENDAT.GP          片頭
    MAINCMD.GP          有「決定」「中止」等字樣, 8px_in_3bytes, 未解析
    MAINCMD2.GP         外交 (error)
    MAINEVT.GP          事件
    MAINITEM.GP         道具
    MAINMAP.GP          地圖
    MAINSTL.GP          月令圖, 小地圖
    """
    pass


@click.command(help="CG 解析")
@click.option("-f", "--file", "cg_file", help="圖像檔案", required=True)
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
@click.option("--prefix", "prefix", default="", help="filename prefix of output files")
def genpei_cg(cg_file, out_dir, prefix):
    """CG 解析（色盤用同目錄 Mainpal.pld 的第 0 組）"""
    os.makedirs(out_dir, exist_ok=True)

    palette = load_mainpal(read_game_file(os.path.dirname(cg_file), "Mainpal.pld"))

    with open(cg_file, "rb") as f:
        offsets = []
        data = bytearray(f.read())
        offset = data.find(b"NPK016")
        while offset != -1:
            offsets.append(offset)
            offset = data.find(b"NPK016", offset + 1)
        offsets.append(len(data))
        for offset in offsets[:-1]:
            print(f"processing {offset=:08X}")

        images = []
        width, height = 0, 0
        for i in range(len(offsets) - 1):
            offset = offsets[i]
            size = offsets[i + 1] - offset
            f.seek(offset)
            npk_data = f.read(size)
            a = int.from_bytes(npk_data[0x06:0x08], LITTLE_ENDIAN)
            b = int.from_bytes(npk_data[0x08:0x0A], LITTLE_ENDIAN) # screen width
            c = int.from_bytes(npk_data[0x0A:0x0C], LITTLE_ENDIAN) # screen height
            width = int.from_bytes(npk_data[0x0C:0x0E], LITTLE_ENDIAN)
            height = int.from_bytes(npk_data[0x0E:0x10], LITTLE_ENDIAN)
            print(f"[{i:02d}] {offset=:08X} {a=:04d} {b=:04d} {c=:04d} {width=:04d} {height=:04d}")
            # palette_data = npk_data[0x10:0x30]
            # s = palette_data.hex()
            # result = ' '.join(s[i:i+4] for i in range(0, len(s), 4))
            # print(f"palette: {result}")
            color_indexes = unpack_npk(npk_data[0x30:], width, height)
            image = Image.new("RGB", (width, height))
            for px_index, color_index in enumerate(color_indexes):
                y, x = divmod(px_index, width)
                c = palette[color_index]
                try:
                    image.putpixel((x, y), c)
                except:
                    print(f'{x=:02d} {y=:02d} {px_index=:02X} {color_index=:02X}')
            image.save(f"{out_dir}/{prefix}{i:03d}.png")
            images.append(image)

        # save 大地圖
        if "mainmap" in cg_file.lower():
            image = Image.new("RGB", (width * len(images) - 48 - 32, height))
            for i, img in enumerate(images):
                pos_x = width * i - math.floor(i / 4) * 16
                image.paste(img, (pos_x, 0))
            image.save(f"{out_dir}/{prefix}all.png")
        print(f"save {len(offsets)-1} images")

        if "cmd2" in cg_file.lower():
            f.seek(86140)
            offsets = []
            data = bytearray(f.read())
            offset = data.find(b"\xa0\x00\x80\x00")
            while offset != -1:
                offsets.append(offset)
                offset = data.find(b"\xa0\x00\x80\x00", offset+1)
            for idx, offset in enumerate(offsets):
                if idx != len(offsets)-1:
                    sz = offsets[idx+1] - offset
                    print(f"{idx=} {offset=:08X} {sz=:08X}")
                else:
                    print(f"{idx=} {offset=:08X}")

        if "cmd2" in cg_file.lower():
            with open(cg_file, 'rb') as f, open(f"{out_dir}/{prefix}cmd2.bin", 'wb') as f2:
                f.seek(86140)
                data = f.read(1152)
                f2.write(data)
                # szs = [4267,4336,3633+2848] # offsets: [87292, 91559, 95895, 99528, 102376]
                szs = [0x109f + 0xc, 0x10f0, 0x1951, 0x1820, 0x1602, 0x19ac, 0x1624, 0x1458, 0x167c, 0x1b00, 0x1874+0x411]
                for idx, sz in enumerate(szs):
                    print(f"{idx=} {sz=:08d} 0x{sz=:08X} offset=0x{f.tell():08X}")
                    data = f.read(sz)
                    color_index = []
                    if data[:3] == b"NPK":
                        width = int.from_bytes(data[0x0C:0x0E], LITTLE_ENDIAN)
                        height = int.from_bytes(data[0x0E:0x10], LITTLE_ENDIAN) 
                        color_indexes = unpack_npk(data[0x30:], width, height)
                    else:
                        width = int.from_bytes(data[0x00:0x02], LITTLE_ENDIAN)
                        height = int.from_bytes(data[0x02:0x04], LITTLE_ENDIAN) 
                        color_indexes = unpack_npk_3bits(data[4:], width, height)
                    image = Image.new("RGB", (width, height))
                    for px_index, color_index in enumerate(color_indexes):
                        y, x = divmod(px_index, width)
                        c = palette[color_index]
                        image.putpixel((x, y), c)
                    image.save(f"{out_dir}/cmd_{prefix}{idx:04d}.png")
                    print(f"save cmd {idx} image")
            # "cmd2" 目前到 0x02502f, 151599, 後面還有 162,372 bytes
                f.seek(0x02502f)
                data = f.read(1920)
                planar_image(data, 64, 80, palette).save(f"{out_dir}/cmd2kao.png")
                # f.seek(279604)
                f.seek(279603)
                data = f.read(1920*18-192)
                planar_image(data, 64, 1432, palette).save(f"{out_dir}/cmd2word.png")
            



def read_game_file(game_dir, name):
    """Read a game file whatever its case (DOS Mainpal.pld, PC-98 MAINPAL.PLD)."""
    for n in os.listdir(game_dir):
        if n.lower() == name.lower():
            with open(os.path.join(game_dir, n), "rb") as f:
                return f.read()
    raise FileNotFoundError(os.path.join(game_dir, name))


def planar_image(data, w, h, palette):
    """3bpp planar (byte k = bit k) image."""
    im = Image.new("RGB", (w, h))
    im.putdata([palette[c] for c in decode_planar(data, 0, w, h, 3)])
    return im


def rgba_image(px, w, h, palette):
    """Indexed pixels to RGBA, GENPEI_TRANSPARENT clear."""
    im = Image.new("RGBA", (w, h))
    im.putdata([(0, 0, 0, 0) if c == GENPEI_TRANSPARENT else (*palette[c], 255) for c in px])
    return im


@click.command(help="專屬頭像（Kaodata.gp）")
@click.option("--game-dir", "game_dir", required=True, help="遊戲目錄（DOS 或 PC-98）")
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
@click.option("--prefix", "prefix", default="", help="filename prefix of output files")
def genpei_face(game_dir, out_dir, prefix):
    """90 張 128×160 頭像，透明處輸出成 alpha 0；檔名後的 (x, y) 是遊戲內 64×80 頭像窗的左上角。

    dekoei.py genpei face --game-dir ../games/genpei-pc98 --out_dir ../games/genpei-pc98/extract/face
    """
    os.makedirs(out_dir, exist_ok=True)
    palette = load_mainpal(read_game_file(game_dir, "Mainpal.pld"))
    for i, (px, (x, y)) in enumerate(load_kaodata(read_game_file(game_dir, "Kaodata.gp"))):
        rgba_image(px, 128, 160, palette).save(f"{out_dir}/{prefix}{i:02d}_{x}_{y}.png")


@click.command(help="組合頭像零件（Montage.gp、Haikei.gp）")
@click.option("--game-dir", "game_dir", required=True, help="遊戲目錄（DOS 或 PC-98）")
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
@click.option("--prefix", "prefix", default="", help="filename prefix of output files")
def genpei_montage(game_dir, out_dir, prefix):
    """3 種類型 × 頭、身、眼、口的零件，檔名是 類型-部位-編號。

    dekoei.py genpei montage --game-dir ../games/genpei-pc98 --out_dir ../games/genpei-pc98/extract/montage
    """
    from kaodata_export import GENPEI_PART_COUNT, GENPEI_PC98_MONTAGE_TABLE
    os.makedirs(out_dir, exist_ok=True)
    palette = load_mainpal(read_game_file(game_dir, "Mainpal.pld"))
    exe = read_game_file(game_dir, "Main.exe")
    try:
        table = montage_types(unpack_main_exe(exe))
    except ValueError:  # the PC-98 Main.exe is not packed
        table = montage_types(exe, GENPEI_PC98_MONTAGE_TABLE)
    files = {}
    for t, layers in enumerate(table):
        for slot, count in GENPEI_PART_COUNT.items():
            src, off, w, h, _ = layers[slot]
            data = files.setdefault(src, read_game_file(game_dir, src))
            step = w * h * 3 // 8 + w * h // 8
            for i in range(count):
                px = masked_part(data, off + i * step, w, h)
                rgba_image(px, w, h, palette).save(f"{out_dir}/{prefix}{t + 1}-{slot}-{i:02d}.png")


genpei.add_command(genpei_cg, "cg")
genpei.add_command(genpei_face, "face")
genpei.add_command(genpei_montage, "montage")


# ---------------------------------------------------------------- face data
# Verified decoders for the portraits, ported from genpei-zh (tools/gfx.py,
# tools/dump_gfx.py, tools/unpack_exe.py, tools/dump_data.py). Format notes:
# notes/genpei.md. Use these instead of the planar order of utils.to_3bpp_indexes
# for this game.

GENPEI_TRANSPARENT = 255
SCENARIO_SIZE = 41266         # Sndata.gp: 4 scenarios
SCENARIO_HEADER = 0x26
GENERAL_SIZE = 71
N_GENERALS = 400
# Montage composition table: DGROUP:0x59CE = file 0x5C23E of the unpacked MZ,
# whose header is 0x53D0 bytes; offset below is into the expanded image.
MONTAGE_TABLE = 0x5C23E - 0x53D0
MONTAGE_TYPES = 3
HAIKEI_BG = (64, 80, 5)       # five 64x80 backgrounds at the start of Haikei.gp


def load_mainpal(data: bytes, index: int = 0) -> list[tuple[int, int, int]]:
    """Mainpal.pld: 48-byte sets of 16 colours, one 4-bit value per byte in B, R, G order."""
    pal = data[index * 48:(index + 1) * 48]
    return [(pal[i * 3 + 1] * 0x11, pal[i * 3 + 2] * 0x11, pal[i * 3] * 0x11) for i in range(16)]


def decode_planar(data: bytes, offset: int, w: int, h: int, planes: int) -> bytearray:
    """Byte-interleaved planes: every `planes` bytes hold 8 pixels, byte k = bit k, MSB leftmost."""
    out = bytearray(w * h)
    pos = offset
    for i in range(w * h // 8):
        for p in range(planes):
            b = data[pos + p]
            if b:
                for k in range(8):
                    if b & (0x80 >> k):
                        out[i * 8 + k] |= 1 << p
        pos += planes
    return out


def apply_mask(px: bytearray, data: bytes, offset: int) -> bytearray:
    """1bpp mask, MSB leftmost, bit 1 = transparent."""
    for i in range(len(px) // 8):
        b = data[offset + i]
        for k in range(8):
            if b & (0x80 >> k):
                px[i * 8 + k] = GENPEI_TRANSPARENT
    return px


def masked_part(data: bytes, offset: int, w: int, h: int) -> bytearray:
    """3bpp colour immediately followed by its 1bpp mask."""
    return apply_mask(decode_planar(data, offset, w, h, 3), data, offset + w * h * 3 // 8)


def read_rle3(data: bytes, pos: int) -> tuple[int, int, bytes, int]:
    """`u16 w, u16 h` + 3-bit RLE (same stream as utils.unpack_npk_3bits);
    returns (w, h, pixels, position after the stream)."""
    w, h = struct.unpack_from("<HH", data, pos)
    pos += 4
    dest = bytearray()
    while len(dest) < w * h:
        b = data[pos]
        pos += 1
        if b & 0x80:
            back = (((b >> 4) & 3) + 1) * (w if b & 0x40 else 4)
            for _ in range(((b & 0x0F) + 1) * 4):
                dest.append(dest[-back] if len(dest) >= back else 0)
        else:
            b1, b2 = b, data[pos]
            pos += 1
            quad = []
            for _ in range(4):
                quad.append(((b1 & 8) >> 1) | ((b2 & 0x80) >> 6) | ((b2 & 8) >> 3))
                b1 <<= 1
                b2 <<= 1
            dest.extend(quad * ((b >> 4) + 1))
    return w, h, bytes(dest[:w * h]), pos


def load_kaodata(data: bytes) -> list[tuple[bytes, tuple[int, int]]]:
    """Kaodata.gp: 90 x (128x160 face RLE3, 128x160 mask RLE3, u8 x, u8 y).
    Mask colour 7 = transparent; (x, y) = top-left of the 64x80 in-game window."""
    out, pos = [], 0
    while pos < len(data):
        _, _, face, pos = read_rle3(data, pos)
        _, _, mask, pos = read_rle3(data, pos)
        px = bytes(GENPEI_TRANSPARENT if m else v for v, m in zip(face, mask))
        out.append((px, (data[pos], data[pos + 1])))
        pos += 2
    return out


def unpack_main_exe(exe: bytes) -> bytes:
    """Expand the run-length packed Main.exe load image (relocations not applied).
    See genpei-zh tools/unpack_exe.py for the stub layout."""
    hdr = struct.unpack_from("<14H", exe, 0)
    image = exe[hdr[4] * 16:]
    cs = hdr[11]
    stub = image[cs * 16:]
    if stub[1:7] != bytes.fromhex("9c508cda5252"):
        raise ValueError("unknown packer stub")
    top = cs * 16 + struct.unpack_from("<H", stub, 0x10)[0] * 16
    out = bytearray(top)
    ctl, src, dst = 0x1977, cs * 16 - 11, top - 1
    for _ in range(struct.unpack_from("<H", stub, 0x2B)[0]):
        b0 = stub[ctl]
        lit = stub[ctl - 1]
        ctl -= 2
        if b0 & 1:
            lit = (lit << 8) | stub[ctl]
            ctl -= 1
        fill = b0 >> 2
        if b0 & 2:
            fill = (fill << 8) | stub[ctl]
            ctl -= 1
        value = stub[ctl]
        ctl -= 1
        for _ in range(lit):
            out[dst] = image[src]
            dst -= 1
            src -= 1
        for _ in range(fill):
            out[dst] = value
            dst -= 1
    if dst != -1:
        raise ValueError(f"expansion ended at {dst + 1:#x}, not at 0")
    return bytes(out)


def montage_types(image: bytes, table: int = MONTAGE_TABLE) -> list[dict]:
    """Composition table (at `table` in `image`), one entry per face type 1-3: per layer
    (file, offset, width, height, (x, y)) and the 64x80 window corner.
    Positions are in a 128x160 buffer of 16 bytes per row."""
    def xy(v):
        return v % 16 * 8, v // 16

    out = []
    for t in range(MONTAGE_TYPES):
        v = struct.unpack_from("<IIHH8H5H", image, table + t * 0x26)
        out.append(dict(
            head=("Montage.gp", v[0], v[4] * 8, v[5], xy(v[12])),
            body=("Montage.gp", v[1], v[6] * 8, v[7], xy(v[13])),
            eyes=("Haikei.gp", v[2], v[8] * 8, v[9], xy(v[14])),
            mouth=("Haikei.gp", v[3], v[10] * 8, v[11], xy(v[15])),
            window=xy(v[16])))
    return out


def load_backgrounds(haikei: bytes) -> list[bytearray]:
    w, h, n = HAIKEI_BG
    tex = decode_planar(haikei, 0, w, h * n, 3)
    return [tex[i * w * h:(i + 1) * w * h] for i in range(n)]


def load_generals(sndata: bytes, scenario: int = 0) -> list[dict]:
    """Sndata.gp generals: name (+0x00 surname, +0x0E given), half-width kana
    readings (+0x07, +0x13) and face code (+0x1A, u16; 0xFFFF = none)."""
    def sjis(b):
        return b.split(b"\0", 1)[0].decode("cp932").rstrip(" ")

    base = scenario * SCENARIO_SIZE + SCENARIO_HEADER
    out = []
    for i in range(N_GENERALS):
        g = sndata[base + i * GENERAL_SIZE:base + (i + 1) * GENERAL_SIZE]
        out.append(dict(id=i, surname=sjis(g[0:7]), surname_kana=sjis(g[7:14]),
                        given=sjis(g[14:19]), given_kana=sjis(g[19:26]),
                        face=struct.unpack_from("<H", g, 0x1A)[0]))
    return out
