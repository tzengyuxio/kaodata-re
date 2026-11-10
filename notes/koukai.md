# 大航海時代（KOUKAI, DOS 中文版）頭像相關格式

`dekoei.py export koukai-dos` 用到的格式。來源是 `games/archives/dos/大航海時代_中文版_uwc.zip` 的 `sea1/`，解開放在 `games/koukai-dos/`。

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

### 能力

- 仲間情報視窗（PC-98 0x311CE）依序顯示 年齢、統率力、判断力、知力、勇気、強靭さ，以及戦闘経験／Ｌｖ、航海経験／Ｌｖ；英文 DOS 版的標籤是 Authority、Judgement、Intellect、Courage、Strength。
- 能力表 DS:0x13F0＋n×10（0x332:0xE2）在 `SHINARIO.CIM` 0x13AE（DOS 0x13CE，PC-88 0x1320）：+0 年齢、+1–5 五項能力、+6／+8 u16 戦闘／航海経験。只有 21 筆（0 レオン、1–20 航海士），男性 21–40（敵對提督）沒有能力記錄。男性記錄 +0xF、+0x10 是戦闘Lv、航海Lv（`koei_stats.load_koukai_stats`）。
- ✅ code（0x312AD 起的 printf 參數）；DOS、PC-98、PC-88 和英文版的值逐 byte 相同（cross）。
- 🟡 忠誠度在 DS:0x125A（執行時才填）；名声、金貨只有主角有。❌ 男性 +0x13 低 4 bit（41 人都是 1）；中文版的標籤沒查（`MAIN.EXE` 沒解開）。
- 指令：`dekoei.py koei-person koukai-pc98`。

## 沒有人物使用的頭像（1–12）

- 只由 0x9F31 的 mode 1 直接指定頭像號叫出。名字是對照 `koukai-fc` 外觀取的，沒逐一追到程式碼，中文版的實際用語（含「土耳其」）也沒查（中文 MAIN.EXE 沒解開）。
- 1–3 葡萄牙／西班牙／土耳其國王；4 道具店、5 造船廠、6 交易所、7 酒館、9 港口、10 王宮；8 老航海士（人物 0xFF 的預設臉）；11 主教（暫定「教會」，FC 沒有）；12 包頭巾的老婦人（對應 FC 宿屋，暫定「旅館」）。

## PC-98 版（`koukai-pc98`）

來源是 `games/archives/pc98/[PC98] 大航海時代.zip`（SYSTEM、海 兩片 FDI）（2026-11-08 移到 `games/archives/to-delete/`，2026-11-09 已刪除；兩片逐 sector 和 `~/game-library/_original/pc98/neo-kobe-2017-11-17/Koei/Daikoukai Jidai/Daikoukai Jidai [FD] [Set 1].zip` 的其中兩片相同），每片解在 `games/archives/pc98/disks/koukai-pc98/`（`SYSTEM/`、`UMI/`），合併放在 `games/koukai-pc98/`（兩片的 `OPEN.EXE` 不同，用 SYSTEM 片的，匯出用不到）。檔案日期 1990-07-20。`MAIN.EXE` 沒有壓縮（MZ 檔頭 0x6A00 bytes），DGROUP 段值 0x39F1；下文是映像（檔案 − 0x6A00）位址。

- `KAO.PUT` 160512 bytes，是 DOS 版的兩倍：排法相同，但全高 64×80（每列 24 bytes，byte 0／1／2 畫到 B／R／G 平面，即 `san2_jp_pixels`）。DOS 版的 64×40 頭像和 PC-98 的不同（人物、順序相同，但姿勢、表情不同，不是縮小）：那是 PC-88 原版的 200 線圖，DOS 直接沿用，PC-98 才是重畫的（見下方 PC-88 一節）。
  - 組合臉 0x7292：每國 0x5D00 bytes（表 DS:0x2B32），零件位置、大小、畫到的列都是 DOS 的兩倍（上 0x3F0、下 0x4080／0x390、眼 0x1F80／0x180、鼻 0x2B80／0x180、口 0x3180／0x1E0），組成 1920 bytes 的全高臉。五官 OR 疊上，檢查過全部組合，和上下及彼此都不重疊。
  - 頭像 0x749C：`seek(0x17400 + n × 0x780)`；女性 i 用頭像 13＋i，男性 0xFF 用頭像 8，同 DOS。
- 色盤：類比色盤（0x11AC，B、R、G 各 4 bit）初始值 DS:0x2800 就是標準 8 色，數位模式（0x812）同樣，所以用 `SAN2_JP_PALETTE`。
- 人物：`SHINARIO.CIM` 記錄格式同 DOS，位置早 0x20 bytes（女性 0x7B0、男性 0x900），姓名是 Shift-JIS（`koei_games.load_koukai_pc98_people`）。男性的臉碼（+0x11–0x13）和 DOS 版完全相同。
- 國名用 `MAIN.EXE` 的寫法：ポルトガル、イスパニア、イスラム、海賊。頭像 1–12 的身分沿用 DOS 版的判讀（國王、設施、老航海士），名字換成日文（道具屋、造船所、交易所、酒場、港、王宮、教会、宿屋）；遊戲字串裡只找得到交易所、酒場、王宮、ギルド，其餘是暫定。

## X68000 版（不另做資料集）

來源是 Internet Archive `softwarelibrary-x68k` 的 `daikoukai_jidai_19xx_koei_disk_x68k`（Mai、Umi 2 片 DIM，各有一份 `[a]`，檔案相同）。和 `koukai-pc98` 的頭像、人名、色盤完全相同，kaodata 只在 `koukai-pc98` 標上 X68000 版：

- Umi 片的 `KAO.PUT`、`NEWGAME.DAT`、`COLOR.CIM` 和 PC-98 逐 byte 相同（`BDAT.DAT` 不同）。
- 沒有 `SHINARIO.CIM`：劇本資料在 Mai 片的 `KMAIN.Z`（未壓縮）裡，女性與男性表在 PC-98 `SHINARIO.CIM` 位置減 0xA 的地方（男性 0x8F6），0x7B0–0xC34 逐 byte 相同。
- 色盤：`KMAIN.Z` 檔案 0x25C2 起是數位文字色盤 `0001 003F 07C1 07FF F801 F83F FFC1 FFFF`（bit 0 藍、bit 1 紅、bit 2 綠），和 PC-98 的數位 8 色相同。
- `VER.DAT` 是編碼過的，沒有解讀。

## PC-88 版（`koukai-pc88`）

`dekoei.py export koukai-pc88` 用到的差異（`build_koukai_dos(pc88=True)`）。

- 來源：Neo Kobe 2016-02-25 的 `~/game-library/_original/pc88/neo-kobe-2016-02-25/Daikoukai Jidai/`。用 `[FD] [Set 1]`（乾淨的 80 軌映像），`[FD]`、`[Set 2]` 的這幾個檔相同。
- 磁碟：Main、Minato、Umi、Opening 四片加 User 片，都是 YDOS 3.0，每軌 9 × 512 bytes。
- `games/koukai-pc88/` 放 Main 片的 `KAO.PUT`、`VER.DAT`，Umi 片的 `SHINARIO.CIM`、`MAIN.COM`（後兩者之外是參考用）。
- 版本：沒有明文版號，`VER.DAT` 是編碼過的。檔案日期最晚是 1990-04-25（`MAIN.OVL`、`MAIN.COM`、`INIT.CIM`）。PC-8801 是首發平台。
- `KAO.PUT` 和 DOS 版**逐 byte 相同**：DOS 沿用的是 PC-88 的 64×40 半高圖，所以頭像、組合臉照 DOS 的排法匯出（`san2_pixels`，逐列加倍）。
  - `SHIP.BIN`、`MAP.PUT`、`NEWGAME.DAT` 等也和 DOS 相同。
- 色盤：數位 8 色（`SAN2_JP_PALETTE`，palette id `pc88`），色號意義同 `san2-pc88`。這是依其他 PC-88 版類推，沒有追 PC-88 的畫圖程式。
- 人物：`SHINARIO.CIM` 的記錄同 DOS／PC-98，位置比 DOS 早 0xAC（男性 0x874、女性 0x724；`load_koukai_pc98_people(..., pc88=True)`），Shift-JIS。
  - 41 男、21 女的姓名、順序、頭像位元組、國籍都和 `koukai-pc98` 相同，`id` 一致，沒有 `nameHistorical`。
- 國名、沒有人物使用的頭像 1–12 的分組與名稱，沿用 PC-98 的日文寫法。

## 港口、交易品、道具、地圖

`dekoei/koukai_extras.py`（`cd dekoei && ../.venv/bin/python koukai_extras.py --game-dir ../games/koukai-pc98 --out ../games/koukai-pc98/extract`）把下列靜態資料寫到 `games/koukai-pc98/extract/`：`tables/ports.csv`（70）、`tables/goods.csv`（26）、`tables/fleets.csv`（21）、`items/items.csv`（31）、`ships/ship_types.csv`（旗艦＋6）、`ships/shipyard.csv`（6）、`map/world.png`、`map/world_ports.png`、`map/STIZU.png`。位址是 PC-98 `SHINARIO.CIM` 的檔案位移（執行時載入到 DS:0x42，`MAIN.EXE` 映像位址同上一節）。截圖見 `captures/screenshots/README.md`「大航海時代 PC-98 遊戲畫面」。

| 項目 | 位置與格式 | 狀態 | 證據 | 說明 |
|---|---|---|---|---|
| 港口名稱 | 0x1766 起 70 筆 × 20 bytes，+0 名稱 15 bytes | ✅ | code+capture | 0–49 是有經濟資料的港口，50–69 是其他地點（ノヴァグラナダ、アカプルコ…）；リスボン、セビリア等和遊戲畫面一致 |
| 港口位置 | +15 bx、+16 by、+17 fx、+18 fy；x＝bx×14＋fx、y＝by×14＋fy（單位是地圖 byte 的一半） | 🟡 | capture+cross | リスボン（451, 124）和出港畫面的海岸線對上；70 個裡 61 個落在海陸交界 1 格內，其餘 9 個（ヴェネチア、オスロ、ハンブルグ、ソファラ、バクダット、メッカ、グアム、コピャポ、シビル）稍遠，沒逐一查 |
| 港口 +19 | u8 | ❌ | | 0–49 是 0x1D 起的不同值，50–69 是 0；意義未解 |
| 港口經濟 | 0xD9A 起 50 筆 × 18 bytes：+0、+4 u32，+8／+9／+10 三國占有率（%），+11–17 | 🟡 | cross | 占有率在首都是 100（リスボン 100/0/0、セビリア 0/100/0、イスタンブール 0/0/100），三國順序推定是葡、西、伊斯蘭；+0、+4（リスボン 800、セビリア 950）推定是經濟／工業值，沒有對畫面 |
| 交易品名稱 | `MAIN.EXE` DS:0x1EAC 26 個 near 指標（0xA45C 的迴圈取用） | ✅ | code+capture | コショウ … ジュウタン；交易所畫面的コショウ、水晶同名 |
| 交易所行情 | 執行時讀 [DS:0x30D2] | ❌ | | 各港賣哪些貨、買價從哪裡算出都沒找到；リスボン的賣價（コショウ 80、水晶 323）見截圖 |
| 道具 | 0xA8 起 31 筆 × 15 bytes：+0 名稱 13 bytes，+13 u16 價格 | 🟡 | code | 望遠鏡 1000、六分儀 800…；價格沒有在道具屋畫面對過；哪個港賣哪些道具沒找到 |
| 船種範本 | 0x132F 起 6 筆 × 21 bytes（ラテン、レドンダ、ベルガンティン、ナオ、カラック、ガレオン），0x12C6 旗艦ヘルメス：+0 名稱 15 bytes，+15 u16、+17 u8、+18 u16、+20 u8 | 🟡 | code | 數值欄位（20/10/70…）推定是船員、大砲、容量之類，未確認 |
| 造船所船名 | `MAIN.EXE` DS:0xC7D4 6 個字串（カラヴェル … 重ガレオン） | 🟡 | code | 和上面的範本名稱不同，兩表的關係與價格沒找到 |
| 艦隊 | 0xC34 起 21 筆 × 17 bytes：+0–3 位置（同港口），+9 u16 金貨 | 🟡 | capture | 艦隊 0 的位置是リスボン、+9 是 1000，和開局「所持金貨 1000枚」一致；其他欄位未解 |
| 世界地圖 | `NEWGAME.DAT`：u16 B 段位移、u16 C 段位移；A 段 288 × 5 bytes（u16 群組號＋3 bytes），24 × 12 群組；B 段每群組 9 個 u16 區塊號（3×3）；C 段每區塊 49 bytes（7×7 地形碼 0–52，0＝海）；全圖 504 × 252 | 🟡 | capture | 和航海畫面（1 byte＝32×32 px）的海岸線對上；`world.png` 每 byte 畫 2×2 點，海＝藍、地形碼 1–3＝綠、其他＝黃，是示意圖，不是遊戲的圖塊 |
| 群組 3 bytes、地形碼意義 | `NEWGAME.DAT` A 段 +2–4 | ❌ | | 推定是風向／海流，沒追 |
| 圖塊 | `MAP.PUT` | ❌ | | 見「負面結論」 |
| 世界全圖 | `STIZU.DAT`：640×400，B、R、G 三個 32000-byte 平面依序，bit 7 是最左點，色號 B<<2\|R<<1\|G，`SAN2_JP_PALETTE` | ✅ | code | 「MAPA DE MUNDO」古地圖；只看輸出圖，沒和遊戲畫面逐點比對 |

### 其他版本

- DOS（`koukai-dos`）：`SHINARIO.CIM` 的港口座標、經濟、船種、艦隊在 PC-98 位置＋0x20，byte 相同（名稱是光榮台灣內碼）；道具表不同，沒有對齊。`NEWGAME.DAT` 和 PC-98 byte 相同。
- PC-88（`koukai-pc88`）：道具、艦隊在 PC-98 位置 −0x8C、港口 −0x90、經濟與船種 −0x8D，記錄內容（名稱以外）byte 相同；匯出只做 PC-98。

### 下一輪候選

- 交易所行情 — 前置：找到寫入 DS:0x30D2 的程式；做法：在進交易所時下 write watch，或在 RAM 傾印裡比對リスボン的 80／323。
- 船種欄位 — 做法：在造船所畫面截圖，對照 0x132F 的數值與 DS:0xC7D4 的船名。
- 港口 +19、經濟 +0／+4、+11–17 — 做法：追 `MAIN.EXE` 裡以 `DS:0x17A8`（港口）與 `DS:0xDDC`（經濟）為基底的存取。
- 忠誠度 DS:0x125A、男性 +0x13 低 4 bit — 沒有動，維持上一節的標記。

### 負面結論

- `MAP.PUT` 照 16×16 圖塊讀是雜訊；改成 24 px 寬（每列 9 bytes 一組三平面）可得到 126 張看得出形狀的 24×16 圖塊，但地形碼到圖塊的對應沒找到 → 要先在程式裡找到畫航海畫面的迴圈才值得重試。
- 1 倍大小的航海畫面和地圖做自動比對分數都在 0.81 左右，分不出位置 → 改用 2 倍（1 byte＝32 px）手動對海岸線才對上。
- 0x28B98、0x296D2 原以為是行情計算，其實是戰利品（DS:0x4182）。
