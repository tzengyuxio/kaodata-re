import struct
import click
from PIL import Image

from utils import (
    color_codes_to_palette,
    extract_images,
    load_person,
    print_table,
    output_images,
)
from san_person import (
    S3Person,
    s3_format,
    s3_headers,
    s3_table_title,
)


def person_loader(file):
    read_count, read_size = 600, struct.calcsize(s3_format)
    person_data = []
    with open(file, "rb") as f:
        for _ in range(read_count):
            pd = f.read(read_size)
            if pd[43:] == b"\x00\x00\x00\x00\x00\x00":
                continue
            person_data.append(pd)
    return person_data


def load_san3_persons(file) -> list[S3Person]:
    return load_person(person_loader(file), s3_format, S3Person)


# MONTAGE.DAT (DOS): 11 heads x 0x3180 bytes; tables from MAIN.EXE (see notes/san3.md)
MONTAGE_HEAD_SIZE = 0x3180
# (offset in head block, bytes per record, offset in the 1920-byte face buffer) per area
MONTAGE_AREAS = [(0, 864, 0), (3456, 1056, 864), (7680, 384, 504), (9984, 384, 792), (10752, 480, 1080)]
MONTAGE_RECORDS = [4, 4, 6, 2, 4]
MONTAGE_FIELDS = [(3, 3), (5, 3), (7, 7), (10, 1), (11, 3)]  # (shift, mask) of each area in the face code


def is_montage_code(code):
    return bool(code & 0x8000)


def montage_head(code):
    """Head block index: bits 0-2, plus 7 when bit 14 is set (the second bank starts at 7 heads)."""
    return (7 if code & 0x4000 else 0) + (code & 7)


def montage_parts(code):
    return [code >> s & m for s, m in MONTAGE_FIELDS]


def montage_record(data, head, area, record):
    offset, size, _ = MONTAGE_AREAS[area]
    start = head * MONTAGE_HEAD_SIZE + offset + record * size
    return data[start:start + size]


# PC-98 (Japanese) SNDATA?B.CIM: 600 records x 62 bytes; face code at +2, Shift-JIS name at +0x31 (6 bytes)
PC98_RECORD_SIZE = 62
# gaiji: MAIN.EXE DGROUP 0x1C62 lists the JIS code of each FONT.DAT glyph; characters read off the glyphs
PC98_GAIJI_JIS = [0x7621, 0x7622, 0x7623, 0x7624, 0x7625, 0x7626, 0x7627, 0x7628, 0x7629, 0x762A, 0x762B, 0x762D,
                  0x762E, 0x762F, 0x7630, 0x7631, 0x7632, 0x7633, 0x7634, 0x7635, 0x7636, 0x7637, 0x7638, 0x7639,
                  0x763A, 0x763B, 0x763C, 0x763D, 0x763E, 0x7641, 0x7642, 0x7646, 0x7648, 0x7649, 0x764A, 0x764B,
                  0x764E, 0x7650, 0x7652, 0x7653, 0x7654, 0x7655, 0x7656, 0x7657, 0x7658, 0x7659, 0x765A, 0x765B]
PC98_GAIJI_CHARS = "瓚昱彧郃蒯蔡傕邕汜詡鄧龐繇邈騭畯闞玠顗邢歆闓禕譙琬郝琮伷褚邳琦璝彤琬釭涪鄴臧莒綝諶惲昕琪笮祜蕤璜"


def jis_to_sjis(code):
    j1, j2 = code >> 8, code & 0xFF
    s1 = ((j1 + 1) >> 1) + (0x70 if j1 < 0x5F else 0xB0)
    s2 = j2 + (0x1F + (j2 >= 0x60) if j1 & 1 else 0x7E)
    return bytes([s1, s2])


PC98_GAIJI = {jis_to_sjis(j): c for j, c in zip(PC98_GAIJI_JIS, PC98_GAIJI_CHARS)}


def decode_pc98_name(raw):
    raw = raw.split(b"\0", 1)[0]
    out, i = [], 0
    while i < len(raw):
        n = 2 if 0x81 <= raw[i] <= 0x9F or 0xE0 <= raw[i] <= 0xFC else 1
        out.append(PC98_GAIJI.get(raw[i:i + n]) or raw[i:i + n].decode("cp932"))
        i += n
    return "".join(out)


def load_san3_pc98_persons(file):
    """(face code, name) of every used record."""
    with open(file, "rb") as f:
        data = f.read()
    persons = []
    for i in range(600):
        rec = data[i * PC98_RECORD_SIZE:(i + 1) * PC98_RECORD_SIZE]
        if rec[0x31:0x37] != bytes(6):
            persons.append((struct.unpack_from("<H", rec, 2)[0], decode_pc98_name(rec[0x31:0x37])))
    return persons


# X68000 SNDATA?.CIM (MAIN.Z 0x15136): MSB-first bits; u8, u8 fill byte, u32 LE size, then for each byte
# a 1 bit (the fill byte) or a 0 bit and 8 bits. Unpacked, the same 600 records as the PC-98 SNDATA?B.CIM,
# with 68000 padding: 72 bytes each from 0x1B72, face code big-endian at +2, name at +0x39
X68_PEOPLE = 0x1B72
X68_RECORD_SIZE = 72


def unpack_x68_sndata(data):
    pos = 0

    def bits(n):
        nonlocal pos
        v = 0
        for _ in range(n):
            v = v << 1 | (data[pos >> 3] >> (7 - (pos & 7)) & 1)
            pos += 1
        return v

    bits(8)
    fill = bits(8)
    size = sum(bits(8) << (8 * k) for k in range(4))
    return bytes(fill if bits(1) else bits(8) for _ in range(size))


def load_san3_x68_persons(file):
    """(face code, name) of every used record of an X68000 SNDATA?.CIM."""
    with open(file, "rb") as f:
        data = unpack_x68_sndata(f.read())
    persons = []
    for i in range(600):
        rec = data[X68_PEOPLE + i * X68_RECORD_SIZE:][:X68_RECORD_SIZE]
        if rec[0x39:0x3F] != bytes(6):
            persons.append((struct.unpack_from(">H", rec, 2)[0], decode_pc98_name(rec[0x39:0x3F])))
    return persons


# Windows (Steam) SCEDATA?.S3: the PC-98 records from 0x46B; the face code is the 1-based cell of FACES.BMP
# (12 x 52 cells of 64x80; 1-307 the PC-98 faces repainted, 313-623 the composites drawn whole).
# S3GAIJI.TTE (Shift-JIS F040-) has the PC-98 FONT.DAT glyphs in JIS order 0x7621-, plus 0x765C 毌, 0x765D 晙
WIN_PEOPLE = 0x46B
WIN_GAIJI = {**dict(zip(PC98_GAIJI_JIS, PC98_GAIJI_CHARS)), 0x765C: "毌", 0x765D: "晙"}


def decode_win_name(raw):
    raw = raw.split(b"\0", 1)[0]
    out, i = [], 0
    while i < len(raw):
        n = 2 if 0x81 <= raw[i] <= 0x9F or 0xE0 <= raw[i] <= 0xFC else 1
        if raw[i] == 0xF0:
            low = raw[i + 1]
            out.append(WIN_GAIJI[0x7621 + low - 0x40 - (low > 0x7F)])
        else:
            out.append(raw[i:i + n].decode("cp932"))
        i += n
    return "".join(out)


def load_san3_win_persons(file):
    """(face code, name) of every used record of a Windows SCEDATA?.S3."""
    with open(file, "rb") as f:
        data = f.read()
    persons = []
    for i in range(600):
        rec = data[WIN_PEOPLE + i * PC98_RECORD_SIZE:][:PC98_RECORD_SIZE]
        if rec[0x31:0x37] != bytes(6):
            persons.append((struct.unpack_from("<H", rec, 2)[0], decode_win_name(rec[0x31:0x37])))
    return persons



@click.group()
def san3():
    """三國志III

    NBDATA.DAT      新武將
    SANGOKU3.SAV    存檔

    dekoei.py san3 face -f kao/SAN3_KAODATA.DAT --out_dir SAN3_DOS --prefix "SAN3_DOS_F"
    dekoei.py san3 face -f kao/SAN3_FACES.BMP --out_dir SAN3_WIN --prefix "SAN3_WIN_F"
    """
    pass


@click.command(help="顏 CG 解析")
@click.option("-f", "--face", "face_file", help="頭像檔案", required=True)
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
@click.option("--prefix", "prefix", default="", help="filename prefix of output files")
def san3_face(face_file, out_dir, prefix):
    """
    KAODATA.DAT (DOS)
    FACES.BMP (WIN, STEAM), 專用顏307, 大眾臉311
    """
    if "faces.bmp" in face_file.lower():
        facebmp = Image.open(face_file)
        skips = [307, 308, 309, 310, 311, 623]
        w, h, num_col = 64, 80, 12
        num_faces = (facebmp.width // 64) * (facebmp.height // 80)
        face_images = dict()
        for i in range(num_faces):
            if i in skips:
                continue
            face = facebmp.crop(
                (
                    i % num_col * w,
                    i // num_col * h,
                    (i % num_col + 1) * w,
                    (i // num_col + 1) * h,
                )
            )
            face_images[str(i)] = face
        output_images(face_images, out_dir, prefix)
        # output_images(list(face_images.values())[:307], out_dir, prefix+'_A')  # 專用顏
        # output_images(list(face_images.values())[307:], out_dir, prefix+'_B')  # 大眾臉
        return

    # for KAODATA.DAT (DOS)
    palette = color_codes_to_palette(
        [
            "#000000",
            "#10B251",
            "#F35100",
            "#F3E300",
            "#0041F3",
            "#00C3F3",
            "#F351D3",
            "#F3F3F3",
        ]
    )
    face_w, face_h = 64, 80

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix)


@click.command(help="人物資料解析")
@click.option("-f", "--file", "file", help="劇本檔案", required=True)
@click.option(
    "--to",
    "to",
    help="Specify output format",
    default="rich",
    type=click.Choice(["rich", "csv", "json", "markdown", "md"]),
)
def san3_person(file, to):
    """
    人物資料解析

    SNDATA1B.CIM

    ./dekoei.py san3 person -f ~/dosbox/SAN3/SNDATA1B.CIM --to csv > PERSONS_TABLE/san3_persons_s1.csv
    ./dekoei.py san3 person -f ~/dosbox/SAN3/SNDATA6B.CIM --to csv > PERSONS_TABLE/san3_persons_s6.csv
    """

    persons = load_san3_persons(file)
    print_table(s3_table_title, s3_headers, persons, to)


# PC-98 battle maps (see notes/san3.md): HEXDATA.DAT holds three 68 x 440-byte layers
# (22 x 20 cells) and 68 x 22 bytes; layer 0 is the tile number of each cell.
BATTLE_COLS, BATTLE_ROWS, BATTLE_MAPS = 22, 20, 68
BATTLE_LAYER = BATTLE_COLS * BATTLE_ROWS
# HEXGRP.DAT tile sets (offset, tiles) of 24x20 3-plane tiles, 180 bytes each
BATTLE_TILESETS = [(0, 228), (41040, 219), (80460, 124)]
# tile set of each map; the game fills this table at run time, so it was picked by eye
BATTLE_MAP_TILESET = [0] * 46 + [1] * 7 + [2] + [1] * 14
PC98_PALETTE = ["#000000", "#0044FF", "#FF5500", "#FF55DD", "#11BB55", "#00CCFF", "#FFEE00", "#FFFFFF"]


def battle_tile(data, palette):
    """24x20 tile, each 8 px as 3 bytes with byte k = colour bit k."""
    im = Image.new("RGB", (24, 20))
    im.putdata([palette[sum(((data[(y * 3 + x // 8) * 3 + p] >> (7 - x % 8)) & 1) << p for p in range(3))]
                for y in range(20) for x in range(24)])
    return im


def render_san3_battle_maps(game_dir):
    palette = color_codes_to_palette(PC98_PALETTE)
    with open(f"{game_dir}/HEXGRP.DAT", "rb") as f:
        grp = f.read()
    with open(f"{game_dir}/HEXDATA.DAT", "rb") as f:
        hexdata = f.read()
    tilesets = [[battle_tile(grp[off + 180 * t:off + 180 * (t + 1)], palette) for t in range(n)]
                for off, n in BATTLE_TILESETS]
    maps = []
    for k in range(BATTLE_MAPS):
        cells = hexdata[BATTLE_LAYER * k:BATTLE_LAYER * (k + 1)]
        tiles = tilesets[BATTLE_MAP_TILESET[k]]
        im = Image.new("RGB", (BATTLE_COLS * 24, BATTLE_ROWS * 20))
        for row in range(BATTLE_ROWS):
            for col in range(BATTLE_COLS):
                if col % 2 and row == BATTLE_ROWS - 1:
                    continue  # the game skips the last cell of odd columns
                im.paste(tiles[cells[row * BATTLE_COLS + col]], (col * 24, row * 20 + 10 * (col % 2)))
        maps.append(im)
    return maps


# PC-98 main map (see notes/san-maps.md): MAPDATA.DAT is three compressed bands (MAIN.EXE image 0x464E reads
# 0x7C72, 0x9ACC, 0x6C1C bytes; 0x1E0F decodes) stacked into one 640 x 400 screen. Palette: entries 0-7 at
# DGROUP 0x2A3A, entries 8-15 per season (month // 3) from DGROUP 0x1AE6 + 24 * season, 3 bytes B, R, G.
WORLD_BANDS = [0x7C72, 0x9ACC, 0x6C1C]
WORLD_W, WORLD_H = 640, 400
WORLD_DGROUP = 0x8C00 + 0x4B200  # MAIN.EXE file offset of DGROUP
WORLD_PALETTE, WORLD_SEASONS = 0x2A3A, 0x1AE6


def world_band(data):
    """One band: u16 width (bit 15 ignored), u16 height, 8 u16 colour words, then codes. A unit is 4 pixels,
    one 16-bit word holding 4 bits of each plane (plane k in bits 4k-4k+3, the high bit is the left pixel)."""
    w, h = struct.unpack_from("<HH", data)
    w &= 0x7FFF
    table = struct.unpack_from("<8H", data, 4)
    units, pos = (w + 3) // 4, 20
    out = [0] * (units * h + 16)  # a run may overshoot the last row

    def byte():
        nonlocal pos
        pos += 1
        return data[pos - 1]

    for row in range(h):
        di, left = row * units, units
        while left > 0:
            c = byte()
            if c & 0x80:  # copy n units from k units back in this row, or from k rows up
                n, k = (c & 0xF) + 1, ((c >> 4) & 3) + 1
                src = di - k * (units if c & 0x40 else 1)
                for i in range(n):
                    out[di + i] = out[src + i]
            else:
                n, a = (c & 7) + 1, c & 0x78
                if a == 0:
                    v = 0
                elif a & 0x40:
                    v = table[(c >> 3) & 7]
                elif a == 0x38:
                    v = byte() << 8
                    v |= byte()
                else:
                    b = byte()
                    v = [b, (b & 0xF) | (b & 0xF0) << 4, (b & 0xF0) << 8 | (b & 0xF), b << 4,
                         (b & 0xF0) << 8 | (b & 0xF) << 4, b << 8][(a - 8) >> 3]
                for i in range(n):
                    out[di + i] = v
            di, left = di + n, left - n
    px = bytearray(units * 4 * h)
    for i, v in enumerate(out[:units * h]):
        for j in range(4):
            px[i * 4 + j] = sum(((v >> (4 * k + 3 - j)) & 1) << k for k in range(4))
    return Image.frombytes("P", (units * 4, h), bytes(px)).crop((0, 0, w, h))


def render_san3_world_map(game_dir, season=0):
    with open(f"{game_dir}/MAPDATA.DAT", "rb") as f:
        data = f.read()
    with open(f"{game_dir}/MAIN.EXE", "rb") as f:
        exe = f.read()
    im, y, off = Image.new("P", (WORLD_W, WORLD_H)), 0, 0
    for n in WORLD_BANDS:
        band = world_band(data[off:off + n])
        im.paste(band, (0, y))
        y, off = y + band.height, off + n
    raw = exe[WORLD_DGROUP + WORLD_PALETTE:][:24] + exe[WORLD_DGROUP + WORLD_SEASONS + 24 * season:][:24]
    im.putpalette([17 * raw[3 * i + k] for i in range(16) for k in (1, 2, 0)])
    return im


@click.command(help="戰場地圖（PC-98）")
@click.option("--game-dir", "game_dir", required=True, help="遊戲目錄")
@click.option("--out", "out_dir", required=True, help="輸出目錄")
def san3_battlemap(game_dir, out_dir):
    """
    dekoei.py san3 battlemap --game-dir ../games/san3-pc98 --out ../games/san3-pc98/extract/battlemap
    """
    import os
    os.makedirs(out_dir, exist_ok=True)
    for k, im in enumerate(render_san3_battle_maps(game_dir)):
        im.save(f"{out_dir}/{k + 1:02d}.png")


san3.add_command(san3_face, "face")
san3.add_command(san3_person, "person")
san3.add_command(san3_battlemap, "battlemap")
