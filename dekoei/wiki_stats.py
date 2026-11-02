"""Main abilities of the 三國志 I-14 officers for koei-wiki, keyed by the kaodata person id: one JSONL line per
person, {"dataset", "id", "name", "stats": {ability: value}}. The abilities keep each game's own names (知力 / 智力,
カリスマ…); where they come from and what was checked is in notes/san-attributes.md「koei-wiki 匯出」. Every
stats_<dataset>(game_dir) rebuilds the builder's characters (kaodata_export.py) and returns [(id, name, stats)]."""
import json
import os
import struct

import click

import kaodata_export as K
import san1
import san2
import san3
import sango
from kaodata_export import SAN3_INPUTS, SAN8PK_WIN_ALIASES, SAN8PK_WIN_ROLES, san3_characters
from san_person import s2_format, s2_format_taiki


# 三國志 (I) PC-98: the scenario files are encoded and SAVEDATA is a game in progress (its values have moved: 劉備 知力
# 100), so the values are the DOS SINADATA.DAT scenario 1 ones: 255 x 32-byte records from 4326 (s1_format), 身体 知力
# 武力 カリスマ 運勢 at +13-17. Same person order and face codes as PC-98 (255/255), the same values in all 5 scenarios,
# and they match the PC-98 ruler screen (status-screens/san1-pc98-cap-01.png, 8 rulers)
SAN1_STATS = ["身体", "知力", "武力", "カリスマ", "運勢"]


def stats_san1_pc98(game_dir, dos_dir=None):
    dos_dir = dos_dir or os.path.join(game_dir, "..", "san1-dos")
    with open(os.path.join(dos_dir, "SINADATA.DAT"), "rb") as f:
        data = f.read()
    pc98 = san1.load_san1_pc98_persons(os.path.join(game_dir, "SAVEDATA"))
    dos = san1.load_san1_dos_persons(os.path.join(dos_dir, "SINADATA.DAT"))
    out = []
    for i, ((code, name), (dos_code, _)) in enumerate(zip(pc98, dos)):
        assert code == dos_code
        rec = data[san1.DOS_PERSONS + i * 32:san1.DOS_PERSONS + (i + 1) * 32]
        out.append((i + 1, name, dict(zip(SAN1_STATS, rec[13:18]))))
    return out


# 三國志II PC-98: SNDATA1-6.CIM (0x16 header, s2_format records, face at +26) then TAIKI.DAT (6-byte header,
# s2_format_taiki: 3 bytes in front); 知力 武力 魅力 at +4-6 (TAIKI +7-9). The builder (load_san2_jp_persons) keeps
# the first record of each face code, so the values are that record's
SAN2_STATS = ["知力", "武力", "魅力"]


def stats_san2_pc98(game_dir):
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


# 三國志III PC-98: SNDATA?B.CIM, 600 x 62-byte records (the first 43 bytes are the DOS s3_format), face code u16 at
# +2; 陸指 水指 武力 知力 政治 魅力 at +17-22 (武力 without items). The builder (san3_characters) takes scenarios 1-6
# in order and keeps each face code once (named by its most common spelling); the values are from the first record
# with that code and name. 0x82CB is both 車胄 (scenario 1) and 楊懐 (1-4): the character is 楊懐, with 楊懐's values.
# Only 劉表 changes between scenarios (水指 67 -> 25, 武力 70 -> 67 from scenario 2); scenario 1 is kept
SAN3_STATS = ["陸指", "水指", "武力", "知力", "政治", "魅力"]


def stats_san3_pc98(game_dir):
    first = {}
    for name in SAN3_INPUTS[2:]:
        with open(os.path.join(game_dir, name), "rb") as f:
            data = f.read()
        for i in range(600):
            rec = data[i * san3.PC98_RECORD_SIZE:(i + 1) * san3.PC98_RECORD_SIZE]
            if rec[0x31:0x37] != bytes(6):
                key = struct.unpack_from("<H", rec, 2)[0], san3.decode_pc98_name(rec[0x31:0x37])
                first.setdefault(key, dict(zip(SAN3_STATS, rec[17:23])))
    return [(i, name, first[code, name]) for i, (code, name) in enumerate(san3_characters(game_dir, True))]


def stats_san4pk_pc98(game_dir):
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


def stats_san5pk_pc98(game_dir):
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


def stats_san6pk_win(game_dir):
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


def stats_san7pk_win(game_dir):
    # build_san7pk_win: id = officer id over all 12 scenarios; values differ between scenarios for a few officers,
    # so take the first scenario in SAN7_SCENARIOS order that has the officer
    first = {}
    for _, _, pid, name, *v in sango.load_san7_stats(game_dir):
        first.setdefault(pid, (name, v))
    names = sango.load_san7_persons(game_dir)
    return [(pid, names[pid][0], dict(zip(sango.SAN7_STATS, first[pid][1]))) for pid in sorted(names)]


def stats_san8pk_win(game_dir):
    # build_san8pk_win: D_Sce.s8 persons without the role and alias records, id = record id
    rows = {r[0]: r for r in sango.load_san8_stats(os.path.join(game_dir, "D_Sce.s8"))}
    persons = sango.load_san8_persons(os.path.join(game_dir, "D_Sce.s8"))
    return [(p["id"], p["name"], dict(zip(sango.SAN8_STATS, rows[p["id"]][2:])))
            for p in persons if p["name"] not in SAN8PK_WIN_ROLES | SAN8PK_WIN_ALIASES]


def _pick(rows, labels, ids_names):
    """rows: (id, name, *values); keep the characters in ids_names (id -> name)."""
    by_id = {r[0]: dict(zip(labels, r[2:])) for r in rows}
    return [(i, n, by_id[i]) for i, n in sorted(ids_names.items()) if i in by_id]


def stats_san9pk_win(game_dir):
    # the builder's characters: persons minus roles 693-699, deduplicated by (name, face)
    chars, seen = {}, set()
    for p in sango.load_san9_persons(game_dir):
        if p["id"] in K.SAN9PK_WIN_ROLES or (p["name"], p["face"]) in seen:
            continue
        seen.add((p["name"], p["face"]))
        chars[p["id"]] = p["name"]
    rows = [r[1:] for r in sango.load_san9_stats(game_dir) if r[0] == sango.SAN9_SCENARIOS[0]]
    return _pick(rows, sango.SAN9_STATS, chars)


def stats_san10pk_win(game_dir):
    exe, sce = os.path.join(game_dir, "San10WPK.exe"), os.path.join(game_dir, "ScePK000.s10")
    chars = {p["id"]: p["name"] for p in sango.load_san10_persons(exe, sce)}
    return _pick(sango.load_san10_stats(exe, sce), sango.SAN10_STATS, chars)


def stats_san11pk_win(game_dir):
    sce = os.path.join(game_dir, K.SAN11PK_WIN_SCENARIOS[0])
    empty = {i for r in K.SAN11PK_WIN_EMPTY for i in r}
    chars = {p["id"]: p["name"] for p in sango.load_san11_persons(sce)
             if p["id"] not in empty and p["id"] not in K.SAN11PK_WIN_ROLES}
    return _pick(sango.load_san11_stats(sce), sango.SAN11_STATS, chars)


def stats_san12pk_win(game_dir):
    sce = os.path.join(game_dir, K.SAN12PK_WIN_SCENARIOS[0])
    chars = {p["id"]: p["name"] for p in sango.load_san12_persons(sce)
             if p["name"] and p["face"] not in K.SAN12PK_WIN_ROLE_FACES}
    return _pick(sango.load_san12_stats(sce), sango.SAN12_STATS, chars)


def stats_san13pk_win(game_dir):
    data = sango.load_san13_persons(game_dir)
    chars = {p: data["names"][p][0] for p in data["pictures"]
             if p not in K.SAN13PK_WIN_ROLES and data["names"][p][0]}
    return _pick(sango.load_san13_stats(game_dir), sango.SAN13_STATS, chars)


def stats_san14pk_win(game_dir):
    path_ja, path_tc = (os.path.join(game_dir, n) for n in K.SAN14PK_WIN_SCENARIOS)
    ja, tc = sango.load_san14_persons(path_ja), sango.load_san14_persons(path_tc, "TC")
    # names as the builder writes them: gaiji read off the other language's name
    gaiji = dict(K.SAN14PK_WIN_GAIJI)
    for a, b in zip(ja, tc):
        for f in ("surname", "given"):
            if len(a[f]) == len(b[f]):
                for x, y in zip(a[f], b[f]):
                    if 0xE000 <= ord(x) <= 0xF8FF and not 0xE000 <= ord(y) <= 0xF8FF:
                        gaiji.setdefault(("JP", x), y)
    chars = {a["id"]: "".join(gaiji.get(("JP", c), c) for c in a["surname"] + a["given"]) for a in ja}
    return _pick(sango.load_san14_stats(path_ja), sango.SAN14_STATS, chars)


DATASETS = {"san1-pc98": stats_san1_pc98, "san2-pc98": stats_san2_pc98, "san3-pc98": stats_san3_pc98,
            "san4pk-pc98": stats_san4pk_pc98, "san5pk-pc98": stats_san5pk_pc98, "san6pk-win": stats_san6pk_win,
            "san7pk-win": stats_san7pk_win, "san8pk-win": stats_san8pk_win, "san9pk-win": stats_san9pk_win,
            "san10pk-win": stats_san10pk_win, "san11pk-win": stats_san11pk_win, "san12pk-win": stats_san12pk_win,
            "san13pk-win": stats_san13pk_win, "san14pk-win": stats_san14pk_win}


@click.command()
@click.argument("dataset", type=click.Choice(list(DATASETS)))
@click.option("--game-dir", "game_dir", required=True)
@click.option("--out", "out", required=True, help="JSONL 檔")
def stats_export(dataset, game_dir, out):
    """匯出三國志 I–14 的武將能力值（JSONL，給 koei-wiki）"""
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    rows = DATASETS[dataset](game_dir)
    with open(out, "w", encoding="utf-8") as f:
        for i, name, stats in rows:
            f.write(json.dumps({"dataset": dataset, "id": i, "name": name, "stats": stats}, ensure_ascii=False) + "\n")
    print(f"{out}: {len(rows)} persons")
