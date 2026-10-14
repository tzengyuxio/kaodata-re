# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概要

研究早期光榮（KOEI）遊戲的資料格式（頭像 顏CG、人物資料、字型），並提供 `dekoei` 工具把原版遊戲檔解出成圖片／資料。支援的遊戲與功能見 README 的 Game List。

- `dekoei/`：主要 Python CLI（click）。所有子命令從 `dekoei/dekoei.py` 進入
- `notes/`：格式研究筆記（繁中），改解碼邏輯前先讀對應筆記，例如源平合戰看 `notes/genpei.md`
- `kaocgeditor/`：獨立的 React（Create React App）頭像編輯器，與 Python 端沒有程式碼共用
- `GLYPH_TABLE/`、`PERSONS_TABLE/`、`MISC_TABLE/`、`montage/`：已產出的成果圖／表，不是原始碼
- `games/`：原版遊戲（壓縮檔，以及解開後的 `games/<dataset-id>/`，如 `games/san2-dos/`），被 `.gitignore` 排除，不要 commit
  - PC-98／X68000 版是磁碟映像（`games/pc98/` 的 FDI／HDI、`games/Sangokushi II [FD]*/` 的 HDM），檔案已解到 `games/<game>-pc98/`、`games/san2-x68/`，每片磁碟的原樣在 `games/pc98/disks/`
- 舊的 unpacker 已移到另一個專案 `dekoei`，本 repo 不再處理

## 指令

Python 環境：沿用既有 `.venv`（Python 3.11；`requirements.txt` 鎖的 `bitarray==2.7.3` 在 3.12 編不起來，見 `BACKLOG.md`）。

`dekoei/` 內的模組用平面 import（`from utils import *`），**一律在 `dekoei/` 目錄下執行**：

```sh
cd dekoei
../.venv/bin/python dekoei.py --help
../.venv/bin/python dekoei.py <game> face -f <FILE> ...        # 例：san11 face -f San11Face00.fce --prefix SAN11_WIN_F
../.venv/bin/python dekoei.py export genpei-dos --game-dir <GENPEI 原版目錄> --out <kaodata>/data-local/genpei-dos
../.venv/bin/python dekoei.py export san1-pc98 --game-dir ../games/san1-pc98 --out ~/works/kaodata/data-local/san1-pc98
../.venv/bin/python dekoei.py export san1-dos --game-dir ../games/san1-dos --out ~/works/kaodata/data-local/san1-dos
../.venv/bin/python dekoei.py export san2-dos --game-dir ../games/san2-dos --out ~/works/kaodata/data-local/san2-dos
../.venv/bin/python dekoei.py export san2-pc98 --game-dir ../games/san2-pc98 --out ~/works/kaodata/data-local/san2-pc98
../.venv/bin/python dekoei.py export san2-x68 --game-dir ../games/san2-x68 --out ~/works/kaodata/data-local/san2-x68
../.venv/bin/python dekoei.py export san3-dos --game-dir ../games/san3-dos --out ~/works/kaodata/data-local/san3-dos
../.venv/bin/python dekoei.py export san3-pc98 --game-dir ../games/san3-pc98 --out ~/works/kaodata/data-local/san3-pc98
../.venv/bin/python dekoei.py export san4pk-dos --game-dir ../games/san4pk-dos --out ~/works/kaodata/data-local/san4pk-dos
../.venv/bin/python dekoei.py export san4pk-pc98 --game-dir ../games/san4pk-pc98 --out ~/works/kaodata/data-local/san4pk-pc98
../.venv/bin/python dekoei.py export san5pk-dos --game-dir ../games/san5pk-dos --out ~/works/kaodata/data-local/san5pk-dos
../.venv/bin/python dekoei.py export san5pk-pc98 --game-dir ../games/san5pk-pc98 --out ~/works/kaodata/data-local/san5pk-pc98
../.venv/bin/python dekoei.py export san6pk-win --game-dir ../games/san6pk-win --out ~/works/kaodata/data-local/san6pk-win
../.venv/bin/python dekoei.py export koumei-win --game-dir ../games/koumei-win --out ~/works/kaodata/data-local/koumei-win
../.venv/bin/python dekoei.py export eiketsu-dos --game-dir ../games/eiketsu-dos --out ~/works/kaodata/data-local/eiketsu-dos
../.venv/bin/python dekoei.py export eiketsu4-win --game-dir ../games/eiketsu4-win --out ~/works/kaodata/data-local/eiketsu4-win
../.venv/bin/python dekoei.py export eiketsu5-win --game-dir ../games/eiketsu5-win --out ~/works/kaodata/data-local/eiketsu5-win
../.venv/bin/python dekoei.py export suikoden-pc98 --game-dir ../games/suikoden-pc98 --out ~/works/kaodata/data-local/suikoden-pc98
../.venv/bin/python dekoei.py export lempe-dos --game-dir ../games/lempe-dos --out ~/works/kaodata/data-local/lempe-dos
../.venv/bin/python dekoei.py export suikoden-dos --game-dir ../games/suikoden-dos --out ~/works/kaodata/data-local/suikoden-dos
../.venv/bin/python dekoei.py export kouryuuki-dos --game-dir ../games/kouryuuki-dos --out ~/works/kaodata/data-local/kouryuuki-dos
../.venv/bin/python dekoei.py export europe-dos --game-dir ../games/europe-dos --out ~/works/kaodata/data-local/europe-dos
../.venv/bin/python dekoei.py export liberty-dos --game-dir ../games/liberty-dos --out ~/works/kaodata/data-local/liberty-dos
../.venv/bin/python dekoei.py export koukai-dos --game-dir ../games/koukai-dos --out ~/works/kaodata/data-local/koukai-dos
../.venv/bin/python dekoei.py export genghis-dos --game-dir ../games/genghis-dos --out ~/works/kaodata/data-local/genghis-dos
../.venv/bin/python dekoei.py export genghis4pk-win --game-dir ../games/genghis4pk-win --out ~/works/kaodata/data-local/genghis4pk-win
../.venv/bin/python dekoei.py export nobu3-dos --game-dir ../games/nobu3-dos --out ~/works/kaodata/data-local/nobu3-dos
../.venv/bin/python dekoei.py export nobu4-dos --game-dir ../games/nobu4-dos --out ~/works/kaodata/data-local/nobu4-dos
../.venv/bin/python dekoei.py export air2-dos --game-dir ../games/air2-dos --out ~/works/kaodata/data-local/air2-dos
../.venv/bin/python dekoei.py export koukaigd-win --game-dir ../games/koukaigd-win --out ~/works/kaodata/data-local/koukaigd-win
../.venv/bin/python dekoei.py export koukai3-win --game-dir ../games/koukai3-win --out ~/works/kaodata/data-local/koukai3-win
../.venv/bin/python dekoei.py export nobu7-win --game-dir ../games/nobu7-win --out ~/works/kaodata/data-local/nobu7-win
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
  - `DATASETS` dict 對應 dataset id → builder 函式：`genpei-dos` → `build_genpei`、`san2-dos` → `build_san2`、`san2-pc98`／`san2-x68` → `build_san2_jp`、`san3-dos`／`san3-pc98` → `build_san3`、`san4pk-dos`／`san4pk-pc98` → `build_san4`、`san5pk-dos`／`san5pk-pc98` → `build_san5pk`、`san6pk-win` → `build_san6pk_win`、`koumei-win` → `build_koumei_win`、`eiketsu-dos` → `build_eiketsu_dos`、`lempe-dos` → `build_lempe`、`san1-pc98`／`san1-dos` → `build_san1`、`suikoden-pc98` → `build_suikoden_pc98`；DOS 中文版 `suikoden-dos`、`kouryuuki-dos`、`europe-dos`、`liberty-dos`、`koukai-dos`、`genghis-dos`、`nobu3-dos`、`nobu4-dos`、`air2-dos` → `build_<game>_dos`；`koukaigd-win` → `build_koukaigd_win`；`koukai3-win` → `build_koukai3_win`；`nobu7-win` → `build_nobu7_win`；`eiketsu4-win` → `build_eiketsu4_win`；`eiketsu5-win` → `build_eiketsu5_win`；`genghis4pk-win` → `build_genghis4pk_win`。
    - `build_genpei` 只用 `genpei.py` 後段的新函式（`load_mainpal`、`montage_types`、`load_kaodata`、`unpack_main_exe` 等），組合表 offset 從展開後的 Main.exe 讀，不寫死。
    - `build_san2` 用 `san2.py` 的 `MONTAGE_AREAS`／`compose_montage`（表格讀自 MAIN.EXE，見 `notes/san2.md`）與 `load_san2_persons`。`san2-pc98`／`san2-x68` 用 `build_san2_jp`：全高頭像在 KAODATA1–3，組合臉零件在 KAODATA3 後段（`san2.JP_MONTAGE_*`，鼻口順序和 DOS 相反），人物用 `load_san2_jp_persons`。
    - `build_san3` 用 `san3.py` 的 `MONTAGE_AREAS` 等（表格讀自 MAIN.EXE，見 `notes/san3.md`）與 `load_san3_persons`；像素是 byte k＝bit k（`genpei.decode_planar`），不是 `to_3bpp_indexes`。`san3-pc98` 也用 `build_san3`（`pc98=True`）：頭像檔相同，人物改用 `load_san3_pc98_persons`（Shift-JIS＋外字），色盤與事件人物名換成日文版的。
    - `build_san4` 用 `sango.py` 的 `load_san4_faces`（KAODATA.S4 是自訂的 RLE＋nibble 壓縮）、`SAN4_MONTAGE_*`（眼、口的列號依頭型不同）與 `load_san4_persons`（SNDATA／TAIKI 是 LS11），見 `notes/san4.md`。MONDATA 像素是 byte k＝bit k。`san4pk-pc98` 用 `build_san4`（`pc98=True, pk=True`），人物姓名是 Shift-JIS＋外字，並多收 KAODATAP 的水滸伝武將頭像、KAODATA2 的挑臉追加頭像與 NBDATA.SUI 的 117 人；`san4pk-dos` 是 `pk=True` 不加 `pc98`，頭像檔和 PC-98 PK 相同，姓名是光榮台灣內碼。
    - `build_san5pk` 只有逐人頭像（KAODATA.S5 未壓縮，byte k＝bit k，後面接 KAOEX.S5 的追加頭像），`san5pk-pc98` 用同一個 builder（`pc98=True`），人物用 `sango.load_san5_persons`；DOS 版的 MAIN.EXE 是破解過的，只當程式碼參考，見 `notes/san5.md`。
    - `build_san6pk_win` 只有逐人頭像（KAODATA.S6 是 96×120 8 bit 未壓縮，色盤是 PALETTE.S6 的 Windows LOGPALETTE），人物用 `sango.load_san6_persons`（SNDATA01–23，Big5），見 `notes/san6.md`。`build_koumei_win` 也只有逐人頭像（KAO.E2 是 LS11，64×80 8 bit；PALET.E2 是 B、R、G），人物從 BAKDATA.E2 的登場記錄整理，兵種／NPC 另分組，見 `notes/koumei.md`。`build_eiketsu_dos`（英傑傳 DOS 中文版）的 FACEDAT.R3 是 TFDED.COM（int 62h）的 TF-DCE 壓縮，用 `koei_games.decode_tfdce` 解開，人物用 `koei_games.load_eiketsu_dos_persons`（BAKDATA.R3），見 `notes/eiketsu.md`。
    - `build_san1`：PICDATA 半高頭像（PC-98 3bpp、DOS 2bpp，臉的順序相同），組合臉是三段橫條（`san1.PC98_BANDS`），PC-98 人物從 SAVEDATA 的存檔槽 0 讀（劇本檔有編碼），DOS 從 SINADATA 讀；DOS 的 `nameZh` 是寫死的表，見 `notes/san1.md`。`build_suikoden_pc98` 只有逐人頭像，見 `notes/koei-games.md`。
    - DOS 中文版（`build_suikoden_dos` 等）：人物讀取放在 `koei_games.py`（`liberty-dos` 在 `liberty.py`），姓名是光榮台灣內碼（`koei_games.koei_tw_name`）。項劉記的 MAIN.EXE 是 PKLITE，用 `pklite.depklite` 解開；`koukai-dos`、`genghis-dos`、`nobu3-dos`、`nobu4-dos` 有組合臉；後三者的眼鼻口用 slot 的 `blend: "xor"`（reference renderer 的 `blit(..., blend="xor")`）。格式見 `notes/koei-games.md`（水滸傳）、`notes/kouryuuki.md`、`notes/europe.md`、`notes/liberty.md`、`notes/koukai.md`、`notes/genghis.md`、`notes/nobu3.md`、`notes/nobu4.md`。`air2-dos` 只有頭像（9 個 GDT 檔，沒有人物和頭像碼），見 `notes/air2.md`。
    - `build_koukaigd_win`（大航海時代外傳 Win 中文版）：頭像在 Kao.lzw（LS11），組合臉零件在 Monkao.dat 的 LS11 之後（7 種類型），眼鼻口用 `blend: "or"`；類型不在頭像碼裡，所以每人 `face` 是類型 1、`expressions` 是類型 2–7。航海士表在 koukaiGD.exe（`koei_games.load_koukaigd_win_mates`），見 `notes/koukaigd.md`。
    - `build_koukai3_win`（大航海時代III Win 中文版）只有逐人頭像：MALE.CDS／FEMALE.CDS（LS11，80×96 8 bit），色盤和人物表（含性別）都在未壓縮的 `CDS95.EXE.pec2bac`（`koei_games.load_koukai3_win_persons`），頭像碼是「性別 << 12 | 頭像」，見 `notes/koukai3.md`。
    - `build_nobu7_win`（信長之野望 將星錄 Win 中文版）只有逐人頭像：Kaodata.nb7 是有索引表的 64×80 8 bit 未壓縮頭像，色盤是 Grppal.nb7（LS11）第 0 段的 B、R、G，人物用劇本 5 的 Sndata05.nb7（`koei_games.load_nobu7_win_persons`，長宗我部等外字姓氏查表），見 `notes/nobu7.md`。
    - `build_eiketsu4_win`（織田信長傳 Win 中文版）只有逐人頭像：KAO.E4 是 LS11（64×80 8 bit），色盤是 PMPALET.E4 第 0 段的 B、R、G，人物表在 DATA.E4 第 0 段（`koei_games.load_eiketsu4_win_persons`），同一人的別名與不同年齡的臉合併（`EIKETSU4_WIN_ALIASES`），見 `notes/eiketsu4.md`。
    - `build_eiketsu5_win`（三國志曹操傳 Win 中文版）格式同織田信長傳（FACE.E5、PMPALET.E5 第 40 段、DATA.E5 第 0 段，`koei_games.load_eiketsu5_win_persons`），但段號是「頭像碼＋7」，曹操、夏侯惇等幾人依劇情旗標換臉（`EIKETSU5_WIN_LOOKS`，EKD5.EXE 0x407597），見 `notes/eiketsu5.md`。
    - `build_genghis4pk_win`（成吉思汗IV 威力加強版 Win 中文版）只有逐人頭像：MENPUK.BMP／WOMENPUK.bmp 是 64×80 格的 8 bit BMP（系統色 0–9、246–255 換成 Windows 預設值，255 移到 254），人物從 SCEDAT1–4.CK 的男女記錄讀（`koei_games.load_genghis4_win_persons`），見 `notes/genghis4.md`。
    - `build_lempe` 只有逐人頭像（像素格式同三國志II），人物用 `koei_games.load_lempe_persons`，見 `notes/lempe.md`。
  - `nameHistorical`（史書寫法）的規則：遊戲寫法讓人認不出或搜不到史書（或《三國演義》）的寫法時才填，用該資料集的字形（日文版用新字體）。
    - 填：寫成別人的名字（樂進→于禁）、錯字（蔡冒→蔡瑁）、缺字代用（劉貴→劉璝）、少字（朶思王→朶思大王）。
    - 不填：同一字的不同字形（関／關、羣／群、彝／彞、万／萬、胄／冑、瞱／曄、毘／毗）、《三國演義》本身的寫法（喬瑁、范疆）、史書就有兩種寫法的（干吉／于吉、朱儁／朱雋、梁綱／梁剛）。
  - `source.revision` 會呼叫 `git rev-parse HEAD`，所以必須在 git 工作目錄下執行。
- **舊 vs 新程式碼**：`genpei.py` 前段的舊命令（`genpei face`、`genpei montage`、舊色表 `genpei_face_colors`）已知有錯，見 `BACKLOG.md`；新匯出以 `load_mainpal` 等新函式為準，不要拿舊函式來用。
