# 蒼狼與白鹿・成吉思汗（GENGHIS, DOS 中文版）頭像相關格式

`dekoei.py export genghis-dos` 用到的格式。來源是 `games/archives/dos/成吉思汗_中文版_khan-c.zip`，解開放在 `games/genghis-dos/`。

## 版本

- 英文 DOS 版 Genghis Khan（1989，部分資料寫 1990）的移植：`KAO.DAT`、`MONTER.DAT`、`PICDATA.DAT` 和英文版（`games/archives/dos/成吉思汗_英文版_genghis-khan.zip`）逐 byte 相同；`MDATA.CIM`／`SDATA.CIM` 換成中文名字（1992-11）。原作是 1987-12 的 PC-98 版。
- 中文版 `MAIN.EXE`（1993-04-26）是 EXEPACK，DGROUP 段值 0x1DED（MZ 檔頭 0x4290）。下文是解壓後的映像位址。

## 頭像：KAO.DAT

- 83 張 × 960 bytes，64×40 半高、3bpp，格式同三國志II DOS（`san2_pixels`），0x5CAA 讀取。頭像碼就是索引。
- 色盤：DGROUP 0x242F 以 int 10h AX=1002 載入，結果就是 `SAN2_PALETTE`（EGA）。

## 組合臉：MONTER.DAT（0x5B57／0x5C68）

- 頭像碼 bit 15 為 1 時是組合臉：`1 ccc vv TT BB EE NN MM`。
- `vv` 是頭型，每型 0x15C0 bytes，各 4 筆：上（19 列，offset 0）、下（21 列，0x720）、眼（7 列，0xF00）、鼻（6 列，0x11A0）、口（5 列，0x13E0）。都是半高、每列 24 bytes。
- 組法（臉緩衝區 DS:0x80B6）：
  1. 上（`TT`）放在第 0–18 列、下（`BB`）放在第 19–39 列。
  2. 0x955 把上下兩半中只有 plane 0 的像素（`to_3bpp_indexes` 的色號 4）換成 `ccc`（bit k → plane k）。
  3. 眼（`EE`）、鼻（`NN`）、口（`MM`）先拼進 432 bytes 的暫存區（第 12–18、19–24、25–29 列），0x5C94 再整塊以 XOR 疊到臉上。
- XOR 的三個部件彼此不重疊，但會和上下重疊，所以不能用一般覆蓋表示。匯出用規格的 `blend: "xor"`：眼鼻口是不透明的部件，色號 0＝不變。各 plane 分別 XOR 等於色號 XOR，換色又在 XOR 之前，所以把 `ccc` 烘進上下兩半就是精確的。
- 匯出成 32 個 variant（`ccc × 4 + vv`，id `vv-ccc`），code 用 bitfield，`$variant` 取 bit 15–10、base 32。用 game 的組法逐像素比對過 91 張組合臉，全部一致。

## 人物：MDATA.CIM／SDATA.CIM

- 蒙古篇（M）、世界篇（S）各一份，記錄首 byte 為 0 是空位，姓名 20 bytes 光榮台灣內碼（`koei_games.load_genghis_dos_people`）：
  - 君主 0x2E2，27 × 43 bytes，頭像碼 +0x27
  - 繼承人 0x76C，4 組 × 5 × 41 bytes（每組 205），+0x27
  - 部將 0xAEB，26 × 33 bytes，+0x1F
  - 子女 0xE46，4 組 × 5 × 32 bytes（每組 160），+0x1E
  - 女性 0x1E8A，40 × 34 bytes，+0x1C／+0x1E／+0x20 是平常／笑／哭三個表情（兩篇相同）
- `id` 依 `genghis-fc` 的順序：蒙古篇君主、繼承人、子女，世界篇君主、繼承人、子女，女性；接著是 FC 沒有的部將（蒙古篇再世界篇）。同名只收一次（兩篇的頭像碼一致）。0–114 和 FC 相同，115–151 是 DOS 才有的部將。共 152 人（91 組合臉、61 頭像），沒有未使用的頭像。
- `nameHistorical`：菲利浦一世→菲利浦二世（FC 是フィリップ2せい）、北鞗政子→北條政子、偪山重忠→畠山重忠（缺字）、斡鄰勒→脫斡鄰勒（少字）、摩柯末→摩訶末、江宗→襄宗（英文版 Chiang Tsung，推斷是西夏襄宗）。
- 未決定、沒填：高麗（英文版 Ghori）、合欽、岐國。

## PC-88 版（`genghis-pc88`）

`dekoei.py export genghis-pc88` 用到的差異（`build_genghis_dos(pc88=True)`）。來源是 Neo Kobe 2016-02-25 的 `games/archives/pc88/neo-kobe-2016-02-25/Aoki Ookami to Shiroki Mejika - Genghis Khan/Aoki Ookami to Shiroki Mejika - Genghis Khan [FD].7z`。附帶的說明檔寫的是「with サウンドウェア」版，V2 模式，1988-01。`[Set 1]` 的資料檔相同。

- 磁碟：D88 每軌 9 × 512 bytes。Disk A 是 YDOS 3.0，B、C 是 FAT12。`games/genghis-pc88/` 放的是 B 片的 `KAO.DAT`、`MONTER.DAT`、`MDATA.CIM`，C 片的 `SDATA.CIM`，以及參考用的 A 片 `MAIN.COM`。B、C 兩片的 `KAO.DAT`、`MONTER.DAT` 相同。
- 版本：B、C 片只有 `Copyright (C) 1987 by KOEI`，沒有版號字串。
- `KAO.DAT`（83 × 960）和 `MONTER.DAT` 都和 DOS 版**逐 byte 相同**，DOS 版直接沿用了 PC-88 的 200 線圖。頭像、組合臉的 variant 與 code 照 DOS 版匯出，只換成數位 8 色（`SAN2_JP_PALETTE`，palette id `pc88`）。膚色重著色（碼的 bit 12–14）沿用 DOS 版的結論，沒有在 PC-88 程式裡另外追。
- 人物：記錄比 DOS 版短，姓名在 +0（Shift-JIS，大多是片假名，NFKC 正規化，去掉姓名間的空白），後面接頭像碼（`koei_games.load_genghis_pc88_people`）：
  - 君主 0x1D1，27 × 33 bytes，頭像碼 +29
  - 繼承人 0x54C，4 組 × 5 × 31 bytes（每組 155），+29
  - 部將 0x7ED，26 × 22 bytes，+20
  - 子女 0xA29，4 組 × 5 × 21 bytes（每組 105），+19
  - 女性 0x1806，40 × 24 bytes，+18／+20／+22
- 人數、頭像碼和 DOS 版逐筆相同，排序與去重規則也相同：152 人，`id` 和 `genghis-dos` 一致。
- `nameHistorical`：只填江宗→襄宗。DOS 版的其他幾筆在 PC-88 版是對的（フィリップ2世、北条政子、畠山重忠、ムハンマド）。トオリオルカン是音譯的寫法不同，不填。

## PC-98 版（`genghis-pc98`）

`dekoei.py export genghis-pc98` 用到的差異（`build_genghis_dos(pc98=True)`）。這是 1987-12 的首發版，kaodata 以它為主、PC-88 改成標籤（2026-10-16）。來源是 Neo Kobe 2017-11-17 的 `games/archives/pc98/neo-kobe-2017-11-17/Koei/Aoki Ookami to Shiroki Mejika - Genghis Khan/`（`[FD]` 三片 HDM，`[Set 1]` 兩片的資料檔相同）。`games/genghis-pc98/` 放 B 片的 `KAO.DAT`、`MONTER.DAT`、`MDATA.CIM`、`SDATA.CIM`，以及參考用的 A 片 `MAIN.EXE`（1988-03-31）。

- `KAO.DAT`、`MONTER.DAT` 和 PC-88、DOS 版逐 byte 相同。
- 色盤是數位 8 色：`MAIN.EXE` 0x583F 起把 4 bytes 的數位色盤寫到 port 0xA8–0xAE，預設表（0x23E8A 的 37 15 26 04）是標準排列，所以用 `SAN2_JP_PALETTE`（palette id `pc98`）。
- 人物：`MDATA.CIM`／`SDATA.CIM` 是 7559 bytes（PC-88 是 7168），記錄內容同 PC-88，只是位置不同，子女與部將在頭像碼前多 1 byte（`load_genghis_pc88_people(pc98=True)`）：
  - 君主 0x1D4，27 × 33 bytes，+29
  - 繼承人 0x550，4 組 × 5 × 31 bytes，+29
  - 部將 0x7F3，26 × 23 bytes，+21
  - 子女 0xA4A，4 組 × 5 × 22 bytes（每組 110），+20
  - 女性 0x19C6，40 × 24 bytes，+18／+20／+22
- 讀出的姓名與頭像碼和 PC-88 逐筆相同，匯出結果除了 id、平台與色盤 id 以外都和 `genghis-pc88` 相同。

## X68000 版（`genghis-x68`）

`dekoei.py export genghis-x68` 用到的格式（`build_genghis_x68`）。來源是 Internet Archive 的 `games/archives/x68000/ia-softwarelibrary/aoki_ookami_to_shiroki_meshika_x68k/`（3 片 XDF，標題寫 1989），`games/genghis-x68/` 放 Disk 1 的 `JINMAIN.Z`、`KAO.PAK`，Disk 2 的 `MON.PIC`、`MDATA.DAT`，Disk 3 的 `SDATA.DAT`。檔案日期 1989-01-20～1989-03-07。

- `JINMAIN.Z` 沒有壓縮，執行位址＝檔案位置＋0x514DE。下文是執行位址。
- 頭像 `KAO.PAK`：重畫的 83 張 48×80、每像素 1 byte（256 色）。偏移表在 0x5F640（84 個 long，最後一個是檔案大小）。第 0 列原樣，之後 `FE n` 是從上一列抄 n 個像素，`FE 01` 是字面的 FE（0x9452A，`genghis_x68_face`）。頭像號和 PC-88 相同（0–20 君主、21–82 女性），全部有人用。
- 組合臉 `MON.PIC`（0x8345C）：碼 `1 00 ttt TT BB EE NN MM`，`ttt` 是 8 種類型（bit 13–14 一律是 0），各 4 筆：
  - 上：offset 0，41 列，放第 0 列
  - 下：0xF600，39 列，放第 41 列
  - 眼：0x1E000，13 列，第 29 列
  - 鼻：0x22E00，17 列，第 38 列
  - 口：0x29400，16 列，第 50 列
  - 每筆是 `列數 × 48` bytes，第 t 型第 i 筆在 `offset + (t × 4 + i) × 大小`。上下直接蓋上，眼鼻口以 OR 疊上（`blend: "or"`）。用遊戲的組法逐像素比對過 8 × 4⁵ 種組合，全部一致。
- 色盤：0x56442 的 256 個 long，低 16 bit 是 X68000 調色盤字（G、R、B 各 5 bit＋亮度 bit）。色號 255（白）有用到，但在 kaodata 是透明，所以移到沒人用的 247。眼鼻口裡的 255 只會和 0 做 OR，OR 的結果不變。
- 人物：`MDATA.DAT`／`SDATA.DAT` 的欄位同 PC-88，但數值擴成 68000 的 long。姓名 15 bytes（Shift-JIS），頭像碼是大端序（`load_genghis_pc88_people(x68=True)`）：
  - 君主 0x210，27 × 48 bytes，頭像碼 +44
  - 繼承人 0x720，4 組 × 5 × 46 bytes（每組 230），+44
  - 部將 0xB04，26 × 30 bytes，+28
  - 子女 0xE10，4 組 × 5 × 28 bytes（每組 140），+26
  - 女性 0x279C，40 × 30 bytes，+20／+24／+28（long 的低 word）
- 姓名、人數、頭像號都和 PC-88 逐筆相同。只有組合臉碼換成 X68 的新編碼，另外ゴータマ的笑、哭兩張臉和 PC-88 對調。共 152 人（91 組合臉、61 頭像），`id` 和 `genghis-dos` 一致，`nameHistorical` 同 PC-88（江宗→襄宗）。

## 發行年份

- 英文 DOS 版 1989（部分資料 1990）；原版 PC-98 1987-12；PC-88 1988-01（說明檔，with サウンドウェア版）；X68000 1989（IA 標題；檔案日期到 1989-03-07）；中文版 MAIN.EXE 1993-04。
