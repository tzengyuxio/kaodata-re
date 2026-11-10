"""寶物 for koei-wiki (koei-items/1, spec in koei-wiki docs/items-format.mkdn): one JSONL line per item slot,
{"dataset", "id", "name", ...}; holders use the kaodata person id. Most fields come from the *-extras CSVs in
games/<id>/extract/items/ (run the game's *-extras first); 信長6 and 11 read the holder slots from the scenario files
again, because their CSVs only keep the holder's name. Which field comes from where and how sure it is:
notes/<game>.md「事件、插圖、道具」and the 寶物 sections; the export per dataset is in notes/koei-items.md."""
import csv
import json
import os
import struct

import click


def _rows(extract, name):
    with open(os.path.join(extract, "items", name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _flat(text):
    """the CSV text with the game's line wrapping dropped"""
    return "".join(line.strip() for line in text.splitlines())


def _scenario_numbers(rows, key, extract=None):
    """scenario file name -> number: the numbers of the persons export (extract/tables/scenarios.csv, written by
    wiki_san<N>; files not in it are left out), else 1-based in file name order"""
    path = extract and os.path.join(extract, "tables", "scenarios.csv")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            return {os.path.basename(r["file"]): int(r["scenario"]) for r in csv.DictReader(f)}
    return {s: n + 1 for n, s in enumerate(sorted({r[key] for r in rows}))}


def _person_holders(rows, scenario, holder, numbers=None):
    """{item id: [{"scenario", "person"}]} from rows that name a scenario and a kaodata person id"""
    out = {}
    for r in rows:
        if r[holder] and (numbers is None or r[scenario] in numbers):
            s = numbers[r[scenario]] if numbers else int(r[scenario])
            out.setdefault(r["_item"], []).append({"scenario": s, "person": int(r[holder])})
    return out


def _clean(row):
    return {k: v for k, v in row.items() if v is not None and v is not False and v != "" and v != []}


# 三國志IV PK (PC-98): holders.csv already has the kaodata id; descriptions in Japanese and the DOS 中文版's
def items_san4pk_pc98(extract):
    holders = {}
    for r in _rows(extract, "holders.csv"):
        holders.setdefault(int(r["item"]), []).append({"scenario": int(r["scenario"]), "person": int(r["kaodata_id"])})
    out = []
    for r in _rows(extract, "items.csv"):
        i = int(r["id"])
        dup = 24 <= i <= 30
        out.append({"id": i, "name": r["name"], "kind": r["kind_name"], "description": r["description"],
                    "descriptionZh": r["description_zh"], "holders": holders.get(i, []), "uncertain": ["kind"],
                    "notes": "玉璽、青釭等 7 件的複本，說明沒有效果欄，各劇本都沒人持有，用途不明" if dup else ""})
    return out


# 三國志VII PK: holder = kaodata id (the 武將編號 of the 人物表 cell); 12 scenarios D_Sn001-
def items_san7pk_win(extract):
    rows = _rows(extract, "holders.csv")
    for r in rows:
        r["_item"] = int(r["item"])
    holders = _person_holders(rows, "scenario", "holder", _scenario_numbers(rows, "scenario", extract))
    return [{"id": int(r["item"]), "name": r["name"], "kind": r["kind"], "price": int(r["value"]),
             "description": _flat(r["description"]), "holders": holders.get(int(r["item"]), []),
             "uncertain": ["kind", "price"]} for r in _rows(extract, "items.csv")]


def _present(dataset):
    """{(person id, scenario)} of the people on the map at the start of a scenario, from the persons export
    (statuses 未登場, 未発見, 死亡 and people without an entry are not there)"""
    out = set()
    path = os.path.join(os.path.dirname(__file__), "..", "export", "koei-wiki", "persons", f"{dataset}.jsonl")
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            for e in p.get("scenarios", []):
                if e["status"] not in ("未登場", "未発見", "死亡"):
                    out.add((p["id"], e["scenario"]))
    return out


# 三國志VIII PK: D_Sce.s8 0x129C5, 112 x 5 bytes: u8 item, u16 start year, u16 person id (0xFFFF nobody); the
# scenario of year Y takes, per item, the last record with start year <= Y (notes/san8.md「koei-wiki 匯出：人物」).
# Holders not on the map in that year (未登場 or dead) are left out. Items placed in a city: one city per item in the
# item table, the same for every scenario as far as the table goes, so it goes to notes, not holders.
SAN8_HOLDERS = 0x129C5
SAN8_CITY_GAIJI = {"": "鄴"}  # 冀州の中心であり in the 情勢 texts


def items_san8pk_win(extract, game_dir):
    with open(os.path.join(game_dir, "D_Sce.s8"), "rb") as f:
        d = f.read()
    recs = {}
    for k in range(struct.unpack_from("<H", d, 16)[0]):
        item, year, person = struct.unpack_from("<BHH", d, SAN8_HOLDERS + 5 * k)
        recs.setdefault(item, []).append((year, person))
    present = _present("san8pk-win")
    with open(os.path.join(extract, "tables", "scenarios.csv"), encoding="utf-8-sig") as f:
        years = [(int(r["scenario"]), int(r["year"])) for r in csv.DictReader(f)]
    holders = {}
    for item, rs in recs.items():
        for n, year in years:
            cur = [p for y, p in sorted(rs) if y <= year]
            if cur and cur[-1] != 0xFFFF and (cur[-1], n) in present:
                holders.setdefault(item, []).append({"scenario": n, "person": cur[-1]})
    out = []
    for r in _rows(extract, "items.csv"):
        i, city = int(r["id"]), r["start"]
        city = "".join(SAN8_CITY_GAIJI.get(c, c) for c in city)
        out.append({"id": i, "name": r["name"], "kind": r["type_name"], "price": int(r["value"]),
                    "description": r["description"], "holders": holders.get(i, []),
                    "uncertain": ["kind", "price"],
                    "notes": f"寶物表記開局放在都市「{city}」（各劇本是否相同沒確認）" if city and city != "人物" else ""})
    return out


# 三國志IX PK: state 2 = held; the place is a city number without a name in the CSV, so it is not exported
def items_san9pk_win(extract):
    rows = _rows(extract, "holders.csv")
    for r in rows:
        r["_item"] = int(r["item"])
    holders = _person_holders(rows, "scenario", "holder", _scenario_numbers(rows, "scenario", extract))
    return [{"id": int(r["id"]), "name": r["name"], "reading": r["reading"], "kind": r["kind_name"],
             "price": int(r["value"]), "description": _flat(r["description"]),
             "holders": holders.get(int(r["id"]), []), "uncertain": ["kind", "price", "holders"]}
            for r in _rows(extract, "items.csv")]


# 三國志X PK: person or city; holder slots 763- are not kaodata characters (no name in the game's 人物 table)
SAN10_PEOPLE = 650


def items_san10pk_win(extract):
    rows = _rows(extract, "holders.csv")
    numbers = _scenario_numbers(rows, "scenario", extract)
    holders, outside = {}, {}
    for r in rows:
        if r["scenario"] not in numbers:  # the base game's Sce00?.s10; the PK's ScePK*.s10 are the ones exported
            continue
        i, s = int(r["id"]), numbers[r["scenario"]]
        if r["holder"] and int(r["holder"]) < SAN10_PEOPLE:
            holders.setdefault(i, []).append({"scenario": s, "person": int(r["holder"])})
        elif r["holder"]:
            outside.setdefault(i, set()).add(int(r["holder"]))
        elif r["cityName"]:
            holders.setdefault(i, []).append({"scenario": s, "other": r["cityName"]})
    out = []
    for r in _rows(extract, "items.csv"):
        i = int(r["id"])
        note = f"有劇本由人物槽 {'、'.join(map(str, sorted(outside[i])))} 持有，這些槽不在 kaodata 資料集裡" if i in outside else ""
        out.append({"id": i, "name": r["name"], "reading": r["reading"], "kind": r["kindName"],
                    "description": r["description"], "holders": holders.get(i, []), "notes": note})
    return out


# 三國志11 PK: person or place; 7 empty 「アイテム」 slots are skipped
def items_san11pk_win(extract):
    holders = {}
    rows = _rows(extract, "holders.csv")
    numbers = _scenario_numbers(rows, "scenario", extract)
    for r in rows:
        if r["scenario"] not in numbers:
            continue
        i, s = int(r["item"]), numbers[r["scenario"]]
        if r["holder_id"]:
            holders.setdefault(i, []).append({"scenario": s, "person": int(r["holder_id"])})
        elif r["place"]:
            holders.setdefault(i, []).append({"scenario": s, "other": r["place"]})
    return [{"id": int(r["id"]), "name": r["name"], "reading": r["reading"], "kind": r["kind_name"],
             "price": int(r["value"]), "holders": holders.get(int(r["id"]), []),
             "uncertain": ["kind", "price", "holders"]}
            for r in _rows(extract, "items.csv") if not r["notes"]]


# 三國志12 PK: the holder is bits 448-458 of the 76-byte 名品 record (part 0x8F) of each PK/Scenario/ScenarioN.dat
# (0x7FF nobody; 赤兎馬 董卓 184, 呂布 190 and 195, 関羽 in 5), a person id; holders not on the map are left out
SAN12_ITEMS, SAN12_ITEM_SIZE, SAN12_HOLDER = 0x8F, 76, (448, 11)


def items_san12pk_win(extract, game_dir):
    import wiki_san12 as w
    present = _present("san12pk-win")
    holders = {}
    for n in w.SCENARIOS:
        part = w._parts(os.path.join(game_dir, "PK", "Scenario", f"Scenario{n}.dat"))[SAN12_ITEMS]
        for k, v in enumerate(w._records(part, SAN12_ITEM_SIZE)):
            h = w._bits(v, SAN12_HOLDER)
            if h != w.NONE and (h, n) in present:
                holders.setdefault(k, []).append({"scenario": n, "person": h})
    return [{"id": int(r["id"]), "name": r["name"], "reading": r["reading"], "kind": r["kindName"],
             "price": int(r["value"]), "description": r["description"], "holders": holders.get(int(r["id"]), []),
             "pk": r["pk"] == "pk", "uncertain": ["kind", "price"]} for r in _rows(extract, "items.csv")]


# 三國志13 PK: table 7 of scenario_00-10 (PK items 942-952), one row per item: col1 holder (person id, -1 none), col3
# place (places export id, 255 none), col4 1 = held, 0 = lying in the place; 2 (11 rows) not known, left out
def items_san13pk_win(extract, game_dir):
    import san13_extras
    import wiki_san13 as w
    present = _present("san13pk-win")
    places = {}
    with open(os.path.join(os.path.dirname(__file__), "..", "export", "koei-wiki", "places", "san13pk-win.jsonl"),
              encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            places[p["id"]] = p["name"]
    holders = {}
    for n, e in enumerate(w.SCENARIOS, 1):
        for k, r in enumerate(w._table(game_dir, e, 7)[:san13_extras.ITEM_COUNT]):
            owner, place, state = r[1], r[3], r[4]
            if state == 1 and owner != -1:
                if (owner, n) in present:
                    holders.setdefault(k, []).append({"scenario": n, "person": owner})
            elif state in (0, 1) and place != 255:
                holders.setdefault(k, []).append({"scenario": n, "other": places[place]})
    zh = san13_extras.zh_items(game_dir)
    return [{"id": int(r["id"]), "name": r["name"], "nameZh": zh[int(r["id"])][0], "reading": r["reading"],
             "kind": r["categoryName"], "price": int(r["price?"]), "description": r["description"],
             "descriptionZh": zh[int(r["id"])][1], "holders": holders.get(int(r["id"]), []),
             "uncertain": ["price", "holders"]} for r in _rows(extract, "items.csv")]


# 三國志14 PK: scenario 01 only (the others are not local). The decoded scedaex01.s14 has the items' state at
# 0x69791 + 65 x item number: u16 holder (game person number, id = number - 1, 2001 -> 1000; 0 nobody), found by
# 赤兎馬 董卓, 青龍偃月刀 関羽, 蛇矛 張飛, 方天画戟 呂布, 雌雄一対の剣 劉備, 古錠刀 孫堅 lining up; the record goes on
# with the Japanese name. Holders not on the map (未登場, 未発見) are left out.
SAN14_HOLDERS, SAN14_ITEM_SIZE = 0x69791, 65


def items_san14pk_win(extract, game_dir):
    import wiki_san14 as w
    present = _present("san14pk-win")
    with open(os.path.join(extract, "tables", "scenarios.csv"), encoding="utf-8-sig") as f:
        scenarios = [(int(r["scenario"]), os.path.basename(r["file"])) for r in csv.DictReader(f)]
    holders = {}
    for n, file in scenarios:
        _, d = w._decode(os.path.join(game_dir, "0010_JP", file))
        for r in _rows(extract, "items.csv"):
            i = int(r["id"])
            h = struct.unpack_from("<H", d, SAN14_HOLDERS + SAN14_ITEM_SIZE * i)[0]
            assert d[SAN14_HOLDERS + SAN14_ITEM_SIZE * i + 6:][:2 * len(r["name"])].decode("utf-16-le") == r["name"], (file, i)
            pid = 1000 if h == 2001 else h - 1
            if h and (pid, n) in present:
                holders.setdefault(i, []).append({"scenario": n, "person": pid})
    return [{"id": int(r["id"]), "name": r["name"], "nameZh": r["nameZh"], "reading": r["reading"], "kind": r["kind"],
             "price": int(r["value"]), "description": r["description"], "descriptionZh": _flat(r["descriptionZh"]),
             "holders": holders.get(int(r["id"]), []), "uncertain": ["price"]} for r in _rows(extract, "items.csv")]


# 信長の野望・天翔記 PK (PC-98): holder = name-record slot (1-based) of each scenario; its face number gives the id
def items_nobu6pk_pc98(extract, game_dir):
    import nobu6_extras as e
    import wiki_nobu6 as w
    face_id, _ = w._ids(game_dir)
    holders = {}
    for s, sc in enumerate(w._parts(game_dir, "SNDATA.N6P")):
        for i in range(e.ITEM_COUNT):
            h = struct.unpack_from("<H", sc, e.ITEMS + e.ITEM_SIZE * i + 0xF)[0]
            if h != 0xFFFF:
                rec = sc[w.NAMES + 18 * (h - 1):][:18]
                holders.setdefault(i + 1, []).append({"scenario": s + 1, "person": face_id[w._u16(rec, 14)]})
    out = []
    for r in _rows(extract, "kahou.csv"):
        i = int(r["id"])
        note = f"說明的標題寫成「{r['description_name']}」" if r["description_name"] else ""
        out.append({"id": i, "name": r["name"], "reading": r["reading"], "kind": r["kind_name"],
                    "effects": [{"target": r["stat"], "amount": int(r["bonus"])}] if r["stat"] else [],
                    "description": r["description"], "holders": holders.get(i, []), "notes": note})
    return out


def _numbered_holders(r, count, offset):
    """holder_sNN columns of 'n name' -> [{"scenario", "person"}], person = n + offset"""
    out = []
    for s in range(1, count + 1):
        v = r[f"holder_s{s:02d}"]
        if v:
            out.append({"scenario": s, "person": int(v.split(" ", 1)[0]) + offset})
    return out


# 信長の野望・将星録 PK: person n (1-based) is kaodata id n - 1; kind has no name in the game (only a number)
def items_nobu7pk_win(extract):
    out = []
    for r in _rows(extract, "kahou.csv"):
        note = f"訊息裡寫成「{r['name_message']}」" if r["name_message"] else ""
        out.append({"id": int(r["no"]), "name": r["name"], "reading": r["reading"], "grade": r["grade"],
                    "description": _flat(r["description"]), "holders": _numbered_holders(r, 10, -1),
                    "uncertain": ["grade"], "notes": note})
    return out


# 信長の野望・烈風伝 PK: person n is kaodata id n; no description text was found
def items_nobu8pk_win(extract):
    return [{"id": int(r["no"]), "name": r["name"], "kind": r["kind_name"], "grade": r["grade"],
             "price": int(r["value_s10"]), "holders": _numbered_holders(r, 10, 0), "uncertain": ["grade", "price"]}
            for r in _rows(extract, "kahou.csv")]


# 信長の野望・嵐世記 PK: person holders by id, 都市 holders by name
def items_nobu9pk_win(extract):
    holders = {}
    for r in _rows(extract, "holders.csv"):
        h = ({"person": int(r["holder_id"])} if r["holder_type"] == "person" else {"other": r["holder"]})
        holders.setdefault(int(r["slot"]), []).append({"scenario": int(r["scenario"]), **h})
    return [{"id": int(r["slot"]), "name": r["name"], "reading": r["reading"], "kind": r["kind_name"],
             "grade": r["grade"], "holders": holders.get(int(r["slot"]), []), "pk": r["pk"] == "1",
             "uncertain": ["grade"]} for r in _rows(extract, "kahou.csv")]


# 信長の野望・蒼天録 PK
def items_nobu10pk_win(extract):
    holders = {}
    for r in _rows(extract, "holders.csv"):
        holders.setdefault(int(r["item"]), []).append({"scenario": int(r["scenario"]), "person": int(r["holder"])})
    out = []
    for r in _rows(extract, "kahou.csv"):
        i = int(r["id"])
        note = f"列伝裡寫成「{r['name_retsuden']}」" if r["name_retsuden"] else ""
        out.append({"id": i, "name": r["name"], "reading": r["reading"], "kind": r["kind"], "grade": r["grade"],
                    "description": r["description"], "holders": holders.get(i, []), "notes": note})
    return out


# 信長の野望・天下創世 PK: holder serial = person slot (kaodata id when it is an officer slot) or a 勢力
def items_nobu11pk_win(extract, game_dir):
    import nobu11_extras as e
    import wiki_nobu11 as w
    officers = set(w.OFFICERS)
    holders = {}
    for n, year in w.SCENARIOS:
        db = w._database(os.path.join(game_dir, "scenario"), n)
        persons = w._persons(db)
        for k in range(e.KAHOU_COUNT):
            serial = w._u16(db, e.KAHOU + e.KAHOU_SIZE * k + 57)
            if serial == 0xFFFF:
                continue
            if serial in e.FACTION_SERIALS:
                h = {"other": f"{e._faction_lord(db, persons, serial)}勢力"}
            else:
                slot = serial - w.PERSONS[0]
                h = {"person": slot} if slot in officers else {"other": w._person_name(persons[slot])}
            holders.setdefault(k, []).append({"scenario": n, **h})
    out = []
    for r in _rows(extract, "kahou.csv"):
        i = int(r["id"])
        note = f"說明的標題寫成「{r['textName']}」" if r["textName"] else ""
        out.append({"id": i, "name": r["name"], "reading": r["reading"], "kind": r["pictureKind"],
                    "grade": r["gradeName"], "description": r["text"], "holders": holders.get(i, []),
                    "uncertain": ["kind"], "notes": note})
    return out


# 信長の野望・革新 PK: owners are 'NN:name'; every name is one person of the persons export
def items_nobu12pk_win(extract):
    ids = {}
    with open(os.path.join(os.path.dirname(__file__), "..", "export", "koei-wiki", "persons",
                           "nobu12pk-win.jsonl"), encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            for n in {p["name"], p.get("nameJa", p["name"])}:
                ids.setdefault(n, set()).add(p["id"])
    out = []
    for r in _rows(extract, "kahou.csv"):
        holders = []
        for t in r["owners"].split():
            s, name = t.split(":", 1)
            (pid,) = ids[name]
            holders.append({"scenario": int(s), "person": pid})
        note = f"說明的標題寫成「{r['description_name']}」" if r["description_name"] else ""
        out.append({"id": int(r["id"]), "name": r["name"], "reading": r["reading"], "kind": r["kind"],
                    "grade": r["grade_name"], "description": r["description"], "holders": holders,
                    "uncertain": ["grade"], "notes": note})
    return out


DATASETS = {"san4pk-pc98": items_san4pk_pc98, "san7pk-win": items_san7pk_win, "san8pk-win": items_san8pk_win,
            "san9pk-win": items_san9pk_win, "san10pk-win": items_san10pk_win, "san11pk-win": items_san11pk_win,
            "san12pk-win": items_san12pk_win, "san13pk-win": items_san13pk_win, "san14pk-win": items_san14pk_win,
            "nobu6pk-pc98": items_nobu6pk_pc98, "nobu7pk-win": items_nobu7pk_win, "nobu8pk-win": items_nobu8pk_win,
            "nobu9pk-win": items_nobu9pk_win, "nobu10pk-win": items_nobu10pk_win,
            "nobu11pk-win": items_nobu11pk_win, "nobu12pk-win": items_nobu12pk_win}
NEEDS_GAME = {"nobu6pk-pc98", "nobu11pk-win", "san8pk-win", "san12pk-win", "san13pk-win", "san14pk-win"}
# 三國志VII-12: nameZh / descriptionZh from the Steam 繁中版 (games/steam/<appid>-tchinese/depot, next to the game
# directory), read by <module>.zh_items(depot) -> {item id: (name, description)}; 11 has no item descriptions
ZH = {"san7pk-win": ("san7_extras", 628030), "san8pk-win": ("san8_extras", 628040),
      "san9pk-win": ("san9_extras", 628050), "san10pk-win": ("san10_extras", 628060),
      "san11pk-win": ("san11_extras", 628070), "san12pk-win": ("san12_extras", 628080)}


def add_zh(dataset, rows, game_dir):
    import importlib
    module, appid = ZH[dataset]
    zh = importlib.import_module(module).zh_items(os.path.join(game_dir, "..", "steam", f"{appid}-tchinese", "depot"))
    for r in rows:
        r["nameZh"], r["descriptionZh"] = zh[r["id"]]
    return rows


def _person_names(dataset):
    """kaodata id -> names: the kaodata dataset's characters, and the koei-wiki persons export where there is one"""
    names = {}
    path = os.path.expanduser(f"~/works/kaodata/data-local/{dataset}/dataset.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for c in json.load(f)["characters"]:
                names.setdefault(c["id"], set()).add(c["name"])
    path = os.path.join(os.path.dirname(__file__), "..", "export", "koei-wiki", "persons", f"{dataset}.jsonl")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                p = json.loads(line)
                names.setdefault(p["id"], set()).update({p["name"], p.get("nameJa", p["name"])})
    return names


def check(dataset, rows):
    """problems: duplicate ids, missing names, holder ids that are not persons of the dataset"""
    problems = []
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        problems.append("duplicate ids")
    names = _person_names(dataset)
    for r in rows:
        if not r.get("name"):
            problems.append(f"{r['id']}: no name")
        for h in r.get("holders", []):
            if "person" in h and h["person"] not in names:
                problems.append(f"{r['id']} {r['name']}: holder {h['person']} is not a person of {dataset}")
    return problems


@click.command()
@click.argument("dataset", type=click.Choice(list(DATASETS)))
@click.option("--extract", "extract", required=True, help="games/<id>/extract")
@click.option("--game-dir", "game_dir", help="遊戲目錄（信長6、11、三國志VIII、12–14 讀劇本的持有者；三國志VII–12 由此找繁中版）")
@click.option("--out", "out", required=True, help="export/koei-wiki/items")
def items_export(dataset, extract, game_dir, out):
    """寶物（koei-items/1）寫到 OUT/<dataset>.jsonl"""
    fn = DATASETS[dataset]
    rows = fn(extract, game_dir) if dataset in NEEDS_GAME else fn(extract)
    if dataset in ZH:
        rows = add_zh(dataset, rows, game_dir)
    rows = [_clean({"dataset": dataset, **r}) for r in rows]
    problems = check(dataset, rows)
    for p in problems:
        click.echo(p)
    if problems:
        raise click.ClickException(f"{len(problems)} problems")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, f"{dataset}.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    held = sum(len(r.get("holders", [])) for r in rows)
    click.echo(f"{dataset}: {len(rows)} items, {held} holders")
