"""信長の野望・烈風伝 with PK (Steam, appid 628110): event pictures, 家宝, 官位 and 官職, 家紋, the message file, the
history chronicle, the maps and the sprite sets, written under --out (notes/nobu8.md「事件、插圖、道具」).

- Every picture file listed in PICTURES is the container of KaoData.nb8: u32 count, count x (u32 offset, size, w, h),
  8-bit pixels from 4 + 16 count. The palette is palette.nb8 (LOGPALETTE, the faces' palette); colours 0-9 are the
  Windows system colours and are written transparent in the sprite sets only.
- Title.nb8, TitleC.NB8, koeilogo.nb8, COLORMAP.NB8, MainMap.nb8 and WarMap{L,M,S}.nb8 are plain BMP files.
- 家宝: SCEDA*.NB8 (XOR removed) 0x3B33C, 350 records of 0x28 bytes: +0 name (14 bytes), +0xE u16 ? (changes by
  scenario, not a castle or person), +0x10 u16 value, +0x12 u16 holder (person number, 0xFFFF none), +0x14 flags
  (bit 0 lost / destroyed), +0x16 effect amount, +0x17 ?, +0x18 effect bits, +0x19 kind (KINDS), +0x1A grade 1-10,
  +0x1B picture (ItemCG.nb8).
- 官位: 0x3E9EC, 250 records of 0x1E bytes: +0 name, +0xE u16 value, +0x10 u16 holder, +0x13 rank.
- 官職: 0x47EB8, 59 records of 0x1C bytes: +0 name, +0xE u16 (changes by scenario, not a person), +0x11 rank.
- MESSAGE.NB8 (LS11, 27 parts) is written as it is; the escapes are those of 将星録 (nobu7_extras.clean).
- The 年表: Nobunaga8WPK.exe .rdata file offset 0x446F98, records of 8 bytes (u16 index, u16 year * 16 + month,
  u32 VA of the title string) until the index breaks.
"""
import csv
import os
import struct

import click
from PIL import Image

import koei_games
import ls11
import nobu7_extras as n7
import wiki_nobu8 as w

ITEMS, ITEM_SIZE, ITEM_COUNT = 0x3B33C, 0x28, 350
KANI, KANI_SIZE, KANI_COUNT = 0x3E9EC, 0x1E, 250
KANSHOKU, KANSHOKU_SIZE, KANSHOKU_COUNT = 0x47EB8, 0x1C, 59
CHRONICLE = 0x446F98  # file offset in Nobunaga8WPK.exe
IMAGE_BASE, RDATA_VA, RDATA_RAW = 0x400000, 0x440000, 0x440000
# +0x19 kinds: the item dialog strings of Nobunaga8WPK.exe (file offset 0x452AAC-0x452C40, stored backwards),
# leaving out the special-effect strings that sit between them; the kinds match the names (平蜘蛛釜 茶道道具, 松風
# 名馬, 地球儀 地図, 蘭奢待 香木)
KINDS = ["茶道道具", "刀槍", "飛び道具", "火縄銃", "短筒", "兵装品", "名馬", "鷹", "剣術書", "砲術書", "兵法書", "医書",
         "忍術書", "水軍書", "知識書", "農政書", "商業書", "建築書", "舶来書", "文学書", "仏教書", "軍記物語", "地図", "絵画",
         "算盤", "将棋盤", "碁盤", "羅針盤", "南蛮時計", "十字架", "遠眼鏡", "煙草", "楽器", "歌留多", "香木"]
# the special effects in the same string list, next to the kind they follow 🟡
SPECIAL = {"茶道道具": "最大義理が上昇する", "名馬": "必ず戦場から退却できる", "兵法書": "すべての陣形が使用可能",
           "医書": "寿命が延びる", "舶来書": "キリスト教に好意を持つ", "地図": "軍団の移動力が上昇する",
           "煙草": "寿命が縮む", "香木": "威信が上昇する"}
# (file, folder, transparent)
PICTURES = [
    ("still.nb8", "eventcg/still", False),     # 72 x 360x160 event stills + frame pieces
    ("MsgCG.nb8", "eventcg/msg", False),       # 3 x 72x72
    ("ItemCG.nb8", "items/pictures", False),   # 51 x 80x80, +0x1B of the 家宝 record
    ("KamonCG.nb8", "kamon", False),           # 162 x 24x24
    ("FlagCG.nb8", "kamon/flags", True),       # 134 flags
    ("MapCG.nb8", "map/mapcg", False),         # 3 small maps
    ("WarBG.Nb8", "map/warbg", False),         # 3 合戦 backgrounds
    ("WChikei.Nb8", "map/wchikei", True),      # 203 field pieces
    ("WarSlope.nb8", "map/warslope", True),    # 260 slope pieces
    ("MainBk.nb8", "ui/mainbk", False),        # 92 panels and backgrounds
    ("MainFly.nb8", "ui/mainfly", True),
    ("MainEtc.nb8", "ui/mainetc", True),
    ("MainCmd.nb8", "ui/maincmd", True),
    ("ButtonCG.nb8", "ui/button", True),
    ("WinTitle.nb8", "ui/wintitle", True),
    ("WinFrm.nb8", "ui/winframe", True),
    ("WarWin.Nb8", "ui/warwin", True),
    ("MarkerCG.nb8", "sprites/marker", True),
    ("MainChip.nb8", "sprites/mainchip", True),
    ("MainUnit.nb8", "sprites/mainunit", True),
    ("WarUnit.Nb8", "sprites/warunit", True),
    ("WJinkei.Nb8", "sprites/jinkei", True),
    ("WEffect.Nb8", "sprites/effect", True),
    ("WMarker.Nb8", "sprites/wmarker", True),
]
BMPS = [("Title.nb8", "eventcg/title/title.png"), ("TitleC.NB8", "eventcg/title/titlec.png"),
        ("koeilogo.nb8", "eventcg/title/koeilogo.png"), ("MainMap.nb8", "map/mainmap.png"),
        ("COLORMAP.NB8", "map/colormap.png"), ("WarMapL.nb8", "map/warmap_l.png"),
        ("WarMapM.nb8", "map/warmap_m.png"), ("WarMapS.nb8", "map/warmap_s.png")]


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def palette(game_dir):
    p = _read(os.path.join(game_dir, "palette.nb8"))
    return b"".join(p[4 + 4 * c:7 + 4 * c] for c in range(256))


def write_pictures(game_dir, out, pal):
    counts = {}
    for name, folder, transparent in PICTURES:
        d = os.path.join(out, folder)
        os.makedirs(d, exist_ok=True)
        n = 0
        for i, (wd, h, px) in enumerate(n7.pictures(_read(os.path.join(game_dir, name)))):
            im = Image.frombytes("P", (wd, h), px)
            im.putpalette(pal)
            if transparent and min(px) < 10:
                im.info["transparency"] = bytes(0 if c < 10 else 255 for c in range(256))
            im.save(os.path.join(d, f"{i:04d}.png"))
            n += 1
        counts[folder] = n
    for name, path in BMPS:
        p = os.path.join(out, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with Image.open(os.path.join(game_dir, name)) as im:
            im.save(p)
            counts[path] = "x".join(map(str, im.size))
    return counts


def _names(data):
    return {i: w._name(data, k) for i, k in w._ids(data).items()}


def _holder(v, names):
    return "" if v == 0xFFFF else f"{v} {names.get(v, '?')}"


def _name14(data, o):
    return data[o:o + 14].split(b"\0")[0].decode("cp932")


def items(out, scenarios, names):
    main = scenarios[w.MAIN]
    rows = []
    for i in range(ITEM_COUNT):
        o = ITEMS + ITEM_SIZE * i
        v0e, value, _ = struct.unpack_from("<3H", main, o + 0xE)
        flags, _, amount, v17, bits, kind, grade, pic = main[o + 0x14:o + 0x1C]
        holders = [_holder(struct.unpack_from("<H", d, o + 0x12)[0], ns) for d, ns in zip(scenarios, names)]
        lost = ["1" if d[o + 0x14] & 1 else "" for d in scenarios]
        rows.append([i, _name14(main, o), kind, KINDS[kind], grade, pic, f"{pic:04d}.png", value, f"{flags:02x}",
                     amount, v17, f"{bits:02x}", v0e, *holders, "".join("x" if x else "." for x in lost)])
    _csv(os.path.join(out, "items", "kahou.csv"),
         ["no", "name", "kind", "kind_name", "grade", "picture", "file", "value_s10", "flags_s10", "effect_amount",
          "v17", "effect_bits", "v0e_s10", *[f"holder_s{k + 1:02d}" for k in range(len(scenarios))],
          "lost_by_scenario"], rows)
    _csv(os.path.join(out, "items", "kinds.csv"), ["kind", "name", "special_effect", "items"],
         [[k, n, SPECIAL.get(n, ""), sum(1 for r in rows if r[2] == k)] for k, n in enumerate(KINDS)])
    return len(rows), sum(1 for r in rows for h in r[13:13 + len(scenarios)] if h)


def kani(out, scenarios, names):
    main = scenarios[w.MAIN]
    rows = []
    for i in range(KANI_COUNT):
        o = KANI + KANI_SIZE * i
        value = struct.unpack_from("<H", main, o + 0xE)[0]
        holders = [_holder(struct.unpack_from("<H", d, o + 0x10)[0], ns) for d, ns in zip(scenarios, names)]
        rows.append([i, _name14(main, o), main[o + 0x13], value, *holders])
    _csv(os.path.join(out, "tables", "kani.csv"),
         ["no", "name", "rank", "value_s10", *[f"holder_s{k + 1:02d}" for k in range(len(scenarios))]], rows)
    sho = []
    for i in range(KANSHOKU_COUNT):
        o = KANSHOKU + KANSHOKU_SIZE * i
        sho.append([i, _name14(main, o), main[o + 0x11],
                    *[struct.unpack_from("<H", d, o + 0xE)[0] for d in scenarios]])
    _csv(os.path.join(out, "tables", "kanshoku.csv"),
         ["no", "name", "rank", *[f"v0e_s{k + 1:02d}" for k in range(len(scenarios))]], sho)
    return len(rows), sum(1 for r in rows for h in r[4:] if h), len(sho)


def chronicle(game_dir, out):
    exe = _read(os.path.join(game_dir, "Nobunaga8WPK.exe"))
    rows = []
    o = CHRONICLE
    while True:
        idx, date, va = struct.unpack_from("<HHI", exe, o)
        if idx != len(rows):
            break
        f = va - IMAGE_BASE - RDATA_VA + RDATA_RAW
        rows.append([idx, date >> 4, date & 15, exe[f:exe.index(b"\0", f)].decode("cp932")])
        o += 8
    _csv(os.path.join(out, "events", "chronicle.csv"), ["index", "year", "month", "title"], rows)
    return len(rows)


def texts(game_dir, out):
    parts = ls11.ls11_decode_parts(_read(os.path.join(game_dir, "MESSAGE.NB8")))
    rows = [[k, i, n7.clean(x.decode("cp932", "replace"))] for k in range(len(parts))
            for i, x in enumerate(n7.w.message_strings(parts[k]))]
    _csv(os.path.join(out, "events", "messages.csv"), ["part", "index", "text"], rows)
    return len(parts), len(rows)


def _csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(header)
        wr.writerows(rows)


@click.command("nobu8-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam files (games/nobu8pk-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/nobu8pk-win/extract)")
def nobu8_extras(game_dir, out):
    """信長の野望・烈風伝 PK: event pictures, 家宝, 官位, 家紋, messages, the 年表, maps and sprites."""
    pal = palette(game_dir)
    scenarios = [koei_games.nobu8_win_data(os.path.join(game_dir, f"SCEDA{k:02d}.NB8")) for k in range(10)]
    names = [_names(d) for d in scenarios]
    for folder, n in write_pictures(game_dir, out, pal).items():
        click.echo(f"{folder}: {n}")
    n, held = items(out, scenarios, names)
    click.echo(f"kahou: {n} ({held} holder entries over {len(scenarios)} scenarios)")
    k, kh, ks = kani(out, scenarios, names)
    click.echo(f"kani: {k} ({kh} holder entries), kanshoku: {ks}")
    click.echo(f"chronicle: {chronicle(game_dir, out)}")
    p, m = texts(game_dir, out)
    click.echo(f"messages: {m} in {p} parts")


if __name__ == "__main__":
    nobu8_extras()
