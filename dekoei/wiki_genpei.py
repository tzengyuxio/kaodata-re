"""源平合戦 (genpei-pc98) for koei-wiki: persons (koei-persons/1), places (koei-places/1) and the two pictures of every
person. Everything is read from the PC-98 files: SNDATA.GP is byte for byte the DOS Sndata.gp except 393's name
(宗商人 / DOS 宋商人, 2 bytes x 4 scenarios), and the map tables in MAIN.EXE are the same bytes as in the DOS
Main.exe. id is the kaodata genpei-pc98 id (the general's number). Field sources: notes/genpei.md「Sndata.gp：劇本」
「戰略地圖與合戰地圖」「koei-wiki 匯出」.

    ../.venv/bin/python wiki_genpei.py --game-dir ../games/genpei-pc98 --out ../export/koei-wiki/portraits
writes portraits/genpei-pc98/{bust,window}/<id>.png (128x160 transparent, and the game's 64x80 face window)."""
import os
import struct

import click
from PIL import Image

import genpei
import genpei_extras as gx
import kaodata_export as ke

DATASET = "genpei-pc98"
SCENARIO_YEARS = [(1180, 10), (1183, 7), (1184, 10), (1185, 10)]
# PC-98 MAIN.EXE (not packed): the node and edge tables, the same bytes as the DOS Main.exe's gx.NODES / gx.EDGES
NODES, EDGES = 0x5B028, 0x5A668
STATUS = {0: "御家人", 1: "棟梁", 2: "代官", 5: "在野", 6: "落武者", 7: "死亡"}
PLACE_VALUES = [(0x2C, "人口"), (0x2E, "商業"), (0x30, "治安"), (0x34, "農業"), (0x36, "財貨"), (0x38, "兵糧"),
                (0x3A, "雑兵"), (0x3C, "雑兵質")]
PLACE_GUESSED = ["商業", "治安", "農業", "財貨", "兵糧"]
WORLD_W, WORLD_H = 1696, 360


def _blocks(game_dir):
    sn = genpei.read_game_file(game_dir, "Sndata.gp")
    return [sn[k * gx.SCEN_SIZE + gx.SCEN_HEADER:(k + 1) * gx.SCEN_SIZE] for k in range(4)]


def _name(g):
    return gx.sjis(g[0:7]).rstrip(" ") + gx.sjis(g[14:19]).rstrip(" ")


def persons(game_dir):
    blocks = _blocks(game_dir)
    G = [gx.recs(b, gx.GENERALS, 71, gx.N_GENERALS) for b in blocks]
    C = [gx.recs(b, gx.CLANS, 20, gx.N_CLANS) for b in blocks]
    R = [gx.recs(b, gx.RANKS, 19, gx.N_RANKS) for b in blocks]
    T = [gx.recs(b, gx.TREASURES, 18, gx.N_TREASURES) for b in blocks]
    rank = [[gx.sjis(r[0:13]) for r in rs] for rs in R]
    treasure = [[gx.sjis(t[0:11]) for t in ts] for ts in T]

    def items(k, g):
        return [treasure[k][t] for t in gx.chain(gx.u16(g, 0x3A), lambda x: gx.u16(T[k][x], 0x0B))]

    # +0x1C: brothers share the code; a code equal to another general's face code makes him the father
    G0 = G[0]
    by_face = {gx.u16(g, 0x1A): i for i, g in enumerate(G0)}
    kin = [gx.u16(g, 0x1C) for g in G0]
    father = {i: by_face[k] for i, k in enumerate(kin) if k in by_face}
    rows = []
    for i, g in enumerate(G0):
        surname, given = gx.sjis(g[0:7]).rstrip(" "), gx.sjis(g[14:19]).rstrip(" ")
        sk, gk = (ke.kana_to_hiragana(gx.sjis(g[o:o + 7]).rstrip(" ")) for o in (7, 19))
        npc = i >= 390
        # 390-399 keep the whole name in the surname field, the reading running on into the given name's field
        row = {"id": i, "name": surname + given, "reading": sk + gk if npc else f"{sk} {gk}".strip()}
        if surname and sk and not npc:
            row.update({"familyName": surname, "familyReading": sk})
        if not npc:
            row["born"] = 1180 - g[0x1E]
        if not npc:
            row["stats"] = {**{n: g[o] for o, n in gx.ABILITIES}, "体力": g[0x42]}
            more = {"年齢": g[0x1E], "兵質": g[0x2F], "動員力": gx.u16(g, 0x2B)}
            if gx.u16(g, 0x29) >= 0:
                more["官位"] = rank[0][gx.u16(g, 0x29)]
            row["more"] = more
        sk_list = [n for m, n in gx.SKILLS if g[0x20] & m]
        if sk_list:
            row["skills"] = {"特技": sk_list}
        rel = {}
        if i in father:
            rel["father"] = [father[i]]
        children = [j for j, f in father.items() if f == i]
        if children:
            rel["children"] = children
        sibs = [j for j in range(len(G0)) if j != i and kin[i] >= 0 and kin[j] == kin[i]]
        if sibs:
            rel["siblings"] = sibs
        if rel:
            row["relations"] = rel
        if not npc:
            scen = []
            for k, (year, month) in enumerate(SCENARIO_YEARS):
                gk_ = G[k][i]
                s = {"scenario": k + 1, "year": year, "month": month, "status": STATUS[gk_[0x27]]}
                if gk_[0x27] != 7:
                    clan = gx.u16(gk_, 0x3C)
                    if clan >= 0:
                        s["lord"] = gx.u16(C[k][clan], 0)
                    s["location"] = gx.u16(gk_, 0x3E)
                    if gx.u16(gk_, 0x29) >= 0:
                        s["rank"] = rank[k][gx.u16(gk_, 0x29)]
                    its = items(k, gk_)
                    if its:
                        s["items"] = its
                    s["stats"] = {**{n: gk_[o] for o, n in gx.ABILITIES}, "体力": gk_[0x42]}
                scen.append(s)
            row["scenarios"] = scen
        game = {} if npc else {n: bool(g[0x21] & m) for m, n in gx.TRAITS[:3]}
        game["組合頭像"] = gx.u16(g, 0x1A) >= 0x4000
        its = items(0, g)
        if its:
            game["所持名物"] = its
        row["game"] = game
        uncertain = []
        if any(s.get("status") == "落武者" for s in row.get("scenarios", [])):
            uncertain.append("scenarios.status")
        if uncertain:
            row["uncertain"] = uncertain
        notes = []
        if npc:
            notes.append("非武將：四個劇本的身分碼都是 7，年齡、能力、旗標都是 0，只交名字、讀音與頭像，不列 stats、scenarios")
        if row["name"] == "宗商人":
            notes.append("PC-98 版寫「宗商人」，DOS 版是「宋商人」（宋的商人），照錄")
        if not npc:
            notes.append("stats 是 1180 年劇本的值（不含名物加成），能力隨劇本不同，各劇本的值在 scenarios[].stats；"
                         "born 是 1180 減 1180 年劇本的年齡；身分「死亡」的劇本不列所屬與所在")
        if any(G[k][i][0x21] & 7 != g[0x21] & 7 for k in range(4)):
            notes.append("game 的僧／女／公家是 1180 年劇本的值，之後的劇本改變了（如成為御家人後不再是公家）")
        if "relations" in row:
            notes.append("relations 由血緣碼推出：兄弟同碼，碼等於另一人的頭像碼則那人是父親")
        row["notes"] = "；".join(notes)
        rows.append(row)
    return rows


def _map(game_dir):
    exe = genpei.read_game_file(game_dir, "Main.exe")
    nodes = gx.recs(exe, NODES, 11, gx.N_NODES)
    edges = [[e for e in struct.unpack_from("<8H", exe, EDGES + 16 * n)[0::2] if e < gx.N_NODES]
             for n in range(gx.N_NODES)]
    return nodes, edges


def places(game_dir, out_dir):
    blocks = _blocks(game_dir)
    P = [gx.recs(b, gx.PLACES, 76, gx.N_PLACES) for b in blocks]
    C = [gx.recs(b, gx.CLANS, 20, gx.N_CLANS) for b in blocks]
    regions = [gx.sjis(r[0:6]) for r in gx.recs(blocks[0], gx.REGIONS, 9, gx.N_REGIONS)]
    nodes, edges = _map(game_dir)
    node_of = {i: gx.u16(p, 0x4A) for i, p in enumerate(P[0])}
    assert all(gx.u16(P[k][i], 0x4A) == node_of[i] for k in range(4) for i in range(gx.N_PLACES))
    rows = []
    for i, p in enumerate(P[0]):
        adjacent = [a for a in (gx.u16(p, 0x12 + 2 * j) for j in range(7)) if a >= 0]
        assert all(gx.u16(P[k][i], 0x12 + 2 * j) == gx.u16(p, 0x12 + 2 * j) for k in range(4) for j in range(7))
        n = nodes[node_of[i]]
        row = {"id": i, "name": gx.sjis(p[0:9]).rstrip(" "),
               "reading": ke.kana_to_hiragana(gx.sjis(p[9:18]).rstrip(" ")), "level": "拠点",
               "region": regions[gx.u16(p, 0x26)], "adjacent": adjacent,
               "pos": {"x": gx.u16(n, 0) + gx.NODE_CX, "y": gx.u16(n, 2) + gx.NODE_CY, "grid": "pixel",
                       "w": WORLD_W, "h": WORLD_H}}
        scen = []
        for k, (year, month) in enumerate(SCENARIO_YEARS):
            pk = P[k][i]
            s = {"scenario": k + 1, "year": year, "month": month}
            clan = gx.u16(pk, 0x28)
            if clan >= 0 and gx.u16(C[k][clan], 0) >= 0:
                s["lord"] = gx.u16(C[k][clan], 0)
            s.update({n: gx.u16(pk, o) for o, n in PLACE_VALUES})
            scen.append(s)
        row["scenarios"] = scen
        row["uncertain"] = [f"scenarios.{n}" for n in PLACE_GUESSED]
        row["notes"] = ("adjacent 是據點表的鄰接欄（+0x12，全部雙向，四個劇本相同）；沿戰略地圖的道路、海路節點展開的結果和它不同"
                        "（海路連成一片，展開後一個據點可到 15 個），所以不用展開的；"
                        "pos 是戰略地圖節點格的中心（節點座標加 (12, 8)），對應 games/genpei-dos/extract/map/ 的四季大地圖；"
                        "scenarios 的 lord 是所屬勢力的棟梁，空白地沒有 lord")
        rows.append(row)
    return rows


def _rgba(img, colors):
    w, h, px = img
    im = Image.frombytes("RGBA", (w, h), ke.to_rgba(img, colors))
    return im


@click.command()
@click.option("--game-dir", "game_dir", required=True, help="games/genpei-pc98")
@click.option("--out", "out", required=True, help="export/koei-wiki/portraits")
def portraits(game_dir, out):
    """Every person's 128x160 picture (transparent) and the 64x80 window the game shows (over its background).
    The window is the kaodata display (checksums.json ch:<id>), so it is checked against the builder's hashes."""
    import hashlib
    meta, blobs = ke.build_genpei(game_dir, pc98=True)
    colors = meta["palettes"][0]["colors"]
    sums = ke.checksums(meta, blobs)["entries"]
    dirs = {d: os.path.join(out, DATASET, d) for d in ("bust", "window")}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    checked, bad = 0, []
    for ch in meta["characters"]:
        face = ch["face"]
        if "portrait" in face:
            p = meta["portraits"][face["portrait"]]
            bust = ke.get_image(meta, blobs, p["img"])
            window = ke.portrait_display(meta, blobs, face["portrait"], face["bg"])
        else:
            variant = meta["composite"]["variants"][face["variant"]]
            bare = {**meta, "composite": {**meta["composite"], "variants": [{**variant, "window": None}]}}
            bare["composite"]["variants"][0].pop("window")
            bust = ke.compose_display(bare, blobs, {**face, "variant": 0, "bg": None})
            window = ke.compose_display(meta, blobs, face)
        assert bust[:2] == (128, 160) and window[:2] == (64, 80)
        checked += 1
        if hashlib.sha256(ke.to_rgba(window, colors)).hexdigest() != sums[f"ch:{ch['id']}"]:
            bad.append(ch["id"])
        _rgba(bust, colors).save(os.path.join(dirs["bust"], f"{ch['id']}.png"))
        _rgba(window, colors).save(os.path.join(dirs["window"], f"{ch['id']}.png"))
    print(f"{DATASET}: {checked} persons, 2 pictures each; window = kaodata ch:<id>: {checked - len(bad)} same, "
          f"{len(bad)} different {bad[:10]}")


if __name__ == "__main__":
    portraits()
