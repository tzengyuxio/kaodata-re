"""三國志VI 威力加強版 (san6pk-win, 繁中版) for koei-wiki: persons (koei-persons/1). id is the kaodata san6pk-win id:
the person slots of SNDATA01-23.S6 in slot order, the four 武將 slots of each tribe counted once (as
kaodata_export.build_san6pk_win and stats() below). The game is only in Chinese, so there is no nameJa.
Layout and evidence: notes/san6.md「koei-wiki 匯出」, notes/san-attributes.md「三國志VI」.

Scenario file header: u16 year, u16 month. Factions: 27 x 0xC0 bytes from 0x7EF68, +10 u16 the ruler's slot (0xFFFF
none). Person record (650 bytes from sango.SAN6_PERSONS): +12 字, +32 身份 (SAN6.EXE pointer table 0x337EA0: 群雄 太守
一般), +34 狀況 (table 0x337EB0: 現役 在野 未發現 待命 俘虜 死亡), +36 出場年, +38 出生年, +44 faction (0xFFFF none),
+48 統率 武力 智力 政治 魅力, +68 忠誠, +76 city (= places id), +80 血緣, +82 father's slot (1000+ a group of brothers
with no father in the game, 0xFFFF none), +84 相性, +118 bits of 義理 野心 冷靜 勇猛."""
import os
import struct

import sango
from kaodata_export import SAN6PK_WIN_NAME_HISTORICAL
from common import u16
from places_export import _bmp_png
from biography import message_parts, offset_table, sections

DATASET = "san6pk-win"
FACTIONS, FACTION_SIZE, FACTION_COUNT = 0x7EF68, 0xC0, 27
RANKS = ("群雄", "太守", "一般")
STATES = ("現役", "在野", "未發現", "待命", "俘虜", "死亡")
# SAN6.EXE 0x34D338: the titles in the order of SNDATA01-23 (7 main, 7 historical, 單挑, 3 more, 5 of the PK)
TITLES = ["黃巾之亂", "董卓之野望", "群雄割據", "河北爭亂", "臥龍與鳳雛", "漢中王劉備", "星落五丈原",
          "義勇軍初陣", "呂布討伐戰", "河北統一戰", "皇帝袁術", "赤壁之戰", "馬超復仇", "出師表", "單挑",
          "誅殺董太師", "入蜀", "昭烈帝駕崩", "白馬長史", "小霸王的奇襲", "驅逐袁氏", "強行北伐", "諸葛誕的崛起"]
DUEL = 15  # 單挑: the duel mode's data (5 rulers, everyone else 現役 under them), not a starting placement
TRAITS = [("義理", 0, 4), ("野心", 4, 4), ("冷靜", 8, 3), ("勇猛", 11, 3)]  # (name, first bit, bits) of +118


def _text(b):
    return b.split(b"\0")[0].strip().decode("big5")


def _load(game_dir):
    """[(number, year, month, [record] by slot, [ruler slot] by faction)] of the 23 scenario files."""
    out = []
    for n in range(1, 24):
        with open(os.path.join(game_dir, f"SNDATA{n:02}.S6"), "rb") as f:
            d = f.read()
        recs = [d[sango.SAN6_PERSONS + s * sango.SAN6_PERSON_SIZE:][:sango.SAN6_PERSON_SIZE]
                for s in range(sango.SAN6_PERSON_SIZE)]
        rulers = [u16(d, FACTIONS + f * FACTION_SIZE + 10) for f in range(FACTION_COUNT)]
        out.append((n, u16(d, 0), u16(d, 2), recs, rulers))
    return out


def persons(game_dir):
    scen = _load(game_dir)
    # ids as build_san6pk_win: the first slot of each (name, face code)
    ids, slot_of = {}, {}
    for slot, name, code in sango.load_san6_persons(game_dir):
        if (name, code) not in ids:
            ids[(name, code)] = len(ids)
            slot_of[ids[(name, code)]] = slot
    id_of = {s: i for i, s in slot_of.items()}
    assert len(ids) == 532
    first = {}  # the record of the first scenario where the slot has a face (stats are the same in all 23)
    for _, _, _, recs, _ in scen:
        for i, s in slot_of.items():
            if i not in first and u16(recs[s], 30):
                first[i] = recs[s]

    father = {i: id_of[u16(first[i], 82)] for i in slot_of if u16(first[i], 82) in id_of}
    group = {i: u16(first[i], 82) for i in slot_of if 1000 <= u16(first[i], 82) < 0xFFFF}
    children = {}
    for c, p in father.items():
        children.setdefault(p, []).append(c)

    rows = []
    for i, s in slot_of.items():
        r = first[i]
        name = _text(r[0:6]) + _text(r[6:12])
        row = {"id": i, "name": name}
        courtesy = _text(r[12:18])
        if courtesy:
            row["courtesy"] = courtesy
        row["born"] = u16(r, 38)
        row["stats"] = dict(zip(sango.SAN6_STATS, struct.unpack_from("<5H", r, 48)))
        bits = u16(r, 118)
        row["hidden"] = {"相性": u16(r, 84), **{k: bits >> b & (1 << n) - 1 for k, b, n in TRAITS}}
        rel = {}
        if i in father:
            rel["father"] = [father[i]]
        if i in children:
            rel["children"] = sorted(children[i])
        sib = sorted(j for j in slot_of if j != i and (
            (i in father and father.get(j) == father[i]) or (i in group and group.get(j) == group[i])))
        if sib:
            rel["siblings"] = sib
        if u16(r, 80) != 0xFFFF:
            rel["clan"] = u16(r, 80)
        if rel:
            row["relations"] = rel

        out = []
        for n, year, month, recs, rulers in scen:
            if n == DUEL:
                continue
            p = recs[s]
            if not u16(p, 30):
                continue
            state = u16(p, 34)
            e = {"scenario": n, "year": year, "month": month}
            if state == 0:
                e["status"] = RANKS[u16(p, 32)]
                faction = u16(p, 44)
                if faction < FACTION_COUNT and rulers[faction] in id_of:
                    e["lord"] = id_of[rulers[faction]]
                e["location"] = u16(p, 76)
                if e["status"] != "群雄":
                    e["loyalty"] = p[68]
            else:
                e["status"] = STATES[state]
                if state == 3:
                    e["debut"] = u16(p, 36)
                elif state != 5:
                    e["location"] = u16(p, 76)
            out.append(e)
        if out:
            row["scenarios"] = out
        row["uncertain"] = ["hidden.義理", "hidden.野心", "hidden.冷靜", "hidden.勇猛"] + \
            (["relations.clan"] if "clan" in rel else []) + \
            (["scenarios.loyalty"] if any("loyalty" in e for e in out) else [])
        notes = []
        if name in SAN6PK_WIN_NAME_HISTORICAL:
            notes.append(f"史書寫法 {SAN6PK_WIN_NAME_HISTORICAL[name]}。")
        if s >= 520:
            notes.append("異族（南蠻、匈奴、烏丸、山越、羌、氐）；每族的 4 筆「武將」記錄同名同頭像，只列一人，劇本資料取第一筆。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows


##############################################################################
# 三國志VI 中文 PK: SNDATA01.S6 (Big5) 51 cities from 0x803A8 (0x68 bytes: name +0, SHIRO number +0x32 u16;
# 45-50 are the 外族) and 117 field places from 0x81994 (0x1E bytes: name +0, SENJOU number +0x18 u16). SAN6.EXE
# file 0x34F808: per city 6 x (i16 neighbour city, i16 field place), compared in order at RVA 0x25ADA9. The maps
# SENJOU0-39.S6 / SHIRO0-38.S6 are 1008 x 720 8-bit BMPs. Place ids here: cities 0-50, field place p is 51 + p
# (its MAPDATA.S6 part number).
SAN6_CITIES, SAN6_PLACES, SAN6_LINKS = 0x803A8, 0x81994, 0x34F808


def places(game_dir, out_dir):
    with open(os.path.join(game_dir, "SNDATA01.S6"), "rb") as f:
        sn = f.read()
    with open(os.path.join(game_dir, "SAN6.EXE"), "rb") as f:
        exe = f.read()

    def big5(b):
        return b.split(b"\0")[0].decode("big5").strip()

    cities = [(big5(sn[SAN6_CITIES + 0x68 * i:][:12]), struct.unpack_from("<H", sn, SAN6_CITIES + 0x68 * i + 0x32)[0])
              for i in range(51)]
    places = [(big5(sn[SAN6_PLACES + 0x1E * p:][:24]), struct.unpack_from("<H", sn, SAN6_PLACES + 0x1E * p + 0x18)[0])
              for p in range(117)]
    links = [[struct.unpack_from("<hh", exe, SAN6_LINKS + 0x18 * c + 4 * k) for k in range(6)] for c in range(51)]
    links = [[(nb, p) for nb, p in ls if nb >= 0] for ls in links]
    for _, s in cities:
        _bmp_png(os.path.join(game_dir, f"SHIRO{s}.S6"), out_dir, f"SHIRO{s}.png")
    for _, s in places:
        _bmp_png(os.path.join(game_dir, f"SENJOU{s}.S6"), out_dir, f"SENJOU{s}.png")
    shiro_users, senjou_users = {}, {}
    for c, (_, s) in enumerate(cities):
        shiro_users.setdefault(s, []).append(c)
    for p, (_, s) in enumerate(places):
        senjou_users.setdefault(s, []).append(51 + p)
    direction = "攻方、守方的方向（第一欄是守方、鄰城是攻方來處）是用古戰場的地理推定的，呼叫端沒追。"
    rows = []
    for c, (name, s) in enumerate(cities):
        maps = [{"file": f"SHIRO{s}.png", "role": "攻城"}]
        if len(shiro_users[s]) > 1:
            maps[0]["sharedWith"] = [x for x in shiro_users[s] if x != c]
        for nb, p in links[c]:
            maps.append({"file": f"SENJOU{places[p][1]}.png", "role": "野戰", "from": nb})
        rows.append({"id": c, "name": name, "level": "都市" if c < 45 else "外族", "adjacent": [nb for nb, _ in links[c]],
                     "battlemaps": maps, "uncertain": ["battlemaps"],
                     "notes": "攻城圖取都市記錄的 SHIRO 號；野戰圖依攻方從哪個鄰城來，查 SAN6.EXE 的鄰城表得到野戰地點，"
                              "再取地點的 SENJOU 號。" + direction + ("45–50 號是外族，遊戲的都市表裡和都市同列。" if c >= 45 else "")})
    for p, (name, s) in enumerate(places):
        users = sorted({c for c in range(51) for nb, q in links[c] if q == p})
        row = {"id": 51 + p, "name": name, "level": "野戰地點",
               "battlemaps": [{"file": f"SENJOU{s}.png", "role": "野戰"}], "uncertain": ["level"]}
        shared = [x for x in senjou_users[s] if x != 51 + p]
        if shared:
            row["battlemaps"][0]["sharedWith"] = shared
        row["notes"] = ("野戰地點的號碼是遊戲的地點號＋51（MAPDATA.S6 的段號）。「野戰地點」是這邊的分類。"
                        + ("名稱是「都市名＋數字」，像開發時的標記，不是地名。" if name[-1:].isdigit() or name[-1:] in "０１２３４５６７８９" else "")
                        + "用到這個地點的守方都市：" + "、".join(cities[c][0] for c in users) + "。")
        rows.append(row)
    return rows


def stats(game_dir):
    # build_san6pk_win: load_san6_persons (slot order, first seen over SNDATA01-23), dedup by (name, code); stats
    # from the scenario where the slot first has a face (the same in all 23 per notes)
    first = {}
    for n in range(1, 24):
        with open(os.path.join(game_dir, f"SNDATA{n:02}.S6"), "rb") as f:
            data = f.read()
        for slot in range(sango.SAN6_PERSON_SIZE):
            r = sango.SAN6_PERSONS + slot * sango.SAN6_PERSON_SIZE
            if int.from_bytes(data[r + 30:r + 32], "little") and slot not in first:
                first[slot] = struct.unpack_from("<5H", data, r + 48)
    out, seen = [], set()
    for slot, name, code in sango.load_san6_persons(game_dir):
        if (name, code) in seen:
            continue
        seen.add((name, code))
        out.append((len(out), name, dict(zip(sango.SAN6_STATS, first[slot]))))
    return out


# 三國志VI PK: MESSAGE.S6 is LS11; each part is a u16 count and count u16 offsets (from the part's start). Parts 1-6
# are the biographies by face code - 1 (521 messages, the last 「沒有列傳。」), one section in Big5: display lines of
# \x01" + text + \n (they break inside words, so they are joined), ending \x05\x05\x05. The kaodata id of persons
# 0-519 is the slot; the 12 tribe leaders (faces 539-550) have none
SAN6_BIO_PARTS = range(1, 7)


def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    parts = message_parts(os.path.join(game_dir, "MESSAGE.S6"))
    bios = [m for k in SAN6_BIO_PARTS for m in offset_table(parts[k], True)]
    out = {}
    for slot, _, face in sango.load_san6_persons(game_dir):
        if face < len(bios):
            t = bios[face - 1].replace(b'\x01"', b"").replace(b"\n", b"").rstrip(b"\x05")
            out[slot] = sections("", [("單段", t.decode("cp950"))])
    return out


def bio_names(game_dir) -> dict[int, str]:
    return {slot: name for slot, name, _ in sango.load_san6_persons(game_dir)}


BIO_LANG = "zh-Hant"  # biography.py: the 列傳 are read from the Chinese release
