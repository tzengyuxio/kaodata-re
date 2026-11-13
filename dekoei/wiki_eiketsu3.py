"""毛利元就傳 (eiketsu3-win): persons for koei-wiki (koei-persons/1). Fields and evidence: notes/eiketsu3.md
「koei-wiki 匯出」.

- DATA.E3 part 0: 54-byte records (koei_stats.load_eiketsu3_win_stats; read by 毛利元就傳_Gr.EXE 0x402922): +33..+36 攻擊力
  防禦力 智力 運氣, +37 u16 耐久力, +39..+41 技能值 命中率 敏捷 (named by label order only), +42 兵種, +43 等級,
  +46..+53 items (part 1 names).
- ids are the kaodata ids: EIKETSU3_WIN_PEOPLE in order, merged by EIKETSU3_WIN_ALIASES, as
  kaodata_export.build_eiketsu3_win.
- Story-only records hold placeholder values (all eight numbers 1, or all 50); they get no stats. Of a person's
  records the one under the person's own name is used, else the first that is not a placeholder.
"""
import os

import kaodata_export as K
import koei_stats as S

UNCERTAIN = ["stats.技能值", "stats.命中率", "stats.敏捷"]


def placeholder(r) -> bool:
    return len(set(r[2:10])) == 1


def persons(game_dir: str) -> list[dict]:
    stats = S.load_eiketsu3_win_stats(os.path.join(game_dir, "DATA.E3"))
    records = {}  # person -> record numbers, in kaodata order
    for i in K.EIKETSU3_WIN_PEOPLE:
        records.setdefault(K.EIKETSU3_WIN_ALIASES.get(stats[i][1], stats[i][1]), []).append(i)
    rows = []
    for name, nums in records.items():
        row = {"id": len(rows), "name": name}
        real = [i for i in nums if not placeholder(stats[i])]
        pick = next((i for i in real if stats[i][1] == name), real[0] if real else None)
        notes = []
        if pick is None:
            notes.append(f"DATA.E3 第 0 段第 {'、'.join(map(str, nums))} 筆只有佔位值（八項都是 {stats[nums[0]][2]}），"
                         "是劇情用的記錄，不填能力。")
        else:
            _, rec, atk, dfn, chi, luck, hp, tech, hit, agi, cls, level, items = stats[pick]
            row["stats"] = {"攻擊力": atk, "防禦力": dfn, "智力": chi, "運氣": luck,
                            "技能值": tech, "命中率": hit, "敏捷": agi}
            row["more"] = {"耐久力": hp}
            row["game"] = {"兵種": cls, "等級": level or 1}
            if items:
                row["game"]["道具"] = items.split("/")
            row["uncertain"] = UNCERTAIN
            notes.append(f"DATA.E3 第 0 段第 {pick} 筆" + (f"（遊戲寫作{rec}）" if rec != name else "") + "。"
                         "攻擊力到耐久力的位置由 毛利元就傳_Gr.EXE 0x402922 確認；技能值、命中率、敏捷只照畫面標籤的順序對上。")
            others = [i for i in real if i != pick]
            if others:
                notes.append("另有記錄" + "、".join(f"第 {i} 筆（{stats[i][1]}，能力{'相同' if stats[i][2:13] == stats[pick][2:13] else '不同'}）"
                                         for i in others) + "，未採用。")
        if name in K.EIKETSU3_WIN_NAME_HISTORICAL:
            notes.append(f"遊戲寫作{name}，史書作{K.EIKETSU3_WIN_NAME_HISTORICAL[name]}。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows
