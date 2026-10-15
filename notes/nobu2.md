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
