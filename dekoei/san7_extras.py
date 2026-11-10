"""三國志VII PK (Steam 628030): every picture file, items (寶物), 列伝 and all messages, extracted for archiving.

See notes/san7.md「事件、插圖、道具」. Usage (from dekoei/):
    dekoei.py san7-extras --game-dir ../games/san7pk-win --out ../games/san7pk-win/extract
"""
import csv
import os
import struct
import unicodedata

import click
from PIL import Image

import ls11
from sango import (SAN7_GAIJI, SAN7_PERSON_SIZE, SAN7_PERSONS, SAN7_SCENARIOS, decode_san7_scenario,
                   load_san7_persons)

# Picture files G_*.s7: the Kaodata.s7 container (u32 count, count x (offset, size, w, h) u32, offsets from the end
# of the table), 8-bit pixels top-down, no compression. The palette is P_<same name>.s7 (Windows LOGPALETTE,
# 0x300, 256 x R G B flags); colour 0 (pure green) is the transparent key. G_KUNIT0-9 share P_Kunit.s7, G_YU_* have
# eight palettes P_YU_<name>1-8 (only the first is used here). G_YMap00-29 are plain BMPs (battle maps, exported by
# places-export, not here).
# (output folder, files); every G_ file not listed goes to pictures/<name>/
FOLDERS = [
    ("eventcg/still", ["G_StlEvD", "G_StlEvH", "G_StlEvJ", "G_StlEvO"]),  # event stills 300x200
    ("eventcg/ending", ["G_StlEd1", "G_StlEd2", "G_StlEd3", "G_StlEd4", "G_SSEnd1", "G_SSEnd2", "G_SSEnd3",
                        "G_SSEnd4"]),
    ("eventcg/scenery", ["G_StlMe1", "G_StlMe2", "G_StlMe3"]),  # 30 landscapes and buildings (名所 🟡)
    ("eventcg/pk", ["G_PKRev1", "G_PKRev2", "G_PKRev3", "G_PKRev4", "G_PKRev5", "G_PKRev6"]),
    ("eventcg/figures", ["G_Ev00Ga", "G_Ev01Ke", "G_Ev02Sa", "G_Ev03Ch", "G_Ev04To", "G_Ev05Bu"]),
    ("eventcg/banners", ["G_Ev20Ek", "G_Ev21Ho", "G_Ev22In", "G_Ev23Ju", "G_Ev24Ko", "G_Ev25Oo", "G_Ev26Ta"]),
    ("eventcg/title", ["G_M8Titl", "G_Start", "G_M9Logo"]),
    ("eventcg/sorcery", ["G_WHouou", "G_WKirin", "G_WRyuu", "G_WMajin", "G_WThund", "G_WTaiho", "G_WJutsu",
                         "G_WJY", "G_WBk0S", "G_WBk1N", "G_WBk2K", "G_WBk3I", "G_WBk4H", "G_WBk5X"]),
    ("eventcg/duel", ["G_IKBk1", "G_IKBk2", "G_IKTM", "G_IKTora", "G_IKEf"]),
    ("eventcg/pk", ["G_Moji"]),  # 46 calligraphy characters of the PK campaign titles (官渡, 赤壁 ...)
]
# G_YMap: battle maps (places-export); G_Item1/2, G_Soubi: written by items()
SKIP = ("G_YMap", "G_Item1", "G_Item2", "G_Soubi")


def palette(game_dir, g):
    stem = g[2:]
    cands = [f"P_{stem}.s7", f"P_{stem}1.s7"] + (["P_Kunit.s7"] if stem.upper().startswith("KUNIT") else [])
    names = {n.lower(): n for n in os.listdir(game_dir)}
    for c in cands:
        if c.lower() in names:
            with open(os.path.join(game_dir, names[c.lower()]), "rb") as f:
                d = f.read()
            assert d[:4] == b"\x00\x03\x00\x01"
            return [tuple(d[4 + 4 * i:7 + 4 * i]) for i in range(256)]
    raise FileNotFoundError(f"no palette for {g}")


def pictures(game_dir, g):
    with open(os.path.join(game_dir, g + ".s7"), "rb") as f:
        d = f.read()
    n = struct.unpack_from("<I", d)[0]
    base = 4 + 16 * n
    pal = palette(game_dir, g)
    flat = [c for rgb in pal for c in rgb]
    for i in range(n):
        o, size, w, h = struct.unpack_from("<4I", d, 4 + 16 * i)
        im = Image.frombytes("P", (w, h), d[base + o:base + o + size])
        im.putpalette(flat)
        im.info["transparency"] = 0
        yield i, im


def dump_pictures(game_dir, out):
    where = {g: folder for folder, gs in FOLDERS for g in gs}
    counts = {}
    for name in sorted(os.listdir(game_dir)):
        if not (name.startswith("G_") and name.endswith(".s7")) or name.startswith(SKIP):
            continue
        g = name[:-3]
        folder = os.path.join(out, where.get(g, "pictures"), g)
        os.makedirs(folder, exist_ok=True)
        k = 0
        for i, im in pictures(game_dir, g):
            im.save(os.path.join(folder, f"{i:03d}.png"), transparency=0)
            k += 1
        top = where.get(g, "pictures")
        counts[top] = counts.get(top, 0) + k
    return counts


# M_Msg.s7, M_BFile.s7: LS11 parts; a part is u16 count, count u16 offsets (from the part start), the entries.
# An entry is one or more texts ended by 05 05 05. Half-width kana are hiragana unless ESC K (katakana) is active;
# ESC H switches back; 0A new line; 01 + 3 bytes and 02 + 2 bytes are variables (kept as {..}), other bytes below
# 0x20 are commands (kept as {..}). Part 0 and the last part are the same in both files.
# gaiji of the texts not in SAN7_GAIJI, drawn with S7gaiji.tte and read in context (厳畯, 費禕, 并州 ...) 🟡; codes
# from 0xE0F1 up only appear inside command bytes
MSG_GAIJI = {**SAN7_GAIJI, **dict(zip(
    [0xE002, 0xE00A, 0xE00B, 0xE010, 0xE017, 0xE01B, 0xE020, 0xE021, 0xE024, 0xE029, 0xE02A, 0xE02D, 0xE030,
     0xE059, 0xE05F], "彧鄧兗畯禕琮邳琦并釭涪鄴鄱蒺犍"))}


def entries(part):
    n = struct.unpack_from("<H", part)[0]
    offs = list(struct.unpack_from(f"<{n}H", part, 2)) + [len(part)]
    return [part[offs[k]:offs[k + 1]] for k in range(n)]


def text(b):
    out, run, mode, i = [], [], "H", 0

    def flush():
        if run:
            s = unicodedata.normalize("NFKC", bytes(run).decode("cp932"))
            if mode == "H":
                s = "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)
            out.append(s)
            run.clear()

    while i < len(b):
        c = b[i]
        if 0xA1 <= c <= 0xDF:
            run.append(c)
            i += 1
            continue
        flush()
        if c == 0x1B and i + 1 < len(b) and b[i + 1] in b"HK":
            mode = chr(b[i + 1])
            i += 2
        elif b[i:i + 3] == b"\x05\x05\x05":
            out.append("\n---\n")
            i += 3
        elif c == 0x0A:
            out.append("\n")
            i += 1
        elif c in (0x01, 0x02):
            k = 4 if c == 1 else 3
            out.append("{" + b[i:i + k].hex() + "}")
            i += k
        elif c == 0x1B:
            out.append("{" + b[i:i + 2].hex() + "}")
            i += 2
        elif c < 0x20:
            out.append("{" + f"{c:02x}" + "}")
            i += 1
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC:
            try:
                ch = b[i:i + 2].decode("cp932")
                out.append(MSG_GAIJI.get(ord(ch), ch))
            except UnicodeDecodeError:
                out.append("{" + b[i:i + 2].hex() + "}")
            i += 2
        else:
            out.append(chr(c))
            i += 1
    flush()
    s = "".join(out)
    while s.endswith("\n---\n"):
        s = s[:-5]
    return s


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def load_parts(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return ls11.ls11_decode_parts(f.read())


# D_Sn???.s7 (decode_san7_scenario) items from 0x125BA: 72 records of 40 bytes. +0 u16 holder = person slot (the
# officer id is the slot's +0 u16; 0xFFFF none), +2 u16 (1/0) 🟡, +4 name 18 bytes, +0x16 u8 value 🟡, +0x17 u8
# bonus 🟡, +0x18 u8 (0xFF or 0x08-0x39, changes between scenarios) ❌, +0x24 u32 bitmask (horses 0x800, 西蜀地形図
# 0x80 ...) ❌. The holders are checked against the story (赤兎馬 呂布, 絶影 曹操, 青龍偃月刀 関羽, 蛇矛 張飛,
# 雌雄一対の剣 劉備, 古錠刀 孫堅 in 189). Pictures: G_Item1.s7 0-33 then G_Item2.s7 0-37, in item order (cross:
# every picture matches its name). Descriptions: M_Msg.s7 part 30 entries 0-71.
ITEMS, ITEM_SIZE, ITEM_COUNT = 0x125BA, 40, 72
PERSONS, PERSON_SIZE, PERSON_COUNT = 0x30A, 0x78, 620
# kinds by item number, named after the items (the game has no kind names) 🟡
KINDS = [(5, "名馬"), (24, "武器"), (26, "地図"), (30, "方術書"), (34, "兵法書"), (54, "書物"), (56, "玉璽・九錫"),
         (68, "宝物"), (72, "霊獣")]
# G_Soubi.s7: 14 兵装 pictures; names from the EXE string block at 0x34E1F8 (stored in reverse), matched by picture
SOUBI = ["弓", "藤甲", "騎馬", "馬鎧", "鉄甲", "弩", "連弩", "井闌", "霹靂車", "火炮", "象", "木獣", "蒙衝", "楼船"]
# EXE 0x3FFFC0: pointer table 武力 知力 政治 魅力, then the 32 特技 names in this order (code; which bit of a person
# record is which 特技 is not checked)
ABILITY_TABLE = 0x3FFFC0
# M_Msg.s7 parts with story events (dialogue of historical events: 27 連環の計, 39 孫策, 40 左慈 ...), the
# chronicle (41: one line per historical event) and the 86 sights (26)
STORY_PARTS, CHRONICLE_PART, SIGHTS_PART, ITEM_PART = [27, 36, 39, 40, 45, 46, 52], 41, 26, 30


def kind(k):
    return next(name for end, name in KINDS if k < end)


def exe_strings(exe, at, n):
    out = []
    for i in range(n):
        o = struct.unpack_from("<I", exe, at + 4 * i)[0] - 0x400000
        out.append(exe[o:exe.index(b"\0", o)].decode("cp932"))
    return out


def items(game_dir, out, msg, persons):
    with open(os.path.join(game_dir, "San7WPK.exe"), "rb") as f:
        exe = f.read()
    desc = [text(b) for b in entries(msg[ITEM_PART])]
    pics = list(pictures(game_dir, "G_Item1")) + list(pictures(game_dir, "G_Item2"))
    os.makedirs(os.path.join(out, "items", "pictures"), exist_ok=True)
    holders, table = [], None
    for sc in SAN7_SCENARIOS:
        with open(os.path.join(game_dir, sc), "rb") as f:
            d = decode_san7_scenario(exe, f.read())
        slots = [struct.unpack_from("<H", d, PERSONS + PERSON_SIZE * k)[0] for k in range(PERSON_COUNT)]
        recs = []
        for k in range(ITEM_COUNT):
            r = d[ITEMS + ITEM_SIZE * k:][:ITEM_SIZE]
            holder, flag = struct.unpack_from("<2H", r)
            name = "".join(MSG_GAIJI.get(ord(c), c) for c in r[4:0x16].split(b"\0")[0].decode("cp932"))
            recs.append((name, r[0x16], r[0x17], r[0x18], struct.unpack_from("<I", r, 0x24)[0]))
            pid = slots[holder] if holder != 0xFFFF else None
            holders.append([sc[:-3], k, name, "" if pid is None else pid,
                            "" if pid is None else persons.get(pid, ("",))[0], flag, r[0x18]])
        table = table or recs
    rows = []
    for k, (name, value, bonus, _, mask) in enumerate(table):
        pics[k][1].save(os.path.join(out, "items", "pictures", f"{k:02d}.png"), transparency=0)
        rows.append([k, name, kind(k), value, bonus, f"{mask:08x}", f"{k:02d}.png", desc[k]])
    write_csv(os.path.join(out, "items", "items.csv"),
              ["item", "name", "kind", "value", "bonus", "mask", "picture", "description"], rows)
    write_csv(os.path.join(out, "items", "holders.csv"),
              ["scenario", "item", "name", "holder", "holder_name", "flag", "field18"], holders)
    os.makedirs(os.path.join(out, "items", "equipment"), exist_ok=True)
    for k, im in pictures(game_dir, "G_Soubi"):
        im.save(os.path.join(out, "items", "equipment", f"{k:02d}_{SOUBI[k]}.png"), transparency=0)
    names = exe_strings(exe, ABILITY_TABLE, 36)
    write_csv(os.path.join(out, "tables", "tokugi.csv"), ["index", "name"], list(enumerate(names[4:])))
    return len(rows), len(holders)


def write_texts(out, msg, bfile, persons):
    rows = [[p, e, text(b)] for p, part in enumerate(msg) for e, b in enumerate(entries(part))]
    write_csv(os.path.join(out, "text", "messages.csv"), ["part", "entry", "text"], rows)
    # M_BFile.s7 parts 1-11: the 列伝 of officers 0-519 in id order, then one "列伝はありません"
    bios = [text(b) for part in bfile[1:12] for b in entries(part)]
    write_csv(os.path.join(out, "text", "biographies.csv"), ["id", "name", "text"],
              [[i, persons[i][0], t] for i, t in enumerate(bios) if i in persons])
    story = [[p, e, text(b)] for p in STORY_PARTS for e, b in enumerate(entries(msg[p]))]
    write_csv(os.path.join(out, "events", "story.csv"), ["part", "entry", "text"], story)
    chron = [[e, text(b)] for e, b in enumerate(entries(msg[CHRONICLE_PART]))]
    write_csv(os.path.join(out, "events", "chronicle.csv"), ["entry", "text"], chron)
    sights = [[e, text(b)] for e, b in enumerate(entries(msg[SIGHTS_PART]))]
    write_csv(os.path.join(out, "text", "sights.csv"), ["entry", "text"], sights)
    return len(rows), sum(1 for i in range(len(bios)) if i in persons), len(story), len(chron), len(sights)


# biography.py reads the Steam 繁中版 (depot 628032): the same files as the Japanese release, texts in cp950 (Big5
# with the ETEN extension, 裏 is F9D8), no gaiji. M_BFile.s7 parts 1-11 entries 0-519 are the 列傳 of officers 0-519
# in the Japanese order (張飛 1, 關羽 2), each one text ended by 05 05 05, 0A the game's line breaks. The scenario
# cipher tables are at San7WPK.exe 0x4E43E0 (byte same as the Japanese 0x4E5500), so names come from the scenarios
# (D_Sn001-007 write 54 喬瑁, 430 傅僉; the PK scenarios 橋瑁, 傅儉).
BIO_LANG = "zh-Hant"
ZH_TABLES = 0x4E43E0


def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    parts = load_parts(game_dir, "M_BFile.s7")
    texts = [b for part in parts[1:12] for b in entries(part)][:520]
    return {i: [("單段", b.rstrip(b"\x05").decode("cp950").replace("\n", "").strip())] for i, b in enumerate(texts)}


def bio_names(game_dir) -> dict[int, str]:
    with open(os.path.join(game_dir, "San7WPK.exe"), "rb") as f:
        exe = f.read()
    names = {}
    for name in SAN7_SCENARIOS:
        with open(os.path.join(game_dir, name), "rb") as f:
            data = decode_san7_scenario(exe, f.read(), ZH_TABLES)
        for o in range(SAN7_PERSONS, SAN7_PERSONS + 620 * SAN7_PERSON_SIZE, SAN7_PERSON_SIZE):
            pid = int.from_bytes(data[o:o + 2], "little")
            if pid != 0xFFFF:
                n = (data[o + 0x2A:o + 0x30].split(b"\0")[0] + data[o + 0x30:o + 0x36].split(b"\0")[0]).decode("cp950")
                names.setdefault(pid, n)  # the PK scenarios D_Sn10x write 54 橋瑁, 430 傅儉; keep D_Sn001's
    return names


@click.command("san7-extras")
@click.option("--game-dir", required=True, help="Steam 628030 安裝目錄")
@click.option("--out", required=True, help="輸出目錄（games/san7pk-win/extract）")
def san7_extras(game_dir, out):
    """三國志VII PK: event pictures, items, 列伝 and all messages."""
    counts = dump_pictures(game_dir, out)
    print(", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    msg, bfile = load_parts(game_dir, "M_Msg.s7"), load_parts(game_dir, "M_BFile.s7")
    persons = load_san7_persons(game_dir)
    n_items, n_holders = items(game_dir, out, msg, persons)
    print(f"items {n_items} (+ 14 equipment), holders {n_holders}, 特技 names 32")
    n_msg, n_bio, n_story, n_chron, n_sights = write_texts(out, msg, bfile, persons)
    print(f"messages {n_msg}, biographies {n_bio}, story lines {n_story}, chronicle {n_chron}, sights {n_sights}")


if __name__ == "__main__":
    san7_extras()
