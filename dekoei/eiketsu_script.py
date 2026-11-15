"""三國志英傑傳 (eiketsu-dos, eiketsu-pc98): scenario scripts SNRnD.R3 / SNRnM.R3. Format and evidence:
notes/eiketsu.md「劇本腳本（SNRnD／SNRnM）」. Addresses are DOS MAIN.EXE load-image offsets (file - 0x6A00).

- SNRnD.R3: LS11, one part per section. A part starts with u16 block offsets ended by FFFF. A block is a list of
  10-byte trigger records [type][group][u16 a][u16 b][u16 c][u16 code offset from the block start] ended by 10 x FF,
  then bytecode; every trigger's code ends with FF. Interpreter 0x14C46, operand lengths DGROUP 0x1A06.
- SNRnM.R3: u16 start offset per section, message offsets in the bytecode are relative to it. Op 00 messages are
  (u16 speaker, NUL-terminated text) pairs ended by speaker FFFF; the other message ops point at one NUL string.
"""
import csv
import os

import click
from PIL import Image, ImageDraw

from ls11 import ls11_decode_parts
import koei_games

# Operand bytes after the opcode: skip table DGROUP 0x1A06 (62 entries), with the interpreter's own reads where the
# table is wrong (03, 22 are > 255; 1D reads 4 but the table says 2). 20, 21, 32 have variable length.
OPLEN = list(bytes.fromhex('02050119000000020202050204020201' '04020000020204010202020105020000'
                           '00008700030203030300010300020503' '0200000000030003010303020201'))
OPLEN[0x03] = 0x119
OPLEN[0x22] = 0x187
OPLEN[0x1D] = 4

# name, operand layout (p person u16, w u16, b u8, m dialogue msg, t text msg, M map word), note
OPS = {
    0x00: ('talk', 'm', ''),
    0x01: ('walk', 'pbbb', 'scene person to x, y, facing; consecutive 01 run together'),
    0x02: ('menu_add', 'b', 'メニュー追加'),
    0x03: ('hex_setup', '', 'ＨＥＸ設定: battle conditions + 30 player slots'),
    0x04: ('nop04', '', '天候 (debug string only)'),
    0x05: ('show_scene', '', ''),
    0x06: ('op06', '', ''),
    0x07: ('picture', 'bb', ''),
    0x08: ('text_center', 't', 'multi-line text'),
    0x09: ('map', 'M', 'マップ選択: 30xx battle, 20xx place, 1000 world map'),
    0x0A: ('place', 'pbbb', 'scene person at x, y, facing'),
    0x0B: ('text_title', 't', ''),
    0x0C: ('op0c', 'wt', ''),
    0x0D: ('text_corner', 't', ''),
    0x0E: ('text_center2', 't', ''),
    0x0F: ('goto_block', 'b', 'ブロック（シーン）移動'),
    0x10: ('duel', 'pp', '一騎討ち a vs b'),
    0x11: ('hex_end', 'M', 'ＨＥＸ終了: leave the battle for map'),
    0x12: ('event_end', '', 'イベント終了'),
    0x13: ('parallel_exit', '', '並列制御から抜け出します'),
    0x14: ('set_flag', 'bb', 'flag, value'),
    0x15: ('if_answer', 'bb', 'if the yes/no answer of the previous 00 == a, skip b instructions'),
    0x16: ('no_hex_combat', 'ww', 'ＨＥＸ部隊戦闘は使えなくなりました'),
    0x17: ('input_mode', 'b', 'ユーザー入力制御'),
    0x18: ('withdraw', 'p', ''),
    0x19: ('op19', 'bb', 'no handler'),
    0x1A: ('join', 'p', '%s の部隊が参戦します (hidden unit appears)'),
    0x1B: ('item', 'b', 'アイテム %d を追加します'),
    0x1C: ('set_ai', '', '武将 %s のアルゴ %d を設定します'),
    0x1D: ('prev_map', 'wbb', '前マップ設定'),
    0x1E: ('clear_chars', '', ''),
    0x1F: ('townsfolk', '', '一般人配置'),
    0x20: ('op20', '', 'n (bit 7 = reset) then n bytes'),
    0x21: ('if_flags', '', 'skip n instructions unless all flags in list 1 are set and all in list 2 clear'),
    0x22: ('deploy', '', '30 slots of 13 bytes'),
    0x23: ('sortie_select', '', ''),
    0x24: ('set_country', 'pb', '%s の所属国を %d にします'),
    0x25: ('choice', 't', 'menu; option k runs the k-th following auto group'),
    0x26: ('map_chip', 'bbb', 'マップチップ変更'),
    0x27: ('screen_cg', 'bbb', '画面効果ＣＧ'),
    0x28: ('set_country_no', 'pb', '国番号変更 %s : %d'),
    0x29: ('game_over', '', 'ゲームオーバー'),
    0x2A: ('ending', 'b', 'エンディング'),
    0x2B: ('data_op', 'bw', 'データ操作'),
    0x2C: ('redraw', '', '画面書換'),
    0x2D: ('halve', 'bb', '半減処理'),
    0x2E: ('reset_pos', 'pbbb', 'ユーザー位置再設定'),
    0x2F: ('set_cg', 'pb', '%s のＣＧを %d に変更します'),
    0x30: ('goal_text', 't', 'text kept in the script state (+0x3C8)'),
    0x31: ('op31', '', 'no handler'),
    0x32: ('op32', '', 'n then n bytes (state +0x549)'),
    0x33: ('op33', '', ''),
    0x34: ('op34', '', ''),
    0x35: ('op35', 'pb', ''),
    0x36: ('op36', '', ''),
    0x37: ('op37', 'pb', ''),
    0x38: ('bgm', 'b', ''),
    0x39: ('level_up', 'pb', ''),
    0x3A: ('change_class', 'pb', ''),
    0x3B: ('op3b', 'bb', ''),
    0x3C: ('op3c', 'w', ''),
    0x3D: ('op3d', 'b', ''),
    0xFF: ('end', '', ''),
}

# Trigger types (record byte 0 & 0x7F) and the arguments compared with record a/b/c; matchers 0x164EB-0x166CF
TRIGGERS = {
    0: 'auto', 1: 'check', 2: 'scene2', 3: 'scene3', 4: 'adjacent', 5: 'scene5', 6: 'at_cell',
    7: 'victory', 8: 'defeat', 9: 'turn', 0xB: 'in_area', 0xC: 'defeated',
}
ANY_PLAYER = 0x400  # person 0x400 = any player unit (trigger) / slot chosen by the player (op 03)

# HEXZMAP part = battle number (09 xx 30); names from the xycq forum list (tid 239493), checked against the maps
BATTLES = ('汜水關 虎牢關 廣川 信都 巨鹿 清河 界橋 北海 徐州 小沛 泰山 夏丘 彭城 淮南 下邳 廣陵 '
           '兗州 古城 潁川 汝南 江夏 南陽 博望坡 新野 襄陽 長坂坡I 長坂坡II 江陵 公安 桂陽 武陵 零陵 '
           '長沙 雒 成都 瓦口關I 瓦口關II 葭萌關I 葭萌關II 定軍山 天蕩山 漢水 陽平關 西陵 夷陵 麥 南郡 新野II '
           '宛I 宛II 許昌I 許昌II 陳倉 長安 洛陽 鄴I 鄴II 鄴III').split()
CHAPTERS = ['序章', '第一章', '第二章', '第三章', '第四章']
AI = {0: '防守', 1: '攻擊', 2: '堅守', 3: '追擊武將', 4: '行軍到座標', 5: '追隨武將', 6: '逃到座標'}
FACING = {1: '右', 3: '左'}
# PC-98 place-name gaiji (EB xx) in SNRnM.R3 missing from koei_games.EIKETSU_PC98_GAIJI, read off the DOS Chinese
# text of the same messages (下邳, 冀州の鄴, 雒城, 涪城, 宛城, 潁川, 兗州); FONT.R3 glyph = xx - 0x9F up to CE,
# xx - 0xA1 for D7-D9, xx - 0xA2 for E4
EIKETSU_PC98_PLACE_GAIJI = {0xAA: '兗', 0xBF: '邳', 0xCC: '邳', 0xCD: '宛', 0xD7: '鄴', 0xD8: '雒', 0xD9: '涪', 0xE4: '潁'}


def u16(d, i):
    return d[i] | d[i + 1] << 8


def oplen(d, p) -> int:
    op = d[p]
    if op == 0x20:
        return 2 + (d[p + 1] & 0x7F)
    if op == 0x21:
        n1 = d[p + 2]
        return 4 + n1 + d[p + 3 + n1]
    if op == 0x32:
        return 2 + d[p + 1]
    if op == 0xFF:
        return 1
    if op >= len(OPLEN):
        raise ValueError(f'unknown opcode {op:02x} at {p:x}')
    return 1 + OPLEN[op]


def parse_part(d: bytes) -> list[dict]:
    offs = []
    while u16(d, 2 * len(offs)) != 0xFFFF:
        offs.append(u16(d, 2 * len(offs)))
    blocks = []
    for s, e in zip(offs, offs[1:] + [len(d)]):
        p, recs = s, []
        while d[p:p + 10] != b'\xff' * 10:
            r = d[p:p + 10]
            recs.append({'type': r[0] & 0x7F, 'tflag': r[0] >> 7, 'group': r[1] & 0x7F, 'gflag': r[1] >> 7,
                         'a': u16(r, 2), 'b': u16(r, 4), 'c': u16(r, 6), 'code': s + u16(r, 8)})
            p += 10
        p += 10
        code, ins = p, []
        while p < e:
            n = oplen(d, p)
            ins.append((p, d[p:p + n]))
            p += n
        blocks.append({'start': s, 'end': e, 'records': recs, 'code_start': code, 'ins': ins})
    return blocks


class Game:
    def __init__(self, game_dir):
        self.dir = game_dir
        self.pc98 = not os.path.exists(os.path.join(game_dir, 'REKO3IBM.COM'))
        bak = os.path.join(game_dir, 'BAKDATA.R3')
        persons = (koei_games.load_eiketsu_pc98_persons(bak) if self.pc98 else
                   koei_games.load_eiketsu_dos_persons(bak))
        self.names = [n for n, _ in persons]

    def name(self, v):
        if v == ANY_PLAYER:
            return '（任一我軍）'
        if v == 0xFFFF:
            return '（無）'
        return self.names[v] if v < len(self.names) else f'?{v:04x}'

    def decode(self, raw: bytes) -> str:
        """DOS: Big5. PC-98 (MAIN.EXE load image 0x11DEA): 20-72 are hiragana (SJIS b + 0x827F), 73-76 、。？！,
        77-7F dropped, 80-FF lead a 2-byte SJIS code (EB xx = KOEI gaiji in FONT.R3), < 20 control bytes."""
        if not self.pc98:
            return raw.decode('big5', 'replace')
        out, i = [], 0
        while i < len(raw):
            c = raw[i]
            if c < 0x20:
                out.append(chr(c))
            elif c < 0x73:
                out.append(bytes([0x82, c + 0x7F]).decode('cp932'))
            elif c < 0x77:
                out.append('、。？！'[c - 0x73])
            elif c >= 0x80:
                if c == 0xEB:
                    out.append(koei_games.EIKETSU_PC98_GAIJI.get(raw[i + 1]) or
                               EIKETSU_PC98_PLACE_GAIJI.get(raw[i + 1], '〓'))
                else:
                    out.append(raw[i:i + 2].decode('cp932', 'replace'))
                i += 1
            i += 1
        return ''.join(out)

    def chapter(self, n):
        with open(os.path.join(self.dir, f'SNR{n}D.R3'), 'rb') as f:
            parts = ls11_decode_parts(f.read())
        with open(os.path.join(self.dir, f'SNR{n}M.R3'), 'rb') as f:
            m = f.read()
        return parts, m, [u16(m, 2 * k) for k in range(len(parts))]


class Section:
    """One SNRnD part with its message base."""

    def __init__(self, game: Game, n, k, data, msgs, base):
        self.g, self.n, self.k, self.d, self.m, self.base = game, n, k, data, msgs, base
        self.blocks = parse_part(data)

    def text(self, off) -> str:
        o = self.base + off
        return self.clean(self.m[o:self.m.index(b'\0', o)])

    def clean(self, raw) -> str:
        return self.g.decode(raw).replace('\r\n', '／').replace('\n', '／').replace('\r', '')

    def dialogue(self, off) -> list[tuple[int, str]]:
        o, out = self.base + off, []
        while u16(self.m, o) != 0xFFFF:
            sp = u16(self.m, o)
            e = self.m.index(b'\0', o + 2)
            out.append((sp, self.clean(self.m[o + 2:e])))
            o = e + 1
        return out

    def fmt(self, ins: bytes) -> str:
        op = ins[0]
        name, layout, _ = OPS.get(op, (f'op{op:02x}', '', ''))
        g = self.g
        if op == 0x03:
            h = hex_setup(ins)
            s = (f'{name} retreat={h["retreat"]} turns={h["turns"]} inherit={h["inherit"]} '
                 f'annihilate_win={h["annihilate_win"]} leader_win={h["leader_win"]}:{g.name(h["enemy_leader"])} '
                 f'annihilated_lose={h["annihilated_lose"]} leader_lose={h["leader_lose"]}:{g.name(h["our_leader"])}')
            for u in h['units']:
                s += f'\n        {g.name(u["person"])} ({u["x"]},{u["y"]}) {unit_note(u)}'
            return s
        if op == 0x22:
            lead, units = deploy(ins)
            s = f'{name} side={lead}'
            for u in units:
                s += f'\n        {g.name(u["person"])} ({u["x"]},{u["y"]}) {unit_note(u)}'
            return s
        if op == 0x1C:
            p, algo = u16(ins, 1), ins[3]
            prm = (g.name(u16(ins, 4)) if algo in (3, 5) else f'({ins[4]},{ins[5]})' if algo in (4, 6) else '')
            return f'{name} {g.name(p)} ai={algo}{AI.get(algo, "")} {prm}'.rstrip()
        if op == 0x20:
            return f'{name} reset={ins[1] >> 7} [{ins[2:].hex(" ")}]'
        if op == 0x21:
            skip, n1 = ins[1], ins[2]
            on, off = list(ins[3:3 + n1]), list(ins[4 + n1:])
            return f'{name} skip={skip} set={on} clear={off}'
        if op == 0x32:
            return f'{name} [{ins[2:].hex(" ")}]'
        args, i = [], 1
        for c in layout:
            if c == 'b':
                args.append(str(ins[i]))
                i += 1
                continue
            v = u16(ins, i)
            i += 2
            if c == 'p':
                args.append(f'{g.name(v)}#{v}')
            elif c == 'w':
                args.append(f'0x{v:04x}')
            elif c == 'M':
                args.append(map_name(v))
            elif c == 't':
                args.append(f'@{v:04x} 「{self.text(v)}」')
            elif c == 'm':
                lines = self.dialogue(v)
                args.append(f'@{v:04x}' + ''.join(f'\n        {g.name(sp)}：{t}' for sp, t in lines))
        return f'{name} ' + ' '.join(args) if args else name

    def listing(self) -> str:
        out = [f'; SNR{self.n}D.R3 part {self.k} ({CHAPTERS[self.n]}), message base 0x{self.base:04x}']
        for bi, b in enumerate(self.blocks):
            out.append(f'\n== block {bi} @{b["start"]:04x}')
            for r in b['records']:
                out.append(f'  trigger {trigger_desc(r, self.g)} group={r["group"]}{"*" if r["gflag"] else ""}'
                           f' -> {r["code"]:04x}')
            starts = {r['code']: r for r in b['records']}
            for p, ins in b['ins']:
                if p in starts:
                    out.append(f'  {p:04x}: ; {trigger_desc(starts[p], self.g)}')
                out.append(f'    {p:04x}  {ins[:8].hex(" "):<24} {self.fmt(ins)}')
        return '\n'.join(out) + '\n'


def map_name(v) -> str:
    kind, n = v >> 8, v & 0xFF
    if kind == 0x30:
        return f'battle {n} {BATTLES[n] if n < len(BATTLES) else "?"}'
    if kind == 0x20:
        return f'place {n}'
    if kind == 0x10:
        return 'world map'
    return f'0x{v:04x}'


def trigger_desc(r, g) -> str:
    t = r['type']
    s = TRIGGERS.get(t, f'type{t}')
    if t in (3, 5, 0xC):
        s += f'({g.name(r["a"])})'
    elif t == 9:
        s += f'({r["a"]})'
    elif t == 4:
        s += f'({g.name(r["a"])},{g.name(r["b"])})'
    elif t == 2:
        s += f'({r["a"]},{r["b"]})'
    elif t == 6:
        s += f'({g.name(r["a"])},({r["b"] >> 8},{r["b"] & 0xFF}))'
    elif t == 0xB:
        s += f'({g.name(r["a"])},x {r["b"] >> 8}-{r["c"] >> 8},y {r["b"] & 0xFF}-{r["c"] & 0xFF})'
    return s


def hex_setup(ins: bytes) -> dict:
    """03: b retreat, b turns, b inherit, b annihilate_win, b leader_win, w enemy leader, b annihilated_lose,
    b leader_lose, w our leader, then 30 x (w person, x, y, side, cond, flag, facing, hidden). Read at 0x14F54."""
    h = {'retreat': ins[1], 'turns': ins[2], 'inherit': ins[3], 'annihilate_win': ins[4], 'leader_win': ins[5],
         'enemy_leader': u16(ins, 6), 'annihilated_lose': ins[8], 'leader_lose': ins[9], 'our_leader': u16(ins, 10),
         'units': []}
    for j in range(30):
        u = ins[12 + 9 * j:21 + 9 * j]
        if u16(u, 0) == 0xFFFF:
            continue
        h['units'].append({'slot': j, 'person': u16(u, 0), 'x': u[2], 'y': u[3], 'side': u[4], 'cond': u[5],
                           'flag': u[6], 'facing': u[7], 'hidden': u[8]})
    return h


def deploy(ins: bytes):
    """22: b side (0 = enemy), then 30 x (w person, x, y, cond, flag, facing, hidden, ai, w ai param, class,
    level). Read at 0x15620."""
    units = []
    for j in range(30):
        u = ins[2 + 13 * j:15 + 13 * j]
        if u16(u, 0) == 0xFFFF:
            continue
        units.append({'slot': j, 'person': u16(u, 0), 'x': u[2], 'y': u[3], 'cond': u[4], 'flag': u[5],
                      'facing': u[6], 'hidden': u[7], 'ai': u[8], 'ai_param': u16(u, 9), 'class': u[11],
                      'level': u[12]})
    return ins[1], units


def unit_note(u) -> str:
    s = [FACING.get(u['facing'], f'facing{u["facing"]}')]
    if u['hidden']:
        s.append('伏兵')
    if u['cond']:
        s.append(f'需旗標{u["flag"]}')
    if 'ai' in u:
        s.append(f'AI{u["ai"]}{AI.get(u["ai"], "")}')
        if u['ai'] in (3, 5, 4, 6):
            s.append(f'目標{u["ai_param"]:04x}')
        s.append(f'兵種{u["class"]} Lv{u["level"]}')
    return ' '.join(s)


def classes(game_dir) -> list[str]:
    """兵種 names from MAIN.EXE (notes/eiketsu.md「能力」)."""
    with open(os.path.join(game_dir, 'MAIN.EXE'), 'rb') as f:
        exe = f.read()
    pc98 = not os.path.exists(os.path.join(game_dir, 'REKO3IBM.COM'))
    o = 0x358B0 if pc98 else 0x37BF8
    return [s.decode('cp932' if pc98 else 'big5') for s in exe[o:o + 400].split(b'\0')[:19]]


def groups(b: dict) -> list[tuple[dict, list]]:
    """(first trigger record, instructions up to and including FF) for every code start of the block."""
    idx = {p: i for i, (p, _) in enumerate(b['ins'])}
    out = []
    for code in sorted({r['code'] for r in b['records']}):
        r = next(r for r in b['records'] if r['code'] == code)
        ins = []
        for p, x in b['ins'][idx[code]:]:
            ins.append((p, x))
            if x[0] == 0xFF:
                break
        out.append((r, ins))
    return out


def with_conditions(ins: list) -> list[tuple[int, bytes, str]]:
    """Attach the 21 (flag test) / 15 (yes-no answer) conditions that guard each instruction (both skip n
    following instructions when the test fails)."""
    active, out = [], []
    for p, x in ins:
        out.append((p, x, ' '.join(lbl for _, lbl in active)))
        active = [(n - 1, lbl) for n, lbl in active if n > 1]
        if x[0] == 0x21:
            n1 = x[2]
            on, off = list(x[3:3 + n1]), list(x[4 + n1:])
            lbl = '旗標' + ''.join(f'+{f}' for f in on) + ''.join(f'-{f}' for f in off)
            active.append((x[1], lbl))
        elif x[0] == 0x15:
            active.append((x[2], f'回答≠{x[1]}'))
    return out


def battle_map(x: bytes):
    return x[1] if x[0] in (0x09, 0x11) and x[2] == 0x30 else None


def extract(game_dir):
    """A battle starts at 09 xx 30 (or 11 xx 30, a second map in the same battle). Its setup is the last 03 and the
    22s executed before it: groups run in code order, auto groups pass their state on, 0F n passes it to block n, and
    the last group that changed it passes it to the next block."""
    g = Game(game_dir)
    sections, battles = [], []
    for n in range(5):
        parts, m, bases = g.chapter(n)
        for k, d in enumerate(parts):
            sec = Section(g, n, k, d, m, bases[k])
            sections.append(sec)
            state, pending, recent = {'setup': None, 'enemy': []}, {}, []
            for bi, b in enumerate(sec.blocks):
                inherit = dict(pending.get(bi, state))
                carry_from = carry = inherit
                found = []
                for r, ins in groups(b):
                    s = dict(inherit)
                    for p, x, cond in with_conditions(ins):
                        if x[0] == 0x03:
                            s['setup'], s['enemy'] = (hex_setup(x), cond), []
                            recent.append(s['setup'])
                        elif x[0] == 0x22:
                            units = [dict(u, side_byte=x[1]) for u in deploy(x)[1]]
                            s['enemy'] = ([v for v in s['enemy'] if v[0]] if cond else []) + [(cond, units)]
                        elif battle_map(x) is not None:
                            found.append({'chapter': n, 'part': k, 'block': bi, 'at': p, 'map': x[1],
                                          'setup': s['setup'][0] if s['setup'] else None,
                                          'setup_cond': s['setup'][1] if s['setup'] else '',
                                          'enemy': s['enemy'], 'sec': sec})
                            s['enemy'] = []
                        elif x[0] == 0x0F:
                            pending[x[1]] = dict(s)
                    if r['type'] == 0:
                        inherit = s
                    if s != carry_from:
                        carry = s
                state = carry
                for i, bt in enumerate(found):
                    end = found[i + 1]['at'] if i + 1 < len(found) else b['end']
                    after = [(p, x) for p, x in b['ins'] if bt['at'] < p < end]
                    goal = next((x for p, x in after if x[0] == 0x30), None)
                    bt['goal'] = sec.text(u16(goal, 1)) if goal else ''
                    pick_setup(bt, recent, g)
                    recent = []
                    bt['events'] = block_events(sec, b, bt['at'], end)
                battles += found
    return g, sections, battles


def pick_setup(bt, recent, g):
    """A choice (25) runs one of several alternative auto groups, each with its own 03; the static walk ends with the
    last one. If the goal text names another candidate's enemy leader, take that candidate."""
    bt['setup_by'] = ''
    h = bt['setup']
    if not h or not bt['goal'] or g.name(h['enemy_leader']) in bt['goal']:
        return
    for c in reversed(recent):
        if g.name(c[0]['enemy_leader']) in bt['goal']:
            bt['setup'], bt['setup_cond'], bt['setup_by'] = c[0], c[1], 'goal'
            return


def duel_result(ins: list, i: int, g: Game) -> str:
    """After 10 a b: 35 (person, code) actions until 33, then usually 18 for the loser."""
    acts, loser = [], ''
    for p, x in ins[i + 1:]:
        if x[0] == 0x35:
            acts.append(f'{g.name(u16(x, 1))}:{x[3]}')
        elif x[0] == 0x33:
            continue
        elif x[0] == 0x18 and not loser:
            loser = g.name(u16(x, 1))
        elif x[0] in (0x10, 0xFF):
            break
    return (f'撤退：{loser}；' if loser else '') + '35：' + ' '.join(acts)


def block_events(sec: Section, b: dict, start: int, end: int) -> list[dict]:
    """Interesting instructions of the trigger groups between the battle's map op and the next one."""
    g, out = sec.g, []
    for r, ins in groups(b):
        ins = [(p, x) for p, x in ins if start < p < end]
        if not ins:
            continue
        for i, (p, x, cond) in enumerate(with_conditions(ins)):
            op = x[0]
            row = None
            if op == 0x10:
                row = ('duel', f'{g.name(u16(x, 1))} vs {g.name(u16(x, 3))}', duel_result(ins, i, g))
            elif op == 0x1A:
                row = ('join', g.name(u16(x, 1)), '')
            elif op == 0x18:
                row = ('withdraw', g.name(u16(x, 1)), '')
            elif op == 0x00:
                lines = sec.dialogue(u16(x, 1))
                row = ('talk', '／'.join(dict.fromkeys(g.name(sp) for sp, _ in lines)),
                       ' '.join(f'{g.name(sp)}：{t}' for sp, t in lines))
            elif op in (0x08, 0x0B, 0x0D, 0x0E, 0x25, 0x30):
                row = (OPS[op][0], '', sec.text(u16(x, 1)))
            elif op == 0x1B:
                row = ('item', '', str(x[1]))
            elif op in (0x24, 0x28):
                row = (OPS[op][0], g.name(u16(x, 1)), str(x[3]))
            elif op == 0x11:
                row = ('hex_end', '', map_name(u16(x, 1)))
            elif op in (0x29, 0x2A):
                row = (OPS[op][0], '', '')
            elif op == 0x14:
                row = ('set_flag', '', f'{x[1]}={x[2]}')
            elif op == 0x1C:
                row = ('set_ai', g.name(u16(x, 1)), sec.fmt(x).split(' ', 2)[2])
            if row:
                out.append({'trigger': trigger_desc(r, g), 'type': r['type'], 'group': r['group'],
                            'code': ins[0][0], 'at': p, 'cond': cond, 'kind': row[0], 'who': row[1],
                            'text': row[2]})
    return out


def battle_id(bt) -> str:
    return f'{bt["chapter"]}-{bt["part"]}-{bt["block"]}-{bt["map"]:02d}'


def write_all(game_dir, out_dir):
    g, sections, battles = extract(game_dir)
    cls = classes(game_dir)
    os.makedirs(os.path.join(out_dir, 'scripts'), exist_ok=True)
    for sec in sections:
        with open(os.path.join(out_dir, 'scripts', f'SNR{sec.n}_{sec.k}.txt'), 'w', encoding='utf-8') as f:
            f.write(sec.listing())
    with open(os.path.join(out_dir, 'battles.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['battle', 'chapter', 'part', 'block', 'map', 'name', 'turns', 'retreat', 'inherit_turns',
                    'win_annihilate', 'win_leader', 'enemy_leader', 'lose_annihilated', 'lose_leader',
                    'our_leader', 'goal_text', 'setup_by', 'player_slots', 'enemy_units', 'duels'])
        for bt in battles:
            h = bt['setup'] or {}
            w.writerow([battle_id(bt), CHAPTERS[bt['chapter']], bt['part'], bt['block'], bt['map'],
                        BATTLES[bt['map']] if bt['map'] < len(BATTLES) else '',
                        h.get('turns', ''), h.get('retreat', ''), h.get('inherit', ''), h.get('annihilate_win', ''),
                        h.get('leader_win', ''), g.name(h['enemy_leader']) if h else '',
                        h.get('annihilated_lose', ''), h.get('leader_lose', ''),
                        g.name(h['our_leader']) if h else '', bt['goal'] or '', bt['setup_by'],
                        len(h.get('units', [])), sum(len(v[1]) for v in bt['enemy']),
                        ' '.join(e['who'] for e in bt['events'] if e['kind'] == 'duel')])
    with open(os.path.join(out_dir, 'deploy.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['battle', 'name', 'side', 'variant', 'slot', 'person', 'person_name', 'x', 'y', 'facing',
                    'hidden', 'need_flag', 'ai', 'ai_target', 'class', 'level'])
        for bt in battles:
            nm = BATTLES[bt['map']] if bt['map'] < len(BATTLES) else ''
            for u in (bt['setup'] or {}).get('units', []):
                w.writerow([battle_id(bt), nm, '我軍' if u['side'] else '敵軍', bt['setup_cond'], u['slot'],
                            u['person'], '（自選）' if u['person'] == ANY_PLAYER else g.name(u['person']),
                            u['x'], u['y'], FACING.get(u['facing'], u['facing']), u['hidden'],
                            u['flag'] if u['cond'] else '', '', '', '', ''])
            for cond, u in ((c, u) for c, us in bt['enemy'] for u in us):
                tgt = (g.name(u['ai_param']) if u['ai'] in (3, 5) else
                       f'({u["ai_param"] & 0xFF},{u["ai_param"] >> 8})' if u['ai'] in (4, 6) else '')
                w.writerow([battle_id(bt), nm, '敵軍' if u['side_byte'] == 0 else '我軍', cond, u['slot'], u['person'],
                            g.name(u['person']), u['x'], u['y'], FACING.get(u['facing'], u['facing']), u['hidden'],
                            u['flag'] if u['cond'] else '', f'{u["ai"]} {AI.get(u["ai"], "")}', tgt,
                            cls[u['class']] if u['class'] < len(cls) else u['class'], u['level']])
    with open(os.path.join(out_dir, 'events.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['battle', 'name', 'trigger', 'group', 'code', 'at', 'condition', 'kind', 'who', 'text'])
        for bt in battles:
            nm = BATTLES[bt['map']] if bt['map'] < len(BATTLES) else ''
            for e in bt['events']:
                w.writerow([battle_id(bt), nm, e['trigger'], e['group'], f'{e["code"]:04x}', f'{e["at"]:04x}',
                            e['cond'], e['kind'], e['who'], e['text']])
    return g, sections, battles


def draw_markers(battles, g, map_dir, out_dir):
    """Unit markers on extract/battlemap/NN.png (one cell = 32 px): blue 我軍, red 敵軍, hollow = 伏兵."""
    os.makedirs(out_dir, exist_ok=True)
    for bt in battles:
        path = os.path.join(map_dir, f'{bt["map"]:02d}.png')
        if not os.path.exists(path):
            continue
        im = Image.open(path).convert('RGB')
        dr = ImageDraw.Draw(im)
        units = [(u, (40, 90, 255)) for u in (bt['setup'] or {}).get('units', [])]
        variant = bt['enemy'][-1:] if bt['enemy'] else []  # the last 22 (the unconditional one if no variants)
        units += [(u, (230, 40, 40) if u['side_byte'] == 0 else (40, 90, 255)) for _, us in variant for u in us]
        for u, col in units:
            x, y = u['x'] * 32, u['y'] * 32
            box = (x + 4, y + 4, x + 27, y + 27)
            if u['hidden'] or u['cond']:
                dr.rectangle(box, outline=col, width=3)
            else:
                dr.rectangle(box, fill=col, outline=(255, 255, 255))
        im.save(os.path.join(out_dir, f'{battle_id(bt)}.png'))


@click.command('scenario', help='劇本腳本：反組譯、戰場、部署、事件')
@click.option('--game-dir', 'game_dir', required=True, help='遊戲目錄')
@click.option('--out', 'out_dir', required=True, help='輸出目錄')
@click.option('--maps', 'map_dir', default=None,
              help='戰場圖目錄（預設 ../eiketsu-pc98/extract/battlemap），有圖才畫部署')
def eiketsu_scenario(game_dir, out_dir, map_dir):
    """
    eiketsu_script.py --game-dir ../games/eiketsu-dos --out ../games/eiketsu-dos/extract/scenario
    """
    g, sections, battles = write_all(game_dir, out_dir)
    map_dir = map_dir or os.path.join(game_dir, '..', 'eiketsu-pc98', 'extract', 'battlemap')
    draw_markers(battles, g, map_dir, os.path.join(out_dir, 'deploy'))
    print(f'{len(sections)} sections, {len(battles)} battles, '
          f'{sum(sum(len(v[1]) for v in b["enemy"]) + len((b["setup"] or {}).get("units", [])) for b in battles)}'
          f' units, '
          f'{sum(e["kind"] == "duel" for b in battles for e in b["events"])} duels')


if __name__ == '__main__':
    eiketsu_scenario()
