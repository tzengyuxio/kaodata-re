"""三國志VII with パワーアップキット (san7pk-win) for koei-wiki: persons (koei-persons/1). id is the kaodata san7pk-win id,
the officer id (= face number) of the D_Sn???.s7 person table. name is the 繁中版's (Steam depot 628032, the same
scenario files under another cipher table, san7_extras.bio_names), nameJa the Japanese one where it differs; reading
and the rest come from the Japanese scenarios. Layout and evidence: notes/san7.md「koei-wiki 匯出」,
notes/san-attributes.md「三國志VII」.

Scenario header (decoded): +0x1A u16 scenario number (1-7, 101-105), +0x1C u16 start year. Person record (0x78 bytes
from sango.SAN7_PERSONS): +0 officer id, +2 u16 登場年, +4 u16 生年, +0xE u16 血縁番号 (a slot), +0x10 u16 親武将 (the
father's slot; 1000+ a group of brothers with no father in the game, 0xFFFF none), +0x12 u16 bits 義理 0-3, 野望 4-7,
冷静 8-10, 勇猛 11-13, +0x36 字, +0x48 身分 (San7WPK.exe pointer table 0x40FFA0: 君主 太守 軍師 一般 在野 未発見 待機
死亡), +0x49 faction (255 none), +0x4A city (= places id), +0x4B 武力 知力 政治 魅力, +0x53 忠誠, +0x59 相性."""
import os
import struct

import sango
import san7_extras
import wiki_stats
from kaodata_export import kana_to_hiragana

DATASET = "san7pk-win"
STATUS = ("君主", "太守", "軍師", "一般", "在野", "未発見", "待機", "死亡")
TRAITS = [("義理", 0, 4), ("野望", 4, 4), ("冷静", 8, 3), ("勇猛", 11, 3)]  # (name, first bit, bits) of +0x12
WAITING, DEAD, NO_FACTION = 6, 7, 255


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _zh_courtesy(zh_dir):
    """officer id -> 字 of the 繁中版 D_Sn001 (cp950)."""
    with open(os.path.join(zh_dir, "San7WPK.exe"), "rb") as f:
        exe = f.read()
    with open(os.path.join(zh_dir, sango.SAN7_SCENARIOS[0]), "rb") as f:
        d = sango.decode_san7_scenario(exe, f.read(), san7_extras.ZH_TABLES)
    out = {}
    for o in range(sango.SAN7_PERSONS, sango.SAN7_PERSONS + 620 * sango.SAN7_PERSON_SIZE, sango.SAN7_PERSON_SIZE):
        pid = _u16(d, o)
        if pid != 0xFFFF:
            out[pid] = d[o + 0x36:o + 0x3C].split(b"\0")[0].decode("cp950").strip()
    return out


def _scenarios(game_dir):
    """[(number, year, {slot: record})] in SAN7_SCENARIOS order."""
    with open(os.path.join(game_dir, "San7WPK.exe"), "rb") as f:
        exe = f.read()
    out = []
    for name in sango.SAN7_SCENARIOS:
        with open(os.path.join(game_dir, name), "rb") as f:
            d = sango.decode_san7_scenario(exe, f.read())
        recs = {}
        for k in range(620):
            r = d[sango.SAN7_PERSONS + k * sango.SAN7_PERSON_SIZE:][:sango.SAN7_PERSON_SIZE]
            if _u16(r, 0) != 0xFFFF:
                recs[k] = r
        out.append((_u16(d, 0x1A), _u16(d, 0x1C), recs))
    return out


def persons(game_dir):
    zh_dir = os.path.join(game_dir, "..", "steam", "628030-tchinese", "depot")
    zh = san7_extras.bio_names(zh_dir)
    courtesy = _zh_courtesy(zh_dir)
    ja = sango.load_san7_persons(game_dir)
    assert set(zh) == set(ja) == set(courtesy)
    stats = {i: st for i, _, st in wiki_stats.stats_san7pk_win(game_dir)}
    scen = _scenarios(game_dir)
    # every scenario has the 520 officers in the same slots
    slot_of = {_u16(r, 0): k for k, r in scen[0][2].items()}
    assert all({_u16(r, 0): k for k, r in recs.items()} == slot_of for _, _, recs in scen)
    id_of = {k: i for i, k in slot_of.items()}
    first = scen[0][2]
    father = {i: id_of[_u16(first[k], 0x10)] for i, k in slot_of.items() if _u16(first[k], 0x10) in id_of}
    group = {i: _u16(first[k], 0x10) for i, k in slot_of.items() if 1000 <= _u16(first[k], 0x10) < 0xFFFF}
    # 血縁番号: the slot of the clan's head (everyone else points at himself); kept only when shared, as the head's id
    clan = {i: _u16(first[k], 0xE) for i, k in slot_of.items()}
    shared = {c for c in clan.values() if list(clan.values()).count(c) > 1}
    children = {}
    for c, p in father.items():
        children.setdefault(p, []).append(c)

    rows = []
    for i in sorted(ja):
        k = slot_of[i]
        r = first[k]
        name_ja, kana = ja[i]
        row = {"id": i, "name": zh[i]}
        if name_ja != zh[i]:
            row["nameJa"] = name_ja
        if courtesy[i]:
            row["courtesy"] = courtesy[i]
        row["reading"] = kana_to_hiragana(kana)
        row["born"] = _u16(r, 4)
        row["stats"] = stats[i]
        bits = _u16(r, 0x12)
        row["hidden"] = {"相性": r[0x59], **{n: bits >> b & (1 << w) - 1 for n, b, w in TRAITS}}
        rel = {}
        if i in father:
            rel["father"] = [father[i]]
        if i in children:
            rel["children"] = sorted(children[i])
        sib = sorted(j for j in ja if j != i and (
            (i in father and father.get(j) == father[i]) or (i in group and group.get(j) == group[i])))
        if sib:
            rel["siblings"] = sib
        if clan[i] in shared and clan[i] in id_of:
            rel["clan"] = id_of[clan[i]]
        if rel:
            row["relations"] = rel

        out = []
        for number, year, recs in scen:
            p = recs[k]
            rulers = {q[0x49]: id_of[s] for s, q in recs.items() if q[0x48] == 0}
            st = p[0x48]
            e = {"scenario": number, "year": year, "status": STATUS[st]}
            if st == WAITING:
                e["debut"] = _u16(p, 2)
            elif st != DEAD:
                e["location"] = p[0x4A]
                if p[0x49] != NO_FACTION:
                    e["lord"] = rulers[p[0x49]]
                    if st != 0:
                        e["loyalty"] = p[0x53]
            v = dict(zip(sango.SAN7_STATS, p[0x4B:0x4F]))
            if v != stats[i]:
                e["stats"] = v
            out.append(e)
        row["scenarios"] = out
        row["uncertain"] = [f"hidden.{n}" for n, _, _ in TRAITS] + \
            (["relations.clan"] if "clan" in rel else []) + \
            (["relations.siblings"] if i in group else []) + \
            (["scenarios.loyalty"] if any("loyalty" in e for e in out) else [])
        notes = []
        if any(e["status"] == "待機" and e["debut"] <= e["year"] for e in out):
            notes.append("有劇本是「待機」但登場年不晚於劇本年，照遊戲資料寫。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows
