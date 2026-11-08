"""信長の野望・嵐世記 with PK (Steam, appid 628120): event pictures, 家宝 and their holders, 家紋, the event titles, the
message file and the other picture sets, written under --out (notes/nobu9.md「事件、插圖、道具」).

- Every picture file (*CG.nb9, MAINMAP, StartUp, ...) is the KaoCG.nb9 container: u32 count, count x 40 bytes (u32
  offset, size, width, height, LWC flag, bits per pixel 8 or 24, 0 x 4), then the data from 4 + 40 count. Flagged
  entries are LWC (ls11.lwc_decode). Pixels are a bottom-up DIB, rows padded to 4 bytes; 24-bit rows are B, G, R.
  8-bit pictures use palette.NB9 (a 100x100 BMP: B, G, R, X from +54), the faces' palette. KaoTMP.nb9 is 2000 copies
  of one face and is not written.
- 家宝: the typed records of type 20 in the decoded SCEDA??.NB9 (wiki_nobu9), 380 x 112 bytes from the first one:
  +4 u16 id (0-349, PK 9280-9309), +12 name (14), +26 reading, +76 u8 kind (Nobunaga9WPK.exe pointer table at file
  0x984F40, 52 names), +80 u32 grade (0-9), +84 holder (u16 id, u16 type: 0 person, 17 勢力, 21 都市; 0xFFFF none),
  +88 picture (ItemCg.nb9), +92 ability amount, +96 ability (0 政治 1 統率 2 知略 3 野望, 4 none), +100 兵種 (5 none),
  +104 特技 code, +108 flags. MESSAGE.NB9 part 27 is the effect text of each kind.
- MESSAGE.NB9: LS11, 50 parts; each part is a u16 offset table A whose first entry points at a second table B, the
  entries start at A[1:] and B (as RETSUDEN.NB9, wiki_nobu9._bio_pairs). Text is Shift-JIS with half-width kana shown
  as hiragana (ESC K / ESC H switch to katakana, wiki_nobu10.kana_text); 0x02 + 2 bytes and 0x01 'C' + 2 bytes are
  variables, 0x05 pads, the other control bytes are conditions.
- Event titles: Nobunaga9WPK.exe pointer table at file 0x996F18, 82 titles in order; 「(なし)」 marks the ones the game
  lists without a picture.
"""
import csv
import os
import re
import struct

import click
from PIL import Image

import koei_games
import ls11
import wiki_nobu9 as w
from wiki_nobu10 import kana_text

# (file, folder): picture sets written one PNG per entry
PICTURES = [
    ("StillCG.nb9", "eventcg/still"),       # 61 x 720x400 event stills, 7 x 360x160 disasters, 3 x 1024x448
    ("EventCG.nb9", "eventcg/event"),       # event backgrounds and the 22-frame 風神 animation
    ("KaisenCG.nb9", "eventcg/kaisen"),     # 海戦 screens
    ("NINJACG.NB9", "eventcg/ninja"),       # 176 x 512x384 frames of the night 忍者 fight, 死亡
    ("MISSONCG.NB9", "eventcg/mission"),    # PK mission frames, 銅／金／鋼／銀賞, chapter names
    ("StartUp.nb9", "eventcg/startup"),     # title logo, option buttons and frames
    ("TUTOCG.NB9", "eventcg/tutorial"),
    ("ItemCg.nb9", "items/pictures"),       # 39 x 120x120, +88 of the 家宝 record
    ("KamonCg.nb9", "kamon/large"),         # 201 x 24x24
    ("SKamon.nb9", "kamon/small"),          # 201 x 16x16
    ("MAINMAP.NB9", "map/mainmap"),         # big map strips and marks
    ("KuniMap.nb9", "map/kuni"),
    ("WLandCG.nb9", "map/wland"),           # 31 field backgrounds
    ("MAINBGCG.NB9", "ui/mainbg"),
    ("MAINMKCG.NB9", "ui/mainmk"),
    ("MainCG.nb9", "ui/main"),
    ("MMENUCG.nb9", "ui/mmenu"),
    ("EditCG.nb9", "ui/edit"),
    ("EditCG2.nb9", "ui/edit2"),
    ("DialogCg.nb9", "ui/dialog"),
    ("WindowCG.nb9", "ui/window"),
    ("CtrlCG.nb9", "ui/ctrl"),
    ("MapBtnCG.nb9", "ui/mapbtn"),
    ("GungiCG.nb9", "sprites/gungi"),       # 軍議
    ("WarCG.nb9", "sprites/war"),
    ("WUnitCG.nb9", "sprites/wunit"),
]
KAHOU, KAHOU_SIZE, KAHOU_COUNT = 20, 112, 380
KINDS_FILE, ABILITIES = 0x984F40, ["政治", "統率", "知略", "野望"]
TITLES_FILE, TITLES_COUNT = 0x996F18, 82
EFFECT_PART = 27
# MESSAGE.NB9 parts, from their content (🟡)
MESSAGE_PARTS = {0: "口調、稱呼", 1: "系統訊息", 2: "出生、元服", 3: "新年祝賀", 4: "評定", 5: "來訪", 6: "歷史事件（1543–1560）",
                 7: "歷史事件", 8: "歷史事件", 9: "歷史事件", 10: "歷史事件", 16: "指令說明", 22: "商人、家宝買賣",
                 27: "家宝效果", 28: "知行、豐凶", 29: "天下統一", 30: "教學", 33: "一揆", 35: "說明分類", 36: "說明分類",
                 42: "南蛮、宣教師", 43: "PK 任務", 44: "事件編輯器", 47: "事件編輯器", 48: "編輯器", 49: "PK 事件"}


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def palette(game_dir):
    p = _read(os.path.join(game_dir, "palette.NB9"))
    return b"".join(bytes((p[56 + 4 * c], p[55 + 4 * c], p[54 + 4 * c])) for c in range(256))


def pictures(data):
    """(width, height, bpp, top-down pixels) of every entry of a picture container."""
    n = struct.unpack_from("<I", data)[0]
    base = 4 + 40 * n
    for i in range(n):
        o, s, wd, h, packed, bpp = struct.unpack_from("<6I", data, 4 + 40 * i)
        body = data[base + o:base + o + s]
        if packed:
            body = ls11.lwc_decode(body)
        row = wd * bpp // 8
        stride = (row + 3) & ~3
        yield wd, h, bpp, b"".join(body[y * stride:y * stride + row] for y in reversed(range(h)))


def image(wd, h, bpp, px, pal):
    if bpp == 24:
        return Image.frombytes("RGB", (wd, h), px, "raw", "BGR")
    im = Image.frombytes("P", (wd, h), px)
    im.putpalette(pal)
    return im


def write_pictures(game_dir, out, pal):
    counts = {}
    for name, folder in PICTURES:
        d = os.path.join(out, folder)
        os.makedirs(d, exist_ok=True)
        n = 0
        for i, (wd, h, bpp, px) in enumerate(pictures(_read(os.path.join(game_dir, name)))):
            image(wd, h, bpp, px, pal).save(os.path.join(d, f"{i:04d}.png"))
            n += 1
        counts[folder] = n
    return counts


class Exe:
    """Nobunaga9WPK.exe: file offsets of VAs and the strings they point at."""

    def __init__(self, data):
        self.data = data
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        n, opt = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
        self.base = struct.unpack_from("<I", data, pe + 52)[0]
        self.sections = [struct.unpack_from("<4I", data, pe + 24 + opt + 40 * i + 8) for i in range(n)]

    def offset(self, va):
        rva = va - self.base
        for size, start, raw_size, raw in self.sections:
            if start <= rva < start + max(size, raw_size):
                return rva - start + raw

    def string(self, va):
        o = self.offset(va)
        return self.data[o:self.data.index(b"\0", o)].decode("cp932")

    def strings(self, table, count):
        return [self.string(struct.unpack_from("<I", self.data, table + 4 * i)[0]) for i in range(count)]


def message_parts(game_dir):
    """the entries (raw bytes) of every MESSAGE.NB9 part."""
    out = []
    for p in ls11.ls11_decode_parts(_read(os.path.join(game_dir, "MESSAGE.NB9"))):
        a = struct.unpack_from(f"<{struct.unpack_from('<H', p)[0] // 2}H", p)
        b = []
        if len(a) > 1:
            for v in struct.unpack_from(f"<{(a[1] - a[0]) // 2}H", p, a[0]):
                if v > len(p) or v <= (b[-1] if b else a[-1]):
                    break
                b.append(v)
        starts = sorted({*a[1:], *b}) + [len(p)]
        out.append([p[x:y] for x, y in zip(starts, starts[1:])])
    return out


def message_text(raw):
    """the text of one entry: variables as {v:xxxx} / {c:xxxx}, other control bytes as {xx}, page ends dropped."""
    out, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c == 0x02 and i + 2 < len(raw):
            out.append(f"{{v:{raw[i + 1]:02x}{raw[i + 2]:02x}}}".encode())
            i += 3
        elif c == 0x01 and raw[i + 1:i + 2] == b"C" and i + 3 < len(raw):
            out.append(f"{{c:{raw[i + 2]:02x}{raw[i + 3]:02x}}}".encode())
            i += 4
        elif c == 0x1B and i + 1 < len(raw):
            out.append(raw[i:i + 2])
            i += 2
        elif c in (0x05, 0x00):
            i += 1
        elif c < 0x20 and c != 0x0A:
            out.append(f"{{{c:02x}}}".encode())
            i += 1
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC:
            out.append(raw[i:i + 2])
            i += 2
        else:
            out.append(raw[i:i + 1])
            i += 1
    return kana_text(b"".join(out).decode("cp932", "replace"))


def write_messages(game_dir, out, parts):
    d = os.path.join(out, "events")
    os.makedirs(d, exist_ok=True)
    n = 0
    with open(os.path.join(d, "messages.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["part", "index", "part_use", "text"])
        for pi, entries in enumerate(parts):
            for j, raw in enumerate(entries):
                wr.writerow([pi, j, MESSAGE_PARTS.get(pi, ""), message_text(raw)])
                n += 1
    return n


def write_titles(exe, out):
    titles = exe.strings(TITLES_FILE, TITLES_COUNT)
    with open(os.path.join(out, "events", "titles.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["event", "title", "no_picture"])
        for i, t in enumerate(titles):
            plain = re.sub(r"[\s　]*\(なし\)\s*$", "", t)
            wr.writerow([i, plain, int(plain != t)])
    return len(titles)


def _kahou_start(data):
    return data.find(struct.pack("<IHHI", 1, 0, KAHOU, 1))


def write_kahou(game_dir, exe, out, parts):
    datas = {s: koei_games.nobu9_win_data(os.path.join(game_dir, "scenario", f"SCEDA{s}.NB9"), exe.data)
             for s in w.SCENARIOS}
    kinds = exe.strings(KINDS_FILE, 52)
    effects = [message_text(raw).replace("\n", "") for raw in parts[EFFECT_PART]]
    main = datas[w.MAIN]
    o0 = _kahou_start(main)
    rows = []
    for i in range(KAHOU_COUNT):
        r = main[o0 + KAHOU_SIZE * i:][:KAHOU_SIZE]
        assert struct.unpack_from("<IHH", r)[::2] == (1, KAHOU)
        grade, _, picture, amount, ability, troop, skill, flags = struct.unpack_from("<8I", r, 80)
        rows.append({"slot": i, "id": struct.unpack_from("<H", r, 4)[0], "name": w._text(r, 12, 14),
                     "reading": w._text(r, 26, 50), "kind": r[76], "kind_name": kinds[r[76]], "grade": grade,
                     "picture": picture, "ability": ABILITIES[ability] if ability < 4 else "",
                     "ability_amount": amount if ability < 4 else "", "troop": troop if troop != 5 else "",
                     "skill_code": skill, "flags": flags, "effect": effects[r[76]], "pk": int(i >= 350)})
    with open(os.path.join(out, "items", "kahou.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    with open(os.path.join(out, "items", "kinds.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["kind", "name", "effect"])
        wr.writerows([k, kinds[k], effects[k]] for k in range(52))

    # holders, scenario by scenario: a person, a 勢力 (named by its 大名) or a 都市
    holders = []
    for s in sorted(w.SCENARIOS, key=lambda s: (w.YEARS[s], s)):
        d = datas[s]
        records = dict(koei_games.nobu9_win_records(d))
        heads = {}
        for pid, o in records.items():
            force, lord = struct.unpack_from("<I", d, o + 0x8C)[0] & 0xFFFF, struct.unpack_from("<I", d, o + 0xAC)[0]
            if force != w.NONE and lord == 0xFFFFFFFF:
                heads[force] = pid
        cities = {i: w._text(d, o, 12) for i, o in w._typed(d, 21).items()}
        start = _kahou_start(d)
        for i in range(KAHOU_COUNT):
            hid, htype = struct.unpack_from("<HH", d, start + KAHOU_SIZE * i + 84)
            if hid == w.NONE:
                continue
            if htype == 0:
                kind, name = "person", w._name(d, records[hid])
            elif htype == 17:
                kind, name = "勢力", (w._name(d, records[heads[hid]]) + "家") if hid in heads else f"勢力{hid}"
            elif htype == 21:
                kind, name = "都市", cities[hid]
            else:
                kind, name = str(htype), ""
            holders.append([s, w.YEARS[s], i, rows[i]["name"], kind, hid, name])
    with open(os.path.join(out, "items", "holders.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["scenario", "year", "slot", "kahou", "holder_type", "holder_id", "holder"])
        wr.writerows(holders)
    return len(rows), len(holders)


@click.command("nobu9-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True, file_okay=False),
              help="the Steam files (games/nobu9pk-win)")
@click.option("--out", required=True, type=click.Path(file_okay=False))
def nobu9_extras(game_dir, out):
    """信長の野望・嵐世記 PK: event pictures, 家宝, 家紋, event titles, messages and other picture sets."""
    pal = palette(game_dir)
    for folder, n in write_pictures(game_dir, out, pal).items():
        click.echo(f"{folder}: {n}")
    exe = Exe(_read(os.path.join(game_dir, "Nobunaga9WPK.exe")))
    parts = message_parts(game_dir)
    click.echo(f"messages: {write_messages(game_dir, out, parts)}")
    click.echo(f"event titles: {write_titles(exe, out)}")
    click.echo("家宝: %d, holders: %d" % write_kahou(game_dir, exe, out, parts))


if __name__ == "__main__":
    nobu9_extras()
