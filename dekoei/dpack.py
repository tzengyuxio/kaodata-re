"""DPACK archives of KOEI's PC-98 HD installers (INSTALL.SYS `UNPACK DPACKn.xxx`).

A port of INSTALL.EXE's UNPACK (提督の決断III, 0x9B20); see notes/dpack.md.
"""
import sys


class Bits:
    """MSB-first bit reader."""

    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos * 8

    def get(self, n: int) -> int:
        v = 0
        for _ in range(n):
            v = v << 1 | (self.data[self.pos >> 3] >> (7 - (self.pos & 7))) & 1
            self.pos += 1
        return v


class Huffman:
    def __init__(self, lengths: list[int], codes: list[int]):
        self.table = {(l, c): s for s, (l, c) in enumerate(zip(lengths, codes)) if l}

    def decode(self, bits: Bits) -> int:
        code = 0
        for length in range(1, 18):
            code = code << 1 | bits.get(1)
            sym = self.table.get((length, code))
            if sym is not None:
                return sym
        raise ValueError("bad Huffman code")


def read_tree(bits: Bits, n: int) -> Huffman:
    """Tree sent in preorder (0x827A): bit 1 = node (left, then right = 1), bit 0 = leaf + symbol."""
    sym_bits = n.bit_length() - 1
    lengths, codes = [0] * n, [0] * n

    def walk(depth, code):
        if bits.get(1):
            walk(depth + 1, code << 1)
            walk(depth + 1, code << 1 | 1)
        else:
            s = bits.get(sym_bits)
            lengths[s], codes[s] = depth, code

    walk(0, 0)
    return Huffman(lengths, codes)


def tree_from_lengths(lengths: list[int]) -> Huffman:
    """0x8122/0x81E0: from the deepest level up, pair the nodes of that depth in index order."""
    n = len(lengths)
    depth = list(lengths) + [0] * (n + 1)
    parent, right = {}, {}
    nxt = n
    for level in range(max(lengths), 0, -1):
        prev = None
        for i in range(2 * n + 1):
            if depth[i] != level:
                continue
            if prev is None:
                prev = i
                continue
            parent[prev] = parent[i] = nxt
            right[nxt] = i
            depth[nxt] = level - 1
            nxt += 1
            prev = None
    codes = [0] * n
    for s in range(n):
        node, k = s, 0
        while node in parent:
            if right[parent[node]] == node:
                codes[s] |= 1 << k
            node = parent[node]
            k += 1
    return Huffman(lengths, codes)


def read_header(bits: Bits) -> dict | None:
    """0x8BA2: 4-bit opcodes up to 15 (block data follows) or 14 (end of volume)."""
    h = {"flags": 0, "dist_bits": 12, "more": 0, "size": 0, "name": None}
    while True:
        op = bits.get(4)
        if op == 0:
            h["flags"] |= 0x8000
        elif op == 1:
            h["flags"] = 0xB5
        elif op == 2:
            h["flags"] |= 1
            if not bits.get(1):
                h["flags"] |= 0x14
            else:
                h["dist_bits"] = bits.get(4)
                if h["dist_bits"] != 12:
                    h["flags"] |= 2
        elif op == 3:
            h["flags"] |= 0x30 | (0x80 if bits.get(1) else 0x40)
        elif op == 5:
            h["more"] = bits.get(1)  # the file continues in the next block
            h["size"] = bits.get(17)  # next block at block start + size - 1
        elif op == 7:
            name = bytearray()
            while len(name) < 13 and (c := bits.get(8)):
                name.append(c)
            h["name"] = name.decode("cp932")
            h["attr"], h["date"], h["time"] = bits.get(8), bits.get(16), bits.get(16)
        elif op == 14:
            return None
        elif op == 15:
            return h
        else:
            raise ValueError(f"unsupported DPACK opcode {op}")


def decode_block(bits: Bits, h: dict) -> bytes:
    """0x8F62: u16 count - 1, trees, then LZSS symbols (< 0x100 literal, else length - 3 + 0x100)."""
    count = bits.get(16) + 1
    flags = h["flags"]
    lit = dist = None
    if flags & 0x20:
        if flags & 0x80:  # code lengths of the 512 symbols, coded with a 16-symbol tree (0x8840)
            len_tree = read_tree(bits, 16)
            skips = {}
            for _ in range(bits.get(4)):
                at = bits.get(9)
                skips[at] = bits.get(9)
            lengths = [0] * 0x200
            s = 0
            while s < 0x200:
                if s in skips:
                    s += skips[s] + 1
                    continue
                lengths[s] = len_tree.decode(bits)
                s += 1
            lit = tree_from_lengths(lengths)
        else:
            lit = read_tree(bits, 0x200)
    elif flags & 0x8000:  # stored
        start = (bits.pos + 7) >> 3
        bits.pos = (start + count) * 8
        return bits.data[start:start + count]
    if flags & 4:  # distance = three nibbles, one tree each
        dist = [read_tree(bits, 16) for _ in range(3)]
    out = bytearray()
    while len(out) < count:
        s = lit.decode(bits) if lit else bits.get(9)
        if s < 0x100:
            out.append(s)
            continue
        if flags & 2:
            d = bits.get(h["dist_bits"]) if bits.get(1) else bits.get(12)
        elif dist:
            d = 0
            for t in dist:
                d = d << 4 | t.decode(bits)
        else:
            d = bits.get(12)
        for _ in range(s - 0xFD):
            out.append(out[-d - 1])
    return bytes(out)


def unpack(*volumes: bytes):
    """Yield (name, data) for the files of DPACK1, DPACK2, ... (a file can span volumes)."""
    name, buf = None, bytearray()
    for data in volumes:
        pos = 0
        while pos < len(data):
            bits = Bits(data, pos)
            h = read_header(bits)
            if h is None:
                break
            name = h["name"] or name
            buf += decode_block(bits, h)
            if not h["more"]:
                yield name, bytes(buf)
                buf = bytearray()
            pos += h["size"] - 1


if __name__ == "__main__":
    import os

    if len(sys.argv) < 3:
        sys.exit("usage: dpack.py OUTDIR DPACK1 [DPACK2 ...]")
    os.makedirs(sys.argv[1], exist_ok=True)
    for name, data in unpack(*(open(p, "rb").read() for p in sys.argv[2:])):
        open(os.path.join(sys.argv[1], name), "wb").write(data)
        print(name, len(data))
