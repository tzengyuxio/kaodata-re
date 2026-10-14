import os
import struct
import click
from PIL import Image
from utils import (
    BGCOLOR,
    LITTLE_ENDIAN,
    color_codes_to_palette,
    save_index_image,
    save_single_images,
    to_unicode_name,
    unpack_npk,
    unpack_npk_3bits,
)

liberty_colors = [
    "#000000",
    "#104192",
    "#b25110",
    "#a27171",
    "#417100",
    "#82a2b2",
    "#e3b292",
    "#f3e3d3",
    "#000000",
    "#001082",
    "#105110",
    "#a28241",
    "#208230",
    "#4161d3",
    "#b29271",
    "#f3f3f3",
]

liberty_event_colors = [
    "#000000",
    "#104192",
    "#b25110",
    "#a27171",
    "#417100",
    "#82a2b2",
    "#e3b292",
    "#f3e3d3",
    "#000000",
    "#001082",
    "#714120",
    "#928230",
    "#a29271",
    "#616192",
    "#d3a251",
    "#a2a2a2",
]

liberty_face_colors = [
    "#000000",
    "#104192",
    "#b25110",
    "#a27171",
    "#417100",
    "#82a2b2",
    "#e3b292",
    "#f3e3d3",
]


@click.group()
def liberty():
    """獨立戰爭 / 独立戦争 / Liberty or Death

    \b
    発売日: 1993
    可解析檔案 (DOS 中文版):
        COMMAND.IDX     命令
        CREDIT.IDX      LOGO
        EVENT.IDX       歷史事件
        FACE.IDX        顏ＣＧ
        MAP.IDX         地圖, 部分 UI
        MOUSE.IDX       UI 元件
    """
    pass


@click.command(help="CG 解析")
@click.option("-f", "--file", "cg_file", help="圖像檔案", required=True)
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
@click.option("--prefix", "prefix", default="", help="filename prefix of output files")
def liberty_cg(cg_file, out_dir, prefix):
    """
    ./dekoei.py liberty face -f ~/DOSBox/LIBERTY/GRAPHICS.IDX --out_dir LIBERTY --prefix "GRAPHICS"
    """
    os.makedirs(out_dir, exist_ok=True)

    palette = (
        color_codes_to_palette(liberty_event_colors)
        if "event" in cg_file.lower()
        else color_codes_to_palette(liberty_colors)
    )

    with open(cg_file, "rb") as f:
        header = f.read(3)
        if header != b"IDX":
            print("not IDX file")
            return
        count = int.from_bytes(f.read(1), LITTLE_ENDIAN)

        offsets = []
        for _ in range(count):
            offset = int.from_bytes(f.read(4), LITTLE_ENDIAN)
            offsets.append(offset)
        file_size = os.stat(cg_file).st_size
        offsets.append(file_size)

        for i in range(len(offsets) - 1):
            offset = offsets[i]
            size = offsets[i + 1] - offset
            f.seek(offset)
            npk_data = f.read(size)
            width = int.from_bytes(npk_data[0x0C:0x0E], LITTLE_ENDIAN)
            height = int.from_bytes(npk_data[0x0E:0x10], LITTLE_ENDIAN)
            # palette = npk_data[0x10:0x30]
            color_indexes = unpack_npk(npk_data[0x30:], width)
            image = Image.new("RGB", (width, height), BGCOLOR)
            for px_index, color_index in enumerate(color_indexes):
                y, x = divmod(px_index, width)
                c = palette[color_index]
                image.putpixel((x, y), c)
            image.save(f"{out_dir}/{prefix}{i:03d}.png")
        print(f"save {count} images")


@click.command(help="顏 CG 解析")
@click.option("-f", "--face", "face_file", help="頭像檔案", required=True)
@click.option("--out_dir", "out_dir", default="_output", help="output directory")
@click.option("--prefix", "prefix", default="", help="filename prefix of output files")
def liberty_face(face_file, out_dir, prefix):
    """
    dekoei.py liberty face -f ~/DOSBox/LIBERTY/FACE.IDX --out_dir LIBERTY --prefix "FACE"
    dekoei.py liberty face -f ~/dosbox/LIBERTY/FACE.IDX --out_dir _output_liberty_face3 --prefix LIBERTY_DOS_F
    """
    os.makedirs(out_dir, exist_ok=True)

    face_w, face_h = 64, 80
    palette = color_codes_to_palette(liberty_face_colors)
    images = []
    with open(face_file, "rb") as f:
        f.read(3)  # 'IDX'
        f.read(1)  # 0x2B (43), 應該是 0x12B (299), 高位元被截斷
        n = 299

        offsets = []
        for _ in range(n):
            offset = int.from_bytes(f.read(4), LITTLE_ENDIAN)
            offsets.append(offset)
        file_size = os.stat(face_file).st_size
        offsets.append(file_size)

        for i in range(len(offsets) - 1):
            offset = offsets[i]
            size = offsets[i + 1] - offset
            f.seek(offset)
            data = f.read(size)
            face_w = int.from_bytes(data[0:2], LITTLE_ENDIAN)
            face_h = int.from_bytes(data[2:4], LITTLE_ENDIAN)
            color_indexes = unpack_npk_3bits(data[4:], face_w, face_h)
            # print(f'#{idx:03d} {width}x{height} {len(color_indexes)}')
            image = Image.new("RGB", (face_w, face_h), BGCOLOR)
            for px_index, color_index in enumerate(color_indexes):
                y, x = divmod(px_index, face_w)
                c = palette[color_index]
                image.putpixel((x, y), c)
            images.append(image)
    # save face index: all, special, mob
    save_index_image(images, face_w, face_h, 16, f"{out_dir}/{prefix}00-INDEX.png")
    # save single faces
    images = (
        {str(i): img for i, img in enumerate(images)}
        if isinstance(images, list)
        else images
    )
    save_single_images(images, out_dir, prefix)


liberty.add_command(liberty_cg, "cg")
liberty.add_command(liberty_face, "face")


# ---------------------------------------------------------------- DOS (Chinese, port of the Japanese DOS/V release)
# see notes/liberty.md; MAIN.EXE offsets are DGROUP (load image 0x357F0, file + 0x5000) offsets
LIBERTY_FACES = 299  # FACE.IDX stores the count as a byte (0x2B)
LIBERTY_DGROUP = 0x5000 + 0x357F0
LIBERTY_PERSONS = (0x3A0A, 58, 250)  # given name at +18, surname at +35 (17 bytes each); face = person number
LIBERTY_OFFICIALS = (0x33D2, 34, 44)  # 2 sides x 22 slots; given name at +4 (13 bytes), surname at +17


def load_liberty_faces(face_idx) -> list[bytes]:
    """FACE.IDX: "IDX", count byte, dword offsets; each face is u16 w, u16 h and NPK 3-bit data."""
    with open(face_idx, "rb") as f:
        data = f.read()
    offsets = list(struct.unpack_from(f"<{LIBERTY_FACES}I", data, 4)) + [len(data)]
    faces = []
    for a, b in zip(offsets, offsets[1:]):
        w, h = struct.unpack_from("<HH", data, a)
        faces.append(bytes(unpack_npk_3bits(data[a + 4:b], w, h)))
    return faces


def liberty_name(given: bytes, surname: bytes) -> str:
    def part(raw):
        raw = raw.split(b"\0")[0]
        return to_unicode_name(raw) if raw else ""
    return part(given) + "・" + part(surname)


def load_liberty_dos_names(main_exe) -> tuple[list[str], list[str]]:
    """Person names (250) and the initial names of the 44 official slots, from MAIN.EXE."""
    with open(main_exe, "rb") as f:
        ds = f.read()[LIBERTY_DGROUP:]
    offset, size, count = LIBERTY_PERSONS
    persons = [liberty_name(ds[offset + i * size + 18:][:17], ds[offset + i * size + 35:][:17]) for i in range(count)]
    offset, size, count = LIBERTY_OFFICIALS
    officials = [liberty_name(ds[offset + i * size + 4:][:13], ds[offset + i * size + 17:][:17]) for i in range(count)]
    return persons, officials
