# 源平合戦（GENPEI, DOS/V）格式

KOEI 1994，IBM-PC DOS/V Ver 1.0（`Version`：11.16,1994）。本 repo 是源平合戦格式研究的正本（2026-11-10 起）；中文化在 genpei-zh，那邊的翻譯、回寫工具、字型政策不搬過來。

- **來源**：2026-11-10 從 genpei-zh@09a5013 的 `docs/formats.md`、`docs/development.md`「重要發現」與 `tools/`（`npk.py`、`ls11.py`、`unpack_exe.py`、`dump_gfx.py`、`dump_data.py`、`message.py`、`exe_text.py` 的解碼部分）移植，程式在本 repo 重寫。引用那邊的實機截圖寫成 `genpei-zh:<路徑>`。
- **原始檔**：`~/game-library/_original/dos/genpei/GENPEI/`（53 個檔，沒有發行包，說明在 `_original/dos/genpei.txt`），`games/genpei-dos/` 是它的唯讀硬連結。`Main.exe` 是硬碟版（35 處 `A:`/`B:` 路徑改 `C:`、停用兩處 INT 13h 軟碟檢查），`Main.ori` 是同一份壓縮資料的軟碟版；`Savedata.gp`（2004-04-20）是檔案附的兩格存檔（genpei-zh 的 `orig-s1-yoshitsune-1185-10`、`orig-s2-yoritomo-1183-01`）。
- **工具**：頭像與能力是 `dekoei.py export genpei-dos`／`genpei-pc98`、`koei-person`；其餘是 `dekoei/genpei_extras.py`：

```sh
cd dekoei
../.venv/bin/python genpei_extras.py --game-dir ../games/genpei-dos --out ../games/genpei-dos/extract
# --no-pictures：只寫表、地圖、文字（約 1 秒）
```

輸出（4.2 MB）：`tables/`（劇本表）、`map/`（世界地圖四季、節點、合戰地圖）、`pictures/`（NPK 與 Kisetsu 的圖、`pictures.csv`）、`text/`（Message.gp、三個執行檔的字串）。

## 進度

| 項目 | 狀態 | 證據 | 說明 |
|------|------|------|------|
| 頭像（專屬 90＋組合 310） | ✅ | capture+cross | genpei-zh 的 9 張截圖逐 pixel 相同；「Kaodata.gp」「Montage.gp／Haikei.gp」 |
| 色盤 Mainpal.pld | ✅ | code+capture | B、R、G nibble；四季只差色 9、15 |
| NPK016 圖（11 檔 220 張） | ✅ | code+cross | 和 genpei-zh `dump_gfx.py` 逐 pixel 相同；Opendat／Enddat 的色盤 🟡 |
| RLE3（Kaodata、Kisetsu 11 張） | ✅ | cross | 同上 |
| 世界地圖 1696×360 | ✅ | cross | 20 條拼接，四季 |
| 戰略地圖 156 節點、190 條路 | ✅ | code+cross | 節點格中心落在城／圓點上 156/156（本 repo 2026-11-10 驗） |
| 合戰地圖編號（節點 +7） | 🟡 | code | 據點只用 30–36、海路全用 37，推測很強 |
| 劇本表（武將、勢力、據點、地方、官位、名物） | ✅／🟡 | capture+cross | 欄位逐一見「Sndata.gp」；1600 列與 genpei-zh 相同 |
| Message.gp 1305 則 | ✅ | code+capture | LS11；genpei-zh 回寫後實機顯示正確 |
| 執行檔字串（Main 496、Open 37、End 41、表 1561） | ✅ | cross | 位移、長度和 genpei-zh `exe_text.py` 完全相同 |
| Main.exe 展開 | ✅ | emu | genpei-zh 展開後的檔實機可玩 |
| 結局分支（INT 65h） | ✅ | code+capture | 三種結局，依勝者勢力種別 |
| 合戰 sprite、Mainanm、Maincmd 等 planar 圖 | 🟡 | | 在 genpei-zh 的 `dump_gfx.py`，本 repo 還沒移植；「其他圖檔」 |
| 字型、音樂 | ❌ | | 沒解 |

## 未解

- Opendat／Enddat 每張圖用哪組前綴色盤 — 要讀 Open.exe／End.exe 的動畫腳本；目前是啟發式（「色盤」）。
- 武將 +0x2D、+0x40–0x46，據點的商業／治安／農業／財貨／兵糧與 +0x46 旗標，勢力的朝廷，官位的兩個效果值（「Sndata.gp」）。
- 劇本資料 0x7BA4 的 32 bytes、劇本檔頭 +0x03、+0x24。
- 名物 +0x0F 旗標。
- 道路圓點 1–5 類的地形意義。
- Mainanm.gp 108,300 之後、Maincmd.gp 段落邊界、Hunitpat 的 mask 與幀對應、Losepal.pld 的用途、Maincmd2 屏風畫的色盤。
- 字型（JIS.FNT、FONT.DAT、FONT.CHR）、音樂（Music.gp、Opmusic.gp、Edmusic.gp，推測 FM／YM2608）。

## 檔案一覽

| 檔案 | 格式 | 內容 |
|---|---|---|
| `Main.exe` | MZ＋RLE 壓縮（「Main.exe」） | 主程式；內含 1180 年劇本表、戰略地圖、UI 字串 |
| `Open.exe`、`End.exe` | MZ，沒有壓縮 | 片頭、片尾 |
| `Sndata.gp` | 4 × 41,266 bytes | 劇本（不是 sound） |
| `Message.gp` | LS11 | 訊息 |
| `Savedata.gp` | 10 × 43,403 bytes | 存檔 |
| `Mainpal.pld`、`Losepal.pld` | 4 × 48 bytes | 色盤 |
| `Logo`、`Mainevt`、`Maincmd2`、`Mainitem`、`Mainstl`、`Mainmap`、`Hikback`、`Hkeshiki`、`Hkumi`、`Opendat`、`Enddat`（`.gp`） | NPK016 | 圖 |
| `Kaodata.gp`、`Kisetsu.gp` | RLE3 | 頭像、季節事件圖 |
| `Montage.gp`、`Haikei.gp`、`Hunitpat.gp`、`Hikuchi.gp`、`Hkei.gp`、`Hground.gp`、`Mainobj.gp`、`Mainanm.gp`、`Maincmd.gp` | planar | 頭像零件、合戰 sprite、地圖物件、指令動畫、UI |
| `Hchikei.gp` | 資料 | 合戰地圖高度與物件 |
| `Music.gp`、`Opmusic.gp`、`Edmusic.gp` | ❌ | 音樂 |
| `JIS.FNT`、`FONT.DAT`、`FONT.CHR`、`DOSJP.COM` | | 字型與第三方 TSR（DOSBox-X `dosv=jp` 時不需要） |

程式碼裡的檔名去掉 `H` 前綴（`B:CHIKEI.GP`、`B:IKKIUCHI.GP`…），是硬碟安裝版的改名【推】。

## 像素格式

- **3bpp／4bpp byte-interleaved planar**：每 N bytes（3 或 4）表示 8 個 pixel，**byte k 是色號的 bit k**（LSB plane 在前），MSB＝最左 pixel。
  - 依據：Grpdrv.exe 的 blitter（檔案 0x37EF）把第 0–3 byte 寫到 VGA map mask 1、4、2、8，色盤設定（0x2AD8）再經 0x24FA 的表 `00 01 04 05 02 03 06 07 …` 對調 bit 1／2 寫 DAC，兩次對調抵銷。✅ code（`genpei-zh:docs/formats.md` §10.1）
  - `utils.to_3bpp_indexes` 的順序剛好相反（第一個 byte 當 bit 2），用在本作時顏色會藍綠、膚色黃對調。
- **1bpp mask**：逐列、MSB＝最左，**bit 1＝透明**。帶 mask 的零件是「3bpp 顏色＋緊接著的 mask」。
- **RLE3**：`u16 w, u16 h`＋壓縮串流，演算法和 `utils.unpack_npk_3bits` 相同。`genpei.read_rle3` 另外回傳串流結束的位置，因為 Kaodata.gp、Kisetsu.gp 要靠這個位置往下讀。用在 Kaodata、Kisetsu、Maincmd2 中段。
  - 一個 byte b：b & 0x80 → 複製 ((b & 0x0F) + 1) × 4 pixel，來源往回 (((b >> 4) & 3) + 1) × (b & 0x40 ? w : 4)；否則再讀 b2，4 pixel 的 bit 2 取 b 低 nibble、bit 1 取 b2 高 nibble、bit 0 取 b2 低 nibble，重複 (b >> 4) + 1 次。

## NPK016

11 個檔（見檔案一覽），chunk **直接串接**，沒有 offset 表，用 magic `NPK016` 掃描（`genpei_extras.npk_chunks`）。和神々の大地的 NPK016 不同：那邊檔頭有 u32 offset 表。

| 位移 | 型別 | 內容 |
|---|---|---|
| +0x00 | char[6] | `NPK016` |
| +0x06 | u16 | 平面數，固定 4 |
| +0x08、+0x0A | u16 | 畫布 640×400 |
| +0x0C、+0x0E | u16 | 寬（也是解碼的 `line`）、高 |
| +0x10 | u16 × 16 | 制式色表 0x0RGB，所有 chunk 都一樣，遊戲不用 |
| +0x30 | | 壓縮資料，剛好解出 寬×高 個 4-bit 色號 |

- 解碼（`genpei_extras.npk_unpack`）：每個 flag byte 由 LSB 起控制 8 個單元。0＝literal：讀 2 bytes 解成 4 pixel（b1 bit 7 → bit 3、b1 bit 3 → bit 2、b2 bit 7 → bit 1、b2 bit 3 → bit 0，然後兩個都左移）；1＝複製：讀 1 byte b，從往回 (((b >> 5) & 3) + 1) × (b & 0x80 ? 寬 : 4) 的位置複製 ((b & 0x1F) + 1) × 4 pixel。✅ code+cross（220 張和 genpei-zh 相同；`utils.unpack_npk` 解出的也完全相同，所以 `genpei cg` 的結果和這裡一樣）
- 遊戲（Open.exe／End.exe）的解碼器是逐行的。原版壓縮串流不會跨行尾回溯、水平回溯不退到行首之前、不參照圖的起點之前；自己壓縮時要守這三條（`genpei-zh:docs/development.md` 重要發現 17）。本 repo 只解不壓。
- chunk 之後的多餘資料：`Opendat.gp` chunk 13–17 後面各有 8 bytes 的 `u16 x, y, w, h`，是下一張圖的擺放位置（寫在 `pictures.csv` 的 notes）；`Maincmd2.gp` chunk 2、3 後面接非 NPK 的圖（「其他圖檔」）。Open.exe／End.exe 用程式裡的 u32 offset 表與 size 表找 chunk（Open.exe 0x12160、0x12170、0x121F8）。

| 檔案 | chunk | 內容 |
|---|---|---|
| `Logo.gp` | 5 | KOEI 商標與字樣 |
| `Mainevt.gp` | 13 | 事件 CG |
| `Maincmd2.gp` | 4 | 640×400 場景 ×3、160×128 |
| `Mainitem.gp` | 19 | 64×64 名物圖（名物 +0x10 的圖示號） |
| `Mainstl.gp` | 13 | 12 張 64×152 月令圖（睦月…師走）＋520×168 小地圖 |
| `Mainmap.gp` | 20 | 88×360 世界地圖直條 |
| `Hikback.gp` | 1 | 一騎討ち背景 |
| `Hkeshiki.gp` | 4 | 640×400 合戰外框景色（4 種地形） |
| `Hkumi.gp` | 5 | 一騎討ち武將組合畫 |
| `Opendat.gp` | 52 | 片頭 CG，前面 1,968 bytes＝41 組色盤 |
| `Enddat.gp` | 84 | 片尾 CG，前面 672 bytes＝14 組色盤 |

## 色盤

- `.pld` 與 Opendat／Enddat 的前綴都是 48 bytes 一組：16 色 × 3 bytes，每 byte 一個 4-bit 值，順序 **B、R、G**，換成 8-bit 乘 `0x11`（`genpei.load_mainpal`）。✅ code+capture（色 1–7 讀成 BRG 是 PC-98 數位 8 色的排列；源頼朝頭像和 `genpei-zh:docs/screenshots/phase1-message-chinese-1.png` 相同）
- `Mainpal.pld` 4 組只差色 9 與 15，是四季（0 春、1 夏、2 秋、3 冬），地圖與合戰景色依季節換色；3bpp 圖只用色 0–7。第 0 組：`#000000 #1144aa #dd4400 #ee8855 #009933 #77bbbb #ffbb44 #ffffdd #332200 #334400 #995533 #cc9944 #778855 #112244 #aaaabb #aabb44`
- 以前 `genpei.py` 有一組從截圖量出來的色表（`#1041a2` 等），nibble 相同（`#14a`），但換算不是 ×0x11，色 8–15 也和 Mainpal 不同，已經移除。
- `Losepal.pld`：4 組，整組變暗的四階，用途 ❌。
- Opendat（41 組）、Enddat（14 組）的圖用哪組由程式決定，**沒解** 🟡。`pictures.csv` 的 palette 欄：Enddat 72–77（片尾卷軸）目視確認是第 10 組（唯一一條由墨色漸到紙色的色階），其餘是啟發式（先挑點亮最多 pixel 的組，再挑相鄰 pixel 亮度差最小者），notes 欄寫 `palette guessed`。例如片頭清盛臉（chunk 8–11）應是火焰色盤，啟發式選成綠色調。

## Kaodata.gp：90 張專屬頭像

- 90 組 ×（128×160 頭像 RLE3＋128×160 mask RLE3＋2 bytes），剛好用完整個檔。
- mask 圖的色 7＝透明（露出背景），色 0＝頭像本體。
- 最後 2 bytes 是 trailer：遊戲內 64×80 頭像窗在 128×160 圖上的左上角 `(x, y)`，多為 (32,16)、(40,16)、(32,24)。
- Main.exe（展開後的檔）0x55F04 有 90 個 u32 offset，0x5606C 起是兩段各 90 個 u16 大小。
- `genpei face --game-dir` 輸出 90 張 128×160 RGBA，檔名是 `編號_x_y.png`；`genpei montage --game-dir` 依組合表輸出 3 類型 × 頭、身、眼、口的零件。DOS 與 PC-98 都可以。

## Montage.gp／Haikei.gp：組合頭像零件

- Montage.gp：頭部與身體，各 8 件。Haikei.gp 開頭 9,600 bytes 之後是眼與口，各 16 件。每件都是 3bpp＋mask，寬度是 8 的倍數。
- 每種類型的零件 offset、尺寸、位置都從 **組合表** 讀，不寫死：
  - 位置：Main.exe 解包後 DGROUP:0x59CE（含 MZ 檔頭的解包檔 0x5C23E；檔頭 0x53D0 bytes，所以在展開後的 image 是 0x56E6E）。共 3 筆 × 0x26 bytes，第 (類型 − 1) 筆（程式 0x48B9B：`0x59A8 + (code >> 14) × 0x26`）。
  - 結構：`u32 頭 offset, u32 身 offset, u16 眼 offset, u16 口 offset, u16×8（頭、身、眼、口的寬 bytes、高）, u16×4 位置, u16 頭像窗`。
  - 位置的編碼：128×160 緩衝區，每列 16 bytes，`x = (v mod 16) × 8`、`y = v ÷ 16`。

| 類型 | 名稱 | 頭 | 身 | 眼 | 口 | 頭像窗 |
|---|---|---|---|---|---|---|
| 1 | 大鎧戴兜 | 120×78 @(0,0) | 128×99 @(0,61) | 40×12 @(40,36) | 40×27 @(40,48) | (32,8) |
| 2 | 鎧 | 72×88 @(24,0) | 128×103 @(0,57) | 40×11 @(48,37) | 40×30 @(48,48) | (32,0) |
| 3 | 直垂 | 72×77 @(32,0) | 128×99 @(0,61) | 40×14 @(40,34) | 40×25 @(40,52) | (32,0) |

- 畫的順序是 **身體 → 頭部 → 眼 → 口**（Main.exe 0x48B36 起），各依自己的 mask 疊上。沒被任何零件蓋到的地方是透明。

## 頭像碼（武將 +0x1A）

- 0–89：Kaodata.gp 第 n 張（0–79 武將各一張，80–89 給 390–399 的非武將角色）。
- ≥ 0x4000：組合頭像，bit 15–14＝類型（1–3）、13–11＝頭、10–8＝身、7–4＝眼、3–0＝口。
- 四個劇本同一人的頭像碼都相同（匯出時會檢查）。400 人都有頭像：90 人用 Kaodata，310 人用組合頭像，組合碼沒有重複。

## 背景與遊戲內頭像窗

- Haikei.gp 開頭是 5 張 64×80 的背景（3bpp、無 mask，共 9,600 bytes）：綠野河川、藍色山影、淺藍瀑布、岩壁、雲天。
- 遊戲裡只顯示 64×80 的頭像窗，從 128×160 圖 1:1 裁出。透明處填背景 **(武將編號 >> 1) mod 5**（Main.exe 0x49048）。
- Kaodata 頭像在遊戲裡也墊同一組背景、同一條公式。匯出時，兩種臉的人物都帶 `bg`，背景放在資料集頂層的 `backgrounds`。
- 匯出把零件與背景放 `pixels.bin`，90 張 Kaodata 頭像放 `portraits.bin`（image ref 第 4 個元素為 1）。
- ✅ capture：`genpei-zh:build/captures/main_002`–`008`（増尾兼房、亀井重清、鈴木重家、江田弘基、平時実、源行家、武蔵坊弁慶）、`main_009`（源義経）、`main_000`（源頼朝）、`main_018`（琵琶法師）的 64×80 範圍逐 pixel 相同（差異 0／5,120）；背景公式由 9 位武將吻合。

## Sndata.gp：劇本

4 個劇本 × 41,266 bytes（1180.10、1183.7、1184.10、1185.10），每個是 0x26 bytes 檔頭＋資料表。`tables/*.csv` 每列都有 `scenario` 欄 0–3；欄名帶 `?` 是推測，`wXX`／`bXX` 是沒解的欄位（record 內位移），參照寫成 `編號:名稱`，−1＝無。

依據欄的「實機」是 `genpei-zh:docs/formats.md` §4.3：1185 年 10 月存檔裡源義経的武將情報畫面（年齢 27、知才 75、菩提 63、体力 100、武力 102、加護 85、優雅 74、無常 34、勇名 90、弓術 68、動員力 2200、兵質 70、伊予守、平安京、棟梁，宝物 7 件）。這張是中文化後的畫面，日文版狀態視窗沒有截圖。

### 檔頭（0x26 bytes）

| 位移 | 內容 | 狀態 |
|---|---|---|
| +0x00 u16 | 年 | ✅ capture |
| +0x02 u8 | 月 − 1 | ✅ capture（1180 年 10 月） |
| +0x03 u8 | 2、1、2、2，存檔裡會變，疑與季節有關 | ❌ |
| +0x04 u16 × 16 | 登場勢力，−1 結尾 | ✅ code |
| +0x24 u16 | 四個都是 380 | ❌ |

### 資料表（相對於劇本資料起點）

| 位置 | 筆數 × 大小 | 內容 | 輸出 |
|---|---|---|---|
| 0x0000 | 400 × 71 | 武將（390–399 是かむろ、賊、吉次、商人、静、政子、白拍子、琵琶法師、後白河法皇等非武將，身分 7） | `generals.csv` |
| 0x6EF0 | 16 × 20 | 勢力（最後一筆空） | `clans.csv` |
| 0x7030 | 39 × 76 | 據點（肥後国府…平泉） | `places.csv` |
| 0x7BA4 | 32 bytes | ❌（四劇本不同） | `scenarios.csv` 的 `unknown32` |
| 0x7BC4 | 8 × 9 | 地方（九州…奥州） | `regions.csv` |
| 0x7C0C | 256 × 19 | 官位（同名多筆＝名額） | `ranks.csv` |
| 0x8F0C | 256 × 18 | 名物（同一名物每件一筆） | `treasures.csv` |

Main.exe（展開後的檔）0x4A570–0x54690 是同一套表，和 1180 年劇本逐 byte 相同，但後段順序不同：地方 0x7BD0、名物 0x7C20、官位 0x8E20。`genpei_extras.py` 每次都比對，四段的差異都是 0 bytes。✅ cross

### 武將（71 bytes）

| 位移 | 型別 | 內容 | 狀態 |
|---|---|---|---|
| +0x00 | char[7] | 姓（SJIS，NUL 補齊；部分用空白補齊） | ✅ |
| +0x07 | char[7] | 姓讀音（半形片假名） | ✅ |
| +0x0E | char[5] | 名 | ✅ |
| +0x13 | char[7] | 名讀音（6 字的會用到 +0x18） | ✅ |
| +0x1A | u16 | 頭像碼 | ✅ code+capture |
| +0x1C | u16 | 血緣碼：兄弟相同；等於另一人的頭像碼＝那人的子女；400 以上＝父親不在遊戲中的兄弟組 | ✅ cross（1180 年 82 組父子合史實） |
| +0x1E | u8 | 1180 年時的年齡 | ✅ capture（22＋5＝27） |
| +0x1F | u8 | 據點，不隨劇本變，疑為本據 | 🟡 |
| +0x20 | u8 | 特技：bit 0 音楽、1 和歌、2 奇略、3 操船 | ✅ capture |
| +0x21 | u8 | bit 0 僧、1 女、2 公家、3 各勢力棟梁與一門（推測）、7 遊戲中才出現 | bit 0–2 ✅ cross；bit 3 🟡 |
| +0x23 | u16 | 同據點武將串列的下一人 | ✅ code（313 個連結全部同據點） |
| +0x25 | u16 | 主君？（1185 年義経已是棟梁仍指向頼朝） | 🟡 |
| +0x27 | u8 | 身分：0 御家人、1 棟梁、2 代官、5 在野、7 死亡／未登場；6 疑為落武者 | 0/1/2/5/7 ✅ |
| +0x29 | u16 | 官位 | ✅ capture（107＝伊予守） |
| +0x2B | u16 | 動員力（開局後改成 官位 +0x0E × 100） | ✅ capture |
| +0x2D | u8 | 多為 5，部分＝動員力／100 | ❌ |
| +0x2F | u8 | 兵質 | ✅ capture |
| +0x31–0x39 | u8 × 9 | 武力 勇名 弓術 知才 優雅 忠節 菩提 無常 加護（不含宝物加成） | ✅ capture |
| +0x3A | u16 | 所持宝物串列的第一件，之後沿名物 +0x0B | ✅ capture（義経 7 件、順序相同） |
| +0x3C | u16 | 所屬勢力 | ✅ |
| +0x3E | u16 | 所在據點 | ✅ capture |
| +0x40 | u16 | 劇本中全 −1，存檔裡會變 | ❌ |
| +0x42 | u8 | 体力 | ✅ capture |
| +0x43–0x46 | u8 × 4 | 劇本中全 0，執行期狀態 | ❌ |

- 宝物加成：畫面值＝記錄值＋同一種類效果最高的一件（刀剣加武力與勇名、鎧與兜加勇名、兵書加知才）。只驗證過義経一人 🟡。
- `koei_stats.load_genpei_stats`、`dekoei.py koei-person genpei-dos --game-dir ../games/genpei-dos`（或 `genpei-pc98`）輸出能力 CSV；日文欄名取自 PC-98 `MAIN.EXE` 0x58962 的一覽表（名前 年齢 忠節 知才 武力 優雅 勇名 勲功 体力 兵数 兵質 弓術 菩提 加護 無常 和歌 音楽 奇略 操船 身分）。勲功、動員数、兵数是執行期的值。

### 勢力（20 bytes，u16 × 10）

| 位移 | 內容 | 狀態 |
|---|---|---|
| +0x00 | 棟梁（−1＝空） | ✅ |
| +0x02 | 種別：0 源氏、1 平氏、2 藤原氏、3 豪族 | ✅ |
| +0x04–0x0A | 對勢力 0–3 的友好度，自己 100，不存在 −1 | ✅ |
| +0x0C | 色別（旗色），同一家族跨劇本同色 | ✅ cross |
| +0x0E | 朝廷（5–50） | 🟡 |
| +0x10 | 政権：佔平安京的勢力為 1 | ✅ cross |
| +0x12 | 恆 0 | |

### 據點（76 bytes）

名稱 char[9]、讀音 char[9]，之後 u16：

| 位移 | 內容 | 狀態 |
|---|---|---|
| +0x12 | 鄰接據點 × 7（−1 補齊，全部雙向） | ✅ |
| +0x20 | 所屬武將串列頭，第一人恆為棟梁或代官 | ✅ |
| +0x22 | 另一個串列頭（劇本中全空，疑為捕虜） | 🟡 |
| +0x24 | 在野武將串列頭 | ✅ |
| +0x26 | 地方 | ✅ |
| +0x28 | 所屬勢力 | ✅ |
| +0x2A | 人口上限？ | 🟡 |
| +0x2C | 人口 | ✅ capture（平安京 41600） |
| +0x2E、+0x30 | 商業、治安 | 🟡 |
| +0x32、+0x34 | 農業上限？、農業 | 🟡 |
| +0x36、+0x38 | 財貨、兵糧 | 🟡 |
| +0x3A | 雑兵 | ✅ capture（16000） |
| +0x3C | 雑兵質 | ✅ capture（75） |
| +0x3E–0x44 | 劇本中全 0 | ❌ |
| +0x46 | 旗標（bit 1–3 各有一些據點，bit 4 遊戲中才出現） | ❌ |
| +0x48 | 恆 0 | |
| +0x4A | 戰略地圖節點 | ✅ code+cross |

### 地方、官位、名物

- 地方（9 bytes）：名稱 char[6]、u8 恆 0、u16（25–50）❌。
- 官位（19 bytes）：名稱 char[13]；+0x0D 0x50＝有人任官、0xFF＝空缺（和武將 +0x29 一一對應，四劇本吻合 ✅）；+0x0E 動員力 ÷ 100 ✅；+0x0F、+0x10 兩個效果值（武官 +0x0F 大、大臣與卿 +0x10 大，推測武／文 🟡）；+0x11 u16 恆 0。
- 名物（18 bytes）：名稱 char[11]；+0x0B u16 同一持有人的下一件 ✅；+0x0D 種類 0–10＝名馬 刀剣 鎧 兜 鞍 楽器 歌集 美術 兵書 唐物 珍宝（Main.exe 字串表順序）✅；+0x0E 效果值 ✅ capture；+0x0F 旗標 ❌；+0x10 圖示號 0–18（Mainitem.gp）✅；+0x11 恆 0。持有人只能從武將 +0x3A 反查。

### 存檔 Savedata.gp

10 格 × 43,403 bytes，沒有檔頭：每格 0x69 bytes 格頭（+0 u16 年、+2 u8 月、+13 棟梁名；+0x13 起是類似劇本檔頭的一份；空欄以 `00 b4 90 00` 開頭），之後同格式的資料，順序不同：武將在 +0x69，勢力之後多約 2 KB 執行期資料（疑為軍團），據點在資料 +0x7846、地方 +0x83DA、官位 +0x8422、名物 +0x9722。🟡（本 repo 沒有讀它的程式）

## 戰略地圖與合戰地圖

戰略地圖是節點圖：據點與道路上的圓點都是節點，部隊沿節點移動。表在 Main.exe 的 DGROUP（DGROUP＝展開後的檔 0x56870）：

| 檔案位置 | DGROUP | 內容 |
|---|---|---|
| 0x57044 | 0x07D4 | 39 × (u16 x, u16 y)：據點在小地圖（Mainstl.gp 520×168）上的座標 |
| 0x58EF8 | 0x2688 | 156 × 4 × (u16 鄰接節點, u16 恆 1)，156＝無；380 條有向邊全部對稱（190 條路） |
| 0x598B8 | 0x3048 | 156 × 11 bytes 節點表 |

節點（11 bytes）：

| 位移 | 內容 | 狀態 |
|---|---|---|
| +0 | u16 x（世界地圖上的像素，24 的倍數） | ✅ cross |
| +2 | u16 y（8 的倍數） | ✅ cross |
| +4 | u8 類型：0 據點（39 個，對應據點 +0x4A）；1–5 道路圓點；6 海路（31 個） | ✅ |
| +5 | u16 恆 −1（執行期，疑為佔據的部隊） | 🟡 |
| +7 | u8 合戰地圖（Hchikei.gp 0–37） | 🟡（強） |
| +8 | 3 bytes 恆 0 | |

- **(x, y) 是節點 24×16 格的左上角**，圓點（12×10 橢圓）與城畫在格子正中，地圖上的位置是 **(x + 12, y + 8)**。✅ cross（本 repo 2026-11-10）：156 個節點在這一點的地圖色號，同類型完全一致，據點全是色 8（城），1 類 4、2 類 6、3 類 4、4 類 2、5 類 5、6 類 1（圓點的填色）；`map/nodes.png` 畫出每個節點與路，全部落在圓點與城上，路沿著地圖上的道路。`nodes.csv` 的 `cx`、`cy` 是這一點。
- 道路圓點 1–5 類的顏色：1 綠橙相間、2 橙、3 綠、4 紅綠相間、5 淺藍、6 海路藍；地形意義 ❌。
- 合戰地圖：一般道路節點用 0–29；據點只用 30–36，其中鎌倉 30、平泉 31、福原 32、屋島 33 專用，其他共用 34–36；海路全是 37。Hchikei.gp 物件表中只有 30–36 有柵，37–39 的高度圖全平（水面）。
- 檢查（`genpei_extras.py` 每次印出）：邊全部對稱、39 個據點都在類型 0 的節點上、節點在自己類型的色號上 156/156。

### 世界地圖 Mainmap.gp

20 條 88×360 直條；每 4 條（352 px）一組，組與組之間重疊 16 px（第 i 條放在 88i − 16⌊i/4⌋），拼起來 1696×360，最右邊是蝶與鶴的裝飾。`map/worldmap_<季>.png` 四季各一張。✅ cross（和 genpei-zh 的四張逐 pixel 相同；重疊部分 genpei-zh 逐 pixel 比對過）

### 合戰 Hchikei.gp

不是圖。0 起 40 筆 × 196 bytes：14×14 u8 角點高度（0–8），對應 13×13 hex；0x1EA0 起 37 筆 × 60 bytes：物件清單，u8 三元組 (type, a, b)、type 0 結尾，格子＝a × 13 ＋ b；type 1／2 疑為柵、type 3 為樹（依季節換圖）🟡。`map/battle_maps.csv`、`battle_objects.csv`（255 個物件）。

## Message.gp

LS11（`ls11.ls11_decode_parts`，檔案表 big-endian）。genpei-zh 曾把表讀成 little-endian，以為是「15 筆劇本描述」。

| block | packed | unpacked | 訊息數 |
|---|---|---|---|
| 0 | 15,550 | 21,799 | 599 |
| 1 | 4,368 | 5,899 | 174 |
| 2 | 4,884 | 6,014 | 220 |
| 3 | 4,359 | 5,685 | 174 |
| 4 | 4,476 | 5,487 | 138 |

- 每個 block：u16-LE offset[n]（offset[0]＝2n）＋訊息。訊息以 `05 05 05` 結尾（一則沒有、一則後面多 `00`），`text/message.csv` 的 `end` 欄是結尾 bytes。
- 控制碼：`0A` 換行（`\n`）、`ESC C d` 顏色（`{C6}` 標題色、`{C7}` 還原）、`ESC K`／`ESC H` 半形假名改以片假名／平假名顯示、printf 參數（`%s %u %4u %B1 %B2 %N1..3 %W1 %D1`）。
- 半形假名＝平假名：訊息裡的假名多半存成半形片假名，引擎預設畫成平假名，`ESC K` 之後才畫片假名。`message.csv` 照遊戲顯示的寫，`{K}`／`{H}` 不列出。
- ✅ code+capture（genpei-zh 回寫後 `genpei-zh:docs/screenshots/phase1-message-chinese-1.png`、`-2.png` 實機正確；1305 則全改的壓力測試也對出畫面與 id 的對應，例：開局軍議 4-000～4-004、來投武將 1-021～1-026）；`message.csv` 和 genpei-zh 的 `extracted/text/message.tsv` 1305 則逐字相同（cross）。
- 1,305 則、約 26,300 字：戰報、軍議／進言、事件、死亡、朝廷、合戰結果、操作提示、遊戲說明。

## Main.exe

- **RLE 壓縮**（`genpei.unpack_main_exe`）：入口 `5440:0001` 的 stub 先在記憶體展開再跳到 `0000:0B86`。stub 段：+0x10 先往上搬的段落數；+0x2B 控制 record 數（0x81F）；+0x1977 往回讀 record：b0（bit 0 字面值長度 2 bytes、bit 1 填充長度 2 bytes，高位元組＝b0 >> 2）、字面值長度、填充長度、填充值，從映像尾端往前寫（字面值從 stub 正下方往回讀）；+0x8B relocation 筆數（5,354），+0x1978 往後讀；+0xBF／+0xB7／+0xBC 真正的 CS:IP、SS、SP。✅ emu（genpei-zh 展開成普通 MZ 後實機可玩）
- 本 repo 的 `unpack_main_exe` 只展開 load image，不重建 relocation；`genpei_extras.unpacked_main` 在前面補 0x53D0 bytes 的 0，讓位移和 genpei-zh 展開後的檔一致（本筆記的 Main.exe 位移都是這個）。
- 分區：0–0x4A570 檔頭（0x53D0）＋程式；0x4A570–0x54690 劇本表；0x54690 之後 UI 字串，主體在 DGROUP（0x56870，由啟動碼 `mov di, 514Ah` 得知）。
- Main.ori 是同一份壓縮資料：2 KB 之後只差 45 bytes（硬碟化），前 2 KB 另包一層、stub 不同（沒解，不需要）。

### 執行檔字串（`text/`）

- `main.csv` 496 條（595 處）、`main_tables.csv` 1561 條（name 937、reading 624）、`open.csv` 37 條、`end.csv` 41 條；同一字串合併，`offsets` 列出全部位置。✅ cross（位移、長度和 genpei-zh `extracted/text/*.tsv` 完全相同）
- 掃法（`genpei_extras.exe_strings`）：只掃 DGROUP（Open.exe 0x11C40、End.exe 0x14DB0 起；Main.exe 從 0x54690 起），NUL 結尾、含全形字的 Shift-JIS 串；字串常緊接在指標表之後，指標的 bytes 會解成「^3」「G!G」之類黏在前面，從第一個合理的位置切掉；只收 JIS X 0208。
- 選單字串用空白補齊來置中（`bytes` 含空白）。

## End.exe 與結局

- MSC 程式，沒有壓縮，MZ 檔頭 0x1600 bytes，DGROUP 段 0x137B（檔案 0x14DB0）；下列位址是「檔案位置 − 0x1600」。
- 不讀存檔。唯一的輸入是 Genpei.com 的 INT 65h 服務（AH＝0 回傳 cs:[0x53B]；1／2 存取 21 bytes；3–8 六個 word 槽）。
- Main.exe（展開後的檔 0x10526）只呼叫一次 `AX=0600h, BX=勝者種別`（勢力 +0x02：0 源氏→0、1 平氏→1、其他→2），End.exe 0x8444 `AX=0601h` 讀回。所以結局只有 3 種，依勝者的勢力種別。
- 片尾流程：0x9916 依結局分派（0→chunk 2、3、14、15；1→0、1、11–13；2→4、5、19–21），0x9FAE 尾聲 CG（0→24／25 紅葉、1→28／29 海上社殿、2→26／27 雪景），卷軸 72–77 三種結局相同。Enddat 6–8、22、23、66–71 沒有被引用。
- ✅ code+capture（genpei-zh `tools/endview.py` 以 13 bytes 的假 Main 直接設定結局，三種都播到 KOEI 標誌；錄影在 genpei-zh）

## 其他圖檔（還沒移植）

genpei-zh `tools/dump_gfx.py` 已切出、本 repo 還沒寫程式的 planar 圖（全部無檔頭、byte-interleaved）：

- Hground.gp：hex 地形 tile，4bpp 寬 48、色 0 透明；3 組 × 37,440 bytes（每組 65 片，高 36／30／24／18／12），第 4 組（112,320 起）3 片水面；Main.exe 0x55918 有 129 個 u16 tile offset。
- Hunitpat.gp：合戰部隊 sprite，3bpp 寬 32；陸戰（0）與水戰（74,048 起）各有騎馬 26、旗 5 色 × 13、mask 39、步弓兵 52、mask 26；148,096 起柵與樹。mask 與幀的對應 ❌。
- Hikuchi.gp：一騎討ち騎馬 3bpp 寬 80：23 張 80×48＋mask（33,120 起）、12 張 80×16 馬腳＋mask（44,160、49,920 起）。
- Hkei.gp：2 張 96×96 3bpp。
- Mainobj.gp（4bpp）：5 張 24×32 武者、32 張 16×32 旗（1920 起）、16 張 24×27 扇（10112 起，中等信心）、15296–23648 寬 24 的地圖圖示、23648 起 7 張 16×16 圓環。
- Mainanm.gp：每場景一張 3bpp 160×128 背景＋4bpp 人物幀；0–108,300 已逐張確認，之後 ±2 列。
- Maincmd.gp（4bpp）：0–3,200 柱飾、40,128 起 11 顆 32×32 指令按鈕（命令 終了 地図 一覧 機能 説明 内政 軍事 人事 外交 計略）確定，其餘段落邊界是估計。
- Maincmd2.gp：NPK chunk 0–3；0x1507C 1,152 bytes 的 4bpp 96×24 名牌框；0x165A7–0x25033 10 張 RLE3 160×128 場景；0x25033 4bpp 640×400 屏風畫（色 8–15 的色盤 ❌）；0x44433 4bpp 48×1432＝4 條 48×358 毛筆字（「驕れる者も久しからず」等，勢力滅亡時顯示，只用色 0、7、14）。
  - 舊的 `genpei cg` 對 Maincmd2 的特殊處理（`cmd2word.png` 用 3bpp 64 寬）是錯的，正確是 4bpp 48 寬。

## PC-98 版（`genpei-pc98`）

來源是 `games/archives/pc98/[PC98] 源平合戦.zip`（5 片 FDI）（2026-11-08 移到 `games/archives/to-delete/`，2026-11-09 已刪除；遊戲檔全部和 neo-kobe 的 `Genpei Kassen [HD].zip` 裡的 HDI 相同，留 HDI），每片解在 `games/archives/pc98/disks/genpei-pc98/`，合併放在 `games/genpei-pc98/`。`VERSION`：「源平合戦」For PC-9801RA~ Series，9.21,1994 Ver. 1.3 Rel 1.0。

- `MAINPAL.PLD`、`MONTAGE.GP`、`HAIKEI.GP`、`KAODATA.GP` 和 DOS 版逐 byte 相同，匯出的 `pixels.bin`、`portraits.bin` 也和 `genpei-dos` 相同。
- `MAIN.EXE` 沒有壓縮（MZ 檔頭 0x5490 bytes），組合表（3 筆 × 0x26 bytes，格式同上）在檔案 0x5DAF4，內容和 DOS 的相同。
- `SNDATA.GP` 格式相同，400 人的頭像碼和 DOS 完全一致；名字只有 393 不同：DOS「宋商人」、PC-98「宗商人」（照錄，`nameHistorical` 填宋商人）。
- ✅ cross：DOS 和 PC-98 的 4 劇本 × 400 人，武將 +0x1A–0x46 逐 byte 相同。
- 兩版的名字都有用空白補齊的（かむろ、賊、吉次、商人、静、政子、白拍子等），`load_generals` 會去掉尾端空白。`genpei-dos` 從 2026-11-10 起可以從 `games/genpei-dos/` 匯出，但還沒重新匯出到 kaodata（kaodata 只有 `genpei-pc98`）。
- `genpei_extras.py` 只對 DOS 版測過；PC-98 的 Main.exe 沒有壓縮、位移不同，不能直接用。

## koei-wiki 匯出

2026-11-14 照 koei-wiki 的規格（`docs/persons-format.mkdn`「源平合戰」、`docs/places-format.mkdn`「交付順序」第 7 點）交出，讀取在 `dekoei/wiki_genpei.py`：

```sh
cd dekoei
../.venv/bin/python dekoei.py places-export genpei-pc98 --game-dir ../games/genpei-pc98 --out ../export/koei-wiki/places
../.venv/bin/python dekoei.py places-label genpei-pc98 --places ../export/koei-wiki/places
../.venv/bin/python dekoei.py persons-export genpei-pc98 --game-dir ../games/genpei-pc98 --out ../export/koei-wiki/persons --places ../export/koei-wiki/places
../.venv/bin/python wiki_genpei.py --game-dir ../games/genpei-pc98 --out ../export/koei-wiki/portraits
```

- **資料集 `genpei-pc98`**：全部讀 PC-98 的檔。SNDATA.GP 和 DOS 的 Sndata.gp 只差 8 bytes（393 的「宗／宋」，4 個劇本各 2 bytes），✅ cross。PC-98 MAIN.EXE 的節點表（0x5B028）、邊表（0x5A668）、小地圖座標（0x587B4）和 DOS 展開後的 Main.exe 逐 byte 相同，✅ cross。
- **人物**：
  - 400 人，`id` 是武將號，和 kaodata `genpei-pc98` 相同。
  - `stats` 是 1180 年劇本的 9 項能力加体力。能力在劇本之間會變（370 人），所以各劇本的值另放 `scenarios[].stats`。
  - 年齢、兵質、動員力、体力、特技、血緣碼在四個劇本都相同。
  - `born` 是 1180 減年齡。
  - `scenarios` 的 `status` 取身分碼。7 在劇本裡都是死亡：沒有人先 7 後活，所以沒有「未登場」。死亡的劇本不列所屬與所在。6 只出現 2 次（瀬尾兼康、平重衡，推測是落武者），寫進 `uncertain`。
  - `lord` 是所屬勢力的棟梁。
  - 僧／女／公家取 1180 年。大江広元等 4 人之後成為御家人，公家旗標就沒了，`notes` 有寫。
  - 非武將 390–399：名字整個存在姓的欄位，讀音延伸到名的欄位。年齡、能力、旗標都是 0，所以只交名字、讀音與頭像。
- **據點**：
  - 39 個，`level` 是「拠点」（Main.exe 的字串「拠点を選択してください」）。
  - `adjacent` 是據點表的鄰接欄。koei-wiki 原本要的是沿道路、海路節點展開的結果，但展開後和鄰接欄不同：
    - 連海路一起展開時，22/39 相同。海路連成一片，一個據點可以到 15 個。
    - 只走陸路時，24/39 相同。
    - 遊戲用的是鄰接欄，所以交鄰接欄。
  - `pos` 是節點格中心，對 `places/genpei-pc98/world/world-{spring,summer,autumn,winter}.png`（1696×360，讀 PC-98 MAINMAP.GP、MAINPAL.PLD，和 DOS 的 `extract/map/worldmap_*.png` 逐 pixel 相同，✅ cross）。
  - `world-spring-labelled.png` 是春季圖放大 2 倍（3392×720），39 個據點標「編號 名稱」，放法同三國志IV、項劉記（`notes/san-maps.md`），圖示框取 `pos` ± 24（放大後）；道路點、海路點不標。koei-wiki 2026-11-14 要求放進匯出。
  - 商業、治安、農業、財貨、兵糧標 `uncertain`（`scenarios.<欄>`）。
- **人物像**：`portraits/genpei-pc98/bust/<id>.png` 是 128×160 透明背景，`window/<id>.png` 是遊戲的 64×80 頭像窗（墊背景）。window 的 RGBA 和 kaodata `checksums.json` 的 `ch:<id>` 400/400 相同，也就是 R2 上 `faces/genpei-pc98/` 那一份。
- **檢查**：據點 288 項（加上大地圖後 327 項）、人物 3967 項，0 不符。koei-wiki 的 `verify_persons.py` 8198 項，0 不符。

## 下一輪候選

- Opendat／Enddat 的色盤 — 前置：無；做法：在 Open.exe／End.exe 找 chunk offset 表（0x12160 等）旁邊的色盤號，或照 End.exe 0x9FAE 那種「色盤位置、offset、大小表」（DGROUP 0x5D0）整理。
- 合戰與 UI 的 planar 圖 — 前置：無；做法：照「其他圖檔」的切法加進 `genpei_extras.py`，和 genpei-zh `build/dump/` 逐張比對。
- 據點 +0x2E–0x38 的內政欄 — 前置：日文版的據點情報截圖；做法：DOSBox-X（`genpei-zh:tools/dosbox/genpei.conf`，要 `xms=false`、`ems=emsboard`，否則選棟梁後當掉）讀 `orig-s1` 存檔，看平安京的商業、治安等，和存檔欄位對照。
- 武將 +0x2D、+0x40–0x46、名物 +0x0F — 做法：比對劇本與存檔，找 Main.exe 讀寫這些欄位的程式。
- 道路圓點類型 1–5 的意義 — 做法：找 Main.exe 讀節點 +4 的移動成本程式。
- PC-98 版的 `genpei_extras` — 做法：PC-98 MAIN.EXE 沒壓縮，檔頭 0x5490；以 DOS 的節點表、劇本表內容搜尋位移。

## 負面結論

- Sndata.gp 當成音效：不是，`Sn`＝scenario；音樂在 Music.gp 等。
- 武將 record 從 0x24 起、第一筆以 u16 0x017C 開頭（genpei-zh `analyze_sndata_gp.py`）：錯 2 bytes，0x017C 屬於檔頭，record 從 0x26 起。
- Message.gp 的檔案表讀成 little-endian：錯，LS11 的表是 big-endian。
- Main.ori 當成 PKLITE：不是，和 Main.exe 同一種 RLE 壓縮。
- Maincmd2 的毛筆字當成 3bpp 64 寬：錯，是 4bpp 48 寬（`genpei cg` 的舊程式碼還照錯的寫）。
- Maincmd 的 32 寬段當成 64 寬：看起來像左右兩半交錯，是 32 寬。
- 節點 (x, y) 當成圓點中心（genpei-zh 的說法「與地圖上城與圓點位置吻合」）：在 (x, y) 取地圖色號，同類型的節點顏色不一致；(x, y) 是格子左上角，圓點中心是 (x + 12, y + 8)。
- DOSJP.COM：DOSBox-X `dosv=jp` 下不需要。
