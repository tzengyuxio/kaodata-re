"""項劉記 (kouryuuki-dos, DOS Chinese) for koei-wiki: persons (koei-persons/1). id is the kaodata kouryuuki-dos id
(0-91; the faces 92-96 have no person). Names are the Chinese version's; nameJa and reading come from the PC-98
version beside it (../kouryuuki-pc98, the same name table order). Labels are the Chinese MAIN.EXE's status window
words. Field sources: notes/kouryuuki.md「人物」「能力」「koei-wiki 匯出（人物）」."""
import os

import kaodata_export as ke
import koei_games as kg
import kouryuuki_extras as kx
import pklite

DATASET = "kouryuuki-dos"
PERSONS = 92
UNITS = 0x39C + 55 * 44 * 2  # SNDT file offset of the 27-byte army records, after the person records and the grid
# person +0 bits 0-2: 0 君主 (one per faction), 1 the faction's general, 2 在野, 7 not on the map
STATUS = {0: "君主", 1: "配下", 2: "在野", 7: "不在"}


def persons(game_dir):
    pc98 = os.path.join(game_dir, "..", "kouryuuki-pc98")
    img = pklite.depklite(open(os.path.join(game_dir, "MAIN.EXE"), "rb").read())
    names = kg.load_kohryuki_dos_names(os.path.join(game_dir, "MAIN.EXE"))
    names_ja = kg.load_kohryuki_x68_names(os.path.join(pc98, "MAIN.EXE"), pc98=True)
    with open(os.path.join(pc98, "MAIN.EXE"), "rb") as f:
        exe_ja = f.read()
    table = img[kg.KOHRYUKI_DOS_NAMES:][:PERSONS * 17]
    cell_place = {int.from_bytes(img[kx.PLACES + i * 19 + 17:][:2], "little"): i for i in range(39)}
    scen = []
    for k in range(1, 5):
        with open(os.path.join(game_dir, f"SNDT{k}.KR1"), "rb") as f:
            scen.append(f.read())

    def where(d, r):
        """The place of a person: a 在野 person's +2 is the place; the others' +2 is their army, whose +8 / +9 are
        the y / x of its cell."""
        if r[0] & 7 == 2:
            return r[2]
        u = d[UNITS + 27 * r[2]:][:27]
        return cell_place.get(u[8] * 55 + u[9])

    rows = []
    for i in range(PERSONS):
        row = {"id": i, "name": names[i]}
        if names_ja[i] != names[i]:
            row["nameJa"] = names_ja[i]
        reading = exe_ja[kg.KOHRYUKI_PC98_NAMES + i * 17 + 7:][:8].split(b"\0")[0].decode("cp932").strip()
        if reading:
            row["reading"] = ke.kana_to_hiragana(reading)
        n = table[i * 17:][:17]
        row["born"] = -(n[15] + 206)
        d = scen[0]
        r = d[4 + i * 10:][:10]
        row["stats"] = {"戰鬥": r[5], "統御": r[6], "用兵": r[7]}
        row["more"] = {"年齡": (n[15] - d[3] - 50) & 0xFF, "體力": r[3], "上限": r[4], "經驗": r[8],
                       "外交": "有" if r[7] >= 80 or r[0] & 8 else "無"}
        out = []
        for k, d in enumerate(scen):
            r = d[4 + i * 10:][:10]
            st = r[0] & 7
            s = {"scenario": k + 1, "year": -d[3], "month": d[1], "status": STATUS[st]}
            if st != 7:
                loc = where(d, r)
                if loc is not None:
                    s["location"] = loc
                if st in (0, 1):
                    s["lord"] = next(j for j in range(PERSONS)
                                     if d[4 + j * 10] & 7 == 0 and d[4 + j * 10] >> 4 == r[0] >> 4)
            out.append(s)
        row["scenarios"] = out
        row["uncertain"] = ["scenarios.status"]
        notes = ["year 是西元前（負數）；born 是名字表 +15 算出的西元前生年。「配下」「不在」不是遊戲畫面上的稱呼："
                 "配下是勢力的武將（遊戲有「の配下に」一詞），不在是劇本開始時不在地圖上（死亡、被俘等，沒追）。"
                 "所在是軍隊所在的格（在野是地點號）；軍隊不在城、關的格上時不填 location。"]
        if i in ke.KOURYUUKI_DOS_NAME_HISTORICAL:
            notes.append(f"中文版寫法有誤，史書寫法 {ke.KOURYUUKI_DOS_NAME_HISTORICAL[i]}。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows
