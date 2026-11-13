"""ランペルール (lempe-dos, DOS Chinese) for koei-wiki: persons (koei-persons/1) and cities (koei-places/1).

NPDATA.CIM holds 5 scenarios of 13270 bytes; all offsets below are scenario offsets. id is the kaodata lempe-dos id
(the record index 0-254, the same as koei-wiki lempe-persons-mapping.csv). Names and words are the Chinese
version's; nameJa comes from the PC-88 NPDATA.CIM beside it (../lempe-pc88, the same order, half-width katakana),
nameEn (persons) and the cities' game.英文名 from the English DOS NPDATA.CIM (same layout and data, English names), read from its archive
games/archives/dos/拿破崙_英文版_l-empereur.zip. Field sources: notes/lempe.md「koei-wiki 匯出」."""
import os
import unicodedata
import zipfile

import kaodata_export as ke
import koei_games as kg
from utils import to_unicode_name

DATASET = "lempe-dos"
PERSONS, CITIES, NATIONS = 255, 46, 15
SCEN = 13270
PERSON = 2  # 15 bytes per person
NATION_NAMES = 7220  # 10 bytes per nation, KOEI-TW
CITY = 7370  # 34 bytes per city: +0 name (15), +16 x, +21 y, +26..+32 neighbours (0xFF none), +33 flags
OWNER = 4102  # owner nation of city c at OWNER + 28 * c; 255 none
DATE = 5628  # u16 year, then the month
PC88_NATIONS, PC88_CITY = 0x1BA1, 0x1C28  # PC-88 NPDATA.CIM: 9-byte nation names; 31-byte cities, name 12 bytes
STATS = ("政治", "財政", "補給", "建設", "領導", "步兵", "騎兵", "砲兵")
GRADE = "DCBA"
# rank (R+0xE & 0xF) -> the Chinese MAIN.EXE title (0x3BE88..); 0 and 1 have no title, 15 is not on the map
TITLES = {2: "戰俘", 3: "預備軍官", 4: "現役軍官", 5: "司令官", 6: "督政官", 7: "國王"}
NAPOLEON_TITLES = {6: "第一執政", 7: "皇帝"}
NOT_ON_MAP = 15
EN_ZIP = ("archives", "dos", "拿破崙_英文版_l-empereur.zip")


def _english(game_dir):
    with zipfile.ZipFile(os.path.join(game_dir, "..", *EN_ZIP)) as z:
        return z.read("empereur/NPDATA.CIM")


def _scenarios(game_dir):
    with open(os.path.join(game_dir, "NPDATA.CIM"), "rb") as f:
        data = f.read()
    return [data[k * SCEN:(k + 1) * SCEN] for k in range(5)]


def _pc88(game_dir):
    with open(os.path.join(game_dir, "..", "lempe-pc88", "NPDATA.CIM"), "rb") as f:
        return f.read()


def _kana(b):
    return unicodedata.normalize("NFKC", b.split(b"\0")[0].decode("cp932")).strip()


def _zh(b):
    return to_unicode_name(b.split(b"\0")[0]).strip()


def _date(d):
    return int.from_bytes(d[DATE:][:2], "little"), d[DATE + 2]


def _person(d, i):
    return d[PERSON + 15 * i:][:15]


def _lords(d):
    """nation -> its lord: the rank 7 person, else the rank 6 one."""
    lords = {}
    for want in (6, 7):
        for i in range(PERSONS):
            r = _person(d, i)
            if r[14] & 0xF == want:
                lords[r[2]] = i
    return lords


def persons(game_dir):
    scen = _scenarios(game_dir)
    names_zh = [p["name"] for p in kg.load_lempe_persons(os.path.join(game_dir, "NPDATA.CIM"), 0)]
    names_ja = [n for n, _ in kg.load_lempe_pc88_persons(os.path.join(game_dir, "..", "lempe-pc88", "NPDATA.CIM"))]
    en = _english(game_dir)
    names_en = [en[8934 + 17 * i:][:14].split(b"\0")[0].decode("ascii") for i in range(PERSONS)]
    nations = [_zh(scen[0][NATION_NAMES + 10 * n:][:10]) for n in range(NATIONS)]
    lords = [_lords(d) for d in scen]
    rows = []
    for i in range(PERSONS):
        row = {"id": i, "name": names_zh[i]}
        if names_ja[i] != names_zh[i]:
            row["nameJa"] = names_ja[i]
        ages = [(_date(d)[0], (_person(d, i)[8] ^ 0x80) - 0x80) for d in scen]
        # age 0 is a dead person (rank 15); the others give one birth year, except for 7 people
        borns = [y - a for y, a in ages if a]
        row["born"] = borns[0]
        born_differs = len(set(borns)) > 1
        r = _person(scen[0], i)
        row["stats"] = {s: GRADE[b >> sh & 3] for s, (b, sh) in zip(STATS, [(b, sh) for b in r[4:6] for sh in (0, 2, 4, 6)])}
        row["more"] = {"國": nations[r[2]], "經驗": r[6], "忠誠": r[7], "兵力": r[9], "士氣": r[13], "訓練": r[12]}
        if r[8] < 200:
            row["more"]["年齡"] = r[8]
        out, uncertain = [], set()
        for k, d in enumerate(scen):
            r = _person(d, i)
            year, month = _date(d)
            s = {"scenario": k + 1, "year": year, "month": month}
            rank = r[14] & 0xF
            if r[8] >= 200:
                s["status"] = "未登場"
            elif rank == NOT_ON_MAP:
                s["status"] = "不在"
                uncertain.add("scenarios.status")
            else:
                title = NAPOLEON_TITLES.get(rank) if i == 0 else None
                if title or rank in TITLES:
                    s["status"] = title or TITLES[rank]
                if r[3] < CITIES:
                    s["location"] = r[3]
                if 3 <= rank <= 7 and r[2] in lords[k]:
                    s["lord"] = lords[k][r[2]]
                if i != 0:
                    s["loyalty"] = r[7]
            out.append(s)
        row["scenarios"] = out
        row["nameEn"] = names_en[i]
        if born_differs:
            uncertain.add("born")
        row["uncertain"] = sorted(uncertain | {"scenarios.month"})
        notes = ["stats 與 more 是劇本 1（1796 年）的值；能力 D–A 各劇本相同。born 是劇本年減年齡。"
                 "month 是劇本年份後一個 byte（都是 3），推定是月。status 是官階（R+0xE）在中文版 MAIN.EXE 的稱呼；"
                 "官階 0、1 沒有稱呼（1 是王位繼承人與未出生者），不填 status；官階 15 是劇本開始時不在地圖上"
                 "（已死或已被取代），寫「不在」，不是遊戲用語。未登場是年齡 ≥ 200（還沒出生）。"
                 "lord 是所屬國的國王（官階 7），沒有國王時是督政官（官階 6）；戰俘不填。"]
        if born_differs:
            notes.append("各劇本的年齡算出的生年不一致（" + "、".join(str(b) for b in dict.fromkeys(borns))
                         + "），born 取最早的劇本。")
        if i == 0:
            notes.append("拿破崙沒有忠誠（遊戲顯示「--」）；官階 5 在某個條件下顯示「總司令官」（MAIN.EXE 0x60E8，條件沒追），這裡寫司令官。")
        if i in ke.LEMPE_NAME_HISTORICAL:
            notes.append(f"中文版寫法有誤，史書寫法 {ke.LEMPE_NAME_HISTORICAL[i]}。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def places(game_dir, out_dir):
    scen = _scenarios(game_dir)
    pc88 = _pc88(game_dir)
    d0 = scen[0]
    nations = [_zh(d0[NATION_NAMES + 10 * n:][:10]) for n in range(NATIONS)]
    lords = [_lords(d) for d in scen]
    en = _english(game_dir)
    rows = []
    for c in range(CITIES):
        rec = d0[CITY + 34 * c:][:34]
        name = _zh(rec[:15])
        name_ja = _kana(pc88[PC88_CITY + 31 * c:][:12])
        game = {"座標": {"x": rec[16], "y": rec[21]}}
        if rec[33] & 1:
            game["臨海"] = True
        game["英文名"] = en[CITY + 34 * c:][:15].split(b"\0")[0].decode("ascii")
        out = []
        for k, d in enumerate(scen):
            year, month = _date(d)
            s = {"scenario": k + 1, "year": year, "month": month}
            owner = d[OWNER + 28 * c]
            if owner < NATIONS:
                s["國"] = nations[owner]
                if owner in lords[k]:
                    s["lord"] = lords[k][owner]
            out.append(s)
        row = {"id": c, "name": name, **({"nameJa": name_ja} if name_ja != name else {}), "level": "城市",
               "adjacent": [x for x in rec[26:33] if x != 0xFF], "scenarios": out, "game": game,
               "uncertain": ["scenarios.month", "game.座標", "game.臨海"],
               "notes": "城市記錄 NPDATA.CIM 7370＋34·c（各劇本相同）；國是劇本開始時的領有國（4102＋28·c），lord 是該國國王"
                        "（沒有國王時是督政官）。game.座標是記錄 +16、+21，畫出來是歐洲的形狀，但大地圖沒解，沒有 pos；"
                        "臨海是 +33 bit 0（推定，和地理一致）。"}
        rows.append(row)
    return rows
