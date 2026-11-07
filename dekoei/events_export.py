"""In-game event pictures for koei-wiki (export/koei-wiki/events/<dataset>.jsonl + <dataset>/<file>.png).

First round (2026-11-07, agreed with koei-wiki): generic disasters and harvests only. The pictures are read from
the extracts the per-game commands write (nobu4-extras, nobu6-extras, san4-extras -> games/<id>/extract/eventcg/);
which picture is which event is recorded in each game's notes「事件、插圖、道具」.
One line per picture: {"dataset", "file", "name" (the game's own word), "nameZh", "confidence", "notes"}.
confidence "code": the program shows the picture with that event's message (or its order matches the messages);
"picture": the event was told from the picture and the game's messages."""
import json
import os
import shutil

import click

# dataset -> [(extract picture, export file, name, nameZh, confidence, notes)]
EVENTS = {
    "nobu4-pc98": [
        ("29-ikki.png", "ikki.png", "一揆", "一揆", "code", "MAIN.EXE 0x2C613「内政を怠った報いです」"),
        ("48-epidemic.png", "epidemic.png", "疫病", "疫病", "code", "MAIN.EXE 0x2C804「で疫病が発生したもようです」"),
        ("58-good-harvest.png", "good-harvest.png", "豊作", "豐收", "code",
         "MAIN.EXE 0x2CAFB「今年は各地で豊作の秋を迎えています」"),
        ("69-bad-harvest.png", "bad-harvest.png", "凶作", "歉收", "code",
         "MAIN.EXE 0x2CB24「今年は全国的な凶作に見舞われています」"),
        ("88-typhoon.png", "typhoon.png", "台風", "颱風", "code", "MAIN.EXE 0x2D629「%sの台風が近づいています」"),
        ("108-earthquake.png", "earthquake.png", "地震", "地震", "code",
         "MAIN.EXE 0x2D2AB「%s沖で%s地震が発生したもようです」"),
        ("118-heavy-snow.png", "heavy-snow.png", "大雪", "大雪", "code", "MAIN.EXE 0x2C95D「は大雪に見舞われています」"),
    ],
    "nobu6pk-pc98": [
        ("hanyou_35.png", "drought.png", "日照り", "乾旱", "code", "PACKGRP.NB6 #35；順序和 MESSAGE 第 5 段的災害訊息相同"),
        ("hanyou_36.png", "long-rain.png", "長雨", "久雨", "code", "PACKGRP.NB6 #36；同上"),
        ("hanyou_37.png", "epidemic.png", "疫病", "疫病", "code", "PACKGRP.NB6 #37；同上"),
        ("hanyou_38.png", "famine.png", "飢饉", "飢荒", "code", "PACKGRP.NB6 #38；同上"),
        ("hanyou_39.png", "heavy-snow.png", "大雪", "大雪", "code", "PACKGRP.NB6 #39；同上"),
        ("hanyou_40.png", "good-harvest.png", "豊作", "豐收", "code", "PACKGRP.NB6 #40；同上"),
        ("hanyou_41.png", "bad-harvest.png", "凶作", "歉收", "code", "PACKGRP.NB6 #41；同上"),
        ("hanyou_42.png", "ikki.png", "一揆", "一揆", "code", "PACKGRP.NB6 #42；同上"),
        ("hanyou_43.png", "ikko-ikki.png", "一向一揆", "一向一揆", "picture", "PACKGRP.NB6 #43；圖上有「南無阿弥陀仏」的旗"),
    ],
    "san4pk-pc98": [
        ("packgrp-50.png", "revolt.png", "反乱", "民變", "picture", "PACKGRP.S4 #50；MESSAGE.S4「ついに住民反乱が発生しました」"),
        ("packgrp-52.png", "locust.png", "蝗災", "蝗災", "picture",
         "PACKGRP.S4 #52；日文版訊息沒找到這個事件的寫法，name 取中文版 MESSAGE.S4「在…鬧蝗災了」「糧食被蝗蟲吃光了」"),
        ("packgrp-53.png", "epidemic.png", "疫病", "疫病", "picture", "PACKGRP.S4 #53；MESSAGE.S4「疫病のため人々は倒れ」"),
        ("packgrp-54.png", "good-harvest.png", "豊作", "豐收", "picture", "PACKGRP.S4 #54；MESSAGE.S4「毎年このように豊作だと」"),
        ("packgrp-56.png", "flood.png", "洪水", "洪水", "picture", "PACKGRP.S4 #56；MESSAGE.S4「長雨のせいで洪水が起こって」"),
        ("packgrp-57.png", "typhoon.png", "台風", "颱風", "picture",
         "PACKGRP.S4 #57（暴風雨的圖）；MESSAGE.S4「台風による被害が心配です」"),
    ],
}


@click.command(help="遊戲內事件的圖（koei-wiki）：天災與豐凶")
@click.argument("dataset", type=click.Choice(sorted(EVENTS)))
@click.option("--extract", "extract_dir", required=True, help="the game's extract dir (games/<id>/extract)")
@click.option("--out", "out_dir", required=True, help="export/koei-wiki/events")
def events_export(dataset, extract_dir, out_dir):
    pics = os.path.join(out_dir, dataset)
    os.makedirs(pics, exist_ok=True)
    with open(os.path.join(out_dir, f"{dataset}.jsonl"), "w", encoding="utf-8") as f:
        for src, file, name, name_zh, confidence, notes in EVENTS[dataset]:
            shutil.copyfile(os.path.join(extract_dir, "eventcg", src), os.path.join(pics, file))
            row = {"dataset": dataset, "file": file, "name": name, "nameZh": name_zh,
                   "confidence": confidence, "notes": notes}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{dataset}: {len(EVENTS[dataset])} pictures")
