"""三國志VIII PK (Steam 628040): event pictures and sprites, items (宝物), biographies and message texts, extracted
for archiving.

See notes/san8.md「事件、插圖、道具」. Usage (from dekoei/):
    dekoei.py san8-extras --game-dir ../games/san8pk-win --out ../games/san8pk-win/extract
"""
import csv
import os
import random
import re
import struct

import click
from PIL import Image

from sango import SAN8_GAIJI, SAN8_PERSON_SIZE, SAN8_PERSONS, koei_archive, load_san8_persons

# The KOEI archives (sango.koei_archive) hold raw 8 bit pixels with no size or palette. Widths are found by row
# correlation (guess_width); palettes are 256 x (R, G, B, flag) entries of p_main.s8, picked per picture by the
# smoothest result (pick_palette) among the ranges below, read off contact sheets. Colour 0 (#00FF00) is the key.
DUMMY_PALETTE = 168          # an almost black palette that "wins" the smoothness test for everything
# g_event 0-78: (first, last, palettes); 0-7 come out as 272-279, 8-30 285-290, 31-35 280-282; the smoothness
# test picks wrong colours for the horses and the 400x396 landscapes over the whole range, so those are narrowed
STILL_PALETTES = [(0, 36, range(160, 320)), (37, 72, range(260, 280)), (73, 78, range(380, 396))]
SPRITE_PALETTES = range(260, 272)  # g_event 151-1845: 140x140 and 180x180 character sprites of the event scenes
ITEM_PALETTES = range(330, 333)    # g_maindy 2201-2280: the 80 item pictures, 120x120
ITEM_PICTURES = 2201
# D_Sce.s8: 255 item records of 21 bytes from 0xEFD (record 255 is a "ダミ" filler): +0 id, +1 name 13,
# +14 type, +15 kind (= picture and description number), +16 value, +17 ability bonus, +18 特技 (0xFF none),
# +19 0 = lies in the city at +20 (0xFF: nowhere), 1 = held by a person (who is not in this file; +20 is 0xFF)
ITEMS = (0xEFD, 21, 255)
# 50 cities of 16 bytes from 0x7F3: +0 id, +1 name 5, +6 reading 7 (half-width kana)
CITIES = (0x7F3, 16, 50)
# item types, named after the items in each (🟡)
TYPES = ["名馬", "武器", "地図", "医書", "仙術書", "兵法書", "経書", "史書", "論書", "玉璽", "宝物", "楽器・装身具"]
# 特技 by the item's +18 byte: the EXE word list read backwards from 猛者 (🟡; 医書 04 医術, 玉璽 03 人徳,
# 算盤 07 商才, 墨子 08 築城, 地図 21 偵察 fit; 23-25 are past the list)
SKILLS = ["猛者", "智嚢", "治略", "人徳", "医術", "天文", "耕作", "商才", "築城", "警備", "発明", "威風", "弁舌",
          "反計", "挑発", "混乱", "虚報", "歩兵", "騎兵", "弩兵", "水軍", "偵察"]
# m_msg.s8 entries: u32 n, n/4 - 1 u32 offsets into the text that starts at n. Text is Shift-JIS between script
# codes ("$" + u16 ..., "@R" before a line), lines end in NUL.
MSG_BIOGRAPHIES = (51, 52, 53, 54)   # 654 biographies, number = face number (楊奉 0, 張飛 1, 関羽 2)
MSG_ITEMS = 50                       # 80 item descriptions by kind
MSG_EFFECTS = 265                    # ability, 計略 and 戦法 effect lines
SJIS_RUN = re.compile(rb"(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc])+")


def sjis_runs(b: bytes) -> list[tuple[int, str]]:
    return [(m.start(), "".join(SAN8_GAIJI.get(ord(c), c) for c in m.group().decode("cp932", "replace")))
            for m in SJIS_RUN.finditer(b)]


def msg_items(e: bytes) -> list[bytes]:
    n = struct.unpack_from("<I", e, 0)[0]
    offs = list(struct.unpack_from(f"<{n // 4 - 1}I", e, 4)) + [len(e) - n]
    return [e[n + a:n + b] for a, b in zip(offs, offs[1:])]


def guess_width(e: bytes, lo: int = 16, hi: int = 1100) -> int:
    def score(w):
        step = max(1, (len(e) - w) // 20000)
        diffs = [abs(e[i] - e[i + w]) for i in range(0, len(e) - w, step)]
        return sum(diffs) / len(diffs)
    cands = [w for w in range(lo, min(hi, len(e) // 8) + 1) if len(e) % w == 0 and len(e) // w >= 8]
    scores = {w: score(w) for w in cands}
    w = min(scores, key=scores.get)
    # rows r and r + 2 look alike too: a width of 2w shows the picture twice, side by side
    while w % 2 == 0 and w // 2 in scores and scores[w // 2] <= scores[w] * 1.15:
        w //= 2
    return w


def load_palettes(game_dir: str) -> dict[int, list[tuple]]:
    entries = koei_archive(open(os.path.join(game_dir, "p_main.s8"), "rb").read())
    return {i: [tuple(e[k * 4:k * 4 + 3]) for k in range(256)] for i, e in enumerate(entries) if len(e) == 1024}


def pick_palette(e: bytes, w: int, palettes: dict, candidates) -> int:
    """The palette giving the smallest neighbour colour distance relative to random pairs (key colour skipped)."""
    def score(pal):
        rnd = random.Random(1)
        near = far = 0
        for _ in range(3000):
            i = rnd.randrange(0, len(e) - w - 1)
            if e[i] == 0:
                continue
            a, b, d, z = pal[e[i]], pal[e[i + 1]], pal[e[i + w]], pal[e[rnd.randrange(len(e))]]
            near += sum(abs(x - y) for x, y in zip(a, b)) + sum(abs(x - y) for x, y in zip(a, d))
            far += 2 * sum(abs(x - y) for x, y in zip(a, z))
        return near / max(far, 1)
    return min((i for i in candidates if i in palettes and i != DUMMY_PALETTE), key=lambda i: score(palettes[i]))


def to_png(e: bytes, w: int, pal: list[tuple], path: str) -> None:
    im = Image.frombytes("P", (w, len(e) // w), e)
    im.putpalette([c for p in pal for c in p])
    im.info["transparency"] = 0
    im.save(path)


def write_csv(path: str, header: list, rows) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def event_pictures(game_dir: str, out: str, palettes: dict) -> tuple[int, int]:
    entries = koei_archive(open(os.path.join(game_dir, "g_event.s8"), "rb").read())
    stills, sprites = os.path.join(out, "eventcg", "still"), os.path.join(out, "eventcg", "sprite")
    os.makedirs(stills, exist_ok=True)
    os.makedirs(sprites, exist_ok=True)
    rows = []
    for i, e in enumerate(entries[:79]):
        w = guess_width(e)
        p = pick_palette(e, w, palettes, next(r for a, b, r in STILL_PALETTES if a <= i <= b))
        to_png(e, w, palettes[p], os.path.join(stills, f"{i:04d}.png"))
        rows.append([i, f"still/{i:04d}.png", w, len(e) // w, p])
    # sprites come in runs of 8 frames; one palette per run (the costume colours are palette swaps)
    sprite_ids = [i for i, e in enumerate(entries) if i >= 151 and len(e) in (19600, 32400)]
    for k in range(0, len(sprite_ids), 8):
        run = sprite_ids[k:k + 8]
        w = 140 if len(entries[run[0]]) == 19600 else 180
        votes = [pick_palette(entries[i], w, palettes, SPRITE_PALETTES) for i in run[::4]]
        p = max(set(votes), key=votes.count)
        for i in run:
            w = 140 if len(entries[i]) == 19600 else 180
            to_png(entries[i], w, palettes[p], os.path.join(sprites, f"{i:04d}.png"))
            rows.append([i, f"sprite/{i:04d}.png", w, w, p])
    write_csv(os.path.join(out, "eventcg", "index.csv"), ["entry", "file", "w", "h", "palette"], rows)
    return 79, len(sprite_ids)


def screens(game_dir: str, out: str) -> int:
    """The *.s8 files that are plain 8 bit BMPs: screen backgrounds, the 2016x768 map, logos."""
    dst = os.path.join(out, "screens")
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(game_dir)):
        path = os.path.join(game_dir, f)
        if f.lower().endswith(".s8") and open(path, "rb").read(2) == b"BM":
            Image.open(path).convert("RGB").save(os.path.join(dst, os.path.splitext(f)[0] + ".png"))
            n += 1
    return n


def cities(sce: bytes) -> list[str]:
    a, size, n = CITIES
    return [sjis_text(sce[a + k * size + 1:a + k * size + 6]) for k in range(n)]


def sjis_text(b: bytes) -> str:
    return "".join(SAN8_GAIJI.get(ord(c), c) for c in b.split(b"\0")[0].decode("cp932").strip())


def items(game_dir: str, out: str, palettes: dict, msg: list) -> int:
    sce = open(os.path.join(game_dir, "D_Sce.s8"), "rb").read()
    city = cities(sce)
    desc = ["".join(t for _, t in sjis_runs(b)) for b in msg_items(msg[MSG_ITEMS])]
    a, size, n = ITEMS
    rows = []
    for k in range(n):
        r = sce[a + k * size:a + (k + 1) * size]
        assert r[0] == k
        typ, kind, value, bonus, skill, held, place = r[14:21]
        rows.append([k, sjis_text(r[1:14]), typ, TYPES[typ], kind, f"{kind:02d}.png", value, bonus,
                     "" if skill == 0xFF else skill, SKILLS[skill] if skill < len(SKILLS) else "",
                     "人物" if held else city[place] if place < len(city) else "", desc[kind]])
    write_csv(os.path.join(out, "items", "items.csv"),
              ["id", "name", "type", "type_name", "kind", "picture", "value", "bonus", "skill", "skill_name",
               "start", "description"], rows)
    write_csv(os.path.join(out, "items", "effects.csv"), ["line", "text"],
              [[k, "".join(t for _, t in sjis_runs(b))] for k, b in enumerate(msg_items(msg[MSG_EFFECTS]))])
    pics = os.path.join(out, "items", "pictures")
    os.makedirs(pics, exist_ok=True)
    entries = koei_archive(open(os.path.join(game_dir, "g_maindy.s8"), "rb").read())
    for kind in range(80):
        e = entries[ITEM_PICTURES + kind]
        to_png(e, 120, palettes[pick_palette(e, 120, palettes, ITEM_PALETTES)], os.path.join(pics, f"{kind:02d}.png"))
    return len(rows)


def texts(game_dir: str, out: str, msg: list) -> tuple[int, int, int]:
    persons = load_san8_persons(os.path.join(game_dir, "D_Sce.s8"))
    by_face = {}
    for p in persons:
        by_face.setdefault(p["face"], []).append(p)
    bios = [b for k in MSG_BIOGRAPHIES for b in msg_items(msg[k])]
    rows = []
    for k, b in enumerate(bios):
        ps = by_face.get(k, [])
        rows.append([k, " ".join(str(p["id"]) for p in ps), " ".join(p["name"] for p in ps),
                     "".join(t for _, t in sjis_runs(b))])
    os.makedirs(os.path.join(out, "text"), exist_ok=True)
    write_csv(os.path.join(out, "text", "biographies.csv"), ["face", "person_ids", "names", "text"], rows)
    # every entry, one row per text run; single-item entries are the event scripts
    lines, events = [], []
    for i, e in enumerate(msg):
        if len(e) < 8:
            continue
        parts = msg_items(e)
        for j, b in enumerate(parts):
            for o, t in sjis_runs(b):
                lines.append([i, j, o, t])
        if len(parts) == 1:
            runs = sjis_runs(parts[0])
            events.append([i, len(runs), runs[0][1] if runs else ""])
    write_csv(os.path.join(out, "text", "m_msg.csv"), ["entry", "item", "offset", "text"], lines)
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    write_csv(os.path.join(out, "events", "index.csv"), ["entry", "lines", "first_line"], events)
    with open(os.path.join(out, "events", "scripts.txt"), "w", encoding="utf-8") as f:
        for i, _, _ in events:
            f.write(f"== {i}\n" + "\n".join(t for _, t in sjis_runs(msg_items(msg[i])[0])) + "\n")
    return len(rows), len(lines), len(events)


# biography.py reads the Steam 繁中版 (depot 628042): the same files and layout as the Japanese release, texts and
# names in cp950, no gaiji. A biography is lines ended by NUL, every line after the first starting with "@R"; the
# entry ends in "$\"" (an empty one is only that: 588, the face 関定 and 劉泌 share). The kaodata ids are the D_Sce.s8 person ids without the event roles and
# 単福 (kaodata_export.SAN8PK_WIN_ROLES, _ALIASES), listed here by id since the 繁中版 names differ.
BIO_LANG = "zh-Hant"
ZH_ROLE_IDS = {575, 577, 579, 580, 581, 582, 585, 586, 587, 588, 591, 592, 595, 596, 597}


def zh_persons(game_dir) -> list[tuple[int, str, int]]:
    """(id, name, face) of the 繁中版 D_Sce.s8 records, roles left out."""
    with open(os.path.join(game_dir, "D_Sce.s8"), "rb") as f:
        data = f.read()

    def text(b):
        return b.split(b"\0")[0].decode("cp950").strip()

    out = []
    for k in range(658):
        r = data[SAN8_PERSONS + k * SAN8_PERSON_SIZE:SAN8_PERSONS + (k + 1) * SAN8_PERSON_SIZE]
        assert int.from_bytes(r[:2], "little") == k
        if k not in ZH_ROLE_IDS:
            out.append((k, text(r[2:7]) + text(r[0x12:0x17]), int.from_bytes(r[0x27:0x29], "little")))
    return out


def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    msg = koei_archive(open(os.path.join(game_dir, "m_msg.s8"), "rb").read())
    texts = [b for k in MSG_BIOGRAPHIES for b in msg_items(msg[k])]
    first = {}
    for k, _, face in zh_persons(game_dir):
        first.setdefault(face, k)
    out = {}
    for face, b in enumerate(texts):
        lines = [s.removeprefix(b"@R").removesuffix(b'$"') for s in b.split(b"\0")]
        t = "".join(s.decode("cp950") for s in lines if not s.startswith(b"$")).strip()
        if t and face in first:
            out[first[face]] = [("單段", t)]
    return out


def bio_names(game_dir) -> dict[int, str]:
    return {k: name for k, name, _ in zh_persons(game_dir)}


@click.command("san8-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam install (628040)")
@click.option("--out", required=True, type=click.Path())
def san8_extras(game_dir, out):
    """三國志VIII PK: event pictures and sprites, items, biographies, message texts, screen backgrounds."""
    os.makedirs(os.path.join(out, "items"), exist_ok=True)
    palettes = load_palettes(game_dir)
    msg = koei_archive(open(os.path.join(game_dir, "m_msg.s8"), "rb").read())
    n_items = items(game_dir, out, palettes, msg)
    n_bios, n_lines, n_events = texts(game_dir, out, msg)
    n_still, n_sprite = event_pictures(game_dir, out, palettes)
    n_screens = screens(game_dir, out)
    print(f"{n_items} items + 80 pictures, {n_bios} biographies, {n_lines} message lines, {n_events} event scripts, "
          f"{n_still} event pictures, {n_sprite} sprites, {n_screens} screens")


if __name__ == "__main__":
    san8_extras()
