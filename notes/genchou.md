# 蒼き狼と白き牝鹿・元朝秘史（GENCHOU, PC-88）頭像相關格式

`dekoei.py export genchou-pc88` 用到的格式（`build_genchou_pc88`）。

## 版本與磁碟

- 來源：Neo Kobe 2016-02-25 的 `games/archives/pc88/neo-kobe-2016-02-25/Aoki Ookami to Shiroki Mejika - Genchou Hishi/` 唯一一組 `[FD]`（Disk A–D 與 Save disk；Alt 1／2 只有 Save disk 不同）。
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

## X68000 版（`genchou-x68`）

`dekoei.py export genchou-x68` 用 `build_genchou_pc88(x68=True)`。

- 來源：Internet Archive `aoki-ookami-to-shiroki-meshika-genchou-hishi-1993-koei-disk-1-of-3`（`games/archives/x68000/ia-softwarelibrary/`，3 片），發行 1993-02-26（ja.wikipedia）。沒有版本字串；`MAIN.Z` 與劇本檔的日期是 1993-02-10，`MAIN.Z` 有「X68000 CONVERSION STAFF … T.FUJINUMA 1992,1993」。`games/genchou-x68/` 放 Disk 1 的 `KAODATA.DAT`、參考用的 `MAIN.Z`，以及 Disk 3 的 `GENDATA1–4.DAT`、`USDATA1–4.DAT`。
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

`dekoei.py export genchou-pc98` 用 `build_genchou_pc88(pc98=True)`。來源是 Internet Archive neo-kobe 的 `Genchou Hishi [FD]`（`games/archives/pc98/neo-kobe-2017-11-17/Koei/`），Disk A 的 `KAODATA.DAT`、`MAIN.EXE`、`VERSION` 與 Disk C 的 `GENDATA1–4.DAT`、`USDATA1–4.DAT` 放在 `games/genchou-pc98/`。`VERSION` 寫「ＰＣ９８０１ＶＭ『元朝秘史』Type B Ver 1.0 Rel 1」，檔案日期 1992-09-16。

- `KAODATA.DAT` 和 X68000 版逐 byte 相同（全高、男性 64 張），所以頭像與組合臉和 `genchou-x68` 相同。
- 色盤：`MAIN.EXE` 檔案 0x3E93A 起是色號 0–7 的類比色，每色 3 bytes（B、R、G，4 bit），換成 8 bit 是 v × 17。設計和 X68000 版相同，只是量化不同（例：`#004488`，X68000 是 `#004a8c`）。
- 人物：`GENDATA` 是 PC-88 的排法往後挪 1 byte（檔頭是 `FF 00`，男性從 2 起、女性從 0x1A26 起），`USDATA` 同 PC-88，但檔尾接著磁碟殘留的垃圾，所以只讀完整的 351 bytes 區塊。頭像碼是 X68000 版的碼（男性 40–63 是獨立頭像）。445 筆記錄的劇本、姓名、頭像碼和 X68000 版完全相同，包括 PC-88 的兩個錯字已改正（畠山重忠、孝宗）。
