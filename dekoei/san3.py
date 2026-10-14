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


san3.add_command(san3_face, "face")
san3.add_command(san3_person, "person")
