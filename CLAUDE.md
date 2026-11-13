# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概要

研究早期光榮（KOEI）遊戲的資料格式（頭像 顏CG、人物資料、字型），並提供 `dekoei` 工具把原版遊戲檔解出成圖片／資料。支援的遊戲與功能見 README 的 Game List。

- `dekoei/`：主要 Python CLI（click）。所有子命令從 `dekoei/dekoei.py` 進入
- `notes/`：格式研究筆記（繁中），改解碼邏輯前先讀對應筆記，例如源平合戰看 `notes/genpei.md`
- `kaocgeditor/`：獨立的 React（Create React App）頭像編輯器，與 Python 端沒有程式碼共用
- `scripts/archive.py`：把一個資料集的成果複製進素材庫 `~/game-library/koei/<dataset>/`（re-common §11 入庫），用法與限制見 `docs/backlog/events-items-art.md`「未收尾」
- `research/face-crop/`：從三國志12／13 的大圖反推小頭像裁切框的研究腳本與結果（`san12pk-win` 的匯出會讀 `data/san12_boxes.json`）（要 numpy、scipy，用法見該目錄的 README）；`samples/` 不進版控
- `GLYPH_TABLE/`、`PERSONS_TABLE/`、`MISC_TABLE/`、`montage/`：已產出的成果圖／表，不是原始碼
- `games/`：原版遊戲，被 `.gitignore` 排除，不要 commit
  - 根目錄只放解開後、給 `--game-dir` 用的 `games/<dataset-id>/`（如 `games/san2-dos/`）
  - 源平合戦 DOS/V 版沒有發行包，安裝後的 `GENPEI/` 本身就是原始檔，放在 `~/game-library/_original/dos/genpei/`（記錄在 `_original/dos/genpei.txt`、`SHA1SUMS.txt`），`games/genpei-dos/` 是它的硬連結（唯讀）。2026-11-10 起源平合戦的格式研究以本 repo 為主，genpei-zh 只做中文化
  - DOS、Windows 的原始壓縮檔與用不到的附帶檔（說明文字、`<dataset-id>-src/`）放在 `games/archives/dos/`、`win/`
  - PC-98、PC-88、X68000 的發行包（磁碟映像、neo-kobe 合集、安裝結果 `pc98/installed/`）放在 `~/game-library/_original/pc98/`、`pc88/`、`x68/`（各有 `SHA1SUMS.txt`，2026-11-09 從 `games/archives/` 搬過去）；新加的這三個平台的原始檔也放那裡。檔案已解到 `games/<game>-pc98/`、`games/san2-x68/` 等，每片磁碟解開的原樣在 `games/archives/pc98/disks/`、`pc88/disks/`；PC-98 的 FD／HD 取捨見 `docs/backlog/pc98-disk-images.md`
- 舊的 unpacker 已移到另一個專案 `dekoei`，本 repo 不再處理；例外是 PC-98 安裝包 DPACK 的解壓 `dekoei/dpack.py`（`python dpack.py OUTDIR DPACK1 DPACK2 ...`，見 `notes/dpack.md`），用來從提督の決断III、三国志V 的磁片取得遊戲檔

## RE 共通語言

@~/.claude/re-common.md

本 repo 的路徑對照（`docs/` 的搬移、`captures/` 與探測腳本的固定位置還沒做）：

| 層／概念 | 本 repo |
|---|---|
| original | 發行包：PC-98／PC-88／X68000 在 `~/game-library/_original/<platform>/`，DOS／Windows 在 `games/archives/<platform>/`；取出的檔案 `games/<id>/`（Steam 版用硬連結） |
| references | `MISC_TABLE/`（能力值 CSV 等）；網址列在 `notes/san-persons.md`「參考來源」 |
| captures | 沒有固定位置 |
| extracted | `games/celt-win/extract/` 等，沒有統一位置 |
| generated | 根目錄 `GLYPH_TABLE/`、`PERSONS_TABLE/`、`montage/`（2023 年的舊成果）、`research/*/samples/` |
| export | `~/works/kaodata/data-local/<id>`（kaodata/1，下游 `pnpm verify`） |
| docs | `notes/<game>.md`（實際上是正式文件，預定搬到 `docs/`）、README.md、CLAUDE.md |
| tools | `dekoei/`（一個 Python 套件，builder 用旗標切換平台）、`research/<topic>/` |
| 不屬任何層 | `notes/` 裡的早期筆記（如 `san-persons.md`） |

## 指令

Python 環境：沿用既有 `.venv`（Python 3.11；`requirements.txt` 鎖的 `bitarray==2.7.3` 在 3.12 編不起來，見 `BACKLOG.md`）。

`dekoei/` 內的模組用平面 import（`from utils import *`），**一律在 `dekoei/` 目錄下執行**：

```sh
cd dekoei
../.venv/bin/python dekoei.py --help
../.venv/bin/python dekoei.py <game> face -f <FILE> ...        # 例：san11 face -f San11Face00.fce --prefix SAN11_WIN_F
../.venv/bin/python dekoei.py export <id> --game-dir ../games/<id> --out ~/works/kaodata/data-local/<id>   # 匯出一個 dataset
../.venv/bin/python dekoei.py celt art --game-dir ../games/celt-win --out ../games/celt-win/extract      # 魔眼邪神的全部美術素材
../.venv/bin/python dekoei.py celt music --game-dir ../games/celt-win --out ../games/celt-win/extract/music
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
- **人物能力（CSV）**：信長 2–13 是 `nobu.py` 的 `nobu-person`；ジンギスカン、英傑傳、大航海時代系列與水滸伝、源平、項劉記、ランペルール、維新の嵐（PC-98）是 `koei_stats.py` 的 `koei-person`（`dekoei.py koei-person <dataset id> --game-dir …`）。各代有哪些屬性見 `notes/*-attributes.md`，欄位證據在各遊戲筆記的「能力」段。
- **戰場地圖**：三國志 I–V 各有 `battlemap` 子命令（`san1`／`san2`／`san3` 在各自模組，IV、V 在 `sango.py`），讀 PC-98 版輸出 PNG 到 `games/<id>/extract/battlemap/`；英傑傳（`eiketsu`，PC-98）、孔明傳（`koumei`）、曹操傳（`eiketsu5`）、水滸伝（`suikoden`，PC-98，四季各一套，另出 49 州的 `provinces.csv`）也有，在 `koei_games.py`（英傑傳另有交戰背景 `battlebg`，曹操傳另有劇情場景與人物動作圖 `scene`）；`san2 battlemap` 另外把 41 張拼成全中國戰場 `china.png`；格式與未確認的部分見各遊戲筆記的「戰場地圖」段，FC／SFC 版在別的 repo，對照表見 `notes/koei-platforms.md`「主機版（其他 repo）」。
- **武將列傳**（`biography.py`）：`dekoei.py biography <dataset> --game-dir … --out export/koei-wiki/<dataset>.jsonl` 匯出列傳給 koei-wiki（三國志用繁中版，VII–12 讀 Steam 的繁中版 depot；信長 5–8 代照主資料集，`lang` 是 `ja` 或 `zh-Hant`），一段一行（`{"dataset","id","name","lang","kind","text"}`，`kind` 是 簡介／演義／史實／單段，`id` 同 kaodata 資料集）。`export/` 不進版控。各代的編碼與人數見 `notes/san-biographies.md`，格式細節見各遊戲筆記的「列傳」段。
- **武將能力值（koei-wiki）**（`wiki_stats.py`）：`dekoei.py stats-export <dataset> --game-dir … --out export/koei-wiki/stats/<dataset>.jsonl` 匯出三國志 I–14 的主能力，一人一行，`id` 同 kaodata 資料集；各代的取值來源見 `notes/san-attributes.md`「koei-wiki 匯出」。
- **地點（koei-wiki）**（`places_export.py`）：`dekoei.py places-export <dataset> --game-dir … --out export/koei-wiki/places` 匯出三國志各代、水滸傳（`suikoden-dos`）、項劉記（`kouryuuki-dos`，讀取在 `kouryuuki_extras.places`）與蒼き狼と白き牝鹿系列（`genghis-pc98`、`genchou-pc98`、`genghis4pk-win`，讀取在各自 `*_extras.places`）的地點、相鄰關係與戰場圖（koei-places/1，規格在 koei-wiki `docs/places-format.mkdn`），寫 `<dataset>.jsonl` 和 `<dataset>/` 的 PNG，並檢查引用與相鄰是否一致；各代的來源見 `notes/san-maps.md`「koei-wiki 匯出」，水滸傳見 `notes/koei-games.md`「州與戰場地圖」。`dekoei.py places-label <dataset> --places export/koei-wiki/places` 在匯出的大地圖上標「編號 名稱」，寫 `world/<圖名>-labelled.png`（目前是 `san4pk-pc98` 與 `kouryuuki-dos` 的春季圖，放法見 `notes/san-maps.md`）。
- **人物（koei-wiki）**（`persons_export.py`）：`dekoei.py persons-export <dataset> --game-dir … --out export/koei-wiki/persons --places export/koei-wiki/places` 匯出人物的全部欄位（koei-persons/1，規格在 koei-wiki `docs/persons-format.mkdn`），檢查 id、關係、所屬大名與所在地點的引用。目前是信長 2–13 代、創造（`nobu14pk-win`，Steam 繁中版，`wiki_nobu14.py`，見 `notes/nobu14.md`）、大志（`nobu15pk-win`，`wiki_nobu15.py`，`--game-dir` 是 `games/steam/628890`，見 `notes/nobu15.md`「koei-wiki 匯出」）與新生（`nobu16pk-win`，`wiki_nobu16.py`，`--game-dir` 是 `games/steam/1336980`，地點只有 247 城，見 `notes/nobu16.md`「koei-wiki 匯出」）（三款的地點、列伝、家宝也有）、蒼き狼と白き牝鹿系列（`genghis-pc98`、`genchou-pc98`、`genghis4pk-win`，`wiki_genghis*.py`、`wiki_genchou.py`；成吉思汗IV 的列傳也接上 `biography.py`）、三國志英傑傳（`eiketsu-dos`、`eiketsu-pc98`，`wiki_eiketsu.py`，見 `notes/eiketsu.md`「koei-wiki 匯出」）、孔明傳（`koumei-win`，`wiki_koumei.py`）與曹操傳（`eiketsu5-win`，`wiki_eiketsu5.py`）（見 `notes/eiketsu-attributes.md`「koei-wiki 匯出」）與三國志VIII–14（`wiki_san<N>.py`，名字用 Steam 繁中版，各劇本的所屬、所在、身分；劇本一覽另寫 `games/<id>/extract/tables/scenarios.csv`，寶物匯出的劇本號照它；三國志14 的劇本號是檔號，27 個）（地點另有 DOS 英文版 `nobu2-dos` 的戰場圖，圖塊從 `captures/screenshots/nobu2-dos/` 的截圖切，`wiki_nobu2_dos.py`），各代的讀取寫在 `wiki_nobu<N>.py`（`persons`、`places`、`bios`；5 代的主資料集 `nobu5pk-pc98` 是 `wiki_nobu5_pc98.py`），`persons_export.py`、`places_export.py`、`biography.py` 用模組名延遲載入；各欄位的來源見 `notes/nobu<N>.md`「koei-wiki 匯出」。
- **寶物（koei-wiki）**（`items_export.py`）：`dekoei.py items-export <dataset> --extract ../games/<id>/extract --game-dir ../games/<id> --out export/koei-wiki/items` 寫 `<dataset>.jsonl`（koei-items/1，規格在 koei-wiki `docs/items-format.mkdn`），讀各遊戲 `*-extras` 的 `extract/items/*.csv`，持有者換成 kaodata 人物 id 並檢查。目前 19 個資料集（三國志IV、VII–14，信長6–12、14–16），含效果 `effects` 與圖 `picture`（圖寫到 `<out>/<dataset>/`）；各資料集的來源與限制、三國志VIII–14 遊戲檔移走後怎麼重跑，見 `notes/koei-items.md`。
- **遊戲內事件（koei-wiki）**（`events_export.py`）：`dekoei.py events-export <dataset> --extract ../games/<id>/extract --out export/koei-wiki/events` 寫 `<dataset>.jsonl`（一張圖一行：`dataset`、`file`、`name`、`nameZh`、`confidence`、`notes`）和 `<dataset>/` 的 PNG，圖從各遊戲 `*-extras` 的 `extract/eventcg/` 取。第一輪只有天災與豐凶（信長4、信長6 PK、三國志IV PK、元朝秘史），規格在 koei-wiki `docs/events-format.mkdn`；各遊戲的事件、插圖、道具見 `docs/backlog/events-items-art.md`。
- **后妃大圖（koei-wiki）**（`ordo_export.py`）：`dekoei.py ordo-export genchou-pc98 --extract ../games/genchou-pc98/extract --out export/koei-wiki/ordo` 寫元朝秘史オルド（後宮）的 31 張圖與 jsonl，規格在 koei-wiki `docs/persons-format.mkdn`「后妃大圖（元朝秘史）」；圖由 `genchou-extras` 解出，見 `notes/genchou.md`「事件、插圖、道具」。
- **事件、插圖、道具**（`<game>_extras.py`，`dekoei.py <game>-extras --game-dir … --out ../games/<id>/extract`）：頭像與人物以外的素材，事件圖（`eventcg/`）、事件文字（`events/`）、道具（`items/`）、家紋（`kamon/`）等，目前 33 款（創造另有頭像與歷代頭像；大航海 I–IV、外傳另有港口、交易品、船與世界地圖；ジンギスカン、元朝秘史、成吉思汗IV 以國、相鄰、大地圖與人物的全部欄位為主，成吉思汗IV 另有列傳 533 人，還沒接 `biography.py`）；各款的內容與重跑指令見各遊戲筆記的「事件、插圖、道具」節，總表在 `docs/backlog/events-items-art.md`。
- **大頭像入庫**（`big_faces.py`，`dekoei.py` 沒掛，直接 `../.venv/bin/python big_faces.py <dataset> --game-dir ../games/<id>`）：三國志VIII–14 每張 kaodata 頭像的 BASE（涵蓋範圍最大，同 kaodata 的 `arts`，但無損）與最大尺寸（13、14 的 1024×1024），寫到 `games/<id>/extract/faces/{base,large}/NNNN.png`（NNNN＝kaodata 頭像序號，同 `scripts/archive.py` 的 `faces.csv`）與 `faces/index.csv`，給 `scripts/archive.py` 打包入庫。
- 魔眼邪神（`celt.py`）的 `celt` group 不匯出 kaodata，而是把圖、地圖拼塊、MIDI 全部拆到 `games/celt-win/extract/`，見 `notes/celt.md`。
- **共用解碼**：`utils.py`（bpp 轉色號、NPK/RLE 解壓 `unpack_npk_3bits` 等、Big5／光榮內碼字表）、`ls11.py`（LS11 壓縮）、`koei_person.py`／`san_person.py`（人物資料結構）、`font.py`（字型）。
  - 注意各遊戲的 planar 位元順序不一定相同：`utils.to_3bpp_indexes` 把第一個 byte 當 bit 2，源平合戰則是 byte k＝bit k（用 `genpei.decode_planar`）。
- **kaodata 統一格式匯出**（`kaodata_export.py`）：
  - 產出給 kaodata 網站 repo 用的 `kaodata/1` 格式：`dataset.json`＋raw-deflate 的 pixel blobs（`pixels.bin`、`portraits.bin`）＋`checksums.json`。規格在**網站 repo** 的 `docs/data-format.md`，不在本 repo。
  - 檔內有一份依規格 §6 實作的 reference renderer（`compose_display`、`portrait_display` 等），`checksums.json` 由它算出；改資料結構時要同步讓 renderer 結果正確。頂層 `"opaque": true` 的資料集沒有透明色，色號 255 照色盤顯示（`to_rgba`）；有 `portraitPalettes` 的資料集，頭像用自己那組色盤算雜湊（`portrait_palette`）；列在 `rgbaBlobs` 的 blob 是全彩 RGBA（`ImageStore.add(..., rgba=True)`），雜湊直接算原始 RGBA（`rgba_image`）。`WEBP_DATASETS`（`san11pk-win`、`nobu13pk-win`、`santsukuru-win`、`san12pk-win`、`san13pk-win`）在寫出時把全彩圖改成逐張無損 WebP（`faces/0000.webp`，images 項是 `{"file", "w", "h"}`，`"blobs": []`，不寫 `rgbaBlobs`，`write_dataset(..., webp=True)`／`webp_images`），alpha 照原樣（可以是半透明），alpha 0 的點存成 0,0,0,0，checksums 不變。
  - BASE（規格 §6.5，`arts`）：全彩的用 `art_webp` 放進 meta 的 `artFiles`，indexed 的用 `ImageStore.add_art`；兩種都由 `write_dataset` 寫到 `art/<SHA-256>`。哪 10 款有、各用哪張圖，見 `notes/kaodata-datasets.md`「BASE」。
  - `DATASETS` dict 對應 dataset id → builder 函式。同一款遊戲的各平台多半共用一個 builder，用旗標切換（`pc98=True`、`x68=True`、`pc88=True`、`dos=True`、`pk=True`）。每個 builder 讀哪些檔、用哪些解碼函式、有什麼例外，見 `notes/kaodata-datasets.md`；格式細節在各遊戲的 `notes/<game>.md`。
  - 新增或改動 dataset 時，同步更新 `notes/kaodata-datasets.md` 的對應條目。
  - PK 資料集（本體完全包含在內、只保留 PK 版的）在 PK 才有的頭像與人物加 `"pk": true`，`group` 照原本的類別名稱、不自己加「PK」：`san4pk-*` 是 340 之後的頭像與 NBDATA.SUI 的人物，`san5pk-*` 是 733 之後的頭像，`tk3pk-pc98` 是 KAODATA2 的頭像 197–204 與用到它們的劇本人物。`tk2pk-pc98` 只改了兩個提督名的寫法，沒有標記。
  - `nameHistorical`（史書寫法）的規則：遊戲寫法讓人認不出或搜不到史書（或《三國演義》）的寫法時才填，用該資料集的字形（日文版用新字體）。
    - 填：寫成別人的名字（樂進→于禁）、錯字（蔡冒→蔡瑁）、缺字代用（劉貴→劉璝）、少字（朶思王→朶思大王）。
    - 不填：同一字的不同字形（関／關、羣／群、彝／彞、万／萬、胄／冑、瞱／曄、毘／毗）、《三國演義》本身的寫法（喬瑁、范疆）、史書就有兩種寫法的（干吉／于吉、朱儁／朱雋、梁綱／梁剛）。
  - `source.revision` 會呼叫 `git rev-parse HEAD`，所以必須在 git 工作目錄下執行。
- **源平合戰**：`genpei.py` 的色盤一律用 `load_mainpal`（Mainpal.pld），像素一律用 `decode_planar`／`read_rle3`。`genpei_extras.py`（`dekoei.py genpei-extras --game-dir ../games/genpei-dos --out ../games/genpei-dos/extract`）輸出 4 個劇本的武將、勢力、國、地方、官位、家寶表，戰略地圖（四季大地圖、156 個節點），NPK016 的圖，Message.gp 訊息與 EXE 字串，格式見 `notes/genpei.md`（2026-11-10 從 genpei-zh 移植）。`genpei cg` 的 NPK 解碼和 `genpei_extras.npk_unpack`、genpei-zh 的 `dump_gfx.py` 相同（220 張，cross），仍沒和截圖比對；它對 Maincmd2 的特殊處理（3bpp 64 寬毛筆字）是錯的，見 `notes/genpei.md`。koei-wiki 的人物、據點（`persons-export`／`places-export genpei-pc98`）與每人兩張人物像（`wiki_genpei.py` 直接跑，128×160 半身像與 64×80 頭像窗）讀在 `wiki_genpei.py`，見 `notes/genpei.md`「koei-wiki 匯出」。
