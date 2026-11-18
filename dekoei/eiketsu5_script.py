"""三國志曹操傳 (eiketsu5-win): scenario scripts R_00-R_58.EEX / S_00-S_57.EEX. Format and evidence:
notes/eiketsu5.md「劇本腳本（R_／S_*.EEX）」.

    cd dekoei && ../.venv/bin/python eiketsu5_script.py --game-dir ../games/eiketsu5-win \
        --out ../games/eiketsu5-win/extract/scenario

Writes scripts/R_NN.txt, scripts/S_NN.txt (listings), battles.csv, deploy.csv, events.csv, stages.csv and
battle/NN.png (unit markers over extract/battlemap/NN.png, when that exists).

File layout (EKD5.EXE 0x410293 load, 0x4100c1 block selection, 0x4105c8 / 0x41086e block execution):
- "EEX\\0", u8 1, u8 2, then header chunks (u16 type, u16 len) up to type 0 (all files: none), then the scene
  table: u32 offsets, the first one also marks the table end, so scenes = (first - 10) / 4.
- scene: u16 block count, then blocks (u16 len, data). A block is a condition list ended by op 00 (the block
  runs when every condition is true; the last matching block wins), then u16 len and the body ended by op 00.
- command: u16 op, then parameters. Each parameter is u16 type + value: type 4 is u32, type 5 a NUL-ended Big5
  string, others u16 (0x418417). Op 01 runs the next command as a test (or op 03 = else) and then a nested
  (u16 len, body) block.
"""
import glob
import os
import struct

import click

from koei_games import load_eiketsu5_win_persons
from common import write_dict_csv

# op -> (name, parameter types, evidence). Types come from the handlers' calls to 0x418417 (dispatch table
# 0x41114f, handler list in notes/eiketsu5.md); names marked "code" were read from the handler, "cross" match the
# xycq.org.cn community table and the data, "data" are only guessed from how the scripts use them.
OPS = {
    0x00: ("結束", [], "code"),
    0x01: ("條件區塊", [], "code"),
    0x02: ("註解", [5], "code"),
    0x03: ("否則", [], "code"),
    0x04: ("詢問?", [0x26], ""),
    0x05: ("旗標測試", "flags", "code"),
    0x06: ("出擊設定", [0x2e, 4] + [0x38] * 5 + [0x39] * 5, "cross"),
    0x07: ("選擇出擊", [], "cross"),
    0x08: ("選單", [0x2e], "cross"),
    0x09: ("等待", [4], "cross"),
    0x0a: ("清除局部旗標", [], "code"),
    0x0b: ("設定旗標", [4, 0x27], "code"),
    0x0c: ("中止", [], "code"),
    0x0d: ("結束本節", [], "code"),
    0x0e: ("戰敗", [], "cross"),
    0x0f: ("結局", [0x12], "cross"),
    0x10: ("許子將指導", [], "cross"),
    0x11: ("跳到關卡", [0x37], "code"),
    0x12: ("選擇框", [5, 2], "data"),
    0x13: ("選擇結果測試", [4], "data"),
    0x14: ("對話", [5], "data"),
    0x15: ("A 對 B 說話", [2, 2, 5], "cross"),
    0x16: ("文字", [5], "cross"),
    0x17: ("單行文字", [5], "cross"),
    0x18: ("?18", [5], ""),
    0x19: ("勝利條件", [5], "data"),
    0x1a: ("地圖大字", [5], "cross"),
    0x1b: ("屏蔽撤退台詞", [2, 0x27], "cross"),
    0x1c: ("繪圖", [], "cross"),
    0x1d: ("調色盤", [], "cross"),
    0x1e: ("?1e", [], ""),
    0x1f: ("視角", [4, 4], "cross"),
    0x20: ("頭像", [0x4a], "cross"),
    0x21: ("放火", [4, 4, 0x10, 0x26, 0x26], "cross"),
    0x22: ("動畫", [0x1b], "cross"),
    0x23: ("音效", [0x1e, 4], "cross"),
    0x24: ("音樂", [9], "cross"),
    0x25: ("到達地點測試", [2, 4, 4], "code"),
    0x26: ("區域測試", [2, 4, 4, 4, 4], "cross"),
    0x27: ("背景", [0x2d, 0x0c, 0x1a, 0x1c, 0x15], "code"),
    0x28: ("?28", [0x36], ""),
    0x29: ("地圖頭像出現", [2, 4, 4], "cross"),
    0x2a: ("地圖頭像移動", [2, 4, 4], "cross"),
    0x2b: ("地圖頭像消失", [2], "cross"),
    0x2c: ("地圖文字", [5, 0x26, 0x26, 0x26], "cross"),
    0x2d: ("點擊武將測試", [2], "cross"),
    0x2e: ("相鄰測試", [2, 2, 0x26], "cross"),
    0x2f: ("清除人物", [], "cross"),
    0x30: ("人物出現", [2, 4, 4, 0x2b, 0x0d], "cross"),
    0x31: ("部隊消失", [0x2c, 2, 4, 4, 4, 4, 3], "cross"),
    0x32: ("人物移動", [0x40, 2, 4, 4, 4, 0x2b], "cross"),
    0x33: ("人物轉向", [2, 0x0d, 0x2b], "cross"),
    0x34: ("人物動作", [2, 0x0d], "cross"),
    0x35: ("人物形象", [2, 0x13], "cross"),
    0x36: ("能力測試", [2, 0x23, 4, 0x24], "cross"),
    0x37: ("金錢等測試", [0x28, 4, 0x24], "cross"),
    0x38: ("能力設定?", [2, 0x23, 0x34, 4], ""),
    0x39: ("升級", [2, 4], "cross"),
    0x3a: ("金錢等設定", [0x28, 0x34, 4], "cross"),
    0x3b: ("武將加入", [2, 0x0e, 0x3e], "cross"),
    0x3c: ("加入測試", [2, 0x0e, 0x3a], "cross"),
    0x3d: ("得到物品", [0x17, 0x49, 0x26, 2], "cross"),
    0x3e: ("加入時裝備", [2, 0x3b, 0x49, 0x3c, 0x49, 0x3d], "cross"),
    0x3f: ("回合測試", [4, 0x24], "code"),
    0x40: ("行動方測試", [0x48], "cross"),
    0x41: ("人數測試", [3, 4, 0x24, 0x3f, 4, 4, 4, 4], "cross"),
    0x42: ("勝利判定", [], "code"),
    0x43: ("敗北判定", [], "code"),
    0x44: ("戰鬥初始化", [], "cross"),
    0x45: ("戰場設定", [0x26, 0x26, 4, 0x3e, 0x32, 2, 0x32, 2, 0x47, 0x22], "code"),
    0x46: ("友軍", [2, 0x26, 4, 4, 0x2b, 0x3e, 0x45, 7, 2, 4, 4] * 20, "code"),
    0x47: ("敵軍", [2, 0x26, 0x26, 4, 4, 0x2b, 0x3e, 0x45, 7, 2, 4, 4] * 80, "code"),
    0x48: ("特殊裝備", [2, 0x3b, 0x49, 0x3c, 0x49, 0x3d], "cross"),
    0x49: ("?49", [], ""),
    0x4a: ("我軍出場控制", [4] + [0x38] * 5 + [0x39] * 5, "code"),
    0x4b: ("我軍位置", [4, 4, 4, 0x2b, 0x26], "cross"),
    0x4c: ("部隊出現", [0x40, 2, 4], "code"),
    0x4d: ("狀態變更", [0x41, 2, 4, 4, 4, 4, 4, 3, 0x2f, 0x18, 0x30, 4, 4], "cross"),
    0x4e: ("AI 變更", [0x2c, 2, 4, 4, 4, 4, 3, 7, 2, 4, 4], "cross"),
    0x4f: ("戰場轉向", [2, 2, 0x2b, 0x26, 0x26, 0x26], "cross"),
    0x50: ("戰場動作", [2, 0x46, 0x26, 0x26], "cross"),
    0x51: ("恢復未行動", [], "cross"),
    0x52: ("兵種改變?", [2, 3], "cross"),
    0x53: ("撤退", [0x2c, 2, 4, 4, 4, 4, 3, 0x26], "cross"),
    0x54: ("強制撤退", [], "cross"),
    0x55: ("復活", [0x40, 2, 4, 4, 4, 0x2b], "cross"),
    0x56: ("?56", [0x47], ""),
    0x57: ("?57", [0x22], ""),
    0x58: ("障礙物", [0x42, 0x43, 0x44, 4, 4, 0x26, 0x26], "cross"),
    0x59: ("戰利品", [4, 0x17, 0x49, 0x17, 0x49, 0x17, 0x49, 0x26], "cross"),
    0x5a: ("開始操作", [], "cross"),
    0x5b: ("高亮地點", [4, 4, 4, 4, 0x26], "cross"),
    0x5c: ("高亮人物", [2], "cross"),
    0x5d: ("最大回合", [0x34, 4], "cross"),
    0x5e: ("武將不同測試", [2, 2], "cross"),
    0x5f: ("單挑結束", [], "cross"),
    0x60: ("單挑出場", [0x26, 5, 0x4c], "cross"),
    0x61: ("單挑勝負字樣", [], "cross"),
    0x62: ("單挑勝者", [0x26], "data"),
    0x63: ("單挑說話", [0x26, 5, 0x26], "cross"),
    0x64: ("單挑動作", [0x26, 0x4c], "cross"),
    0x65: ("單挑特殊攻擊", [0x26, 0x4d, 0x26], "cross"),
    0x66: ("單挑特殊攻擊", [0x26, 0x4e, 0x26], "cross"),
    0x67: ("?67", [4, 5], ""),
    0x68: ("單挑開始", [2, 2], "cross"),
    0x69: ("?69", [5], ""),
    0x6a: ("戰鬥狀態", [], "cross"),
    0x6b: ("法術圖示", [4, 4, 0x4b, 0x26], "cross"),
}

# special person codes of type-2 parameters in battle tests (0x45afa1, 0x45954b)
PERSON_CODES = {0x400: "任一部隊", 0x401: "我軍或友軍部隊", 0x402: "敵軍部隊", 0x403: "事件部隊(0x455d20)"}
SIDES = {0: "我軍", 1: "友軍", 2: "敵軍"}
FACING = {0: "上", 1: "右", 2: "下", 3: "左"}  # community table; matches the R_00 walk directions
AI_TARGET_PERSON = {3, 5}  # 0x412945 table: these AI types keep the type-2 target person
AI_TARGET_XY = {4, 6}  # and these the two u32 x, y
NONE = 0xffff


class Reader:
    def __init__(self, data, pos):
        self.d, self.p = data, pos

    def u16(self):
        v, = struct.unpack_from("<H", self.d, self.p)
        self.p += 2
        return v

    def param(self, t):
        if t == 1:
            return self.u16()
        tag = self.u16()
        if tag != t:
            raise ValueError(f"parameter type {tag:#x}, expected {t:#x} at {self.p - 2:#x}")
        if t == 4:
            v, = struct.unpack_from("<I", self.d, self.p)
            self.p += 4
            return v
        if t == 5:
            e = self.d.index(b"\0", self.p)
            v = self.d[self.p:e].decode("big5", "replace")
            self.p = e + 1
            return v
        return self.u16()


class Cmd:
    """One command: op, params; op 01 has .test (a Cmd) and .body (list of Cmd)."""

    def __init__(self, at, op, params, test=None, body=None):
        self.at, self.op, self.params, self.test, self.body = at, op, params, test, body


def read_cmd(r):
    at = r.p
    op = r.u16()
    if op not in OPS:
        raise ValueError(f"unknown op {op:#x} at {at:#x}")
    sig = OPS[op][1]
    if sig == "flags":  # 0x4117c1: n flags that must be set, then m flags that must be clear
        on = [r.param(1) for _ in range(r.param(0x35))]
        off = [r.param(1) for _ in range(r.param(0x35))]
        return Cmd(at, op, [on, off])
    return Cmd(at, op, [r.param(t) for t in sig])


def read_body(r):
    out = []
    while True:
        c = read_cmd(r)
        if c.op == 1:
            c.test = read_cmd(r)
            n = r.u16()
            end = r.p + n
            c.body = read_body(r)
            if r.p != end:
                raise ValueError(f"nested block length mismatch at {c.at:#x}")
        out.append(c)
        if c.op == 0:
            return out


def read_eex(data):
    """[(scene offset, [(conditions, body), ...]), ...]"""
    if data[:4] != b"EEX\0":
        raise ValueError("not an EEX file")
    p = 6
    while True:  # header chunks (0x410345)
        t, n = struct.unpack_from("<HH", data, p)
        p += 4 + n
        if t == 0:
            break
    first, = struct.unpack_from("<I", data, p)
    offsets = struct.unpack_from(f"<{(first - p) // 4}I", data, p)
    scenes = []
    for o in offsets:
        count, = struct.unpack_from("<H", data, o)
        q = o + 2
        blocks = []
        for _ in range(count):
            n, = struct.unpack_from("<H", data, q)
            r = Reader(data, q + 2)
            conds = []
            while True:
                c = read_cmd(r)
                conds.append(c)
                if c.op == 0:
                    break
            n2 = r.u16()
            body_end = r.p + n2
            body = read_body(r)
            if r.p != body_end or r.p != q + 2 + n:
                raise ValueError(f"block length mismatch at {q:#x}")
            blocks.append((conds[:-1], body))
            q += 2 + n
        scenes.append((o, blocks))
    return scenes


def walk(cmds, depth=0):
    """Every command with its depth, tests of op 01 included."""
    for c in cmds:
        yield c, depth
        if c.op == 1:
            yield c.test, depth
            yield from walk(c.body, depth + 1)


class Names:
    def __init__(self, game_dir):
        self.persons = [n for n, _ in load_eiketsu5_win_persons(os.path.join(game_dir, "DATA.E5"))]
        with open(os.path.join(game_dir, "IMSG.E5"), "rb") as f:
            imsg = f.read()
        self.imsg = [imsg[o:o + 200].split(b"\0")[0].decode("big5", "replace").rstrip()
                     for o in range(0, len(imsg), 200)]

    def person(self, v):
        if v == NONE:
            return "-"
        if v in PERSON_CODES:
            return PERSON_CODES[v]
        if v < len(self.persons):
            return self.persons[v]
        return f"?{v}"

    def battle_name(self, m):
        return self.imsg[250 + m] if m < 0x3a else ""  # 0x40bfd4


def fmt_value(names, t, v):
    if isinstance(v, str):
        return '"' + v.replace("\n", "\\n") + '"'
    if t in (2, 0x38, 0x39):
        return f"{v}" if v == NONE else f"{v}{names.person(v)}"
    if t == 3:
        return SIDES.get(v, str(v))
    if t == 0x2b:
        return FACING.get(v, str(v))
    return str(v)


def fmt_cmd(names, c):
    name, sig, _ = OPS[c.op]
    if sig == "flags":
        return f"{c.op:02x} {name} 須設 {c.params[0]} 須未設 {c.params[1]}"
    if c.op in (0x46, 0x47):
        n = 11 if c.op == 0x46 else 12
        rows = [c.params[i:i + n] for i in range(0, len(c.params), n)]
        lines = [f"{c.op:02x} {name}"]
        for i, row in enumerate(rows):
            if row[0] != NONE:
                lines.append(f"    #{i:02d} " + " ".join(f"{t:x}:{fmt_value(names, t, v)}"
                                                       for t, v in zip(sig[:n], row)))
        return "\n".join(lines)
    return f"{c.op:02x} {name} " + " ".join(f"{t:x}:{fmt_value(names, t, v)}" for t, v in zip(sig, c.params))


def listing(names, fname, scenes):
    out = [f"# {fname}"]

    def show(cmds, ind):
        for c in cmds:
            pad = "  " * ind
            if c.op == 1:
                out.append(f"{c.at:05x} {pad}IF {fmt_cmd(names, c.test)}")
                show(c.body, ind + 1)
            elif c.op != 0:
                text = fmt_cmd(names, c).replace("\n", "\n      " + pad)
                out.append(f"{c.at:05x} {pad}{text}")

    for si, (o, blocks) in enumerate(scenes):
        for bi, (conds, body) in enumerate(blocks):
            out.append(f"\n== scene {si} block {bi}")
            for c in conds:
                out.append(f"{c.at:05x} WHEN {fmt_cmd(names, c)}")
            show(body, 0)
    return "\n".join(out) + "\n"


def trigger_text(names, conds):
    """The block's conditions in one line (op 02 labels dropped)."""
    parts = [fmt_cmd(names, c) for c in conds if c.op != 2]
    return "; ".join(parts)


def label_of(conds):
    return " ".join(c.params[0] for c in conds if c.op == 2 and c.params[0])


def speakers(text):
    return [ln[1:] for ln in text.split("\n") if ln.startswith("&")]


def battle_rows(names, n, scenes):
    """battles.csv row, deploy.csv rows and the 'appears' events of one S file."""
    setup = {"battle": f"S_{n:02d}"}
    deploy = []
    appear = {}  # person -> trigger text of the block whose op 4C (mode 0) shows it
    for si, (o, blocks) in enumerate(scenes):
        for conds, body in blocks:
            for c, _ in walk(body):
                if si == 0 and c.op == 0x27 and c.params[0] == 3:
                    setup["map"] = c.params[4]
                    setup["name"] = names.battle_name(c.params[4])
                elif c.op == 0x45:
                    p = c.params
                    setup.update(turns=p[2], enemy_level=level_mod(p[3]),
                                 target_person=names.person(p[5]), lose_person=names.person(p[7]))
                elif c.op == 0x19:
                    win, _, lose = c.params[0].partition("失敗條件")
                    setup.setdefault("victory", win.replace("勝利條件", "").strip().replace("\n", " "))
                    setup.setdefault("defeat", lose.strip().replace("\n", " "))
                elif c.op == 0x4c and c.params[0] in (0, 1):
                    key = c.params[1] if c.params[0] == 0 else ("slot", c.params[2])
                    appear.setdefault(key, f"scene{si} " + (trigger_text(names, conds) or "-"))
    for conds, body in scenes[0][1]:
        for c, _ in walk(body):
            if c.op == 0x46:
                for i in range(20):
                    r = c.params[i * 11:(i + 1) * 11]
                    if r[0] != NONE:
                        deploy.append(unit_row(names, n, "友軍", 0xf + i, r[0], r[2], r[3], r[4], r[1], r[5],
                                               r[6], r[7], r[8], r[9], r[10], ""))
            elif c.op == 0x47:
                for i in range(80):
                    r = c.params[i * 12:(i + 1) * 12]
                    if r[0] != NONE:
                        deploy.append(unit_row(names, n, "敵軍", 0x23 + i, r[0], r[3], r[4], r[5], r[2], r[6],
                                               r[7], r[8], r[9], r[10], r[11], "" if r[1] in (0, NONE) else r[1]))
            elif c.op == 0x4b:
                slot, x, y, d, hidden = c.params
                if x == 0 and y == 0:  # unused slot (every battle fills all 15)
                    continue
                deploy.append(unit_row(names, n, "我軍", slot, NONE, x, y, d, hidden, NONE, NONE, NONE, NONE,
                                       0, 0, ""))
    for row in deploy:
        key = ("slot", row["slot"]) if row["side"] == "我軍" else row["person"]
        row["appears"] = appear.get(key, "") if row["hidden"] else ""
    return setup, deploy


def level_mod(v):
    """0x412311 / 0x4125e5: up to 50 adds to the base level, above 50 subtracts v - 50."""
    if v == NONE:
        return 0
    return v if v <= 50 else -(v - 50)


def unit_row(names, n, side, slot, person, x, y, d, hidden, lv, ai_mode, ai, target, tx, ty, flag2):
    if ai in AI_TARGET_PERSON:
        tgt = fmt_value(names, 2, target)
    elif ai in AI_TARGET_XY:
        tgt = f"({tx},{ty})"
    else:
        tgt = ""
    return {"battle": f"S_{n:02d}", "side": side, "slot": slot, "person": person,
            "name": "(玩家選擇)" if side == "我軍" else names.person(person), "x": x, "y": y,
            "facing": FACING.get(d, d), "hidden": 0 if hidden == NONE else hidden,
            "level": "" if side == "我軍" else level_mod(lv),
            "ai_mode": "" if ai_mode == NONE else ai_mode, "ai": "" if ai == NONE else ai, "ai_target": tgt,
            "flag2": flag2}


def event_rows(names, fname, scenes):
    rows = []
    for si, (o, blocks) in enumerate(scenes):
        for bi, (conds, body) in enumerate(blocks):
            trig = trigger_text(names, conds)
            label = label_of(conds)
            base = {"file": fname, "scene": si, "block": bi, "label": label, "trigger": trig}

            def add(kind, at, who="", text="", extra=""):
                rows.append(dict(base, kind=kind, at=f"{at:05x}", participants=who, text=text, detail=extra))

            def scan(cmds, inner):
                for c in cmds:
                    if c.op == 1:
                        t = c.test
                        sub = inner + ("; " if inner else "") + fmt_cmd(names, t) if t.op != 2 else \
                            inner + ("; " if inner else "") + t.params[0]
                        if t.op == 0x12:
                            add("branch", t.at, text=t.params[0].replace("\n", " / "), extra="選擇框")
                        duel = [x for x in c.body if x.op == 0x68]
                        if duel:
                            add_duel(c.body, duel[0], sub)
                            continue
                        scan(c.body, sub)
                        continue
                    if c.op == 0x68:
                        add_duel(cmds, c, inner)
                        return
                    ctx = f" [{inner}]" if inner else ""
                    if c.op == 0x14:
                        add("talk", c.at, "、".join(dict.fromkeys(speakers(c.params[0]))),
                            c.params[0].replace("\n", " "), ctx.strip())
                    elif c.op == 0x15:
                        add("talk", c.at, names.person(c.params[0]), c.params[2].replace("\n", " "), ctx.strip())
                    elif c.op == 0x4c and c.params[0] == 0:
                        add("reinforce", c.at, names.person(c.params[1]), "", ctx.strip())
                    elif c.op == 0x4c and c.params[0] == 1:
                        add("reinforce", c.at, f"我軍 slot {c.params[2]}", "", ctx.strip())
                    elif c.op == 0x53:
                        add("retreat", c.at, names.person(c.params[1]), "", f"26:{c.params[7]}" + ctx)
                    elif c.op == 0x11:
                        add("branch", c.at, "", "", f"跳到 {stage_file(c.params[0] + 1)}" + ctx)
                    elif c.op == 0x27:
                        mode, v = c.params[0], c.params[{0: 1, 1: 2, 2: 3, 3: 4}.get(c.params[0], 1)]
                        add("scene", c.at, "", "", f"背景 2d:{mode} 值 {v}" + ctx)
                    elif c.op == 0x3d:
                        add("item", c.at, names.person(c.params[3]), names.imsg[c.params[0]][:20]
                            if c.params[0] < len(names.imsg) else "", f"物品 {c.params[0]}" + ctx)
                    elif c.op == 0x3b:
                        add("join", c.at, names.person(c.params[0]), "", f"0e:{c.params[1]}" + ctx)
                    elif c.op in (0x19, 0x1a):
                        add("objective", c.at, "", c.params[0].replace("\n", " "), ctx.strip())

            def add_duel(cmds, start, inner):
                a, b = start.params
                lines, winners = [], []
                for x in cmds[cmds.index(start):]:
                    if x.op in (0x60, 0x63):
                        who = names.person(a if x.params[0] == 1 else b)
                        lines.append(f"{who}:{x.params[1]}".replace("\n", " "))
                    elif x.op == 0x62:
                        winners.append(names.person(a if x.params[0] == 1 else b))
                    elif x.op == 0x5f:
                        break
                add("duel", start.at, f"{names.person(a)} vs {names.person(b)}", " / ".join(lines),
                    ("勝:" + "、".join(winners) if winners else "") + (f" [{inner}]" if inner else ""))

            scan(body, "")
    return rows


def jumps(cmds, tests):
    """Op 11 commands with the op 01 tests around them (op 03 = else of the previous test)."""
    for c in cmds:
        if c.op == 0x11:
            yield c, tests
        elif c.op == 1:
            yield from jumps(c.body, tests + [c.test])


def stage_file(s):
    """0x417ef2: stage s (DGROUP 0x4AE750 +7) loads R_(s/2) when even, S_(s/2) when odd."""
    return f"{'S' if s & 1 else 'R'}_{s // 2:02d}"


def draw_battle(map_png, units, out_png):
    from PIL import Image, ImageDraw
    im = Image.open(map_png).convert("RGB")
    dr = ImageDraw.Draw(im)
    colors = {"我軍": (40, 90, 255), "友軍": (40, 200, 60), "敵軍": (230, 40, 40)}
    for u in units:
        x0, y0 = u["x"] * 48, u["y"] * 48
        col = colors[u["side"]]
        if u["hidden"]:
            dr.rectangle([x0 + 4, y0 + 4, x0 + 43, y0 + 43], outline=col, width=3)
        else:
            dr.rectangle([x0 + 4, y0 + 4, x0 + 43, y0 + 43], fill=col, outline=(0, 0, 0))
        dr.text((x0 + 6, y0 + 6), str(u["slot"]), fill=(255, 255, 255))
    im.save(out_png)


@click.command("scenario")
@click.option("--game-dir", required=True, type=click.Path(exists=True), help="games/eiketsu5-win")
@click.option("--out", required=True, type=click.Path(), help="games/eiketsu5-win/extract/scenario")
def scenario(game_dir, out):
    """Disassemble R_/S_*.EEX and list battles, deployments and events."""
    names = Names(game_dir)
    os.makedirs(os.path.join(out, "scripts"), exist_ok=True)
    battles, deploy, events, stages = [], [], [], []
    for path in sorted(glob.glob(os.path.join(game_dir, "[RS]_*.EEX"))):
        fname = os.path.basename(path)[:-4]
        with open(path, "rb") as f:
            scenes = read_eex(f.read())
        with open(os.path.join(out, "scripts", fname + ".txt"), "w", encoding="utf-8") as f:
            f.write(listing(names, fname, scenes))
        events += event_rows(names, fname, scenes)
        if fname[0] == "S":
            setup, units = battle_rows(names, int(fname[2:]), scenes)
            battles.append(setup)
            deploy += units
        for si, (o, blocks) in enumerate(scenes):
            for bi, (conds, body) in enumerate(blocks):
                for c, tests in jumps(body, []):
                    stages.append({"file": fname, "scene": si, "block": bi, "at": f"{c.at:05x}",
                                   "to": stage_file(c.params[0] + 1), "trigger": trigger_text(names, conds),
                                   "if": "; ".join(fmt_cmd(names, t) for t in tests)})
    write_dict_csv(os.path.join(out, "battles.csv"), battles, ["battle", "name", "map", "turns", "enemy_level", "target_person", "lose_person", "victory", "defeat"])
    write_dict_csv(os.path.join(out, "deploy.csv"), deploy, ["battle", "side", "slot", "person", "name", "x", "y", "facing", "hidden", "appears", "level",
               "ai_mode", "ai", "ai_target", "flag2"])
    write_dict_csv(os.path.join(out, "events.csv"), events, ["file", "scene", "block", "at", "kind", "participants", "text", "detail", "label", "trigger"])
    write_dict_csv(os.path.join(out, "stages.csv"), stages, ["file", "scene", "block", "at", "to", "trigger", "if"])
    maps = os.path.join(game_dir, "extract", "battlemap")
    if os.path.isdir(maps):
        os.makedirs(os.path.join(out, "battle"), exist_ok=True)
        for b in battles:
            png = os.path.join(maps, f"{b['map']:02d}.png")
            if os.path.exists(png):
                draw_battle(png, [u for u in deploy if u["battle"] == b["battle"]],
                            os.path.join(out, "battle", f"{b['battle'][2:]}.png"))
    print(f"{len(battles)} battles, {len(deploy)} units, {sum(e['kind'] == 'duel' for e in events)} duels, "
          f"{len(events)} events")


if __name__ == "__main__":
    scenario()
