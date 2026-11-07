"""信長の野望・天翔記 with パワーアップキット (PC-98, nobu6pk-pc98): event pictures, 家宝, 官位, 家紋 and message
text, written under --out as eventcg/, items/, kamon/ and events/ (notes/nobu6.md「事件、插圖、道具」).

- Picture files REKISHI1/2.NB6, PACKGRP.NB6, GAMEN.NB6 (base install) and REKISHI3.N6P (PK): u16 count, then
  (u32 offset, u16 size) per entry, offsets from the index end (sango.san5_parts). OHIROME.NB6 is LS11. Every
  picture is NPK016 (PK: magic 'NPK16\\0'): +8 screen w, h, +0xC w, +0xE h, +0x10 16 u16 colours (G << 8 | R << 4
  | B; most files carry the default digital set), pixels from 0x30 (utils.unpack_npk).
- Colours: MAINPK.EXE file 0x28CBE, 16 x (B, R, G) 4-bit (same bytes as MAIN.EXE 0x3870C); the pictures only use
  8-15 (the face colours, the same in every season), 0-7 change with the season.
- SNDATA.N6P part (one per scenario): 家宝 0xD334, 120 x 19 bytes (MAIN.EXE image 0x26025): +0 name 13, +0xD kind
  (DS:0x10D0 names), +0xE picture (PACKGRP entry 1 + n), +0xF u16 holder (name record slot, 1-based; FFFF none),
  +0x11 bonus 1-10 (bit 0-3), +0x12 flags. Kind 0-4 add the bonus to 政治, 5-10 戦闘, 11-12 智謀, 13- 野望
  (image 0x26086 and 0x261BC). 官位 0xDC1C, 250 x 18 bytes (image 0x26571): +0 name 13, +0xD court rank code
  (image 0x265C4: 0-5 正/従 一-三位, then 正/従 四位上 ...), +0xE u16 holder, +0x10 value 1-10.
- KAMON2.N6P (PK, raw): 355 x 96 bytes, 16 x 16, 3 bpp, 6 bytes a row (utils.to_3bpp_indexes), shown with colours
  8-15. 大名 record +8 (SNDATA 0xC5CA, 22 bytes) is the 家紋 number. KAMON.NB6 (base, LS11) holds the first 110.
- MESSAGE.N6P (PK, LS11, 23 parts): each part a u16 offset table, then strings. Parts 15-17 are the 家宝
  descriptions (header ESC k reading ESC H \\n name, then body), 18-22 castle descriptions.
"""
import csv
import json
import os
import re
import struct
import unicodedata

import click
from PIL import Image

import ls11
import utils
import wiki_nobu6
from sango import san5_parts

PALETTE = 0x28CBE  # MAINPK.EXE
ITEMS, ITEM_SIZE, ITEM_COUNT = 0xD334, 19, 120
KANI, KANI_SIZE, KANI_COUNT = 0xDC1C, 18, 250
DAIMYO, DAIMYO_SIZE = 0xC5CA, 22
KINDS = ["茶碗", "茶壺", "茶入", "茶釜", "花入", "刀剣", "槍", "具足", "馬", "鞍", "陣羽織", "巻子本", "明朝綴本", "香木",
         "地球儀", "南蛮時計", "水墨画", "十字架", "聖書", "玉手箱", "ビードロ杯", "遠眼鏡", "ルソン壺", "煙草"]  # DS:0x10D0
SCENARIOS = [1534, 1560, 1571, 1582, 1546, 1599]  # SNDATA.N6P order


def item_stat(kind):
    return "野望" if kind >= 13 else "智謀" if kind >= 11 else "戦闘" if kind >= 5 else "政治"


def court_rank(code):
    """image 0x265C4: 0-5 正一位 従一位 ... 従三位, then 正四位上 正四位下 従四位上 従四位下 正五位上 ..."""
    if code < 6:
        return ("従" if code & 1 else "正") + "一二三"[code // 2] + "位"
    s = code - 6
    return ("従" if s & 3 >= 2 else "正") + "四五六七八"[s // 4] + "位" + ("下" if s & 1 else "上")


# Pictures: (group, file, base install?, entries, description); descriptions are read off the pictures (🟡) except
# the 天災 set, whose order follows MESSAGE part 5 strings 0-7 (日照り ... 一揆).
PICTURES = [
    ("rekishi", "REKISHI1.NB6", True, range(5),
     ["公家と対面する武将", "夕焼けの天守", "火縄銃を構える武将（背後に炎）", "南蛮人と鉄砲", "宣教師の説教"]),
    ("rekishi", "REKISHI2.NB6", True, range(7),
     ["書状を読み上げる武将", "格子越しに見る武将たち", "門前の対面", "騎馬の大将と歓声", "鬨の声を上げる足軽",
      "炎上する城", "鉄甲船"]),
    ("rekishi_pk", "REKISHI3.N6P", False, range(15),
     ["茶を運ぶ小姓", "三人の武将", "天守と縁側の武将", "上座の武将と家臣", "大杯をあおる武将", "剃髪", "追放",
      "騎馬隊の突撃", "組み打ち", "膳を囲む二人", "寝所の刺客", "独眼の武将", "捕縛", "小舟と剣士", "木刀の立ち合い"]),
    ("shugyou", "PACKGRP.NB6", True, range(25, 35),
     ["茶の湯", "弓の稽古", "説法", "相撲", "乗馬", "鉄砲の稽古", "水練", "算術", "書見", "鷹狩"]),
    ("hanyou", "PACKGRP.NB6", True, range(35, 51),
     ["日照り", "長雨", "疫病", "飢饉", "大雪", "豊作", "凶作", "一揆", "一向一揆", "臨終", "上座の武将", "密談",
      "夜の城門", "隠居", "婚礼", "出陣"]),
]
PICTURE_EVIDENCE = {("hanyou", k): "✅ cross: MESSAGE part 5" for k in range(35, 43)}
PICTURE_EVIDENCE[("hanyou", 43)] = "✅ cross: 南無阿弥陀仏 banners"
GAMEN = [(0, 1, 2, "朝廷（謁見）"), (3, 4, 5, "将軍（謁見）"), (6, 7, 8, "大名（評定）")]  # bar, hall, bar
OHIROME_BACKGROUNDS = 6  # OHIROME.NB6 parts 0-5 are 288 x 128 backgrounds; 6-53 are figure frames (not kept)


def _palette(game_dir):
    with open(os.path.join(game_dir, "MAINPK.EXE"), "rb") as f:
        f.seek(PALETTE)
        b = f.read(48)
    return [(b[3 * i + 1] * 17, b[3 * i + 2] * 17, b[3 * i] * 17) for i in range(16)]


def npk(data, palette):
    assert data[:6] in (b"NPK016", b"NPK16\0"), data[:6]
    w, h = struct.unpack_from("<2H", data, 0xC)
    im = Image.new("RGB", (w, h))
    im.putdata([palette[i] for i in utils.unpack_npk(data[0x30:], w, h)[:w * h]])
    return im


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _text(b):
    """MESSAGE string: half-width kana is hiragana, katakana between ESC K and ESC H; gaiji as in the 列伝; other
    control codes (I… conditions, S*n, C…, d/e/f placeholders) are left as they are, bytes below 0x20 as {xx}."""
    out, i, katakana = [], 0, False
    while i < len(b):
        gaiji = next((k for k in wiki_nobu6.NOBU6_PC98_GAIJI if b.startswith(k, i)), None)
        if gaiji:
            out.append(wiki_nobu6.NOBU6_PC98_GAIJI[gaiji])
            i += len(gaiji)
        elif b[i] == 0x1B:
            katakana, i = b[i + 1:i + 2] in (b"K", b"k"), i + 2
        elif 0xA1 <= b[i] <= 0xDF:
            j = i
            while j < len(b) and 0xA1 <= b[j] <= 0xDF:
                j += 1
            run = b[i:j].decode("cp932")
            out.append(("ヶ" if run == "ｹ" else unicodedata.normalize("NFKC", run)) if katakana
                       else wiki_nobu6._kana(run, True))
            i = j
        elif b[i] == 5:
            i += 1
        elif b[i] < 0x20 and b[i] != 0x0A:
            out.append(f"{{{b[i]:02x}}}")
            i += 1
        else:
            n = 2 if (0x81 <= b[i] <= 0x9F or 0xE0 <= b[i] <= 0xFC) and i + 1 < len(b) else 1
            out.append(b[i:i + n].decode("cp932", "replace"))
            i += n
    return "".join(out).strip()


def _strings(part):
    n = struct.unpack_from("<H", part)[0] // 2
    offs = list(struct.unpack_from(f"<{n}H", part)) + [len(part)]
    return [part[offs[j]:offs[j + 1]] for j in range(n)]


def _described(parts):
    """(header, body) pairs of description parts: header ESC k reading ESC H \\n name, or name ESC k reading."""
    out = []
    for part in parts:
        s = _strings(part)
        out += [(s[j], s[j + 1]) for j in range(0, len(s) - 1, 2)]
    return out


def _write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def eventcg(game_dir, base_dir, out):
    pal = _palette(game_dir)
    os.makedirs(out, exist_ok=True)
    rows = []
    for group, name, base, entries, descs in PICTURES:
        parts = san5_parts(os.path.join(base_dir if base else game_dir, name))
        for n, desc in zip(entries, descs):
            file = f"{group}_{n:02d}.png"
            im = npk(parts[n], pal)
            im.save(os.path.join(out, file))
            rows.append([file, group, f"{name}#{n}", f"{im.width}x{im.height}", desc,
                         PICTURE_EVIDENCE.get((group, n), "🟡 description read off the picture")])
    parts = san5_parts(os.path.join(base_dir, "GAMEN.NB6"))
    for k, (top, hall, bottom, desc) in enumerate(GAMEN):
        ims = [npk(parts[i], pal) for i in (top, hall, bottom)]
        im = Image.new("RGB", (640, sum(i.height for i in ims)))
        y = 0
        for i in ims:
            im.paste(i, (0, y))
            y += i.height
        file = f"gamen_{k}.png"
        im.save(os.path.join(out, file))
        rows.append([file, "gamen", f"GAMEN.NB6#{top}-{bottom}", f"{im.width}x{im.height}", desc,
                     "🟡 bars stacked above and below the hall; how the game places them not checked"])
    parts = ls11.ls11_decode_parts(_read(os.path.join(base_dir, "OHIROME.NB6")))
    for n in range(OHIROME_BACKGROUNDS):
        file = f"ohirome_{n:02d}.png"
        im = npk(parts[n], pal)
        im.save(os.path.join(out, file))
        rows.append([file, "ohirome", f"OHIROME.NB6#{n}", f"{im.width}x{im.height}", "修行披露の背景",
                     "🟡 description read off the picture"])
    _write_csv(os.path.join(out, "index.csv"), ["file", "group", "source", "size", "description", "evidence"], rows)
    return len(rows)


def _scenario_names(game_dir):
    """per scenario: name of each name-record slot (1-based)"""
    out = []
    for sc in ls11.ls11_decode_parts(_read(os.path.join(game_dir, "SNDATA.N6P"))):
        names = {}
        for slot in range(1, 532):
            rec = sc[wiki_nobu6.NAMES + 18 * (slot - 1):][:18]
            if rec[0]:
                names[slot] = wiki_nobu6._name(rec)
        out.append((sc, names))
    return out


def _name13(b):
    return wiki_nobu6._nobu6_pc98_text(b[:13].split(b"\0")[0])


def items(game_dir, base_dir, out):
    pal = _palette(game_dir)
    os.makedirs(os.path.join(out, "pictures"), exist_ok=True)
    packgrp = san5_parts(os.path.join(base_dir, "PACKGRP.NB6"))
    scenarios = _scenario_names(game_dir)
    messages = ls11.ls11_decode_parts(_read(os.path.join(game_dir, "MESSAGE.N6P")))
    descs = _described(messages[15:18])
    rows = []
    for i in range(ITEM_COUNT):
        rec = scenarios[0][0][ITEMS + ITEM_SIZE * i:][:ITEM_SIZE]
        name, kind, picture, bonus, flags = _name13(rec), rec[0xD], rec[0xE], rec[0x11] & 0xF, rec[0x12]
        holders = []
        for year, (sc, names) in zip(SCENARIOS, scenarios):
            h = struct.unpack_from("<H", sc, ITEMS + ITEM_SIZE * i + 0xF)[0]
            if h != 0xFFFF:
                holders.append(f"{year}:{names.get(h, h)}")
        head, body = descs[i]
        m = re.match(rb"\x1bk(.*?)\x1bH\n(.*?)\x05", head, re.S)
        reading = unicodedata.normalize("NFKC", m.group(1).decode("cp932"))
        desc_name = _text(m.group(2))
        rows.append([i + 1, name, reading, kind, KINDS[kind], item_stat(kind), bonus, f"pictures/{picture:02d}.png",
                     " ".join(holders), f"{flags:02x}", desc_name if desc_name != name else "",
                     _text(body).replace("\n", "")])
    _write_csv(os.path.join(out, "kahou.csv"),
               ["id", "name", "reading", "kind", "kind_name", "stat", "bonus", "picture", "holders", "flags",
                "description_name", "description"], rows)
    for n in range(22):  # picture n is PACKGRP entry 1 + n
        npk(packgrp[1 + n], pal).save(os.path.join(out, "pictures", f"{n:02d}.png"))
    kani = []
    for i in range(KANI_COUNT):
        rec = scenarios[0][0][KANI + KANI_SIZE * i:][:KANI_SIZE]
        holders = []
        for year, (sc, names) in zip(SCENARIOS, scenarios):
            h = struct.unpack_from("<H", sc, KANI + KANI_SIZE * i + 0xE)[0]
            if h != 0xFFFF:
                holders.append(f"{year}:{names.get(h, h)}")
        kani.append([i + 1, _name13(rec), rec[0xD], court_rank(rec[0xD]), rec[0x10], " ".join(holders)])
    _write_csv(os.path.join(out, "kani.csv"), ["id", "name", "rank_code", "court_rank", "value", "holders"], kani)
    return len(rows), len(kani)


def kamon(game_dir, out):
    pal = _palette(game_dir)[8:]
    data = _read(os.path.join(game_dir, "KAMON2.N6P"))
    users = {}
    for year, (sc, names) in zip(SCENARIOS, _scenario_names(game_dir)):
        for d in range(72):
            rec = sc[DAIMYO + DAIMYO_SIZE * d:][:DAIMYO_SIZE]
            lord = struct.unpack_from("<H", rec)[0]
            if lord not in (0, 0xFFFF):
                users.setdefault(rec[8], []).append(f"{year}:{names.get(lord, lord)}")
    os.makedirs(out, exist_ok=True)
    rows = []
    for n in range(len(data) // 96):
        im = Image.new("RGB", (16, 16))
        im.putdata([pal[i] for i in utils.to_3bpp_indexes(data[96 * n:96 * n + 96])])
        im.save(os.path.join(out, f"{n:03d}.png"))
        rows.append([n, f"{n:03d}.png", " ".join(users.get(n, []))])
    _write_csv(os.path.join(out, "index.csv"), ["number", "file", "daimyo"], rows)
    return len(rows)


def events(game_dir, out):
    """MESSAGE.N6P strings, one line each (parts 0-14 and the castle descriptions 18-22)."""
    parts = ls11.ls11_decode_parts(_read(os.path.join(game_dir, "MESSAGE.N6P")))
    os.makedirs(out, exist_ok=True)
    n = 0
    with open(os.path.join(out, "messages.jsonl"), "w", encoding="utf-8") as f:
        for k, part in enumerate(parts):
            if 15 <= k <= 17:
                continue  # 家宝 descriptions (items/kahou.csv)
            if k >= 18:
                continue
            for j, s in enumerate(_strings(part)):
                f.write(json.dumps({"part": k, "index": j, "text": _text(s)}, ensure_ascii=False) + "\n")
                n += 1
    castles = []
    for head, body in _described(parts[18:]):
        m = re.match(rb"(?:I4=\d)?(.*?) \x1bk(.*?)(?:\x05|$)", head, re.S)
        if not m:
            continue
        castles.append([wiki_nobu6._nobu6_pc98_text(m.group(1)),
                        unicodedata.normalize("NFKC", m.group(2).decode("cp932")), _text(body).replace("\n", "")])
    _write_csv(os.path.join(out, "castles.csv"), ["name", "reading", "description"], castles)
    return n, len(castles)


@click.command(help="信長の野望・天翔記 PK: event pictures, 家宝, 官位, 家紋 and message text.")
@click.option("--game-dir", required=True, help="PK files (games/nobu6pk-pc98)")
@click.option("--base-dir", required=True, help="base install (games/nobu6-pc98): REKISHI1/2, PACKGRP, GAMEN, OHIROME")
@click.option("--out", required=True)
def nobu6_extras(game_dir, base_dir, out):
    print("eventcg:", eventcg(game_dir, base_dir, os.path.join(out, "eventcg")))
    print("items (家宝, 官位):", items(game_dir, base_dir, os.path.join(out, "items")))
    print("kamon:", kamon(game_dir, os.path.join(out, "kamon")))
    print("events (messages, castles):", events(game_dir, os.path.join(out, "events")))

