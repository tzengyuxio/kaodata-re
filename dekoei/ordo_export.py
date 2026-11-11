"""元朝秘史 后妃大圖 for koei-wiki: export/koei-wiki/ordo/<dataset>.jsonl + <dataset>/<file>.png (spec: koei-wiki
docs/persons-format.mkdn「后妃大圖（元朝秘史）」). Read from genchou-extras' extract/ordo/; how the game picks the
pictures is in notes/genchou.md「事件、插圖、道具」.
One line per picture: {"dataset", "set", "culture" | "person", "stage" (from 1), "label", "file", "notes"}."""
import csv
import json
import os
import shutil

import click

LABELS = ["盛裝", "寬衣", "寢室"]  # 【推】 from the pictures; no name for them was found in the game
# sets 8-10: face code 0 / 1 / 7 -> person id (persons export genchou-pc98: 孛兒帖, 忽蘭, 拉奇)
PERSONS = {"0": 1000, "1": 1008, "7": 1012}
PICK = ("遊戲用 [DS:0xADFE] 選階段（<100、<150、其餘），組是女性的文化圏，頭像碼 0、1、7 例外用組 8、9、10"
        "（MAIN.EXE 0x20C21，位移表 DS:0xAD5A）")


@click.command(help="元朝秘史的后妃大圖（koei-wiki）")
@click.argument("dataset", type=click.Choice(["genchou-pc98"]))
@click.option("--extract", "extract_dir", required=True, help="games/genchou-pc98/extract")
@click.option("--out", "out_dir", required=True, help="export/koei-wiki/ordo")
def ordo_export(dataset, extract_dir, out_dir):
    src, pics = os.path.join(extract_dir, "ordo"), os.path.join(out_dir, dataset)
    os.makedirs(pics, exist_ok=True)
    for f in os.listdir(pics):
        os.remove(os.path.join(pics, f))
    with open(os.path.join(src, "ordo.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    with open(os.path.join(out_dir, f"{dataset}.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            shutil.copyfile(os.path.join(src, r["file"]), os.path.join(pics, r["file"]))
            s, stage = int(r["group"]), int(r["stage"])
            line = {"dataset": dataset, "set": s}
            if r["culture"]:
                line["culture"] = r["culture"]
            else:
                line["person"] = PERSONS[r["face"]]
            line.update({"stage": stage + 1, "label": LABELS[stage], "file": r["file"], "uncertain": ["label"]})
            notes = PICK
            if s == 10:
                notes += "；這組只有一張，階段 1、2 都用它，階段 3 不顯示她的圖"
            line["notes"] = notes
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    click.echo(f"{dataset}: {len(rows)} pictures")
