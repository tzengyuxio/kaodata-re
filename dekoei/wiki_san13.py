"""三國志13 with PK (san13pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list. Names are the
繁中 ones (string table of PK item 1416), the Japanese ones (PK item 2) go to nameJa. Fields and evidence:
notes/san13.md「koei-wiki 匯出：人物」, notes/san-attributes.md「三國志13」.

    ../.venv/bin/python wiki_san13.py --game-dir ../games/san13pk-win   # writes extract/tables/scenarios.csv

The people are the kaodata san13pk-win characters: persons with pictures, minus the role records
(kaodata_export.SAN13PK_WIN_ROLES) and the nameless 古武將; id = person number (row of the person tables).

Person data comes from two layouts. PK item 941 (scenario_bs, the editor's base data) item 6: 307 columns, the
fixed attributes (SAN13 below). PK items 942-952 (scenario_00-10, the 11 scenarios in menu order) item 6: 275
columns, the scenario state (SCEN below); item 0 is the header (col0 scenario number, col6 year), item 5 the forces
(row = force, col0 255 unused, col1 ruler). Items 992-1030 (scenario_50-88) are the 英傑伝 stages, not exported.
"""
import csv
import os

import click
from PIL import Image

import sango
from kaodata_export import SAN13PK_WIN_ROLES, kana_to_hiragana
import struct
from places_export import _gaiji
import kaodata_export as K
from wiki_stats import _pick
from biography import split_marked

SCENARIOS = range(942, 953)
BASE = 941
NAMES_JA, NAMES_TC = sango.SAN13_NAMES, sango.SAN13_NAMES_TC
TITLES = 4  # string 4 + scenario number: the title
# 941 item 6 columns: 0 属性, 1 性別, 6 生年, 7 登場年, 8 没年, 9 病死, 10-13 統率 武力 知力 政治, 14-16 適性 (0-3 =
# C-S), 17 戦法 (-1 none), 18 重臣特性 (255 none), 19 相性 (i8, read as u8), 20 一門 (the head's person number), 21
# 父親, 22 母親, 23 性格, 24-27 武具 書物 宝物 酒興味, 28 物欲, 33 配偶者, 36 義兄 (the eldest), 38 義理, 40 勇愛,
# 42 才愛
APTITUDE = ["槍兵", "騎兵", "弓兵"]
GRADES = "CBAS"
TACTICS = 18403, 141  # Japanese strings: 戦法 names (呂布 0 天下無双, 関羽 2 軍神)
TRAITS = 20443, 17  # 重臣特性 names (諸葛亮 0 神算鬼謀, 関羽 14 槍術調練)
SKILLS = 16707, 20  # 特技 names, 商業 … 鬼謀
TEMPERS = 20620  # 小心 冷静 豪胆 猪突
INTERESTS = ["武具興味", "書物興味", "宝物興味", "酒興味"]
# 942-952 item 6 columns: 13 status (STATUS), 14 96-120 for officers (not 忠誠, which is 0-100; not exported), 17 force (255 none), 18 place (places export id, 255
# none), 25-64 20 pairs (特技 k or 255, value) — the same in every scenario
STATUS = 20626  # 未登場 未発見 在野 現役 捕虜 死亡 特殊 イベント = codes 0-7
ACTIVE = 3


def _strings(game_dir, item, enc, gaiji={}):
    return sango.san13_strings(sango.san13_items(sango.san13_items(sango.san13_entry(game_dir, item))[0])[0], enc,
                               gaiji)


def _table(game_dir, entry, sub):
    return _xl_rows(sango.san13_unzip(sango.san13_items(sango.san13_entry(game_dir, entry))[sub]))


def scenarios(game_dir):
    """[(number, file, title, titleZh, year, {force: ruler}, person table)]"""
    ja, tc = _strings(game_dir, NAMES_JA, "cp932"), _strings(game_dir, NAMES_TC, "cp950", sango.SAN13_GAIJI_TC)
    out = []
    for n, e in enumerate(SCENARIOS, 1):
        header = _table(game_dir, e, 0)[0]
        assert header[0] == n - 1 and header[1] == 0, e
        rulers = {f: r[1] for f, r in enumerate(_table(game_dir, e, 5)) if r[0] != 255}
        out.append((n, f"pk/data/scenario/scenario_{n - 1:02d}.bin.zp", ja[TITLES + n - 1], tc[TITLES + n - 1],
                    header[6], rulers, _table(game_dir, e, 6)))
    return out


def _places():
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "export", "koei-wiki", "places", "san13pk-win.jsonl")
    with open(path, encoding="utf-8") as f:
        return {json.loads(line)["id"] for line in f}


def persons(game_dir):
    data = sango.load_san13_persons(game_dir)
    people = sorted(p for p, (name, _, _) in data["names"].items() if name and p not in SAN13PK_WIN_ROLES)
    ids = set(people)
    ja = _strings(game_dir, NAMES_JA, "cp932")
    tc = _strings(game_dir, NAMES_TC, "cp950", sango.SAN13_GAIJI_TC)
    start, run = sango.SAN13_NAME_FIELDS
    base = _table(game_dir, BASE, 6)
    scens = scenarios(game_dir)
    places = _places()
    first = scens[0][6]
    status = ja[STATUS:STATUS + 8]
    sworn, children = {}, {}
    for p in people:
        r = base[p]
        if r[36] in ids:
            sworn.setdefault(r[36], []).append(p)
        for c in (21, 22):
            if r[c] in ids:
                children.setdefault(r[c], []).append(p)
    rows = []
    for p in people:
        r = base[p]
        name_ja, name, reading = data["names"][p]
        row = {"id": p, "name": name}
        if name != name_ja:
            row["nameJa"] = name_ja
        courtesy = tc[start + 2 * run + p]
        if courtesy:
            row["courtesy"] = courtesy
        row["reading"] = kana_to_hiragana(reading)
        row["born"], row["debut"], row["died"] = r[6], r[7], r[8]
        row["stats"] = dict(zip(sango.SAN13_STATS, r[10:14]))
        row["more"] = {"性別": "女" if r[1] else "男"}
        hidden = {"相性": r[19] & 0xFF, "性格": ja[TEMPERS + r[23]] if r[23] < 4 else r[23]}
        hidden.update(zip(INTERESTS, r[24:28]))
        hidden.update({"物欲": r[28], "義理": r[38], "勇愛": r[40], "才愛": r[42], "属性": r[0], "病死": r[9]})
        row["hidden"] = hidden
        if r[14] != 255:  # 255: 霊帝, 献帝, 華佗, 左慈 … (no troops)
            row["aptitude"] = {a: GRADES[v] for a, v in zip(APTITUDE, r[14:17])}
        skills, values = {}, {}
        if 0 <= r[17] < TACTICS[1]:
            skills["戦法"] = [ja[TACTICS[0] + r[17]]]
        if r[18] < TRAITS[1] and ja[TRAITS[0] + r[18]]:
            skills["重臣特性"] = [ja[TRAITS[0] + r[18]]]
        for k in range(SKILLS[1]):
            s, v = first[p][25 + 2 * k:27 + 2 * k]
            if s != 255:
                assert s == k, (p, k)
                values[ja[SKILLS[0] + k]] = v
        if values:
            skills["特技"] = list(values)
        if skills:
            row["skills"] = skills
        if values:
            row["game"] = {"特技値": values}
        rel = {}
        for key, c in (("father", 21), ("mother", 22), ("spouse", 33)):
            if r[c] in ids:
                rel[key] = [r[c]]
        if p in children:
            rel["children"] = sorted(children[p])
        group = sworn.get(r[36], [])
        if len(group) > 1:
            rel["sworn"] = sorted(x for x in group if x != p)
        if r[20] in ids:
            rel["clan"] = r[20]
        if rel:
            row["relations"] = rel
        row["scenarios"] = []
        for n, _, _, _, year, rulers, table in scens:
            s = table[p]
            code, force, place = s[13], s[17], s[18]
            e = {"scenario": n, "year": year, "status": status[code]}
            if code == ACTIVE:
                ruler = rulers[force]
                if ruler == p:
                    e["status"] = "君主"
                elif ruler in ids:
                    e["lord"] = ruler
            else:
                assert force == 255, (p, n)
            if place in places and code != 5:  # 死亡 keeps a place
                e["location"] = place
            if code == 0:
                e["debut"] = r[7]
            row["scenarios"].append(e)
        row["uncertain"] = ["aptitude", "skills", "game.特技値", "hidden", "relations"]
        if any(e["status"] not in ("君主", "現役", "未登場", "死亡") for e in row["scenarios"]):
            row["uncertain"].append("scenarios.status")
        rows.append(row)
    return rows


@click.command()
@click.option("--game-dir", "game_dir", required=True)
def main(game_dir):
    """寫 <game-dir>/extract/tables/scenarios.csv（劇本號、檔名、標題（日、繁中）、年、各勢力的君主）"""
    names = sango.load_san13_persons(game_dir)["names"]
    out = os.path.join(game_dir, "extract", "tables", "scenarios.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "name", "nameZh", "year", "rulers"])
        for n, file, title, title_zh, year, rulers, _ in scenarios(game_dir):
            w.writerow([n, file, title, title_zh, year, " ".join(names[r][0] for f, r in sorted(rulers.items()))])
    print(out)


if __name__ == "__main__":
    main()


##############################################################################
# 三國志13 PK: names are strings 210 + id of the string tables (item 0 of item 0 of PK item 2, Japanese; 1416,
# Traditional Chinese); positions in node.stgn (PK item 450: 20-byte records, u16 id, x, y at +4, +8). XL
# tables of PK item 941: 1 cities (col 0 地方, col 1 州, cols 3-9 neighbours, col 10 itself), 2 関, 3 縣級地點 (col 1 id, cols
# 2-5 related cities), 22 battle numbers (col 18 stage: 0-15 btl_CSL, 16-26 btl_FLD, 27 btl_RIV, 28 btl_GAT). 14
# 州 names are strings 5222-5235. Field battles pick their map by the region code under the unit, not by place.
SAN13_REGIONS = ["河北", "中原", "西北", "巴蜀", "荊楚", "吳越"]


SAN13_STAGES = [f"btl_CSL_{i:02d}" for i in range(16)] + [f"btl_FLD_{i:02d}" for i in range(11)] + \
    ["btl_RIV_00", "btl_GAT_00"]


SAN13_PLACE_GAIJI_TC = {b"\xfa\x70": "坂"}  # 長坂 (the Japanese name)


_XL = {0: "I", 1: "i", 2: "h", 3: "B", 4: "i", 5: "H", 6: "b", 7: "f"}


def _xl_rows(b):
    _, _, cols, rows, size, header = struct.unpack_from("<6H", b, 2)
    fmt = "<" + "".join(_XL[t] for t in b[0x10:0x10 + cols])
    assert struct.calcsize(fmt) == size
    return [struct.unpack_from(fmt, b, header + r * size) for r in range(rows)]


# 全國地圖 (world/ground.png and ground-autumn / -winter.png): texture 1 of ground_<season>.g1t.zp (PK items 487,
# 495, 499; summer 491 is the same bytes as spring), the 4096 x 4096 ground colour of the 3D map seen from above,
# cropped to SAN13_CROP and halved. It shares its texture space with the place-id map (item 486 texture 2): the
# coastlines and borders line up with no offset. node.stgn's world position (x, y) is at (SAN13_TEX[0] x + SAN13_TEX[1],
# SAN13_TEX[2] y + SAN13_TEX[3]) on both, fitted so that all 266 places fall in their own id area (🟡 fitted).
SAN13_TEX = (0.00557924, -9.8, 0.007169, -7.0)
SAN13_CROP = (480, 640, 3680, 3600)
SAN13_GROUND = {"": 487, "-autumn": 495, "-winter": 499}
SAN13_PLACE_IDS = 486


def san13_texture_pos(x, y):
    """node.stgn world position -> pixel on the 4096 x 4096 ground textures."""
    a, b, c, d = SAN13_TEX
    return a * x + b, c * y + d


def world_check(game_dir, rows):
    """Each place's world position falls in its own area of the place-id map (id = (B - 2) / 5 * 50 + (G - 2) / 5)."""
    import san13_extras
    from gfx import gt1g_texture
    pk = san13_extras.Container(game_dir, "pk/DATA0.S13", "pk/DATA1.S13")
    px = gt1g_texture(pk[SAN13_PLACE_IDS], 2).convert("RGB").load()
    bad = []
    for r in rows:
        x, y = san13_texture_pos(r["game"]["座標"]["x"], r["game"]["座標"]["y"])
        c = px[round(x), round(y)]
        if (c[2] - 2) // 5 * 50 + (c[1] - 2) // 5 != r["id"]:
            bad.append(f"{r['id']}: world position not in its area")
    return len(rows), bad


def places(game_dir, out_dir):
    import san13_extras
    from gfx import gt1g_texture
    pk = san13_extras.Container(game_dir, "pk/DATA0.S13", "pk/DATA1.S13")
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    for suffix, item in SAN13_GROUND.items():
        im = gt1g_texture(pk[item], 1).convert("RGB").crop(SAN13_CROP)
        im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(os.path.join(out_dir, "world", f"ground{suffix}.png"))
    mw, mh = (SAN13_CROP[2] - SAN13_CROP[0]) // 2, (SAN13_CROP[3] - SAN13_CROP[1]) // 2

    def strings(item, enc, gaiji):
        return sango.san13_strings(sango.san13_items(sango.san13_items(sango.san13_entry(game_dir, item))[0])[0], enc,
                                   gaiji)

    tc = strings(sango.SAN13_NAMES_TC, "cp950", {**sango.SAN13_GAIJI_TC, **SAN13_PLACE_GAIJI_TC})
    jp = strings(sango.SAN13_NAMES, "cp932", {})
    # The Japanese names' gaiji (U+E0xx) read off the Chinese name of the same place, where both are as long
    gaiji = {}
    for i in range(210, 710):
        if len(jp[i]) == len(tc[i]):
            for c, d in zip(jp[i], tc[i]):
                if 0xE000 <= ord(c) < 0xF900:
                    assert gaiji.setdefault(ord(c), d) == d
    guessed = {i - 210 for i in range(210, 710) if len(jp[i]) != len(tc[i]) and any(ord(c) in gaiji for c in jp[i])}
    jp = [_gaiji(x, gaiji) for x in jp]
    tables = sango.san13_items(sango.san13_entry(game_dir, 941))
    cities, gates, counties, battles = (_xl_rows(sango.san13_unzip(tables[k])) for k in (1, 2, 3, 22))
    node = sango.san13_entry(game_dir, 450)
    n = struct.unpack_from("<I", node, 8)[0]
    pos = {}
    for i in range(n):
        pid, _, _, x, y = struct.unpack_from("<HBBII", node, 0x10 + 20 * i)
        pos[pid] = (x, y)
    states = [tc[5222 + i] for i in range(14)]
    county = {r[1]: r for r in counties if r[1] >= 0}
    gate_battle = {360 + i: gates[i][0] for i in range(len(gates))}
    rows = []
    for pid in range(500):
        name, name_ja = tc[210 + pid] if 210 + pid < len(tc) else "", jp[210 + pid] if 210 + pid < len(jp) else ""
        if not name and not name_ja:
            continue
        row = {"id": pid, "name": name or name_ja}
        notes, uncertain = [], []
        if name_ja and name_ja != row["name"]:
            row["nameJa"] = name_ja
            if pid in guessed:
                uncertain.append("nameJa")
                notes.append("日文版的名稱和繁中版不同，其中的外字是照別的地點的繁中名對出來的。")
        if pid < 60:
            row["level"] = "都市"
            row["region"], row["province"] = SAN13_REGIONS[cities[pid][0]], states[cities[pid][1]]
            row["adjacent"] = [c for c in cities[pid][3:10] if c < 60]
            notes.append(f"攻城圖是 {SAN13_STAGES[battles[pid][18]]}（3D，沒有輸出圖）。")
        elif pid < 300:
            row["level"] = "縣級地點"
            uncertain.append("level")
            notes.append("遊戲裡這類地點的稱呼沒找到，「縣級地點」是這邊的分類。")
            related = [c for c in county[pid][2:6] if c != 255] if pid in county else []
            if related:
                row["parentCity"] = related[0]
                uncertain.append("parentCity")
                notes.append("parentCity 取相關都市的第一個（推定是所屬）；相關都市："
                             + "、".join(tc[210 + c] for c in related) + "。")
        elif 360 <= pid < 380:
            row["level"] = "關"
            notes.append(f"關的戰場圖是 {SAN13_STAGES[battles[gate_battle[pid]][18]]}，8 關共用（3D，沒有輸出圖）。")
        elif 380 <= pid < 460:
            row["level"] = "港" if row["name"].endswith("港") else "渡口"
        else:
            row["level"] = "沖" if row["name"].endswith("沖") else "地點"
            if row["level"] == "地點":
                uncertain.append("level")
                notes.append("「地點」是這邊的分類（官渡、開封這類，遊戲裡的稱呼沒找到）。")
        if pid in pos:
            tx, ty = san13_texture_pos(*pos[pid])
            row["pos"] = {"x": round((tx - SAN13_CROP[0]) / 2), "y": round((ty - SAN13_CROP[1]) / 2), "grid": "pixel",
                          "w": mw, "h": mh}
            row["game"] = {"座標": {"x": pos[pid][0], "y": pos[pid][1]}}
        if uncertain:
            row["uncertain"] = uncertain
        notes.append("野戰看部隊所在位置的地域碼選圖，不看地點；水戰另有一張。game.座標是 node.stgn 的世界座標；pos 是它在全國地圖 world/ground.png（3D 大地圖的地面貼圖，從上往下看）上的像素，換算係數是擬合的。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def stats(game_dir):
    data = sango.load_san13_persons(game_dir)
    chars = {p: data["names"][p][0] for p in data["pictures"]
             if p not in K.SAN13PK_WIN_ROLES and data["names"][p][0]}
    return _pick(sango.load_san13_stats(game_dir), sango.SAN13_STATS, chars)


# 三國志13 PK: the biography of person n is string 15235 + n (6535 + 6 x 1450) of the name table, Big5 in item 1416.
# "summary\n ESC C4 <icon> ESC R 演義 \n ESC C2 <icon> ESC R 史實"; ESC R is also followed by digits of the text.
# The icons are FA60 then FA49, swapped in 27 of the added persons (1151-) whose first section is still 演義 (無記述
# for people only in the histories), so the sections go by order. The 古武將 (850-898) have one section. Gaiji (FAxx) besides the names' own: 坂 (長坂坡) and 𩅦 (孫𩅦, the
# Japanese text writes 孫［ソンワン］)
SAN13_BIO = sango.SAN13_NAME_FIELDS[0] + 6 * sango.SAN13_NAME_FIELDS[1]


SAN13_BIO_GAIJI = {0xFA40: "伷", 0xFA41: "璝", 0xFA44: "𩅦", 0xFA45: "儁", 0xFA70: "坂"}


SAN13_MARKS = {b"\x1bC4\xfa\x60\x1bR", b"\x1bC2\xfa\x49\x1bR", b"\x1bC4\xfa\x49\x1bR", b"\x1bC2\xfa\x60\x1bR"}


def san13_big5(b: bytes) -> str:
    """Big5 text with the game's gaiji; the section marks become \0."""
    out, i = [], 0
    while i < len(b):
        mark = next((m for m in SAN13_MARKS if b.startswith(m, i)), None)
        if mark:
            out.append("\0")
            i += len(mark)
        elif b[i] >= 0x81:
            code = b[i] << 8 | b[i + 1]
            out.append(SAN13_BIO_GAIJI.get(code) or b[i:i + 2].decode("cp950"))
            i += 2
        else:
            assert b[i] != 0x1B, b[i:i + 4]
            out.append(chr(b[i]))
            i += 1
    return "".join(out)


def san13_raw_strings(b: bytes) -> list[bytes]:
    rows, size, header = struct.unpack_from("<3H", b, 8)
    out = []
    for r in range(rows):
        o = header + struct.unpack_from("<I", b, header + r * size)[0]
        out.append(b[o:b.index(b"\0", o)])
    return out


def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    item = sango.san13_items(sango.san13_items(sango.san13_entry(game_dir, sango.SAN13_NAMES_TC))[0])[0]
    strings = san13_raw_strings(item)
    out = {}
    for n in range(sango.SAN13_NAME_FIELDS[1]):
        if strings[SAN13_BIO + n]:
            out[n] = split_marked(san13_big5(strings[SAN13_BIO + n]))
    return out


def bio_names(game_dir) -> dict[int, str]:
    return {p: v[1] for p, v in sango.load_san13_persons(game_dir)["names"].items()}


BIO_LANG = "zh-Hant"  # biography.py: the 列傳 are read from the Chinese release
