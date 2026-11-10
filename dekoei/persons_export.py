"""Persons for koei-wiki in the koei-persons/1 format (koei-wiki docs/persons-format.mkdn): one JSONL line per person in
<out>/<dataset>.jsonl. id is the kaodata person id of the dataset. Each game's reader is a module wiki_<game>.py with
persons(game_dir) -> [row]; where the fields come from is in that game's notes/<game>.md「人物欄位」."""
import importlib
import json
import os

import click

# dataset -> module with persons(game_dir)
DATASETS = {"nobu2-pc88": "wiki_nobu2", "nobu3-pc98": "wiki_nobu3", "nobu4-pc98": "wiki_nobu4",
            "nobu5pk-win": "wiki_nobu5", "nobu5pk-pc98": "wiki_nobu5_pc98", "nobu6pk-pc98": "wiki_nobu6", "nobu7pk-win": "wiki_nobu7",
            "nobu8pk-win": "wiki_nobu8", "nobu9pk-win": "wiki_nobu9", "nobu10pk-win": "wiki_nobu10",
            "nobu11pk-win": "wiki_nobu11", "nobu12pk-win": "wiki_nobu12", "nobu13pk-win": "wiki_nobu13", "nobu14pk-win": "wiki_nobu14", "nobu15pk-win": "wiki_nobu15", "nobu16pk-win": "wiki_nobu16",
            "san8pk-win": "wiki_san8", "san9pk-win": "wiki_san9", "san10pk-win": "wiki_san10", "san11pk-win": "wiki_san11",
            "san12pk-win": "wiki_san12", "san13pk-win": "wiki_san13",
            "san14pk-win": "wiki_san14",
            "genghis-pc98": "wiki_genghis", "genchou-pc98": "wiki_genchou", "genghis4pk-win": "wiki_genghis4"}


def check(rows, places):
    """koei-persons/1 checks: unique ids, relations and scenario lords refer to persons of the dataset, scenario
    locations to places of the same game's places export (skipped when there is none). Returns (checked, [problems])."""
    ids = [r["id"] for r in rows]
    bad = [f"duplicate id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    ids, checked = set(ids), len(ids)
    for r in rows:
        for key, value in r.get("relations", {}).items():
            for x in [] if key == "clan" else value:
                checked += 1
                if x not in ids:
                    bad.append(f"{r['id']}: {key} {x} not a person")
        for s in r.get("scenarios", []):
            if "lord" in s:
                checked += 1
                if s["lord"] not in ids:
                    bad.append(f"{r['id']}: scenario {s['scenario']} lord {s['lord']} not a person")
            if "location" in s and places is not None:
                checked += 1
                if s["location"] not in places:
                    bad.append(f"{r['id']}: scenario {s['scenario']} location {s['location']} not a place")
    return checked, bad


@click.command()
@click.argument("dataset", type=click.Choice(list(DATASETS)))
@click.option("--game-dir", "game_dir", required=True)
@click.option("--out", "out", required=True, help="輸出目錄（寫 <dataset>.jsonl）")
@click.option("--places", "places_dir", default=None, help="地點匯出的目錄（檢查 scenarios[].location 用）")
def persons_export(dataset, game_dir, out, places_dir):
    """匯出人物的全部欄位（koei-persons/1，給 koei-wiki）

    dekoei.py persons-export nobu8pk-win --game-dir ../games/nobu8pk-win --out ../export/koei-wiki/persons --places ../export/koei-wiki/places
    """
    os.makedirs(out, exist_ok=True)
    rows = [{"dataset": dataset, **r} for r in importlib.import_module(DATASETS[dataset]).persons(game_dir)]
    with open(os.path.join(out, f"{dataset}.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    places = None
    path = places_dir and os.path.join(places_dir, f"{dataset}.jsonl")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            places = {json.loads(line)["id"] for line in f}
    checked, bad = check(rows, places)
    for b in bad:
        print(b)
    print(f"{dataset}: {len(rows)} persons; {checked} checked, {len(bad)} mismatched")
