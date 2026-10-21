import os
import click

##############################################################################


@click.group()
def nobu3():
    """
    信長之野望II 戰國群雄傳

    "name": "信長之野望II 戰國群雄傳",
    "face_file": "KAODATA.DAT", # KAO_OE 僅有前 28 人
    "face_size": (64, 80),
    "face_count": 177, # 177 之後是大眾臉
    "double_height": True,
    "palette": ['#000000', '#55FF55', '#FF5555', '#FFFF55', '#5555FF', '#55FFFF', '#FF55FF', '#FFFFFF']
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def nobu3_face(face_file, out_dir, prefix):
    pass


@click.command(help='人物資料解析')
def nobu3_person():
    """
    人物資料解析
    """
    pass


nobu3.add_command(nobu3_face, 'face')
nobu3.add_command(nobu3_person, 'person')

##############################################################################


@click.group()
def nobu4():
    """
    信長之野望 武將風雲錄

    "name": "武將風雲錄",
    "face_file": "KAODATA.DAT",
    "face_size": (64, 80),
    "palette": ['#000000', '#00AA00', '#AA0000', '#FFFF00', '#0000AA', '#00AAAA', '#AA00AA', '#FFFFFF']
    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def nobu4_face(face_file, out_dir, prefix):
    pass


@click.command(help='人物資料解析')
def nobu4_person():
    """
    人物資料解析
    """
    pass


nobu4.add_command(nobu4_face, 'face')
nobu4.add_command(nobu4_person, 'person')

##############################################################################


@click.group()
def nobu5():
    """
    信長之野望 霸王傳

    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def nobu5_face(face_file, out_dir, prefix):
    pass


@click.command(help='人物資料解析')
def nobu5_person():
    """
    人物資料解析
    """
    pass


def nobu5_test(filename: str):
    # sep = b'\x00\x00\x00\x00\x40\x00\x50\x00'
    sep = b'\x40\x00\x50\x00'
    lsep = len(sep)
    tt = dict()
    with open(filename, 'rb') as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        f.seek(0)

        bs = f.read()
        i = 0
        old_pos = 0
        pos = bs.find(sep)
        while pos != -1:
            ss = pos+lsep-old_pos
            if ss in tt:
                tt[ss] += 1
            else:
                tt[ss] = 1
            f.seek(old_pos)
            nn = f.read(1)
            print('[{:04d}] {:8d}  {:8d} {:2d}(byte size)'.format(i, pos, ss, int.from_bytes(nn, 'big')))
            i += 1
            old_pos = pos + lsep
            pos = bs.find(sep, old_pos)
        print('[{:04d}] {:8d}  {:8d}'.format(i, pos, file_size-old_pos))

        # for k in sorted(tt.keys()):
        #     print("{:4d} : {:4d}".format(k, tt[k]))


nobu5.add_command(nobu5_face, 'face')
nobu5.add_command(nobu5_person, 'person')

# GT1G0500 2C400000 20000000 01000000 00000000 00000000 00000000 04000000 10016600 00102100 B0-1 (64)
# GT1G0500 2C400000 20000000 01000000 00000000 00000000 00000000 04000000 10016600 00102100 B0-2
# G1TG0050 00000030 00000020 00000001 00000001 00000000 00000000 00000004 01010000 00011200 FF405154 <- 48bytes
# GT1G0500 2C100000 20000000 01000000 00000000 00000000 00000000 04000000 10015500 00102100 B1-1 (32)
# GT1G0500 2C001000 20000000 01000000 00000000 00000000 00000000 04000000 10019900 00102100 B2-1 (512)
#          ^^x4
#          16428
#          block size

##############################################################################


@click.group()
def nobu6():
    """
    信長之野望 天翔記

    """
    pass


@click.command(help='顏 CG 解析')
@click.option('-f', '--face', 'face_file', help="頭像檔案", required=True)
@click.option('--out_dir', 'out_dir', default='_output', help='output directory')
@click.option('--prefix', 'prefix', default='', help='filename prefix of output files')
def nobu6_face(face_file, out_dir, prefix):
    pass


@click.command(help='人物資料解析')
def nobu6_person():
    """
    人物資料解析
    """
    pass


nobu6.add_command(nobu6_face, 'face')
nobu6.add_command(nobu6_person, 'person')

##############################################################################


def _nobu_stats(game, game_dir):
    """(labels, rows of (scenario, name, *stats)) of one 信長の野望 release; see notes/nobuN.md「能力」."""
    import fnmatch
    import glob
    import koei_games as k

    def files(pattern):
        return sorted(f for f in glob.glob(os.path.join(game_dir, "*")) if fnmatch.fnmatch(os.path.basename(f).lower(), pattern.lower()))

    if game == "nobu2-pc88":
        import pc88
        with open(os.path.join(game_dir, "DISK_A.D88"), "rb") as f:
            data = pc88.cpm_files(pc88.d88_image(f.read()))["DATA50S.DAT"]
        return k.NOBU2_STATS, [("50國", *r[1:]) for r in k.load_nobu2_pc88_stats(data)]
    if game == "nobu2-x68":
        with open(os.path.join(game_dir, "DATA50.DAT"), "rb") as f:
            return k.NOBU2_STATS, [("50國", *r[1:]) for r in k.load_nobu2_pc88_stats(f.read(), x68=True)]
    if game in ("nobu3-pc98", "nobu3-pc88", "nobu3-x68", "nobu3-win"):
        tables = k.load_nobu3_pc98_stats(game_dir, pc88=game == "nobu3-pc88", x68=game == "nobu3-x68",
                                         win=game == "nobu3-win")
        return k.NOBU3_STATS, [(f"SNDATA{n}", *r) for n, t in zip((1, 2), tables) for r in t]
    if game == "nobu4-pc98":
        tables = k.load_nobu4_pc98_stats(game_dir)
        return k.NOBU4_STATS, [(f"SNDATA{i // 2 + 1}{'T' if i % 2 else ''}", *r) for i, t in enumerate(tables) for r in t]
    if game in ("nobu5-pc98", "nobu5-x68"):
        x68, rows = game == "nobu5-x68", []
        for n in (1, 2, 3):
            with open(os.path.join(game_dir, f"SN{n}.NB5"), "rb") as f:
                rows += [(f"SN{n}", *r[1:]) for r in k.load_nobu5_pc98_stats(f.read(), x68)]
            with open(os.path.join(game_dir, f"S{n}T.NB5"), "rb") as f:
                rows += [(f"S{n}T", *r[1:]) for r in k.load_nobu5_pc98_arrival_stats(f.read(), x68)]
        return k.NOBU5_STATS, rows
    if game == "nobu5pk-win":
        with open(os.path.join(game_dir, "Nobunaga5WPK.exe"), "rb") as f:
            exe = f.read()
        rows = []
        for n, name in enumerate(k.NOBU5_WIN_SCENARIOS):
            with open(os.path.join(game_dir, name), "rb") as f:
                rows += [(name, *r[1:]) for r in k.load_nobu5_win_stats(f.read())]
            rows += [(f"{name} 後登場", *r[1:]) for r in k.load_nobu5_win_arrival_stats(exe, n)]
        return k.NOBU5_STATS, rows
    if game in ("nobu6-pc98", "nobu6pk-pc98"):
        ext, years = ("N6P", (1534, 1560, 1571, 1582, 1546, 1599)) if game == "nobu6pk-pc98" else ("NB6", (1534, 1560, 1571, 1582))
        with open(os.path.join(game_dir, f"SNDATA.{ext}"), "rb") as f, open(os.path.join(game_dir, f"TAIKI.{ext}"), "rb") as g:
            tables = k.load_nobu6_pc98_stats(f.read(), g.read())
        return k.NOBU6_PC98_STATS, [(f"{y}{'' if r[0] is not None else ' 後登場'}", *r[1:]) for y, t in zip(years, tables)
                                    for r in t]
    if game in ("nobu7-win", "nobu7pk-win"):
        enc = "cp932" if game == "nobu7pk-win" else "big5"
        return k.NOBU7_WIN_STATS, [(os.path.basename(f), *r[1:]) for f in files("Sndata*.nb7")
                                   for r in k.load_nobu7_win_stats(f, enc)]
    if game == "nobu8pk-win":
        return k.NOBU8_WIN_STATS, [(os.path.basename(f), *r[1:]) for f in files("SCEDA*.NB8")
                                   for r in k.load_nobu8_win_stats(f)]
    if game == "nobu9pk-win":
        with open(os.path.join(game_dir, "Nobunaga9WPK.exe"), "rb") as f:
            exe = f.read()
        return k.NOBU9_WIN_STATS, [(os.path.basename(f), *r[1:]) for f in files("SCEDA*.NB9")
                                   for r in k.load_nobu9_win_stats(f, exe)]
    loaders = {"nobu10pk-win": ("SCEDAT*.NBX", k.load_nobu10_win_stats, k.NOBU10_WIN_STATS),
               "nobu11pk-win": ("DBSCEDA*.N11", k.load_nobu11_win_stats, k.NOBU11_WIN_STATS),
               "nobu12pk-win": ("sceda*.n12", k.load_nobu12_win_stats, k.NOBU12_WIN_STATS),
               "nobu13pk-win": ("sceda*.n13", k.load_nobu13_win_stats, k.NOBU13_WIN_STATS)}
    pattern, load, labels = loaders[game]
    return labels, [(os.path.basename(f), *r[1:]) for f in files(pattern) for r in load(f)]


@click.command(help="信長の野望 人物能力（CSV）")
@click.argument("game")
@click.option("--game-dir", "game_dir", required=True, help="遊戲目錄（劇本檔所在處）")
@click.option("-s", "--scenario", help="只列這個劇本（檔名或表名）")
def nobu_person(game, game_dir, scenario):
    """
    GAME 是 dataset id：nobu2-pc88、nobu2-x68、nobu3-pc98（-pc88、-x68、-win）、nobu4-pc98、nobu5-pc98（-x68）、nobu5pk-win、
    nobu6-pc98、nobu6pk-pc98、nobu7-win、nobu7pk-win、
    nobu8pk-win、nobu9pk-win、nobu10pk-win…nobu13pk-win

    dekoei.py nobu-person nobu4-pc98 --game-dir ../games/nobu4-pc98 -s SNDATA1
    """
    labels, rows = _nobu_stats(game, game_dir)
    print(",".join(["劇本", "姓名"] + list(labels)))
    for row in rows:
        if scenario is None or row[0] == scenario:
            print(",".join(map(str, row)))
