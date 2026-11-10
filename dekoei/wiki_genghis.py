"""蒼き狼と白き牝鹿・ジンギスカン (genghis-pc98) for koei-wiki: persons (koei-persons/1). Read from the
genghis-extras output (extract/persons.csv, both 篇 of MDATA.CIM / SDATA.CIM); name is the DOS 中文版 spelling, nameJa
the PC-98 one. id is the kaodata genghis-pc98 id, which keeps one character per name across the two 篇. Field
sources: notes/genghis.md「能力」「人物欄位」「koei-wiki 匯出」."""
import csv
import json
import os
import unicodedata

import kaodata_export as ke

SCENARIOS = {"mongol": ("蒙古篇", 1175, 100), "world": ("世界篇", 1205, 0)}  # name, year of 年齢, place id base
ABILITIES = ["統率力", "判断力", "企画力", "説得力", "体力", "武力"]
STATUS = {"ruler": "君主", "family": "繼承人", "son": "子女", "general": "部將", "woman": "女性"}
NOTES = {
    "ruler": "君主的 6 項能力是劇本的存值；テムジン／ジンギスカン 開局時重新分配（「次に１００ポイントを…」）。",
    "family": "繼承人分 4 組，每組屬於哪位君主是照名字推的（遊戲開局才填），`lord` 與 `clan` 照這個填。",
    "son": "子女分 4 組，屬於哪位君主是照名字推的，`father` 照這個填；女兒的能力是 0。",
    "general": "部將是「優秀な人物」的候補名單，沒有所在國；`more.基本能力値` 升格成繼承人時 6 項能力各取它的 80–119%。",
    "woman": "女性的 `所属` 在劇本裡都是未所屬。",
}


def _key(name):
    """kaodata names are NFKC without the space between family and given name."""
    return unicodedata.normalize("NFKC", name).replace(" ", "")


def _rows(game_dir):
    with open(os.path.join(game_dir, "extract", "persons.csv"), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def persons(game_dir):
    meta, _ = ke.DATASETS["genghis-pc98"](game_dir)
    ids = {_key(c["name"]): c["id"] for c in meta["characters"]}
    historical = {c["id"]: c["nameZh"] for c in meta["characters"]}
    rows = _rows(game_dir)
    out = {}
    rulers = {(r["scenario"], r["name"]): ids[_key(r["name"])] for r in rows if r["kind"] == "ruler"}
    for r in rows:
        pid = ids[_key(r["name"])]
        sc_name, year, base = SCENARIOS[r["scenario"]]
        p = out.setdefault(pid, {"id": pid, "name": r["nameZh"], "kinds": [], "scenarios": [], "ages": []})
        if r["name"] != r["nameZh"]:
            p["nameJa"] = r["name"]
        if historical[pid] != r["nameZh"]:
            p["historical"] = historical[pid]
        kind = r["kind"]
        p["kinds"].append(kind)
        s = {"scenario": sc_name, "status": STATUS[kind]}
        if kind == "ruler":
            s.update(lord=pid, location=base + int(r["国"]))
            p.setdefault("stats", {k: int(r[k]) for k in ABILITIES})
            p.setdefault("hidden", {})["+28"] = int(r["+28"])
        elif kind in ("family", "son"):
            lord = rulers[r["scenario"], r["family"]]
            s["lord"] = lord
            if kind == "family":
                p.setdefault("stats", {k: int(r[k]) for k in ABILITIES})
                p.setdefault("hidden", {})["+28"] = int(r["+28"])
                if r["+28"] == "0":
                    p.setdefault("clan", set()).add(lord)
            else:
                p.setdefault("more", {}).setdefault("基本能力値", int(r["基本能力値"]))
                p.setdefault("game", {})["性別"] = "男" if r["男子"] == "1" else "女"
                p.setdefault("fathers", set()).add(lord)
        elif kind == "general":
            more = p.setdefault("more", {})
            more.setdefault("基本能力値", int(r["基本能力値"]))
            more.setdefault("血縁値", int(r["血縁値"]))
            if r["存在"] == "1":
                s["status"] = "部將（未發掘）"
        else:
            p.setdefault("game", {})["性格"] = r["性格"]
        if r["年齢"]:
            p["ages"].append(f"{sc_name}（{year} 年）{r['年齢']} 歲")
            p.setdefault("more", {}).setdefault("年齢", int(r["年齢"]))
        p["scenarios"].append(s)

    # clan: a ruler and the family of his group who are 一族 (+28 = 0) share the ruler's id as the group number
    children = {}
    for p in out.values():
        for f in p.get("fathers", ()):
            children.setdefault(f, []).append(p["id"])
    result = []
    for pid in sorted(out):
        p = out[pid]
        row = {"id": pid, "name": p["name"]}
        if "nameJa" in p:
            row["nameJa"] = p["nameJa"]
        for k in ("stats", "more", "hidden", "game"):
            if k in p:
                row[k] = p[k]
        rel = {}
        if p.get("fathers"):
            rel["father"] = sorted(p["fathers"])
        if pid in children:
            rel["children"] = sorted(children[pid])
        clan = p.get("clan") or ({pid} if any(pid in q.get("clan", ()) for q in out.values()) else set())
        if len(clan) == 1:
            rel["clan"] = next(iter(clan))
        if rel:
            row["relations"] = rel
        row["scenarios"] = p["scenarios"]
        uncertain = []
        if "hidden" in row:
            uncertain.append("hidden.+28")
        if any(k in ("family", "son") for k in p["kinds"]) or pid in children:
            uncertain.append("relations")
        if uncertain:
            row["uncertain"] = uncertain
        notes = [NOTES[k] for k in dict.fromkeys(p["kinds"])]
        if p["ages"]:
            notes.append("年齢是劇本的存值：" + "、".join(p["ages"]) + "；兩篇都有的人，`stats`、`more` 取蒙古篇的值。兩篇的年齡差不一定等於 30，沒有換算生年。")
        if "hidden" in row:
            notes.append("`hidden.+28` 是一族記號（0＝一族；1、2 的名稱不知道，2 比 1 親近）。")
        if "historical" in p:
            notes.append(f"史書寫法：{p['historical']}。")
        if p.get("nameJa") in ("テムジン", "ジンギスカン"):
            notes.append(f"テムジン（蒙古篇）和ジンギスカン（世界篇）是同一人，kaodata 依名字分成兩個 id"
                         f"（{ids['テムジン']}、{ids['ジンギスカン']}）。")
        row["notes"] = "".join(notes)
        result.append(row)
    return result


if __name__ == "__main__":
    for r in persons("../games/genghis-pc98")[:5]:
        print(json.dumps(r, ensure_ascii=False))
