"""信長の野望・武将風雲録 PC-98 (nobu4-pc98): event pictures, 茶器 and paintings, opening/ending pictures, fans, and
the MAIN.EXE string table. Formats and evidence: notes/nobu4.md「事件、插圖、道具」.

- PACKDATA.DAT, OPEN.DAT, ENDING.DAT hold images in KOEI's 4-pixel-unit compression (DOS MAIN.EXE 0x33DA decodes
  straight into VGA memory): u16 width, u16 height, then per row commands of 4-pixel units (nibbles of the three
  planes): 1kkknnnn with bit 6 clear copies n+1 units from k+1 units to the left, with bit 6 set from k+1 rows above;
  0nnnpppp qqqqrrrr fills n+1 units with the pattern (plane 1 = p, plane 0 = r, plane 2 = q). A command may run past
  the row end; the rest of that command is dropped from the picture. PACKDATA images start on 512-byte blocks (the
  game seeks block * 512, DOS 0x8404); OPEN.DAT and ENDING.DAT images follow each other.
- OUGICHAK.DAT and KAIGA.DAT are raw 3bpp (3 bytes per 8 pixels, utils.to_3bpp_indexes order, drawn by DOS 0x286A).
"""
import csv
import os
import struct

import click
from PIL import Image

import koei_games
import utils

# colour of VGA plane bits (plane 0 = bit 0) in the PC-98 game screens (captures guest os_031/032: event stills)
MAIN_PALETTE = [(0, 0, 0), (0, 0, 207), (0, 255, 0), (0, 255, 255), (255, 0, 0), (255, 0, 207), (255, 255, 0),
                (255, 255, 207)]
# OPEN.EXE's palette (capture guest os_007, 伊達晴宗's card); END.EXE's is assumed to be the same
OPEN_PALETTE = [(0, 0, 0), (16, 16, 255), (16, 255, 16), (16, 255, 255), (255, 16, 16), (255, 16, 255),
                (255, 255, 16), (255, 255, 255)]
# to_3bpp_indexes index (byte 0 = bit 2) -> VGA plane bits: byte 0 is plane 0, byte 1 plane 2, byte 2 plane 1
RAW_TO_PLANES = [(i >> 2 & 1) | (i & 1) << 1 | (i >> 1 & 1) << 2 for i in range(8)]

# PACKDATA block -> (file name, Japanese name, PC-98 MAIN.EXE image offset of a call showing it, evidence)
EVENT_STILLS = {
    9: ("09-invasion", "出陣・侵攻", "0xC1EB 「%s領 %sへ攻め込みました」", "✅ code, capture: guest os_032"),
    21: ("21-ninja", "忍者", "0x15CDC 「忍者を送り」", "✅ code"),
    29: ("29-ikki", "一揆", "0x2C613 「内政を怠った報いです」", "✅ code"),
    40: ("40-rebellion", "謀叛", "0x2E726、0x2ECF0 「謀叛を起こし、大名となり」", "✅ code"),
    48: ("48-epidemic", "疫病", "0x2C804 「で疫病が発生したもようです」", "✅ code"),
    58: ("58-good-harvest", "豊作", "0x2CAFB 「今年は各地で豊作の秋を迎えています」", "✅ code"),
    69: ("69-bad-harvest", "凶作", "0x2CB24 「今年は全国的な凶作に見舞われています」", "✅ code"),
    80: ("80-tea-ceremony", "茶会", "0x15289 「今井宗久殿を招待し」", "✅ code"),
    88: ("88-typhoon", "台風", "0x2D629 「%sの台風が近づいています」", "✅ code"),
    100: ("100-meeting", "会見・密会", "0xCE99 「会っているようです」、0xD3F2 外交の返答", "✅ code, capture: guest os_031"),
    108: ("108-earthquake", "地震", "0x2D2AB 「%s沖で%s地震が発生したもようです」", "✅ code"),
    118: ("118-heavy-snow", "大雪", "0x2C95D 「は大雪に見舞われています」", "✅ code"),
    128: ("128-bombard-ship", "砲撃（鉄甲船）", "0x24580（戦闘の砲撃、条件で 128／141）", "🟡 code; which is which by the picture"),
    141: ("141-bombard-cannon", "砲撃（大砲）", "0x24580（戦闘の砲撃、条件で 128／141）", "🟡 code; which is which by the picture"),
    150: ("150-azuchi-castle", "安土城築城", "0x2A9D9 「政秀寺開山 沢彦」「安土城」", "✅ code"),
    169: ("169-imperial-envoy", "朝廷使者（改名）", "0x2A785 「朝廷使者」「改名し」", "✅ code"),
    186: ("186-honnoji", "本能寺の変", "0x2E175 「明智軍に寝返り」「織田信忠も…自刃して果てました」", "✅ code"),
    209: ("209-arson", "放火", "0x2AC38 「城から火の手が！！！」「米蔵に火がつけられた」", "✅ code"),
    220: ("220-assassination", "暗殺", "0x103A1 「が斬られた」", "✅ code"),
    232: ("232-gold-mine", "金山", "0x111FC 「金山が見つかり」", "✅ code"),
    241: ("241-ironclad", "鉄甲船完成", "0x8CD8 「鉄甲船ができ上り」", "✅ code"),
}
OPEN_NAMES = ["koei-logo", "koei-presents", "rekishi-simulation-game", "kou-shibusawa-production", "title",
              "title-bu", "title-shou", "title-fuu", "title-un", "title-roku", "mask-1", "mask-2", "mask-3", "frame",
              "date-harumune", "uesugi-kenshin", "takeda-shingen", "houjou-ujiyasu", "imagawa-yoshimoto",
              "saitou-dousan", "asakura-yoshikage", "azai-hisamasa", "miyoshi-nagayoshi", "mouri-motonari",
              "chousokabe-kunichika", "ootomo-sourin", "ryuuzouji-takanobu", "shimazu-takahisa", "oda-nobunaga"]
OPEN_DAIMYO = ["伊達晴宗", "上杉謙信", "武田信玄", "北条氏康", "今川義元", "斎藤道三", "朝倉義景", "浅井久政", "三好長慶",
               "毛利元就", "長宗我部国親", "大友宗麟", "龍造寺隆信", "島津貴久", "織田信長"]
# 茶器 kinds (MAIN.EXE DS:0x9E4C), painters (DS:0x9F9E, the painting index is the painter id - 0x1E 🟡) and fans
TEA_KINDS = ["茶碗", "茶入", "茶壷", "茶釜", "花入"]
PAINTERS = ["狩野永徳", "長谷川等伯", "海北友松", "狩野山楽"]
SEASONS = ["spring", "summer", "autumn", "winter"]
# item-name gaiji (GAIJI.DAT glyphs, read off the glyphs)
ITEM_GAIJI = {0xA9: "蛛", 0xAA: "絆", 0xAB: "蝗", 0xAC: "蟲", 0xAD: "盞", 0xAE: "鞁", 0xAF: "鷗", 0xB0: "霰"}
TEA_RECORDS, TEA_COUNT = 0x890, 48  # SNDATAn.CIM: 16 bytes, name 12, 0, u16 holder pointer, kind | value << 3
FAN_BYTES, TEA_PICTURE_BYTES, PAINTING_BYTES = 96 * 64 * 3 // 8, 48 * 64 * 3 // 8, 30 * 152 * 3


def decode_pack(data: bytes, pos: int):
    """-> (VGA plane-bit rows, width, height, bytes used), or None when the header is not a picture."""
    w, h = struct.unpack_from("<HH", data, pos)
    if not (0 < w <= 640 and 0 < h <= 480):
        return None
    units, stride = (w + 3) >> 2, 160 + 16
    cells = [0] * (stride * (h + 4))  # 4 spare rows on top for references above the picture
    p = pos + 4
    for y in range(h):
        x = 0
        while x < units:
            c = data[p]
            p += 1
            di = (y + 4) * stride + x
            if c & 0x80:
                n, k = (c & 15) + 1, c >> 4 & 3
                src = di - (k + 1) * (stride if c & 0x40 else 1)
                for i in range(n):
                    if x + i < stride:
                        cells[di + i] = cells[src + i]
            else:
                e = data[p]
                p += 1
                n, v = (c >> 4 & 7) + 1, (e & 15) | (c & 15) << 4 | (e >> 4) << 8
                for i in range(n):
                    if x + i < stride:
                        cells[di + i] = v
            x += n
    rows = []
    for y in range(h):
        row = []
        for x in range(units):
            v = cells[(y + 4) * stride + x]
            for s in range(3, -1, -1):
                row.append((v >> s & 1) | (v >> 4 + s & 1) << 1 | (v >> 8 + s & 1) << 2)
        rows.append(row[:w])
    return rows, w, h, p - pos


def _image(rows, palette):
    im = Image.new("P", (len(rows[0]), len(rows)))
    im.putpalette([c for rgb in palette for c in rgb])
    im.putdata([v for row in rows for v in row])
    return im


def _raw_image(data, width, palette=MAIN_PALETTE):
    idx = utils.to_3bpp_indexes(data)
    return _image([[RAW_TO_PLANES[i] for i in idx[y * width:(y + 1) * width]] for y in range(len(idx) // width)],
                  palette)


def _write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _read(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return f.read()


def event_stills(game_dir, out):
    data = _read(game_dir, "PACKDATA.DAT")
    os.makedirs(out, exist_ok=True)
    rows = []
    for block, (file, name, where, evidence) in EVENT_STILLS.items():
        pic, w, h, used = decode_pack(data, block * 512)
        _image(pic, MAIN_PALETTE).save(os.path.join(out, f"{file}.png"))
        rows.append([f"{file}.png", name, w, h, f"PACKDATA.DAT block {block} (0x{block * 512:X}, {used} bytes)",
                     where, evidence])
    _write_csv(os.path.join(out, "index.csv"), ["file", "name", "width", "height", "source", "shown by", "evidence"],
               rows)
    return len(rows)


def sequence(game_dir, name, palette, out, names=None):
    """OPEN.DAT / ENDING.DAT: pictures one after the other until a header is not a picture."""
    data = _read(game_dir, name)
    os.makedirs(out, exist_ok=True)
    rows, pos = [], 0
    while pos < len(data) - 4:
        r = decode_pack(data, pos)
        if not r:
            break
        pic, w, h, used = r
        k = len(rows)
        file = f"{k:02d}-{names[k]}.png" if names else f"{k:02d}.png"
        _image(pic, palette).save(os.path.join(out, file))
        label = OPEN_DAIMYO[k - 14] if names and k >= 14 else ""
        rows.append([file, label, w, h, f"{name} 0x{pos:X} ({used} bytes)"])
        pos += used
    _write_csv(os.path.join(out, "index.csv"), ["file", "daimyo", "width", "height", "source"], rows)
    return len(rows), pos


def fans(game_dir, out):
    data = _read(game_dir, "OUGICHAK.DAT")
    os.makedirs(out, exist_ok=True)
    rows = []
    for s, season in enumerate(SEASONS):
        for f in range(5):
            o = (5 * s + f) * FAN_BYTES
            file = f"{season}-{f}.png"
            _raw_image(data[o:o + FAN_BYTES], 96).save(os.path.join(out, file))
            rows.append([file, season, f, f"OUGICHAK.DAT 0x{o:X}"])
    _write_csv(os.path.join(out, "index.csv"), ["file", "season", "frame", "source"], rows)
    return len(rows)


def _item_name(raw):
    out, raw, i = "", raw.split(b"\0")[0], 0
    while i < len(raw):
        if raw[i] == 0xEB:
            out += ITEM_GAIJI.get(raw[i + 1]) or koei_games.NOBU4_GAIJI[raw[i + 1]]
            i += 2
        else:
            n = 2 if 0x81 <= raw[i] <= 0x9F or raw[i] >= 0xE0 else 1
            out += raw[i:i + n].decode("cp932")
            i += n
    return out


def items(game_dir, out):
    data = _read(game_dir, "OUGICHAK.DAT")
    os.makedirs(os.path.join(out, "pictures"), exist_ok=True)
    base = 20 * FAN_BYTES
    for k in range(15):
        o = base + k * TEA_PICTURE_BYTES
        _raw_image(data[o:o + TEA_PICTURE_BYTES], 48).save(os.path.join(out, "pictures", f"tea-{k:02d}.png"))
    kaiga = _read(game_dir, "KAIGA.DAT")
    for k, painter in enumerate(PAINTERS):
        rec = kaiga[k * PAINTING_BYTES:(k + 1) * PAINTING_BYTES]
        # 30 columns of 8 pixels, each 152 rows of 3 bytes (DOS 0x30A30 draws one column per call)
        im = Image.new("P", (240, 152))
        im.putpalette([c for rgb in MAIN_PALETTE for c in rgb])
        for c in range(30):
            col = _raw_image(rec[c * 456:(c + 1) * 456], 8)
            im.paste(col, (8 * c, 0))
        im.save(os.path.join(out, "pictures", f"painting-{k}.png"))
    rows = []
    scenarios = [_read(game_dir, f"SNDATA{n}.CIM") for n in (1, 2, 3)]
    for k in range(TEA_COUNT):
        recs = [s[TEA_RECORDS + 16 * k:][:16] for s in scenarios]
        kind = recs[0][15] & 7
        row = [k, _item_name(recs[0][:12]), TEA_KINDS[kind]]
        for s, r in zip(scenarios, recs):
            value, ptr = r[15] >> 3, struct.unpack_from("<H", r, 13)[0]
            holder = koei_games.nobu4_pc98_name(s[ptr - 0x40:][:7]) + koei_games.nobu4_pc98_name(
                s[ptr - 0x40 + 7:][:7]) if ptr else ""
            row += ["" if value == 31 else value, holder,
                    "" if value == 31 else f"pictures/tea-{3 * kind + value // 10:02d}.png"]
        rows.append(row)
    header = ["id", "name", "kind"]
    for n in (1, 2, 3):
        header += [f"value_s{n}", f"holder_s{n}", f"picture_s{n}"]
    _write_csv(os.path.join(out, "chaki.csv"), header, rows)
    _write_csv(os.path.join(out, "paintings.csv"), ["file", "painter", "source"],
               [[f"pictures/painting-{k}.png", p, f"KAIGA.DAT 0x{k * PAINTING_BYTES:X}"] for k, p in enumerate(PAINTERS)])
    return len(rows)


def strings(game_dir, out):
    """All Shift-JIS strings of MAIN.EXE's data segment (DGROUP at image 0x37990), with their DS offsets."""
    d = _read(game_dir, "MAIN.EXE")
    seg = d[struct.unpack_from("<H", d, 8)[0] * 16 + 0x37990:]
    rows, o = [], 0
    while o < len(seg):
        e = seg.find(b"\0", o)
        if e < 0:
            break
        raw = seg[o:e]
        if len(raw) >= 4:
            try:
                text = raw.decode("cp932")
            except UnicodeDecodeError:
                text = None
            if text and any(ord(ch) > 0x3000 for ch in text):
                rows.append([f"0x{o:04X}", text])
        o = e + 1
    os.makedirs(out, exist_ok=True)
    _write_csv(os.path.join(out, "strings.csv"), ["ds_offset", "text"], rows)
    return len(rows)


@click.command()
@click.option("--game-dir", required=True, help="games/nobu4-pc98")
@click.option("--out", required=True, help="output directory, e.g. games/nobu4-pc98/extract")
def nobu4_extras(game_dir, out):
    """信長の野望・武将風雲録 PC-98: event stills, 茶器, paintings, fans, opening/ending pictures, strings."""
    n = event_stills(game_dir, os.path.join(out, "eventcg"))
    k, _ = sequence(game_dir, "OPEN.DAT", OPEN_PALETTE, os.path.join(out, "eventcg", "opening"), OPEN_NAMES)
    e, _ = sequence(game_dir, "ENDING.DAT", OPEN_PALETTE, os.path.join(out, "eventcg", "ending"))
    f = fans(game_dir, os.path.join(out, "items", "fans"))
    t = items(game_dir, os.path.join(out, "items"))
    s = strings(game_dir, os.path.join(out, "events"))
    print(f"{n} event stills, {k} opening and {e} ending pictures, {f} fan frames, {t} 茶器 + 15 pictures, "
          f"4 paintings, {s} strings")
