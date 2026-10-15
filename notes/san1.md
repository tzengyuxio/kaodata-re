# 三國志（SAN1, PC-98 日文版）頭像相關格式

`dekoei.py export san1-pc98` 用到的格式。來源是 `games/archives/pc98/【PC98】三國志.rar` 的 FDI（Ver.2.4, 87/4/20），解出放在 `games/san1-pc98/`。

## 頭像：PICDATA.DAT

- 每張 720 bytes：48×40 半高、3bpp，每列 18 bytes，順序同 `utils.to_3bpp_indexes`（第一個 byte 是 bit 2），顯示時逐列重複成 48×80。
- 0–112 是臉，113 起是空白和其他圖：
  - 0–64：65 張專屬頭像，頭像碼就是索引。
  - 65：和 64（馬岱）逐 byte 相同，沒有人用，group「未使用」。
  - 66–83：18 張女性，婚姻外交的女兒，group「姫」。英文 DOS 版的公式是 `0x42 + (… mod 16)`，只用到 66–81，82、83 可能沒用到（只有 DOS 證據）。
  - 84–112：組合臉素材，5 組各 5 張，每組後面一張全黑的空位（89、95、101、107、113）。
- 色盤：SANMAIN.EXE、SANGOKU.OVL 都沒有寫類比色盤 port（0xA8–0xAE）或切 16 色模式（port 0x6A）的指令，所以是預設的 8 色數位色盤，每分量 0 或 FF（同 `san2-pc98`）。

## 組合臉

- 頭像碼 ≥ 0x1000 是組合臉，寫成 0xGTMB（190 人）：G 是組別 6–10，素材是 PICDATA 第 6 ×（G＋8）張起的 5 張；T、M、B 各是 0–4，分別取第 T 張的半高列 0–14、第 M 張的 15–24、第 B 張的 25–39。
- 依據是英文 DOS 版 MAIN.EXE 0x467B：組合臉 seek `((si >> 12) + 8) * 0xB40`，讀 5 張，取 0xB4／0x78／0xB4 bytes 三段（15／10／15 列）。PC-98 的對應程式在 SANGOKU.OVL 裡，有編碼過，讀不到。
- 所以 PC-98 是同一規則是推論，但 190 張合成後接縫都自然，各組第 14 列也幾乎相同，正好是切線。
- 匯出成 3 個 slot（上、中、下），5 個 variant（組別 6–10）。

## 人物

- 原始劇本有編碼（PACKDATA.DAT、SANGOKU.OVL），沒有解開。人物改從 `SAVEDATA` 讀（`san1.load_san1_pc98_persons`）：
  - 前 300 bytes 是 10 × 30 bytes 的存檔槽標頭，之後是 10 個 29364 bytes 的槽。
  - 槽 0 的人物表在 300 ＋ 0x1096，255 筆 × 34 bytes。其他槽在同一 offset 讀到的是亂的。
  - 這份 SAVEDATA 的日期是 1991-08-15，有玩家存檔（槽名 "YAWARA!" 等），換一份磁碟映像時要重新確認。
- 記錄 34 bytes：+0 讀音（8 bytes 半形片假名，不匯出）、+8 姓名（3 個 little-endian JIS word）、+14 年齡、+15–20 能力、+22 u16 頭像碼、+26 城、+27 勢力。
- 255 個頭像碼和英文 DOS 版 `SINADATA.DAT` 5 個劇本完全一致，所以頭像碼不隨劇本變，從存檔取可行。
- 外字：JIS 0x7620–0x7672，字形在 `KANJIF.DAT` 的 0x4000 ＋ 32 ×（碼 − 0x7620），看字形判讀，見 `san1.PC98_GAIJI`。0x766D 起是地名用字，人名沒用到。
- 夏侯尚的「尚」存成 0xBE30（多了 bit 15），讀的時候 `& 0x7FFF`，原因不明。
- 順序和 `san1-fc` 相同，`id` 也照 FC 從 1 起算。和 FC 寫法不同的 10 人照遊戲寫法：干禁、旬攸、許収、蔡仲、雷同、李湛、諸葛謹、刑道栄、鮑龍、沙摩可，以及和 FC 相同的尚寵（向寵）。都是錯字，依 `nameHistorical` 規則（見 CLAUDE.md）填史書寫法（`SAN1_PC98_NAME_HISTORICAL`，11 筆）。陳嬉（197）找不到對應的史書人物，不填。

## 發行年份

PC-9801 版 1986-04-30（ja.wikipedia〈三國志 (ゲーム)〉，和 FM-16β 同日）。另有 1995 年 3 月的 PC-9801 復刻版。

## DOS 英文版（`san1-dos`）

`dekoei.py export san1-dos` 用到的差異。來源是 `games/archives/dos/三國志_英文版_romance-of-the-three-kingdoms.zip`，解開放在 `games/san1-dos/`（檔案日期 1996-06-06，應是重新包裝的日期）。`MAIN.EXE` 標題字串「(C)1988 KOEI CORPORATION」「Ver.2.4(87/4/20)」，和 PC-98 版號相同。

- `MAIN.EXE` 用 PLINK86 overlay（`SAN.OVL`），C 程式庫是 MSC 1986，DGROUP 在檔案 0x13830。
- PICDATA.DAT：
  - 每張 480 bytes：48×40 半高、2bpp，每列 12 bytes，順序同 `utils.to_2bpp_indexes`（第一個 byte 是高位）。
  - 臉的順序、組合臉規則（0x467B，`((si >> 12) + 8) * 0xB40`）和 PC-98 相同，匯出共用 `build_san1`。
  - 和 PC-98 不同處：
    - 82、83 和 81 逐 byte 相同。女兒公式 `0x42 + (… mod 16)` 只用到 66–81，所以 82、83 標「未使用」。
    - 組合臉第 8 組（96–100）的第 3、4 張和第 0、1 張相同；各組後面的空位（89、95、101、107、113）是同組某一張的複本，不是全黑。
    - 顏良（頭像 40）的頭盔不同。
- 色盤：
  - 遊戲有 CGA（0xB800）和 EGA（0xA000）兩種畫面。
  - EGA 用 int 10h AX=1002 設調色盤，表在 DGROUP 0x1BC：暫存器 1–7 是 0x11–0x17（亮色）。
  - 頭像的兩個 plane 寫到色號 bit 1、2，所以 4 色是 0、2、4、6：`#000000 #55FF55 #FF5555 #FFFF55`。這和 CGA 調色盤 0（高亮度）相同，也和舊 `san1 face` 的色碼一致。
- 人物：
  - `SINADATA.DAT` 有 5 個劇本，從 4326 起每劇本 12490 bytes。
  - 每劇本 255 筆 × 32 bytes（`s1_format`），姓名 12 bytes ASCII，+20 是 u16 頭像碼。
  - 5 個劇本的姓名、頭像碼都相同，匯出取劇本 1（`san1.load_san1_dos_persons`）。
  - 255 個頭像碼和 PC-98 逐筆相同，能力值也一致（PC-98 是存檔，年齡多 5），所以順序同 PC-98／FC，`id` 從 1 起算。
- 姓名：
  - `name` 照遊戲的英文，錯字照錄。拼音是不標聲調的漢語拼音（Cao Cao、Liu Bei、Zhuge Liang、Xiahou Dun），「呂」寫 Lu。
  - 有不少錯拼，例如：
    - Gou Yu（荀彧）、Wei Yang（魏延）、Fan Zhang（潘璋）
    - Deng Lan（鄧賢）、Ma Lin（馬休）、Wei Pin（文聘）
    - Xiahou Xi（夏侯尚）、Liu Coing（劉琮）
    - Xiong Rong（邢道榮）、Gou Zhi（郭攸之）
  - 有三組英文名對調。頭像和能力值都是 PC-98／FC 的同一人，只有英文名掉換：
    - 14 Cao Ang／15 Cao Hong 是曹洪／曹昂
    - 76 Liang Xing／129 Liang Gang 是梁剛／梁興
    - 161 Song Qian／210 Song Xian 是宋憲／宋謙
  - `nameZh` 依 `id` 取 PC-98 姓名，套用 `SAN1_PC98_NAME_HISTORICAL`，再轉成繁體字形（`SAN1_DOS_NAME_ZH`），所以已經是史書寫法，不另填 `nameHistorical`。
- 發行年份：
  - Wikipedia 沒列 DOS 版日期。
  - Home of the Underdogs、oldgames.sk 寫 1989。
  - 遊戲內版權年是 1988。
  - 沒有日文 DOS 版，英文 DOS 版就是該平台首發。
