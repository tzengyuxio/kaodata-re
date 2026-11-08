"""太閤立志伝V DX (Steam, appid 1842810): event pictures, event texts, items, trade goods, battle cards, town and room
backgrounds and maps, written under --out (notes/taikoh5.md「事件、插圖、道具」).

- *.G1T: one 'GT1G' texture set, or an 'MRLK' archive of them (+4 u32 count, (u32 offset, u32 size) pairs from +8).
  A texture set has u32 +12 the table offset and u32 +16 the count; each texture header (table + table[i]) has byte 1
  the format (0x59 BC1, 0x5B BC3, 0x01 RGBA8), byte 2 log2 height/width (0 = the u32 width, height at +0x14, +0x18),
  u32 +8 the size of the extra header the pixels follow.
- Taiko5DX.exe (x64) holds the tables, found by a name in them and walked while the records stay valid:
  items 355 x 40 bytes (name 15, half-width reading 18, +0x21 u8 picture in ITEM.G1T, u16 price, u8 kind, u8, u8,
  u8), trade goods 100 x 26 (name 9, reading 11, 6 bytes, the last the picture in TRITEM.G1T), battle cards 75 x 34
  (4 bytes, name 15, u8, reading 14), event still titles (4-aligned strings); the Traditional Chinese copies (Big5 with
  the KOEI codes of koei_games.TAIKOH5_WIN_TW_GAIJI) sit in the same layout.
- CMENU/SNR/SNR?_JP.TR5 part 18: 355 x (u16 holder record, u16) — 1305 is nobody.
- EVENT/*.TS5 (and EVENT_TW/): event scripts, 4-byte aligned opcodes; 0x11 xx xx xx is followed by a NUL-terminated
  text. Hiragana are half-width katakana bytes; \\#XXXX names a person record (0x800: given name only, 0x1000: surname
  only), \\%NN is a run-time variable.
"""
import csv
import json
import os
import re
import struct

import click
from PIL import Image

import koei_games as kg

BCN = {0x59: 1, 0x5B: 3}
HALF = "｡｢｣､･ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝﾞﾟ"
HIRA = "。「」、・をぁぃぅぇぉゃゅょっーあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん゛゜"
TO_HIRA = str.maketrans(HALF, HIRA)
SCENARIOS = 9
NOBODY = 1305
# the first 32 titles match EVSTILL 0-31 one to one (checked by eye); 44-50 are titles 40-46
STILL_TITLE = {**{i: i for i in range(32)}, **{i: i - 4 for i in range(44, 51)}}
# (folder, file): pictures written as they are
PICTURES = [
    ("eventcg/town", "MP/TOWN.G1T"),            # 156 x 1920x1080 town views
    ("eventcg/room", "MP/ROOM.G1T"),            # 67 x 1920x1080 interiors
    ("eventcg/battle", "WAR/CWGRP1.G1T"),       # 23 x 1920x1080 battle backgrounds
    ("eventcg/scenario", "CMENU/INITSCNSTL.G1T"),  # 9 scenario pictures
    ("cards/pictures", "FUDA.G1T"),             # 179 x 416x544 card pictures
    ("map/japan_tiles", "JP/JAPANMAP.G1T"),     # 276 x 720x504
    ("map/nankai", "JP/NANKAIMAP.G1T"),
    ("map/japan_b", "JP/JAPANMAPB.G1T"),
    ("map/battle", "WAR/FWARMAP.G1T"),          # 20 field battle maps
    ("map/kyoten", "BASE/JMAPKYOTEN.G1T"),      # 35 map markers
]
MINIMAP = ("JP/JAPANMMAP.G1T", 11)  # 110 x 480x336, 11 per row


def textures(path):
    with open(path, "rb") as f:
        data = f.read()
    sets = [data]
    if data[:4] == b"MRLK":
        n, = struct.unpack_from("<I", data, 4)
        sets = [data[o:o + s] for o, s in (struct.unpack_from("<2I", data, 8 + 8 * i) for i in range(n))]
    for d in sets:
        assert d[:4] == b"GT1G"
        table, count = struct.unpack_from("<2I", d, 12)
        for off in struct.unpack_from(f"<{count}I", d, table):
            h = table + off
            fmt, dim = d[h + 1], d[h + 2]
            w, ht = struct.unpack_from("<2I", d, h + 0x14) if dim == 0 else (1 << (dim & 15), 1 << (dim >> 4))
            start = h + 8 + struct.unpack_from("<I", d, h + 8)[0]
            if fmt in BCN:
                size = w * ht // 2 if BCN[fmt] == 1 else w * ht
                yield Image.frombytes("RGBA", (w, ht), d[start:start + size], "bcn", BCN[fmt])
            else:
                assert fmt == 1, fmt
                yield Image.frombytes("RGBA", (w, ht), d[start:start + w * ht * 4])


def save_all(path, out):
    os.makedirs(out, exist_ok=True)
    n = 0
    for n, im in enumerate(textures(path), 1):
        im.save(os.path.join(out, f"{n - 1:04d}.png"))
    return n


def tw(b: bytes) -> str:
    out, i = "", 0
    while i < len(b):
        if b[i] < 0x80:
            out, i = out + chr(b[i]), i + 1
            continue
        if i + 1 == len(b):  # a lone lead byte ends some texts
            return out + "\ufffd"
        code = b[i] << 8 | b[i + 1]
        out, i = out + (kg.TAIKOH5_WIN_TW_GAIJI.get(code) or b[i:i + 2].decode("big5", "replace")), i + 2
    return out


def jp(b: bytes) -> str:
    return b.decode("cp932", "replace")


def cstr(b: bytes) -> bytes:
    return b.split(b"\0")[0]


def table(exe, anchor, size, valid, shift=0):
    """Records of a fixed-size table holding anchor (at shift in its record), walked while valid(record bytes)."""
    o = exe.find(anchor)
    assert o >= 0, anchor
    o -= shift
    while valid(exe[o - size:o]):
        o -= size
    recs = []
    while valid(exe[o:o + size]):
        recs.append(exe[o:o + size])
        o += size
    return recs


def kana(b: bytes) -> bool:
    return bool(b) and all(0xA1 <= c <= 0xDF for c in b)


def titles(exe, anchor, decode, count):
    o, out = exe.find(anchor), []
    assert o >= 0
    while len(out) < count:
        j = exe.index(b"\0", o)
        out.append(decode(exe[o:j]))
        o = (j + 4) & ~3
        while exe[o] == 0:
            o += 4
    return out


def person_names(path, tw_text):
    """(surname, given name) of every person record of one SNR?.TR5."""
    part = kg._taikoh5_win_part(path, 16)
    dec = tw if tw_text else jp
    return [(dec(cstr(part[o:o + 9])), dec(cstr(part[o + 9:o + 18])))
            for o in range(0, len(part), kg.TAIKOH5_WIN_PERSON)]


def event_texts(data):
    """(offset, opcode hex, text bytes) of every text of a .TS5 script."""
    out, i = [], 0x10
    while i < len(data) - 4:
        if data[i] == 0x11:
            j = data.find(b"\0", i + 4)
            if j > i + 4:
                out.append((i, data[i:i + 4].hex(), data[i + 4:j]))
            i = (j + 4) & ~3
            continue
        i += 4
    return out


def resolve(text, names):
    def name(m):
        v = int(m.group(1), 16)
        k = v & 0x7FF
        if k >= len(names):
            return m.group(0)
        sur, given = names[k]
        return sur if v & 0x1000 else given if v & 0x800 else sur + given
    return re.sub(r"\\#([0-9A-F]{4})", name, text)


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


@click.command()
@click.option("--game-dir", required=True, type=click.Path(exists=True, file_okay=False),
              help="Steam files (games/taikoh5dx-win)")
@click.option("--out", required=True, type=click.Path(file_okay=False))
def taikoh5_extras(game_dir, out):
    """太閤立志伝V DX: event pictures and texts, items, trade goods, battle cards, backgrounds, maps."""
    data = os.path.join(game_dir, "data")
    with open(os.path.join(game_dir, "Taiko5DX.exe"), "rb") as f:
        exe = f.read()
    snr = [os.path.join(data, "CMENU", "SNR", f"SNR{s}_{{}}.TR5") for s in range(SCENARIOS)]
    names_jp = person_names(snr[5].format("JP"), False)
    names_tw = person_names(snr[5].format("TW"), True)

    # items
    def item_ok(r):
        return len(r) == 40 and kana(cstr(r[15:0x21])) and bool(cstr(r[:15]))
    items = table(exe, "古天明平蜘蛛".encode("cp932"), 40, item_ok)
    o = exe.find("帝釋栗毛".encode("big5")) - 40
    items_tw = [exe[o + 40 * i:o + 40 * i + 40] for i in range(len(items))]
    assert len(items) == 355, len(items)
    rows = []
    for i, (r, t) in enumerate(zip(items, items_tw)):
        pic, price, kind, b4, b5, b6 = struct.unpack_from("<BHBBBB", r, 0x21)
        assert t[0x21:] == r[0x21:], i  # the Chinese table keeps the same data bytes
        rows.append([i, jp(cstr(r[:15])), jp(cstr(r[15:0x21])), tw(cstr(t[:15])), pic, price,
                     f"0x{kind:02X}", b4, b5, b6])
    write_csv(os.path.join(out, "items", "items.csv"),
              ["item", "name", "reading", "name_zh", "picture", "price", "kind", "b4", "b5", "b6"], rows)
    hold = []
    for s in range(SCENARIOS):
        part = kg._taikoh5_win_part(snr[s].format("JP"), 18)
        names = person_names(snr[s].format("JP"), False)
        for i in range(len(items)):
            h, x = struct.unpack_from("<2H", part, 4 * i)
            if h != NOBODY:
                hold.append([s, i, rows[i][1], h, "".join(names[h]) if h < len(names) else "", x])
    write_csv(os.path.join(out, "items", "holders.csv"),
              ["scenario", "item", "name", "holder", "holder_name", "u16"], hold)
    n_item_pics = save_all(os.path.join(data, "ITEM.G1T"), os.path.join(out, "items", "pictures"))

    # trade goods
    def good_ok(r):
        return len(r) == 26 and bool(cstr(r[:9])) and kana(cstr(r[9:20]))
    goods = table(exe, "朝鮮人参".encode("cp932"), 26, good_ok)
    o = exe.find("醬油".encode("big5"))
    goods_tw = [exe[o + 26 * i:o + 26 * i + 26] for i in range(len(goods))]
    write_csv(os.path.join(out, "goods", "goods.csv"), ["good", "name", "reading", "name_zh", "bytes", "picture"],
              [[i, jp(cstr(r[:9])), jp(cstr(r[9:20])), tw(cstr(t[:9])), r[20:25].hex(), r[25]]
               for i, (r, t) in enumerate(zip(goods, goods_tw))])
    n_goods_pics = save_all(os.path.join(data, "TRITEM.G1T"), os.path.join(out, "goods", "pictures"))

    # battle cards
    def card_ok(r):
        return len(r) == 34 and bool(cstr(r[4:19])) and kana(cstr(r[20:34]))
    cards = table(exe, "罵詈雑言".encode("cp932"), 34, card_ok, 4)
    write_csv(os.path.join(out, "cards", "battle_cards.csv"), ["card", "name", "reading", "bytes", "u8"],
              [[i, jp(cstr(r[4:19])), jp(cstr(r[20:34])), r[:4].hex(), r[19]] for i, r in enumerate(cards)])

    # event stills
    t_jp = titles(exe, "墨俣築城".encode("cp932"), jp, 64)
    t_tw = titles(exe, "墨俁築城".encode("big5"), tw, 64)
    n_still = save_all(os.path.join(data, "EVSTILL.G1T"), os.path.join(out, "eventcg", "still"))
    write_csv(os.path.join(out, "eventcg", "still.csv"), ["file", "title", "title_zh", "confidence"],
              [[f"{i:04d}.png", t_jp[STILL_TITLE[i]] if i in STILL_TITLE else "",
                t_tw[STILL_TITLE[i]] if i in STILL_TITLE else "",
                "picture" if i < 32 else "guess" if i in STILL_TITLE else ""] for i in range(n_still)])
    write_csv(os.path.join(out, "eventcg", "titles.csv"), ["title", "name", "name_zh"],
              [[i, a, b] for i, (a, b) in enumerate(zip(t_jp, t_tw))])

    # other pictures
    counts = {}
    for folder, rel in PICTURES:
        counts[folder] = save_all(os.path.join(data, rel), os.path.join(out, folder))
    tiles = list(textures(os.path.join(data, MINIMAP[0])))
    w, h = tiles[0].size
    cols = MINIMAP[1]
    mm = Image.new("RGBA", (cols * w, len(tiles) // cols * h))
    for i, im in enumerate(tiles):
        mm.paste(im, (i % cols * w, i // cols * h))
    mm.save(os.path.join(out, "map", "japan_mini.png"))

    # event scripts
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    index, n_lines = [], 0
    with open(os.path.join(out, "events", "messages.jsonl"), "w", encoding="utf-8") as f:
        for name in sorted(os.listdir(os.path.join(data, "EVENT"))):
            if not name.endswith(".TS5"):
                continue
            with open(os.path.join(data, "EVENT", name), "rb") as g:
                lines = event_texts(g.read())
            zh_path = os.path.join(data, "EVENT_TW", name)
            zh = []
            if os.path.exists(zh_path):
                with open(zh_path, "rb") as g:
                    zh = event_texts(g.read())
            for k, (off, op, text) in enumerate(lines):
                ja = jp(text).translate(TO_HIRA)
                rec = {"file": name[:-4], "line": k, "op": op, "ja": ja, "jaNames": resolve(ja, names_jp)}
                if len(zh) == len(lines):
                    rec["zh"] = tw(zh[k][2])
                    rec["zhNames"] = resolve(rec["zh"], names_tw)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_lines += len(lines)
            refs = sorted({int(m, 16) & 0x7FF for _, _, t in lines for m in re.findall(rb"\\#([0-9A-F]{4})", t)})
            index.append([name[:-4], len(lines), len(zh) == len(lines),
                          " ".join("".join(names_jp[r]) for r in refs if r < len(names_jp)),
                          resolve(jp(lines[0][2]).translate(TO_HIRA), names_jp).replace("\n", " ") if lines else ""])
    write_csv(os.path.join(out, "events", "index.csv"),
              ["event", "lines", "zh_aligned", "persons", "first_line"], index)

    click.echo(f"items {len(items)} ({len(hold)} holdings in {SCENARIOS} scenarios, {n_item_pics} pictures), "
               f"goods {len(goods)} ({n_goods_pics} pictures), battle cards {len(cards)}, "
               f"event stills {n_still}, events {len(index)} ({n_lines} lines)")
    click.echo(", ".join(f"{k} {v}" for k, v in counts.items()) + f", japan_mini {mm.size[0]}x{mm.size[1]}")


if __name__ == "__main__":
    taikoh5_extras()
