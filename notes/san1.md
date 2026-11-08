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
- 依據是英文 DOS 版 MAIN.EXE 0x467B：組合臉 seek `((si >> 12) + 8) * 0xB40`，讀 5 張，取 0xB4／0x78／0xB4 bytes 三段（15／10／15 列）。PC-98 的對應程式在 SANGOKU.OVL 裡，檔案在磁碟上有加密（見「磁碟 A 的加密」，可以用 `san1.read_pc98_file` 解開），還沒有回頭讀。
- 所以 PC-98 是同一規則是推論，但 190 張合成後接縫都自然，各組第 14 列也幾乎相同，正好是切線。
- 匯出成 3 個 slot（上、中、下），5 個 variant（組別 6–10）。

## 人物

- 原始劇本推定在 SANGOKU.OVL 裡（檔案有加密，見「磁碟 A 的加密」；解開後還沒找劇本）（`PACKDATA.DAT` 是插圖，見「事件、插圖」）。人物改從 `SAVEDATA` 讀（`san1.load_san1_pc98_persons`）：
  - 前 300 bytes 是 10 × 30 bytes 的存檔槽標頭，之後是 10 個 22904 bytes 的槽（之後 64600 bytes 不明）。
  - 槽 k 的人物表在 300 ＋ 22904k ＋ 0x1096，255 筆 × 34 bytes（匯出讀槽 0）。舊筆記把槽長寫成 29364，所以以為其他槽是亂的。
  - 這份 SAVEDATA 的日期是 1991-08-15，有玩家存檔（槽名 "YAWARA!" 等），換一份磁碟映像時要重新確認。
- 記錄 34 bytes：+0 讀音（8 bytes 半形片假名，不匯出）、+8 姓名（3 個 little-endian JIS word）、+14 年齡、+15–20 能力、+22 u16 頭像碼、+26 城、+27 勢力。
- 255 個頭像碼和英文 DOS 版 `SINADATA.DAT` 5 個劇本完全一致，所以頭像碼不隨劇本變，從存檔取可行。
- 外字：JIS 0x7620–0x7672，字形在 `KANJIF.DAT` 的 0x4000 ＋ 32 ×（碼 − 0x7620），看字形判讀，見 `san1.PC98_GAIJI`。0x766D 起是地名用字，人名沒用到。
- 夏侯尚的「尚」存成 0xBE30（多了 bit 15），讀的時候 `& 0x7FFF`，原因不明。
- 順序和 `san1-fc` 相同，`id` 也照 FC 從 1 起算。和 FC 寫法不同的 10 人照遊戲寫法：干禁、旬攸、許収、蔡仲、雷同、李湛、諸葛謹、刑道栄、鮑龍、沙摩可，以及和 FC 相同的尚寵（向寵）。都是錯字，依 `nameHistorical` 規則（見 CLAUDE.md）填史書寫法（`SAN1_PC98_NAME_HISTORICAL`，12 筆）。陳嬉（197）找不到對應的史書人物，不填。
  - 204 劉延在劉度帳下，是劉度之子劉賢，不是東郡太守劉延：填 `nameHistorical` 劉賢（2026-11-02，依據是使用者的三國志能力表（Google 試算表，2015）的備註；`san1-sfc` 也改寫成劉賢）。DOS 版的 `nameZh` 一併改成劉賢。

## 戰場地圖

58 國各一張，14 欄 × 12 列，每格 1 byte，逐列存放；奇數欄往下錯半格排成六角格。格式和 FC 版相同（`famicom-re:sangokushi/docs/BATTLE_MAP.md`）：bit 3–5 是地形 0–5（平地、山、森林、河、城、雪山，名稱是 FC 那邊看圖取的），bit 0–2 是布陣區。

- 位置：`SAVEDATA` 每槽 +0x3278（PC-98 檔案 13220 ＋ 22904k）起 58 × 168 bytes。原始劇本推定在 `SANGOKU.OVL` 裡（解密後還沒找），所以和人物一樣從存檔讀。
- 其他版本的位置：DOS 英文版 `SAVEDATA` 12770 ＋ 22474k；X68000 主檔（原廠初始資料）`SAVEDATA` 19018 ＋ 28702k。
- ✅ cross：DOS、X68000 的 58 張地形和 FC 逐格相同；布陣區（bit 0–2）兩版和 FC 有 61 格不同（DOS 與 X68000 彼此相同）。
- PC-98 這份 `SAVEDATA` 全是玩家存檔（槽名 YAWARA! 等），各槽的地形和 FC 相同，只有幾格從 0x05（平地）變成 0x24（城）：所有槽都有 48、50 國的 (2,7)，部分槽另有 38 國 (7,8)、45 國 (3,7) 等。槽之間不一致，推定是遊玩中改寫的，🟡。槽 0 的布陣區和 FC 完全相同。
- ✅ capture：`captures/screenshots/san1-pc98/battle-04.png`（4 國 冀州）、`battle-10.png`（10 國 徐州），使用者遊玩、Claude 擷取 NP2kai（5939e0c，日文字型用 Osaka 代替）視窗。兩張的 168 格地形都和槽 0 的資料相同，只差畫面上的白圈（部隊與布陣標記）。
- 畫面：640×200 模式，每格 32×16 點，奇數欄往下 8 列；六角遮罩在 `SANMAIN.EXE 0x5D54`（64 bytes）。NP2kai 視窗是 1280×864（標題列 64），每點畫成 2×4 並有掃描線空隙，取 (2x＋1, 64＋4y＋1)、門檻 127 還原。
- 地形圖案：檔案裡找不到（`PICDATA.DAT` 113 號之後是小動畫，`PACKDATA.DAT` 是插圖，見「事件、插圖」；`KANJIF.DAT` 0x2000–0x4000 的彩色花紋圖塊排法沒確定；`SANMAIN.EXE`／`SANGOKU.OVL` 當時以為有編碼，其實是磁碟加密，解開後還沒找圖案），改從截圖切：每種地形取所有格的多數決，偶數欄、奇數欄與兩張截圖的圖案相同，6 種都有出現。PC-98 畫面上 0 平地、1 綠色山、2 水上長草（FC 叫森林）、3 河、4 城、5 灰白山頂（FC 叫雪山，多在南方地圖）。
- 輸出：`dekoei.py san1 battlemap --savedata ../games/san1-pc98/SAVEDATA --capture ../captures/screenshots/san1-pc98/battle-04.png:4 --capture ../captures/screenshots/san1-pc98/battle-10.png:10 --out ../games/san1-pc98/extract/battlemap` 寫出 `01.png`–`58.png`（448×400，列加倍）與 `terrain.png`。不畫布陣區。

## 事件、插圖

三國志沒有劇本事件，「事件」是災害、外交、戰鬥時跳出的插圖與小動畫。PC-98 的程式（`SANMAIN.EXE`／`SANGOKU.OVL`）在磁碟上有加密（見「磁碟 A 的加密」），格式是讀 DOS 英文版 `MAIN.EXE`／`SAN.OVL` 得到的，再套到 PC-98 檔案上（✅ cross：DOS 和 PC-98 的圖順序、構圖相同，PC-98 是 8 色、DOS 是 4 色）。DOS `SAN.OVL` 載入在 `MAIN.EXE` 的 0x5AA0（呼叫落在函式開頭的比例最高）。

### 插圖：`PACKDATA.DAT`

- 不是劇本：插圖都在這個檔裡（舊筆記以為 `PACKDATA.DAT` 是編碼過的劇本）。檔案前 48 KB 有一半在加密的磁區上，讀之前先用 `san1.read_pc98_file` 解開（見「磁碟 A 的加密」）。DOS `MAIN.EXE` 0x35F 讀第 n 個 512-byte block，u16 寬（點）、u16 高，接著是 0xDB3 的 RLE：
  - 前兩列原樣。
  - 之後每個 byte：0x96 n 表示從**上兩列**同位置複製 n 個 byte（n＝0 是 256），0x96 0x01 是字面的 0x96；其他是字面。
  - PC-98 每個 8 點的欄是 3 個 byte（3 個平面，順序同 `to_3bpp_indexes`），DOS 是 2 個。下一張圖從下一個 block 開始。
- 畫面是 200 列模式，輸出時列加倍（例如 192×80 輸出成 192×160）。色盤是數位 8 色（同頭像）。
- 戰鬥插圖的用途讀 DOS 程式確定（✅ code）：`SAN.OVL` 0xAF71 依攻擊種類查 DGROUP 0x8894 的表（1 一般 142、2 同時 153、3 突擊 147、4 計略 137），5 火攻另外寫死 165（0xAF5D），撤退是 159（0xB080），DOS 的 州地圖是 55（`MAIN.EXE` 0x2B9C）。PC-98 依順序對應。
- 其他插圖的用途沒有追到呼叫處，只依畫面描述（🟡）。

| PC-98 block | 尺寸（輸出） | 內容 | DOS block |
|---|---|---|---|
| 46、54、94、104、112 | 248／128 寬 | 河邊城寨、持戟兵士、舞劍女子、斬人、兩名武將 | 25、34、72、79、84 |
| 118、122、128、140、144 | | 坐車的人、一排兵士、打鬥、室內兩人、夜裡河邊的人 | 88、90、94、103、105 |
| 152、160、166 | 160×160、240×160 | 三名武將、三名文人、宮殿起火 | 111、116、120 |
| 176–238（7 張 192×160） | | 城樓前的兵士；戰鬥：計略、一般、突擊、同時、撤退、火攻 | 127–165 |
| 244、184、188 | | 山丘上的軍旗、持火光的兩人、混戰 | 169、131、134 |
| 0、70 | 320×400 | 58 國的大地圖、15 州的地圖（國號、州名畫在圖上） | 0、55 |
| 28、40、60 | 248／128／192 寬 | 穀穗上的蝗蟲、手與器物的特寫、倒塌的城郭與倒地的人 | —、—、48 |
| 252 | 640×400 | 結局（圖裡有「英雄 は見事その志を遂げた。」） | 175 |
| 306、332、374 | 576×328、640×400 | 標題的雙龍、標題畫面、開場題字 | 211、226、252 |

- block 0、28、40、60、70 這 5 張在加密的磁區上，解密後格式和其他張相同（舊筆記以為是 4 張、另一種編碼；block 28 的標頭在加密區裡，所以沒發現）。0 是 58 國的大地圖，70 是 15 州的地圖，和 DOS 0、55 構圖相同；PC-88 V1 版 `PACKDATA` 裡也有這兩張，RLE 資料 byte 相同（✅ cross）。28、40、60 的用途照畫面描述（🟡）。
- 32 張圖的 RLE 長度剛好接到下一張圖之前（✅ code：每張解完的位置都在下一個起點之前，中間只有補 0）。

### 小動畫：`PICDATA.DAT` 113 之後

- 頭像（0–112）之後是動畫：DOS `MAIN.EXE` 0x4016 讀第 n 個 512-byte block 當腳本，每個指令是一個字母 'A'–'Y'（跳躍表在 0x4242），K、M、N、S、U 與 0xFF 結束：
  - `B n`：從腳本後面再讀 n × 256 bytes（格子圖）。
  - `A w h`：之後畫的格子是 w × 8 點寬、h 列高（PC-98 每格 w × h × 3 bytes）。
  - `P k x`／`Q k x y`：畫第 k 格（從格子區 k × 360 bytes 起；DOS 是 k × 0xF0），`V x` 用同一格再畫一次；`Y y` 設預設 y。
  - `C`（5 bytes，填色塊）、`D`（6 bytes）、`T`（速度）、`W`（等待）、`L`／`R`／`O`（往左／往右移動／停）、`E`、`F n`、`G`、`H`、`I`、`J`、`X` 是畫面控制，輸出不用。
- 輸出每個動畫腳本畫到的格子（去重，依 k 排序），不重現動畫本身。
- 用途（✅ code）：`SAN.OVL` 0xB11D 投降確認（「Are you positive?」）後播 DOS 244（PC-98 354，武將與跪伏的兵士），0xB188 待命（「Mobility is now %d」）後播 DOS 254（PC-98 368，騎兵與軍旗）。其他 12 個依畫面描述（🟡）：騎兵奔馳與城樓（162）、軍旗與車（186）、推車（200、238）、跪拜（224）、遞物（262）、雪地揮槌（278）、揮斧（288）、揮刀（304）、行走的女子（318）、白衣人（328）、打鐵（334）。
- ❌ block 348、378 的腳本只有 `T A E X Y U`，沒有 `B`，後面的資料不是格子圖，也不是上面的 RLE（照 24×40、24×80 解是雜訊），沒解。

### 州的說明：`STRING.DAT`

- 17 個 512-byte block，Shift-JIS，補 0：0–1 是 MML 音樂，2–16 是 15 州的說明（順序同 DOS 英文版 `STRING.DAT`，✅ cross）。
- 文字裡的外字（Shift-JIS 0xEB9F 起＝JIS 0x7621 起）用 `USKCG.SYS` 的字形，不是人名用的 `KANJIF.DAT`：`USKCG.SYS` 是 0x22 bytes 標頭，接著每項 34 bytes（u16 JIS 碼＋16×16 字形）。0x7621–0x7628 是冀兗并廬渤彭淮襄（看字形判讀）。

### 輸出

| 指令（在 `dekoei/` 下） | 輸出 | 數量 |
|---|---|---|
| `dekoei.py san1 eventcg --game-dir ../games/san1-pc98 --out ../games/san1-pc98/extract/eventcg` | `<block>-<名稱>.png`、`anim-<block>-<名稱>/<k>.png`、`index.csv`（UTF-8-BOM：編號、檔案、內容、來源、尺寸、DOS 對應、依據） | 插圖 32 張、動畫 14 組 86 格 |
| `dekoei.py san1 strings --game-dir ../games/san1-pc98 --out ../games/san1-pc98/extract/events` | `provinces.csv`（州號、州、本文、來源、依據） | 15 州 |

### 事件文字

- PC-98 的事件訊息（蝗害、洪水、疫病、地震、一揆、外交使者等）在 `SANGOKU.OVL` 裡；檔案解密後還沒找。DOS 英文版的訊息是 `MAIN.EXE` DGROUP 的明文（0x13B0D 起的州資訊、0x1832A 起的災害與外交訊息），但沒有對到觸發條件，也沒有匯出。

### 封存前還缺

- PICDATA 348、378 兩段資料。
- 事件文字（要從解密後的 `SANGOKU.OVL` 找）。
- 插圖與動畫的用途多數是 🟡；要確定得追 DOS 的呼叫處或在模擬器裡看。

## 磁碟 A 的加密

本節的位址是磁碟 A 的 `COMMAND.COM`（2189 bytes，載入在 0x100）。

- 磁碟 A 第 5–14 cylinder 的 head 0（磁碟位移 0x4000 × cyl 起的 8 KB）每個 1024-byte 磁區都 XOR 一份 1024 bytes 的 key，key 依 cylinder 不同。檔案是連續存放的（磁碟 A 的 FAT），落在這一段的有 `SANMAIN.EXE`（磁碟 0x12000 起）、`SANGOKU.OVL`（0x20800）、`PACKDATA.DAT`（0x30800）的前 48 KB。舊筆記說「程式有編碼」「PACKDATA 有第二層編碼」都是這個。
- 解密在 `COMMAND.COM`（標題「Ver. 2.4 (87-04-20) I.yoda (Y.S.A)」，是破解版的啟動程式，不是 MS-DOS 的）✅ code：
  - 0x734 把 0x285 起 0x1F0 bytes 複製到 0090:0000 並把 int 1Bh 指過去：這段是代替原廠防拷的假磁碟處理程式，讀 R＝F5、F7 的隱藏磁區時造出一段假的原始磁軌（0xC5、0x4E 間隙、`A1 A1 A1 FE C H R N`…），讀 R＝9（N＝1）時填 0、1、…、255。
  - 0x7C7 再把 int 1Bh 指到 0x103：讀取（AH 低 4 bit 是 6）落在 head 0、cylinder 5–14 時，讀完後把每 1024 bytes XOR 0x285 的緩衝區。緩衝區換 cylinder 時重建（0x16F）：cylinder 10–14 讀 R＝9 再每 byte 加 0x15，接著 0x18B bytes 填 0xE5；5–9 讀 F5（留 0x215 bytes）和 F7（0x76 bytes）。其餘 373 bytes 是緩衝區原本的內容。
  - 0x769–0x7C5 是原廠讀隱藏磁區的檢查與解密，被 0x767 的 `jmp` 跳過。
- `san1.pc98_disk_a_key`／`read_pc98_file` 照上面的規則算 key（從 `COMMAND.COM` 取字串與 CRC 表），✅ emu：和用 Unicorn 跑 `COMMAND.COM` 的 int 1Bh 處理程式（假 BIOS 回傳 FDI 的磁區）解出的 80 個磁區逐 byte 相同。解開後 `SANGOKU.OVL` 每 4 KB 都有 `55 8B EC`（函式開頭），`PACKDATA.DAT` 的 5 張圖都解得出來。

## 大地圖

- 58 國的大地圖是 `PACKDATA.DAT` block 0（320×200，解密後），畫面是 200 列模式，輸出逐列加倍成 320×400（`san1.world_map`、`dekoei.py san1 worldmap`）。國號畫在圖上；每國是一塊白色區域，剛好 58 塊。
- 色盤用數位 8 色（見「頭像」的色盤），沒有大地圖畫面的截圖可以比對（🟡）。
- 國的位置：程式裡的座標表還沒找（SANGOKU.OVL 剛解開），`pos` 從圖上取：用數字字形比對讀出每塊白色區域的國號，數字碰到國界線的 5 國（3、18、38、46、52）用相鄰關係決定，這是 140 組遊戲相鄰全部在圖上相接的唯一配法（✅ cross：`SAVEDATA` 的鄰國表）。圖上另外只有 17、21 兩國在 19 的國界交點相接，遊戲不算相鄰。
- PC-88 V1 版：`PACKDATA` 照遊戲讀的順序（見「PC-88 V1 版」的磁碟）在 0x10000 起有同一張圖，RLE 資料 13948 bytes 和 PC-98 byte 相同（✅ cross），所以圖和 `pos` 都相同。

## 下一輪候選

- `SANGOKU.OVL` 解密後的內容（原始劇本、事件訊息、組合臉程式、戰場地形圖案）— 前置：已可用 `san1.read_pc98_file` 讀；做法：照 DOS 英文版 `SAN.OVL` 的函式（同一套 PLINK86 overlay）比對找位址。
- 用 15 州地圖（block 70）核對各國所屬的州（現在取自 FC）— 前置：無；做法：兩張圖海岸線相同，取各國 `pos` 在州圖上的顏色。試過一次 5×5 取樣，州圖是兩色網點、國號字會蓋到，結果大致相符但不乾淨，要改成整塊區域的顏色統計。
- 大地圖的色盤 — 前置：主畫面的截圖。

## 負面結論

- 把 PACKDATA 的加密當成固定 key 的 XOR 或位移 XOR 解：每 256 bytes 的常見值會在區塊中間換，不是檔案自己的編碼，是磁碟加密的 key 裡夾著假磁軌的間隙與 ID 欄位；要從 `COMMAND.COM` 的 int 1Bh 處理程式看才解得開。
- 在 `SANMAIN.EXE` 解密前找 PACKDATA 的讀檔程式：檔名字串在 DGROUP，但讀檔的程式在 overlay 裡，root 沒有。

## 發行年份

PC-9801 版 1986-04-30（ja.wikipedia〈三國志 (ゲーム)〉，和 FM-16β 同日）。另有 1995 年 3 月的 PC-9801 復刻版。

## PC-88 V1 版（`san1-pc88`）

`dekoei.py export san1-pc88` 用到的格式。來源是 Neo Kobe 2016-02-25 的 `games/archives/pc88/neo-kobe-2016-02-25/Sangokushi/Sangokushi [FD].7z`，取其中 V1 模式的 Disk A、B（`Sangokushi (Disk A|B) {V1 mode}.d88`），原樣放在 `games/san1-pc88/DISK_A.D88`、`DISK_B.D88`。

### 版本

- Disk A 標題字串 `[Ver.1.1(86/1/6)]`。同一包的 Alt 2（16-Apr-1986）是 `[Ver.1.2(86/3/14)]`，Set 1 沒有版號字串。
- 各版本的 SN1.EXT 人物表、Disk B 的頭像磁軌都相同，匯出用 FD 主檔。
- Disk C（YDOS 3.0，「SANGOKUSHI 10-Nov-86」）的 SAVEDATA 用的是 PC-98 式的頭像碼 0–64，和 V1 本體不同，不採用。
- 發行年份：PC-8801 版 1985-12-10（ja.wikipedia〈三國志 (ゲーム)〉），是系列首發。
- `Sangokushi (SR)`（PC-8801mkIISR 版）Disk A 的頭像和 PC-98 PICDATA 0–112 逐 byte 相同（0x18C00 起，每 9 磁區一軌放 6 張），不另做資料集，只在 `san1-pc98` 標記。

### 磁碟

- 2D D88，40 cylinder × 2 head × 16 × 256 bytes。依 (c, h, r) 排序串成線性映像（`pc88.d88_image`）。
- Disk A 第 1–9 cylinder 的 head 0 多了 id 245–247 的磁區（拷貝保護），要略過，否則檔案會錯位。
- Disk A 0x4000 是 CP/M 式目錄（YDOS 2.2），2 KB 一個 block（`pc88.cpm_files`）：PACKDATA、SANMAIN.COM、MAIN.OVL、KANJIF.DAT、SN1.EXT 等。
- `PACKDATA` 的目錄把 block 從磁碟 0x4F800 往回排，照目錄接起來的圖會錯位；照「從最後一軌（0x4F000）往前、每軌 4 KB 依磁區順序」接（`san1.pc88_packdata`），58 國大地圖（0x10000）、15 州地圖（0x2000）、結局（0x5000）、標題雙龍（0xC000）、開場題字（0）的 RLE 資料都和 PC-98 byte 相同（✅ cross）。沒有標頭，大小照 PC-98。`MAIN.OVL` 有一部分看起來也加密過，沒查。
- Disk B 沒有可用的目錄，遊戲直接以磁軌讀。

### 頭像（Disk B）

- 格式和 PC-98 PICDATA 相同：每張 720 bytes，48×40 半高、3bpp（`to_3bpp_indexes`），逐列重複成 48×80。
- 一軌 4 KB 放 5 張：頭像碼 n 在第 n // 5 軌第 n % 5 張，offset ＝ 軌 × 4096 ＋ 張 × 720（`san1.pc88_face_by_code`）。
- 人物用到的頭像碼是 0–29 和 43（劉表），共 31 張；第 8 軌第 4 張是劉表的複本，沒有人用，不收。
- 和 PC-98 比：16 張相同、12 張修過；兩張是 PC-98 沒有的畫（碼 8 孫策、碼 19）。PC-98 有頭像而 V1 沒有的人（夏侯淵、荀彧等）在 V1 是組合臉。
- 女兒：第 40–43 軌（43 只有第 0 張）共 16 張，和 PC-98 的 66–81 相同。沒有找到頭像碼，匯出成 group「姫」、不填 `code`。
- 色盤：數位 8 色，同 PC-98。

### 組合臉

- 頭像碼規則同 PC-98（0xGTMB，三段橫條）。組別 G 的素材是第 G 軌的 5 張；第 8 軌後兩張是劉表，所以組別 8 只有 0–2，碼也只用到 0–2。
- 224 人是組合臉；PC-98 的 190 個組合臉在 V1 的碼都相同。

### 人物（SN1.EXT）

- 34 bytes 一筆，格式同 PC-98 SAVEDATA。0x104D 是多出來的一筆曹操，255 人從 0x104D ＋ 34 起（`san1.load_san1_pc88_persons`）。
- 姓名是 3 個 little-endian JIS word（+8），部分 byte 的 bit 7 有設（張勲、太史慈、陸績等），讀的時候每 byte `& 0x7F`。+22 是 u16 頭像碼。
- 這份表和 V1 Disk A 的 SAVEDATA（0x106F）完全相同。姓名、順序和 PC-98 的 255 人一致，所以 `id` 從 1 起算，`nameHistorical` 沿用 `SAN1_PC98_NAME_HISTORICAL`。

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

## X68000 版（`san1-x68`）

`dekoei.py export san1-x68` 用 `build_san1_x68`。

- 來源：Internet Archive `sangokushi_1988_koei_disk_1_of_x68k`（`games/archives/x68000/ia-softwarelibrary/`），A、B 兩片 DIM，各有主檔、`[a]`、`[a2]` 三份。
  - A 片三份只有 `SANMAIN.Z` 差十幾個 byte，`KAODATA` 相同。
  - B 片 `[a]`、`[a2]` 的 `SAVEDATA` 有玩家存檔；主檔的 10 個槽都是「KOEI.GAME 1988-12-05」的原廠初始資料，所以用主檔。
  - `games/san1-x68/` 放 A 片的 `KAODATA` 與參考用的 `SANMAIN.Z`，B 片的 `SAVEDATA`、`SANGOKU.PAL`。
- `SANMAIN.Z` 沒有壓縮，執行位址＝檔案＋0x4FFDE。
- 頭像全部重畫成 256 色：`KAODATA` 每張 48×80、每點 1 byte（3840 bytes），用 `SANGOKU.PAL` 的 256 色（X68000 圖形色盤字：G、R、B 各 5 bit 再接亮度 bit，0x6A69A 整份設進去）。
  - 0–64 是武將（順序和 PC-98 不同），65–84 是 20 位女兒（0x626FC：`65 + (… mod 20)`，group「姫」）。
  - 6 沒有人用（group「未使用」）；程昱、曹丕都用 7（PC-98 分別是 46、27），照資料匯出，兩人加 `note` 說明。
- 組合臉（0x62682）：頭像碼 ≥ 100 時寫成 0xGTMEB，G 是組別 1–5，T、M、E、B 各 4 bit。`KAODATA` 0x4FB00 起整塊 0x21270 bytes：
  - 頭：0x4B00 × (G − 1) ＋ 0xF00 × T，48×80 整張，五官處是 0。
  - 眼：0x15900 起，每組 0xC30，每個 0x270（13 列），貼在第 25 列。
  - 鼻：0x19110 起，每組 0xD20，每個 0x2A0（14 列），貼在第 34 列。
  - 口：0x1CD70 起，每組 0xF00，每個 0x300（16 列），貼在第 46 列。
  - 頭直接貼，眼鼻口用 OR（0x709C6 模式 3）。各區都是 23 個，第 5 組只有 0–2，劇本也只用到 0–2。
  - 匯出成 `blend: "or"`。零件彼此不重疊，也只填在頭的 0 上，只有第 1 組口 3、第 3 組口 4、第 4 組口 3 各有 1 個邊緣像素會和頭的非 0 像素 OR（用到的 22 人照遊戲 OR）。
- 色盤 256 色互不相同，色號 255（白）有用到，但 kaodata 的 255 是透明，所以把 255 換到沒有圖用到的 250。真正會 OR 到非 0 的只有 106、108、110、112、153、156、174、190、222，不碰 250、255，所以 OR 結果不變。
- 人物：`SAVEDATA` 前 300 bytes 是槽標頭，槽 0 的人物表在 0x1E42，第一筆是多出來的曹操，之後 255 筆 × 44 bytes（`san1.load_san1_x68_persons`）：+0 讀音 8 bytes、+8 姓名（3 個大端 32 位元 JIS 碼，外字同 PC-98）、+28 u32 頭像碼。
  - 名字和 PC-98 逐筆相同（含錯字），`id`、`nameHistorical` 照 `san1-pc98`。
  - 純頭像 64 人、組合臉 190 人（同 PC-98）。
