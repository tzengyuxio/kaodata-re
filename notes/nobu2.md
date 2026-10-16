# 信長の野望・全国版（NOBU2, PC-88）頭像相關格式

`dekoei.py export nobu2-pc88` 用到的格式。來源是 Neo Kobe 2016-02-25 的 `games/archives/pc88/neo-kobe-2016-02-25/Nobunaga no Yabou - Zenkoku-ban/Nobunaga no Yabou - Zenkoku-ban [FD].7z` 主檔的 Disk A、B，原樣放在 `games/nobu2-pc88/DISK_A.D88`、`DISK_B.D88`。

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

## 和 FC 版比較

- FC 版是 48×48 的重畫，另有 22 張姫；PC-88 是 64×40（200 線）的 53 張大名與 20 張 88×48 的女性。

## X68000 版（`nobu2-x68`）

`dekoei.py export nobu2-x68` 用 `build_nobu2_x68`。

- 來源：Internet Archive `nobunaga_no_yabou_zenkokuhan_1_x68k`（`games/archives/x68000/ia-softwarelibrary/`），A、B 兩片 DIM，各有主檔、`[a]`、`[a2]`。A 片的 `KAO.DAT`、`DATA50.DAT` 三份相同，`[a2]` 的 `ODAMAIN.Z` 不同；用主檔。`games/nobu2-x68/` 放 A 片的 `KAO.DAT`、`DATA50.DAT`、`ODAMAIN.Z`（色盤）。檔案日期 1988-07～09-29，沒有版本字串。
- `ODAMAIN.Z` 沒有壓縮，執行位址＝檔案＋0x4FFDE。
- `KAO.DAT`（0x606F0 整檔讀進來）：全部重畫成 64×80 全高，每 8 點 B、R、G 3 bytes（`pc88.brg_pixels(..., double=False)`）。
  - 大名 53 張（0x6103C），女性 20 張從 0x18D80 起（0x61132，group「姫」）。
  - 大名 51、52（羽柴秀吉、柴田勝家）在 0x61084 互換，所以羽柴用頭像 52、柴田用 51（兩人加 `note` 說明）；人物 id 和名字照 `nobu2-pc88`（`DATA50.DAT` 同一張表，名字逐筆相同，`load_nobu2_pc88_names(..., x68=True)`）。
  - 後繼者的組合臉（0x60EE0，表在 0x70632）：0x22380 起 4 個 64×80 的頭，接著眉（第 25 列起 7 列）、眼（32 起 5 列）、鼻（37 起 11 列）、口（48 起 7 列）各 4 個，寬 40 點、貼在 x＝0。碼是 10 bit，每段 2 bit，頭在最低位。人物資料不用組合臉（後繼者是遊戲中產生），匯出成一個 variant「後継者」。
- 色盤（0x60EA2）：0x706EC 是兩組 8 色（X68000 色盤字），設到色號 8–15；大名與組合臉用第 0 組、女性用第 1 組。kaodata 一份資料集只有共用的色盤，所以女性的像素加 8，色盤做成 16 色（0–7 大名、8–15 女性）。

## DOS 英文版（Nobunaga's Ambition，1988）

來源：`games/archives/dos/信長之野望_英文版_nobunagas-ambition.zip`（`MAIN.EXE` 寫 `(C)1988 KOEI CORPORATION`）。還沒有匯出，資料集怎麼收待定。

- `MAIN.EXE` 是 MS C（1986），DGROUP 在檔案 0x13320（＝0x400＋0x12F20）。PICDATA 的檔案代碼存在 DS:0x160（`B:PICDATA.DAT` 或硬碟安裝的 `1ODA_B\PICDATA.DAT`，兩份相同）。
- `PICDATA.DAT`（196608 bytes）裡的頭像，沒有壓縮：
  - 大名 0x20600 起，53 張 × 640 bytes（64×40），讀取在 0x1325，序號在 17 國劇本經 DS:0x184 的表換算（同 PC-88）。
  - 後繼者組合臉 0x28C00 起 4 張 64×40（0x125B 一次讀 0xA00），橫條的列號表在 DS:0x174／0x17C。
  - 女性 0x29600 起，20 張 × 1056 bytes（88×48，0x13BF）。
- 像素：每 8 點 2 bytes，第一個寫到 EGA 平面 2、第二個寫到平面 1，平面 0 清成 0（繪圖 0x988 → 0x9BF），所以色號是 0、2、4、6。
- 色盤：「Play in color mode?」答是時用 mode 0x0E，色盤暫存器設成 DS:0xB22 的 `00 11 12 13 14 15 16 17…`，色號 0、2、4、6 是黑、亮綠、亮紅、黃（CGA 色盤 0 的高亮度那組）。答否時用 mode 6（640×200 單色），每點是兩個平面 OR 起來的黑白（0xB80 → 0xBA2）。
- 圖是重畫的 4 色版，和 PC-88 的 8 色圖不同，人物順序相同（`DATA50S.DAT` 0x1700 起是羅馬拼音的 53 個姓，各 11 bytes，接著 53 個名：Kakizaki Yoshihiro … Oda Nobunaga … Shibata Katsuie）。
- 拼法有幾個怪的：Ruzoji（龍造寺）、Kinoi（一条？待查）、Kosa（本願寺光佐）。
