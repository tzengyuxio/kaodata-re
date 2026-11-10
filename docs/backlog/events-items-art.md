---
status: in-progress
created: 2026-11-07
---

# 事件、事件插圖、道具（三國志 I–V、12–14；信長 2–6、12–13）

## 結論

- 範圍（使用者 2026-11-07 定）：三國志 I–V 與信長 2–6，加上三國志 12–14、信長 12–14，各代要解的是事件（文字與觸發）、事件插圖、道具（名稱、效果、圖）。
- 目的之一是封存（`~/.claude/re-common.md` §11）：素材和資料先解好，就可以把遊戲封存、清出空間。新作佔的空間大（三國志12 11 GB、13 14 GB、14 20 GB），格式也比較單純；早期作品省下的空間有限，但規則已經比較熟。
- 影音不留（使用者 2026-11-07）：三國志 6 以後、信長以 Windows 為主要平台以後的作品，過場影片、BGM、語音都不轉檔也不留，封存時直接捨棄（那時的檔案大、多是通用格式）。早期作品自家的音源與色盤動畫才照 re-common §10 處理。
- 信長初代本地沒有遊戲檔，不在範圍內。信長14（創造）2026-11-11 才找到正確的 appid（292990，PK 是 DLC 344120），列在第三輪。
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
| 信長14 創造 PK（292990＋DLC 344120，繁中） | `RES_PK/res_grp.bin`（LINK，同大志） | `RES_PK/res_event.bin`、EXE 事件標題表 | 家宝：劇本檔＋`MSG_PK/kahou_retsuden*`、圖在 `res_grp.bin` 第 8 項 |

## 產出進度（2026-11-07 起，一款一 fork）

產出都在 `games/<id>/extract/`（不進版控），格式與重跑方式寫在各遊戲筆記的「事件、插圖、道具」節。

| 遊戲 | 指令 | 產出 | 封存前還缺 |
|---|---|---|---|
| 三國志 `san1-pc98` | `san1 eventcg`、`san1 strings` | 事件插圖 27 張（在 `PACKDATA.DAT`，不是 PICDATA；戰鬥 6 張用途 ✅ code，其餘 🟡）；PICDATA 113 起的小動畫 14 組 86 格（投降、待命 ✅，其餘 🟡）；`STRING.DAT` 15 州說明；沒有道具 | 4 張插圖（block 0、40、60、70，部分 XOR 編碼）與 PICDATA 348、378 ❌；事件文字在編碼過的程式裡 ❌（DOS 英文版是明文，可替代） |
| 三國志14 `san14pk-win` | `san14-extras` | 寶物 131 件＋圖 219 ✅（加成對象 🟡）；事件文字 511 個 × 日／繁中 ✅（事件號 🟡）；事件插圖 913 張（事件 93、場景、背景、題詩、名勝、人物插圖 148 🟡、表情 540）；rdb inventory | 事件腳本 `0004/Event*.s14`；3D rdb 3.4 GB；寶物持有者 |
| 三國志IV `san4pk-pc98`（中文 `san4pk-dos`） | `san4-extras` | 道具 31 件＋圖（加成 ✅ cross＋capture，種類名 🟡）、10 劇本持有者 129 筆 ✅ cross；事件插圖 53 張（NPK016，名稱 🟡、主色盤 🟡）；訊息日 1710／中 1711 則、38 段 | `OPENDAT` 85、`ENDDAT` 79 張（色盤）；`PREGRP`（NPK16）；事件腳本與觸發；音樂（§10） |
| 三國志12 `san12pk-win` | `san12-extras` | 事件 CG 130 張 ✅（歷史 39、汎用 32、komo 9、背景 23、結局 3、表情特寫 24）；名品 205 件＋圖 200 ✅（能力、特技 ✅ cross，其他效果與種類名 🟡）、特典名品 CG 20、特技 20；有語音台詞 520 句／16 段 ✅、事件訊息 2453 則 🟡、年表事件名 38 🟡 | `BtlMap` 1.8 GB、`CityMap`、`UI`；事件腳本位置；戰略地圖是 3D（只有小地圖） |
| 三國志13 `san13pk-win` | `san13-extras` | 事件插圖 242 張 ✅（事件 70、結局 22、故事 15、小物 11、背景 51、教學 73）；寶物 234 件＋圖 256（種類 ✅，圖號與持有者 🟡）；訊息腳本 29859 段 ✅、事件名 50 🟡、事件表 999 筆（欄位 ❌）；容器 inventory 3380 項 | 事件表欄位；繁中 `msggame`；`tenkai*`、`event_sf`、`eiketsu_*`、`kako_kao_still` 6107 張 |
| 信長4 `nobu4-pc98` | `nobu4-extras` | 事件圖 21 張（名稱 ✅ code，2 張 ✅ capture，砲撃 2 張 🟡）；開場 29 張（大名介紹卡 15，✅ capture）；結局 22 張（色盤 🟡）；茶器 48 件 ✅ code＋圖 15（持有者 🟡）；屏風畫 4 幅（繪師 🟡）；扇 20 格；`MAIN.EXE` 字串 2246 筆 | 事件切分與觸發；`DEMO.DAT`、`OPEN.DAT` 0x1E1CF 之後；茶器 value、扇的季節、結局色盤 |
| 信長5 `nobu5pk-win`（Steam 628090；PC-98 對照） | `nobu5-extras` | 家宝 120 件 ✅ cross（類別 ✅，價值、flag 🟡；開局無人持有 ✅，人物 +35 bit 7＝家宝的推測不成立）＋圖 26 種；事件靜止圖 5 🟡、影片清單 12 🟡；家紋 106；四季大地圖 4＋割拠図（春夏 🟡）；EXE 字串 1923 則（事件表 0xB8C58 250 則） | 事件對應與觸發（`.text` 加密）；家紋↔大名；`Hexmap.dll` 戰場圖 206 張；PC-98 事件圖色盤 |
| 信長6 `nobu6pk-pc98`（本體 `nobu6-pc98`） | `nobu6-extras` | 家宝 120 件（種類、加成 ✅ code，6 劇本持有者、讀音說明 ✅ cross）＋圖 22；官位 250（位階 ✅ code，持有者 ✅ cross）；家紋 355＋各劇本大名 ✅ cross；事件插圖 62 張（圖 ✅，說明多 🟡）；訊息 2020 則；城說明 233 | 事件切分、觸發、插圖對應；`OPEN*`／`END*` 色盤（`.PLD`）；本體 `KAMON.NB6` 110 號以後 ❌；音樂（§10）；野戰圖 |
| 信長12 `nobu12pk-win` | `nobu12-extras` | 事件 CG 121 幅（rekishi ✅ cross，hanyou／ending 界線 🟡）；家宝 355 件（名稱說明圖 ✅，弓／大砲種類名 🟡，8 劇本持有者）；特產品 20 ✅；官位／役職圖示；家紋 228；事件腳本 137 檔 10256 框（文字 ✅，觸發 🟡） | 歷史事件標題找不到；`Media/graphres.bin`；家紋↔勢力、圖示名稱 |
| 信長13 `nobu13pk-win` | `nobu13-extras` | 家宝 353 件（圖 73 種 × 2）✅／等級持有者 🟡；事件插圖 251 張（歷史組 ✅ cross，其他 🟡）；家紋 237 個；事件腳本 191 檔（文字 ✅，觸發 ❌） | 事件觸發、家宝效果、家紋↔勢力；`media/` 3D（影音不留） |

## 第三輪：刪 Steam 安裝目錄前補解（2026-11-08 起）

使用者 2026-11-08：搬移、刪除 `games/steam/` 之前，Windows 版為主的 Steam 遊戲都先盡量多解一些，免得很快又要重裝。PC-98 版已是主資料集的（三國志III、信長 1–5）不做；三國志12–14、信長12–13 第一輪做過，不重做。影音照「結論」不留。每款一個 `<game>_extras.py`，輸出到 `games/<id>/extract/`，最後再決定刪哪些安裝目錄（要先問使用者）。

| 遊戲 | appid | 大小 | 狀態 | 產出 | 還缺 |
|---|---|---|---|---|---|
| 信長 大志 PK `nobu15pk-win` | 628890 | 35 GB | ✅ `nobu15-extras` | 家宝 121 件＋圖（名稱、說明、種類 ✅ code，等級 🟡）；事件腳本 326 個（台詞 ✅ code，指令 ❌）；歷史事件目標 437 筆；事件圖 13 組 897 張（用途 🟡）；家紋 255 ✅ cross，家名 219（勢力名 108 ✅、姓推定 111 🟡） | 事件觸發（`QUEST_PK/*.bsf`）、家宝效果與持有者、天災圖對名稱、DLC 頭像（加密）；讀的檔約 2.2 GB（`RES_PK/res_face.bin`、`res_grp.bin`、`res_event.bin` 等）；`PBOX_Books/` 數位畫冊 104 MB 沒開 |
| 信長 新生 PK `nobu16pk-win` | 1336980 | 26 GB | ✅ `nobu16-extras` | 事件圖 264 張（1080p 145 ✅ code，對應 ❌）；家宝 122 件＋圖（名稱說明 ✅ cross，圖號 🟡）；家紋 226 ✅ code（號碼同大志，名稱照大志）；事件名 555（465 對到事件號 ✅ code）；事件全文 17916 列；歷代武將頭像 17320 張（14 代，代別 🟡）；演出大字 138 | 事件↔插圖↔對白、發生條件（`FLOW*/REKISHI_0n.bsf`）、家宝種類效果持有者（`fixdataPK.n16`）、歷代頭像↔武將；讀的檔約 1.7 GB＋`RES/res_face.bin` 1.4 GB |
| 信長 創造 PK `nobu14pk-win` | 292990 | 5.1 GB | ✅ `nobu14-extras` | 頭像 2510＋特大 470（頭像號↔格號：0–1999、7400、9000、9500 段 ✅／🟡，其他 79 個號碼 ❌）；歷代頭像 12628（代別 ❌）；家宝 160 件＋圖 54＋圖示（細類＝圖號 ✅ capture）；事件 519 個（台詞 ✅ code，標題 359 ✅ code）；事件圖 127、戦法字 102；家紋 251 格（72×72，名稱 152）；koei-wiki 人物、城國、列伝、家宝已匯出 | 頭像號 4000–8214、事件背景↔圖與觸發、城相鄰、特性、家宝效果、大地圖（`res_stage.bin`）；遊戲檔還在 `games/steam/292990-tchinese/`，沒硬連結到 `games/nobu14pk-win/` |
| 三國志11 PK `san11pk-win` | 628070 | 2.0 GB | ✅ `san11-extras` | 事件圖 88＋PK 戰役 19＋特寫 62（圖 ✅，對應 🟡）；寶物 43 件＋圖 35 ✅、14 劇本持有者 602 筆 🟡；規則表（特技 100、技巧、施設、兵裝、爵位、官職、戰法、地形；名稱說明 ✅，數值 🟡）；訊息全文、列傳 821 人 ✅ cross；事件台詞 3934 則 | 事件觸發（`.eve` 位元組碼）、事件圖↔事件名、寶物加成與數值欄；讀的檔 752 MB，`games/san11pk-win/` 只缺 `media/san11res1.bin` 與 `media/msg/`（約 120 MB） |
| 三國志X PK `san10pk-win` | 628060 | 964 MB | ✅ `san10-extras` | 寶物 200 件＋圖 176 ✅ code、18 劇本持有者 3600 筆（持有者 ✅ cross）；訊息 27732 則 ✅ code；事件靜止圖 96＋PK 10、事件場景素材 1177、都市畫面 800（圖 ✅，對應 🟡） | 事件腳本 `Event/*.EVS`／`*.PES` 加密（推定 XOR）；寶物 `b2`／`b3`；戰場是 3D（只出背景 7 張）、一騎討／舌戰沒做；讀的檔約 145 MB，研究事件另留 `Event/`（3.6 MB） |
| 三國志IX PK `san9pk-win` | 628050 | 1.3 GB | ✅ `san9-extras` | 事件靜止圖 72＋PK 14（圖 ✅ code，對應 ❌）；結局、畫廊、戰役群像 41（色盤 🟡）；寶物 100 件＋圖 200（名稱說明 ✅ code，加成 🟡）、20 劇本持有者 2000 筆 🟡；兵法 41；訊息 14210／11073 則；列傳 679 則（600 以後對人錯開 🟡） | 事件圖↔事件、觸發（EXE 有 SteamStub）、列傳 600 以後對人、寶物加成與兵法數值；讀的檔 98 MB，`games/san9pk-win/` 缺 8 個 `G_*.s9`＋`M_Msg.s9`、`M_Rtdn.s9`（約 83 MB）；說明書 `San9WPK.pdf` 28 MB 可留 |
| 三國志VIII PK `san8pk-win` | 628040 | 789 MB | ✅ `san8-extras` | 寶物 255 筆（名稱 ✅ code，開局所在 ✅ cross，持有者 ❌）＋圖 80；效果字串 42；列傳 654 則 ✅ cross；訊息 323 項；事件腳本 230 個（各年情勢 51 ✅ code）；事件圖 79、人物動作 1695（色盤 🟡）；畫面背景 53 | 寶物持有者（`D_Sce.s8` 0xEF45 後）、寶物↔特技效果、事件腳本碼與觸發；戰法、一騎討、戰術地圖沒做（大地圖只有概覽圖 10 張）；`games/san8pk-win/` 缺 `g_event.s8`、`m_msg.s8` 與 53 個背景檔（約 71 MB） |
| 三國志VII PK `san7pk-win` | 628030 | 637 MB | ✅ `san7-extras` | 寶物 72 件＋圖（名稱 ✅ code，說明 ✅ cross）、12 劇本持有者 864 筆 ✅ cross；兵裝 14；特技名 32 ✅ code；事件靜止圖 25、結局 30、名所 30、人物立繪 722、一騎討 209 等（用途 🟡）；訊息 7261、歷史事件對白 1575、年表 347；列傳 520 人 ✅ cross | 事件觸發（EXE，SteamStub）、事件圖↔事件、寶物加成欄、人物特技 bit；讀的檔 188 MB，`games/san7pk-win/` 缺約 140 MB（`G_*.s7`、`P_*.s7`、`M_Msg.s7`、`M_BFile.s7`、`S7gaiji.tte`） |
| 信長 將星錄 PK `nobu7pk-win` | 628100 | 682 MB | ✅ `nobu7-extras` | 家宝 200 件（名稱說明 ✅ code，10 劇本持有者 387 筆 ✅ cross，種類等級 🟡）＋種類圖 27；家紋 147＋大名↔家紋 300 列 ✅ cross；事件靜止圖 32（對應 ❌）；大地圖全圖、小地圖、野戰地形；訊息 4474 則；合戰解說 16、城說明 66、官位 250（順序 🟡） | 家宝種類名與效能、事件切分與觸發、官位號（都要解殼 EXE，SteamStub）；讀的檔 65 MB，`games/nobu7pk-win/` 缺 14 個圖檔約 61 MB；說明書 6 MB 可留 |
| 信長 烈風傳 PK `nobu8pk-win` | 628110 | 658 MB | ✅ `nobu8-extras` | 家宝 350 件（名稱、種類 35、圖號 ✅ cross）、10 劇本持有者 614 筆 ✅ cross＋圖 51；官位 250＋持有者 738 筆 ✅ cross、官職 59；年表 233 條 ✅ code；訊息 4612 則；事件靜止圖 72（對應 ❌）；家紋 162、旗印 134；大地圖 12928×2752、合戰背景、地形片 | 事件↔插圖、觸發、家宝效果與說明文、家紋↔大名、官職持有者（多半要解殼 EXE）；`games/nobu8pk-win/` 缺圖檔、BMP、`MESSAGE.NB8`、EXE 約 108 MB；說明書 52 MB 可留 |
| 信長 嵐世記 PK `nobu9pk-win` | 628120 | 724 MB | ✅ `nobu9-extras` | 家宝 380 件（名稱、種類 ✅ code）、種類效果 52 種、12 劇本持有者 1885 筆 ✅ cross＋圖 39；事件靜止圖 71（對應 ❌）、其他事件圖 423；歷史事件名 82 ✅ code；`MESSAGE.NB9` 4731 則（明文，之前沒解）；家紋 201×2 | 事件↔插圖↔對白與觸發、家紋↔勢力、家宝特技碼與兵種、戰場地形 `war/`；`games/nobu9pk-win/` 缺 26 個圖檔＋`MESSAGE.NB9` 約 190 MB，另 `war/` 2.4 MB、說明書 22 MB 可留 |
| 信長 蒼天錄 PK `nobu10pk-win` | 628130 | 885 MB | ✅ `nobu10-extras` | 家宝 460 件（名稱說明 ✅ code，種類 34 ✅ cross）、11 劇本持有者 510 筆 ✅ cross＋圖 38；家紋 229＝血族號 ✅ cross＋血族 219；官位 350、役職 75、城說明 250；歷史事件圖 40（對應 ❌）、其他事件圖 324、動畫 2553 格；大地圖 2 張＋城座標 ✅ cross；訊息 6518 則 | 事件切分與觸發、家宝 +54–57 與效果、官位號（解殼 EXE）；野戰、攻城選圖；`TUTOPRTS.NBX` 124 MB 沒輸出；`games/nobu10pk-win/` 缺 43 個 NBX 約 497 MB；說明書 30 MB 可留。另：`wiki_nobu10.places` 的 `pos` 可從 uncertain 改確定（`GMAP_POS` 單位＝`gmap1.png` 像素） |
| 信長 天下創世 PK `nobu11pk-win` | 628140 | 1.5 GB | ✅ `nobu11-extras` | 家宝 430 件（名稱說明 ✅ code）、7 劇本持有者 664 筆 ✅ cross＋圖 39；家紋 220＋大名↔家紋 354 列 ✅ cross；官位 350、役職 75＋持有者 ✅ cross；事件圖 61＋場景 83＋季節 8（對應 ❌）；事件腳本 48 檔 10503 框（條件可讀 🟡）；字串 28847 則 | 事件↔插圖（`FadeinStill` 參數）、觸發時機、家宝種類效果、施設圖命名、`yabou.n11`；`games/nobu11pk-win/` 缺 5 個 `grp` 圖檔約 75 MB＋`msg/` 1.9 MB；說明書 64 MB 可留 |
| 大航海時代IV PK HD `koukai4pk-win` | 1424800 | 2.0 GB | ✅ `koukai4-extras` | 劇情 CG 416、全身立繪 84、遺跡 25、古地圖 100 等共 803 張（對劇本 ❌）；港町背景 62；道具 231＋圖（名稱、繁中 ✅ code，效果 🟡）；交易品 105（分類 ✅ cross）；港口 97（交易品 ✅ cross；2026-11-10 補ロンドン、港號全部 +1）；世界地圖 2500×1250 格＋港口座標 ✅（`map/world.png`、`world_ports.png`）；船 39 種 107 型；上陸地點 24；劇本台詞日繁並排 35929 行 ✅ code；mesfile 日 6481／繁 4004 | 劇情 CG↔劇本、事件條件（`EV0–6.dk4`、`EVA.DK4`）、道具效果與說明、港口船其餘欄位、`World.dat` 格值；`load_koukai4_win_bustups` 的 GT1G 讀法只對 `bustup.dk4` 成立（沒改）；重跑要 1.48 GB，只留表與文字 25 MB |
| 太閤立志傳V DX `taikoh5dx-win` | 1842810 | 7.0 GB | ✅ `taikoh5-extras` | 道具 355（名稱 ✅ code）、9 劇本持有者 1503 筆 ✅ cross＋圖 104；交易品 100＋圖 47；合戰札 75＋圖 179（對應 ❌）；事件圖 79（標題 0–31 ✅ cross）；事件全文 169 個 53620 則＋繁中配對 ✅ code；城下、室內、合戰背景 255；日本全圖 | 道具說明與加成（`TAI5MSG_*.DAT` XOR 後還有一層）、事件名與觸發（`Evcon` 加密）、札圖↔札名、大地圖排法、家紋；讀的檔 451 MB，`games/taikoh5dx-win/` 幾乎都缺；`PBBATTLE/` 4 GB 3D 不留 |
| 三國志ツクール `santsukuru-win` | 397720 | 786 MB | ✅ `santsukuru-extras` | 事件圖 6（工具本身只有這些）、結局特效畫面 76；41 州地圖 ✅ cross；戰利品圖 367（類別 0–4 ✅ cross）、範例劇本道具 16；訊息 3110 行；曲名 66；說明書 11 頁；介面零件 590 | 戰利品持有者、類別 5 名稱；LINKDATA 136（地形？）、`D01005J`、`_N1G`、`LHSK`、`LCSK`；`games/santsukuru-win/` 只缺 `RES/D01128J.bin`（12 MB） |

## 第四輪：大航海 I–III、外傳、源平合戦（2026-11-10）

使用者 2026-11-10 要求補齊大航海系列缺的港口、交易品、道具、地圖與人物欄位；源平合戦的研究同日從 genpei-zh 移到本 repo。

| 遊戲 | 指令 | 產出 | 還缺 |
|---|---|---|---|
| 大航海時代 `koukai-pc98`（DOS、PC-88 表相同） | `koukai-extras` | 港口 70（名稱 ✅，位置與占有率 🟡）、交易品 26 ✅、道具 31 🟡、船種 6＋旗艦、艦隊 21 🟡；世界地圖 504×252（地形碼的三色示意圖）＋港口；古地圖 `STIZU.DAT` ✅ | 交易所行情、`MAP.PUT` 圖塊對應、船與港口經濟欄位 |
| 大航海時代II `koukai2-pc98` | `koukai2-extras` | 港口 100＋補給港 30、商圈 13（價格、貨架 ✅ code）、交易品 46、酒 14、船種 25、道具 100（種類、威力 ✅）、發現物 100＋圖 128；世界地圖 2160×1080，130 港、98 發現物落在標記格上 ✅ cross | 其他地形碼、港口旗標與狀態 +34／+35、船種 +0／+9 |
| 大航海時代外傳 `koukaigd-win` | `koukaigd-extras` | 同 II 的表（船種 32），圖 165；多半是對照 II 的結構 🟡 cross | 外傳自己的程式只讀了道具圖號 |
| 大航海時代III `koukai3-win` | `koukai3-extras` | 城市 226（港 135；名稱、座標、國、規模、設施 ✅ code）、國家 78、交易品 70（28 區價格 ✅）、設施 1508、船 8 ✅、道具 285＋圖 205、發現物 273＋圖 84、城鎮圖 226；世界地圖是地形類別示意圖 | 世界地圖的圖塊對應、交易品與部分發現物的圖、幾個城市／船／國家欄位 |
| 大航海時代IV `koukai4pk-win` | `koukai4-extras`（補） | 港口改為 97（補ロンドン，港號 +1）；`World.dat` 2500×1250 格的世界地圖＋港口 ✅；港口中心港、地區 ✅ | 交易品、船、道具效果、上陸地點的欄位 |
| 源平合戦 `genpei-dos` | `genpei-extras` | 4 劇本的武將、勢力、國、地方、官位、家寶表（和 genpei-zh 0 差異）；四季大地圖＋156 節點 ✅ cross；NPK016 圖 220＋季節圖 11；訊息 1305 則、EXE 字串 | 合戰圖塊、部隊圖、`Maincmd`／`Mainanm`；開場結尾色盤；PC-98 版 |
| 項劉記 `kouryuuki-dos` | `kouryuuki-extras` | 地點 39（中文名、PC-98 日文名與讀音、格、四劇本地點碼 ✅ code，相鄰【推】）；大地圖 2640×1408 四季各一張＋標名版（`MAP.KR1`＋`GRP4.KR1`，✅ code，2026-11-10 加） | 地點表 +14–16、`HKMD`／`HYMD` 戰場圖、部隊圖 |
| ジンギスカン `genghis-pc98` | `genghis-extras` | 國 41（欄位 ✅ code+cross）、相鄰 ✅ cross（41 張戰場圖的進入區）；大地圖 2 張 384×160（PAK，✅ code）＋標名版；戰場地形 41 國 CSV（地形名 🟡）；人物 200；圖片 103（格式 ✅ code，內容【推】）；沒有道具 | `ANIME`／`HANIME`、地形名與六角格排法、`SAVEDATA` |
| 元朝秘史 `genchou-pc98` | `genchou-extras` | 4 劇本的國 113 筆（✅ code+cross，PC-88／X68000／DOS 同值）、勢力 87 ✅ cross、人物 346；大地圖蒙古篇、世界篇各四季（✅ code，沒和截圖比對） | 結局圖 `ENDGRP` 23 張的色盤（在 `END.EXE`）、`PACKDATA`、`OPENGRP`；國表 +0x2A 高位、勢力關係表 |
| 成吉思汗IV `genghis4pk-win` | `genghis4-extras` | 4 劇本的地域、國、都市、特產品、文化寶物、兵種、男女人物（讀取順序 ✅ code）；列傳 533 人 ✅ code；寶物圖 134、特產品圖 31、事件圖 5（名稱【推】）；大地圖 16000 × 3616（`LARGEMAP.BMP` 的 320 × 226 區塊，✅ code＋cross）＋各劇本都市標示 | `MAPFIX`／`MAPVAR` 每格屬性的意義 🟡、都市相鄰 ❌、都市的特產品 ❌、+44 bit 3–9、國關係旗標 |

## 下一步

建議順序（投入／收穫）：

1. 三國志 I 事件插圖：`PICDATA.DAT` 113 之後，格式已知。
2. 信長 12、13 的家宝與事件：檔案都分好名、文字格式（N12F／N13F）已經解過，事件插圖在單一檔案裡。做完可以先封存信長 12、13。
3. 三國志 12–14 的事件圖與道具圖：封裝都已經解得開，主要是分類和命名；做完可以封存，清出最多空間（共約 45 GB）。
4. 信長 4、5、6 的道具：名表或位置已知，補欄位和圖。
5. 三國志 IV、V 的美術檔：NPK016 的解碼器（源平、英傑傳）也許可以直接用。
6. 事件文字：從 EXE、`MESSAGE`、`STR` 切成一則一則，工作量最大，等 koei-wiki 訂格式。

koei-wiki 事件條目（2026-11-07 提案；koei-wiki 的使用者同意，格式定案；同日匯出第一輪 `events-export`：信長4 7 張、信長6 PK 9 張、三國志IV PK 6 張）：

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

- 第一輪 10 款已 commit（4fe35fa）並 push。
- 第三輪 15 款（2026-11-08）已 commit（7cdaa78）並 push；要讀的檔已硬連結到 `games/<資料集>/`、重跑驗證過，三國志 6 以後、信長 7 以後的 Steam 安裝目錄已刪，大航海4、太閤5、ツクール與早期作品的保留（見 `notes/steam.md`「安裝目錄的刪除」）。
- 第二輪候選（三國志 II、III、V，信長 2、3）還沒開始。
- 第四輪（大航海 I–III、外傳、IV 補完，源平合戦）2026-11-10 完成並 commit（6c5cb96 等），已 push。
- 三國志VIII–14（`san8pk-win`–`san14pk-win`）2026-11-11 已入庫，遊戲檔上傳到 NAS 後刪除本機副本（`notes/steam.md`「三國志8–14 的封存」）；其他款還沒入庫，每款「封存前還缺」見上表。新作的影音不留（見「結論」）。入庫用 `scripts/archive.py <dataset> [--library DIR] [--skip-original]`（re-common §11）：kaodata 匯出＋`faces.cbz`／`faces.csv`、koei-wiki 匯出、`extract/`（純圖資料夾打包成 cbz）、截圖複製進 `~/game-library/koei/<dataset>/`，Steam 安裝目錄硬連結到 `_original/win/` 並記 sha1；目前只收三國志 10–14、信長 9–13 的 Steam 版。2026-11-10 用 `nobu12pk-win --skip-original` 試跑到暫存目錄，頭像 1379 張、7 個 cbz 的張數都和來源一致；`--skip-original` 以外的路徑沒測，因為這 10 款的安裝目錄已經刪了。
