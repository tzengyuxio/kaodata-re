# 歐陸戰線（EUROPE, DOS 中文版）頭像相關格式

`dekoei.py export europe-dos` 用到的格式。來源是 `games/archives/dos/歐陸戰線_中文版_europe.rar` 的 `olzx/`，解開放在 `games/europe-dos/`。

## 版本

- 檔案日期 1994-01-18，`MAIN.EXE` 沒有版權年（只有 MS C 1990）。
- 原作 ヨーロッパ戦線：SFC／MD 1993-01-16。英文 DOS 版 Operation Europe: Path to Victory 1939-45 只在北美發行，年份資料矛盾（[Wikipedia](https://en.wikipedia.org/wiki/Operation_Europe:_Path_to_Victory) 1994、[Playnite](https://playnite.gamescrobbler.com/games/operation-europe-path-to-victory-1939-45) 1991）。中文版是否由英文 DOS 版移植，未證實。
- `MAIN.EXE` 沒有壓縮，MZ 檔頭 0x5800，DGROUP 在檔案 0x46B00。「映像」＝扣掉檔頭的位址。

## 頭像：FACE.DAT

- 120 張 × 1920 bytes：64×80 全高，3bpp byte 交錯，byte k＝bit k（`genpei.decode_planar`），沒有壓縮。
- 映像 0xAA10 讀取：seek `face × 0x780`（0xAA8D）。
- 色盤：
  - 映像 0xAE48 `setpal(0, 8, DGROUP 0x56B6)`（檔案 0x4C1B6）；8–15 色是地圖用，依季節從 0x56CE／0x56E6／0x56FE／0x5716 選。
  - 映像 0x23D5 把每色 3 bytes 送到 DAC：R、G、B＝byte1、byte2、byte0，各 `<< 2`。
  - 換算 `(v6 << 2) | (v6 >> 4)`：`#000000 #104192 #D33030 #D371B2 #419241 #71B2B2 #F3C361 #F3F3F3`。
  - 舊 `europe face` 用 `to_3bpp_indexes`（第一個 byte 當 bit 2）配 G、B 對調的色盤，碰巧顏色正確；紅、青兩色和 MAIN.EXE 略有不同。
- 和 `europe-sfc` 的 120 張順序、內容一致。沒有組合臉。

## 人物

- 文字是光榮台灣內碼，不是 Big5。
- 記錄 22 bytes：+0 姓名 8 bytes，+9 國別（1 德、2 義、4 美、8 英、16 法、32 蘇；0xFF 是空位），+10–17 能力，+20 頭像碼＝人物編號，+21 雜項／領袖職位。映像 0xAAC0 以 `[bx+0x14]` 取頭像。
- 指揮官 0–93：`SCEDATA` 7 個劇本，起點 0x1772、間隔 0x1D95，各 40 筆（前 20 軸心、後 20 聯合軍），合起來 0–93 都有。
- 領袖 94–105：`MAIN.EXE` 檔案 0x49898（DGROUP 0x2D98）12 筆，+21 是職位（4 最高統帥、5 參謀總長、6 空軍司令、7 特種兵長官；依字串順序推得）。
- 劇本間寫法不同的 3 人，取出現最多的（同票取先出現）：14 克呂韋爾／克魯韋爾、34 蒂夫／提夫、36 巴特爾／海德（SFC 是ハイテ）。`koei_games.load_europe_dos_names`。
- `id` 從 0 起算，0–99 和 `europe-sfc` 一一對應；100–105（戈林、斯帕茨、諾比科夫、迪克茲、勒考克、梅爾赫夫）SFC 沒有。103–105 的史實人物沒查。
- `nameHistorical` 不填：多是音譯不同（如 60 弗萊舍＝Freyberg）。86 加里寧可能被誤認成 Kalinin，待考。

## 沒有人物使用的頭像

- 106–117 替補指揮官：映像 0xBD9E 建立新指揮官（名字「--------」），頭像範圍表在 DGROUP 0x57BA：軸心 106–111、聯合軍 112–117。
- 118 村姑、119 修女：映像 0x11834、0x114A0 直接 seek，旁邊是對應的字串。

## PC-88 版（`europe-pc88`）

`dekoei.py export europe-pc88` 用到的差異（`build_europe_dos(pc88=True)`）。

- 來源：Neo Kobe 2016-02-25 的 `games/archives/pc88/neo-kobe-2016-02-25/Europe Sensen/` 主組 `[FD]`（Disk A–C）。[Set 1]、[Alt 1] 只有 Disk A 的程式檔不同，頭像和人物檔相同。三片都是 YDOS 3.0，每軌 9 × 512 bytes。
- 版本：Disk A 的 `KOEI.C` 寫「Copyright KOEI 1991.12.5」「Ver. 1.00 rel. 1」，檔案日期多是 1991-12-06。
- `games/europe-pc88/` 放 Disk A 的 `FACE.PIC`、`KOEI.C`（參考用），Disk B 的 `SCEDATA.CIM`、`MAIN.COM`，Disk C 的 `FACE2.PIC`。
- 頭像：`FACE.PIC` 102 張、`FACE2.PIC` 2 張（匯出成 102、103），都是 64×40、每 8 點 B、R、G 3 bytes（`MAIN.COM` 0x1320 依序寫 port 0x5C–0x5E），960 bytes。匯出用 `pc88.brg_pixels`，逐列加倍。
  - 第 0 列與第 39 列全白，是畫框線。
  - 0–99 和 DOS 是同一批人、同樣順序，但 DOS 是重畫的全高圖，沒有一張相同。
  - 100、101 是沒有人物用到的軍官臉，看圖像 DOS 的替補指揮官，分類「替補指揮官」（陣營未確認，不加軸心／聯合軍）。
  - 102、103（`FACE2.PIC`）分類「事件人物」：`SCOM.OVL` 0x16E72 讀 FACE2.PIC 第 0 張、旁邊印「村娘」，0x16A41 讀第 1 張（0x3C0）、印「修道女」（SCOM.OVL 載入位址 = 檔案位移 − 0xC902，0x9503 是字串 `FACE2.PIC`）。對應 DOS 的 118 村姑、119 修女。
- 人物：記錄格式同 DOS（22 bytes，名字 8 bytes，國籍 +9，頭像 +20），名字是半形片假名（轉全形）。`SCEDATA.CIM` 0x229 起 7 個劇本、間隔 0x1D64、各 40 筆；領袖 6 人在 `MAIN.COM` 0x264（頭像 94–99）。DOS 的 100–105（戈林等）PC-88 版沒有（`koei_games.load_europe_pc88_names`）。
  - 共 100 人，id 和名字與 `europe-sfc` 逐筆相同（11 ラフェンシュタイ 是 8 字截斷）。
- 色盤：`MAIN.OVL` 0x555A 在數位模式下把 8 個暫存器設成恆等對應，就是數位 8 色（palette id `pc88`）。

## X68000 版（`europe-x68`）

`dekoei.py export europe-x68` 用 `build_europe_dos(x68=True)`。

- 來源：Internet Archive `europe_sensen_1992_koei_disk_1_x68k`（`games/archives/x68000/ia-softwarelibrary/`，A、B、C 3 片 DIM）。`games/europe-x68/` 放 A 片的 `FACE.DAT`、`SCEDATA`、`MAIN.Z`。
- `MAIN.Z` 沒有壓縮，執行位址＝檔案位址＋0x514DE。
- `FACE.DAT`：前 120 張（230400 bytes）和 DOS 中文版逐 byte 相同，後面 52480 bytes 全是 0。分類照 PC-88：106–117「替補指揮官」，118「事件人物」村娘、119「事件人物」修道女（`MAIN.Z` 有這兩個字串）。
- 色盤：0x55DCC 把 0x9A536（檔案 0x49058）的 8 個長字（X68000 GRB）設到文字色盤 0–7：`#000000 #184A9C #DE3939 #DE7BBD #4A9C4A #7BBDBD #FFCE6B #FFFFFF`，和 DOS 的 VGA 值接近但不同。
- 人物：22 bytes 記錄、半形片假名，格式同 PC-88。`SCEDATA` 的劇本由 0x52930 讀：第 s 個在 0x1518 ＋ s × 0x2E21，長 0x2E21，指揮官 40 筆在劇本 +0x302。領袖 12 人（頭像 94–105，和 DOS 一樣有 100–105）在 `MAIN.Z` 檔案 0x4369C（`koei_games.load_europe_x68_names`）。
  - 這份映像的劇本 1–4（劇本 2–5「北アフリカ」到「ノルマンディー」）的磁區內容是 `MSGRP.DAT` 的資料，FAT 沒有交叉連結（第二份 FAT 是沒維護的舊內容），應該是原片或傾印就壞了。所以只讀得到劇本 0、5、6：58 名指揮官加 12 名領袖，共 70 人，名字和 PC-88 逐筆相同。
  - 只在劇本 1–4 出現的 36 張臉（4–6、8、11–13、15–19、21、23、25、26、50–63、66、67、69–72）沒有人物，分類「劇本資料損壞」、不命名。找到完好的傾印後應重新匯出。

## PC-98 版（`europe-pc98`）

`dekoei.py export europe-pc98` 用 `build_europe_dos(pc98=True)`。來源是 Internet Archive neo-kobe 的 `Europe Sensen [FD]`（`games/archives/pc98/neo-kobe-2017-11-17/Koei/`，3 片），Disk A 的 `FACE.DAT`、`SCEDATA`、`MAIN.EXE` 放在 `games/europe-pc98/`，檔案日期 1992-03-18。

- `FACE.DAT` 和 DOS 版逐 byte 相同（120 張）。
- 色盤：`MAIN.EXE` 檔案 0x4CBAC 的 8 個 word 是色號 0–7 的類比色（4 bit，由高到低 G、R、B），換成 8 bit 是 v × 17。數值和 DOS 版那張表相同，X68000 版只是量化成 5 bit。
- 人物：`SCEDATA` 的排法同 DOS（7 個劇本各 40 筆，22 bytes 一筆），姓名是 Shift-JIS；12 位領袖在 `MAIN.EXE` 檔案 0x4A288（`koei_games.load_europe_x68_names(pc98=True)`）。7 個劇本都讀得到，共 106 人，和 PC-88、X68000 版讀得到的部分完全相同，所以 X68000 版「劇本資料損壞」的 36 張臉在這版都有名字。
- 替補指揮官、村娘、修道女同 X68000 版（`MAIN.EXE` 也有「村娘」「修道女」字串）。
