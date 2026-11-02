"""FB reel: the strategic map, one province opens into its hex battlefield, all 41 fly out and
lock together, the joined map turns 30 degrees into China, then the question.

python reel.py fc OUT.mp4   (fc, sfc or pc98; run pc98_assets.py first for pc98)
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
FONT = "/Users/user/.local/share/fonts/STHeiti Medium.ttc"
FC = "/Users/user/works/famicom-re/san2/output"

# axial hex coordinates of provinces 1-41 (kaodata-re dekoei/san2.py SAN2_PROVINCE_HEX)
HEX = [
    (0, 0), (1, 0), (2, 0), (3, 0), (4, -1), (2, -1), (3, -1), (2, -2), (3, -2), (4, -2),
    (5, -2), (6, -2), (7, -2), (7, -1), (6, 0), (3, -3), (4, -3), (4, -4), (5, -3), (6, -3),
    (6, -4), (6, -5), (7, -5), (3, -4), (4, -5), (5, -6), (5, -5), (5, -4), (7, -3), (8, -3),
    (7, -4), (8, -4), (9, -4), (9, -5), (10, -5), (10, -6), (6, -6), (7, -6), (8, -6), (8, -5),
    (9, -6),
]
# province label centres on the FC strategic map (448x288), read off map.png
FC_LABELS = [
    (409, 40), (343, 40), (265, 40), (216, 40), (216, 72), (312, 72), (265, 72), (359, 88),
    (312, 104), (262, 104), (216, 104), (167, 88), (119, 104), (71, 88), (39, 72), (359, 120),
    (280, 136), (327, 136), (231, 136), (184, 136), (231, 168), (264, 216), (216, 200), (391, 152),
    (391, 184), (376, 216), (344, 200), (312, 184), (135, 136), (88, 136), (167, 168), (120, 168),
    (56, 168), (88, 200), (24, 216), (71, 248), (327, 232), (247, 248), (200, 248), (152, 216),
    (152, 264),
]

SFC = "/Users/user/works/superfamicom-re/san2/output"
SFC_LABELS = [
    (409, 24), (343, 24), (296, 24), (247, 24), (231, 56), (327, 56), (279, 56), (359, 88),
    (312, 104), (264, 104), (216, 104), (184, 88), (136, 88), (104, 72), (56, 24), (375, 120),
    (296, 136), (343, 152), (263, 136), (200, 136), (247, 184), (279, 216), (216, 216), (423, 136),
    (408, 184), (391, 216), (343, 200), (312, 184), (152, 136), (104, 120), (167, 168), (120, 168),
    (72, 152), (104, 200), (24, 200), (72, 232), (327, 248), (247, 264), (200, 264), (167, 216),
    (152, 264),
]

PC98_LABELS = [
    (272, 64), (227, 76), (181, 80), (152, 90), (156, 115), (205, 115), (181, 115), (239, 134), (202, 150),
    (173, 153), (147, 146), (121, 147), (84, 159), (64, 123), (24, 81), (239, 169), (197, 183), (226, 199),
    (172, 199), (134, 196), (163, 236), (179, 285), (145, 270), (261, 204), (267, 241), (255, 285), (235, 248),
    (210, 245), (93, 196), (62, 186), (114, 236), (82, 239), (52, 231), (73, 284), (26, 289), (56, 322),
    (217, 316), (170, 328), (139, 332), (112, 297), (101, 345),
]
VIDEO = os.path.dirname(os.path.abspath(__file__))  # pc98_map.png, pc98_司馬懿.png from pc98_assets.py
PC98 = "/Users/user/works/kaodata-re/games/san2-pc98/extract/battlemap"

VERSIONS = {
    "fc": dict(
        map=f"{FC}/map.png", fields=f"{FC}/battle_maps/{{:02d}}.png", labels=FC_LABELS,
        hook=["41 張戰場", "拼出一個天下"],
        face=f"{FC}/faces/255_諸葛亮.png",
        say=dict(
            intro=["主公請看，", "這是天下形勢圖。"],
            field=["每州交兵之時，", "皆是一張六角戰場。"],
            join=["依州界相鄰排之，", "江河山脈竟能相連。"],
            turn=["再稍微轉一下——"],
            ask=["此片分魏、蜀、吳三版，", "主公所見乃蜀（FC）之天下，", "其餘兩版，微臣亦已備妥。"],
        ),
        focus=21,  # province opened in close-up
        order="number",  # how the fields leave the map
        cmp_from="top",  # where the strategic map comes back from at the end
    ),
    "sfc": dict(
        map=f"{SFC}/map.png", fields=f"{SFC}/battle_maps/{{:02d}}.png", labels=SFC_LABELS,
        hook=["把 41 個戰場拼起來", "會出現什麼？"],
        face=f"{SFC}/faces/158_周瑜.png",
        say=dict(
            intro=["主公，", "此乃天下形勢之圖。"],
            field=["一州一戰場，", "六角棋盤之上決勝負。"],
            join=["將諸州戰場並列，", "山川竟連成天下！"],
            turn=["主公，再稍稍轉一下⋯⋯"],
            ask=["此片分魏、蜀、吳三版，", "主公所見乃吳（SFC）之天下，", "餘下兩版，微臣恭候一閱。"],
        ),
        focus=28,
        order="radial",
        cmp_from="left",
    ),
    "pc98": dict(
        map=f"{VIDEO}/pc98_map.png", fields=f"{PC98}/{{:02d}}.png", labels=PC98_LABELS,
        hook=["41 張六角格戰場", "藏著整個天下"],
        face=f"{VIDEO}/pc98_司馬懿.png",
        say=dict(
            intro=["主公請看，", "天下形勢盡在此圖。"],
            field=["每州之戰，", "皆布於六角之陣。"],
            join=["依諸州之鄰而合，", "山河自成一體。"],
            turn=["稍轉一下，便知分曉。"],
            ask=["此片分魏、蜀、吳三版，", "此乃魏（PC-9801）之天下，", "其餘兩版，微臣另有安排。"],
        ),
        focus=19,
        order="north",
        cmp_from="right",
    ),
}


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def ease_out_back(t):
    t = min(max(t, 0.0), 1.0)
    c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


def phase(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


cfg = VERSIONS[sys.argv[1]]
out = sys.argv[2]
smap = Image.open(cfg["map"]).convert("RGB")
MAP_PAD = 600
smap_pad = Image.new("RGB", (smap.width + 2 * MAP_PAD, smap.height + 2 * MAP_PAD))
smap_pad.paste(smap, (MAP_PAD, MAP_PAD))
fields = [Image.open(cfg["fields"].format(i + 1)).convert("RGB") for i in range(41)]
FW, FH = fields[0].width, fields[0].height  # 416x400: 13 columns of 32 px, odd ones 16 px lower
CW = FW // 13
mask = Image.new("L", (FW, FH))
md = ImageDraw.Draw(mask)
for c in range(13):
    md.rectangle([c * CW, (c % 2) * CW // 2, c * CW + CW - 1, (c % 2) * CW // 2 + FH - CW // 2 - 1], fill=255)
for f in fields:
    f.putalpha(mask)

# field slots in the joined map (field px): column -(q+r), row -r, every other column half a field down
pitch_x, pitch_y = FW, FH - CW // 2
cells = [(-(q + r), -r) for q, r in HEX]
slots = [(c * pitch_x, row * pitch_y - c * pitch_y // 2) for c, row in cells]
x0, y0 = min(x for x, _ in slots), min(y for _, y in slots)
slots = [(x - x0, y - y0) for x, y in slots]
JW, JH = max(x for x, _ in slots) + FW, max(y for _, y in slots) + FH
joined = Image.new("RGBA", (JW, JH))
for f, s in zip(fields, slots):
    joined.alpha_composite(f, s)
joined_small = joined.resize((JW // 4, JH // 4), Image.BOX)  # what gets turned

# screen layout
map_s = min(W / smap.width, 1300 / smap.height)
SCY = min(H / 2, 1560 - smap.height * map_s / 2)  # screen y of the map centre
join_s = 1000 / JW
join_xy = ((W - JW * join_s) / 2, (H - JH * join_s) / 2)
card_w = 44  # field width while it sits on its province

font_big = ImageFont.truetype(FONT, 86, index=0)
font_mid = ImageFont.truetype(FONT, 60, index=0)
font_say = ImageFont.truetype(FONT, 50, index=0)
WIN = (30, 1590, 1050, 1880)  # narrator window
face = Image.open(cfg["face"]).convert("RGB")
face = face.resize((face.width * (240 // face.height),) * 1 + (face.height * (240 // face.height),), Image.NEAREST)


def narrator(frame, ld, a):
    """KOEI-style message window: navy box, white frame, portrait on the left."""
    dy = round(80 * (1 - a))
    win = Image.new("RGBA", (W, H))
    wd = ImageDraw.Draw(win)
    wd.rectangle((WIN[0], WIN[1] + dy, WIN[2], WIN[3] + dy), fill=(0, 0, 120, int(235 * a)), outline=(255, 255, 255, int(255 * a)), width=6)
    frame.alpha_composite(win)
    f = face.copy().convert("RGBA")
    f.putalpha(int(255 * a))
    fx, fy = WIN[0] + 30, WIN[1] + 20 + dy
    frame.alpha_composite(f, (fx, fy))
    ImageDraw.Draw(frame).rectangle([fx - 3, fy - 3, fx + face.width + 2, fy + face.height + 2],
                                    outline=(255, 255, 255, int(255 * a)), width=3)


def text(dr, lines, y, font, alpha=1.0):
    fill = (255, 255, 255, int(255 * alpha))
    stroke = (0, 0, 0, int(255 * alpha))
    for line in lines:
        dr.text((W / 2, y), line, font=font, fill=fill, anchor="mm", stroke_width=6, stroke_fill=stroke)
        y += font.size * 1.25


def map_cam(t):
    """Strategic map camera: (centre in map px, scale)."""
    centre, s = (smap.width / 2, smap.height / 2), map_s
    focus = cfg["labels"][cfg["focus"] - 1]
    k = ease(phase(t, 2.6, 4.4)) - ease(phase(t, 5.8, 7.2))
    zoom = map_s * 6
    if t < 0:  # still settling in from the dissolve
        return centre, map_s * lerp(1.0, 1.12, ease(-t / (XF + SETTLE)))
    return (lerp(centre[0], focus[0], k), lerp(centre[1], focus[1], k)), map_s * (zoom / map_s) ** k


def to_screen(p, cam):
    (cx, cy), s = cam
    return W / 2 + (p[0] - cx) * s, SCY + (p[1] - cy) * s


def draw_map(frame, cam, alpha):
    (cx, cy), s = cam
    box = (cx - W / 2 / s, cy - SCY / s, cx + W / 2 / s, cy + (H - SCY) / s)
    m = smap_pad.resize((W, H), Image.NEAREST, box=tuple(v + MAP_PAD for v in box))
    inside = Image.new("L", (W, H))
    tl, br = to_screen((0, 0), cam), to_screen((smap.width, smap.height), cam)
    ImageDraw.Draw(inside).rectangle([tl[0], tl[1], br[0] - 1, br[1] - 1], fill=int(255 * alpha))
    frame.paste(m, (0, 0), inside)


def paste_field(frame, i, cx, cy, w, alpha=1.0):
    h = w * FH / FW
    if w < 2:
        return
    im = fields[i].resize((max(1, round(w)), max(1, round(h))), Image.NEAREST if w >= FW else Image.BOX)
    if alpha < 1:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(im, (round(cx - w / 2), round(cy - h / 2)))


def leave_order():
    if cfg["order"] == "number":
        return list(range(41))
    fx, fy = cfg["labels"][cfg["focus"] - 1]
    if cfg["order"] == "radial":  # rings outward from the opened province
        return sorted(range(41), key=lambda i: math.dist(cfg["labels"][i], (fx, fy)))
    if cfg["order"] == "north":  # north to south
        return sorted(range(41), key=lambda i: cfg["labels"][i][1])
    raise ValueError(cfg["order"])


ORDER = leave_order()
T_POP, T_FLY, T_JOINED, T_TURN, T_TURNED, T_ASK, T_END = 7.4, 9.0, 12.2, 14.0, 16.0, 17.0, 24.0


turned = joined_small.rotate(-30, Image.BICUBIC, expand=True)
TEASER = 2.2  # blurred hint, the last XF seconds dissolve into the map
XF = 0.9
SETTLE = 0.9  # map alone before the narrator shows up
MAIN0 = TEASER - XF + SETTLE  # video time of main_frame(0)
TOTAL = MAIN0 + T_END
MUSIC = "/Users/user/works/kaodata/posts/reel/out/theme-sangokushi.wav"


def frame_at(t):
    if t < TEASER - XF:
        return teaser(t)
    main = main_frame(t - MAIN0)
    if t < TEASER:
        return Image.blend(teaser(t), main, ease((t - (TEASER - XF)) / XF))
    return main


def teaser(t):
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    s = 1040 / turned.width * lerp(1.25, 1.0, ease(t / TEASER))
    im = turned.resize((round(turned.width * s), round(turned.height * s)), Image.BICUBIC)
    frame.alpha_composite(im, (round(W / 2 - im.width / 2), round(H / 2 - im.height / 2)))
    frame = frame.filter(ImageFilter.GaussianBlur(lerp(28, 12, ease(t / TEASER))))  # a hint, not the answer
    layer = Image.new("RGBA", (W, H))
    text(ImageDraw.Draw(layer), cfg["hook"], 330, font_big, min(1.0, t / 0.2))
    frame.alpha_composite(layer)
    return frame.convert("RGB")


def main_frame(t):
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dr = ImageDraw.Draw(frame)
    focus = cfg["focus"] - 1
    if t < T_FLY + 2.0:
        cam = map_cam(t)
        draw_map(frame, cam, 1 - ease(phase(t, T_FLY, T_FLY + 1.5)))
        # the focus province opens into its battlefield and closes back to a card
        k_open = ease(phase(t, 3.8, 4.6)) - ease(phase(t, 5.8, 7.0))
        if 3.8 <= t < T_POP:
            px, py = to_screen(cfg["labels"][focus], cam)
            w = lerp(card_w * cam[1] / map_s, W, k_open)
            paste_field(frame, focus, lerp(px, W / 2, k_open), lerp(py, SCY, k_open), w,
                        min(1.0, phase(t, 3.8, 4.1) * 1.0) if t < 5 else 1.0)
    # all fields pop out of their provinces, then fly to their slots
    if t >= T_POP:
        cam = map_cam(t)
        for n, i in enumerate(ORDER):
            start = T_POP + 1.2 * n / 41
            pop = ease_out_back(phase(t, start, start + 0.35))
            fly_start = T_FLY + 1.6 * n / 41
            k = ease(phase(t, fly_start, fly_start + 1.4))
            if pop <= 0 and i != focus:
                continue
            if i == focus:
                pop = 1.0
            sx, sy = to_screen(cfg["labels"][i], cam)
            ex, ey = (join_xy[0] + (slots[i][0] + FW / 2) * join_s, join_xy[1] + (slots[i][1] + FH / 2) * join_s)
            w = lerp(card_w * pop, FW * join_s, k)
            if t < T_JOINED:
                paste_field(frame, i, lerp(sx, ex, k), lerp(sy, ey, k), w)
    if t >= T_JOINED:
        turn = 30 * ease(phase(t, T_TURN, T_TURNED))
        im = joined_small.rotate(-turn, Image.BICUBIC, expand=True)
        s0 = join_s * 4
        s1 = 1040 / turned.width
        s = lerp(s0, s1, ease(phase(t, T_TURN, T_TURNED)))
        im = im.resize((round(im.width * s), round(im.height * s)), Image.BICUBIC if s > 1 else Image.BOX)
        lift = -120 * ease(phase(t, T_TURNED - 0.3, T_TURNED + 0.5))
        frame.alpha_composite(im, (round(W / 2 - im.width / 2), round(H / 2 - im.height / 2 - lift)))
    a = ease(phase(t, T_TURNED - 0.3, T_TURNED + 0.5))
    if a > 0:
        k = min(860 / smap.width, 560 / smap.height)
        m = smap.resize((round(smap.width * k), round(smap.height * k)), Image.NEAREST).convert("RGBA")
        cmp_w = m.width
        m.putalpha(int(255 * a))
        if cfg["cmp_from"] == "right":
            frame.alpha_composite(m, ((W - cmp_w) // 2 + round(W * (1 - a)), 110))
        elif cfg["cmp_from"] == "left":
            frame.alpha_composite(m, ((W - cmp_w) // 2 - round(W * (1 - a)), 110))
        else:
            frame.alpha_composite(m, ((W - cmp_w) // 2, 110 - round(40 * (1 - a))))
    # captions: the narrator's window, one line set per beat
    layer = Image.new("RGBA", (W, H))
    ld = ImageDraw.Draw(layer)
    say = cfg["say"]
    beats = [(0.4, 2.6, say["intro"]), (4.4, 6.8, say["field"]), (T_FLY, T_TURN - 0.2, say["join"]),
             (T_TURN, T_ASK - 0.1, say["turn"]), (T_ASK, 1e9, say["ask"])]
    box = ease(phase(t, 0.0, 0.5))
    if box > 0:
        narrator(frame, ld, box)
    for a0, a1, lines in beats:
        a = ease(phase(t, a0, a0 + 0.3)) - ease(phase(t, a1 - 0.3, a1))
        if a > 0:
            y = WIN[1] + (WIN[3] - WIN[1]) / 2 - font_say.size * 1.3 * (len(lines) - 1) / 2
            for line in lines:
                ld.text((WIN[0] + face.width + 70, y), line, font=font_say, fill=(255, 255, 255, int(255 * a)), anchor="lm")
                y += font_say.size * 1.3
    frame.alpha_composite(layer)
    return frame.convert("RGB")


if __name__ == "__main__":
    if len(sys.argv) > 3:  # preview frames: reel.py fc out.png t1 t2 ...
        ims = [frame_at(float(x)).resize((270, 480), Image.BOX) for x in sys.argv[3:]]
        strip = Image.new("RGB", (270 * len(ims), 480))
        for k, im in enumerate(ims):
            strip.paste(im, (270 * k, 0))
        strip.save(out)
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", MUSIC,
                           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                           "-af", f"afade=t=out:st={TOTAL - 1.5}:d=1.5", "-c:a", "aac", "-b:a", "192k",
                           "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    for n in range(int(TOTAL * FPS)):
        ff.stdin.write(frame_at(n / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
