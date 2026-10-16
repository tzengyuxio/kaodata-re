from collections import namedtuple
import inspect
import io
from functools import reduce
from itertools import zip_longest
import math
import os
import typing
import struct
from PIL import Image
from rich.console import Console
from rich.progress import track
from rich.table import Table
from pytablewriter import JsonTableWriter, MarkdownTableWriter
from ls11 import ls11_decode, LS11_MAGIC

console = Console()
cns11643_unicode_table = {}
unicode_koeitw_table: dict[str, bytes] = {}

BGCOLOR = (55, 55, 55)

BIG_ENDIAN = 'big'
LITTLE_ENDIAN = 'little'
DEFAULT_ENDIAN = LITTLE_ENDIAN

# H 為表頭的欄位資訊
# name 為名稱，用以對應 Person 的欄位,
# text 為表頭顯示的文字,
# cate 為 category 縮寫, 作為表頭欄位的分類，不同分類的表頭會搭配不同的 color and style
# 預計的表頭欄位分類有： id, name, face, base(基本能力), mask(隱藏能力), status(劇本相關資訊), memo...等
H = namedtuple('H', 'name, text, cate')


def column_arguments(h: H) -> dict:
    style = None
    justify = 'left'
    if h.cate == 'id':
        justify = 'center'
        style = 'cyan'
    elif h.cate == 'name':
        pass
    elif h.cate == 'face':
        justify = 'right'
        style = 'magenta'
    elif h.cate == 'base':
        justify = 'right'
        style = 'green'
    elif h.cate == 'mask':
        justify = 'right'
        style = 'blue'
    return {
        'justify': justify,
        'style': style,
    }


def color_codes_to_palette(color_codes) -> list[tuple[int, int, int]]:
    # ['#FF0000', '#00FF00', '#0000FF'] --> ((255, 0, 0), (0, 255, 0), (0, 0, 255))
    return [(int(x[1:3], base=16), int(x[3:5], base=16), int(x[5:7], base=16)) for x in color_codes]


def load_palette_from_file(filename, offset=0) -> list[tuple[int, int, int]]:
    with open(filename, 'rb') as f:
        f.seek(offset)
        raw_data = f.read(1024)
        return list(grouper(raw_data, 4))


def grouper(iterable, n, incomplete='fill', fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, fillvalue='x') --> ABC DEF Gxx
    # grouper('ABCDEFG', 3, incomplete='ignore') --> ABC DEF
    args = [iter(iterable)] * n
    if incomplete == 'fill':
        return zip_longest(*args, fillvalue=fillvalue)
    if incomplete == 'ignore':
        return zip(*args)
    else:
        raise ValueError('Expected fill, strict, or ignore')


def to_2bpp_indexes(data: bytes) -> list[int]:
    indexes = []
    for g in grouper(data, 2, incomplete='ignore'):
        indexes.extend([
            (((g[0] >> i) & 1) << 1) |
            ((g[1] >> i) & 1)
            for i in range(7, -1, -1)
        ])
    return indexes


def to_3bpp_indexes(data: bytes) -> list[int]:
    indexes = []
    for g in grouper(data, 3, incomplete='ignore'):
        indexes.extend([
            (((g[0] >> i) & 1) << 2) |
            (((g[1] >> i) & 1) << 1) |
            ((g[2] >> i) & 1)
            for i in range(7, -1, -1)
        ])
    return indexes


def to_4bpp_indexes(data: bytes) -> list[int]:
    indexes = []
    for g in grouper(data, 4, incomplete='ignore'):
        indexes.extend([
            (((g[0] >> i) & 1) << 3) |
            (((g[1] >> i) & 1) << 2) |
            (((g[2] >> i) & 1) << 1) |
            ((g[3] >> i) & 1)
            for i in range(7, -1, -1)
        ])
    return indexes


def to_color_indexes(data: bytes, num_colors: int):
    if num_colors == 4:
        return to_2bpp_indexes(data)
    if num_colors == 8:
        return to_3bpp_indexes(data)
    if num_colors == 16:
        return to_4bpp_indexes(data)
    if num_colors == 64 or num_colors == 256:
        # do nothing, origin raw data is just the color indexes
        return data
    raise ValueError('Expected 4, 8, 16, 64 or 256 colors in palette.')


def data_to_image(data: bytes, w: int, h: int, palette: list, hh=False, alpha=None) -> Image.Image:
    """
    Convert binary bytes to image.

    :param data:        binary bytes
    :param w:           width
    :param h:           height
    :param palette:     color table
    :param hh:          data contains only half height of size
    :return:            PIL.Image
    """
    mode = 'RGB'
    if alpha is None:
        alpha = [255] * (w*h)
    else:
        mode = 'RGBA'
    image = Image.new(mode, (w, h), BGCOLOR)
    color_indexes = to_color_indexes(data, len(palette))
    for px_index, color_index in enumerate(color_indexes):
        y, x = divmod(px_index, w)
        c = palette[color_index] + (alpha[px_index],)
        if hh:
            image.putpixel((x, 2*y), c)
            image.putpixel((x, 2*y+1), c)
        else:
            image.putpixel((x, y), c)
    return image


def load_images_with_data(data: bytes, w: int, h: int, palette: list, hh: bool, part_size: int, num_part: int) -> list[Image.Image]:
    images = []
    for i in track(range(num_part), description="Loding...   "):
        pos = i*part_size
        img = data_to_image(data[pos:pos+part_size], w, h, palette, hh)
        images.append(img)
    return images


def load_images(g: typing.Generator[bytes, None, None], w: int, h: int, palette: list, hh: bool) -> list[Image.Image]:
    data_stream = track(g, description="Loding...   ")
    return [data_to_image(data, w, h, palette, hh) for data in data_stream]


def save_index_image(images: list[Image.Image], w: int, h: int, num_col: int, filename: str) -> None:
    # index image
    if w > 96:
        console.log(':exclamation: Single image too large to generate index image.', style='yellow')
        return
    img_w = w * num_col
    img_h = h * math.ceil(len(images) / num_col)
    index_image = Image.new('RGB', (img_w, img_h), color=BGCOLOR)
    for idx, img in track(enumerate(images), description="Saving index", total=len(images)):
        pos_x = (idx % num_col) * w
        pos_y = (idx // num_col) * h
        index_image.paste(img, (pos_x, pos_y))
    index_image.save(filename)


def save_single_images(images: dict[str, Image.Image], out_dir: str, prefix: str) -> None:
    for key in track(images, description='Saving...   ', total=len(images)):
        out_filename = '{}/{}{:0>4}.png'.format(out_dir, prefix, key)
        images[key].save(out_filename)


def calc_part_size(w: int, h: int, num_colors: int, hh=False) -> int:
    """
    計算單一張頭像所佔用的 raw data 大小
    """
    bpp: int  # bits per pixel
    if num_colors == 4:
        bpp = 2
    elif num_colors == 8:
        bpp = 3
    elif num_colors == 16:
        bpp = 4
    else:
        # default 1 byte per color in palette mode (indexed-color)
        # when color-used more than 256, true-color mode instead (3 or 4 bytes per pixel)
        bpp = 8

    return int(w * h * bpp / 8 / 2) if hh else int(w * h * bpp / 8)


def basic_data_stream(filename: str, read_size: int, read_count: int) -> typing.Generator[bytes, None, None]:
    with open(filename, 'rb') as f:
        header = f.read(4)
        f.seek(0)
        buf_reader: typing.Union[io.BufferedReader, io.BytesIO]
        buf_reader = io.BytesIO(ls11_decode(f.read())) if header in LS11_MAGIC else f
        count = 0
        while data := buf_reader.read(read_size):
            if len(data) < read_size or (read_count > 0 and count >= read_count):
                break
            count += 1
            yield data


# output_images take a map or a list of Image.Image, save them to out_dir with prefix
def output_images(images: typing.Union[list[Image.Image], dict[str, Image.Image]],
                  out_dir: str, prefix: str,
                  w: typing.Optional[int] = None, h: typing.Optional[int] = None) -> None:
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # zip images with index if it's a list
    images = {str(i): img for i, img in enumerate(images)} if isinstance(images, list) else images
    image_list = list(images.values())

    if w is None or h is None:
        w, h = image_list[0].width, image_list[0].height

    # index image
    out_filename = '{}/{}00-INDEX.png'.format(out_dir, prefix)
    save_index_image(image_list, w, h, 16, out_filename)

    # single images
    save_single_images(images, out_dir, prefix)

    # output image info
    console.log(':white_check_mark: {} images saved to {}.'.format(len(images), out_dir), style='green')


def extract_images(filename: str, w: int, h: int, palette: list, out_dir: str, prefix: str, part_size=-1, num_part=-1, hh=False, data_loader=None) -> None:
    """
    A basic scaffold of loading file, save index and save single images.
    """
    if part_size == -1:
        part_size = calc_part_size(w, h, len(palette), hh)

    data_generator: typing.Generator[bytes, None, None]
    if data_loader is None:
        print('Using basic data stream loader.')
        data_generator = basic_data_stream(filename, part_size, num_part)
    elif inspect.isgeneratorfunction(data_loader):
        print('Using custom data stream loader.')
        data_generator = data_loader()
    else:  # deprecated
        print('Using custom data loader.')
        raw_data = data_loader()
        data_generator = (raw_data[i*part_size:(i+1)*part_size] for i in range(num_part))

    # if num_part == -1:
    #     num_part = len(raw_data) // part_size

    # load each single images from raw data
    images = load_images(data_generator, w, h, palette, hh)

    output_images(images, out_dir, prefix)


def create_floppy_image_loader(filename: str, offset_infos: list[tuple[int, int]]) -> typing.Callable[[], bytes]:
    """
    Create a data loader for floppy image.
    """
    def loader():
        raw_data = bytearray()
        with open(filename, 'rb') as f:
            for offset, size in offset_infos:
                f.seek(offset)
                raw_data.extend(f.read(size))
        return bytes(raw_data)
    return loader


def create_floppy_image_stream(filename: str, offset_infos: list[tuple[int, int]], read_size: int) -> typing.Callable[[], typing.Generator[bytes, None, None]]:
    """
    Create a data stream loader for floppy image.
    """
    def stream() -> typing.Generator[bytes, None, None]:
        with open(filename, 'rb') as f:
            for offset, size in offset_infos:
                f.seek(offset)
                for _ in range(size // read_size):
                    yield f.read(read_size)
    return stream


def order_of_big5(c: typing.Union[bytes, int]) -> int:
    """
    Return the order of a big5 character.

    0-base, start from '一' (0xA440)
    """
    if isinstance(c, int):
        c = c.to_bytes(2, 'big')

    if len(c) != 2:
        return -1

    hi, lo = c[0], c[1]
    offset: int
    hi_base: int
    if 0xa4 <= hi <= 0xc6:
        offset, hi_base = 0, 0xa4
    elif 0xc9 <= hi <= 0xf9:
        offset, hi_base = 5401, 0xc9
    else:
        return -1

    if 0x40 <= lo <= 0x7e:
        return offset + (hi - hi_base) * 157 + lo - 0x40
    elif 0xa1 <= lo <= 0xfe:
        return offset + (hi - hi_base) * 157 + lo - 0xa1 + 63
    else:
        return -1


def order_of_koei_tw(c: typing.Union[bytes, int]) -> int:
    """
    Return the order of a koei-tw character.

    0-base, start from '一' (0x92A0)
    """
    if isinstance(c, int):
        c = c.to_bytes(2, 'big')

    if len(c) != 2:
        return -1

    hi, lo = c[0], c[1]
    offset: int
    hi_base: int
    if hi == 0x92:
        offset, hi_base = -94, 0x92
    elif 0x92 < hi < 0xd9:
        offset, hi_base = 94, 0x93
    else:
        return -1

    if 0x30 <= lo <= 0x39:
        return offset + (hi - hi_base) * 188 + lo - 0x30
    elif 0x41 <= lo <= 0x5a:
        return offset + (hi - hi_base) * 188 + lo - 0x41 + 10
    elif 0x61 <= lo <= 0x7a:
        return offset + (hi - hi_base) * 188 + lo - 0x61 + 36
    elif 0x80 <= lo <= 0xfd:
        return offset + (hi - hi_base) * 188 + lo - 0x80 + 62
    else:
        return -1


def reverse_order_of_koei_tw(order: int) -> bytes:
    """
    Given a zero-based order, returns the corresponding koei-tw character as bytes.
    """
    if order < 0:
        return b'\x00\x00'

    order += 94  # hi[0x92] starts from 94
    hi_offset, lo_offset = divmod(order, 188)
    hi, lo = hi_offset + 0x92, -1
    if 0 <= lo_offset < 10:
        lo = 0x30 + lo_offset
    elif 10 <= lo_offset < 36:
        lo = 0x41 + lo_offset - 10
    elif 36 <= lo_offset < 62:
        lo = 0x61 + lo_offset - 36
    elif 62 <= lo_offset:
        lo = 0x80 + lo_offset - 62

    if lo == -1:
        return b'\x00\x00'

    return bytes([hi, lo])


def cns_from_order(n: int) -> str:
    """
    Return the cns11643 code from order.

    0-base, start from (0x2121), and "一" is 0x4421
    """
    if n < 0:
        return ''
    if n < 5401:
        hi, lo = divmod(n, 94)
        return '{}-{:4X}'.format(1, (hi + 0x44) << 8 | lo + 0x21)
    n -= 5546  # 5401 + 145 (MAGIC NUM)
    hi, lo = divmod(n, 94)
    return '{}-{:4X}'.format(2, (hi + 0x21) << 8 | lo + 0x21)


def cns_to_order(s: str) -> int:
    if s == '':
        return -1
    plane, code = s.split('-')
    offset = 0 if plane == '1' else 5546
    hi_start = '44' if plane == '1' else '21'
    hi = int(code[:2], 16) - int(hi_start, 16)
    lo = int(code[2:], 16) - int('21', 16)
    return offset + hi * 94 + lo


def load_cns11643_unicode_table(filename: str = '../Unicode/CNS2UNICODE_Unicode BMP.txt') -> dict[str, str]:
    table = {'': ''}
    with open(filename, 'r') as f:
        while entry := f.readline():
            tokens = [str(x) for x in entry.split('\t')]
            if tokens[0][:2] not in ['1-', '2-']:
                continue
            code_point = int(tokens[1].strip(), 16)
            table[tokens[0]] = chr(code_point)
    # print('cns11643 table loaded with {} code points.'.format(len(table)))
    return table


def to_unicode_name(s: bytes) -> str:
    """
    Convert a string to unicode name.
    """
    if 32 <= s[0] <= 126:
        try:
            return s.decode('ascii').strip('\x00')
        except UnicodeDecodeError:
            print('decode error: {}'.format(s))
            return ''
    global cns11643_unicode_table
    if len(cns11643_unicode_table) == 0:
        cns11643_unicode_table = load_cns11643_unicode_table()
    words = struct.unpack('>' + 'H'*int(len(s)/2), s)
    return ''.join([cns11643_unicode_table[cns_from_order(order_of_koei_tw(w))] for w in words])


def to_koeitw(s: str) -> bytes:
    """
    Convert a string to koeitw.
    """
    global cns11643_unicode_table
    if len(cns11643_unicode_table) == 0:
        cns11643_unicode_table = load_cns11643_unicode_table()
    global unicode_koeitw_table
    if len(unicode_koeitw_table) == 0:
        for i in range(5401):
            u_char = cns11643_unicode_table[cns_from_order(i)]
            k_char = reverse_order_of_koei_tw(i)
            # print(i, u_char, k_char.hex())
            unicode_koeitw_table[u_char] = k_char

    return reduce(lambda x, y: x + y, [unicode_koeitw_table[x] for x in s])


def kao2str(face: int, upper_limit: int = -1, one_base: bool = False) -> str:
    """
    Convert a kao face to string.

    one_base: face number in game data is one-base. If True, minus 1 to meet zero-base.
    """
    if upper_limit != -1 and face > upper_limit:
        # convert face from number to hex string
        return hex(face)[2:].upper()

    face = face - 1 if one_base else face
    # return '[red]'+str(face)
    return str(face)


def build_table(title: str, headers: list[H]) -> Table:
    """
    Build a table with title and headers.
    """
    table = Table(title=title)
    for h in headers:
        args = column_arguments(h)
        table.add_column(h.text, justify=args['justify'], style=args['style'])
    return table


def load_person(data: list[bytes], format: str, ptype: typing.Type) -> list:
    persons = []
    for idx, pd in enumerate(data):
        try:
            p = ptype._make(struct.unpack(format, pd))
            p.id = idx
            persons.append(p)
        except struct.error:
            print('struct error: [{}]{}'.format(idx, pd))
    return persons


def print_table(title: str, headers: list, persons: list, to: str = 'rich') -> None:
    """
    Print a list of persons in table format.
    """
    if to == 'csv':
        print(','.join([h.text for h in headers]))
        for p in persons:
            print(','.join([p[h.name] for h in headers]))
        return
    elif to == 'json':
        writer = JsonTableWriter(
            table_name=title,
            headers=[h.text for h in headers],
            value_matrix=[[p[h.name] for h in headers] for p in persons],
        )
        writer.write_table()
        return
    elif to == 'markdown' or to == 'md':
        writer = MarkdownTableWriter(
            table_name=title,
            headers=[h.text for h in headers],
            value_matrix=[[p[h.name] for h in headers] for p in persons],
        )
        writer.write_table()
        return

    table = build_table(title, headers)
    for p in persons:
        table.add_row(*[p[h.name] for h in headers])

    console.print(table)


def conv_palette(_16bit: int) -> tuple[int, int, int]:
    """
    input 16-bit color, output 24-bit color
    """
    b = (_16bit >> 0) & 0x0F
    r = (_16bit >> 4) & 0x0F
    g = (_16bit >> 8) & 0x0F

    r = r * 0x11
    g = g * 0x11
    b = b * 0x11

    return (r, g, b)


def pack():
    """
    npk pack
    """


def unpack_npk(src: bytes, line, height) -> bytes:
    """
    return size of unpacked data
    """
    data = io.BytesIO(src)
    dest = bytearray()
    bitflag = 0x0000
    data_len = len(src)
    dest_len = line * height
    while (data.tell() < data_len and len(dest) < dest_len):
    # while (data.tell() < data_len and len(dest) <= 10240):
        if not (bitflag & 0xFF00):
            # 這個 if 裡的操作相當於透過 bigflag 做 for i in range(8)
            bitflag = 0xFF00 | data.read(1)[0]
        # print('bitflag: {}, cursor={}, dest_len={}'.format(hex(bitflag), data.tell(), len(dest)))

        if bitflag & 1:
            # read 1 byte, and copy to dest
            # let b = 0b A0 B0 B1 C0 C1 C2 C3 C4
            #                     ^^^^^^^^^^^^^^ repeat count (1~32) * 4
            #               ^^^^^ offset (1~4) * 4
            #            ^^ over_line, if true, offset *= line (ignore the '4' above)
            b = data.read(1)[0]
            run_size = ((b & 0x1F) + 1)         # info.len / repeat count
            run_offset = ((b & 0x60) >> 5) + 1  # info.range
            run_offset = run_offset * line if (b & 0x80) else run_offset * 4
            # print(f'{data.tell(): 6d} type: {bitflag:016b}, dir: {(b & 0x80) >> 7}, offset: {run_offset}, run_size: {run_size}, dest_len: {len(dest)}')
            for _ in range(run_size*4):
                dest.append(dest[-run_offset])
        else:
            # read 2 bytes, and convert to 4 bytes to dest
            # let b1 = 0b A0 A1 A2 A3 A4 A5 A6 A7
            #     b2 = 0b B0 B1 B2 B3 B4 B5 B6 B7
            # convert to:
            #     d1 = 0b  0  0  0  0 A0 A4 B0 B4
            #     d2 = 0b  0  0  0  0 A1 A5 B1 B5
            #     d3 = 0b  0  0  0  0 A2 A6 B2 B6
            #     d4 = 0b  0  0  0  0 A3 A7 B3 B7
            try:
                b1 = data.read(1)[0]
                b2 = data.read(1)[0]
            except:
                print(len(dest), data.tell())
                break
            for _ in range(4):
                d = ((b1 & 0x80) >> 4) | ((b1 & 0x08) >> 1) | \
                    ((b2 & 0x80) >> 6) | ((b2 & 0x08) >> 3)
                dest.append(d)
                b1 = (b1 << 1) & 0xFF
                b2 = (b2 << 1) & 0xFF
            # print(f'{data.tell(): 6d} type: {bitflag:016b}, dest_len: {len(dest)}')

        bitflag >>= 1

    if data_len - data.tell() > 0:
        print(f'    used: {data.tell():6d} left: {data_len-data.tell():6d}')
    return bytes(dest)


def unpack_npk_3bits(src: bytes, line, height) -> bytes:
    """
    return size of unpacked data
    """
    data = io.BytesIO(src)
    dest = bytearray()
    data_len = len(src)
    dest_len = line * height
    while (data.tell() < data_len and len(dest) < dest_len):
        b = data.read(1)[0]
        if b & 0x80:
            run_size = ((b & 0x0F) + 1)         # info.len
            run_offset = ((b & 0x30) >> 4) + 1  # info.range
            run_offset = run_offset * line if (b & 0x40) else run_offset * 4
            for _ in range(run_size*4):
                dest.append(dest[-run_offset])
            # print(f'{data.tell(): 6d} type: {b:08b}, dir: {b & 0x40}, offset: {run_offset}, run_size: {run_size} pos={len(dest)}')
        else:
            b1 = b
            b2 = data.read(1)[0]
            count = ((b1 & 0xF0) >> 4) + 1
            buf = []
            for _ in range(4):
                d = ((b1 & 0x08) >> 1) | ((b2 & 0x80) >> 6) | ((b2 & 0x08) >> 3)
                buf.append(d)
                b1 = b1 << 1
                b2 = b2 << 1
            dest.extend(buf * count)
            # print(f'{data.tell(): 6d} type: {(b1>>4):02x} {(b2>>4):02x}, count: {count}, buf: {buf} pos={len(dest)}')
    if data_len - data.tell() > 0:
        print(f'    used: {data.tell():6d} left: {data_len-data.tell():6d}')
    return bytes(dest)


def pe_resources(data: bytes, rtype: int) -> list[tuple[int, bytes]]:
    """(id, bytes) of each resource of numeric type `rtype` in a PE file (first language only)."""
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec, opt = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    secs = [struct.unpack_from("<IIII", data, pe + 24 + opt + 40 * i + 8) for i in range(nsec)]
    rsrc = struct.unpack_from("<I", data, pe + 24 + (96 if opt == 0xE0 else 112) + 8 * 2)[0]

    def offset(rva):
        return next(rva - va + raw for vsize, va, rsize, raw in secs if va <= rva < va + max(vsize, rsize))

    base = offset(rsrc)

    def entries(o):
        named, ids = struct.unpack_from("<HH", data, base + o + 12)
        return [struct.unpack_from("<II", data, base + o + 16 + 8 * i) for i in range(named + ids)]

    out = []
    for tid, tdir in entries(0):
        if tid != rtype:
            continue
        for rid, rdir in entries(tdir & 0x7FFFFFFF):
            _, leaf = entries(rdir & 0x7FFFFFFF)[0]
            rva, size = struct.unpack_from("<II", data, base + leaf)
            out.append((rid, data[offset(rva):offset(rva) + size]))
    return out
