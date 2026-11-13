"""獨立戰爭 Liberty or Death for koei-wiki: persons (koei-persons/1).

Main dataset liberty-pc98 (the Japanese original); the person records (MAIN.EXE, 250 x 58 bytes) of the PC-98 and the
Chinese DOS version are the same apart from two near pointers (+0, +0xF), so the values are read from the PC-98 EXE,
name from the Chinese DOS MAIN.EXE beside it (../liberty-dos) and nameJa from the PC-98 one. id = person number =
face number (the kaodata id). There is no English version here. Field sources: notes/liberty.md「koei-wiki 匯出」."""
import os

import liberty as L

DATASET = "liberty-pc98"
# Chinese MAIN.EXE DGROUP 0x1202 (side, record +2) and 0x1216 (rank, record +8 & 3)
SIDES = ["美國", "愛國派", "法國", "西班牙", "英國", "保皇黨"]
NO_RANK = (1, 5)  # the officer screen (DOS MAIN.EXE file 0x2018E) shows 「--」 for these sides
RANKS = ["將軍", "上校", "少校", "上尉"]
OFF_MAP = 0x35  # record +3 of the officers not on the map at the start
START = (1775, 7)  # DGROUP 0x2990 = 42612 half-months: year = v // 24, month = (v % 24) // 2 + 1 (DOS MAIN.EXE file 0x242F4)


def persons(game_dir):
    root = os.path.dirname(os.path.abspath(game_dir))
    pc98 = os.path.join(root, "liberty-pc98", "MAIN.EXE")
    with open(pc98, "rb") as f:
        exe = f.read()
    names_ja, _ = L.load_liberty_pc98_names(pc98)
    names_zh, _ = L.load_liberty_dos_names(os.path.join(root, "liberty-dos", "MAIN.EXE"))
    rows = []
    for i in range(L.LIBERTY_PERSONS[2]):
        r = exe[L.LIBERTY_PC98_PERSONS + 58 * i:][:58]
        row = {"id": i, "name": names_zh[i]}
        if names_ja[i] != names_zh[i]:
            row["nameJa"] = names_ja[i]
        row["stats"] = {"統御": r[0x35], "戰術": r[0x36], "指導": r[0x37], "名聲": r[5]}
        row["more"] = {"陣營": SIDES[r[2]], "忠誠": r[6]}
        s = {"scenario": 1, "year": START[0], "month": START[1]}
        if r[3] == OFF_MAP:
            s["status"] = "未登場"
        else:
            row["more"].update({"訓練": r[0xD], "武裝": r[0xC], "士氣": r[0xE]})
        if r[2] not in NO_RANK:
            s["rank"] = RANKS[r[8] & 3]
        s["loyalty"] = r[6]
        row["scenarios"] = [s]
        row["uncertain"] = ["more.陣營", "scenarios.month"]
        notes = ["只有一個開局（1775 年）。stats 與忠誠照人物畫面（中文版 MAIN.EXE 檔案 0x20147 起）的欄位：統御 +0x35、戰術 +0x36、"
                 "指導 +0x37、名聲 +5、忠誠 +6；訓練、武裝、士氣（+0xD、+0xC、+0xE）是所率部隊的值，只列開局在地圖上的人。"
                 "陣營是記錄 +2 在遊戲字串表的名稱，遊戲沒有這一欄的稱呼。"
                 "rank 是 +8 的低 2 bit（將軍、上校、少校、上尉）；愛國派、保皇黨畫面顯示「--」，不填。"
                 "未登場是記錄 +3 為 53（開局不在地圖上的 195 人；遊戲沒有稱呼，照使用者 2026-11-14 的規則）。"
                 "month 是執行檔裡日期的初值（半月制），沒有確認開局時是否改寫。"]
        if i == 82:
            notes.append("中文版寫成托馬斯・蓋茨，日文版是トーマス・ゲージ，史書寫法托馬斯・蓋奇。")
        if i == 191:
            notes.append("中文版寫成伊塞亞・加德納（另一人的名字），日文版是イスラエル・パットナム，史書寫法伊斯雷爾・帕特南。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows
