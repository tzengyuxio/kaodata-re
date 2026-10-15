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
- 「考宗」是孝宗（FC 198），填 `nameHistorical`。
