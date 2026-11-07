---
status: in-progress
created: 2026-11-07
---

# 事件、事件插圖、道具（三國志 I–V、12–14；信長 2–6、12–13）

## 結論

- 範圍（使用者 2026-11-07 定）：三國志 I–V 與信長 2–6，加上三國志 12–14、信長 12–14，各代要解的是事件（文字與觸發）、事件插圖、道具（名稱、效果、圖）。
- 目的之一是封存（`~/.claude/re-common.md` §11）：素材和資料先解好，就可以把遊戲封存、清出空間。新作佔的空間大（三國志12 11 GB、13 14 GB、14 20 GB），格式也比較單純；早期作品省下的空間有限，但規則已經比較熟。
- 影音不留（使用者 2026-11-07）：三國志 6 以後、信長以 Windows 為主要平台以後的作品，過場影片、BGM、語音都不轉檔也不留，封存時直接捨棄（那時的檔案大、多是通用格式）。早期作品自家的音源與色盤動畫才照 re-common §10 處理。
- 信長初代本地沒有遊戲檔；信長14（創造）帳號沒有，都不在範圍內。
- 事件文字要交給 koei-wiki 的話，格式要先和 koei-wiki 談（目前沒有規格）。

## 現況（2026-11-07 盤點）

`dekoei` 讀過的美術檔只有頭像、組合臉、戰場圖；事件文字只解了列傳。下表多半是看檔名和既有筆記推的【推】，檔案本身大多還沒打開。

### 早期作品

| 遊戲（主資料集） | 事件插圖候選 | 事件文字 | 道具 |
|---|---|---|---|
| 三國志 `san1-pc98` | `PICDATA.DAT` 第 113 張之後（筆記寫是事件插圖，和頭像同格式） | `STRING.DAT`（8 KB） | 沒有道具 |
| 三國志II `san2-pc98` | `OPENNING.DAT`、`ENDING.DAT`、`PACKDATA.DAT` | `MAIN.EXE` 裡 | 沒有道具【推】 |
| 三國志III `san3-pc98` | `NPKDATA.DAT`、`ENDSTIL.DAT`、`HEXIKKI.DAT`（一騎討？）、`OPENGRP.DAT` | `MAIN.EXE` 裡；事件人物、貂蟬連環計的條件已追到一部分（`notes/san3.md`） | 人物 +8 bitmask 🟡；名表沒找 |
| 三國志IV `san4pk-pc98` | `PACKGRP*.S4`、`NEWGRP`、`REVGRP`、`PREGRP`、`HIBACK`、`MAINCG`、`TOSHICG`、`ENDDAT`、`OPENDAT`（部分是 NPK016，`notes/npk016.md`） | `MESSAGE.S4` 其他段（列傳只用 24–33 段） | 有（能力有道具加成），表沒找 |
| 三國志V `san5pk-pc98` | `CANMA/B/D.S5`、`IKKI1/2.S5`、`IKKIHAI.S5`、`ESTL.S5`、`IMODE.S5`、`BUDOUKAI.S5`、`END1–4.S5`、`OPMONO*.S5` | `MESSAGE.S5` 其他段 | `ITEM.S5`（150 KB，推定是道具圖） |
| 信長2 `nobu2-pc88` | Disk B、`ODA.OVL` 沒查 | — | 沒有道具 |
| 信長3 `nobu3-pc98` | `OPEN.DAT`、`END1/2.DAT`、`PACKDATA.DAT` | `MAIN.EXE` 裡 | 沒有道具【推】 |
| 信長4 `nobu4-pc98` | `KAIGA.DAT`（絵画？）、`OUGICHAK.DAT`（扇／茶器？）、`DEMO.DAT`；事件人物的程式位址已記（`notes/nobu4.md`） | `MAIN.EXE` 裡 | 茶器名 48 個（`SNDATAn.CIM` 0x0890），其他欄位沒解 |
| 信長5 `nobu5-pc98`（Win PK 只有 `Kao.dll`＋EXE） | `ANIME.NB5`、`FUJIN.NB5`、`JISIN.NB5`、`PACK.NB5` | `STR1/2.NB5`（XOR 0xA5） | `ITEM.NB5`；人物 +35 bit 7 推定是持有家宝 🟡 |
| 信長6 `nobu6pk-pc98`（本體 `nobu6-pc98`） | `REKISHI1/2.NB6`（歷史事件？）、`OHIROME.NB6`、`GAMEN.NB6`、`OPEN*`、`END*`（部分是 NPK016） | `BFILE` 第 0 段（事件對話稿）、`MESSAGE.NB6` | 家宝 120 件、官位 250 個的名稱已知，其他欄位沒解 |

### 新作（Steam，`games/steam/<appid>/`）

| 遊戲（appid，大小） | 事件插圖 | 事件文字 | 道具 |
|---|---|---|---|
| 三國志12 PK（628080，11 GB） | `Data/EventStill/`（105 個 `ev_look_*.bin`）、`PK/Data/EventStill/`、`Data/EventEffect/`；`resfiles_*.bin` 沒查 | `Data`、`PK/Msg` 沒查 | `Data/ITEM_STL.S12`（45 MB，`LINK` 封裝）、`resfiles_additem20_pk.bin`、`resfiles_spitem0_pk.bin` |
| 三國志13 PK（363150，14 GB） | `DATA1.S13` 封裝內（封裝已解，`notes/san13.md`），哪幾項是事件圖沒分類 | 本體／PK 第 1275 項 `XL` 表（事件文字） | 封裝內，沒找 |
| 三國志14 PK（872410，20 GB） | `0002/*.rdb`（RDB 已解，`notes/san14.md`）；`ScreenLayout.rdb` 有 `sti_scenery_*` 25 張 | `0010_JP`、`0010_TC` 之外沒查 | `ScreenLayout.rdb` 的 `sti_item*` 219 張（512×512，已能解出）；名稱、效果沒找 |
| 信長12 革新 PK（363090，1.8 GB） | `Grp/rekishicg.n12`（歷史事件）、`endingcg.n12`、`tokusanhincg.n12`（特産品） | `Msg/rek_*.n12`（歷史事件約 40 個）、`tok_tec_*`、`trl_*`、`end_*`、`rekev.n12`、`tokev.n12` | 家宝：`Grp/kahou.n12`（圖）、`Msg/Kfile01–08.n12`（說明）、人物串列 3（家宝 id）🟡 |
| 信長13 天道 PK（363110，4.6 GB） | `grp/rekishicg.n13`、`endingcg.n13`、`titlecg.n13` | `msg/rks_*.n13`（歷史事件約 75 個）、`cev_*`（勢力事件約 60 個）、`han_*`（約 40 個）、`event_root.n13`、`rekev.n13`、`tokev.n13` | 家宝：`grp/kahou.n13`、`msg/Kfile01–08.n13`、人物串列 4 |
| 信長14 創造 | 帳號沒有 | | |

## 產出進度（2026-11-07 起，一款一 fork）

產出都在 `games/<id>/extract/`（不進版控），格式與重跑方式寫在各遊戲筆記的「事件、插圖、道具」節。

| 遊戲 | 指令 | 產出 | 封存前還缺 |
|---|---|---|---|
| 三國志 `san1-pc98` | `san1 eventcg`、`san1 strings` | 事件插圖 27 張（在 `PACKDATA.DAT`，不是 PICDATA；戰鬥 6 張用途 ✅ code，其餘 🟡）；PICDATA 113 起的小動畫 14 組 86 格（投降、待命 ✅，其餘 🟡）；`STRING.DAT` 15 州說明；沒有道具 | 4 張插圖（block 0、40、60、70，部分 XOR 編碼）與 PICDATA 348、378 ❌；事件文字在編碼過的程式裡 ❌（DOS 英文版是明文，可替代） |
| 三國志14 `san14pk-win` | `san14-extras` | 寶物 131 件＋圖 219 ✅（加成對象 🟡）；事件文字 511 個 × 日／繁中 ✅（事件號 🟡）；事件插圖 913 張（事件 93、場景、背景、題詩、名勝、人物插圖 148 🟡、表情 540）；rdb inventory | 事件腳本 `0004/Event*.s14`；3D rdb 3.4 GB；寶物持有者 |
| 三國志IV `san4pk-pc98`（中文 `san4pk-dos`） | `san4-extras` | 道具 31 件＋圖（加成 ✅ cross＋capture，種類名 🟡）、10 劇本持有者 129 筆 ✅ cross；事件插圖 53 張（NPK016，名稱 🟡、主色盤 🟡）；訊息日 1710／中 1711 則、38 段 | `OPENDAT` 85、`ENDDAT` 79 張（色盤）；`PREGRP`（NPK16）；事件腳本與觸發；音樂（§10） |
| 三國志12 `san12pk-win` | `san12-extras` | 事件 CG 130 張 ✅（歷史 39、汎用 32、komo 9、背景 23、結局 3、表情特寫 24）；名品 205 件＋圖 200 ✅（能力、特技 ✅ cross，其他效果與種類名 🟡）、特典名品 CG 20、特技 20；有語音台詞 520 句／16 段 ✅、事件訊息 2453 則 🟡、年表事件名 38 🟡 | `BtlMap` 1.8 GB、`CityMap`、`UI`；事件腳本位置、劇本的名品持有者；koei-wiki 地點與戰場圖 |
| 三國志13 `san13pk-win` | `san13-extras` | 事件插圖 242 張 ✅（事件 70、結局 22、故事 15、小物 11、背景 51、教學 73）；寶物 234 件＋圖 256（種類 ✅，圖號與持有者 🟡）；訊息腳本 29859 段 ✅、事件名 50 🟡、事件表 999 筆（欄位 ❌）；容器 inventory 3380 項 | 事件表欄位；繁中 `msggame`；`tenkai*`、`event_sf`、`eiketsu_*`、`kako_kao_still` 6107 張 |
| 信長4 `nobu4-pc98` | `nobu4-extras` | 事件圖 21 張（名稱 ✅ code，2 張 ✅ capture，砲撃 2 張 🟡）；開場 29 張（大名介紹卡 15，✅ capture）；結局 22 張（色盤 🟡）；茶器 48 件 ✅ code＋圖 15（持有者 🟡）；屏風畫 4 幅（繪師 🟡）；扇 20 格；`MAIN.EXE` 字串 2246 筆 | 事件切分與觸發；`DEMO.DAT`、`OPEN.DAT` 0x1E1CF 之後；茶器 value、扇的季節、結局色盤 |
| 信長5 `nobu5pk-win`（Steam 628090；PC-98 對照） | `nobu5-extras` | 家宝 120 件 ✅ cross（類別 ✅，價值、flag 🟡；開局無人持有 ✅，人物 +35 bit 7＝家宝的推測不成立）＋圖 26 種；事件靜止圖 5 🟡、影片清單 12 🟡；家紋 106；四季大地圖 4＋割拠図（春夏 🟡）；EXE 字串 1923 則（事件表 0xB8C58 250 則） | 事件對應與觸發（`.text` 加密）；家紋↔大名；`Hexmap.dll` 戰場圖 206 張；PC-98 事件圖色盤 |
| 信長6 `nobu6pk-pc98`（本體 `nobu6-pc98`） | `nobu6-extras` | 家宝 120 件（種類、加成 ✅ code，6 劇本持有者、讀音說明 ✅ cross）＋圖 22；官位 250（位階 ✅ code，持有者 ✅ cross）；家紋 355＋各劇本大名 ✅ cross；事件插圖 62 張（圖 ✅，說明多 🟡）；訊息 2020 則；城說明 233 | 事件切分、觸發、插圖對應；`OPEN*`／`END*` 色盤（`.PLD`）；本體 `KAMON.NB6` 110 號以後 ❌；音樂（§10）；野戰圖 |
| 信長12 `nobu12pk-win` | `nobu12-extras` | 事件 CG 121 幅（rekishi ✅ cross，hanyou／ending 界線 🟡）；家宝 355 件（名稱說明圖 ✅，弓／大砲種類名 🟡，8 劇本持有者）；特產品 20 ✅；官位／役職圖示；家紋 228；事件腳本 137 檔 10256 框（文字 ✅，觸發 🟡） | 歷史事件標題找不到；`Media/graphres.bin`；家紋↔勢力、圖示名稱 |
| 信長13 `nobu13pk-win` | `nobu13-extras` | 家宝 353 件（圖 73 種 × 2）✅／等級持有者 🟡；事件插圖 251 張（歷史組 ✅ cross，其他 🟡）；家紋 237 個；事件腳本 191 檔（文字 ✅，觸發 ❌） | 事件觸發、家宝效果、家紋↔勢力；`media/` 3D（影音不留） |

## 下一步

建議順序（投入／收穫）：

1. 三國志 I 事件插圖：`PICDATA.DAT` 113 之後，格式已知。
2. 信長 12、13 的家宝與事件：檔案都分好名、文字格式（N12F／N13F）已經解過，事件插圖在單一檔案裡。做完可以先封存信長 12、13。
3. 三國志 12–14 的事件圖與道具圖：封裝都已經解得開，主要是分類和命名；做完可以封存，清出最多空間（共約 45 GB）。
4. 信長 4、5、6 的道具：名表或位置已知，補欄位和圖。
5. 三國志 IV、V 的美術檔：NPK016 的解碼器（源平、英傑傳）也許可以直接用。
6. 事件文字：從 EXE、`MESSAGE`、`STR` 切成一則一則，工作量最大，等 koei-wiki 訂格式。

koei-wiki 事件條目（2026-11-07 提案，koei-wiki 回了草案，**等它的使用者定格式，先不匯出**）：

- 第一輪只做天災與豐凶（洪水、飢饉、蝗害、台風、疫病、地震、大雪、豊作、凶作、一揆、一向一揆、日照り），歷史事件之後另一輪。
- 草案格式：`export/koei-wiki/events/<dataset>.jsonl`，一張圖一行 `{"dataset","file","name"（遊戲原文）,"nameZh"?,"confidence":"code|picture","notes"?}`；規則之後再加欄位。規格會寫在 koei-wiki `docs/events-format.mkdn`。
- 圖的網址 `img.simagame.me/kaodata/event/<dataset>/<file>.png`＋`index.json`，R2 上傳由 koei-wiki 做。

封存前要先跑完成品、具名素材打包（cbz）、`_original/` 登記（§11「封存的步驟」）。

## 負面結論

- 三國志 I：`PACKDATA.DAT` 不是編碼過的劇本，是事件插圖；`PICDATA.DAT` 113 起是小動畫格，不是插圖。
- 信長5：人物 +35 bit 7 不是「持有家宝」（開局沒有人持有家宝）。
- 信長6：`BFILE`／`MESSAGE` 第 0 段是稱呼規則，不是事件稿。
- 信長12：歷史事件的日文標題在 Msg、劇本、EXE、DLL 都找不到。
- 各代事件的觸發條件都還沒解：新作的事件腳本格式不同，早期作品在 EXE／overlay 裡（信長5 Win 版 `.text` 加密）。

## 發現的問題（範圍外）

- 信長4 PC-98 頭像的藍綠：fork 回報可能對調，2026-11-07 查證沒有對調（`guest os_024` 的織田信長頭像逐點相同，見 `notes/nobu4.md`「事件、插圖、道具」色盤）。是事件圖解碼器的 plane 順序不同。

## 未收尾

- 第一輪 10 款已 commit（4fe35fa），還沒 push。
- 第二輪候選（三國志 II、III、V，信長 2、3）還沒開始。
- 封存還沒做；每款「封存前還缺」見上表。新作的影音不留（見「結論」）。
