"""武將列傳 (officer biographies) of the Traditional Chinese 三國志 releases, as JSONL for koei-wiki: one line per
section, {"dataset", "id", "name", "lang", "kind", "text"}. id is the person id of the kaodata dataset; kind is 簡介
(the one-line summary), 演義, 史實, or 單段 for a biography that is not split. Sections that only say 無記述 are left
out. Formats are in notes/<game>.md「列傳」."""
import importlib
import json
import os
import struct

import click

import ls11
import sango
import utils

KINDS = {"演義", "史實"}


def sections(intro: str, parts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """(kind, text) of a biography: the summary, then the parts, without the empty and 無記述 ones."""
    out = [("簡介", intro.strip())] + [(k, t.strip()) for k, t in parts]
    return [(k, t) for k, t in out if t and t.rstrip("。") != "無記述"]


# 三國志13 PK: the biography of person n is string 15235 + n (6535 + 6 x 1450) of the name table, Big5 in item 1416.
# "summary\n ESC C4 <icon> ESC R 演義 \n ESC C2 <icon> ESC R 史實"; ESC R is also followed by digits of the text.
# The icons are FA60 then FA49, swapped in 27 of the added persons (1151-) whose first section is still 演義 (無記述
# for people only in the histories), so the sections go by order. The 古武將 (850-898) have one section. Gaiji (FAxx) besides the names' own: 坂 (長坂坡) and 𩅦 (孫𩅦, the
# Japanese text writes 孫［ソンワン］)
SAN13_BIO = sango.SAN13_NAME_FIELDS[0] + 6 * sango.SAN13_NAME_FIELDS[1]
SAN13_BIO_GAIJI = {0xFA40: "伷", 0xFA41: "璝", 0xFA44: "𩅦", 0xFA45: "儁", 0xFA70: "坂"}
SAN13_MARKS = {b"\x1bC4\xfa\x60\x1bR", b"\x1bC2\xfa\x49\x1bR", b"\x1bC4\xfa\x49\x1bR", b"\x1bC2\xfa\x60\x1bR"}


def san13_big5(b: bytes) -> str:
    """Big5 text with the game's gaiji; the section marks become \0."""
    out, i = [], 0
    while i < len(b):
        mark = next((m for m in SAN13_MARKS if b.startswith(m, i)), None)
        if mark:
            out.append("\0")
            i += len(mark)
        elif b[i] >= 0x81:
            code = b[i] << 8 | b[i + 1]
            out.append(SAN13_BIO_GAIJI.get(code) or b[i:i + 2].decode("cp950"))
            i += 2
        else:
            assert b[i] != 0x1B, b[i:i + 4]
            out.append(chr(b[i]))
            i += 1
    return "".join(out)


def san13_raw_strings(b: bytes) -> list[bytes]:
    rows, size, header = struct.unpack_from("<3H", b, 8)
    out = []
    for r in range(rows):
        o = header + struct.unpack_from("<I", b, header + r * size)[0]
        out.append(b[o:b.index(b"\0", o)])
    return out


def split_marked(t: str) -> list[tuple[str, str]]:
    intro, *parts = t.split("\0")
    if not parts:
        return sections("", [("單段", intro)])
    assert len(parts) == 2
    return sections(intro, list(zip(("演義", "史實"), parts)))


def san13_bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    item = sango.san13_items(sango.san13_items(sango.san13_entry(game_dir, sango.SAN13_NAMES_TC))[0])[0]
    strings = san13_raw_strings(item)
    out = {}
    for n in range(sango.SAN13_NAME_FIELDS[1]):
        if strings[SAN13_BIO + n]:
            out[n] = split_marked(san13_big5(strings[SAN13_BIO + n]))
    return out


# 三國志14 PK: 0001_TC/msgdata.bin is zp1 (as 三國志13), an archive whose item 0 holds an XL string table (item 0,
# UTF-16LE, offsets from 0x18); the biography of person n is string 386 + n. Same layout as 三國志13 with
# "^05<U+E020>^00" before 演義 and "^03<U+E009>^00" before 史實. Gaiji: U+E000 伷, E001 璝, E005 儁, E00B 崖 (珠崖),
# E00C 喁, E030 坂, and E004 for both 衜 (羊衜) and 𩅦 (孫𩅦; the Japanese text has a code of its own)
SAN14_MSGDATA = "0001_TC/msgdata.bin"
SAN14_BIO = 386
SAN14_BIO_GAIJI = {"\ue000": "伷", "\ue001": "璝", "\ue004": "衜", "\ue005": "儁", "\ue00b": "崖", "\ue00c": "喁",
                   "\ue030": "坂"}


def san14_strings(game_dir) -> list[str]:
    with open(os.path.join(game_dir, SAN14_MSGDATA), "rb") as f:
        b = sango.san13_unzip(f.read())
    x = sango.san13_items(sango.san13_items(b)[0])[0]
    assert x[:2] == b"XL"
    rows, size = struct.unpack_from("<2H", x, 8)
    out = []
    for r in range(rows):
        o = 0x18 + struct.unpack_from("<I", x, 0x18 + r * size)[0]
        e = o
        while x[e:e + 2] != b"\0\0":
            e += 2
        out.append(x[o:e].decode("utf-16-le"))
    return out


def san14_bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    strings = san14_strings(game_dir)
    out = {}
    for n in range(sango.SAN14_PERSON_COUNT):
        t = strings[SAN14_BIO + n].replace("孫\ue004", "孫𩅦")
        t = t.replace("\n^05\ue020^00", "\0").replace("\n^03\ue009^00", "\0")
        t = "".join(SAN14_BIO_GAIJI.get(c, c) for c in t)
        assert "^" not in t and not any(0xE000 <= ord(c) <= 0xF8FF for c in t), (n, t)
        out[n] = split_marked(t)
    return out


# 三國志IV / V PK DOS 中文版: KOEI-TW internal code, the same as the names (utils.to_unicode_name). Hanzi are hi
# 0x92-0xD8 (utils.order_of_koei_tw -> cns_from_order); punctuation is hi 0x81-0x91 with the same lo order, n =
# (hi - 0x81) x 188 + lo order -> CNS 1-2121 + n (8131 ，8133 。8134 ．8172/8173 「」). 0x0A is a display line
# break, 0x01 + 1 byte (三國志V) a line attribute, 05 05 05 the end (padded with spaces). One section, no gaiji.
# 三國志IV writes every full stop as 8134 ．(8133 never occurs), taken as 。
def koei_tw_text(b: bytes, period="．") -> str:
    if not utils.cns11643_unicode_table:
        utils.cns11643_unicode_table = utils.load_cns11643_unicode_table()
    table = utils.cns11643_unicode_table
    b = b.split(b"\x05\x05\x05")[0]
    out, i = [], 0
    while i < len(b):
        c = b[i]
        if c == 0x01:
            i += 2
            continue
        if c < 0x81:
            assert c == 0x0A or 0x20 <= c < 0x7F, b[i:i + 2]
            out.append("" if c == 0x0A else chr(c))
            i += 1
            continue
        code = b[i:i + 2]
        if c >= 0x92:
            ch = table[utils.cns_from_order(utils.order_of_koei_tw(code))]
        else:
            lo = utils.order_of_koei_tw(bytes([0x93, b[i + 1]])) - 94  # the order within a row
            assert lo >= 0, code
            hi, lo = divmod((c - 0x81) * 188 + lo, 94)
            ch = table[f"1-{0x21 + hi:02X}{0x21 + lo:02X}"]
            ch = period if ch == "．" else ch
        out.append(ch)
        i += 2
    return "".join(out).strip()


def message_parts(path) -> list[bytes]:
    with open(path, "rb") as f:
        return ls11.ls11_decode_parts(f.read())


def offset_table(part: bytes, count_first: bool) -> list[bytes]:
    """Messages of a part: a u16 offset table (from the part's start), after a u16 count or sized by the first
    offset."""
    if count_first:
        n, start = struct.unpack_from("<H", part)[0], 2
    else:
        n, start = struct.unpack_from("<H", part)[0] // 2, 0
    offsets = list(struct.unpack_from(f"<{n}H", part, start)) + [len(part)]
    return [part[a:b] for a, b in zip(offsets, offsets[1:])]


# 三國志IV PK: MESSAGE.S4 parts 24-33 (454 messages; the offset table has no count). A plain face code c < 0x8000 is
# message c; a montage face is message 250 + its index in the MAIN.EXE 0x3EA98 table of codes (244, ends below
# 0x8000). Persons are numbered as in kaodata_export.build_san4: scenario order, by (code, name); the tribes (南蠻王…)
# and the 水滸伝 officers have none
SAN4_BIO_PARTS = range(24, 34)
SAN4_MONTAGE_CODES = 0x3EA98


def san4_persons(game_dir) -> dict[int, tuple[str, int]]:
    from kaodata_export import SAN4PK_DOS_NAME_FIX
    seen = {}
    for _, name, code in sango.load_san4_persons(os.path.join(game_dir, "SNDATA.S4"),
                                                  os.path.join(game_dir, "TAIKI.S4")):
        seen.setdefault((code, SAN4PK_DOS_NAME_FIX.get(name, name)), len(seen))
    return {i: (name, code) for (code, name), i in seen.items()}


def san4_bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    parts = message_parts(os.path.join(game_dir, "MESSAGE.S4"))
    bios = [m for k in SAN4_BIO_PARTS for m in offset_table(parts[k], False)]
    with open(os.path.join(game_dir, "MAIN.EXE"), "rb") as f:
        exe = f.read()
    montage = []
    while (c := struct.unpack_from("<H", exe, SAN4_MONTAGE_CODES + 2 * len(montage))[0]) >= 0x8000:
        montage.append(c)
    out = {}
    for i, (_, code) in san4_persons(game_dir).items():
        k = code if code < 0x8000 else 250 + montage.index(code) if code in montage else None
        if k is not None and k < len(bios):
            out[i] = sections("", [("單段", koei_tw_text(bios[k], "。"))])
    return out


# 三國志V PK: MESSAGE.S5 parts 1-10, 50 messages each (u16 count + offsets); message c is face code c. Persons are
# numbered as in kaodata_export.build_san5pk: scenario order, one per face code
SAN5_BIO_PARTS = range(1, 11)


def san5_persons(game_dir) -> dict[int, tuple[str, int]]:
    seen = {}
    for _, name, code in sango.load_san5_persons(os.path.join(game_dir, "SNDATA.S5"),
                                                  os.path.join(game_dir, "TAIKI.S5"), False, tail=1100):
        if code not in seen:
            seen[code] = (len(seen), name)
    return {i: (name, code) for code, (i, name) in seen.items()}


def san5_bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    parts = message_parts(os.path.join(game_dir, "MESSAGE.S5"))
    bios = [m for k in SAN5_BIO_PARTS for m in offset_table(parts[k], True)]
    return {i: sections("", [("單段", koei_tw_text(bios[code]))])
            for i, (_, code) in san5_persons(game_dir).items() if code < len(bios)}


# 三國志VI PK: MESSAGE.S6 is LS11; each part is a u16 count and count u16 offsets (from the part's start). Parts 1-6
# are the biographies by face code - 1 (521 messages, the last 「沒有列傳。」), one section in Big5: display lines of
# \x01" + text + \n (they break inside words, so they are joined), ending \x05\x05\x05. The kaodata id of persons
# 0-519 is the slot; the 12 tribe leaders (faces 539-550) have none
SAN6_BIO_PARTS = range(1, 7)


def san6_bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    parts = message_parts(os.path.join(game_dir, "MESSAGE.S6"))
    bios = [m for k in SAN6_BIO_PARTS for m in offset_table(parts[k], True)]
    out = {}
    for slot, _, face in sango.load_san6_persons(game_dir):
        if face < len(bios):
            t = bios[face - 1].replace(b'\x01"', b"").replace(b"\n", b"").rstrip(b"\x05")
            out[slot] = sections("", [("單段", t.decode("cp950"))])
    return out


def san6_names(game_dir) -> dict[int, str]:
    return {slot: name for slot, name, _ in sango.load_san6_persons(game_dir)}


def san13_names(game_dir) -> dict[int, str]:
    return {p: v[1] for p, v in sango.load_san13_persons(game_dir)["names"].items()}


def san14_names(game_dir) -> dict[int, str]:
    from kaodata_export import SAN14PK_WIN_GAIJI, SAN14PK_WIN_SCENARIOS
    gaiji = {**SAN14_BIO_GAIJI, **{c: v for (lang, c), v in SAN14PK_WIN_GAIJI.items() if lang == "TC"}}
    persons = sango.load_san14_persons(os.path.join(game_dir, SAN14PK_WIN_SCENARIOS[1]), "TC")
    return {p["id"]: "".join(gaiji.get(c, c) for c in p["surname"] + p["given"]) for p in persons}


DATASETS = {"san4pk-dos": (san4_bios, lambda d: {i: v[0] for i, v in san4_persons(d).items()}),
            "san5pk-dos": (san5_bios, lambda d: {i: v[0] for i, v in san5_persons(d).items()}),
            "san6pk-win": (san6_bios, san6_names), "san13pk-win": (san13_bios, san13_names), "san14pk-win": (san14_bios, san14_names)}
# 信長の野望 and 三國志VII–12: dataset -> module with bios(game_dir) -> {id: [(kind, text)]}, bio_names(game_dir) -> {id:
# name} and BIO_LANG (the text's language)
MODULES = {"nobu5pk-win": "wiki_nobu5", "nobu5pk-pc98": "wiki_nobu5_pc98", "nobu6pk-pc98": "wiki_nobu6", "nobu7pk-win": "wiki_nobu7", "nobu8pk-win": "wiki_nobu8",
           "nobu9pk-win": "wiki_nobu9", "nobu10pk-win": "wiki_nobu10", "nobu11pk-win": "wiki_nobu11",
           "nobu12pk-win": "wiki_nobu12", "nobu13pk-win": "wiki_nobu13",
           "san7pk-win": "san7_extras", "san8pk-win": "san8_extras", "san9pk-win": "san9_extras", "san10pk-win": "san10_extras", "san11pk-win": "san11_extras",
           "san12pk-win": "san12_extras",  # 三國志VII–12: the Steam 繁中版 depots
           "genghis4pk-win": "wiki_genghis4"}


def records(dataset, game_dir):
    if dataset in MODULES:
        m = importlib.import_module(MODULES[dataset])
        bios, names, lang = m.bios, m.bio_names, m.BIO_LANG
    else:
        (bios, names), lang = DATASETS[dataset], "zh-Hant"
    names = names(game_dir)
    for n, parts in sorted(bios(game_dir).items()):
        for kind, text in parts:
            yield {"dataset": dataset, "id": n, "name": names.get(n, ""), "lang": lang, "kind": kind, "text": text}


@click.command()
@click.argument("dataset", type=click.Choice(sorted({**DATASETS, **MODULES})))
@click.option("--game-dir", "game_dir", required=True)
@click.option("--out", "out", required=True, help="JSONL 檔")
def biography(dataset, game_dir, out):
    """匯出武將列傳（JSONL，給 koei-wiki；三國志是繁中版，信長の野望照主資料集的語言）"""
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for r in records(dataset, game_dir):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    print(f"{out}: {n} sections")
