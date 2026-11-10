"""三國志X PK (Steam, appid 628060): event pictures, event scripts and messages, 寶物 and other material.

Run from dekoei/:
  ../.venv/bin/python san10_extras.py --game-dir ../games/san10pk-win --out ../games/san10pk-win/extract
Formats: notes/san10.md「事件、插圖、道具」.
"""
import csv
import json
import os
import struct
import unicodedata

import click
from PIL import Image

import ls11
import sango


ITEM_GAIJI = {0xE029: "釭", 0xE059: "蒺"}  # 青釭の剣, 鉄蒺藜骨朶; glyphs read off S10Gaiji.tte
# more glyphs read off S10Gaiji.tte for the messages (E08C/E08D are the up and down arrows of the help texts), and
# the place-name ones of places_export; the rest stay as private-use characters
TEXT_GAIJI = {**sango.SAN10_GAIJI, **ITEM_GAIJI, 0xE08C: "↗", 0xE08D: "↘", 0xE036: "琪", 0xE030: "鄱",
              0xE018: "譙", 0xE06B: "祁", 0xE06C: "嶲", 0xE02D: "鄴", 0xE020: "邳", 0xE022: "淄", 0xE024: "并",
              0xE00B: "兗"}


def read_msg(path) -> list[bytes]:
    """msg/S10M??PK.s10: one LS11 part, u16 count, then u32 offsets of the entries."""
    with open(path, "rb") as f:
        part = ls11.ls11_decode_parts(f.read())[0]
    n = struct.unpack_from("<H", part, 0)[0]
    offs = [struct.unpack_from("<I", part, 2 + 4 * i)[0] for i in range(n)] + [len(part)]
    return [part[offs[i]:offs[i + 1]] for i in range(n)]


def _kana(ch: str, katakana: bool) -> str:
    """Half-width kana to full-width; hiragana unless ESC K switched to katakana."""
    full = unicodedata.normalize("NFKC", ch)
    if katakana or full == "ー":
        return full
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in full)


def text(b: bytes) -> str:
    """Message bytes to text: Shift-JIS with half-width kana shown as hiragana (ESC K ... ESC H = katakana),
    newline 0A, the 05 05 05 end mark dropped, 02 xx yy (a name or number put in at run time) as {xxyy},
    01 'C' xx yy (a speech ending that depends on the speaker) as 〜, other control bytes as {xx}."""
    out, i, kata, kana = [], 0, False, b""

    def flush():
        nonlocal kana
        if kana:
            s = kana.decode("cp932")
            out.append(_kana(unicodedata.normalize("NFKC", s), kata) if s else "")
            kana = b""

    while i < len(b):
        c = b[i]
        if 0xA1 <= c <= 0xDF:
            # keep runs together so a voiced mark (ﾞ ﾟ) joins the kana before it
            kana += bytes([c])
            i += 1
            continue
        flush()
        if c == 0x1B and i + 1 < len(b) and b[i + 1] in b"HK":
            kata = b[i + 1] == ord("K")
            i += 2
        elif c == 0x0A:
            out.append("\n")
            i += 1
        elif c == 0x05:
            i += 1
        elif c == 0x02 and i + 2 < len(b):
            out.append("{%02x%02x}" % (b[i + 1], b[i + 2]))
            i += 3
        elif c == 0x01 and i + 3 < len(b) and b[i + 1] == ord("C"):
            out.append("〜")
            i += 4
        elif c < 0x20:
            out.append("{%02x}" % c)
            i += 1
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC:
            try:
                ch = b[i:i + 2].decode("cp932")
                out.append(TEXT_GAIJI.get(ord(ch), ch))
            except UnicodeDecodeError:  # a control byte inside a word, see the callers' notes
                out.append("{%02x}" % c)
                i -= 1
            i += 2
        else:
            out.append(chr(c))
            i += 1
    flush()
    return "".join(out).strip("\n")


def grp_png(entry) -> Image.Image:
    w, h, pixels, pal = entry
    im = Image.frombytes("P", (w, h), pixels)
    im.putpalette(b"".join(bytes((pal[k + 2], pal[k + 1], pal[k])) for k in range(0, 1024, 4)))
    return im


EXE_BASE = 0x400000
# San10WPK.exe .data 0x4F43E8: u32 VAs of strings; the 寶物 names are slots 102-301, their readings (half-width kana)
# 302-501, the kind names 502-527 (名馬 … 玉璽), then 未登場／登場／破棄 and the kind effects
STRINGS = 0x4F43E8
ITEM_NAMES, ITEM_READINGS, KIND_NAMES, STATUS_NAMES = 102, 302, 502, 528
ITEMS, KINDS = 200, 26
# Scenario files end with 200 寶物 records of 12 bytes: u8 id, u8 kind, u8 ?, u8 ?, u16 holder (officer id, FFFF
# none), u8 city where it waits to be found (FF none), u8 status (0 未登場 1 登場 2 破棄), u8 ?, u8 ?, u16 picture (GrpStill entry 5 + n for 240x240, 181 + n for 120x120)
ITEM_RECORD = 12
STILL_LARGE, STILL_SMALL, STILL_PICTURES = 5, 181, 176
# GrpStill entries that are not 寶物 pictures: 0-4 (272x272), 357-359, and the 87 event stills 360-446 (512x384)
MSG_FILES = 31  # msg/S10M00PK.s10 … S10M30PK.s10 (the PK reads these, not S10MSG??)
# whole archives written out entry by entry (folder, archive, smallest width kept)
ARCHIVES = [("eventcg/event_sprites", "GrpEvent.s10", 0),   # event scenes: actor animation strips, effects, sets
            ("eventcg/city", "GrpCity.s10", 0),             # city command screens and their pieces
            ("eventcg/start", "GrpStart.s10", 300),         # title, scenario and new-game screens
            ("eventcg/start_pk", "GpkStart.s10", 300),
            ("eventcg/logo", "GrpELogo.s10", 0)]


def _exe_strings(exe: bytes, first: int, count: int) -> list[str]:
    out = []
    for k in range(count):
        o = struct.unpack_from("<I", exe, STRINGS + 4 * (first + k))[0] - EXE_BASE
        s = exe[o:exe.index(b"\0", o)].decode("cp932")
        out.append("".join(TEXT_GAIJI.get(ord(c), c) for c in s))
    return out


def _save(im: Image.Image, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)


def place_names(exe: bytes) -> list[str]:
    import places_export as pe
    gaiji = {**sango.SAN10_GAIJI, **pe.SAN10_EXTRA_GAIJI}
    out = []
    for i in range(pe.SAN10_PLACE_KINDS):
        o = struct.unpack_from("<I", exe, pe.SAN10_PLACES + 12 * i)[0] - EXE_BASE
        out.append(pe._gaiji(exe[o:exe.index(b"\0", o)].decode("cp932"), gaiji))
    return out


def items(game_dir: str, out: str) -> int:
    with open(os.path.join(game_dir, "San10WPK.exe"), "rb") as f:
        exe = f.read()
    names = _exe_strings(exe, ITEM_NAMES, ITEMS)
    readings = [unicodedata.normalize("NFKC", s) for s in _exe_strings(exe, ITEM_READINGS, ITEMS)]
    kinds = _exe_strings(exe, KIND_NAMES, KINDS)
    status = _exe_strings(exe, STATUS_NAMES, 3)
    descs = [text(b).replace("\n", "") for b in read_msg(os.path.join(game_dir, "msg", "S10M12PK.s10"))[:ITEMS]]
    places = place_names(exe)
    scen_dir = os.path.join(game_dir, "Scenario")
    scenarios = sorted(os.listdir(scen_dir))
    persons = {p["id"]: p["name"] for p in
               sango.load_san10_persons(os.path.join(game_dir, "San10WPK.exe"), os.path.join(scen_dir, scenarios[0]))}
    os.makedirs(os.path.join(out, "items"), exist_ok=True)
    base_rec = None
    holders = []
    for sc in scenarios:
        with open(os.path.join(scen_dir, sc), "rb") as f:
            d = f.read()
        start = len(d) - ITEMS * ITEM_RECORD
        recs = [d[start + ITEM_RECORD * k:start + ITEM_RECORD * (k + 1)] for k in range(ITEMS)]
        assert [r[0] for r in recs] == list(range(ITEMS)), sc
        if base_rec is None:
            base_rec = recs
        for k, r in enumerate(recs):
            holder, city = struct.unpack_from("<H", r, 4)[0], r[6]
            holders.append([sc, k, names[k], "" if holder == 0xFFFF else holder, persons.get(holder, ""),
                            "" if city == 0xFF else city, places[city] if city < len(places) else "", r[7],
                            status[r[7]], r[8], r[9]])
    with open(os.path.join(out, "items", "items.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "reading", "kind", "kindName", "b2", "b3", "picture", "description"])
        for k, r in enumerate(base_rec):
            w.writerow([k, names[k], readings[k], r[1], kinds[r[1]], r[2], r[3], struct.unpack_from("<H", r, 10)[0],
                        descs[k]])
    with open(os.path.join(out, "items", "holders.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "id", "name", "holder", "holderName", "city", "cityName", "status", "statusName", "b8",
                    "b9"])
        w.writerows(holders)
    still = sango.load_san10_grp(os.path.join(game_dir, "Grp", "GrpStill.s10"))
    for n in range(STILL_PICTURES):
        _save(grp_png(still[STILL_LARGE + n]), os.path.join(out, "items", "pictures", f"{n:03d}.png"))
        _save(grp_png(still[STILL_SMALL + n]), os.path.join(out, "items", "pictures_small", f"{n:03d}.png"))
    with open(os.path.join(out, "items", "kinds.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "name"])
        w.writerows(enumerate(kinds))
    return len(names)


def event_pictures(game_dir: str, out: str) -> dict:
    counts = {}
    still = sango.load_san10_grp(os.path.join(game_dir, "Grp", "GrpStill.s10"))
    other = [i for i in range(len(still)) if not STILL_LARGE <= i < STILL_SMALL + STILL_PICTURES]
    for i in other:
        _save(grp_png(still[i]), os.path.join(out, "eventcg", "still", f"{i:03d}.png"))
    counts["still"] = len(other)
    pk = sango.load_san10_grp(os.path.join(game_dir, "Grp", "GpkEvent.s10"))
    for i, e in enumerate(pk):
        _save(grp_png(e), os.path.join(out, "eventcg", "still_pk", f"{i:03d}.png"))
    counts["still_pk"] = len(pk)
    for folder, name, min_w in ARCHIVES:
        n = 0
        for i, e in enumerate(sango.load_san10_grp(os.path.join(game_dir, "Grp", name))):
            w, h, pixels, pal = e
            if w < min_w or len(pixels) != w * h or len(pal) != 1024:
                continue  # entries shorter than w x h + palette are another format (not decoded)
            _save(grp_png(e), os.path.join(out, folder, f"{i:04d}.png"))
            n += 1
        counts[folder.split("/")[1]] = n
    return counts


def events(game_dir: str, out: str) -> int:
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    n = 0
    with open(os.path.join(out, "events", "messages.jsonl"), "w", encoding="utf-8") as f, \
            open(os.path.join(out, "events", "files.csv"), "w", encoding="utf-8-sig", newline="") as g:
        w = csv.writer(g)
        w.writerow(["file", "entries", "first"])
        for k in range(MSG_FILES):
            name = f"S10M{k:02d}PK.s10"
            msgs = read_msg(os.path.join(game_dir, "msg", name))
            for i, b in enumerate(msgs):
                f.write(json.dumps({"file": name, "index": i, "text": text(b)}, ensure_ascii=False) + "\n")
            n += len(msgs)
            w.writerow([name, len(msgs), next((text(b) for b in msgs if text(b).strip()), "")[:40].replace("\n", " ")])
    return n


# biography.py reads the Steam 繁中版 (depot 628062): msg/S10M13PK.s10 has the same 807 entries as the Japanese
# release, the 列傳 being the ones a person record's +20 points at (0-730), cp950 ended by 05 05 05 with the gaiji of
# 三國志IX (san9_extras.ZH_GAIJI; 朱儁's 儁 is FA45). The names are in San10WPK.exe like the Japanese ones
# (sango.load_san10_persons), the three u32 VA tables at 0x919120 (surname), 0x919B48 (given name), 0x91A570 (style).
BIO_LANG = "zh-Hant"
ZH_NAME_TABLES = (0x919120, 0x919B48)


def zh_persons(game_dir) -> list[tuple[int, str, int]]:
    """(id, name, 列傳 number) of the 650 officers of the 繁中版."""
    from san9_extras import zh_text
    with open(os.path.join(game_dir, "San10WPK.exe"), "rb") as f:
        exe = f.read()
    with open(os.path.join(game_dir, "Scenario", "Sce000.s10"), "rb") as f:
        sce = f.read()

    def name(table, k):
        o = struct.unpack_from("<I", exe, table - 0x400000 + 4 * k)[0] - 0x400000
        return zh_text(exe[o:exe.index(b"\0", o)])

    start, size, count = sango.SAN10_PERSONS
    out = []
    for k in range(count):
        r = sce[start + k * size:start + (k + 1) * size]
        assert struct.unpack_from("<H", r, 14)[0] == k
        out.append((k, "".join(name(t, k) for t in ZH_NAME_TABLES), struct.unpack_from("<H", r, 20)[0]))
    return out


# 繁中版 San10WPK.exe: the same string pointer table at 0x51D4D8 (item 0 at slot 102 = 0x51D670 -> 赤兔馬, kind 0 at
# slot 502 -> 名馬)
ZH_STRINGS = 0x51D4D8


def zh_items(game_dir) -> dict[int, tuple[str, str]]:
    """item k -> (name, description) of the 繁中版: EXE string slots 102 + k and msg/S10M12PK.s10 entry k"""
    from san9_extras import zh_text
    with open(os.path.join(game_dir, "San10WPK.exe"), "rb") as f:
        exe = f.read()
    msg = read_msg(os.path.join(game_dir, "msg", "S10M12PK.s10"))
    out = {}
    for k in range(ITEMS):
        o = struct.unpack_from("<I", exe, ZH_STRINGS + 4 * (ITEM_NAMES + k))[0] - EXE_BASE
        out[k] = (zh_text(exe[o:exe.index(b"\0", o)]), zh_text(msg[k].rstrip(b"\x05")).replace("\n", "").strip())
    return out


def bios(game_dir) -> dict[int, list[tuple[str, str]]]:
    from san9_extras import zh_text
    msg = read_msg(os.path.join(game_dir, "msg", "S10M13PK.s10"))
    out = {}
    for k, _, bio in zh_persons(game_dir):
        t = zh_text(msg[bio].rstrip(b"\x05")).replace("\n", "").strip()
        if t:
            out[k] = [("單段", t)]
    return out


def bio_names(game_dir) -> dict[int, str]:
    return {k: name for k, name, _ in zh_persons(game_dir)}


@click.command()
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="Steam files (games/san10pk-win)")
@click.option("--out", required=True, type=click.Path(), help="games/san10pk-win/extract")
def san10_extras(game_dir, out):
    """三國志X PK: 寶物 (names, kinds, holders, pictures), event pictures, city and start screens, messages."""
    print(f"{items(game_dir, out)} items")
    print(f"{events(game_dir, out)} messages")
    print(event_pictures(game_dir, out))


if __name__ == "__main__":
    san10_extras()
