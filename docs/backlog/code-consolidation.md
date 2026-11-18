---
status: in-progress
created: 2026-11-18
branch: refactor/code-consolidation
---

# dekoei 程式碼整合

`dekoei/` 約 150 個模組、4.8 萬行：63 個 `wiki_*`、38 個 `*_extras`、`kaodata_export.py` 的 82 個 builder。這份文件列出要整合、要統一的地方，照下面的順序一項一項做。

## 使用者的決定（2026-11-18）

- 第二節的共用工具這次**破例一次換完**，不照 re-common §4「不回頭改已經能跑的工具」。換完之後新程式一律用共用模組
- 補測試：共用模組要有單元測試，整體用「改前改後的輸出逐檔比對」（`scripts/regress.py`）
- 舊的 `face`／`person` 指令**修好留著**，標成 legacy
- 根目錄的雜項程式搬到 `legacy/`；`SAN2_MSG16P.*`：PNG 刪掉（`GLYPH_TABLE/GLYPH_TABLE_SAN2_MSG16P(1150).png` 是新版），txt 改名放到 `GLYPH_TABLE/GLYPH_TABLE_SAN2_MSG16P(1150).txt`（2026-11-18 使用者同意）

## 驗證方式

`scripts/regress.py run <label>` 把本機跑得動的指令全部跑一次，輸出寫到 `scratch/regress/<label>/`，記下每個檔的 sha256（`dataset.json` 先去掉 `source.revision`）；`scripts/regress.py diff <a> <b>` 逐檔比對。每一項改完都和基準 `base` 比，結果應該完全相同。刻意改變輸出的項目（例如修 bug）另外記在該項。

本機跑不到的：三國志8–11、13、14 的遊戲檔已移到 NAS（見 `notes/steam.md`「三國志8–14 的封存」），NAS 沒掛上時這幾款只能靠單元測試，以及「換上去的共用函式和原本的函式逐 byte 相同」的論證。

## 清單

### 1. 已知的問題

- [x] `unpack_npk` 少一個參數：`koei_games.py:63`、`koei_games.py:85`、`liberty.py:121` 只傳兩個參數，簽名是 `unpack_npk(src, line, height)`（`utils.py:565`），一跑就 `TypeError`。都在舊的 `face` 指令裡
- [x] GT1G 貼圖 format 0x01 的色序：`nobu14_extras.py`、`nobu15_extras.py` 當 BGRA，`nobu16_extras.py` 當 RGBA。看信長16 歷代頭像（04–08 項 3360 張）確認是 BGRA，改掉；大航海IV `koukai4_extras` 同樣錯（687 張），一起改。NAS 掛上後（2026-11-18）看三國志14 `hex_terrain.png`：格內寫著地形字，BGRA 時砂是褐、川是淺藍、街是黃，RGBA 時砂變深藍、川變黃，所以也是 BGRA；三國志13 只有地點號圖 `regions.png` 是 0x01（編號圖，沒有「正確顏色」），一起改成 BGRA，公式改用 B、`regions.csv` 的 `r` 欄改名 `b`；太閤V 沒有 0x01 的貼圖。`gfx` 拿掉 `raw` 參數，0x01 一律 BGRA

### 2. 重複的小工具（抽成共用模組）

| 項目 | 複本 | 處理 |
|---|---|---|
| 寫 CSV | 33 | ✅ `common.write_csv`／`write_dict_csv`（DictWriter 的 4 份） |
| `_u16`／`_u32` | 20 | ✅ `common.u16`／`u32`；`wiki_nobu7._u16(data, k, field)`、`genpei_extras.u16`（0xFFFF 回 -1）意思不同，保留 |
| `_read(game_dir, name)`／`_read(path)` | 17 | ✅ `common.read_file(*parts)`；`nobu15_extras._read(path, entry)`、`wiki_nobu3`、`wiki_royal`、`wiki_san8` 的不同，保留 |
| NUL 結尾字串 | 15 個函式 | ✅ `common.cstr(b, encoding, errors, nfkc)`；有外字表的（san11、san12 `sjis`、`nobu5._cstr`、`wiki_san6._text`、`wiki_san14._text` 等）保留。inline 的 `.split(b"\0")[0].decode(...)` 不動 |
| 半形假名 | 8＋2 處 inline | ✅ `common.fold_kana(s, katakana)` |
| 交錯 planar 解碼 | 4 | ✅ `gfx.decode_planar`（從 `genpei.py` 搬過去）；`celt.celt_planar` 每列各自分組，寬度不是 8 的倍數時和 `decode_planar` 不同，保留 |
| GT1G 貼圖 | 15 | ✅ `gfx.gt1g_texture`／`gt1g_header`／`texture_image`，含大航海IV、太閤V 的 dim 0 尺寸（本機 79 檔 4785 張和原寫法一致）；三國志12 的 GT1G0500 版面不同，保留 |
| LINK 容器 | 6 | 不合併：表的起點（0x10／0x20／看 +8）、回傳（rect、偏移、圖）各不相同，合成一個要帶一堆參數 |
| B,R,G 色盤 | 7 | 不合併：每處的縮放（×17、`<<2|>>4`）、起點、回傳型別（list、bytes、tuple）、前面補幾色都不同，共通的只有順序 |
| u16 位移表訊息 | 4 | 未做（`biography.offset_table` 已有） |
| 同一款遊戲的人物欄位解兩三次 | | ✅ ジンギスカン：共用記錄走訪 `koei_games.genghis_slots`，名字解法不同（DOS 內碼、PC-88 切到臉欄位、`koei_stats` 切 15 byte）各自保留；信長7：`koei_games.nobu7_win_text`；英傑傳 PC-98：`koei_games.eiketsu_pc98_text`（原 `koei_stats._pc98_text`，缺字給〓） |
| 完全相同的成對函式 | | ✅ `_section` → `wiki_nobu12`、`_decode` → `wiki_nobu15`、`_strings` → `nobu12_extras`、`_save_cell` → `nobu15_extras`、`join_marks` → `san4_extras`、`flush` → `fold_kana`；`bio_names` 是各模組給 `biography.py` 的介面，底下讀法不同，保留 |

### 3. koei-wiki 匯出的組織

- [x] dataset → 模組的對照表有 8 份（persons、places ×3、biography ×2、items、stats），合成一份：`wiki_datasets.py`（persons、places、bios、stats；某一類由別的模組讀時寫成 `places=kouryuuki_extras`）。places 的單向相鄰改成各模組的 `PLACES_ONE_WAY`
- [x] `places_export.py` 的三國志 1–14、水滸傳讀取（約 1150 行）搬到各自的 `wiki_san<N>.py`（`places`、`world_check`）；`wiki_stats.py` 的 14 個 `stats_*` 搬成各模組的 `stats`，`biography.py` 的三國志IV、V、VI、13、14 搬成 `bios`／`bio_names`／`BIO_LANG`。只被一款用到的常數與 helper 跟著搬，多款共用的（`_save`、`_text`、`_gaiji`、`_pick`、`offset_table`…）留在原模組。`items_export.py` 不搬，見「負面結論」
- [x] `--out`：`biography`、`stats-export` 是檔案，其他 5 個是資料夾。兩者改成資料夾、寫 `<out>/<dataset>.jsonl`；`--out ../export/koei-wiki` 寫出的位置和原本相同，下游不用改
- [x] `dekoei/export/` 是誤寫的輸出（文件寫「在 `dekoei/` 下跑，`--out export/...`」）；文件的路徑改成 `../export/...`。裡面只有 `places/san3-pc98`，和 `export/` 的逐檔相同，已移到垃圾桶

### 4. `*_extras` 輸出資料夾的名稱

地圖 `map/`、`worldmap/`、`world/`、`maps/`；圖片 `eventcg/`、`pictures/`；訊息散在 `text/`、`tables/`、`events/`、根目錄；道具 `items/kahou.csv`、`items/items.csv`，三款在根目錄另有 `items.csv`。改名要連帶改 notes、`events_export`／`items_export` 的讀檔路徑、`scripts/archive.py` 與素材庫，等真的要動那些遊戲時再做。

### 5. `kaodata_export.py`

- [x] 每個 builder 重寫的讀檔迴圈（79）、sha1 inputs（78）、meta dict（82）抽成 helper：`read_inputs(game_dir, names)` 換掉 78 個讀檔迴圈，`source(files, names)` 換掉 76 個 `"source"` 區塊；其餘幾個有改路徑（`n.upper()`）或另算 inputs 的保留。meta 其他欄位每款都不同，不抽
- [ ] ~~照系列拆檔~~ 不拆（2026-11-18 使用者決定）；27 個 `wiki_*` 把它當常數庫 import，名字要留著能 import。驗證用 `checksums.json` 與下游 `pnpm verify`。理由：只是搬位置、不減少程式碼；67 個區段之間互相引用常數（信長3 用三國志II 的色盤等），拆開要處理 import 順序與循環；三國志8–11、13、14 的匯出在 NAS 上，跑不了回歸

### 6. 舊程式

- [x] 舊的 `face`／`person` 指令（33＋22）修好，標成 legacy；`nobu.py` 信長3–6 的空 `pass` 指令（信長3、4 的 face／person 補上，接到 kaodata 的讀法）
- [x] `dekoei.py` 註解掉的 `add_command`：`air2`、`genghis`、`genchoh` 沒有定義，`ishin2` 有定義但沒註冊
- [x] `gadgets.py`、`gen_font_table.py` 沒有呼叫者，搬到 `legacy/`
- [x] 根目錄的 `build_name_key.py`、`game_infos.py`、`get_colors.py`、`annotate.sh`、`watermark.sh` 搬到 `legacy/`

## 現況

第 1、2、3、6 節做完，第 5 節做了 helper，拆檔暫緩；第 4 節照計畫不動。全部在分支 `refactor/code-consolidation`，沒有 commit。

回歸（`scripts/regress.py`，基準 `base`，413 個案例）：

- `step1`（第 1、6 節後的完整一輪）：預期只有信長16 歷代頭像不同（BGRA 修正）。這一輪的 `items/*` 失敗是快照少連了 `export/`（`items-export` 從 `../export/koei-wiki/persons/` 讀人物），和程式無關，已修正腳本
- `b1`、`b3`、`b5`：第 2、3、5 節換完後的子集。`b3`（places、stats、biography、persons 共 148 個）和基準完全相同；`biography`、`stats` 的輸出檔名從 `bios.jsonl`／`stats.jsonl` 變成 `<dataset>.jsonl`（`--out` 改成資料夾），比對時要對應過去
- `step1` 結果：只有信長16 歷代頭像 04–08 項 3227 張不同（BGRA 修正）
- `step2`（第 2 節換完後的完整一輪）：只有信長16 歷代頭像 3227 張、大航海IV extras 685 張不同；後者全是 format 0x01 的圖（687 張中另外 2 張每點紅藍相等，對調不變），其餘 411 個案例和基準相同
- `step3`（第 3、5 節換完後的完整一輪）：和 `step2` 一樣，只有信長16 歷代頭像 3227 張、大航海IV 685 張（兩處 BGRA 修正）不同，其餘和基準相同（`biography`、`stats` 的檔名對應成 `<dataset>.jsonl` 後比對）
- `nasbase`／`nasnew`（NAS 掛上後，三國志8–14 的 49 個案例；基準用 HEAD 的 `dekoei/`＋平行 WebP，`--src`、`--old-out`）：只有三國志13 `regions.png`／`regions.csv`、三國志14 `hex_terrain.png` 不同（format 0x01 改 BGRA），其餘相同。途中抓到一個第 3 節的錯：`san10_extras.place_names` 還從 `places_export` 讀已搬到 `wiki_san10` 的 `SAN10_EXTRA_GAIJI`、`SAN10_PLACES`，已改；另外用 AST 掃過所有 `模組.名稱` 與 `from 模組 import 名稱`，沒有其他指向已搬走名稱的
- `b5`（第 5 節後的 kaodata 匯出子集）：和基準相同
- `webp`：`write_dataset` 的無損 WebP 改成多程序平行壓（2026-11-18 使用者同意），santsukuru-win 88 分鐘 → 11 分鐘、nobu13pk-win 17 → 4 分鐘，兩者和基準逐檔相同（也涵蓋第 5 節的 helper）

## 下一步

目前沒有。2026-11-18 已用 BGRA 重跑 `games/nobu16pk-win/extract/`、`games/koukai4pk-win/extract/`，並把素材庫三國志13 的 `worldmap/regions.png`／`regions.csv`、三國志14 的 `worldmap/hex_terrain.png` 換成新版（兩份 README 有記）

## 負面結論

- `items_export.py` 的遊戲讀取搬到各 `wiki_*`：每款只有 1–4 個名字，卻都依賴 `items_export` 的共用 helper（`_rows`、`_flat`、`_unsure`、`_skill`…）與 `PICTURES`、`ZH` 設定表，搬過去只會讓 25 個模組 import `items_export` 的私有函式，程式碼不會變少；`wiki_nobu14`、`wiki_nobu16` 也已經有意思不同的 `items`。等 items 的設定表要重寫時再考慮
- LINK 容器、B,R,G 色盤合併：各處的表起點、回傳型別、縮放都不同，合成一個要帶的參數比省下的程式碼還多
- `celt.celt_planar` 換成 `decode_planar`：celt 的寬度是「每列 byte 數 × 2」，不保證是 8 的倍數，celt 每列各自分組，兩者在這種寬度下結果不同
- 半形假名的共用函式叫 `kana` 時，`wiki_san9.persons` 裡有 `for i, (ja, kana) in ...`，改成 `kana(kana)` 會壞，所以叫 `fold_kana`

## 未收尾

- 全部未 commit（`legacy/` 的搬移已 `git add`，其他沒有）
- 待使用者決定：`nobu4-dos` 的色盤（舊 `nobu4 face` 與 kaodata 同一份，膚色偏綠，沒查證）
