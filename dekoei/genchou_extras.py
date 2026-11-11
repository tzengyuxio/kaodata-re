"""蒼き狼と白き牝鹿・元朝秘史 PC-98 (genchou-pc98): countries, factions and people of the 4 scenarios, and the
main maps. Chinese names come from the DOS version (genchou-dos, same file layout). Formats and evidence:
notes/genchou.md「國與大地圖」「人物欄位」.

Addresses are PC-98 MAIN.EXE: MZ header 0x4200, DGROUP at image 0x37B20 (file 0x3BD20). GENDATA<n>.DAT is read
whole to DS:0x42, so a GENDATA offset + 0x42 is its DS address.
"""
import csv
import os
import struct
import unicodedata

import click
from PIL import Image

from koei_games import koei_tw_name
from koei_stats import GENCHOU_GRADES
from san3 import world_band

DGROUP = 0x3BD20  # MAIN.EXE file offset of DS:0
# GENDATA (PC-98 / DOS): (offset, record size, records)
MEN, WOMEN = (2, 27, 109), (0x1A26, 23, 33)
COUNTRIES, FACTIONS = (0xB82, 49, 33), (0x11D4, 22, 33)  # DS:0x0BC4, DS:0x1216
STAGE, SEASON, N_COUNTRIES, N_FACTIONS = 0x1F58, 0x1F59, 0x1F5B, 0x1F5C  # DS:0x1F9A, 0x1F9B, 0x1F9D, 0x1F9E
PLACEHOLDERS = ("モンゴル統一者", "蒙古統一者")  # scenario 4: the player's own Mongol leader
# ZNAME.DAT: 17-byte names; MAIN.EXE 0x9E70 reads the Mongolian regions from 0, the world from 0x231 (33 * 17)
# when [stage] != 0.
ZNAME_WORLD = 33
SEASONS = ["spring", "summer", "autumn", "winter"]  # DS:0x41BE 春 夏 秋 冬, indexed by [0x1F9B]
# DS tables of near string pointers
CULTURES, CLIMATES, PRODUCTS, UNITS = (0x85F0, 8), (0x5C2E, 8), (0x8366, 12), (0xC098, 16)
RANKS = (0x5C0E, 4)  # 身分, +24 bits 0-1 (MAIN.EXE 0x1ACC3): 将軍 政治顧問 領主 国王
# MAPDATA.DAT: 640 x 200 bands in san3.world_band's format, two per screen (MAIN.EXE 0x569E, 0x71C3 read them).
MAPS = {"mongolia": (0x0, 0x3F1D), "world": (0x8CC7, 0xFDB9), "screen": (0x15B27, 0x1CD20)}
# Number boxes (16 x 24, top left) of each region on the map: x table, y table (MAIN.EXE 0x56A9; hit test 0x7A20)
POINTS = {"mongolia": (0x309E, 0x30E0, 14), "world": (0x3122, 0x3164, 33)}
PALETTE_BASE, PALETTE_SEASON = 0x2C1A, 0x245E  # colours 0-7, colours 8-15 at + 0x48 * season (MAIN.EXE 0x4FE4)
MARKS = {3: "#", 2: "*"}  # +23 bits 0-1: DS:0x27C8; 3 = 君主, 2 = 君主の兄弟
# PACKDATA.DAT: pictures one after another in 信長4's packed format (nobu4_extras.decode_pack), 8 colours of the
# palette at PALETTE_BASE: 6 events 224 x 160, 31 オルド pictures 152 x 304, 47 region pictures 128 x 64, then
# 216 x 200, 432 x 224 and a 160 x 112 that does not decode (and 33 KB not in this format).
# オルド: u32 offsets at DS:0xAD5A, 11 groups x 3 stages (MAIN.EXE 0x20C21): stage 0 / 1 / 2 by [DS:0xADFE] < 100 /
# < 150 / more; the group is the woman's 文化圏 (0-7, same order as CULTURES), or 8 / 9 / 10 for face code 0 / 1 / 7
# (ボルテ, クラン, ラッチ; group 10 has one picture, all three offsets point to it, and stage 2 is skipped).
ORDO_OFFSETS, ORDO_SPECIAL = 0xAD5A, {8: 0, 9: 1, 10: 7}
# Region pictures: u32 offsets at DS:0x270C, index = region number, + 14 on the world map (MAIN.EXE 0xA8B9)
REGION_PICTURES = 0x270C
# Event pictures in file order: (name, evidence). 砂嵐-干ばつ: u32 offsets at DS:0xB504 and names at DS:0xB39C, one
# index (0x23A0A; the battle screen shows the same four from DS:0xC1E4 by [DS:0xBB9D] ^ 4, 0x24BF0); 疫病: 0x22F7E
# prints DS:0xB468 and loads offset 0; 豊作: 0x23750 prints DS:0xB4F4 and loads 0xCA7A; the オルド one is loaded at
# 0x20CEF after stage 2; the 432 x 224 one at 0x32BE2 (what that routine is, not followed).
EVENT_NAMES = [("疫病", "✅ code"), ("砂嵐", "✅ code"), ("寒波", "✅ code"), ("台風", "✅ code"), ("干ばつ", "✅ code"),
               ("豊作", "✅ code"), ("オルド", "✅ code"), ("勝利", "【推】")]


def pack_pictures(game_dir):
    """[(offset, image)] of PACKDATA.DAT, in file order, up to the first part that is not a picture"""
    from nobu4_extras import decode_pack, _image
    data, exe = _read(game_dir, "PACKDATA.DAT"), _read(game_dir, "MAIN.EXE")
    pal = palette(exe, 0)[:24]
    pal = [tuple(pal[i:i + 3]) for i in range(0, 24, 3)]
    out, off = [], 0
    while off < len(data):
        r = decode_pack(data, off)
        if not r or (r[1], r[2]) == (160, 112):
            break
        rows, w, h, used = r
        out.append((off, _image(rows, pal)))
        off += used
    return out


def pictures(game_dir, dos_dir, out):
    """eventcg/, ordo/ and regions/ with a CSV each"""
    exe = _read(game_dir, "MAIN.EXE")
    pics = pack_pictures(game_dir)
    by_off = dict(pics)
    events = [(o, im) for o, im in pics if im.size != (152, 304) and im.size != (128, 64)]
    os.makedirs(os.path.join(out, "eventcg"), exist_ok=True)
    rows = []
    for k, (o, im) in enumerate(events):
        im.save(os.path.join(out, "eventcg", f"pack{k:02d}.png"))
        rows.append({"file": f"pack{k:02d}.png", "offset": hex(o), "width": im.width, "height": im.height,
                     "name": EVENT_NAMES[k][0], "evidence": EVENT_NAMES[k][1]})
    _write_csv(os.path.join(out, "eventcg", "pack.csv"), rows)
    cultures = _strings(exe, CULTURES)
    os.makedirs(os.path.join(out, "ordo"), exist_ok=True)
    rows = []
    for g in range(11):
        for s in range(3):
            o = struct.unpack_from("<I", exe, DGROUP + ORDO_OFFSETS + 4 * (3 * g + s))[0]
            if g == 10 and s:
                continue
            by_off[o].save(os.path.join(out, "ordo", f"{g:02d}-{s}.png"))
            rows.append({"file": f"{g:02d}-{s}.png", "group": g, "stage": s, "offset": hex(o),
                         "culture": cultures[g] if g < 8 else "",
                         "face": ORDO_SPECIAL.get(g, "")})
    _write_csv(os.path.join(out, "ordo", "ordo.csv"), rows)
    mongolia, world = region_names(game_dir, dos_dir)
    os.makedirs(os.path.join(out, "regions"), exist_ok=True)
    rows = []
    for k, (ja, zh) in enumerate(mongolia + world):
        o = struct.unpack_from("<I", exe, DGROUP + REGION_PICTURES + 4 * k)[0]
        by_off[o].save(os.path.join(out, "regions", f"{k:02d}.png"))
        rows.append({"file": f"{k:02d}.png", "map": "mongolia" if k < 14 else "world",
                     "country": k if k < 14 else k - 14, "name": ja, "nameZh": zh, "offset": hex(o)})
    _write_csv(os.path.join(out, "regions", "regions.csv"), rows)
    return len(events), len(pics) - len(events) - 47, 47


def _read(game_dir, name):
    with open(os.path.join(game_dir, name), "rb") as f:
        return f.read()


def _ja(raw):
    return unicodedata.normalize("NFKC", raw.split(b"\0")[0].decode("cp932")).strip()


def _zh(raw):
    raw = raw.split(b"\0")[0]
    return koei_tw_name(raw + b"\0" * (len(raw) % 2)).strip()


def _strings(exe, table):
    off, n = table
    out = []
    for p in struct.unpack_from(f"<{n}H", exe, DGROUP + off):
        end = exe.index(b"\0", DGROUP + p)
        out.append(exe[DGROUP + p:end].decode("cp932").replace("　", "").replace(" ", ""))
    return out


def _records(data, table):
    off, size, n = table
    return [data[off + size * k:][:size] for k in range(n)]


def region_names(game_dir, dos_dir):
    """(ja, zh) names: ZNAME.DAT 17-byte records; [0] the 14 Mongolian regions, [1] the 33 world countries."""
    ja, zh = _read(game_dir, "ZNAME.DAT"), _read(dos_dir, "ZNAME.DAT")
    names = [(_ja(ja[17 * k:][:17]), _zh(zh[17 * k:][:17])) for k in range(len(ja) // 17)]
    return names[:14], names[ZNAME_WORLD:ZNAME_WORLD + 33]


def points(exe, which):
    xo, yo, n = POINTS[which]
    return list(zip(struct.unpack_from(f"<{n}H", exe, DGROUP + xo), struct.unpack_from(f"<{n}H", exe, DGROUP + yo)))


def palette(exe, season):
    raw = exe[DGROUP + PALETTE_BASE:][:24] + exe[DGROUP + PALETTE_SEASON + 0x48 * season:][:24]
    return [v * 17 for i in range(16) for v in (raw[3 * i + 1], raw[3 * i + 2], raw[3 * i])]  # stored B, R, G


def render_map(game_dir, which, season=0):
    data, exe = _read(game_dir, "MAPDATA.DAT"), _read(game_dir, "MAIN.EXE")
    im = Image.new("P", (640, 400))
    for i, off in enumerate(MAPS[which]):
        im.paste(world_band(data[off:]), (0, 200 * i))
    im.putpalette(palette(exe, season))
    return im


def maps(game_dir, out):
    os.makedirs(out, exist_ok=True)
    for which in ("mongolia", "world"):
        for s, season in enumerate(SEASONS):
            render_map(game_dir, which, s).save(os.path.join(out, f"{which}-{season}.png"))
    render_map(game_dir, "screen").save(os.path.join(out, "screen.png"))
    return 9


def scenario(game_dir, dos_dir, sc):
    """(countries, factions) rows of GENDATA<sc>."""
    exe = _read(game_dir, "MAIN.EXE")
    gen, gen_zh = _read(game_dir, f"GENDATA{sc}.DAT"), _read(dos_dir, f"GENDATA{sc}.DAT")
    cultures, climates, products, units = (_strings(exe, t) for t in (CULTURES, CLIMATES, PRODUCTS, UNITS))
    world = gen[STAGE] != 0
    names = region_names(game_dir, dos_dir)[world]
    pts = points(exe, "world" if world else "mongolia")
    factions = []
    for k, (f, fz) in enumerate(zip(_records(gen, FACTIONS)[:gen[N_FACTIONS]],
                                   _records(gen_zh, FACTIONS)[:gen[N_FACTIONS]])):
        if not f[:16].strip(b"\0") or f[21] & 0x80:
            continue
        capital, ruler = struct.unpack_from("<HH", f, 17)
        factions.append({"scenario": sc, "faction": k, "name": _ja(f[:16]), "nameZh": _zh(fz[:16]),
                         "capital": (capital - 0xBC4) // 49, "ruler": (ruler - 0x44) // 27,
                         "culture": cultures[f[21] & 7]})
    countries = []
    for k, c in enumerate(_records(gen, COUNTRIES)[:gen[N_COUNTRIES]]):
        gold, food, people = struct.unpack_from("<3H", c, 8)
        troops = list(c[0x16:0x26])
        x, y = pts[k]
        link = struct.unpack_from("<H", c, 0)[0]
        nxt = (link - 0xBC4) // 49 if link else ""  # +0: DS pointer to another country of the same owner
        countries.append({
            "scenario": sc, "map": "world" if world else "mongolia", "country": k, "label": k + 1,
            "name": names[k][0], "nameZh": names[k][1], "owner": c[2],
            "adjacent": " ".join(str(a) for a in c[3:8] if a != 0xFF),
            "金": gold, "食糧": food, "人口": people, "町%": c[0xE], "農%": c[0xF], "畜%": c[0x10], "特%": c[0x11],
            "城防": c[0x12], "経済": c[0x13], "農産": c[0x14], "住モ": c[0x15],
            "部隊": sum(troops), "troops": " ".join(f"{units[i]}{n}" for i, n in enumerate(troops) if n),
            "装備": c[0x26], "訓練": c[0x27], "特産品": products[c[0x28]] if c[0x28] < len(products) else c[0x28],
            "文化圏": cultures[c[0x29] >> 2 & 7], "気候": climates[c[0x29] >> 5],
            "病": c[0x2A] & 1, "災": c[0x2A] >> 1 & 3, "+0x2A bits 4-7": f"{c[0x2A] & 0xF0:02X}", "next": nxt, "x": x + 8,
            "y": y + 12})
    return countries, factions


def persons(game_dir, dos_dir, sc):
    exe = _read(game_dir, "MAIN.EXE")
    cultures, ranks = _strings(exe, CULTURES), _strings(exe, RANKS)
    gen, gen_zh = _read(game_dir, f"GENDATA{sc}.DAT"), _read(dos_dir, f"GENDATA{sc}.DAT")
    rows = []
    for i, (m, mz) in enumerate(zip(_records(gen, MEN), _records(gen_zh, MEN))):
        name = _ja(m[:17])
        if not name or m[24] & 0x80:
            continue
        g = GENCHOU_GRADES
        rows.append({
            "scenario": sc, "table": "men", "index": i, "name": name, "nameZh": _zh(mz[:17]),
            "faction": "" if m[17] == 0xFF else m[17], "country": "" if m[18] == 0xFF else m[18],
            "政治力": g[m[20] & 7], "戦闘力": g[m[20] >> 4 & 7], "指揮力": g[m[21] & 7], "魅力": g[m[21] >> 4 & 7],
            "体力": m[19] & 15, "体力上限": m[19] >> 4, "年齢": m[22], "mark": MARKS.get(m[23] & 3, ""),
            "文化圏": cultures[m[23] >> 2 & 7], "捕虜台詞": m[23] >> 5, "身分": ranks[m[24] & 3],
            "重病": m[24] >> 6 & 1, "+24 bits 2-5": m[24] >> 2 & 15, "face": f"{m[25] | m[26] << 8:04X}",
            "placeholder": int(name in PLACEHOLDERS)})
    for i, (w, wz) in enumerate(zip(_records(gen, WOMEN), _records(gen_zh, WOMEN))):
        name = _ja(w[:17])
        if not name:
            continue
        rows.append({"scenario": sc, "table": "women", "index": i, "name": name, "nameZh": _zh(wz[:17]),
                     "country": "" if w[20] == 0xFF else w[20], "+17": w[17], "+18": w[18], "+19": w[19],
                     "face": f"{w[21] | w[22] << 8:04X}"})
    return rows


def places(game_dir, out_dir):
    """koei-places/1 rows (places_export). 劇本 1 (蒙古篇) and 劇本 2-4 (世界篇) use two maps with different
    countries: 世界篇 keeps the game's number (1-33, the same in 劇本 2-4), 蒙古篇 gets 100 + number. name is the
    Chinese DOS spelling, nameJa the PC-98 one; pos is the centre of the number box on world/<map>-<season>.png."""
    dos_dir = os.path.join(game_dir, os.pardir, "genchou-dos")
    os.makedirs(os.path.join(out_dir, "world"), exist_ok=True)
    for which in ("mongolia", "world"):
        for s, season in enumerate(SEASONS):
            render_map(game_dir, which, s).save(os.path.join(out_dir, "world", f"{which}-{season}.png"))
    world = [scenario(game_dir, dos_dir, sc)[0] for sc in (2, 3, 4)]
    for other in world[1:]:  # the 世界篇 scenarios share names, adjacency and boxes
        assert [(c["name"], c["adjacent"], c["x"], c["y"]) for c in other] == \
            [(c["name"], c["adjacent"], c["x"], c["y"]) for c in world[0]]
    rows = []
    for base, stage, which, cs in ((100, "蒙古篇（劇本 1）", "mongolia", scenario(game_dir, dos_dir, 1)[0]),
                                   (0, "世界篇（劇本 2–4）", "world", world[0])):
        for c in cs:
            row = {"id": base + c["label"], "name": c["nameZh"]}
            if c["name"] != c["nameZh"]:
                row["nameJa"] = c["name"]
            row.update({"level": "國", "adjacent": [base + int(a) + 1 for a in c["adjacent"].split()],
                        "pos": {"x": c["x"], "y": c["y"], "grid": "pixel", "w": 640, "h": 400},
                        "notes": f"{stage}（`world/{which}-*.png`）；pos 是地圖上國號框的中心"})
            rows.append(row)
    return rows

def _write_csv(path, rows):
    header = []
    for r in rows:
        header += [k for k in r if k not in header]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, header)
        w.writeheader()
        w.writerows(rows)


@click.command()
@click.option("--game-dir", required=True, help="games/genchou-pc98")
@click.option("--dos-dir", default=None, help="games/genchou-dos (Chinese names); default <game-dir>/../genchou-dos")
@click.option("--out", required=True, help="output directory, e.g. games/genchou-pc98/extract")
def genchou_extras(game_dir, dos_dir, out):
    """蒼き狼と白き牝鹿・元朝秘史 PC-98: countries, factions, people per scenario, and the main maps."""
    dos_dir = dos_dir or os.path.join(game_dir, os.pardir, "genchou-dos")
    os.makedirs(out, exist_ok=True)
    countries, factions, people = [], [], []
    for sc in range(1, 5):
        c, f = scenario(game_dir, dos_dir, sc)
        countries += c
        factions += f
        people += persons(game_dir, dos_dir, sc)
    _write_csv(os.path.join(out, "countries.csv"), countries)
    _write_csv(os.path.join(out, "factions.csv"), factions)
    _write_csv(os.path.join(out, "persons.csv"), people)
    n = maps(game_dir, os.path.join(out, "map"))
    print(f"{len(countries)} countries, {len(factions)} factions, {len(people)} people in 4 scenarios, {n} maps")
    e, o, r = pictures(game_dir, dos_dir, out)
    print(f"PACKDATA: {e} event pictures, {o} オルド pictures, {r} region pictures")


if __name__ == "__main__":
    genchou_extras()
