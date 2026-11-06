"""信長の野望・全国版 (nobu2-pc88) for koei-wiki: persons (koei-persons/1) and places (koei-places/1). Field sources
and how sure they are: notes/nobu2.md「人物欄位」「地理」「koei-wiki 匯出」."""
import os

import koei_games
import pc88

# Disk A (pc88.cpm_files): DATA50S.DAT holds the 53 lords (names 0x1581 / 0x175E, 7-byte records from 0x1308:
# 年令 健康 野心 運 魅力 ＩＱ, then 0), DATA50N.DAT the 50 國 (names 0x104, 9 bytes; neighbours 0x881, 8 bytes,
# 0-based, FF ends; 地方 number 1-7 at 0xA11). The only scenario is 1560; lord k rules 國 k + 1 (the 國 are
# numbered 1-50 in the game), 50-52 (明智, 羽柴, 柴田) start without a 國.
NOBU2_YEAR = 1560
NOBU2_PROVINCES, NOBU2_NAMES, NOBU2_NEIGHBOURS, NOBU2_REGIONS = 50, 0x104, 0x881, 0xA11
NOBU2_LABELS = ["年令", "健康", "野心", "運", "魅力", "ＩＱ"]


def _disk(game_dir, name="DISK_A.D88"):
    with open(os.path.join(game_dir, name), "rb") as f:
        return pc88.cpm_files(pc88.d88_image(f.read()))


def persons(game_dir):
    data50s = _disk(game_dir)["DATA50S.DAT"]
    rows = []
    for i, name, age, *values in koei_games.load_nobu2_pc88_stats(data50s):
        row = {"id": i, "name": name, "born": NOBU2_YEAR - age,
               "stats": dict(zip(NOBU2_LABELS[1:], values)), "more": {"年令": age},
               "notes": "只有大名。生年是 1560 減開局的年令。"}
        if i < NOBU2_PROVINCES:
            row["scenarios"] = [{"scenario": "50國", "year": NOBU2_YEAR, "lord": i, "location": i + 1,
                                 "status": "大名"}]
        else:
            row["notes"] += "開局沒有國（後繼或替代用的大名）。"
        rows.append(row)
    return rows


def places(game_dir, out_dir, disk="DISK_A.D88"):
    d = _disk(game_dir, disk)["DATA50N.DAT"]
    rows = []
    for k in range(NOBU2_PROVINCES):
        nb = d[NOBU2_NEIGHBOURS + 8 * k:][:8]
        adjacent = [n + 1 for n in nb.split(b"\xff")[0]]
        rows.append({"id": k + 1, "name": d[NOBU2_NAMES + 9 * k:][:9].split(b"\0")[0].decode("cp932"),
                     "level": "國", "adjacent": adjacent,
                     "notes": f"地方號 {d[NOBU2_REGIONS + k]}（1–7，東北到九州；地方的名稱沒找到）。這是 50 國劇本的國，"
                              "17 國劇本另有一組國，沒有匯出。戰場圖 HEXMAP.50 是每國一張（打哪一國用那一國的圖），"
                              "PC-88 的圖塊沒解，沒有輸出圖。地圖座標只有各地方地圖上的位置，單位沒確認，沒有輸出。"})
    return rows
