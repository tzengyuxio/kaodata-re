"""PC-8801 disk images (D88) and the KOEI 2D disk layout, see notes/san1.md and notes/nobu2.md."""
import struct

SECTOR = 256
TRACK = 16 * SECTOR


def d88_image(data: bytes) -> bytes:
    """Linear 2D image (40 cylinders x 2 heads x 16 x 256 bytes) of a D88 file.

    Sectors outside ids 1-16 are copy-protection extras (Sangokushi V1 disk A has 245-247 on cylinders 1-9)
    and are left out."""
    sectors = {}
    for track_ofs in struct.unpack_from("<164I", data, 0x20):
        if not track_ofs or track_ofs >= len(data):
            continue
        p = track_ofs
        count = struct.unpack_from("<H", data, p + 4)[0]
        for _ in range(count):
            c, h, r = data[p], data[p + 1], data[p + 2]
            size = struct.unpack_from("<H", data, p + 14)[0]
            if 1 <= r <= 16:
                sectors[(c, h, r)] = data[p + 16:p + 16 + size]
            p += 16 + size
    return b"".join(sectors[k] for k in sorted(sectors))


def cpm_files(image: bytes, base: int = 0x4000, block: int = 2048) -> dict[str, bytes]:
    """Files of the CP/M-like directory KOEI used on 2D disks (YDOS 2.2): 32-byte entries at `base`,
    16 one-byte block numbers per entry, blocks counted from `base`."""
    extents = {}
    for o in range(base, base + block, 32):
        e = image[o:o + 32]
        if e[0] == 0xE5 or not any(e[1:12]):
            continue
        raw = bytes(c & 0x7F for c in e[1:12]).decode("latin1")
        if not all(0x20 <= ord(c) < 0x7F for c in raw):
            continue
        name = (raw[:8].strip() + "." + raw[8:].strip()).strip(".")
        extents.setdefault(name, []).append((e[12], e[15], [b for b in e[16:] if b]))
    files = {}
    for name, ents in extents.items():
        data = b""
        for ex, records, blocks in sorted(ents):
            # one entry covers two logical 16 KB extents; ex is the last one, records counts within it
            chunk = b"".join(image[base + b * block:base + (b + 1) * block] for b in blocks)
            data += chunk[:((ex % 2) * 128 + records) * 128]
        files[name] = data
    return files


def brg_pixels(raw: bytes, w: int, double: bool = True) -> bytes:
    """Colour indexes (B = bit 0, R = bit 1, G = bit 2) of a picture stored as B, R, G plane bytes per 8 pixels
    (the order the KOEI blitters write GVRAM planes 0x5C-0x5E), each row shown twice (200-line screen) unless
    `double` is False."""
    rows = []
    for o in range(0, len(raw), w * 3):
        row = bytearray()
        for x in range(o, o + w * 3, 3):
            b, r, g = raw[x:x + 3]
            row += bytes((b >> k & 1) | (r >> k & 1) << 1 | (g >> k & 1) << 2 for k in range(7, -1, -1))
        rows.append(bytes(row) * (2 if double else 1))
    return b"".join(rows)
