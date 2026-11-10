"""三國志12 PK (Steam 628080): event stills, items (名品) and event text, extracted for archiving.

See notes/san12.md「事件、插圖、道具」. Usage (from dekoei/):
    dekoei.py san12-extras --game-dir ../games/san12pk-win --out ../games/san12pk-win/extract
"""
import csv
import json
import os
import struct
import unicodedata

import click
from PIL import Image

from sango import SAN12_GAIJI, san12_decrypt

# Data/EventStill, PK/Data/EventStill: headerless BGRA, the size gives the shape
STILL_SHAPES = {1280 * 960 * 4: (1280, 960), 576 * 432 * 4: (576, 432), 400 * 224 * 4: (400, 224)}
STILL_DIRS = [("Data/EventStill", False), ("PK/Data/EventStill", True)]
# Scenario0.dat part 27 (PK) / 17 (base): 300 item records of 76 (PK) / 60 (base) bytes; +4 name (13 bytes),
# +0x11 reading, u16 +0x30: kind (bits 0-5), stat (6-7), effect type (8-9: 0 the stat, 1 other, 3 none), amount
# (10-15); u16 +0x32 bits 5-9 the 特技 (31 none); +0x34 value; u16 +0x3A >> 6 the picture number
# (unused bits hold leftovers, as in the person records)
ITEM_PART, ITEM_SIZE, BASE_ITEM_PART, BASE_ITEM_SIZE = 27, 76, 17, 60
SKILL_PART, SKILL_SIZE = 41, 136  # PK Scenario0 part 41: 20 特技 (name +4, reading +9, description +16)
STATS = {0: "統率", 1: "武力", 2: "知力", 3: "政治"}
# item kinds read off the item names (no kind-name table found)
KINDS = {0: "馬・乗り物", 1: "剣", 2: "刀", 3: "長柄刀", 4: "矛", 5: "戟", 6: "斧", 7: "鞭", 8: "鎚", 9: "暗器",
         10: "弓", 11: "兵法書", 12: "法家書", 13: "史書", 14: "経書", 15: "論", 16: "医書", 17: "術書", 18: "地図",
         19: "装飾品", 20: "薬", 21: "宝物", 22: "玉璽"}
ITEM_GAIJI = {0xE059: "蒺"}  # 蒺藜棒 (reading ｼﾂﾚｲﾎﾞｳ)
# item pictures: ITEM_STL.S12 (179) then resfiles_additem20_pk.bin (21) = picture numbers 0-199;
# resfiles_spitem0_pk.bin holds 20 more 名品CG (special edition bonus) with no item record
ITEM_PICTURES = [("Data/ITEM_STL.S12", 0), ("resfiles_additem20_pk.bin", 0x18)]
SP_PICTURES = ("resfiles_spitem0_pk.bin", 0x18)
MSG = "PK/Msg/S12MSG0{}.s12"
# maps (notes/san12.md「地圖」), read from the 繁中版 depot (no text in them): BmpMapColor_s_* are the painted
# battle (bf; cf the versus maps) and city (ha) maps, RGB565 little-endian, no header; MiniMap_* GT1G 256x256; the strategy map is
# 3D, its only 2D picture is the 512x512 minimap base
# (VS: the versus maps cf01-03; PK MidMap_*: 512x512 middle-size minimaps)
MAP_DIRS = [("Data/BtlMap", "battlemap", (3072, 2688)), ("Data/BtlMap/VS", "battlemap", (3072, 2688)),
            ("PK/Data/BtlMap", "battlemap", (3072, 2688)), ("PK/Data/BtlMap/MidMap", "battlemap", None),
            ("Data/CityMap", "citymap", (1920, 1440))]
WORLD_MINIMAP = "Data/UI/20_shoki/20_map_minimap_base.G1T"
VOICE_DIR = "SND/voice/Strategy"
EVENT_TITLES = range(98, 136)  # S12MSG01: the history list (some entries are templates)


def scenario_parts(path):
    """ILNK: u32 part count at +4, part offsets at +8; every part but 0 is encrypted."""
    with open(path, "rb") as f:
        d = f.read()
    n = struct.unpack_from("<I", d, 4)[0]
    offs = list(struct.unpack_from(f"<{n}I", d, 8)) + [len(d)]
    return [d[offs[0]:offs[1]]] + [san12_decrypt(d[offs[i]:offs[i + 1]]) for i in range(1, n)]


def sjis(b, gaiji=None):
    s = b.split(b"\0")[0].decode("cp932", "replace")
    table = {**SAN12_GAIJI, **(gaiji or {})}
    return "".join(table.get(ord(c), c) for c in s)


def messages(path):
    """S12MSG: u16 count, then count u32 offsets."""
    with open(path, "rb") as f:
        d = f.read()
    n = struct.unpack_from("<H", d)[0]
    offs = list(struct.unpack_from(f"<{n}I", d, 2)) + [len(d)]
    return [d[offs[i]:offs[i + 1]] for i in range(n)]


def decode_message(b):
    """Half-width kana are hiragana unless ESC K (katakana) is active, ESC H goes back; 02 96 <n> x is a colour
    ({cN}), 02 97 h / 02 97 z bracket a reading (dropped, the reading itself is kept); 0A newline, 05 padding.
    Other control bytes stay as {xx}."""
    out, i, kata = [], 0, False
    while i < len(b):
        c = b[i]
        if c == 0x1B and i + 1 < len(b):
            kata, i = b[i + 1] == 0x4B, i + 2
        elif c == 0x02 and i + 1 < len(b) and b[i + 1] == 0x96:
            j = b.find(b"x", i + 2)
            out.append("{c%s}" % b[i + 2:j].decode("ascii", "replace"))
            i = j + 1
        elif c == 0x02 and i + 2 < len(b) and b[i + 1] == 0x97:
            i += 3
        elif c == 0x0A:
            out.append("\n")
            i += 1
        elif c == 0x05:
            i += 1
        elif (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC) and i + 1 < len(b):
            ch = b[i:i + 2].decode("cp932", "replace")
            out.append(SAN12_GAIJI.get(ord(ch), ch) if len(ch) == 1 else ch)
            i += 2
        elif 0xA1 <= c <= 0xDF:
            ch = unicodedata.normalize("NFKC", bytes([c]).decode("cp932"))
            if ch in "゙゚゛゜" and out:
                mark = "゙" if ch in "゙゛" else "゚"
                out[-1] = unicodedata.normalize("NFC", out[-1] + mark)
            else:
                out.append(chr(ord(ch) - 0x60) if not kata and "ァ" <= ch <= "ヶ" else ch)
            i += 1
        elif 0x20 <= c < 0x7F:
            out.append(chr(c))
            i += 1
        else:
            out.append("{%02x}" % c)
            i += 1
    return "".join(out)


def link_entries(d, base=0):
    """LINK: +4 count, +0x10 rect table (u16 x, y, w, h per 12 bytes; 0 = none), (u32 offset, u32 size) from +0x20,
    offsets relative to the LINK."""
    assert d[base:base + 4] == b"LINK"
    n, rects = struct.unpack_from("<I", d, base + 4)[0], struct.unpack_from("<I", d, base + 0x10)[0]
    for k in range(n):
        o, size = struct.unpack_from("<II", d, base + 0x20 + 8 * k)
        rect = struct.unpack_from("<4H", d, base + rects + 12 * k) if rects else None
        yield d[base + o:base + o + size], rect


def gt1g(t, rect=None):
    """GT1G0500: +0x26 log2 height << 4 | log2 width, BGRA from +0x2C."""
    assert t[:8] == b"GT1G0500"
    w, h = 1 << (t[0x26] & 15), 1 << (t[0x26] >> 4)
    im = Image.frombytes("RGBA", (w, h), t[0x2C:0x2C + w * h * 4], "raw", "BGRA")
    return im.crop((rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])) if rect and rect[2] else im


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def event_stills(game_dir, out):
    os.makedirs(out, exist_ok=True)
    rows = []
    for folder, pk in STILL_DIRS:
        for name in sorted(os.listdir(os.path.join(game_dir, folder))):
            if not name.endswith(".bin"):
                continue
            with open(os.path.join(game_dir, folder, name), "rb") as f:
                d = f.read()
            w, h = STILL_SHAPES[len(d)]
            im = Image.frombytes("RGBA", (w, h), d, "raw", "BGRA")
            stem = name[:-4]
            parts = stem.split("_")
            if parts[1] == "look":  # ev_look_<face number>_<expression>: a cut-out close-up
                kind, face, mood = "look", int(parts[2]), parts[3]
            else:
                kind, face, mood = parts[2], "", ""
                im = im.convert("RGB") if im.getextrema()[3] == (255, 255) else im
            im.save(os.path.join(out, stem + ".png"))
            rows.append([stem + ".png", f"{folder}/{name}", kind, face, mood, w, h, "pk" if pk else "", "✅ code"])
    write_csv(os.path.join(out, "index.csv"), ["file", "source", "kind", "face", "expression", "width", "height",
                                               "pk", "evidence"], rows)
    return len(rows)


def items(game_dir, out):
    os.makedirs(os.path.join(out, "pictures"), exist_ok=True)
    os.makedirs(os.path.join(out, "sp"), exist_ok=True)
    parts = scenario_parts(os.path.join(game_dir, "PK/Scenario/Scenario0.dat"))
    base = scenario_parts(os.path.join(game_dir, "Scenario/Scenario0.dat"))[BASE_ITEM_PART]
    base_names = {k for k in range(len(base) // BASE_ITEM_SIZE) if base[BASE_ITEM_SIZE * k + 4]}
    skills_part = parts[SKILL_PART]
    skills = [sjis(skills_part[SKILL_SIZE * k + 4:SKILL_SIZE * k + 9]) for k in range(len(skills_part) // SKILL_SIZE)]
    write_csv(os.path.join(out, "skills.csv"), ["skill", "name", "reading", "description"],
              [[k, skills[k], sjis(skills_part[SKILL_SIZE * k + 9:SKILL_SIZE * k + 15]),
                sjis(skills_part[SKILL_SIZE * k + 16:SKILL_SIZE * (k + 1)])] for k in range(len(skills))])
    desc = messages(os.path.join(game_dir, MSG.format(4)))
    table = parts[ITEM_PART]
    rows = []
    for k in range(len(table) // ITEM_SIZE):
        r = table[ITEM_SIZE * k:ITEM_SIZE * (k + 1)]
        name = sjis(r[4:0x11], ITEM_GAIJI)
        if not name:
            continue
        a, b = struct.unpack_from("<HH", r, 0x30)
        kind, stat, flag, amount, skill = a & 63, a >> 6 & 3, a >> 8 & 3, a >> 10, b >> 5 & 31
        picture = struct.unpack_from("<H", r, 0x3A)[0] >> 6
        rows.append([k, name, sjis(r[0x11:0x30]), kind, KINDS.get(kind, ""), STATS[stat] if flag == 0 else "",
                     amount, stat | flag << 2, skill if skill != 31 else "", skills[skill] if skill < len(skills) else "", r[0x34],
                     f"{picture:03d}.png", "" if k in base_names else "pk",
                     decode_message(desc[k]).replace("\n", "") if k < len(desc) else ""])
    write_csv(os.path.join(out, "items.csv"),
              ["id", "name", "reading", "kind", "kindName", "stat", "amount", "effect", "skill", "skillName", "value",
               "picture", "pk", "description"], rows)
    n = 0
    for f, base_off in ITEM_PICTURES:
        with open(os.path.join(game_dir, f), "rb") as fh:
            d = fh.read()
        for t, rect in link_entries(d, base_off):
            gt1g(t, rect).convert("RGB").save(os.path.join(out, "pictures", f"{n:03d}.png"))
            n += 1
    with open(os.path.join(game_dir, SP_PICTURES[0]), "rb") as fh:
        d = fh.read()
    sp = 0
    for t, rect in link_entries(d, SP_PICTURES[1]):
        gt1g(t, rect).convert("RGB").save(os.path.join(out, "sp", f"{sp:02d}.png"))
        sp += 1
    return len(rows), n, sp


def events(game_dir, out):
    os.makedirs(out, exist_ok=True)
    script = messages(os.path.join(game_dir, MSG.format(5)))
    # S12MSG05: 0 "Start of script voice message.", 1-520 voiced lines, 521 end, 522 "Begin of script message.",
    # 523-2973 other event lines, 2974 end, 2975 the unification message. The voiced lines follow the sorted
    # voice files EV<event>_<part>_<line>.g1l one to one (520 files).
    # The voice files are not kept (AV rule); without them, read their names from VOICE_DIR + ".list".
    vdir = os.path.join(game_dir, VOICE_DIR)
    names = os.listdir(vdir) if os.path.isdir(vdir) else open(vdir + ".list", encoding="ascii").read().split()
    voices = sorted(f[:-4] for f in names if f.startswith("EV"))
    assert decode_message(script[521]).startswith("End of script voice") and len(voices) == 520
    with open(os.path.join(out, "voiced.jsonl"), "w", encoding="utf-8") as f:
        for k, v in enumerate(voices):
            f.write(json.dumps({"event": v[:7], "voice": v, "msg": k + 1, "text": decode_message(script[k + 1])},
                               ensure_ascii=False) + "\n")
    with open(os.path.join(out, "script.jsonl"), "w", encoding="utf-8") as f:
        for k in range(523, len(script)):
            f.write(json.dumps({"msg": k, "text": decode_message(script[k])}, ensure_ascii=False) + "\n")
    ui = messages(os.path.join(game_dir, MSG.format(1)))
    write_csv(os.path.join(out, "history.csv"), ["msg", "text"],
              [[k, decode_message(ui[k])] for k in EVENT_TITLES])
    return len(voices), len(script) - 523


# biography.py reads the Steam 繁中版 (depot 628082). PK/Msg/S12MSG03.s12 has 938 列傳 (the Japanese release 1089),
# not by person id but packed by id range (🟡 cross: the content fits the person in every range; 貂蝉 824 → 774,
# 織田信長 900 → 789, 項籍 1157 → 861): BIO_RANGES. 549-749, 896-928 are empty and 936, 937 are not text; the
# relatives 1410- have none. A 列傳 is cp950 with 02 96 'NNx' colour codes: the summary, then the 演義 part after
# the icon FA60 and the 史實 part after FA49, as in 三國志11. The names are in the person records of
# PK/Scenario/Scenario0.dat (sango.san12_person_part): surname +9, given name +4, cp950.
BIO_LANG = "zh-Hant"
BIO_RANGES = [(0, 750, 0), (800, 832, 50), (900, 965, 111), (1150, 1232, 296), (1300, 1307, 518)]  # ids, minus
ZH_GAIJI = {b"\xfa\x70": "坂", b"\xfa\x7f": "琰"}  # besides san9_extras.ZH_GAIJI: 高坂昌信, 崔琰の父 (🟡)


def zh_items(game_dir) -> dict[int, tuple[str, str]]:
    """item k -> (name, description) of the 繁中版 (depot 628082): the same PK/Scenario/Scenario0.dat part 27 records
    (cp950 name at +4) and PK/Msg/S12MSG04.s12 entry k"""
    import re
    from san9_extras import ZH_GAIJI as SAN9
    from san9_extras import zh_text
    gaiji = {**SAN9, **ZH_GAIJI}
    table = scenario_parts(os.path.join(game_dir, "PK/Scenario/Scenario0.dat"))[ITEM_PART]
    desc = messages(os.path.join(game_dir, MSG.format(4)))
    out = {}
    for k in range(len(table) // ITEM_SIZE):
        name = zh_text(table[ITEM_SIZE * k + 4:ITEM_SIZE * k + 0x11].split(b"\0")[0], gaiji)
        if name:
            text = re.sub(rb"\x02\x96[0-9]+x", b"", desc[k]).rstrip(b"\x05") if k < len(desc) else b""
            out[k] = (name, zh_text(text, gaiji).replace("\n", "").strip())
    return out


def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    import re
    from biography import sections
    from san9_extras import ZH_GAIJI as SAN9
    from san9_extras import zh_text
    from san11_extras import ZH_ICONS, ZH_NO_RECORD
    gaiji = {**SAN9, **ZH_GAIJI}
    msgs = messages(os.path.join(game_dir, "PK/Msg/S12MSG03.s12"))
    out = {}
    for lo, hi, minus in BIO_RANGES:
        for k in range(lo, hi):
            lines = re.sub(rb"\x02\x96[0-9]+x", b"", msgs[k - minus]).rstrip(b"\x05").split(b"\n")
            intro, parts = zh_text(lines[0], gaiji).strip(), []
            for line in lines[1:]:
                if line[:2] in ZH_ICONS:
                    parts.append((ZH_ICONS[line[:2]], zh_text(line[2:], gaiji).strip()))
                elif parts:
                    parts[-1] = (parts[-1][0], parts[-1][1] + zh_text(line, gaiji).strip())
                else:
                    intro += zh_text(line, gaiji).strip()
            parts = [(kind, t) for kind, t in parts if t.rstrip("。") not in ZH_NO_RECORD]
            if sections(intro, parts):
                out[k] = sections(intro, parts)
    return out


def bio_names(game_dir) -> dict[int, str]:
    from san9_extras import ZH_GAIJI as SAN9
    from san9_extras import zh_text
    from sango import SAN12_PERSONS, san12_person_part
    part = san12_person_part(os.path.join(game_dir, "PK/Scenario/Scenario0.dat"), 292)
    out = {}
    for k in range(SAN12_PERSONS):
        r = part[k * 292:(k + 1) * 292]
        name = "".join(zh_text(f.split(b"\0")[0], {**SAN9, **ZH_GAIJI}) for f in (r[9:14], r[4:9]))
        if name:
            out[k] = name
    return out


def maps(depot, out):
    """the painted battle and city maps, the battle minimaps and the strategy minimap -> out/{battlemap,citymap,
    worldmap}; returns the number of pictures"""
    rows = []
    for folder, kind, size in MAP_DIRS:
        for name in sorted(os.listdir(os.path.join(depot, folder))):
            path = os.path.join(depot, folder, name)
            if name.startswith("BmpMapColor_s_"):
                with open(path, "rb") as f:
                    d = f.read()
                assert len(d) == 2 * size[0] * size[1], name
                im = Image.frombytes("RGB", size, d, "raw", "BGR;16")
                file = f"{kind}/{name[14:-4].lower()}.png"
            elif name.startswith(("MiniMap_", "MidMap_")):
                with open(path, "rb") as f:
                    im = gt1g(f.read())
                stem = name[:-4].lower().split("_", 1)
                file = f"{kind}/{stem[0]}/{stem[1]}.png"
            else:
                continue
            os.makedirs(os.path.dirname(os.path.join(out, file)), exist_ok=True)
            im.save(os.path.join(out, file))
            rows.append([file, f"{folder}/{name}", im.width, im.height])
    os.makedirs(os.path.join(out, "worldmap"), exist_ok=True)
    with open(os.path.join(depot, WORLD_MINIMAP), "rb") as f:
        gt1g(f.read()).save(os.path.join(out, "worldmap", "minimap.png"))
    rows.append(["worldmap/minimap.png", WORLD_MINIMAP, 512, 512])
    write_csv(os.path.join(out, "maps.csv"), ["file", "source", "w", "h"], rows)
    return len(rows)


@click.command("san12-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam install (628080)")
@click.option("--out", required=True, type=click.Path())
@click.option("--maps-depot", type=click.Path(exists=True), help="繁中版 depot (628082) for the maps")
def san12_extras(game_dir, out, maps_depot):
    """三國志12 PK: event stills, items, event text and (with --maps-depot) the battle, city and strategy maps."""
    stills = event_stills(game_dir, os.path.join(out, "eventcg"))
    n_items, pictures, sp = items(game_dir, os.path.join(out, "items"))
    voiced, script = events(game_dir, os.path.join(out, "events"))
    print(f"{stills} stills, {n_items} items, {pictures} item pictures + {sp} sp, {voiced} voiced lines, "
          f"{script} script lines")
    if maps_depot:
        print(f"{maps(maps_depot, out)} map pictures")
