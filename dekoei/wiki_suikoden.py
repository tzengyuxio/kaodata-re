"""水滸傳・天命之誓 (suikoden-dos, DOS Chinese) for koei-wiki: persons (koei-persons/1). id is the kaodata suikoden-dos
id (0-254, the same order as suikoden-pc98 and suikoden-fc). Names are the Chinese version's; nameJa and reading come
from the PC-98 version beside it (../suikoden-pc98, the same ids and face codes). Labels are the Chinese MAIN.EXE's
status window words. Field sources: notes/koei-games.md「水滸伝・天命の誓い」「能力」「koei-wiki 匯出（人物）」."""
import os

import kaodata_export as ke
import koei_games as kg
import koei_stats as ks

DATASET = "suikoden-dos"
# DOS MAIN.EXE (LZEXE + EXEPACK unpacked) 0x397D8-0x3983D, the scenario menu: (1101 年) ... (1105 年)
SCENARIO_YEARS = [1101, 1103, 1104, 1105]
# 身份 names, the Chinese MAIN.EXE's 34 strings in the order of PC-98 DS:0x35BC (koei_person.SUIKODENPerson)
STATUS = ("太尉 太守 官吏 好漢 頭目 強盜 義兄 義弟 死亡 罪犯 僧侶 漁夫 苦力 醫者 生意人 客棧掌櫃 技工 學究 富人 少爺 "
          "少女 藝妓 獵人 大力士 壯士 客商 江湖藝人 道士 失業武人 無業遊民 虎 狼 熊 豹").split()
# statuses that belong to a band: 太尉, 太守, 官吏 serve 高俅 (P+3 = 0); 好漢 lead their own band (P+3 = own id);
# 頭目, 強盜, 義兄, 義弟 follow the 好漢 whose id is P+3. Everyone else has P+3 = 1 (魯智深's id), which means nothing.
BAND = set(range(8))
DEAD = 8


def _status(b):
    s = b & 0x3F
    return (s & 0x0F) + 22 if s & 0x10 else (s & 0x1F) + 8 if s & 0x20 else s


def _records(path):
    with open(path, "rb") as f:
        data = f.read()
    return data, [data[4 + i * 22:][:22] for i in range(255)]


def persons(game_dir):
    pc98 = os.path.join(game_dir, "..", "suikoden-pc98")
    zh = kg.load_suikoden_dos_persons(os.path.join(game_dir, "SUIDATA1.CIM"))
    ja = kg.load_suikoden_pc98_persons(os.path.join(pc98, "SUIDATA1.CIM"))
    assert [f for f, _ in zh] == [f for f, _ in ja]
    with open(os.path.join(pc98, "SUIDATA1.CIM"), "rb") as f:
        ja_data = f.read()
    scen = [_records(os.path.join(game_dir, f"SUIDATA{k}.CIM")) for k in range(1, 5)]
    data0, recs0 = scen[0]

    rows = []
    for i, ((_, name), (_, name_ja)) in enumerate(zip(zh, ja)):
        row = {"id": i, "name": name}
        if name_ja != name:
            row["nameJa"] = name_ja
        reading = ja_data[7124 + i * 20 + 7:][:9].split(b"\0")[0].decode("cp932").strip()
        if reading:
            row["reading"] = ke.kana_to_hiragana(reading)
        r = recs0[i]
        tone, flag = data0[7124 + i * 45 + 43], data0[7124 + i * 45 + 44]
        row["stats"] = {"體力": r[3], "能耐": r[8], "技能": r[9], "智慧": r[10], "忠義": r[5], "仁愛": r[6], "勇氣": r[7]}
        more = {"年齡": r[0], "體力上限": r[4], "能耐經驗": r[11], "技能經驗": r[12], "智慧經驗": r[13], "士兵": r[18],
                "人望": r[16] | r[17] << 8, "身份": STATUS[_status(r[19])], "性別": "男" if flag & 0x80 else "女"}
        if r[19] & 0x40:
            more["船隻"] = True
        if flag & 0x40:
            more["掌舵"] = True
        row["more"] = more
        row["hidden"] = {"口調": tone}
        out = []
        for k, (_, recs) in enumerate(scen):
            r = recs[i]
            st = _status(r[19])
            s = {"scenario": k + 1, "year": SCENARIO_YEARS[k], "status": STATUS[st]}
            if st != DEAD:
                s["location"] = r[2] + 1
            if st in BAND:
                s["lord"] = r[1]
                if r[1] != i:
                    s["loyalty"] = r[14]
            out.append(s)
        row["scenarios"] = out
        notes = []
        if i in ke.SUIKODEN_DOS_NAME_HISTORICAL:
            notes.append(f"中文版寫法有誤，小說寫法 {ke.SUIKODEN_DOS_NAME_HISTORICAL[i]}。")
        if i in ke.SUIKODEN_PC98_NAME_HISTORICAL:
            notes.append(f"日文版寫法有誤，小說寫法 {ke.SUIKODEN_PC98_NAME_HISTORICAL[i]}。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows
