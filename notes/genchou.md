# 蒼き狼と白き牝鹿・元朝秘史（GENCHOU, PC-88）頭像相關格式

`dekoei.py export genchou-pc88` 用到的格式（`build_genchou_pc88`）。

## 版本與磁碟

- 來源：Neo Kobe 2016-02-25 的 `~/game-library/_original/pc88/neo-kobe-2016-02-25/Aoki Ookami to Shiroki Mejika - Genchou Hishi/` 唯一一組 `[FD]`（Disk A–D 與 Save disk；Alt 1／2 只有 Save disk 不同）。
- 四片都是 YDOS 3.0，每軌 9 × 512 bytes。
- Disk A 的 `VERSION` 寫「ＰＣ－８８０１ＳＲ版 … ver 1.2 1992.07.17」，檔案日期 1992-04～07-17。
- `games/genchou-pc88/` 放 Disk C 的 `KAODATA.DAT`、`GENDATA1–4.DAT`、`USDATA1–4.DAT`，Disk D 的 `QKAODATA.DAT`，以及參考用的 Disk A `MAIN.COM`、`VERSION`。

## 頭像：KAODATA.DAT（男）、QKAODATA.DAT（女）

- 前段是 40 張逐人頭像，每張 1830 bytes：
  - 6 bytes 表頭：眼 1、眼 2、口的位置（x 像素、y 半高列）。
  - 960 bytes 的 64×40 臉，每 8 點 B、R、G 3 bytes（`pc88.brg_pixels`，逐列加倍）。
  - +0x3C6 起是眼的動畫幀（第 0 幀 2 塊 × 9 bytes × 8 列），+0x606 起是口（第 0 幀 12 bytes × 8 列）。臉圖的眼口處是空的，匯出時把第 0 幀依表頭位置 OR 進去（x & 7 做位移）。
- 後段是組合臉類型，每型 7302 bytes：KAODATA 16 型、QKAODATA 8 型（`MAIN.COM` 0x2973，表格在 0x2913 大小、0x292B 位移、0x2943 間隔、0x295B 目的位置）。
  - 6 bytes 表頭同上，接著上、下、眼、口各 4 個：

    | 部件 | 男：位移／大小 | 女：位移／大小 |
    | --- | --- | --- |
    | 上 | 6／480（20 列） | 6／576（24 列） |
    | 下 | 0x786／480（接在上之後） | 0x906／384（16 列） |
    | 眼 | 0xF06／2 × 72（間隔 576） | 同左 |
    | 口 | 0x1806／96（間隔 288） | 同左 |

  - 上、下直接貼；眼、口用 OR 疊在表頭位置，匯出成整張 64×80 的項目、slot 用 `blend: "or"`。
- 頭像碼（`MAIN.COM` 0x2C66）：< 0x28 是逐人頭像號（女性的號對 QKAODATA）；否則類型在 bit 11–14，上、下、眼、口是 bit 9、7、5、3 起的 2 bit。
- 匯出：portraits 0–39 男、40–79 女（同 `genchou-fc`）；variants 0–15 是「男 N」、16–23 是「女 N」。
- 色盤：找不到寫色盤 port 的程式，是預設的數位 8 色（palette id `pc88`）。
- 沒用到：女性 P32（portrait 72，戴頭巾的女子；FC 把它給イァティマード，PC-88 的イァティマード和サフィーア都用 P33）、女性類型 3。

## 人物

`koei_games.load_genchou_pc88_people` 讀 4 個劇本：

- `GENDATA<s>.DAT`：男 109 筆 × 27 bytes（從 1 起，名字 17 bytes Shift-JIS，頭像碼 +25）；女 33 筆 × 23 bytes（0x1A23 起，頭像碼 +21）。沒有名字（或名字是「　」）的是空位。劇本 4 男性第 0 筆「モンゴル統一者」是玩家自己的佔位，略過。
- `USDATA<s>.DAT`：每 351 bytes 一區，前 8 筆是 27 bytes 的登場武將，後 5 筆是 23 bytes 的子嗣（頭像碼 +21，女兒是 0、沒有臉，略過）。`GENDATA` 0x14A7 起是 `USDATA1` 的副本（後段是別的資料），不讀。
  - 子嗣頭像：`USDATA2` 第 0 區的ジュチ、チャガタイ、オゴタイ、トゥルイ是頭像 35–38。
- 名字做 NFKC（同 `genchou-fc`）。同名（女性另算）是同一人；碼不同時依劇本放 `expressions`（只有三浦義村：劇本 2、4）。
- id 照 `genchou-fc`：男是 GENDATA1、USDATA1 第 0 區、GENDATA2–4 的出現順序，女從 1000，只當子嗣出現的從 2000；`genchou-fc` 的 299 人全部對得上。FC 把アイバク（劇本 4）、アルベルトゥス（劇本 3）各當另一人（FC 的臉不同），這裡照做（`GENCHOU_PC88_SPLIT`）。FC 沒有的 USDATA 武將從 222、子嗣從 2004 起。
- 「考宗」是孝宗（FC 198）、「畠山重定」是畠山重忠，填 `nameHistorical`。

### 能力

- 男性記錄：+20 bit 0–2 政治力、bit 4–6 戦闘力；+21 bit 0–2 指揮力、bit 4–6 魅力；值 0–4 顯示成 Ｅ–Ａ（DS:0x4CB0）。+19 体力，低 nibble 是現在值、高 nibble 是上限；+22 年齢；+24 bit 0–1 身分（将軍／政治顧問／領主，DS:0x4CAA），bit 6 重病。讀取用 `koei_stats.load_genchou_stats`，`dekoei.py koei-person genchou-pc98`。
- ✅ code：PC-98 `MAIN.EXE` 段 0 的 0x6808–0x6874 讀取函式、人物視窗 0xD59E（`政治力 体力 戦闘力 年令 指揮力 身分 魅力`）、司令官視窗 0x2B3C0（另有 `重病`）。
- ✅ cross：PC-88、PC-98、X68000、DOS 的能力值 339 筆相同。+17–+24 只有劇本 3 ミカエル8世 的 +23 不同（X68000、DOS 0x57，PC-88、PC-98 0x53）。
- +17 是所属勢力、+18 是所在国（FF＝沒有／未登場）。2026-11-10 改正：之前寫反了。其他欄位見下面「人物欄位」。
- ❌ 女性 +17–+19；記錄裡沒有生年、相性、寿命。

## X68000 版（`genchou-x68`）

`dekoei.py export genchou-x68` 用 `build_genchou_pc88(x68=True)`。

- 來源：Internet Archive `aoki-ookami-to-shiroki-meshika-genchou-hishi-1993-koei-disk-1-of-3`（`~/game-library/_original/x68/ia-softwarelibrary/`，3 片），發行 1993-02-26（ja.wikipedia）。沒有版本字串；`MAIN.Z` 與劇本檔的日期是 1993-02-10，`MAIN.Z` 有「X68000 CONVERSION STAFF … T.FUJINUMA 1992,1993」。`games/genchou-x68/` 放 Disk 1 的 `KAODATA.DAT`、參考用的 `MAIN.Z`，以及 Disk 3 的 `GENDATA1–4.DAT`、`USDATA1–4.DAT`。
- `MAIN.Z` 是 CZ10（`ls11.cz10_decode`，映像位址＝檔案＋0x514FA）。
- `KAODATA.DAT` 一個檔放男女兩組，排法同 PC-88 但全高（列數、表頭 y 都是整列，各部件高度加倍）：
  - 男 64 張 × 3654 bytes（6 bytes 表頭、1920 bytes 64×80、眼 4 幀 × 2 × 9 bytes × 16 列、口 3 幀 × 12 bytes × 16 列），接 16 型 × 14598 bytes 的組合臉；女 40 張、8 型。
  - 組合臉：男上 6／960、下 0xF06／960；女上 6／1152、下 0x1206／768；眼 0x1E06／288（間隔 1152）、口 0x3006／192（間隔 576）。
  - PC-88 的 40 張男性頭像全部重畫，另多 40–63 共 24 張：PC-88 用組合臉的 24 人（カサル、ベルグタイ、カチウン、テムゲ、耶律阿海、北条義時、ルイ8世、パスパ、アルグン等）改用獨立頭像。
- 人物：記錄是 PC-88 的再加 3 bytes 0，頭像碼改成大端序放在最後 2 bytes（`load_genchou_pc88_people(..., x68=True)`）。
  - `GENDATA1–3`、`USDATA1–3` 是 `san3.unpack_x68_sndata` 的壓縮，`GENDATA4`、`USDATA4` 沒壓縮（第一個 byte 是 0xFF）。
  - `GENDATA`：開頭是 `USDATA1` 的副本（0x66A bytes），男 109 筆 × 30 bytes 從 0x66A 起，女 33 筆 × 26 bytes 從 0x1E46 起。`USDATA`：2 bytes（FF FF）後每 410 bytes 一區，8 筆 30 bytes 的武將接 5 筆 26 bytes 的子嗣。
  - 名字、記錄順序與 PC-88 逐筆相同（445 筆），只有頭像碼不同（上述 24 人，以及イァティマード用女性 P32，PC-88 是 P33），並修正兩個錯字：「考宗」→孝宗、「畠山重定」→畠山重忠。所以 id 照 `genchou-pc88`，不需要 `nameHistorical`。
- 色盤：`MAIN.Z` 0x38D6E 是寫圖形色盤（$E82200）的程式，0x2724 把檔案 0x44924 的 16 色（B、R、G 各 0–31）設進去；頭像用 0–7（palette id `x68`）。
- 104 張頭像全部用到；女性類型 3 同 PC-88 沒用到。

## PC-98 版（`genchou-pc98`）

`dekoei.py export genchou-pc98` 用 `build_genchou_pc88(pc98=True)`。來源是 Internet Archive neo-kobe 的 `Genchou Hishi [FD]`（`~/game-library/_original/pc98/neo-kobe-2017-11-17/Koei/`），Disk A 的 `KAODATA.DAT`、`MAIN.EXE`、`VERSION` 與 Disk C 的 `GENDATA1–4.DAT`、`USDATA1–4.DAT` 放在 `games/genchou-pc98/`。`VERSION` 寫「ＰＣ９８０１ＶＭ『元朝秘史』Type B Ver 1.0 Rel 1」，檔案日期 1992-09-16。

- `KAODATA.DAT` 和 X68000 版逐 byte 相同（全高、男性 64 張），所以頭像與組合臉和 `genchou-x68` 相同。
- 色盤：`MAIN.EXE` 檔案 0x3E93A 起是色號 0–7 的類比色，每色 3 bytes（B、R、G，4 bit），換成 8 bit 是 v × 17。設計和 X68000 版相同，只是量化不同（例：`#004488`，X68000 是 `#004a8c`）。
- 人物：`GENDATA` 是 PC-88 的排法往後挪 1 byte（檔頭是 `FF 00`，男性從 2 起、女性從 0x1A26 起），`USDATA` 同 PC-88，但檔尾接著磁碟殘留的垃圾，所以只讀完整的 351 bytes 區塊。頭像碼是 X68000 版的碼（男性 40–63 是獨立頭像）。445 筆記錄的劇本、姓名、頭像碼和 X68000 版完全相同，包括 PC-88 的兩個錯字已改正（畠山重忠、孝宗）。

## DOS 中文版（`genchou-dos`）

`dekoei.py export genchou-dos` 用 `build_genchou_pc88(dos=True)`。來源是 `games/archives/dos/元朝秘史_killpeople.rar`（上傳者標記 killpeople，解在 `games/archives/dos/genchou-dos-src/`），`games/genchou-dos/` 放 `KAODATA.DAT`、`MAIN.EXE`、`GENDATA1–4.DAT`、`USDATA1–4.DAT`。`MAIN.EXE`、劇本檔的日期是 1994-01-14，有 `MSG.16P`／`NAME.16P` 中文字型。

- `KAODATA.DAT` 和 PC-98、X68000 版逐 byte 相同，頭像與組合臉也就和 `genchou-pc98` 相同。
- 色盤：`MAIN.EXE` 檔案 0x422D4（DS:0x3734，DGROUP 是 0x3A3A）是 16 色表，前 8 色和 PC-98 的色表逐 byte 相同（B、R、G，4 bit）。0x49C6 把每個值左移 2 寫進 VGA DAC，換成 8 bit 是 `v << 4 | v >> 2`（palette id `vga`）。
- 人物：`GENDATA`、`USDATA` 的大小與排法都和 PC-98 相同，名字換成光榮台灣內碼（`load_genchou_pc88_people(dos=True)`，`koei_tw_name`）。854 筆記錄逐筆比對，頭像碼與有名字的位置全部和 PC-98 一致；劇本 4 的玩家佔位叫「蒙古統一者」。
- id 照 `genchou-pc98`（372 人）。中文名的分組和日文名不同，用兩張表調整：
  - `GENCHOU_DOS_NAMES`：15 人在劇本 2、4 的譯名不同（例：帖卜騰格里／騰格里、茶哥／恰凱），取劇本 4（使用者決定）。分組時劇本 4 的記錄歸到劇本 2 的寫法，因為アル・ナーセル的劇本 4 譯名「納西爾」也是劇本 2 另一人（ムハマドナーセル）的名字。
  - `GENCHOU_DOS_SPLIT`：5 個名字在 PC-98 是兩人：亦納勒赤（イナルチ／イナルチュク）、脫劣勒赤（トレルチ／子嗣ドルジ）、阿合馬（アーマド／アフマド）、席拉（シイラ／シャーラ），以及照 FC 拆開的艾伯克（アイバク）。
- `nameHistorical`（`GENCHOU_DOS_NAME_HISTORICAL`，9 筆）：字型缺字的偪山重忠（畠）、浘原景時（梶），錯字籐原定家、阿興道（陳興道）、摩柯末（摩訶末）、耶木罕（那木罕）、普西重（普西里），以及寫成別人名字的マンガラ（蒙哥→忙哥剌）、タタトンガ（脫里脫→塔塔統阿）。音譯不同的（如海渡）不填。
- 日文版（`genchou-pc98`、`genchou-x68`、`genchou-pc88`）的 `nameZh` 就是這份中文名（有 `nameHistorical` 的用正確寫法），依 id 對應；各遊戲目錄的 `dos/` 放同一份 `GENDATA1–4.DAT`、`USDATA1–4.DAT`（記在 `source.inputs`）。`genchou-sfc`、`genchou-md` 的編號不同，沒有加。

## 國與大地圖

`dekoei.py genchou-extras --game-dir ../games/genchou-pc98 --out ../games/genchou-pc98/extract`（`genchou_extras.py`）輸出 `countries.csv`、`factions.csv`、`persons.csv`、`map/`，以及 `PACKDATA.DAT` 的 `eventcg/`、`ordo/`、`regions/`（見「事件、插圖、道具」）。中文名讀 `games/genchou-dos/` 同位置的記錄（`--dos-dir`）。

位址是 PC-98 `MAIN.EXE` 的映像位址（MZ 檔頭 0x4200，DGROUP 在映像 0x37B20、檔案 0x3BD20）。`GENDATA<n>.DAT` 整個讀到 DS:0x42，所以「GENDATA 位移＋0x42＝DS 位址」：國表在 DS:0x0BC4（0x67E0 用 `(bx − 0xBC4) / 0x31` 換回國號）、勢力表在 DS:0x1216（0x67EC）、男性在 DS:0x44。✅ code

磁碟：`games/genchou-pc98/` 原本只放頭像與劇本檔，2026-11-10 從 neo-kobe `Genchou Hishi [FD]` 的 Disk A–C 補齊（`MAPDATA.DAT`、`ZNAME.DAT`、`OPENGRP.DAT`、`ENDGRP.DAT` 等，逐片原樣在 `games/archives/pc98/disks/genchou-pc98/a`、`b`、`c`、`savedisk/`；FAT12 讀法只在 session scratch）。DOS 版的同名檔補進 `games/genchou-dos/`。`MAPDATA`、`HEXKG`、`HEXSG`、`KGRP`、`SGRP`、`KPAT`、`SUNIT`、`PACKDATA`、`FONT` 兩版 byte 相同；`ZNAME`、`ORDMSG`、`GRPDATA` 不同（中文）。

### 劇本檔的其他區（GENDATA，PC-98／DOS 位移）

| 位移 | DS | 內容 |
|---|---|---|
| 0xB82 | 0x0BC4 | 國，33 × 49 bytes（蒙古統一篇只用 14 筆） |
| 0x11D4 | 0x1216 | 勢力，33 × 22 bytes |
| 0x1D1E | 0x1D60 | 勢力兩兩之間的關係，三角表 528 bytes、每格低 4 bit（0x6914、0x6960）；四個劇本開局都是 0 |
| 0x1F58 | 0x1F9A | 階段：0＝蒙古統一篇（劇本 1），其他＝世界篇。0x9E70 依它決定 `ZNAME.DAT` 從 0 讀或從 0x231 讀 ✅ code |
| 0x1F59 | 0x1F9B | 季節 0–3：0x58CD 用它查 DS:0x41BE 的「春 夏 秋 冬」，0x4FE4 用它選地圖色盤 ✅ code；開局都是 0（春） |
| 0x1F5B | 0x1F9D | 國數（14／33）；0x13DBC 等迴圈的上限 ✅ code |
| 0x1F5C | 0x1F9E | 勢力數（14／33）🟡 |

- 0x1F8B 的 u16 在 4 個劇本是 1184、1206、1271、1185，像開始年，但程式把 DS:0x1FCD 當 byte 旗標讀（0x2C39 等），沒有確認。❌

### 國（49 bytes）

| 位移 | 內容 | 證據 |
|---|---|---|
| +0 | u16，DS 指標，指到同一勢力的另一國（劇本 2：華北→遼東、シリア→エジプト），沒有是 0 | 🟡 |
| +2 | 所属勢力（勢力號） | ✅ code（0x13DC8 比 `[bx+2]`）＋cross（各勢力的本國都屬於自己） |
| +3–+7 | 相鄰的國，最多 5 個，FF 補位（0x68B2 傳回 +3） | ✅ code；四個劇本都對稱 |
| +8、+0xA、+0xC | u16 金、食糧、人口 | ✅ code：「領国一覧」0x13E80 起的 printf，格式 DS:0x86F5，表頭 DS:0x85F0「金 食糧 人口 経済 農産 住モ 文化圏 気候 病 災」 |
| +0xE–+0x11 | 町％、農％、畜％、特％（和 100） | ✅ code：同一個函式的第 2 頁（0x140AE，表頭 DS:0x8642「町％ 農％ 畜％ 特％ 特産品 部隊 装備 訓練 城防」） |
| +0x12 | 城防 | ✅ code（第 2 頁） |
| +0x13、+0x14、+0x15 | 経済、農産、住モ（住民モラル） | ✅ code（第 1 頁） |
| +0x16–+0x25 | 16 種兵各幾隊；0xE284 把 16 格加起來就是「部隊」 | ✅ code（加總）；第幾格是哪一種 🟡：照 DS:0xC098 的兵種表順序（軽歩兵 重歩兵 長槍兵 火砲兵 短弓兵 長弓兵 弩弓兵 象兵 投石機 狩猟騎兵 槍騎兵 蒙古騎兵 軽弓騎兵 突撃騎兵 騎士 武士），武士只在日本、象兵只在印度文化圏、騎士只在歐洲，對得上 |
| +0x26、+0x27 | 装備、訓練 | ✅ code（第 2 頁） |
| +0x28 | 特産品，查 DS:0x8366（毛皮 絹 宝石 貴金属 医薬品 木工品 陶磁器 ガラス 織物 香料 食糧 武具） | ✅ code |
| +0x29 | bit 2–4 文化圏（0x689A，DS:0x85F0：蒙古 内亜 印度 日本 西欧 東欧 回教 中国），bit 5–7 気候（0x68A6，DS:0x5C2E：Ａ Ｂ Ｃfa Ｃfb Ｃw Ｃs Ｄf Ｄw）；bit 0–1 都是 0 | ✅ code |
| +0x2A | bit 0 病（0x6AC8），bit 1、bit 2 災（0x6AD0、0x6AD8，任一個就顯示「○」） | ✅ code；開局都是 0 |
| +0x2A bit 4–7 | 每個劇本各一國：高昌 0x10、華南 0x20、アラビア 0x40、イタリア 0x80（蒙古篇是アルタイ山麓 0x10、内モンゴル高原 0x20） | ❌ |
| +0x2B–+0x2E | 町農畜特％的副本 | 🟡 |
| +0x2F–+0x30 | 開局都是 0 | ❌ |

- ✅ cross：PC-88 版的國表在 0xB80，33 筆的 +2–+0x2E 全部相同；X68000 版（解壓後 0x1330，58 bytes 一筆：+0 改成 u32、金食糧人口改成大端序 u32）的值也全部相同。DOS 版和 PC-98 版 byte 相同。

### 勢力（22 bytes）

+0 名稱 16 bytes、+0x10 是 0、+0x11 u16 本國（國表的 DS 指標）、+0x13 u16 君主（男性記錄的 DS 指標，27 bytes 一筆）、+0x15 bit 0–2 文化圏（同國表的名稱），bit 7＝不存在（名稱留著）。

- ✅ cross：每個勢力的君主 +17 是該勢力、+18 是本國，本國的 +2 也是該勢力（4 個劇本 87 家全部成立）。+0x15 和君主 +23 bit 2–4 的文化圏也一致。
- 中文名讀 DOS 版同位置（`factions.csv` 的 `nameZh`）。

### 國名（ZNAME.DAT）

17 bytes 一筆：0–13 是蒙古統一篇的 14 地方（オノン河流域…アルタイ山麓），33–65 是世界篇的 33 國（モンゴル高原…イベリア），中間空白。DOS 版是中文（光榮台灣內碼），第 10 筆寫成「貝加爾湖東岸」，和第 7 筆重複，日文是「バイカル湖西岸」；匯出照原樣。

### 大地圖（MAPDATA.DAT）

- 6 段 640×200 的壓縮圖，格式同三國志III（`san3.world_band`：u16 寬、u16 高、8 個 u16 色字、4 平面），兩段上下拼成一個 640×400 的畫面：0x0000＋0x3F1D 是蒙古統一篇、0x8CC7＋0xFDB9 是世界篇（0x569E 的參數是 0 時讀 0x0000 起 0x8CC7 bytes，否則讀 0x8CC7 起 0xCE60 bytes），0x15B27＋0x1CD20 是人物畫面的底圖（青花紋樣；0x1CB96 也讀 `MAPDATA.DAT`，讀哪一段沒追 🟡）。蒙古篇、世界篇 ✅ code（讀取位置）；圖在畫面上的樣子沒有截圖比對【推】。
- 圖上已畫好國號（國號＋1）與視窗框。各國號碼框的左上角：蒙古篇 x 在 DS:0x309E、y 在 DS:0x30E0（14 個）；世界篇 DS:0x3122、DS:0x3164（33 個）。0x7A20 用它做 16×24 的點選判定，0x54F0 在那裡重畫號碼 ✅ code。`countries.csv` 的 `x`、`y` 是框的中心；47 個框裡都有號碼字（色號 0）且大半是陸地白（色號 7）✅ cross。
- 色盤：色號 0–7 是 DS:0x2C1A，8–15 是 DS:0x245E＋0x48 × 季節（0x4FE4）；每色 3 bytes，依 0x192 寫 port 的順序是 B、R、G（4 bit），換成 8 bit 是 v × 17。每個季節 0x48 bytes 是 3 組 8 色，只差色號 9、13、15 輪替（水面的色盤動畫），匯出用第 0 組。✅ code。冬季的山有雪。
- `map/mongolia-<季節>.png`、`world-<季節>.png`（spring、summer、autumn、winter）、`screen.png`（人物畫面底圖，用春季色盤 🟡）。
- 0x238A0 起的 288×256（寬字 0x0120）用同一解法解不出來，0x249A0 之後 27 KB 沒查。❌

**koei-wiki 匯出**：`dekoei.py places-export genchou-pc98 --game-dir ../games/genchou-pc98 --out ../export/koei-wiki/places`（`genchou_extras.places`，koei-places/1，2026-11-10；DOS 中文版要放在旁邊的 `../genchou-dos`）。47 國，`level` 是「國」；世界篇（劇本 2–4，三個劇本的國名、相鄰、號碼框相同，匯出時有檢查）用遊戲的國號 1–33，蒙古篇（劇本 1）是 100＋國號（101–114）。`name` 是 DOS 中文版的寫法，`nameJa` 是 PC-98 版的。大地圖 `world/{mongolia,world}-{spring,summer,autumn,winter}.png`（640×400），`pos` 是國號框的中心。檢查 391 項、0 不符。

人物：`dekoei.py persons-export genchou-pc98 --game-dir ../games/genchou-pc98 --out ../export/koei-wiki/persons --places ../export/koei-wiki/places`（`wiki_genchou.py`，koei-persons/1，2026-11-11），372 人，和 kaodata `genchou-pc98` 的人物一一對上。檢查 864 項、0 不符；koei-wiki `verify_persons.py` 3260 項、0 不符。

- 跨劇本對人：照 kaodata 的 `genchou_ids`，同名（NFKC，女性另算）是同一人；アイバク（劇本 4）、アルベルトゥス（劇本 3）照 FC 當另一人（`GENCHOU_PC88_SPLIT`）。`name` 用同 id 的 DOS 中文名（劇本 2、4 寫法不同的 15 人取劇本 4 的寫法，同 kaodata），史書寫法不同的 9 人寫在 `notes`。
- 收哪些人：4 個劇本 `GENDATA` 的男女（劇本 4 的「モンゴル統一者」佔位不收），加上 `USDATA` 的登場武將（`status`「登場武將」，劇本開始時不在場，沒有 debut，標 `uncertain`）和有頭像的子嗣（「子嗣」）。
- `stats` 是 政治力 戦闘力 指揮力 魅力，照存的 Ａ–Ｅ；`more` 是年齢、体力、体力上限、身分、文化圏、重病；`hidden.捕虜台詞`（欄名是這邊取的，標 `uncertain`）。能力、年齢取第一個出現的劇本，各劇本年齢寫在 `notes`。
- `scenarios`：`status` 是身分（国王、領主、政治顧問、将軍），沒有所屬勢力的寫「将軍（無所屬）」；`lord` 是所屬勢力（+17）的君主；`location` 是所在国（+18，劇本 1 是 100＋國號＋1，其他是國號＋1，同地點匯出）。沒有年（0x1F8B 的年沒確認）。劇本 4 玩家勢力的人沒有 `lord`。
- `relations.siblings`：+23 記號 `*`（君主的兄弟）連到同劇本的君主。其他親屬沒有欄位。
- `extract/factions.csv` 只列到 GENDATA 的勢力數（+0x1F5C），但人物的 +17 會指到更後面的勢力（劇本 1 的タタル族是 26），匯出直接讀 33 筆勢力記錄。
- 亂數產生的名字：劇本資料裡沒有；女性、子嗣的名字都存在檔案裡。

## 人物欄位

男性 27 bytes（PC-98 `GENDATA` 從 2 起，記錄內位移各版相同），`persons.csv` 一劇本一筆：

| 位移 | 內容 | 證據 |
|---|---|---|
| +0 | 名字 17 bytes | |
| +17 | 所属勢力（FF＝沒有） | ✅ code：0x1AC8D `mov al,[si+0x11]` 交給 0x67BC（勢力號 → 勢力記錄）；cross 見上 |
| +18 | 所在国（FF＝未登場） | ✅ cross：各勢力君主的 +18 都是本國 |
| +19 | 体力：低 nibble 現在值、高 nibble 上限 | 見「能力」 |
| +20、+21 | 政治力 戦闘力、指揮力 魅力 | 見「能力」 |
| +22 | 年齢 | 見「能力」 |
| +23 | bit 0–1 記號（0x6850，DS:0x27C8：3＝`#` 君主、2＝`*` 君主的兄弟）；bit 2–4 文化圏（0x685C，名稱同國表）；bit 5–7 捕虜時的台詞類型 0–4（0x6868，唯一呼叫端 0x1ACAD：DS:0xA57A 起每類 2 句隨機一句，例：0「我が命運も ここまでか…」、1「命乞いはせぬ さっさと殺せ！」、2「貴人としての 死を願おう…」） | 記號、台詞 ✅ code；文化圏 ✅ cross（和勢力 +0x15 一致） |
| +24 | bit 0–1 身分：0x1ACC3 查 DS:0x5C0E「将軍 政治顧問 領主 国王」（3＝国王，君主都是 3）；bit 6 重病；bit 7＝空位（0x69D4 刪除人物時寫 0x80）；bit 2–5 都是 0 | ✅ code |
| +25 | u16 頭像碼 | 見「頭像」 |

- 台詞類型的遊戲內名稱不知道，欄名 `捕虜台詞` 是這邊取的。
- 人物記錄裡沒有父子、兄弟等關係欄位；能知道的只有 +23 的君主兄弟記號。子嗣在 `USDATA`（見「人物」），`persons.csv` 沒有收。
- 女性 23 bytes（0x1A26 起）：+20 是所在国（✅ cross：岐国公主在華北、宣徳公主在朝鮮半島、八条在日本、イザベラ在イギリス，都是該國勢力的本國），+17 都是 FF，+18、+19 不明（照原值輸出），+21 u16 頭像碼。❌

## 事件、插圖、道具

- 沒有道具。
- `ENDGRP.DAT`：開頭 23 張用 `san3.world_band` 解得出來（第 0 張 640×104，之後 640×200），色盤在 `END.EXE`，沒找，所以沒輸出。❌
- `PACKDATA.DAT`（DOS 版同檔）：一張接一張，格式同信長4 的壓縮圖（`nobu4_extras.decode_pack`，u16 寬、u16 高；每張讀完剛好接到下一張 ✅ code），色盤是 `PALETTE_BASE` 的 8 色（同頭像），`genchou-extras` 輸出到 `eventcg/`、`ordo/`、`regions/`，各附 CSV：
  - 事件圖 224×160 6 張（`eventcg/pack00–05`，疫病、？、大雪、嵐、旱魃、豊作【推】，看圖），另有 216×200 的オルド圖（后妃與君主相擁，`pack06`）、432×224 的勝利圖（`pack07`）【推】。
  - オルド（後宮）152×304 31 張（`ordo/GG-S.png`）：位移表 DS:0xAD5A，11 組 × 3 階段（0x20C21 ✅ code）。階段由 DS:0xADFE 決定（<100、<150、其餘，推定是寵愛度 🟡）：盛裝、寬衣、寢室。組是女性的文化圏 0–7（蒙古 内亜 印度 日本 西欧 東欧 回教 中国，同 DS:0x85F0），頭像碼 0、1、7 例外用組 8、9、10（ボルテ、クラン、ラッチ）；組 10 只有一張，三個位移都指向它，階段 2 跳過。使用者以前也解過，記得的 11 組相同（2026-11-12）。
  - 地域圖 128×64 47 張（`regions/NN.png`）：位移表 DS:0x270C，索引是國號，世界篇（DS:0x1F9A≠0）加 14（0xA8B9 ✅ code）；朝鮮半島、日本、ビルマ、エジプト、イベリア等的圖也和國相符 ✅ cross。
  - 之後的 160×112 解不出來，最後 33 KB（0x68A4A 起）不是這個格式 ❌。
- `OPENGRP.DAT`（352×176 起）、`GRPDATA.DAT`、`KGRP.DAT`、`SGRP.DAT`、`KPAT.DAT`、`HEXKG.DAT`、`HEXSG.DAT` 的格式都沒解。❌

## 進度

| 項目 | 狀態 | 證據 | 說明 |
|---|---|---|---|
| 國 33（蒙古篇 14）的名稱、相鄰、數值 | ✅ | code+cross | 見「國」；+0x2A bit 4–7 ❌ |
| 勢力的名稱、本國、君主、文化圏 | ✅ | cross | 見「勢力」 |
| 大地圖 2 張 × 4 季 | ✅ | code | 沒和截圖比對 |
| 人物 +17 勢力、+18 所在国、+23、+24 | ✅ | code+cross | 見「人物欄位」 |
| 兵種格的對應 | 🟡 | | 照兵種表順序與文化圏推定 |
| 女性 +17–+19 | ❌ | | |
| PACKDATA 的事件、オルド、地域圖 | ✅ | code | 86 張；事件圖名稱【推】 |
| 結局圖 | ❌ | | 見「事件、插圖、道具」 |

## 未解

- 國 +0x2A bit 4–7、+0x2F–+0x30，勢力關係表的意義（開局全 0）。
- 0x1F8B 的「年」、0x238A0 的 288×256 圖。
- 結局圖的色盤（`END.EXE`）、其他圖檔的格式。

## 下一輪候選

- 結局圖：先在 `END.EXE` 找寫 port 0xA8–0xAE 的程式與色表，再用 `san3.world_band` 輸出 23 張。
- 兵種格：追 0x68B6（傳回 +0x16）的呼叫端裡查 DS:0xC098 的地方，把 🟡 改成 code。
- koei-wiki 地點匯出：`countries.csv` 已有名稱、相鄰、`x`／`y`，可以照 `places_export` 的 `kouryuuki-dos` 做法接上。

## 負面結論

- 用信長4 的 `decode_pack`、水滸伝的 `unpack_suikoden_picture` 解 `MAPDATA.DAT`：前者解出來是雜訊、後者越界，因為 `MAPDATA` 在寬高後面多了 8 個色字，是三國志III 的格式；換成 `san3.world_band` 才對。
