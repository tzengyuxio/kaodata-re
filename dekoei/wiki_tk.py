"""提督の決断 (tk-pc98) for koei-wiki: persons (koei-persons/1). id is the kaodata tk-pc98 id, the index of the 19-byte
admiral record at RENMAIN.EXE DS:0xC6FC (also the RENPIC.DAT face). Only the Japanese release exists. The records
hold the name only: an admiral's abilities are presumably rolled when a game starts (「将校のデータを決定してください（スペースキーで
停止）」, RENMAIN.EXE DS:0x6B7F, file 0x4369F), so there are no stats to export. Field sources: notes/koei-games.md「提督の決断」
「koei-wiki 匯出」."""
import os

import koei_games as kg

DATASET = "tk-pc98"
JAPAN = 20  # 0-19 Japan, 20-39 the Allies
SIDES = ("日本軍", "連合国軍")  # the game's words (RENMAIN.EXE file 0x437DB「あなたの担当は 1)日本軍 2)連合国軍」)


def persons(game_dir):
    names = kg.load_tk_pc98_names(os.path.join(game_dir, "RENMAIN.EXE"))
    rows = []
    for i, name in enumerate(names):
        family, _, given = name.partition("　")  # only 宇垣　纒 and 吉川　潔 are spaced
        rows.append({"id": i, "name": family + given, **({"familyName": family} if given else {}),
                     "more": {"軍": SIDES[i >= JAPAN]},
                     "notes": "記錄只有名字；能力推定是開始遊戲時隨機決定（「将校のデータを決定してください」），沒有固定值。"
                              "軍是名單的前後半（0–19 日本、20–39 連合国軍），國籍沒有記錄。"})
    return rows
