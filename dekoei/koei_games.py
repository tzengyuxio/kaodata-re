import bitarray
import click
import unicodedata
from ls11 import *
from rich.table import Table
from PIL import ImageFile
from utils import *
from koei_person import *
from itertools import chain
ImageFile.LOAD_TRUNCATED_IMAGES = True  # for KOUKAI3 palette file


@click.group()
def eiketsu():
    """三國志英傑傳

    FACEDAT.R3  461KB LS11
    FACEDAT.R3  342KB LS11
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def eiketsu_face(face_file, out_dir, prefix):
    palette = color_codes_to_palette(
        ['#777777x', '#2045AA', '#EF6500', '#CF75AA', '#00BA75', '#8ACFFF', '#FFCF55', '#FFFFFF',
         '#000000', '#2045AA', '#0000FFx', '#FFFF00x', '#FF00FFx', '#00FFFFx', '#AAAAAAx', '#BBBBBBx']  # 使用: 1~8, 9(未抓圖證實), 15未使用
    )
    face_w, face_h = 64, 80
    images = []
    os.makedirs(out_dir, exist_ok=True)
    with open(face_file, 'rb') as f:
        if f.read(4) != b'LS11':
            print('Not LS11 file: DOS version?')
            f.seek(0)
            count = 240
            offset_infos = []
            for _ in range(count):
                # offset 這部分沒問題
                #   後來發現這部分 offset 跟 SAN4 KAODATA 一樣 340*6 之後開始頭像資料
                #   (340 張頭像, 每個 offset info 6 bytes)
                #   SAN4 KAODATA 的資料是以 0x04000500 開頭，這是圖像尺寸，很有可能與 npk_3bits 相同
                offset = int.from_bytes(f.read(4), LITTLE_ENDIAN)
                size = int.from_bytes(f.read(2), LITTLE_ENDIAN)
                offset_infos.append((offset, size))
            for i in range(3):
                offset, size = offset_infos[i]
                f.seek(offset)
                data = f.read(size)
                print(f'#{i} offset={offset} size={size}')
                # 如何解析 這部分仍是一團謎
                #   每一段 data 開頭都有類似的 7bytes: 02540850 003303
                #   推測可能是某種固定 header 經過壓縮，所以開頭 7 bytes 都一致
                #   但如果是 NPK 經過 LS11 壓縮，又沒有字典可查
                #   可能要把這段 data 寫成檔案試著用各種方式解壓看看
                # begin - unknown how to unpack
                color_indexed_data = unpack_npk(data[8:], face_w)
                image = Image.new('RGB', (face_w, face_h), BGCOLOR)
                for px_index, color_index in enumerate(color_indexed_data):
                    if px_index >= face_w * face_h:
                        break
                    y, x = divmod(px_index, face_w)
                    c = palette[color_index]
                    image.putpixel((x, y), c)
                # end - unknown how to unpack
                images.append(image)
            # save single faces
            images = {str(i): img for i, img in enumerate(images)} if isinstance(images, list) else images
            save_single_images(images, out_dir, prefix)
            return
        f.seek(0)
        npks = ls11_decode_parts(f.read(), print_only=False)
        for idx, npk_data in enumerate(npks):
            width = int.from_bytes(npk_data[0x0c:0x0e], LITTLE_ENDIAN)
            height = int.from_bytes(npk_data[0x0e:0x10], LITTLE_ENDIAN)
            # raw = list(npk_data[0x10:0x30])
            # color_data = [struct.unpack('<h', bytes(raw[i:i+2]))[0] for i in range(0, len(raw), 2)]
            # palette = [conv_palette(p) for p in color_data]
            color_indexed_data = unpack_npk(npk_data[0x30:], width)
            image = Image.new('RGB', (width, height), BGCOLOR)
            for px_index, color_index in enumerate(color_indexed_data):
                y, x = divmod(px_index, width)
                c = palette[color_index]
                image.putpixel((x, y), c)
            images.append(image)
            # image.save(f'{out_dir}/{prefix}{idx:03d}.png')
    # save face index: all, special, mob
    save_index_image(images, 64, 80, 16, f'{out_dir}/{prefix}00-INDEX.png')
    # save single faces
    images = {str(i): img for i, img in enumerate(images)} if isinstance(images, list) else images
    save_single_images(images, out_dir, prefix)

    # extract_images(face_file, face_w, face_h, palette, out_dir, prefix)


eiketsu.add_command(eiketsu_face, 'face')


def decode_tfdce(src: bytes) -> tuple[int, int, list[list[bytearray]]]:
    """Decode an image of TFDED.COM (TF-DCE 5.11, the int 62h driver of 英傑傳 DOS).

    Returns (bytes per row, rows, planes), planes[p][row] being the bytes of plane p.
    Each coded plane is a byte stream laid out column by column (a byte column is 8 pixels),
    going down the first column, up the next and so on. See notes/eiketsu.md.
    """
    pos = src[0]  # header length
    w = src[pos]
    h = src[pos + 1] | src[pos + 2] << 8
    codes = src[pos + 3] | src[pos + 4] << 8  # 4 bits per plane, in stream order
    order = [(src[pos + 5] >> (2 * k)) & 3 for k in range(4)]  # plane of each stream slot
    flags = src[pos + 6]
    pos += 7
    if flags & 0x40:  # palette
        pos += 32
    dic = []
    if flags & 0x20:  # 2-byte codes used by opcodes 00-1F
        n = src[pos]
        dic = [(src[pos + 1 + 2 * i], src[pos + 2 + 2 * i]) for i in range(n)]
        pos += 1 + 2 * n
    planes = [[bytearray(w) for _ in range(h)] for _ in range(4)]
    total = w * h

    def rc(n):
        col, k = divmod(n, h)
        return (k if col % 2 == 0 else h - 1 - k), col

    def rol(b, s):
        s &= 7
        return ((b << s) | (b >> (8 - s))) & 0xff

    xforms = (lambda b: b, lambda b: b ^ 0xff, lambda b: rol(b, 7), lambda b: rol(b, 1))
    masks = [0x00, 0xff, 0x55, 0xaa]  # recent AND masks, kept over all planes
    for p in order:
        code = codes & 0xf
        codes >>= 4
        plane = planes[p]
        if code == 1:  # solid
            for row in plane:
                row[:] = bytes([src[pos]]) * w
            pos += 1
        elif code == 2:  # copy of another plane
            other = planes[order[src[pos]]]
            pos += 1
            for y in range(h):
                plane[y][:] = other[y]
        elif code == 3:
            n = 0
            while n < total:
                c = src[pos]
                pos += 1
                arg = None
                if c < 0x20:
                    c, arg = dic[c]
                    if c >> 4 in (0, 1, 6):
                        continue
                hi = c >> 4
                if arg is None and hi not in (6, 7) and not (hi in (5, 9) and c & 0xc == 0xc):
                    arg = src[pos]
                    pos += 1
                if hi >= 10:  # run
                    cnt, f = (c - 0x9e) & 0xff, lambda i, y, x, b=arg: b
                elif hi == 7:  # literal
                    if arg is not None:
                        lit = bytes([arg])
                    else:
                        lit = src[pos:pos + (c & 0xf) + 1]
                        pos += len(lit)
                    cnt, f = len(lit), lambda i, y, x, lit=lit: lit[i]
                elif hi in (6, 8):  # repeated byte pair
                    if hi == 6:
                        pair = src[pos:pos + 2]
                        pos += 2
                    else:
                        pair = ((arg & 0xf) * 0x11, (arg >> 4) * 0x11)
                    cnt, f = ((c & 0xf) + 1) * 2, lambda i, y, x, pair=pair: pair[i & 1]
                elif hi == 4:  # copy from d byte columns to the left
                    cnt, f = arg + 2, lambda i, y, x, d=(c & 0xf) + 1: plane[y][x - d]
                elif hi == 2:  # copy from d bytes back in the stream
                    def f(i, y, x, d=arg):
                        sy, sx = rc(n - d)
                        return plane[sy][sx]
                    cnt = (c & 0xf) + 3
                elif hi == 3:  # another plane, transformed
                    cnt = arg + 2
                    f = lambda i, y, x, o=planes[order[(c >> 2) & 3]], t=xforms[c & 3]: t(o[y][x])
                else:  # 5, 9: another plane AND a mask (9: mask rotating per byte)
                    if arg is None:
                        o, mask, cnt = planes[order[c & 3]], src[pos], src[pos + 1] + 2
                        pos += 2
                        masks[2:] = [mask, masks[2]]
                    else:
                        o, k, cnt = planes[order[(c >> 2) & 3]], c & 3, arg + 2
                        mask = masks[k]
                        if k:
                            masks[k - 1], masks[k] = mask, masks[k - 1]
                    r = 0 if hi == 5 else 1 if mask in (0x55, 0xaa) else 2
                    f = lambda i, y, x, o=o, m=mask, r=r: o[y][x] & rol(m, r * i)
                for i in range(cnt):
                    y, x = rc(n)
                    plane[y][x] = f(i, y, x)
                    n += 1
                    if n >= total:
                        break
    return w, h, planes


def load_eiketsu_dos_faces(facedat) -> list[bytes]:
    """FACEDAT.R3 (DOS): 240 x (u32 offset from the table end, u16 size), TF-DCE images of 64x80, 8 colours."""
    with open(facedat, "rb") as f:
        data = f.read()
    faces = []
    for i in range(240):
        off, size = struct.unpack_from("<IH", data, i * 6)
        w, h, planes = decode_tfdce(data[240 * 6 + off:240 * 6 + off + size])
        px = bytearray(w * 8 * h)
        for y in range(h):
            for x in range(w * 8):
                bit = 0x80 >> (x & 7)
                px[y * w * 8 + x] = sum(1 << p for p in range(4) if planes[p][y][x >> 3] & bit)
        faces.append(bytes(px))
    return faces


# BAKDATA.R3 (DOS): 384 person records of 21 bytes from 0x1100 (256 officers, then troops and townsfolk);
# +0 name 6 bytes Big5 (NUL or space padded), +6 kana reading, +14 face
EIKETSU_DOS_PERSONS = (0x1100, 384, 21)


# PC-98 BAKDATA.R3 names are Shift-JIS with KOEI gaiji EB xx (glyphs in FONT.R3), read off the glyphs and the
# Chinese release's names for the same records (AE is drawn 鷙, the Chinese has 騭)
EIKETSU_PC98_GAIJI = dict(zip(
    [0x9F, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA7, 0xA8, 0xA9, 0xAB, 0xAE, 0xAF, 0xB0, 0xB1, 0xB3, 0xB6, 0xB8,
     0xB9, 0xC0, 0xC1, 0xC4, 0xCA, 0xE2],
    "瓚昱彧郃蒯蔡傕汜詡鄧龐鷙畯闞玠邢禕琬郝琦琮璝褚邈"))


def load_eiketsu_pc98_persons(bakdata) -> list[tuple[str, int]]:
    """As load_eiketsu_dos_persons, for the PC-98 BAKDATA.R3."""
    with open(bakdata, "rb") as f:
        data = f.read()
    start, count, size = EIKETSU_DOS_PERSONS

    def name(raw: bytes) -> str:
        raw = raw.split(b"\0")[0]
        return "".join(EIKETSU_PC98_GAIJI[raw[i + 1]] if raw[i] == 0xEB else raw[i:i + 2].decode("cp932")
                       for i in range(0, len(raw), 2)).strip()
    return [(name(data[o:o + 6]), data[o + 14]) for o in range(start, start + count * size, size)]


def load_eiketsu_dos_persons(bakdata) -> list[tuple[str, int]]:
    """(name, face code) of every BAKDATA.R3 person record, in file order."""
    with open(bakdata, "rb") as f:
        data = f.read()
    start, count, size = EIKETSU_DOS_PERSONS
    return [(data[o:o + 6].split(b"\0")[0].decode("big5").strip(), data[o + 14])
            for o in range(start, start + count * size, size)]


# koukaiGD.exe: two mate tables (120 records of 27 bytes; 0x416190 copies table [0x4BFDA1] = protagonist),
# then the given-name and surname tables (13-byte Big5 slots); all file offsets
KOUKAIGD_WIN_MATES = (0x773E0, 0x78088)
KOUKAIGD_WIN_NAMES = (0x78D30, 0x79348)
# Sdata.dat: event people, 26-byte records (20-byte Big5 name, face at +23)
KOUKAIGD_WIN_EVENT = (0x9AA, 20, 26)
# Sdata.dat: tavern women, 19-byte records (12-byte Big5 name); woman k has portrait 0x61 + k (exe 0x425D87)
KOUKAIGD_WIN_TAVERN = (0x770, 30, 19)
KOUKAIGD_WIN_TAVERN_FACE = 0x61


def load_koukaigd_win_mates(exe) -> list[list[tuple[str | None, int]]]:
    """Per mate table: (name or None for an empty / player slot, face code) of every record."""
    with open(exe, "rb") as f:
        data = f.read()

    def name(table, i):
        o = table + i * 13
        return data[o:o + 13].split(b"\0")[0].decode("big5")

    tables = []
    for start in KOUKAIGD_WIN_MATES:
        rows = []
        for o in range(start, start + 120 * 27, 27):
            given, surname = data[o], data[o + 1]
            full = None if 0xFF in (given, surname) else \
                f"{name(KOUKAIGD_WIN_NAMES[0], given)}•{name(KOUKAIGD_WIN_NAMES[1], surname)}"
            rows.append((full, int.from_bytes(data[o + 2:o + 4], "little")))
        tables.append(rows)
    return tables


def load_koukaigd_win_events(sdata, extra=False) -> list[tuple[str, int]]:
    """(name, portrait) of the Sdata.dat event people; `extra`: the two records after them instead
    (加斯帕爾•比利, 長谷平藏), whose portrait byte is a placeholder."""
    with open(sdata, "rb") as f:
        data = f.read()
    start, count, size = KOUKAIGD_WIN_EVENT
    if extra:
        start, count = start + count * size, 2
    return [(data[o:o + 20].split(b"\0")[0].decode("big5"), data[o + 23])
            for o in range(start, start + count * size, size)]


def load_koukaigd_win_tavern(sdata) -> list[tuple[str, int]]:
    """(name, portrait) of the Sdata.dat tavern women."""
    with open(sdata, "rb") as f:
        data = f.read()
    start, count, size = KOUKAIGD_WIN_TAVERN
    return [(data[o:o + 12].split(b"\0")[0].decode("big5"), KOUKAIGD_WIN_TAVERN_FACE + k)
            for k, o in enumerate(range(start, start + count * size, size))]


# DATA1.LZW part 15 (the starting state; Sdata.dat of 大航海時代外伝): (offset, count, record size)
KOUKAI2_PC98_MATES = (0x612, 120, 50)  # given 13, surname 13, u16 face code, ..., +49 low nibble = face type
KOUKAI2_PC98_EVENT = (0x1D82, 20, 22)  # name 16, ..., +18 portrait
KOUKAI2_PC98_TAVERN = (0x1F3A, 30, 19)  # name 12, ...; the face is 0x61 + index (MAIN.EXE 0x25F15)


def load_koukai2_pc98_people(data1) -> tuple[list, list, list]:
    """Mates (name, face code, face type), event people and tavern women (name, portrait) of DATA1.LZW."""
    with open(data1, "rb") as f:
        data = ls11_decode_parts(f.read())[15]

    def name(raw):
        return raw.split(b"\0")[0].decode("cp932")

    start, count, size = KOUKAI2_PC98_MATES
    mates = [(name(data[o:o + 13]) + "・" + name(data[o + 13:o + 26]), int.from_bytes(data[o + 26:o + 28], "little"),
              data[o + 49] & 0xF) for o in range(start, start + count * size, size)]
    start, count, size = KOUKAI2_PC98_EVENT
    events = [(name(data[o:o + 16]), data[o + 18]) for o in range(start, start + count * size, size)]
    start, count, size = KOUKAI2_PC98_TAVERN
    tavern = [(name(data[o:o + 12]), 0x61 + k) for k, o in enumerate(range(start, start + count * size, size))]
    return mates, events, tavern

##############################################################################


@click.group()
def europe():
    """歐陸戰線

    FACE.DAT
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def europe_face(face_file, out_dir, prefix):
    palette = color_codes_to_palette(
        ['#000000', '#419241', '#B24120', '#F3C361', '#104192', '#6FAEAE', '#D371B2', '#F3F3F3']
    )
    face_w, face_h = 64, 80

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix)


europe.add_command(europe_face, 'face')

# DOS (Chinese): 22-byte commander records, name (KOEI TW code) at +0, nation bits at +9 (0xFF = empty), face at +20.
# SCEDATA has 7 scenarios of 40 records; MAIN.EXE (DGROUP = file 0x46B00) holds the 12 leaders at DGROUP 0x2D98.
EUROPE_SCENARIOS = (0x1772, 0x1D95, 7)
EUROPE_LEADERS = (0x46B00 + 0x2D98, 12)


def load_europe_dos_names(scedata, main_exe) -> dict[int, str]:
    """Name per face/person number; a few commanders are spelt differently between scenarios, the most
    frequent spelling wins (the first seen on ties)."""
    from collections import Counter
    with open(scedata, 'rb') as f:
        sce = f.read()
    with open(main_exe, 'rb') as f:
        main = f.read()
    first, stride, count = EUROPE_SCENARIOS
    spellings = {}
    for s in range(count):
        for r in range(40):
            rec = sce[first + s * stride + r * 22:first + s * stride + (r + 1) * 22]
            if rec[9] != 0xFF:
                spellings.setdefault(rec[20], Counter())[koei_tw_name(rec[:8])] += 1
    names = {face: c.most_common(1)[0][0] for face, c in spellings.items()}
    offset, count = EUROPE_LEADERS
    for r in range(count):
        rec = main[offset + r * 22:offset + (r + 1) * 22]
        names[rec[20]] = koei_tw_name(rec[:8])
    return names



# PC-88: the same 22-byte records with half-width katakana names; SCEDATA.CIM has 7 scenarios of 40,
# MAIN.COM the 6 leaders (faces 94-99)
EUROPE_PC88_SCENARIOS = (0x229, 0x1D64, 7)
EUROPE_PC88_LEADERS = (0x264, 6)


def load_europe_pc88_names(scedata, main_com) -> dict[int, str]:
    """Name per face/person number (every commander is spelt the same in all scenarios)."""
    with open(scedata, 'rb') as f:
        sce = f.read()
    with open(main_com, 'rb') as f:
        main = f.read()

    def name(rec):
        return unicodedata.normalize('NFKC', rec[:8].split(b'\0')[0].decode('cp932')).strip()

    first, stride, count = EUROPE_PC88_SCENARIOS
    names = {}
    for s in range(count):
        for r in range(40):
            rec = sce[first + s * stride + r * 22:first + s * stride + (r + 1) * 22]
            if rec[9] != 0xFF:
                names.setdefault(rec[20], name(rec))
    offset, count = EUROPE_PC88_LEADERS
    for r in range(count):
        rec = main[offset + r * 22:offset + (r + 1) * 22]
        names[rec[20]] = name(rec)
    return names


# X68000: the PC-88 records (half-width katakana) in SCEDATA scenarios of 0x2E21 bytes from 0x1518 (MAIN.Z 0x52930),
# commanders at +0x302; MAIN.Z (not packed) holds the 12 leaders (faces 94-105) at file 0x4369C. In the only
# dump (IA europe_sensen_1992_koei_disk_1_x68k) the sectors of scenarios 1-4 hold MSGRP.DAT data, so only
# scenarios 0, 5 and 6 can be read.
EUROPE_X68_SCENARIOS = (0x181A, 0x2E21, (0, 5, 6))
EUROPE_X68_LEADERS = (0x4369C, 12)


def load_europe_x68_names(scedata, main_z) -> dict[int, str]:
    """Name per face/person number from the readable scenarios and the leaders."""
    with open(scedata, 'rb') as f:
        sce = f.read()
    with open(main_z, 'rb') as f:
        main = f.read()

    def name(rec):
        return unicodedata.normalize('NFKC', rec[:8].split(b'\0')[0].decode('cp932')).strip()

    first, stride, scenarios = EUROPE_X68_SCENARIOS
    names = {}
    for s in scenarios:
        for r in range(40):
            rec = sce[first + s * stride + r * 22:first + s * stride + (r + 1) * 22]
            if rec[9] != 0xFF:
                names.setdefault(rec[20], name(rec))
    offset, count = EUROPE_X68_LEADERS
    for r in range(count):
        rec = main[offset + r * 22:offset + (r + 1) * 22]
        names[rec[20]] = name(rec)
    return names

##############################################################################


@click.group()
def kohryuki():
    """項劉記

    KAO.KR1
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def kohryuki_face(face_file, out_dir, prefix):
    palette = color_codes_to_palette(
        ['#000000', '#418200', '#C34100', '#E3A251', '#0030A2', '#71A2B2', '#B27171', '#F3E3D3']
    )
    face_w, face_h = 64, 80

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix)


@click.command(help='人物資料解析')
@click.option('-d', '--dir', 'game_dir', help="遊戲目錄", required=True)
@click.option('-t', '--to', 'to', help="Specify output format", default='rich', type=click.Choice(['rich', 'csv', 'json', 'markdown', 'md']))
@click.option('-s', '--scenario', 'scenario', help="Specify scenario number (starts from 1)", default=0)
def kohryuki_person(game_dir, to, scenario):
    """
    人物資料解析

    MAIN.EXE    人名 (offset: 264260, 17bytes)
    SNDT1.KR1   劇本1
    SNDT2.KR1   劇本2
    SNDT3.KR1   劇本3
    SNDT4.KR1   劇本4

    TODO(yuxioz): 中日文版差異
        - main.exe filename
        - main.exe offset
        - decode name with different encoding

    ./dekoei.py kohryuki person -d ~/DOSBox/kanso/
    ./dekoei.py kohryuki person -d ~/DOSBox/kanso/ --to csv > PERSONS_TABLE/kohryuki-persons-s1.csv
    """
    main_exe = os.path.join(game_dir, 'MAIN.EXE')
    # main_exe = os.path.join(game_dir, 'output.000.exe')

    def person_loader(main_exe, scenario=scenario):
        sn_file = os.path.join(game_dir, 'SNDT{}.KR1'.format(scenario+1))
        with open(main_exe, 'rb') as fmain, open(sn_file, 'rb') as fsn:
            fmain.seek(264260)  # 日文版
            # fmain.seek(276180) # 中文版
            fsn.seek(4)
            person_data = []
            for _ in range(92):
                d1 = fmain.read(17)
                d2 = fsn.read(10)
                person_data.append(b''.join([d1, d2]))
        return person_data
    person_data = person_loader(main_exe)

    persons = load_person(person_data, kohryuki_format, KOHRYUKIPerson)
    print_table(kohryuki_table_title, kohryuki_headers, persons, to)


kohryuki.add_command(kohryuki_face, 'face')
kohryuki.add_command(kohryuki_person, 'person')

# DOS (Chinese) MAIN.EXE is PKLITE packed; the 92 x 17-byte name table is at 0x3D0D4 of the unpacked image
KOHRYUKI_DOS_NAMES = 0x3D0D4


def load_kohryuki_dos_names(main_exe) -> list[str]:
    import pklite
    with open(main_exe, 'rb') as f:
        image = pklite.depklite(f.read())
    return [koei_tw_name(image[KOHRYUKI_DOS_NAMES + i * 17:KOHRYUKI_DOS_NAMES + i * 17 + 6]) for i in range(92)]


# X68000 MAIN.Z (not packed): 92 x 18-byte records from 0x50F1A, Shift-JIS name +0 (7 bytes), kana +7 (8 bytes)
KOHRYUKI_X68_NAMES = 0x50F1A
KOHRYUKI_X68_GAIJI = {0xEBB7: "蒯", 0xEBE1: "酈", 0xEBE2: "噲", 0xEBE3: "芮", 0xEBE5: "卬", 0xEBE6: "靳"}


def load_kohryuki_x68_names(main_z) -> list[str]:
    with open(main_z, 'rb') as f:
        main = f.read()
    names = []
    for i in range(92):
        raw = main[KOHRYUKI_X68_NAMES + i * 18:][:7].split(b'\0')[0]
        name = ''
        for j in range(0, len(raw), 2):
            code = int.from_bytes(raw[j:j + 2], 'big')
            name += KOHRYUKI_X68_GAIJI.get(code) or raw[j:j + 2].decode('cp932')
        names.append(name)
    return names

##############################################################################


@click.group()
def ishin():
    """維新之嵐

    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def ishin_face(face_file, out_dir, prefix):
    """
    ./dekoei.py ishin face -f kao/ISHIN_維新の嵐A.fdi --prefix ISHIN_PC98_F

    專有顏:105, 守衛:1, 背景:8, 大眾:約56格大小
    """
    palette = color_codes_to_palette(
        ['#000000', '#00FF00', '#FF0000', '#FFFF00', '#0000FF', '#00FFFF', '#FF00FF', '#FFFFFF']
    )
    face_w, face_h = 48, 80
    num_part = 105
    part_size = calc_part_size(face_w, face_h, len(palette), hh=True)
    loader = create_floppy_image_stream(face_file, [(582656, num_part * part_size)], part_size)

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix, hh=True, data_loader=loader)


ishin.add_command(ishin_face, 'face')

##############################################################################


@click.group()
def ishin2():
    """維新之嵐2

    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def ishin2_face(face_file, out_dir, prefix):
    pass


ishin2.add_command(ishin2_face, 'face')

##############################################################################


@click.group()
def koukai():
    """大航海時代"""
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output')
@click.option('--prefix', 'prefix', default='')
def koukai_face(face_file, out_dir, prefix):
    """
    KAO.PUT
    """
    palette = color_codes_to_palette(
        ['#000000', '#55FF55', '#FF5555', '#FFFF55', '#5555FF', '#55FFFF', '#FF55FF', '#FFFFFF']
    )
    face_w, face_h = 64, 80
    part_size = calc_part_size(face_w, face_h, len(palette), hh=True)

    def stream() -> typing.Generator[bytes, None, None]:
        with open(face_file, 'rb') as f:
            f.seek(47616)
            for _ in range(34):
                yield f.read(part_size)

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix, num_part=34, hh=True, data_loader=stream)


koukai.add_command(koukai_face, 'face')

# DOS (Chinese) SHINARIO.CIM: 21 women x 16 bytes at 0x7D0, then 41 men x 20 bytes at 0x920 (see notes/koukai.md)
KOUKAI_WOMEN = (0x7D0, 16, 21)
KOUKAI_MEN = (0x920, 20, 41)


def load_koukai_dos_people(shinario) -> tuple[list[tuple[str, int, int, int]], list[str]]:
    """Men as (name, face byte 0x11, face byte 0x12, nation), women as names."""
    with open(shinario, 'rb') as f:
        data = f.read()
    off, size, n = KOUKAI_MEN
    men = []
    for i in range(n):
        r = data[off + i * size:off + (i + 1) * size]
        men.append((koei_tw_name(r[:15]), r[0x11], r[0x12], r[0x13] >> 4))
    off, size, n = KOUKAI_WOMEN
    return men, [koei_tw_name(data[off + i * size:off + i * size + 15]) for i in range(n)]


KOUKAI_PC98_SHIFT = -0x20  # PC-98 SHINARIO.CIM: the same records, 0x20 bytes earlier
KOUKAI_PC88_SHIFT = -0xAC  # PC-88 SHINARIO.CIM: the same records, 0xAC bytes earlier


def load_koukai_pc98_people(shinario, pc88=False) -> tuple[list[tuple[str, int, int, int]], list[str]]:
    """As load_koukai_dos_people, names in Shift-JIS; pc88 reads the PC-88 SHINARIO.CIM."""
    shift = KOUKAI_PC88_SHIFT if pc88 else KOUKAI_PC98_SHIFT
    with open(shinario, 'rb') as f:
        data = f.read()

    def name(raw: bytes) -> str:
        return raw.split(b"\0")[0].decode("shift_jis")
    off, size, n = KOUKAI_MEN
    off += shift
    men = []
    for i in range(n):
        r = data[off + i * size:off + (i + 1) * size]
        men.append((name(r[:15]), r[0x11], r[0x12], r[0x13] >> 4))
    off, size, n = KOUKAI_WOMEN
    off += shift
    return men, [name(data[off + i * size:off + i * size + 15]) for i in range(n)]

# GENGHIS DOS MDATA.CIM / SDATA.CIM: kind -> (offset, groups, group size, records, record size, face offset)
GENGHIS_TABLES = {"ruler": (0x2E2, 1, 0, 27, 43, 0x27), "family": (0x76C, 4, 205, 5, 41, 0x27),
                  "son": (0xE46, 4, 160, 5, 32, 0x1E), "general": (0xAEB, 1, 0, 26, 33, 0x1F),
                  "woman": (0x1E8A, 1, 0, 40, 34, 0x1C)}


def load_genghis_dos_people(cim) -> dict[str, list[tuple[str, list[int]]]]:
    """(name, face codes) per kind, in table order; women have three faces (normal, smile, cry)."""
    with open(cim, 'rb') as f:
        data = f.read()
    out = {}
    for kind, (off, groups, gsize, n, size, face) in GENGHIS_TABLES.items():
        out[kind] = []
        for g in range(groups):
            for i in range(n):
                o = off + g * gsize + i * size
                if data[o]:
                    faces = 3 if kind == "woman" else 1
                    out[kind].append((koei_tw_name(data[o:o + 20]),
                                      [int.from_bytes(data[o + face + 2 * j:o + face + 2 * j + 2], 'little')
                                       for j in range(faces)]))
    return out


# PC-88: kind -> (offset, groups, group size, records, record size, face offset); the name (Shift-JIS) is at +0
GENGHIS_PC88_TABLES = {"ruler": (0x1D1, 1, 0, 27, 33, 29), "family": (0x54C, 4, 155, 5, 31, 29),
                       "son": (0xA29, 4, 105, 5, 21, 19), "general": (0x7ED, 1, 0, 26, 22, 20),
                       "woman": (0x1806, 1, 0, 40, 24, 18)}


def load_genghis_pc88_people(cim) -> dict[str, list[tuple[str, list[int]]]]:
    """As load_genghis_dos_people, for the PC-88 MDATA.CIM / SDATA.CIM (same people and face codes)."""
    with open(cim, 'rb') as f:
        data = f.read()
    out = {}
    for kind, (off, groups, gsize, n, size, face) in GENGHIS_PC88_TABLES.items():
        out[kind] = []
        for g in range(groups):
            for i in range(n):
                o = off + g * gsize + i * size
                if data[o]:
                    faces = 3 if kind == "woman" else 1
                    out[kind].append((unicodedata.normalize("NFKC", data[o:o + face].split(b'\0')[0].decode('cp932'))
                                      .replace(" ", ""),
                                      [int.from_bytes(data[o + face + 2 * j:o + face + 2 * j + 2], 'little')
                                       for j in range(faces)]))
    return out

def load_nobu3_dos_people(game_dir) -> list[list[tuple[str, int]]]:
    """(name, face code) per scenario (SNDATA1, SNDATA2): 44-byte records from 0xD38, surname 11 bytes,
    given name 11 bytes, +0x21 face code."""
    tables = []
    for n in (1, 2):
        with open(f'{game_dir}/SNDATA{n}.CIM', 'rb') as f:
            data = f.read()
        tables.append([(koei_tw_name(data[o:o + 11].split(b'\0')[0]) + koei_tw_name(data[o + 11:o + 22].split(b'\0')[0]),
                         int.from_bytes(data[o + 0x21:o + 0x23], 'little'))
                        for o in range(0xD38, len(data) - 43, 44) if data[o]])
    return tables


def load_nobu3_pc98_people(game_dir, pc88=False, x68=False) -> list[list[tuple[str, int]]]:
    """(name, face code) per scenario (SNDATA1, SNDATA2) of the PC-98 version: 38-byte records from 0xD38,
    surname 9 bytes, given name 7 bytes (Shift-JIS), +27 face code; same people and codes as the DOS version.
    The PC-88 records are 36 bytes from 0xC1E, the X68000 ones 44 bytes from 0x11F8
    with the face code big-endian at +30; otherwise the same fields."""
    start, size = (0xC1E, 36) if pc88 else (0x11F8, 44) if x68 else (0xD38, 38)
    tables = []
    for n in (1, 2):
        with open(f'{game_dir}/SNDATA{n}.CIM', 'rb') as f:
            data = f.read()
        tables.append([(unicodedata.normalize("NFKC", (data[o:o + 9].split(b'\0')[0] +
                                                       data[o + 9:o + 16].split(b'\0')[0]).decode('cp932')),
                         int.from_bytes(data[o + 30:o + 32], 'big') if x68 else
                         int.from_bytes(data[o + 27:o + 29], 'little'))
                        for o in range(start, len(data) - size + 1, size) if data[o]])
    return tables


# NOBU4 DOS gaiji (GAIJI.DAT, glyph = code - 0x9F); 0xA0 0xA1 together draw 宗我部, 0xB3 0xB4 squeeze two characters
NOBU4_GAIJI = {0x9F: "長", 0xA0: "宗", 0xA1: "我部", 0xA3: "蘆", 0xA4: "堯", 0xA5: "香", 0xA8: "瓊",
               0xB3: "山內", 0xB4: "深谷"}


def nobu4_name(raw: bytes) -> str:
    """KOEI Taiwan internal code name with NOBU4 gaiji (0xEB xx), cut at the first zero byte."""
    out = ''
    for i in range(0, len(raw) - 1, 2):
        if raw[i] == 0:
            break
        out += NOBU4_GAIJI[raw[i + 1]] if raw[i] == 0xEB else to_unicode_name(raw[i:i + 2])
    return out


def load_nobu4_dos_people(game_dir) -> list[list[tuple[str, int]]]:
    """(name, face code) per table: SNDATA1, SNDATA1T, SNDATA2, SNDATA2T, SNDATA3, SNDATA3T."""
    tables = []
    for n in range(1, 4):
        with open(f'{game_dir}/SNDATA{n}.CIM', 'rb') as f:
            data = f.read()
        people = []
        # 33-byte records from 0x1192: surname 6, 0, given name 6, 0, ..., +0x15 face code
        for o in range(0x1192, len(data) - 32, 33):
            if not data[o]:
                break
            people.append((nobu4_name(data[o:o + 6]) + nobu4_name(data[o + 7:o + 13]),
                           int.from_bytes(data[o + 0x15:o + 0x17], 'little')))
        tables.append(people)
        with open(f'{game_dir}/SNDATA{n}T.CIM', 'rb') as f:
            data = f.read()
        # 28-byte records of later arrivals: +3 surname 6, 0, given name 6, 0, ..., +0x18 face code
        tables.append([(nobu4_name(data[o + 3:o + 9]) + nobu4_name(data[o + 10:o + 16]),
                        int.from_bytes(data[o + 0x18:o + 0x1A], 'little'))
                       for o in range(0, len(data) - 27, 28) if data[o + 3]])
    return tables


def nobu4_pc98_name(raw: bytes) -> str:
    """Shift-JIS name with the same KOEI gaiji (EB xx) as the DOS version, cut at the first zero byte."""
    out, i = '', 0
    raw = raw.split(b'\0')[0]
    while i < len(raw):
        if raw[i] == 0xEB:
            out += NOBU4_GAIJI[raw[i + 1]].replace("山內", "山内")
            i += 2
        else:
            n = 2 if 0x81 <= raw[i] <= 0x9F or raw[i] >= 0xE0 else 1
            out += unicodedata.normalize("NFKC", raw[i:i + n].decode('cp932'))
            i += n
    return out


def load_nobu4_pc98_people(game_dir, x68=False) -> list[list[tuple[str, int]]]:
    """As load_nobu4_dos_people, but surname and given name are 7 bytes each (Shift-JIS, NUL padded).
    X68000: the same fields with 68000 padding, 40-byte records from 0x17C8 (face code big-endian at +24)
    and 30-byte arrivals (face code big-endian at +26)."""
    start, size, face = (0x17C8, 40, 24) if x68 else (0x1192, 33, 0x15)
    arrival, arrival_face = (30, 26) if x68 else (28, 0x18)
    order = 'big' if x68 else 'little'
    tables = []
    for n in range(1, 4):
        with open(f'{game_dir}/SNDATA{n}.CIM', 'rb') as f:
            data = f.read()
        people = []
        for o in range(start, len(data) - size + 1, size):
            if data[o] < 0x20:  # scenario 2 ends with a record starting 0x01
                break
            people.append((nobu4_pc98_name(data[o:o + 7]) + nobu4_pc98_name(data[o + 7:o + 14]),
                           int.from_bytes(data[o + face:o + face + 2], order)))
        tables.append(people)
        with open(f'{game_dir}/SNDATA{n}T.CIM', 'rb') as f:
            data = f.read()
        tables.append([(nobu4_pc98_name(data[o + 3:o + 10]) + nobu4_pc98_name(data[o + 10:o + 17]),
                        int.from_bytes(data[o + arrival_face:o + arrival_face + 2], order))
                       for o in range(0, len(data) - arrival + 1, arrival) if data[o + 3]])
    return tables



def load_nobu4_pc88_people(game_dir) -> list[list[tuple[str, int]]]:
    """PC-88 (two scenarios, no later arrivals): the PC-98 records, starting at 0x1175."""
    tables = []
    for n in (1, 2):
        with open(f'{game_dir}/SNDATA{n}.CIM', 'rb') as f:
            data = f.read()
        people = []
        for o in range(0x1175, len(data) - 32, 33):
            if data[o] < 0x20:  # scenario 2 ends with a record starting 0x01
                break
            people.append((nobu4_pc98_name(data[o:o + 7]) + nobu4_pc98_name(data[o + 7:o + 14]),
                           int.from_bytes(data[o + 0x15:o + 0x17], 'little')))
        tables.append(people)
    return tables

##############################################################################


@click.group()
def koukai2():
    """大航海時代II

    KAO.LZW     顏 CG (64x80) x 128
                道具 CG (48x48) x 128 (start_pos: 245,760, ls11)
                大眾臉 CG (start_pos: 292,514)
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output')
@click.option('--prefix', 'prefix', default='')
def koukai2_face(face_file, out_dir, prefix):
    """KAO2.LZW

    /dekoei.py koukai2 face -f kao/KOUKAI2_KAO.LZW
    """
    palette = color_codes_to_palette(
        ['#000000', '#00A261', '#D34100', '#F3A261', '#0041D3', '#00A2F3', '#D361A2', '#F3E3D3']
    )
    face_w, face_h = 64, 80

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix, num_part=128)


koukai2.add_command(koukai2_face, 'face')

##############################################################################


@click.group()
def koukai3():
    """大航海時代III"""
    pass


@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('-p', '--palette', 'palette_file', default='cds95FaceHeader.bmp', help="色盤檔案")
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
@click.command(help='顏 CG 解析')
def koukai3_face(face_file, palette_file, out_dir, prefix):
    """
    ./dekoei.py koukai3 face --face kao/KOUKAI3_FEMALE.CDS --palette kao/cds95FaceHeader.bmp
    ./dekoei.py koukai3 face --face kao/KOUKAI3_MALE.CDS --palette kao/cds95FaceHeader.bmp
    """
    # load palette
    palette_img = Image.open(palette_file)
    # palette_img.mode: "P"
    # palette_img.palette.getdata()[0]: "BGRX"
    #   "P" means using a color palette
    #   "BGRX" means the color order in palette with padding('X')
    #   see https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes

    # get palette with "RGB" mode, return list like [R0, G0, B0, R1, G1, B1, R2...]
    palette = list(grouper(palette_img.getpalette(rawmode='RGB'), 3))

    face_w, face_h = 80, 96

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix)


koukai3.add_command(koukai3_face, 'face')

# CDS95.EXE (the unpacked exe, CDS95.EXE.pec2bac): .rdata VA 0x4C2000 = file 0xC0600, .data VA 0x51E000 = file 0x11C400
KOUKAI3_WIN_SECTIONS = [(0x4C2000, 0x51E000, 0xC0600), (0x51E000, 0x608000, 0x11C400)]
# person table (VA 0x4FB618, 281 records of 0xCC bytes, read by 0x47EEE0):
# +0 given-name pointer, +4 surname pointer, +8 face, +0xC sex (1 = FEMALE.CDS), +0x10 age offset
KOUKAI3_WIN_PERSONS = (0x4FB618, 281, 0xCC)
# faces use colours 10-73, set by 0x4B43F3(10, 64, VA 0x50C160) from B, R, G triplets
KOUKAI3_WIN_FACE_PALETTE = 0x50C160


def koukai3_win_offset(va: int) -> int:
    for lo, hi, base in KOUKAI3_WIN_SECTIONS:
        if lo <= va < hi:
            return va - lo + base
    raise ValueError(hex(va))


def load_koukai3_win_persons(exe) -> list[tuple[str, int, int]]:
    """(name, face, sex) of every CDS95.EXE person record; name is 名•姓, or just 名 without a surname."""
    with open(exe, "rb") as f:
        data = f.read()

    def string(va):
        o = koukai3_win_offset(va)
        return data[o:data.index(b"\0", o)].decode("big5")

    start, count, size = KOUKAI3_WIN_PERSONS
    base = koukai3_win_offset(start)
    persons = []
    for o in range(base, base + count * size, size):
        given, surname, face, sex = struct.unpack("<IIii", data[o:o + 16])
        names = [string(given), string(surname) if surname else ""]
        persons.append(("•".join(n for n in names if n), face, sex))
    return persons


def load_koukai3_win_face_palette(exe) -> list[tuple[int, int, int]]:
    """RGB of colours 10-73."""
    with open(exe, "rb") as f:
        data = f.read()
    o = koukai3_win_offset(KOUKAI3_WIN_FACE_PALETTE)
    return [(data[i + 1], data[i + 2], data[i]) for i in range(o, o + 64 * 3, 3)]

# NOBU7 (Win, Chinese): Sndata01-05.nb7 hold 744 person records of 0x5C bytes from 0x53D0;
# +0 surname, +8 given name (8-byte Big5 each), +0x1C u16 face, +0x50 u16 person id
NOBU7_WIN_PERSONS = (0x53D0, 744, 0x5C)
# surnames written with Gaiji.nb7 glyphs (EB9F-EBA2)
NOBU7_WIN_GAIJI = {bytes.fromhex("eb9feba0eba1"): "長宗我部", bytes.fromhex("eba2eba0eba1"): "香宗我部"}


def load_nobu7_win_persons(path) -> list[tuple[int, str, str, int]]:
    """(person id, surname, given name, face) of one Sndata*.nb7 scenario."""
    with open(path, "rb") as f:
        data = f.read()

    def text(b):
        b = b.split(b"\0")[0]
        return NOBU7_WIN_GAIJI.get(b) or b.decode("big5")

    start, count, size = NOBU7_WIN_PERSONS
    persons = []
    for o in range(start, start + count * size, size):
        face, = struct.unpack_from("<H", data, o + 0x1C)
        pid, = struct.unpack_from("<H", data, o + 0x50)
        persons.append((pid, text(data[o:o + 8]), text(data[o + 8:o + 16]), face))
    return persons

# EIKETSU4 (織田信長傳, Win, Chinese): DATA.E4 part 0 holds 645 person records of 77 bytes;
# +0 name (12-byte Big5), +28 u16 face (also written as ASCII at +13)
EIKETSU4_WIN_PERSON = 77


def load_eiketsu4_win_persons(path) -> list[tuple[str, int]]:
    """(name, face) of every DATA.E4 person record."""
    with open(path, "rb") as f:
        data = ls11_decode_parts(f.read())[0]
    persons = []
    for o in range(0, len(data), EIKETSU4_WIN_PERSON):
        face, = struct.unpack_from("<H", data, o + 28)
        persons.append((data[o:o + 12].split(b"\0")[0].decode("big5"), face))
    return persons

# EIKETSU5 (三國志曹操傳, Win, Chinese): DATA.E5 part 0 holds 512 person records of 32 bytes;
# +0 name (13-byte Big5), +13 u16 face code (FACE.E5 part = code + 7, see notes/eiketsu5.md)
EIKETSU5_WIN_PERSON = 32


def load_eiketsu5_win_persons(path) -> list[tuple[str, int]]:
    """(name, face code) of every DATA.E5 person record."""
    with open(path, "rb") as f:
        data = ls11_decode_parts(f.read())[0]
    persons = []
    for o in range(0, len(data), EIKETSU5_WIN_PERSON):
        code, = struct.unpack_from("<H", data, o + 13)
        persons.append((data[o:o + 13].split(b"\0")[0].decode("big5"), code))
    return persons

# EIKETSU3 (毛利元就傳, Win, Chinese): DATA.E3 part 0 holds 800 person records of 54 bytes;
# +0 name (13-byte Big5), +13 reading (half-width katakana), +28 u16 face (KAO.E3 part)
EIKETSU3_WIN_PERSON = 54


def load_eiketsu3_win_persons(path) -> list[tuple[str, int]]:
    """(name, face) of every DATA.E3 person record."""
    with open(path, "rb") as f:
        data = ls11_decode_parts(f.read())[0]
    persons = []
    for o in range(0, len(data), EIKETSU3_WIN_PERSON):
        face, = struct.unpack_from("<H", data, o + 28)
        persons.append((data[o:o + 13].split(b"\0")[0].decode("big5"), face))
    return persons

# GENGHIS4 PK (Win, Chinese): SCEDAT1-4.CK each hold a run of 51-byte male records followed by
# 24-byte female records. A male record is u16 id + 17-byte Big5 name (NUL, then spaces) + ...; a female
# one u8 id + name (CKW95.EXE 0x495F10). Offsets below count from the name:
# male: +40 11 11, +44 u16 face (MenPuk.bmp); female: +17 nation, +21 02, +22 u8 face (WomenPuk.bmp)


def load_genghis4_win_persons(path) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """((name, face) of the men, (name, face) of the women) of one SCEDAT*.CK scenario."""
    with open(path, "rb") as f:
        data = f.read()

    def name(o):
        return data[o:o + 17].split(b"\0")[0].decode("big5")

    def male(o):
        return data[o + 40:o + 42] == b"\x11\x11"

    o = next(o for o in range(len(data)) if all(male(o + k * 51) for k in range(10)))
    men = []
    while male(o):
        men.append((name(o), struct.unpack_from("<H", data, o + 44)[0]))
        o += 51
    o -= 1  # a u8 id instead of u16 before the first female name
    women = []
    while o + 23 <= len(data) and data[o + 21] == 2:
        women.append((name(o), data[o + 22]))
        o += 24
    return men, women

##############################################################################


def unpack_abi(b):
    lookup = {0: 'D', 1: 'C', 2: 'B', 3: 'A'}
    ability = [lookup[(b >> 2*i) & 0b11] for i in range(4)]
    return ability


def unpack_mask(b):
    # 0b00000100 幸運
    # 0b00001000 魅力
    # 0b00010000 勇氣
    # 0b00100000 膽小
    # 0b01000000 冷靜
    # 0b10000000 單純
    masks = [''] * 4
    if b & 0b11000000 == 0b01000000:
        masks[0] = '冷靜'
    elif b & 0b11000000 == 0b10000000:
        masks[0] = '單純'

    if b & 0b00110000 == 0b00010000:
        masks[1] = '勇氣'
    elif b & 0b00110000 == 0b00100000:
        masks[1] = '膽小'

    if b & 0b00001000:
        masks[2] = '魅力'
    if b & 0b00000100:
        masks[3] = '幸運'
    return masks


@click.group()
def lempe():
    """拿破崙

    KAODATA.DAT

    "nations": [
        "France", "Holland", "Bavaria", "Denmark", "Turkey", "Italy", "Venice", "Naples",
        "Portugal", "Sweden", "Spain", "Prussia", "Russia", "Austria", "England", "Dublin"
    ]

    "places": {
        "start_pos": 7404,
        "data_size": 34,
        "data_count": 45 # 1-46?
    },
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def lempe_face(face_file, out_dir, prefix):
    palette = color_codes_to_palette(
        ['#000000', '#55FF55', '#FF5555', '#FFFF55', '#5555FF', '#55FFFF', '#FF55FF', '#FFFFFF']
    )
    face_w, face_h = 64, 80

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix, hh=True)


def lempe_person_loader(file, scenario):
    offsets1 = [8934, 22204, 35474, 48744, 62014]
    offsets2 = [x-8930 for x in offsets1]  # offsets2 = [4, 13274, 26544, 39814, 53084]
    read_count, read_size1, read_size2 = 255, 17, 15
    person_data = []
    with open(file, 'rb') as f:
        for i in range(read_count):
            f.seek(offsets1[scenario]+read_size1*i)
            d1 = f.read(read_size1)
            f.seek(offsets2[scenario]+read_size2*i)
            d2 = f.read(read_size2)
            person_data.append(b''.join([d1, d2]))
    return person_data


def load_lempe_persons(file, scenario=0) -> list[LEMPEPerson]:
    return load_person(lempe_person_loader(file, scenario), lempe_format, LEMPEPerson)



LEMPE_PC88_PERSONS = 0x21BA  # PC-88 NPDATA.CIM: 5 scenarios of 0x3100 bytes; 255 x 15 bytes (name 12, face u8)
LEMPE_X68_PERSONS = 0x2C92  # X68000 NPDATA1-5.DAT (one per scenario): the same records padded to 16 bytes


def load_lempe_pc88_persons(npdata, x68=False) -> list[tuple[str, int]]:
    """(name, face) of the PC-88 NPDATA.CIM scenario 1 (half-width katakana, NFKC); the same order as DOS.
    x68=True: the X68000 NPDATA1.DAT (the same names and faces in all 5 scenarios)."""
    with open(npdata, 'rb') as f:
        data = f.read()
    start, size = (LEMPE_X68_PERSONS, 16) if x68 else (LEMPE_PC88_PERSONS, 15)
    return [(unicodedata.normalize("NFKC", data[o:o + 12].split(b'\0')[0].decode('cp932')), data[o + 12])
            for o in range(start, start + 255 * size, size)]

@click.command(help='人物資料解析')
@click.option('-f', '--file', 'file', help="劇本檔案", required=True)
@click.option('-t', '--to', 'to', help="Specify output format", default='rich', type=click.Choice(['rich', 'csv', 'json', 'markdown', 'md']))
@click.option('-s', '--scenario', 'scenario', help="Specify scenario number (starts from 1)", default=0)
def lempe_person(file, to, scenario):
    """
    人物資料解析
    TODO:
      - [ ] check names of following person in game
        - [183] 默函特二世

    NPDATA.CIM

    ./dekoei.py lempe person -f ~/DOSBox/lempereur/NPDATA.CIM
    ./dekoei.py lempe person -f ~/DOSBox/empereur/NPDATA.CIM --to csv --scenario 2 > lempe-persons-s2-en.csv
    ./dekoei.py lempe person -f ~/DOSBox/lempereur/NPDATA.CIM --to csv --scenario 4 > lempe-persons-s4-zh.csv
    """
    persons = load_lempe_persons(file, scenario=0)
    print_table(lempe_table_title, lempe_headers, persons, to)


lempe.add_command(lempe_face, 'face')
lempe.add_command(lempe_person, 'person')


##############################################################################


@click.group()
def royal():
    """魔法皇冠

    ./dekoei.py royal face -f kao/ROYAL_KAODATA.DAT
    ./dekoei.py royal face -f kao/ROYAL_PC98_ロイヤルブラッド_B.fdi
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def royal_face(face_file, out_dir, prefix):
    """
    KAODATA.DAT
    PC98_ロイヤルブラッド_B.fdi
    """
    palette = color_codes_to_palette(
        ['#000000', '#55FF55', '#FF5555', '#FFFF55', '#5555FF', '#55FFFF', '#FF55FF', '#FFFFFF']
    )
    face_w, face_h = 64, 80
    loader = None
    num_part = 91
    hh = True

    # PC98 floppy image as face_file
    if '.fdi' in face_file.lower():
        palette = color_codes_to_palette(
            ['#000000', '#00BA65', '#FF5555', '#EFCF55', '#0065BA', '#459ADF', '#FF55FF', '#FFFFFF']
        )
        hh = False
        part_size = calc_part_size(face_w, face_h, len(palette), hh=hh)
        offset_infos = [(414720, num_part*part_size)]  # (offset, face_count * part_size)
        loader = create_floppy_image_stream(face_file, offset_infos, part_size)

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix, num_part=num_part, hh=hh, data_loader=loader)


royal.add_command(royal_face, 'face')

##############################################################################


@click.group()
def suikoden():
    """水滸傳

    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def suikoden_face(face_file, out_dir, prefix):
    """
    KAOIBM.DAT
    水滸伝2.FDI
    """
    palette = color_codes_to_palette(
        ['#000000', '#55FF55', '#FF5555', '#FFFF55', '#5555FF', '#55FFFF', '#FF55FF', '#FFFFFF']
    )
    face_w, face_h = 64, 80
    loader = None
    hh = True

    # PC98 floppy image as face_file
    if '.fdi' in face_file.lower():
        palette = color_codes_to_palette(
            ['#000000', '#00FF00', '#FF0000', '#FFFF00', '#0000FF', '#00FFFF', '#FF00FF', '#FFFFFF']
        )
        hh = False
        num_part = 260
        part_size = calc_part_size(face_w, face_h, len(palette), hh=hh)
        offset_infos = [(15360, num_part*part_size)]  # (offset, face_count * part_size)
        loader = create_floppy_image_stream(face_file, offset_infos, part_size)

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix, hh=hh, data_loader=loader)


@click.command(help='人物資料解析')
@click.option('-d', '--dir', 'game_dir', help="遊戲目錄", required=True)
@click.option('-t', '--to', 'to', help="Specify output format", default='rich', type=click.Choice(['rich', 'csv', 'json', 'markdown', 'md']))
@click.option('-s', '--scenario', 'scenario', help="Specify scenario number (starts from 1)", default=0)
@click.option('-f', '--file', 'file', help="劇本檔案")
def suikoden_person(game_dir, to, scenario, file):
    """
    人物資料解析

    SUIDATA1.CIM
    SUIDATA2.CIM
    SUIDATA3.CIM
    SUIDATA4.CIM

    ./dekoei.py suikoden person -d ~/DOSBox/sui/
    ./dekoei.py suikoden person -d ~/DOSBox/sui/ --to csv > PERSONS_TABLE/suikoden-persons-s1.csv
    """
    def person_loader(scenario=scenario):
        sn_file = os.path.join(game_dir, 'SUIDATA{}.CIM'.format(scenario+1))
        with open(sn_file, 'rb') as fsn:
            offset1 = 7124  # name
            offset2 = 4  # ability
            read_count, read_size1, read_size2 = 255, 45, 22
            person_data = []
            for i in range(read_count):
                fsn.seek(offset1+read_size1*i)
                d1 = fsn.read(read_size1)
                fsn.seek(offset2+read_size2*i)
                d2 = fsn.read(read_size2)
                person_data.append(b''.join([d1, d2]))
        return person_data
    person_data = person_loader(scenario)

    persons = load_person(person_data, suikoden_format, SUIKODENPerson)
    print_table(suikoden_table_title, suikoden_headers, persons, to)


# PC-98 (Japanese) SUIDATA?.CIM: 255 x 20 bytes at 7124: Shift-JIS name (7), half-width kana (9), 0, face, ?, flags.
# The gaiji glyphs are on disk 1 (not available); characters inferred from the FC names and the kana readings,
# and confirmed by the X68000 FONT68K.DAT (28 glyphs from 0xEB9F)
SUIKODEN_PC98_GAIJI = dict(zip(range(0xEBA0, 0xEBAE), "鄧郝龔蔣玘鮑俅鄔烕燁褚貹龐戩"))


def load_suikoden_pc98_persons(sndata, pc88: bool = False, x68: bool = False) -> list[tuple[int, str]]:
    """(face, name) per person. pc88: 19-byte records from 0x1884 (no byte 18), the same gaiji codes.
    x68: 40-byte records from 0x232C, the face at +37."""
    with open(sndata, 'rb') as f:
        data = f.read()
    if x68:
        data = b''.join(data[0x232C + i * 40:][:17] + data[0x232C + i * 40 + 37:][:1] + b'\0' for i in range(255))
    start, size = (0x1884, 19) if pc88 else (0, 19) if x68 else (7124, 20)
    persons = []
    for i in range(255):
        rec = data[start + i * size:start + (i + 1) * size]
        raw, name, j = rec[:7].split(b'\0')[0], [], 0
        while j < len(raw):
            n = 2 if 0x81 <= raw[j] <= 0x9F or 0xE0 <= raw[j] <= 0xFC else 1
            name.append(SUIKODEN_PC98_GAIJI.get(int.from_bytes(raw[j:j + n], 'big')) or raw[j:j + n].decode('cp932'))
            j += n
        persons.append((rec[17], ''.join(name)))
    return persons


suikoden.add_command(suikoden_face, 'face')
suikoden.add_command(suikoden_person, 'person')


def koei_tw_name(raw: bytes) -> str:
    """KOEI Taiwan internal code name, cut at the first zero word."""
    words = [raw[i:i + 2] for i in range(0, len(raw) - 1, 2)]
    if b'\0\0' in words:
        words = words[:words.index(b'\0\0')]
    return to_unicode_name(b''.join(words)) if words else ''


def load_suikoden_dos_persons(suidata) -> list[tuple[int, str]]:
    """(face, name) per person: 255 x 45 bytes at 7124, name (KOEI TW code, 3 characters) at +0, face at +42."""
    with open(suidata, 'rb') as f:
        data = f.read()
    return [(data[7124 + i * 45 + 42], koei_tw_name(data[7124 + i * 45:7124 + i * 45 + 6])) for i in range(255)]

##############################################################################


@click.group()
def taikoh():
    """太閤立志傳

    KAO.PUT
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def taikoh_face(face_file, out_dir, prefix):
    palette = color_codes_to_palette(
        ['#000000', '#41C341', '#F35100', '#F3D300', '#2061A2', '#00C3F3', '#F361B2', '#F3F3F3']
    )
    face_w, face_h = 64, 80

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix)


taikoh.add_command(taikoh_face, 'face')

# DOS (Chinese) MAIN.EXE: DGROUP is file 0x5C180 (0x6A00-byte header + segment 0x5578). Person records are
# 0x47 bytes: +0 surname (6 bytes), +7 given name (6 bytes), +14 u16 face code; the 241 at the start of a game
# are at DGROUP 0xB8C, TBS.DAT holds 472 more in the same layout. Women: 30 x 12 bytes at DGROUP 0x776,
# +0 name (6 bytes), +7 HIME.PUT face (0xFF none). See notes/taikoh.md
TAIKOH_DOS_DGROUP = 0x5C180
TAIKOH_DOS_PERSON = 0x47


def _taikoh_persons(data: bytes, start: int, count: int, name=koei_tw_name) -> list[tuple[str, int]]:
    return [(name(data[o:o + 6]) + name(data[o + 7:o + 13]),
             int.from_bytes(data[o + 14:o + 16], "little"))
            for o in range(start, start + count * TAIKOH_DOS_PERSON, TAIKOH_DOS_PERSON)]


def load_taikoh_dos_persons(main_exe, tbs) -> list[tuple[str, int]]:
    """(name, face code) of the people in MAIN.EXE, then those in TBS.DAT."""
    with open(main_exe, "rb") as f:
        main = f.read()
    with open(tbs, "rb") as f:
        later = f.read()
    return (_taikoh_persons(main, TAIKOH_DOS_DGROUP + 0xB8C, 241)
            + _taikoh_persons(later, 0, len(later) // TAIKOH_DOS_PERSON))


def load_taikoh_dos_women(main_exe) -> list[tuple[str, int]]:
    """(name, HIME.PUT face or 0xFF) of the 30 women in MAIN.EXE."""
    with open(main_exe, "rb") as f:
        main = f.read()
    o = TAIKOH_DOS_DGROUP + 0x776
    return [(koei_tw_name(main[o + i * 12:o + i * 12 + 6]), main[o + i * 12 + 7]) for i in range(30)]


# PC-98 MAIN.EXE: the same tables, DGROUP at file 0x55B90 (0x6C00-byte header + segment 0x4EF9); names in
# Shift-JIS, padded with half- and full-width spaces for display
TAIKOH_PC98_DGROUP = 0x55B90


def _sjis_name(raw: bytes) -> str:
    return raw.split(b"\0")[0].decode("cp932").replace(" ", "").replace("\u3000", "")


def load_taikoh_pc98_persons(main_exe, tbs) -> list[tuple[str, int]]:
    """As load_taikoh_dos_persons, for the PC-98 version."""
    with open(main_exe, "rb") as f:
        main = f.read()
    with open(tbs, "rb") as f:
        later = f.read()
    return (_taikoh_persons(main, TAIKOH_PC98_DGROUP + 0xB8C, 241, _sjis_name)
            + _taikoh_persons(later, 0, len(later) // TAIKOH_DOS_PERSON, _sjis_name))


def load_taikoh_pc98_women(main_exe) -> list[tuple[str, int]]:
    """As load_taikoh_dos_women, for the PC-98 version."""
    with open(main_exe, "rb") as f:
        main = f.read()
    o = TAIKOH_PC98_DGROUP + 0x776
    return [(_sjis_name(main[o + i * 12:o + i * 12 + 6]), main[o + i * 12 + 7]) for i in range(30)]


# X68000 MAIN.Z is CZ10 packed; in the unpacked image the same records have 68000 padding and big-endian faces:
# people 0x4A bytes from 0x5FE7E (face +14), women 14 bytes from 0x5FA32 (face +8, 0xFF none)
TAIKOH_X68_PEOPLE = 0x5FE7E
TAIKOH_X68_PERSON = 0x4A
TAIKOH_X68_WOMEN = 0x5FA32


def load_taikoh_x68_persons(main_z, tbs) -> list[tuple[str, int]]:
    """As load_taikoh_pc98_persons; TBS.DAT is the PC-98 file, little-endian faces and all."""
    import ls11
    with open(main_z, "rb") as f:
        main = ls11.cz10_decode(f.read())
    with open(tbs, "rb") as f:
        later = f.read()
    people = [(_sjis_name(main[o:o + 6]) + _sjis_name(main[o + 7:o + 13]), int.from_bytes(main[o + 14:o + 16], "big"))
              for o in range(TAIKOH_X68_PEOPLE, TAIKOH_X68_PEOPLE + 241 * TAIKOH_X68_PERSON, TAIKOH_X68_PERSON)]
    return people + _taikoh_persons(later, 0, len(later) // TAIKOH_DOS_PERSON, _sjis_name)


def load_taikoh_x68_women(main_z) -> list[tuple[str, int]]:
    import ls11
    with open(main_z, "rb") as f:
        main = ls11.cz10_decode(f.read())
    o = TAIKOH_X68_WOMEN
    return [(_sjis_name(main[o + i * 14:o + i * 14 + 6]), int.from_bytes(main[o + i * 14 + 8:o + i * 14 + 10], "big"))
            for i in range(30)]


TAIKOH2_WIN_PERSON = 59  # BSDATA*.TR2 record: surname, given name, ..., u16 person number at +16
TAIKOH2_WIN_DATA = 0x500000 - 0xFE800  # Taik2w95.exe .data: VA - this = file offset


# GAIJI.TR2 glyphs (0xFA70-) squeeze a four-character surname into three cells
TAIKOH2_WIN_GAIJI = {b"\xfa\x71\xfa\x73\xfa\x74": "長宗我部", b"\xfa\x72\xfa\x73\xfa\x74": "香宗我部"}


def _big5(b: bytes) -> str:
    b = b.split(b"\0")[0]
    return TAIKOH2_WIN_GAIJI.get(b) or b.decode("big5")


# PC-98 GAIJI.TR2 holds the same squeeze as JIS 0x7670- (Shift-JIS EBEE-), plus single characters
TAIKOH2_PC98_GAIJI = {b"\xeb\xef\xeb\xf1\xeb\xf2": "長宗我部", b"\xeb\xf0\xeb\xf1\xeb\xf2": "香宗我部",
                      b"\xeb\xee": "堯", b"\xeb\xf5": "垪", b"\xeb\xf9": "瓊"}
TAIKOH2_PC98_NAMES = (0x30DF8, 0x30ECA, 0x30F9C)  # MAIN.EXE: master surnames, given names, women
TAIKOH2_PC98_KEY = 0xD5  # SNDATA1.TR2 XOR


def _taikoh2_pc98_sjis(b: bytes) -> str:
    b = b.split(b"\0")[0]
    for code, text in TAIKOH2_PC98_GAIJI.items():
        b = b.replace(code, text.encode("cp932"))
    return b.decode("cp932")


def load_taikoh2_win_persons(bsdata, decode=_big5) -> list[tuple[int, str]]:
    """(person number, name) of BSDATA1.TR2; the number is also the FACE.LZW face."""
    with open(bsdata, "rb") as f:
        data = f.read()
    persons = []
    for o in range(0, len(data), TAIKOH2_WIN_PERSON):
        number = int.from_bytes(data[o + 16:o + 18], "little")
        name = decode(data[o:o + 7]) + decode(data[o + 7:o + 14])
        persons.append((number, name))
    return persons


def load_taikoh2_win_others(exe, sndata, names=tuple(va - TAIKOH2_WIN_DATA for va in (0x5067D8, 0x5068B0, 0x506988)),
                            decode=_big5, key=0x26) -> list[tuple[int, str, int]]:
    """(person number, name, face) of the 30 masters (1000-) and the named women (2000-).

    Names are in Taik2w95.exe; the faces are (number, face) pairs in SNDATA1.TR2, which is XORed with 0x26 (PC-98: 0xD5)."""
    with open(exe, "rb") as f:
        exe = f.read()
    with open(sndata, "rb") as f:
        sn = bytes(b ^ key for b in f.read())
    faces = {}
    for first, step in ((1000, 12), (2000, 4)):  # (number, face, ...) records
        o = 0
        while True:
            o = sn.find(first.to_bytes(2, "little"), o)
            if o < 0:
                raise ValueError(f"no {first} records in {sndata}")
            if int.from_bytes(sn[o + step:o + step + 2], "little") == first + 1:
                break
            o += 1
        while (n := int.from_bytes(sn[o:o + 2], "little")) // 1000 == first // 1000:
            faces[n] = int.from_bytes(sn[o + 2:o + 4], "little")
            o += step
    surname, given, women = (exe[o:] for o in names)
    others = [(1000 + i, decode(surname[i * 7:i * 7 + 7]) + decode(given[i * 7:i * 7 + 7]), faces[1000 + i])
              for i in range(30)]
    others += [(2000 + i, decode(women[i * 5:i * 5 + 5]), faces[2000 + i]) for i in range(4)]
    return others


PROGEN_PC98_DGROUP = 0x4400 + 0x341F0  # MAIN.EXE: header + DGROUP segment 0x341F
PROGEN_PC98_PERSONS = 0x33E4  # DS: 100 x 33 bytes (0xA95A); the last three are リザーブ１-３
PROGEN_PC98_PEOPLE = 97


def load_progen_pc98_persons(main_exe) -> list[tuple[int, str]]:
    """(face code, name) of the MAIN.EXE person table: u16 face code, u8, Shift-JIS name, ..."""
    with open(main_exe, "rb") as f:
        main = f.read()
    persons = []
    for i in range(PROGEN_PC98_PEOPLE):
        rec = main[PROGEN_PC98_DGROUP + PROGEN_PC98_PERSONS + i * 33:][:33]
        persons.append((int.from_bytes(rec[:2], "little"), rec[3:19].split(b"\0")[0].decode("cp932")))
    return persons


ROYAL_PC98_DGROUP = 0x27270  # MAIN.EXE file offset of DS (the name table DS:0xE52 is used by 0x5B0)
ROYAL_PC88_SNDATA = 0x6EB  # PC-88 SNDATA1.CIM starts at PC-98 DS:0x6EB


def _royal_pc98_names(main: bytes, offset: int, size: int, count: int, base=ROYAL_PC98_DGROUP) -> list[str]:
    """Half-width katakana names, as full-width."""
    o = base + offset
    return [unicodedata.normalize("NFKC", main[o + i * size:o + i * size + 10].split(b"\0")[0].decode("cp932"))
            for i in range(count)]


def load_royal_pc98_names(main_exe, pc88=False) -> tuple[list[str], list[str]]:
    """(64 lords, whose index is also the KAODATA.DAT face; 23 unit types, faces 68-90) from MAIN.EXE.
    pc88: `main_exe` is the PC-88 SNDATA1.CIM, a copy of the PC-98 data at DS - 0x6EB."""
    with open(main_exe, "rb") as f:
        main = f.read()
    if pc88:
        main = bytes(ROYAL_PC98_DGROUP + ROYAL_PC88_SNDATA) + main
    return _royal_pc98_names(main, 0xE52, 13, 64), _royal_pc98_names(main, 0x13CC, 16, 23)


def load_royal_x68_names(main_z) -> tuple[list[str], list[str]]:
    """As load_royal_pc98_names, from the X68000 MAIN.Z (not packed): the same records with 68000 padding,
    lords 16 bytes from file 0x249C0, unit types 20 bytes from 0x25018."""
    with open(main_z, "rb") as f:
        main = f.read()
    return _royal_pc98_names(main, 0x249C0, 16, 64, 0), _royal_pc98_names(main, 0x25018, 20, 23, 0)


NOBU2_PC88_DATA = 0x1581  # DATA50S.DAT: 53 clan names (9 bytes), then 53 given names (5 bytes) at 0x175E
NOBU2_PC88_LORDS = 53


NOBU2_X68_DATA = (0x1E86, 0x2064)  # X68000 DATA50.DAT: the same tables, the given names at an even offset


def load_nobu2_pc88_names(data50s: bytes, x68: bool = False) -> list[str]:
    """Shift-JIS names of the 50 daimyo and 明智, 羽柴, 柴田; the index is also the face (ODAMAIN 0x3A67).
    x68=True: the X68000 DATA50.DAT."""
    clans, given = NOBU2_X68_DATA if x68 else (NOBU2_PC88_DATA, NOBU2_PC88_DATA + 9 * NOBU2_PC88_LORDS)
    return [data50s[clans + 9 * i:][:9].split(b"\0")[0].decode("cp932")
            + data50s[given + 5 * i:][:5].split(b"\0")[0].decode("cp932") for i in range(NOBU2_PC88_LORDS)]


ISHIN_PC98_PEOPLE = 423  # 0x2F12: ids 0-422 are the historical people
ISHIN_PC98_SCENARIO = 0xA770  # SHINARIO.DAT: 3 scenarios, each loaded to DS:0x930A
ISHIN_PC98_FACES = 0x3C  # scenario offset of the 6-byte face records (DS:0x9346, 0x4AB1)
# KOEI gaiji in the names; glyphs in USKCG.SYS
ISHIN_PC98_GAIJI = {0xEB9F: "恂", 0xEBA0: "寛", 0xEBA1: "屏", 0xEBA2: "佶", 0xEBA3: "溥", 0xEBA5: "叟", 0xEBA6: "孚",
                    0xEBA7: "訥", 0xEBA8: "阮", 0xEBA9: "煕", 0xEBAA: "襄", 0xEBAB: "奎", 0xEBAC: "霖", 0xEBAD: "謨"}


def _ishin_pc98_text(raw: bytes) -> str:
    out, i = [], 0
    while i < len(raw):
        n = 2 if 0x81 <= raw[i] <= 0x9F or 0xE0 <= raw[i] <= 0xFC else 1
        code = int.from_bytes(raw[i:i + n], "big")
        out.append(ISHIN_PC98_GAIJI.get(code) or raw[i:i + n].decode("cp932"))
        i += n
    return "".join(out)


def load_ishin_pc98_persons(isin_exe, shinario) -> list[tuple[str, list[bytes]]]:
    """(name, face record of each scenario) of the historical people.

    Names are in ISIN.EXE (surname 7 bytes at 0x42312, given name 9 bytes at 0x449F4); the face records are
    in SHINARIO.DAT: 0xFF and a KAODAT.DAT face, or a MONDAT.DAT composite."""
    with open(isin_exe, "rb") as f:
        exe = f.read()
    with open(shinario, "rb") as f:
        sc = f.read()
    persons = []
    for i in range(ISHIN_PC98_PEOPLE):
        name = "".join(_ishin_pc98_text(exe[o + i * n:o + (i + 1) * n].split(b"\0")[0])
                       for o, n in ((0x42312, 7), (0x449F4, 9)))
        faces = [sc[s + ISHIN_PC98_FACES + i * 6:][:6] for s in range(0, len(sc), ISHIN_PC98_SCENARIO)]
        persons.append((name, faces))
    return persons



ISHIN_PC88_PEOPLE = 201
ISHIN_PC88_SURNAMES = 0x47AB  # MAIN.COM: 7 bytes each
ISHIN_PC88_SCENARIOS = [(0xA90, 0x275F), (0x3490, 0x515F)]  # SHINARIO.OVL: given names (9 bytes), face records


def load_ishin_pc88_persons(main_com, shinario) -> list[tuple[list[str], bytes]]:
    """(name in each scenario, 5-byte face record) of the historical people of the PC-88 version.

    The face records are the same in both scenarios (0xFF and a KAODAT.DAT face, or a composite, MAIN.COM 0x37C9);
    two given names change in scenario 2, where the domain has passed to the successor."""
    with open(main_com, "rb") as f:
        main = f.read()
    with open(shinario, "rb") as f:
        sc = f.read()
    persons = []
    for i in range(ISHIN_PC88_PEOPLE):
        surname = _ishin_pc98_text(main[ISHIN_PC88_SURNAMES + i * 7:][:7].split(b"\0")[0])
        names = [surname + _ishin_pc98_text(sc[o + i * 9:][:9].split(b"\0")[0]) for o, _ in ISHIN_PC88_SCENARIOS]
        persons.append((names, sc[ISHIN_PC88_SCENARIOS[0][1] + i * 5:][:5]))
    return persons


ISHIN_X68_SURNAMES = 0x4548  # ISINMAIN.Z (not packed): the PC-88 surnames, byte for byte
ISHIN_X68_GIVEN = 0x1DBE  # SDATA1.DAT / SDATA2.DAT: the PC-88 given names of each scenario
ISHIN_X68_FACES = 0x2B18  # SDATA1.DAT: 5-byte face records (the same in SDATA2.DAT)


def load_ishin_x68_persons(main_z, sdata1, sdata2) -> list[tuple[list[str], bytes]]:
    """As load_ishin_pc88_persons, for the X68000 version: the same people and names, but the composite
    records index the X68000 MONDAT.DAT."""
    with open(main_z, "rb") as f:
        main = f.read()
    scenarios = []
    for path in (sdata1, sdata2):
        with open(path, "rb") as f:
            scenarios.append(f.read())
    persons = []
    for i in range(ISHIN_PC88_PEOPLE):
        surname = _ishin_pc98_text(main[ISHIN_X68_SURNAMES + i * 7:][:7].split(b"\0")[0])
        names = [surname + _ishin_pc98_text(sc[ISHIN_X68_GIVEN + i * 9:][:9].split(b"\0")[0]) for sc in scenarios]
        persons.append((names, scenarios[0][ISHIN_X68_FACES + i * 5:][:5]))
    return persons


# 元朝秘史 PC-88: GENDATA<s>.DAT has the men (109 x 27 bytes from 1, face code at +25) and the women (33 x 23 bytes
# from 0x1A23, face code at +21); empty records have no name (or "　"); USDATA<s>.DAT is blocks of 351 bytes, each
# 8 men (27 bytes) and then 5 children (23 bytes, face code at +21, 0 for the daughters, who have no face)
GENCHOU_PC88_MEN = (1, 27, 109)
GENCHOU_PC88_WOMEN = (0x1A23, 23, 33)
GENCHOU_PC88_BLOCK = 351
GENCHOU_PC88_PLACEHOLDER = "モンゴル統一者"  # scenario 4: the player's own Mongol leader
# X68000: GENDATA1-3, USDATA1-3 are packed (san3.unpack_x68_sndata), GENDATA4 and USDATA4 are not. GENDATA begins
# with a copy of USDATA1; the records are 3 bytes longer (zero) before a big-endian face code: men 30 bytes from
# 0x66A, women 26 from 0x1E46; USDATA is 2 bytes (FF FF), then blocks of 410: 8 men, then 5 children at +240
GENCHOU_X68_MEN = (0x66A, 30, 109)
GENCHOU_X68_WOMEN = (0x1E46, 26, 33)
GENCHOU_X68_BLOCK = 410


def load_genchou_pc88_people(game_dir, x68=False) -> list[tuple[int, int, str, str, int]]:
    """(scenario, USDATA block or -1 for GENDATA, kind "man" / "woman" / "child", NFKC name, face code) of every
    record, in file order. x68=True: the X68000 files."""
    from san3 import unpack_x68_sndata

    def name(rec):
        return unicodedata.normalize("NFKC", rec[:17].split(b"\0")[0].decode("cp932")).strip()

    def read(file):
        with open(os.path.join(game_dir, file), "rb") as f:
            data = f.read()
        return unpack_x68_sndata(data) if x68 and data[0] != 0xFF else data

    if x68:
        men, women, block, first_block, order = GENCHOU_X68_MEN, GENCHOU_X68_WOMEN, GENCHOU_X68_BLOCK, 2, "big"
    else:
        men, women, block, first_block, order = GENCHOU_PC88_MEN, GENCHOU_PC88_WOMEN, GENCHOU_PC88_BLOCK, 0, "little"
    man_size, woman_size = men[1], women[1]
    people = []
    for sc in range(1, 5):
        gen = read(f"GENDATA{sc}.DAT")
        us = read(f"USDATA{sc}.DAT")
        first, size, count = men
        for i in range(count):
            rec = gen[first + i * size:][:size]
            if name(rec) and name(rec) != GENCHOU_PC88_PLACEHOLDER:
                people.append((sc, -1, "man", name(rec), int.from_bytes(rec[size - 2:size], order)))
        first, size, count = women
        for i in range(count):
            rec = gen[first + i * size:][:size]
            if name(rec):
                people.append((sc, -1, "woman", name(rec), int.from_bytes(rec[size - 2:size], order)))
        for b in range(first_block, len(us), block):
            for i in range(8):
                rec = us[b + i * man_size:][:man_size]
                if name(rec):
                    people.append((sc, b // block, "man", name(rec), int.from_bytes(rec[man_size - 2:], order)))
            for i in range(5):
                rec = us[b + 8 * man_size + i * woman_size:][:woman_size]
                code = int.from_bytes(rec[woman_size - 2:], order)
                if name(rec) and code:
                    people.append((sc, b // block, "child", name(rec), code))
    return people

TK_PC98_ADMIRALS = 0x4600 + 0x38520 + 0xC6FC  # RENMAIN.EXE: header + DGROUP 0x3852, DS:0xC6FC
TK_PC98_PEOPLE = 40  # 19-byte records: 0-19 Japan, 20-39 the Allies
TK_PC98_GAIJI = (b"\xeb\xa4", "纒")  # KOEI gaiji in 宇垣纒; glyph in USKCG.SYS (JIS 0x7626)


TK_PC88_ADMIRALS = 0x7849  # PC-88 YSHELL.COM: the PC-98 records, byte for byte
TK_X68_ADMIRALS = 0x5F1D8  # X68000 RENMAIN.Z (not packed): the same names in 20-byte records


def load_tk_pc98_names(renmain_exe, offset=None, size=19) -> list[str]:
    """Admiral names from RENMAIN.EXE; the index is also the RENPIC.DAT face. The PC-88 YSHELL.COM holds the same
    records at `offset` TK_PC88_ADMIRALS, the X68000 RENMAIN.Z at TK_X68_ADMIRALS with `size` 20.

    Half-width katakana become full-width; spaces (full-width in 吉川　潔, two half-width in 宇垣　纒) stay
    one full-width space."""
    with open(renmain_exe, "rb") as f:
        exe = f.read()
    names = []
    for i in range(TK_PC98_PEOPLE):
        raw = exe[(TK_PC98_ADMIRALS if offset is None else offset) + i * size:][:size].split(b"\0")[0]
        text = TK_PC98_GAIJI[1].join(unicodedata.normalize("NFKC", p.decode("cp932")) for p in raw.split(TK_PC98_GAIJI[0]))
        names.append("　".join(text.split()))
    return names


# 提督の決断II (PC-98): scenario 1 of each table; the names are the same in every scenario
TK2_PC98_TABLES = [("ARDATA", 17, 60), ("GRDATA", 18, 30), ("SJDATA", 31, 9)]  # admirals, generals, leaders


def _tk2_pc98_name(raw: bytes) -> str:
    text = unicodedata.normalize("NFKC", raw.split(b"\0")[0].decode("cp932"))
    return "　".join(text.split())


def load_tk2_pc98_names(ardata: bytes, grdata: bytes, sjdata: bytes) -> tuple[list[str], list[str], list[str]]:
    """(60 admirals: 0-29 Japan, 30-59 the Allies; 30 generals: 0-14 Japan, 15-29 the Allies; 9 heads of state).

    Each record starts with the name (Shift-JIS, half-width katakana for westerners, 14 bytes; 13 for SJDATA)."""
    return tuple([_tk2_pc98_name(data[i * size:i * size + (13 if name == "SJDATA" else 14)]) for i in range(count)]
                 for (name, size, count), data in zip(TK2_PC98_TABLES, (ardata, grdata, sjdata)))


# 提督の決断III (PC-98): MAIN.EXE table of 111 admirals and generals, 26-byte records:
# [u8][0][name 12, Shift-JIS][0][nation][0]...[face u8 at +25]
TK3_PC98_PEOPLE = 111
TK3_PC98_RECORD = 26
TK3_PC98_LEADERS = 24  # MESSAGE.TK3 part 0, the strings after 索敵記録 (170-193; PK 172-195): faces 141-164


def _tk3_pc98_name(raw: bytes) -> str:
    return unicodedata.normalize("NFKC", raw.split(b"\0")[0].decode("cp932"))


def load_tk3_pc98_persons(data: bytes, offset: int, count: int = TK3_PC98_PEOPLE) -> list[tuple[str, int]]:
    """(name, face) of the people table at `offset` (MAIN.EXE, or a scenario copy in SNDATA*.TK3)."""
    return [(_tk3_pc98_name(data[o + 2:o + 14]), data[o + 25])
            for o in range(offset, offset + count * TK3_PC98_RECORD, TK3_PC98_RECORD)]


def tk3_pc98_messages(message_tk3: bytes, part: int) -> list[str]:
    """MESSAGE.TK3 strings of a part (message id 1000 * part + index): LS11 parts of u16 count, u16 offsets,
    then the strings, ended by \\x05\\x05\\x05; \\x1bk, \\x1bH and \\x1bK switch the font."""
    data = ls11_decode_parts(message_tk3)[part]
    count = struct.unpack_from("<H", data)[0]
    offsets = list(struct.unpack_from(f"<{count}H", data, 2)) + [len(data)]
    texts = []
    for a, b in zip(offsets, offsets[1:]):
        raw = data[a:b].split(b"\x05")[0]
        for esc in (b"\x1bk", b"\x1bH", b"\x1bK"):
            raw = raw.replace(esc, b"")
        texts.append(unicodedata.normalize("NFKC", raw.decode("cp932", "replace")).strip())
    return texts


def load_tk3_pc98_leaders(message_tk3: bytes) -> list[str]:
    texts = tk3_pc98_messages(message_tk3, 0)
    start = texts.index("索敵記録") + 1
    return texts[start:start + TK3_PC98_LEADERS]


# 信長の野望・覇王伝 (PC-98): SN1-3.NB5 are XOR 0xB4; people at 0xAE4, 460 slots of 39 bytes:
# [family 7][given 7, Shift-JIS, NUL padded]...[0xFF at +22]...[face u16 at +29]; empty slots start with 0.
# S1T-S3T.NB5 (not XORed) are the later arrivals of each scenario, 30-byte records:
# [u8 year][...][family 7 at +4][given 7 at +11]...[face u16 at +26]; trailing records are blank.
NOBU5_PC98_XOR = 0xB4
NOBU5_PC98_PEOPLE = 0xAE4
NOBU5_PC98_SLOTS = 460
NOBU5_PC98_PRINCESSES = 0x6A9E  # SN copy of DS:0x6AE8, 36 x 14 bytes, 8-byte name at +8 (face 878 + index)
NOBU5_PC98_PRINCESS_COUNT = 36
# X68000: the same tables, not XORed and with 68000 padding: SN people at 0xC2A, 50 bytes with the face big-endian
# at +32; S*T 34 bytes with the face big-endian at +28; princesses at 0x8D2C, 18 bytes with the name at +8
NOBU5_X68_PEOPLE = 0xC2A
NOBU5_X68_PRINCESSES = 0x8D2C
# KOEI gaiji (KANJI.NB5, 16x16) used in family names
NOBU5_PC98_GAIJI = {b"\xec\x8c\xec\x8d\xec\x8e": "長宗我部", b"\xec\x8f\xec\x8d\xec\x8e": "香宗我部"}


def _nobu5_pc98_name(raw: bytes) -> str:
    raw = raw.split(b"\0")[0]
    for code, text in NOBU5_PC98_GAIJI.items():
        if raw.startswith(code):
            return text + raw[len(code):].decode("cp932")
    return raw.decode("cp932")


def load_nobu5_pc98_scenario(sn: bytes, x68=False) -> list[tuple[str, int]]:
    """(name, face) of a SN*.NB5 people table."""
    data = sn if x68 else bytes(b ^ NOBU5_PC98_XOR for b in sn)
    start, size, face, order = (NOBU5_X68_PEOPLE, 50, 32, "big") if x68 else (NOBU5_PC98_PEOPLE, 39, 29, "little")
    persons = []
    for o in range(start, start + NOBU5_PC98_SLOTS * size, size):
        if data[o]:
            persons.append((_nobu5_pc98_name(data[o:o + 7]) + _nobu5_pc98_name(data[o + 7:o + 14]),
                            int.from_bytes(data[o + face:o + face + 2], order)))
    return persons


def load_nobu5_pc98_arrivals(st: bytes, x68=False) -> list[tuple[str, int]]:
    """(name, face) of a S*T.NB5 table of later arrivals."""
    size, face, order = (34, 28, "big") if x68 else (30, 26, "little")
    persons = []
    for o in range(0, len(st) - size + 1, size):
        name = _nobu5_pc98_name(st[o + 4:o + 11]) + _nobu5_pc98_name(st[o + 11:o + 18])
        if name:
            persons.append((name, int.from_bytes(st[o + face:o + face + 2], order)))
    return persons


def load_nobu5_pc98_princesses(sn: bytes, x68=False) -> list[str]:
    """Names of the 36 princesses (faces 878-913); "" for the unnamed ones."""
    data = sn if x68 else bytes(b ^ NOBU5_PC98_XOR for b in sn)
    start, size = (NOBU5_X68_PRINCESSES, 18) if x68 else (NOBU5_PC98_PRINCESSES, 14)
    return [_nobu5_pc98_name(data[start + i * size + 8:][:8]) for i in range(NOBU5_PC98_PRINCESS_COUNT)]


# 信長の野望・天翔記 (PC-98): name records of 18 bytes, [surname 7][given 7, Shift-JIS][u16 face][u8][u8];
# MAIN.EXE 0x2372C: person p (1-532) is record p - 1, 0x23824 reads the face at +0x0E
NOBU6_PC98_PEOPLE = 0x6C8E  # SNDATA.NB6 part (one per scenario): 500 men, then the princesses
NOBU6_PC98_SLOTS = 531  # slot 532 (0x213) is scratch, filled for merchants, monks etc. at run time
NOBU6_PC98_TAIKI_STATS = 52  # TAIKI.NB6 part: n records of 52 bytes, then their n name records
# GAIJI.NB6 glyphs 169-172 (EC8C-EC8F): 長, 宗, 我部, 香; only used in these surnames
NOBU6_PC98_GAIJI = {b"\xec\x8c\xec\x8d\xec\x8e": "長宗我部", b"\xec\x8f\xec\x8d\xec\x8e": "香宗我部"}


def _nobu6_pc98_text(raw: bytes) -> str:
    for seq, text in NOBU6_PC98_GAIJI.items():
        if seq in raw:
            return text.join(_nobu6_pc98_text(p) for p in raw.split(seq))
    return unicodedata.normalize("NFKC", raw.decode("cp932"))


def load_nobu6_pc98_persons(sndata: bytes, taiki: bytes) -> list[tuple[str, int]]:
    """(name, face code) of every name record: scenario 1, its later arrivals (TAIKI), scenario 2, ...

    Face code bit 15 set: composite (MONDATA.NB6), else the KAODATA.NB6 face."""
    persons = []
    for scenario, waiting in zip(ls11_decode_parts(sndata), ls11_decode_parts(taiki)):
        n = len(waiting) // (NOBU6_PC98_TAIKI_STATS + 18)
        for data, offset, count in ((scenario, NOBU6_PC98_PEOPLE, NOBU6_PC98_SLOTS),
                                    (waiting, n * NOBU6_PC98_TAIKI_STATS, n)):
            for o in range(offset, offset + count * 18, 18):
                if data[o]:  # empty slots are all 0 with face FFFF
                    name = _nobu6_pc98_text(data[o:o + 7].split(b"\0")[0]) + \
                        _nobu6_pc98_text(data[o + 7:o + 14].split(b"\0")[0])
                    persons.append((name, int.from_bytes(data[o + 14:o + 16], "little")))
    return persons


##############################################################################


@click.group()
def tk2():
    """提督之決斷II

    KAO.TK2
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def tk2_face(face_file, out_dir, prefix):
    palette = color_codes_to_palette(
        ['#000000', '#417100', '#D32000', '#E3A261', '#0030A2', '#7192B2', '#C36161', '#F3F3F3']
    )
    face_w, face_h = 48, 64

    extract_images(face_file, face_w, face_h, palette, out_dir, prefix)


tk2.add_command(tk2_face, 'face')

##############################################################################


@click.group()
def winning():
    """光榮賽馬, 賽馬大亨

    (有大眾臉)
    """
    pass


@click.option('-d', '--dir', 'game_dir', help="遊戲目錄", required=True)
@click.option('--out_dir', 'out_dir', default='_output')
@click.option('--prefix', 'prefix', default='')
@click.command(help='顏 CG 解析')
def winning_face(game_dir, out_dir, prefix):
    """

    /dekoei.py winning face --dir ~/DOSBox/winning
    """
    palette = color_codes_to_palette(
        ['#000000', '#20D320', '#F30000', '#F3D300', '#0061C3', '#00B2F3', '#F351F3', '#F3F3F3']
    )
    face_w, face_h, bpp = 64, 80, 3
    part_size = int(face_w*face_h*bpp/8)

    def stream() -> typing.Generator[bytes, None, None]:
        with open(game_dir+'/KAO.DAT', 'rb') as f:
            while part := f.read(part_size):
                yield part
        with open(game_dir+'/TEXTGRP.DAT', 'rb') as f:
            # 有馬桜子
            yield f.read(part_size)

    extract_images('', face_w, face_h, palette, out_dir, prefix, data_loader=stream)


winning.add_command(winning_face, 'face')
