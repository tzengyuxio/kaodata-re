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

import sango
import san7_extras
from kaodata_export import kana_to_hiragana
from common import u16
from places_export import PLACE_GAIJI, _bmp_png, _gaiji, _reading, area_interior

DATASET = "san7pk-win"
STATUS = ("君主", "太守", "軍師", "一般", "在野", "未発見", "待機", "死亡")
TRAITS = [("義理", 0, 4), ("野望", 4, 4), ("冷静", 8, 3), ("勇猛", 11, 3)]  # (name, first bit, bits) of +0x12
WAITING, DEAD, NO_FACTION = 6, 7, 255


def _zh_courtesy(zh_dir):
    """officer id -> 字 of the 繁中版 D_Sn001 (cp950)."""
    with open(os.path.join(zh_dir, "San7WPK.exe"), "rb") as f:
        exe = f.read()
    with open(os.path.join(zh_dir, sango.SAN7_SCENARIOS[0]), "rb") as f:
        d = sango.decode_san7_scenario(exe, f.read(), san7_extras.ZH_TABLES)
    out = {}
    for o in range(sango.SAN7_PERSONS, sango.SAN7_PERSONS + 620 * sango.SAN7_PERSON_SIZE, sango.SAN7_PERSON_SIZE):
        pid = u16(d, o)
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
            if u16(r, 0) != 0xFFFF:
                recs[k] = r
        out.append((u16(d, 0x1A), u16(d, 0x1C), recs))
    return out


def persons(game_dir):
    zh_dir = os.path.join(game_dir, "..", "steam", "628030-tchinese", "depot")
    zh = san7_extras.bio_names(zh_dir)
    courtesy = _zh_courtesy(zh_dir)
    ja = sango.load_san7_persons(game_dir)
    assert set(zh) == set(ja) == set(courtesy)
    by_id = {i: st for i, _, st in stats(game_dir)}
    scen = _scenarios(game_dir)
    # every scenario has the 520 officers in the same slots
    slot_of = {u16(r, 0): k for k, r in scen[0][2].items()}
    assert all({u16(r, 0): k for k, r in recs.items()} == slot_of for _, _, recs in scen)
    id_of = {k: i for i, k in slot_of.items()}
    first = scen[0][2]
    father = {i: id_of[u16(first[k], 0x10)] for i, k in slot_of.items() if u16(first[k], 0x10) in id_of}
    group = {i: u16(first[k], 0x10) for i, k in slot_of.items() if 1000 <= u16(first[k], 0x10) < 0xFFFF}
    # 血縁番号: the slot of the clan's head (everyone else points at himself); kept only when shared, as the head's id
    clan = {i: u16(first[k], 0xE) for i, k in slot_of.items()}
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
        row["born"] = u16(r, 4)
        row["stats"] = by_id[i]
        bits = u16(r, 0x12)
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
                e["debut"] = u16(p, 2)
            elif st != DEAD:
                e["location"] = p[0x4A]
                if p[0x49] != NO_FACTION:
                    e["lord"] = rulers[p[0x49]]
                    if st != 0:
                        e["loyalty"] = p[0x53]
            v = dict(zip(sango.SAN7_STATS, p[0x4B:0x4F]))
            if v != by_id[i]:
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


##############################################################################
# 三國志VII PK: D_Sn001.s7 (sango.decode_san7_scenario; the 12 scenarios agree) 54 cities from 0x160FC (0x60
# bytes: name +0 6, reading +6 8, six neighbours +0x0E, road kinds +0x14, battlefields +0x1A, slot for slot) and
# 192 battlefields from 0x157C8 (10 bytes: name 8, G_YMap number +8). The field battle of a city attacked from
# its j-th neighbour is its j-th battlefield (the PK 歷史戰役 D_Camp*.s7 agree). G_YMap00-29.s7 are 1944 x 768
# 8-bit BMPs. Place ids here: cities 0-53, battlefield b is 54 + b.
SAN7_CITIES, SAN7_FIELDS = 0x160FC, 0x157C8


SAN7_ROADS = {0: "陸路", 1: "山路", 2: "渡河", 3: "海路", 4: "棧道"}  # guessed from the maps
# 全國地圖 (the strategic screen's small map, 400 x 360): G_MMapCh.s7 picture 0 is the frame and land outside China
# (black inside), G_M5MMap.s7 picture 1 colours each city's area with colour city + 1 (55 the borders), picture 0
# the roads by kind with a legend. Each file has its own palette (P_<name>.s7). The game probably recolours the
# areas by ruler (not checked); the export keeps the file's colours.
SAN7_MAP_W, SAN7_MAP_H = 400, 360


def san7_world_maps(game_dir):
    """(areas, areas + roads, area index image)."""
    from PIL import Image
    bg = dict(san7_extras.pictures(game_dir, "G_MMapCh"))[0].load()
    mm = dict(san7_extras.pictures(game_dir, "G_M5MMap"))
    pb, pm = san7_extras.palette(game_dir, "G_MMapCh"), san7_extras.palette(game_dir, "G_M5MMap")
    area, road = mm[1].load(), mm[0].load()
    a, b = Image.new("RGB", (SAN7_MAP_W, SAN7_MAP_H)), Image.new("RGB", (SAN7_MAP_W, SAN7_MAP_H))
    pa, pr = a.load(), b.load()
    for y in range(SAN7_MAP_H):
        for x in range(SAN7_MAP_W):
            pa[x, y] = pm[area[x, y]] if area[x, y] else pb[bg[x, y]]
            pr[x, y] = pm[road[x, y]] if road[x, y] else pa[x, y]
    return a, b, mm[1]


def places(game_dir, out_dir):
    with open(os.path.join(game_dir, "San7WPK.exe"), "rb") as f:
        exe = f.read()
    with open(os.path.join(game_dir, "D_Sn001.s7"), "rb") as f:
        sc = sango.decode_san7_scenario(exe, f.read())
    gaiji = {**sango.SAN7_GAIJI, **PLACE_GAIJI}

    def s(b):
        return _gaiji(b.split(b"\0")[0].decode("cp932").strip(), gaiji)

    fields = [(s(sc[SAN7_FIELDS + 10 * b:][:8]), sc[SAN7_FIELDS + 10 * b + 8]) for b in range(192)]
    cities = [sc[SAN7_CITIES + 0x60 * k:][:0x60] for k in range(54)]
    for m in sorted({m for _, m in fields}):
        _bmp_png(os.path.join(game_dir, f"G_YMap{m:02d}.s7"), out_dir, f"G_YMap{m:02d}.png")
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    areas_map, roads_map, areas = san7_world_maps(game_dir)
    areas_map.save(os.path.join(out_dir, "world", "minimap.png"))
    roads_map.save(os.path.join(out_dir, "world", "minimap-roads.png"))
    pos = {k - 1: p for k, p in area_interior(areas, range(1, 55)).items()}
    users = {}
    for b, (_, m) in enumerate(fields):
        users.setdefault(m, []).append(54 + b)
    rows = []
    for k, r in enumerate(cities):
        maps, adjacent, odd = [], [], []  # odd: (slot, battlefield) with no neighbour
        for j in range(6):
            nb, road, b = r[0x0E + j], r[0x14 + j], r[0x1A + j]
            if nb != 0xFF:
                adjacent.append(nb)
                if b != 0xFF:
                    maps.append({"file": f"G_YMap{fields[b][1]:02d}.png", "role": "野戰", "from": nb})
            elif b != 0xFF:
                odd.append((j, b))
        notes = "野戰圖是「守方都市第 j 格鄰城來犯，用守方第 j 格的戰場」，PK 歷史戰役的攻守方對得上。" \
                "沒有各都市專用的攻城圖（攻城用共用素材拼成）。"
        for j, b in odd:
            notes += f"第 {j + 1} 格有戰場（{fields[b][0]}）但沒有鄰城，遊戲資料本身如此，沒有輸出。"
        notes += ("pos 是全國地圖 world/minimap.png（400×360）上這個都市的區域（G_M5MMap.s7 第 1 張的色號＝都市號＋1）"
                  "裡離邊界最遠的點；遊戲裡沒找到都市在這張圖上的座標。")
        rows.append({"id": k, "name": s(r[:6]), "reading": _reading(r[6:0x0E]), "level": "都市", "adjacent": adjacent,
                     "battlemaps": maps,
                     "pos": {"x": pos[k][0], "y": pos[k][1], "grid": "pixel", "w": SAN7_MAP_W, "h": SAN7_MAP_H},
                     "notes": notes})
    owners = {}
    for k, r in enumerate(cities):
        for j in range(6):
            if r[0x1A + j] != 0xFF and r[0x0E + j] != 0xFF:
                owners.setdefault(r[0x1A + j], []).append((k, r[0x0E + j], r[0x14 + j]))
    for b, (name, m) in enumerate(fields):
        row = {"id": 54 + b, "name": name, "level": "戰場", "battlemaps": [{"file": f"G_YMap{m:02d}.png", "role": "野戰"}],
               "uncertain": ["level"]}
        shared = [x for x in users[m] if x != 54 + b]
        if shared:
            row["battlemaps"][0]["sharedWith"] = shared
        uses = "、".join(f"{s(cities[a][:6])}←{s(cities[n][:6])}" for a, n, _ in owners.get(b, []))
        row["notes"] = ("戰場的號碼是遊戲的戰場號＋54。「戰場」是這邊的分類；名稱多是関或古戰場。"
                        + (f"用到的戰線（守方←攻方）：{uses}。" if uses else "沒有都市用到這個戰場。")
                        + (f"路的種類推定是{SAN7_ROADS.get(owners[b][0][2], '不明')}。" if b in owners else ""))
        rows.append(row)
    return rows


def stats(game_dir):
    # build_san7pk_win: id = officer id over all 12 scenarios; values differ between scenarios for a few officers,
    # so take the first scenario in SAN7_SCENARIOS order that has the officer
    first = {}
    for _, _, pid, name, *v in sango.load_san7_stats(game_dir):
        first.setdefault(pid, (name, v))
    names = sango.load_san7_persons(game_dir)
    return [(pid, names[pid][0], dict(zip(sango.SAN7_STATS, first[pid][1]))) for pid in sorted(names)]


def world_check(game_dir, rows):
    """Each city's pos lies inside its own area (at least 2 px from the edge), and two adjacent cities' areas touch
    (within 3 px, across the border line) unless the road between them is 海路 (kind 3)."""
    with open(os.path.join(game_dir, "San7WPK.exe"), "rb") as f:
        exe = f.read()
    with open(os.path.join(game_dir, "D_Sn001.s7"), "rb") as f:
        sc = sango.decode_san7_scenario(exe, f.read())
    px = san7_world_maps(game_dir)[2].load()
    bad, checked = [], 0
    for r in rows:
        if "pos" not in r:
            continue
        x, y = r["pos"]["x"], r["pos"]["y"]
        checked += 1
        if any(px[x + i, y + j] != r["id"] + 1 for i in range(-2, 3) for j in range(-2, 3)):
            bad.append(f"{r['id']}: pos not inside its area")
    touch = set()
    for y in range(SAN7_MAP_H):
        for x in range(SAN7_MAP_W):
            a = px[x, y]
            if 1 <= a <= 54:
                for i in range(-3, 4):
                    for j in range(-3, 4):
                        if 0 <= x + i < SAN7_MAP_W and 0 <= y + j < SAN7_MAP_H and 1 <= px[x + i, y + j] <= 54:
                            touch.add((a - 1, px[x + i, y + j] - 1))
    for k in range(54):
        r = sc[SAN7_CITIES + 0x60 * k:][:0x60]
        for j in range(6):
            nb, road = r[0x0E + j], r[0x14 + j]
            if nb != 0xFF and k < nb:
                checked += 1
                if ((k, nb) in touch) == (road == 3):
                    bad.append(f"{k}-{nb}: areas {'touch' if (k, nb) in touch else 'apart'}, road kind {road}")
    return checked, bad
