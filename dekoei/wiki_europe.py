"""歐陸戰線 Operation Europe for koei-wiki: persons (koei-persons/1).

Main dataset europe-pc98 (the Japanese original). SCEDATA of the PC-98 and the Chinese DOS version have the same
layout and, apart from the names, the same 22-byte person records; the 12 leaders are in each MAIN.EXE. name is the
Chinese DOS spelling (koei_games.load_europe_dos_names, ../europe-dos), nameJa the PC-98 one. id = person number =
face number (the kaodata id, 0-93 commanders, 94-105 leaders). There is no English version here.
Field sources: notes/europe.md「koei-wiki 匯出」."""
import os

import koei_games as kg

DATASET = "europe-pc98"
# Chinese MAIN.EXE DGROUP 0x3704: record +9 bit k -> nationality; 0x370E: record +21 & 7 -> post
NATIONS = ["德", "意", "美", "英", "法", "蘇"]
POSTS = {1: "軍團長", 2: "作戰參謀", 3: "情報參謀", 4: "最高統帥", 5: "參謀總長", 6: "空軍司令", 7: "特種兵長官"}
# the officer table (DOS MAIN.EXE file 0x1279E): 國籍 +9, then these, 經驗 +18
STATS = {"指揮": 10, "魅力": 11, "勇猛": 12, "體力": 13, "步兵": 15, "砲兵": 16, "坦克": 17}
# SCEDATA block k is scenario menu item k (DOS MAIN.EXE image 0x6CB6 seeks to 0x1518 + k * 0x1D95 with the item id);
# the block is read to DGROUP 0x42, so block +2 is the year - 1940 (DGROUP 0x44, image 0xA11E adds 1940) and +3 the
# month (0x45). Menu labels (PC-98 MAIN.EXE 0x4BDAB): 0 is the campaign start
SCENARIO_NAMES = ["キャンペーン", "フランス侵攻戦", "北アフリカ戦", "クルスク機甲戦", "ノルマンディーの戦い", "バルジの戦い",
                  "ベルリン攻防戦"]


def _nations(mask):
    return "・".join(n for k, n in enumerate(NATIONS) if mask >> k & 1)


def persons(game_dir):
    root = os.path.dirname(os.path.abspath(game_dir))
    pc98, dos = os.path.join(root, "europe-pc98"), os.path.join(root, "europe-dos")
    names_zh = kg.load_europe_dos_names(os.path.join(dos, "SCEDATA"), os.path.join(dos, "MAIN.EXE"))
    names_ja = kg.load_europe_x68_names(os.path.join(pc98, "SCEDATA"), os.path.join(pc98, "MAIN.EXE"), pc98=True)
    with open(os.path.join(pc98, "SCEDATA"), "rb") as f:
        sce = f.read()
    with open(os.path.join(pc98, "MAIN.EXE"), "rb") as f:
        main = f.read()
    first, stride, count = kg.EUROPE_SCENARIOS
    block = first - 0x25A  # the people table is at block +0x25A
    dates = [(1940 + sce[block + s * stride + 2], sce[block + s * stride + 3]) for s in range(count)]
    records, scenarios = {}, {}
    for s in range(count):
        for k in range(40):
            rec = sce[first + s * stride + k * 22:][:22]
            if rec[9] != 0xFF:
                records.setdefault(rec[20], rec)
                scenarios.setdefault(rec[20], []).append(s)
    offset, n = kg.EUROPE_PC98_LEADERS
    leaders = {rec[20]: rec for rec in (main[offset + 22 * k:][:22] for k in range(n))}
    rows = []
    for i in sorted(names_zh):
        row = {"id": i, "name": names_zh[i]}
        if names_ja[i] != names_zh[i]:
            row["nameJa"] = names_ja[i]
        if i in records:
            r = records[i]
            row["stats"] = {k: r[o] for k, o in STATS.items()}
            row["more"] = {"國籍": _nations(r[9]), "經驗": r[18]}
            row["scenarios"] = [{"scenario": s + 1, "year": dates[s][0], "month": dates[s][1]} for s in scenarios[i]]
            row["uncertain"] = ["stats.體力"]
            notes = ("指揮官，記錄在 SCEDATA 的劇本裡（22 bytes）；能力各劇本相同，經驗開局都是 0。"
                     "欄位照指揮官一覽（中文版 MAIN.EXE 檔案 0x1279E）：國籍 +9（bit 對應德、意、美、英、法、蘇），"
                     "指揮、魅力、勇猛、體力、步兵、砲兵、坦克是 +10–+13、+15–+17，經驗 +18；+14 和 +13 相同，"
                     "推定是體力上限。scenario 是遊戲劇本選單的順序（1 キャンペーン、2 フランス侵攻戦、3 北アフリカ戦、"
                     "4 クルスク機甲戦、5 ノルマンディーの戦い、6 バルジの戦い、7 ベルリン攻防戦），選單第 k 項（id k − 1）載入 SCEDATA 第 k 個區塊；"
                     "1 是戰役模式的開局（1940.5），之後各階段讀劇本 3–7 的區塊。year、month 是區塊開頭的日期。")
            if i in (14, 34, 36):
                notes += "中文版各劇本寫法不同，name 取出現最多的寫法（notes/europe.md）。"
            row["notes"] = notes
        else:
            r = leaders[i]
            row["more"] = {"國籍": _nations(r[9]), "職位": POSTS[r[21] & 7]}
            row["uncertain"] = ["more.國籍"]
            row["notes"] = ("領袖，記錄在 MAIN.EXE（PC-98 檔案 0x4A288 起 12 筆），沒有能力值，也不在劇本的指揮官表裡。"
                            "職位是 +21 在遊戲職位表的名稱（中文版 MAIN.EXE 檔案 0x13FD4 以 +21 & 7 查表），"
                            "國籍是 +9 的 bit（軸心、聯合軍、蘇聯各一人）。")
        rows.append(row)
    return rows
