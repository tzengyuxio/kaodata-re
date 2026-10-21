import struct
import click

from utils import (
    calc_part_size,
    color_codes_to_palette,
    create_floppy_image_stream,
    extract_images,
    load_person,
    print_table,
)
from san_person import S1Person, s1_format, s1_headers, s1_table_title


@click.group()
def san1():
    """三國志（初代）

    SAN_B/PICDATA.DAT

    dekoei.py san1 face -f kao/三國志b.fdi
    dekoei.py san1 face -f kao/SAN1_DOS_PICDATA.DAT
    """
    pass


@click.command(help="顏 CG 解析")
@click.option("-f", "--face", "face_file", help="頭像檔案", required=True)
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
@click.option("--prefix", "prefix", default="", help="filename prefix of output files")
def san1_face(face_file, out_dir, prefix):
    palette = color_codes_to_palette(["#000000", "#55FF55", "#FF5555", "#FFFF55"])
    face_w, face_h = 48, 80
    num_part = 114
    loader = None

    # PC98 floppy image as face_file
    if ".fdi" in face_file.lower():
        """PC98_SAN_B.FDI"""
        palette = color_codes_to_palette(
            [
                "#000000",
                "#00FF00",
                "#FF0000",
                "#FFFF00",
                "#0000FF",
                "#00FFFF",
                "#FF00FF",
                "#FFFFFF",
            ]
        )
        num_part = 113
        part_size = calc_part_size(face_w, face_h, len(palette), hh=True)
        offset_infos = [
            (15360, num_part * part_size)
        ]  # (offset, face_count * part_size)
        loader = create_floppy_image_stream(face_file, offset_infos, part_size)

    extract_images(
        face_file,
        face_w,
        face_h,
        palette,
        out_dir,
        prefix,
        num_part=num_part,
        hh=True,
        data_loader=loader,
    )


@click.command(help="人物資料解析")
@click.option("-f", "--file", "file", help="劇本檔案", required=True)
@click.option("-s", "--scenario", "scenario", help="劇本", default=0)
@click.option(
    "-t",
    "--to",
    "to",
    help="Specify output format",
    default="rich",
    type=click.Choice(["rich", "csv", "json", "markdown", "md"]),
)
def san1_person(file, scenario, to):
    """
    人物資料解析

    SINADATA.DAT

    ./dekoei.py san1 person -s 1 -f ~/dosbox/san1/SINADATA.DAT --to csv > PERSONS_TABLE/san1_persons_s1.csv
    """

    def person_loader(file, scenario=0):
        offsets = [4326, 16816, 29306, 41796, 54286]
        read_count, read_size = 255, struct.calcsize(s1_format)
        person_data = []
        with open(file, "rb") as f:
            f.seek(offsets[scenario])
            for _ in range(read_count):
                person_data.append(f.read(read_size))
        return person_data

    person_data = person_loader(file, scenario)

    persons = load_person(person_data, s1_format, S1Person)
    print_table(s1_table_title, s1_headers, persons, to)


san1.add_command(san1_face, "face")
san1.add_command(san1_person, "person")


# ---------------------------------------------------------------- PC-98 (Japanese, Ver 2.4), see notes/san1.md
# PICDATA.DAT: 48x40 half-height 3bpp faces, 18-byte rows (to_3bpp_indexes order), shown line-doubled
PC98_FACE = 720
PC98_FACE_ROWS = 40
# composite code 0xGTMB: group G (6-10) is the five faces at 6 * (G + 8); half-height rows of
# face T, M, B for the top / middle / bottom bands (DOS MAIN.EXE 0x467B)
PC98_BANDS = [(0, 15), (15, 25), (25, 40)]
# SAVEDATA: 10 x 30-byte slot headers, then 10 slots of 22904 bytes; slot 0 holds the person table
PC98_PERSONS = 300 + 0x1096
PC98_PERSON_SIZE = 34
# KOEI gaiji JIS 0x7620.. (glyphs in KANJIF.DAT at 0x4000 + 32 * k), read off the glyphs
PC98_GAIJI = ("袁焉瓚荀彧昱韋曄攸丕瑜翊苞沮郃譚煕蒯蔡瑁琦琮粲傕邕汜賈詡樊稠軫趙岑旻鄧璋沛璝懿龐褚繇糜邈鮑暹儁魏廖雍曠翔"
              "隲薛畯闞潘玠虔顗謖鞏聘歆閻傅逵沙闓禕譙楙姜淮毗琬郝")


def is_pc98_composite(code):
    return code >= 0x1000


def pc98_composite_group(code):
    """First PICDATA face of the composite group."""
    return 6 * ((code >> 12) + 8)


def pc98_composite_parts(code):
    return [code >> 8 & 15, code >> 4 & 15, code & 15]


def pc98_name(raw):
    """Little-endian JIS words; one record (夏侯尚) has bit 15 set on a character."""
    out = []
    for i in range(0, len(raw), 2):
        w = int.from_bytes(raw[i:i + 2], "little") & 0x7FFF
        if not w:
            break
        if 0x7620 <= w < 0x7620 + len(PC98_GAIJI):
            out.append(PC98_GAIJI[w - 0x7620])
        else:
            out.append(bytes([0x1B, 0x24, 0x42, w >> 8, w & 0xFF, 0x1B, 0x28, 0x42]).decode("iso2022_jp"))
    return "".join(out)


def load_san1_pc98_persons(savedata):
    """(face code, name) of the 255 persons in save slot 0 (the scenario files are encoded; face codes
    match every DOS scenario)."""
    with open(savedata, "rb") as f:
        data = f.read()
    persons = []
    for i in range(255):
        rec = data[PC98_PERSONS + i * PC98_PERSON_SIZE:PC98_PERSONS + (i + 1) * PC98_PERSON_SIZE]
        persons.append((int.from_bytes(rec[22:24], "little"), pc98_name(rec[8:14])))
    return persons


# Battle maps (same layout as FC): 58 provinces x 14 columns x 12 rows, one byte per cell row by row;
# bits 3-5 terrain 0-5, bits 0-2 deployment zone. Odd columns sit half a cell lower.
PC98_SLOT = 22904
PC98_BATTLE_MAPS = 300 + 0x3278
BATTLE_COLS, BATTLE_ROWS, BATTLE_MAPS = 14, 12, 58
# The 200-line screen draws each cell as a 32x16 block (SANMAIN.EXE 0x5D54 is the hex mask). The terrain
# graphics are not found in the files, so they are cut from NP2kai window captures (1280x864: 64-pixel title
# bar, every 200-line pixel drawn 2 wide and 4 high with a scanline gap).
BATTLE_CELL_W, BATTLE_CELL_H = 32, 16


def load_san1_pc98_battle_maps(savedata, slot=0):
    """58 maps of 168 cell bytes from a save slot (the scenario files are encoded)."""
    with open(savedata, "rb") as f:
        data = f.read()
    start = PC98_BATTLE_MAPS + slot * PC98_SLOT
    size = BATTLE_COLS * BATTLE_ROWS
    return [data[start + i * size:start + (i + 1) * size] for i in range(BATTLE_MAPS)]


def np2kai_capture_screen(path):
    """640x200 8-colour screen of an NP2kai window capture."""
    from PIL import Image
    src = Image.open(path).convert("RGB").load()
    screen = Image.new("RGB", (640, 200))
    screen.putdata([tuple(255 if v > 127 else 0 for v in src[2 * x + 1, 64 + 4 * y + 1])
                    for y in range(200) for x in range(640)])
    return screen


def battle_cell_box(col, row):
    x, y = col * BATTLE_CELL_W, row * BATTLE_CELL_H + (BATTLE_CELL_H // 2 if col % 2 else 0)
    return x, y, x + BATTLE_CELL_W, y + BATTLE_CELL_H


def battle_tiles(captures):
    """Terrain -> 32x16 tile: the most common cell image of each terrain over the captured battles
    [(screen, map cells)]; cells under units or the cursor are outvoted."""
    from collections import Counter, defaultdict
    from PIL import Image
    votes = defaultdict(Counter)
    for screen, cells in captures:
        for col in range(BATTLE_COLS):
            for row in range(BATTLE_ROWS):
                votes[cells[row * BATTLE_COLS + col] >> 3 & 7][screen.crop(battle_cell_box(col, row)).tobytes()] += 1
    return {t: Image.frombytes("RGB", (BATTLE_CELL_W, BATTLE_CELL_H), v.most_common(1)[0][0]) for t, v in votes.items()}


def render_battle_map(cells, tiles):
    """448x400 image of one map (200-line screen, line-doubled)."""
    from PIL import Image
    w, h = BATTLE_COLS * BATTLE_CELL_W, BATTLE_ROWS * BATTLE_CELL_H + BATTLE_CELL_H // 2
    im = Image.new("RGB", (w, h))
    for col in range(BATTLE_COLS):
        for row in range(BATTLE_ROWS):
            im.paste(tiles[cells[row * BATTLE_COLS + col] >> 3 & 7], battle_cell_box(col, row)[:2])
    return im.resize((w, h * 2), Image.NEAREST)


@click.command(help="戰場地圖（PC-98）")
@click.option("--savedata", required=True, help="SAVEDATA（讀第 0 槽）")
@click.option("--capture", "captures", multiple=True, required=True,
              help="NP2kai 戰場截圖:國號，例 battle-04.png:4；要涵蓋 6 種地形")
@click.option("--out", "out_dir", required=True, help="輸出目錄")
def san1_battlemap(savedata, captures, out_dir):
    """
    dekoei.py san1 battlemap --savedata ../games/san1-pc98/SAVEDATA \\
        --capture ../captures/screenshots/san1-pc98/battle-04.png:4 \\
        --capture ../captures/screenshots/san1-pc98/battle-10.png:10 --out ../games/san1-pc98/extract/battlemap
    """
    import os
    maps = load_san1_pc98_battle_maps(savedata)
    shots = []
    for c in captures:
        path, n = c.rsplit(":", 1)
        shots.append((np2kai_capture_screen(path), maps[int(n) - 1]))
    tiles = battle_tiles(shots)
    missing = [t for t in range(6) if t not in tiles]
    if missing:
        raise click.UsageError(f"截圖沒有地形 {missing}")
    os.makedirs(out_dir, exist_ok=True)
    for i, cells in enumerate(maps):
        render_battle_map(cells, tiles).save(os.path.join(out_dir, f"{i + 1:02d}.png"))
    from PIL import Image
    sheet = Image.new("RGB", (6 * (BATTLE_CELL_W + 4), BATTLE_CELL_H * 2))
    for t in range(6):
        sheet.paste(tiles[t].resize((BATTLE_CELL_W, BATTLE_CELL_H * 2), Image.NEAREST), (t * (BATTLE_CELL_W + 4), 0))
    sheet.save(os.path.join(out_dir, "terrain.png"))


san1.add_command(san1_battlemap, "battlemap")


# X68000 SAVEDATA (Disk B, all 10 slots the factory start): slot 0's table at 0x1E42 is an extra copy of 曹操,
# then the 255 persons, 44 bytes each: +0 reading, +8 name (3 big-endian 32-bit JIS codes), +28 u32 face code
X68_PERSONS = 0x1E42 + 44
X68_PERSON_SIZE = 44


def load_san1_x68_persons(savedata):
    """(face code, name) of the 255 persons of the X68000 SAVEDATA, in the PC-98 order."""
    with open(savedata, "rb") as f:
        data = f.read()
    persons = []
    for i in range(255):
        rec = data[X68_PERSONS + i * X68_PERSON_SIZE:][:X68_PERSON_SIZE]
        name = b"".join(rec[k + 2:k + 4][::-1] for k in range(8, 20, 4))
        persons.append((int.from_bytes(rec[28:32], "big"), pc98_name(name)))
    return persons


# ---------------------------------------------------------------- PC-88 V1 (Ver.1.1), see notes/san1.md
# Disk B is read by track: face code n is slot n % 5 of track n // 5 (5 PC-98-format faces per 4 KB track);
# composite group G is track G, its parts slots 0-4; daughters fill tracks 40-43 (16 faces)
PC88_FACES_PER_TRACK = 5
PC88_DAUGHTER_TRACK = 40
PC88_DAUGHTERS = 16
# SN1.EXT: 34-byte records as in the PC-98 SAVEDATA; the first record is an extra copy of 曹操
PC88_PERSONS = 0x104D + PC98_PERSON_SIZE


def pc88_face(disk_b, track, slot):
    """720-byte PICDATA-format face from the linear disk B image."""
    start = track * 4096 + slot * PC98_FACE
    return disk_b[start:start + PC98_FACE]


def pc88_face_by_code(disk_b, code):
    return pc88_face(disk_b, code // PC88_FACES_PER_TRACK, code % PC88_FACES_PER_TRACK)


def load_san1_pc88_persons(sn1):
    """(face code, name) of the 255 persons of SN1.EXT; bit 7 of some name bytes is a flag."""
    persons = []
    for i in range(255):
        rec = sn1[PC88_PERSONS + i * PC98_PERSON_SIZE:PC88_PERSONS + (i + 1) * PC98_PERSON_SIZE]
        persons.append((int.from_bytes(rec[22:24], "little"), pc98_name(bytes(c & 0x7F for c in rec[8:14]))))
    return persons


# ---------------------------------------------------------------- DOS (English), see notes/san1.md
# PICDATA.DAT: 48x40 half-height 2bpp faces (to_2bpp_indexes order), same face order and composite rule as PC-98
DOS_FACE = 480
# SINADATA.DAT: 5 scenarios of 255 x 32-byte records (s1_format); face codes are the same in every scenario
DOS_PERSONS = 4326


def load_san1_dos_persons(sinadata):
    """(face code, name) of the 255 persons in scenario 1."""
    with open(sinadata, "rb") as f:
        data = f.read()
    persons = []
    for i in range(255):
        rec = data[DOS_PERSONS + i * 32:DOS_PERSONS + (i + 1) * 32]
        persons.append((int.from_bytes(rec[20:22], "little"), rec[:12].split(b"\0", 1)[0].decode("ascii")))
    return persons
