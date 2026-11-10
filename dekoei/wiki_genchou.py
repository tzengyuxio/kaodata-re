"""蒼き狼と白き牝鹿・元朝秘史 (genchou-pc98) for koei-wiki: persons (koei-persons/1). The 4 scenarios' GENDATA men and
women (genchou_extras.persons), the USDATA 登場武將 and 子嗣; name is the DOS 中文版 spelling (games/genchou-pc98/dos,
the same files with Chinese names), nameJa the PC-98 one. id is the kaodata genchou-pc98 id (kaodata_export.genchou_ids:
one character per name, women apart). Field sources: notes/genchou.md「人物」「人物欄位」「koei-wiki 匯出」."""
import os
import struct

import genchou_extras as ge
import kaodata_export as ke
import koei_games
from koei_stats import GENCHOU_GRADES

ABILITIES = ["政治力", "戦闘力", "指揮力", "魅力"]
BLOCK, MAN, CHILD = koei_games.GENCHOU_PC88_BLOCK, 27, 23  # USDATA: 351-byte blocks of 8 men and 5 子嗣


def _man(m, cultures, ranks):
    """stats and more of a 27-byte man record (the GENDATA layout, also used by USDATA)."""
    g = GENCHOU_GRADES
    stats = {"政治力": g[m[20] & 7], "戦闘力": g[m[20] >> 4 & 7], "指揮力": g[m[21] & 7], "魅力": g[m[21] >> 4 & 7]}
    more = {"年齢": m[22], "体力": m[19] & 15, "体力上限": m[19] >> 4, "身分": ranks[m[24] & 3],
            "文化圏": cultures[m[23] >> 2 & 7]}
    if m[24] >> 6 & 1:
        more["重病"] = 1
    return stats, more, {"捕虜台詞": m[23] >> 5}


def persons(game_dir):
    dos_dir = os.path.join(game_dir, "dos")  # the kaodata builder's Chinese people files
    ext_dir = os.path.join(game_dir, os.pardir, "genchou-dos")  # genchou_extras also reads ZNAME.DAT there
    _, ids = ke.genchou_ids(koei_games.load_genchou_pc88_people(game_dir, pc98=True), ke.GENCHOU_PC88_SPLIT, {})
    dos_aliases = {(4, b): a for a, b in ke.GENCHOU_DOS_NAMES.items()}
    _, zh_ids = ke.genchou_ids(koei_games.load_genchou_pc88_people(dos_dir, dos=True), ke.GENCHOU_DOS_SPLIT, dos_aliases)
    name_zh = {i: ke.GENCHOU_DOS_NAMES.get(k[1], k[1]) for k, i in zh_ids.items()}
    historical = {i: ke.GENCHOU_DOS_NAME_HISTORICAL.get(n, n) for i, n in name_zh.items()}
    split = ke.GENCHOU_PC88_SPLIT
    exe = ge._read(game_dir, "MAIN.EXE")
    cultures, ranks = ge._strings(exe, ge.CULTURES), ge._strings(exe, ge.RANKS)

    def pid(sc, woman, name):
        return ids[woman, name, (name, sc) in split]

    out, siblings = {}, {}

    def person(i, name_ja):
        p = out.setdefault(i, {"id": i, "name": name_zh[i], "scenarios": [], "ages": [], "kinds": []})
        if name_ja != p["name"]:
            p["nameJa"] = name_ja
        return p

    for sc in range(1, 5):
        gen = ge._read(game_dir, f"GENDATA{sc}.DAT")
        records = [r for r in ge._records(gen, ge.MEN)]
        base = 100 if sc == 1 else 0
        rows = ge.persons(game_dir, ext_dir, sc)
        men = {r["index"]: r for r in rows if r["table"] == "men" and not r["placeholder"]}
        # all 33 faction records: the +17 numbers go past GENDATA's faction count (genchou_extras.scenario stops there)
        # 劇本 4's Mongol faction is led by the player's placeholder (モンゴル統一者), who is not a person: no lord
        heads = {k: (struct.unpack_from("<H", f, 19)[0] - 0x44) // 27
                 for k, f in enumerate(ge._records(gen, ge.FACTIONS)) if f[:16].strip(b"\0") and not f[21] & 0x80}
        rulers = {k: pid(sc, False, men[h]["name"]) for k, h in heads.items() if h in men}
        for r in rows:
            if r.get("placeholder"):
                continue
            woman = r["table"] == "women"
            i = pid(sc, woman, r["name"])
            p = person(i, r["name"])
            s = {"scenario": sc}
            if r["country"] != "":
                s["location"] = base + r["country"] + 1
            if woman:
                p["kinds"].append("woman")
                s["status"] = "女性"
            else:
                p["kinds"].append("man")
                stats, more, hidden = _man(records[r["index"]], cultures, ranks)
                p.setdefault("stats", stats)
                p.setdefault("more", more)
                p.setdefault("hidden", hidden)
                p["ages"].append(f"劇本 {sc} {more['年齢']} 歲")
                s["status"] = more["身分"] if r["faction"] != "" else f"{more['身分']}（無所屬）"
                if r["faction"] in rulers:
                    s["lord"] = rulers[r["faction"]]
                elif r["faction"] != "":
                    p["player"] = True
                if r["mark"] == "*" and r["faction"] in rulers:  # 君主の兄弟
                    siblings.setdefault(i, set()).add(rulers[r["faction"]])
                    siblings.setdefault(rulers[r["faction"]], set()).add(i)
            p["scenarios"].append(s)
        us = ge._read(game_dir, f"USDATA{sc}.DAT")
        for b in range(0, len(us) - BLOCK + 1, BLOCK):
            for k in range(8):
                m = us[b + k * MAN:][:MAN]
                name = ge._ja(m[:17])
                if not name:
                    continue
                i = pid(sc, False, name)
                p = person(i, name)
                p["kinds"].append("usdata")
                stats, more, hidden = _man(m, cultures, ranks)
                p.setdefault("stats", stats)
                p.setdefault("more", more)
                p.setdefault("hidden", hidden)
                p["scenarios"].append({"scenario": sc, "status": "登場武將"})
            for k in range(5):
                c = us[b + 8 * MAN + k * CHILD:][:CHILD]
                name = ge._ja(c[:17])
                if not name or not int.from_bytes(c[CHILD - 2:], "little"):
                    continue
                key = (False, name, (name, sc) in split)
                if key not in ids:
                    continue
                p = person(ids[key], name)
                p["kinds"].append("child")
                p["scenarios"].append({"scenario": sc, "status": "子嗣"})

    result = []
    for i in sorted(out):
        p = out[i]
        row = {"id": i, "name": p["name"]}
        if "nameJa" in p:
            row["nameJa"] = p["nameJa"]
        for k in ("stats", "more", "hidden"):
            if k in p:
                row[k] = p[k]
        if siblings.get(i):
            row["relations"] = {"siblings": sorted(siblings[i] - {i})}
        # a person can be in a scenario both in GENDATA and as a USDATA entry; keep one entry per scenario and status
        seen, scenarios = set(), []
        for s in p["scenarios"]:
            if (s["scenario"], s["status"]) not in seen:
                seen.add((s["scenario"], s["status"]))
                scenarios.append(s)
        row["scenarios"] = scenarios
        uncertain, notes = [], []
        if "hidden" in row:
            uncertain.append("hidden.捕虜台詞")
            notes.append("`hidden.捕虜台詞` 是被俘時台詞的類型 0–4，名稱是這邊取的。")
        if len(p["ages"]) > 1:
            notes.append("能力、年齢等取第一個出現的劇本；各劇本的年齢：" + "、".join(p["ages"]) + "。")
        if "usdata" in p["kinds"]:
            uncertain.append("scenarios.status")
            notes.append("「登場武將」是劇本的 USDATA 裡的人物，劇本開始時不在場，登場條件沒解，所以沒有 debut。")
        if "child" in p["kinds"]:
            uncertain.append("scenarios.status")
            notes.append("「子嗣」是劇本的 USDATA 裡的子嗣（只收有頭像的兒子），父親是誰沒有欄位。")
        if any(s["status"].endswith("（無所屬）") for s in scenarios):
            notes.append("「（無所屬）」是沒有所屬勢力（+17＝FF），身分照存值。")
        if i in historical and historical[i] != row["name"]:
            notes.append(f"史書寫法：{historical[i]}。")
        if p.get("player"):
            notes.append("劇本 4 屬於玩家的蒙古勢力（君主是玩家自己建的「蒙古統一者」，不是人物），所以沒有 `lord`。")
        if row.get("relations"):
            notes.append("`siblings` 來自 +23 的「君主的兄弟」記號（`*`），只連到同劇本的君主。")
        if uncertain:
            row["uncertain"] = list(dict.fromkeys(uncertain))
        if notes:
            row["notes"] = "".join(notes)
        result.append(row)
    return result
