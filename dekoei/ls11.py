import bitarray
from rich.progress import track

LS11_ENDIAN = 'big'
LS11_MAGIC = [b'LS11', b'Ls12']


def get_codes(data: bytes) -> list[int]:
    """將壓縮資料轉換為字典索引值 list"""
    codes = []
    stream = bitarray.bitarray()
    stream.frombytes(data)
    mask_len, pos, pos_end = 0, 0, len(data)*8
    while True:
        bit = stream[pos]
        mask_len += 1
        pos += 1
        if not bit:
            mask = (1 << mask_len) - 2
            factor = 0
            for _ in range(mask_len):
                factor = (factor << 1) | stream[pos]
                pos += 1
            codes.append(mask+factor)
            # pos += mask_len
            mask_len = 0
        if pos >= pos_end:
            break
    return codes


def recover(codes: list[int], dictionary: bytes, min_copy: int = 3) -> bytes:
    """從字典索引值與字典還原原始數據"""
    recover_data = bytearray()
    delta = 0
    for code in codes:
        if delta > 0:
            nc = min_copy + code  # number of copy
            for _ in range(nc):
                pos = len(recover_data) - delta
                try:
                    recover_data.append(recover_data[pos])
                except IndexError:
                    # TODO: review this exception handler
                    print(f"IndexError: {len(recover_data)=}, {pos=}, {delta=}")
                    recover_data.append(0)
            delta = 0
        elif code < 256:  # replace code with dictionary
            recover_data.append(dictionary[code])
        else:  # copy operation
            delta = code - 256
    return bytes(recover_data)


def ls11_decode_parts(data: bytes, print_only=False) -> list[bytes]:
    if data[:4] not in LS11_MAGIC:
        # TODO(yuxioz): wrong header, log chars here.
        return []

    dictionary = data[16:16+256]
    pos = 16+256
    infos = []
    while data[pos:pos+4] != b'\x00\x00\x00\x00':
        compressed_size = int.from_bytes(data[pos:pos+4], LS11_ENDIAN)
        uncompressed_size = int.from_bytes(data[pos+4:pos+8], LS11_ENDIAN)
        offset = int.from_bytes(data[pos+8:pos+12], LS11_ENDIAN)
        infos.append((compressed_size, uncompressed_size, offset))
        pos += 12

    if print_only:
        for info in infos:
            compressed_size, uncompressed_size, offset = info
            header = data[offset:offset+3]
            if header == b'NPK':
                print(info, 'NPK')
            else:
                print(info)
        return []

    decoded_data = []
    # for i in track(range(len(infos)), description="Decoding... "):
    # rich.errors.LiveError: Only one live display may be active at once
    for i in range(len(infos)):
        compressed_size, uncompressed_size, offset = infos[i]
        compressed_data = data[offset:offset+compressed_size]
        if compressed_size == uncompressed_size:
            decoded_data.append(compressed_data)
            continue
        codes = get_codes(compressed_data)
        recover_data = recover(codes, dictionary)
        decoded_data.append(recover_data[:uncompressed_size])

    return decoded_data


def ls11_decode(data: bytes, print_only=False) -> bytes:
    decoded_data = ls11_decode_parts(data, print_only)
    if len(decoded_data) == 0:
        return b''

    return b''.join(decoded_data)


def cz11_decode(data: bytes) -> bytes:
    """Text and data of a KOEI CZ11-packed X68000 executable (信長の野望・覇王伝 MAIN.Z, unpacked by SYS/IPL113.R):
    a 0x1C-byte X header, then 'CZ11', u32 text size, u32 data size, ..., the 256-byte dictionary at +0x24 and
    LS11 codes from +0x126. The result starts at the X header's base address."""
    body = data[0x1C:]
    if body[:4] != b'CZ11':
        raise ValueError('not a CZ11 file')
    size = int.from_bytes(body[4:8], LS11_ENDIAN) + int.from_bytes(body[8:12], LS11_ENDIAN)
    return recover(get_codes(body[0x126:]), body[0x24:0x124])[:size]


def cz10_decode(data: bytes) -> bytes:
    """As cz11_decode, for CZ10 (三国志III, 太閤立志伝 MAIN.Z, unpacked by SYS/IPL101.R): the copy length is the
    code itself, without the 3 added."""
    body = data[0x1C:]
    if body[:4] != b'CZ10':
        raise ValueError('not a CZ10 file')
    size = int.from_bytes(body[4:8], LS11_ENDIAN) + int.from_bytes(body[8:12], LS11_ENDIAN)
    return recover(get_codes(body[0x126:]), body[0x24:0x124], min_copy=0)[:size]


def lw11_decode_files(data: bytes) -> dict[str, bytes]:
    """LW11 archive (提督の決断II PK PACK.LZW): LS11 coding, but each table entry is a 16-byte file name before
    the (compressed size, uncompressed size, offset) triple, plus 4 more bytes. Names are upper-cased."""
    dictionary = data[16:16+256]
    pos = 16+256
    files = {}
    while data[pos] != 0:
        name = data[pos:pos+16].split(b'\0')[0].decode('ascii').upper()
        compressed_size, uncompressed_size, offset = (int.from_bytes(data[pos+k:pos+k+4], LS11_ENDIAN) for k in (16, 20, 24))
        compressed_data = data[offset:offset+compressed_size]
        if compressed_size == uncompressed_size:
            files[name] = compressed_data
        else:
            files[name] = recover(get_codes(compressed_data), dictionary)[:uncompressed_size]
        pos += 32
    return files
