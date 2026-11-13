"""維新の嵐 (ishin-pc98) for koei-wiki: persons (koei-persons/1) and places (koei-places/1). id is the kaodata ishin-pc98 id: 0-422 are the
historical people of ISIN.EXE, and the successors that take over a record under another given name in scenarios 2-3
follow from 423 in the order kaodata_export.build_ishin_pc98 makes them. Field sources: notes/koei-games.md
「維新の嵐」「能力」「koei-wiki 匯出」."""
import os

import kaodata_export as ke
import koei_games as kg
import koei_stats as ks

DATASET = "ishin-pc98"
# ISIN.EXE 0x3E672: 嘉永６年（１８５８）１月２８日、文久３年（１８６３）５月１０日、慶応３年（１８６７）１１月１５日
SCENARIO_DATES = [(1858, 1), (1863, 5), (1867, 11)]
ON_STAGE = 0x40  # +0x1B of the 28-byte record: set for the people on the map in that scenario (🟡, from the values)
THOUGHTS = ("尊王", "公議", "佐幕", "攘夷")  # +0x16..+0x19 (🟡, from the values)
LEADERS = {"藩主", "将軍", "天皇"}
# ISIN.EXE file offsets. 場所名: 87 provinces (the first 66 are the 66 hans' provinces, in the han order) then the 9
# towns 江戸-横浜, 7 bytes each. Map nodes: 6 bytes each, node 1-401: +0 場所 + 1, +1 地区, +3 / +4 the hex column /
# row (towns: their 4 x 4 grid, rows from 101), +2 / +5 not known. A person's location (19-byte record +0 u16) is a node.
PLACE_NAMES, N_PLACES, N_HANS = 0x42072, 96, 66
NODES, N_NODES = 0x29F9A, 402
REGIONS = ("東北１", "東北２", "関東", "信越", "近畿", "中四国", "九州")  # 地区, ISIN.EXE 0x3AD9A


def _scenarios(game_dir):
    with open(os.path.join(game_dir, "ISIN.EXE"), "rb") as f:
        exe = f.read()
    with open(os.path.join(game_dir, "SHINARIO.DAT"), "rb") as f:
        sc = f.read()
    (b0, bs), (a0, as_) = ks.ISHIN_PC98_TABLES
    out = []
    for t in range(3):
        s = sc[t * kg.ISHIN_PC98_SCENARIO:][:kg.ISHIN_PC98_SCENARIO]
        hans = [kg._ishin_pc98_text(s[ks.ISHIN_PC98_HANS + i * 7:][:7].split(b"\0")[0]).strip() for i in range(87)]
        recs = []
        for i in range(kg.ISHIN_PC98_PEOPLE):
            b, a = s[b0 + i * bs:][:bs], s[a0 + i * as_:][:as_]
            code = int.from_bytes(b[1:3], "little")
            recs.append({"code": code, "rank": ks.ishin_pc98_rank(code, hans), "on": bool(b[0x1B] & ON_STAGE),
                         "node": int.from_bytes(a[0:2], "little"),
                         "stats": {"武力": a[0xF], "剣道": b[0xC], "学力": b[0xD], "魅力": b[0xE], "原体力": a[0x11]},
                         "more": {"年齢": b[3], "戦闘経験": b[0x12], "レベル": int.from_bytes(b[0x10:0x12], "little")},
                         "thought": dict(zip(THOUGHTS, b[0x16:0x1A]))})
        out.append(recs)
    return exe, out


def _nodes(exe):
    """[(場所 index, 地区 index)] per map node; node 0 is empty."""
    return [(exe[NODES + n * 6] - 1, exe[NODES + n * 6 + 1]) for n in range(N_NODES)]


def _characters(game_dir, scen):
    """(chars, leader, owner): the characters as build_ishin_pc98 numbers them, (record, name, scenarios that use
    the name); per scenario the records of each group's 藩主 / 将軍 / 天皇 on stage; (record, scenario) -> id."""
    chars, later = [], []
    for i, (names, _) in enumerate(kg.load_ishin_pc98_persons(os.path.join(game_dir, "ISIN.EXE"),
                                                              os.path.join(game_dir, "SHINARIO.DAT"))):
        people = {}
        for t, name in enumerate(names):
            people.setdefault(ke.ISHIN_PC98_SAME_PERSON.get(name, name), []).append(t)
        for k, (name, ts) in enumerate(people.items()):
            (later if k else chars).append((i, name, ts))
    chars += later
    leader = []
    for t, recs in enumerate(scen):
        heads = {}
        for i, r in enumerate(recs):
            group, status = _split(r["rank"])
            if r["on"] and group and status in LEADERS:
                heads.setdefault(group, []).append(i)
        leader.append(heads)
    owner = {(i, t): cid for cid, (i, _, ts) in enumerate(chars) for t in ts}
    return chars, leader, owner


def _hans(game_dir):
    """The scenario han names (the same in the three scenarios)."""
    with open(os.path.join(game_dir, "SHINARIO.DAT"), "rb") as f:
        sc = f.read()
    names = [[kg._ishin_pc98_text(sc[t * kg.ISHIN_PC98_SCENARIO + ks.ISHIN_PC98_HANS + i * 7:][:7].split(b"\0")[0])
              .strip() for i in range(N_HANS)] for t in range(3)]
    assert names[0] == names[1] == names[2]
    return names[0]


def places(game_dir, out_dir):
    exe, scen = _scenarios(game_dir)
    chars, leader, owner = _characters(game_dir, scen)
    nodes = _nodes(exe)
    hans = _hans(game_dir)
    region = {}
    for place, r in nodes[1:]:
        assert region.setdefault(place, r) == r
    rows = []
    for k in range(N_PLACES):
        town = k >= 87
        row = {"id": k, "name": kg._ishin_pc98_text(exe[PLACE_NAMES + k * 7:][:7].split(b"\0")[0]).strip(),
               "level": "町" if town else "国", "region": REGIONS[region[k]]}
        if k < N_HANS:
            row["game"] = {"藩": hans[k]}
            out = []
            for t, (year, month) in enumerate(SCENARIO_DATES):
                s = {"scenario": t + 1, "year": year, "month": month}
                heads = leader[t].get(hans[k], [])
                if len(heads) == 1:
                    s["lord"] = owner[(heads[0], t)]
                out.append(s)
            row["scenarios"] = out
        row["uncertain"] = ["level"] + (["region"] if town else [])
        row["notes"] = (f"{'町（9 處，進去有町內地圖）' if town else '國'}；地圖節點 "
                        f"{sum(1 for p, _ in nodes[1:] if p == k)} 個（ISIN.EXE 0x29F9A 的節點表 +0）。"
                        + ("" if town else "名稱是 ISIN.EXE 的場所名表；有藩的國，藩名放 game.藩，"
                           "scenarios 的 lord 是那個劇本在地圖上的藩主。" if k < N_HANS else "")
                        + ("地區取節點表 +1；町的地區和所在地不合（江戸在東北２、京都在信越），原因沒追。" if town else ""))
        rows.append(row)
    return rows


def _split(rank):
    """(group, title): 「土佐藩士」-> ("土佐", "藩士"), 「幕臣」-> ("幕府", "幕臣"); others have no group. The group's
    leader (藩主, 将軍, 天皇 on stage) is the scenario's lord, and the group is more.藩 (the han table's name, or 幕府 /
    朝廷)."""
    for word in ("藩主", "家老", "重臣", "藩士"):
        if rank.endswith(word) and rank != word:
            return rank[:-len(word)], word
    if rank in ("将軍", "老中", "奉行", "幕臣"):
        return "幕府", rank
    if rank in ("天皇", "大臣", "議奏", "朝臣"):
        return "朝廷", rank
    return None, rank


def persons(game_dir):
    exe, scen = _scenarios(game_dir)
    surnames = [kg._ishin_pc98_text(exe[0x42312 + i * 7:][:7].split(b"\0")[0]) for i in range(kg.ISHIN_PC98_PEOPLE)]
    chars, leader, owner = _characters(game_dir, scen)
    nodes = _nodes(exe)

    rows = []
    for cid, (i, name, ts) in enumerate(chars):
        row = {"id": cid, "name": name}
        if surnames[i] and name.startswith(surnames[i]) and name != surnames[i]:
            row["familyName"] = surnames[i]
        on = [t for t in ts if scen[t][i]["on"]]
        top = on[0] if on else ts[0]
        r = scen[top][i]
        row["stats"] = r["stats"]
        group, _ = _split(r["rank"])
        row["more"] = {**r["more"], "身分": r["rank"], **({"藩": group} if group else {}), **r["thought"]}
        out = []
        for t in ts:
            r = scen[t][i]
            year, month = SCENARIO_DATES[t]
            s = {"scenario": t + 1, "year": year, "month": month}
            if not r["on"]:
                s["status"] = "未登場" if not on or t < on[0] else "不在"
            else:
                group, _ = _split(r["rank"])
                s["status"] = r["rank"]
                heads = leader[t].get(group, []) if group else []
                if len(heads) == 1:
                    s["lord"] = owner[(heads[0], t)]
                if 0 < r["node"] < N_NODES:
                    s["location"] = nodes[r["node"]][0]
                s["stats"] = r["stats"]
            out.append(s)
        row["scenarios"] = out
        row["uncertain"] = [f"more.{k}" for k in THOUGHTS]
        notes = []
        if any(x["status"] in ("未登場", "不在") for x in out):
            notes.append("「未登場」「不在」是看劇本開始時有沒有在地圖上（28 bytes 記錄 +0x1B bit 6）：第一次登場前寫未登場，登場過之後寫不在"
                         "（遊戲沒有稱呼，照使用者 2026-11-14 的規則；何時由事件登場沒追，所以沒有 debut）。")
        if any(x["status"] == "不在" for x in out):
            notes.append("登場過之後不在地圖上，推定已死（沒追）。")
        if top:
            notes.append(f"頂層的 stats、more 取劇本 {top + 1}（第一個登場的劇本）。")
        if i != cid:
            notes.append(f"劇本 {'、'.join(str(t + 1) for t in ts)} 接手 {chars[i][1]}（id {i}）的人物記錄。")
        if name in ke.ISHIN_PC98_NAME_HISTORICAL:
            notes.append(f"史書寫法 {ke.ISHIN_PC98_NAME_HISTORICAL[name]}。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows
