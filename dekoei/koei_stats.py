"""Officer stats of the KOEI series other than 三國志 and 信長の野望 (ジンギスカン, 英傑傳, 大航海時代, 水滸伝,
源平合戦, 項劉記, ランペルール, 維新の嵐). Every loader returns rows (slot, name, *values) in the order of its <GAME>_STATS
labels; the evidence of each field is in the game's notes/<game>.md「能力」."""
import fnmatch
import glob
import os
import struct
import unicodedata

import click

import genpei
import koei_games as k
import pklite
import sango
from koei_person import LEMPEPerson
from ls11 import ls11_decode_parts
from san3 import unpack_x68_sndata

##############################################################################
# ジンギスカン (GENGHIS): MDATA.CIM / SDATA.CIM (X68000 MDATA.DAT / SDATA.DAT)
#
# PC-88 / PC-98: name 15 bytes, +15 年齢 (at the scenario's base year 1175 / 1205), +16 six u16 統率力 判断力
# 企画力 説得力 体力 武力, +28 一族区分 (0 = 一族); PC-98 MAIN.EXE 0x1146D prints the window from the same layout.
# DOS (English / Chinese): the same fields 10 bytes later (20-byte name + 5). X68000: the numbers are big-endian
# longs, 一族区分 at +40. Generals: +16 基本能力値, +18 血縁値 (X68000 +20); sons: +16 基本能力値, +18 1 = son
# (X68000 +20). The values are the same on all five releases.
GENGHIS_STATS = ("統率力", "判断力", "企画力", "説得力", "体力", "武力")
GENGHIS_GENERAL_STATS = ("基本能力値", "血縁値")
GENGHIS_SON_STATS = ("基本能力値", "男子")
GENGHIS_START_YEAR = {"MDATA": 1175, "SDATA": 1205}  # +15 is the age in this year (MAIN.EXE 0xDDB5)


def _genghis_layout(platform):
    """(tables, shift, number size, 一族区分 offset, general 血縁値 offset) of one platform."""
    if platform == "x68":
        return k.GENGHIS_X68_TABLES, 0, 4, 40, 20
    if platform == "dos":
        return k.GENGHIS_TABLES, 10, 2, 38, 28
    return (k.GENGHIS_PC98_TABLES if platform == "pc98" else k.GENGHIS_PC88_TABLES), 0, 2, 28, 18


def _genghis_records(cim: bytes, platform, kind):
    tables, shift, *_ = _genghis_layout(platform)
    off, groups, gsize, n, size, face = tables[kind]
    for g in range(groups):
        for i in range(n):
            o = off + g * gsize + i * size
            rec = cim[o:o + size]
            if not rec[0]:
                continue
            if platform == "dos":
                name = k.koei_tw_name(rec[:20])
            else:
                raw = rec[:15].split(b"\0")[0]
                name = unicodedata.normalize("NFKC", raw.decode("cp932")).replace(" ", "")
            yield f"{g}.{i}" if groups > 1 else str(i), name, rec


def _num(rec, o, size):
    return int.from_bytes(rec[o:o + size], "big" if size == 4 else "little")


def load_genghis_stats(cim: bytes, platform="pc98") -> list[tuple]:
    """(slot, name, 年齢, 統率力, 判断力, 企画力, 説得力, 体力, 武力, 一族) of the rulers ("ruler") and heirs
    ("family") of one MDATA / SDATA file; platform is pc88, pc98, dos (English or Chinese) or x68."""
    _, shift, step, clan, _ = _genghis_layout(platform)
    rows = []
    for kind in ("ruler", "family"):
        for slot, name, rec in _genghis_records(cim, platform, kind):
            rows.append((f"{kind} {slot}", name, rec[15 + shift],
                         *(_num(rec, 16 + shift + j * step, step) for j in range(6)), rec[clan] == 0))
    return rows


def load_genghis_general_stats(cim: bytes, platform="pc98") -> list[tuple]:
    """(slot, name, 年齢, 基本能力値, 血縁値 or 男子) of the generals ("general") and children ("son")."""
    _, shift, step, _, blood = _genghis_layout(platform)
    rows = []
    for slot, name, rec in _genghis_records(cim, platform, "general"):
        rows.append((f"general {slot}", name, rec[15 + shift], _num(rec, 16 + shift, step), rec[blood]))
    for slot, name, rec in _genghis_records(cim, platform, "son"):
        rows.append((f"son {slot}", name, rec[15 + shift], _num(rec, 16 + shift, step),
                     (rec[23] if step == 4 else rec[18 + shift]) == 1))  # PC-88: a byte before the face code
    return rows


##############################################################################
# 蒼き狼と白き牝鹿・元朝秘史 (GENCHOU): GENDATA<s>.DAT / USDATA<s>.DAT men (27 bytes; X68000 30)
#
# +17 所在国 (FF = 未登場), +18 所属勢力, +19 体力 (low nibble now, high nibble max), +20 政治力 (bits 0-2) 戦闘力
# (bits 4-6), +21 指揮力 (bits 0-2) 魅力 (bits 4-6), each 0-4 = Ｅ–Ａ, +22 年齢, +23 three bit fields, +24 bits 0-1
# 身分 (0 将軍 1 政治顧問 2 領主, 3 = ruler), bit 6 重病; PC-98 MAIN.EXE accessors 0:6808-6874, window 0x2B3C0.
# Same offsets on PC-88, PC-98, X68000 and DOS (the X68000 adds 3 zero bytes before the face code).
GENCHOU_STATS = ("政治力", "戦闘力", "指揮力", "魅力", "体力", "年齢")
GENCHOU_GRADES = "ＥＤＣＢＡ＊"  # MAIN.EXE DS:0x4CB0


def _genchou_man(rec):
    grade = GENCHOU_GRADES
    return (grade[rec[20] & 7], grade[rec[20] >> 4 & 7], grade[rec[21] & 7], grade[rec[21] >> 4 & 7],
            rec[19] >> 4, rec[22])


def load_genchou_stats(game_dir, x68=False, pc98=False, dos=False) -> list[tuple]:
    """(scenario, table, name, 政治力, 戦闘力, 指揮力, 魅力 (Ｅ–Ａ), 体力 (max), 年齢) of every man in GENDATA1-4
    ("GENDATA") and the USDATA arrivals ("USDATA <block>"); flags as load_genchou_pc88_people."""
    def read(file):
        with open(os.path.join(game_dir, file), "rb") as f:
            data = f.read()
        return unpack_x68_sndata(data) if x68 and data[0] != 0xFF else data

    def name(rec):
        raw = rec[:17].split(b"\0")[0]
        if dos:
            return k.koei_tw_name(raw + b"\0" * (len(raw) % 2)).strip()
        return unicodedata.normalize("NFKC", raw.decode("cp932")).strip()

    if x68:
        men, block, first_block = k.GENCHOU_X68_MEN, k.GENCHOU_X68_BLOCK, 2
    else:
        men, block, first_block = (k.GENCHOU_PC98_MEN if pc98 or dos else k.GENCHOU_PC88_MEN), k.GENCHOU_PC88_BLOCK, 0
    first, size, count = men
    rows = []
    for sc in range(1, 5):
        gen, us = read(f"GENDATA{sc}.DAT"), read(f"USDATA{sc}.DAT")
        for i in range(count):
            rec = gen[first + i * size:][:size]
            if name(rec) and name(rec) not in (k.GENCHOU_PC88_PLACEHOLDER, k.GENCHOU_DOS_PLACEHOLDER):
                rows.append((sc, "GENDATA", name(rec), *_genchou_man(rec)))
        for b in range(first_block, len(us) - block + 1, block):
            for i in range(8):
                rec = us[b + i * size:][:size]
                if name(rec):
                    rows.append((sc, f"USDATA {b // block}", name(rec), *_genchou_man(rec)))
    return rows


##############################################################################
# 蒼狼與白鹿IV (GENGHIS4 / GENGHIS4PK, Win, Chinese): SCEDAT*.CK men, offsets from the name
# (CKW95.EXE 0x495C90 copies them into the person object):
# +17 nation, +18 city (0x50 = none), +19 u16 father, +21 u16 grandfather, +27 u16 lord (500 = none), +23 u16 生年,
# +25 u16 任官年 (0 = not yet), +29 政治 +30 戰鬥 +31 智謀 +32 忠誠 (u8, object +0x2a-0x2d, switch at 0x43F0D0),
# +33 (always 0; object +0x2e), +34..+37 兵種 適性 0-5, +38 u16 特技 bits 0-11, +46 u16 登場年, +48 登場 city.
GENGHIS4_STATS = ("政治", "戰鬥", "智謀", "忠誠", "步兵", "弓兵", "騎兵", "水軍", "生年")
# CKW95.EXE 0x5D8D20 (file 0x1D7520): 内政特技 bits 0-5, 戰鬥特技 bits 6-11
GENGHIS4_SKILLS = ("農業", "商業", "建設", "文化", "外交", "錄用", "機動", "突擊", "連射", "火攻", "攻城", "伏兵")


def load_genghis4_win_stats(path) -> list[tuple]:
    """(id, name, 政治, 戰鬥, 智謀, 忠誠, 步兵, 弓兵, 騎兵, 水軍, 生年, 特技) of the men of one SCEDAT*.CK
    (PK and 無印 have the same layout); 特技 is the list of skill names."""
    with open(path, "rb") as f:
        data = f.read()

    def male(o):
        return data[o + 40:o + 42] == b"\x11\x11"

    o = next(o for o in range(len(data)) if all(male(o + j * 51) for j in range(10)))
    rows = []
    while male(o):
        skills, = struct.unpack_from("<H", data, o + 38)
        rows.append((struct.unpack_from("<H", data, o - 2)[0], data[o:o + 17].split(b"\0")[0].decode("big5"),
                     *data[o + 29:o + 33], *data[o + 34:o + 38], struct.unpack_from("<H", data, o + 23)[0],
                     [s for b, s in enumerate(GENGHIS4_SKILLS) if skills >> b & 1]))
        o += 51
    return rows


##############################################################################
# 英傑傳 series

# 三國志英傑傳 (DOS, PC-98) BAKDATA.R3. Person record (21 bytes from 0x1100, k.EIKETSU_DOS_PERSONS):
# +16 -> person +5 (?), +17 -> +0x18 統率 (read by the 防禦力 formula, MAIN.EXE load image 0x13098),
# +18 -> +0x19 武力 (攻擊力 formula 0x12F6A), +19 -> +0x1A 知力, +20 -> +0x1B flags (init at 0x13542).
# A second table of 384 x 18 bytes at 0x3080 holds the start state: +0 0x80 | faction, +4 士氣, +5 u16 兵力,
# +7 兵種, +8 等級, +10..+17 items (BAKDATA 0xD00 + 16 * id). The window shows 武力 知力 統率 (0x25DBC).
EIKETSU_DOS_STATS = ["武力", "知力", "統率", "兵種", "等級", "兵力", "士氣", "道具"]
EIKETSU_DOS_STATE = (0x3080, 18)
EIKETSU_DOS_ITEMS = (0xD00, 16, 64)
# MAIN.EXE DGROUP string list (DOS 0x37BF8, PC-98 0x358B0), in class-code order
EIKETSU_DOS_CLASSES = ("短兵", "長兵", "戰車", "弓兵", "連弩兵", "發石車", "輕騎兵", "重騎兵", "近衛隊", "山賊", "惡賊",
                       "義賊", "軍樂隊", "猛獸兵團", "武術家隊", "妖術師", "異民族", "民眾", "運輸隊")
EIKETSU_PC98_CLASSES = ("短兵", "長兵", "戦車", "弓兵", "連弩兵", "発石車", "軽騎兵", "重騎兵", "親衛隊", "山賊", "凶賊",
                        "義賊", "軍楽隊", "猛獣使い", "武道家隊", "妖術使い", "異民族", "民衆", "輸送隊")


def _name(raw: bytes, enc: str) -> str:
    return raw.split(b"\0")[0].decode(enc, "replace").strip()


def _pc98_text(raw: bytes) -> str:
    """Shift-JIS with KOEI gaiji EB xx (k.EIKETSU_PC98_GAIJI; unknown ones become 〓)."""
    raw, out, i = raw.split(b"\0")[0], [], 0
    while i < len(raw):
        if raw[i] == 0xEB and i + 1 < len(raw):
            out.append(k.EIKETSU_PC98_GAIJI.get(raw[i + 1], "〓"))
            i += 2
        elif raw[i] >= 0x81 and i + 1 < len(raw) and not 0xA0 <= raw[i] <= 0xDF:
            out.append(raw[i:i + 2].decode("cp932", "replace"))
            i += 2
        else:
            out.append(raw[i:i + 1].decode("cp932", "replace"))
            i += 1
    return "".join(out).strip()


def load_eiketsu_dos_stats(bakdata, pc98=False) -> list[tuple]:
    """(slot, name, 武力, 知力, 統率, 兵種, 等級, 兵力, 士氣, items) of every BAKDATA.R3 person record."""
    with open(bakdata, "rb") as f:
        data = f.read()
    names = (k.load_eiketsu_pc98_persons if pc98 else k.load_eiketsu_dos_persons)(bakdata)
    classes = EIKETSU_PC98_CLASSES if pc98 else EIKETSU_DOS_CLASSES
    start, _, size = k.EIKETSU_DOS_PERSONS
    st, st_size = EIKETSU_DOS_STATE
    it, it_size, _ = EIKETSU_DOS_ITEMS
    rows = []
    for slot, (name, _) in enumerate(names):
        r = data[start + slot * size:][:size]
        s = data[st + slot * st_size:][:st_size]
        items = "/".join(_pc98_text(data[it + i * it_size:][:12]) if pc98 else _name(data[it + i * it_size:][:12], "big5")
                         for i in s[10:] if i != 0xFF)
        rows.append((slot, name, r[18], r[19], r[17], classes[s[7]] if s[7] < len(classes) else s[7], s[8],
                     s[5] | s[6] << 8, s[4], items))
    return rows


# 三國志孔明傳 (Win) BAKDATA.E2: after the 512 17-byte records (sango.KOUMEI_PERSONS) come 512 x 26 bytes at 0x3AF0,
# one per record: +1 武力, +2 統御力, +3 智力 (order from the values), +4 u16 耐久力?, +6 策略值?, +8 兵種, +9 等級,
# +11..+25 items (BAKDATA 0x900 + 16 * id). EKD2.EXE reads the table (0x3400 bytes at 0x3AF0) but the use is not traced.
KOUMEI_WIN_STATS = ["武力", "智力", "統御力", "耐久力", "策略值", "兵種", "等級", "道具"]
KOUMEI_WIN_STATE = (0x3AF0, 26, 512)
KOUMEI_WIN_ITEMS = (0x900, 16)
# EKD2.EXE string list from 0x11F36, in class-code order
KOUMEI_WIN_CLASSES = ("短兵", "長兵", "近衛兵", "弓兵", "弩兵", "連弩兵", "輕騎兵", "重騎兵", "親衛隊", "輕戰車", "重戰車",
                      "大戰車", "小砲車", "大砲車", "霹靂車", "弓騎兵", "弩騎兵", "連弩騎兵", "軍師", "名軍師", "大軍師", "山賊",
                      "義賊", "武術家", "大武術家", "虎兵團", "運糧隊", "物資隊", "軍樂隊", "南蠻兵", "南蠻騎兵", "皇帝", "都督",
                      "藤甲兵", "羌族兵", "象兵團", "蛇兵團", "幻術師", "北荻兵", "巨艦", "戰艦", "火船")


def load_koumei_win_stats(bakdata) -> list[tuple]:
    """(slot, name, 武力, 智力, 統御力, 耐久力?, 策略值?, 兵種, 等級, items) of BAKDATA.E2 records 0-511."""
    with open(bakdata, "rb") as f:
        data = f.read()
    start, size, count = KOUMEI_WIN_STATE
    it, it_size = KOUMEI_WIN_ITEMS
    rows = []
    for slot, (name, _) in enumerate(sango.load_koumei_persons(bakdata)[:count]):
        s = data[start + slot * size:][:size]
        items = "/".join(_name(data[it + i * it_size:][:12], "big5") for i in s[11:] if i != 0xFF)
        cls = KOUMEI_WIN_CLASSES[s[8]] if s[8] < len(KOUMEI_WIN_CLASSES) else s[8]
        rows.append((slot, name, s[1], s[3], s[2], s[4] | s[5] << 8, s[6], cls, s[9], items))
    return rows


def _parts(path):
    with open(path, "rb") as f:
        return ls11_decode_parts(f.read())


def _table(part: bytes, size: int, width: int) -> list[str]:
    return [_name(part[o:o + width], "big5") for o in range(0, len(part) - size + 1, size)]


# 毛利元就傳 (Win) DATA.E3 part 0, 54-byte records (k.load_eiketsu3_win_persons); 毛利元就傳_Gr.EXE 0x402922 copies
# +33..+36 -> person +0x28..+0x2B, +37 u16 -> +8 (max 1000), +39..+41 -> +0x2C..+0x2E, +42 -> +0x31, +43 -> +0x32
# (min 1), +45 -> +0x34 (equipped slot), +46..+53 -> 8 items (DATA.E3 part 1, 33 bytes). Labels and their order are
# the EXE's status list at 0x47D8C0 (攻擊力 防禦力 智力 運氣 耐久力 技能值 命中率 敏捷 等級 經驗值).
EIKETSU3_WIN_STATS = ["攻擊力", "防禦力", "智力", "運氣", "耐久力", "技能值", "命中率", "敏捷", "兵種", "等級", "道具"]
# EXE strings from 0x47D910, in class-code order
EIKETSU3_WIN_CLASSES = ("豪族", "大名", "槍兵", "槍大將", "弓兵", "弓大將", "騎兵", "騎大將", "弓騎兵", "弓騎大將", "步槍兵",
                        "步槍大將", "砲兵", "砲大將", "浪人", "劍豪", "下忍", "上忍", "女忍者", "女忍者頭", "參謀", "軍師", "強盜",
                        "義賊", "海盜", "海盜頭", "僧兵", "修練行者", "小運輸", "大運輸", "鼓笛隊", "軍樂隊")


def load_eiketsu3_win_stats(path) -> list[tuple]:
    """(slot, name, 攻擊力, 防禦力, 智力, 運氣, 耐久力, 技能值, 命中率, 敏捷, 兵種, 等級, items) of DATA.E3 part 0."""
    parts = _parts(path)
    items = _table(parts[1], 33, 13)
    p, size = parts[0], k.EIKETSU3_WIN_PERSON
    rows = []
    for slot, o in enumerate(range(0, len(p) - size + 1, size)):
        r = p[o:o + size]
        cls = EIKETSU3_WIN_CLASSES[r[42]] if r[42] < len(EIKETSU3_WIN_CLASSES) else r[42]
        rows.append((slot, _name(r[:13], "big5"), *r[33:37], r[37] | r[38] << 8, *r[39:42], cls, r[43],
                     "/".join(items[i] for i in r[46:54] if i != 0xFF)))
    return rows


# 織田信長傳 (Win) DATA.E4 part 0, 77-byte records (k.load_eiketsu4_win_persons); Ekd4.EXE 0x403190 copies
# +33..+40 -> person +0x4E (8 得意技, DATA.E4 part 5), +41..+48 -> +0x56 (8 特性, EXE list below),
# +49..+55 -> +0x5E (7 bytes, unknown), +56..+59 -> +0x28..+0x2B, +60 u16 -> +8 (max 1000), +62 -> +0x2C,
# +63 -> +0x2E, +64 -> +0x2F, +65 -> +0x32 兵種 (part 3), +66 -> +0x33 等級 (min 1), +69..+76 -> 8 items (part 1).
# Labels: EXE 0x476BE0 (攻擊 防禦 智力 運氣 耐久 技能 命中 敏捷 等級 經驗).
EIKETSU4_WIN_STATS = ["攻擊力", "防禦力", "智力", "運氣", "耐久力", "技能值", "命中力", "敏捷", "兵種", "等級", "得意技",
                      "特性", "道具"]
# Ekd4.EXE strings from 0x477688, in id order (the list is read as 特性 ids, see report)
EIKETSU4_WIN_TRAITS = ("草原戰術", "山岳戰術", "森林戰術", "海戰戰術", "渡河戰術", "城塞戰術", "巷戰戰術", "鐵壁", "後方支援",
                       "攻擊指南", "吆喝", "休養", "集中", "鍛鍊", "痊癒", "解禁", "鎮靜", "治癒力", "充實", "身手", "遠見",
                       "南蠻砲術", "放棄", "撥開", "彈道眼", "煙霧彈", "幸運", "壞天專長", "持久戰術", "奮鬥", "身輕", "保留")


def load_eiketsu4_win_stats(path) -> list[tuple]:
    """(slot, name, 攻擊力, 防禦力, 智力, 運氣, 耐久力, 技能值, 命中力, 敏捷, 兵種, 等級, 得意技, 特性, items)."""
    parts = _parts(path)
    items, classes, arts = _table(parts[1], 51, 20), _table(parts[3], 39, 12), _table(parts[5], 17, 17)
    p, size = parts[0], k.EIKETSU4_WIN_PERSON
    rows = []
    for slot, o in enumerate(range(0, len(p) - size + 1, size)):
        r = p[o:o + size]

        def names(ids, table):
            return "/".join(table[i] if i < len(table) else str(i) for i in ids if i != 0xFF)
        rows.append((slot, _name(r[:12], "big5"), *r[56:60], r[60] | r[61] << 8, *r[62:65],
                     classes[r[65]] if r[65] < len(classes) else r[65], r[66], names(r[33:41], arts),
                     names(r[41:49], EIKETSU4_WIN_TRAITS), names(r[69:77], items)))
    return rows


# 曹操傳 (Win) DATA.E5 part 0, 32-byte records (k.load_eiketsu5_win_persons); EKD5.EXE 0x408BD3 copies
# +15 -> person +2 (own person number), +18..+22 -> +0x15..+0x19 (and current copies +0x21..), +23 u16 -> +0x1C
# (max 500), +25 -> +0x20 (max 250), +26 -> +0x2B, +27 -> +0x2C (min 1), +29/+30 -> +0x2E/+0x31 (item, level 1, exp 0),
# +31 -> +0x34. The getter at 0x406D77 indexes them 0-6 as one array. Stat names: EXE has 武力 智力 統率力 敏捷 運氣
# (0x48A258, item messages); the order below follows the values (郭嘉 third 49, 呂布 third 6).
EIKETSU5_WIN_STATS = ["武力", "統率", "智力", "敏捷", "運氣", "HP", "MP", "兵種", "等級", "武器", "護具", "輔助"]
# EKD5.EXE strings from 0x489BA4 (file 0x88FA4), in class-code order (3 tiers per line, then single classes)
EIKETSU5_WIN_CLASSES = ("群雄", "英雄", "霸王", "輕步兵", "重步兵", "近衛兵", "弓兵", "弩兵", "連弩兵", "輕騎兵", "重騎兵",
                        "親衛隊", "弓騎兵", "弩騎兵", "連弩騎兵", "輕砲車", "重砲車", "霹靂車", "武道家", "拳士", "拳聖", "賊兵",
                        "義賊", "豪傑", "策士", "參謀", "軍師", "風水士", "方術士", "仙術士", "道士", "幻術士", "妖術士",
                        "騎馬策士", "騎馬參謀", "騎馬軍師", "舞孃", "舞伎", "巫女", "西涼騎兵", "黃巾賊", "海盜", "馴熊師",
                        "馴虎師", "都督", "咒術士", "仙人", "輜重隊", "糧秣隊", "木人", "土偶", "皇帝", "百姓")


def load_eiketsu5_win_stats(path) -> list[tuple]:
    """(slot, name, 武力, 統率, 智力, 敏捷, 運氣, HP, MP, 兵種, 等級, 武器, 護具, 輔助) of DATA.E5 part 0."""
    parts = _parts(path)
    items = _table(parts[1], 25, 12)
    p, size = parts[0], k.EIKETSU5_WIN_PERSON
    rows = []
    for slot, o in enumerate(range(0, len(p) - size + 1, size)):
        r = p[o:o + size]
        cls = EIKETSU5_WIN_CLASSES[r[26]] if r[26] < len(EIKETSU5_WIN_CLASSES) else r[26]
        rows.append((slot, _name(r[:13], "big5"), *r[18:23], r[23] | r[24] << 8, r[25], cls, r[27],
                     *(items[i] if i < len(items) else "" for i in r[29:32])))
    return rows


##############################################################################
# 大航海時代 (KOUKAI): SHINARIO.CIM

# PC-98 MAIN.EXE 0x311CE (image) prints the 仲間の情報 window: the man record (0x332:0xD4, DS:0x942 + id * 20)
# gives +0xF 戦闘Lv and +0x10 航海Lv; a second table (0x332:0xE2, DS:0x13F0 + id * 10) gives +0 年齢,
# +1..+5 統率力 判断力 知力 勇気 強靭さ, +6 u16 戦闘経験, +8 u16 航海経験 (format strings at file 0x4EF08).
# SHINARIO.CIM is loaded at DS:0x42, so the stat table is at file 0x13AE; it has 21 records (men 0-20 = the
# player レオン and the 20 mates); men 21-40 (rival admirals) have no stat record there.
# English DOS main.exe calls the five Authority, Judgement, Intellect, Courage, Strength.
KOUKAI_STATS = ("年齢", "統率力", "判断力", "知力", "勇気", "強靭さ", "戦闘Lv", "航海Lv", "国籍")
KOUKAI_STAT_TABLE = {"dos": 0x13CE, "pc98": 0x13AE, "pc88": 0x1320}  # pc88: found by content (same bytes)
KOUKAI_STAT_RECORDS = 21
KOUKAI_STAT_SIZE = 10
KOUKAI_MEN_OFFSET = {"dos": k.KOUKAI_MEN[0], "pc98": k.KOUKAI_MEN[0] + k.KOUKAI_PC98_SHIFT,
                     "pc88": k.KOUKAI_MEN[0] + k.KOUKAI_PC88_SHIFT}
# nation = high nibble of man record +0x13 (notes/koukai.md); PC-98 MAIN.EXE spelling
KOUKAI_NATIONS = ("ポルトガル", "イスパニア", "イスラム", "海賊")


def load_koukai_stats(shinario, platform="dos") -> list[tuple]:
    """(slot, name, 年齢, 統率力, 判断力, 知力, 勇気, 強靭さ, 戦闘Lv, 航海Lv, 国籍) of men 0-20;
    platform is dos (Chinese), pc98 or pc88."""
    if platform == "dos":
        men, _ = k.load_koukai_dos_people(shinario)
    else:
        men, _ = k.load_koukai_pc98_people(shinario, pc88=platform == "pc88")
    with open(shinario, "rb") as f:
        data = f.read()
    rows = []
    for slot in range(KOUKAI_STAT_RECORDS):
        s = data[KOUKAI_STAT_TABLE[platform] + slot * KOUKAI_STAT_SIZE:][:KOUKAI_STAT_SIZE]
        m = data[KOUKAI_MEN_OFFSET[platform] + slot * 20:][:20]
        rows.append((slot, men[slot][0], *s[:6], m[0xF], m[0x10], KOUKAI_NATIONS[m[0x13] >> 4]))
    return rows


##############################################################################
# 大航海時代II (KOUKAI2, PC-98): DATA1.LZW part 15, 120 mates x 50 bytes from 0x612

# MAIN.EXE image 0x1BC30 draws the mate window: +0x1C..+0x22 seven stats (label pointers DS:0x8C8), +0x2A 年齢,
# +0x24 航海Lv, +0x26 u16 航海経験, +0x25 戦闘Lv, +0x28 u16 戦闘経験, +0x31 low nibble 国籍 (DS:0x8B0),
# +0x30 技能 bits (skill i is set when byte & (0x10 >> i); labels DS:0x8BE), +0x2E 役職 (DS:0x8A2)
KOUKAI2_STATS = ("統率力", "航海術", "知識", "直感", "勇気", "剣技", "魅力", "年齢", "航海Lv", "航海経験",
                 "戦闘Lv", "戦闘経験", "国籍", "技能")
KOUKAI2_NATIONS = ("ポルトガル", "イスパニア", "オスマン帝国", "イギリス", "イタリア", "オランダ", "海賊")
KOUKAI2_SKILLS = ("測量", "地図作製", "砲術", "会計", "交渉")


def _skills(bits: int, names) -> str:
    return "／".join(n for i, n in enumerate(names) if bits & (0x10 >> i))


def _koukai2_values(r: bytes, base: int, nations, skills) -> tuple:
    """Values of one mate record; base is the offset of the first stat (II 28, 外伝 4)."""
    o = base
    return (*r[o:o + 7], r[o + 14], r[o + 8], int.from_bytes(r[o + 10:o + 12], "little"), r[o + 9],
            int.from_bytes(r[o + 12:o + 14], "little"), nations[r[o + 21] & 0xF], _skills(r[o + 20], skills))


def load_koukai2_pc98_stats(data1) -> list[tuple]:
    """(slot, name, *KOUKAI2_STATS) of every DATA1.LZW mate."""
    mates, _, _ = k.load_koukai2_pc98_people(data1)
    with open(data1, "rb") as f:
        data = k.ls11_decode_parts(f.read())[15]
    start, count, size = k.KOUKAI2_PC98_MATES
    return [(slot, mates[slot][0], *_koukai2_values(data[start + slot * size:][:size], 28, KOUKAI2_NATIONS,
                                                    KOUKAI2_SKILLS))
            for slot in range(count)]


##############################################################################
# 大航海時代外伝 (KOUKAIGD, Win, Chinese): koukaiGD.exe mate tables (27 bytes = II's record without the names)

# 0x446F60 draws the window: +0x12 年齢 (msg 0x382), +4..+10 seven stats (labels VA 0x45B0E0, 7-byte slots),
# +0xC 航海水平, +0xE 經驗, +0xD 戰鬥水平, +0x10 經驗, +0x19 low nibble 國籍 (VA 0x45B050), +0x18 技能 bits
# (VA 0x45B0B0), +0x16 職位 (VA 0x45AFC8)
KOUKAIGD_STATS = ("統御力", "航海術", "知識", "直覺", "勇氣", "劍術", "魅力", "年齡", "航海水平", "航海經驗",
                  "戰鬥水平", "戰鬥經驗", "國籍", "技能")
KOUKAIGD_NATIONS = ("葡萄牙", "西班牙", "奧斯曼帝國", "英國", "義大利", "荷蘭", "海盜")
KOUKAIGD_SKILLS = ("測量", "地圖製作", "砲術", "會計", "交涉")


def load_koukaigd_win_stats(exe) -> list[tuple]:
    """(table/slot, name, *KOUKAIGD_STATS) of both mate tables (0 = 米蘭塔's, 1 = 薩爾巴多爾's); empty and
    player slots are skipped, and table 1 only lists records that differ from table 0."""
    names = k.load_koukaigd_win_mates(exe)
    with open(exe, "rb") as f:
        data = f.read()
    rows, seen = [], {}
    for t, start in enumerate(k.KOUKAIGD_WIN_MATES):
        for slot in range(120):
            r = data[start + slot * 27:][:27]
            if names[t][slot][0] is None or seen.get(slot) == r:
                continue
            seen.setdefault(slot, r)
            rows.append((f"{t}/{slot}", names[t][slot][0], *_koukai2_values(r, 4, KOUKAIGD_NATIONS, KOUKAIGD_SKILLS)))
    return rows


##############################################################################
# 大航海時代III (KOUKAI3, Win, Chinese): CDS95.EXE person table (281 x 0xCC bytes of i32)

# 0x47EF00 copies a record into the runtime person (0x11C bytes): t+0x40..+0x54 - 1 -> r+0x20..+0x34 (six stats,
# label pointers VA 0x551FC8), t+0x60..+0x90 -> r+0x40.. (13 skills, VA 0x551F50), t+0x94..+0xC8 -> r+0x74.. (14
# languages, VA 0x551F88), t+0x24 -> r+0xAC 名聲, t+0x28 -> r+0xB0 惡名. The status window 0x42A7D2 prints
# r+0x20..+0x2C plus 1 as 體力 智力 武力 魅力, so the table values are the shown values.
KOUKAI3_WIN_ATTRS = ("體力", "智力", "武力", "魅力", "運氣", "信仰")
KOUKAI3_WIN_SKILLS = ("航海術", "運用術", "劍術", "砲術", "射擊術", "醫學", "辯論", "測量", "歷史學", "會計", "造船技術",
                      "神學", "科學")
KOUKAI3_WIN_LANGUAGES = ("西班牙語", "葡萄牙語", "羅曼語", "日耳曼語", "斯拉夫•希臘語", "阿拉伯語", "波斯語", "漢語",
                         "印地語", "維吾爾語", "非洲土語", "中南美土語", "東南亞土語", "東亞土語")
KOUKAI3_WIN_STATS = (*KOUKAI3_WIN_ATTRS, "名聲", "惡名", *KOUKAI3_WIN_SKILLS, *KOUKAI3_WIN_LANGUAGES)
KOUKAI3_WIN_PEOPLE = 246  # 246-280 are troops, tribes, fleets, sea monsters and empty records


def load_koukai3_win_stats(exe) -> list[tuple]:
    """(slot, name, *KOUKAI3_WIN_STATS) of person records 0-245."""
    persons = k.load_koukai3_win_persons(exe)
    with open(exe, "rb") as f:
        data = f.read()
    start, _, size = k.KOUKAI3_WIN_PERSONS
    base = k.koukai3_win_offset(start)
    rows = []
    for slot in range(KOUKAI3_WIN_PEOPLE):
        v = struct.unpack_from("<51i", data, base + slot * size)
        rows.append((slot, persons[slot][0], *v[16:22], v[9], v[10], *v[24:37], *v[37:51]))
    return rows


##############################################################################
# 大航海時代IV PK HD (KOUKAI4PK, Win): World?.dll person table (235 x 56 bytes)

# +0x20..+0x25: six u8. DK4HD_jp.exe has a label pointer table (file 0x6866B0) 体力 敏捷 魅力 知力 精神 運勢,
# followed by 生命力 統率力 操船術 測量術 会計術 剣闘術 命中力 説得力 謀略術 観察力 (the shown abilities, not in the
# record). That the six bytes follow the label order is not traced in code (🟡).
KOUKAI4_WIN_STATS = ("体力", "敏捷", "魅力", "知力", "精神", "運勢")


def load_koukai4_win_stats(path, first="ラファエル", encoding="cp932") -> list[tuple]:
    """(slot, 名・中間名・姓, *KOUKAI4_WIN_STATS) of the records 0-97 and 213 that have stats."""
    persons = k.load_koukai4_win_persons(path, first, encoding)
    with open(path, "rb") as f:
        data = f.read()
    # the table: same search as load_koukai4_win_persons
    pe, = struct.unpack_from("<I", data, 0x3C)
    sections, header = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    image, = struct.unpack_from("<Q", data, pe + 48)
    spans = [struct.unpack_from("<3I", data, pe + 24 + header + 40 * i + 12) for i in range(sections)]
    o = data.index(first.encode(encoding) + b"\0")
    va = next(image + rva + o - raw for rva, size, raw in spans if raw <= o < raw + size)
    table = data.index(struct.pack("<Q", va))
    rows = []
    for slot, (given, family, middle, _, _) in enumerate(persons):
        r = data[table + slot * k.KOUKAI4_WIN_PERSON:][:k.KOUKAI4_WIN_PERSON]
        if any(r[0x20:0x26]):
            sep = "‧" if encoding != "cp932" else "・"
            rows.append((slot, sep.join(n for n in (given, middle, family) if n), *r[0x20:0x26]))
    return rows


##############################################################################
# 水滸伝・天命の誓い. SUIDATA?.CIM person records P (MAIN.EXE PC-98: P = DS:0x44 + 0x16 * i = file 2 + 22 * i):
# +2 年齢, +3 勢力, +4 所在, +5 体力, +6 体力上限, +7..9 忠義 仁愛 勇気, +0xA..C 腕力 技量 知力,
# +0xD..F 腕力/技量/知力経験 (window shows "－" when the stat is 100), +0x10 忠誠度, +0x11 ?, +0x12 u16 人気,
# +0x14 小者, +0x15 bit 6 船, bits 0-5 身分 (MAIN.EXE 0x5B1A). The file stores P+2..P+0x15 (20 bytes):
# DOS / PC-98 from 4, stride 22; PC-88 from 1, stride 20; X68000 from 6, stride 26 (人気 big-endian at +18).
# Name record: PC-98 +18 / DOS +43 口調 (message set, MAIN.EXE 0x3CF2), PC-98 +19 / DOS +44 bit 7 男, bit 6 舵.

SUIKODEN_STATS = ("年齢", "体力", "腕力", "技量", "知力", "体力上限", "腕力経験", "技量経験", "知力経験",
                  "小者", "忠義", "仁愛", "勇気", "忠誠度", "人気", "身分", "性", "船", "舵", "口調")
# MAIN.EXE (PC-98) DS:0x35BC, 34 pointers
SUIKODEN_STATUS = ("寵臣 高官 官吏 好漢 首領 無頼漢 義兄 義弟 死亡 罪人 僧侶 漁師 人夫 医者 商人 居酒屋 職人 学者 長者 "
                   "若旦那 小娘 芸妓 猟師 力士 武芸者 旅商人 旅芸人 道士 浪人 無法者 虎 狼 熊 豹").split()


def suikoden_status(b: int) -> str:
    """身分 of P+0x15 (MAIN.EXE PC-98 0x5B1A): bit 4 -> index (b & 0xF) + 22, bit 5 -> (b & 0x1F) + 8."""
    s = b & 0x3F
    i = (s & 0x0F) + 22 if s & 0x10 else (s & 0x1F) + 8 if s & 0x20 else s
    return SUIKODEN_STATUS[i] if i < len(SUIKODEN_STATUS) else f"?{s:#x}"


def load_suikoden_stats(suidata: str, platform: str = "pc98") -> list[tuple]:
    """platform: dos, pc98, pc88, x68. Names from the existing koei_games loaders."""
    with open(suidata, "rb") as f:
        data = f.read()
    if platform == "dos":
        names = [n for _, n in k.load_suikoden_dos_persons(suidata)]
        flags = [data[7124 + i * 45 + 43:][:2] for i in range(255)]
    else:
        names = [n for _, n in k.load_suikoden_pc98_persons(suidata, platform == "pc88", platform == "x68")]
        start, size, at = {"pc98": (7124, 20, 18), "pc88": (0x1884, 19, None), "x68": (0x232C, 40, 38)}[platform]
        flags = [(data[start + i * size + at] if at else None, data[start + i * size + (at or 17) + 1])
                 for i in range(255)]
    start, size = {"dos": (4, 22), "pc98": (4, 22), "pc88": (1, 20), "x68": (6, 26)}[platform]
    rows = []
    for i in range(255):
        r = data[start + i * size:][:size]
        if platform == "x68":
            popularity, men, status = int.from_bytes(r[18:20], "big"), r[20], r[21]
        else:
            popularity, men, status = r[16] | r[17] << 8, r[18], r[19]
        tone, flag = flags[i]
        rows.append((i, names[i], r[0], r[3], *r[8:11], r[4], *r[11:14], men, *r[5:8], r[14], popularity,
                     suikoden_status(status), "男" if flag & 0x80 else "女", "○" if status & 0x40 else "",
                     "○" if flag & 0x40 else "", "" if tone is None else tone))
    return rows


##############################################################################
# 源平合戦. Sndata.gp (DOS) / SNDATA.GP (PC-98, byte-identical stats): 4 scenarios x 41266 bytes, 0x26-byte header
# (u16 year), 400 x 71-byte records. Field table and capture: genpei-zh docs/formats.md §4.3.
# +0x1E age in 1180, +0x20 bits 0-3 音楽 和歌 奇略 操船, +0x27 身分, +0x2B u16 動員力, +0x2F 兵質,
# +0x31..39 武力 勇名 弓術 知才 優雅 忠節 菩提 無常 加護, +0x42 体力. Values exclude the treasure bonus.

GENPEI_STATS = ("年齢", "忠節", "知才", "武力", "優雅", "勇名", "体力", "動員力", "兵質", "弓術", "菩提", "加護",
                "無常", "和歌", "音楽", "奇略", "操船", "身分")
GENPEI_STATUS = {0: "御家人", 1: "棟梁", 2: "代官", 5: "在野", 6: "落武者?", 7: "死亡/未登場"}


def load_genpei_stats(sndata: bytes, scenario: int = 0) -> list[tuple]:
    base = scenario * genpei.SCENARIO_SIZE
    year = struct.unpack_from("<H", sndata, base)[0]
    rows = []
    for g, info in zip((sndata[base + 0x26 + i * 71:][:71] for i in range(400)),
                       genpei.load_generals(sndata, scenario)):
        sk = g[0x20]
        rows.append((info["id"], info["surname"] + info["given"], g[0x1E] + year - 1180, g[0x36], g[0x34], g[0x31],
                     g[0x35], g[0x32], g[0x42], struct.unpack_from("<H", g, 0x2B)[0], g[0x2F], g[0x33], g[0x37],
                     g[0x39], g[0x38], *("○" if sk & m else "×" for m in (2, 1, 4, 8)),
                     GENPEI_STATUS.get(g[0x27], g[0x27])))
    return rows


##############################################################################
# 項劉記. SNDT?.KR1: 4-byte header (+1 month, +3 year BC), 92 x 10-byte records (PC-98 MAIN.EXE: DS:0x46 + 10 * i,
# accessors seg 1EEA 0xC52-0xE32): +0 bits 0-2 状態 (2 在野), bit 3 外交 flag, bits 4-7 ?; +2 所在; +3 体力; +4 上限;
# +5 戦闘; +6 統率; +7 用兵; +8 経験; +9 ?. 外交 is 有 when 用兵 >= 80 or +0 bit 3 (0x7767 -> 0x5C21).
# Name table (DOS image 0x3D0D4 / PC-98 0x45D24 / X68 0x50F1A): +15 birth year BC - 206 (年齢 = +15 - year + 206,
# 0x7EE8), +16 four 2-bit hidden values (0xDD2, 0xDDE, 0xDEA, 0xDF6). SNDT records are byte-identical on DOS,
# PC-98 and X68000 (PC-98 / X68 SNDT are only on disk images, not in games/).

KOURYUUKI_STATS = ("年齢", "体力", "上限", "戦闘", "統率", "用兵", "経験", "外交", "生年", "隠し")


def load_kouryuuki_stats(names: list[str], name_table: bytes, size: int, sndt: bytes) -> list[tuple]:
    """name_table: the 92 name records (17 bytes; 18 on X68000), sndt: the whole SNDT file."""
    year_bc = sndt[3]
    rows = []
    for i in range(92):
        n, r = name_table[i * size:][:17], sndt[4 + i * 10:][:10]
        hidden = "/".join(str(n[16] >> s & 3) for s in (0, 2, 4, 6))
        rows.append((i, names[i], (n[15] - year_bc - 50) & 0xFF, *r[3:9], "有" if r[7] >= 80 or r[0] & 8 else "無",
                     -(n[15] + 206), hidden))
    return rows


def kouryuuki_dos_name_table(main_exe: str) -> bytes:
    with open(main_exe, "rb") as f:
        return pklite.depklite(f.read())[k.KOHRYUKI_DOS_NAMES:][:92 * 17]


##############################################################################
# ランペルール. Person records R, 15 bytes (MAIN.EXE en DS:0x44 + 15 * i = NPDATA file 2 + 15 * i per scenario):
# +2 国, +3 所在 (city), +4 政治 財政 補給 建設 (2 bits each, low first, 0-3 = D C B A), +5 指揮 歩兵 騎兵 砲兵,
# +6 経験, +7 忠誠 (Napoleon "--"), +8 年齢, +9 兵力, +0xA, +0xB 騎兵 / 砲兵 marker (0x6078), +0xC 訓練, +0xD 士気,
# +0xE 官階. Status window: MAIN.EXE (en) 0x166FA. DOS: 5 scenarios every 13270 bytes; PC-88 every 0x3100 from 1;
# X68000 NPDATAn.DAT from 4, stride 18. Name record +15: bits 0-1 (3 = the Bonaparte family?), bits 2-7 flags.

LEMPE_STATS = ("政治", "財政", "補給", "建設", "領導", "步兵", "騎兵", "砲兵", "經驗", "忠誠", "年齡",
               "兵力", "士氣", "訓練", "官階", "所在", "國", "隱藏")
LEMPE_GRADE = "DCBA"


def load_lempe_stats(npdata: str, scenario: int = 0, platform: str = "dos") -> list[tuple]:
    with open(npdata, "rb") as f:
        data = f.read()
    if platform == "dos":
        persons = k.load_lempe_persons(npdata, scenario)
        names = [p["name"] for p in persons]
        traits = [p.masks for p in persons]
        start, size = scenario * 13270 + 2, 15
    else:
        names = [n for n, _ in k.load_lempe_pc88_persons(npdata, x68=platform == "x68")]
        o, s = (k.LEMPE_X68_PERSONS, 16) if platform == "x68" else (k.LEMPE_PC88_PERSONS, 15)
        traits = [data[o + i * s + 13] for i in range(255)]
        start, size = (4, 18) if platform == "x68" else (scenario * 0x3100 + 1, 15)
    rows = []
    for i in range(255):
        r = data[start + i * size:][:15]
        grades = [LEMPE_GRADE[b >> s & 3] for b in r[4:6] for s in (0, 2, 4, 6)]
        city = LEMPEPerson.cities[r[3]][0] if r[3] < 46 else r[3]
        rows.append((i, names[i], *grades, r[6], r[7], r[8], r[9], r[13], r[12], r[14] & 0xF, city, r[2],
                     f"{traits[i]:08b}"))
    return rows


##############################################################################
# 維新の嵐 (ISHIN, PC-98): SHINARIO.DAT, 3 scenarios of 0xA770 bytes. The scenario offset 0xAC8 is offset 0 of
# the game's segment 0x2690, where ISIN.EXE keeps two person tables (ISINS.OVL 0xF1BF draws the status window):
# - 0x606:0xD3 (image 0x6133): 28 bytes at 0x3A35 + id * 28 (ids <= 450): +1 u16 身分 code, +3 年齢, +0xC 剣道
#   (max 100), +0xD 学力, +0xE 魅力 (max 200), +0x10 u16 レベル, +0x12 戦闘経験 (max 100); +0x16..+0x19 are read
#   as 尊王 公議 佐幕 攘夷 from the values only (🟡).
# - 0x606:0xF (image 0x606F): 19 bytes at 0x537 + id * 19: +0xF 武力, +0x11 原体力 (max 200).
# Names: the surname table of ISIN.EXE and the scenario's given names (+0x983A, 9 bytes each), which the load puts
# over the exe's default table (DS:0xA034, read by 0x622:0x198).
ISHIN_PC98_STATS = ("年齢", "身分", "原体力", "武力", "剣道", "学力", "魅力", "戦闘経験", "レベル", "身分碼",
                    "尊王", "公議", "佐幕", "攘夷")
ISHIN_PC98_TABLES = (0xAC8 + 0x3A35, 28), (0xAC8 + 0x537, 19)
ISHIN_PC98_GIVEN = 0x983A  # scenario offset of the 9-byte given names
ISHIN_PC98_HANS = 0x95D9  # scenario offset of the 7-byte han and province names; han n is entry n - 1
ISHIN_PC98_BAKUFU = 0x46  # 0x622:0x6B6; the name is 幕府 (DS:0x651E)
# ISIN.EXE DS:0x6790: the far pointers of the 身分 names, indexed by 0x622:0x80A's result
ISHIN_PC98_RANKS = ("天皇 大臣 議奏 朝臣 将軍 老中 奉行 幕臣 浪人 藩主 家老 重臣 藩士 浪人 独立諸隊 儒学者 国学者 蘭学者 "
                    "兵学者 砲学者 学者 女性 女房 女官 将軍家御台所 勤王家 天理教々祖 おいらん 仁侠親分 仁侠子分 商人 総領事 "
                    "外交官 艦隊司令 外国商人 僧 神官 金光教々租 志士 町人").split()
ISHIN_PC98_UNITS = "新撰組 奇兵隊 海援隊 彰義隊 天狗党 見廻組 天誅組 白虎隊 諸生党".split()  # DS:0x6578, codes 0x5D-0x65


def ishin_pc98_rank(code: int, hans: list[str]) -> str:
    """身分 name of a person's +1 code, as 0x622:0x80A (the decoder of the high nibble) and 0x622:0x198 do."""
    kind, n, low = code >> 12, code >> 8 & 0xF, code & 0xFF
    if kind == 1:
        if 0x5C < low < 0x66:
            return ISHIN_PC98_UNITS[low - 0x5D]
        index = n + 4 if low == ISHIN_PC98_BAKUFU else n + 9 if 0 < low < 0x57 else n
        han = "幕府" if low == ISHIN_PC98_BAKUFU else hans[low - 1] if low else ""
        return han + ISHIN_PC98_RANKS[index] if 9 <= index <= 12 else ISHIN_PC98_RANKS[index]
    index = {2: 0xE + low, 3: 0x15 + low, 4: 0x1C if n == 0 else 0x1D, 5: 0x1E, 6: 0x1F + n, 7: 0x23 + low, 8: 0x26,
             9: 0x27}.get(kind)
    return ISHIN_PC98_RANKS[index] if index is not None and index < len(ISHIN_PC98_RANKS) else f"?{code:04X}"


def load_ishin_pc98_stats(isin_exe, shinario, scenario: int = 0) -> list[tuple]:
    with open(isin_exe, "rb") as f:
        exe = f.read()
    with open(shinario, "rb") as f:
        sc = f.read()[scenario * k.ISHIN_PC98_SCENARIO:][:k.ISHIN_PC98_SCENARIO]
    hans = [k._ishin_pc98_text(sc[ISHIN_PC98_HANS + i * 7:][:7].split(b"\0")[0]).strip() for i in range(87)]
    (b0, bs), (a0, as_) = ISHIN_PC98_TABLES
    rows = []
    for i in range(k.ISHIN_PC98_PEOPLE):
        name = "".join(k._ishin_pc98_text(raw[o + i * n:][:n].split(b"\0")[0])
                       for raw, o, n in ((exe, 0x42312, 7), (sc, ISHIN_PC98_GIVEN, 9)))
        b, a = sc[b0 + i * bs:][:bs], sc[a0 + i * as_:][:as_]
        code = int.from_bytes(b[1:3], "little")
        rows.append((i, name, b[3], ishin_pc98_rank(code, hans), a[0x11], a[0xF], b[0xC], b[0xD], b[0xE], b[0x12],
                     int.from_bytes(b[0x10:0x12], "little"), f"{code:04X}", *b[0x16:0x1A]))
    return rows


##############################################################################

def _koei_stats(game, game_dir):
    """(labels, rows of (scenario or table, name, *stats)) of one dataset."""
    def path(name):
        return next(f for f in glob.glob(os.path.join(game_dir, "*")) if os.path.basename(f).lower() == name.lower())

    def read(name):
        with open(path(name), "rb") as f:
            return f.read()

    def files(pattern):
        return sorted(f for f in glob.glob(os.path.join(game_dir, "*"))
                      if fnmatch.fnmatch(os.path.basename(f).lower(), pattern.lower()))

    platform = game.rsplit("-", 1)[1]
    if game.startswith("genghis-"):
        ext = "DAT" if platform == "x68" else "CIM"
        rows = []
        for f in ("MDATA", "SDATA"):
            cim = read(f"{f}.{ext}")
            rows += [(f"{f} {slot.split()[0]}", name, *v[:-1], "○" if v[-1] else "", "", "")
                     for slot, name, *v in load_genghis_stats(cim, platform)]
            rows += [(f"{f} {slot.split()[0]}", name, age, *[""] * 7, base, "○" if extra is True else extra)
                     for slot, name, age, base, extra in load_genghis_general_stats(cim, platform)]
        return ("年齢", *GENGHIS_STATS, "一族", "基本能力値", "血縁値/男子"), rows
    if game.startswith("genchou-"):
        rows = load_genchou_stats(game_dir, x68=platform == "x68", pc98=platform == "pc98", dos=platform == "dos")
        return GENCHOU_STATS, [(f"GENDATA{sc}" if t == "GENDATA" else f"USDATA{sc} {t.split()[1]}", *r)
                               for sc, t, *r in rows]
    if game == "genghis4pk-win":
        return (*GENGHIS4_STATS, "特技"), [(os.path.basename(f), *r[1:-1], "/".join(r[-1]))
                                          for f in files("SCEDAT*.CK") for r in load_genghis4_win_stats(f)]
    if game in ("eiketsu-dos", "eiketsu-pc98"):
        return EIKETSU_DOS_STATS, [("BAKDATA", *r[1:]) for r in load_eiketsu_dos_stats(path("BAKDATA.R3"),
                                                                                       pc98=platform == "pc98")]
    one = {"koumei-win": ("BAKDATA.E2", load_koumei_win_stats, KOUMEI_WIN_STATS),
           "eiketsu3-win": ("DATA.E3", load_eiketsu3_win_stats, EIKETSU3_WIN_STATS),
           "eiketsu4-win": ("DATA.E4", load_eiketsu4_win_stats, EIKETSU4_WIN_STATS),
           "eiketsu5-win": ("DATA.E5", load_eiketsu5_win_stats, EIKETSU5_WIN_STATS),
           "koukai2-pc98": ("DATA1.LZW", load_koukai2_pc98_stats, KOUKAI2_STATS),
           "koukai3-win": ("CDS95.EXE.pec2bac", load_koukai3_win_stats, KOUKAI3_WIN_STATS)}
    if game in one:
        name, load, labels = one[game]
        return labels, [(name, *r[1:]) for r in load(path(name))]
    if game in ("koukai-dos", "koukai-pc98", "koukai-pc88"):
        return KOUKAI_STATS, [("SHINARIO", *r[1:]) for r in load_koukai_stats(path("SHINARIO.CIM"), platform)]
    if game == "koukaigd-win":
        return KOUKAIGD_STATS, [(f"table {r[0].split('/')[0]}", *r[1:]) for r in load_koukaigd_win_stats(path("koukaiGD.exe"))]
    if game == "koukai4pk-win":
        rows = []
        for lang, first, enc in (("JP", "ラファエル", "cp932"), ("TC", "拉斐爾", "cp950")):
            for f in sorted(glob.glob(os.path.join(game_dir, lang, "World*.dll"))):
                rows += [(f"{lang}/{os.path.basename(f)}", *r[1:]) for r in load_koukai4_win_stats(f, first, enc)]
        return KOUKAI4_WIN_STATS, rows
    if game.startswith("suikoden-"):
        return SUIKODEN_STATS, [(os.path.basename(f), *r[1:]) for f in files("SUIDATA*.CIM")
                                for r in load_suikoden_stats(f, platform)]
    if game.startswith("genpei-"):
        sndata = read("SNDATA.GP")
        return GENPEI_STATS, [(f"劇本{s + 1}", *r[1:]) for s in range(len(sndata) // genpei.SCENARIO_SIZE)
                              for r in load_genpei_stats(sndata, s)]
    if game == "kouryuuki-dos":
        exe = path("MAIN.EXE")
        names, table = k.load_kohryuki_dos_names(exe), kouryuuki_dos_name_table(exe)
        return KOURYUUKI_STATS, [(os.path.basename(f), *r[1:]) for f in files("SNDT*.KR1")
                                 for r in load_kouryuuki_stats(names, table, 17, open(f, "rb").read())]
    if game == "ishin-pc98":
        return ISHIN_PC98_STATS, [(f"劇本{s + 1}", *r[1:]) for s in range(3)
                                  for r in load_ishin_pc98_stats(path("ISIN.EXE"), path("SHINARIO.DAT"), s)]
    if game.startswith("lempe-"):
        if platform == "x68":
            return LEMPE_STATS, [(os.path.basename(f), *r[1:]) for f in files("NPDATA*.DAT")
                                 for r in load_lempe_stats(f, 0, "x68")]
        npdata = path("NPDATA.CIM")
        step, first = (13270, 2) if platform == "dos" else (0x3100, 1)
        count = (os.path.getsize(npdata) - first - 255 * 15) // step + 1
        return LEMPE_STATS, [(f"劇本{s + 1}", *r[1:]) for s in range(count) for r in load_lempe_stats(npdata, s, platform)]
    raise click.BadParameter(f"unknown dataset {game}")


@click.command(help="光榮其他系列 人物能力（CSV）")
@click.argument("game")
@click.option("--game-dir", "game_dir", required=True, help="遊戲目錄（劇本檔所在處）")
@click.option("-s", "--scenario", help="只列這個劇本（檔名或表名）")
def koei_person(game, game_dir, scenario):
    """
    GAME 是 dataset id：genghis-pc88（-pc98、-x68、-dos）、genchou-pc88（-pc98、-x68、-dos）、genghis4pk-win、
    eiketsu-dos（-pc98）、koumei-win、eiketsu3-win、eiketsu4-win、eiketsu5-win、koukai-dos（-pc98、-pc88）、
    koukai2-pc98、koukaigd-win、koukai3-win、koukai4pk-win、suikoden-dos（-pc98、-pc88、-x68）、genpei-pc98（-dos）、
    kouryuuki-dos、lempe-dos（-pc88、-x68）、ishin-pc98

    dekoei.py koei-person genghis-pc98 --game-dir ../games/genghis-pc98 -s MDATA
    """
    labels, rows = _koei_stats(game, game_dir)
    print(",".join(["劇本", "姓名"] + list(labels)))
    for row in rows:
        if scenario is None or row[0] == scenario or row[0].startswith(scenario + " "):
            print(",".join(map(str, row)))
