"""PKLITE 1.15 decompression (項劉記 DOS MAIN.EXE), ported from the stub without running it."""
import struct


def depklite(exe: bytes) -> bytes:
    """PKLITE 1.15 packed EXE -> load image (segment 0), a port of the decompressor stub (relocations ignored)."""
    img = exe[struct.unpack_from("<H", exe, 8)[0] * 16:]
    stub = img[0x44:0x44 + 0x246]
    t209, t214, t21f, t22f = stub[0x209:], stub[0x214:], stub[0x21F:], stub[0x22F:]
    src = img[0x290:]
    st = {"pos": 2, "bp": struct.unpack_from("<H", src, 0)[0], "dx": 16}

    def byte():
        st["pos"] += 1
        return src[st["pos"] - 1]

    def bit():
        r = st["bp"] & 1
        st["bp"] >>= 1
        st["dx"] -= 1
        if st["dx"] == 0:
            st["bp"] = struct.unpack_from("<H", src, st["pos"])[0]
            st["pos"] += 2
            st["dx"] = 16
        return r

    out = bytearray()
    while True:
        if bit() == 0:
            out.append(byte())
            continue
        bx = bit() << 1 | bit()
        if bx >= 2:
            cx = bx
        else:
            bx = bx << 1 | bit()
            if bx == 0:
                cx = t209[0]
            else:
                bx = bx << 1 | bit()
                if bx >= 5:
                    bx = bx << 1 | bit()
                if bx <= 0xC:
                    cx = t209[bx]
                else:
                    bx = (bx & 3) << 1 | bit()
                    if bx >= 5:
                        bx = bx << 1 | bit()
                    if bx <= 0xC:
                        cx = t214[bx]
                        if cx == 0x19:
                            al = byte()
                            cx += al
                            if al == 0xFF:
                                break
                            if al == 0xFE:
                                continue
                    else:
                        bx = (bx & 3) << 1 | bit()
                        if bx >= 5:
                            bx = bx << 1 | bit()
                        cx = t21f[bx]
        hi = 0
        if cx != 2 and bit() == 0:
            bx = bit() << 2 | bit() << 1 | bit()
            if bx >= 2:
                bx = bx << 1 | bit()
                if bx >= 8:
                    bx = bx << 1 | bit()
                    if bx >= 0x17:
                        bx = bx << 1 | bit()
                        hi = bx & 0xDF
            if not hi and bx < 0x17:
                hi = t22f[bx]
        off = hi << 8 | byte()
        for _ in range(cx):
            out.append(out[-off])
    return bytes(out)
