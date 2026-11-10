"""三國志孔明傳 (koumei-win): persons for koei-wiki (koei-persons/1). Fields and evidence: notes/koumei.md
「koei-wiki 匯出」.

- BAKDATA.E2 0x18F0: 512 records of 17 bytes (sango.load_koumei_persons); 0x3AF0: 512 x 26 bytes, one per record
  (koei_stats.load_koumei_win_stats): +1 武力, +2 統御力, +3 智力, +4 u16 耐久力?, +6 策略值?, +8 兵種, +9 等級,
  +11..+25 equipment.
- ids are the kaodata ids: names in order of their first record, skipping troops and townsfolk; a name's first
  record holds the stats (the ending's repeats 498-506 are all 0); four non-combatants have an all-0 row and no stats.
"""
import os

import kaodata_export as K
import koei_stats as S
import sango

UNCERTAIN = ["stats", "more.耐久力", "more.策略值", "game.兵種", "game.道具"]


def persons(game_dir: str) -> list[dict]:
    path = os.path.join(game_dir, "BAKDATA.E2")
    generic = K.KOUMEI_WIN_TROOPS | K.KOUMEI_WIN_FOLK
    stats = S.load_koumei_win_stats(path)
    first = {}
    for i, (name, _) in enumerate(sango.load_koumei_persons(path)):
        if name not in generic:
            first.setdefault(name, i)
    rows = []
    for name, i in first.items():
        _, _, bu, chi, tou, hp, sp, cls, level, items = stats[i]
        row = {"id": len(rows), "name": name}
        if not any((bu, chi, tou, hp, sp)):  # non-combatants (黃承彥, 獻帝…): the whole stats row is 0
            row["notes"] = f"BAKDATA.E2 第 {i} 筆的能力表全是 0（不參戰的人物），不填能力。"
            rows.append(row)
            continue
        row.update({"stats": {"武力": bu, "統御力": tou, "智力": chi}, "more": {"耐久力": hp, "策略值": sp},
                    "game": {"兵種": cls, "等級": level}})
        if items:
            row["game"]["道具"] = items.split("/")
        row["uncertain"] = UNCERTAIN
        row["notes"] = (f"BAKDATA.E2 第 {i} 筆（這個名字的第一筆記錄）的能力表。讀取程式沒追，欄位都是推定：武力、統御力、智力"
                        "照 EXE 的標籤字串和數值排名對應，耐久力、策略值只依數值推定；兵種名照 EKD2.EXE 字串順序；"
                        "等級在記錄裡都是 1。"
                        + (f"遊戲寫作{name}，史書作{K.KOUMEI_WIN_NAME_HISTORICAL[name]}。"
                           if name in K.KOUMEI_WIN_NAME_HISTORICAL else ""))
        rows.append(row)
    return rows
