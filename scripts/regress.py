#!/usr/bin/env python3
"""Regression check for refactors: run every dekoei command this machine has the game files for, hash the outputs,
and compare two runs file by file.

    .venv/bin/python scripts/regress.py run base            # all cases -> scratch/regress/base/manifest.json
    .venv/bin/python scripts/regress.py run after -k nobu1  # only cases whose name contains "nobu1"
    .venv/bin/python scripts/regress.py diff base after     # compare (cases missing from either run are listed, not failed)

Each run first copies dekoei/ to scratch/regress/<label>/src/ and runs that copy, so the code can be edited while a
run is going (a full run takes 40 minutes to an hour; the slowest case is export/santsukuru-win, about 11 minutes).
--src runs another dekoei/ instead (e.g. `git archive HEAD dekoei` unpacked in scratch) for a baseline of the old code;
--old-out for code before 2026-11-18, whose biography / stats-export --out was a file.

Outputs are hashed and then deleted (pass --keep to keep them under scratch/regress/<label>/out/). dataset.json is
hashed without source.revision, which changes with every commit. A case whose --game-dir (or other input dir) is
missing is skipped and recorded as such, so the san8–14 games kept on the NAS just drop out when it is not mounted.
A missing games/<id> or games/steam/<x> is looked up as $NAS_STEAM/<id> or <x> (the NAS layout, notes/steam.md), and a
missing games/<id>/extract as the 素材庫 ~/game-library/koei/<id>. The san7–12 readers find the 繁中版 depot at
<game-dir>/../steam/<appid>-tchinese, which the NAS does not have; point NAS_STEAM at a mirror instead: a real folder
per game holding symlinks to the NAS entries, the depots as symlinks, and steam -> . (symlinked game folders would not
do: <link>/.. resolves on the NAS side).
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEKOEI = os.path.join(ROOT, "dekoei")
PYTHON = os.path.join(ROOT, ".venv", "bin", "python")
GAMES = os.path.join(ROOT, "games")
STEAM = os.path.join(GAMES, "steam")
EXPORT = os.path.join(ROOT, "export", "koei-wiki")
REGRESS = os.environ.get("REGRESS_ROOT", os.path.join(ROOT, "scratch", "regress"))
# 三國志VIII–14 live on the NAS (notes/steam.md), their extract/ in the 素材庫 (notes/koei-items.md); used when the
# games/ copy is gone
NAS = os.environ.get("NAS_STEAM", "/Volumes/Media/games/koei/Steam")
LIBRARY = os.path.expanduser(os.environ.get("GAME_LIBRARY", "~/game-library"))

# dataset id -> --game-dir, where it is not games/<id>
GAME_DIRS = {"nobu14pk-win": f"{STEAM}/292990-tchinese/depot", "nobu15pk-win": f"{STEAM}/628890",
             "nobu16pk-win": f"{STEAM}/1336980"}
# biography reads the 繁中版 depot for 三國志VII–12
BIO_DIRS = {"san7pk-win": f"{STEAM}/628030-tchinese/depot", "san8pk-win": f"{STEAM}/628040-tchinese/depot",
            "san9pk-win": f"{STEAM}/628050-tchinese/depot", "san10pk-win": f"{STEAM}/628060-tchinese/depot",
            "san11pk-win": f"{STEAM}/628070-tchinese/depot", "san12pk-win": f"{STEAM}/628080-tchinese/depot"}

# <game>-extras / -scenario commands: (command, game dir, extra args); output goes to {out}
EXTRAS = [
    ("genchou-extras", "genchou-pc98", []), ("genghis-extras", "genghis-pc98", []),
    ("genghis4-extras", "genghis4pk-win", []), ("genpei-extras", "genpei-dos", []),
    ("koukai-extras", "koukai-pc98", []), ("koukai2-extras", "koukai2-pc98", []),
    ("koukai3-extras", "koukai3-win", []), ("koukai4-extras", "koukai4pk-win", []),
    ("koukaigd-extras", "koukaigd-win", []), ("kouryuuki-extras", "kouryuuki-dos", []),
    ("nobu4-extras", "nobu4-pc98", []), ("nobu5-extras", "nobu5pk-win", ["--pc98-dir", f"{GAMES}/nobu5-pc98"]),
    ("nobu6-extras", "nobu6pk-pc98", ["--base-dir", f"{GAMES}/nobu6-pc98"]),
    ("nobu7-extras", "nobu7pk-win", []), ("nobu8-extras", "nobu8pk-win", []), ("nobu9-extras", "nobu9pk-win", []),
    ("nobu10-extras", "nobu10pk-win", []), ("nobu11-extras", "nobu11pk-win", []),
    ("nobu12-extras", "nobu12pk-win", []), ("nobu13-extras", "nobu13pk-win", []),
    ("nobu14-extras", "nobu14pk-win", []), ("nobu15-extras", "nobu15pk-win", []),
    ("nobu16-extras", "nobu16pk-win", []),
    ("san4-extras", "san4pk-pc98", ["--dos-dir", f"{GAMES}/san4pk-dos"]),
    ("san5-extras", "san5pk-pc98", ["--dos-dir", f"{GAMES}/san5pk-dos"]),
    ("san7-extras", "san7pk-win", []), ("san8-extras", "san8pk-win", []), ("san9-extras", "san9pk-win", []),
    ("san10-extras", "san10pk-win", []), ("san11-extras", "san11pk-win", []), ("san12-extras", "san12pk-win", []),
    ("san13-extras", "san13pk-win", []), ("san14-extras", "san14pk-win", []),
    ("sanr-extras", "sanr-win", []), ("santsukuru-extras", "santsukuru-win", []),
    ("suikoden2-extras", "suikoden2-win", []), ("taikoh5-extras", "taikoh5dx-win", []),
    ("tk3-extras", "tk3pk-pc98", []),
    ("eiketsu-scenario", "eiketsu-dos", []), ("koumei-scenario", "koumei-win", []),
    ("eiketsu5-scenario", "eiketsu5-win", []),
]
# legacy per-game face / person subcommands, run with the case's output directory as cwd (they write to _output/ by
# default); person output (stdout) is kept as stdout.txt. {G} is games/
LEGACY = [
    "eiketsu face -f {G}/eiketsu-dos/FACEDAT.R3", "europe face -f {G}/europe-dos/FACE.DAT",
    "genpei cg -f {G}/genpei-dos/Mainstl.gp", "genpei face --game-dir {G}/genpei-dos",
    "genpei montage --game-dir {G}/genpei-dos", "ishin face -f {G}/ishin-pc98/KAODAT.DAT",
    "ishin2 face -f {G}/ishin2-win/FACE.I2",
    "kohryuki face -f {G}/kouryuuki-dos/KAO.KR1", "kohryuki person -d {G}/kouryuuki-dos -s 1 -t csv",
    "koukai face -f {G}/koukai-dos/KAO.PUT", "koukai2 face -f {G}/koukai2-pc98/KAO.LZW",
    "koukai3 face -f {G}/koukai3-win/MALE.CDS", "lempe face -f {G}/lempe-dos/KAODATA.DAT",
    "lempe person -f {G}/lempe-dos/NPDATA.CIM -s 1 -t csv", "liberty cg -f {G}/liberty-dos/EVENT.IDX",
    "liberty face -f {G}/liberty-dos/FACE.IDX", "nobu3 face -f {G}/nobu3-dos/KAODATA.DAT",
    "nobu3 person --game-dir {G}/nobu3-pc98", "nobu4 face -f {G}/nobu4-dos/KAODATA.DAT",
    "nobu4 person --game-dir {G}/nobu4-pc98", "royal face -f {G}/royal-pc98/KAODATA.DAT",
    "san1 face -f {G}/san1-dos/PICDATA.DAT", "san1 person -f {G}/san1-dos/SINADATA.DAT -s 1 -t csv",
    "san2 face -f {G}/san2-dos/KAODATA.DAT", "san2 person -f {G}/san2-dos/SCENARIO.DAT -t {G}/san2-dos/TAIKI.DAT --to csv",
    "san2 grp --game_dir {G}/san2-dos", "san2 grpa --game_dir {G}/san2-dos", "san2 map --game_dir {G}/san2-dos",
    "san3 face -f {G}/san3-dos/KAODATA.DAT", "san3 person -f {G}/san3-dos/SNDATA1.CIM --to csv",
    "san4 face -f {G}/san4pk-dos/KAODATAP.S4", "san4 person --game-dir {G}/san4pk-dos",
    "san5 face -f {G}/san5pk-dos/KAODATAP.S5", "san5 person --game-dir {G}/san5pk-dos",
    "san6 face -d {G}/san6pk-win", "san6 person --game-dir {G}/san6pk-win",
    "san7 face -d {G}/san7pk-win", "san7 person --game-dir {G}/san7pk-win",
    "san8 person --game-dir {G}/san8pk-win", "san9 person --game-dir {G}/san9pk-win",
    "san10 person --game-dir {G}/san10pk-win", "san13 person --game-dir {G}/san13pk-win",
    "suikoden face -f {G}/suikoden-dos/KAOIBM.DAT", "suikoden person -d {G}/suikoden-dos -s 1 -t csv",
    "taikoh face -f {G}/taikoh-dos/KAO.PUT", "tk2 face -f {G}/tk2-pc98/KAO.TK2", "winning face -d {G}/winning-pc98",
]
# top-level directories the copied dekoei/ reaches through ../ (CNS table, face-crop boxes, captures, games, the
# koei-wiki persons export that items-export reads)
SRC_LINKS = ["Unicode", "research", "captures", "games", "MISC_TABLE", "export"]
# <game> <subcommand> with --game-dir / --out
GAME_SUBCOMMANDS = [
    ("celt art", "celt-win"), ("celt music", "celt-win"),
    ("eiketsu battlemap", "eiketsu-pc98"), ("eiketsu battlebg", "eiketsu-pc98"),
    ("koumei battlemap", "koumei-win"), ("eiketsu5 battlemap", "eiketsu5-win"), ("eiketsu5 scene", "eiketsu5-win"),
    ("san1 eventcg", "san1-pc98"), ("san1 strings", "san1-pc98"),
    ("san2 battlemap", "san2-pc98"), ("san3 battlemap", "san3-pc98"), ("san4 battlemap", "san4-pc98"),
    ("san5 battlemap", "san5pk-pc98"), ("suikoden battlemap", "suikoden-pc98"), ("suikoden worldmap", "suikoden-pc98"),
]


def nas(path):
    """path, or its NAS copy when path is gone (games/<id> -> NAS/<id>, games/steam/<x> -> NAS/<x>)."""
    if os.path.exists(path):
        return path
    rel = os.path.relpath(path, STEAM if path.startswith(STEAM) else GAMES)
    alt = os.path.join(NAS, rel)
    return alt if os.path.exists(alt) else path


def game_dir(dataset, table=GAME_DIRS):
    return nas(table.get(dataset) or GAME_DIRS.get(dataset) or os.path.join(GAMES, dataset))


def extract_dir(dataset):
    ex = os.path.join(GAMES, dataset, "extract")
    lib = os.path.join(LIBRARY, "koei", dataset)
    return ex if os.path.exists(ex) or not os.path.exists(lib) else lib


def choices(command):
    """The DATASET choices of a top-level dekoei command, read from the click definition."""
    sys.path.insert(0, DEKOEI)
    cwd = os.getcwd()
    os.chdir(DEKOEI)
    try:
        import dekoei
        cmd = dekoei.dekoei.commands[command]
        return list(next(p for p in cmd.params if p.name == "dataset").type.choices)
    finally:
        os.chdir(cwd)


def cases(old_out=False):
    """[(name, argv with {out}, [input dirs that must exist])]. old_out: biography and stats-export take a file
    (the code before 2026-11-18), written as {out}/<dataset>.jsonl so the names match the current code's."""
    out = []
    for ds in choices("export"):
        out.append((f"export/{ds}", ["export", ds, "--game-dir", game_dir(ds), "--out", "{out}"], [game_dir(ds)]))
    for ds in choices("persons-export"):
        out.append((f"persons/{ds}", ["persons-export", ds, "--game-dir", game_dir(ds), "--out", "{out}",
                                      "--places", f"{EXPORT}/places"], [game_dir(ds)]))
    for ds in choices("places-export"):
        out.append((f"places/{ds}", ["places-export", ds, "--game-dir", game_dir(ds), "--out", "{out}"], [game_dir(ds)]))
    for ds in choices("biography"):
        d = game_dir(ds, BIO_DIRS)
        out.append((f"biography/{ds}", ["biography", ds, "--game-dir", d, "--out",
                                        f"{{out}}/{ds}.jsonl" if old_out else "{out}"], [d]))
    for ds in choices("stats-export"):
        out.append((f"stats/{ds}", ["stats-export", ds, "--game-dir", game_dir(ds), "--out",
                                    f"{{out}}/{ds}.jsonl" if old_out else "{out}"],
                    [game_dir(ds)]))
    for ds in choices("items-export"):
        ex = extract_dir(ds)
        out.append((f"items/{ds}", ["items-export", ds, "--extract", ex, "--game-dir", game_dir(ds), "--out", "{out}"],
                    [ex, game_dir(ds)]))
    for ds in choices("events-export"):
        ex = extract_dir(ds)
        out.append((f"events/{ds}", ["events-export", ds, "--extract", ex, "--out", "{out}"], [ex]))
    ex = os.path.join(GAMES, "genchou-pc98", "extract")
    out.append(("ordo/genchou-pc98", ["ordo-export", "genchou-pc98", "--extract", ex, "--out", "{out}"], [ex]))
    for cmd, ds, extra in EXTRAS:
        d = game_dir(ds)
        dirs = [d] + [a for a in extra if a.startswith("/")]
        out.append((f"extras/{cmd}", [cmd, "--game-dir", d, "--out", "{out}", *extra], dirs))
    for cmd, ds in GAME_SUBCOMMANDS:
        d = game_dir(ds)
        out.append((f"game/{cmd.replace(' ', '-')}", [*cmd.split(), "--game-dir", d, "--out", "{out}"], [d]))
    d = game_dir("san1-pc98")
    out.append(("game/san1-worldmap", ["san1", "worldmap", "--game-dir", d, "--out", "{out}/world.png"], [d]))
    for line in LEGACY:
        argv = line.replace("{G}", GAMES).split()
        dirs = [os.path.dirname(a) if os.path.splitext(a)[1] else a for a in argv if a.startswith(GAMES)]
        out.append((f"legacy/{argv[0]}-{argv[1]}", argv, dirs))
    return out


def file_hash(path):
    if os.path.basename(path) == "dataset.json":
        meta = json.load(open(path, encoding="utf-8"))
        meta.get("source", {}).pop("revision", None)
        return hashlib.sha256(json.dumps(meta, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_case(case, label, keep, src):
    name, argv, dirs = case
    missing = [d for d in dirs if not os.path.isdir(d)]
    if missing:
        return name, {"status": "skipped", "missing": missing}
    out = os.path.join(REGRESS, label, "out", name)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    t = time.time()
    legacy = name.startswith("legacy/")
    try:
        p = subprocess.run([PYTHON, os.path.join(src, "dekoei.py"), *(a.replace("{out}", out) for a in argv)],
                           cwd=out if legacy else src, capture_output=True, text=True, timeout=7200)
    except subprocess.TimeoutExpired:
        return name, {"status": "timeout", "seconds": round(time.time() - t, 1)}
    if legacy and argv[1] == "person":
        with open(os.path.join(out, "stdout.txt"), "w") as f:
            f.write(p.stdout)
    files = {}
    for base, _, names in os.walk(out):
        for n in names:
            path = os.path.join(base, n)
            files[os.path.relpath(path, out)] = file_hash(path)
    if not keep:
        shutil.rmtree(out)
    result = {"status": "ok" if p.returncode == 0 else "failed", "seconds": round(time.time() - t, 1), "files": files}
    if p.returncode:
        result["stderr"] = p.stderr[-2000:]
    return name, result


def cmd_run(args):
    todo = [c for c in cases(args.old_out) if not args.k or any(k in c[0] for k in args.k)]
    # snapshot of the code under test
    src_root = os.path.join(REGRESS, args.label, "src")
    shutil.rmtree(src_root, ignore_errors=True)
    src = os.path.join(src_root, "dekoei")
    shutil.copytree(args.src or DEKOEI, src, ignore=shutil.ignore_patterns("__pycache__", "export"))
    for d in SRC_LINKS:
        os.symlink(os.path.join(ROOT, d), os.path.join(src_root, d))
    path = os.path.join(REGRESS, args.label, "manifest.json")
    manifest = json.load(open(path)) if os.path.exists(path) and args.k else {}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(args.jobs) as pool:
        futures = [pool.submit(run_case, c, args.label, args.keep, src) for c in todo]
        for f in concurrent.futures.as_completed(futures):
            name, result = f.result()
            manifest[name] = result
            extra = f" {len(result['files'])} files {result['seconds']}s" if "files" in result else ""
            print(f"{result['status']:8} {name}{extra}", flush=True)
            # written after every case, so a long run can be diffed before it ends
            json.dump(dict(sorted(manifest.items())), open(path, "w"), indent=1)
    counts = {s: sum(r["status"] == s for r in manifest.values()) for s in ("ok", "failed", "timeout", "skipped")}
    print(f"{path}: {counts}")


def cmd_diff(args):
    a, b = (json.load(open(os.path.join(REGRESS, label, "manifest.json"))) for label in (args.a, args.b))
    bad = 0
    for name in sorted(set(a) | set(b)):
        ra, rb = a.get(name), b.get(name)
        if ra is None or rb is None:
            print(f"only in {args.a if rb is None else args.b}: {name}")
            continue
        if ra["status"] == rb["status"] == "skipped":
            continue
        if ra["status"] != rb["status"]:
            bad += 1
            print(f"STATUS {name}: {ra['status']} -> {rb['status']}")
            if "stderr" in rb:
                print("  " + rb["stderr"].strip().splitlines()[-1])
            continue
        fa, fb = ra.get("files", {}), rb.get("files", {})
        changed = sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
        if changed:
            bad += 1
            print(f"FILES {name}: {len(changed)} differ")
            for k in changed[:10]:
                print(f"  {k}: {'missing' if k not in fa else ''}{'gone' if k not in fb else ''}")
    print("identical" if not bad else f"{bad} cases differ")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("label")
    r.add_argument("-k", action="append", help="only cases whose name contains this (repeatable); merges into an "
                                                "existing manifest")
    r.add_argument("--jobs", type=int, default=4)
    r.add_argument("--keep", action="store_true", help="keep the outputs")
    r.add_argument("--src", help="the dekoei/ to test instead of the working tree's (e.g. git archive of an older "
                                 "commit); the cases still come from the working tree")
    r.add_argument("--old-out", action="store_true", help="biography / stats-export --out as a file (code before "
                                                         "2026-11-18)")
    d = sub.add_parser("diff")
    d.add_argument("a")
    d.add_argument("b")
    args = ap.parse_args()
    if args.cmd == "run":
        cmd_run(args)
    else:
        sys.exit(cmd_diff(args))


if __name__ == "__main__":
    main()
