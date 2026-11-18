"""武將列傳 (officer biographies) of the Traditional Chinese 三國志 releases, as JSONL for koei-wiki: one line per
section, {"dataset", "id", "name", "lang", "kind", "text"}. id is the person id of the kaodata dataset; kind is 簡介
(the one-line summary), 演義, 史實, or 單段 for a biography that is not split. Sections that only say 無記述 are left
out. Formats are in notes/<game>.md「列傳」."""
import json
import os
import struct

import click

import ls11
import utils
from wiki_datasets import datasets, module

KINDS = {"演義", "史實"}


def sections(intro: str, parts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """(kind, text) of a biography: the summary, then the parts, without the empty and 無記述 ones."""
    out = [("簡介", intro.strip())] + [(k, t.strip()) for k, t in parts]
    return [(k, t) for k, t in out if t and t.rstrip("。") != "無記述"]


def split_marked(t: str) -> list[tuple[str, str]]:
    intro, *parts = t.split("\0")
    if not parts:
        return sections("", [("單段", intro)])
    assert len(parts) == 2
    return sections(intro, list(zip(("演義", "史實"), parts)))


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


def records(dataset, game_dir):
    m = module(dataset, "bios")
    names, lang = m.bio_names(game_dir), m.BIO_LANG
    for n, parts in sorted(m.bios(game_dir).items()):
        for kind, text in parts:
            yield {"dataset": dataset, "id": n, "name": names.get(n, ""), "lang": lang, "kind": kind, "text": text}


@click.command()
@click.argument("dataset", type=click.Choice(sorted(datasets("bios"))))
@click.option("--game-dir", "game_dir", required=True)
@click.option("--out", "out", required=True, help="輸出目錄（寫 <dataset>.jsonl）")
def biography(dataset, game_dir, out):
    """匯出武將列傳（JSONL，給 koei-wiki；三國志是繁中版，信長の野望照主資料集的語言）"""
    os.makedirs(out, exist_ok=True)
    out, n = os.path.join(out, f"{dataset}.jsonl"), 0
    with open(out, "w", encoding="utf-8") as f:
        for r in records(dataset, game_dir):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    print(f"{out}: {n} sections")
