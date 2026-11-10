"""三國志12 with PK (san12pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list.

The persons are the kaodata characters (kaodata_export.build_san12pk_win): the named records of PK/Scenario/Scenario0.dat
minus the 60 title slots (文官, 兵士, 山賊将…, faces SAN12PK_WIN_ROLE_FACES), 770 people, id = record id. Records are
292-byte bit fields read as one little-endian integer ("bit n"); field names follow the cp950 field-name list of the
繁中版 San12WPK.exe (0x1a57b2c–0x1a57c8c: 所屬勢力 基礎忠誠 位階 相性武將 軍團長 … 義兄 勇猛 死因 卒年 生年 登場年 性別
血緣 所在都市), evidence per field in notes/san12.md「koei-wiki 匯出：人物」. Names are the 繁中版's (Steam depot 628082,
san12_extras.bio_names), the Japanese ones go to nameJa.

The scenarios are the 17 of PK/Scenario (1–15, 20, 21; Scenario0 is the master copy, not playable); the PK set
contains the base game's scenarios, so there is no separate base list. Their number is the header byte +0 (= the
file number).

    persons(game_dir) -> [row]          (persons_export.py; reads ZH_DIR too)
    scenarios_csv(game_dir, path)       the 17 scenarios: number, file, titles, year, rulers
"""
import csv
import os
import struct

import sango
from kaodata_export import SAN12PK_WIN_ROLE_FACES, kana_to_hiragana

SCENARIOS = [*range(1, 16), 20, 21]
MASTER = 0  # Scenario0: the values the stats export uses
SIZE = 292
ZH_DIR = os.path.join("..", "steam", "628080-tchinese", "depot")  # relative to game_dir
# part type ids (part 0 of the ILNK container lists them)
HEADER, FORCES, CORPS, CITIES, PERSONS = 0x95, 0x85, 0x87, 0x82, 0x92
NONE = 0x7FF
# person bit fields (offset, width)
FORCE, CITY = (1866, 6), (1873, 6)  # 63 = none
LOYALTY = (1824, 8)
SEX, BORN, DEBUT, DIED = (480, 1), (512, 10), (522, 10), (532, 10)
CLAN, FATHER, MOTHER = (1280, 11), (1292, 11), (1312, 11)
SPOUSES = [(1344, 11), (1376, 11), (1408, 11)]
SWORN = (1440, 11)  # the eldest brother; he points to himself
LIKED = [(b, 11) for b in (1472, 1504, 1536, 1568)]
DISLIKED = [(b, 11) for b in (1632, 1664, 1696, 1728)]
HIDDEN = {"相性": (1263, 8), "義理": (1813, 3)}
SKILLS = "商才 耕作 名士 兵心 練兵 収集 人脈 監視 補修 弁舌 豪傑 一騎 神速 水練 遠射 攻城 兵器 冷静 鬼謀 軍師".split()
UNITS = ["槍兵", "騎兵", "弓兵", "固有"]


def _bits(v, field):
    b, w = field
    return v >> b & ((1 << w) - 1)


def _parts(path):
    """{part type: decrypted bytes} of a Scenario*.dat"""
    with open(path, "rb") as f:
        d = f.read()
    assert d[:4] == b"ILNK"
    n = struct.unpack_from("<I", d, 4)[0]
    offs = list(struct.unpack_from(f"<{n}I", d, 8)) + [len(d)]
    types = struct.unpack_from(f"<{n - 1}I", d, offs[0])
    return {t: sango.san12_decrypt(d[offs[i + 1]:offs[i + 2]]) for i, t in enumerate(types)}


def _records(part, size):
    return [int.from_bytes(part[k:k + size], "little") for k in range(0, len(part), size)]


def _scenario(game_dir, n):
    """year, title (ja), [person int], {force: ruler}, {corps leader}, {city governor}"""
    p = _parts(os.path.join(game_dir, "PK", "Scenario", f"Scenario{n}.dat"))
    h = p[HEADER]
    assert h[0] == n
    year = struct.unpack_from("<I", h, 0)[0] >> 12 & 0x3FF
    year = year - 0x400 if year & 0x200 else year  # 戦国七雄: 246 BC
    title = h[4:25].split(b"\0")[0].decode("cp932")
    rulers = {k: _bits(v, (14, 11)) for k, v in enumerate(_records(p[FORCES], 84)) if _bits(v, (14, 11)) != NONE}
    corps = {_bits(v, (7, 11)) for v in _records(p[CORPS], 800)} - {NONE}
    governors = {_bits(v, (967, 11)) for v in _records(p[CITIES], 248)} - {NONE}
    return year, title, _records(p[PERSONS], SIZE), rulers, corps, governors


def _zh_titles(game_dir):
    out = []
    for n in SCENARIOS:
        h = _parts(os.path.join(game_dir, ZH_DIR, "PK", "Scenario", f"Scenario{n}.dat"))[HEADER]
        out.append(h[4:25].split(b"\0")[0].decode("cp950"))
    return out


def _people(game_dir):
    """the kaodata characters: [(id, ja name, kana)]"""
    ja = sango.load_san12_persons(os.path.join(game_dir, "PK", "Scenario", f"Scenario{MASTER}.dat"), SIZE)
    return [p for p in ja if p["name"] and p["face"] not in SAN12PK_WIN_ROLE_FACES]


def persons(game_dir):
    import san12_extras
    zh = san12_extras.bio_names(os.path.join(game_dir, ZH_DIR))
    people = _people(game_dir)
    ids = {p["id"] for p in people}
    master = _scenario(game_dir, MASTER)[2]
    data = [_scenario(game_dir, n) for n in SCENARIOS]
    raw = sango.san12_person_part(os.path.join(game_dir, "PK", "Scenario", f"Scenario{MASTER}.dat"), SIZE)

    def ref(v, field):
        x = _bits(v, field)
        return x if x in ids else None

    fathers = {k: ref(master[k], FATHER) for k in ids}
    mothers = {k: ref(master[k], MOTHER) for k in ids}
    eldest = {k: ref(master[k], SWORN) for k in ids}
    sworn = {}
    for k, e in eldest.items():
        if e is not None:
            sworn.setdefault(e, set()).add(k)

    rows = []
    for p in people:
        k, r = p["id"], master[p["id"]]
        b = raw[k * SIZE:(k + 1) * SIZE]
        row = {"id": k, "name": zh.get(k, p["name"])}
        if row["name"] != p["name"]:
            row["nameJa"] = p["name"]
        if p["kana"]:
            row["reading"] = kana_to_hiragana(p["kana"])
        born, died, debut = _bits(r, BORN), _bits(r, DIED), _bits(r, DEBUT)
        if born:
            row["born"], row["died"], row["debut"] = born, died, debut
        row["stats"] = dict(zip(sango.SAN12_STATS, b[68:72]))
        row["more"] = {"性別": "女" if _bits(r, SEX) else "男", "兵科": UNITS[b[0x48] & 3]}
        row["hidden"] = {label: _bits(r, f) for label, f in HIDDEN.items()}
        skills = [s for i, s in enumerate(SKILLS) if struct.unpack_from("<I", b, 0x4C + 4 * i)[0]]
        if skills:
            row["skills"] = {"特技": skills}
        notes = ["能力、特技、隱藏值與關係取 Scenario0（各劇本相同的母本）；姓名取繁中版，nameJa 是日文版。"]
        if not born:
            notes.append("沒有生年、登場年、沒年與能力（只當親屬引用的人）。")

        rel = {}
        if fathers[k] is not None:
            rel["father"] = [fathers[k]]
        if mothers[k] is not None:
            rel["mother"] = [mothers[k]]
        children = sorted(j for j in ids if fathers[j] == k or mothers[j] == k)
        if children:
            rel["children"] = children
        sib = sorted(j for j in ids if j != k and (fathers[k] is not None and fathers[j] == fathers[k]
                                                    or mothers[k] is not None and mothers[j] == mothers[k]))
        if sib:
            rel["siblings"] = sib
        spouses = [x for x in (ref(r, f) for f in SPOUSES) if x is not None]
        spouses += [j for j in ids if j not in spouses and k in (ref(master[j], f) for f in SPOUSES)]
        if spouses:
            rel["spouse"] = sorted(spouses)
        if eldest[k] is not None and len(sworn[eldest[k]]) > 1:
            rel["sworn"] = sorted(sworn[eldest[k]] - {k})
        if ref(r, CLAN) is not None:
            rel["clan"] = _bits(r, CLAN)
        if rel:
            row["relations"] = rel
        for label, fields in (("親愛武將", LIKED), ("厭惡武將", DISLIKED)):
            xs = [x for x in (ref(r, f) for f in fields) if x is not None]
            if xs:
                notes.append(f"{label}：{'、'.join(zh.get(x, x) for x in xs)}。")

        scen = []
        for n, (year, _, recs, rulers, corps, governors) in zip(SCENARIOS, data):
            x = recs[k]
            force, city = _bits(x, FORCE), _bits(x, CITY)
            if city == 63:
                continue  # not in this scenario (dead, or a person of another scenario)
            e = {"scenario": n, "year": year}
            if force != 63:
                lord = rulers[force]
                e["status"] = ("君主" if k == lord else "都督" if k in corps else "太守" if k in governors else "一般")
                e["lord"], e["location"] = lord, city
                if k != lord:
                    e["loyalty"] = _bits(x, LOYALTY)
            elif _bits(x, DEBUT) <= year:
                e["status"], e["location"] = "在野", city
            else:
                e["status"], e["debut"] = "未登場", _bits(x, DEBUT)
            scen.append(e)
        if scen:
            row["scenarios"] = scen
        row["uncertain"] = ["more.性別", "more.兵科", "skills.特技", "died", "debut",
                            *[f"hidden.{label}" for label in HIDDEN], "relations.mother", "relations.spouse",
                            "relations.sworn", "relations.clan", "relations.siblings",
                            "scenarios.status", "scenarios.location", "scenarios.loyalty"]
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def scenarios_csv(game_dir, path):
    import san12_extras
    zh = san12_extras.bio_names(os.path.join(game_dir, ZH_DIR))
    zh_titles = _zh_titles(game_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "name", "nameZh", "year", "rulers"])
        for n, zt in zip(SCENARIOS, zh_titles):
            year, title, _, rulers, _, _ = _scenario(game_dir, n)
            w.writerow([n, f"PK/Scenario/Scenario{n}.dat", title, zt, year,
                        "、".join(zh[rulers[k]] for k in sorted(rulers))])
    return len(SCENARIOS)
