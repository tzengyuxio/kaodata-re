"""Small helpers shared by the game modules: reading files and little-endian numbers, NUL-terminated strings, half-width
kana and CSV output. New code uses these instead of local copies (docs/backlog/code-consolidation.md)."""
import csv
import os
import struct
import unicodedata


def read_file(*parts) -> bytes:
    """The bytes of os.path.join(*parts)."""
    with open(os.path.join(*parts), "rb") as f:
        return f.read()


def u16(b, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


def cstr(b: bytes, encoding: str = "cp932", errors: str = "strict", nfkc: bool = False) -> str:
    """The text before the first NUL; nfkc=True also folds half-width kana and full-width ASCII (NFKC)."""
    s = b.split(b"\0", 1)[0].decode(encoding, errors)
    return unicodedata.normalize("NFKC", s) if nfkc else s


def fold_kana(s: str, katakana: bool = False) -> str:
    """Half-width kana to full-width (NFKC), as hiragana unless katakana: KOEI text shows half-width kana as hiragana
    by default and switches to katakana with ESC K."""
    s = unicodedata.normalize("NFKC", s)
    return s if katakana else "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def write_csv(path: str, header, rows) -> int:
    """A UTF-8-BOM CSV of header and rows, creating the directory; returns the row count."""
    rows = list(rows)
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return len(rows)


def write_dict_csv(path: str, rows, header=None) -> int:
    """A UTF-8-BOM CSV of dict rows. Columns are header (other keys dropped), or else every key in first-seen order."""
    rows = list(rows)
    if header is None:
        header = []
        for r in rows:
            header += [k for k in r if k not in header]
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)
