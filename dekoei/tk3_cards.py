"""提督の決断III PK (PC-98): one picture per weapon, drawn like the game's 艦型 / 航空機 / 戦車 / 新兵器 windows
(notes/koei-games.md「事件、插圖、地圖」「兵器資料卡」).

What comes from the game files and what from the screenshots:
- Game files: the ship / aircraft / tank / new-weapon pictures and their BACKGRP backgrounds, the national flags
  (PARTS.TK3 part 0, 32 x 24 at (nation - 1) * 0x180), the ship's-wheel background (PARTS2.TK3 part 0 0x5660, an
  80 x 80 1 bpp tile drawn in colours 1 and 10 from the window's top left), every value and the text formats
  (MESSAGE.TK3), and the aircraft 航空性能 chart's red line.
- Screenshots (captures/screenshots/tk3pk-pc98): the window frame, title bar, label boxes, buttons and the chart's
  pentagon. Per window kind the pixel that most captures agree on is taken (the mouse cursor and the values
  differ), then every value field is cleared again before drawing.
- Text: the PC-98 font from DOSBox-X's freecg98.bmp (the font the captures were taken with; 8 x 16 ANK at
  x = code * 8, y = 0; JIS kanji at x = (row - 0x20) * 16, y = cell * 16), drawn bold (each dot also one to the
  right) like the game. Half-width kana are hiragana after \\x1bH (the default), full-width katakana after \\x1bK,
  half-width after \\x1bk.
"""
import math
import os
import struct
import unicodedata

from PIL import Image

from ls11 import ls11_decode_parts
from gfx import decode_planar

EXPAND = [0x00, 0x10, 0x20, 0x30, 0x45, 0x55, 0x65, 0x75, 0x8A, 0x9A, 0xAA, 0xBA, 0xCF, 0xDF, 0xEF, 0xFF]  # DOSBox-X
W, H = 640, 400
GEAR = 0x5660  # PARTS2.TK3 part 0
FLAG_SIZE = 0x180
TEXT, BLACK = 15, 10

# window rectangles (x0, y0, x1, y1) on the 640 x 400 screen, and the screenshots of each kind
WINDOWS = {"ships": (16, 10, 625, 391), "aircraft": (48, 50, 593, 351), "tanks": (184, 110, 465, 291),
           "new_weapons": (80, 98, 569, 303)}
CAPTURES = {"ships": [35, 42, 43, 44, 45, 46, 47, 48, 55, 56, 57, 58, 59, 60, 61], "aircraft": [39, 40, 41],
            "tanks": [49, 50], "new_weapons": [36, 37, 38, 51]}
CAPTURE_NAME = "user-guest-os_{:03d}.png"
FONT = "~/Downloads/dosbox-x-macosx-arm64-2026/dosbox-x/dosbox-x.app/Contents/Resources/freecg98.bmp"


def expand_palette(raw):
    """16 x (B, R, G) 4-bit values -> RGB as DOSBox-X shows them."""
    return [(EXPAND[raw[3 * i + 1]], EXPAND[raw[3 * i + 2]], EXPAND[raw[3 * i]]) for i in range(16)]


class Font:
    def __init__(self, path):
        self.im = Image.open(path).convert("1")
        self.cache = {}

    def _crop(self, box):
        if box not in self.cache:
            g = self.im.crop(box)
            px = g.load()
            self.cache[box] = (g.size[0], [(x, y) for y in range(16) for x in range(g.size[0]) if px[x, y] == 0])
        return self.cache[box]

    def ank(self, c):
        return self._crop((c * 8, 0, c * 8 + 8, 16))

    def kanji(self, b1, b2):
        j1 = (b1 - 0x71 if b1 <= 0x9F else b1 - 0xB1) * 2 + 1
        if b2 > 0x7F:
            b2 -= 1
        j1, j2 = (j1 + 1, b2 - 0x7D) if b2 >= 0x9E else (j1, b2 - 0x1F)
        return self._crop(((j1 - 0x20) * 16, j2 * 16, (j1 - 0x20) * 16 + 16, j2 * 16 + 16))

    def glyphs(self, raw, mode="H"):
        out, i = [], 0
        while i < len(raw):
            c = raw[i]
            if c == 0x1B:
                mode = chr(raw[i + 1])
                i += 2
            elif c in (0, 5):
                break
            elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC:
                out.append(self.kanji(c, raw[i + 1]))
                i += 2
            elif 0xA6 <= c <= 0xDD and c != 0xB0 and mode != "k":
                s = raw[i:i + 1]
                i += 1
                if i < len(raw) and raw[i] in (0xDE, 0xDF):
                    s += raw[i:i + 1]
                    i += 1
                ch = unicodedata.normalize("NFKC", s.decode("cp932"))
                if mode == "H" and "ァ" <= ch <= "ヶ":
                    ch = chr(ord(ch) - 0x60)
                b = ch.encode("cp932")
                out.append(self.kanji(b[0], b[1]))
            else:
                out.append(self.ank(c))
                i += 1
        return out

    def width(self, raw, mode="H"):
        return sum(w for w, _ in self.glyphs(raw, mode))


class Canvas:
    """640 x 400 colour numbers."""

    def __init__(self, base, font, gear):
        self.px = bytearray(base)
        self.font = font
        self.gear_tile = gear

    def put(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[y * W + x] = c

    def strip(self, rect, xs, period=2):
        """Refill rect with the texture of columns xs .. xs + period - 1 (box and button faces)."""
        x0, y0, x1, y1 = rect
        for y in range(y0, y1):
            row = self.px[y * W + xs:y * W + xs + period]
            for x in range(x0, x1):
                self.px[y * W + x] = row[(x - xs) % period]

    def restore(self, base, rect, color):
        """Put back the template's dots of one colour in rect (lines the game draws over a picture)."""
        x0, y0, x1, y1 = rect
        for y in range(y0, y1):
            for x in range(x0, x1):
                if base[y * W + x] == color:
                    self.px[y * W + x] = color

    def box(self, base, x, y, faces):
        """Clear the box around (x, y + 8): the run of `faces` (or text) colours on that row of the template."""
        row = (y + 8) * W
        ok = set(faces) | {TEXT, BLACK}
        left = x
        while base[row + left - 1] in ok:
            left -= 1
        right = x
        while base[row + right] in ok:
            right += 1
        while base[row + left] not in faces or base[row + left + 1] not in faces:
            left += 1
        self.strip((left, y, right, y + 16), left)
        return left, right

    def boxed(self, base, raw, cx, y, faces=(5, 8), mode="H"):
        """A value centred in its box (the box is found from the template and cleared first)."""
        self.box(base, cx, y, faces)
        self.centred(raw, cx, y, mode=mode)

    def gear(self, rect, origin):
        x0, y0, x1, y1 = rect
        ox, oy = origin
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.px[y * W + x] = 1 if self.gear_tile[(y - oy) % 80][(x - ox) % 80] else 10

    def paste(self, im, x, y, transparent=False):
        w, h = im.size
        data = im.tobytes()
        for yy in range(h):
            for xx in range(w):
                c = data[yy * w + xx]
                if not (transparent and c == 0):
                    self.put(x + xx, y + yy, c)

    def text(self, raw, x, y, color=TEXT, mode="H"):
        for w, dots in self.font.glyphs(raw, mode):
            for dx, dy in dots:
                self.put(x + dx, y + dy, color)
                self.put(x + dx + 1, y + dy, color)
            x += w

    def centred(self, raw, cx, y, color=TEXT, mode="H"):
        """Centre on cx, moved left onto the 4-dot text grid (x % 4 == 3 in every capture)."""
        x = cx - self.font.width(raw, mode) // 2
        self.text(raw, x - (x - 3) % 4, y, color, mode)

    def line(self, p, q, c):
        (x0, y0), (x1, y1) = p, q
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.put(x0, y0, c)
            if (x0, y0) == (x1, y1):
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def image(self, rect, pal):
        x0, y0, x1, y1 = rect
        im = Image.frombytes("P", (W, H), bytes(self.px)).crop(rect)
        im.putpalette([v for c in pal for v in c])
        return im


def load_capture(path, pal):
    """Screenshot -> colour numbers (unknown colours -> 255)."""
    lookup = {}
    for i, c in enumerate(pal):
        lookup.setdefault(c, i)
    return bytes(lookup.get(c, 255) for c in Image.open(path).convert("RGB").getdata())


def template(captures, rect, ignore=()):
    """Per pixel, the colour most captures agree on (colours in `ignore` only when nothing else is there)."""
    out = bytearray(W * H)
    x0, y0, x1, y1 = rect
    for y in range(y0, y1):
        for x in range(x0, x1):
            k = y * W + x
            counts = {}
            for cap in captures:
                counts[cap[k]] = counts.get(cap[k], 0) + 1
            best = sorted(counts.items(), key=lambda kv: (kv[0] in ignore, -kv[1]))
            out[k] = best[0][0]
    return bytes(out)


def planar(data, w, h):
    return Image.frombytes("P", (w, h), bytes(decode_planar(data, 0, w, h, 4)))


def fmt(raw, *values):
    """Fill the %s / %Nd / %Nu / %Nlu of a MESSAGE.TK3 format (bytes) like printf."""
    out, i, k = b"", 0, 0
    while i < len(raw):
        if raw[i] == 0x25:
            j = i + 1
            while raw[j] in b"-0123456789l":
                j += 1
            v = values[k]
            k += 1
            out += v if raw[j] == 0x73 else (b"%" + raw[i + 1:j].replace(b"l", b"") + b"d") % v
            i = j + 1
        else:
            out += raw[i:i + 1]
            i += 1
    return out


# ------------------------------------------------------------------------------------------------ ship window

# ship window: new-weapon button k (0-10) has its label at SHIP_SLOTS[k]; the button faces are x = 75 + 88 * col .. +81
SHIP_SLOTS = [(79, 314), (167, 314), (255, 314), (355, 314), (443, 314), (531, 314),
              (91, 338), (191, 338), (259, 338), (347, 338), (435, 338)]


def ship_slots(r):
    """Which new weapons the ship window lists (inferred from 15 screenshots, not from the code)."""
    main, calibre, torp, aa, flags = r[15], r[16], r[19], r[20], r[34]
    sub = flags & 15 == 10
    big_gun = main and calibre <= 10  # 20.0 cm or more
    return [True, True, big_gun, not sub, sub, big_gun, aa > 0, True, torp > 0, torp > 0, bool(flags & 0x10)]


REFIT_KIND = {1: 2684, 0: 2681, 5: 2682, 8: 2683, 7: 2680, 2: 2685}  # 0x80 variants by 艦種 -> MESSAGE id


def refit_label(r):
    """The 改装 name of a variant (MESSAGE 2678-2685), inferred from the flags (+34) and checked on 4 windows."""
    flags = r[34]
    if flags & 0x80:
        return REFIT_KIND.get(flags & 15, 2679)
    return 2679 if flags & 0x40 else 2678


# ------------------------------------------------------------------------------------------------ cards

class Cards:
    def __init__(self, game_dir, font_path, capture_dir):
        read = lambda n: open(os.path.join(game_dir, n), "rb").read()  # noqa: E731
        self.exe = read("MAIN.EXE")
        self.pal = expand_palette(self.exe[0x3E6BA:0x3E6BA + 48])
        self.font = Font(font_path)
        msg = ls11_decode_parts(read("MESSAGE.TK3"))
        self.messages = msg
        p2 = ls11_decode_parts(read("PARTS2.TK3"))[0][GEAR:GEAR + 800]
        self.gear = [[(p2[y * 10 + x // 8] >> (7 - x % 8)) & 1 for x in range(80)] for y in range(80)]
        self.flags_data = ls11_decode_parts(read("PARTS.TK3"))[0]
        self.pics = {n: ls11_decode_parts(read(f"{n}.TK3")) for n in ("KSGRP", "KKGRP", "SSGRP", "HKGRP", "BACKGRP")}
        self.templates = {}
        caps = {}
        for kind, ns in CAPTURES.items():
            for n in ns:
                if n not in caps:
                    caps[n] = load_capture(os.path.join(capture_dir, CAPTURE_NAME.format(n)), self.pal)
            self.templates[kind] = template([caps[n] for n in ns], WINDOWS[kind], ignore=(2,) if kind == "aircraft"
                                            else ())
        self.captures = caps

    def raw(self, mid):
        d = self.messages[mid // 1000]
        count = struct.unpack_from("<H", d)[0]
        offs = list(struct.unpack_from(f"<{count}H", d, 2)) + [len(d)]
        return d[offs[mid % 1000]:offs[mid % 1000 + 1]].split(b"\x05")[0]

    def flag(self, nation):
        return planar(self.flags_data[(nation - 1) * FLAG_SIZE:nation * FLAG_SIZE], 32, 24)

    def canvas(self, kind):
        return Canvas(self.templates[kind], self.font, self.gear)

    def gear_origin(self, kind):
        return WINDOWS[kind][:2]

    # -- ships
    def ship(self, k):
        exe = self.exe
        rec = lambda n: exe[0x3FB10 + (n - 1) * 38:0x3FB10 + n * 38]  # noqa: E731
        r = rec(k)
        name = r[:12]
        group = [n for n in range(1, 236) if rec(n)[:12] == name]
        base = next((n for n in group if refit_label(rec(n)) == 2678), k)
        cls = self.raw(2070 + rec(base)[31]).split(b"\x81i")[0]  # without （日）
        c = self.canvas("ships")
        g = self.gear_origin("ships")
        c.strip((200, 15, 440, 31), 100, 8)
        c.centred(cls, 320, 15)
        c.strip((28, 42, 117, 58), 26)
        c.centred(self.raw(2304 + (r[34] & 15)), 72, 42)
        c.strip((144, 42, 292, 58), 142)
        c.centred(cls, 208, 42)
        c.gear((296, 38, 392, 62), g)  # 同型艦 button: only on the player's own classes (game state), left out
        others = [self.raw(refit_label(rec(n))) for n in group if n != k]
        c.strip((452, 42, 598, 58), 450)
        c.centred(b"&".join(others) if others else self.raw(2266), 524, 42)
        c.paste(self.flag(r[13]), 24, 66)
        c.strip((70, 70, 446, 86), 66)
        cost, steel = struct.unpack_from("<2H", r, 27)
        c.text(fmt(self.raw(2041).replace(b"%4d", b"  --"), cost, steel), 71, 70)
        main, sec, torp = r[15], r[17], r[19]
        for y, x, v in [(101, 119, (r[16], main >> 4, main & 15) if main else None),
                        (129, 119, (r[18], sec >> 5, sec & 31) if sec else None)]:
            c.gear((x, y, 290, y + 16), g)
            c.text(fmt(self.raw(2263), self.raw(2008 + v[0]), b"cm", self.raw(2036 + v[1]), v[2], v[2])
                   if v else self.raw(2266), x, y)
        c.gear((135, 157, 290, 173), g)
        c.text(fmt(self.raw(2265), self.raw(2036 + (torp >> 4)), torp & 15, torp & 15) if torp else self.raw(2266),
               135, 157)
        for (x, y, x1), s in [((439, 101, 497), fmt(self.raw(2269), b"", r[20], r[20])),
                              ((431, 129, 505), fmt(self.raw(2271), b"", r[21], r[21])),
                              ((455, 157, 489), self.raw(2267 if r[34] & 0x10 else 2266)),
                              ((543, 209, 568), b"%3d" % r[26]),
                              ((151, 261, 225), b"%2d/%2dkn/h" % (r[24], r[24])),
                              ((167, 289, 209), b"%2d/%2d" % (r[22], r[22])),
                              ((463, 261, 513), b" 0/%3d" % r[25]),
                              ((455, 289, 497), b"%2d/%2d" % (r[23], r[23]) if r[23] else b"--/--")]:
            c.gear((x, y, x1, y + 16), g)
            c.text(s, x, y)
        bg = planar(self.pics["BACKGRP"][0], 288, 72)
        c.paste(bg, 136, 178)
        c.paste(planar(self.pics["KSGRP"][r[31] % 190], 288, 72), 136, 178, transparent=True)
        c.restore(self.templates["ships"], (136, 178, 424, 250), TEXT)  # the lines drawn over the picture
        for j, ((x, y), on) in enumerate(zip(SHIP_SLOTS, ship_slots(r))):
            col = (j % 6) if j < 6 else j - 6
            left = 75 + 88 * col
            c.strip((left, y, left + 81, y + 16), left + 1)
            if on:
                c.text(self.weapon_name(j), x, y, BLACK, "k")
        return c.image(WINDOWS["ships"], self.pal)

    def weapon_name(self, i):
        return self.exe[0x429E0 + i * 21:0x429E0 + i * 21 + 11].split(b"\0")[0]

    # -- aircraft
    def aircraft(self, i):
        exe = self.exe
        r = exe[0x41E00 + i * 22:0x41E00 + (i + 1) * 22]
        p = exe[0x52180 + i * 15:0x52180 + (i + 1) * 15]
        base = self.templates["aircraft"]
        c = self.canvas("aircraft")
        g = self.gear_origin("aircraft")
        name = r[:12].split(b"\0")[0]
        c.strip((150, 55, 490, 71), 100, 8)
        c.centred(name, 320, 55, mode="k")
        c.paste(self.flag(r[13]), 76, 78)
        kind = r[21]
        deck = self.raw(2763) if p[11] & 1 else self.raw(2764) if p[11] & 2 else b""
        c.boxed(base, self.raw(7144 if kind & 1 else 7145) + deck + self.raw(2707 + ((kind >> 1) & 7)), 180, 82)
        c.boxed(base, name, 300, 82, mode="k")
        arm = ARMS[2] if kind & 0x20 else ARMS[1] if kind & 0x10 else ARMS[0]
        c.boxed(base, exe[arm:exe.index(b"\0", arm)], 396, 82)
        c.paste(planar(self.pics["BACKGRP"][4], 192, 64), 76, 106)
        c.paste(planar(self.pics["KKGRP"][i], 192, 64), 76, 106, transparent=True)
        if not p[11] & 4:
            c.gear((76, 174, 116, 198), g)  # no 偵察 box
        cost, alu = struct.unpack_from("<2H", r, 15)
        c.box(base, 90, 204, (5, 8))
        c.text(fmt(self.raw(2715), cost, alu), 91, 204)
        c.boxed(base, b"--", 252, 228)
        c.box(base, 90, 252, (5, 8))
        c.text(self.raw(2718), 83, 252)
        c.box(base, 90, 276, (5, 8))
        c.text(self.raw(2714), 79, 276)
        speed, reach = struct.unpack_from("<2H", p, 3)
        c.boxed(base, b"%d" % p[0], 444, 114)
        c.boxed(base, b"%d" % p[1], 348, 166)
        c.boxed(base, b"%d" % p[2], 532, 166)
        c.box(base, 380, 242, (5, 8))
        c.text(fmt(self.raw(2779), reach), 359, 242)
        c.box(base, 500, 242, (5, 8))
        c.text(fmt(self.raw(2780), speed), 475, 242)
        pts = []
        for k, (v, m) in enumerate(zip((p[0], p[2], speed, reach, p[1]), (100, 100, 1000, 600, 100))):
            ang = math.radians(-90 + 72 * k)
            rr = min(v, m) * CHART_R / m  # 航続 over 6000 km (富嶽 and others) kept on the pentagon 【推】
            pts.append((CHART_C[0] + int(rr * math.cos(ang)), CHART_C[1] + int(rr * math.sin(ang))))
        for k in range(5):
            c.line(pts[k], pts[(k + 1) % 5], 2)
        for j, on in enumerate(aircraft_slots(kind)):
            cx = 212 + 96 * j
            c.strip((167 + 96 * j, 302, 254 + 96 * j, 318), 167 + 96 * j)
            if on:
                c.centred(self.weapon_name(11 + j), cx, 302, BLACK, "k")
        return c.image(WINDOWS["aircraft"], self.pal)

    # -- tanks
    def tank(self, i):
        r = self.exe[0x42850 + i * 20:0x42850 + (i + 1) * 20]
        base = self.templates["tanks"]
        c = self.canvas("tanks")
        c.strip((207, 115, 442, 131), 212, 8)
        c.centred(r[:11].split(b"\0")[0], 324, 115, mode="k")
        c.paste(self.flag(r[11]), 212, 138)
        c.paste(planar(self.pics["BACKGRP"][5], 120, 56), 212, 170)
        c.paste(planar(self.pics["SSGRP"][i], 120, 56), 212, 170, transparent=True)
        c.box(base, 350, 190, (5, 8))
        c.text(fmt(self.raw(1259), r[19]), 347, 190)
        cost, steel = struct.unpack_from("<2H", r, 13)
        c.box(base, 222, 238, (5, 8))
        c.text(fmt(self.raw(1260), cost, steel), 219, 238)
        return c.image(WINDOWS["tanks"], self.pal)

    # -- new weapons
    def new_weapon(self, i):
        r = self.exe[0x429E0 + i * 21:0x429E0 + (i + 1) * 21]
        base = self.templates["new_weapons"]
        c = self.canvas("new_weapons")
        c.strip((150, 103, 500, 119), 120, 8)
        c.centred(r[:11].split(b"\0")[0], 324, 103, mode="k")
        c.paste(planar(self.pics["HKGRP"][i], 152, 88), 108, 127)
        g = self.gear_origin("new_weapons")
        for k, line in enumerate(self.raw(1240 + i).split(b"\n")):
            c.gear((270, 130 + 17 * k, 527, 146 + 17 * k), g)
            c.text(line, 275, 130 + 17 * k)
        for k, v in enumerate(struct.unpack_from("<5H", r, 11)):
            c.box(base, 210 + 72 * k, 226, (5, 8))
            c.text(b"%2d" % v, 207 + 72 * k, 226)
        c.gear((100, 248, 560, 276), g)  # each nation's 開発中: game state
        return c.image(WINDOWS["new_weapons"], self.pal)


CHART_C, CHART_R = (412, 190), 50  # aircraft 航空性能 pentagon: centre and axis length on the screen
ARMS = (0x5D1DE, 0x5D1E4, 0x5D1EC)  # MAIN.EXE: 銃装, 爆装, 雷装


def aircraft_slots(kind):
    """航空ﾚｰﾀﾞｰ, 焼夷弾, 航空ﾛｹｯﾄ弾, 誘導弾 on the aircraft window (inferred from 3 screenshots and the
    weapon descriptions MESSAGE 1251-1254, not from the code)."""
    bomber = (kind >> 1) & 7 in (1, 5)
    return [False, bomber, bool(kind & 0x10), bool(kind & 0x10)]


def file_name(record, name):
    return f"{record:03d}_" + "".join("_" if ch in '/\\:*?"<>| ' else ch for ch in name) + ".png"


def write_cards(out, game_dir, font, captures, rows):
    """rows: the ships, aircraft, tanks and new_weapons table rows of tk3_extras (record numbers and names)."""
    cards = Cards(game_dir, font, captures)
    n = 0
    for kind, draw, table in zip(("ships", "aircraft", "tanks", "new_weapons"),
                                 (cards.ship, cards.aircraft, cards.tank, cards.new_weapon), rows):
        folder = os.path.join(out, kind)
        os.makedirs(folder, exist_ok=True)
        for row in table:
            draw(row["record"]).save(os.path.join(folder, file_name(row["record"], row["name"])))
            n += 1
    return n
