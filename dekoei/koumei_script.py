"""三國志孔明傳 (koumei-win): scenario scripts SNRnD.E2 / SNRnM.E2. Format and evidence: notes/koumei.md「劇本腳本」.

- SNRnD.E2 is LS11, one part per 幕. A part starts with u16 section offsets (FFFF ends). A section starts with
  10-byte trigger records (ten FF bytes end the table): +0 trigger type (bit 7: only when the leading 21 test holds),
  +1 group (bit 7: the group stays armed after it runs), +2..+7 parameters, +8 u16 code offset from the section start.
  Only the current group is armed; when one of its records reaches FF the group is done (unless bit 7).
- Code is 1-byte opcodes with fixed operand lengths (EKD2.EXE DGROUP 0x34C, 63 words), except 20 and 21.
  Interpreter: EKD2.EXE segment 4 0x5E34, dispatch at 4:73A6.
- SNRnM.E2 starts with one u16 per part (the message base); a message operand is a byte offset from that base.
  Plain messages end with NUL; a conversation (opcode 00) is repeated (u16 speaker record, text NUL) up to speaker FFFF.
"""
import csv
import os
import struct

import click

import koei_stats
import sango
from ls11 import ls11_decode_parts

# Operand lengths from EKD2.EXE DGROUP 0x34C (the interpreter's skip table), except 1D: the table says 2 but the
# handler (4:6826) reads 4 bytes, and the scripts agree with the handler.
OPLEN = [2, 5, 1, 281, 0, 0, 0, 2, 2, 2, 6, 2, 4, 2, 2, 1, 3, 2, 0, 0, 2, 2, 4, 1, 8, 2, 2, 1, 5, 4, 0, 0,
         None, None, 571, 0, 3, 2, 3, 3, 3, 0, 1, 3, 0, 2, 5, 3, 2, 4, 10, 2, 3, 4, 0, 4, 1, 3, 3, 2, 2, 1, 1]

# opcode: (mnemonic, operands); operand kinds: b u8, w u16, p u16 person record, m u16 message, c u16 conversation.
OPS = {
    0x00: ("talk", "c"), 0x01: ("move", "pbbb"), 0x02: ("op02", "b"), 0x03: ("deploy_player", None),
    0x04: ("nop", ""), 0x05: ("show", ""), 0x06: ("op06", ""), 0x07: ("msgpos", "bb"), 0x08: ("msgbox", "m"),
    0x09: ("scene", "w"), 0x0a: ("place", "pbbbb"), 0x0b: ("text", "m"), 0x0c: ("op0c", "wm"),
    0x0d: ("text2", "m"), 0x0e: ("text", "m"), 0x0f: ("goto_section", "b"), 0x10: ("movie", "bbb"),
    0x11: ("scene_keep", "w"), 0x12: ("next_part", ""), 0x13: ("end_group", ""), 0x14: ("setflag", "bb"),
    0x15: ("yesno_skip", "bb"), 0x16: ("op16", "ww"), 0x17: ("op17", "b"), 0x18: ("unit18", "pbbbbbb"),
    0x19: ("nop19", ""), 0x1a: ("unplace", "p"), 0x1b: ("item", "b"), 0x1c: ("ai", None),
    0x1d: ("op1d", "pbb"), 0x1e: ("clear_actors", ""), 0x1f: ("op1f", ""), 0x20: ("list20", None),
    0x21: ("if", None), 0x22: ("deploy_enemy", None), 0x23: ("choose_units", ""), 0x24: ("op24", "wb"),
    0x25: ("menu", "m"), 0x26: ("op26", "bbb"), 0x27: ("op27", "bbb"), 0x28: ("op28", "wb"),
    0x29: ("lose", ""), 0x2a: ("ending", "b"), 0x2b: ("value", None), 0x2c: ("op2c", ""),
    0x2d: ("op2d", "bb"), 0x2e: ("op2e", "wbbb"), 0x2f: ("op2f", "wb"), 0x30: ("goal_text", "m"),
    0x31: ("cmp_skip", "bbbb"), 0x32: ("op32", "bpbbbbbbb"), 0x33: ("sound", "bb"), 0x34: ("op34", "wb"),
    0x35: ("op35", "bbbb"), 0x36: ("op36", ""), 0x37: ("op37", "wbb"), 0x38: ("bgm", "b"),
    0x39: ("levelup", "pb"), 0x3a: ("set_class", "pb"), 0x3b: ("stop3b", "bb"), 0x3c: ("nop3c", "w"),
    0x3d: ("op3d", "b"), 0x3e: ("nop3e", ""), 0xff: ("end", ""),
}
# Trigger types (rec +0 & 0x7F), see notes/koumei.md「觸發」.
TRIGGERS = {0: "自動", 1: "類型1", 2: "類型2", 3: "類型3", 4: "相鄰", 5: "類型5", 6: "到達", 7: "勝利",
            8: "敗北", 9: "回合", 0x0b: "進入區域", 0x0c: "撤退"}
AI = {0: "防守", 1: "攻擊", 2: "堅守", 3: "追擊", 4: "前往", 5: "跟隨", 6: "逃往"}
VALUE_SLOTS = {0: "seg9+2 減", 1: "seg9+2 加（上限 200）", 2: "seg9+8 加（上限 50000）", 3: "seg9+8 清 0",
               4: "seg9+0 加（上限 50000）", 5: "6:EAFA"}
ANY_PLAYER = 0x400  # trigger parameter: any player unit; deployment: a slot the player fills


def oplen(b, p):
    op = b[p]
    if op == 0x20:
        return 2 + (b[p + 1] & 0x7f)
    if op == 0x21:
        n1 = b[p + 2]
        return 4 + n1 + b[p + 3 + n1]
    if op < len(OPLEN):
        return 1 + OPLEN[op]
    return 1


class Script:
    def __init__(self, game_dir, n):
        with open(os.path.join(game_dir, f"SNR{n}D.E2"), "rb") as f:
            self.parts = ls11_decode_parts(f.read())
        with open(os.path.join(game_dir, f"SNR{n}M.E2"), "rb") as f:
            self.m = f.read()
        self.n = n

    def base(self, k):
        return struct.unpack_from("<H", self.m, 2 * k)[0]

    def text(self, k, off):
        a = self.base(k) + off
        return self.m[a:self.m.index(b"\0", a)].decode("big5", "replace").replace("\r\n", "／").replace("\n", "／")

    def conversation(self, k, off):
        a, out = self.base(k) + off, []
        while a + 2 <= len(self.m):
            spk = struct.unpack_from("<H", self.m, a)[0]
            if spk == 0xffff:
                break
            e = self.m.index(b"\0", a + 2)
            out.append((spk, self.m[a + 2:e].decode("big5", "replace").replace("\r\n", "／").replace("\n", "／")))
            a = e + 1
        return out


def sections(b):
    offs = []
    while True:
        o = struct.unpack_from("<H", b, 2 * len(offs))[0]
        if o == 0xffff:
            return offs
        offs.append(o)


def records(b, s):
    r, out = s, []
    while b[r:r + 2] != b"\xff\xff":
        out.append(b[r:r + 10])
        r += 10
    return out, r + 10


def decode_units(b, p, kind):
    """Units of a deployment (03: player and allies, 22: enemies); slots with person FFFF are skipped."""
    units = []
    if kind == 3:
        for i in range(30):
            q = p + 12 + 9 * i
            pid, x, y, a, cond, var, face, hide = struct.unpack_from("<H7B", b, q)
            if pid != 0xffff:
                units.append({"slot": i, "person": pid, "x": x, "y": y, "side": "我軍" if a else "友軍",
                              "cond": cond, "var": var, "face": face, "hidden": hide})
    else:
        for i in range(30):
            q = p + 2 + 19 * i
            pid, x, y, cond, var, face, hide, ai, aip, cls, lv = struct.unpack_from("<H6BBHBB", b, q)
            if pid != 0xffff:
                units.append({"slot": i, "person": pid, "x": x, "y": y, "side": "敵軍", "cond": cond, "var": var,
                              "face": face, "hidden": hide, "ai": ai, "aip": aip, "class": cls, "level": lv,
                              "extra": b[q + 13:q + 19].hex(" ")})
    return units


class Disassembler:
    def __init__(self, game_dir):
        self.game_dir = game_dir
        self.names = [n for n, _ in sango.load_koumei_persons(os.path.join(game_dir, "BAKDATA.E2"))]

    def person(self, pid):
        if pid == 0xffff:
            return "－"
        if pid >= ANY_PLAYER:
            return f"自選{pid - ANY_PLAYER}" if pid > ANY_PLAYER else "我軍任一"
        return f"{pid}:{self.names[pid]}" if pid < len(self.names) else str(pid)

    def operands(self, sc, k, b, p):
        """(text, messages) of the instruction at p; messages are (speaker or None, text)."""
        op = b[p]
        name, fmt = OPS.get(op, (f"op{op:02x}", ""))
        msgs, args = [], []
        if op == 0x03:
            h = b[p + 1:p + 12]
            args.append(f"continue={h[0]} turns={h[1]} keep_turn={h[2]} all_win?={h[3]} "
                        f"boss_win={h[4]} boss={self.person(h[5] | h[6] << 8)} all_lose?={h[7]} "
                        f"key_lose={h[8]} key={self.person(h[9] | h[10] << 8)}")
            for u in decode_units(b, p, 3):
                args.append(self.unit_text(u))
            return name + " " + "\n            ".join(args), msgs
        if op == 0x22:
            args.append(f"flags={b[p + 1]}")
            for u in decode_units(b, p, 0x22):
                args.append(self.unit_text(u))
            return name + " " + "\n            ".join(args), msgs
        if op == 0x20:
            n = b[p + 1]
            return f"{name} {'reset ' if n & 0x80 else ''}[{' '.join(f'{x:02x}' for x in b[p + 2:p + 2 + (n & 0x7f)])}]", msgs
        if op == 0x21:
            skip, n1 = b[p + 1], b[p + 2]
            on = list(b[p + 3:p + 3 + n1])
            n2 = b[p + 3 + n1]
            off = list(b[p + 4 + n1:p + 4 + n1 + n2])
            return f"if set{on} clear{off} else skip {skip}", msgs
        if op == 0x1c:
            pid, kind = struct.unpack_from("<HB", b, p + 1)
            tail = (self.person(struct.unpack_from("<H", b, p + 4)[0]) if kind in (3, 5)
                    else f"({b[p + 4]},{b[p + 5]})" if kind in (4, 6) else f"{b[p + 4]:02x} {b[p + 5]:02x}")
            return f"{name} {self.person(pid)} {AI.get(kind, kind)} {tail}", msgs
        if op == 0x2b:
            kind, v = struct.unpack_from("<BH", b, p + 1)
            what = VALUE_SLOTS.get(kind, "孔明頭像 seg9+0xF")
            return f"{name} {kind} {v}  ; {what}", msgs
        q = p + 1
        for c in fmt:
            if c == "b":
                args.append(str(b[q]))
                q += 1
                continue
            v = struct.unpack_from("<H", b, q)[0]
            q += 2
            if c == "w":
                args.append(f"0x{v:04x}")
            elif c == "p":
                args.append(self.person(v))
            elif c == "m":
                args.append(f"m{v}")
                msgs.append((None, sc.text(k, v)))
            elif c == "c":
                args.append(f"m{v}")
                msgs.extend(sc.conversation(k, v))
        if op == 0x09:
            args.append(f"; {SCENE_KIND.get(v >> 12, v >> 12)} {v & 0xfff}")
        return name + (" " + " ".join(args) if args else ""), msgs

    def unit_text(self, u):
        s = f"{u['side']} {self.person(u['person'])} ({u['x']},{u['y']})"
        if u["cond"]:
            s += f" if flag{u['var']}"
        if u["hidden"]:
            s += " 伏兵"
        s += f" 朝向{u['face']}"
        if "ai" in u:
            aip = self.person(u["aip"]) if u["ai"] in (3, 5) else f"({u['aip'] & 0xff},{u['aip'] >> 8})"
            s += f" AI {AI.get(u['ai'], u['ai'])}" + (f" {aip}" if u["ai"] >= 3 else "")
            s += f" {class_name(u['class'])} Lv{u['level']}"
            if u["extra"] != "00 00 00 00 00 00":
                s += f" [{u['extra']}]"
        return s

    def message_lines(self, msgs):
        return [f"            {'' if s is None else self.person(s) + '：'}{t}" for s, t in msgs]


SCENE_KIND = {0: "畫面", 1: "大地圖", 2: "場所", 3: "戰場"}


def class_name(c):
    cl = koei_stats.KOUMEI_WIN_CLASSES
    return cl[c] if c < len(cl) else f"兵種{c}"


def trigger_text(dis, rec):
    t, g = rec[0], rec[1]
    p1, p2 = struct.unpack_from("<HH", rec, 2)
    kind = TRIGGERS.get(t & 0x7f, f"類型{t & 0x7f}")
    if t & 0x7f == 4:
        cond = f"{dis.person(p1)} 與 {dis.person(p2)} 相鄰"
    elif t & 0x7f == 6:
        cond = f"{dis.person(p1)} 到達 ({rec[5]},{rec[4]})"
    elif t & 0x7f == 0x0b:
        cond = f"{dis.person(p1)} 進入 x {rec[5]}–{rec[7]}, y {rec[4]}–{rec[6]}"
    elif t & 0x7f == 0x0c:
        cond = f"{dis.person(p1)} 撤退"
    elif t & 0x7f == 9:
        cond = f"第 {p1} 回合"
    elif t & 0x7f in (2, 3, 5):
        cond = f"p1={dis.person(p1)} p2={p2}"
    else:
        cond = ""
    flags = ("（需先通過開頭的 21）" if t & 0x80 else "") + ("（組保留）" if g & 0x80 else "")
    return kind, cond, flags


def walk(b, s, end):
    """Linear sweep of a section's code: [(offset, length)]."""
    _, p = records(b, s)
    out = []
    while p < end:
        n = oplen(b, p)
        out.append((p, n))
        p += n
    return out


def disassemble_part(dis, sc, k, fp):
    b = sc.parts[k]
    secs = sections(b)
    bounds = secs[1:] + [len(b)]
    fp.write(f"; SNR{sc.n}D.E2 part {k}, {len(b)} bytes, message base {sc.base(k)}\n")
    for si, (s, end) in enumerate(zip(secs, bounds)):
        recs, _ = records(b, s)
        entries = {}
        fp.write(f"\n;==== section {si} at 0x{s:04x}\n")
        for ri, rec in enumerate(recs):
            kind, cond, flags = trigger_text(dis, rec)
            target = s + struct.unpack_from("<H", rec, 8)[0]
            entries.setdefault(target, []).append(ri)
            fp.write(f";  rec {ri:2d} group {rec[1] & 0x7f:2d}: {kind} {cond}{flags} -> 0x{target:04x}  [{rec.hex(' ')}]\n")
        for p, n in walk(b, s, end):
            for ri in entries.pop(p, []):
                rec = recs[ri]
                kind, cond, _ = trigger_text(dis, rec)
                fp.write(f"\n; --- rec {ri} (group {rec[1] & 0x7f}, {kind} {cond})\n")
            text, msgs = dis.operands(sc, k, b, p)
            fp.write(f"  {p:04x}  {b[p:p + min(n, 8)].hex(' '):24s}{text}\n")
            for line in dis.message_lines(msgs):
                fp.write(line + "\n")
        for target, ris in entries.items():
            fp.write(f"; !! rec {ris} target 0x{target:04x} is not on an instruction boundary\n")


# Battle names: tid-210344 (xycq.org.cn) lists the 22 00 offsets of every battle in file order; ours run in the
# same order with the same count per file (offsets differ by 0x13E-0x155: another build). Reference only.
REFERENCE_BATTLES = {
    0: ["博望坡"] * 4 + ["新野"] * 2 + ["江夏急行"] + ["長坂坡"],
    1: ["赤壁 I"] + ["赤壁 II"] * 2 + ["荊州南部"] + ["綿竹、葭萌關"] + ["漢水"] + ["麥城"] + ["彝陵"],
    2: ["陽平關"] + ["益州南部"] + ["玉溪峰"] * 2 + ["夾山谷"] + ["瀘水"] * 3 + ["西耳湖"] * 2 + ["禿龍洞"] * 2
    + ["三江城"] + ["蠻都"] + ["桃葉江"] * 2 + ["盤蛇谷"],  # the second 桃葉江 (part 3 section 3) is not in tid-210344
    3: ["風鳴山"] * 2 + ["南安、安定"] * 2 + ["天水城"] * 2 + ["冀城"] * 2 + ["祁山"] * 2 + ["西平關"] * 2
    + ["街亭"] + ["漢中退卻"],
    4: ["陳倉、祁山"] * 2 + ["陳倉攻城"] * 2 + ["祁山追擊"] * 2 + ["二谷道"] * 2 + ["祁山 2"] + ["渭水"] * 2
    + ["葫蘆谷"] * 2 + ["五丈原"] * 2,
    5: ["郿城"] * 2 + ["武功"] * 2 + ["長安攻城 1"] + ["巴西（孟獲為敵）", "巴西（孟獲為我軍）"] + ["白帝城"] * 2
    + ["江陵"] + ["建寧"] + ["長安攻城 2"] + ["華山"] * 2 + ["函谷關"] * 2 + ["洛陽 1"] + ["洛陽 2"],
}


def bodies(b, s, end):
    """Each trigger record's code, from its entry up to its FF: [(record, [offsets])]."""
    recs, _ = records(b, s)
    code = walk(b, s, end)
    index = {p: i for i, (p, _) in enumerate(code)}
    out = []
    for rec in recs:
        body = []
        for p, _ in code[index.get(s + struct.unpack_from("<H", rec, 8)[0], len(code)):]:
            body.append(p)
            if b[p] == 0xff:
                break
        out.append((rec, body))
    return out


def collect(dis, game_dir):
    """One battle row per enemy deployment (22), with the player deployment (03) that leads to it."""
    battles, events = [], []
    for n in range(6):
        sc = Script(game_dir, n)
        ref = iter(REFERENCE_BATTLES.get(n, []))
        enemy_count = 0
        for k, b in enumerate(sc.parts):
            secs = sections(b)
            parts = [bodies(b, s, end) for s, end in zip(secs, secs[1:] + [len(b)])]
            # an 03 belongs to the sections its record jumps to (0F), else to its own section
            # (a few battles get their 03 from a section reached another way: then the last 03 before the 22)
            player, all03 = {}, []
            for si, recs in enumerate(parts):
                for rec, body in recs:
                    last = None
                    for p in body:
                        if b[p] == 0x03:
                            last = p
                            all03.append((p, si))
                            player.setdefault(si, (si, p))
                        elif b[p] == 0x0f and last is not None:
                            player[b[p + 1]] = (si, last)
            seen = set()
            for si, recs in enumerate(parts):
                goal = [sc.text(k, struct.unpack_from("<H", b, p + 1)[0])
                        for _, body in recs for p in body if b[p] == 0x30]
                for rec, body in recs:
                    for i, p in enumerate(body):
                        if b[p] != 0x22 or p in seen:
                            continue
                        seen.add(p)
                        enemy_count += 1
                        bid = next((b[q + 1] | (b[q + 2] & 0xf) << 8 for q in body[i:]
                                    if b[q] == 0x09 and b[q + 2] >> 4 == 3), None)
                        p03 = next((q for q in reversed(body[:i]) if b[q] == 0x03), None)
                        src = (si, p03) if p03 is not None else player.get(si)
                        if src is None:
                            src = next(((s3, q) for q, s3 in reversed(sorted(all03)) if q < p), None)
                        units = decode_units(b, src[1], 3) if src else []
                        battles.append({"file": n, "part": k, "section": si, "offset": p, "battle": bid,
                                        "header": b[src[1] + 1:src[1] + 12] if src else None,
                                        "player_at": f"{src[0]}:{src[1]:04x}" if src else "",
                                        "units": units + decode_units(b, p, 0x22), "goal": goal,
                                        "ref": next(ref, "")})
                for ri, (rec, body) in enumerate(recs):
                    bid = next((b[q + 1] | (b[q + 2] & 0xf) << 8 for _, bd in recs for q in bd
                                if b[q] == 0x09 and b[q + 2] >> 4 == 3), None)
                    events.append(summarize(dis, sc, k, b, n, si, ri, rec, body, bid))
        if enemy_count != len(REFERENCE_BATTLES.get(n, [])):
            print(f"SNR{n}D: {enemy_count} enemy deployments, reference lists {len(REFERENCE_BATTLES.get(n, []))}")
    return battles, events


def summarize(dis, sc, k, b, n, si, ri, rec, body, bid):
    kind, cond, flags = trigger_text(dis, rec)
    ops = [b[p] for p in body]
    people, texts, notes = [], [], []
    for p in body:
        op = b[p]
        if op == 0x00:
            for spk, t in sc.conversation(k, struct.unpack_from("<H", b, p + 1)[0]):
                people.append(dis.person(spk))
                texts.append(f"{dis.person(spk)}：{t}")
        elif op in (0x08, 0x0b, 0x0e, 0x0d, 0x25):
            texts.append(sc.text(k, struct.unpack_from("<H", b, p + 1)[0]))
        elif op == 0x10:
            notes.append("動畫 " + " ".join(f"I{x:02d}" for x in b[p + 1:p + 4]))
        elif op == 0x0f:
            notes.append(f"跳到第 {b[p + 1]} 節")
        elif op == 0x09:
            v = struct.unpack_from("<H", b, p + 1)[0]
            notes.append(f"場景 {SCENE_KIND.get(v >> 12, v >> 12)} {v & 0xfff}")
        elif op == 0x14:
            notes.append(f"旗標{b[p + 1]}={'1' if b[p + 2] else '0'}")
        elif op in (0x03, 0x22):
            notes.append("部署")
    tags = []
    t = rec[0] & 0x7f
    if t == 7:
        tags.append("victory")
    elif t == 8:
        tags.append("defeat")
    if t == 4 and rec[2] | rec[3] << 8 < ANY_PLAYER:
        tags.append("contact")
    if any(x in ops for x in (0x25, 0x15)):
        tags.append("branch")
    if 0x0f in ops:
        tags.append("goto")
    if 0x00 in ops:
        tags.append("talk")
    if 0x10 in ops:
        # every 10 in the scripts sits in a contact record between two named persons: a battle cut-in (duel?)
        tags.append("duel?" if "contact" in tags else "movie")
    if 0x18 in ops or 0x32 in ops:
        tags.append("unit")
    if any(x in ops for x in (0x03, 0x22)):
        tags.append("deploy")
    return {"file": f"SNR{n}", "part": k, "section": si, "record": ri, "group": rec[1] & 0x7f,
            "battle": "" if bid is None else bid, "trigger": kind, "condition": cond + flags,
            "kind": "/".join(tags), "persons": " ".join(dict.fromkeys(people)), "notes": "；".join(notes),
            "text": " ｜ ".join(texts)}


def write_outputs(game_dir, out_dir):
    dis = Disassembler(game_dir)
    os.makedirs(os.path.join(out_dir, "scripts"), exist_ok=True)
    for n in range(6):
        sc = Script(game_dir, n)
        for k in range(len(sc.parts)):
            with open(os.path.join(out_dir, "scripts", f"SNR{n}_{k}.txt"), "w", encoding="utf-8") as fp:
                disassemble_part(dis, sc, k, fp)
    battles, events = collect(dis, game_dir)
    with open(os.path.join(out_dir, "battles.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["battle", "map", "file", "part", "section", "offset", "player_deploy", "reference_name", "turns", "keep_turn",
                    "win_boss", "lose_key", "player", "allies", "enemies", "hidden", "conditional", "goal_text"])
        for bt in battles:
            h, u = bt["header"], bt["units"]
            boss = dis.person(h[5] | h[6] << 8) if h and h[4] else ""
            key = dis.person(h[9] | h[10] << 8) if h and h[8] else ""
            side = [x["side"] for x in u]
            w.writerow([bt["battle"], bt["battle"], f"SNR{bt['file']}", bt["part"], bt["section"], f"{bt['offset']:04x}",
                        bt["player_at"], bt["ref"],
                        h[1] if h else "", h[2] if h else "", boss, key, side.count("我軍"), side.count("友軍"),
                        side.count("敵軍"), sum(1 for x in u if x["hidden"]), sum(1 for x in u if x["cond"]),
                        " ｜ ".join(bt["goal"])])
    with open(os.path.join(out_dir, "deploy.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["battle", "file", "part", "section", "offset", "side", "slot", "person", "name", "x", "y", "hidden",
                    "if_flag", "facing", "ai", "ai_target", "class", "level", "extra"])
        for bt in battles:
            for x in bt["units"]:
                pid = x["person"]
                name = dis.person(pid).split(":")[-1]
                ai = AI.get(x["ai"], x["ai"]) if "ai" in x else ""
                target = ""
                if "ai" in x and x["ai"] in (3, 5):
                    target = dis.person(x["aip"])
                elif "ai" in x and x["ai"] in (4, 6):
                    target = f"({x['aip'] & 0xff},{x['aip'] >> 8})"
                w.writerow([bt["battle"], f"SNR{bt['file']}", bt["part"], bt["section"], f"{bt['offset']:04x}", x["side"], x["slot"],
                            pid if pid < ANY_PLAYER else "", name, x["x"], x["y"], x["hidden"],
                            x["var"] if x["cond"] else "", x["face"], ai, target,
                            class_name(x["class"]) if "class" in x else "", x.get("level", ""), x.get("extra", "")])
    with open(os.path.join(out_dir, "events.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(events[0]))
        w.writeheader()
        w.writerows(events)
    draw_markers(game_dir, out_dir, battles)
    return battles, events


SIDE_COLOURS = {"我軍": (40, 90, 255), "友軍": (40, 200, 60), "敵軍": (230, 30, 30)}


def draw_markers(game_dir, out_dir, battles):
    """One PNG per battle section: the battle map with a dot per deployed unit (cell = 48 px)."""
    from PIL import Image, ImageDraw
    src = os.path.join(game_dir, "extract", "battlemap")
    if not os.path.isdir(src):
        return
    os.makedirs(os.path.join(out_dir, "deploy"), exist_ok=True)
    for bt in battles:
        path = os.path.join(src, f"{bt['battle']:02d}.png") if bt["battle"] is not None else ""
        if not os.path.exists(path):
            continue
        im = Image.open(path).convert("RGB")
        d = ImageDraw.Draw(im)
        for x in bt["units"]:
            cx, cy = x["x"] * 48 + 24, x["y"] * 48 + 24
            col = SIDE_COLOURS[x["side"]]
            box = (cx - 14, cy - 14, cx + 14, cy + 14)
            if x["hidden"] or x["cond"]:
                d.ellipse(box, outline=col, width=4)
            else:
                d.ellipse(box, fill=col, outline=(255, 255, 255), width=2)
        im.save(os.path.join(out_dir, "deploy", f"b{bt['battle']:02d}_SNR{bt['file']}_{bt['part']}_{bt['offset']:04x}.png"))


@click.command(help="劇本腳本（SNR?D.E2）：反組譯、戰役、部署、事件")
@click.option("--game-dir", "game_dir", required=True, help="遊戲目錄")
@click.option("--out", "out_dir", required=True, help="輸出目錄")
def scenario(game_dir, out_dir):
    """
    python koumei_script.py --game-dir ../games/koumei-win --out ../games/koumei-win/extract/scenario
    """
    battles, events = write_outputs(game_dir, out_dir)
    ids = {b["battle"] for b in battles}
    print(f"{len(battles)} enemy deployments, {len(ids)} battle maps, "
          f"{sum(len(b['units']) for b in battles)} unit placements, {len(events)} trigger records")


if __name__ == "__main__":
    scenario()
