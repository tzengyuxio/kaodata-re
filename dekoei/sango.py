import collections
import ls11
import re
import zlib
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


# 三國志VII PK (Steam) D_Sn???.s7: a plain 0x4C-byte header (+0x1A u16 scenario number), then every byte goes
# through one of four 256-byte substitution tables in San7WPK.exe (file 0x4E5500 + 0x100 k; the file's most common
# byte is the encoded 0). The person table starts at 0x30A: 620 records of 0x78 bytes (520 officers, then 100
# new-officer slots with id 0xFFFF); +0 u16 id = face number into Kaodata.s7 (again at +0x24), +0x2A surname 6 bytes,
# +0x30 given name 6, +0x36 style name 6, +0x3C kana 12 (half-width, no separator), Shift-JIS with S7gaiji.tte EUDC.
SAN7_TABLES = 0x4E5500
SAN7_PERSONS = 0x30A
SAN7_PERSON_SIZE = 0x78
SAN7_SCENARIOS = ["D_Sn001.s7", "D_Sn002.s7", "D_Sn003.s7", "D_Sn004.s7", "D_Sn005.s7", "D_Sn006.s7", "D_Sn007.s7",
                  "D_Sn101.s7", "D_Sn102.s7", "D_Sn103.s7", "D_Sn104.s7", "D_Sn105.s7"]
# S7gaiji.tte glyphs used in names, by private-use code point
SAN7_GAIJI = dict(zip(
    [0xE000, 0xE003, 0xE004, 0xE006, 0xE007, 0xE009, 0xE00C, 0xE00D, 0xE00E, 0xE00F, 0xE011, 0xE012, 0xE014,
     0xE015, 0xE016, 0xE018, 0xE019, 0xE01A, 0xE01C, 0xE01D, 0xE027, 0xE02E, 0xE032, 0xE037, 0xE038, 0xE039,
     0xE03A, 0xE03B, 0xE03E, 0xE03F, 0xE040, 0xE043, 0xE044, 0xE04D, 0xE04F, 0xE051, 0xE056, 0xE05C],
    "瓚郃蒯傕邕詡龐繇邈騭闞玠邢歆闓譙琬郝伷褚肜磾綝笮祜蕤璜毌靚琰頎龔眭毗宓禕蹋勑"))


def decode_san7_scenario(exe: bytes, data: bytes) -> bytes:
    tables = [exe[SAN7_TABLES + 0x100 * k:SAN7_TABLES + 0x100 * (k + 1)] for k in range(4)]
    zero = collections.Counter(data[0x4C:]).most_common(1)[0][0]
    table = next(t for t in tables if t[0] == zero)
    inv = bytearray(256)
    for i, b in enumerate(table):
        inv[b] = i
    return data[:0x4C] + bytes(inv[c] for c in data[0x4C:])


def load_san7_persons(game_dir) -> dict[int, tuple[str, str]]:
    """Officer id (= face number) -> (name, half-width kana), the same in all twelve scenarios."""
    with open(os.path.join(game_dir, "San7WPK.exe"), "rb") as f:
        exe = f.read()

    def text(b):
        return "".join(SAN7_GAIJI.get(ord(c), c) for c in b.split(b"\0")[0].decode("cp932"))

    persons = {}
    for name in SAN7_SCENARIOS:
        with open(os.path.join(game_dir, name), "rb") as f:
            data = decode_san7_scenario(exe, f.read())
        for o in range(SAN7_PERSONS, SAN7_PERSONS + 620 * SAN7_PERSON_SIZE, SAN7_PERSON_SIZE):
            pid = int.from_bytes(data[o:o + 2], "little")
            if pid != 0xFFFF:
                assert pid == int.from_bytes(data[o + 0x24:o + 0x26], "little")
                full = (text(data[o + 0x2A:o + 0x30]) + text(data[o + 0x30:o + 0x36]), text(data[o + 0x3C:o + 0x48]))
                assert persons.setdefault(pid, full) == full
    return persons


def load_san7_palette(palette) -> list[str]:
    """P_Kao.s7: a Windows LOGPALETTE (256 x RGBX). Index 0 is the unused key colour #FF00FF."""
    with open(palette, "rb") as f:
        data = f.read()
    assert data[:4] == b"\x00\x03\x00\x01"
    return [f"#{data[4 + i * 4]:02x}{data[5 + i * 4]:02x}{data[6 + i * 4]:02x}" for i in range(256)]


# 三國志VIII PK (Steam) "KOEI" archives (g_maindy.s8, p_main.s8): +8 u32 data base, +16 u32 size of the u32 offset
# table at +0x18; entry n is at base + 12 + offset[n]. g_maindy entries 0-845 are 160x180 faces, 846-1691 the same
# faces at 64x80; p_main entry 4 is the face palette (256 x RGBX).
SAN8_FACES = 846
# D_Sce.s8 (plain): 658 person records of 0x4F bytes from 0x2437; +0 u16 id, +2 surname 5 bytes, +7 its kana 11,
# +0x12 given name 5, +0x17 its kana 11, +0x22 style name 5 (Shift-JIS, S8gaiji.tte EUDC), +0x27 u16 face number
SAN8_PERSONS = 0x2437
SAN8_PERSON_SIZE = 0x4F
SAN8_GAIJI = {**SAN7_GAIJI, 0xE013: "顗", 0xE025: "璝", 0xE03D: "瓘", 0xE063: "淩"}


def koei_archive(data: bytes) -> list[bytes]:
    base, size = struct.unpack_from("<I", data, 8)[0], struct.unpack_from("<I", data, 16)[0]
    offsets = list(struct.unpack_from(f"<{size // 4}I", data, 0x18)) + [len(data) - base - 12]
    return [data[base + 12 + a:base + 12 + b] for a, b in zip(offsets, offsets[1:])]


def load_san8_persons(sce) -> list[dict]:
    """Person records of D_Sce.s8 in id order: id, name, surname/given kana, face number."""
    with open(sce, "rb") as f:
        data = f.read()

    def text(b):
        return "".join(SAN8_GAIJI.get(ord(c), c) for c in b.split(b"\0")[0].decode("cp932").strip())

    persons = []
    for k in range(658):
        r = data[SAN8_PERSONS + k * SAN8_PERSON_SIZE:SAN8_PERSONS + (k + 1) * SAN8_PERSON_SIZE]
        assert int.from_bytes(r[:2], "little") == k
        persons.append({"id": k, "name": text(r[2:7]) + text(r[0x12:0x17]),
                        "kana": (text(r[7:0x12]), text(r[0x17:0x22])), "face": int.from_bytes(r[0x27:0x29], "little")})
    return persons


# 三國志IX PK (Steam): G_FaceS.s9 (786) and the PK's G_FacSPK.s9 (50) are u32 file size, then per face a 16-byte
# header (u32 size incl. header, ?, width, height) and 64x80 8-bit pixels; face numbers run on across both files.
# P_Face.s9: u32 count 2, then 2 x (BITMAPINFOHEADER + 256 x RGBX): the normal and a sepia palette.
SAN9_FACE_FILES = ["G_FaceS.s9", "G_FacSPK.s9"]
SAN9_SCENARIOS = [f"D_Sce{k:03d}.S9" for k in range(1, 21)]
# S9gaiji.tte glyphs used in names: the SAN8 ones plus these. U+E06A is 孫𩅦's name (Sun Xiu's eldest son)
SAN9_GAIJI = {**SAN8_GAIJI, 0xE001: "昱", 0xE002: "彧", 0xE008: "汜", 0xE00A: "鄧", 0xE010: "晙", 0xE01B: "琮",
              0xE021: "琦", 0xE033: "諶", 0xE035: "昕", 0xE048: "嘏", 0xE050: "珝", 0xE055: "甯", 0xE065: "璜",
              0xE067: "璿", 0xE068: "騄", 0xE069: "紞", 0xE06A: "\U00029166"}
SAN9_PERSONS = 700


def load_san9_faces(game_dir) -> list[bytes]:
    faces = []
    for name in SAN9_FACE_FILES:
        with open(os.path.join(game_dir, name), "rb") as f:
            data = f.read()
        assert struct.unpack_from("<I", data)[0] == len(data)
        o = 4
        while o < len(data):
            size, _, w, h = struct.unpack_from("<4I", data, o)
            assert (size, w, h) == (16 + 64 * 80, 64, 80)
            faces.append(data[o + 16:o + size])
            o += size
    return faces


def load_san9_palettes(palette) -> list[list[str]]:
    with open(palette, "rb") as f:
        data = f.read()
    count = struct.unpack_from("<I", data)[0]
    return [[f"#{data[o + i * 4]:02x}{data[o + i * 4 + 1]:02x}{data[o + i * 4 + 2]:02x}" for i in range(256)]
            for o in (4 + k * (40 + 1024) + 40 for k in range(count))]


def load_san9_persons(game_dir) -> list[dict]:
    """The 700 people (kana order): id, name, kana, face number.

    Faces come from the "prsn" chunk of the D_Sce???.S9 RIFF files (134-byte records, +4 u16 id, +14 u16 face; the
    same in all 20 scenarios, records 700-799 are new-officer slots). Names are in part 0 of M_MsgPK.s9 (LS11), from
    阿会喃 on: surname, given name, style name and kana (ESC k ... ESC H) separated by 05 05 05."""
    faces = None
    for name in SAN9_SCENARIOS:
        with open(os.path.join(game_dir, name), "rb") as f:
            data = f.read()
        i = data.index(b"prsn")
        prsn = data[i + 8:i + 8 + struct.unpack_from("<I", data, i + 4)[0]]
        assert all(struct.unpack_from("<H", prsn, k * 134 + 4)[0] == k for k in range(SAN9_PERSONS))
        f = [struct.unpack_from("<H", prsn, k * 134 + 14)[0] for k in range(SAN9_PERSONS)]
        assert faces in (None, f)
        faces = f
    with open(os.path.join(game_dir, "M_MsgPK.s9"), "rb") as f:
        msg = ls11.ls11_decode_parts(f.read())[0]
    parts = msg[msg.index("阿会".encode("cp932")):].split(b"\x05\x05\x05")

    def text(b):
        return "".join(SAN9_GAIJI.get(ord(c), c) for c in b.decode("cp932"))

    return [{"id": k, "name": text(parts[4 * k]) + text(parts[4 * k + 1]),
             "kana": parts[4 * k + 3][2:-2].decode("cp932"), "face": faces[k]} for k in range(SAN9_PERSONS)]


# 三國志X PK (Steam): Grp/GrpFaceS.s10 and the PK's Grp/GpkFaceS.s10 are "SAN10GRP" archives: u16 count at 12, an
# LS11 dictionary at 20-276, then 24-byte entries (u32 width, height, size, packed size, offset, flags); an entry is
# LS11-packed when its packed size differs, and holds width x height 8-bit pixels and a 256 x BGRX palette.
# The left- and right-facing versions of a face are separate entries sharing a palette.
SAN10_FACE_FILES = ["GrpFaceS.s10", "GpkFaceS.s10"]
# D_FacTbl.s10 / D_FacPK.s10: u16 count, then four u16 tables of 885 / 40 slots; the first maps a face code to the
# entry of the face as drawn (0xFFFF = no face). The PK's faces have codes 4000 + k (San10WPK.exe 0x40A130)
SAN10_FACE_TABLES = ["D_FacTbl.s10", "D_FacPK.s10"]
SAN10_PK_FACE_CODE = 4000
# Scenario files: 650 officer records of 66 bytes from 23001: +14 u16 index (kana order), +20 u16 biography number,
# +22 u16 face code. Names are in San10WPK.exe (.rdata/.data are not encrypted by the SteamStub): pointer tables of
# 650 u32 VAs (image base 0x400000) to the surname, given name, style name and reading (half-width kana, full name)
SAN10_PERSONS = (23001, 66, 650)
SAN10_NAME_TABLES = {"sei": 0x8F0030, "mei": 0x8F0A58, "azana": 0x8F1480, "yomi": 0x8F1EA8}
# S10Gaiji.tte has the same glyphs as S9gaiji.tte, plus U+E031
SAN10_GAIJI = {**SAN9_GAIJI, 0xE031: "莒"}


def load_san10_grp(path) -> list[tuple[int, int, bytes, bytes]]:
    """(width, height, pixels, BGRX palette) of every entry of a SAN10GRP archive."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"SAN10GRP"
    dic = data[20:276]
    entries = []
    for i in range(struct.unpack_from("<H", data, 12)[0]):
        w, h, size, packed, start, _ = struct.unpack_from("<6I", data, 276 + 24 * i)
        raw = data[start:start + packed]
        if packed != size:
            raw = ls11.recover(ls11.get_codes(raw), dic)[:size]
        entries.append((w, h, raw[:w * h], raw[w * h:w * h + 1024]))
    return entries


def load_san10_face_table(path) -> list[int]:
    """Face code -> archive entry (None = no face), from the first table of D_FacTbl.s10 / D_FacPK.s10."""
    with open(path, "rb") as f:
        data = f.read()
    slots = (len(data) - 2) // 8
    return [None if e == 0xFFFF else e for e in struct.unpack_from(f"<{slots}H", data, 2)]


def load_san10_persons(exe_path, scenario) -> list[dict]:
    """The 650 officers in index (kana) order: id, name, style name, kana, face code."""
    with open(exe_path, "rb") as f:
        exe = f.read()
    with open(scenario, "rb") as f:
        sce = f.read()

    def text(va):
        o = va - 0x400000
        return "".join(SAN10_GAIJI[ord(c)] if 0xE000 <= ord(c) <= 0xF8FF else c
                       for c in exe[o:exe.index(b"\0", o)].decode("cp932"))

    start, size, count = SAN10_PERSONS
    persons = []
    for k in range(count):
        r = sce[start + k * size:start + (k + 1) * size]
        assert struct.unpack_from("<H", r, 14)[0] == k
        names = {key: text(struct.unpack_from("<I", exe, t - 0x400000 + 4 * k)[0])
                 for key, t in SAN10_NAME_TABLES.items()}
        persons.append({"id": k, "name": names["sei"] + names["mei"], "azana": names["azana"], "kana": names["yomi"],
                        "face": struct.unpack_from("<H", r, 22)[0]})
    return persons


# 三國志11 PK (Steam): media/face/San11Face00.fce is "FACE@" + u32 2200, u32 6600 at 12, 2200 u32 (unknown), then
# 6600 (u32 offset, u32 size) entries (size 0 = empty). An entry is "WFTX0010", u32 size, u32 1, u16 width, height,
# u8 bpp, 3 flag bytes, then pixels: 24 bit is top-down B, G, R; 8 bit is indices plus a 256 x RGBX palette.
# Entries 0-2199 are the 240 x 240 face k; 2200 + 2k + d (k < 1100) and 4400 + 2(k - 1100) + d are the 64 x 80 face k
# facing left (d = 0) and right (d = 1); the right-facing one is redrawn, not a plain mirror image.
SAN11_FACE_FILE = "San11Face00.fce"
# Scenario files (media/scenario/Scen000-013.s11): 850 person records of 152 bytes from 0x3BCD; +0 surname 5 bytes,
# +5 given name 5, +10 style name 5 (cp932 with gaiji at F040-, read as U+E000-), +15 reading 25 (full-width
# katakana, full name), +0x35 u16 face code, +0x37 sex (0 male, 1 female, 0xFF empty slot)
SAN11_PERSONS = (0x3BCD, 152, 850)
SAN11_GAIJI = {**SAN10_GAIJI, 0xE062: "臏"}


def load_san11_small_faces(path) -> dict[int, bytes]:
    """Face code -> 64 x 80 left-facing face as top-down RGBA."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:5] == b"FACE@"
    n1, n2 = struct.unpack_from("<II", data, 12)
    entries = struct.unpack_from(f"<{2 * n2}I", data, 20 + 4 * n1)
    faces = {}
    for k in range(2200):
        slot = 2200 + 2 * k if k < 1100 else 4400 + 2 * (k - 1100)
        start, size = entries[2 * slot:2 * slot + 2]
        if not size:
            continue
        assert data[start:start + 8] == b"WFTX0010"
        w, h, bpp = struct.unpack_from("<HHB", data, start + 16)
        assert (w, h) == (64, 80)
        px = data[start + 24:start + 24 + w * h * bpp // 8]
        if bpp == 8:
            pal = data[start + 24 + w * h:start + 24 + w * h + 1024]
            px = b"".join(pal[c * 4:c * 4 + 3][::-1] for c in px)
        rgba = bytearray(b"\xff") * (w * h * 4)
        rgba[0::4], rgba[1::4], rgba[2::4] = px[2::3], px[1::3], px[0::3]
        faces[k] = bytes(rgba)
    return faces


def load_san11_persons(scenario) -> list[dict]:
    """The 850 person records: id, name, style name, kana, face code, sex."""
    with open(scenario, "rb") as f:
        data = f.read()

    def text(b):
        return "".join(SAN11_GAIJI.get(ord(c), c) for c in b.split(b"\0")[0].decode("cp932"))

    start, size, count = SAN11_PERSONS
    persons = []
    for k in range(count):
        r = data[start + k * size:start + (k + 1) * size]
        persons.append({"id": k, "name": text(r[0:5]) + text(r[5:10]), "azana": text(r[10:15]),
                        "kana": text(r[15:40]), "face": struct.unpack_from("<H", r, 0x35)[0], "sex": r[0x37]})
    return persons


# 三國志12 PK (Steam): Data/KAO_W_S.S12 is a LINK of 2000 GT1G0500 textures (+0x26 log2 height << 4 | log2 width,
# B, G, R, A from +0x2C), each cropped by the 12-byte rect table (u16 x, y, w, h) at +0x10 to its 90 x 128 face;
# an empty slot is 1 x 1. The added faces are LINKs of the same kind whose face numbers are a .dat (u32 count, u32s).
SAN12_FACE_FILES = [("Data/KAO_W_S.S12", None), ("AddKao00/ADD00_KAO_W_S.S12", "AddKao00/ADD00.dat"),
                    ("PK/AddKao20/ADD20_KAO_W_S.S12", "PK/AddKao20/ADD20.dat"),
                    ("PK/AddKao21/ADD21_KAO_W_S.S12", "PK/AddKao21/ADD21.dat"),
                    ("PK/AddKao21/SP0_KAO_W_S.S12", "PK/AddKao21/SP0.dat")]
# Scenario*.dat: ILNK; every part but 0 is encrypted from seed 0xE0A (San12WPK.exe 0x5F8D90). The person part is
# 1500 bit-field records of 292 bytes (PK) or 264 (base): +4 given name 5 bytes, +9 surname 5, +0xE reading
# (half-width katakana, full name), cp932 with gaiji at F040- (read as U+E000-); bit 482 is the 11-bit face number
SAN12_PERSONS = 1500
SAN12_FACE_BIT = 482
SAN12_GAIJI = {0xE000: "瓚", 0xE003: "郃", 0xE004: "蒯", 0xE006: "傕", 0xE009: "詡", 0xE00C: "龐", 0xE00D: "繇",
               0xE00E: "邈", 0xE00F: "騭", 0xE011: "闞", 0xE012: "玠", 0xE014: "邢", 0xE015: "歆", 0xE016: "闓",
               0xE018: "譙", 0xE019: "琬", 0xE01A: "郝", 0xE01D: "褚", 0xE025: "璝", 0xE032: "綝", 0xE037: "笮",
               0xE038: "祜", 0xE039: "蕤", 0xE03B: "毌", 0xE03D: "瓘", 0xE03F: "琰", 0xE043: "鞏", 0xE044: "眭",
               0xE04F: "宓", 0xE051: "禕", 0xE056: "蹋", 0xE05A: "氐", 0xE062: "臏", 0xE063: "淩", 0xE064: "嬴",
               0xE065: "璜", 0xE06F: "罃", 0xE0D4: "嬀"}


def load_san12_faces(game_dir, files=SAN12_FACE_FILES) -> dict[int, tuple[int, int, bytes]]:
    """Face number -> (w, h, top-down RGBA) of every 90 x 128 face in files."""
    faces = {}
    for name, numbers in files:
        with open(os.path.join(game_dir, name), "rb") as f:
            data = f.read()
        assert data[:4] == b"LINK"
        count, rects = struct.unpack_from("<I", data, 4)[0], struct.unpack_from("<I", data, 0x10)[0]
        if numbers:
            with open(os.path.join(game_dir, numbers), "rb") as f:
                ids = f.read()
            ids = struct.unpack_from(f"<{count}I", ids, 4)
        else:
            ids = range(count)
        for k, face in enumerate(ids):
            start, size = struct.unpack_from("<II", data, 0x20 + 8 * k)
            x, y, w, h = struct.unpack_from("<4H", data, rects + 12 * k)
            if w <= 1:
                continue
            t = data[start:start + size]
            assert t[:8] == b"GT1G0500"
            width = 1 << (t[0x26] & 15)
            rgba = bytearray()
            for row in range(y, y + h):
                o = 0x2C + (row * width + x) * 4
                line = bytearray(t[o:o + w * 4])
                line[0::4], line[2::4] = line[2::4], line[0::4]
                rgba += line
            assert face not in faces
            faces[face] = (w, h, bytes(rgba))
    return faces


def san12_decrypt(data: bytes, seed: int = 0xE0A) -> bytes:
    """A part of a Scenario*.dat: an LCG word (s >> 16) per step; odd: XOR the next word into 2 bytes, else (or
    with 1 byte left) XOR (r >> 8 ^ r) & 0xFF of the next word into 1 byte."""
    out, s, i, n = bytearray(data), seed, 0, len(data)
    while i < n:
        s = (s * 0x6C078965 + 0x3039) & 0xFFFFFFFF
        odd = s >> 16 & 1
        s = (s * 0x6C078965 + 0x3039) & 0xFFFFFFFF
        r = s >> 16
        if n - i >= 2 and odd:
            out[i] ^= r & 0xFF
            out[i + 1] ^= r >> 8
            i += 2
        else:
            out[i] ^= (r >> 8 ^ r) & 0xFF
            i += 1
    return bytes(out)


def load_san12_persons(path, size=292) -> list[dict]:
    """The 1500 person records: id, name, kana, face (an empty slot has no name)."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"ILNK"
    n = struct.unpack_from("<I", data, 4)[0]
    offsets = list(struct.unpack_from(f"<{n}I", data, 8)) + [len(data)]
    part, = [san12_decrypt(data[a:b]) for a, b in zip(offsets[1:], offsets[2:]) if b - a == SAN12_PERSONS * size]

    def text(b):
        return "".join(SAN12_GAIJI.get(ord(c), c) for c in b.split(b"\0")[0].decode("cp932"))

    persons = []
    for k in range(SAN12_PERSONS):
        r = part[k * size:(k + 1) * size]
        persons.append({"id": k, "name": text(r[9:14]) + text(r[4:9]), "kana": text(r[14:]),
                        "face": int.from_bytes(r, "little") >> SAN12_FACE_BIT & 0x7FF})
    return persons


# 三國志13 PK (Steam): DATA0.S13 is 32-byte entries (u64 offset into DATA1.S13, size, stored size, compressed); a
# compressed entry is "zp1\0" + u32 size, u32 chunk size, u32 chunk count, the chunk sizes, then from 0x800 the
# chunks (each aligned to 0x80) of u32 length + zlib. Many entries are "u32 count, count x (u32 offset, u32 size)"
# archives. XL tables: "XL", u16 version, u16 size, u16 columns, u16 rows, u16 row size, u16 header size, a type
# byte per column from +0x10; a string column is a u32 offset from the header size.
SAN13_PK = "pk/"
SAN13_NAMES = 2  # item 0 of item 0: the string table (names from 6535, a 1450-long run per field)
SAN13_NAMES_TC = 1416  # the same, Big5
SAN13_NAME_FIELDS = 6535, 1450  # surname, given name, style name, surname reading, given name reading…
SAN13_FACES = 20  # 72 x 72 faces: 128 x 128 BC3 G1T textures; picture p is item p (< 1271) or p - 179 (>= 1450)
SAN13_OWNERS = 1398  # the person of picture i + 1 (-1 none); the base game's is item 1047
SAN13_BASE_OWNERS = 1047
SAN13_VERSIONS = 1395  # version code of picture i + 1 (its name is string 1680 + code of item 1 of item 0 of 2)
SAN13_GAIJI_TC = {b"\xfa\x40": "伷", b"\xfa\x41": "璝", b"\xfa\x45": "儁"}  # the Big5 names' own gaiji


def san13_entry(game_dir, i, base=SAN13_PK) -> bytes:
    with open(os.path.join(game_dir, base + "DATA0.S13"), "rb") as f:
        f.seek(32 * i)
        offset, _, stored, _ = struct.unpack("<4Q", f.read(32))
    with open(os.path.join(game_dir, base + "DATA1.S13"), "rb") as f:
        f.seek(offset)
        return san13_unzip(f.read(stored))


def san13_unzip(b: bytes) -> bytes:
    if b[:4] != b"zp1\0":
        return b
    size, _, n = struct.unpack_from("<3I", b, 4)
    out, o = bytearray(), (16 + 4 * n + 0x7FF) // 0x800 * 0x800
    for s in struct.unpack_from(f"<{n}I", b, 16):
        o = (o + 0x7F) // 0x80 * 0x80
        out += zlib.decompress(b[o + 4:o + 4 + struct.unpack_from("<I", b, o)[0]])
        o += s
    assert len(out) == size
    return bytes(out)


def san13_items(b: bytes) -> list[bytes]:
    n = struct.unpack_from("<I", b)[0]
    return [b[o:o + s] for o, s in (struct.unpack_from("<2I", b, 4 + 8 * k) for k in range(n))]


def san13_strings(b: bytes, encoding: str, gaiji: dict[bytes, str] = {}) -> list[str]:
    """The first column (strings) of an XL table; gaiji are 2-byte codes outside the encoding."""
    assert b[:2] == b"XL"
    rows, size, header = struct.unpack_from("<3H", b, 8)
    out = []
    for r in range(rows):
        o = header + struct.unpack_from("<I", b, header + r * size)[0]
        t = b[o:b.index(b"\0", o)]
        for code, c in gaiji.items():
            t = t.replace(code, c.encode(encoding, "xmlcharrefreplace"))
        # other strings than the names (biographies…) have more codes outside the encoding
        out.append(re.sub(r"&#(\d+);", lambda m: chr(int(m[1])), t.decode(encoding, "replace")))
    return out


def load_san13_faces(game_dir) -> list[bytes]:
    """The 72 x 72 RGBA of each item of the face entry."""
    from PIL import Image
    faces = []
    for t in san13_items(san13_entry(game_dir, SAN13_FACES)):
        t = san13_unzip(t)
        fmt, dim = t[0x25], t[0x26]
        w, h = 1 << (dim & 15), 1 << (dim >> 4)
        start = 0x2C + struct.unpack_from("<I", t, 0x2C)[0]
        assert fmt == 8
        faces.append(Image.frombytes("RGBA", (w, h), t[start:start + w * h], "bcn", 3).crop((0, 0, 72, 72)).tobytes())
    return faces


def san13_face_item(picture: int) -> int:
    return picture if picture < 1271 else picture - 179


def load_san13_persons(game_dir) -> dict:
    """{"names": person -> (name, nameZh, reading), "pictures": person -> pictures (in order), "versions": picture ->
    version name, "base": persons of the base game}; the Japanese names have gaiji (U+E000-) read off the
    Traditional Chinese names."""
    def strings(item, encoding, gaiji={}):
        return san13_strings(san13_items(san13_items(san13_entry(game_dir, item))[0])[0], encoding, gaiji)

    ja, tc = strings(SAN13_NAMES, "cp932"), strings(SAN13_NAMES_TC, "cp950", SAN13_GAIJI_TC)
    start, run = SAN13_NAME_FIELDS
    gaiji = {}
    for k in range(2 * run):
        a, b = ja[start + k], tc[start + k]
        if len(a) == len(b):
            for x, y in zip(a, b):
                if 0xE000 <= ord(x) <= 0xF8FF:
                    assert gaiji.setdefault(x, y) == y
    owners = san13_entry(game_dir, SAN13_OWNERS)
    pictures = {}
    for i, p in enumerate(struct.unpack_from(f"<{len(owners) // 2}h", owners)):
        if p >= 0:
            pictures.setdefault(p, []).append(i + 1)
    names = {}
    for p in pictures:
        name = "".join(gaiji.get(c, c) for c in ja[start + p] + ja[start + run + p])
        reading = " ".join(r for r in (ja[start + 3 * run + p], ja[start + 4 * run + p]) if r)
        names[p] = (name, tc[start + p] + tc[start + run + p], reading)
        assert "\ufffd" not in "".join(names[p])
    codes = struct.unpack_from("<1645h", san13_entry(game_dir, SAN13_VERSIONS))
    labels = san13_items(san13_items(san13_entry(game_dir, SAN13_NAMES))[0])[1]
    labels = san13_strings(labels, "cp932")
    versions = {i + 1: labels[1680 + c] for i, c in enumerate(codes) if c >= 0}
    owners = san13_entry(game_dir, SAN13_BASE_OWNERS, "")
    base = set(struct.unpack_from(f"<{len(owners) // 2}h", owners)) - {-1}
    return {"names": names, "pictures": pictures, "versions": versions, "base": base}


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
