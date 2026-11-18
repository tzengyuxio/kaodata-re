"""ランペルール PC-98 (lempe-pc98) for koei-wiki: the world map and the 46 cities with pos (koei-places/1).

The PC-98 scenario files NPDATA1-5.CIM hold the same data as the DOS Chinese NPDATA.CIM (persons, city owners and
city links byte for byte, see world_check), so the rows are the lempe-dos rows (wiki_lempe.places, read from
../lempe-dos) plus pos on the PC-98 world map. Addresses are MAIN.EXE load-image offsets (file - 0x3E00), DGROUP
0x38A2 (image 0x38A20). Notes: notes/lempe.md「PC-98 版」."""
import os
import struct

from PIL import Image

import wiki_lempe
from common import cstr, read_file

SCENARIOS = 5
SAME = 0x1600  # NPDATA*.CIM 0..0x15FF equals the DOS scenario (persons, owners, date); later parts are moved
CITY, CITY_SIZE = 0x18A8, 41  # +0 name (12, half-width kana), +12 as DOS +15, +13 five u16 x, +23 five u16 y, +33 links
PC88_CITY = 0x1C28
MAP_X, MAP_Y = 0, 128  # picture 0 of the map table DS:0x3898 is drawn at (0, 128) (image 0x680E)
ICON_W, ICON_H = 24, 16  # city sprite and hit box (image 0x6BA6 draws 3 bytes x 16 rows; 0x3017 tests x+24, y+16)
# the analog palette after the fade-in (image 0x7030): colour = G<<2 | R<<1 | B at full intensity
PALETTE = [(0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0),
           (255, 255, 255)]


def decode_picture(data, off):
    """PACDATA picture (image 0x1476): u16 width, u16 height, then 4-pixel units drawn into VRAM row by row.
    Byte b < 0x80 + b2: (b >> 4) + 1 units with planes B = b2 & 15, R = b2 >> 4, G = b & 15. b >= 0x80: copy
    (b & 15) + 1 units from ((b >> 4) & 3) + 1 units back, or that many 640-pixel screen rows up if bit 6 is set.
    A row ends once its units are used up; a run past the end is overwritten by the next row."""
    w, h = struct.unpack_from("<HH", data, off)
    pos, bw = off + 4, (w + 3) // 4
    units = [None] * (160 * h)  # one screen row is 160 units; the map is 640 wide, so rows are screen rows
    for y in range(h):
        di, left = y * 160, bw
        while left > 0:
            b = data[pos]
            pos += 1
            if b & 0x80:
                n = (b & 15) + 1
                back = (((b >> 4) & 3) + 1) * (160 if b & 0x40 else 1)
                for k in range(n):
                    units[di + k] = units[di + k - back]
            else:
                b2 = data[pos]
                pos += 1
                n = ((b >> 4) & 7) + 1
                for k in range(n):
                    units[di + k] = (b2 & 15, b2 >> 4, b & 15)
            di += n
            left -= n
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            blue, red, green = units[y * 160 + x // 4]
            m = 8 >> (x % 4)
            px[x, y] = PALETTE[(4 if green & m else 0) | (2 if red & m else 0) | (1 if blue & m else 0)]
    return img


def _city(scen, c):
    return scen[CITY + CITY_SIZE * c:][:CITY_SIZE]


def places(game_dir, out_dir):
    world = os.path.join(out_dir, "world")
    os.makedirs(world, exist_ok=True)
    img = decode_picture(read_file(game_dir, "PACDATA.DAT"), 0)
    img.save(os.path.join(world, "world.png"))
    scen = read_file(game_dir, "NPDATA1.CIM")
    rows = wiki_lempe.places(os.path.join(game_dir, "..", "lempe-dos"), None)
    for r in rows:
        rec = _city(scen, r["id"])
        x, y = struct.unpack_from("<H", rec, 13)[0], struct.unpack_from("<H", rec, 23)[0]
        r["pos"] = {"x": x * 8 + ICON_W // 2 - MAP_X, "y": y + ICON_H // 2 - MAP_Y, "grid": "pixel",
                    "w": img.width, "h": img.height}
        r["game"].pop("座標")
        r["uncertain"].remove("game.座標")
        r["notes"] = ("城市、相鄰、各劇本的領有國與 DOS 中文版（lempe-dos）相同（PC-98 NPDATA1–5.CIM 與 DOS 逐 byte 比對），"
                      "name 用中文版，nameJa 是 PC-98 的片假名（同 PC-88），nameEn 取英文版。"
                      "pos 是城市圖示（24×16）的中心：城市記錄 +13 的 x（×8）與 +23 的 y 是畫面座標，大地圖畫在畫面 (0, 128)，"
                      "所以減掉 128；記錄裡另外 4 組座標是其他 4 張區域地圖用的，不匯出。地圖上印的城市號是 id＋1。"
                      "臨海是 +33 bit 0（推定，和地理一致）。")
    return rows


def world_check(game_dir, rows):
    """The PC-98 scenarios equal the DOS ones where the rows come from; nameJa and links match the PC-98 city
    records; every pos is inside the map."""
    dos = read_file(os.path.join(game_dir, "..", "lempe-dos"), "NPDATA.CIM")
    checked, bad = 0, []
    for k in range(SCENARIOS):
        scen = read_file(game_dir, f"NPDATA{k + 1}.CIM")
        d = dos[k * wiki_lempe.SCEN:(k + 1) * wiki_lempe.SCEN]
        checked += 1
        if scen[:SAME] != d[:SAME]:
            bad.append(f"scenario {k + 1}: PC-98 NPDATA differs from DOS before {SAME:#x}")
        for r in rows:
            rec = _city(scen, r["id"])
            checked += 1
            if rec[33:41] != d[wiki_lempe.CITY + 34 * r["id"] + 26:][:8]:
                bad.append(f"scenario {k + 1} city {r['id']}: links or flags differ from DOS")
    for r in rows:
        rec = _city(read_file(game_dir, "NPDATA1.CIM"), r["id"])
        checked += 2
        if cstr(rec[:12], nfkc=True).strip() != r.get("nameJa", r["name"]):
            bad.append(f"{r['id']}: PC-98 name {cstr(rec[:12], nfkc=True).strip()} != nameJa")
        p = r["pos"]
        if not (0 <= p["x"] < p["w"] and 0 <= p["y"] < p["h"]):
            bad.append(f"{r['id']}: pos {p['x']},{p['y']} outside the map")
    return checked, bad
