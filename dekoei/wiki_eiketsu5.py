"""三國志曹操傳 (eiketsu5-win): persons for koei-wiki (koei-persons/1). Fields and evidence: notes/eiketsu5.md
「koei-wiki 匯出」.

- DATA.E5 part 0: 512 records of 32 bytes (koei_stats.load_eiketsu5_win_stats): +18..+22 武力 統率 智力 敏捷 運氣,
  +23 u16 HP, +25 MP, +26 兵種, +27 等級, +29..+31 武器 護具 輔助 (EKD5.EXE 0x408BD3).
- ids are the kaodata ids: records 0-173 in order, skipping props (赤兔馬…) and the numbered extra looks (劉備99,
  諸葛亮1-4), as kaodata_export.build_eiketsu5_win.
"""
import os

import kaodata_export as K
import koei_stats as S

UNCERTAIN = ["stats.統率", "stats.智力"]


def persons(game_dir: str) -> list[dict]:
    stats = S.load_eiketsu5_win_stats(os.path.join(game_dir, "DATA.E5"))
    rows = []
    for i, name, bu, tou, chi, bin_, un, hp, mp, cls, level, weapon, armor, extra in stats[:174]:
        if name in K.EIKETSU5_WIN_PROPS or name.rstrip("0123456789") != name:
            continue
        row = {"id": len(rows), "name": name, "stats": {"武力": bu, "統率": tou, "智力": chi, "敏捷": bin_, "運氣": un},
               "more": {"HP": hp, "MP": mp}, "game": {"兵種": cls, "等級": level}}
        equip = {k: v for k, v in (("武器", weapon), ("護具", armor), ("輔助", extra)) if v}
        if equip:
            row["game"].update(equip)
        row["uncertain"] = UNCERTAIN
        row["notes"] = (f"DATA.E5 第 0 段第 {i} 筆。五項能力的位置由 EKD5.EXE 0x408BD3 確認；EXE 的訊息順序是武力 智力 統率力，"
                        "和記錄順序不合，第 2、3 項的名稱照數值排名（郭嘉第三項 49、呂布 6）推定為統率、智力。"
                        + (f"遊戲寫作{name}，史書作{K.EIKETSU5_WIN_NAME_HISTORICAL[name]}。"
                           if name in K.EIKETSU5_WIN_NAME_HISTORICAL else ""))
        rows.append(row)
    return rows
