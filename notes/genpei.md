# 源平合戰（GENPEI, DOS）頭像相關格式

這份筆記整理 `dekoei/genpei.py` 後段「face data」的解碼方式，`dekoei.py export genpei-dos` 就是用這些函式產生 kaodata 統一格式資料集。內容移植自 genpei-zh 的 `docs/formats.md`（§4.3 頭像碼、§10 圖形格式與色盤）和 `tools/`（`gfx.py`、`dump_gfx.py`、`unpack_exe.py`、`dump_data.py`），那邊已經和實機截圖逐 pixel 比對過。

## 像素格式

- **3bpp byte-interleaved planar**：每 3 bytes 表示 8 個 pixel，**byte k 是色號的 bit k**（LSB plane 在前），MSB＝最左 pixel。
  - `utils.to_3bpp_indexes` 的順序剛好相反（第一個 byte 當 bit 2），用在本作時顏色會藍綠、膚色黃對調。
- **1bpp mask**：逐列、MSB＝最左，**bit 1＝透明**。帶 mask 的零件是「3bpp 顏色＋緊接著的 mask」。
- **RLE3**：`u16 w, u16 h`＋壓縮串流，演算法和 `utils.unpack_npk_3bits` 相同。`genpei.read_rle3` 另外回傳串流結束的位置，因為 Kaodata.gp 要靠這個位置往下讀。

## 色盤 `Mainpal.pld`

- 4 組 × 48 bytes。每組 16 色 × 3 bytes，每 byte 是一個 4-bit 值，順序 **B、R、G**。換成 8-bit 時乘上 `0x11`。
- 四組只差色 9 與色 15，對應四季（0 春、1 夏、2 秋、3 冬）。頭像只用色 0–7，所以匯出時用第 0 組。
- 第 0 組：`#000000 #1144aa #dd4400 #ee8855 #009933 #77bbbb #ffbb44 #ffffdd #332200 #334400 #995533 #cc9944 #778855 #112244 #aaaabb #aabb44`
- 舊的 `genpei_face_colors`（`#1041a2` 等）是從截圖量出來的，nibble 相同（`#14a`），但換算不是 ×0x11；色 8–15 也和 Mainpal 不同。以 Mainpal 為準。

## Kaodata.gp：90 張專屬頭像

- 90 組 ×（128×160 頭像 RLE3＋128×160 mask RLE3＋2 bytes），剛好用完整個檔。
- mask 圖的色 7＝透明（露出背景），色 0＝頭像本體。
- 最後 2 bytes 是 trailer：遊戲內 64×80 頭像窗在 128×160 圖上的左上角 `(x, y)`，多為 (32,16)、(40,16)、(32,24)。

## Montage.gp／Haikei.gp：組合頭像零件

- Montage.gp：頭部與身體，各 8 件。Haikei.gp 開頭 9,600 bytes 之後是眼與口，各 16 件。每件都是 3bpp＋mask，寬度是 8 的倍數。
- 每種類型的零件 offset、尺寸、位置都從 **組合表** 讀，不寫死：
  - 位置：Main.exe 解包後 DGROUP:0x59CE（含 MZ 檔頭的解包檔 0x5C23E；檔頭 0x53D0 bytes，所以在展開後的 image 是 0x56E6E）。共 3 筆 × 0x26 bytes，第 (類型 − 1) 筆。
  - 結構：`u32 頭 offset, u32 身 offset, u16 眼 offset, u16 口 offset, u16×8（頭、身、眼、口的寬 bytes、高）, u16×4 位置, u16 頭像窗`。
  - 位置的編碼：128×160 緩衝區，每列 16 bytes，`x = (v mod 16) × 8`、`y = v ÷ 16`。
- Main.exe 有 run-length 壓縮，必須先展開才讀得到組合表（`genpei.unpack_main_exe`；stub 格式見 genpei-zh `tools/unpack_exe.py`）。

| 類型 | 名稱 | 頭 | 身 | 眼 | 口 | 頭像窗 |
|---|---|---|---|---|---|---|
| 1 | 大鎧戴兜 | 120×78 @(0,0) | 128×99 @(0,61) | 40×12 @(40,36) | 40×27 @(40,48) | (32,8) |
| 2 | 鎧 | 72×88 @(24,0) | 128×103 @(0,57) | 40×11 @(48,37) | 40×30 @(48,48) | (32,0) |
| 3 | 直垂 | 72×77 @(32,0) | 128×99 @(0,61) | 40×14 @(40,34) | 40×25 @(40,52) | (32,0) |

- 畫的順序是 **身體 → 頭部 → 眼 → 口**，各依自己的 mask 疊上。沒被任何零件蓋到的地方是透明。

## 頭像碼（Sndata.gp 武將 record +0x1A）

- Sndata.gp＝4 個劇本 × 41,266 bytes。每個劇本是 0x26 bytes 檔頭，接著 400 筆 × 71 bytes 的武將 record。
- record：+0x00 姓（SJIS 7 bytes）、+0x07 姓讀音（半形片假名 7 bytes）、+0x0E 名（5 bytes）、+0x13 名讀音（7 bytes）、+0x1A 頭像碼（u16）。
- 頭像碼：
  - 0–89：Kaodata.gp 第 n 張。
  - ≥ 0x4000：組合頭像，bit 15–14＝類型（1–3）、13–11＝頭、10–8＝身、7–4＝眼、3–0＝口。
- 四個劇本同一人的頭像碼都相同（匯出時會檢查）。目前 400 人都有頭像：90 人用 Kaodata，310 人用組合頭像。

## 背景與遊戲內頭像窗

- Haikei.gp 開頭是 5 張 64×80 的背景（3bpp、無 mask，共 9,600 bytes）。
- 遊戲裡只顯示 64×80 的頭像窗，從 128×160 圖 1:1 裁出。透明處填背景 **(武將編號 >> 1) mod 5**（Main.exe 0x49048）。
- Kaodata 頭像在遊戲裡也墊同一組背景、同一條公式。匯出時，兩種臉的人物都帶 `bg`，背景放在資料集頂層的 `backgrounds`。
- 匯出把零件與背景放 `pixels.bin`，90 張 Kaodata 頭像放 `portraits.bin`（image ref 第 4 個元素為 1）。
