"""大航海時代IV with PK HD for koei-wiki (koei-persons/1, koei-places/1): dataset koukai4pk-win. name is the
Traditional Chinese version's (TC/World0.dll, TC port names), nameJa the Japanese one; labels and values are the
Japanese game's words (DK4HD_jp.exe tables). The 本體 mode (World0.dll) is the main data; where the PK mode
(World1.dll) differs, the PK values go in game.PK*. Field sources: notes/koukai4.md「koei-wiki 匯出」.

- Persons: the kaodata characters, person records 0-97 and 213 (people) and 214-234 (酒場娘, the second name field is
  their port). The game has one shared start (seven protagonists, no scenario data per person), so no scenarios.
- Places: the 97 ports of World0.dll from ロンドン (koukai4_extras.tables); pos is the town position (map units of
  1/16 cell) as a World.dat cell, on world/world.png (2500 x 1250, one pixel per cell).
"""
import os
import struct

from PIL import Image

import kaodata_export as ke
import koei_games
import koukai4_extras as kx

DATASET = "koukai4pk-win"
# DK4HD_jp.exe VAs (.rdata, readable without decrypting): nationality names (person +0x27), star signs (12 x 32
# bytes, person +0x29; 13 = drawn at random), the six base values (person +0x20..+0x25), the zones (port +0x25;
# zone +8 is the sea area)
NATIONS, SIGNS, VALUES, ZONES = 0x140684a90, 0x14068ad60, 0x1406886b0, 0x1405b73e0
PERSON = koei_games.KOUKAI4_WIN_PERSON
PROTAGONISTS = range(7)  # the heroes of Sc0-6.dk4


def _pe(game_dir, *path, enc="cp932"):
    return kx.PE(os.path.join(game_dir, *path), enc)


def _names(e, va, n, stride=8):
    o = e.offset(va)
    return [e.text(e.ptr(o + stride * i)) for i in range(n)]


def _person_table(pe):
    o = pe.data.index("ラファエル".encode("cp932") + b"\0")
    return pe.data.index(struct.pack("<Q", pe.va(o)))


def _forces(w0):
    start, n = w0.table("カストール商会", 0x58)
    return [(w0.text(w0.ptr(start + 0x58 * i)), w0.data[start + 0x58 * i + 8]) for i in range(n)]


def _ports(game_dir):
    """(jp name, zh name, World0 record, World1 record) of the 97 ports, as koukai4_extras.tables finds them."""
    jp, w1 = _pe(game_dir, "JP", "World0.dll"), _pe(game_dir, "JP", "World1.dll")
    tc = _pe(game_dir, "TC", "World0.dll", enc="cp950")
    first = b"\x0c\x00" + "ブリストル".encode("cp932") + b"\0"
    o0, p1 = jp.data.index(first) + 2 - kx.PORT_SIZE, w1.data.index(first) + 2 - kx.PORT_SIZE
    t0 = tc.data.find(jp.data[o0 + 20:o0 + kx.PORT_SIZE]) - 20
    assert t0 >= 0
    out = []
    for i in range(kx.PORTS):
        rec = jp.data[o0 + i * kx.PORT_SIZE:][:kx.PORT_SIZE]
        pk = w1.data[p1 + i * kx.PORT_SIZE:][:kx.PORT_SIZE]
        out.append((rec[:20].split(b"\0")[0].decode("cp932"), tc.data[t0 + i * kx.PORT_SIZE:][:20].split(b"\0")[0]
                    .decode("cp950"), rec, pk))
    assert out[0][0] == "ロンドン"
    return out


def persons(game_dir):
    exe, w0, w1 = _pe(game_dir, "DK4HD_jp.exe"), _pe(game_dir, "JP", "World0.dll"), _pe(game_dir, "JP", "World1.dll")
    nations, values = _names(exe, NATIONS, 19), _names(exe, VALUES, 6)
    signs = _names(exe, SIGNS, 12, 32)
    forces, pk_forces = _forces(w0), _forces(w1)
    leads = {leader: name for name, leader in forces}
    port_ids = {jp: i for i, (jp, *_) in enumerate(_ports(game_dir))}
    base = koei_games.load_koukai4_win_persons(os.path.join(game_dir, "JP", "World0.dll"), "ラファエル", "cp932")
    zh = koei_games.load_koukai4_win_persons(os.path.join(game_dir, "TC", "World0.dll"), "拉斐爾", "cp950")
    t0, t1 = _person_table(w0), _person_table(w1)

    def force(fs, k):
        return fs[k][0] if k < len(fs) else None

    rows = []
    for i in [*ke.KOUKAI4PK_WIN_PEOPLE, *ke.KOUKAI4PK_WIN_GIRLS]:
        given, family, middle, sex, _ = base[i]
        z_given, z_family, z_middle = zh[i][:3]
        r, pk = w0.data[t0 + i * PERSON:][:PERSON], w1.data[t1 + i * PERSON:][:PERSON]
        girl = i in ke.KOUKAI4PK_WIN_GIRLS[1:]
        row = {"id": i}
        if girl:
            name_ja, name = given, z_given
        else:
            name_ja = "・".join(n for n in (given, middle, family) if n)
            if i in ke.KOUKAI4PK_WIN_EAST_ASIAN:
                name = z_family + ("" if i in ke.KOUKAI4PK_WIN_NO_MIDDLE_ZH else z_middle) + z_given
            else:
                name = "‧".join(n for n in (z_given, z_middle, z_family) if n)
        row["name"] = name
        if name_ja != name:
            row["nameJa"] = name_ja
        if not girl and i in ke.KOUKAI4PK_WIN_EAST_ASIAN and name.startswith(z_family) and name != z_family:
            row["familyName"] = z_family
        uncertain, game, notes = [], {}, []
        if any(r[0x20:0x26]):
            row["stats"] = dict(zip(values, r[0x20:0x26]))
            if pk[0x20:0x26] != r[0x20:0x26]:
                game["PK能力"] = dict(zip(values, pk[0x20:0x26]))
        more = {"性別": "女" if sex else "男"}
        if girl:
            port = family
            game["所在港"] = port
            notes.append(f"酒場娘（{port}の酒場）；遊戲只存名字和港名。")
            if port not in port_ids:
                notes.append("港名和港口表的寫法不同。")
        else:
            if r[0x27] < len(nations):
                more["国籍"] = nations[r[0x27]]
                uncertain.append("more.国籍")
            if r[0x29] < len(signs):
                more["星座"] = signs[r[0x29]]
                uncertain.append("more.星座")
            if force(forces, r[0x2A]):
                more["所属"] = force(forces, r[0x2A])
                uncertain.append("more.所属")
            if pk[0x2A] != r[0x2A]:
                game["PK所属"] = force(pk_forces, pk[0x2A]) or "なし"
                uncertain.append("game.PK所属")
        row["more"] = more
        if game:
            row["game"] = game
        if uncertain:
            row["uncertain"] = uncertain
        if i in PROTAGONISTS:
            notes.insert(0, f"主人公（劇本 Sc{i}.dk4）。")
        if i in leads:
            notes.append(f"{leads[i]}的首領（勢力表 +8）。")
        if "PK能力" in game or "PK所属" in game:
            notes.append("頂層是本體模式（World0.dll）的值，PK 模式（World1.dll）不同的放 game.PK*。")
        if notes:
            row["notes"] = "".join(notes)
        rows.append(row)
    return rows


def _cells(game_dir):
    with open(os.path.join(game_dir, "World.dat"), "rb") as f:
        data = f.read()
    return struct.unpack(f"<{len(data) // 2}H", data)


def _world_png(game_dir, path):
    """World.dat at one pixel per cell: each Chip.DK4 tile averaged (BOX) over the sea texture, as map/world.png of
    koukai4-extras shrunk to a quarter."""
    cells = _cells(game_dir)
    with open(os.path.join(game_dir, "Chip.DK4"), "rb") as f:
        tex = [kx.decode(fmt, w, h, px) for _, fmt, w, h, px in kx.textures(f.read())]
    chip, sea = tex[0], tex[4].convert("RGB").resize((16, 16), Image.BOX)
    seapx = list(sea.getdata())
    tiles = {}
    for v in set(cells):
        t = chip.crop((v % 16 * kx.TILE, v // 16 * kx.TILE, v % 16 * kx.TILE + kx.TILE, v // 16 * kx.TILE + kx.TILE))
        tiles[v] = t.resize((1, 1), Image.BOX).getpixel((0, 0)) if t.getextrema()[3][1] else None
    out = []
    for k, v in enumerate(cells):
        s = seapx[(k // kx.WORLD_W % 16) * 16 + k % kx.WORLD_W % 16]
        t = tiles[v]
        if t is None:
            out.append(s)
        else:
            a = t[3] / 255
            out.append(tuple(round(t[c] * a + s[c] * (1 - a)) for c in range(3)))
    im = Image.new("RGB", (kx.WORLD_W, kx.WORLD_H))
    im.putdata(out)
    im.save(path)


def places(game_dir, out_dir):
    exe, w0, w1 = _pe(game_dir, "DK4HD_jp.exe"), _pe(game_dir, "JP", "World0.dll"), _pe(game_dir, "JP", "World1.dll")
    zo = exe.offset(ZONES)
    zones = [(exe.text(exe.ptr(zo + 0xE0 * k)), exe.data[zo + 0xE0 * k + 8]) for k in range(len(kx.ZONES))]
    forces, pk_forces = [f for f, _ in _forces(w0)], [f for f, _ in _forces(w1)]
    world = os.path.join(out_dir, "world")
    os.makedirs(world, exist_ok=True)
    _world_png(game_dir, os.path.join(world, "world.png"))

    def facilities(r):
        bits, = struct.unpack_from("<I", r, 0x48)
        return [f for k, f in enumerate(kx.FACILITIES) if bits >> k & 1]

    def share(r, fs):
        return {fs[r[0x4C + 2 * k]]: r[0x4D + 2 * k] for k in range(3)
                if r[0x4C + 2 * k] != kx.NO_FORCE and r[0x4D + 2 * k]}

    rows = []
    for i, (name_ja, name, rec, pk) in enumerate(_ports(game_dir)):
        x, y = struct.unpack_from("<2I", rec, 0x14)
        zone, area = zones[rec[0x25]]
        game = {"海域": kx.SEA_AREAS[area], "施設": facilities(rec)}
        if rec[0x24]:
            game["中心港"] = True
        if share(rec, forces):
            game["シェア"] = share(rec, forces)
        if facilities(pk) != game["施設"]:
            game["PK施設"] = facilities(pk)
        if share(pk, pk_forces) != share(rec, forces):
            game["PKシェア"] = share(pk, pk_forces)
        row = {"id": i, "name": name, **({"nameJa": name_ja} if name_ja != name else {}), "level": "港",
               "region": zone,
               "pos": {"x": x // kx.UNIT, "y": y // kx.UNIT, "grid": "pixel", "w": kx.WORLD_W, "h": kx.WORLD_H},
               "game": game,
               "uncertain": [k for k in ("game.施設", "game.シェア", "game.PK施設", "game.PKシェア")
                             if k.split(".")[1] in game],
               "notes": "值是開局時的；本體模式（World0.dll）為主，PK 模式不同的放 game.PK*；region 是港口所屬的地域，"
                        "game.海域是地域所屬的海域；中心港（記錄 +0x24）是各地域的中心港，名稱是 kaodata-re 取的；"
                        "シェア是勢力的影響力（%）；pos 是 World.dat 的格（world/world.png 一格一點）。"}
        rows.append(row)
    return rows


def world_check(game_dir, rows):
    """Every port has sea (a Chip.DK4 tile with transparent pixels: open sea or coast) within 4 cells of its pos."""
    cells = _cells(game_dir)
    with open(os.path.join(game_dir, "Chip.DK4"), "rb") as f:
        chip = next(kx.decode(fmt, w, h, px) for _, fmt, w, h, px in kx.textures(f.read()))
    sea = {v for v in set(cells) if chip.crop((v % 16 * kx.TILE, v // 16 * kx.TILE, v % 16 * kx.TILE + kx.TILE,
                                                v // 16 * kx.TILE + kx.TILE)).getextrema()[3][0] < 255}
    checked, bad = 0, []
    for r in rows:
        x, y = r["pos"]["x"], r["pos"]["y"]
        checked += 1
        if not any(cells[yy * kx.WORLD_W + xx] in sea for yy in range(max(0, y - 4), min(kx.WORLD_H, y + 5))
                   for xx in range(max(0, x - 4), min(kx.WORLD_W, x + 5))):
            bad.append(f"{r['id']}: port {x},{y} has no sea within 4 cells")
    return checked, bad
