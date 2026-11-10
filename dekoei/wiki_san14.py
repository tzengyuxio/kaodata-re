"""三國志14 with PK (san14pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list. Names are the
繁中 ones (0010_TC), the Japanese ones (0010_JP) go to nameJa. Fields and evidence: notes/san14.md「koei-wiki 匯出：
人物」, notes/san-attributes.md「三國志14」.

    ../.venv/bin/python wiki_san14.py --game-dir ../games/san14pk-win   # writes extract/tables/scenarios.csv

The people are the 1001 kaodata san14pk-win characters (sango.load_san14_persons), id 0-1000. Record boundary: the
ability block of person id k is the next record slot, start + (k + 1) x size, and begins with the game's person
number k + 1 (英布 is 2001); person references in it are game numbers, so id = number - 1 (2001 -> 1000). Slot 0
(before 阿会喃) is no person. References to numbers outside 1-1000 / 2001 (the 父 of 341 people points to 10000+,
people not in the person table such as 曹嵩) are left out.

Scenarios: the 27 0010_JP/scedaex*.s14 of the PK; the scenario number is the file number (01-08, 21-25, 55-62, 71,
100-104), the menu order is not known. 100-104 are 決戦制覇 battles: everyone outside the battle is 死亡 there, so
死亡 is left out of them; 71 is the tutorial (991 people have code 0, not in it).
"""
import csv
import os
import struct

import click

import biography
import ls11
import sango
from kaodata_export import SAN14PK_WIN_GAIJI, kana_to_hiragana

# scenario header (before the LWC block): +0x14 description, +0x1A6 title (17 UTF-16 chars), +0x1C8 u16 year,
# +0x1CA mode (1 normal, 2 tutorial, 4 決戦制覇), +0x1CE file number, +0x1D3 1 historical / 0 hypothetical
TITLE, YEAR, MODE, HISTORICAL = 0x1A6, 0x1C8, 0x1CA, 0x1D3
KINDS = {4: "決戦制覇", 2: "チュートリアル"}
# decoded scenario: the 軍団 table, entries of 4 bytes from 0x54EE up to a zero leader: u8 force, u8 order in the
# force (1 = the ruler's own), u16 leader (game number); the person's +6 is the row + 1
GUNDAN = 0x54EE
START, SIZE, _ = sango.SAN14_PERSONS["JP", True]
# ability block (JP PK, from the u16 game number): +2 配偶, +4 義兄弟 (the eldest; himself for the eldest), +6 軍団,
# +7 u16 所属 city, +9 u16 所在 city, +11 身分 (STATUS), +13 忠誠, +16 5 x u8 stats, +26 5 x u16 個性, +44 u16 陣形
# bits, +48 6 x u8 戦法, +58 政策, +63 u16 仕官, +66 性別, +67 u16 登場年, +69 生年, +71 没年, +74 一門 (the head),
# +76 父, +78 母, +81 相性, +82 8 x u16 親愛武将, +98 7 x u16 嫌悪武将, +124 主義
STATUS = 249  # msgdata (0, 0) strings 249-257: 君主 都督 太守 一般 在野 捕虜 未登場 未発見 死亡 = codes 1-9
RULER, NOT_YET, DEAD = 1, 7, 9
FORMATIONS = ["魚鱗", "鋒矢", "雁行", "方円", "鶴翼", "長蛇", "錐行", "井闌", "衝車", "投石"]  # bits 1-10
# fixdataex.s14 (JP) name tables: (start, record size), the name is the first 20 bytes (UTF-16)
TRAITS = 0x406AF, 149  # 個性
TACTICS = 0x2E046, 93  # 戦法
POLICIES = 0x3B31C, 120  # 政策
ISMS = 0x3AEB2, 102  # 主義
CITIES = 51  # fixdataex city records 1-51 (0x3E8 + 53 x c)
# 所在 52-61 are the gates 1-10 of the fixdataex gate table (0xEB4 + 40 x k, name 5 UTF-16 chars; 壺関 虎牢関 潼関
# 函谷関 武関 陽平関 白水関 剣閣 涪水関 綿竹関): 華雄 53 虎牢関 in 190, 楊懐 58 白水関
GATES = 0xEB4, 40


def _decode(path):
    with open(path, "rb") as f:
        d = f.read()
    return d, ls11.lwc_decode(d[d.index(b"LWC\x1a"):])


def _text(b):
    return b.decode("utf-16-le").split("\0")[0]


def _msg(game_dir, lang):
    with open(os.path.join(game_dir, f"0001_{lang}", "msgdata.bin"), "rb") as f:
        x = sango.san13_items(sango.san13_items(sango.san13_unzip(f.read()))[0])[0]
    rows, size = struct.unpack_from("<2H", x, 8)
    out = []
    for r in range(rows):
        o = e = 0x18 + struct.unpack_from("<I", x, 0x18 + r * size)[0]
        while x[e:e + 2] != b"\0\0":
            e += 2
        out.append(x[o:e].decode("utf-16-le"))
    return out


def _names(fix, table, k):
    start, size = table
    return _text(fix[start + size * k:][:20])


def _city_areas(game_dir):
    """{所在 value: places export id}: cities 1-51 (the city's own area), gates 52-61 (by name)"""
    import json
    _, tc = _decode(os.path.join(game_dir, "0010_TC", "fixdataex.s14"))
    from places_export import SAN14_AREAS
    out = {}
    for i in range(1, 344):
        city = tc[SAN14_AREAS + 65 * i + 36]
        out.setdefault(city, i)  # the city's own area comes first (its 治所)
    path = os.path.join(os.path.dirname(__file__), "..", "export", "koei-wiki", "places", "san14pk-win.jsonl")
    with open(path, encoding="utf-8") as f:
        gates = {r["name"]: r["id"] for r in map(json.loads, f) if r["level"] == "關"}
    for k in range(1, 11):
        out[CITIES + k] = gates[_text(tc[GATES[0] + GATES[1] * k:][:10])]
    return out


def _files(game_dir):
    names = [f for f in os.listdir(os.path.join(game_dir, "0010_JP")) if f.startswith("scedaex")]
    return sorted((int(f[7:-4]), f) for f in names)


def scenarios(game_dir):
    """[(number, file, title, titleZh, year, kind, {force: ruler id}, {軍団 row + 1: (force, ruler id)}, decoded)]"""
    out = []
    for n, name in _files(game_dir):
        raw, d = _decode(os.path.join(game_dir, "0010_JP", name))
        raw_tc, _ = _decode(os.path.join(game_dir, "0010_TC", name))
        title, title_tc = _text(raw[TITLE:TITLE + 34]), _text(raw_tc[TITLE:TITLE + 34])
        year = struct.unpack_from("<H", raw, YEAR)[0]
        assert year == struct.unpack_from("<H", raw_tc, YEAR)[0]
        assert raw[0x1CE] == n % 256, name
        kind = KINDS.get(raw[MODE], "史実" if raw[HISTORICAL] else "仮想")
        gundan = []
        while leader := struct.unpack_from("<H", d, GUNDAN + 4 * len(gundan) + 2)[0]:
            o = GUNDAN + 4 * len(gundan)
            gundan.append((d[o], d[o + 1], leader))
        rulers = {f: _id(leader) for f, order, leader in gundan if order == 1}
        corps = {i + 1: (f, rulers[f]) for i, (f, _, _) in enumerate(gundan)}
        out.append((n, f"0010_JP/{name}", title, title_tc, year, kind, rulers, corps, d))
    return out


def _id(number):
    """game person number -> kaodata id (None outside the table)"""
    if 1 <= number <= 1000:
        return number - 1
    return 1000 if number == 2001 else None


def _person_names(game_dir):
    path_ja, path_tc = (os.path.join(game_dir, f"0010_{l}", "scedaex01.s14") for l in ("JP", "TC"))
    ja, tc = sango.load_san14_persons(path_ja), sango.load_san14_persons(path_tc, "TC")
    # as kaodata_export.build_san14pk_win: gaiji read off the other language's name; the TC ones also as the
    # biographies
    gaiji = dict(SAN14PK_WIN_GAIJI)
    for a, b in zip(ja, tc):
        for f in ("surname", "given", "azana"):
            if len(a[f]) == len(b[f]):
                for x, y in zip(a[f], b[f]):
                    if 0xE000 <= ord(x) <= 0xF8FF and not 0xE000 <= ord(y) <= 0xF8FF:
                        gaiji.setdefault(("JP", x), y)
                    if 0xE000 <= ord(y) <= 0xF8FF and not 0xE000 <= ord(x) <= 0xF8FF:
                        gaiji.setdefault(("TC", y), x)
    for c, v in biography.SAN14_BIO_GAIJI.items():
        gaiji.setdefault(("TC", c), v)

    def text(lang, t):
        t = "".join(gaiji.get((lang, c), c) for c in t)
        assert not any(0xE000 <= ord(c) <= 0xF8FF for c in t), t
        return t

    return [(text("TC", b["surname"] + b["given"]), text("JP", a["surname"] + a["given"]), text("TC", b["azana"]),
             " ".join(kana_to_hiragana(r) for r in a["reading"])) for a, b in zip(ja, tc)]


def persons(game_dir):
    names = _person_names(game_dir)
    _, fix = _decode(os.path.join(game_dir, "0010_JP", "fixdataex.s14"))
    status = _msg(game_dir, "JP")[STATUS:STATUS + 9]
    assert status[0] == "君主" and status[-1] == "死亡", status
    city_area = _city_areas(game_dir)
    scens = scenarios(game_dir)
    first = scens[0][8]
    blocks = [first[START + (k + 1) * SIZE:][:157] for k in range(1001)]
    for k, b in enumerate(blocks):
        assert _id(struct.unpack_from("<H", b)[0]) == k, k

    def u16(b, o):
        return struct.unpack_from("<H", b, o)[0]

    def ref(b, o):
        return _id(u16(b, o))

    sworn, children = {}, {}
    for k, b in enumerate(blocks):
        if ref(b, 4) is not None:
            sworn.setdefault(ref(b, 4), []).append(k)
        for o in (76, 78):
            if ref(b, o) is not None:
                children.setdefault(ref(b, o), []).append(k)
    rows = []
    for k, b in enumerate(blocks):
        name, name_ja, courtesy, reading = names[k]
        row = {"id": k, "name": name}
        if name_ja != name:
            row["nameJa"] = name_ja
        if courtesy:
            row["courtesy"] = courtesy
        row["reading"] = reading
        row["born"], row["debut"], row["died"] = u16(b, 69), u16(b, 67), u16(b, 71)
        row["stats"] = dict(zip(sango.SAN14_STATS, b[16:21]))
        more = {"性別": "女" if b[66] else "男"}
        if b[124]:
            more["主義"] = _names(fix, ISMS, b[124])
        row["more"] = more
        row["hidden"] = {"相性": b[81]}
        skills = {}
        traits = [_names(fix, TRAITS, t) for t in struct.unpack_from("<5H", b, 26) if t]
        if traits:
            skills["個性"] = traits
        tactics = [_names(fix, TACTICS, t) for t in b[48:54] if t]
        if tactics:
            skills["戦法"] = tactics
        formations = [f for i, f in enumerate(FORMATIONS, 1) if u16(b, 44) >> i & 1]
        if formations:
            skills["陣形"] = formations
        if b[58]:
            skills["政策"] = [_names(fix, POLICIES, b[58])]
        if skills:
            row["skills"] = skills
        game = {}
        for key, o, n in (("親愛武将", 82, 8), ("嫌悪武将", 98, 7)):
            people = [x for x in (ref(b, o + 2 * i) for i in range(n)) if x is not None]
            if people:
                game[key] = people
        if game:
            row["game"] = game
        rel = {}
        for key, o in (("father", 76), ("mother", 78), ("spouse", 2)):
            if ref(b, o) is not None:
                rel[key] = [ref(b, o)]
        if k in children:
            rel["children"] = sorted(children[k])
        group = sworn.get(ref(b, 4), [])
        if len(group) > 1:
            rel["sworn"] = sorted(x for x in group if x != k)
        if ref(b, 74) is not None:
            rel["clan"] = ref(b, 74)
        if rel:
            row["relations"] = rel
        row["scenarios"] = []
        for n, _, _, _, year, kind, rulers, corps, d in scens:
            s = d[START + (k + 1) * SIZE:][:157]
            code, city = s[11], u16(s, 9)
            if code == 0 or code == DEAD and kind == "決戦制覇":  # not in the scenario
                continue
            e = {"scenario": n, "year": year, "status": status[code - 1]}
            if s[6]:
                assert code <= 4, (k, code)
                ruler = corps[s[6]][1]
                if ruler != k:
                    e["lord"] = ruler
                    e["loyalty"] = s[13]
                else:
                    assert code == RULER, k
            if city in city_area and code != DEAD:
                e["location"] = city_area[city]
            if code == NOT_YET:
                e["debut"] = u16(s, 67)
            row["scenarios"].append(e)
        if not row["scenarios"]:
            del row["scenarios"]
            row["notes"] = "每個劇本的身分碼都是 0、沒有所在，像是不在劇本裡的特殊人物（遊戲內人物號 2001）。"
        row["uncertain"] = ["born", "debut", "died", "more.性別", "more.主義", "hidden.相性", "relations",
                            "game.親愛武将", "game.嫌悪武将", "scenarios.lord", "scenarios.loyalty", "scenarios.location"]
        rows.append(row)
    return rows


@click.command()
@click.option("--game-dir", "game_dir", required=True)
def main(game_dir):
    """寫 <game-dir>/extract/tables/scenarios.csv（劇本號＝檔案號、檔名、標題（日、繁中）、年、種類、各勢力的君主）"""
    names = _person_names(game_dir)
    out = os.path.join(game_dir, "extract", "tables", "scenarios.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "name", "nameZh", "year", "kind", "rulers"])
        for n, file, title, title_zh, year, kind, rulers, _, _ in scenarios(game_dir):
            w.writerow([n, file, title, title_zh, year, kind, " ".join(names[r][0] for _, r in sorted(rulers.items()))])
    print(out)


if __name__ == "__main__":
    main()
