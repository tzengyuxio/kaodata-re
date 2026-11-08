# 信長の野望・全国版（NOBU2, PC-88）頭像相關格式

`dekoei.py export nobu2-pc88` 用到的格式。來源是 Neo Kobe 2016-02-25 的 `~/game-library/_original/pc88/neo-kobe-2016-02-25/Nobunaga no Yabou - Zenkoku-ban/Nobunaga no Yabou - Zenkoku-ban [FD].7z` 主檔的 Disk A、B，原樣放在 `games/nobu2-pc88/DISK_A.D88`、`DISK_B.D88`。

## 版本

- 磁碟上沒有遊戲版號，只有系統的 `YDOS Ver 2.2 (58.5K) 15-Feb-85`。
- FD 主檔、Alt 1–3、Set 1–5 的 Disk B 頭像區（下文三段）和 Disk A `DATA50S.DAT` 的姓名表都相同。ODAMAIN.COM 各組不同，Set 2、3 的 Disk A 目錄讀不出來（拷貝保護或別的格式）。匯出用 FD 主檔。
- 發行年份：PC-8801 版 1986-10（ja.wikipedia〈信長の野望・全国版〉；ファミ通的文章寫 1986-09）。說明書 p.22 MAIN 畫面 ③「大名の顔が表示されます」。

## 磁碟

- 2D D88，沒有拷貝保護磁區，依 (c, h, r) 串成線性映像（`pc88.d88_image`）。
- Disk A 0x4000 是 CP/M 式目錄（`pc88.cpm_files`）：ODAMAIN.COM（載入在 0x100）、ODA.OVL、DATA50N／S.DAT、DATA17N／S.DAT、PICDATA 等。Disk B 遊戲直接以磁軌、磁區讀（透過副 CPU），下文的位置是線性映像的 offset。

## 頭像（Disk B）

- 畫法（ODAMAIN 0x1B1D）：每 8 點 3 bytes，依序寫到 GVRAM 平面 0x5C、0x5D、0x5E（B、R、G），沒有壓縮。200 線畫面，匯出時每列重複一次（`pc88.brg_pixels`）。
- 讀取（0x3A67 → 0x38F2）：第 i 張的 offset ＝ i × 大小，磁區 ＝ offset / 256 ＋ 起點，再以磁軌讀進副 CPU RAM 後取出。對到線性映像：
  - 大名 0x13D00 起，53 張 × 960 bytes（64×40），到 0x203C0 為止。
  - 女性 0x20400 起，20 張 × 1584 bytes（88×48），到 0x27FC0 為止。0x3A67 的參數為 0 時畫女性，序號不經大名表換算。
- 色盤：遊戲沒有寫 port 0x54–0x5B，也沒有切類比模式（port 0x32），所以是數位 8 色（色號 bit 0 B、bit 1 R、bit 2 G）。

## 組合臉（後繼者）

- 大名換人時（0x1FF4）把大名記錄 +6 設成 1，並隨機產生一個 8 bit 碼（每 bit 各 rand(2)），和現有大名的碼都不同時才採用，存在 0xAF0A＋大名序號。
- 畫臉時 +6 不為 0 就走 0x39B3：把 Disk B 0x3100 起的 4 張 64×40 臉（15 磁區）讀進來，碼的 4 組 2 bit（低位起）分別選這 4 張之一的橫條：第 0–13 列、14–18 列、19–23 列、24–39 列（表在 0x39A3、0x39AB）。
- 匯出成 4 個 slot（頭、眼、鼻、口）、1 個 variant，code 是 8 bit bitfield。劇本裡沒有人一開始就用組合臉，所以沒有 character 指到它。

## 人物（DATA50S.DAT）

- 0x1581 起 53 筆 9 bytes 的姓（Shift-JIS，0 補齊），0x175E 起 53 筆 5 bytes 的名（`koei_games.load_nobu2_pc88_names`）：50 國劇本的 50 位大名，加上明智光秀、羽柴秀吉、柴田勝家。序號就是頭像號。
- 17 國劇本的大名經 0x3A43 的表換成 50 國的序號，用同一批頭像。
- 順序和 `nobu2-fc` 相同（看臉對過：一色義道光頭、堀内氏善與明智光秀綁頭巾等），所以 `id` 照 FC 從 0 起。
- `nameHistorical`：別所長冶 → 別所長治。蛎崎、葦名、斉藤、竜造寺等字形差異照錄不填。

### 能力

- 每位大名 6 個 u8，依序是年令、健康、野心、運、魅力、IQ（畫面寫全形「ＩＱ」）；可以超過 100（最高 115）。順序和名稱照 DOS 版 MAIN.EXE 印出這 6 格的程式（DS:0x2510＋8 i，對應 DATA50S.DAT 0x14B0）。
- 位置：PC-88 `DATA50S.DAT` 0x1308 起每筆 7 bytes，X68000 `DATA50.DAT` 0x1BD6 起每筆 8 bytes，DOS `DATA50S.DAT` 0x14B0 起每筆 8 bytes；三版的值相同（`koei_games.load_nobu2_pc88_stats`，`dekoei.py nobu-person nobu2-pc88`）。第 53 筆是 69、60、60、60、60、60，像是新大名的樣板（未確認）。
- 年令和 1560 年的實際年齡相符（信長 26、信玄 39、家康 18）。`status-screens/` 的截圖是玩家大名開局時亂數重骰的值，只能對名稱、不能對數值。
- 17 國劇本 `DATA17S.DAT` 0x1308 起也是同樣的 7 bytes 記錄（依國順），只有筒井順慶的魅力、IQ 不同。

## 人物欄位

只有大名，沒有家臣。50 國劇本 53 筆（50 位大名＋明智光秀、羽柴秀吉、柴田勝家），17 國劇本 17 筆。劇本只有 1560 年一個（50 國、17 國是兩種模式）。

- PC-88 `DATA50S.DAT` 0x1308 起每筆 7 bytes：+0 年令、+1 健康、+2 野心、+3 運、+4 魅力、+5 ＩＱ、+6 是 0（後繼者旗標，見「組合臉」）。姓名在 0x1581／0x175E（見上）。✅ cross：和 FC 劇本映像 `$752F` 的 7 bytes 記錄逐筆相同（`famicom-re:zenkoku/docs/ROM_FORMAT.md` §2）。
- 生年可以由年令推出（1560 − 年令），檔案裡沒有生年、壽命、一門、相性、義理之類的欄位。
- 所屬：50 國劇本是大名 k 治國 k（FC `$6E15` 開局是恆等，PC-88 沒有找到這張表）；第 50–52 筆開局沒有國。17 國劇本的大名 k 是 50 國的第 `ODAMAIN.COM 0x3A43`［k］筆（`15 9 13 20 21 17 19 23 22 31 26 27 25 30 32 14 24`，和 FC `0x3F6CB` byte 相同）。

## 地理

**國**（PC-88 Disk A，檔案用 `pc88.cpm_files` 取出）：

- 國名：`DATA50N.DAT` 0x104 起 50 筆 × 9 bytes（Shift-JIS，0 補齊）；`DATA17N.DAT` 同位置 17 筆。
  - 寫法照錄：2 睦奥（X68000 版也是睦奥）、8 盤城（X68000 版改成磐城）。
  - 一國可以是兩國合併的名字（越後上野、武蔵伊豆、甲斐信濃…），17 國劇本另有加賀越中、越前若狭。
- 相鄰：`DATA50N.DAT` 0x881 起 50 × 8 bytes，鄰國號（0 起算），`FF` 結尾、0 補齊；`DATA17N.DAT` 0x881 起 17 × 8。
  - ✅ cross：50 國、17 國兩張都和 FC（PRG `0x10004`、`0x10300`）byte 相同，也都是對稱的。
  - X68000 `DATA50.DAT` 0x2336、DOS 英文版 `MAIN.EXE` 檔案 0x163EE（DGROUP＋0x30CE）也是 byte 相同的 50 國表。
- 地方：`DATA50N.DAT` 0xA11 起 50 bytes，1–7（東北→九州），和 FC `$7B79` byte 相同；地方的名稱沒找到。
- 地圖位置 🟡：`DATA50N.DAT` 0xA75 起 7 段 × 52 bytes，每段是一張地方地圖的 `[國][x][y]`，`FF` 結尾。
  - 和 FC `0x10194` byte 相同，FC 筆記推定是旗子的位置。
  - x 0–54、y 0–144，單位沒確認；一國可以出現在幾張地方地圖上（美濃在第 2–5 張），所以沒有全國一張圖的座標。
  - DOS 英文版 `MAIN.EXE` 0x165B3 起是同樣結構、不同數值的表（DOS 自己的地圖）。
- 國的數值：`DATA50S.DAT` 0xDDA 起 50 × 26 bytes（13 個 u16：金、借金、町、兵糧、石高、治水、民忠、民財、兵力、兵忠、訓練、武装、第 13 項）。前 12 項和 FC 相同；第 13 項（FC 叫 `Unk24`，600／800／1000）PC-88 是 2500、7000、4500 這類值，意義沒解。

**戰場**：

- `HEXMAP.50`（2816 bytes）：50 張 × 55 bytes（11 欄 × 5 列），地形碼同 FC（`02` 場外、`04` 平地、`08` 町、`10` 林、`20` 城、`40` 川・海、`80` 山），後面補 0。和 FC PRG `0x1256E` 比，只有第 38 國（三備）第 40 格不同（PC-88 `40`、FC `10`）。
- 選圖：DOS 英文版 `MAIN.EXE` 映像 0x1026D–0x102AE 開 `HEXMAP.50`，seek 到（DS:0x1F86 的國號經一次換算）× 0x37，讀 0x37 bytes。✅ code（DOS）。換算前是不是被攻打的國，照 FC 的模擬器結果（打哪一國用那一國的圖，17 國劇本經上面的對照表）✅ cross；PC-88 的程式沒追。
- `HATA.50`（5504 bytes）是旗子的圖，不是座標。
- DOS 版的圖塊（2026-11-07，✅ capture）：遊戲檔裡沒找到，改從 DOS 英文版的截圖切（`captures/screenshots/nobu2-dos/`，說明在那裡的 `index.md`）。
  - 畫面 640×400（EGA 640×200 兩倍），地圖區從 x 192 起，448×352。格 (0,0) 中心在 (215, 32)，欄距 40、列距 64，奇數欄下移 32。六角形上下邊離中心 ±16、左右角 ±24（量自布陣游標的藍色格）。
  - 7 種地形：`04` 平地、`08` 町、`20` 城、`40` 川・海（深綠點）取自尾張（圖 24）；`10` 林（樹叢）、`80` 山取自下野（圖 11，AI 對 AI）；`02` 場外取自伊勢志摩（圖 25）：整格黑色、沒有外框。
  - 驗證：用切出的圖塊畫尾張、蝦夷（圖 0，沒拿來切）、伊勢志摩，和截圖比，除了部隊所在的格子，只有地圖外框的斜線約 450 點不同（外框屬於地圖外的格子，規則沒找到）🟡。
  - 程式在 `wiki_nobu2_dos.py`（從截圖切圖塊、畫 50 張），匯出 `places-export nobu2-dos`。DOS 版是重畫的美術，主資料集 `nobu2-pc88` 不掛這些圖（使用者 2026-11-07 定）。
- PC-88 的圖塊沒找到 ❌：PC-88 Disk A 的 `PICDATA`（畫成 3 平面是雜訊）、`HOGEN.HEX`（Shift-JIS 文字）都不是；DOS 英文版 `HOGEN.HEX`（1408 bytes，指標表＋英文訊息）、`PICDATA.DAT` 也不是。`ODA.OVL`、`PACKDATA.DAT`、Disk B 沒查。
- DOS 英文版的完整檔案在 `games/archives/dos/信長之野望_英文版_nobunagas-ambition.zip`（`games/nobu2-dos/` 只放頭像用的三個檔），`HEXMAP.50` 和 PC-88 相同。DOS 版是重畫的 EGA 圖，用 DOS 截圖切圖塊時，要不要拿來畫 `nobu2-pc88` 的戰場圖待決定。

## 負面結論與未解

- PC-88 的「國 → 大名」表沒找到（FC `$6E15` 對應的位置在 PC-88 是別的值）；開局是恆等，匯出不需要。
- 地方的名稱、地方地圖的座標單位、國數值第 13 項沒解。
- 17 國劇本的地圖位置表（`DATA17N.DAT` 0x909 以後）是 0，沒有再找。

## koei-wiki 匯出

`dekoei.py persons-export nobu2-pc88 --game-dir ../games/nobu2-pc88 --out ../export/koei-wiki/persons --places ../export/koei-wiki/places` 和 `places-export nobu2-pc88`（`wiki_nobu2.py`，koei-persons/1、koei-places/1，規格在 koei-wiki 的 `docs/persons-format.mkdn`、`docs/places-format.mkdn`）。

- 人物 53 位，`id` 同 kaodata（0 起）。`stats` 是健康、野心、運、魅力、ＩＱ，`more.年令` 是 1560 年的年令，`born`＝1560－年令。劇本只有一個 `50國`，大名 k 在國 k＋1；明智、羽柴、柴田沒有 `scenarios`。
- 地點是 50 國劇本的 50 國，`id` 1–50，`adjacent` 照 `DATA50N.DAT` 的順序。地方只有號碼（寫在 `notes`），沒有 `region`；地方地圖的圖和座標單位沒解（見「負面結論」），沒有大地圖與 `pos`；戰場圖的圖塊沒找到（見「戰場」），沒有 PNG。17 國劇本的國沒有匯出。
- `places-export nobu2-dos --game-dir ../games/nobu2-dos`（`wiki_nobu2_dos.py`）：同樣 50 國（國表、地方號讀 `games/nobu2-dos/PC88_DISK_A.D88`，`name` 用漢字，DOS 的英文國名 `DATA50N.DAT` 0x3A 起每筆 14 bytes 寫進 `notes`），加上 50 張戰場圖 `01.png`–`50.png`（448×352，`role` 戰場，圖塊見「戰場」）。`games/nobu2-dos/` 另從 DOS 壓縮檔取出 `HEXMAP.50`、`DATA50N.DAT`；圖塊要讀 `captures/screenshots/nobu2-dos/` 的截圖。

## 和 FC 版比較

- FC 版是 48×48 的重畫，另有 22 張姫；PC-88 是 64×40（200 線）的 53 張大名與 20 張 88×48 的女性。

## X68000 版（`nobu2-x68`）

`dekoei.py export nobu2-x68` 用 `build_nobu2_x68`。

- 來源：Internet Archive `nobunaga_no_yabou_zenkokuhan_1_x68k`（`~/game-library/_original/x68/ia-softwarelibrary/`），A、B 兩片 DIM，各有主檔、`[a]`、`[a2]`。A 片的 `KAO.DAT`、`DATA50.DAT` 三份相同，`[a2]` 的 `ODAMAIN.Z` 不同；用主檔。`games/nobu2-x68/` 放 A 片的 `KAO.DAT`、`DATA50.DAT`、`ODAMAIN.Z`（色盤）。檔案日期 1988-07～09-29，沒有版本字串。
- `ODAMAIN.Z` 沒有壓縮，執行位址＝檔案＋0x4FFDE。
- `KAO.DAT`（0x606F0 整檔讀進來）：全部重畫成 64×80 全高，每 8 點 B、R、G 3 bytes（`pc88.brg_pixels(..., double=False)`）。
  - 大名 53 張（0x6103C），女性 20 張從 0x18D80 起（0x61132，group「姫」）。
  - 大名 51、52（羽柴秀吉、柴田勝家）在 0x61084 互換，所以羽柴用頭像 52、柴田用 51（兩人加 `note` 說明）；人物 id 和名字照 `nobu2-pc88`（`DATA50.DAT` 同一張表，名字逐筆相同，`load_nobu2_pc88_names(..., x68=True)`）。
  - 後繼者的組合臉（0x60EE0，表在 0x70632）：0x22380 起 4 個 64×80 的頭，接著眉（第 25 列起 7 列）、眼（32 起 5 列）、鼻（37 起 11 列）、口（48 起 7 列）各 4 個，寬 40 點、貼在 x＝0。碼是 10 bit，每段 2 bit，頭在最低位。人物資料不用組合臉（後繼者是遊戲中產生），匯出成一個 variant「後継者」。
- 色盤（0x60EA2）：0x706EC 是兩組 8 色（X68000 色盤字），設到色號 8–15；大名與組合臉用第 0 組、女性用第 1 組。kaodata 一份資料集只有共用的色盤，所以女性的像素加 8，色盤做成 16 色（0–7 大名、8–15 女性）。

## DOS 英文版（`nobu2-dos`，Nobunaga's Ambition，1988）

`dekoei.py export nobu2-dos` 用 `build_nobu2_dos`。來源：`games/archives/dos/信長之野望_英文版_nobunagas-ambition.zip`（`MAIN.EXE` 寫 `(C)1988 KOEI CORPORATION`），`games/nobu2-dos/` 放 `MAIN.EXE`、`PICDATA.DAT`、`DATA50S.DAT`，再加 `nobu2-pc88` 的 Disk A（`PC88_DISK_A.D88`，取漢字名）。

- `MAIN.EXE` 是 MS C（1986），DGROUP 在檔案 0x13320（＝0x400＋0x12F20）。PICDATA 的檔案代碼存在 DS:0x160（`B:PICDATA.DAT` 或硬碟安裝的 `1ODA_B\PICDATA.DAT`，兩份相同）。
- `PICDATA.DAT`（196608 bytes）裡的頭像，沒有壓縮：
  - 大名 0x20600 起，53 張 × 640 bytes（64×40），讀取在 0x1325，序號在 17 國劇本經 DS:0x184 的表換算（同 PC-88）。
  - 後繼者組合臉 0x28C00 起 4 張 64×40（0x125B 一次讀 0xA00），橫條的列號表在 DS:0x174／0x17C。
  - 女性 0x29600 起，20 張 × 1056 bytes（88×48，0x13BF）。
- 像素：每 8 點 2 bytes，第一個寫到 EGA 平面 2、第二個寫到平面 1，平面 0 清成 0（繪圖 0x988 → 0x9BF），所以色號是 0、2、4、6。
- 色盤：「Play in color mode?」答是時用 mode 0x0E，色盤暫存器設成 DS:0xB22 的 `00 11 12 13 14 15 16 17…`，色號 0、2、4、6 是黑、亮綠、亮紅、黃（CGA 色盤 0 的高亮度那組）。答否時用 mode 6（640×200 單色），每點是兩個平面 OR 起來的黑白（0xB80 → 0xBA2）。
- 圖是重畫的 4 色版，和 PC-88 的 8 色圖不同，人物順序相同。匯出時 200 線的列重複一次（64×80、88×96），組合臉的 4 段橫條和碼同 PC-88。
- 人名：`DATA50S.DAT` 0x1760 起是 53 個羅馬拼音的姓、0x19A8 起是 53 個名，各 11 bytes（Kakizaki Yoshihiro … Shibata Katsuie）。`name` 照遊戲原文（Ruzoji＝竜造寺、Kinoi＝城井、Kosa＝光佐、Hideyosi 等怪拼法照錄），`nameZh` 依 id 取 PC-88 的漢字名，別所長冶照 PC-88 的 `nameHistorical` 改成別所長治。
- 色盤：`ega`（預設）照 DS:0xB22 的色盤暫存器換算；`mono` 是單色模式（色號 0 黑、其他白）。

## 下一輪候選

- PC-88 的地方地圖（koei-wiki 要的大地圖）— 前置：找到 `ODAMAIN.COM`／`ODA.OVL`（Z80）裡畫地方地圖的程式，或在模擬器（PC-88）拍一張地方地圖的截圖，知道圖的大小與位置；做法：從程式讀出存圖的檔案與位移，再用 `DATA50N.DAT` 0xA75 的 `[國][x][y]` 對圖驗證座標單位。

## 負面結論

- 在 Disk A `PICDATA` 找地方地圖（2026-11-08）：照 `pc88.brg_pixels` 試寬 64–128 點、自相關找列寬，最常見的列寬是 102 bytes（272 點），畫出來是許多小圖（事件或圖示），沒有地圖 → 圖的大小、存放順序要從程式讀出來才值得再試。
- 在 Disk B 映像頭像以外的部分（0x28000–0x50000）找地方地圖：資料像是以 0x96 為跳脫碼的 RLE（`96 n` 重複），照「前一個 byte 重複」解開後，以 640 點一列畫成單平面是雜訊，平面排法和列寬都沒對上 → 同上，要先找到解壓與畫圖的程式。
- 沒有 PC-88 版的截圖，也沒有全國一張的大地圖：遊戲只有 7 張地方地圖，一國可以出現在幾張上，所以就算解出圖，也要決定交付哪幾張。
