"""信長の野望・将星録 with PK (nobu7pk-win) for koei-wiki: persons (koei-persons/1), 城 (koei-places/1) and 列伝.
The data is the Steam PK's (SNDATA01-10.NB7, 10 scenarios); the names come from the 中文視窗版 (../nobu7-win, the
same person and 城 numbers), the Japanese ones go to nameJa. Fields and evidence: notes/nobu7.md「人物欄位（全部）」
「地理」「koei-wiki 匯出」."""
import os
import re
import struct
import unicodedata

from PIL import Image

import koei_games
import ls11

# person records: 744 x 0x5C from 0x53D0 (koei_games.NOBU7_WIN_PERSONS); person n (1-744) is kaodata id n - 1, and
# only 1-716 are kaodata characters (717- are the unnamed 姫一-十六, 農民 and 佚名). 城 k (1-64) at 0x469C + 0x34 k.
PERSONS, COUNT, SIZE = koei_games.NOBU7_WIN_PERSONS
PEOPLE = 716
CASTLES = 0x469C
SCENARIOS = ["SNDATA01.NB7", "SNDATA02.NB7", "SNDATA03.NB7", "SNDATA04.NB7", "SNDATA05.NB7",
             "Sndata06.nb7", "Sndata07.nb7", "Sndata08.nb7", "Sndata09.nb7", "Sndata10.nb7"]
ZH_SCENARIOS = ["Sndata01.nb7", "Sndata02.nb7", "Sndata03.nb7", "Sndata04.nb7", "Sndata05.nb7"]
MAIN = 4  # scenario 5 (1582): the names kaodata uses; the person-level values are read from it too
# labels: the PK Nobunaga7WPK.exe strings (VA 0x521584-0x521680)
STATUS = ["大名", "現役", "独立", "浪人", "姫", "待機", "一向", "農民", "死亡"]
ABSENT = {5, 8}  # 待機, 死亡: not on the map in that scenario
JOBS = ["忍者", "茶人", "剣豪", "僧侶", "切支丹"]
RANKS = ["足軽頭", "侍大将", "部将", "家老", "宿老", "大名"]
ARMS = ["足軽", "騎馬", "鉄砲", "水軍"]
GRADES = " EDCBAS"
DOMESTIC = [(1, "農業"), (2, "商業"), (4, "建設"), (8, "外交"), (0x10, "登用"), (0x20, "抜穴")]
BATTLE = [(1, "騎突"), (2, "三段"), (4, "焙烙"), (8, "騎鉄")]  # 1 = 騎突 is inferred
BIO_LANG = "zh-Hant"
# 攻城圖: ATKMAP.NB7 holds 12 pictures of 768 x 512, 8 bit (u32 count, count x (offset, size, w, h), data from 4 + 16
# count). Castle k fights the siege on picture (城 +0x26): the ATKDATA.NB7 record of each castle (642 bytes, read by
# San7WPK VA 0x4065d0; type 11 = 安土 reads record 65, VA 0x4f87dc) gives cell positions that sit on that picture's
# marked squares for all 11 types in use (type 9 is never used). The palette is GRPPAL.NB7 part 0 (B, R, G), the one
# the screen code loads (VA 0x463fe0, part index < 2), judged by eye.
ATKMAP_TYPE = 0x26


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _scenarios(game_dir):
    return [_read(os.path.join(game_dir, n)) for n in SCENARIOS]


def _zh(game_dir, name=ZH_SCENARIOS[MAIN]):
    return _read(os.path.join(game_dir, "..", "nobu7-win", name))


def _name(data, k, encoding):
    """surname + given name of person k (0-based record)."""
    o = PERSONS + SIZE * k

    def text(b):
        b = b.split(b"\0")[0]
        return koei_games.NOBU7_WIN_GAIJI.get(b) or b.decode(encoding)

    return text(data[o:o + 8]) + text(data[o + 8:o + 16])


def _u16(data, k, field):
    return struct.unpack_from("<H", data, PERSONS + SIZE * k + field)[0]


def _records(data):
    """{person number: record index}"""
    return {_u16(data, k, 0x50): k for k in range(COUNT)}


def _castle_name(data, k, encoding):
    return data[CASTLES + 0x34 * k + 2:][:10].split(b"\0")[0].decode(encoding).strip()


def message_strings(part: bytes) -> list[bytes]:
    """The strings of one LS11 part of a message file: u16 count, count x u16 offsets, the strings."""
    n = struct.unpack_from("<H", part)[0]
    offsets = list(struct.unpack_from(f"<{n}H", part, 2)) + [len(part)]
    return [part[a:b] for a, b in zip(offsets, offsets[1:])]


BIO_HEAD = re.compile(r"^([^\x00-\x1f]+?)\s*(?:\x1bk(.*?)\x1bH)?\s*([0-9?]{4})[～∼]([0-9?]{4})$")


def half_kana(s: str) -> str:
    """Half-width katakana runs as full-width."""
    return re.sub(r"[｡-ﾟ]+", lambda m: unicodedata.normalize("NFKC", m.group()), s)


def biographies(parts, encoding) -> list[tuple[str, str, int, int, str]]:
    """(name, reading, born, died, text) of every person biography in the parts of a message file: a header string
    「name ESC k reading ESC H born～died」 followed by the text. Templates (generated 姫 and 新武将) start with
    control codes and are left out; years ???? are None."""
    out = []
    for part in parts:
        s = [x.decode(encoding, "replace") for x in message_strings(part)]
        for head, text in zip(s, s[1:]):
            m = BIO_HEAD.match(head.replace("\x05", "").strip())
            if not m:
                continue
            name, reading, born, died = m.groups()
            text = re.sub(r"\x1b[A-Za-z]", "", text)
            text = re.sub(r"[\x00-\x1f]", "", text).strip()
            out.append((name.strip(), half_kana(reading) if reading else None,
                        None if "?" in born else int(born), None if "?" in died else int(died), half_kana(text)))
    return out


def _bio_index(entries, names, born):
    """{person id: entry index} by name (any scenario's spelling), the birth year breaking ties; and the unmatched
    names. Entries left over are tried again without the persons already placed (two 武田信豊, one born ????)."""
    by_name = {}
    for i, ns in names.items():
        for n in ns:
            by_name.setdefault(n, set()).add(i)

    def candidates(e, taken):
        ids = sorted(set(by_name.get(e[0], ())) - taken)
        if len(ids) > 1:
            ids = [i for i in ids if born.get(i) == e[2]] or ids
        if not ids:  # one character off (槁直之 / 塙直之, 甘糟 / 甘粕): the only such person, or the one born that year
            ids = sorted({i for n, js in by_name.items() if len(n) == len(e[0])
                          and sum(x != y for x, y in zip(n, e[0])) == 1 for i in js} - taken)
            if len(ids) > 1:
                ids = [i for i in ids if born.get(i) == e[2]]
        if not ids and e[2]:  # another surname (結城秀康 / 松平秀康, 市 / 織田市): same given name and birth year
            ids = sorted({i for n, js in by_name.items() if n.endswith(e[0][-2:]) for i in js
                          if born.get(i) == e[2]} - taken)
        return ids

    out = {}
    for rest in (False, True):
        for p, e in enumerate(entries):
            if p in out.values():
                continue
            ids = candidates(e, set(out) if rest else set())
            if len(ids) == 1 and ids[0] not in out:
                out[ids[0]] = p
    return out, [e[0] for p, e in enumerate(entries) if p not in out.values()]


def _bios(game_dir):
    """(Chinese entries, Japanese entries, {person id: entry index}). The two files hold the same 716 entries in the
    same order (only 真田信幸 and 瀬名 differ in the years), so the Japanese names, which match the PK records, place
    the Chinese texts too."""
    zh = biographies(ls11.ls11_decode_parts(_read(os.path.join(game_dir, "..", "nobu7-win", "Message.nb7"))), "big5")
    ja = biographies(ls11.ls11_decode_parts(_read(os.path.join(game_dir, "message.nb7"))), "cp932")
    assert len(zh) == len(ja)
    names, born = _person_names(game_dir)
    return zh, ja, _bio_index(ja, names, born)[0]


def _person_names(game_dir):
    """{id: names in every scenario, Chinese and Japanese}, {id: birth year}"""
    names, born = {}, {}
    files = [(d, "cp932") for d in _scenarios(game_dir)] + [(_zh(game_dir, n), "big5") for n in ZH_SCENARIOS]
    for data, enc in files:
        for n, k in _records(data).items():
            if n <= PEOPLE:
                names.setdefault(n - 1, set()).add(_name(data, k, enc))
                born[n - 1] = _u16(data, k, 0x10)
    return names, born


def bios(game_dir):
    zh, _, index = _bios(game_dir)
    return {i: [("單段", zh[p][4])] for i, p in index.items()}


def bio_names(game_dir):
    zh = _zh(game_dir)
    return {n - 1: _name(zh, k, "big5") for n, k in _records(zh).items() if n <= PEOPLE}


def persons(game_dir):
    scenarios = _scenarios(game_dir)
    main, zh = scenarios[MAIN], _zh(game_dir)
    rec, zh_rec = _records(main), _records(zh)
    _, ja, index = _bios(game_dir)

    def person(n):  # n: person number 1-744 -> id or None
        return n - 1 if 1 <= n <= PEOPLE else None

    fathers = {n - 1: _u16(main, rec[n], 0x3E) for n in range(1, PEOPLE + 1)}
    rows = []
    for i in range(PEOPLE):
        k = rec[i + 1]
        u = lambda field: _u16(main, k, field)  # noqa: E731
        name, name_ja = _name(zh, zh_rec[i + 1], "big5"), _name(main, k, "cp932")
        row = {"id": i, "name": name}
        if name_ja != name:
            row["nameJa"] = name_ja
        uncertain, notes = ["debut", "hidden.寿命", "hidden.義理", "hidden.口調"], []
        bio = ja[index[i]] if i in index else None
        if bio and bio[1]:
            row["reading"] = bio[1]
        row["born"] = u(0x10)
        died = bio and bio[3]
        if died:
            row["died"] = died
            notes.append("歿年取自列伝的標頭（記錄裡沒有歿年）。")
        row["debut"] = u(0x12)
        row["stats"] = {"政治": u(0x16), "戦闘": u(0x18), "智謀": u(0x1A)}
        more = {"身分": RANKS[u(0x24)], "勲功": u(0x26), "性別": "女性" if u(0x54) == 1 else "男性"}
        row["more"] = more
        row["hidden"] = {"寿命": u(0x14), "義理": u(0x28), "相性": u(0x2A), "口調": u(0x4E)}
        row["aptitude"] = {a: GRADES[u(0x30 + 2 * j)] for j, a in enumerate(ARMS)}
        skills = {}
        domestic = [label for bit, label in DOMESTIC if u(0x44) & bit]
        battle = [label for bit, label in BATTLE if u(0x46) & bit]
        if domestic:
            skills["内政特技"] = domestic
        if battle:
            skills["戦闘特技"] = battle
            if "騎突" in battle:
                uncertain.append("skills.戦闘特技")
        if skills:
            row["skills"] = skills
        relations = {}
        father = person(u(0x3E))
        if father is not None:
            relations["father"] = [father]
        children = [j for j, f in fathers.items() if f and person(f) == i]
        if children:
            relations["children"] = children
        siblings = [j for j, f in fathers.items() if j != i and f and f == u(0x3E)]
        if siblings:
            relations["siblings"] = siblings
        spouse = person(u(0x3C))
        if spouse is not None:
            relations["spouse"] = [spouse]
        if u(0x2C) != 0xFF:
            relations["clan"] = u(0x2C)
        if relations:
            row["relations"] = relations
        if u(0x22) != 0xFFFF:
            row["game"] = {"職業": JOBS[u(0x22)]}
        row["scenarios"] = []
        for s, data in enumerate(scenarios):
            r = _records(data)[i + 1]
            status = _u16(data, r, 0x20)
            if status in ABSENT:
                continue
            sc = {"scenario": s + 1, "year": struct.unpack_from("<H", data)[0], "status": STATUS[status]}
            lord = i if status == 0 else person(_u16(data, r, 0x52))
            if lord is not None:
                sc["lord"] = lord
            if 1 <= _u16(data, r, 0x2E) <= 64:
                sc["location"] = _u16(data, r, 0x2E)
            if status not in (0, 3):
                sc["loyalty"] = _u16(data, r, 0x1E)
            row["scenarios"].append(sc)
        row["uncertain"] = uncertain
        notes.insert(0, "數值取自 PK 劇本 5（1582）；scenarios 是 PK 的 10 個劇本，待機、死亡的劇本不列。"
                        "寿命是 0–7 的等級，義理、相性是 0–15，口調 0–7 的名稱沒找到。")
        if bio is None:
            notes.append("沒有列伝。")
        row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def _siege_maps(game_dir, out_dir, types):
    """Write the 攻城圖 of the given types as Atkmap_NN.png; returns {type: file}."""
    data = _read(os.path.join(game_dir, "ATKMAP.NB7"))
    pal = ls11.ls11_decode_parts(_read(os.path.join(game_dir, "grppal.nb7")))[0]
    pal = b"".join(bytes((pal[3 * c + 1], pal[3 * c + 2], pal[3 * c])) for c in range(256))
    base = 4 + 16 * struct.unpack_from("<I", data, 0)[0]
    os.makedirs(out_dir, exist_ok=True)
    files = {}
    for t in sorted(types):
        offset, size, w, h = struct.unpack_from("<4I", data, 4 + 16 * t)
        im = Image.frombytes("P", (w, h), data[base + offset:base + offset + size])
        im.putpalette(pal)
        files[t] = f"Atkmap_{t:02d}.png"
        im.convert("RGB").save(os.path.join(out_dir, files[t]))
    return files


def places(game_dir, out_dir):
    scenarios = _scenarios(game_dir)
    zh = [_zh(game_dir, n) for n in ZH_SCENARIOS]
    main = scenarios[MAIN]
    types = {k: [struct.unpack_from("<H", d, CASTLES + 0x34 * k + ATKMAP_TYPE)[0] for d in scenarios]
             for k in range(1, 65)}
    files = _siege_maps(game_dir, out_dir, {t for ts in types.values() for t in ts})
    users = {}
    for k, ts in types.items():
        for t in set(ts):
            users.setdefault(t, []).append(k)
    rows = []
    for k in range(1, 65):
        name, name_ja = _castle_name(zh[MAIN], k, "big5"), _castle_name(main, k, "cp932")
        x, y = struct.unpack_from("<HH", main, CASTLES + 0x34 * k + 0x22)
        row = {"id": k, "name": name}
        if name_ja != name:
            row["nameJa"] = name_ja
        maps = []
        for t in sorted(set(types[k]), key=types[k].index):
            m = {"file": files[t], "role": "攻城"}
            shared = [x for x in users[t] if x != k]
            if shared:
                m["sharedWith"] = shared
            maps.append(m)
        row.update({"level": "城", "pos": {"x": x, "y": y, "grid": "square", "w": 176, "h": 151},
                    "battlemaps": maps, "uncertain": ["pos"]})
        others = []
        for s, data in enumerate(zh):
            n = _castle_name(data, k, "big5")
            if n != name:
                others.append(f"中文版劇本 {s + 1}：{n}")
        for s, data in enumerate(scenarios):
            n = _castle_name(data, k, "cp932")
            if n != name_ja:
                others.append(f"PK 劇本 {s + 1}：{n}")
        notes = "城號 1–64，名稱取劇本 5（1582）。這一代沒有令制國，也沒有城與城的相鄰表（部隊在大地圖上自由移動），" \
                "所以不給 province、adjacent。pos 是城記錄 +0x22、+0x24，在 Mapdata.nb7 的 176×151 格上，沒和畫面對過。"
        if others:
            notes += "其他劇本的名稱：" + "、".join(others) + "。"
        notes += "攻城圖照城的樣式（城記錄 +0x26）選 12 張 Atkmap 之一，同樣式的城共用一張，色盤是 grppal.nb7 第 0 組（看圖判斷）。" \
                 "野戰在大地圖上打，沒有獨立的野戰圖。"
        if len(set(types[k])) > 1:
            notes += "樣式隨劇本不同：" + "、".join(f"PK 劇本 {s + 1} 是 {files[t]}" for s, t in enumerate(types[k])
                                                if t != types[k][0]) + f"，其餘是 {files[types[k][0]]}。"
        row["notes"] = notes
        rows.append(row)
    return rows
