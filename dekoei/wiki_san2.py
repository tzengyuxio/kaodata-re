"""三國志II (san2-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san2-pc98 id: scenarios 1-6 then
TAIKI.DAT, deduplicated by face code (san2.load_san2_jp_persons). Names are the DOS Chinese release's (san2-dos, same
ids and face codes), the PC-98 ones go to nameJa. Layout and evidence: notes/san2.md「koei-wiki 匯出」,
notes/san-attributes.md「三國志II」.

SNDATAn.CIM (0x33AF bytes): u16 year at +2 (the game shows it + 1), 255 person records of 43 bytes from 0x16, 16
factions of 41 bytes from 0x2AF2, 41 provinces of 35 bytes from 0x2D82. Pointers are run-time offsets: person slot
s is at 88 + 43 s, province p (1-41) at 0x2DC4 + 35 (p - 1)."""
import os
import struct

import kaodata_export as ke
import san2
from san_person import s2_format, s2_format_taiki
from common import u16
from PIL import Image
from places_export import BATTLE, _areas, _save, _text

DATASET = "san2-pc98"
SIZE, PERSONS, SLOTS, BASE = 43, 0x16, 255, 88
FACTIONS, FACTION_SIZE = 0x2AF2, 41  # u16 君主, u16 capital province, u16 軍師 (pointers)
PROVINCES, PROVINCE_SIZE, PROVINCE_BASE = 0x2D82, 35, 0x2DC4  # +2 現役 chain, +6 在野 chain, +16 owner faction
HIDDEN = [(7, "義理"), (8, "人徳"), (9, "野望"), (15, "相性")]
# the DOS Chinese version gives 31 張顗 the name of 310 張嶷; the PC-98 name is right, so name takes the historical
# spelling instead (notes/san2.md)
ZH_OTHER_PERSON = {31}


def _scenario(d):
    """{slot: (record, status, location, faction)} and the faction rulers {faction: slot}."""
    rec = [d[PERSONS + s * SIZE:PERSONS + (s + 1) * SIZE] for s in range(SLOTS)]
    slot = lambda p: (p - BASE) // SIZE  # noqa: E731
    rulers, advisors = {}, set()
    for f in range(16):
        r = d[FACTIONS + f * FACTION_SIZE:][:6]
        if u16(r, 0):
            rulers[f] = slot(u16(r, 0))
            if u16(r, 4):
                advisors.add(slot(u16(r, 4)))
    out = {}
    for k in range(41):
        prov = d[PROVINCES + k * PROVINCE_SIZE:][:PROVINCE_SIZE]
        for chain, at in (("現役", 2), ("在野", 6)):
            p, first = u16(prov, at), True
            while p:
                s = slot(p)
                faction = rec[s][10]
                assert (faction == 255) == (chain == "在野") and s not in out
                if chain == "在野":
                    status = "在野"
                elif rulers.get(faction) == s:
                    status = "君主"
                elif s in advisors:
                    status = "軍師"
                elif first:
                    assert prov[16] == faction
                    status = "太守"
                else:
                    status = "現役"
                out[s] = (rec[s], status, k + 1, faction)
                p, first = u16(rec[s], 0), False
    assert len(out) == next(s for s in range(SLOTS) if rec[s][28:32] == bytes(4))
    return out, rulers


def persons(game_dir):
    jp = san2.load_san2_jp_persons(game_dir)
    face_id = {face: i for i, (face, _) in enumerate(jp)}
    dos = san2.load_san2_persons(os.path.join(game_dir, "..", "san2-dos", "SCENARIO.DAT"),
                                 os.path.join(game_dir, "..", "san2-dos", "TAIKI.DAT"))
    assert [p.face for p in dos] == [f for f, _ in jp]
    first = {}  # id -> the first record (scenario order, then TAIKI)
    scen = []
    for n in range(1, 7):
        with open(os.path.join(game_dir, f"SNDATA{n}.CIM"), "rb") as f:
            d = f.read()
        people, rulers = _scenario(d)
        year = u16(d, 2) + 1
        by_id = {}
        for s, (r, status, location, faction) in people.items():
            i = face_id[u16(r, 26)]
            first.setdefault(i, r)
            by_id[i] = (r, status, location, faction)
        lord_of = {f: face_id[u16(people[s][0], 26)] for f, s in rulers.items()}
        scen.append((year, by_id, lord_of))
    taiki = {}
    with open(os.path.join(game_dir, "TAIKI.DAT"), "rb") as f:
        t = f.read()
    tsize = struct.calcsize(s2_format_taiki)
    for k in range(420):
        r = t[6 + k * tsize:6 + (k + 1) * tsize]
        if r[31:35] == bytes(4):
            break
        i = face_id[u16(r, 29)]
        taiki.setdefault(i, r)
        first.setdefault(i, r[3:])
    assert struct.calcsize(s2_format) == SIZE and len(first) == len(jp)

    rows = []
    for i, (face, name_ja) in enumerate(jp):
        r = first[i]
        name = ke.SAN2_NAME_HISTORICAL[i] if i in ZH_OTHER_PERSON else dos[i]["name"]
        row = {"id": i, "name": name}
        if name_ja != name:
            row["nameJa"] = name_ja
        reading = ke.kana_to_hiragana(r[35:42].split(b"\0")[0].decode("cp932")).strip()
        if reading:
            row["reading"] = reading
        row["born"] = r[25]
        if i in taiki:
            row["debut"] = taiki[i][0]
        row["stats"] = {"知力": r[4], "武力": r[5], "魅力": r[6]}
        row["hidden"] = {**{k: r[o] for o, k in HIDDEN}, "親族": u16(r, 16)}
        out = []
        for n, (year, by_id, lord_of) in enumerate(scen):
            s = {"scenario": n + 1, "year": year}
            if i in by_id:
                rec, status, location, faction = by_id[i]
                s["status"] = status
                if faction != 255:
                    s["lord"] = lord_of[faction]
                s["location"] = location
                if status not in ("君主", "在野"):
                    s["loyalty"] = rec[11]
            elif i in taiki and taiki[i][0] >= year:
                s.update({"status": "未登場", "debut": taiki[i][0]})
                if 1 <= taiki[i][2] <= 41:
                    s["location"] = taiki[i][2]
            else:
                continue
            out.append(s)
        row["scenarios"] = out
        uncertain = ["hidden"]
        if i in taiki:
            uncertain.append("debut")
        if any(s["status"] == "未登場" for s in out):
            uncertain.append("scenarios.debut")
            if any(s["status"] == "未登場" and "location" in s for s in out):
                uncertain.append("scenarios.location")
        if any(s["status"] in ("太守", "軍師") for s in out):
            uncertain.append("scenarios.status")
        row["uncertain"] = uncertain
        notes = []
        if ke.yoshikawa_note(row["name"]):
            notes.append(ke.yoshikawa_note(row["name"]))
        elif i in ZH_OTHER_PERSON:
            notes.append(f"中文版寫成別人的名字「{dos[i]['name']}」，name 改用史書寫法。")
        elif i in ke.SAN2_NAME_HISTORICAL:
            notes.append(f"中文版寫法有誤，史書寫法 {ke.SAN2_NAME_HISTORICAL[i]}。")
        if i in ke.SAN2_JP_NAME_HISTORICAL and ke.SAN2_JP_NAME_HISTORICAL[i] != ke.SAN2_NAME_HISTORICAL.get(i):
            notes.append(f"日文版寫法有誤，史書寫法 {ke.SAN2_JP_NAME_HISTORICAL[i]}。")
        if i in taiki and not any(s["status"] != "未登場" for s in out):
            notes.append("只在 TAIKI.DAT（後登場武將表），不在任何劇本的初始資料。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows


##############################################################################
# 三國志II PC-98: 41 州 with numbers only; adjacency from san2.SAN2_PROVINCE_HEX (checked against the
# HEXDATA.DAT deployment layer). The names are borrowed from 三国志ツクール: its sample scenario (LINKDATA item
# 151) has 41 州 records in the same order with the same adjacency (notes/santsukuru.md「範例劇本」).
SANTSUKURU_ITEM, SANTSUKURU_PROVINCES = 151, 0x125FD  # first 州 record (0x40 bytes, name at +0x30)


SANTSUKURU_GAIJI = {0xF06D: "鄴", 0xF060: "邳", 0xF070: "鄱"}  # read off the place names


def santsukuru_provinces(game_dir):
    """[(name, x, y, [neighbour 0-based])] of the 41 州 of the 三国志ツクール sample scenario."""
    with open(os.path.join(game_dir, "LINKDATA.IDX"), "rb") as f:
        f.seek(32 * SANTSUKURU_ITEM)
        offset, _, stored, _ = struct.unpack("<4Q", f.read(32))
    with open(os.path.join(game_dir, "LINKDATA0.BIN"), "rb") as f:
        f.seek(offset)
        data = f.read(stored)
    out = []
    for k in range(41):
        r = data[SANTSUKURU_PROVINCES + 0x40 * k:][:0x40]
        assert r[0x29] == k
        x, y = struct.unpack_from("<HH", r, 0x1D)
        out.append((_text(r[0x30:0x40], SANTSUKURU_GAIJI), x, y, [b for b in r[0x23:0x29] if b != 0xFF]))
    return out


# MAPDATA.DAT: the left panel of the main screen, 296 x 400, 3 planes interleaved per 8 pixels (111 bytes a row,
# bit 0 B, bit 1 R, bit 2 G; the first 44400 bytes); all 400 rows match the capture main_000.raw1.png, where the
# white 州 are filled with the owners' colours. The game's 州 numbers are drawn on it. Each 州 is one white area;
# SAN2_MAP_POS is the point of each 州 (1-41) farthest from its border, picked by reading the numbers.
SAN2_MAP, SAN2_MAP_W, SAN2_MAP_H, SAN2_WHITE = "MAPDATA.DAT", 296, 400, 7


SAN2_MAP_POS = [(268, 44), (212, 86), (170, 79), (142, 88), (145, 111), (198, 126), (190, 115), (250, 122),
                (210, 141), (170, 134), (136, 130), (110, 122), (66, 157), (60, 104), (40, 94), (230, 157),
                (211, 171), (220, 182), (185, 211), (145, 207), (142, 232), (168, 299), (130, 261), (249, 188),
                (272, 259), (245, 271), (224, 277), (214, 219), (106, 208), (75, 179), (108, 253), (90, 257),
                (52, 213), (52, 277), (18, 312), (36, 333), (200, 326), (156, 317), (151, 346), (110, 276),
                (94, 332)]


def san2_world_map(game_dir):
    with open(os.path.join(game_dir, SAN2_MAP), "rb") as f:
        d = f.read()
    px = bytearray(SAN2_MAP_W * SAN2_MAP_H)
    for y in range(SAN2_MAP_H):
        for x in range(SAN2_MAP_W):
            o, bit = y * 111 + x // 8 * 3, 7 - x % 8
            px[y * SAN2_MAP_W + x] = sum(((d[o + k] >> bit) & 1) << k for k in range(3))
    im = Image.frombytes("P", (SAN2_MAP_W, SAN2_MAP_H), bytes(px))
    im.putpalette([255 * ((c >> b) & 1) for c in range(8) for b in (1, 2, 0)])
    return im


def world_check(game_dir, rows):
    """Each 州 pos is on a white area of its own, and the areas touch (across a border of up to 8 px) exactly as
    the adjacency says."""
    im = san2_world_map(game_dir)
    w, h = im.size
    lab = _areas(im, SAN2_WHITE)
    area = {lab[r["pos"]["y"] * w + r["pos"]["x"]]: r["id"] for r in rows}
    checked, bad = len(rows), [f"{r['id']}: pos not on a white area" for r in rows
                               if not lab[r["pos"]["y"] * w + r["pos"]["x"]]]
    if len(area) != len(rows):
        bad.append("two 州 share a white area")
    touch = set()
    for y in range(h):
        for x in range(w):
            a = area.get(lab[y * w + x])
            if a is None:
                continue
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    u, v = x + dx, y + dy
                    b = area.get(lab[v * w + u]) if 0 <= u < w and 0 <= v < h else None
                    if b and b != a:
                        touch.add((a, b))
    for r in rows:
        checked += 1
        if sorted(b for a, b in touch if a == r["id"]) != r["adjacent"]:
            bad.append(f"{r['id']}: map neighbours differ from adjacent")
    return checked, bad


def places(game_dir, out_dir):
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    san2_world_map(game_dir).save(os.path.join(out_dir, "world", "MAPDATA.png"))
    maps, _ = san2.render_san2_battle_maps(os.path.join(game_dir, "HEXDATA.DAT"))
    _save(maps, out_dir, [f"{n:02d}.png" for n in range(1, 42)])
    where = {qr: k + 1 for k, qr in enumerate(san2.SAN2_PROVINCE_HEX)}
    tsukuru_dir = os.path.join(game_dir, "..", "santsukuru-win")
    borrowed = santsukuru_provinces(tsukuru_dir)
    # 三国志ツクール's strategy map, for comparison: plain, and with its 41 州 numbered like ours; in compare/, since
    # every world/ map must fit the pos coordinates
    import santsukuru_extras
    labelled, plain, _ = santsukuru_extras.province_maps(santsukuru_extras.Linkdata(tsukuru_dir), tsukuru_dir)
    os.makedirs(os.path.join(out_dir, "compare"), exist_ok=True)
    plain.save(os.path.join(out_dir, "compare", "tsukuru-map.png"))
    labelled.save(os.path.join(out_dir, "compare", "tsukuru-provinces.png"))
    rows = []
    for k, (q, r) in enumerate(san2.SAN2_PROVINCE_HEX):
        adjacent = sorted(where[q + dq, r + dr] for dq, dr in san2.HEX_DIRS if (q + dq, r + dr) in where)
        name, _, _, tsukuru = borrowed[k]
        assert sorted(n + 1 for n in tsukuru) == adjacent, k + 1
        rows.append({"id": k + 1, "name": None, "nameBorrowed": {"name": name, "from": "santsukuru-win"},
                     "level": "州", "adjacent": adjacent,
                     "battlemaps": [{"file": f"{k + 1:02d}.png", "role": BATTLE}],
                     "pos": {"x": SAN2_MAP_POS[k][0], "y": SAN2_MAP_POS[k][1], "grid": "pixel", "w": SAN2_MAP_W,
                             "h": SAN2_MAP_H},
                     "uncertain": ["battlemaps"],
                     "notes": "州只有號碼，借用的名字來自三国志ツクール範例劇本（41 州的順序與相鄰關係和本作相同）。"
                              "pos 是大地圖 world/MAPDATA.png（296×400）上這一州白色區塊裡離州界最遠的點。"
                              "從哪個鄰州進攻只換布陣位置、不換地圖，沒在遊戲裡確認。"})
    return rows


# 三國志II PC-98: SNDATA1-6.CIM (0x16 header, s2_format records, face at +26) then TAIKI.DAT (6-byte header,
# s2_format_taiki: 3 bytes in front); 知力 武力 魅力 at +4-6 (TAIKI +7-9). The builder (load_san2_jp_persons) keeps
# the first record of each face code, so the values are that record's
SAN2_STATS = ["知力", "武力", "魅力"]


def stats(game_dir):
    out, seen = [], set()

    def add(rec, face_at, stats_at):
        if rec[face_at + 2:face_at + 6] == bytes(4):
            return False
        face = int.from_bytes(rec[face_at:face_at + 2], "little")
        if face not in seen:
            seen.add(face)
            out.append(dict(zip(SAN2_STATS, rec[stats_at:stats_at + 3])))
        return True

    size = struct.calcsize(s2_format)
    for n in range(1, 7):
        with open(os.path.join(game_dir, f"SNDATA{n}.CIM"), "rb") as f:
            d = f.read()
        for i in range(215):
            if not add(d[0x16 + i * size:0x16 + (i + 1) * size], 26, 4):
                break
    with open(os.path.join(game_dir, "TAIKI.DAT"), "rb") as f:
        d = f.read()
    size = struct.calcsize(s2_format_taiki)
    for i in range(420):
        if not add(d[6 + i * size:6 + (i + 1) * size], 29, 7):
            break
    names = san2.load_san2_jp_persons(game_dir, False)
    assert len(names) == len(out)
    return [(i, name, s) for i, ((_, name), s) in enumerate(zip(names, out))]
