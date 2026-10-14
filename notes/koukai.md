# 大航海時代（KOUKAI, DOS 中文版）頭像相關格式

`dekoei.py export koukai-dos` 用到的格式。來源是 `games/大航海時代_中文版_uwc.zip` 的 `sea1/`，解開放在 `games/koukai-dos/`。

## 版本

- 英文 DOS 版 Uncharted Waters（1991，[Wikipedia](https://en.wikipedia.org/wiki/Uncharted_Waters_(video_game))）的移植：`KAO.PUT`、`COLOR.CIM`、`GRAPH.DAT` 等和英文版逐 byte 相同（1991-11-26）；`SHINARIO.CIM` 同大小，只換成中文名字。原作是 1990 年的 PC-88 版。
- 中文版 `MAIN.EXE` 1993-08-17，是 TINYPROG 壓縮，沒有解開；程式碼看英文版 `main.exe`（EXEPACK，DGROUP 0x4289）。下文是它解壓後的映像位址。

## 頭像：KAO.PUT

- 80256 bytes，沒有壓縮，全部是 64×40 半高、3bpp，格式同三國志II DOS（`san2_pixels`）。
- 0x0000–0xB9FF：組合臉零件，4 組（葡萄牙、西班牙、土耳其、海盜），每組 0x2E80 bytes（offset 表 DGROUP 0x305C）。
- 0xBA00 起：34 張頭像 × 0x3C0（0x9FE1 `seek(0xBA00 + n × 0x3C0)`）。
- 色盤：EGA mode 0x0E（0x9351），0x155F 把 byte0／1／2 寫到 plane 0／2／1，0x57D9 int 10h AX=1002 載入 DS:0x2C48 `00 11 12 … 17`。結果就是 `SAN2_PALETTE`，舊 `koukai face` 的色盤是對的。

## 組合臉（0x9ED9 → 0x9CD6）

- 男性記錄 +0x11（b0）、+0x12（b1）決定臉，+0x13 高 4 位元是國籍＝零件組＝variant。
- 零件（組內 offset、每筆大小、數量、索引、半高列）：上 0x0000、0x1F8、8、`b1 & 7`、0；下 0x2040、0x1C8、8、`b1 >> 3 & 7`、21；眼 0x0FC0、0xC0、8、`b0 & 7`、10；鼻 0x15C0、0xC0、4、`b1 >> 6`、16；口 0x18C0、0xF0、8、`b0 >> 4 & 7`、22。
- 上下直接複製，五官用 OR 疊上（0x9C7C）。檢查過全部組合，五官不會蓋到上下的非 0 像素、彼此也不重疊，所以匯出成「0＝透明」的覆蓋是精確的。
- `b0 == 0xFF` 時改用頭像 `b1`，只有里昂（頭像 0）。`face.code` 填 `b1 << 8 | b0`，例如費南多 `CB36`。

## 人物：SHINARIO.CIM

- 女性 0x7D0 起 21 筆 × 16 bytes；男性 0x920 起 41 筆 × 20 bytes（0x5D4C 以 `DS:0x970 + id × 20` 取用）。姓名 15 bytes，光榮台灣內碼（`koei_games.load_koukai_dos_people`）。
- 女性 i 用頭像 13＋i（0x9F7E）。
- `id`：男性 0–40、女性 41–61，和 `koukai-fc` 一致（男性國籍和 FC 的 variant 全部吻合）。女性 61 克莉絲汀娜（頭像 33）在 FC 只有頭像、沒有人物。
- 人物都是虛構的，不填 `nameHistorical`。4 號「亞米洯斯」的「洯」沒驗證。

## 沒有人物使用的頭像（1–12）

- 只由 0x9F31 的 mode 1 直接指定頭像號叫出。名字是對照 `koukai-fc` 外觀取的，沒逐一追到程式碼，中文版的實際用語（含「土耳其」）也沒查（中文 MAIN.EXE 沒解開）。
- 1–3 葡萄牙／西班牙／土耳其國王；4 道具店、5 造船廠、6 交易所、7 酒館、9 港口、10 王宮；8 老航海士（人物 0xFF 的預設臉）；11 主教（暫定「教會」，FC 沒有）；12 包頭巾的老婦人（對應 FC 宿屋，暫定「旅館」）。
