import click
import genpei
from rich.console import Console
from utils import *
from san_person import *

console = Console()


##############################################################################


@click.group()
def san4():
    """三國志IV"""
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def san4_face(face_file, out_dir, prefix):
    """
    KAODATA.S4 (DOS, Steam) 530,413 byte (不明)
    KAODATA2.S4 (DOS)       三國志3:150, 水滸:170, TOTAL:320
    KAODATA2.S4 (Steam)     三國志3:150, 水滸:170, 信長:117, TOTAL:437
    KAODATAP.S4 (DOS)       三國志4:340, 水滸:117, 大眾:244, TOTAL:701
    KAODATAP.S4 (Steam)     三國志4:340, 水滸:117, 大眾:244, 信長:117, TOTAL:818

    # color pallete (威力加強版編輯器)
    #   | 黑[0] | 深藍[4] | 朱紅[2] | 深皮[6] |
    #   | 綠[1] | 淺藍[5] | 淺皮[3] | 雪白[7] |

    dekoei.py san4 face -f /Volumes/common/San4WPK/KAODATA2.S4 --prefix SAN4_WIN_F
    dekoei.py san4 face -f /Volumes/common/San4WPK/KAODATAP.S4 --prefix SAN4_WIN_F
    """
    palette = color_codes_to_palette(
        ['#302000', '#417120', '#B24120', '#D3B282', '#204182', '#418292', '#C38251', '#D3D3B2']
    )
    face_w, face_h = 64, 80

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix)


san4.add_command(san4_face, 'face')


# DOS release (see notes/san4.md)

def decode_san4_face(src: bytes) -> tuple[int, int, bytes]:
    """One KAODATA.S4 entry -> (w, h, colour indexes). Decompressor at MAIN.EXE 0x24E54."""
    pos = 4
    w, h = int.from_bytes(src[0:2], 'little'), int.from_bytes(src[2:4], 'little')
    count = last = 0
    half = None

    def byte():  # byte stream with RLE: 0xFE n repeats the last byte n times (0 = 256), 0xFE 0x01 = 0xFE
        nonlocal pos, count, last
        if count == 0:
            b = src[pos]
            pos += 1
            if b != 0xFE:
                last = b
                return b
            n = src[pos]
            pos += 1
            if n == 1:
                last = 0xFE
                return 0xFE
            count = n or 256
        count -= 1
        return last

    def nibble():  # high nibble first
        nonlocal half
        if half is None:
            half = byte()
            return half >> 4
        b, half = half, None
        return b & 15

    px = bytearray(w * h)
    for y in range(h):
        ref = nibble()  # what a run copies: 8+n = the pixel n-7 rows up, else the pixel n+1 to the left
        dy, dx = (ref - 7, 0) if ref & 8 else (0, ref + 1)
        run = 0
        for x in range(w):
            if run == 0:
                c = nibble()
                if c & 8:
                    run = ((c & 3) << 4) + nibble() + 6 if c & 4 else (c & 3) + 2
                else:
                    px[y * w + x] = c
            if run:
                px[y * w + x] = px[(y - dy) * w + x - dx]
                run -= 1
    return w, h, bytes(px)


def load_san4_faces(file) -> list[tuple[int, int, bytes]]:
    """KAODATA.S4: 340 (u32 offset, u16 size) entries; offsets count from the end of the index."""
    with open(file, 'rb') as f:
        data = f.read()
    count = 340
    faces = []
    for i in range(count):
        offset = int.from_bytes(data[i * 6:i * 6 + 4], 'little') + count * 6
        size = int.from_bytes(data[i * 6 + 4:i * 6 + 6], 'little')
        faces.append(decode_san4_face(data[offset:offset + size]))
    return faces


# PC-98 KOEI gaiji (SJIS 0xEB9F + glyph index of FONT.S4); only the codes used by person names,
# read off the FONT.S4 glyphs
SAN4_PC98_GAIJI = {
    0xEB9F: "瓚", 0xEBA0: "昱", 0xEBA1: "彧", 0xEBA2: "郃", 0xEBA3: "蒯", 0xEBA5: "傕", 0xEBA6: "邕",
    0xEBA7: "汜", 0xEBA8: "詡", 0xEBA9: "鄧", 0xEBAB: "龐", 0xEBAC: "繇", 0xEBAD: "邈", 0xEBAE: "騭",
    0xEBB0: "闞", 0xEBB1: "玠", 0xEBB3: "邢", 0xEBB4: "歆", 0xEBB5: "闓", 0xEBB6: "禕", 0xEBB7: "譙",
    0xEBB8: "琬", 0xEBB9: "郝", 0xEBBA: "琮", 0xEBBB: "伷", 0xEBBC: "褚", 0xEBBD: "璜", 0xEBC0: "琦",
    0xEBC6: "彤", 0xEBD1: "綝", 0xEBD2: "諶", 0xEBD4: "昕", 0xEBD6: "笮", 0xEBD7: "祜", 0xEBDA: "毌",
    0xEBDD: "靚", 0xEBDF: "頎", 0xEBEC: "毗", 0xEBEE: "宓", 0xEBF5: "蹋",
}


def san4_pc98_name(b: bytes, gaiji=SAN4_PC98_GAIJI) -> str:
    out, i = [], 0
    while i < len(b):
        if 0x81 <= b[i] <= 0x9F or 0xE0 <= b[i] <= 0xFC:
            code = b[i] << 8 | b[i + 1]
            out.append(gaiji[code] if code >= 0xEB9F else b[i:i + 2].decode("cp932"))
            i += 2
        else:
            out.append(b[i:i + 1].decode("cp932"))
            i += 1
    return "".join(out)


def san4_parts(data: bytes) -> list[bytes]:
    """LS11 (DOS, PC-98), or uncompressed (PC-98 PK): u16 count, count x (u32 offset, u16 size) from the table end."""
    if data[:4] == b"LS11":
        import ls11
        return ls11.ls11_decode_parts(data)
    n = int.from_bytes(data[:2], "little")
    base = 2 + n * 6
    return [data[base + o:base + o + size] for o, size in
            (struct.unpack_from("<IH", data, 2 + i * 6) for i in range(n))]


def load_san4_persons(sndata, taiki, pc98=False) -> list[tuple[int, str, int]]:
    """(scenario, name, face code) of every person record: SNDATA.S4 then TAIKI.S4 per scenario.

    One part per scenario. SNDATA's person table runs to the end of the part, 30 bytes each (name 20 bytes,
    face u16); TAIKI is 50-byte records with the same 30 bytes at +20. PC-98: the name is 9 bytes Shift-JIS
    followed by 11 bytes of half-width kana.
    """
    with open(sndata, 'rb') as f:
        sn = san4_parts(f.read())
    with open(taiki, 'rb') as f:
        tk = san4_parts(f.read())

    def person(scenario, b):
        name = san4_pc98_name(b[:9].split(b'\0')[0]) if pc98 else to_unicode_name(b[:20].split(b'\0')[0])
        return scenario, name, int.from_bytes(b[20:22], 'little')

    persons = []
    for scenario, (part, extra) in enumerate(zip(sn, tk), 1):
        start = len(part)
        while start >= 30 and part[start - 30] >= 0x80 and part[start - 10:start - 8] != b'\xff\xff':
            start -= 30
        persons += [person(scenario, part[o:o + 30]) for o in range(start, len(part), 30)]
        persons += [person(scenario, extra[o + 20:o + 50]) for o in range(0, len(extra), 50)]
    return persons


# PK: NBDATA.SUI holds 117 水滸伝 officers (117 x 20-byte blocks, then 117 x 30-byte person records,
# face codes 340-456); the PC-98 PK's FONT.S4 adds the gaiji they need
SAN4PK_SUIKODEN_GAIJI = {**SAN4_PC98_GAIJI, 0xEBE2: "龔", 0xEBF9: "玘", 0xEBFA: "俅"}


def load_san4pk_suikoden(nbdata_sui, pc98=True) -> list[tuple[str, int]]:
    """(name, face code) of the NBDATA.SUI officers; names as in SNDATA.S4."""
    with open(nbdata_sui, "rb") as f:
        data = f.read()
    records = [data[117 * 20 + i * 30:117 * 20 + (i + 1) * 30] for i in range(117)]
    return [(san4_pc98_name(r[:9].split(b"\0")[0], SAN4PK_SUIKODEN_GAIJI) if pc98 else
             to_unicode_name(r[:20].split(b"\0")[0]), int.from_bytes(r[20:22], "little")) for r in records]


# MONDATA.S4: 16 heads x 0x2E80 bytes, 3bpp planar rows of 24 bytes (byte k = bit k, as genpei.decode_planar).
# Composer at MAIN.EXE 0x24FB8; face code bit 15 = composite, bits 0-3 head.
SAN4_MONTAGE_HEAD_SIZE = 0x2E80
# (offset in head block, rows per record, records, (shift, mask) in the face code) per area
SAN4_MONTAGE_AREAS = [(0, 36, 4, (4, 3)), (3456, 44, 4, (6, 3)), (7680, 16, 6, (8, 7)), (9984, 20, 4, (11, 3))]
# first face row of each area per head: top and bottom are fixed, eyes and mouth from DGROUP 0x395A / 0x396A
SAN4_MONTAGE_ROWS = [
    [0] * 16,
    [36] * 16,
    [20, 26, 20, 22, 26, 21, 25, 26, 23, 25, 25, 24, 21, 20, 21, 20],
    [41, 46, 38, 43, 47, 40, 46, 43, 41, 45, 45, 43, 44, 41, 43, 42],
]


def san4_montage_parts(code):
    return [code >> s & m for *_, (s, m) in SAN4_MONTAGE_AREAS]


def san4_montage_record(data, head, area, record) -> tuple[int, int, bytes]:
    offset, rows, _, _ = SAN4_MONTAGE_AREAS[area]
    start = head * SAN4_MONTAGE_HEAD_SIZE + offset + record * rows * 24
    return 64, rows, bytes(genpei.decode_planar(data, start, 64, rows, 3))

##############################################################################


@click.group()
def san5():
    """三國志V"""
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def san5_face(face_file, out_dir, prefix):
    """
    KAODATA.S5 (DOS)    專用與大眾臉: 783
    KAODATAP.S5 (DOS)   同上，兩檔案大小相同 1,503,360 byte
    KAOEX.S5 (DOS)      三４:160, 項劉:30, 信長:60, 英傑:100, 水滸:32, TOTAL:382
    Steam 版三檔案與上述同

    dekoei.py san5 face -f /Volumes/common/San5WPK/KAODATA.S5 --prefix SAN5_WIN_F
    dekoei.py san5 face -f /Volumes/common/San5WPK/KAOEX.S5  --prefix SAN5_WIN_F
    """
    palette = color_codes_to_palette(
        ['#202010', '#206510', '#BA3000', '#EFAA8A', '#104575', '#658A9A', '#BA7545', '#EFDFCF']
    )
    face_w, face_h = 64, 80

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix)


san5.add_command(san5_face, 'face')


# DOS release (see notes/san5.md)

SAN5_FACE = 1920  # 64x80, 3bpp planar rows of 24 bytes, byte k = bit k


def san5_parts(file) -> list[bytes]:
    """SNDATA.S5 / TAIKI.S5: u16 count, then (u32 offset, u16 size) per scenario; offsets count from the index end."""
    with open(file, 'rb') as f:
        data = f.read()
    count = int.from_bytes(data[:2], 'little')
    base = 2 + count * 6
    parts = []
    for i in range(count):
        offset = base + int.from_bytes(data[2 + i * 6:6 + i * 6], 'little')
        size = int.from_bytes(data[6 + i * 6:8 + i * 6], 'little')
        parts.append(data[offset:offset + size])
    return parts


# PC-98 KOEI gaiji (SJIS 0xEB9F + glyph index of FONT.S5); only the codes used by person names
SAN5_PC98_GAIJI = {
    **SAN4_PC98_GAIJI, 0xEBAF: "畯", 0xEBD9: "璜", 0xEBE2: "龔",
}


def load_san5_persons(sndata, taiki, pc98=False, tail=1100) -> list[tuple[int, str, int]]:
    """(scenario, name, face code) of every person record: SNDATA.S5 then TAIKI.S5 for each scenario.

    SNDATA's person table ends `tail` bytes before the end of each scenario (PK 1100, base game 64), 38 bytes per person
    (name 10 bytes, face u16 at +30); TAIKI is 69-byte records with the same 38 bytes at +31.
    PC-98: the name is 8 bytes Shift-JIS + NUL, then the reading in half-width kana at +9.
    """
    def person(scenario, b):
        name = san4_pc98_name(b[:9].split(b'\0')[0], SAN5_PC98_GAIJI) if pc98 else \
            to_unicode_name(b[:10].split(b'\0')[0])
        return scenario, name, int.from_bytes(b[30:32], 'little')

    def is_person(b):
        return b[0] >= 0x81 and b[8] == 0 and 0xA1 <= b[9] <= 0xDF if pc98 else b[0] >= 0x80 and not any(b[10:20])

    persons = []
    for scenario, part in enumerate(san5_parts(sndata), 1):
        end = start = len(part) - tail
        while start >= 38 and is_person(part[start - 38:start]):
            start -= 38
        persons += [person(scenario, part[o:o + 38]) for o in range(start, end, 38)]
    for scenario, part in enumerate(san5_parts(taiki), 1):
        persons += [person(scenario, part[o + 31:o + 69]) for o in range(0, len(part), 69)]
    return persons

##############################################################################


@click.group()
def san6():
    """三國志VI"""
    pass


@click.command(help='顏 CG 解析')
@click.option('-d', '--dir', 'game_dir', help="遊戲目錄")
@click.option('-f', '--face', 'face_file', help="頭像檔案")
@click.option('-p', '--palette', 'palette_file', default='Palette.S6', help="色盤檔案")
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def san6_face(game_dir, face_file, palette_file, out_dir, prefix):
    """
    ./dekoei.py san6 face -d /Volumes/common/San6WPK/
    """
    if game_dir is not None:
        palette_file = os.path.join(game_dir, 'Palette.S6')
        face_file = os.path.join(game_dir, 'Kaodata.s6')

    palette = load_palette_from_file(palette_file, 4)  # 4 bytes: 0x01000300
    face_w, face_h = 96, 120

    def stream() -> typing.Generator[bytes, None, None]:
        with open(face_file, 'rb') as f:
            """
            KAODATA.S6

            CNT             4       bytes
            OFFSET INFO     16*CNT  bytes
                POS             4   bytes
                SZ              4   bytes
                W               4   bytes
                H               4   bytes
            IMAGES          ...
            """
            count = int.from_bytes(f.read(4), LITTLE_ENDIAN)
            offset = 4 + 16 * count  # 4: header size; 16: info size(pos, len, w, h)
            f.seek(offset)
            while data := f.read(96*120):
                yield data

    extract_images('', face_w, face_h, palette, out_dir, prefix, data_loader=stream)


san6.add_command(san6_face, 'face')


def load_san6_faces(kaodata) -> list[bytes]:
    """KAODATA.S6: u32 count, count x (offset, size, w, h) u32, then 96x120 8-bit images."""
    with open(kaodata, "rb") as f:
        data = f.read()
    count = int.from_bytes(data[:4], "little")
    base = 4 + 16 * count
    return [data[base + o:base + o + size] for o, size, w, h in
            (struct.unpack_from("<4I", data, 4 + 16 * i) for i in range(count))]


def load_san6_palette(palette) -> list[str]:
    """PALETTE.S6: three identical Windows LOGPALETTEs (0x300, 256 x RGBX); faces use colours 0-245."""
    with open(palette, "rb") as f:
        data = f.read()
    assert data[:4] == b"\x00\x03\x00\x01"
    return [f"#{data[4 + i * 4]:02x}{data[5 + i * 4]:02x}{data[6 + i * 4]:02x}" for i in range(246)]


# 孔明傳 (EKD2) BAKDATA.E2: 17-byte battle/story person records from 0x18F0 to 0x3AF0 (one per appearance);
# +0 name 12 bytes Big5, +14 u16 face code into KAO.E2
KOUMEI_PERSONS = (0x18F0, 0x3AF0, 17)


def load_koumei_persons(bakdata) -> list[tuple[str, int]]:
    """(name, face code) of every BAKDATA.E2 person record, in file order."""
    with open(bakdata, "rb") as f:
        data = f.read()
    start, end, size = KOUMEI_PERSONS
    return [(data[o:o + 12].split(b"\0")[0].decode("big5"), int.from_bytes(data[o + 14:o + 16], "little"))
            for o in range(start, end, size)]


def load_koumei_palette(palet) -> list[str]:
    """PALET.E2: 256 x (B, R, G), 8 bits each; faces use 0 and 16-239."""
    with open(palet, "rb") as f:
        data = f.read()
    return [f"#{data[i * 3 + 1]:02x}{data[i * 3 + 2]:02x}{data[i * 3]:02x}" for i in range(240)]


# SNDATAnn.S6: 650 person records of 650 bytes from 0x17D04 (550 persons, then 100 new-officer slots);
# +0 surname 6 bytes, +6 given name 6 bytes (Big5, NUL then spaces), +12 style name, +30 u16 face code
SAN6_PERSONS = 0x17D04
SAN6_PERSON_SIZE = 650


def load_san6_persons(game_dir, scenarios=23) -> list[tuple[int, str, int]]:
    """(slot, name, face code) of every person slot with a face, first seen over SNDATA01-23."""
    def text(b):
        return b.split(b"\0")[0].strip().decode("big5")

    persons = {}
    for n in range(1, scenarios + 1):
        with open(os.path.join(game_dir, f"SNDATA{n:02}.S6"), "rb") as f:
            data = f.read()
        for slot in range(SAN6_PERSON_SIZE):
            r = SAN6_PERSONS + slot * SAN6_PERSON_SIZE
            face = int.from_bytes(data[r + 30:r + 32], "little")
            if face:
                persons.setdefault(slot, (text(data[r:r + 6]) + text(data[r + 6:r + 12]), face))
                assert persons[slot][1] == face
    return [(slot, name, face) for slot, (name, face) in sorted(persons.items())]

##############################################################################


@click.group()
def san7():
    """三國志VII"""
    pass


@click.command(help='顏 CG 解析')
@click.option('-d', '--dir', 'game_dir', help="遊戲目錄")
@click.option('-f', '--face', 'face_file', help="頭像檔案")
@click.option('-p', '--palette', 'palette_file', default='P_Kao.s7', help="色盤檔案")
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def san7_face(game_dir, face_file, palette_file, out_dir, prefix):
    """
    P_Kao.s7    Palette file
    Kaodata.s7  KAO file

    ./dekoei.py san7 face -d /Volumes/common/San7WPK/
    """
    if game_dir is not None:
        palette_file = os.path.join(game_dir, 'P_Kao.s7')
        face_file = os.path.join(game_dir, 'Kaodata.s7')

    palette = load_palette_from_file(palette_file, 4)  # 4 bytes: 0x01000300
    face_w, face_h = 96, 120

    def stream() -> typing.Generator[bytes, None, None]:
        with open(face_file, 'rb') as f:
            """
            KAODATA.S7

            CNT             4       bytes  # 0xA602 = 678
            OFFSET INFO     16*CNT  bytes
                POS             4   bytes
                SZ              4   bytes
                W               4   bytes
                H               4   bytes
            IMAGES          ...
            """
            count = int.from_bytes(f.read(4), LITTLE_ENDIAN)
            offset = 4 + 16 * count  # 4: header size; 16: info size(pos, len, w, h)
            f.seek(offset)
            while data := f.read(96*120):
                yield data

    extract_images('', face_w, face_h, palette, out_dir, prefix, data_loader=stream)


san7.add_command(san7_face, 'face')

##############################################################################


@click.group()
def san8():
    """三國志VIII"""
    pass


@click.command(help='顏 CG 解析')
@click.option('-d', '--dir', 'game_dir', help="遊戲目錄")
@click.option('-f', '--face', 'face_file', help="頭像檔案")
@click.option('-p', '--palette', 'palette_file', default='P_Kao.s7', help="色盤檔案")
@click.option('-s', '--size', 'size', default='small', help="頭像大小 (small, large)")
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def san8_face(game_dir, face_file, palette_file, size, out_dir, prefix):
    """
    P_MAIN.S8       Palette file
    g_maindy.s8     Kao file

    ./dekoei.py san8 face -d /Volumes/common/San8WPK/
    """
    is_large = True if size.lower() == 'large' else False

    if game_dir is not None:
        palette_file = os.path.join(game_dir, 'P_MAIN.S8')
        face_file = os.path.join(game_dir, 'g_maindy.s8')

    """
    P_MAIN.S8

    MAGIC WORD      8       bytes  # 0x4B4F4549 = 'KOEI'
    OFFSET          8       bytes  # 0x4C06 = 1612
    SIZE            8       bytes  # size of BOFFSETS (block offsets), 0x3406 = 1588
    BOFFSETS        4x397   bytes  # 397 = SIZE / 4
    UNKNOWN        12       bytes  # 0xFFFFFFFF 0x00000000 0x00000000

    BLOCK N      1024       bytes  # offset = OFFSET + BOFFSETS[N] + 12
                                    # size = BOFFSETS[N+1] - BOFFSETS[N]

    KAO PALETTE = BLOCK 4 (0-base)
    """
    palette = load_palette_from_file(palette_file, 5720)  # 5720 = 4096 + 1612 + 12, 4096: BOFFSETS[4]

    face_w, face_h = 64, 80  # 小頭像
    offset = 24374192  # 9380 + 24364800 + 12 = 24,374,192
    if is_large:
        face_w, face_h = 160, 180  # 大頭像
        offset = 9380+12

    def stream() -> typing.Generator[bytes, None, None]:
        with open(face_file, 'rb') as f:
            count = 846
            f.seek(offset)
            for _ in range(count):
                yield f.read(face_w * face_h)

    extract_images('', face_w, face_h, palette, out_dir, prefix, data_loader=stream)


san8.add_command(san8_face, 'face')

##############################################################################


@click.group()
def san9():
    """三國志IX

    \b
    File List:
        G_FaceL.s9
        G_FaceS.s9
        G_FaceT.s9
        G_FacLPK.s9
        G_FacSPK.s9
        G_FacTPK.s9
        P_Face.s9       武將CG色盤
    """
    pass


@click.command(help="顏CG解析")
@click.option('-d', '--dir', 'game_dir', help="遊戲目錄")
@click.option('-p', '--palette', 'palette_file', help="色盤", required=True)
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
@click.option('--image-size',
              type=click.Choice(['L', 'S', 'T'], case_sensitive=False),
              help='頭像尺寸 L 240x240,\n S:  64x 80,\n T: 32x40')
def san9_face(game_dir, palette_file, face_file, image_size, out_dir, prefix):
    """三國志 IX 頭像解析

    dekoei.py san9 face -p KAO/SAN9_P_Face.s9 -f KAO/SAN9_G_FaceL.s9  -t SAN9L   --image-size=L --prefix "SAN9_WIN_FL"
    dekoei.py san9 face -p KAO/SAN9_P_Face.s9 -f KAO/SAN9_G_FacLPK.s9 -t SAN9PKL --image-size=L --prefix "SAN9PK_WIN_FL"
    dekoei.py san9 face -p KAO/SAN9_P_Face.s9 -f KAO/SAN9_G_FaceS.s9  -t SAN9S   --image-size=S --prefix "SAN9_WIN_FS"
    dekoei.py san9 face -p KAO/SAN9_P_Face.s9 -f KAO/SAN9_G_FacSPK.s9 -t SAN9PKS --image-size=S --prefix "SAN9PK_WIN_FS"
    dekoei.py san9 face -p KAO/SAN9_P_Face.s9 -f KAO/SAN9_G_FaceT.s9  -t SAN9T   --image-size=T --prefix "SAN9_WIN_FT"
    dekoei.py san9 face -p KAO/SAN9_P_Face.s9 -f KAO/SAN9_G_FacTPK.s9 -t SAN9PKT --image-size=T --prefix "SAN9PK_WIN_FT"

    ./dekoei.py san9 face -p /Volumes/common/San9WPK/P_Face.s9 -f /Volumes/common/San9WPK/G_FaceS.s9 --image-size=S
    ./dekoei.py san9 face -p /Volumes/common/San9WPK/P_Face.s9 -f /Volumes/common/San9WPK/G_FaceL.s9 --image-size=L
    """
    image_size_spec = {"L": (240, 240), "S": (64, 80), "T": (32, 40)}
    # face_filenames = {"L": "G_FaceL.s9", "S": "G_FaceS.s9", "T": "G_FaceT.s9"}
    pk_face_filenames = {"L": "G_FacLPK.s9", "S": "G_FacSPK.s9", "T": "G_FacTPK.s9"}

    if game_dir is not None:
        palette_file = os.path.join(game_dir, 'P_FACE.s9')
        face_file = os.path.join(game_dir, pk_face_filenames[image_size])

    palette = load_palette_from_file(palette_file, 44)
    face_w, face_h = image_size_spec[image_size]

    def stream() -> typing.Generator[bytes, None, None]:
        with open(face_file, 'rb') as f:
            data_size = face_w * face_h
            file_size = os.stat(face_file).st_size
            count = file_size // data_size

            f.seek(4)  # skip header
            for _ in range(count):
                f.read(16)  # skip info(block_size, ?, width, height)
                yield f.read(data_size)

    extract_images('', face_w, face_h, palette, out_dir, prefix, data_loader=stream)


@click.command()
def san9_person():
    pass


san9.add_command(san9_face, "face")
san9.add_command(san9_person, "person")
