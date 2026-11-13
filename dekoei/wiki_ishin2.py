"""維新の嵐 幕末志士伝 (ishin2-win) for koei-wiki: persons (koei-persons/1). id is the kaodata ishin2-win id, the
number of the 480-byte person record in ISHIN2.EXE (the generic roles and 589 are not persons, as in
kaodata_export.build_ishin2_win). Only the Japanese release exists. Field sources: notes/ishin2.md「人物：ISHIN2.EXE」
「koei-wiki 匯出」."""
import os
import struct

import kaodata_export as ke
import koei_games as kg

DATASET = "ishin2-win"
# ISHIN2.EXE file offsets: 811 facilities of 76 bytes (+8 name), 40 organisations of 148 bytes (+0 name, +4 kind
# 0 幕府 1 朝廷 2 藩 3 隊), and the 28 身分 names as (name pointer, grade) pairs (将軍 … 外国商人, 僧侶, 芸妓, 町人,
# アメリカ人 … ロシア人)
PLACES, PLACE_SIZE, N_PLACES = 0x1592D8, 76, 811
ORGS, ORG_SIZE, N_ORGS = 0x10D218, 148, 40
RANKS, N_RANKS = 0x10F2A0, 28


def _exe(game_dir):
    with open(os.path.join(game_dir, "ISHIN2.EXE"), "rb") as f:
        exe = f.read()
    pe = struct.unpack_from("<I", exe, 0x3C)[0]
    nsec, opt = struct.unpack_from("<H", exe, pe + 6)[0], struct.unpack_from("<H", exe, pe + 20)[0]
    base = struct.unpack_from("<I", exe, pe + 52)[0]
    secs = [struct.unpack_from("<IIII", exe, pe + 24 + opt + 40 * i + 8) for i in range(nsec)]

    def text(o):
        va = struct.unpack_from("<I", exe, o)[0]
        if not va:
            return ""
        p = next(va - base - rva + raw for _, rva, size, raw in secs if 0 <= va - base - rva < size)
        return exe[p:exe.index(b"\0", p)].decode("cp932")
    return exe, text


def persons(game_dir):
    exe, text = _exe(game_dir)
    places = [text(PLACES + i * PLACE_SIZE + 8) for i in range(N_PLACES)]
    orgs = [text(ORGS + i * ORG_SIZE) for i in range(N_ORGS)]
    ranks = [text(RANKS + 8 * i) for i in range(N_RANKS)]
    start, size, count = kg.ISHIN2_WIN_PERSONS
    rows = []
    for i in range(count):
        if i in ke.ISHIN2_WIN_GENERIC | ke.ISHIN2_WIN_SKIP:
            continue
        o = start + i * size
        surname, given, alias_s, alias_g, common = (text(o + 4 * k) for k in range(5))
        born, died, sex, _, home = struct.unpack_from("<5i", exe, o + 20)  # +36: the first of the +108 list
        org, rank = struct.unpack_from("<2i", exe, o + 52)
        titled = surname in ke.ISHIN2_WIN_TITLES
        row = {"id": i, "name": given if titled else surname + given}
        if surname and not titled and given:
            row["familyName"] = surname
        row["born"], row["died"] = born, died
        more = {"性別": "男" if sex == 1 else "女", "身分": ranks[rank]}
        if org >= 0:
            more["所属組織"] = orgs[org]
        row["more"] = more
        game = {}
        if alias_s or alias_g:
            game["別名"] = alias_s + alias_g
        if common:
            game["通称"] = common
        if home >= 0:
            game["本拠"] = places[home]
            row["uncertain"] = ["game.本拠"]
        if game:
            row["game"] = game
        rows.append(row)
    return rows
