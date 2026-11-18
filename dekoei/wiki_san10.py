"""三國志X with PK (san10pk-win) for koei-wiki: persons (koei-persons/1) and the scenario list.

The officers are the 650 records of the PK scenarios Scenario/ScePK0??.s10 (plain, 66 bytes a record). The record
of officer k starts at 23015 + 66 k: the repo's older offsets (sango.SAN10_PERSONS from 23001, notes/san10.md「人物」)
are 14 bytes earlier, so their "+n" is "+n - 14" here. Field names follow the reversed field-name list of
San10WPK.exe (0x460478 down to 0x4602ec: 所在 顔 性別 登場年 誕生年 死亡年 死因 登場 身分 血縁 父親 母親 配偶者
登場予定君主 忠誠 功績 名声 統率 … 魅力 勢力相性 個人相性 義兄弟 仇敵 義理 登用不可 起用 漢室 飲酒 好み 物欲 性格
戦略傾向 任務態度 旗番号); evidence per field in notes/san10.md「koei-wiki 匯出：人物」. Names are the 繁中版's
(Steam depot 628062, San10WPK.exe tables 0x919120 / 0x919B48 / 0x91A570 as san10_extras.zh_persons), the
Japanese ones go to nameJa.

    persons(game_dir) -> [row]          (persons_export.py; reads ZH_DIR too)
    scenarios_csv(game_dir, path)       the 11 scenarios: number, file, titles, year, rulers
"""
import csv
import os
import struct

import sango
from kaodata_export import kana_to_hiragana
from common import u16
from places_export import _gaiji
from wiki_stats import _pick

# the PK scenarios in the game's order (titles: msg/S10M18PK.s10 entries 0, 2, … 20, whose years match the files)
SCENARIOS = ["ScePK000", "ScePK001", "ScePK002", "ScePK003", "ScePK004", "ScePK005", "ScePK006", "ScePK020",
             "ScePK021", "ScePK022", "ScePK023"]
MAIN = 0  # ScePK000 (184): the values the stats export uses
RECORDS, SIZE, PEOPLE = 23015, 66, 650
# 50 軍団 of 5 bytes: 軍団 id, 勢力 (0xFF unused), number within the 勢力, u16 軍団長 (its 君主 or 都督). Person +2 is
# the 軍団; every 勢力 has exactly one 君主 in all 11 scenarios
CORPS = 3582
YEAR = 0x12  # u16 scenario year
ZH_DIR = os.path.join("..", "steam", "628060-tchinese", "depot")  # relative to game_dir
ZH_STYLE = 0x91A570  # 字 table of the 繁中版 EXE
# FA43 (S10Gaiji.tte) appears only in 秦宓's 字, Japanese 子勑 (🟡); the other gaiji as san9_extras.ZH_GAIJI
ZH_GAIJI_STYLE = {b"\xfa\x43": "勑"}
# 登場 (+18): 0 not yet, 1 and 2 on the map (1 only for 在野), 3 dead. 身分 (+19), 0xFF when not on the map
STATUS = {0: "君主", 1: "都督", 2: "太守", 3: "一般", 4: "在野"}
SKILLS = ("農業 商業 技術 改修 治安 徴兵 訓練 突撃 火矢 一斉 鎮静 鼓舞 奇襲 隠密 同討 足止 誘引 混乱 天文 地理 石陣 回復 "
          "気合 気炎 受返 弾返 三段 螺旋 威圧 抗弁 反論 揚足 論破 挑発 面罵 軍師 名士 提督 間諜 酒豪 医者 仙人").split()
HIDDEN = [("勢力相性", 42), ("個人相性", 43), ("義理", 48), ("起用", 50), ("漢室", 51), ("飲酒", 52), ("好み", 53),
          ("物欲", 54), ("性格", 55), ("戦略傾向", 56), ("任務態度", 57), ("死因", 17)]
NONE = 0xFFFF


def _scenario(game_dir, name):
    """year, [person record], {軍団: 勢力}"""
    with open(os.path.join(game_dir, "Scenario", name + ".s10"), "rb") as f:
        d = f.read()
    corps = {d[o]: d[o + 1] for o in range(CORPS, CORPS + 5 * 50, 5) if d[o + 1] != 0xFF}
    return struct.unpack_from("<H", d, YEAR)[0], [d[RECORDS + SIZE * k:][:SIZE] for k in range(PEOPLE)], corps


def _rulers(recs, corps):
    """軍団 (+2) -> person id of the 君主 (身分 0) of its 勢力"""
    heads = {corps[r[2]]: k for k, r in enumerate(recs) if r[18] in (1, 2) and r[19] == 0}
    return {c: heads[f] for c, f in corps.items()}


def _scenario_titles(game_dir):
    import san10_extras
    from san9_extras import zh_text
    ja = san10_extras.read_msg(os.path.join(game_dir, "msg", "S10M18PK.s10"))
    zh = san10_extras.read_msg(os.path.join(game_dir, ZH_DIR, "msg", "S10M18PK.s10"))
    return ([san10_extras.text(ja[2 * i]) for i in range(len(SCENARIOS))],
            [zh_text(zh[2 * i].rstrip(b"\x05")) for i in range(len(SCENARIOS))])


def _zh_names(game_dir):
    import san10_extras
    from san9_extras import ZH_GAIJI, zh_text
    zh_dir = os.path.join(game_dir, ZH_DIR)
    names = {k: n for k, n, _ in san10_extras.zh_persons(zh_dir)}
    with open(os.path.join(zh_dir, "San10WPK.exe"), "rb") as f:
        exe = f.read()
    style = {}
    for k in range(PEOPLE):
        o = struct.unpack_from("<I", exe, ZH_STYLE - 0x400000 + 4 * k)[0] - 0x400000
        style[k] = zh_text(exe[o:exe.index(b"\0", o)], {**ZH_GAIJI, **ZH_GAIJI_STYLE})
    return names, style


def persons(game_dir):
    ja = sango.load_san10_persons(os.path.join(game_dir, "San10WPK.exe"),
                                  os.path.join(game_dir, "Scenario", SCENARIOS[MAIN] + ".s10"))
    zh, zh_style = _zh_names(game_dir)
    data = [_scenario(game_dir, n) for n in SCENARIOS]
    main = data[MAIN][1]
    rulers = [_rulers(recs, corps) for _, recs, corps in data]

    def series(k, o):
        """distinct u16 values of field o over the scenarios in order, NONE dropped: [(scenario index, value)]"""
        out = []
        for s, (_, recs, _) in enumerate(data):
            v = u16(recs[k], o)
            if v != NONE and (not out or out[-1][1] != v):
                out.append((s, v))
        return out

    fathers = {k: (series(k, 22) or [(0, None)])[0][1] for k in range(PEOPLE)}
    mothers = {k: (series(k, 24) or [(0, None)])[0][1] for k in range(PEOPLE)}
    sworn = {}
    for _, recs, _ in data:
        groups = {}
        for k, r in enumerate(recs):
            if u16(r, 44) != NONE:
                groups.setdefault(u16(r, 44), set()).add(k)
        for g in groups.values():
            for k in g:
                sworn.setdefault(k, set()).update(g - {k})

    rows = []
    for k in range(PEOPLE):
        r, p = main[k], ja[k]
        row = {"id": k, "name": zh[k]}
        if p["name"] != zh[k]:
            row["nameJa"] = p["name"]
        if zh_style[k]:
            row["courtesy"] = zh_style[k]
        row["reading"] = kana_to_hiragana(p["kana"])
        row["born"], row["died"], row["debut"] = u16(r, 13), u16(r, 15), u16(r, 11)
        row["stats"] = dict(zip(sango.SAN10_STATS, r[37:42]))
        row["more"] = {"性別": "女" if r[10] else "男"}
        row["hidden"] = {label: r[o] for label, o in HIDDEN}
        bits = int.from_bytes(r[60:66], "little")
        skills = [s for i, s in enumerate(SKILLS) if bits >> i & 1]
        if skills:
            row["skills"] = {"特技": skills}
        notes = ["能力、特技、隱藏值取劇本 1（184 年）；姓名取繁中版，nameJa 是日文版。"]
        changed = [f"劇本 {s + 1}" for s in range(len(data)) if data[s][1][k][37:42] != r[37:42]
                   or data[s][1][k][60:66] != r[60:66]]
        if changed:
            notes.append(f"能力或特技在{'、'.join(changed)}和劇本 1 不同（劇本裡已成長）。")

        rel = {}
        if fathers[k] is not None and fathers[k] < PEOPLE:
            rel["father"] = [fathers[k]]
        children = [j for j in range(PEOPLE) if fathers[j] == k]
        if children:
            rel["children"] = children
        sib = sorted(j for j in range(PEOPLE) if j != k and (
            fathers[k] is not None and fathers[j] == fathers[k] or mothers[k] is not None and mothers[j] == mothers[k]))
        if sib:
            rel["siblings"] = sib
        if sworn.get(k):
            rel["sworn"] = sorted(sworn[k])
        if u16(r, 20) != NONE:
            rel["clan"] = u16(r, 20)
        if rel:
            row["relations"] = rel
        fs = series(k, 22)
        if len(fs) > 1:
            notes.append("父親隨劇本變：" + "→".join(
                f"劇本 {s + 1} 起 {ja[v]['name'] if v < PEOPLE else v}" for s, v in fs) + "；father 取最早的。")
        for label, o in (("配偶者", 26), ("母親", 24)):
            outside = sorted({v for _, v in series(k, o) if v >= PEOPLE})
            if outside:
                notes.append(f"{label}指到武將以外的記錄 {'、'.join(map(str, outside))}（名字沒找到）。")
        enemies = [(s, v) for s, v in series(k, 46) if v < PEOPLE]
        if enemies:
            notes.append("仇敵：" + "、".join(f"劇本 {s + 1} {ja[v]['name']}" for s, v in enemies) + "。")

        scen = []
        for s, (year, recs, _) in enumerate(data):
            x = recs[k]
            state, rank = x[18], x[19]
            if state == 3:
                continue
            e = {"scenario": s + 1, "year": year}
            if state == 0:
                e["status"], e["debut"] = "未登場", u16(x, 11)
            else:
                e["status"] = STATUS[rank]
                e["location"] = u16(x, 3)
                if x[2] in rulers[s]:
                    e["lord"] = rulers[s][x[2]]
                if rank in (1, 2, 3):
                    e["loyalty"] = x[32]
            scen.append(e)
        if scen:
            row["scenarios"] = scen
        row["uncertain"] = ["died", "debut", "relations.clan", "relations.siblings",
                            *[f"hidden.{label}" for label, _ in HIDDEN], "scenarios.status", "scenarios.lord", "scenarios.location", "scenarios.loyalty"]
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def scenarios_csv(game_dir, path):
    ja_titles, zh_titles = _scenario_titles(game_dir)
    zh, _ = _zh_names(game_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "file", "name", "nameZh", "year", "rulers"])
        for s, name in enumerate(SCENARIOS):
            year, recs, corps = _scenario(game_dir, name)
            rulers = _rulers(recs, corps)
            heads = {corps[c]: k for c, k in rulers.items()}
            w.writerow([s + 1, f"Scenario/{name}.s10", ja_titles[s], zh_titles[s], year,
                        "、".join(zh[heads[f]] for f in sorted(heads))])
    return len(SCENARIOS)


##############################################################################
# 三國志X PK (Steam 628060): the place table at San10WPK.exe 0x480C90 (.rdata, not encrypted by SteamStub; file
# offset = VA - 0x400000), 200 x 12 bytes: name VA, battle file VA, u32 kind (1 城門戦, 2 市街戦, 0 other). 0-49
# cities, 50-118 拠点, 119-143 市街戦 maps, 144-168 平地街道, 169-193 山地街道, 194-199 水路 maps (VA 0x602D00,
# 0x5F86B2). fieldmap.s10: hex cells (rows alternate 100 / 99 cells, x doubled) of 5 bytes: b0 city (50 none), b1
# road kind, b2 place (0-118, one cell each), b3 field map, b4 region bit. ScePK000.s10 0x5804: 69 x 7 bytes of
# 拠点 structures, +1 kind (3 関; all 18 scenarios have the same 8 関).
SAN10_PLACES, SAN10_PLACE_KINDS = 0x480C90, 200


SAN10_EXTRA_GAIJI = {0xE018: "譙", 0xE06B: "祁", 0xE06C: "嶲", 0xE02D: "鄴", 0xE020: "邳", 0xE022: "淄", 0xE024: "并",
                     0xE00B: "兗"}  # place-name gaiji, read off S10Gaiji.tte


SAN10_REGIONS = {62: "河北", 61: "中原", 59: "西北", 55: "巴蜀", 47: "楚", 31: "呉越"}  # b4 -> name (EXE 0x4F4030)


SAN10_MAP_LEVELS = [(119, "市街戦"), (144, "平地街道"), (169, "山地街道"), (194, "水路")]  # first entry, level


def san10_fieldmap(path):
    """{place: (x, row, city, region bits)} of fieldmap.s10 (VA 0x7BFD90) and the map size (2 W, 2 H - 1)."""
    with open(path, "rb") as f:
        d = f.read()
    n = d[0]
    assert d[1:1 + n] == b"San10MainMapEditor"
    p = 1 + n + 4
    w, h = d[p], d[p + 1]
    p += 1 + 0x41
    cells = {}
    for row in range(2 * h - 1):
        for x in range(row & 1, 2 * w - (row & 1), 2):
            b = d[p:p + 5]
            p += 5
            if b[2] != 0xFF:
                cells[b[2]] = (x, row, b[0], b[4])
    return cells, (2 * w, 2 * h - 1)


def places(game_dir, out_dir):
    with open(os.path.join(game_dir, "San10WPK.exe"), "rb") as f:
        exe = f.read()
    gaiji = {**sango.SAN10_GAIJI, **SAN10_EXTRA_GAIJI}

    def s(va):
        o = va - 0x400000
        return _gaiji(exe[o:exe.index(b"\0", o)].decode("cp932"), gaiji)

    table = [struct.unpack_from("<3I", exe, SAN10_PLACES + 12 * i) for i in range(SAN10_PLACE_KINDS)]
    cells, (w, h) = san10_fieldmap(os.path.join(game_dir, "fieldmap.s10"))
    with open(os.path.join(game_dir, "ScePK000.s10"), "rb") as f:
        sce = f.read()
    gates = {50 + i for i in range(69) if sce[0x5804 + 7 * i + 1] == 3}
    rows = []
    for i, (name, _, _) in enumerate(table):
        row = {"id": i, "name": s(name)}
        if i < 119:
            x, y, city, bits = cells[i]
            row["level"] = "都市" if i < 50 else "関" if i in gates else "拠点"
            if i >= 50 and city < 50:
                row["parentCity"] = city
            row["region"] = SAN10_REGIONS[bits]
            row["pos"] = {"x": x, "y": y, "grid": "hex-doubled", "w": w, "h": h}
            row["uncertain"] = ["region"] + (["parentCity"] if "parentCity" in row else [])
            notes = ["地方是大地圖格子的地方位元，位元和地方名的對應照地理推定。"]
            if i >= 50:
                notes.append("所屬都市是大地圖上這個拠点那一格的所屬都市（沒有靜態表）。")
            if i in gates:
                notes.append("遊戲裡是拠点，工作物是関（18 個劇本都有）。")
            notes.append("沒有相鄰表，部隊在大地圖的六角格上沿街道走。pos 是大地圖六角格（列交錯，x 用兩倍寬座標）。"
                         "戰場圖晚點補（城門戰、拠点、市街戰、街道共 200 張）。")
            row["notes"] = "".join(notes)
        else:
            row["level"] = [lv for first, lv in SAN10_MAP_LEVELS if first <= i][-1]
            row["uncertain"] = ["level"]
            row["notes"] = ("不是地名，是地點表裡的戰場圖項目：市街戦是都市城門突破後的戰場，平地街道、山地街道、"
                            "水路是街道上遭遇時依那一格指定的戰場。level 是這邊照名稱的分類。")
        rows.append(row)
    return rows


def stats(game_dir):
    exe, sce = os.path.join(game_dir, "San10WPK.exe"), os.path.join(game_dir, "ScePK000.s10")
    chars = {p["id"]: p["name"] for p in sango.load_san10_persons(exe, sce)}
    return _pick(sango.load_san10_stats(exe, sce), sango.SAN10_STATS, chars)
