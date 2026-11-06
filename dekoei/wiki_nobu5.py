"""信長の野望・覇王伝 with PK (Windows, Steam; nobu5pk-win) for koei-wiki: persons (koei-persons/1) and places
(koei-places/1). Field positions and evidence are in notes/nobu5.md「人物欄位」「地理」「Win 版的對應」.

Scenario files SV10.N5S-SV14.N5S (scenarios 1-5 in year order, the years are the u32 table at Nobunaga5WPK.exe file
0xB7628): after the 26-byte header and the 656-byte block,
- 460 person slots of 39 bytes at 0x2AA: +0-4 政治 戦闘 智謀 采配 野望, +5 birth year - 1453, +6 義理?, +7 lord
  (daimyo number, 0xFF 浪人), +9 一門 (0xFF none), +10 city, +11 province, +13 忠誠, +14 bits 6-7 寿命 (A-D),
  +17 u16 face, +21 u16 next person of the same city (slot, 0xFFFF ends), +23 family 9 bytes, +32 given 7 bytes;
- 64 daimyo of 39 bytes at 0x48BE: +0 u16 the daimyo's person slot (0xFFFF unused);
- 173 cities of 38 bytes at 0x5536: +0 name 9 bytes (without 城), +9 u16 first person slot, +11 u16 lord (daimyo
  number), +13 province (0-63). Names change between scenarios (日之岳 / 平戸 ...).
The later arrivals are in the EXE (koei_games.NOBU5_WIN_ARRIVALS, 36 bytes): +0 year - 1453, +1 一門, +2 lord, +3 city
(0xFF not fixed), +4 family, +13 given, +20 birth year - 1453, +21-25 abilities, +26 義理?, +27 寿命, +28 u16 face.
The 64 province names are pointed to by the u32 table at Nobunaga5WPK.exe file 0xB9E10 (.rdata, VA - 0x401600).
列伝: Nobunaga5WPK.exe file 0x876D8 (.data), 1057 records of 164 bytes (faces 0-1056; the bytes after are other data), record n is face n: u16 birth year, u16 death
year (0xFFFF unknown), then 160 bytes of Shift-JIS text (0x0A line breaks of the 19-character window, NUL padded);
empty for the unnamed princesses and a few unused faces."""
import os
import struct

import kaodata_export as K
import koei_games as G

PEOPLE, DAIMYO, CITIES = 0x2AA, 0x48BE, 0x5536
YEARS, PROVINCE_NAMES, BIOS, BIO_SIZE, BIO_COUNT = 0xB7628, 0xB9E10, 0x876D8, 164, 1057
BIO_LANG = "ja"
RDATA = 0x400000 + 0x74000 - 0x72A00  # VA - file offset of .rdata
STATS = ["政治", "戦闘", "智謀", "采配", "野望"]
LIFESPAN = "ABCD"
PROVINCE_BASE = 173  # place id of province k is 173 + k (cities are 0-172)


def _u16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def _name(raw):
    return raw.split(b"\0")[0].decode("cp932").replace("　", "").strip()


def _load(game_dir):
    files = {}
    for name in G.NOBU5_WIN_SCENARIOS + ["Nobunaga5WPK.exe"]:
        with open(os.path.join(game_dir, name), "rb") as f:
            files[name] = f.read()
    return [files[n] for n in G.NOBU5_WIN_SCENARIOS], files["Nobunaga5WPK.exe"]


def province_names(exe):
    return [_name(exe[struct.unpack_from("<I", exe, PROVINCE_NAMES + 4 * k)[0] - RDATA:][:16]) for k in range(64)]


def _scenario(sv):
    """(slot -> person record, daimyo number -> slot) of a SV1n.N5S file."""
    people = {s: sv[PEOPLE + 39 * s:][:39] for s in range(G.NOBU5_PC98_SLOTS) if sv[PEOPLE + 39 * s + 23]}
    daimyo = {d: _u16(sv, DAIMYO + 39 * d) for d in range(64) if _u16(sv, DAIMYO + 39 * d) in people}
    return people, daimyo


def _arrivals(exe, n):
    start, stride, size = G.NOBU5_WIN_ARRIVALS
    out = []
    for o in range(start + n * stride, start + (n + 1) * stride - size + 1, size):
        if not exe[o]:
            break
        out.append(exe[o:o + size])
    return out


def _ids(scenarios, exe):
    """face -> kaodata id and name: the builder's order (base scenarios 1-3 of the PC-98, then the PK's), one per face."""
    ids, names = {}, {}
    for n in K.NOBU5_WIN_ORDER:
        for name, face in G.load_nobu5_win_scenario(scenarios[n]) + G.load_nobu5_win_arrivals(exe, n):
            if face not in ids:
                ids[face], names[face] = len(ids), K.NOBU5_WIN_ALIASES.get(name, name)
    return ids, names


def _bio(exe, face):
    """(birth year, death year or None, text) of the 列伝 of a face; text "" when there is none."""
    if face >= BIO_COUNT:
        return None, None, ""
    o = BIOS + BIO_SIZE * face
    born, died = struct.unpack_from("<HH", exe, o)
    text = exe[o + 4:o + BIO_SIZE].split(b"\0")[0].decode("cp932").replace("\n", "").strip()
    return born, None if died == 0xFFFF else died, text


def bios(game_dir):
    scenarios, exe = _load(game_dir)
    ids, _ = _ids(scenarios, exe)
    return {i: [("單段", _bio(exe, face)[2])] for face, i in ids.items() if _bio(exe, face)[2]}


def bio_names(game_dir):
    scenarios, exe = _load(game_dir)
    ids, names = _ids(scenarios, exe)
    return {i: names[face] for face, i in ids.items()}


def persons(game_dir):
    scenarios, exe = _load(game_dir)
    years = struct.unpack_from("<5I", exe, YEARS)
    ids, names = _ids(scenarios, exe)
    rows = {}

    def row(face, n, born, stats, giri, life, clan):
        """The person's row; the fixed values come from the first scenario of the builder's order."""
        if face not in rows:
            r = {"id": ids[face], "name": names[face], "born": born, "stats": dict(zip(STATS, stats)),
                 "hidden": {"義理": giri, "寿命": LIFESPAN[life >> 6]}, "scenarios": [],
                 "uncertain": ["hidden.義理", "scenarios.loyalty"]}
            if clan != 0xFF:
                r["relations"] = {"clan": clan}
                r["uncertain"].insert(1, "relations.clan")
            rows[face] = (n, r)
        return rows[face][1]

    entries = {}  # face -> {scenario: entry}
    for n in K.NOBU5_WIN_ORDER:
        people, daimyo = _scenario(scenarios[n])
        lord_face = {d: _u16(people[s], 17) for d, s in daimyo.items()}
        rulers = set(daimyo.values())
        for s, p in people.items():
            face = _u16(p, 17)
            row(face, n, 1453 + p[5], p[0:5], p[6], p[14], p[9])
            e = {"scenario": n + 1, "year": years[n],
                 "status": "大名" if s in rulers else "浪人" if p[7] == 0xFF else "家臣", "location": p[10]}
            if p[7] != 0xFF:
                e["lord"] = ids[lord_face[p[7]]]
                e["loyalty"] = p[13]
            entries.setdefault(face, {})[n] = e
        for a in _arrivals(exe, n):
            face = _u16(a, 28)
            r = row(face, n, 1453 + a[20], a[21:26], a[26], a[27], a[1])
            if rows[face][0] == n:
                r["debut"] = 1453 + a[0]
            e = {"scenario": n + 1, "year": years[n], "status": "後登場"}
            if a[2] != 0xFF:
                e["lord"] = ids[lord_face[a[2]]]
            if a[3] != 0xFF:
                e["location"] = a[3]
            entries.setdefault(face, {})[n] = e
    out = []
    for face, (_, r) in rows.items():
        _, died, _ = _bio(exe, face)
        if died:
            r = {**{k: r[k] for k in ("id", "name", "born")}, "died": died, **r}
        r["scenarios"] = [entries[face][n] for n in sorted(entries[face])]
        r["notes"] = ("能力、生年、義理、寿命、一門取自 kaodata 編號所依的第一個劇本（本體劇本優先），各劇本的值可能略有不同。"
                      "劇本 1–5 依年份排（1534、1551、1568、1582、1583），2–4 是本體的劇本、1 和 5 是 PK 的。"
                      "status 的「家臣」「後登場」是這邊的分類（記錄裡只分大名、仕官、浪人）；浪人的 location 是所在的城。"
                      "義理是推定（和武将風雲録同一組值）；一門是遊戲的一門編號。"
                      "died 取列伝的没年；列伝也記生年，有 23 人和劇本的生年不同，born 照劇本。")
        out.append(r)
    return sorted(out, key=lambda r: r["id"])


def places(game_dir, out_dir):
    scenarios, exe = _load(game_dir)
    years = struct.unpack_from("<5I", exe, YEARS)
    provinces = province_names(exe)
    rows = []
    for k in range(173):
        names = [_name(sv[CITIES + 38 * k:][:9]) for sv in scenarios]
        province = scenarios[0][CITIES + 38 * k + 13]
        assert all(sv[CITIES + 38 * k + 13] == province for sv in scenarios)
        row = {"id": k, "name": names[0], "level": "城", "province": provinces[province],
               "notes": "城的號碼是遊戲的城號（九州往東北排）。名稱取劇本 1（1534 年）；城表裡的名字不含「城」字。"
                        "遊戲資料沒有城與城的相鄰關係，也沒有大地圖座標，所以沒給 adjacent、pos。"}
        renamed = [f"劇本 {n + 1}（{years[n]}）{name}" for n, name in enumerate(names) if name != names[0]]
        if renamed:
            row["notes"] += "其他劇本的名稱：" + "、".join(renamed) + "。"
        rows.append(row)
    for k, name in enumerate(provinces):
        rows.append({"id": PROVINCE_BASE + k, "name": name, "level": "國",
                     "notes": f"國號 {k}，地點號是國號＋{PROVINCE_BASE}。國名在 EXE 的國名表；國本身沒有記錄（金、兵在城上），"
                              "有些是兩國合成一格（筑前対馬、阿波淡路…），有些一國拆成兩格（北／南近江…）。沒有相鄰表。"})
    return rows
