"""太閤立志傳III (taikoh3-win, Windows Chinese) for koei-wiki: persons (koei-persons/1).

id and name are the kaodata taikoh3-win ones: 0-249 are the records of TPEDATA.DAT (the 木下藤吉郎 start), 250 and 251
are records 0 and 230 of FPEDATA.DAT (the 粱田政勝 start). A record is 22 bytes: +0 the birth year - 1490 (told from
the values: 信長 44, 石田三成 70, 森蘭丸 75), +1 unknown, +2 surname, +11 given name, +18.. unknown. The other scenario
data (abilities, clans, places) is not in the extracted files. Field sources: notes/taikoh3.md「koei-wiki 匯出」."""
import os

import kaodata_export as ke

DATASET = "taikoh3-win"
RECORD, YEAR0 = 22, 1490


def _records(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        data = f.read()
    out = []
    for r in range(0, ke.TAIKOH3_WIN_PERSONS * RECORD, RECORD):
        name = (data[r + 2:r + 11].split(b"\0")[0] + data[r + 11:r + 18].split(b"\0")[0]).decode("big5")
        out.append((name, YEAR0 + data[r]))
    return out


def persons(game_dir):
    t = _records(game_dir, "TPEDATA.DAT")
    f = _records(game_dir, "FPEDATA.DAT")
    people = [(i, *t[i], f[i]) for i in range(ke.TAIKOH3_WIN_PERSONS)]
    people += [(ke.TAIKOH3_WIN_PERSONS + k, *f[i], None) for k, i in enumerate(ke.TAIKOH3_WIN_FREE)]
    rows = []
    for p, name, born, other in people:
        row = {"id": p, "name": name, "born": born, "uncertain": ["born"]}
        notes = []
        if other and other[0] == name and other[1] != born:
            notes.append(f"粱田政勝劇本（FPEDATA）的生年是 {other[1]}。")
        elif other and other[0] != name:
            notes.append(f"粱田政勝劇本（FPEDATA）的同一筆是{other[0]}。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows
