"""信長の野望・天下創世 with PK (Steam, appid 628140): event pictures, 家宝, 家紋, 官位, 役職 and the message scripts,
written under --out (notes/nobu11.md「事件、插圖、道具」).

- grp/*.N11 are F11N containers: +4 u32 texture count, +8 sprite count, from 0x14 one 20-byte entry per texture
  (u32 sprite count, rect table offset, T11N offset, 2 more u32). A rect is 4 u16 (x, y, w, h). T11N: u32 width,
  height, texture width, height, then u8 format: 9 is a 256 x (B, G, R, X) palette and 8-bit pixels from +22 + 1024,
  33 is B, G, R, A pixels from +22. One sprite per texture: the sprite is the top-left width x height.
- Wide pictures are cut into a left and a right texture: EVENT_STILL 61 x (360 + 360) x 400, SEIRYAKU_BASE_IMG
  textures 95-126 16 x (360 + 360) x 400 and 65-94 15 x (256 + 64) x 240, JISETSU_IMG 1-16 8 x (256 + 228) x 182.
- 家宝: DBSCEDA (LWC decoded, wiki_nobu11) 0x226AE4, 630 x 63-byte records (430 named): +2 name 13, +15 reading 38,
  +53 grade (9 = 一等級), +54 picture (SEIRYAKU_BASE_IMG texture 128 + n), +55 origin? (0 日本, 1 南蛮, 2 明), +56 ?,
  +57 u16 holder serial: 勢力 0x4D-0xB0 (the clan's store), person 0x241- (wiki_nobu11 serials). The text is
  msg/KFile<k // 50 + 1>.n11 entries 2 + 5 (k % 50): the name and 4 lines (the name there differs
  for a few, e.g. 本能寺文琳 / 本願寺文琳: written as textName).
- 官位: 0x2305EE, 350 x 47 bytes: +2 name 13, +15 reading, +44 rank, +45 u16 holder. 役職: 0x234630, 75 x 41 bytes:
  +2 u16 holder, +4 name 11, +15 reading, +40 rank.
- 勢力 (0x7B2, 100 x 432): +2 家紋 (KAMON.N11 sprite), +3 ?, +4 u16 lord.
- msg/*.n11 (N11F): u32 end of the script; the script is tokens split by ',\\n', each a type byte, ',' and an
  argument; from the end the strings XOR 97 9E 79 E9 (wiki_nobu11._bio_entries). Jump arguments count tokens.
"""
import csv
import glob
import json
import os
import struct

import click
from PIL import Image

import wiki_nobu11 as w

KAHOU, KAHOU_SIZE, KAHOU_COUNT = 0x226AE4, 63, 630
KANI, KANI_SIZE, KANI_COUNT = 0x2305EE, 47, 350
YAKU, YAKU_SIZE, YAKU_COUNT = 0x234630, 41, 75
FACTIONS, FACTION_SIZE = 0x7B2, 432
FACTION_SERIALS = range(0x4D, 0xB1)
# Nobunaga11WPK.exe 0x3827E4 (forwards 一等級 ... 十等級), grade +53: 9 is 一等級
GRADES = ["十等級", "九等級", "八等級", "七等級", "六等級", "五等級", "四等級", "三等級", "二等級", "一等級"]
ORIGINS = ["日本", "南蛮", "明"]  # the 3 strings before the grades 🟡
# +54 picture -> what it shows (looked at the 39 pictures; +54 n is picture n + 1) 🟡
PICTURE_KINDS = ["茶入", "茶入", "茶壺", "茶釜", "茶碗", "茶碗", "花入", "茶杓", "香炉", "水指", "刀剣", "刀剣", "刀剣", "槍",
                 "槍", "火縄銃", "管打銃", "短筒", "具足", "具足", "兜", "兜", "名馬", "名馬", "名馬", "書物", "書物",
                 "書物", "書物", "水墨画", "彩色画", "地図", "菓子", "南蛮具", "南蛮時計", "地酒", "香木", "大砲"]
SEASONS = ["新春", "春", "梅雨", "夏", "秋", "晩秋", "冬", "厳冬"]  # JISETSU_IMG pairs, read off the pictures
# script token types (the first byte); meanings from the token patterns 🟡
OPS = {"&": "text", "(": "call", ")": "int", ",": "ref", "\x0e": "push", "+": "const", "$": "op", "#": "jump_if",
       "\x16": "jump", "\x19": "jump_unless", "*": "label", "\x0f": "end"}
SKIP_MSG = ("Bfile",)  # 列伝: wiki_nobu11.bios


def textures(path):
    """[(texture index, [sprites])] of one F11N file"""
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"F11N"
    n, = struct.unpack_from("<I", d, 4)
    out = []
    for i in range(n):
        count, rects, data, _, _ = struct.unpack_from("<5I", d, 0x14 + 20 * i)
        assert d[data:data + 4] == b"T11N"
        width, height, tw, th = struct.unpack_from("<4I", d, data + 4)
        if d[data + 20] == 9:
            pal = d[data + 22:data + 22 + 1024]
            tex = Image.frombytes("P", (tw, th), d[data + 1046:data + 1046 + tw * th])
            tex.putpalette(bytes(v for c in range(256) for v in (pal[4 * c + 2], pal[4 * c + 1], pal[4 * c])))
            tex = tex.convert("RGB")
        else:
            assert d[data + 20] == 33
            tex = Image.frombytes("RGBA", (tw, th), d[data + 22:data + 22 + tw * th * 4], "raw", "BGRA")
        if count == 1:
            out.append((i, [tex.crop((0, 0, width, height))]))
        else:
            out.append((i, [tex.crop((x, y, x + rw, y + rh))
                            for x, y, rw, rh in (struct.unpack_from("<4H", d, rects + 8 * k) for k in range(count))]))
    return out


def joined(left, right):
    im = Image.new(left.mode, (left.width + right.width, max(left.height, right.height)))
    im.paste(left, (0, 0))
    im.paste(right, (left.width, 0))
    return im


def save_all(images, folder, names=None):
    os.makedirs(folder, exist_ok=True)
    for k, im in enumerate(images):
        im.save(os.path.join(folder, f"{k:03d}{'_' + names[k] if names else ''}.png"))
    return len(images)


def pictures(grp, out):
    first = {i: s[0] for i, s in textures(os.path.join(grp, "EVENT_STILL.N11"))}
    n = {"eventcg/still": save_all([joined(first[2 * k], first[2 * k + 1]) for k in range(len(first) // 2)],
                                   os.path.join(out, "eventcg/still"))}
    n["eventcg/event"] = save_all([s[0] for _, s in textures(os.path.join(grp, "EVENT_IMG.N11"))],
                                  os.path.join(out, "eventcg/event"))
    base = {i: s for i, s in textures(os.path.join(grp, "SEIRYAKU_BASE_IMG.N11"))}
    n["eventcg/seiryaku"] = save_all([joined(base[t][0], base[t + 1][0]) for t in range(95, 127, 2)],
                                     os.path.join(out, "eventcg/seiryaku"))
    n["eventcg/seiryaku_small"] = save_all([joined(base[t][0], base[t + 1][0]) for t in range(65, 95, 2)],
                                           os.path.join(out, "eventcg/seiryaku_small"))
    n["items/pictures"] = save_all([base[t][0] for t in range(127, 166)], os.path.join(out, "items/pictures"))
    n["kamon/small"] = save_all(base[0], os.path.join(out, "kamon/small"))
    season = {i: s[0] for i, s in textures(os.path.join(grp, "JISETSU_IMG.N11"))}
    n["eventcg/jisetsu"] = save_all([joined(season[t], season[t + 1]) for t in range(1, 17, 2)],
                                    os.path.join(out, "eventcg/jisetsu"), SEASONS)
    n["kamon"] = save_all(textures(os.path.join(grp, "KAMON.N11"))[0][1], os.path.join(out, "kamon"))
    return n


def _faction_lord(db, persons, serial):
    f = db[FACTIONS + FACTION_SIZE * (serial - FACTION_SERIALS[0]):][:FACTION_SIZE]
    lord = w._u16(f, 4)
    return "" if lord == 0xFFFF else w._person_name(persons[lord - w.PERSONS[0]])


def _holder(db, persons, serial):
    """(kind, name) of a holder serial"""
    if serial == 0xFFFF:
        return "", ""
    if serial in FACTION_SERIALS:
        return "勢力", _faction_lord(db, persons, serial)
    assert serial >= w.PERSONS[0], hex(serial)
    return "人物", w._person_name(persons[serial - w.PERSONS[0]])


def _write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(header)
        cw.writerows(rows)
    return len(rows)


def tables(game_dir, out):
    dbs = [(year, w._database(os.path.join(game_dir, "scenario"), n)) for n, year in w.SCENARIOS]
    persons = {year: w._persons(db) for year, db in dbs}
    main = dbs[-1][1]
    files = {}
    items, holders = [], []
    for k in range(KAHOU_COUNT):
        r = main[KAHOU + KAHOU_SIZE * k:][:KAHOU_SIZE]
        assert w._u16(r, 0) == 0xB17 + k
        if not r[2]:
            continue
        name = w._text(r[2:15])
        fn = k // 50 + 1
        if fn not in files:
            files[fn] = w._bio_entries(os.path.join(game_dir, "msg", f"KFile{fn:02d}.n11"))
        entry = files[fn][2 + 5 * (k % 50):][:5]
        text = "".join(line.replace("\\n", "") for line in entry[1:])
        items.append([k, name, w._text(r[15:53]), r[53], GRADES[r[53]], r[54] + 1, PICTURE_KINDS[r[54]],
                      ORIGINS[r[55]], r[56], "" if entry[0] == name else entry[0], text])
        for year, db in dbs:
            rec = db[KAHOU + KAHOU_SIZE * k:][:KAHOU_SIZE]
            kind, who = _holder(db, persons[year], w._u16(rec, 57))
            if kind:
                holders.append([year, k, name, kind, who])
    n = {"items/kahou.csv": _write_csv(os.path.join(out, "items/kahou.csv"),
                                       ["id", "name", "reading", "grade", "gradeName", "picture", "pictureKind",
                                        "origin", "flag56", "textName", "text"], items),
         "items/holders.csv": _write_csv(os.path.join(out, "items/holders.csv"),
                                         ["year", "id", "name", "holderKind", "holder"], holders)}
    for key, (start, size, count, name_at, holder_at, rank_at) in {
            "kani": (KANI, KANI_SIZE, KANI_COUNT, (2, 15, 44), 45, 44),
            "yakushoku": (YAKU, YAKU_SIZE, YAKU_COUNT, (4, 15, 40), 2, 40)}.items():
        a, b, c = name_at
        rows, held = [], []
        for k in range(count):
            r = main[start + size * k:][:size]
            rows.append([k, w._text(r[a:b]), w._text(r[b:c]), r[rank_at]])
            for year, db in dbs:
                kind, who = _holder(db, persons[year], w._u16(db[start + size * k:][:size], holder_at))
                if kind:
                    held.append([year, k, rows[-1][1], who])
        n[f"tables/{key}.csv"] = _write_csv(os.path.join(out, f"tables/{key}.csv"),
                                            ["id", "name", "reading", "rank"], rows)
        n[f"tables/{key}_holders.csv"] = _write_csv(os.path.join(out, f"tables/{key}_holders.csv"),
                                                    ["year", "id", "name", "holder"], held)
    daimyo = []
    for year, db in dbs:
        for k in range(len(FACTION_SERIALS)):
            f = db[FACTIONS + FACTION_SIZE * k:][:FACTION_SIZE]
            if w._u16(f, 4) != 0xFFFF:
                daimyo.append([year, k, _faction_lord(db, persons[year], FACTION_SERIALS[0] + k), f[2], f[3]])
    n["kamon/daimyo.csv"] = _write_csv(os.path.join(out, "kamon/daimyo.csv"),
                                       ["year", "faction", "lord", "kamon", "byte3"], daimyo)
    return n


def script(path):
    """(first message number, strings, tokens, boxes) of one N11F file; a token is [index, op, argument], a box is
    {"token", "text"} with '{var}' for shown values, closed by '(,$'"""
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"N11F"
    end, = struct.unpack_from("<I", d, 4)
    x = bytes(b ^ w.BIO_KEY[i % 4] for i, b in enumerate(d[end:]))
    count, first = struct.unpack_from("<2I", x, 0)
    if 8 + 4 * (count + 1) > len(x):
        return None  # yabou.n11: the strings are not in this layout
    offsets = struct.unpack_from(f"<{count + 1}I", x, 8)
    base = 8 + 4 * (count + 1)
    strings = [x[base + offsets[k]:base + offsets[k + 1]].decode("cp932") for k in range(count)]
    tokens, boxes, cur, start = [], [], [], None
    for i, t in enumerate(d[8:end].split(b",\n")[:-1] if d[8:end].endswith(b",\n") else d[8:end].split(b",\n")):
        t = t.decode("cp932")
        op, arg = t[:1], t[2:]
        tokens.append([i, OPS.get(op, f"x{ord(op):02x}"), arg])
        if op == "&":
            if start is None:
                start = i
            cur.append(strings[int(arg[3:]) - first].replace("\\n", "\n") if arg.startswith("MSG") else "{" + arg + "}")
        elif op == "(" and arg == "$":
            if cur:
                boxes.append({"token": start, "text": "".join(cur)})
            cur, start = [], None
    if cur:
        boxes.append({"token": start, "text": "".join(cur)})
    return first, strings, tokens, boxes


def events(msg_dir, out):
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    index, messages, n_boxes = [], [], 0
    with open(os.path.join(out, "events/scripts.jsonl"), "w", encoding="utf-8") as f:
        for path in sorted(glob.glob(os.path.join(msg_dir, "*.n11"))):
            name = os.path.basename(path)
            if name.startswith(SKIP_MSG):
                continue
            parsed = script(path)
            if parsed is None:
                index.append([name, "", "", "", "(not parsed)"])
                continue
            first, strings, tokens, boxes = parsed
            f.write(json.dumps({"file": name, "first": first, "boxes": boxes, "tokens": tokens},
                               ensure_ascii=False) + "\n")
            messages += [[name, first + k, s.replace("\\n", "\n")] for k, s in enumerate(strings) if k >= 2]
            index.append([name, len(boxes), len(strings) - 2, sum(t[1] == "call" for t in tokens),
                          boxes[0]["text"][:40].replace("\n", " ") if boxes else ""])
            n_boxes += len(boxes)
    _write_csv(os.path.join(out, "events/index.csv"), ["file", "boxes", "strings", "calls", "first"], index)
    _write_csv(os.path.join(out, "events/messages.csv"), ["file", "msg", "text"], messages)
    return {"events/scripts.jsonl": f"{len(index)} files, {n_boxes} boxes", "events/messages.csv": len(messages)}


@click.command("nobu11-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True, file_okay=False),
              help="the Steam files (games/nobu11pk-win)")
@click.option("--out", required=True, type=click.Path(file_okay=False))
def nobu11_extras(game_dir, out):
    """信長の野望・天下創世 PK: event pictures, 家宝, 家紋, 官位, 役職 and the message scripts."""
    for part in (pictures(os.path.join(game_dir, "grp"), out), tables(game_dir, out),
                 events(os.path.join(game_dir, "msg"), out)):
        for k, v in part.items():
            click.echo(f"{k}: {v}")


if __name__ == "__main__":
    nobu11_extras()
