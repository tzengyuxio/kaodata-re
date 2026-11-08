"""信長の野望・覇王伝 with パワーアップキット (PC-98; nobu5pk-pc98) for koei-wiki: persons (koei-persons/1), places
(koei-places/1) and 列伝. The rows follow wiki_nobu5 (nobu5pk-win); field positions and evidence are in notes/nobu5.md
「劇本檔的整體配置」「人物欄位」「地理」「PC-98 版 パワーアップキット」.

Scenario files SN0.NB5-SN4.NB5 (scenarios 1-5 in year order, XOR 0xB4), the PC-98 layout of the base game:
- 0x0000: scenario number, year, month. The PK counts every year from 1453 (as the Win version), the base game
  from 1476: the header year, person +14, S*T +0 and +18 are the only bytes of SN1 / S1T that differ from the base;
- 64 daimyo of 39 bytes at 0x122: +0 u16 pointer to the daimyo's person (minus 0x40 is the file offset);
- 460 person slots of 39 bytes at 0xAE4, from the family name: +0 family 7, +7 given 7, +14 birth year - 1453,
  +15-19 政治 戦闘 智謀 采配 野望, +20 義理?, +21 lord (daimyo number, 0xFF 浪人), +23 一門 (0xFF none), +24 city,
  +25 province, +27 忠誠, +28 bits 6-7 寿命 (A-D), +29 u16 face;
- 173 cities of 38 bytes at 0x50F8: +2 name 9 bytes (without 城), +11 province (0-63).
S0T.NB5-S4T.NB5 are the later arrivals, 30 bytes: +0 year - 1453, +1 一門, +2 lord, +3 city (0xFF not fixed),
+4 family, +11 given, +18 birth year - 1453, +19-23 abilities, +24 義理?, +25 寿命, +26 u16 face.
The 64 province names are NUL-separated Shift-JIS strings in MAIN.EXE from 0x603D8 (in the order of the provinces).
列伝: BFILE.NB5, 1100 records of 164 bytes laid out as the Win version's (wiki_nobu5): record n is face n, u16 birth
year, u16 death year (0xFFFF unknown), 160 bytes of Shift-JIS text; 1057 and after are empty."""
import os
import struct

from PIL import Image

import kaodata_export as K
import koei_games as G
from wiki_nobu5 import LIFESPAN, PROVINCE_BASE, STATS, _name

BASE_YEAR = 1453
DAIMYO, CITIES = 0x122, 0x50F8
PROVINCE_NAMES = 0x603D8
BIO_SIZE = 164
BIO_LANG = "ja"

# World map (notes/nobu5.md「大地圖」). M_PARTS.NB5 starts with the 120 x 23 cell grid, 3 bytes a cell at
# (column * 23 + row) * 3: +0 terrain tile, +1 sprite (0xFF none), +2 overlay shape in the low nibble (0xE castle,
# 0xFF none). M_CHIKEI.NB5 holds 239 terrain tiles of 96 bytes from 0, 128-byte sprites from 0x59A0 (96 bytes OR'd,
# 32-byte mask AND'd first) and 64-byte overlay shapes from 0xAFA0 (32-byte shape, 32-byte mask). Tiles are 16 x 16,
# a row is 6 bytes: left 8 dots in planes 0-2, then right 8 dots. The cell draw is MAIN.EXE image 0x7024. Odd columns
# sit 8 dots lower (image 0x6F16). The castle cells are a table of (column, row) bytes for the 173 castles at image
# 0x43870 + 0x114 (searched by image 0x6F49). The colours 0-7 are the season table at file 0x47596 + 0x18 x season
# (B, R, G nibbles); table 0 is taken as spring.
MAP_COLS, MAP_ROWS, CELL = 120, 23, 16
MAP_W, MAP_H = MAP_COLS * CELL, MAP_ROWS * CELL + CELL // 2
MAP_CASTLES, MAP_SEASONS = 0x43870 + 0x114, 0x47596
NOBU5_WORLD_FILE = "M_CHIKEI-spring.png"


def _u16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def _load(game_dir):
    def read(name):
        with open(os.path.join(game_dir, name), "rb") as f:
            return f.read()
    sns = [bytes(b ^ G.NOBU5_PC98_XOR for b in read(f"SN{n}.NB5")) for n in range(5)]
    sts = [read(f"S{n}T.NB5") for n in range(5)]
    return sns, sts, read("MAIN.EXE"), read("BFILE.NB5")


def province_names(exe):
    names = exe[PROVINCE_NAMES:].split(b"\0")[:64]
    return [n.decode("cp932") for n in names]


def _scenario(sn):
    """(file offset of the family name -> person record, daimyo number -> offset) of a SN*.NB5 file."""
    people = {o: sn[o:o + 39] for o in range(G.NOBU5_PC98_PEOPLE, G.NOBU5_PC98_PEOPLE + G.NOBU5_PC98_SLOTS * 39, 39)
              if sn[o]}
    daimyo = {d: _u16(sn, DAIMYO + 39 * d) - 0x40 for d in range(64) if _u16(sn, DAIMYO + 39 * d) - 0x40 in people}
    return people, daimyo


def _arrivals(st):
    return [st[o:o + 30] for o in range(0, len(st) - 29, 30) if st[o + 4]]


def _person_name(raw):
    return G._nobu5_pc98_name(raw[:7]) + G._nobu5_pc98_name(raw[7:14])


def _ids(sns, sts):
    """face -> kaodata id and name: the builder's order (K.NOBU5_WIN_ORDER, each scenario then its arrivals)."""
    ids, names = {}, {}
    for n in K.NOBU5_WIN_ORDER:
        people, _ = _scenario(sns[n])
        for name, face in [(_person_name(p), _u16(p, 29)) for p in people.values()] + \
                G.load_nobu5_pc98_arrivals(sts[n]):
            if face not in ids:
                ids[face], names[face] = len(ids), K.NOBU5_WIN_ALIASES.get(name, name)
    return ids, names


def _bio(bfile, face):
    """(birth year, death year or None, text) of the 列伝 of a face; text "" when there is none."""
    o = BIO_SIZE * face
    if o + BIO_SIZE > len(bfile):
        return None, None, ""
    born, died = struct.unpack_from("<HH", bfile, o)
    text = bfile[o + 4:o + BIO_SIZE].split(b"\0")[0].decode("cp932").replace("\n", "").strip()
    return born, None if died == 0xFFFF else died, text


def bios(game_dir):
    sns, sts, _, bfile = _load(game_dir)
    ids, _ = _ids(sns, sts)
    return {i: [("單段", _bio(bfile, face)[2])] for face, i in ids.items() if _bio(bfile, face)[2]}


def bio_names(game_dir):
    sns, sts, _, _ = _load(game_dir)
    ids, names = _ids(sns, sts)
    return {i: names[face] for face, i in ids.items()}


def _years(sns):
    return [BASE_YEAR + sn[1] for sn in sns]


def persons(game_dir):
    sns, sts, _, bfile = _load(game_dir)
    years = _years(sns)
    ids, names = _ids(sns, sts)
    rows = {}

    def row(face, born, stats, giri, life, clan):
        """The person's row; the fixed values come from the first scenario of the builder's order."""
        if face not in rows:
            r = {"id": ids[face], "name": names[face], "born": born, "stats": dict(zip(STATS, stats)),
                 "hidden": {"義理": giri, "寿命": LIFESPAN[life >> 6]}, "scenarios": [],
                 "uncertain": ["hidden.義理", "scenarios.loyalty"]}
            if clan != 0xFF:
                r["relations"] = {"clan": clan}
                r["uncertain"].insert(1, "relations.clan")
            rows[face] = r
        return rows[face]

    entries = {}  # face -> {scenario: entry}
    for n in K.NOBU5_WIN_ORDER:
        people, daimyo = _scenario(sns[n])
        lord_face = {d: _u16(people[o], 29) for d, o in daimyo.items()}
        rulers = set(daimyo.values())
        for o, p in people.items():
            face = _u16(p, 29)
            row(face, BASE_YEAR + p[14], p[15:20], p[20], p[28], p[23])
            e = {"scenario": n + 1, "year": years[n],
                 "status": "大名" if o in rulers else "浪人" if p[21] == 0xFF else "家臣", "location": p[24]}
            if p[21] != 0xFF:
                e["lord"] = ids[lord_face[p[21]]]
                e["loyalty"] = p[27]
            entries.setdefault(face, {})[n] = e
        for a in _arrivals(sts[n]):
            face = _u16(a, 26)
            r = row(face, BASE_YEAR + a[18], a[19:24], a[24], a[25], a[1])
            r.setdefault("debut", BASE_YEAR + a[0])
            e = {"scenario": n + 1, "year": years[n], "status": "後登場", "debut": BASE_YEAR + a[0]}
            if a[2] != 0xFF:
                e["lord"] = ids[lord_face[a[2]]]
            if a[3] != 0xFF:
                e["location"] = a[3]
            entries.setdefault(face, {})[n] = e
    out = []
    for face, r in rows.items():
        _, died, _ = _bio(bfile, face)
        if died:
            r = {**{k: r[k] for k in ("id", "name", "born")}, "died": died, **r}
        r["scenarios"] = [entries[face][n] for n in sorted(entries[face])]
        r["notes"] = ("能力、生年、義理、寿命、一門取自 kaodata 編號所依的第一個劇本（本體劇本優先），各劇本的值可能略有不同。"
                      "劇本 1–5 依年份排（" + "、".join(map(str, years)) + "），2–4 是本體的劇本、1 和 5 是 PK 的。"
                      "status 的「家臣」「後登場」是這邊的分類（記錄裡只分大名、仕官、浪人）；浪人的 location 是所在的城。"
                      "義理是推定（和武将風雲録同一組值）；一門是遊戲的一門編號。"
                      "died 取列伝的没年；列伝也記生年，有 23 人和劇本的生年不同，born 照劇本。")
        out.append(r)
    return sorted(out, key=lambda r: r["id"])


def _map_files(game_dir):
    def read(name):
        with open(os.path.join(game_dir, name), "rb") as f:
            return f.read()
    return read("M_PARTS.NB5")[:MAP_COLS * MAP_ROWS * 3], read("M_CHIKEI.NB5"), read("MAIN.EXE")


def _cell(grid, c, r):
    return grid[(c * MAP_ROWS + r) * 3:(c * MAP_ROWS + r) * 3 + 3]


def _cell_dots(grid, chikei, c, r):
    terrain, sprite, overlay = _cell(grid, c, r)
    buf = bytearray(chikei[terrain * 96:terrain * 96 + 96])
    if overlay != 0xFF and overlay & 0xF < 0xE:
        o = 0xAFA0 + (overlay & 0xF) * 64
        colour = 2 if terrain >= 0x5F else 7
        for i in range(32):
            for p in range(3):
                buf[i * 3 + p] &= chikei[o + 32 + i]
                if colour >> p & 1:
                    buf[i * 3 + p] |= chikei[o + i]
    if sprite != 0xFF:
        o = 0x59A0 + sprite * 128
        for i in range(96):
            buf[i] = buf[i] & chikei[o + 0x60 + i // 3] | chikei[o + i]
    return [sum((buf[y * 6 + x // 8 * 3 + p] >> (7 - x % 8) & 1) << p for p in range(3))
            for y in range(CELL) for x in range(CELL)]


def world_map(game_dir):
    grid, chikei, exe = _map_files(game_dir)
    pal = []
    for i in range(8):
        b, r, g = exe[MAP_SEASONS + 3 * i:MAP_SEASONS + 3 * i + 3]
        pal += [r * 17, g * 17, b * 17]
    im = Image.new("P", (MAP_W, MAP_H))
    im.putpalette(pal)
    tile = Image.new("P", (CELL, CELL))
    for c in range(MAP_COLS):
        for r in range(MAP_ROWS):
            tile.putdata(_cell_dots(grid, chikei, c, r))
            im.paste(tile, (c * CELL, r * CELL + (CELL // 2 if c & 1 else 0)))
    return im


def _castle_cells(exe):
    base = _u16(exe, 8) * 16
    return [tuple(exe[base + MAP_CASTLES + 2 * k:base + MAP_CASTLES + 2 * k + 2]) for k in range(173)]


def _cell_at(x, y):
    c = x // CELL
    return c, (y - (CELL // 2 if c & 1 else 0)) // CELL


def world_check(game_dir, rows):
    """Every castle pos falls on a castle cell (overlay 0xE) of the grid, the one the castle table gives for it."""
    grid, _, exe = _map_files(game_dir)
    cells = _castle_cells(exe)
    checked, bad = 0, []
    for r in rows:
        if "pos" not in r:
            continue
        checked += 1
        c, row = _cell_at(r["pos"]["x"], r["pos"]["y"])
        if (c, row) != cells[r["id"]] or _cell(grid, c, row)[2] & 0xF != 0xE:
            bad.append(f"{r['id']}: pos {r['pos']['x']},{r['pos']['y']} is not on its castle cell")
    flagged = sum(1 for c in range(MAP_COLS) for r in range(MAP_ROWS) if _cell(grid, c, r)[2] & 0xF == 0xE)
    if flagged != len(set(cells)):
        bad.append(f"{flagged} castle cells on the grid, {len(set(cells))} in the castle table")
    return checked, bad


def places(game_dir, out_dir):
    sns, _, exe, _ = _load(game_dir)
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    world_map(game_dir).save(os.path.join(out_dir, "world", NOBU5_WORLD_FILE))
    cells = _castle_cells(exe)
    years = _years(sns)
    provinces = province_names(exe)
    rows = []
    for k in range(173):
        names = [_name(sn[CITIES + 38 * k + 2:][:9]) for sn in sns]
        province = sns[0][CITIES + 38 * k + 11]
        assert all(sn[CITIES + 38 * k + 11] == province for sn in sns)
        row = {"id": k, "name": names[0], "level": "城", "province": provinces[province],
               "notes": f"城的號碼是遊戲的城號（九州往東北排）。名稱取劇本 1（{years[0]} 年）；城表裡的名字不含「城」字。"
                        f"pos 是大地圖 world/{NOBU5_WORLD_FILE}（{MAP_W}×{MAP_H}）上城格的中心像素；"
                        "大地圖是 120×23 格、一格 16 點，奇數欄往下錯半格。遊戲資料沒有城與城的相鄰關係，所以沒給 adjacent。",
               "pos": {"x": cells[k][0] * CELL + CELL // 2,
                       "y": cells[k][1] * CELL + (CELL // 2 if cells[k][0] & 1 else 0) + CELL // 2,
                       "grid": "pixel", "w": MAP_W, "h": MAP_H}}
        renamed = [f"劇本 {n + 1}（{years[n]}）{name}" for n, name in enumerate(names) if name != names[0]]
        if renamed:
            row["notes"] += "其他劇本的名稱：" + "、".join(renamed) + "。"
        rows.append(row)
    for k, name in enumerate(provinces):
        rows.append({"id": PROVINCE_BASE + k, "name": name, "level": "國",
                     "notes": f"國號 {k}，地點號是國號＋{PROVINCE_BASE}。國名在 MAIN.EXE 的國名字串；國本身沒有記錄（金、兵在城上），"
                              "有些是兩國合成一格（筑前対馬、阿波淡路…），有些一國拆成兩格（北／南近江…）。沒有相鄰表。"})
    return rows
