"""信長の野望・蒼天録 with PK (Steam, appid 628130): event pictures, 家宝, 家紋, the 官位 / 役職 / 城 descriptions, the
message file, the big map and the other picture sets, written under --out (notes/nobu10.md「事件、插圖、道具」).

- Every DATA/*.NBX picture file is the KAOCG.NBX container: u32 count, count x 44 bytes (u32 offset, size, width,
  height, LWC flag, bits per pixel 8 / 24, 4 x 0, palette number), the data; then u32 palette count, count x
  (u32 offset, size, LWC flag) and the palettes (256 x B, G, R, X). Flagged data is LWC (ls11.lwc_decode). Pixels
  are a bottom-up DIB, rows padded to 4 bytes; 24-bit rows are B, G, R.
- GMAP1 / GMAP2.NBX: 36 tiles, 9 a row (8 x 800 + 724 wide, 3 x 600 + 200 high): the 7124 x 2000 map; the castle
  points of GMAP_POS.NBX fall on it.
- 家宝: scenario 0x8E6C2, 460 records of 61 bytes: +0 name (13), +13 reading (hiragana, 34), +50 kind (KINDS),
  +51 grade (0 十等級 - 9 一等級), +52 picture (KAHOU.NBX), +53 生産国 (0 日本, 1 南蛮, 2 明国), +54..+57 unknown,
  +58 u16 holder (officer serial, 0xFFFE none), +60 flags. The names and descriptions are RETSUDEN.NBX entries
  3796 + 2k, 3797 + 2k; then 350 官位 (4716-), 75 役職 (5416-) and the 250 城 (5566-), name / description pairs.
- 家紋 n is the 家紋 of 血族 n (officer record +67); 220-228 are the faction marks (国人, 商人, 仏, キリスト教 ...).
- MESSAGE.NBX: u16 count, u32 offsets, Shift-JIS strings with the same codes as the 列伝 (wiki_nobu10.kana_text):
  ESC K / ESC H switch the script, 0x02 x y is a variable, 0x04 .. 0x05 0x05 0x05 a condition, 0x05 0x05 0x05 ends.
"""
import collections
import csv
import os
import re
import struct

import click
from PIL import Image

import ls11
import wiki_nobu10 as w

ITEMS, ITEM_SIZE, ITEM_COUNT = 0x8E6C2, 61, 460
# RETSUDEN.NBX (name, description) pairs after the officers' 列伝: (first entry, count, file)
RETSUDEN_TABLES = [(3796, 460, None), (4716, 350, "tables/kani.csv"), (5416, 75, "tables/yakushoku.csv"),
                   (5566, 250, "tables/castles.csv")]
# 家宝 kinds, grades and 生産国 (Nobunaga10WPK.exe 0x479B50-0x479CB8, stored in reverse order)
KINDS = ["茶入", "茶壺", "茶釜", "茶碗", "花入", "茶杓", "香炉", "水指", "刀剣", "槍", "火縄銃", "管打銃", "短筒", "大筒",
         "具足", "兜", "名馬", "剣術書", "農業書", "商業書", "建築書", "逸話物", "外交書", "武術書", "馬術書", "砲術書",
         "知識書", "兵法書", "医書", "水墨画", "彩色画", "菓子", "地酒", "香木"]
ORIGINS = ["日本", "南蛮", "明国"]
GRADES = ["十", "九", "八", "七", "六", "五", "四", "三", "二", "一"]
GMAP_COLUMNS = 9
KAMON_CLANS = 220  # 家紋 220-228 are the faction marks, not clans
# (file, folder): picture sets written one PNG per entry. TUTOPRTS.NBX (114 tutorial screenshots, 124 MB) is left out.
PICTURES = [
    ("REVENT.NBX", "eventcg/history"),      # 40 x 720x400 historical events
    ("CMDSTILL.NBX", "eventcg/command"),    # 46 x 360x240 command / disaster / common event stills
    ("HYOUJOU.NBX", "eventcg/hyoujou"),     # 48 評定 scenes and parts
    ("YsStill.NBX", "eventcg/field"),       # 17 x 320x240 野戦 stills
    ("KJSSTLCG.NBX", "eventcg/siege"),      # 9 x 320x240 攻城戦 stills
    ("SEASON.NBX", "eventcg/season"),       # 16 seasons screens and banners
    ("INIT.NBX", "eventcg/init"),           # 179 title, scenario selection and setup screens
    ("REFERENC.NBX", "eventcg/reference"),  # 9 reference screen pictures
    ("NINANIME.NBX", "anime/ninja"),        # 238 忍者 animation frames
    ("KOUANIME.NBX", "anime/kou"),          # 1742 animation frames
    ("CMDANIME.NBX", "anime/command"),      # 573 command animation frames
    ("KAHOU.NBX", "items/pictures"),        # 38 x 120x120, one per 家宝 picture number
    ("KAMON.NBX", "kamon"),                 # 229 x 16x16
    ("REGKAOCG.NBX", "ui/regkao"),          # 1 face of the officer register
    ("GMAP_P.NBX", "map/parts"),            # 74 big-map marks
    ("INFOMAP.NBX", "map/info"),            # 96 information map and marks
    ("YsMapCG.NBX", "map/field"),           # 28 x 2680x1000 野戦 maps, 2 small
    ("KJSMAPCG.NBX", "map/siege"),          # 1150 攻城戦 map pieces
    ("KJSOBJCG.NBX", "map/siege_objects"),  # 172 攻城戦 objects
    ("CMDBTN.NBX", "ui/cmdbtn"), ("CMNWIN.NBX", "ui/cmnwin"), ("ComSys.nbx", "ui/comsys"), ("Custom.NBX", "ui/custom"),
    ("EvEdit.NBX", "ui/evedit"), ("GWIN.NBX", "ui/gwin"), ("KJSWndCG.NBX", "ui/kjswnd"), ("SeiDlg.nbx", "ui/seidlg"),
    ("THyoujou.NBX", "ui/thyoujou"), ("TUTORIAL.NBX", "ui/tutorial"), ("YsDlg.NBX", "ui/ysdlg"),
    ("GUNGIKJS.NBX", "sprites/gungikjs"), ("GUNIT.NBX", "sprites/gunit"), ("WARCMN.NBX", "sprites/warcmn"),
    ("WARUNIT.NBX", "sprites/warunit"), ("WarSengo.NBX", "sprites/warsengo"), ("WarSmoke.NBX", "sprites/warsmoke"),
    ("YsEffect.NBX", "sprites/yseffect"), ("YsGungi.NBX", "sprites/ysgungi"), ("YsHonjin.NBX", "sprites/yshonjin"),
]


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def pictures(data):
    """PIL images of every entry of an NBX picture container."""
    n, = struct.unpack_from("<I", data)
    base = 4 + 44 * n
    entries = [struct.unpack_from("<11I", data, 4 + 44 * i) for i in range(n)]
    tail = base + max(e[0] + e[1] for e in entries)
    count, = struct.unpack_from("<I", data, tail)
    pal_base = tail + 4 + 12 * count
    palettes = []
    for i in range(count):
        o, s, packed = struct.unpack_from("<3I", data, tail + 4 + 12 * i)
        p = data[pal_base + o:pal_base + o + s]
        if packed:
            p = ls11.lwc_decode(p)
        palettes.append(b"".join(bytes((p[4 * c + 2], p[4 * c + 1], p[4 * c])) for c in range(256)))
    for o, s, wd, h, packed, bpp, *_, pal in entries:
        body = data[base + o:base + o + s]
        if packed:
            body = ls11.lwc_decode(body)
        row = wd * bpp // 8
        stride = (row + 3) & ~3
        px = b"".join(body[y * stride:y * stride + row] for y in reversed(range(h)))
        if bpp == 24:
            yield Image.frombytes("RGB", (wd, h), px, "raw", "BGR")
        else:
            im = Image.frombytes("P", (wd, h), px)
            im.putpalette(palettes[pal])
            yield im


def write_pictures(data_dir, out):
    counts = {}
    for name, folder in PICTURES:
        os.makedirs(os.path.join(out, folder), exist_ok=True)
        n = 0
        for i, im in enumerate(pictures(_read(os.path.join(data_dir, name)))):
            im.save(os.path.join(out, folder, f"{i:04d}.png"))
            n += 1
        counts[folder] = n
    return counts


def big_maps(data_dir, out):
    """GMAP1 / GMAP2 stitched, and GMAP_POS's 250 castle points drawn on a copy of GMAP1."""
    sizes = []
    for name in ("GMAP1.NBX", "GMAP2.NBX"):
        tiles = list(pictures(_read(os.path.join(data_dir, name))))
        rows = [tiles[i:i + GMAP_COLUMNS] for i in range(0, len(tiles), GMAP_COLUMNS)]
        wd, h = sum(t.width for t in rows[0]), sum(r[0].height for r in rows)
        im = Image.new("RGB", (wd, h))
        y = 0
        for r in rows:
            x = 0
            for t in r:
                im.paste(t.convert("RGB"), (x, y))
                x += t.width
            y += r[0].height
        im.save(os.path.join(out, "map", name.replace(".NBX", ".png").lower()))
        sizes.append(im.size)
        if name == "GMAP1.NBX":
            pos = _read(os.path.join(data_dir, "GMAP_POS.NBX"))
            for k in range(250):
                x, y = struct.unpack_from("<2I", pos, 8 * k)
                for dx in range(-4, 5):
                    for dy in range(-4, 5):
                        if 0 <= x + dx < wd and 0 <= y + dy < h:
                            im.putpixel((x + dx, y + dy), (255, 0, 0))
            im.save(os.path.join(out, "map", "gmap1_castles.png"))
    return sizes


def _entries(data):
    n, = struct.unpack_from("<H", data)
    offsets = list(struct.unpack_from(f"<{n}I", data, 2)) + [len(data)]
    return [data[a:b] for a, b in zip(offsets, offsets[1:])]


def _plain(raw):
    """A text entry as shown: control codes other than line breaks become {xx}; half-width kana as w.kana_text."""
    s = raw.decode("cp932", "replace")
    s = w.kana_text(s)
    return re.sub(r"[\x00-\x09\x0b-\x1f]", lambda m: f"{{{ord(m.group()):02x}}}", s).strip()


def _desc(raw):
    s = w.kana_text(raw.split(b"\x05\x05\x05")[0].decode("cp932", "replace"))
    return re.sub(r"[\x00-\x1f]", "", s).strip()


def _title(raw):
    """(name, reading) of a RETSUDEN title entry「name ESC k reading ESC H」or「name」."""
    s = raw.split(b"\x05\x05\x05")[0].decode("cp932", "replace")
    m = re.match(r"([^\x1b]*?)\s*(?:\x1bk(.*?)\x1bH)?\s*$", s)
    name, reading = (m.group(1), m.group(2)) if m else (s, None)
    return re.sub(r"[\x00-\x1f]", "", w.kana_text(name)).strip(), w.kana_text(reading) if reading else ""


def _write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(header)
        cw.writerows(rows)


def tables(retsuden, out):
    """官位, 役職 and 城 descriptions; returns the 家宝 (name, description) list."""
    counts = {}
    kahou = []
    for first, count, path in RETSUDEN_TABLES:
        rows = []
        for k in range(count):
            name, reading = _title(retsuden[first + 2 * k])
            rows.append([k, name, reading, _desc(retsuden[first + 2 * k + 1])])
        if path:
            _write_csv(os.path.join(out, path), ["id", "name", "reading", "description"], rows)
            counts[path] = len(rows)
        else:
            kahou = rows
    return kahou, counts


def items(scenarios, kahou_text, out):
    first = scenarios[w.SCENARIOS[0]]
    rows = []
    for k in range(ITEM_COUNT):
        r = first[ITEMS + ITEM_SIZE * k:][:ITEM_SIZE]
        name = w._text(r[:13])
        # the 列伝 file spells 10 names differently (壷／壺, 本願寺文琳／本能寺文琳, 影秀／鞍切景秀): kept as name_retsuden
        other = kahou_text[k][1] if kahou_text[k][1] != name else ""
        rows.append([k, name, other, w.kana_text(w._text(r[13:47])), r[50], KINDS[r[50]], f"{GRADES[r[51]]}等級", r[52],
                     ORIGINS[r[53]], r[54], r[55], r[56], r[57], r[60], kahou_text[k][3]])
    _write_csv(os.path.join(out, "items/kahou.csv"),
               ["id", "name", "name_retsuden", "reading", "kind_id", "kind", "grade", "picture", "origin", "u54", "u55",
                "u56", "u57", "flags", "description"], rows)
    held = []
    for n in sorted(scenarios, key=lambda n: (int(scenarios[n][0x2C:0x30]), n)):
        d = scenarios[n]
        officers = w._officers(d)
        for k in range(ITEM_COUNT):
            r = d[ITEMS + ITEM_SIZE * k:][:ITEM_SIZE]
            h, = struct.unpack_from("<H", r, 58)
            if h < w.PEOPLE:
                held.append([n, int(d[0x2C:0x30]), k, w._text(r[:13]), h,
                             w._name(officers[h]) if h in officers else ""])
    _write_csv(os.path.join(out, "items/holders.csv"),
               ["scenario", "year", "item", "name", "holder", "holder_name"], held)
    return len(rows), len(held)


def kamon(scenarios, out):
    """家紋 n = 血族 n: the surnames of the officers of each 血族 and the 大名 (状態 6) who lead it in some scenario."""
    surnames, daimyo = collections.defaultdict(collections.Counter), collections.defaultdict(set)
    for n, d in scenarios.items():
        for serial, r in w._officers(d).items():
            if serial >= w.PEOPLE:
                continue
            clan, = struct.unpack_from("<H", r, 67)
            surnames[clan][w._text(r[:9])] += 1
            if r[52] == 6:
                daimyo[clan].add(w._name(r))
    rows = [[k, " ".join(s for s, _ in surnames[k].most_common(3)), " ".join(sorted(daimyo[k]))]
            for k in sorted(surnames) if k < KAMON_CLANS]
    _write_csv(os.path.join(out, "kamon/clans.csv"), ["kamon", "surnames", "daimyo"], rows)
    return len(rows)


def messages(data_dir, out):
    rows = [[i, _plain(raw)] for i, raw in enumerate(_entries(_read(os.path.join(data_dir, "MESSAGE.NBX"))))]
    _write_csv(os.path.join(out, "events/messages.csv"), ["id", "text"], rows)
    names = [s.decode("cp932", "replace") for s in _read(os.path.join(data_dir, "NEB_TEXT.NBX")).split(b"\0") if s]
    _write_csv(os.path.join(out, "events/neb_text.csv"), ["id", "text"], list(enumerate(names)))
    return len(rows), len(names)


@click.command("nobu10-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam files (games/nobu10pk-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/nobu10pk-win/extract)")
def nobu10_extras(game_dir, out):
    """信長の野望・蒼天録 PK: event pictures, 家宝, 家紋, 官位 / 役職 / 城 texts, messages, the big map and sprites."""
    data_dir = os.path.join(game_dir, "DATA")
    scenarios = {n: _read(os.path.join(game_dir, "Scenario", f"SCEDAT{n}.NBX")) for n in w.SCENARIOS}
    for folder, n in write_pictures(data_dir, out).items():
        click.echo(f"{folder}: {n}")
    click.echo(f"map/gmap1.png, gmap2.png: {big_maps(data_dir, out)}")
    kahou_text, counts = tables(_entries(_read(os.path.join(data_dir, "RETSUDEN.NBX"))), out)
    for path, n in counts.items():
        click.echo(f"{path}: {n}")
    n, held = items(scenarios, kahou_text, out)
    click.echo(f"kahou: {n} ({held} holder entries over {len(scenarios)} scenarios)")
    click.echo(f"kamon/clans.csv: {kamon(scenarios, out)} rows")
    m, t = messages(data_dir, out)
    click.echo(f"messages: {m}, neb_text: {t}")


if __name__ == "__main__":
    nobu10_extras()
