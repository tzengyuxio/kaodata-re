import bitarray
import click
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


def load_koukaigd_win_events(sdata) -> list[tuple[str, int]]:
    """(name, portrait) of the Sdata.dat event people."""
    with open(sdata, "rb") as f:
        data = f.read()
    start, count, size = KOUKAIGD_WIN_EVENT
    return [(data[o:o + 20].split(b"\0")[0].decode("big5"), data[o + 23])
            for o in range(start, start + count * size, size)]


def load_koukaigd_win_tavern(sdata) -> list[tuple[str, int]]:
    """(name, portrait) of the Sdata.dat tavern women."""
    with open(sdata, "rb") as f:
        data = f.read()
    start, count, size = KOUKAIGD_WIN_TAVERN
    return [(data[o:o + 12].split(b"\0")[0].decode("big5"), KOUKAIGD_WIN_TAVERN_FACE + k)
            for k, o in enumerate(range(start, start + count * size, size))]

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
# The gaiji glyphs are on disk 1 (not available); characters inferred from the FC names and the kana readings
SUIKODEN_PC98_GAIJI = dict(zip(range(0xEBA0, 0xEBAE), "鄧郝龔蔣玘鮑俅鄔烕燁褚貹龐戩"))


def load_suikoden_pc98_persons(sndata) -> list[tuple[int, str]]:
    """(face, name) per person."""
    with open(sndata, 'rb') as f:
        data = f.read()
    persons = []
    for i in range(255):
        rec = data[7124 + i * 20:7124 + (i + 1) * 20]
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
