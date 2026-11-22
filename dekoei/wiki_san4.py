"""三國志IV PK (san4pk-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san4pk-pc98 id: the 462
scenario people (SNDATA.S4 then TAIKI.S4 of the 10 scenarios, deduplicated by (face code, name), as
kaodata_export.build_san4) and the 117 水滸伝 officers of NBDATA.SUI (462-578). Names are the DOS Chinese PK's
(san4pk-dos, same ids and faces), the PC-98 ones go to nameJa. Layout and evidence: notes/san4.md「koei-wiki 匯出」,
notes/san-attributes.md「三國志IV」.

Ability record a+ (20 bytes): +2-6 統率 武力 知力 政治 魅力, +11 忠誠, +12 city (= places id), +13 faction (255 none),
+14 u32 特殊能力 bits, +18 low nibble 身分 (MAIN.EXE DS:0x37EE table, read at 0e7f:99A0 as a+18 & 0xF). Person
record p+ (30 bytes): +9 reading (11 bytes half-width kana), +20 face code, +22 血縁, +24 相性, +25 born - 100, +27 24
bits of 義理 野望 冷静 勇猛. Scenario year: u16 at part offset 0x584."""
import os

import kaodata_export as ke
import sango
from places_export import _reading, _save, _text
import struct
from biography import koei_tw_text, message_parts, offset_table, sections

DATASET = "san4pk-pc98"
YEAR = 0x584
# scenario 10 (237) has all 400 people in city 0 under one ruler (劉諶): not a starting placement, so it is left out
SKIPPED = 9
STATUS = "君主 将軍 軍師 侍中 一般 在野 未発 死亡 待機 太守 捕虜 皇帝".split()
SKILLS = "外交 情報 人材 製造 作敵 駆虎 流言 焼計 諜報 歩兵 騎兵 弓兵 海戦 火計 落石 同討 天変 風変 混乱 連環 落雷 修復 罵声 虚報".split()
TRAITS = [("義理", 0, 4), ("野望", 4, 4), ("冷静", 11, 3), ("勇猛", 14, 3)]  # (name, first bit, bits) of p+27


def _skills(a):
    bits = int.from_bytes(a[14:18], "little")
    return [s for i, s in enumerate(SKILLS) if bits >> (i if i <= 8 else i + 3) & 1]


def _traits(p):
    bits = int.from_bytes(p[27:30], "little")
    return {k: bits >> b & (1 << n) - 1 for k, b, n in TRAITS}


def _scenarios(game_dir):
    """[(year, [(name, ability, person)] of SNDATA, [same] of TAIKI)] for the 10 scenarios; san4_records yields each
    part's SNDATA records (as many as its person table) before its TAIKI ones."""
    with open(os.path.join(game_dir, "SNDATA.S4"), "rb") as f:
        sn = sango.san4_parts(f.read())
    counts = []
    for part in sn:
        start = len(part)
        while start >= 30 and part[start - 30] >= 0x80 and part[start - 10:start - 8] != b"\xff\xff":
            start -= 30
        counts.append((len(part) - start) // 30)
    out = [(int.from_bytes(part[YEAR:YEAR + 2], "little"), [], []) for part in sn]
    seen = [0] * len(sn)
    for scenario, name, a, p in sango.san4_records(os.path.join(game_dir, "SNDATA.S4"),
                                                    os.path.join(game_dir, "TAIKI.S4"), True):
        k = scenario - 1
        (out[k][1] if seen[k] < counts[k] else out[k][2]).append((name, a, p))
        seen[k] += 1
    return out


def persons(game_dir):
    zh, _ = ke.build_san4(os.path.join(game_dir, "..", "san4pk-dos"), pk=True)
    ja, _ = ke.build_san4(game_dir, pc98=True, pk=True)
    zh, ja = zh["characters"], ja["characters"]
    assert len(zh) == len(ja) == 579 and all(a["face"] == b["face"] for a, b in zip(zh, ja))
    scen = _scenarios(game_dir)
    # ids as build_san4: first appearance of (face code, name) in scenario order, SNDATA before TAIKI
    ids, first = {}, {}
    for _, people, later in scen:
        for name, a, p in people + later:
            key = (int.from_bytes(p[20:22], "little"), name)
            if key not in ids:
                ids[key] = len(ids)
                first[ids[key]] = (a, p)
    assert len(ids) == 462 and all(ja[i]["name"] == n for (_, n), i in ids.items())
    code_of = {i: c for (c, _), i in ids.items()}
    by_face = {}
    for i, c in code_of.items():
        by_face.setdefault(c, i)
    kin = {i: int.from_bytes(p[22:24], "little") for i, (_, p) in first.items()}

    per = []  # per scenario: {id: (ability, status word)}, {faction: ruler id}, {id} of TAIKI
    for year, people, later in scen:
        here, rulers = {}, {}
        for name, a, p in people:
            i = ids[(int.from_bytes(p[20:22], "little"), name)]
            if i in here:
                continue  # the 4 異民族 have several records of one name and face (one army each)
            here[i] = a
            if a[18] & 0xF == 0 and a[13] != 0xFF:
                assert rulers.setdefault(a[13], i) == i
        taiki = {ids[(int.from_bytes(p[20:22], "little"), name)] for name, a, p in later} - set(here)
        per.append((year, here, rulers, taiki))

    rows = []
    for i in range(579):
        name = zh[i]["name"]
        row = {"id": i, "name": name}
        if ja[i]["name"] != name:
            row["nameJa"] = ja[i]["name"]
        notes = []
        for c, label in ((zh[i], "中文版"), (ja[i], "日文版")):
            if "nameHistorical" in c:
                notes.append(f"{label}寫法有誤，史書寫法 {c['nameHistorical']}。")
        if i >= 462:
            row.update(_suikoden(game_dir, i - 462))
            notes.append("威力加強版 NBDATA.SUI 的水滸伝武將，不在任何劇本裡（新武將登錄時可以選用）。")
            row["notes"] = "".join(notes)
            rows.append(row)
            continue
        a, p = first[i]
        reading = ke.kana_to_hiragana(p[9:20].split(b"\0")[0].decode("cp932")).strip()
        if reading:
            row["reading"] = reading
        row["born"] = p[25] + 100
        row["stats"] = dict(zip(sango.SAN4_STATS, a[2:7]))
        skills = _skills(a)
        if skills:
            row["skills"] = {"特殊能力": skills}
        row["hidden"] = {"相性": p[24], **_traits(p), "血縁": kin[i]}
        # 血縁: a person's face code makes that person the father (孫策 -> 孫堅); 1000 and up is a group number shared
        # by kin whose father is not in the game (袁紹 and 袁術 1001); same father = siblings
        relations = {}
        if kin[i] in by_face and by_face[kin[i]] != i:
            relations["father"] = [by_face[kin[i]]]
            sib = sorted(j for j, k in kin.items() if k == kin[i] and j != i)
            if sib:
                relations["siblings"] = sib
        elif kin[i] != 0xFFFF and kin[i] >= 1000:
            relations["clan"] = kin[i]
        children = sorted(j for j, k in kin.items() if k == code_of[i] and j != i)
        if children:
            relations["children"] = children
        if relations:
            row["relations"] = relations
        out = []
        for n, (year, here, rulers, taiki) in enumerate(per):
            if n == SKIPPED or i not in here:
                continue
            s = {"scenario": n + 1, "year": year}
            r = here[i]
            s["status"] = STATUS[r[18] & 0xF]
            if r[13] != 0xFF and r[13] in rulers:
                s["lord"] = rulers[r[13]]
            s["location"] = r[12]
            if r[18] & 0xF not in (0, 5, 6):
                s["loyalty"] = r[11]
            if row["stats"] != dict(zip(sango.SAN4_STATS, r[2:7])):
                s["stats"] = dict(zip(sango.SAN4_STATS, r[2:7]))
            out.append(s)
        if out:
            row["scenarios"] = out
        later = [n + 1 for n, (_, here, _, taiki) in enumerate(per) if i in taiki and n != SKIPPED]
        if later:
            notes.append(f"劇本 {'、'.join(map(str, later))} 是後登場武將（TAIKI.S4），登場年的規則沒追，所以這些劇本沒列。")
        row["uncertain"] = ["hidden"] + (["relations"] if relations else [])
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def _suikoden(game_dir, k):
    """reading, stats and skills of NBDATA.SUI officer k (117 x 20-byte ability records, then 117 x 30-byte persons)."""
    with open(os.path.join(game_dir, "NBDATA.SUI"), "rb") as f:
        nb = f.read()
    a, p = nb[k * 20:k * 20 + 20], nb[117 * 20 + k * 30:][:30]
    row = {}
    reading = ke.kana_to_hiragana(p[9:20].split(b"\0")[0].decode("cp932")).strip()
    if reading:
        row["reading"] = reading
    row["stats"] = dict(zip(sango.SAN4_STATS, a[2:7]))
    skills = _skills(a)
    if skills:
        row["skills"] = {"特殊能力": skills}
    return row


##############################################################################
# 三國志IV PC-98 with PK: 43 cities at MAIN.EXE 0x4615D (base game 0x3EA7D, byte-identical; 29 bytes: name +3,
# reading +8, neighbours +15 0-based FF-ended). Field maps: the table at 0x3FC28 (base 0x3855A, byte-identical to
# the SFC table) gives map table[6 * defender + k] for the k-th neighbour attacking; siege map 46 + city.
SAN4PK_PC98_CITIES, SAN4PK_PC98_FIELD = 0x4615D, 0x3FC28


SAN4_GAIJI = {6: "鄴", 16: "下邳", 19: "譙"}


SAN4_WORLD_W, SAN4_WORLD_H = sango.SAN4_WORLD_COLS * 16, sango.SAN4_WORLD_ROWS * 16


def san4_world_pos(game_dir):
    """{city: pixel} of the centre of the castle: the cell of layer 9 part 10 (middle of the 3 x 3 castle)."""
    pos = {}
    for y, row in enumerate(sango.san4_world_cells(game_dir)):
        for x, cell in enumerate(row):
            if cell[9] == 10 and cell[8] != 0xFF:
                assert cell[8] not in pos
                pos[cell[8]] = (x * 16 + 8, y * 16 + 8)
    return pos


def world_check(game_dir, rows):
    """Each pos is on a cell of its own city (layer 8) whose layer 2 is the middle tile of a castle (9 k + 4), the
    city's whole 3 x 5 area is cells of that city with parts 0-14 in order, and the map has no other cities."""
    cells = sango.san4_world_cells(game_dir)
    bad = []
    for r in rows:
        x, y = r["pos"]["x"] // 16, r["pos"]["y"] // 16
        if cells[y][x][8] != r["id"] or cells[y][x][2] == 0xFF or cells[y][x][2] % 9 != 4:
            bad.append(f"{r['id']}: pos not on the middle of its castle")
            continue
        area = [cells[y - 3 + k // 3][x - 1 + k % 3] for k in range(15)]
        if any(c[8] != r["id"] or c[9] != k for k, c in enumerate(area)):
            bad.append(f"{r['id']}: 3 x 5 area around pos is not the city's")
    found = {c[8] for row in cells for c in row if c[9] < 100 and c[8] != 0xFF}
    if found != {r["id"] for r in rows}:
        bad.append(f"cities on the map {sorted(found)} differ from the places")
    return len(rows), bad


def places(game_dir, out_dir):
    base = os.path.join(game_dir, "..", "san4-pc98", "MAIN.EXE")  # the palette offsets are the base game's
    _save(sango.render_san4_battle_maps(game_dir, palette_exe=base), out_dir, [f"{n:02d}.png" for n in range(1, 89)])
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    # MAINMAP.png is the spring map: the default palette (DS:0x1136) colours 0-7 never appear in the game
    for season, name in enumerate(("spring", "summer", "autumn", "winter")):
        im = sango.render_san4_world_map(game_dir, palette_exe=base, season=season)
        im.save(os.path.join(out_dir, "world", f"MAINMAP-{name}.png"))
        if season == 0:
            im.save(os.path.join(out_dir, "world", "MAINMAP.png"))
    pos = san4_world_pos(game_dir)
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        exe = f.read()
    recs = [exe[SAN4PK_PC98_CITIES + 29 * i:][:29] for i in range(43)]
    field = exe[SAN4PK_PC98_FIELD:][:43 * 6]
    adj = [[b for b in r[15:29] if b != 0xFF] for r in recs]
    users = {}
    for i in range(43):
        for k in range(len(adj[i])):
            users.setdefault(field[6 * i + k], set()).add(i)
    rows = []
    for i, r in enumerate(recs):
        maps = [{"file": f"{46 + i:02d}.png", "role": "攻城"}]
        for k, a in enumerate(adj[i]):
            m = {"file": f"{field[6 * i + k] + 1:02d}.png", "role": "野戰", "from": a}
            shared = sorted(users[field[6 * i + k]] - {i})
            if shared:
                m["sharedWith"] = shared
            maps.append(m)
        rows.append({"id": i, "name": SAN4_GAIJI.get(i) or _text(r[3:8]), "reading": _reading(r[8:15]),
                     "level": "都市", "adjacent": adj[i], "battlemaps": maps,
                     "pos": {"x": pos[i][0], "y": pos[i][1], "grid": "pixel", "w": SAN4_WORLD_W, "h": SAN4_WORLD_H},
                     "notes": "讀的是 PC-98 PK 版；都市表、野戰表和本體 byte 相同。野戰圖依攻方從哪個鄰城來而定"
                              "（from），攻城圖是都市自己的。攻城圖的色盤只隨季節變；野戰圖的色盤種類（乾黃、黃綠、翠綠）照打仗的都市，"
                              "共用的野戰圖取多數都市的種類。圖都是春（1–3 月）的色盤。"
                              "pos 是大地圖 world/MAINMAP.png（1536×1280，96×80 格、一格 16 點）上的像素：城的 3×3 格圖示"
                              "正中那格的中心（MAINMAP.S4 第 8 層是都市號）。"})
    return rows


def stats(game_dir):
    # build_san4(pc98=True, pk=True): load_san4_persons order (scenarios 1-6), dedup by (code, name), no name fix;
    # load_san4_stats yields the same records in the same order, so the first record of each kept person is used
    sndata, taiki = os.path.join(game_dir, "SNDATA.S4"), os.path.join(game_dir, "TAIKI.S4")
    persons = sango.load_san4_persons(sndata, taiki, True)
    stats = sango.load_san4_stats(sndata, taiki, True)
    assert len(persons) == len(stats)
    out, seen = [], set()
    for (_, name, code), (_, name2, *v) in zip(persons, stats):
        assert name == name2
        if (code, name) in seen:
            continue
        seen.add((code, name))
        out.append((len(out), name, dict(zip(sango.SAN4_STATS, v))))
    # then the 117 水滸伝 officers of NBDATA.SUI (ids 462-578); their 20-byte ability blocks have the SNDATA layout
    # (統率 武力 知力 政治 魅力 at +2)
    with open(os.path.join(game_dir, "NBDATA.SUI"), "rb") as f:
        nb = f.read()
    for k, (name, _) in enumerate(sango.load_san4pk_suikoden(os.path.join(game_dir, "NBDATA.SUI"), True)):
        out.append((len(out), name, dict(zip(sango.SAN4_STATS, nb[k * 20 + 2:k * 20 + 7]))))
    return out


# 三國志IV PK: MESSAGE.S4 parts 24-33 (454 messages; the offset table has no count). A plain face code c < 0x8000 is
# message c; a montage face is message 250 + its index in the MAIN.EXE 0x3EA98 table of codes (244, ends below
# 0x8000). Persons are numbered as in kaodata_export.build_san4: scenario order, by (code, name); the tribes (南蠻王…)
# and the 水滸伝 officers have none
SAN4_BIO_PARTS = range(24, 34)


SAN4_MONTAGE_CODES = 0x3EA98


def san4_persons(game_dir) -> dict[int, tuple[str, int]]:
    from kaodata_export import SAN4PK_DOS_NAME_FIX
    seen = {}
    for _, name, code in sango.load_san4_persons(os.path.join(game_dir, "SNDATA.S4"),
                                                  os.path.join(game_dir, "TAIKI.S4")):
        seen.setdefault((code, SAN4PK_DOS_NAME_FIX.get(name, name)), len(seen))
    return {i: (name, code) for (code, name), i in seen.items()}


def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    parts = message_parts(os.path.join(game_dir, "MESSAGE.S4"))
    bios = [m for k in SAN4_BIO_PARTS for m in offset_table(parts[k], False)]
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        exe = f.read()
    montage = []
    while (c := struct.unpack_from("<H", exe, SAN4_MONTAGE_CODES + 2 * len(montage))[0]) >= 0x8000:
        montage.append(c)
    out = {}
    for i, (_, code) in san4_persons(game_dir).items():
        k = code if code < 0x8000 else 250 + montage.index(code) if code in montage else None
        if k is not None and k < len(bios):
            out[i] = sections("", [("單段", koei_tw_text(bios[k], "。"))])
    return out


def bio_names(game_dir):
    return {i: v[0] for i, v in san4_persons(game_dir).items()}


BIO_LANG = "zh-Hant"  # biography.py: the 列傳 are read from the Chinese release
