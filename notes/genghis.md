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
- `nameHistorical`：菲利浦一世→菲利浦二世（FC 是フィリップ2せい）、北鞗政子→北條政子、偪山重忠→畠山重忠（缺字）、斡鄰勒→脫斡鄰勒（少字）、摩柯末→摩訶末、江宗→襄宗（英文版 Chiang Tsung，推斷是西夏襄宗）、貝魯拉拉→貝魯拉拉二世、岐國→岐國公主（少字）、麗崋→麗華（使用者決定，2026-10-17）。
- 未決定、沒填：高麗（英文版 Ghori）、合欽、岐國。

### 能力

- 君主、繼承人：+16 起 6 個 u16，依序是 統率力 判断力 企画力 説得力 体力 武力（DOS 往後 10 bytes，X68000 是大端 long）。+15 是年齢，指蒙古篇 1175 年、世界篇 1205 年時的年齡（部將一覽 0xDDB5 印「+15＋年−1175」）。+28＝0 是一族（DOS +38，X68000 +40）。讀取用 `koei_stats.load_genghis_stats`，`dekoei.py koei-person genghis-pc98`。
- ✅ code：PC-98 `MAIN.EXE` 0x1146D 的君主視窗依 DS:0x6A98 的標籤迴圈 6 次印 +16 起的值；+28＝0 時顯示「この方は%s様の一族ですが…」（0xB1B0）並在視窗畫星形記號。
- 部將：+16 基本能力値、+18 血縁値（DOS +28、X68000 +20）、PC-98 +19 u16 存在（0＝既発掘），是「優秀な人物」一覽的內容（0xDD45）✅ code。升格成繼承人時，6 項能力各是 min(999, 基本能力値 ×（80＋rand(40)）÷100)，即 80–119%（0x8CDC：`rand(n)`＝0x814E 取餘數，`a×b÷100`＝0x7FBB）✅ code；呼叫它的升格流程沒追。子女：+16 基本能力値，+18＝1 是兒子（女兒能力 0、頭像碼 0x8000）🟡，+19 都是 0。女性：+15 性格（1 いつでもＯＫ／0 気分しだい／2 絶対拒否）、+16 所属（FF＝未所属）、+17 回数 ✅ code（0xDC14）。
- ✅ cross：PC-88、PC-98、X68000、中文 DOS、英文 DOS 的 MDATA 35 筆、SDATA 85 筆逐筆相同；年齢和史實生年相符（源頼朝 1147、リチャード1世 1157）。英文版的標籤 Leadership、Judgement、Planning、Persuasive、Physical、Military 和日文版的順序相同。
- 🟡 +28＝1、2（一族以外，背叛判定 0x1036E 不同）的名稱未知。寫入的地方（2026-11-10）：君主即位（0x17EDF）、派將軍統治（0x12C84）一律寫 2；部將升格時，部將 +18 血縁値＋DS:0x1903 大於 7 寫 2，否則 1（0x1770F）✅ code。所以 2 比 1 親近，但畫面上叫什麼沒找到。劇本裡君主都是 2，繼承人裡ムカリ、ジェベ、ヒューバード、北条泰時是 1，ウィリアム、ドゥーカス、北条義時是 2。
- 君主 +31 是統治的國號（0 起算），+32 是統治狀態：0x64 本国、0x65 将軍統治（0x89B9 比對；派將軍時寫 0x65、+31＝國號，0x12C77）✅ code。劇本裡君主 k 統治第 k 國、+32 都是 100；テムジン／ジンギスカン 存的是 100／400，開局時重新分配（「次に１００ポイントを各能力に振り分けます」）。沒有技能、相性、寿命。

## PC-88 版（`genghis-pc88`）

`dekoei.py export genghis-pc88` 用到的差異（`build_genghis_dos(pc88=True)`）。來源是 Neo Kobe 2016-02-25 的 `~/game-library/_original/pc88/neo-kobe-2016-02-25/Aoki Ookami to Shiroki Mejika - Genghis Khan/Aoki Ookami to Shiroki Mejika - Genghis Khan [FD].7z`。附帶的說明檔寫的是「with サウンドウェア」版，V2 模式，1988-01。`[Set 1]` 的資料檔相同。

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

`dekoei.py export genghis-pc98` 用到的差異（`build_genghis_dos(pc98=True)`）。這是 1987-12 的首發版，kaodata 以它為主、PC-88 改成標籤（2026-10-16）。來源是 Neo Kobe 2017-11-17 的 `~/game-library/_original/pc98/neo-kobe-2017-11-17/Koei/Aoki Ookami to Shiroki Mejika - Genghis Khan/`（`[FD]` 三片 HDM，`[Set 1]` 兩片的資料檔相同）。`games/genghis-pc98/` 放 B 片的 `KAO.DAT`、`MONTER.DAT`、`MDATA.CIM`、`SDATA.CIM`，以及參考用的 A 片 `MAIN.EXE`（1988-03-31）。

- `KAO.DAT`、`MONTER.DAT` 和 PC-88、DOS 版逐 byte 相同。
- 色盤是數位 8 色：`MAIN.EXE` 0x583F 起把 4 bytes 的數位色盤寫到 port 0xA8–0xAE，預設表（0x23E8A 的 37 15 26 04）是標準排列，所以用 `SAN2_JP_PALETTE`（palette id `pc98`）。
- 人物：`MDATA.CIM`／`SDATA.CIM` 是 7559 bytes（PC-88 是 7168），記錄內容同 PC-88，只是位置不同，子女與部將在頭像碼前多 1 byte（`load_genghis_pc88_people(pc98=True)`）：
  - 君主 0x1D4，27 × 33 bytes，+29
  - 繼承人 0x550，4 組 × 5 × 31 bytes，+29
  - 部將 0x7F3，26 × 23 bytes，+21
  - 子女 0xA4A，4 組 × 5 × 22 bytes（每組 110），+20
  - 女性 0x19C6，40 × 24 bytes，+18／+20／+22
- 讀出的姓名與頭像碼和 PC-88 逐筆相同，匯出結果除了 id、平台與色盤 id 以外都和 `genghis-pc88` 相同。
- `nameZh`：取 `genghis-dos` 同 id 的中文名（`genghis_name_zh`，讀 `games/genghis-pc98/dos/` 的 DOS 版 `MDATA.CIM`／`SDATA.CIM`），中文版寫錯的幾筆（`GENGHIS_DOS_NAME_HISTORICAL`：北鞗政子、偪山重忠、菲利浦一世、斡鄰勒、江宗、摩柯末、貝魯拉拉、岐國、麗崋）改用正確寫法（使用者決定，2026-10-17）。X68000 版也一樣。

## X68000 版（`genghis-x68`）

`dekoei.py export genghis-x68` 用到的格式（`build_genghis_x68`）。來源是 Internet Archive 的 `~/game-library/_original/x68/ia-softwarelibrary/aoki_ookami_to_shiroki_meshika_x68k/`（3 片 XDF，標題寫 1989），`games/genghis-x68/` 放 Disk 1 的 `JINMAIN.Z`、`KAO.PAK`，Disk 2 的 `MON.PIC`、`MDATA.DAT`，Disk 3 的 `SDATA.DAT`。檔案日期 1989-01-20～1989-03-07。

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
- 姓名、人數、頭像號都和 PC-88 逐筆相同。只有組合臉碼換成 X68 的新編碼，另外ゴータマ的笑、哭兩張臉和 PC-88 對調。共 152 人（91 組合臉、61 頭像），`id` 和 `genghis-dos` 一致，`nameHistorical` 同 PC-88（江宗→襄宗），`nameZh` 同 PC-98 版（`games/genghis-x68/dos/`）。

## 發行年份

- 英文 DOS 版 1989（部分資料 1990）；原版 PC-98 1987-12；PC-88 1988-01（說明檔，with サウンドウェア版）；X68000 1989（IA 標題；檔案日期到 1989-03-07）；中文版 MAIN.EXE 1993-04。

## PC-98 的磁片與 `genghis-extras`

`dekoei.py genghis-extras --game-dir ../games/genghis-pc98 --out ../games/genghis-pc98/extract`（`dekoei/genghis_extras.py`，2026-11-10）輸出 `countries.csv`、`hexmaps.csv`、`persons.csv`、`map/`、`pictures/`。

- 三片 HDM（`[FD]` 的 Disk A、B、C）是標準 FAT12（1024 bytes／sector），每片解開的原樣放在 `games/archives/pc98/disks/genghis-pc98/A`、`B`、`C/`；`games/genghis-pc98/` 另外放了 A 片的 `MMAP.PAK`、`SMAP.PAK`、`OPEN.DAT`，B 片的 `MHEXMAP.DAT`、`SHEXMAP.DAT`、`PACDATA.DAT`、`PICDATA.DAT`、`ENDDATA.DAT`、`ANIME.DAT`、`HANIME.DAT`。C 片只有 `SAVEDATA`（存檔，沒解）。
- 和中文 DOS 版 byte 相同的：`MMAP.PAK`、`SMAP.PAK`、`OPEN.DAT`、`MHEXMAP.DAT`、`SHEXMAP.DAT`、`PICDATA.DAT`、`ENDDATA.DAT`、`ANIME.DAT`、`HANIME.DAT`、`KAO.DAT`、`MONTER.DAT`；不同的是 `MAIN.EXE`、`LOGO.COM`、`MDATA.CIM`、`SDATA.CIM`、`PACDATA.DAT`（DOS 51712，PC-98 58368）。
- 位址：本節的 MAIN.EXE 位址和上文一樣是**檔案位置**（load image＋0x5200）。DGROUP 是 0x1CE9（起始碼 0x60AD `mov di,0x1ce9`），`DS:xxxx` 指 MAIN.EXE 的資料段。`MDATA.CIM`／`SDATA.CIM` 整個讀到 DS:0x36，所以 DS 位址＝檔案位置＋0x36。

## 國與大地圖

蒙古篇 14 國（部族）、世界篇 27 國。國數在 `*DATA.CIM` 0x1CF（DS:0x205），0x1D0 u16 是年（1174／1205），0x1D2 是 3。中文 DOS 版的國資料和 PC-98 byte 相同（國表在 DOS 0x10C6、相鄰表在 0x1988；國名 25 bytes 一筆，從 0x3A 起，國數在 0x2DD）✅ cross。

`*DATA.CIM` 的開頭：

| 位置 | 內容 | 證據 |
|---|---|---|
| 0x04 | 27 個 u16：每國的風景圖號（0x8000＋`PICDATA.DAT` 的 512-byte block），國資訊視窗用（0x993F 取 DS:0x3A＋國號×2） | ✅ code |
| 0x3A | 27 個國名，各 15 bytes（Shift-JIS） | ✅ code（0xE02C 一覽表印的國名） |
| 0xC02 | 國記錄，27 × 0x53 bytes（DS:0xC38，0x86E9 算位址） | ✅ code |
| 0x14C4 | 相鄰表，27 × 14 bytes（DS:0x14FA） | ✅ code＋cross |

國記錄（0x53 bytes）：

| 位置 | 欄位 | 證據 |
|---|---|---|
| +0x00 | 10 個部隊，各 2 bytes：兵種（0 騎馬、1 歩兵、2 弓矢，FF＝無）、兵士配分的 ％（劇本裡都是 20，合計 100） | 🟡 code（「兵士配分表」的字串與 0xE1E9 數非空部隊；位元組與畫面沒有逐一對照） |
| +0x14 | 武装度 | ✅ code（0x116C9 起的國データ視窗、0xE21C 的一覽表二） |
| +0x16 | 訓練度 | ✅ code |
| +0x18 | 兵士（住民配分的兵士） | ✅ code |
| +0x1A | 経済力 | ✅ code |
| +0x1C | 町造り | ✅ code |
| +0x1E | 城防御度 | ✅ code |
| +0x20 | 城造り | ✅ code |
| +0x22–0x36 | 11 個 u16：毛皮 絹 宝石 貴金属 医薬品 木工品 陶磁器 ガラス 織物 香料 食糧（品名表 DS:0x4382）；+0x36 食糧也就是一覽表的「食」 | ✅ code（0xE3DC 的一覽表三） |
| +0x3A | 特産品作り | ✅ code |
| +0x3E | 食料作り | ✅ code |
| +0x40 | 金 | ✅ code |
| +0x42 | モラル（住民モラル） | ✅ code |
| +0x44 | 税 | ✅ code |
| +0x48 | 一覽表二的「比」（劇本裡 30，日本 35） | 🟡 code（印出的位置確定，意思沒確定；推測是兵士配分表的移動比） |
| +0x49 | 一覽表二的「民」（15–60） | 🟡 code（同上，意思沒確定） |
| +0x38、+0x3C、+0x46、+0x4A–0x50 | 劇本裡都是 0 | ❌ |
| +0x51 | 統治者的記錄位址（DS 位址；君主 k＝0x20A＋33k） | ✅ code（0x86F6） |

- 一覽表一的「人」不是欄位，是 兵士＋町造り＋城造り＋特産品作り＋食料作り（0x8A86），劇本裡都是 100 ✅ code。也就是說住民分成這五種的配分。
- 劇本裡第 k 國都由君主 k 統治，統治狀態是本国。

相鄰表（14 bytes 一筆）：

| 位置 | 欄位 | 證據 |
|---|---|---|
| +0、+1 | 國號在地圖上的文字座標（欄、列，×8＝像素） | 🟡 code |
| +2、+4 | u16 x、y，畫面像素（640×200，大地圖畫在 x＝256） | 🟡（畫成 `map/*-labelled.png`，每個號碼都落在對應的區域裡【推】） |
| +6 | 特産品（品名表的編號；國データ視窗的「特産品」，0x8A9D） | ✅ code |
| +7–13 | 相鄰國號，FF 補滿 | ✅ cross：和 `*HEXMAP.DAT` 每國戰場圖的入口區完全一致（41 國都對上） |

- 世界篇的 27 國依序是モンゴル帝国、金、クマン族同盟、キエフ公国、ドイツ騎士団領、ポーランド、イングランド、フランス、神聖ローマ帝国、ハンガリー、ビザンツ帝国、セルジュク連邦、ホラズム、西遼、ウイグル、西夏、吐蕃、高麗、日本国、ムワッヒド朝、アイユーブ朝、カリフ領、インド諸王朝、ゴール朝、パガン朝、南宋、大越大理連合；中文版的寫法在 `countries.csv` 的 `nameZh`（中文版把ムワッヒド朝寫成「倭馬亞王朝」，照錄）。
- **大地圖** `MMAP.PAK`（蒙古篇）／`SMAP.PAK`（世界篇）：384×160（200 線），讀到 VRAM 0xBC00:0（0x1FDDE，國數＝27 讀 SMAP），再由 0x989F 解到畫面 x＝256。格式見下面的 PAK。輸出 `map/MMAP.png`、`SMAP.png`（縱向放大 2 倍）與標上國號的 `*-labelled.png` ✅ code（兩張都剛好用完整個檔案）。沒有季節之分。
- **戰場圖** `MHEXMAP.DAT`（14 張）／`SHEXMAP.DAT`（27 張）：每國一張，320 bytes：前 160 bytes 是 16 × 10 格的地形，後 160 bytes 是入口區（攻進來的國號，FF＝無）。由 0x1D192 依國號讀到 DS:0x95B8、0x9668；0x1D208 取地形時去掉 bit 7。輸出成 `hexmaps.csv`（一格一行）。
  - 地形 7 不能進入（0x1CCBC 等十幾處檢查）✅ code。
  - 6、5 每張各一格：開戰時把 6 的位置記到 DS:0x9B04、5 的位置記到 DS:0x9708（0x1C5D7），6 也擋其他部隊（0x1CCC1），推測 6 是城、5 是守方本隊的位置 🟡 code。
  - 0–4 的名稱、bit 7 的意思沒找到 ❌。DS:0x7D68 有一張依地形取值的表 `08 06 03 04 05 04 05 FF`（0x1D23C），推測是移動力消耗 🟡。
  - 格子的排法（哪幾行錯開半格）沒確認，所以只輸出 CSV，沒畫圖。

### PAK 圖片格式

`MMAP.PAK`、`SMAP.PAK`，以及 `PACDATA.DAT`、`PICDATA.DAT`、`ENDDATA.DAT`、`OPEN.DAT` 裡的每一張都是同一種格式（解碼 0x5908）✅ code：

- u16 寬、u16 高，接著逐列、逐 8 點一欄，每欄依 B、R、G 三個 plane 各一 byte（色號＝B＋2R＋4G，數位 8 色）。
- 前兩列是原樣的 byte。之後讀到 0x96 時再讀 n：n＝1 是字面的 0x96；否則從兩列上面同一欄、同一 plane 抄 n 個（0＝256），計數依（欄、plane）的順序延續，可以跨列。
- 合集檔裡每張圖從 512-byte 的 block 開始，圖號＝block 號；`PICDATA.DAT` 的圖號另加 0x8000（0x96FA 依圖號選 `PACDATA`／`PICDATA` 再乘 512 seek）。

**koei-wiki 匯出**：`dekoei.py places-export genghis-pc98 --game-dir ../games/genghis-pc98 --out ../export/koei-wiki/places`（`genghis_extras.places`，koei-places/1，2026-11-10）。41 國，`level` 是「國」；世界篇用遊戲的國號 1–27，蒙古篇是 100＋國號（101–114），兩篇是不同的地圖與國。`name` 是 DOS 中文版的寫法，`nameJa` 是 PC-98 版的；ムワッヒド朝在中文版寫成「倭馬亞王朝」（另一個王朝），照遊戲原文，寫在 `notes`。大地圖 `world/mongol.png`、`world/world.png`（384×320，200 線的圖縱向放大兩倍），`pos` 是國號標籤的中心。戰場地形只有 CSV，沒有給圖。檢查 353 項、0 不符。

人物：`dekoei.py persons-export genghis-pc98 --game-dir ../games/genghis-pc98 --out ../export/koei-wiki/persons --places ../export/koei-wiki/places`（`wiki_genghis.py`，koei-persons/1，2026-11-11），讀 `extract/persons.csv`，152 人。檢查 314 項、0 不符；koei-wiki `verify_persons.py` 1291 項、0 不符。

- `id` 是 kaodata 的流水號：兩篇同名（NFKC、去掉姓名間的空白）是同一人，所以跨篇用名字對。テムジン（蒙古篇）和ジンギスカン（世界篇）是同一人，但名字不同，kaodata 分成兩個 id，`notes` 有寫。
- `name` 是 DOS 中文版的寫法，和 kaodata `nameHistorical` 不同的在 `notes` 寫史書寫法；`nameJa` 是 PC-98 的。
- `scenarios`：`scenario` 是「蒙古篇」「世界篇」，沒有年（年齡是 1175／1205 年的值，劇本檔的年是 1174／1205，沒確認哪個是開始年）。`status` 照表名寫 君主、繼承人、子女、部將（部將的 `存在` 都是 1，寫「部將（未發掘）」）、女性；遊戲裡的稱呼沒找。君主有 `location`（100＋國號或國號，同地點匯出）。
- 繼承人、子女的 `lord`、子女的 `father`、君主的 `children` 照「哪一組屬於哪位君主」的推定（🟡，見「人物欄位」），標 `uncertain: relations`。`clan` 是君主和 +28＝0（一族）的繼承人共用君主的 id。
- `stats` 是君主、繼承人的 6 項能力；`more` 放年齢、部將與子女的基本能力値、部將的血縁値；兩篇都有的人取蒙古篇的值，各篇年齢寫在 `notes`（兩篇的年齡差不一定是 30，沒有換算生年）。`hidden.+28` 是一族記號。
- 亂數產生的名字：劇本資料裡沒有。女性 40 人兩篇相同、名字固定；遊戲中出生的子女、升格的部將不在劇本資料裡，所以不在匯出裡。

## 人物欄位

`persons.csv`：兩篇的君主、繼承人、部將、子女、女性，共 200 筆（同一人在兩篇各一筆），欄位見上面「能力」與本節。中文名取 `dos/` 的中文版同位置記錄。

- 繼承人與子女分 4 組，各 5 個位置。每組屬於哪位君主由 DS:0x1878 的 4 個國號決定（0x872B 依統治者的 +31 找組）；劇本裡這 4 個 byte 都是 FF（開局才填）。從名字看，蒙古篇只有第 0 組（テムジン），世界篇是 0 ジンギスカン、1 リチャード１世、2 アレクシオス、3 源 頼朝，正好是 4 個可選的君主 🟡（`persons.csv` 的 `family` 欄照這個填）。
- 部將沒有所在國：是「優秀な人物」的候補名單，+19 存在＝1 表示還沒被找到。
- 女性 +16 所属在劇本裡都是 FF。

## 事件、插圖、道具

`pictures/` 共 103 張（PAK 格式，縱向放大 2 倍；檔名 `<檔名>_<block 號>.png`）✅ code：

| 檔案 | 張數 | 內容【推】（看圖） |
|---|--:|---|
| `PACDATA.DAT` | 46 | 80×32 的指令、事件小圖 43 張（群眾、宴會、間諜、書信、武將…），開場的「蒼き狼…元朝秘史」引文（512×120）、標題字（640×32）、版權（208×28） |
| `PICDATA.DAT` | 46 | 災害 3 張（128×80：蝗害？、洪水、雷）、寝室 2 張（160×64），以及 41 張各國風景（192×40）。風景依 `*DATA.CIM` 0x04 的圖號對到國 ✅ code，`countries.csv` 的 `picture` 欄 |
| `ENDDATA.DAT` | 9 | 結局 320×128 5 張、640×120 4 張 |
| `OPEN.DAT` | 2 | 開場 424×8、136×168 |

- 沒有道具；特産品（11 種）只有名稱與數量。
- `ANIME.DAT`（101888 bytes）、`HANIME.DAT`（8400）不是 PAK 格式，只在 `ANIME.DAT` 偶然認出 2 張 ❌。事件文字在 `MAIN.EXE` 裡（Shift-JIS 明文，約 3000 筆），沒有整理。

## 進度

| 項目 | 狀態 | 證據 | 說明 |
|------|------|------|------|
| 頭像、組合臉 | ✅ | code+emu | 見「頭像」「組合臉」；kaodata 匯出 |
| 君主、繼承人能力 | ✅ | code+cross | 見「能力」 |
| 國表（14＋27 國）的數值欄位 | ✅ | code+cross | 國記錄 22 個欄位；+0x48、+0x49 只知道印在哪 |
| 相鄰 | ✅ | code+cross | 相鄰表與戰場圖入口區一致 |
| 大地圖 | ✅ | code | `map/` |
| 戰場圖地形 | 🟡 | code | 7＝不能進入；0–6 的名稱沒解 |
| 圖片（PACDATA、PICDATA、ENDDATA、OPEN） | ✅ | code | 103 張；各張用途是看圖推的 |
| 繼承人／子女的組對應 | 🟡 | | 依名字推 |
| `ANIME.DAT`、`HANIME.DAT` | ❌ | | 格式不同 |
| 存檔 `SAVEDATA` | ❌ | | 沒看 |

## 未解

- 一族區分 +28＝1／2 的名稱 — 寫入條件已知（「能力」）。
- 戰場地形 0–6 的名稱、bit 7 — 讀取程式 0x1D208；畫面上沒有地形名稱字串。
- 國記錄 +0x48「比」、+0x49「民」的意思 — 一覽表二印出（0xE21C）。
- `ANIME.DAT`、`HANIME.DAT` 的格式 — 檔案 handle 在 DS:0x970A，讀取在 0x997B 附近。

## 下一輪候選

- 戰場圖畫成圖：前置是確認格子排法與地形圖塊；做法：找畫戰場的程式（0x1D192 之後），或在 DOSBox-X 截一張戰場畫面比對。
- 繼承人組對應：做法：追開局寫 DS:0x1878 的程式。
- 地形名稱：做法：追 DS:0x7D68 表的使用處，或從說明書（reference）取得名稱後和 code 對照。

## 負面結論

- 用地名字串找地形名稱：`MAIN.EXE` 裡沒有「草原」「森」「山」之類的字串，地形名只能從程式行為或說明書推。
- 3 片磁片用 7-Zip 開不起來：HDM 沒有 7-Zip 認得的格式；照 1024 bytes／sector 的 FAT12 直接讀（開機區沒有 BPB，用 PC-98 2HD 的預設：保留 1、FAT 2×2、根目錄 192 筆）。
