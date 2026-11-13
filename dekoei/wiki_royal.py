"""ロイヤルブラッド (royal-pc98) for koei-wiki: persons (koei-persons/1) and the 30 国 (koei-places/1).

id is the kaodata royal-pc98 id (the lord index 0-63, also the name table and face index). Scenarios are
SNDATA1-4.CIM, loaded at DS:0x42 (MAIN.EXE image 0x59C: person = (ptr - 0xF2) / 10, so file 0xB0 = DS:0xF2).
Field sources: notes/koei-games.md「ロイヤルブラッド」「koei-wiki 匯出」."""
import os
import unicodedata

import koei_games as kg
from kaodata_export import kana_to_hiragana

DS = kg.ROYAL_PC98_DGROUP
LORDS, PLACES = 64, 30
PERSON = 0xB0  # 10 bytes: +0 ptr, +2 政治, +3 軍事, +4 魅力, +5 国 (FF absent), +6 家, +7 身分, +8 血縁, +9 名声
PLACE = 0x330  # 36 bytes: +14 owning house (FF none)
YEARS = 2  # years since scenario 1 (DS:0x44), added to the age base
MONTH = 3  # DS:0x45, the month; 0xD734 wraps it after 12
AGE = 0xE52 + 10  # name record (13 bytes) +10: u16 age base (image 0x5DE adds DS:0x44)
PLACE_NAMES = 0x1192  # 19 bytes: +0 name (9), +9 neighbours (8, FF none), +17 two bytes (map position?)
HOUSES = 0x153C  # 11 bytes per house name
STATUS = {1: "当主", 2: "領主", 4: "家臣"}  # +7 & 0xF -> DS:0x1D50 labels (image 0x8660, 0x8746)
STATS = ("政治", "軍事", "魅力")  # DS:0x56AE「政治%3d 軍事%3d 魅力%3d」prints +2, +3, +4 (image 0x8622)
SCENARIO_NAMES = ("エランとレッドワルト", "フェリアス家の危機", "ティリアンの戦い", "ロイヤルブラッド")


def _kana(b):
    return unicodedata.normalize("NFKC", b.split(b"\0")[0].decode("cp932"))


def _read(game_dir):
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        main = f.read()
    scen = []
    for s in range(1, 5):
        with open(os.path.join(game_dir, f"SNDATA{s}.CIM"), "rb") as f:
            scen.append(f.read())
    return main, scen


def _houses(main):
    return [_kana(main[DS + HOUSES + 11 * h:][:11]) for h in range(41)]


def _lords(d):
    """house -> its 当主 in scenario d"""
    out = {}
    for i in range(LORDS):
        r = d[PERSON + 10 * i:][:10]
        if r[5] != 0xFF and r[7] & 0xF == 1:
            out[r[6]] = i
    return out


def persons(game_dir):
    main, scen = _read(game_dir)
    names, _ = kg.load_royal_pc98_names(os.path.join(game_dir, "MAIN.EXE"))
    houses = _houses(main)
    lords = [_lords(d) for d in scen]
    rows = []
    for i, name in enumerate(names):
        base = int.from_bytes(main[DS + AGE + 13 * i:][:2], "little")
        out, seen, first, fame, kin = [], False, None, False, []
        for k, d in enumerate(scen):
            r = d[PERSON + 10 * i:][:10]
            s = {"scenario": k + 1, "month": d[MONTH]}
            if r[5] == 0xFF:
                s["status"] = "不在" if seen else "未登場"
            else:
                seen = True
                if first is None:
                    first = k
                s.update(lord=lords[k][r[6]], location=r[5], status=STATUS[r[7] & 0xF],
                         stats=dict(zip(STATS, r[2:5])))
                if r[7] & 0xF == 1:
                    s["stats"]["名声"] = r[9]
                    fame = True
                if r[8] != 0xFF and houses[r[8]] not in kin:
                    kin.append(houses[r[8]])
            out.append(s)
        row = {"id": i, "name": name, "reading": kana_to_hiragana(name)}
        notes = [f"劇本（{'、'.join(f'{n + 1}.{t}' for n, t in enumerate(SCENARIO_NAMES))}）沒有西曆年，"
                 "只有開局後經過的年數 0、5、10、15，所以不填 year；劇本都從 12 月開始。"]
        if first is not None:
            d = scen[first]
            row["stats"] = dict(zip(STATS, d[PERSON + 10 * i + 2:][:3]))
            row["more"] = {"年齢": base + d[YEARS]}
            if kin:
                row["more"]["血縁"] = kin[0] if len(kin) == 1 else kin
            notes.append(f"頂層的 stats、年齢取劇本 {first + 1}（第一個登場的劇本），各劇本的能力放 scenarios[].stats；"
                         "年齢是名字表的基準值加劇本經過的年數（劇本開始的 12 月）。")
            if kin:
                notes.append("血縁是記錄 +8 的家（不是 FF 時狀態畫面標「血縁」），值換成家名【推】。")
            if fame:
                notes.append("名声只有当主有（狀態畫面只對当主印），放在該劇本的 stats。")
            if any(x["status"] in ("未登場", "不在") for x in out):
                notes.append("「未登場」「不在」是劇本裡所在国為 FF：第一次登場前寫未登場，登場過之後寫不在"
                             "（遊戲沒有稱呼，照使用者 2026-11-14 的規則；何時由事件登場沒追，所以沒有 debut）。")
        else:
            notes.append("四個劇本都不在地圖上。")
        row["scenarios"] = out
        if kin:
            row["uncertain"] = ["more.血縁"]
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def places(game_dir, out_dir):
    main, scen = _read(game_dir)
    houses = _houses(main)
    lords = [_lords(d) for d in scen]
    rows = []
    for c in range(PLACES):
        rec = main[DS + PLACE_NAMES + 19 * c:][:19]
        out = []
        for k, d in enumerate(scen):
            s = {"scenario": k + 1, "month": d[MONTH]}
            owner = d[PLACE + 36 * c + 14]
            if owner != 0xFF:
                s["家"] = houses[owner]
                s["lord"] = lords[k][owner]
            out.append(s)
        rows.append({"id": c, "name": _kana(rec[:9]), "level": "国", "adjacent": [x for x in rec[9:17] if x != 0xFF],
                     "scenarios": out,
                     "notes": "国的記錄 MAIN.EXE DS:0x1192＋19·c（名字、相鄰）；家是劇本開始時的支配家（劇本 0x330＋36·c ＋14），"
                              "lord 是該家的当主；沒有支配家的是空白地。"})
    return rows
