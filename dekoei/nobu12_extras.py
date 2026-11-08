"""信長の野望・革新 with PK (Steam, appid 363090): event pictures, 家宝, 特産品, 家紋 and event scripts, written under
--out as eventcg/, items/, kamon/ and events/ (notes/nobu12.md「事件、插圖、道具」).

- Grp/*.n12 picture files are F11N containers: +4 u32 texture count, then from 0xC one 20-byte entry per texture
  (u32 first sprite, last sprite, sprite count, rect table offset, texture offset). A rect is 4 u16 (x, y, w, h); a
  texture is 'T11N', u32 width, height, texture width, height, 2 bytes, then B, G, R, A pixels. Files with one
  sprite per texture use the whole width x height (the rect table there is not needed).
- Event pictures are left / right halves: rekishicg.n12 152 x 360x400, endingcg.n12 16 x 360x400 (then 140 sepia
  256x256 fog tiles and a mask), hanyoucg.n12 74 x 240x360. Script scene numbers (Msg/*.n12 calls of Fnc042) count
  the joined pictures hanyou 0-36, rekishi 37-112, ending 113-120.
- 家宝: section (9, 455) of the LWC-decoded scenario holds the names (201 bytes: name 15, reading from +15); section
  (13, 455) the data (21 bytes: u16 id, i16 戦法, i16 ?, i16 owner slot, u32 picture, u32 grade 1-10, u32 kind,
  u8 flags). Kind names: NOBU12PK.exe 0x753E9C-0x753F9C (stored backwards from 茶入; 弓 and 大砲 are missing from
  the table and inferred). The 355 named records follow Msg/Kfile01-08.n12 in order.
- 特産品: tokusanhincg.n12, 20 x 96x96, in the order of the NOBU12PK.exe name table (backwards from 漆器 at
  0x755398).
- Msg/*.n12 (N12F) scripts: tokens split by ',\\n'; '&,MSGnnn' a string, '&,<var>.FncNNN' a value shown in the text,
  '),<n>' and ',,<var>' arguments of the next '(,FncNNN' call, '(,Fnc000' without arguments ends a text box,
  '*,<n>' a label.
"""
import csv
import glob
import json
import os
import struct

import click
from PIL import Image

import wiki_nobu12
from wiki_nobu12 import msg_entries

ITEM_NAMES, ITEM_DATA = (9, 455), (13, 455)
NAME_SIZE, DATA_SIZE = 201, 21
# kind 0-35; NOBU12PK.exe 0x753F9C backwards, with 弓 (11) and 大砲 (22) inferred from the items of those kinds
KINDS = ["茶入", "茶壷", "茶釜", "茶碗", "花入", "茶杓", "香炉", "水指", "刀剣", "槍", "名馬", "弓", "火縄銃", "管打銃", "短筒",
         "具足", "兜", "剣術書", "馬術書", "弓術書", "砲術書", "忍術書", "大砲", "水軍書", "建築書", "農業書", "商業書", "知識書",
         "兵法書", "軍記物", "医書", "水墨画", "彩色画", "菓子", "地酒", "香木"]
INFERRED_KINDS = {11, 22}
GRADES = ["十等級", "九等級", "八等級", "七等級", "六等級", "五等級", "四等級", "三等級", "二等級", "一等級"]  # grade 1-10
# NOBU12PK.exe 0x755398 backwards; the 20 pictures of tokusanhincg.n12 match them one by one
SPECIALTIES = ["漆器", "焼物", "日本刀", "紙", "書画", "絹織物", "麻織物", "綿織物", "金", "銀", "銅", "硫黄", "米", "醤油",
               "塩", "酒", "茶", "魚介", "木材", "薬"]
# (set, file, first scene number, pictures used): two pictures make one scene
CG_SETS = [("hanyou", "hanyoucg.n12", 0, 74), ("rekishi", "rekishicg.n12", 37, 152), ("ending", "endingcg.n12", 113, 16)]
CG_CALL = "042"
ICON_SETS = [("kani", "kanicg.n12"), ("yakushoku", "yakushokucg.n12")]  # 8 colour tiers each, names not found
KINDS_OF_FILE = [("rek_", "歴史イベント"), ("tok_tec_", "特殊技術"), ("trl_", "試練"), ("end_", "エンディング"),
                 ("ending", "エンディング"), ("tut_", "チュートリアル"), ("rekev", "歴史イベント共通"),
                 ("tokev", "汎用イベント"), ("ryouyuu", "歴史イベント")]
SKIP_MSG = ("Bfile", "Kfile", "N12MsgTag")  # 列伝 (biography export), 家宝 descriptions (items/), the tag list


def f11n_sprites(path):
    """The sprites of an F11N file as RGBA images, in sprite order."""
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"F11N"
    n, = struct.unpack_from("<I", d, 4)
    for i in range(n):
        first, last, count, rects, data = struct.unpack_from("<5I", d, 0xC + 20 * i)
        assert d[data:data + 4] == b"T11N"
        w, h, tw, th = struct.unpack_from("<4I", d, data + 4)
        tex = Image.frombytes("RGBA", (tw, th), d[data + 22:data + 22 + tw * th * 4], "raw", "BGRA")
        if count == 1:
            yield tex.crop((0, 0, w, h))
            continue
        for k in range(count):
            x, y, rw, rh = struct.unpack_from("<4H", d, rects + 8 * k)
            yield tex.crop((x, y, x + rw, y + rh))


def _strings(d, st):
    cnt, first = struct.unpack_from("<2I", d, st)
    offs = struct.unpack_from(f"<{cnt + 1}I", d, st + 8)
    base = st + 8 + 4 * (cnt + 1)
    return first, [d[base + offs[k]:base + offs[k + 1]].decode("cp932") for k in range(cnt)]


def script(path):
    """(text boxes, steps, strings) of one N12F file: a box is its text with '{var.FncNNN}' for shown values; a step
    is [function, arguments] in order, ['box', k] where text box k falls and ['label', n] for '*,n'."""
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"N12F"
    st, n = struct.unpack_from("<2I", d, 4)
    first, strings = _strings(d, st)
    boxes, steps, cur, args = [], [], [], []

    def close():
        if cur:
            boxes.append("".join(cur).replace("\\n", "\n"))
            steps.append(["box", len(boxes) - 1])

    for t in d[0x14 + 4 * n:st].split(b",\n"):
        t = t.decode("cp932")
        if t.startswith("&,MSG"):
            cur.append(strings[int(t[5:]) - first])
        elif t.startswith("&,"):
            cur.append("{" + t[2:] + "}")
        elif t.startswith("),") or t.startswith(",,"):
            args.append(t[2:].strip())
        elif t.startswith("*,"):
            steps.append(["label", int(t[2:])])
        elif t.startswith("(,"):
            fn = t[2:].split("Fnc")[-1] if "." not in t else t[2:]
            if fn == "000" and not args:
                close()
                cur = []
            else:
                steps.append([fn, args])
            args = []
    close()
    return boxes, steps, strings


def _csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _scripts(game_dir):
    for path in sorted(glob.glob(os.path.join(game_dir, "Msg", "*.n12"))):
        name = os.path.basename(path)[:-4]
        if not name.startswith(SKIP_MSG):
            yield name, script(path)


def items(game_dir, out):
    """家宝 table, pictures and descriptions; 特産品 and the 官位／役職 icons -> out/items/"""
    pic_dir = os.path.join(out, "items", "pictures")
    os.makedirs(pic_dir, exist_ok=True)
    pics = list(f11n_sprites(os.path.join(game_dir, "Grp", "kahou.n12")))
    for k, im in enumerate(pics):
        im.save(os.path.join(pic_dir, f"{k:02d}.png"))
    sdir = os.path.join(game_dir, "scenario")
    owners = {}
    for s in wiki_nobu12.SCENARIOS:
        data = wiki_nobu12._data(sdir, s)
        owners[s] = [struct.unpack_from("<h", data, wiki_nobu12._section(data, ITEM_DATA) + DATA_SIZE * i + 6)[0]
                     for i in range(ITEM_DATA[1])]
    names = wiki_nobu12._names(wiki_nobu12._data(sdir, wiki_nobu12.MAIN))[0]
    data = wiki_nobu12._data(sdir, "01")
    nb, db = wiki_nobu12._section(data, ITEM_NAMES), wiki_nobu12._section(data, ITEM_DATA)
    texts = msg_entries([os.path.join(game_dir, "Msg", f"Kfile{k:02d}.n12") for k in range(1, 9)])
    rows, t = [], iter(texts)
    for i in range(ITEM_NAMES[1]):
        r = data[nb + NAME_SIZE * i:nb + NAME_SIZE * (i + 1)]
        name = r[:15].split(b"\0")[0].decode("cp932")
        if not name:
            continue
        reading = r[15:].split(b"\0")[0].decode("cp932")
        no, tactic, u4, _, picture, grade, kind = struct.unpack_from("<HhhhIII", data, db + DATA_SIZE * i)
        assert no == i and picture < len(pics)
        tname, text = next(t)
        who = " ".join(f"{s}:{names[owners[s][i]]}" for s in wiki_nobu12.SCENARIOS if owners[s][i] >= 0)
        rows.append([i, name, reading, kind, KINDS[kind] + ("?" if kind in INFERRED_KINDS else ""), grade,
                     GRADES[grade - 1], wiki_nobu12.TACTICS[tactic] if tactic >= 0 else "", u4,
                     data[db + DATA_SIZE * i + 20], f"pictures/{picture:02d}.png", who,
                     "" if tname == name else tname, text])
    assert next(t, None) is None
    _csv(os.path.join(out, "items", "kahou.csv"),
         ["id", "name", "reading", "kind_id", "kind", "grade", "grade_name", "tactic", "u4", "flags", "picture",
          "owners", "description_name", "description"], rows)
    sdir = os.path.join(out, "items", "tokusanhin")
    os.makedirs(sdir, exist_ok=True)
    spec = list(f11n_sprites(os.path.join(game_dir, "Grp", "tokusanhincg.n12")))
    assert len(spec) == len(SPECIALTIES)
    for k, im in enumerate(spec):
        im.save(os.path.join(sdir, f"{k:02d}.png"))
    _csv(os.path.join(sdir, "index.csv"), ["id", "name", "file"],
         [[k, n, f"{k:02d}.png"] for k, n in enumerate(SPECIALTIES)])
    for kind, name in ICON_SETS:
        os.makedirs(os.path.join(out, "items", kind), exist_ok=True)
        for k, im in enumerate(f11n_sprites(os.path.join(game_dir, "Grp", name))):
            im.save(os.path.join(out, "items", kind, f"{k}.png"))
    return len(rows)


def _join(a, b):
    im = Image.new("RGBA", (a.width + b.width, max(a.height, b.height)))
    im.paste(a, (0, 0))
    im.paste(b, (a.width, 0))
    return im


def eventcg(game_dir, out):
    """the 121 script-numbered scenes (two halves joined) -> out/eventcg/, with index.csv"""
    used = {}
    for name, (_, steps, _) in _scripts(game_dir):
        for fn, args in steps:
            if fn == CG_CALL:
                used.setdefault(int(args[-1]), set()).add(name)
    rows = []
    for kind, name, first, count in CG_SETS:
        os.makedirs(os.path.join(out, "eventcg", kind), exist_ok=True)
        sprites = list(f11n_sprites(os.path.join(game_dir, "Grp", name)))[:count]
        for k in range(count // 2):
            im = _join(sprites[2 * k], sprites[2 * k + 1])
            file = f"{kind}/{k:03d}.png"
            im.convert("RGB").save(os.path.join(out, "eventcg", file))
            cg = first + k
            # the scene numbers were checked on rek_okehazama_zenya (8 scenes match the text, 🟡 for the others)
            rows.append([cg, kind, k, im.width, im.height, file, f"Grp/{name} {2 * k},{2 * k + 1}",
                         " ".join(sorted(used.get(cg, ()))), "✅ cross" if kind == "rekishi" else "🟡"])
    _csv(os.path.join(out, "eventcg", "index.csv"),
         ["scene", "set", "index", "width", "height", "file", "source", "used_by", "evidence"], rows)
    return len(rows)


def kamon(game_dir, out):
    """456 sprites: the 228 家紋 at 16x16, then the same 228 at 12x12"""
    os.makedirs(os.path.join(out, "kamon"), exist_ok=True)
    ims = list(f11n_sprites(os.path.join(game_dir, "Grp", "kamon.n12")))
    half = len(ims) // 2
    for k, im in enumerate(ims):
        im.save(os.path.join(out, "kamon", f"{k % half:03d}{'-small' if k >= half else ''}.png"))
    return half


def _kind(name):
    return next((k for p, k in KINDS_OF_FILE if name.startswith(p)), "その他")


def events(game_dir, out):
    """one JSONL record per N12F script (all Msg/*.n12 but 列伝 and 家宝) -> out/events/events.jsonl"""
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    n = 0
    with open(os.path.join(out, "events", "events.jsonl"), "w", encoding="utf-8") as f:
        for name, (boxes, steps, strings) in _scripts(game_dir):
            scenes = [int(a[-1]) for fn, a in steps if fn == CG_CALL]
            f.write(json.dumps({"file": f"Msg/{name}.n12", "kind": _kind(name), "scenes": scenes, "boxes": boxes,
                                "steps": steps, "strings": strings}, ensure_ascii=False) + "\n")
            n += 1
    return n


@click.command("nobu12-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam files (games/nobu12pk-win)")
@click.option("--out", required=True, type=click.Path(), help="output directory (games/nobu12pk-win/extract)")
def nobu12_extras(game_dir, out):
    """信長の野望・革新 PK: event pictures, 家宝, 特産品, 家紋 and event scripts."""
    click.echo(f"items: {items(game_dir, out)}")
    click.echo(f"eventcg: {eventcg(game_dir, out)}")
    click.echo(f"kamon: {kamon(game_dir, out)}")
    click.echo(f"events: {events(game_dir, out)}")
