"""蒼き狼と白き牝鹿・ジンギスカン (PC-98, 1987): countries, persons, maps and pictures of both scenarios.

`dekoei.py genghis-extras --game-dir ../games/genghis-pc98 --out ../games/genghis-pc98/extract` writes
countries.csv, hexmaps.csv, persons.csv, map/ (MMAP, SMAP and the labelled copies) and pictures/ (PACDATA, PICDATA,
ENDDATA, OPEN). The Chinese names come from the DOS MDATA.CIM / SDATA.CIM in `dos/`. Format and evidence:
notes/genghis.md「國與大地圖」「人物欄位」「事件、插圖、道具」.

MDATA.CIM (蒙古篇) / SDATA.CIM (世界篇) are loaded at DS:0x36 of MAIN.EXE (DGROUP 0x1CE9), so DS = file + 0x36.
"""
import csv
import os
import struct

import click
from PIL import Image, ImageDraw

from koei_games import koei_tw_name, load_genghis_dos_people

SCENARIOS = (("mongol", "MDATA.CIM", "MMAP.PAK", "MHEXMAP.DAT"), ("world", "SDATA.CIM", "SMAP.PAK", "SHEXMAP.DAT"))
GOODS = ["毛皮", "絹", "宝石", "貴金属", "医薬品", "木工品", "陶磁器", "ガラス", "織物", "香料", "食糧"]  # DS:0x4382
UNIT_KINDS = {0: "騎馬", 1: "歩兵", 2: "弓矢"}
COUNTRY_TABLE, COUNTRY_SIZE = 0xC02, 0x53   # DS:0xC38
ADJ_TABLE, ADJ_SIZE = 0x14C4, 14            # DS:0x14FA
LORD_TABLE, LORD_SIZE = 0x1D4, 33           # DS:0x20A
# country record: offset -> field (u16 unless noted); evidence in notes/genghis.md
COUNTRY_FIELDS = [(0x14, "武装度"), (0x16, "訓練度"), (0x18, "兵士"), (0x1A, "経済力"), (0x1C, "町造り"),
                  (0x1E, "城防御度"), (0x20, "城造り"), (0x3A, "特産品作り"), (0x3E, "食料作り"), (0x40, "金"),
                  (0x42, "モラル"), (0x44, "税")] + [(0x22 + 2 * i, g) for i, g in enumerate(GOODS)] + \
                 [(0x38, "+38"), (0x3C, "+3C"), (0x46, "+46")]
# kind -> (offset, groups, group size, records, record size)
PERSON_TABLES = {"ruler": (0x1D4, 1, 0, 27, 33), "family": (0x550, 4, 155, 5, 31), "general": (0x7F3, 1, 0, 26, 23),
                 "son": (0xA4A, 4, 110, 5, 22), "woman": (0x19C6, 1, 0, 40, 24)}
ABILITIES = ["統率力", "判断力", "企画力", "説得力", "体力", "武力"]
PERSONALITY = {0: "気分しだい", 1: "いつでもＯＫ", 2: "絶対拒否"}
STATUS = {0x64: "本国", 0x65: "将軍統治", 0x66: "0x66"}
# the four families (heir and child groups 0-3) of the selectable rulers, by ruler slot 【推】from the names
FAMILY_RULERS = {"mongol": [0], "world": [0, 6, 10, 18]}


def sjis(raw: bytes) -> str:
    return raw.split(b"\0")[0].decode("cp932")


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


# ---------------------------------------------------------------------------------------------------------------
# PAK picture (MAIN.EXE file 0x5908, readers 0x989F / 0x96FA): u16 width, u16 height, then 3 planes (B, R, G) per 8-pixel
# column. Rows 0-1 are literal; later bytes are literal unless 0x96, which is followed by n: n = 1 is a literal 0x96,
# otherwise copy n (0 = 256) bytes from two rows above, counted in (column, plane) order across rows.

def decode_pak(data: bytes, off: int = 0):
    w, h = struct.unpack_from("<HH", data, off)
    bw, pos = w // 8, off + 4
    planes = [bytearray(bw * h) for _ in range(3)]
    rep = 0
    for y in range(h):
        for x in range(bw):
            i = y * bw + x
            for p in range(3):
                if y < 2:
                    planes[p][i] = data[pos]
                    pos += 1
                elif rep:
                    rep -= 1
                    planes[p][i] = planes[p][i - 2 * bw]
                else:
                    b = data[pos]
                    pos += 1
                    if b == 0x96:
                        n = data[pos]
                        pos += 1
                        if n != 1:
                            rep = (n or 256) - 1
                            b = planes[p][i - 2 * bw]
                    planes[p][i] = b
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for xb in range(bw):
            b, r, g = (planes[p][y * bw + xb] for p in range(3))
            for k in range(8):
                m = 0x80 >> k
                px[xb * 8 + k, y] = (255 if r & m else 0, 255 if g & m else 0, 255 if b & m else 0)
    return img, pos - off


def pak_archive(path):
    """Pictures of PACDATA / PICDATA / ENDDATA / OPEN.DAT: each starts on a 512-byte block, picture id = block
    (PICDATA ids have 0x8000 added, MAIN.EXE file 0x96FA)."""
    with open(path, "rb") as f:
        data = f.read()
    off = 0
    while off + 4 <= len(data):
        w, h = struct.unpack_from("<HH", data, off)
        if not w or not h or w % 8 or w > 640 or h > 400:
            off += 512
            continue
        img, used = decode_pak(data, off)
        yield off // 512, img
        off += (used + 511) // 512 * 512


def double(img):
    return img.resize((img.width, img.height * 2), Image.NEAREST)  # 200-line pictures


# ---------------------------------------------------------------------------------------------------------------

def countries(data: bytes, zh_names: list[str]):
    n = data[0x1CF]
    names = [sjis(data[0x3A + 15 * k:0x3A + 15 * k + 15]) for k in range(n)]
    rows = []
    for k in range(n):
        rec = data[COUNTRY_TABLE + COUNTRY_SIZE * k:COUNTRY_TABLE + COUNTRY_SIZE * (k + 1)]
        adj = data[ADJ_TABLE + ADJ_SIZE * k:ADJ_TABLE + ADJ_SIZE * (k + 1)]
        col, row, x, y, goods = struct.unpack_from("<BBHHB", adj)
        ruler = (u16(rec, 0x51) - 0x20A) // LORD_SIZE
        units = [(rec[2 * i], rec[2 * i + 1]) for i in range(10)]
        row_ = {"no": k + 1, "name": names[k], "nameZh": zh_names[k],
                "ruler": sjis(data[LORD_TABLE + LORD_SIZE * ruler:][:15]),
                "neighbours": " ".join(str(b + 1) for b in adj[7:] if b != 0xFF),
                "neighbourNames": "、".join(names[b] for b in adj[7:] if b != 0xFF),
                "特産品": GOODS[goods], "picture": f"PICDATA {u16(data, 4 + 2 * k) & 0x7FFF:#04x}",
                "labelX": x, "labelY": y,
                "人": sum(u16(rec, o) for o in (0x18, 0x1C, 0x20, 0x3A, 0x3E))}
        row_.update({name: u16(rec, off) for off, name in COUNTRY_FIELDS})
        row_.update({"移動比?": rec[0x48], "民?": rec[0x49],
                     "部隊": " ".join(f"{UNIT_KINDS[t]}{p}%" for t, p in units if t != 0xFF)})
        rows.append(row_)
    return rows


def hexmaps(path, scenario, names):
    with open(path, "rb") as f:
        data = f.read()
    rows = []
    for k in range(len(data) // 320):
        for y in range(10):
            for x in range(16):
                t, z = data[320 * k + 16 * y + x], data[320 * k + 160 + 16 * y + x]
                rows.append({"scenario": scenario, "no": k + 1, "name": names[k], "row": y, "col": x,
                             "terrain": t & 0x7F, "flag80": t >> 7, "entryFrom": "" if z == 0xFF else z + 1})
    return rows


def persons(data: bytes, dos, scenario):
    rows = []
    zh = {kind: [n for n, _ in people] for kind, people in dos.items()}
    rulers = [sjis(data[LORD_TABLE + LORD_SIZE * k:][:15]) for k in range(27)]
    for kind, (off, groups, gsize, n, size) in PERSON_TABLES.items():
        seen = 0
        for g in range(groups):
            for i in range(n):
                o = off + g * gsize + i * size
                r = data[o:o + size]
                if not r[0]:
                    continue
                row = {"scenario": scenario, "kind": kind, "group": g if groups > 1 else "", "slot": i,
                       "name": sjis(r[:15]), "nameZh": zh[kind][seen]}
                seen += 1
                if groups > 1:
                    fam = FAMILY_RULERS[scenario]
                    row["family"] = rulers[fam[g]] if g < len(fam) else ""
                if kind in ("ruler", "family"):
                    row["年齢"] = r[15]
                    row.update({a: u16(r, 16 + 2 * j) for j, a in enumerate(ABILITIES)})
                    row["+28"] = r[28]
                    row["face"] = f"{u16(r, 29):04X}"
                    if kind == "ruler":
                        row["国"] = r[31] + 1
                        row["状態"] = STATUS.get(r[32], r[32])
                elif kind == "general":
                    row.update({"年齢": r[15], "基本能力値": u16(r, 16), "血縁値": r[18], "存在": u16(r, 19),
                                "face": f"{u16(r, 21):04X}"})
                elif kind == "son":
                    row.update({"年齢": r[15], "基本能力値": u16(r, 16), "男子": r[18], "+19": r[19],
                                "face": f"{u16(r, 20):04X}"})
                else:
                    row.update({"性格": PERSONALITY.get(r[15], r[15]), "所属": "" if r[16] == 0xFF else r[16],
                                "回数": r[17], "face": " ".join(f"{u16(r, 18 + 2 * j):04X}" for j in range(3))})
                rows.append(row)
    return rows


def places(game_dir, out_dir):
    """koei-places/1 rows (places_export): the countries of both scenarios. The 蒙古篇 and 世界篇 are two maps with
    their own countries, so 世界篇 keeps the game's number and 蒙古篇 gets 100 + number. name is the Chinese DOS
    spelling, nameJa the PC-98 one; pos is the country's number label on world/<map>.png (MAIN.EXE draws the map
    at x = 256 on a 200-line screen, so x - 256 and y doubled)."""
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    rows = []
    for scenario, cim, pak, _ in SCENARIOS:
        with open(os.path.join(game_dir, cim), "rb") as f:
            data = f.read()
        with open(os.path.join(game_dir, "dos", cim), "rb") as f:
            dos_data = f.read()
        zh = [koei_tw_name(dos_data[0x3A + 25 * k:0x3A + 25 * k + 25].split(b"\0")[0]) for k in range(data[0x1CF])]
        with open(os.path.join(game_dir, pak), "rb") as f:
            img, _ = decode_pak(f.read())
        img = double(img)
        img.save(os.path.join(out_dir, "world", f"{scenario}.png"))
        base = 100 if scenario == "mongol" else 0
        stage = "蒙古篇" if scenario == "mongol" else "世界篇"
        for r in countries(data, zh):
            row = {"id": base + r["no"], "name": r["nameZh"]}
            if r["name"] != r["nameZh"]:
                row["nameJa"] = r["name"]
            row["level"] = "國"
            row["adjacent"] = [base + int(n) for n in r["neighbours"].split()]
            row["pos"] = {"x": r["labelX"] - 256 + 6, "y": r["labelY"] * 2 + 7, "grid": "pixel",
                          "w": img.width, "h": img.height}
            notes = f"{stage}（`world/{scenario}.png`）；pos 是地圖上國號標籤的中心"
            if r["name"] == "ムワッヒド朝":
                notes += "；中文版寫成「倭馬亞王朝」（伍麥亞王朝，另一個王朝），照遊戲原文"
            row["notes"] = notes
            rows.append(row)
    return rows

def write_csv(path, rows):
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(rows)


@click.command(help="ジンギスカン（PC-98）的國、人物、大地圖與圖片")
@click.option("--game-dir", required=True, help="PC-98 遊戲目錄（另需 dos/ 的中文版 MDATA.CIM、SDATA.CIM）")
@click.option("--out", required=True, help="輸出目錄")
def genghis_extras(game_dir, out):
    os.makedirs(os.path.join(out, "map"), exist_ok=True)
    os.makedirs(os.path.join(out, "pictures"), exist_ok=True)
    all_countries, all_hex, all_persons = [], [], []
    for scenario, cim, pak, hexf in SCENARIOS:
        with open(os.path.join(game_dir, cim), "rb") as f:
            data = f.read()
        dos_path = os.path.join(game_dir, "dos", cim)
        with open(dos_path, "rb") as f:
            dos_data = f.read()
        zh = [koei_tw_name(dos_data[0x3A + 25 * k:0x3A + 25 * k + 25].split(b"\0")[0]) for k in range(data[0x1CF])]
        rows = countries(data, zh)
        all_countries += [{"scenario": scenario, **r} for r in rows]
        all_hex += hexmaps(os.path.join(game_dir, hexf), scenario, [r["name"] for r in rows])
        all_persons += persons(data, load_genghis_dos_people(dos_path), scenario)
        with open(os.path.join(game_dir, pak), "rb") as f:
            img, _ = decode_pak(f.read())
        double(img).save(os.path.join(out, "map", pak.replace(".PAK", ".png")))
        lab = double(img)
        draw = ImageDraw.Draw(lab)
        for r in rows:  # label positions are screen pixels; the map is drawn at x = 256 (MAIN.EXE file 0x989F)
            x, y = r["labelX"] - 256, r["labelY"] * 2
            draw.rectangle((x - 1, y - 1, x + 13, y + 15), fill=(0, 0, 0))
            draw.text((x + 1, y + 2), str(r["no"]), fill=(255, 255, 0))
        lab.save(os.path.join(out, "map", pak.replace(".PAK", "-labelled.png")))
    write_csv(os.path.join(out, "countries.csv"), all_countries)
    write_csv(os.path.join(out, "hexmaps.csv"), all_hex)
    write_csv(os.path.join(out, "persons.csv"), all_persons)
    count = 0
    for name in ("PACDATA.DAT", "PICDATA.DAT", "ENDDATA.DAT", "OPEN.DAT"):
        for block, img in pak_archive(os.path.join(game_dir, name)):
            double(img).save(os.path.join(out, "pictures", f"{name[:-4]}_{block:03x}.png"))
            count += 1
    click.echo(f"{len(all_countries)} countries, {len(all_persons)} persons, {count} pictures -> {out}")
