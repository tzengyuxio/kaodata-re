# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概要

研究早期光榮（KOEI）遊戲的資料格式（頭像 顏CG、人物資料、字型），並提供 `dekoei` 工具把原版遊戲檔解出成圖片／資料。支援的遊戲與功能見 README 的 Game List。

- `dekoei/`：主要 Python CLI（click）。所有子命令從 `dekoei/dekoei.py` 進入
- `notes/`：格式研究筆記（繁中），改解碼邏輯前先讀對應筆記，例如源平合戰看 `notes/genpei.md`
- `kaocgeditor/`：獨立的 React（Create React App）頭像編輯器，與 Python 端沒有程式碼共用
- `GLYPH_TABLE/`、`PERSONS_TABLE/`、`MISC_TABLE/`、`montage/`：已產出的成果圖／表，不是原始碼
- `games/`：原版遊戲（壓縮檔，以及解開後的 `games/<dataset-id>/`，如 `games/san2-dos/`），被 `.gitignore` 排除，不要 commit
- 舊的 unpacker 已移到另一個專案 `dekoei`，本 repo 不再處理

## 指令

Python 環境：沿用既有 `.venv`（Python 3.11；`requirements.txt` 鎖的 `bitarray==2.7.3` 在 3.12 編不起來，見 `BACKLOG.md`）。

`dekoei/` 內的模組用平面 import（`from utils import *`），**一律在 `dekoei/` 目錄下執行**：

```sh
cd dekoei
../.venv/bin/python dekoei.py --help
../.venv/bin/python dekoei.py <game> face -f <FILE> ...        # 例：san11 face -f San11Face00.fce --prefix SAN11_WIN_F
../.venv/bin/python dekoei.py export genpei-dos --game-dir <GENPEI 原版目錄> --out <kaodata>/data-local/genpei-dos
../.venv/bin/python dekoei.py export san2-dos --game-dir ../games/san2-dos --out ~/works/kaodata/data-local/san2-dos
```

測試（pytest）：必須用 `python -m pytest`，直接跑 `.venv/bin/pytest` 會因為 `dekoei/__init__.py` 讓 rootdir 跑到上層而 `ModuleNotFoundError: utils`：

```sh
cd dekoei
../.venv/bin/python -m pytest -q test_utils.py
../.venv/bin/python -m pytest -q test_utils.py::test_unpack_mask   # 單一測試
```

kaocgeditor（在 `kaocgeditor/` 下）：`npm start`、`npm test`、`npm run build`；有 ESLint／Prettier 設定。

Python 端沒有 linter／formatter 設定。

## 架構

- **CLI 組裝**：`dekoei.py` 定義根 group `dekoei`，底部一長串 `dekoei.add_command(...)` 掛上每款遊戲的 click group（一款遊戲一個 group，底下多半有 `face`、`person` 等子命令）。新增遊戲時寫好 group 後要在這裡註冊。
  - SAN10–14 的 group 與解碼直接寫在 `dekoei.py`；SAN1/2/3 在 `san1.py`／`san2.py`／`san3.py`；其他三國志在 `sango.py`；信長在 `nobu.py`；其餘遊戲大多集中在 `koei_games.py`；源平、獨立戰爭各有獨立模組。
- **共用解碼**：`utils.py`（bpp 轉色號、NPK/RLE 解壓 `unpack_npk_3bits` 等、Big5／光榮內碼字表）、`ls11.py`（LS11 壓縮）、`koei_person.py`／`san_person.py`（人物資料結構）、`font.py`（字型）。
  - 注意各遊戲的 planar 位元順序不一定相同：`utils.to_3bpp_indexes` 把第一個 byte 當 bit 2，源平合戰則是 byte k＝bit k（用 `genpei.decode_planar`）。
- **kaodata 統一格式匯出**（`kaodata_export.py`，目前開發中的 `feat/kaodata-export`）：
  - 產出給 kaodata 網站 repo 用的 `kaodata/1` 格式：`dataset.json`＋raw-deflate 的 pixel blobs（`pixels.bin`、`portraits.bin`）＋`checksums.json`。規格在**網站 repo** 的 `docs/data-format.md`，不在本 repo。
  - 檔內有一份依規格 §6 實作的 reference renderer（`compose_display`、`portrait_display` 等），`checksums.json` 由它算出；改資料結構時要同步讓 renderer 結果正確。
  - `DATASETS` dict 對應 dataset id → builder 函式：`genpei-dos` → `build_genpei`、`san2-dos` → `build_san2`。
    - `build_genpei` 只用 `genpei.py` 後段的新函式（`load_mainpal`、`montage_types`、`load_kaodata`、`unpack_main_exe` 等），組合表 offset 從展開後的 Main.exe 讀，不寫死。
    - `build_san2` 用 `san2.py` 的 `MONTAGE_AREAS`／`compose_montage`（表格讀自 MAIN.EXE，見 `notes/san2.md`）與 `load_san2_persons`。
  - `source.revision` 會呼叫 `git rev-parse HEAD`，所以必須在 git 工作目錄下執行。
- **舊 vs 新程式碼**：`genpei.py` 前段的舊命令（`genpei face`、`genpei montage`、舊色表 `genpei_face_colors`）已知有錯，見 `BACKLOG.md`；新匯出以 `load_mainpal` 等新函式為準，不要拿舊函式來用。
