"""三國志V (san5pk-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata san5pk-pc98 id (500 people,
scenarios 1-12 with SNDATA before TAIKI, deduplicated by face code, as stats() below). name is the DOS
Chinese version's spelling of the same face code (the two versions have the same records in the same order), nameJa
the PC-98 one. Field sources: notes/san5.md「koei-wiki 匯出」, notes/san-attributes.md「三國志V」."""
import os
import re

import kaodata_export as ke
import ls11
import sango
from common import u16
from PIL import Image
import struct
from places_export import _reading, _save, _text
import kaodata_export as K
from biography import koei_tw_text, message_parts, offset_table, sections

# SNDATA.S5 scenario part (PC-98 PK): u16 year at +577 (the year before for the January scenarios), u16 person
# count at +579; city n's 30-byte record at 961 + 30n (u16 heads of three person lists at +0 officers, +2 在野,
# +4 未発見; the next person is the ability record's +2); 18 force records of 77 bytes at 3899 (u16 ruler +2,
# u16 軍師 +14). Person numbers are 1-based indexes into the scenario's SNDATA person table.
YEAR, COUNT, CITIES, FORCES, FORCE_SIZE, N_FORCES = 577, 579, 961, 3899, 77, 18
# PC-98 MAIN.EXE 0x54742: 身分 君主 軍師 一般 修行 在野 未発見 待機 死亡, then 将軍 太守 皇帝
TITLE = re.compile(r'"(\d+)年 *([０-９\d]+)月 ([^"|]+?) *\|')
N_SCENARIOS = 11  # the 12th scenario of SNDATA.S5 has no title (MESSAGE.S5 part 13 lists 11) and is not exported
SEPARATE = 1000  # +32 parent face code; from 1000 up it is a sibling group without a parent in the game (🟡)
TEMPER = (("義理", 0, 15), ("野望", 4, 15), ("冷静", 8, 7), ("勇猛", 11, 7))  # +34 u16 bit fields (🟡)


def _titles(game_dir):
    """(year, month, name) of scenarios 1-11 from the scenario menu in MESSAGE.S5 part 13."""
    with open(os.path.join(game_dir, "MESSAGE.S5"), "rb") as f:
        part = ls11.ls11_decode_parts(f.read())[13]
    text = re.sub(rb"[\x00-\x1f]", b"|", part).decode("cp932", "replace")
    return [(int(y), int(m.translate(str.maketrans("０１２３４５６７８９", "0123456789"))), n)
            for y, m, n in TITLE.findall(text)]


def persons(game_dir):
    sn, tk = os.path.join(game_dir, "SNDATA.S5"), os.path.join(game_dir, "TAIKI.S5")
    stat_rows = stats(game_dir)
    codes = list(dict.fromkeys(c for _, _, c in sango.load_san5_persons(sn, tk, True)))
    assert len(codes) == len(stat_rows)
    cid = {c: i for i, c in enumerate(codes)}
    dos = os.path.join(game_dir, "..", "san5pk-dos")
    zh = {}
    for _, name, code in sango.load_san5_persons(os.path.join(dos, "SNDATA.S5"), os.path.join(dos, "TAIKI.S5")):
        zh.setdefault(code, name)
    assert set(zh) == set(codes)
    titles = _titles(game_dir)
    assert len(titles) == N_SCENARIOS
    parts = sango.san5_parts(sn)
    records = list(sango.san5_records(sn, tk, True))
    person = {}  # face code -> 38-byte person record (the same in every scenario)
    scen = []  # per scenario: {id: scenario entry}
    for k in range(N_SCENARIOS):
        part, (year, month, _) = parts[k], titles[k]
        assert u16(part, YEAR) == year - (month == 1)
        recs = [(a, b) for s, _, a, b in records if s == k + 1]
        count = u16(part, COUNT)
        pid = [cid[u16(b, 30)] for _, b in recs]
        lists = {}  # SNDATA index -> (city, list offset, first in the list)
        for n in range(1, 48):
            city = part[CITIES + 30 * n:][:30]
            for off in (0, 2, 4):
                h, first = u16(city, off), True
                while h not in (0, 0xFFFF):
                    a = recs[h - 1][0]
                    assert a[20] == n and h - 1 not in lists
                    lists[h - 1], h, first = (n, off, first), u16(a, 2), False
        assert len(lists) == count
        forces = {}
        for f in range(N_FORCES):
            r = part[FORCES + FORCE_SIZE * f:][:FORCE_SIZE]
            if u16(r, 2) not in (0, 0xFFFF):
                forces[f + 1] = (u16(r, 2) - 1, u16(r, 14) - 1)
        out = {}
        for i, (a, b) in enumerate(recs):
            person.setdefault(u16(b, 30), b)
            s = {"scenario": k + 1, "year": year, "month": month, "location": a[20]}
            if i >= count:
                s["status"] = "待機"
            else:
                city, off, first = lists[i]
                if a[21] == 0xFF:
                    assert off == (4 if a[10] & 1 else 2)
                    s["status"] = "未発見" if a[10] & 1 else "在野"
                else:
                    assert off == 0
                    ruler, adviser = forces[a[21]]
                    s["status"] = "君主" if i == ruler else "軍師" if i == adviser else "一般"
                    s["lord"] = pid[ruler]
                    if i != ruler:
                        s["loyalty"] = a[19]
                        if first:
                            s["rank"] = "太守"
            out[pid[i]] = s
        scen.append(out)

    by_code = {c: i for i, c in enumerate(codes)}
    rows = []
    for i, ((_, name_ja, st), code) in enumerate(zip(stat_rows, codes)):
        b = person[code] if code in person else next(b for _, _, _, b in records if u16(b, 30) == code)
        row = {"id": i, "name": zh[code]}
        if name_ja != zh[code]:
            row["nameJa"] = name_ja
        row["born"] = b[21] + 100
        row["stats"] = st
        temper = u16(b, 34)
        row["hidden"] = {"相性": b[20], **{k: temper >> sh & mask for k, sh, mask in TEMPER}}
        rel = {}
        parent = u16(b, 32)
        if parent < SEPARATE and parent in by_code:
            rel["father"] = [by_code[parent]]
        children = [j for j, c in enumerate(codes) if u16(_record(person, records, c), 32) == code]
        if children:
            rel["children"] = children
        if parent != 0xFFFF:
            sib = [j for j, c in enumerate(codes) if j != i and u16(_record(person, records, c), 32) == parent]
            if sib:
                rel["siblings"] = sib
        if b[22]:
            rel["clan"] = b[22]
        if rel:
            row["relations"] = rel
        out = [s[i] for s in scen if i in s]
        assert out
        row["scenarios"] = out
        row["uncertain"] = [f"hidden.{k}" for k in row["hidden"]] + (["relations.clan"] if "clan" in rel else []) + \
            (["relations.siblings"] if parent >= SEPARATE and "siblings" in rel else []) + \
            [f"scenarios.{k}" for k in ("loyalty", "rank") if any(k in s for s in out)]
        notes = []
        if code in ke.SAN5PK_NAME_HISTORICAL:
            notes.append(f"中文版寫法的史書寫法 {ke.SAN5PK_NAME_HISTORICAL[code]}。")
        if code in ke.SAN5PK_PC98_NAME_HISTORICAL:
            notes.append(f"日文版寫法的史書寫法 {ke.SAN5PK_PC98_NAME_HISTORICAL[code]}。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def _record(person, records, code):
    if code not in person:
        person[code] = next(b for _, _, _, b in records if u16(b, 30) == code)
    return person[code]


##############################################################################
# 三國志V PC-98 with PK: 47 cities at MAIN.EXE 0x41C20 (base game 0x3F3A0, byte-identical; 32 bytes: name +0 5,
# reading +5 7, six neighbours +12 1-based FF-padded). HEXMAP.S5 / HEXGRP.S5 are the base game's (byte-identical);
# the battle palette offsets are the base game's MAIN.EXE ones (the PK has the same bytes elsewhere).
SAN5PK_PC98_CITIES = 0x41C20


SAN5_WHITE, SAN5_BLACK = (238, 221, 204), (34, 34, 17)  # palette 15 and 8 of the default palette


SAN5_GAIJI = {7: "鄴", 17: "下邳", 20: "譙", 47: "鄱陽"}  # 1-based city numbers


SAN5PK_PC98_BOX = 24  # city record +24 u16 x, +26 u16 y: top left of the city's 32 x 32 box on MAINMAP.S5


SAN5_CAPTURE, SAN5_CAPTURE_AT, SAN5_FLAG = "guest-os-000.png", (160, 64), (0, -13, 30, 27)  # map scroll; flag box


def san5_world_boxes(game_dir):
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        exe = f.read()
    return {n: struct.unpack_from("<2H", exe, SAN5PK_PC98_CITIES + 32 * (n - 1) + SAN5PK_PC98_BOX) for n in range(1, 48)}


def world_check(game_dir, rows):
    """Each pos is (16, 12) into its city's box; the boxes lie inside the map without overlapping; under each castle
    is the city's outlined white name, centred on the box (within 5 px) and 24.5-32 px below its top; and in the capture guest-os-000 (map
    scrolled to 160, 64) every visible owned city has the game's ownership flag drawn exactly at box + (0, -13)."""
    boxes, bad = san5_world_boxes(game_dir), []
    im = sango.render_san5_world_map(game_dir, os.path.join(game_dir, "..", "san5-pc98", "MAIN.EXE"))
    w, h = im.size
    px = im.load()
    for r in rows:
        x, y = boxes[r["id"]]
        if (r["pos"]["x"], r["pos"]["y"]) != (x + 16, y + 12):
            bad.append(f"{r['id']}: pos is not its box + (16, 12)")
        if not (0 <= x and x + 32 <= w and 0 <= y and y + 32 <= h):
            bad.append(f"{r['id']}: box outside the map")
            continue
        text = [(u, v) for v in range(y + 19, min(h - 1, y + 41)) for u in range(max(1, x - 8), min(w - 1, x + 40))
                if px[u, v] == SAN5_WHITE and SAN5_BLACK in (px[u - 1, v], px[u + 1, v], px[u, v - 1], px[u, v + 1])]
        if len(text) < 40 or abs(sum(u for u, _ in text) / len(text) - x - 16) > 5 or \
                not 24.5 <= sum(v for _, v in text) / len(text) - y <= 32:
            bad.append(f"{r['id']}: no name centred under the box")
    for a in rows:
        for b in rows:
            (xa, ya), (xb, yb) = boxes[a["id"]], boxes[b["id"]]
            if a["id"] < b["id"] and abs(xa - xb) < 32 and abs(ya - yb) < 32:
                bad.append(f"{a['id']}, {b['id']}: boxes overlap")
    checked = 2 * len(rows)
    shot = os.path.join(game_dir, "..", "..", "captures", "screenshots", "san5pk-pc98", SAN5_CAPTURE)
    if not os.path.exists(shot):
        return checked, bad + [f"capture {SAN5_CAPTURE} missing"]
    cap, (ox, oy) = Image.open(shot).convert("RGB"), SAN5_CAPTURE_AT
    cp = cap.load()
    votes = {}
    for v in range(cap.size[1]):
        for u in range(cap.size[0]):
            votes.setdefault(px[u + ox, v + oy], {}).setdefault(cp[u, v], 0)
            votes[px[u + ox, v + oy]][cp[u, v]] += 1
    seen = {c: max(vs, key=vs.get) for c, vs in votes.items()}

    flagged = 0
    for r in rows:
        x, y = boxes[r["id"]]
        if not (ox + 6 <= x and x + 36 <= ox + 335 and oy + 18 <= y and y + 15 <= oy + 345):  # left of the window
            continue
        others = [(bx, by + SAN5_FLAG[1]) for n, (bx, by) in boxes.items() if n != r["id"]]
        d = [(u - x, v - y) for v in range(y - 18, y + 15) for u in range(x - 6, x + 36)
             if cp[u - ox, v - oy] != seen[px[u, v]] and
             not any(bx <= u < bx + SAN5_FLAG[2] and by <= v < by + SAN5_FLAG[3] for bx, by in others)]
        if len(d) < 20:
            continue  # no owner, no flag
        checked += 1
        flagged += 1
        if (min(u for u, _ in d), max(u for u, _ in d)) != (0, SAN5_FLAG[2] - 1) or \
                not SAN5_FLAG[1] <= min(v for _, v in d) <= SAN5_FLAG[1] + 1:
            bad.append(f"{r['id']}: the capture's flag is not at box + (0, -13)")
    if flagged < 5:
        bad.append(f"only {flagged} flags found in {SAN5_CAPTURE}")
    return checked, bad


def places(game_dir, out_dir):
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    sango.render_san5_world_map(game_dir, os.path.join(game_dir, "..", "san5-pc98", "MAIN.EXE")).save(
        os.path.join(out_dir, "world", "MAINMAP.png"))
    boxes = san5_world_boxes(game_dir)
    _save(sango.render_san5_battle_maps(game_dir, palette_exe=os.path.join(game_dir, "..", "san5-pc98", "MAIN.EXE")),
          out_dir, [f"{n:02d}.png" for n in range(1, 48)])
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        exe = f.read()
    rows = []
    for n in range(1, 48):
        r = exe[SAN5PK_PC98_CITIES + 32 * (n - 1):][:32]
        rows.append({"id": n, "name": SAN5_GAIJI.get(n) or _text(r[:5]), "reading": _reading(r[5:12]),
                     "level": "都市", "adjacent": [b for b in r[12:18] if b != 0xFF],
                     "battlemaps": [{"file": f"{n:02d}.png", "role": "攻城"}], "uncertain": ["battlemaps"],
                     "pos": {"x": boxes[n][0] + 16, "y": boxes[n][1] + 12, "grid": "pixel", "w": sango.SAN5_WORLD_W,
                             "h": sango.SAN5_WORLD_H},
                     "notes": "讀的是 PC-98 PK 版；都市表、戰場圖檔和本體 byte 相同。戰場 47 張，第 n 張是第 n 個"
                              "都市的圖（程式用同一個都市號選圖和色盤）；那個都市號是不是守方都市沒追。這一代野戰與攻城在同一張圖上，"
                              "role 填攻城是這邊的分類。戰場色盤隨季節變，華北、漢中、下弁以外的都市（都市表 +0x1E 沒有 bit 1）夏、冬改用另一組；"
                              "圖是春（1–3 月）的色盤，春季各都市相同。"
                              "pos 是大地圖 world/MAINMAP.png（800×592）上的像素：都市表 +24、+26 是遊戲的 32×32 都市框左上角，"
                              "pos 取框內 (16, 12)，約是城的圖示中心（城和地名畫在地圖裡）。"})
    return rows


def stats(game_dir):
    # build_san5pk(pc98=True): load_san5_persons(tail=1100) order, dedup by face code; name from
    # SAN5PK_PC98_NAME_PICK when the code has one
    sndata, taiki = os.path.join(game_dir, "SNDATA.S5"), os.path.join(game_dir, "TAIKI.S5")
    persons = sango.load_san5_persons(sndata, taiki, True, tail=1100)
    stats = sango.load_san5_stats(sndata, taiki, True, tail=1100)
    assert len(persons) == len(stats)
    out, seen = [], set()
    for (_, name, code), (_, name2, *v) in zip(persons, stats):
        assert name == name2
        if code in seen:
            continue
        seen.add(code)
        out.append((len(out), K.SAN5PK_PC98_NAME_PICK.get(code, name), dict(zip(sango.SAN5_STATS, v))))
    return out


# 三國志V PK: MESSAGE.S5 parts 1-10, 50 messages each (u16 count + offsets); message c is face code c. Persons are
# numbered as in kaodata_export.build_san5pk: scenario order, one per face code
SAN5_BIO_PARTS = range(1, 11)


def san5_persons(game_dir) -> dict[int, tuple[str, int]]:
    seen = {}
    for _, name, code in sango.load_san5_persons(os.path.join(game_dir, "SNDATA.S5"),
                                                  os.path.join(game_dir, "TAIKI.S5"), False, tail=1100):
        if code not in seen:
            seen[code] = (len(seen), name)
    return {i: (name, code) for code, (i, name) in seen.items()}


def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    parts = message_parts(os.path.join(game_dir, "MESSAGE.S5"))
    bios = [m for k in SAN5_BIO_PARTS for m in offset_table(parts[k], True)]
    return {i: sections("", [("單段", koei_tw_text(bios[code]))])
            for i, (_, code) in san5_persons(game_dir).items() if code < len(bios)}


def bio_names(game_dir):
    return {i: v[0] for i, v in san5_persons(game_dir).items()}


BIO_LANG = "zh-Hant"  # biography.py: the 列傳 are read from the Chinese release
