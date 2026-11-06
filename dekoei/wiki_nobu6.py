"""信長の野望・天翔記 with パワーアップキット (PC-98, nobu6pk-pc98) for koei-wiki: persons (koei-persons/1), places
(koei-places/1) and the 列伝. Formats and how sure each field is: notes/nobu6.md「劇本段的完整配置」「人物欄位」「地理」;
the export is described in its「koei-wiki 匯出」."""
import os
import re
import struct
import unicodedata

import ls11
from kaodata_export import NOBU6PK_PC98_ALIASES, nobu6pk_pc98_face
from koei_games import NOBU6_PC98_GAIJI, _nobu6_pc98_text

# SNDATA.N6P part (one per scenario, 60848 bytes; tables numbered from 1): +0xB7 start year - 1454
PEOPLE, NAMES, CASTLES, CASTLE_POS, DAIMYO, PROVINCES = 0xAE2, 0x6C8E, 0x91F6, 0xAD8C, 0xC5CA, 0xCBFA
SLOTS = 531  # slot 532 is scratch
TAIKI_ENTRY, TAIKI_RECORD = 5, 47 + 18  # TAIKI part: n 5-byte arrival entries, n 47-byte records, n name records
STATES = ["大名", "軍団長", "一般", "隠居", "浪人", "姫", "待機", "死亡"]  # name record +0x10 bit 0-3
RANKS = [None, "大名", "宿老", "家老", "部将", "侍大将", "足軽頭"]  # bit 4-7
SKILLS = ["一喝", "暗殺", "流出", "煽動", "流言", "弁舌", "焼討", "挑発"]  # +0x29, bit i
JOBS = [None, "忍者", "茶人", "剣豪", "僧侶"]  # +0x2A bit 4-6
# 國 order runs by region (MAINPK.EXE has the names, no 國 -> region table was found): first 國 of each
REGIONS = [("東北", 0), ("関東", 8), ("東海", 17), ("甲信", 24), ("北陸", 28), ("畿内", 35), ("山陰", 45), ("山陽", 51),
           ("四国", 59), ("九州", 64)]
PROVINCE_ID = 1000  # place id of 國 n (1-74) is 1000 + n; 城 n (1-214) keeps n
MAP_W, MAP_H = 170, 42  # MAINMAP.NB6 part 1: 5 bytes a cell, +3 road tile (FF none), +4 castle cell (FF none)
DIRS = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
BIO_LANG = "ja"


def _u16(b, o):
    return b[o] | b[o + 1] << 8


def _name(rec):
    return _nobu6_pc98_text(rec[:7].split(b"\0")[0]) + _nobu6_pc98_text(rec[7:14].split(b"\0")[0])


def _parts(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return ls11.ls11_decode_parts(f.read())


def _ids(game_dir):
    """face number -> kaodata person id, id -> name, as build_nobu6_pc98(pk=True) numbers the characters: one per
    face (the face code of TABLE.N6P), in order of first appearance, aliases merged."""
    with open(os.path.join(game_dir, "TABLE.N6P"), "rb") as f:
        data = f.read()
    table = struct.unpack(f"<{len(data) // 2}H", data)
    names = {}
    for sc, wait in zip(_parts(game_dir, "SNDATA.N6P"), _parts(game_dir, "TAIKI.N6P")):
        for rec, _ in _records(sc, wait):
            name = _name(rec)
            names.setdefault(_u16(rec, 14), NOBU6PK_PC98_ALIASES.get(name, name))
    codes = {}
    for face, name in names.items():
        codes[nobu6pk_pc98_face(face, table)] = name
    order = {code: i for i, code in enumerate(codes)}
    return {face: order[nobu6pk_pc98_face(face, table)] for face in names}, dict(enumerate(codes.values()))


def _records(sc, wait):
    """(name record, (ability record, slot or None, arrival entry or None)) of a scenario's people, then the arrivals."""
    out = []
    for slot in range(SLOTS):
        rec = sc[NAMES + 18 * slot:][:18]
        if rec[0]:
            out.append((rec, (sc[PEOPLE + 47 * slot:][:47], slot + 1, None)))
    n = len(wait) // (TAIKI_ENTRY + TAIKI_RECORD)
    for i in range(n):
        rec = wait[n * (TAIKI_ENTRY + 47) + 18 * i:][:18]
        if rec[0]:
            out.append((rec, (wait[n * TAIKI_ENTRY + 47 * i:][:47], None, wait[TAIKI_ENTRY * i:][:TAIKI_ENTRY])))
    return out


##############################################################################
# 列伝 BFILE.N6P (LS11): part k >= 1 holds 50 persons, header and body each (u16 offset table first); person j of
# part k is face number 50 (k - 1) + j. Header: name ESC k reading ESC H birth～death (???? unknown). Half-width kana
# is hiragana in the body, katakana between ESC K and ESC H; pages end with 05 05 05, lines are only wrapping.
def _entries(game_dir):
    out = {}
    for k, part in enumerate(_parts(game_dir, "BFILE.N6P")[1:]):
        n = _u16(part, 0) // 2
        offs = list(struct.unpack_from(f"<{n}H", part, 0)) + [len(part)]
        for j in range(n // 2):
            out[50 * k + j] = (part[offs[2 * j]:offs[2 * j + 1]], part[offs[2 * j + 1]:offs[2 * j + 2]])
    return out


def _kana(s, hiragana):
    s = unicodedata.normalize("NFKC", s)
    return "".join(chr(ord(c) - 0x60) if hiragana and "ァ" <= c <= "ヶ" else c for c in s) if hiragana else s


def _bio_text(b):
    out, i, katakana = [], 0, False
    while i < len(b):
        gaiji = next((k for k in NOBU6_PC98_GAIJI if b.startswith(k, i)), None)
        if gaiji:
            out.append(NOBU6_PC98_GAIJI[gaiji])
            i += len(gaiji)
        elif b[i] == 0x1B:
            katakana, i = b[i + 1] in b"Kk", i + 2
        elif 0xA1 <= b[i] <= 0xDF:
            j = i
            while j < len(b) and 0xA1 <= b[j] <= 0xDF:
                j += 1
            run = b[i:j].decode("cp932")
            out.append(("ヶ" if run == "ｹ" else _kana(run, False)) if katakana else _kana(run, True))
            i = j
        else:
            n = 2 if 0x81 <= b[i] <= 0x9F or 0xE0 <= b[i] <= 0xFC else 1
            out.append(b[i:i + n].decode("cp932"))
            i += n
    return "\n".join(p.replace("\n", "") for p in "".join(out).split("\x05\x05\x05")).strip()


def _header(b):
    m = re.match(rb"(.*?) \x1bk(.*?)\x1bH ([\d?]{4})\x81\x60([\d?]{4})", b, re.S)
    born, died = (None if y == b"????" else int(y) for y in (m.group(3), m.group(4)))
    return _nobu6_pc98_text(m.group(1)), unicodedata.normalize("NFKC", m.group(2).decode("cp932")), born, died


def bios(game_dir):
    face_id, _ = _ids(game_dir)
    return {face_id[face]: [("單段", _bio_text(body))] for face, (_, body) in _entries(game_dir).items()
            if face in face_id}


def bio_names(game_dir):
    return _ids(game_dir)[1]


##############################################################################
def persons(game_dir):
    face_id, names = _ids(game_dir)
    entries = _entries(game_dir)
    scenarios = list(zip(_parts(game_dir, "SNDATA.N6P"), _parts(game_dir, "TAIKI.N6P")))
    rows, father_of, couples = {}, {}, {}
    for s, (sc, wait) in enumerate(scenarios):
        year = 1454 + sc[0xB7]
        people = _records(sc, wait)
        slot_id = {slot: face_id[_u16(rec, 14)] for rec, (_, slot, _) in people if slot}
        lords = {k + 1: slot_id.get(_u16(sc, DAIMYO + 22 * k)) for k in range(72)}
        for rec, (r, slot, arrival) in people:
            i = face_id[_u16(rec, 14)]
            flags = _u16(rec, 0x10)
            state, rank = STATES[flags & 0xF], RANKS[flags >> 4 & 0xF]
            entry = {"scenario": s + 1, "year": year}
            lord = _u16(r, 0x15) if arrival is None else _u16(arrival, 3)
            if lords.get(lord) is not None:
                entry["lord"] = lords[lord]
            where = _u16(r, 0x19) if arrival is None else _u16(arrival, 1)
            if 1 <= where <= 214:
                entry["location"] = where
            entry["status"] = state
            if rank and state != "姫":
                entry["rank"] = rank
            if state not in ("大名", "姫") and arrival is None:
                entry["loyalty"] = r[0x11]
            if arrival is not None:
                entry["debut"] = 1454 + arrival[0]
            if i not in rows:
                apt = _u16(r, 0x2B)
                row = {"id": i, "name": names[i]}
                if _u16(rec, 14) in entries:
                    _, reading, _, died = _header(entries[_u16(rec, 14)][0])
                    row["reading"] = reading
                    if died:
                        row["died"] = died
                row["born"] = 1454 + r[0x23]
                row["stats"] = {label: r[6 + k] * _u16(r, 9 + 2 * k) // 1000
                                for k, label in enumerate(("政治", "戦闘", "智謀"))}
                row["stats"].update(魅力=r[0xF], 野望=r[0x10])
                row["more"] = {"政才": "CBA"[r[0x28] & 3], "戦才": "CBA"[r[0x28] >> 2 & 3],
                               "智才": "CBA"[r[0x28] >> 4 & 3], "勲功": _u16(r, 0x12), "仕官": r[0x21]}
                job = JOBS[r[0x2A] >> 4 & 7] if (r[0x2A] >> 4 & 7) < len(JOBS) else None
                if job:
                    row["more"]["職業"] = job
                row["hidden"] = {"相性": r[0x27]}
                row["aptitude"] = {**{k: "EDCBAS"[apt >> 3 * n & 7] for n, k in enumerate(("足軽", "騎馬", "鉄砲", "水軍"))},
                                   "大砲": "○" if apt & 0x1000 else "×", "鉄甲船": "○" if apt & 0x2000 else "×"}
                skills = [k for n, k in enumerate(SKILLS) if r[0x29] >> n & 1]
                if skills:
                    row["skills"] = {"技能": skills}
                row["relations"] = {}
                if r[0x14] != 0xFF:
                    row["relations"]["clan"] = r[0x14]
                row["scenarios"] = []
                row["_first"] = year
                rows[i] = row
                if _u16(r, 0x24) != 0xFFFF:
                    father_of[i] = _u16(r, 0x24)
            if r[0x22] != 0xFF:
                couples.setdefault((s, r[0x22]), set()).add(i)
            rows[i]["scenarios"].append(entry)
    # relations: +0x24 is the father's face number (2000- are groups of brothers whose father is not in the game),
    # +0x22 a couple number per scenario
    for i, f in father_of.items():
        if f in face_id and face_id[f] != i:
            rows[i]["relations"]["father"] = [face_id[f]]
            rows[face_id[f]]["relations"].setdefault("children", []).append(i)
    groups = {}
    for i, f in father_of.items():
        groups.setdefault(f, []).append(i)
    for members in groups.values():
        for i in members:
            others = sorted(set(members) - {i})
            if others:
                rows[i]["relations"]["siblings"] = others
    for pair in couples.values():
        for i in pair:
            others = sorted(pair - {i})
            if others:
                spouse = rows[i]["relations"].setdefault("spouse", [])
                spouse += [x for x in others if x not in spouse]
    out = []
    for i in sorted(rows):
        row = rows[i]
        first = row.pop("_first")
        if not row["relations"]:
            del row["relations"]
        uncertain = ["hidden.相性", "aptitude"]
        if "職業" in row["more"]:
            uncertain.append("more.職業")
        uncertain += [f"relations.{k}" for k in row.get("relations", {})]
        row["uncertain"] = uncertain
        row["notes"] = (f"能力取第一次出現的劇本（{first} 年）的值；政治、戦闘、智謀是上限×千分比÷1000，和畫面相同。"
                        "讀音與歿年取列伝標頭，生年取劇本檔。適性 E、S 是推定。相性、職業、一門（clan）、父子、兄弟、"
                        "夫妻是由資料推定的欄位。scenarios 的「身分」是身分欄（大名…足軽頭），status 是狀態欄。")
        out.append(row)
    return out


##############################################################################
def _roads(game_dir, pos):
    """Castles reached from each castle along the road layer. A road tile's exits are the directions in which at
    least 90% of its cells have a road or castle cell (inferred from the map itself); a step needs the exit on both
    sides. Castle cells (2 x 2) take any direction."""
    m = _parts(game_dir, "MAINMAP.NB6")[1]

    def cell(x, y):
        return m[(y * MAP_W + x) * 5:][:5] if 0 <= x < MAP_W and 0 <= y < MAP_H else None

    counts = {}
    for y in range(MAP_H):
        for x in range(MAP_W):
            c = cell(x, y)
            if c[3] == 0xFF or c[4] != 0xFF:
                continue
            r = counts.setdefault(c[3], [0] * 9)
            r[8] += 1
            for k, (dx, dy) in enumerate(DIRS):
                n = cell(x + dx, y + dy)
                if n and (n[3] != 0xFF or n[4] != 0xFF):
                    r[k] += 1
    exits = {t: {k for k in range(8) if r[k] >= 0.9 * r[8]} for t, r in counts.items()}
    owner = {(x + dx, y + dy): k for k, (x, y) in enumerate(pos) for dx in (0, 1) for dy in (0, 1)}

    def out_of(p):
        if p in owner:
            return set(range(8))
        c = cell(*p)
        return exits.get(c[3], set()) if c and c[3] != 0xFF else set()

    adj = []
    for k, (x, y) in enumerate(pos):
        start = [(x + dx, y + dy) for dx in (0, 1) for dy in (0, 1)]
        seen, stack, found = set(start), list(start), set()
        while stack:
            p = stack.pop()
            for d in out_of(p):
                q = (p[0] + DIRS[d][0], p[1] + DIRS[d][1])
                if q in seen or (d + 4) % 8 not in out_of(q):
                    continue
                if q in owner:
                    found.add(owner[q])
                    continue
                seen.add(q)
                stack.append(q)
        adj.append(sorted(found))
    return adj


def places(game_dir, out_dir):
    scenarios = _parts(game_dir, "SNDATA.N6P")
    sc = scenarios[0]
    years = [1454 + d[0xB7] for d in scenarios]
    names = [[_nobu6_pc98_text(d[CASTLES + 33 * k + 8:][:9].split(b"\0")[0]) for k in range(214)] for d in scenarios]
    provinces = [_nobu6_pc98_text(sc[PROVINCES + 25 * n:][:7].split(b"\0")[0]) for n in range(74)]
    province_of = [_u16(sc, CASTLE_POS + 8 * k) for k in range(214)]
    pos = [(sc[CASTLE_POS + 8 * k + 6], sc[CASTLE_POS + 8 * k + 7]) for k in range(214)]
    region = [next(r for r, first in reversed(REGIONS) if n >= first) for n in range(74)]
    adj = _roads(game_dir, pos)
    rows = []
    for k in range(214):
        p = province_of[k] - 1
        row = {"id": k + 1, "name": names[0][k], "level": "城", "province": provinces[p], "region": region[p],
               "adjacent": [j + 1 for j in adj[k]],
               "pos": {"x": pos[k][0], "y": pos[k][1], "grid": "square", "w": MAP_W, "h": MAP_H},
               "uncertain": ["region", "adjacent"]}
        notes = "名稱取劇本 1（1534 年）。"
        renamed = [(years[s], names[s][k]) for s in range(len(scenarios)) if names[s][k] != names[0][k]]
        if renamed:
            notes += "其他劇本的名稱：" + "、".join(f"{y} 年{n}" for y, n in renamed) + "。"
        row["notes"] = notes + ("相鄰是沿大地圖 MAINMAP.NB6 的道路圖層推算的（道路圖塊的出口由地圖本身統計），遊戲移動用的"
                                "相鄰判斷沒找到程式。地方是照國的排列順序推的。pos 是大地圖 170×42 格的左上角，城佔 2×2 格。")
        rows.append(row)
    for n in range(74):
        own = [k for k in range(214) if province_of[k] == n + 1]
        near = sorted({province_of[j] for k in own for j in adj[k]} - {n + 1})
        rows.append({"id": PROVINCE_ID + n + 1, "name": provinces[n], "level": "國", "region": region[n],
                     "adjacent": [PROVINCE_ID + x for x in near], "uncertain": ["region", "adjacent"],
                     "notes": f"國的 id 是 {PROVINCE_ID}＋國表號。國內的城：" + "、".join(names[0][k] for k in own) +
                              "。相鄰是由城的道路相鄰推出（有一條路跨國就算），地方照國的順序推。"})
    return rows
