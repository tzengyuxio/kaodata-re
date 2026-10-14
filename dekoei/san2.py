import io
import os
import struct
import click
from PIL import Image

from utils import (
    BGCOLOR,
    LITTLE_ENDIAN,
    calc_part_size,
    color_codes_to_palette,
    create_floppy_image_stream,
    data_to_image,
    extract_images,
    load_images_with_data,
    load_person,
    output_images,
    print_table,
    save_index_image,
    save_single_images,
    unpack_npk_3bits,
)
from san_person import (
    S2Person,
    s2_format,
    s2_format_taiki,
    s2_headers,
    s2_table_title,
)

san2_face_palette = color_codes_to_palette(
    [
        "#000000",
        "#55FF55",
        "#FF5555",
        "#FFFF55",
        "#5555FF",
        "#55FFFF",
        "#FF55FF",
        "#FFFFFF",
    ]
)


@click.group()
def san2():
    """三國志II

    KAODATA.DAT

    dekoei.py san2 face -f kao/SAN2_DOS_KAODATA.DAT
    dekoei.py san2 face -f kao/SAN2_PC98_三國志2_b.fdi
    dekoei.py san2 face -f kao/SAN2_WIN_FACE01.SN2 --out_dir _outdir_san2win --prefix SAN2_WIN_F
    """
    pass


@click.command(help="顏 CG 解析")
@click.option("-f", "--face", "face_file", help="頭像檔案", required=True)
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
@click.option("--prefix", "prefix", default="", help="filename prefix of output files")
def san2_face(face_file, out_dir, prefix):
    palette = color_codes_to_palette(
        [
            "#000000",
            "#55FF55",
            "#FF5555",
            "#FFFF55",
            "#5555FF",
            "#55FFFF",
            "#FF55FF",
            "#FFFFFF",
        ]
    )
    face_w, face_h = 64, 80
    hh = True
    loader = None

    # PC98 floppy image as face_file
    if ".fdi" in face_file.lower():
        """PC98_SAN2_B.FDI"""
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
        hh = False
        # NOTE: 在第二組 offset_info 之後還有 52 個 face 大小的 montage 資料
        part_size = calc_part_size(face_w, face_h, len(palette), hh=hh)
        # 371840 = 189440 + 95 * part_size
        offset_infos = [
            (189440, 95 * part_size),
            (371840 + 896, 124 * part_size),
        ]  # (offset, face_count * part_size)
        loader = create_floppy_image_stream(face_file, offset_infos, part_size)
    elif ".hdm" in face_file.lower():
        """X68_SAN2_C.HDM"""
        palette = color_codes_to_palette(
            [
                "#000000",
                "#00E700",
                "#E70000",
                "#E7E700",
                "#0000E7",
                "#00E7E7",
                "#E700E7",
                "#E7E7E7",
            ]
        )
        hh = False
        # 211072 = 28672 + 95 * part_size
        # 396288 = (211072+896) + 95 * part_size
        part_size = calc_part_size(face_w, face_h, len(palette), hh=hh)
        offset_infos = [
            (28672, 95 * part_size),
            (211072 + 896, 96 * part_size),
            (396288 + 896 + 128, 28 * part_size),
        ]  # (offset, face_count * part_size)
        # NOTE: 在第三組 offset_info 之後還有 60 個 face 大小的 montage 資料
        loader = create_floppy_image_stream(face_file, offset_infos, part_size)
    elif ".sn2" in face_file.lower():
        """FACE01.SN2, FACE02.SAN2"""
        bmp_size = 6198
        images = []
        files = [face_file]
        files.append(face_file.replace("FACE01", "FACE02"))
        for f in files:
            with open(f, "rb") as f:
                data = f.read(bmp_size)
                while data:
                    img = Image.open(io.BytesIO(data))
                    images.append(img)
                    data = f.read(bmp_size)
        # save face index: all, special, mob
        save_index_image(images[1:], 64, 80, 16, f"{out_dir}/{prefix}00-INDEX.png")
        save_index_image(
            images[1:220], 64, 80, 16, f"{out_dir}/{prefix}00-INDEX_KAO.png"
        )
        save_index_image(
            images[220:], 64, 80, 16, f"{out_dir}/{prefix}00-INDEX_MOB.png"
        )
        # save single faces
        for idx, img in enumerate(images[1:]):
            filename = f"{out_dir}/{prefix}{idx:04d}.png"
            img.save(filename)
        return

    extract_images(
        face_file, face_w, face_h, palette, out_dir, prefix, hh=hh, data_loader=loader
    )


def person_loader(file, taiki_file):
    """Raw person records (taiki layout): scenarios 1-6, then TAIKI, deduplicated by face code."""
    offsets = [
        0x0,
        0x33AF,
        0x675E,
        0x9B0D,
        0xCEBC,
        0x1026B,
    ]  # size=0x33af per scenario
    read_count, read_size = 215, struct.calcsize(s2_format)  # count=215
    tf_read_count, tf_read_size = 420, struct.calcsize(s2_format_taiki)  # count=420
    person_data = []
    kaos = set()  # 用來過濾重複
    with open(file, "rb") as f, open(taiki_file, "rb") as tf:
        for offset in offsets:
            f.seek(offset + 0x16)
            for _ in range(read_count):
                pd = f.read(read_size)
                if pd[26:28] in kaos:  # [26:28]
                    continue
                if pd[28:32] == b"\x00\x00\x00\x00":
                    break
                person_data.append(b"".join([b"\xFF\xFF\xFF", pd]))
                kaos.add(pd[26:28])
        tf.seek(0x6)
        for _ in range(tf_read_count):
            pd = tf.read(tf_read_size)
            if pd[29:31] in kaos:  # [29:31]
                continue
            if pd[31:35] == b"\x00\x00\x00\x00":
                break
            person_data.append(pd)
            kaos.add(pd[29:31])
    return person_data


def load_san2_persons(file, taiki_file) -> list[S2Person]:
    return load_person(person_loader(file, taiki_file), s2_format_taiki, S2Person)


@click.command(help="人物資料解析")
@click.option("-f", "--file", "file", help="劇本檔案", required=True)
@click.option("-t", "--taiki-file", "taiki_file", help="待機檔案", required=True)
@click.option(
    "--to",
    "to",
    help="Specify output format",
    default="rich",
    type=click.Choice(["rich", "csv", "json", "markdown", "md"]),
)
def san2_person(file, taiki_file, to):
    """
    人物資料解析

    dekoei.py san2 person -f ~/dosbox/SAN2/SCENARIO.DAT -t ~/DOSBox/san2/TAIKI.DAT
    """
    persons = load_san2_persons(file, taiki_file)
    print_table(s2_table_title, s2_headers, persons, to)


@click.command(help="地圖資料解析")
@click.option("--game_dir", "game_dir", default="san2", help="game directory")
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
def san2_map(game_dir, out_dir):
    palette = color_codes_to_palette(
        [
            "#000000",
            "#55FF55",
            "#FF5555",
            "#FFFF55",
            "#5555FF",
            "#55FFFF",
            "#FF55FF",
            "#FFFFFF",
        ]
    )
    hex_file = f"{game_dir}/HEXDATA.DAT"
    hex_file = os.path.expanduser(hex_file)
    map_size = 12 * 13
    total_map_size = map_size * 41
    terrain_type_count = 7  # 平原 森林 丘陵 高山 水域 營寨 城池
    terrain_cg_size = int(32 * 16 / 8 * 3)  # 192
    with open(hex_file, "rb") as f:
        f.seek(total_map_size * 2)
        data = f.read(terrain_cg_size * terrain_type_count)
        images = load_images_with_data(
            data, 32, 32, palette, True, terrain_cg_size, terrain_type_count
        )
        output_images(images, out_dir, "")


@click.command(help="其他資料解析")
@click.option("--game_dir", "game_dir", default="san2", help="game directory")
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
def san2_grp(game_dir, out_dir):
    """
    1) 640 x 200 劇本選擇圖
    2) 296 x 200 大地圖
    3) 344 x 200 右半邊框
    4) 336 x   3 分隔線
    5)  80 x  56 圖框
    6) 128 x  64 外交事件
    7) 128 x  64 信件攔截事件
    """
    palette = color_codes_to_palette(
        [
            "#000000",
            "#55FF55",
            "#FF5555",
            "#FFFF55",
            "#5555FF",
            "#55FFFF",
            "#FF55FF",
            "#FFFFFF",
        ]
    )
    grp_file = f"{game_dir}/GRPDATA.DAT"
    grp_file = os.path.expanduser(grp_file)
    images = []
    with open(grp_file, "rb") as f:
        offset_info = [
            (0, 14254),
            (14254, 11012),
            (25266, 1695),
            (26961, 25),
            (26986, 174),
            (27160, 2311),
            (29471, 14232),
        ]
        for offset, size in offset_info:
            f.seek(offset)
            data = f.read(size)
            w = int.from_bytes(data[0:2], LITTLE_ENDIAN)
            h = int.from_bytes(data[2:4], LITTLE_ENDIAN)
            print(w, h)
            color_indexes = unpack_npk_3bits(data[4:], w, h)
            image = Image.new("RGB", (w, h), BGCOLOR)
            for px_index, color_index in enumerate(color_indexes):
                y, x = divmod(px_index, w)
                c = palette[color_index]
                image.putpixel((x, y), c)
            images.append(image)
    images = (
        {str(i): img for i, img in enumerate(images)}
        if isinstance(images, list)
        else images
    )
    save_single_images(images, out_dir, "")


@click.command(help="其他資料解析")
@click.option("--game_dir", "game_dir", default="san2", help="game directory")
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
@click.option("--prefix", "prefix", default="", help="filename prefix of output files")
def san2_grpa(game_dir, out_dir, prefix):
    os.makedirs(out_dir, exist_ok=True)
    palette = color_codes_to_palette(
        [
            "#000000",
            "#5555FF",
            "#FF5555",
            "#FF55FF",
            "#55FF55",
            "#55FFFF",
            "#FFFF55",
            "#FFFFFF",
        ]
    )
    # file size 46715
    # 30 張圖 45851
    # left: 864 bytes, 箭頭, 6 方向 6 張，每張 144, 寬 24, 高可能為 16(hh, 32)
    # 風向箭頭
    # 目前未知: 馬, 戰爭圖
    grp_file = f"{game_dir}/GRPDATA.DAT"
    # grp_file = f"{game_dir}/PACKDATA.DAT"
    grp_file = os.path.expanduser(grp_file)
    images = []
    offsets = []
    with open(grp_file, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        next_offset = 0
        # i = 0
        # while i < 1:
        while True:
            # i += 1
            offset = next_offset
            f.seek(offset)
            dest = bytearray()
            w = int.from_bytes(f.read(2), LITTLE_ENDIAN)
            h = int.from_bytes(f.read(2), LITTLE_ENDIAN)
            if w == 0 or h == 0:
                print(f"OUT OF RANGE: {w=} {h=} pos:{offset=}")
                f.seek(f.tell()-4)
                break
            dest_len = w * h
            while f.tell() < file_size and len(dest) < dest_len:
                b = f.read(1)[0]
                if b & 0x80:
                    run_size = (b & 0x0F) + 1  # info.len
                    run_offset = ((b & 0x30) >> 4) + 1  # info.range
                    run_offset = run_offset * w if (b & 0x40) else run_offset * 4
                    for _ in range(run_size * 4):
                        dest.append(dest[-run_offset])
                    # print(f'{data.tell(): 6d} type: {b:08b}, dir: {b & 0x40}, offset: {run_offset}, run_size: {run_size} pos={len(dest)}')
                else:
                    b1 = b
                    b2 = f.read(1)[0]
                    count = ((b1 & 0xF0) >> 4) + 1
                    buf = []
                    for _ in range(4):
                        d = ((b1 & 0x08) >> 1) | ((b2 & 0x80) >> 6) | ((b2 & 0x08) >> 3)
                        buf.append(d)
                        b1 = b1 << 1
                        b2 = b2 << 1
                    dest.extend(buf * count)
                    # print(f'{data.tell(): 6d} type: {(b1>>4):02x} {(b2>>4):02x}, count: {count}, buf: {buf} pos={len(dest)}')
            # save image
            print(f"{w=}, {h=}")
            image = Image.new("RGB", (w, h * 2), BGCOLOR)
            for px_index, color_index in enumerate(bytes(dest)):
                y, x = divmod(px_index, w)
                c = palette[color_index]
                # image.putpixel((x, y), c)
                image.putpixel((x, 2 * y), c)
                image.putpixel((x, 2 * y + 1), c)
            images.append(image)
            # prepare for loop
            next_offset = f.tell()
            offsets.append((offset, next_offset - offset))
            if next_offset >= file_size:
                break
        if next_offset < file_size:
            w = 24
            h = 32
            # data_size = int(w * h / 2 / 8 * 3)  # 144
            data_size = 144
            for i in range(6):
                data = f.read(data_size)
                print(len(data))
                img = data_to_image(data, w, h, san2_face_palette, True)
                images.append(img)
    total_size = 0
    for offset, size in offsets:
        print(f"{offset=}, {size=}")
        total_size += size
    print(f"{total_size=}")
    images = (
        {str(i): img for i, img in enumerate(images)}
        if isinstance(images, list)
        else images
    )
    save_single_images(images, out_dir, prefix)


# ---------------------------------------------------------------- montage (DOS MONTAGE.DAT)
# A composite face code has bit 15 set, bits 0-2 = head, then a 2-bit record number per area
# (bits 3-4, 5-6, 7-8, 9-10, 11-12). Each head is a 0x18C0-byte block of 4 records per area, in
# the same 3bpp half-height layout as KAODATA.DAT (24 bytes per row). MAIN.EXE builds the face in a
# 960-byte buffer: copies the first two areas, then ORs the other three in (see notes/san2.md).
MONTAGE_HEAD_SIZE = 0x18C0
# (offset in the head block, bytes per record, offset in the face buffer), from MAIN.EXE's tables
MONTAGE_AREAS = [(0, 432, 0), (1728, 528, 432), (3840, 192, 240), (4608, 240, 528), (5568, 192, 384)]
MONTAGE_SHIFTS = [3, 5, 7, 9, 11]


def is_montage_code(code: int) -> bool:
    return bool(code & 0x8000)


def montage_record(data: bytes, head: int, area: int, record: int) -> bytes:
    base, size, _ = MONTAGE_AREAS[area]
    pos = head * MONTAGE_HEAD_SIZE + base + record * size
    return data[pos:pos + size]


def compose_montage(data: bytes, code: int) -> bytes:
    """The game's 960-byte face buffer for a composite code."""
    face = bytearray(960)
    for area, shift in enumerate(MONTAGE_SHIFTS):
        _, size, dest = MONTAGE_AREAS[area]
        rec = montage_record(data, code & 7, area, code >> shift & 3)
        for i, b in enumerate(rec):
            face[dest + i] = b if area < 2 else face[dest + i] | b
    return bytes(face)


# ---------------------------------------------------------------- PC-98 / X68000 (Japanese, see notes/san2.md)
# KAODATA1/2/3.DAT: full-height 64x80 3bpp faces, 1920 bytes each (95 + 96 + 28 = 219); the montage parts
# follow in KAODATA3 at 0xD200: 8 heads x 0x37E0 bytes, areas ORed the same way as DOS
JP_FACE = 1920
JP_FACE_FILES = [("KAODATA1.DAT", 95), ("KAODATA2.DAT", 96), ("KAODATA3.DAT", 28)]
JP_MONTAGE_OFFSET = 0xD200
JP_MONTAGE_HEAD_SIZE = 0x37E0
# (offset in the head block, bytes per record, first face row); areas 3 and 4 are nose then mouth
JP_MONTAGE_AREAS = [(0, 792, 0), (3168, 1128, 33), (7680, 552, 21), (9888, 552, 29), (12096, 552, 41)]
# KOEI gaiji (SJIS 0xEB9F..), glyphs in FONT.DAT; table at PC-98 MAIN.EXE DGROUP 0x34B0, read off the glyphs
JP_GAIJI = dict(zip(
    [0xEB9F + i for i in range(32)] + [0xEBC0, 0xEBC1, 0xEBC3, 0xEBC4, 0xEBC6, 0xEBC7],
    "瓚昱彧郃蒯蔡傕Ⅱ汜詡鄧兗龐繇邈鷙畯闞玠顗邢歆闓禕釭琬郝琮♥褚©℗" "琦琮幷璝彤琬"))


def jp_montage_record(data: bytes, head: int, area: int, record: int) -> bytes:
    """`data` is KAODATA3.DAT."""
    base, size, _ = JP_MONTAGE_AREAS[area]
    pos = JP_MONTAGE_OFFSET + head * JP_MONTAGE_HEAD_SIZE + base + record * size
    return data[pos:pos + size]


def jp_name(raw: bytes) -> str:
    """14-byte name field: 7 bytes Shift-JIS (+ gaiji), then 7 bytes of half-width kana (not returned)."""
    raw = raw[:7].split(b"\0")[0]
    out, i = [], 0
    while i < len(raw):
        n = 2 if 0x81 <= raw[i] <= 0x9F or 0xE0 <= raw[i] <= 0xFC else 1
        code = int.from_bytes(raw[i:i + n], "big")
        out.append(JP_GAIJI.get(code) or raw[i:i + n].decode("cp932"))
        i += n
    return "".join(out)


def load_san2_jp_persons(game_dir: str, x68: bool = False) -> list[tuple[int, str]]:
    """(face code, name): SNDATA1-6.CIM then TAIKI.DAT, deduplicated by face code (same order as DOS).

    PC-98 records are the DOS ones (s2_format / s2_format_taiki). X68000 records are big-endian with
    68000 padding: 54 bytes (face u32 at +34, name at +38), TAIKI adds 4 bytes in front.
    """
    persons, seen = [], set()

    def add(rec, face_at, name_at):
        if rec[name_at:name_at + 4] == bytes(4):
            return False
        face = int.from_bytes(rec[face_at:face_at + (4 if x68 else 2)], "big" if x68 else "little") & 0xFFFF
        if face not in seen:
            seen.add(face)
            persons.append((face, jp_name(rec[name_at:name_at + 14])))
        return True

    size, header, face_at = (54, 0x1A, 34) if x68 else (struct.calcsize(s2_format), 0x16, 26)
    for n in range(1, 7):
        with open(os.path.join(game_dir, f"SNDATA{n}.CIM"), "rb") as f:
            d = f.read()
        for i in range(215):
            if not add(d[header + i * size:header + (i + 1) * size], face_at, face_at + (4 if x68 else 2)):
                break
    with open(os.path.join(game_dir, "TAIKI.DAT"), "rb") as f:
        d = f.read()
    size, face_at = (58, 38) if x68 else (struct.calcsize(s2_format_taiki), 29)
    for i in range(420):
        if not add(d[6 + i * size:6 + (i + 1) * size], face_at, face_at + (4 if x68 else 2)):
            break
    return persons


san2.add_command(san2_face, "face")
san2.add_command(san2_grp, "grp")
san2.add_command(san2_grpa, "grpa")
san2.add_command(san2_map, "map")
san2.add_command(san2_person, "person")
