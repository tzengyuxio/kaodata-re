"""織田信長傳 (eiketsu4-win): persons for koei-wiki (koei-persons/1). Fields and evidence: notes/eiketsu4.md
「koei-wiki 匯出」.

- DATA.E4 part 0: 77-byte records (koei_stats.load_eiketsu4_win_stats; read by Ekd4.EXE 0x403190): +56..+59 攻擊力
  防禦力 智力 運氣, +60 u16 最大耐久力, +62 最大技能值, +63..+64 命中力 敏捷 (named by label order only), +65 兵種,
  +66 等級, +33..+40 得意技 and +41..+48 特性 (told apart by content), +69..+76 items.
- ids are the kaodata ids: records outside troops and generic NPCs, merged by EIKETSU4_WIN_ALIASES, in first-seen
  order, as kaodata_export.build_eiketsu4_win.
- Event records (603-639) hold the default values 10/100; they get no stats. Of a person's records the one under the
  person's own name is used, else the first that is not a default.
"""
import os

import kaodata_export as K
import koei_stats as S

UNCERTAIN = ["stats.技能值", "stats.命中力", "stats.敏捷", "skills"]
DEFAULT = (10, 10, 10, 10, 100, 10, 10, 10)


def persons(game_dir: str) -> list[dict]:
    stats = S.load_eiketsu4_win_stats(os.path.join(game_dir, "DATA.E4"))
    records = {}  # person -> record numbers, in kaodata order
    for i, r in enumerate(stats):
        if i in K.EIKETSU4_WIN_TROOPS or i in K.EIKETSU4_WIN_FOLK or r[1] in K.EIKETSU4_WIN_NOT_PEOPLE:
            continue
        records.setdefault(K.EIKETSU4_WIN_ALIASES.get(r[1], r[1]), []).append(i)
    rows = []
    for name, nums in records.items():
        row = {"id": len(rows), "name": name}
        real = [i for i in nums if tuple(stats[i][2:10]) != DEFAULT]
        pick = next((i for i in real if stats[i][1] == name), real[0] if real else None)
        notes = []
        if pick is None:
            notes.append(f"DATA.E4 第 0 段第 {'、'.join(map(str, nums))} 筆只有預設值（能力 10、耐久力 100），"
                         "是事件用的記錄，不填能力。")
        else:
            _, rec, atk, dfn, chi, luck, hp, tech, hit, agi, cls, level, tokui, traits, items = stats[pick]
            row["stats"] = {"攻擊力": atk, "防禦力": dfn, "智力": chi, "運氣": luck,
                            "技能值": tech, "命中力": hit, "敏捷": agi}
            row["more"] = {"耐久力": hp}
            row["game"] = {"兵種": cls, "等級": level}
            if items:
                row["game"]["道具"] = items.split("/")
            skills = {k: v.split("/") for k, v in (("得意技", tokui), ("特性", traits)) if v}
            if skills:
                row["skills"] = skills
            row["uncertain"] = UNCERTAIN
            notes.append(f"DATA.E4 第 0 段第 {pick} 筆" + (f"（遊戲寫作{rec}）" if rec != name else "") + "。"
                         "攻擊力到最大技能值的位置由 Ekd4.EXE 0x403190 確認；耐久力、技能值是最大值；命中力、敏捷只照畫面"
                         "標籤的順序對上；得意技和特性兩組只靠內容分辨（主動的招式、被動的加成）。")
            others = [i for i in real if i != pick]
            if others:
                notes.append("另有記錄" + "、".join(f"第 {i} 筆（{stats[i][1]}，能力{'相同' if stats[i][2:15] == stats[pick][2:15] else '不同'}）"
                                         for i in others) + "，未採用。")
        if name in K.EIKETSU4_WIN_NAME_HISTORICAL:
            notes.append(f"遊戲寫作{name}，史書作{K.EIKETSU4_WIN_NAME_HISTORICAL[name]}。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows
