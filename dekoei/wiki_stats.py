"""Main abilities of the 三國志 I-14 officers for koei-wiki, keyed by the kaodata person id: one JSONL line per
person, {"dataset", "id", "name", "stats": {ability: value}}. The abilities keep each game's own names (知力 / 智力,
カリスマ…); where they come from and what was checked is in notes/san-attributes.md「koei-wiki 匯出」. Every
stats_<dataset>(game_dir) rebuilds the builder's characters (kaodata_export.py) and returns [(id, name, stats)]."""
import json
import os

import click

from wiki_datasets import datasets, module


def _pick(rows, labels, ids_names):
    """rows: (id, name, *values); keep the characters in ids_names (id -> name)."""
    by_id = {r[0]: dict(zip(labels, r[2:])) for r in rows}
    return [(i, n, by_id[i]) for i, n in sorted(ids_names.items()) if i in by_id]


@click.command()
@click.argument("dataset", type=click.Choice(datasets("stats")))
@click.option("--game-dir", "game_dir", required=True)
@click.option("--out", "out", required=True, help="輸出目錄（寫 <dataset>.jsonl）")
def stats_export(dataset, game_dir, out):
    """匯出三國志 I–14 的武將能力值（JSONL，給 koei-wiki）"""
    os.makedirs(out, exist_ok=True)
    out = os.path.join(out, f"{dataset}.jsonl")
    rows = module(dataset, "stats").stats(game_dir)
    with open(out, "w", encoding="utf-8") as f:
        for i, name, stats in rows:
            f.write(json.dumps({"dataset": dataset, "id": i, "name": name, "stats": stats}, ensure_ascii=False) + "\n")
    print(f"{out}: {len(rows)} persons")
