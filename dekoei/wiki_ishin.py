"""維新の嵐 (ishin-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata ishin-pc98 id: 0-422 are the
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
                         "stats": {"武力": a[0xF], "剣道": b[0xC], "学力": b[0xD], "魅力": b[0xE], "原体力": a[0x11]},
                         "more": {"年齢": b[3], "戦闘経験": b[0x12], "レベル": int.from_bytes(b[0x10:0x12], "little")},
                         "thought": dict(zip(THOUGHTS, b[0x16:0x1A]))})
        out.append(recs)
    return exe, out


def _split(rank):
    """(group, title): 「土佐藩士」-> ("土佐", "藩士"), 「幕臣」-> ("幕府", "幕臣"); others have no group. The group's
    leader (藩主, 将軍, 天皇 on stage) is the scenario's lord."""
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
    # the characters as build_ishin_pc98 numbers them: (record, name, scenarios that use the name)
    chars, later = [], []
    for i, (names, _) in enumerate(kg.load_ishin_pc98_persons(os.path.join(game_dir, "ISIN.EXE"),
                                                              os.path.join(game_dir, "SHINARIO.DAT"))):
        people = {}
        for t, name in enumerate(names):
            people.setdefault(ke.ISHIN_PC98_SAME_PERSON.get(name, name), []).append(t)
        for k, (name, ts) in enumerate(people.items()):
            (later if k else chars).append((i, name, ts))
    chars += later

    # the leader of each group in each scenario: the 藩主 / 将軍 / 天皇 on stage
    leader = []
    for t, recs in enumerate(scen):
        heads = {}
        for i, r in enumerate(recs):
            group, status = _split(r["rank"])
            if r["on"] and group and status in LEADERS:
                heads.setdefault(group, []).append(i)
        leader.append(heads)
    owner = {(i, t): cid for cid, (i, _, ts) in enumerate(chars) for t in ts}

    rows = []
    for cid, (i, name, ts) in enumerate(chars):
        row = {"id": cid, "name": name}
        if surnames[i] and name.startswith(surnames[i]) and name != surnames[i]:
            row["familyName"] = surnames[i]
        on = [t for t in ts if scen[t][i]["on"]]
        top = on[0] if on else ts[0]
        r = scen[top][i]
        row["stats"] = r["stats"]
        row["more"] = {**r["more"], "身分": r["rank"], **r["thought"]}
        out = []
        for t in ts:
            r = scen[t][i]
            year, month = SCENARIO_DATES[t]
            s = {"scenario": t + 1, "year": year, "month": month}
            if not r["on"]:
                s["status"] = "不在" if not on or t < on[0] else "死亡"
            else:
                group, _ = _split(r["rank"])
                s["status"] = r["rank"]
                heads = leader[t].get(group, []) if group else []
                if len(heads) == 1:
                    s["lord"] = owner[(heads[0], t)]
                s["stats"] = r["stats"]
            out.append(s)
        row["scenarios"] = out
        row["uncertain"] = [f"more.{k}" for k in THOUGHTS]
        notes = []
        if any(x["status"] in ("不在", "死亡") for x in out):
            row["uncertain"].append("scenarios.status")
            notes.append("「不在」「死亡」是看劇本開始時有沒有在地圖上推的：第一次登場前寫不在（之後是否由事件登場沒追），登場過之後不在寫死亡。")
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
