"""成吉思汗 蒼狼與白鹿IV 威力加強版 (genghis4pk-win, Win 中文版) for koei-wiki: persons (koei-persons/1) and the 列傳
(biography.py). Read from the 4 scenario files (genghis4_extras.load_scenario) and MESSAGE.CK. id is the kaodata
genghis4pk-win id: one character per (sex, name, face) over scenarios 1-4, men then women, which is not the game's
person number (+0, shared by all scenarios). Field sources: notes/genghis4.md「人物欄位」「列傳」「koei-wiki 匯出」."""
import os

import genghis4_extras as g4
import kaodata_export as ke

BIO_LANG = "zh-Hant"
STATUS = {1: "未登場", 2: "將軍", 3: "在野", 4: "君主", 5: "未登場（子女）", 6: "將軍"}  # +44 bits 0-2; 6 becomes 2
NOT_RECORDED = 501  # father numbers 501-512: a father without a record, shared by brothers


def _scenarios(game_dir):
    return {k: g4.load_scenario(game_dir, k) for k in range(1, 5)}


def _ids(scenarios):
    """{(sex, name, face): kaodata id}, as build_genghis4pk_win numbers them."""
    ids = {}
    for k, sc in scenarios.items():
        for sex, people in enumerate((sc["men"], sc["women"])):
            for p in people:
                key = (sex, p["name"], min(p["face"], ke.GENGHIS4PK_WIN_SHEETS[sex][2]))
                ids.setdefault(key, len(ids))
    return ids


def _key(sex, p):
    return sex, p["name"], min(p["face"], ke.GENGHIS4PK_WIN_SHEETS[sex][2])


def _bio_rows(game_dir, scenarios):
    """{game person number: (name, born, died, text)} from MESSAGE.CK (genghis4_extras.biographies)."""
    msgs = g4.load_messages(game_dir)
    numbers = sorted({m["id"] for sc in scenarios.values() for m in sc["men"]})
    out = {}
    for n in range(max(numbers) + 1):
        name, _, years = g4._text(msgs[7000 + n]).rpartition(" ")
        born, _, died = years.partition("∼")
        out[n] = (name, born, died, g4._text(msgs[g4.bio_id(n)]))
    return out


def _numbers(scenarios, ids):
    """{kaodata id: [game person numbers]} of the men."""
    out = {}
    for sc in scenarios.values():
        for m in sc["men"]:
            nums = out.setdefault(ids[_key(0, m)], [])
            if m["id"] not in nums:
                nums.append(m["id"])
    return out


def persons(game_dir):
    scenarios = _scenarios(game_dir)
    ids = _ids(scenarios)
    numbers = _numbers(scenarios, ids)
    bios = _bio_rows(game_dir, scenarios)
    regions = {r["id"]: r["name"] for r in scenarios[1]["regions"]}
    out, children, spouses = {}, {}, {}
    for k, sc in scenarios.items():
        men = [ids[_key(0, m)] for m in sc["men"]]
        cities = sc["cities"]
        rulers = [c["ruler"] for c in sc["countries"]]
        by_father = {}
        for i, m in enumerate(sc["men"]):
            if m["father"] < len(men) or NOT_RECORDED <= m["father"] <= NOT_RECORDED + 11:
                by_father.setdefault(m["father"], []).append(men[i])
        for i, m in enumerate(sc["men"]):
            pid = men[i]
            p = out.setdefault(pid, {"id": pid, "name": m["name"], "sex": 0, "scenarios": [], "rel": {}})
            p.setdefault("stats", {"政治": m["pol"], "戰鬥": m["war"], "智謀": m["int"]})
            p.setdefault("aptitude", dict(zip(g4.APTITUDES, m["apt"])))
            skills = [s for b, s in enumerate(g4.SKILLS) if m["skills"] >> b & 1]
            if skills:
                p.setdefault("skills", {"特技": skills})
            p.setdefault("more", {"出身": regions[m["region"]]})
            if m["father"] < len(men):
                p["rel"].setdefault("father", set()).add(men[m["father"]])
                children.setdefault(men[m["father"]], set()).add(pid)
            if m["grandfather"] < len(men):
                p.setdefault("game", {})["祖父"] = sc["men"][m["grandfather"]]["name"]
            for b in by_father.get(m["father"], []):
                if b != pid:
                    p["rel"].setdefault("siblings", set()).add(b)
            status = m["status"] & 7
            s = {"scenario": k, "year": sc["year"], "status": STATUS.get(status, str(status))}
            if m["city"] < len(cities):
                city = cities[m["city"]]
                s["location"] = city["id"]
                if status == 4:
                    s["lord"] = pid
                elif status in (2, 6) and city["owner"] < len(sc["countries"]):
                    s["lord"] = men[rulers[city["owner"]]]
            if status not in (1, 4, 5):
                s["loyalty"] = m["loyalty"]
            if status in (1, 5) and m["appear_year"]:
                s["debut"] = m["appear_year"]
            p["scenarios"].append(s)
        for w in sc["women"]:
            pid = ids[_key(1, w)]
            p = out.setdefault(pid, {"id": pid, "name": w["name"], "sex": 1, "scenarios": [], "rel": {}})
            p.setdefault("more", {"出身": regions[w["region"]], "文化傾向": w["culture"]})
            s = {"scenario": k, "year": sc["year"], "status": "妃子"}
            if w["husband"] < len(men):
                husband = men[w["husband"]]
                p["rel"].setdefault("spouse", set()).add(husband)
                spouses.setdefault(husband, set()).add(pid)
            p["scenarios"].append(s)

    result = []
    for pid in sorted(out):
        p = out[pid]
        row = {"id": pid, "name": p["name"]}
        uncertain, notes = [], []
        if p["sex"] == 0:
            nums = numbers[pid]
            name, born, died, _ = bios[nums[0]]
            for key, v in (("born", born), ("died", died)):
                if v.isdigit():
                    row[key] = int(v)
                else:
                    uncertain.append(key)
            if "born" in uncertain or "died" in uncertain:
                notes.append("生卒年表寫 ????（不明），沒有填。")
            if len(nums) > 1:
                notes.append(f"遊戲的人物號有 {len(nums)} 個（{'、'.join(map(str, nums))}），名字與頭像相同，kaodata 當同一人；"
                             f"生卒年、列傳取人物號 {nums[0]}。")
        for key in ("stats", "more", "aptitude", "skills", "game"):
            if key in p:
                row[key] = p[key]
        rel = {k: sorted(v) for k, v in p["rel"].items()}
        if pid in children:
            rel["children"] = sorted(children[pid])
        if pid in spouses:
            rel["spouse"] = sorted(set(rel.get("spouse", [])) | spouses[pid])
        if rel:
            row["relations"] = rel
        row["scenarios"] = p["scenarios"]
        if "skills" in row:
            uncertain.append("skills")
            notes.append("特技 12 項的位元順序是推定的。")
        if p["sex"] == 1:
            uncertain.append("more.文化傾向")
            notes.append("妃子沒有列傳；`more.文化傾向` 是 0–9 的存值，意義沒確認。")
        if any(s["status"] == "未登場（子女）" for s in row["scenarios"]):
            notes.append("「未登場（子女）」是身分 5，劇本開始時還沒登場的子女，沒有登場年。")
        if "game" in row:
            notes.append("`game.祖父` 是劇本記錄的祖父。")
        if rel.get("siblings"):
            notes.append("`siblings` 是同一劇本裡父親相同的人（父親沒有記錄的，遊戲用共用的號碼 501–512 表示兄弟）。")
        if uncertain:
            row["uncertain"] = uncertain
        if notes:
            row["notes"] = "".join(notes)
        result.append(row)
    return result


def bios(game_dir):
    """{kaodata id: [("單段", text)]}: the 列傳 of the game person number, for the men with a scenario record."""
    scenarios = _scenarios(game_dir)
    rows = _bio_rows(game_dir, scenarios)
    return {pid: [("單段", rows[nums[0]][3])] for pid, nums in _numbers(scenarios, _ids(scenarios)).items()
            if rows[nums[0]][3]}


def bio_names(game_dir):
    scenarios = _scenarios(game_dir)
    ids = _ids(scenarios)
    return {i: name for (sex, name, _), i in ids.items() if sex == 0}
