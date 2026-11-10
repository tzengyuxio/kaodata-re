"""三國志IX PK (Steam 628050): event pictures, items (寶物), 兵法, scenario and PK stage texts, all messages and the
列伝, extracted for archiving.

See notes/san9.md「事件、插圖、道具」. Usage (from dekoei/):
    dekoei.py san9-extras --game-dir ../games/san9pk-win --out ../games/san9pk-win/extract
"""
import csv
import os
import struct
import unicodedata
from collections import Counter

import click
from PIL import Image

import ls11
from sango import SAN9_GAIJI, SAN9_SCENARIOS, load_san9_persons

# Picture files G_*.s9 ("palettes first"): u32 palette count, count x (BITMAPINFOHEADER 40 bytes + 256 x R G B X),
# u32 size of the picture block, then pictures of a 16-byte header (u32 size incl. header, u32 stride (= width),
# u32 width, u32 height) and 8-bit pixels, top-down. Colour 0 (pure green) is the transparent key.
# When there are as many palettes as pictures, picture k uses palette k (G_Still, G_StilPK); otherwise the file
# does not say which palette a picture uses, so it is guessed (pick_palette, 🟡).
# (folder, file, pictures); picked from contact sheets of every file
PICTURES = [
    ("still", "G_Still.s9", range(0, 72)),        # 45 small (160x128) and 27 large (512x384) event stills
    ("still_pk", "G_StilPK.s9", range(0, 14)),    # 14 PK event stills (512x384)
    ("ending", "G_Ending.s9", [0, 3, *range(22, 37), 47, 48, 49]),  # ending maps and stills (palette 🟡)
    ("gallery", "G_BGGAL.s9", [29, *range(47, 62)]),  # 16 round paintings of the gallery screen (palette 🟡)
    ("pk_campaign", "G_StrtPK.s9", range(10, 15)),  # the 5 PK 決戦制覇 campaigns' group portraits (palette 🟡)
    ("pk_titles", "G_LocMPK.s9", range(1, 64, 2)),  # 32 PK stage title banners, in stage order (palette 🟡)
    ("title", "G_Title.s9", [0]),
    ("title", "G_TitlPK.s9", [0]),
]
# G_Still.s9 120-120 and 240x240 pictures of the 100 items: item k is picture 72 + k / 172 + k; 272-282 are 11
# facility pictures (no names)
ITEM_SMALL, ITEM_LARGE, FACILITIES = 72, 172, range(272, 283)
# M_MsgPK.s9 / M_Msg.s9 / M_Rtdn.s9: LS11, u16 count, count u32 offsets; an entry is one or more texts ended by
# 05 05 05. Half-width kana are hiragana unless ESC K (katakana) / ESC k (a reading, katakana) is active; ESC H
# switches back; 0A new line; 01, 02 xx variables (kept as {..}).
MSG_FILES = {"M_MsgPK.s9": "messages_pk.csv", "M_Msg.s9": "messages.csv"}
# entries of M_MsgPK.s9: (name, description) pairs. 0-59 the 30 scenarios (20 base, 10 PK slots), 60-71 the 6
# tutorials, 72-135 the 32 PK stages (same order as the pk_titles banners); 1219-1341 the 41 兵法 as (name,
# reading, description); 1392-1631 the 120 item slots as (name, reading); 7641-7740 the 100 item descriptions
SCENARIO_TEXTS, TUTORIAL_TEXTS, STAGE_TEXTS = (0, 30), (60, 6), (72, 32)
HEIHOU, ITEMS_NAMES, ITEM_TEXTS = 1219, 1392, 7641
# D_Sce???.S9 (RIFF S9SC) chunk `item`: 120 records of 22 bytes (100 items, 20 empty PK slots), u16 each:
# +0 id (+2, +4 the same), +6 picture (= id), +8 kind, +10 value 🟡, +12 bonus 🟡, +14 兵法 (hiho index, 0xFFFF
# none) 🟡, +16 holder (person id, 0xFFFF none), +18 state (1 unowned, 2 held), +20 place (places-export id:
# cities 0-49, bldg + 50). The field names come from the item editor labels in M_MsgPK.s9 1635-1648
# (ＣＧ番号 種類 能力 効果 兵法 所有 状態番号 地域番号 所在).
ITEM = (b"item", 22, 100)
# kinds 0-12, named after the items in them (🟡; the game has no kind names); 4, 5, 6 match the descriptions'
# first word (史書, 經書, 論文)
KINDS = ["名馬・乗物", "武器", "兵法書", "政治書", "史書", "経書", "論文", "地図", "医書・方術書", "仙書", "玉璽",
         "宝物", "装身具"]
# M_Rtdn.s9 列伝 k belongs to the people with face k for k < 563 and face k + 7 from 563 on: faces 563-569 (霊帝, 少帝,
# 献帝, 貂蝉, 大喬, 小喬, 蔡琰) have no 列伝, so the rest move up 7. 659-667 are blank (faces 666-674: 北斗, 南斗 and the
# role records), 668-678 are the 倭, 烏丸, 羌, 山越, 南蛮 people (a tribe's officers share one). ✅ cross: 573 of the
# 584 texts that 三國志VII/VIII also have match the person of the same name there (the other 2 differ only in a
# misspelt name, 厳晙/田与); the 95 IX-only texts fit their person by content.
BIO_NO_TEXT = range(563, 570)
BIO_LANG = "ja"


def bio_face(k: int) -> int:
    return k if k < BIO_NO_TEXT.start else k + len(BIO_NO_TEXT)


# texts' gaiji not in SAN9_GAIJI, read off the readings beside them (🟡)
MSG_GAIJI = {0xE006: "傕", 0xE00B: "兗", 0xE011: "闞", 0xE018: "譙", 0xE020: "邳", 0xE029: "釭", 0xE059: "蒺"}


def entries(path):
    with open(path, "rb") as f:
        d = ls11.ls11_decode_parts(f.read())[0]
    n = struct.unpack_from("<H", d)[0]
    offs = list(struct.unpack_from(f"<{n}I", d, 2)) + [len(d)]
    return [d[offs[k]:offs[k + 1]] for k in range(n)]


def text(b):
    """One message entry to text; several texts in one entry are joined by a line of ---."""
    out, run, mode, i = [], [], "H", 0
    gaiji = {**SAN9_GAIJI, **MSG_GAIJI}

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
        if c == 0x1B and i + 1 < len(b):
            mode = "H" if b[i + 1] == ord("H") else "K"
            i += 2
        elif b[i:i + 3] == b"\x05\x05\x05":
            out.append("\n---\n")
            i += 3
        elif c == 0x0A:
            out.append("\n")
            i += 1
        elif c == 0x02 and i + 1 < len(b):
            out.append("{" + b[i:i + 2].hex() + "}")
            i += 2
        elif c < 0x20:
            if c:
                out.append("{" + f"{c:02x}" + "}")
            i += 1
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC:
            try:
                ch = b[i:i + 2].decode("cp932")
                out.append(gaiji.get(ord(ch), ch))
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


def load_pictures(path):
    with open(path, "rb") as f:
        d = f.read()
    n = struct.unpack_from("<I", d)[0]
    pals = [d[4 + k * 1064 + 40:4 + (k + 1) * 1064] for k in range(n)]
    o = 4 + n * 1064
    end = o + struct.unpack_from("<I", d, o)[0]
    o += 4
    pics = []
    while o < end:
        size, _, w, h = struct.unpack_from("<4I", d, o)
        pics.append((w, h, d[o + 16:o + size]))
        o += size
    assert o == len(d)
    return pals, pics


def pick_palette(w, h, px, pals):
    """The palette that keeps the used colours distinct and neighbouring pixels closest (a guess)."""
    pairs = Counter()
    for y in range(0, h, max(1, h // 64)):
        row = px[y * w:(y + 1) * w]
        pairs.update(p for p in zip(row, row[1:]) if p[0] != p[1])
    used = set(px[::3])
    n = sum(pairs.values()) or 1

    def score(pal):
        distinct = len({pal[4 * i:4 * i + 3] for i in used}) / len(used)
        diff = sum(m * sum(abs(pal[4 * a + j] - pal[4 * b + j]) for j in range(3)) for (a, b), m in pairs.items())
        return distinct < 0.9, diff / n

    return min(range(len(pals)), key=lambda k: score(pals[k]))


def to_image(w, h, px, pal):
    im = Image.frombytes("P", (w, h), px)
    im.putpalette([pal[4 * i + j] for i in range(256) for j in range(3)])
    alpha = Image.frombytes("L", (w, h), bytes(0 if c == 0 else 255 for c in px))
    im = im.convert("RGBA")
    im.putalpha(alpha)
    return im


def pictures(game_dir, out):
    rows = []
    for folder, name, picks in PICTURES:
        pals, pics = load_pictures(os.path.join(game_dir, name))
        os.makedirs(os.path.join(out, "eventcg", folder), exist_ok=True)
        for k in picks:
            w, h, px = pics[k]
            own = len(pals) == len(pics)
            p = k if own else pick_palette(w, h, px, pals)
            file = f"eventcg/{folder}/{os.path.splitext(name)[0]}_{k:03d}.png"
            to_image(w, h, px, pals[p]).save(os.path.join(out, file))
            rows.append([file, name, k, w, h, p, "✅" if own else "🟡"])
    write_csv(os.path.join(out, "eventcg", "index.csv"),
              ["file", "source", "picture", "width", "height", "palette", "palette_confidence"], rows)
    return len(rows)


def scenario_chunk(game_dir, scenario, tag):
    with open(os.path.join(game_dir, scenario), "rb") as f:
        d = f.read()
    i = d.index(tag)
    return d[i + 8:i + 8 + struct.unpack_from("<I", d, i + 4)[0]]


def items(game_dir, out, msg, persons):
    tag, size, count = ITEM
    heihou = [text(msg[HEIHOU + 3 * k]) for k in range(41)]
    pals, pics = load_pictures(os.path.join(game_dir, "G_Still.s9"))
    os.makedirs(os.path.join(out, "items", "pictures"), exist_ok=True)
    it = scenario_chunk(game_dir, SAN9_SCENARIOS[0], tag)
    rows = []
    for k in range(count):
        f = struct.unpack_from("<11H", it, size * k)
        assert f[0] == f[3] == k
        for base, suffix in [(ITEM_SMALL, "s"), (ITEM_LARGE, "l")]:
            w, h, px = pics[base + k]
            to_image(w, h, px, pals[base + k]).save(os.path.join(out, "items", "pictures", f"{k:03d}{suffix}.png"))
        rows.append([k, text(msg[ITEMS_NAMES + 2 * k]), text(msg[ITEMS_NAMES + 2 * k + 1]), f[4], KINDS[f[4]],
                     f[5], f[6], "" if f[7] == 0xFFFF else heihou[f[7]], text(msg[ITEM_TEXTS + k]),
                     f"pictures/{k:03d}s.png", f"pictures/{k:03d}l.png"])
    write_csv(os.path.join(out, "items", "items.csv"),
              ["id", "name", "reading", "kind", "kind_name", "value", "bonus", "heihou", "description",
               "picture_small", "picture_large"], rows)
    names = {p["id"]: p["name"] for p in persons}
    holders = []
    for scenario in SAN9_SCENARIOS:
        it = scenario_chunk(game_dir, scenario, tag)
        for k in range(count):
            holder, state, place = struct.unpack_from("<3H", it, size * k + 16)
            holders.append([scenario, k, rows[k][1], "" if holder == 0xFFFF else holder,
                            names.get(holder, ""), state, place])
    write_csv(os.path.join(out, "items", "holders.csv"),
              ["scenario", "item", "item_name", "holder", "holder_name", "state", "place"], holders)
    os.makedirs(os.path.join(out, "items", "facilities"), exist_ok=True)
    for k in FACILITIES:
        w, h, px = pics[k]
        to_image(w, h, px, pals[k]).save(os.path.join(out, "items", "facilities", f"G_Still_{k:03d}.png"))
    return len(rows), len(holders)


def tables(game_dir, out, msg):
    # D_Sce001.S9 chunk `hiho`: 41 records of 38 bytes, in the order of the 兵法 names (u16 fields, meaning 🟡)
    hiho = scenario_chunk(game_dir, SAN9_SCENARIOS[0], b"hiho")
    rows = []
    for k in range(41):
        rows.append([k, text(msg[HEIHOU + 3 * k]), text(msg[HEIHOU + 3 * k + 1]), text(msg[HEIHOU + 3 * k + 2]),
                     *struct.unpack_from("<19H", hiho, 38 * k)])
    write_csv(os.path.join(out, "tables", "heihou.csv"),
              ["id", "name", "reading", "description", *[f"u{2 * j:02d}" for j in range(19)]], rows)
    return len(rows)


def texts(game_dir, out, msg, persons):
    counts = {}
    for name, csv_name in MSG_FILES.items():
        es = msg if name == "M_MsgPK.s9" else entries(os.path.join(game_dir, name))
        write_csv(os.path.join(out, "text", csv_name), ["index", "text"], [[k, text(b)] for k, b in enumerate(es)])
        counts[name] = len(es)
    for csv_name, (start, n) in [("scenarios.csv", SCENARIO_TEXTS), ("tutorials.csv", TUTORIAL_TEXTS),
                                 ("pk_stages.csv", STAGE_TEXTS)]:
        rows = [[k, text(msg[start + 2 * k]), text(msg[start + 2 * k + 1])] for k in range(n)]
        if csv_name == "pk_stages.csv":
            rows = [r + [f"eventcg/pk_titles/G_LocMPK_{2 * r[0] + 1:03d}.png"] for r in rows]
        write_csv(os.path.join(out, "events", csv_name),
                  ["index", "title", "description"] + (["title_picture"] if csv_name == "pk_stages.csv" else []),
                  rows)
    # M_Rtdn.s9: 679 列伝, linked to people by bio_face
    by_face = {}
    for p in persons:
        by_face.setdefault(p["face"], []).append(p)
    bios = entries(os.path.join(game_dir, "M_Rtdn.s9"))
    rows = []
    for k, b in enumerate(bios):
        t = text(b).strip()
        people = by_face.get(bio_face(k), []) if t else []
        rows.append([k, bio_face(k), " ".join(str(p["id"]) for p in people), " ".join(p["name"] for p in people), t])
    write_csv(os.path.join(out, "text", "biographies.csv"), ["index", "face", "person_ids", "names", "text"], rows)
    counts["M_Rtdn.s9"] = len(bios)
    return counts



def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    """列伝 for biography.py: {person id: [("單段", text)]}, the line breaks of the game's layout removed. A tribe's
    officers share one face and one 列伝; it goes to the first of them, the one the kaodata dataset keeps."""
    first = {}
    for p in load_san9_persons(game_dir):
        first.setdefault(p["face"], p["id"])
    out = {}
    for k, b in enumerate(entries(os.path.join(game_dir, "M_Rtdn.s9"))):
        t = text(b).strip().replace("\n", "")
        if t and bio_face(k) in first:
            out[first[bio_face(k)]] = [("單段", t)]
    return out


def bio_names(game_dir) -> dict[int, str]:
    return {p["id"]: p["name"] for p in load_san9_persons(game_dir)}

@click.command("san9-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam install (628050)")
@click.option("--out", required=True, type=click.Path())
def san9_extras(game_dir, out):
    """三國志IX PK: event pictures, items, 兵法, scenario / PK stage texts, messages and 列伝."""
    msg = entries(os.path.join(game_dir, "M_MsgPK.s9"))
    persons = load_san9_persons(game_dir)
    print(f"{pictures(game_dir, out)} event pictures")
    n, h = items(game_dir, out, msg, persons)
    print(f"{n} items ({2 * n} pictures), {h} holder rows, {len(FACILITIES)} facility pictures")
    print(f"{tables(game_dir, out, msg)} 兵法")
    print("texts:", texts(game_dir, out, msg, persons))


if __name__ == "__main__":
    san9_extras()
