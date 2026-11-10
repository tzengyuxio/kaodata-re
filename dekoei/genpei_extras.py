"""源平合戦 (KOEI 1994, DOS/V): scenario tables, strategic map, pictures and text, written under --out
(notes/genpei.md). Ported from genpei-zh (tools/dump_data.py, dump_gfx.py, npk.py, message.py, exe_text.py) and
re-derived here; the formats are in notes/genpei.md.

- tables/: Sndata.gp, 4 scenarios x 41266 bytes (0x26-byte header + tables): generals 400 x 71, clans 16 x 20,
  places 39 x 76, regions 8 x 9, ranks 256 x 19, treasures 256 x 18; one CSV per table with a `scenario` column.
  Columns ending in `?` are guesses, `wXX`/`bXX` are undecoded u16/u8 fields named after their offset; references are
  `id:name`, -1 none. The unpacked Main.exe keeps a copy of the 1180 tables (compared, not written again).
- map/: the world map (Mainmap.gp, 20 NPK strips of 88 x 360 → 1696 x 360) in the 4 seasonal palettes, the 156
  strategic-map nodes and their edges from Main.exe DGROUP, the 40 battle-map height grids and object lists
  (Hchikei.gp), and nodes.png with every node drawn on the map at its cell centre (x + 12, y + 8).
- pictures/: every NPK016 chunk of the 11 NPK files and the RLE3 pictures of Kisetsu.gp, with pictures.csv. Main
  files use Mainpal set 0; Opendat/Enddat chunks use one of the file's prefix palettes, picked by eye where known and
  otherwise by a heuristic (marked in pictures.csv).
- text/: Message.gp (LS11, 5 blocks of u16-LE offset tables, 1305 messages) and the Shift-JIS strings of Main.exe
  (unpacked), Open.exe, End.exe. Half-width kana are shown as the game draws them: hiragana, katakana after ESC K.

    cd dekoei && ../.venv/bin/python genpei_extras.py --game-dir ../games/genpei-dos --out ../games/genpei-dos/extract
"""
import collections
import csv
import math
import os
import re
import struct
import unicodedata

import click
from PIL import Image, ImageDraw

import genpei
from ls11 import ls11_decode_parts

SCEN_SIZE = genpei.SCENARIO_SIZE
SCEN_HEADER = genpei.SCENARIO_HEADER
# tables inside a scenario block (after the header)
GENERALS, CLANS, PLACES, UNKNOWN32 = 0x0000, 0x6EF0, 0x7030, 0x7BA4
REGIONS, RANKS, TREASURES = 0x7BC4, 0x7C0C, 0x8F0C
N_GENERALS, N_CLANS, N_PLACES, N_REGIONS, N_RANKS, N_TREASURES = 400, 16, 39, 8, 256, 256

# Main.exe offsets are file offsets of the unpacked MZ (header 0x53D0 bytes), as in genpei-zh.
MAIN_HEADER = 0x53D0
MAIN_BLOCK = (0x4A570, 0x54690)  # copy of the 1180 tables
MAIN_REGIONS, MAIN_TREASURES, MAIN_RANKS = 0x7BD0, 0x7C20, 0x8E20  # their order differs from Sndata
MAIN_DGROUP = 0x56870
MINIMAP = 0x57044   # DGROUP 0x07D4: 39 x (u16 x, u16 y) on the 520 x 168 map of Mainstl.gp
EDGES = 0x58EF8     # DGROUP 0x2688: 156 x 4 x (u16 neighbour, u16 1), 156 = none
NODES = 0x598B8     # DGROUP 0x3048: 156 x 11 bytes
N_NODES = 156
# a node's (x, y) is the top-left corner of its 24 x 16 cell; the road dot (12 x 10 ellipse) and the castle are centred
# in the cell, so the map point is (x + 12, y + 8)
NODE_CX, NODE_CY = 12, 8

STATUS = {0: "御家人", 1: "棟梁", 2: "代官", 5: "在野", 6: "落武者?", 7: "死亡"}
CLAN_TYPE = {0: "源氏", 1: "平氏", 2: "藤原氏", 3: "豪族"}
TREASURE_KIND = ["名馬", "刀剣", "鎧", "兜", "鞍", "楽器", "歌集", "美術", "兵書", "唐物", "珍宝"]
NODE_TYPE = {0: "拠点", 1: "緑橙斑", 2: "橙", 3: "緑", 4: "赤緑斑", 5: "水色", 6: "海路"}
SKILLS = [(0x01, "音楽"), (0x02, "和歌"), (0x04, "奇略"), (0x08, "操船")]
TRAITS = [(0x01, "僧"), (0x02, "女"), (0x04, "公家"), (0x08, "一門?")]
ABILITIES = [(0x31, "武力"), (0x32, "勇名"), (0x33, "弓術"), (0x34, "知才"), (0x35, "優雅"), (0x36, "忠節"),
             (0x37, "菩提"), (0x38, "無常"), (0x39, "加護")]
SEASONS = ["spring", "summer", "autumn", "winter"]

NPK_FILES = ["Logo.gp", "Mainevt.gp", "Maincmd2.gp", "Mainitem.gp", "Mainstl.gp", "Mainmap.gp", "Hikback.gp",
             "Hkeshiki.gp", "Hkumi.gp", "Opendat.gp", "Enddat.gp"]
# prefix palettes confirmed by eye: Enddat 72-77 (ending scroll) use set 10, the only ink-to-paper ramp
KNOWN_PALETTES = {("Enddat.gp", i): 10 for i in range(72, 78)}


# ---------------------------------------------------------------- helpers

def sjis(b: bytes) -> str:
    return b.split(b"\0", 1)[0].decode("cp932", errors="replace")


def u16(b: bytes, o: int) -> int:
    v = struct.unpack_from("<H", b, o)[0]
    return -1 if v == 0xFFFF else v


def ref(i: int, names: list) -> str:
    return f"{i}:{names[i]}" if 0 <= i < len(names) else str(i)


def chain(head: int, nxt) -> list:
    out = []
    while head != -1 and head not in out:
        out.append(head)
        head = nxt(head)
    return out


def recs(block: bytes, off: int, size: int, n: int) -> list:
    return [block[off + i * size:off + (i + 1) * size] for i in range(n)]


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def unpacked_main(game_dir) -> bytes:
    """Main.exe as genpei-zh's unpacked MZ: the expanded load image behind a 0x53D0-byte header (zeros here), so
    the file offsets in notes/genpei.md and genpei-zh apply unchanged."""
    image = genpei.unpack_main_exe(genpei.read_game_file(game_dir, "Main.exe"))
    exe = bytes(MAIN_HEADER) + image
    assert exe[MAIN_BLOCK[0]:MAIN_BLOCK[0] + 2] == "源".encode("cp932"), "unexpected Main.exe"
    return exe


def to_image(px: bytes, w: int, h: int, palette) -> Image.Image:
    im = Image.new("P", (w, h))
    im.putpalette([c for rgb in palette for c in rgb])
    im.putdata(px)
    return im


# ---------------------------------------------------------------- NPK016

def npk_chunks(data: bytes) -> list:
    """NPK016 chunks are concatenated without an offset table; find them by the magic. Header (48 bytes): magic,
    u16 planes, u16 canvas w/h (640x400), u16 w, u16 h, 16 x u16 stock palette (unused by the game)."""
    offs = [m.start() for m in re.finditer(b"NPK016", data)] + [len(data)]
    out = []
    for i in range(len(offs) - 1):
        o = offs[i]
        _, _, _, w, h = struct.unpack_from("<5H", data, o + 6)
        out.append(dict(index=i, offset=o, size=offs[i + 1] - o, w=w, h=h, payload=data[o + 0x30:offs[i + 1]]))
    return out


def npk_unpack(src: bytes, line: int, count: int) -> tuple:
    """Flag byte (LSB first) per 8 units. 0: literal of 2 bytes → 4 pixels (b1 bit7 → bit 3, b1 bit3 → bit 2,
    b2 bit7 → bit 1, b2 bit3 → bit 0, then shift). 1: one byte b, copy ((b & 0x1F) + 1) x 4 pixels from
    (((b >> 5) & 3) + 1) x (line if b & 0x80 else 4) back. Returns (pixels, bytes used)."""
    dest = bytearray()
    pos, flag = 0, 0
    while len(dest) < count and pos < len(src):
        if not flag & 0xFF00:
            flag = 0xFF00 | src[pos]
            pos += 1
        if flag & 1:
            b = src[pos]
            pos += 1
            back = (((b >> 5) & 3) + 1) * (line if b & 0x80 else 4)
            for _ in range(((b & 0x1F) + 1) * 4):
                dest.append(dest[-back] if len(dest) >= back else 0)
        else:
            b1, b2 = src[pos], src[pos + 1]
            pos += 2
            for _ in range(4):
                dest.append(((b1 & 0x80) >> 4) | ((b1 & 0x08) >> 1) | ((b2 & 0x80) >> 6) | ((b2 & 0x08) >> 3))
                b1, b2 = (b1 << 1) & 0xFF, (b2 << 1) & 0xFF
        flag >>= 1
    return bytes(dest[:count]), pos


def palettes(data: bytes, n: int) -> list:
    return [genpei.load_mainpal(data, i) for i in range(n)]


def pick_palette(px: bytes, w: int, h: int, pals: list) -> int:
    """Heuristic from genpei-zh dump_gfx.py: keep the sets that light up the most pixels, then take the smoothest
    picture (lowest neighbour luminance difference relative to contrast). A guess."""
    cnt = collections.Counter(px)
    total = len(px)
    pairs = collections.Counter()
    for y in range(0, h, 2):
        r = px[y * w:(y + 1) * w]
        pairs.update(zip(r, r[1:]))
    npairs = sum(pairs.values()) or 1

    def cover(p):
        return sum(k for c, k in cnt.items() if c == 0 or p[c] != (0, 0, 0)) / total

    def rough(p):
        lum = [0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2] for c in p]
        mean = sum(lum[c] * k for c, k in cnt.items()) / total
        var = sum((lum[c] - mean) ** 2 * k for c, k in cnt.items()) / total
        if var < 1:
            return math.inf
        return sum(abs(lum[a] - lum[b]) * k for (a, b), k in pairs.items()) / npairs / math.sqrt(var)

    cv = [cover(p) for p in pals]
    best = max(cv)
    return min((i for i in range(len(pals)) if cv[i] >= best * 0.97), key=lambda i: rough(pals[i]))


# ---------------------------------------------------------------- tables

def scenario_tables(k: int, block: bytes, nodes: list, minimap: list) -> dict:
    G = recs(block, GENERALS, 71, N_GENERALS)
    C = recs(block, CLANS, 20, N_CLANS)
    P = recs(block, PLACES, 76, N_PLACES)
    RG = recs(block, REGIONS, 9, N_REGIONS)
    R = recs(block, RANKS, 19, N_RANKS)
    T = recs(block, TREASURES, 18, N_TREASURES)
    gname = [sjis(g[0:7]) + sjis(g[14:19]) for g in G]
    pname = [sjis(p[0:9]) for p in P]
    cname = [gname[u16(c, 0)] if u16(c, 0) >= 0 else "" for c in C]
    rgname = [sjis(r[0:6]) for r in RG]
    rname = [sjis(r[0:13]) for r in R]
    tname = [sjis(t[0:11]) for t in T]
    face_owner = {u16(g, 0x1A): i for i, g in enumerate(G) if u16(g, 0x1A) >= 0}
    rank_holder = {u16(g, 0x29): i for i, g in enumerate(G) if u16(g, 0x29) >= 0}
    t_owner = {t: i for i, g in enumerate(G) for t in chain(u16(g, 0x3A), lambda x: u16(T[x], 0x0B))}
    out = {}

    rows = []
    for i, g in enumerate(G):
        face, kin = u16(g, 0x1A), u16(g, 0x1C)
        face_src = ("" if face < 0 else f"kaodata:{face}" if face < 90
                    else f"montage{face >> 14}:h{face >> 11 & 7}/b{face >> 8 & 7}/e{face >> 4 & 15}/m{face & 15}")
        parent = face_owner.get(kin, -1) if 0 <= kin < 400 or kin >= 0x4000 else -1
        rows.append([
            k, i, gname[i], sjis(g[0:7]), sjis(g[7:14]), sjis(g[14:19]), sjis(g[19:26]),
            face, face_src, i // 2 % 5, kin, ref(parent, gname),
            g[0x1E], 1180 - g[0x1E] if g[0x1E] else "", ref(g[0x1F], pname),
            *("○" if g[0x20] & m else "×" for m, _ in SKILLS),
            *(1 if g[0x21] & m else 0 for m, _ in TRAITS), 1 if g[0x21] & 0x80 else 0,
            STATUS.get(g[0x27], g[0x27]), ref(u16(g, 0x3C), cname), ref(u16(g, 0x3E), pname),
            ref(u16(g, 0x25), gname), ref(u16(g, 0x29), rname),
            " ".join(ref(t, tname) for t in chain(u16(g, 0x3A), lambda x: u16(T[x], 0x0B))),
            ref(u16(g, 0x23), gname), u16(g, 0x2B), g[0x2D], g[0x2F],
            *(g[o] for o, _ in ABILITIES), g[0x42], u16(g, 0x40), g[0x43:0x47].hex(), g.hex()])
    out["generals"] = ([
        "scenario", "id", "name", "surname", "surname_kana", "given", "given_kana",
        "face", "face_src", "face_bg", "kin", "parent", "age1180", "born", "home?",
        *(n for _, n in SKILLS), *(n for _, n in TRAITS), "in_game_only",
        "status", "clan", "location", "lord?", "rank", "treasures", "next_in_place",
        "mobilize", "b2d", "troop_quality", *(n for _, n in ABILITIES), "体力", "w40", "b43_46", "raw"], rows)

    rows = []
    for i, c in enumerate(C):
        lead = u16(c, 0)
        rows.append([k, i, ref(lead, gname), CLAN_TYPE.get(u16(c, 2), u16(c, 2)),
                     *(u16(c, o) for o in (4, 6, 8, 10)), u16(c, 0x0C), u16(c, 0x0E), u16(c, 0x10), u16(c, 0x12),
                     sum(1 for p in P if u16(p, 0x28) == i),
                     sum(1 for g in G if u16(g, 0x3C) == i) if lead >= 0 else 0])
    out["clans"] = (["scenario", "id", "leader", "type", "rel_c0", "rel_c1", "rel_c2", "rel_c3", "color", "court?",
                     "government", "w12", "n_places", "n_generals"], rows)

    rows = []
    for i, p in enumerate(P):
        nid = u16(p, 0x4A)
        nd = nodes[nid]
        members = chain(u16(p, 0x20), lambda x: u16(G[x], 0x23))
        ronin = chain(u16(p, 0x24), lambda x: u16(G[x], 0x23))
        rows.append([
            k, i, pname[i], sjis(p[9:18]), ref(u16(p, 0x26), rgname), ref(u16(p, 0x28), cname),
            ref(members[0] if members else -1, gname), len(members), u16(p, 0x22), len(ronin),
            " ".join(pname[a] for a in (u16(p, 0x12 + 2 * j) for j in range(7)) if a >= 0),
            *(u16(p, o) for o in range(0x2A, 0x3E, 2)), *(u16(p, o) for o in range(0x3E, 0x46, 2)),
            f"{u16(p, 0x46) & 0xFFFF:#06x}", u16(p, 0x48), nid, u16(nd, 0), u16(nd, 2), nd[7], *minimap[i]])
    out["places"] = ([
        "scenario", "id", "name", "kana", "region", "clan", "governor", "n_members", "w22_head?", "n_ronin",
        "adjacent", "pop_max?", "population", "commerce?", "security?", "farm_max?", "farm?", "gold?", "food?",
        "soldiers", "soldier_quality", "w3e", "w40", "w42", "w44", "flags", "w48",
        "map_node", "map_x", "map_y", "battle_map?", "mini_x", "mini_y"], rows)

    out["regions"] = (["scenario", "id", "name", "b06", "w07"],
                      [[k, i, rgname[i], r[6], u16(r, 7)] for i, r in enumerate(RG)])
    out["ranks"] = (["scenario", "id", "name", "held", "holder", "mobilize", "military?", "civil?", "w11"],
                    [[k, i, rname[i], 1 if r[13] == 0x50 else 0, ref(rank_holder.get(i, -1), gname), r[14] * 100,
                      r[15], r[16], u16(r, 17)] for i, r in enumerate(R)])
    out["treasures"] = (["scenario", "id", "name", "kind", "value", "flags", "icon", "b11", "owner", "next"],
                        [[k, i, tname[i], TREASURE_KIND[t[13]] if t[13] < 11 else t[13], t[14], f"{t[15]:02x}",
                          t[16], t[17], ref(t_owner.get(i, -1), gname), u16(t, 0x0B)] for i, t in enumerate(T)])
    return out


def scenario_row(k: int, s: bytes, block: bytes) -> list:
    G = recs(block, GENERALS, 71, N_GENERALS)
    gname = [sjis(g[0:7]) + sjis(g[14:19]) for g in G]
    C = recs(block, CLANS, 20, N_CLANS)
    clans = [c for c in struct.unpack_from("<16h", s, 4) if c >= 0]
    return [k, u16(s, 0), s[2] + 1, s[3], " ".join(f"{c}:{gname[u16(C[c], 0)]}" for c in clans), u16(s, 0x24),
            block[UNKNOWN32:UNKNOWN32 + 32].hex()]


def tables(game_dir, out) -> dict:
    sn = genpei.read_game_file(game_dir, "Sndata.gp")
    assert len(sn) == 4 * SCEN_SIZE, len(sn)
    exe = unpacked_main(game_dir)
    scen = [sn[k * SCEN_SIZE:(k + 1) * SCEN_SIZE] for k in range(4)]
    blocks = [s[SCEN_HEADER:] for s in scen]
    nodes = recs(exe, NODES, 11, N_NODES)
    minimap = [struct.unpack_from("<HH", exe, MINIMAP + 4 * i) for i in range(N_PLACES)]
    merged = {}
    for k in range(4):
        for name, (cols, rows) in scenario_tables(k, blocks[k], nodes, minimap).items():
            merged.setdefault(name, (cols, []))[1].extend(rows)
    write_csv(os.path.join(out, "tables", "scenarios.csv"),
              ["scenario", "year", "month", "b03", "clans", "w24", "unknown32"],
              [scenario_row(k, scen[k], blocks[k]) for k in range(4)])
    counts = {}
    for name, (cols, rows) in merged.items():
        write_csv(os.path.join(out, "tables", f"{name}.csv"), cols, rows)
        counts[name] = len(rows)
    # Main.exe keeps a copy of the 1180 tables in another order: count the differing bytes
    m, b = exe[MAIN_BLOCK[0]:MAIN_BLOCK[1]], blocks[0]
    for label, mo, so, size in [("generals..places", 0, 0, UNKNOWN32), ("regions", MAIN_REGIONS, REGIONS, 72),
                                ("ranks", MAIN_RANKS, RANKS, N_RANKS * 19),
                                ("treasures", MAIN_TREASURES, TREASURES, N_TREASURES * 18)]:
        counts[f"Main.exe≠1180 {label}"] = sum(1 for i in range(size) if m[mo + i] != b[so + i])
    return counts


# ---------------------------------------------------------------- map

def world_map(game_dir) -> tuple:
    """5 blocks of 4 strips of 88 x 360; consecutive blocks overlap 16 px → 1696 x 360."""
    chunks = npk_chunks(genpei.read_game_file(game_dir, "Mainmap.gp"))
    w, h = chunks[0]["w"], chunks[0]["h"]
    W = w * len(chunks) - 16 * (len(chunks) // 4 - 1)
    canvas = bytearray(W * h)
    for i, c in enumerate(chunks):
        px, _ = npk_unpack(c["payload"], w, w * h)
        x0 = w * i - 16 * (i // 4)
        for y in range(h):
            canvas[y * W + x0:y * W + x0 + w] = px[y * w:(y + 1) * w]
    return bytes(canvas), W, h


def map_outputs(game_dir, out) -> dict:
    out = os.path.join(out, "map")
    os.makedirs(out, exist_ok=True)
    pal = genpei.read_game_file(game_dir, "Mainpal.pld")
    px, W, H = world_map(game_dir)
    for s, season in enumerate(SEASONS):
        to_image(px, W, H, genpei.load_mainpal(pal, s)).save(os.path.join(out, f"worldmap_{s}_{season}.png"))

    exe = unpacked_main(game_dir)
    sn = genpei.read_game_file(game_dir, "Sndata.gp")
    P0 = recs(sn[SCEN_HEADER:SCEN_SIZE], PLACES, 76, N_PLACES)
    base = {u16(p, 0x4A): (i, sjis(p[0:9])) for i, p in enumerate(P0)}
    nodes = recs(exe, NODES, 11, N_NODES)
    edges = [[struct.unpack_from("<H", exe, EDGES + 16 * n + 4 * j)[0] for j in range(4)] for n in range(N_NODES)]
    rows, colour = [], collections.defaultdict(collections.Counter)
    for n, r in enumerate(nodes):
        x, y = u16(r, 0), u16(r, 2)
        pid, pn = base.get(n, (-1, ""))
        c = px[(y + NODE_CY) * W + x + NODE_CX]
        colour[r[4]][c] += 1
        rows.append([n, x, y, x + NODE_CX, y + NODE_CY, r[4], NODE_TYPE.get(r[4], ""), r[7],
                     f"{pid}:{pn}" if pn else "",
                     " ".join(str(e) for e in edges[n] if e < N_NODES), c, r[5:7].hex(), r[8:11].hex()])
    write_csv(os.path.join(out, "nodes.csv"),
              ["node", "x", "y", "cx", "cy", "type", "kind", "battle_map?", "place", "neighbours", "map_colour", "b05",
               "b08"],
              rows)

    # checks: edges are symmetric, each place's node is a type-0 node, and the cell centre of every node of one type
    # has the same map colour (the castle's colour 8, the dot's fill colour)
    asym = sum(1 for n in range(N_NODES) for e in edges[n] if e < N_NODES and n not in edges[e])
    places_ok = sum(1 for n in base if nodes[n][4] == 0)
    n_type0 = sum(1 for r in nodes if r[4] == 0)

    im = to_image(px, W, H, genpei.load_mainpal(pal, 0)).convert("RGB")
    d = ImageDraw.Draw(im)
    for n in range(N_NODES):
        for e in edges[n]:
            if n < e < N_NODES:
                d.line([(u16(nodes[n], 0) + NODE_CX, u16(nodes[n], 2) + NODE_CY),
                        (u16(nodes[e], 0) + NODE_CX, u16(nodes[e], 2) + NODE_CY)], fill=(255, 255, 255))
    for n, r in enumerate(nodes):
        x, y = u16(r, 0) + NODE_CX, u16(r, 2) + NODE_CY
        d.rectangle([x - 2, y - 2, x + 2, y + 2], outline=(255, 0, 0) if r[4] == 0 else (0, 0, 0))
    im.save(os.path.join(out, "nodes.png"))

    hc = genpei.read_game_file(game_dir, "Hchikei.gp")
    used = collections.defaultdict(list)
    for n, r in enumerate(nodes):
        used[r[7]].append(str(n))
    write_csv(os.path.join(out, "battle_maps.csv"), ["map", "nodes", "max_height", "heights_14x14"],
              [[m, " ".join(used.get(m, [])), max(hc[m * 196:(m + 1) * 196]),
                " ".join("".join(str(v) for v in hc[m * 196 + y * 14:m * 196 + (y + 1) * 14]) for y in range(14))]
               for m in range(40)])
    obj = []
    for m in range(37):
        rec = hc[0x1EA0 + m * 60:0x1EA0 + (m + 1) * 60]
        for e in range(20):
            t, a, b = rec[e * 3:e * 3 + 3]
            if t == 0:
                break
            obj.append([m, e, t, a, b, a * 13 + b])
    write_csv(os.path.join(out, "battle_objects.csv"), ["map", "entry", "type", "a", "b", "cell"], obj)
    uniform = sum(c.most_common(1)[0][1] for c in colour.values())
    return {"map": f"{W}x{H}", "nodes": N_NODES, "asymmetric edges": asym,
            "nodes on their type's colour": f"{uniform}/{N_NODES}",
            "places on type-0 nodes": f"{places_ok}/{len(base)} (type-0 nodes {n_type0})",
            "dot colours": {t: dict(c) for t, c in sorted(colour.items())},
            "battle maps": 40, "battle objects": len(obj)}


# ---------------------------------------------------------------- pictures

def pictures(game_dir, out) -> dict:
    mainpal = genpei.load_mainpal(genpei.read_game_file(game_dir, "Mainpal.pld"))
    rows = []
    for name in NPK_FILES:
        data = genpei.read_game_file(game_dir, name)
        stem = name[:-3].lower()
        chunks = npk_chunks(data)
        pals, palname = [mainpal], "Mainpal[0]"
        if name in ("Opendat.gp", "Enddat.gp"):
            pals = palettes(data, chunks[0]["offset"] // 48)
        os.makedirs(os.path.join(out, "pictures", stem), exist_ok=True)
        for c in chunks:
            px, used = npk_unpack(c["payload"], c["w"], c["w"] * c["h"])
            trailer = c["payload"][used:]
            note = ""
            if len(pals) > 1:
                i = KNOWN_PALETTES.get((name, c["index"]))
                note = "palette by eye" if i is not None else "palette guessed"
                if i is None:
                    i = pick_palette(px, c["w"], c["h"], pals)
                palname = f"prefix[{i}]"
                pal = pals[i]
            else:
                pal = mainpal
            if len(trailer) == 8 and name == "Opendat.gp":
                note += "; next chunk at ({},{}) {}x{}".format(*struct.unpack("<4H", trailer))
            elif trailer.strip(b"\0"):
                note += f"; {len(trailer)} bytes after the payload"
            path = f"pictures/{stem}/{stem}_{c['index']:03d}.png"
            to_image(px, c["w"], c["h"], pal).save(os.path.join(out, path))
            rows.append([name, c["index"], f"{c['offset']:#x}", c["size"], c["w"], c["h"], palname, note.strip("; "),
                         path])
    # Kisetsu.gp: 11 RLE3 pictures of 160 x 128, back to back
    data = genpei.read_game_file(game_dir, "Kisetsu.gp")
    os.makedirs(os.path.join(out, "pictures", "kisetsu"), exist_ok=True)
    pos, i = 0, 0
    while pos < len(data):
        start = pos
        w, h, px, pos = genpei.read_rle3(data, pos)
        path = f"pictures/kisetsu/kisetsu_{i:03d}.png"
        to_image(px, w, h, mainpal).save(os.path.join(out, path))
        rows.append(["Kisetsu.gp", i, f"{start:#x}", pos - start, w, h, "Mainpal[0]", "RLE3", path])
        i += 1
    write_csv(os.path.join(out, "pictures", "pictures.csv"),
              ["file", "index", "offset", "size", "w", "h", "palette", "notes", "png"], rows)
    return collections.Counter(r[0] for r in rows)


# ---------------------------------------------------------------- text

def _kana(s: str, katakana: bool) -> str:
    s = unicodedata.normalize("NFKC", s)
    return s if katakana else "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def to_display(body: bytes) -> str:
    """Message bytes → text: \\n newline, {C6} colour, half-width kana as hiragana (katakana after ESC K, back to
    hiragana after ESC H), printf arguments as they are."""
    out, kata, i = [], False, 0
    while i < len(body):
        b = body[i]
        if b == 0x1B:
            op = chr(body[i + 1])
            if op == "K":
                kata = True
            elif op == "H":
                kata = False
            elif op == "C":
                out.append(f"{{C{chr(body[i + 2])}}}")
                i += 1
            else:
                out.append(f"{{{op}}}")
            i += 2
        elif b == 0x0A:
            out.append("\\n")
            i += 1
        elif 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC:
            out.append(body[i:i + 2].decode("cp932", errors="replace"))
            i += 2
        elif 0xA1 <= b <= 0xDF:
            j = i + 1 + (i + 1 < len(body) and body[i + 1] in (0xDE, 0xDF))
            out.append(_kana(body[i:j].decode("cp932"), kata))
            i = j
        else:
            out.append(chr(b))
            i += 1
    return "".join(out)


def messages(game_dir) -> list:
    """Message.gp: LS11 with a big-endian file table, 5 blocks; a block is u16-LE offsets (offset[0] = 2n) then the
    messages, each ending in 05 05 05 (one has none, one has a 00 after it)."""
    rows = []
    for blk, block in enumerate(ls11_decode_parts(genpei.read_game_file(game_dir, "Message.gp"))):
        n = struct.unpack_from("<H", block, 0)[0] // 2
        offs = list(struct.unpack_from(f"<{n}H", block, 0)) + [len(block)]
        for k in range(n):
            msg = block[offs[k]:offs[k + 1]]
            body = msg.rstrip(b"\x05\x00")
            rows.append([f"{blk}-{k:03d}", blk, k, len(body), msg[len(body):].hex(), to_display(body)])
    return rows


def _lead(b: int) -> bool:
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def _wide(t: str) -> bool:
    return len(t) == 1 and unicodedata.east_asian_width(t) in "WF"


JUNK_ASCII = set("^!\"#$&*+;<=>@[]_`|~")
PRINTF = re.compile(r"%[-0-9]*[dusxcBNWD][0-9]?")


def _scan(data: bytes, start: int, end: int):
    """NUL-terminated runs of Shift-JIS, half-width kana, ASCII, \\n, ESC C<d>, ESC K/H: (offset, raw, tokens)."""
    i = start
    while i < end:
        j, toks = i, []
        while j < end:
            b = data[j]
            if _lead(b) and 0x40 <= data[j + 1] <= 0xFC and data[j + 1] != 0x7F:
                try:
                    toks.append(data[j:j + 2].decode("cp932"))
                except UnicodeDecodeError:
                    break
                j += 2
            elif b == 0x1B and data[j + 1:j + 2] == b"C" and data[j + 2:j + 3].isdigit():
                toks.append("{C" + chr(data[j + 2]) + "}")
                j += 3
            elif b == 0x1B and data[j + 1] in b"KH":
                toks.append("{" + chr(data[j + 1]) + "}")
                j += 2
            elif 0xA1 <= b <= 0xDF:
                toks.append(data[j:j + 1].decode("cp932"))
                j += 1
            elif b == 0x0A:
                toks.append("\\n")
                j += 1
            elif 0x20 <= b <= 0x7E:
                toks.append(chr(b))
                j += 1
            else:
                break
        if j > i and data[j] == 0:
            yield i, data[i:j], toks
        i = j + 1 if j == i else j


def _anchor(toks: list):
    """First full-width character that is not glued to an ASCII letter, digit or odd symbol (binary junk)."""
    for i, t in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if _wide(t) and not (len(nxt) == 1 and nxt.isascii() and (nxt.isalnum() or nxt in JUNK_ASCII)):
            return i
    return None


def _plausible_prefix(toks: list, whole: bool) -> bool:
    s = re.sub(r"\{[A-Z]\d?\}", "", "".join(toks))
    if whole and re.fullmatch(r"[\uff66-\uff9f]{3,}\d*", s):
        return True                       # "ｱﾅﾛｸﾞ16色": a narrow-kana label
    if whole and re.match(r"[A-Za-z]%", s):
        s = s[1:]                         # "S%u": slot letter + argument
    rest = PRINTF.sub("", s)
    if re.fullmatch(r"\d+", rest):
        return False
    return re.fullmatch(r"[\s\d\-]*", rest) is not None


def _clean(toks: list):
    """Junk tokens to cut in front (pointer-table bytes before a string), None if it is not text."""
    k = _anchor(toks)
    if k is None:
        return None
    return next(c for c in range(k + 1) if _plausible_prefix(toks[c:k], whole=c == 0))


def _jis0208(raw: bytes) -> bool:
    i = 0
    while i < len(raw):
        if _lead(raw[i]):
            if raw[i] == 0x87 or raw[i] >= 0xED:
                return False
            i += 2
        else:
            i += 1
    return True


def _level2(text: str) -> bool:
    try:
        b = text.encode("cp932")
    except UnicodeEncodeError:
        return False
    return len(b) == 2 and (b[0] << 8 | b[1]) >= 0x989F


def _size(t: str) -> int:
    return len(t) - 1 if t.startswith("{") else 1 if t == "\\n" else len(t.encode("cp932"))


def exe_strings(data: bytes, start: int, end: int, ds: int) -> list:
    """UI strings (re-derived from genpei-zh tools/exe_text.py): runs with a real full-width character, junk cut in
    front, JIS X 0208 only, no stray single level-2 kanji or single characters outside DGROUP (ds)."""
    out = []
    for off, raw, toks in _scan(data, start, end):
        cut = _clean(toks) if any(_wide(t) for t in toks) else None
        if cut is None:
            continue
        skip = sum(_size(t) for t in toks[:cut])
        off, raw, toks = off + skip, raw[skip:], toks[cut:]
        text = "".join(toks)
        if not _jis0208(raw) or (len(toks) == 1 and (off < ds or _level2(text))):
            continue
        out.append((off, len(raw), "ui", text))
    return out


def table_strings(data: bytes, start: int, end: int) -> list:
    """Names (kind name) and half-width kana readings (kind reading) in the Main.exe scenario tables."""
    out = []
    for off, raw, toks in _scan(data, start, end):
        text = "".join(toks)
        if not any(_wide(t) for t in toks):
            if len(text) < 2 or not all(0xFF61 <= ord(c) <= 0xFF9F for c in text):
                continue
            kind = "reading"
        elif _clean(toks) != 0 or not _jis0208(raw) or (len(toks) == 1 and _level2(text)):
            continue
        else:
            kind = "name"
        out.append((off, len(raw), kind, text))
    return out


def dgroup(data: bytes) -> int:
    """File offset of DGROUP from the MS C startup (mov di, DGROUP at entry + 0xD)."""
    hdr = struct.unpack_from("<14H", data, 0)
    entry = hdr[4] * 16 + hdr[11] * 16 + hdr[10]
    assert data[entry:entry + 4] == bytes.fromhex("b430cd21") and data[entry + 13] == 0xBF
    return hdr[4] * 16 + struct.unpack_from("<H", data, entry + 14)[0] * 16


def text_outputs(game_dir, out) -> dict:
    counts = {}
    rows = messages(game_dir)
    write_csv(os.path.join(out, "text", "message.csv"), ["id", "block", "index", "bytes", "end", "text"], rows)
    counts["Message.gp"] = len(rows)
    exe = unpacked_main(game_dir)
    opn, end = genpei.read_game_file(game_dir, "Open.exe"), genpei.read_game_file(game_dir, "End.exe")
    for name, found in [("main", exe_strings(exe, MAIN_BLOCK[1], len(exe) - 1, MAIN_DGROUP)),
                        ("main_tables", table_strings(exe, *MAIN_BLOCK)),
                        ("open", exe_strings(opn, dgroup(opn), len(opn) - 1, dgroup(opn))),
                        ("end", exe_strings(end, dgroup(end), len(end) - 1, dgroup(end)))]:
        uniq = {}
        for off, size, kind, text in found:
            uniq.setdefault((kind, text), (size, []))[1].append(off)
        write_csv(os.path.join(out, "text", f"{name}.csv"), ["id", "offsets", "bytes", "kind", "text"],
                  [[i, " ".join(f"{o:#x}" for o in offs), size, kind, text]
                   for i, ((kind, text), (size, offs)) in enumerate(sorted(uniq.items(), key=lambda x: x[1][1][0]))])
        counts[name] = len(uniq)
    return counts


@click.command("genpei-extras")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="games/genpei-dos")
@click.option("--out", required=True, type=click.Path(), help="games/genpei-dos/extract")
@click.option("--no-pictures", is_flag=True, help="skip pictures/ (tables, map and text only)")
def genpei_extras(game_dir, out, no_pictures):
    """源平合戦 DOS/V: scenario tables, strategic map, pictures, messages and UI strings."""
    os.makedirs(out, exist_ok=True)
    for label, fn in [("tables", tables), ("map", map_outputs), ("text", text_outputs)] + \
            ([] if no_pictures else [("pictures", pictures)]):
        print(label, fn(game_dir, out))


if __name__ == "__main__":
    genpei_extras()
