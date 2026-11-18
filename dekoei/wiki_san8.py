"""三國志VIII with PK (san8pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list.

All 51 scenarios (one a year, 184-234) come from the one file D_Sce.s8: the person table holds the fixed fields and a
timeline table holds every person's state from a given year on; a scenario of year Y takes, per person, the last
timeline record with year <= Y. Names are the Steam 繁中版's (depot 628040, san8_extras.zh_persons), the Japanese
ones go to nameJa. Layout and evidence: notes/san8.md「koei-wiki 匯出：人物」, notes/san-attributes.md「三國志VIII」.

    ../.venv/bin/python wiki_san8.py --game-dir ../games/san8pk-win   # writes extract/tables/scenarios.csv

The people are the kaodata san8pk-win characters: the records minus SAN8PK_WIN_ROLES and the alias 単福 (587, only
ever 身分 10, never an officer; 徐庶 is 236), id = record number.
"""
import collections
import csv
import os
import struct

import click

import sango
import san8_extras
from kaodata_export import SAN8PK_WIN_ALIASES, SAN8PK_WIN_ROLES
from common import cstr, fold_kana, u16
from PIL import Image
from places_export import PLACE_GAIJI, _gaiji, _reading

SCE = "D_Sce.s8"
ZH_DIR = os.path.join("..", "steam", "628040-tchinese", "depot")  # relative to game_dir
# Header u16 at 0: counts of the tables (16 州, 192 戦場?, 51 scenarios at +6, 512 city states at +8, 86 roads,
# 255 items, 112 item holders at +16, 4098 timeline records at +20)
SCENARIO_COUNT, FIRST_YEAR = 51, 184
# Timeline, 0x12BF5: 4098 x 13 bytes sorted by (person, year): u16 person, u16 year (from), u8 city (0-49, 0xFF),
# u8 勢力 (0xFF none), u8 身分, u8 忠誠, u8 階級? (0xFF none), u32 ? (not decoded). Year 271 records are past the
# last scenario and never apply.
TIMELINE, TL_SIZE, TL_COUNT = 0x12BF5, 13, 4098
# 身分: 3-9 match the EXE's strategy classes (一般 軍師 太守 軍団長 君主 / 同志 頭領 of a 放浪軍) and history
# (劉備 9 with 関羽 8 in 185, 198, 200; 諸葛亮 4 from 208, 6 in the 北伐 years; 関羽 6 from 212). 0, 1, 2 have no
# 勢力, 忠誠 0 and 階級 0xFF: exported as 在野 (the three are not told apart). 10 is never an officer (霊帝, 献帝,
# 華佗, 于吉, 祝融, 孫尚香 208, 単福): left out like san9's 9.
STATUS = {0: "在野", 1: "在野", 2: "在野", 3: "一般", 4: "軍師", 5: "太守", 6: "軍団長", 7: "君主", 8: "同志",
          9: "頭領"}
LORDS = (7, 9)
NOT_OFFICER = 10
SKILLS = san8_extras.SKILLS
TACTICS = ["突撃", "乱撃", "撹乱", "奇襲", "槍衾", "車懸", "火矢", "斉射", "乱射", "矢嵐", "激流", "烈火", "落石", "妖術",
           "攻城"]


def _read(game_dir):
    with open(os.path.join(game_dir, SCE), "rb") as f:
        return f.read()


def _record(data, i):
    o = sango.SAN8_PERSONS + i * sango.SAN8_PERSON_SIZE
    return data[o:o + sango.SAN8_PERSON_SIZE]


def timeline(data):
    """person id -> [(year, city, force, status, loyalty, rank)] in year order"""
    assert u16(data, 6) == SCENARIO_COUNT and u16(data, 20) == TL_COUNT
    out = collections.defaultdict(list)
    for k in range(TL_COUNT):
        pid, year, city, force, status, loyalty, rank = struct.unpack_from("<HHBBBBB", data, TIMELINE + TL_SIZE * k)
        out[pid].append((year, city, force, status, loyalty, rank))
    return out


def died(data, i):
    return u16(_record(data, i), 0x2B)


def state(tl, i, year):
    """the timeline record in force in a scenario year, or None (not yet in the game)"""
    s = None
    for r in tl[i]:
        if r[0] <= year:
            s = r
    return s


def scenario_states(data, tl, year):
    """{person: record} of the people alive in the scenario (year < 歿年), and {force: lord}"""
    states, lords = {}, {}
    for i in range(len(tl)):
        s = state(tl, i, year)
        if s and year < died(data, i):
            states[i] = s
            if s[3] in LORDS:
                assert s[2] not in lords
                lords[s[2]] = i
    return states, lords


def persons(game_dir):
    data = _read(game_dir)
    zh_dir = os.path.join(game_dir, ZH_DIR)
    zh = san8_extras.bio_names(zh_dir)
    with open(os.path.join(zh_dir, "D_SCE.S8"), "rb") as f:
        zh_data = f.read()
    people = {p["id"]: p for p in sango.load_san8_persons(os.path.join(game_dir, SCE))
              if p["name"] not in SAN8PK_WIN_ROLES | SAN8PK_WIN_ALIASES}
    tl = timeline(data)
    scens = [(n, FIRST_YEAR + n - 1, *scenario_states(data, tl, FIRST_YEAR + n - 1)) for n in range(1, SCENARIO_COUNT + 1)]
    children = {}
    for i in people:
        parent = u16(_record(data, i), 0x33)
        if parent in people and parent != i:
            children.setdefault(parent, []).append(i)
    rows = []
    for i, p in people.items():
        r = _record(data, i)
        row = {"id": i, "name": zh[i]}
        if zh[i] != p["name"]:
            row["nameJa"] = p["name"]
        courtesy = cstr(_record(zh_data, i)[0x22:0x27], "cp950").strip()
        if courtesy:
            row["courtesy"] = courtesy
        row["reading"] = fold_kana("".join(p["kana"]))
        row["born"], row["died"] = u16(r, 0x29), u16(r, 0x2B)
        row["stats"] = dict(zip(sango.SAN8_STATS, r[0x2D:0x31]))
        row["more"] = {"性別": "女" if r[0x38] & 0x80 else "男"}
        row["hidden"] = {"相性": r[0x35], "義理": r[0x36] & 15, "野望": r[0x36] >> 4, "冷静": r[0x37] & 7,
                         "勇猛": r[0x37] >> 3 & 7, "有名度": r[0x38] & 15, "寿命": r[0x3A]}
        bits = int.from_bytes(r[0x3B:0x3E], "little")
        skills = {}
        tokugi = [s for k, s in enumerate(SKILLS) if bits >> k & 1]
        if tokugi:
            skills["特技"] = tokugi
        levels = {t: v for t, v in zip(TACTICS, r[0x40:0x4F]) if v != 0xFF}
        if levels:
            skills["戦法"] = list(levels)
            row["game"] = {"戦法等級": levels}
        if skills:
            row["skills"] = skills
        rel = {"clan": u16(r, 0x31)}
        parent = u16(r, 0x33)
        if parent in people and parent != i:
            rel["father"] = [parent]
        if i in children:
            rel["children"] = sorted(children[i])
        row["relations"] = rel
        entries = []
        first = tl[i][0][0] if tl[i] else None
        for n, year, states, lords in scens:
            if i not in states:
                # not yet in the game: list it when a later record makes the person an officer or 在野
                if first is not None and year < first < row["died"] and state(tl, i, first)[3] != NOT_OFFICER:
                    entries.append({"scenario": n, "year": year, "status": "未登場", "debut": first})
                continue
            _, city, force, code, loyalty, _ = states[i]
            if code == NOT_OFFICER:
                continue
            e = {"scenario": n, "year": year, "status": STATUS[code]}
            if code >= 3:
                if lords[force] in people:
                    e["lord"] = lords[force]
                if code not in LORDS:
                    e["loyalty"] = loyalty
            if city < 50:
                e["location"] = city
            entries.append(e)
        if entries:
            row["scenarios"] = entries
        row["uncertain"] = ["born", "died", "more.性別", "hidden", "relations.clan", "relations.father",
                            "relations.children", "skills.戦法", "game.戦法等級", "scenarios.status"]
        rows.append(row)
    return rows


@click.command()
@click.option("--game-dir", "game_dir", required=True)
def main(game_dir):
    """寫 <game-dir>/extract/tables/scenarios.csv（劇本號、檔名、名稱、年、各勢力的君主）"""
    data = _read(game_dir)
    names = {p["id"]: p["name"] for p in sango.load_san8_persons(os.path.join(game_dir, SCE))}
    tl = timeline(data)
    out = os.path.join(game_dir, "extract", "tables", "scenarios.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "name", "nameZh", "year", "rulers"])
        for n in range(1, SCENARIO_COUNT + 1):
            year = FIRST_YEAR + n - 1
            states, lords = scenario_states(data, tl, year)
            rulers = [names[i] for i in sorted(lords.values(), key=lambda i: (states[i][3], i)) if states[i][3] == 7]
            w.writerow([n, SCE, f"{year}年", f"{year}年", year, " ".join(rulers)])
    print(out)


if __name__ == "__main__":
    main()


##############################################################################
# 三國志VIII PK: D_Sce.s8 (plain): 16 州 from 0x22 (17 bytes, name +2), 50 cities from 0x7F3 (16 bytes: name
# +1 5, reading +6 7, 州 +13), 86 roads from 0xB22 (7 bytes: kind, city A, city B, A-end place, B-end place, FF FF);
# the 172 places are the road ends (D_YMap.s8 part k is place k). San8WPK.exe VA 0x5D8A00 finds the place of the
# city pair; place -> picture: file 0x363EF0, 172 x (u32 left, u32 right) into G_W01Map.s8 (left, 35 + right).
# Each half is 1008 x 648 in its own palette: half k (and 35 + k) uses p_main.s8 palette 174 + k (256 x RGBX; 209-243
# repeat 174-208), found by colour statistics and by eye, not in the code. Place ids here: cities 0-49, place k is
# 50 + k.
SAN8_STATES, SAN8_CITIES, SAN8_ROADS, SAN8_PICTURES, SAN8_PALETTES = 0x22, 0x7F3, 0xB22, 0x363EF0, 174


def san8_picture(halves, palettes, left, right):
    """The 2016 x 648 battle map of W01Map[left] + W01Map[35 + right], each half in palette 174 + its number."""
    out = Image.new("RGB", (2016, 648))
    for x, k in ((0, left), (1008, 35 + right)):
        im = Image.frombytes("P", (1008, len(halves[k]) // 1008), halves[k])
        im.putpalette(b"".join(palettes[SAN8_PALETTES + k % 35][4 * c:4 * c + 3] for c in range(256)))
        out.paste(im.convert("RGB"), (x, 0))
    return out


def places(game_dir, out_dir):
    with open(os.path.join(game_dir, "D_Sce.s8"), "rb") as f:
        sce = f.read()
    exe_path = os.path.join(game_dir, "San8WPK.exe")
    with open(exe_path, "rb") as f:
        exe = f.read()
    gaiji = {**sango.SAN8_GAIJI, **PLACE_GAIJI}

    def s(b):
        return _gaiji(b.split(b"\0")[0].decode("cp932").strip(), gaiji)

    states = [s(sce[SAN8_STATES + 17 * k + 2:][:5]) for k in range(16)]
    cities = [sce[SAN8_CITIES + 16 * k:][:16] for k in range(50)]
    roads, o = [], SAN8_ROADS
    while sce[o + 5] == 0xFF:
        roads.append(sce[o:o + 5])
        o += 7
    pictures = struct.unpack_from("<344I", exe, SAN8_PICTURES)
    end = {}
    for kind, a, b, pa, pb in roads:
        end[pa], end[pb] = (a, b, kind), (b, a, kind)
    file = {p: f"W01Map_{pictures[2 * p]:02d}_{35 + pictures[2 * p + 1]:02d}.png" for p in end}
    with open(os.path.join(game_dir, "G_W01Map.s8"), "rb") as f:
        halves = sango.koei_archive(f.read())
    with open(os.path.join(game_dir, "p_main.s8"), "rb") as f:
        palettes = sango.koei_archive(f.read())
    os.makedirs(out_dir, exist_ok=True)
    for p in sorted(end, key=file.get):
        path = os.path.join(out_dir, file[p])
        if not os.path.exists(path):
            san8_picture(halves, palettes, pictures[2 * p], pictures[2 * p + 1]).save(path)
    users = {}
    for p in end:
        users.setdefault(file[p], []).append(50 + p)
    palette_note = "戰場圖的色盤是 p_main.s8 第 174＋（半張號 mod 35）組，用色彩統計和看圖找到，程式裡的出處沒追。"
    rows = []
    for k, r in enumerate(cities):
        adjacent, maps = [], []
        for _, a, b, pa, pb in roads:
            if k in (a, b):
                adjacent.append(b if a == k else a)
                maps.append({"file": file[pa if a == k else pb], "role": "野戰", "from": b if a == k else a})
        rows.append({"id": k, "name": s(r[1:6]), "reading": _reading(r[6:13]), "level": "都市",
                     "province": states[r[13]], "adjacent": adjacent, "battlemaps": maps, "uncertain": ["battlemaps"],
                     "notes": "相鄰是 D_Sce.s8 的道路表，照道路順序。戰場圖取道路在這個都市一端的地點；"
                              "遊戲用守方還是攻方那一端沒確認，所以標 uncertain。" + palette_note})
    for p in range(len(end)):
        a, b, kind = end[p]
        m = {"file": file[p], "role": "野戰"}
        shared = [x for x in users[file[p]] if x != 50 + p]
        if shared:
            m["sharedWith"] = shared
        rows.append({"id": 50 + p, "name": None, "level": "道路地點", "parentCity": a, "battlemaps": [m],
                     "uncertain": ["level"],
                     "notes": f"道路 {s(cities[a][1:6])}—{s(cities[b][1:6])} 的{s(cities[a][1:6])}端（號碼是遊戲的地點號＋50，"
                              f"也是 D_YMap.s8 的段號），道路種類碼 {kind}。這一代的 191 個戰場名和 172 個地點對不上，"
                              "所以不填名稱；「道路地點」是這邊的分類。戰場圖是 G_W01Map.s8 第 "
                              f"{pictures[2 * p]} 張（左）與第 {35 + pictures[2 * p + 1]} 張（右）拼成，172 個地點只有 43 種組合，"
                              "同組合的地形相同，差在布陣點和旗標。" + palette_note})
    return rows


def stats(game_dir):
    # build_san8pk_win: D_Sce.s8 persons without the role and alias records, id = record id
    rows = {r[0]: r for r in sango.load_san8_stats(os.path.join(game_dir, "D_Sce.s8"))}
    persons = sango.load_san8_persons(os.path.join(game_dir, "D_Sce.s8"))
    return [(p["id"], p["name"], dict(zip(sango.SAN8_STATS, rows[p["id"]][2:])))
            for p in persons if p["name"] not in SAN8PK_WIN_ROLES | SAN8PK_WIN_ALIASES]
