"""三國志英傑傳 (eiketsu-dos, eiketsu-pc98): persons for koei-wiki (koei-persons/1). Fields and evidence:
notes/eiketsu.md「koei-wiki 匯出」.

- BAKDATA.R3 0x1100: 384 records of 21 bytes; +6..+13 the reading (half-width katakana, NUL-terminated), +17 統率,
  +18 武力, +19 知力. The initial state table (koei_stats.load_eiketsu_dos_stats) gives 兵種, 等級, 兵力, 士氣, 道具.
- ids are the kaodata ids: records in file order, skipping the troop and folk names (264 characters).
"""
import os
import unicodedata

import kaodata_export as K
import koei_stats as S

UNCERTAIN = ["stats.知力", "stats.統率", "game.兵種"]


def persons(game_dir: str, pc98: bool = None) -> list[dict]:
    if pc98 is None:
        pc98 = "pc98" in os.path.basename(os.path.normpath(game_dir))
    troops, folk, historical = ((K.EIKETSU_PC98_TROOPS, K.EIKETSU_PC98_FOLK, K.EIKETSU_PC98_NAME_HISTORICAL) if pc98 else
                                (K.EIKETSU_DOS_TROOPS, K.EIKETSU_DOS_FOLK, K.EIKETSU_DOS_NAME_HISTORICAL))
    path = os.path.join(game_dir, "BAKDATA.R3")
    with open(path, "rb") as f:
        data = f.read()
    start, _, size = K.koei_games.EIKETSU_DOS_PERSONS
    rows = []
    for slot, name, bu, chi, tou, cls, level, troops_n, morale, items in S.load_eiketsu_dos_stats(path, pc98):
        if name in troops | folk:
            continue
        row = {"id": len(rows), "name": name}
        if pc98:
            raw = data[start + slot * size + 6:][:8].split(b"\0")[0]
            row["reading"] = unicodedata.normalize("NFKC", raw.decode("cp932"))
        row["stats"] = {"武力": bu, "知力": chi, "統率": tou}
        row["more"] = {"兵力": troops_n, "士氣": morale}
        row["game"] = {"兵種": cls, "等級": level}
        if items:
            row["game"]["道具"] = items.split("/")
        row["uncertain"] = UNCERTAIN
        row["notes"] = (f"BAKDATA.R3 第 {slot} 筆。武力、知力、統率是記錄 +18、+19、+17：武力由攻擊力公式確認，知力、統率的名稱只依"
                        "數值推定（遊戲用圖示標示）；兵種名照 MAIN.EXE 的字串順序對應（推定）；兵力、士氣、兵種、等級、道具是開局的狀態表。"
                        + ("讀音是記錄裡的半形片假名，轉成全形。" if pc98 else "")
                        + (f"遊戲寫作{name}，史書作{historical[name]}。" if name in historical else ""))
        rows.append(row)
    return rows
