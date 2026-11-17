# 三國志V 威力加強版（SAN5PK, DOS 中文版）頭像相關格式

`dekoei.py export san5pk-dos` 用到的格式。來源是 `games/archives/dos/6.3_三國志五DOS加強版_killpeople.rar`（killpeople 是上傳者標記），解開放在 `games/san5pk-dos/`。

## 版本檢查

- 是威力加強版（PK）的資料：
  - `INSTALL.INI`（1997-01-15）是 PK 的安裝設定，標題「三國志加強版」，要先裝好本體（`DISK02VOL SAN5PUK`）。
  - `SNDATA.S5`、`TAIKI.S5`、`MESSAGE.S5` 的日期是 1997-01-14，和 PK 安裝程式同期。其他本體檔多是 1996-06／07。
  - `SNDATA.S5` 有 12 個劇本。ja.wikipedia〈三國志V〉說本體 7 個、PK 加 4 個。
  - `VERSION.S5`：「三國志V中文版／1996/06/27／光榮軟件有限公司」。
- 頭像和人物資料沒看到修改跡象：
  - `KAODATA.S5`（1996-06-17）和 `KAODATAP.S5` 逐 byte 相同，日期是原廠的。
  - `SNDATA.S5` 的劇本 offset 和 `gadgets.get_san5_name_list`（作者自己那份 SAN5）寫死的 offset 一致。
  - 不過手上沒有官方原檔，無法逐 byte 比對。
- `MAIN.EXE` 改過（日期 2000-03-11）：
  - 附有 `CRACK.TXT`（Martin Wu 的光碟檢查破解）：0x14533 75→EB、0x1A7BF 00→01、0x98DAA 75→EB。
  - 目前檔案只有 0x1A7BF 是 01，另外兩處仍是 75，所以實際改了什麼不確定。
  - 匯出不讀 `MAIN.EXE`，只拿它的程式碼當參考。

## MAIN.EXE

- MZ 檔頭 0x5600 bytes，有 47 個 MS-LINK overlay（各自有 MZ 檔頭，第一個在檔案 0x5E200）。
- DGROUP 在檔案 0x51F50（段值 0x4C95）。0xBDAD0 `push 0x5AB2` 指向字串 "KAODATA.S5"。下文的位址都是檔案 offset。

## KAODATA.S5：頭像

- 783 張，每張 64×80、3bpp planar、全高，1920 bytes，沒有壓縮。
- 每列 24 bytes，byte k＝色號 bit k（同 `genpei.decode_planar`）。
- 頭像碼就是索引（0 起算），人物用到 0–499，一碼一人。
- 色盤：
  - DGROUP 0x5C94 起 16 色（0xC2967 載入），每色 3 bytes（B、R、G，各 4 bit），頭像用 8–15 色。
  - 換算同三國志IV：`(v << 4) | (v >> 2)`。
  - 結果：`#202010 #104171 #B23000 #B27141 #206110 #618292 #E3A282 #E3D3C3`。
  - 和舊 `san5 face` 的 WIN 編輯器色碼相近，順序是 `to_3bpp_indexes` 的 bit 0、2 對調。

## 人物

- `SNDATA.S5`、`TAIKI.S5` 開頭都是 u16 劇本數（12），接著每劇本 (u32 offset, u16 size)，offset 從索引結尾算起（`sango.san5_parts`）。
- SNDATA：
  - 人物表在每個劇本的結尾前 1100 bytes 結束。
  - 每筆 38 bytes：姓名 10 bytes，+30 是 u16 頭像碼。
  - 往前找到第一筆不像姓名的記錄為止（`sango.load_san5_persons`）。
- TAIKI：每筆 69 bytes，+31 起是同樣的 38 bytes。
- 依劇本 1–12、每個劇本先 SNDATA 再 TAIKI 的順序，以頭像碼去重，共 500 人，`id` 就是這個順序。
- 能力（`sango.load_san5_stats`，`dekoei.py san5 person`）：
  - 每人一筆 31 bytes。SNDATA 的能力表緊接在人物表前面，筆數和順序相同；TAIKI 每筆 69 bytes 的前 31 bytes 就是能力。
  - +12 起依序是武力、知力、政治、魅力（u8）。
  - 這是基礎值，武將詳細會再加上道具加成。✅ capture：`status-screens/san5pk-pc98-cap-02.png` 夏侯惇（劇本 1）的 武力 94／知力 70／政治 81／魅力 87 與解出值相同；`cap-01` 曹操的知力 97 比解出的 96 多 1，因為加上了道具。
  - PC-98 本體（`--tail 64`）、PC-98 PK、DOS PK 同一人的值相同；全部記錄的四項都在 1–100。
- 頭像碼和姓名一一對應。同名只有馬忠（222、452），本來就是兩個人。
- `nameHistorical`（規則見 CLAUDE.md）：孔岫→孔伷、龐義→龐羲；左賢王（134）是稱號，填劉豹；許子将（494）是用字稱人，填許劭（使用者 2026-11-02 決定），三個資料集都填。不填的：異體字劉瞱（劉曄）、關彞（關彝），《三國演義》寫法范疆（范彊）。
- 華佗、司馬徽、許子將、于吉、左慈、管輅、南華老仙都是劇本人物（492–499），不算未使用頭像。

## 列傳（DOS 中文版 PK）

- `MESSAGE.S5`（LS11）第 1–10 段，每段 u16 筆數（50）加 u16 位置表（從段首算），共 500 則；第 c 則是頭像碼 c 的人物（`biography.san5_bios`，`dekoei.py biography san5pk-dos`）。
- 人物號照 kaodata `san5pk-dos`（劇本順序、依頭像碼去重）：500 人都有，id 與姓名全部相同（✅ cross：`dataset.json`）。範例：關羽 17 → 第 1 則、劉備 110 → 第 35 則、諸葛亮 312 → 第 44 則。
- 只有一段。編碼同三國志IV 中文版的列傳（見 `notes/san4.md`「列傳」），另有 0x01＋1 byte 的行首屬性碼要跳過。

## 沒有人物使用的頭像（500–782）

- 新武將的挑臉函式在 overlay 16（0x8D420、0x8D21C、0x8D170、0x8D2B7）。
  - 記錄 +0x46 是性別旗標：參數為 0 時設成 1。
  - +0x4E 是起點：0x1FC（508），旗標為 0 時再加 0x75，得 625；翻頁時每頁加 32。
  - +0x50 是終點：0x270（624），旗標為 0 時再加 0x6C，得 732。
  - 超過終點後接到 0x2DD（733），旗標為 0 時再加 0x19，得 758。
  - 依畫面判斷旗標 1 是男、0 是女：
    - 新武將（男）：508–624、733–757
    - 新武將（女）：625–732、758–782
  - 733–782 的畫風和前面不同。
- 500–507 事件人物：
  - DGROUP 0x8E7A 起有 6 bytes 一格的名字表：獻帝、貂蟬、民眾、使者、士兵。
  - 兩人都不是劇本人物，依名字順序和畫面對應：
    - 500 獻帝
    - 501 貂蟬
    - 502–505 民眾（四張不同的平民）
    - 506 使者（官帽）
    - 507 士兵（頭盔）
  - DGROUP 0x5EFE 也有 [500…507] 的表。
  - 這兩張表都沒找到直接存取它們的程式碼，所以頭像和名字的對應是推斷的，之後在 koei.wiki 確認。

## KAOEX.S5：追加頭像（783–1164）

- 382 張，格式同 KAODATA（64×80、byte k＝bit k、1920 bytes、無壓縮）。DOS 和 PC-98 的檔案相同。
- PK 的挑臉對話框（PC-98 MAIN.EXE 0x6AC08）開啟 `KAOEX.S5`，選擇器 0x68744 的總數是 0x48D＝1165＝783＋382，每頁 32 張；碼 ≥ 783 讀 KAOEX 第（碼 − 783）張。劇本人物沒有用到，只在武將編輯、新武將換臉時可選。
- 第 0–95、97–159 張就是三國志IV `KAODATA.S4` 的第 0–95、97–217 張，連色號都相同（第 96 張不一樣）；其餘 222 張和三國志III、IV 都對不上，來源待考。
- 匯出時接在 KAODATA 後面，code 從 0x30F 起，group「追加頭像」。

## 發行年份

- ja.wikipedia〈三國志V〉：
  - 本體 PC-98 1995-12-15，PK PC-98 1996-07-19
  - Win3.1 1996-03、PK 1996-09
- Wikipedia 沒列 DOS 版。網站採用 PK 原版年份 1996。

## PC-98 日文版 PK（`san5pk-pc98`）

`dekoei.py export san5pk-pc98` 用到的差異。來源是 `games/archives/pc98/【PC98】三國志５　パワーアップキット.rar` 的 HDI 硬碟映像（已安裝 PK）（2026-11-08 移到 `games/archives/to-delete/`，2026-11-09 已刪除；87 個遊戲檔的 SHA-1 都在 neo-kobe 的 `Sangokushi V/Sangokushi V (with Powerup Kit) [HD].zip` 裡，留那份），解出放在 `games/san5pk-pc98/`。

- `KAODATA.S5`、`KAODATAP.S5`、`KAOEX.S5` 和 DOS 中文版逐 byte 相同。`KAODATAP.S5` 是遊戲讀人物頭像用的工作副本（0x884E3 開檔，0x68704 讀取），原廠內容和 KAODATA 相同，匯出照舊用 KAODATA。
- `MAIN.EXE`：MZ 檔頭 0x5400，DGROUP 在檔案 0x51250（段值 0x4BE5）。
- 色盤：DGROUP 0x910 的 16 色和 DOS 逐 byte 相同。`GRP98W.EXE` 0x15F6 寫 port 的順序是 B→0xAE、R→0xAC、G→0xAA。PC-98 類比色盤每色 4 bit，所以用 v × 17：`#222211 #114477 #BB3300 #BB7744 #226611 #668899 #EEAA88 #EEDDCC`。256 色驅動（`GRP9821.EXE` 等）只用在地圖（`PAL256.S5`），頭像仍是 16 色。
- 人物：SNDATA／TAIKI 的結構、每筆的劇本和頭像碼都和 DOS 相同。38 bytes 記錄的姓名欄改成 8 bytes Shift-JIS＋NUL，+9 起是半形片假名讀音，所以往前找人物表起點的條件改成「首 byte ≥ 0x81、+8 為 0、+9 是半形假名」（`sango.load_san5_persons(..., pc98=True)`）。讀音不匯出。
  - 外字：SJIS 0xEB9F 起，字形在 `FONT.S5`（92 個 16×16 字），人名用到 42 個（`sango.SAN5_PC98_GAIJI`）。
  - 500 人，順序同 DOS。頭像碼 199 在劇本 1、2 寫蘆植（錯字），8、9、12 寫盧植，取盧植（`SAN5PK_PC98_NAME_PICK`）。
  - DOS 的錯字孔岫、劉瞱、關彞，日文版是正確的孔伷、劉曄、関彝；龐義兩版都錯，填 `nameHistorical`；范疆是《三國演義》的寫法，不填。
- 未使用頭像和 DOS 相同（新武將挑臉在 0x839F8 等處）。事件人物的名字表在 DGROUP 0x35BA：500 献帝、501 貂蝉、502–505 民衆、506 使者、507 兵士，對應同樣是推斷的。
- 發行年份：PK PC-9801 版 1996-07-19（ja.wikipedia〈三國志V〉）。

### koei-wiki 匯出

```sh
cd dekoei
../.venv/bin/python dekoei.py persons-export san5pk-pc98 --game-dir ../games/san5pk-pc98 --out ../export/koei-wiki/persons --places ../export/koei-wiki/places
```

讀取在 `dekoei/wiki_san5.py`，資料取 PC-98 PK 的 `SNDATA.S5`、`TAIKI.S5`、`MESSAGE.S5`（koei-persons/1）。

- 500 人，`id` 同 kaodata `san5pk-pc98`。`name` 用 DOS 中文版同一頭像碼的寫法（兩版每筆記錄的劇本與頭像碼相同），日文寫法不同的 88 人填 `nameJa`；史書寫法照中、日文版各自的表寫在 `notes`。
- `stats` 同 stats 匯出。`born` 是 38 bytes 人物記錄 +21 加 100。
- 38 bytes 人物記錄的其他欄位（這次對過）：
  - +22：血族號，同姓一家同號（曹、孫、袁紹、夏侯淵…，0 是沒有），放 `relations.clan`，🟡。
  - +32 u16：父親的頭像碼（曹丕→曹操、關興→關羽、劉禪→劉備、司馬師→司馬懿，57 個父親，子比父年輕 13 歲以上），放 `relations.father`、`children`，同父的是 `siblings`。值 ≥ 1000 是沒有父親在遊戲裡的兄弟組（諸葛亮、諸葛瑾、諸葛均同值；孫堅、孫靜同值），這種 `siblings` 標 `uncertain`。上面「三國志V」屬性表原本寫 p+32 是血縁，是錯的，血族在 +22。
  - +20 相性、+34 u16 的義理 野望 冷静 勇猛放 `hidden`（🟡，同屬性表）。
  - +24–29 特技 6 格：已習得幾格沒查，不匯出。
- 劇本：MESSAGE.S5 第 13 段的劇本選單有 11 個標題（184年１月 黄巾ノ乱 … 213年５月 劉備入蜀），`year`、`month` 取它。SNDATA 劇本 +577 的 u16 年份和標題相同，1 月的劇本少 1（184 年 1 月存 183、200 年 1 月存 199），程式裡有 assert。SNDATA 的第 12 個劇本沒有標題（183 年，300 人，238 人在野），不匯出；500 人在劇本 1–11 都有出現。
- 劇本 +579 u16 是人數；能力記錄 +20 是所在都市（地點匯出的 id），+21 是勢力號（1 起，FF 是無）。
- 勢力記錄：劇本 +3899 起 18 筆 × 77 bytes，+2 u16 君主、+14 u16 軍師（人物表的 1 起序號）。
- 都市記錄：劇本 +961＋30n 是都市 n，+0、+2、+4 是三串人物的開頭（下一個是能力記錄 +2），+18 是勢力號。三串分別是勢力的武將、在野、未発見：每個劇本的人物剛好各在一串，串裡的人所在都市都對。
- `status` 用 `MAIN.EXE` 0x54742 的身分詞：
  - 有勢力：君主、軍師（勢力記錄）、一般；`lord` 是勢力的君主；君主以外填 `loyalty`（能力記錄 +19，🟡：君主是 100、在野是 1）。
  - 沒有勢力：能力記錄 +10 bit 0 是 1 的在「未発見」串，0 的在「在野」串（642 筆全部一致）。
  - TAIKI 的人寫「待機」（身分詞第 7 個，檔名也是 TAIKI），所在取能力記錄 +20。登場的條件沒追，所以不填 `debut`。
  - 都市武將串的第一個人：不是君主時填 `rank`「太守」（🟡：太守是身分詞後面的稱號，第一個是太守是推的）。
- 檢查：persons-export 7014 筆、koei-wiki `verify_persons.py` 14588 筆，0 筆不符。

## PC-98 本體（`san5-pc98`）

- `games/san5-pc98/` 只有安裝片：`INSTALL.EXE`（KOEI Install Program Ver 2.1）照 `INSTALL.SYS` 的 `UNPACK DPACKn.S5` 解出 7 個包。
- DPACK 用 `dekoei/dpack.py` 解開（格式見 [dpack.md](dpack.md)），解出的檔放在 `games/san5-pc98/`：64 個檔和 `san5pk-pc98` 的同名檔相同，KAODATA.S5 是 PK 版的前段。
- `dekoei.py export san5-pc98` 用 `build_san5pk(pc98=True, pk=False)`：
  - KAODATA.S5 是 733 張（PK 的 0–732），沒有 KAOEX.S5。
  - 劇本只有 7 個；SNDATA.S5 每個劇本的人物表後面只接 64 bytes（PK 是 1100），`sango.load_san5_persons(tail=64)`。TAIKI.S5 的記錄格式相同。人物（500 人）、名字、頭像碼都和 PK 相同。
  - 新武將挑臉（MAIN.EXE 檔案 0x79830）：起點 0x1FC（508），旗標為 0 時加 0x75（625），每頁 32 張，第 4 頁男 21 張、女 12 張，所以是男 508–624、女 625–732，沒有 PK 的 733–782。
  - 頭像色盤在 MAIN.EXE 檔案 0x49E2A，值和 PK 相同。
- PC-98 本體 1995-12-15 發行。

### 戰場地圖

`dekoei.py san5 battlemap --game-dir ../games/san5-pc98 --out ../games/san5-pc98/extract/battlemap [--season 0–3]` 寫出 `01.png`–`47.png`（800×768，遊戲畫面會捲動），第 n 張是都市 n 的圖；預設季節 0（1–3 月），這一季 47 張都用第 0 組色盤。

- `HEXMAP.S5` 是 LS11，共 141 個 part：47 張 7200 bytes 的圖塊圖，接著 2 × 47 個 600 bytes 的串流（推測是配置與地形，像 IV 的 220 bytes 兩段，沒有解）。
- 圖塊圖是三層 50 × 48，每格 1 byte，`FF` 是空格。各層的值加上 0、138、323 就是圖塊編號；`HEXGRP.S5`（LS11，1 個 part）共 488 張，138＋185＋165 剛好用完。
- 圖塊格式同 IV：16×16 點，4 個色面依序排，每面 32 bytes。第 0 層不透明，上兩層的色 0 是透明（`sango.render_tile_layers`）。
- 下文的程式位址是 MAIN.EXE 檔案 − 0x4A00（MZ 檔頭）；0x4A72B 以後是 overlay，同樣用檔案 − 0x4A00。
- 圖號（✅ code）：0x8161F 把 DGROUP 0x8A8 − 1 設成圖號（DGROUP 0x7954），0x8131E 讀 `HEXMAP.S5` 第 n、n＋47、n＋94 段。0x8A8 是 1 起的都市號（下面的色盤用它查都市表），所以第 n 張圖是都市 n 的圖。0x8A8 是不是守方都市沒追。
- 色盤（0x84212，✅ code）：
  - 色 0–7：`0x2EE7:0x3A40`（檔案 0x372B0）的 6 組 × 24 bytes，第 g 組。g＝季節（DGROUP 0x49，0x1009:0x5566 讀取）；但都市（DGROUP 0x8A8）的都市表 +0x1E 沒有 bit 1 時（0x1009:0x7BFA），季節 1 改用第 4 組、季節 3 改用第 5 組。
  - 都市表在 `0x3A9A:0`（檔案 0x3F3A0，47 × 32 bytes，PK 檔案 0x41C20，byte 相同），+0x1E 有 bit 1 的是 1–22（襄平…宛）、38 漢中、39 下弁，其他 23 城（荊州、揚州、益州、交州一帶）沒有。程式裡沒有寫 +0x1E 的地方（0x17EC2、0x17EEE 只是整表存讀檔）。
  - 季節：0x4AC12 每月呼叫 0x1009:0x5584 把月（DGROUP 0x48）＋1（12 之後回 1），月變成 1、4、7、10 時呼叫 0x1009:0x556C 把季節＋1（mod 4）。季節 3 的第 3 組偏灰白、第 5 組仍是暗綠（看圖），所以 0 是 1–3 月、3 是 10–12 月（推定：季節的初值在哪裡設定沒追）。
  - 色 8–15 照 DGROUP 0x8DA（頭像色盤 0x8C2 的後 24 bytes，檔案 0x49E2A）。
  - PK `MAIN.EXE` 檔案 0x93229 起是同一段程式（表在 `0x308B:0x3E46`，檔案 0x39AF6，和本體 byte 相同），✅ cross。
  - 0x13570 依季節從 DGROUP 0x8F2 選 4 組之一，那是大地圖的色盤，和戰場無關。
  - 顏色本身沒和遊戲截圖比過（`captures/` 沒有 V 的戰鬥畫面）。
- ✅ cross：PC-98 本體、PC-98 PK、DOS 中文版 PK 的 `HEXMAP.S5`、`HEXGRP.S5` 解開後 byte 相同。
- 畫面上沒有畫六角格線。

#### 下一輪候選

- 色盤的 capture 證據與季節的編號 — 前置：DOSBox-X／NP2kai 跑到一場戰鬥；做法：記下遊戲內月份與都市，截圖和匯出圖比色號 0–7，同時確認季節 0 是 1–3 月。
- DGROUP 0x8A8 是不是守方都市 — 前置：無；做法：追 0x8A8 的寫入點（出陣、被攻的流程）。

#### 負面結論

- 舊筆記的 0x13570（DGROUP 0x8F2 的 4 組）是大地圖色盤，不是戰場的；戰場色盤要從讀 `0x2EE7:0x3A40` 的 0x84212 找，它在 overlay 裡，用 MZ 檔頭算出的 load image 範圍內搜不到。

## 事件、插圖、道具

`dekoei.py san5-extras --game-dir ../games/san5pk-pc98 --dos-dir ../games/san5pk-dos --out ../games/san5pk-pc98/extract`（`dekoei/san5_extras.py`）。

- `eventcg/`：事件圖 34 張、一騎討ち 3 張、武術大會對戰表、一騎討ちモード、場景背景 9 張、勢力分布圖，共 49 張，附 `index.csv`。
- `map/`：大地圖 16 色 4 張、256 色 4 張，附 `index.csv`。
- `items/`：`items.csv`（32 件）、`holders.csv`（223 筆）、`pictures/00–47.png`。
- `events/messages.jsonl`：日文 3578 則、繁中 3534 則。
- `opening/`（13 張）、`ending/`（7 張），附 `opening-ending.csv`。
- `fragments/`：無名碎片的 contact sheet（re-common §11），包括 `ui.png`、`sprites.png`（IKKI1/2、CANMA）、`opening-cels.png`、`ending-cels.png`。

本節的位址，沒寫檔名的都是 PK 版 `MAIN.EXE` 的檔案位移。MZ 檔頭在 0x5400，DGROUP 在 0x51250；換成 load image 位址要減 0x5400。

### 共通格式

- **raw 圖（rcp）**：
  - 每列是 w/8 組，每組 4 bytes，依序是 plane 0–3 的 8 個點（MSB 在左），一張 w×h 的圖佔 w×h/2 bytes。
  - 畫圖 `0x1041:d296` 的參數依序是 x、y、w、h、buffer 內 offset。
- **ESTL.S5、ITEM.S5、頭像的色**：都只用色 8–15。ESTL 是 3 面，每組 3 bytes，解出的色號加 8。
- **主色盤**：DGROUP 0x910，16 色 ×（B、R、G）nibble。
  - 色 8–15 是頭像色（DGROUP 0x928）。
  - 大地圖的色 0–7 照季節換，取自 DGROUP 0x940 + 24×季節（0x18dad `imul ax,ax,0x18; add ax,0x940`）。
- **畫面模式**：640×400、640×480、800×600 三種（`0x1041:2f6e` 判斷 256 色，`2f7e`／`2f8e` 判斷模式）。檔案裡三種模式的框都有。

### 各檔

| 檔 | 內容 | 證據 |
|---|---|---|
| `ESTL.S5` | LS11，34 段 × 14400 bytes，240×160、3 面。畫在 0x1a41e（第 27 張以後用 248×168 的窗），顯示在 0x1a592，事件分派在 0x71c12（表 es:[0x44b8]） | 圖 ✅ code；名稱 🟡 看圖 |
| `IKKIHAI.S5` | 一騎討ち背景，讀在 0x8c0e0。640×400 由兩個 320×400 拼成（0x13100 放在 (0,0)、0x22B00 放在 (320,0)）；條件 DGROUP 0x2a00 成立時，再疊兩條 624×116（0x39D00 放在 (8,160)、0x42A60 放在 (8,276)），推定是武術大會版。800×600 框：80×296 四塊（0、0x2E40、0x5C80、0x8AC0）、640×56 兩塊（0xB900、0x35700）、640×40 兩塊（0xFF00、0x32500）；640×480 模式只用後兩塊 | 各塊 ✅ code；800×600 的組合 🟡 |
| `BUDOUKAI.S5` | 從 0 起是 328×312 的武術大會對戰表，畫在 0xbcdd8；後面 1536 bytes 是小零件 | ✅ code |
| `IMODE.S5` | 讀在 0xaf530，4 塊 320×200（32000 bytes），依序放在 (0,0)、(0,200)、(320,0)、(320,200)，畫在 0xafd54 起；之後到 236800 是 800×600 的框，再後面 6560 bytes 是別的資料 | 排法 ✅ code；只用色 1–4 與 8，色盤 🟡；用途（一騎討ちモード）🟡 |
| `CANMB.S5` | 開頭 u16 個數，接著每項（u32 offset、u16 size），資料從 2+6n 起。共 18 項：0–6 是 256 寬（#5 是 207 列），7–8 是 400×256 的場景背景，9–17 是小零件。存取經過 0x1041:e08（0x661ba） | 索引 ✅ code；寬度、名稱 🟡 |
| `CANMA.S5` 180 格、`CANMD.S5` | 同樣的索引格式。CANMA 是人物動作格，CANMD 是動畫腳本 | 只出 sheet |
| `IKKI1/2.S5` | 各 109536 bytes，64 寬的騎將動作格，載入 EMS buffer 0x6ac0（IKKI2 在 +0x1abe0） | 只出 sheet，分格不明 |
| `FMAP.S5` | 64800 bytes，讀在 0x18b4f，勢力分布圖 | 讀取 ✅ code；360×360 🟡 看圖 |
| `MAINMAP.S5` | 50 欄 × 4736 bytes。每欄 16×592，4 個 plane 依序排，每 plane 每列 2 bytes | ✅ capture：和 `captures/screenshots/san5pk-pc98/guest-os-000.png` 在 (160,64) 起逐點一致，12 月時用季節第 3 組 |
| `MAP256.S5`、`PAL256.S5` | 256 色版，50 欄 × 9472 bytes，每點 1 byte（0x88540；欄大小 [0x77fc] 是 0x2500 或 0x1280，在 0x87f00／0x87f31 設定）。`PAL256.S5` 是 4 組 × 213 色（色號 32–244），每色 B、R、G 各 1 byte | 排法 ✅ code；B、R、G 的順序與季節對應 🟡 看圖 |
| UI：`BTNGRP`、`GRAPH`、`MAINWIN`、`CALC`、`HENV`、`HUNIT`、`HANIME`、`MAPANM` | 按鈕、圖示、視窗零件。BTNGRP 整檔讀進 0x6ab4；HANIME 在 0x8a5cd 從 19456 起讀 7680 bytes | 只出 `fragments/ui.png` |
| `IMDATA.S5`、`ENDDATA.S5` | 資料，不是圖 | |

### 道具

- **名表**：
  - `MAIN.EXE` 0x48e80（0x494c0 另有一份相同的），100 格 × 16 bytes，用了 32 格。
  - 每筆：+0、+1、+2 是 3 個加成值，+3 起是 13 bytes 的 Shift-JIS 名字。
  - 武器只用 +0，書只用 +1 或 +2，馬與玉璽都是 0，推定依序是武力、知力、政治 🟡。
  - 外字 0xEBC8＝釭、0xEBF8＝蒺，和 FONT.S5 的字形對過。
- **中文名**：DOS 版 `MAIN.EXE` 0x4fa20，格式相同（`sango.to_unicode_name`）。兩版逐筆一致，✅ cross。
- **圖**：`ITEM.S5` 48 張 80×80（3200 bytes）。0xb4c3a 依 n×0xC80 讀出、畫成 80×80，✅ code。
  - 0–31 號圖對應 0–31 號道具（✅ cross，圖和名字對得上）。
  - 32–47 號推定是給 PK 道具編輯器（`ｸﾞﾗﾌｨｯｸ`）讓玩家自訂道具時選的圖 🟡。
- **持有者**：
  - 各劇本 SNDATA 段的最後 1100 bytes 是 100 筆 × 11 bytes；+0 u16 是持有者，0xFFFF 表示沒有。
  - 持有者的值是該劇本人物記錄的序號，從 1 起算，順序是 SNDATA 在前、TAIKI 在後（`sango.san5_records` 的順序）。+2 是 0xFF，其餘是 0。
  - ✅ cross：方天画戟→呂布、青龍偃月刀→関羽、孟徳新書→曹操；玉璽在劇本 1 是何進，劇本 4 起是曹操。換成 kaodata id 後，223 筆和 `san5pk-pc98` 的人名全部一致。
- **沒有道具說明文**：MESSAGE.S5 沒有逐件的說明段。`MAIN.EXE` 只有道具編輯器的字串（ランク、特殊効果、ｸﾞﾗﾌｨｯｸ、ｱｲﾃﾑ削除）。

### MESSAGE.S5

- **結構**：LS11，56 段，每段開頭是 u16 個數，接著是 u16 offset（`biography.offset_table(p, True)`）。日文版共 3578 則，DOS 中文版共 3534 則，兩版的段不是一一對應。
- **控制碼**：
  - `01 22` 是行屬性，不帶參數；其他 `01 xx` 後面接 2 bytes。
  - `02 xx yy` 插入變數，輸出寫成 `{V:xxyy}`。
  - `04 xx`、`06 xx` 推定是選項清單的條件 🟡。
  - `0A` 換行；`05 05 05` 結束一個選項。
- **日文**：Shift-JIS，半形假名照三國志IV 的慣例寫成平假名，外字取自 FONT.S5（0xEB9F 起）。
- **中文**：用 `biography.koei_tw_text`，88 則還有不認得的碼，寫成 `[xxxx]`。
- **plain 欄**：去掉控制碼後的文字。

### 開場、結局

- **呼叫位址**：
  - OPEN.EXE：code seg 0 在檔案 0x1800，DGROUP 在 0xCB10。開檔 0:0x89a8、讀 0:0x7a70、NPK 解壓 0:0x671e、畫圖 0:0x2e88、設色盤 0:0x6676。
  - END.EXE：code seg 0 在檔案 0x1600，DGROUP 在 0xC820。開檔 0:0x88bc、讀 0:0x7990、設色盤 0:0x658a。
- **NPK16**：`OPEN1`、`OPEN3`、`OPTITLE.S5` 是 NPK16，就是 NPK016（見 `notes/npk016.md`）。
  - 解出的長度剛好是 w×h。
  - OPEN1、OPEN3 的 NPK 塊後面直接接 raw 資料，要在 raw 的起點（0x357D0、0xC0F6、0xE26C）切開。
- **色盤**：`OPENPLD.S5` 43 組、`EDPAL.S5` 41 組，每組 48 bytes，16 色 ×（B、R、G）nibble，程式用檔內 offset 選組。
  - B、R、G 的順序和三國志IV `OPENDAT.S4` 的場景色盤相同（OPEN.EXE 依序寫 port 0xAE、0xAC、0xAA，見 `notes/san4.md`），✅ cross。
  - 選第幾組 ✅ code；顏色沒和截圖比過。
- **開場**：`opening/op-01`–`13`，依序是龍、龍全身、龍紋浮雕、城樓遠望、戰場 3 張、武將 3 張、山水、三君主、標題。各張的來源與證據見 `opening-ending.csv`。
- **結局**：`ending/ed-01`–`07`，依序是都城鳥瞰、宮門、皇帝即位、宮殿內、皇帝背影 2 張、騎兵（ENDSCR，NPK016）。
  - END2 部分圖的寬度是由檔案大小推的 🟡。
  - END3 的色盤 🟡；END4 的 272×336 ✅ code（0x678d）。
- **動畫格**：OPEN1 的龍 10 格、OPMONO 41 格、END2 的 26 格（576×160）只放進 contact sheet。

### 進度

| 項目 | 狀態 | 證據 | 說明 |
|------|------|------|------|
| 事件圖 ESTL 34 張 | 🟡 | code | 圖 ✅；名稱看圖，和事件的對應沒追 |
| 一騎討ち背景、武術大會 | 🟡 | code | 各塊位置 ✅；800×600 組合、武術大會版的條件 🟡 |
| 武術大會對戰表 | ✅ | code | 0xbcdd8 |
| 一騎討ちモード（IMODE） | 🟡 | code | 排法 ✅；色盤 🟡 |
| 場景背景 CANMB 9 張 | 🟡 | code | 索引 ✅；寬度、名稱看圖 |
| 勢力分布圖 FMAP | 🟡 | code | 尺寸看圖 |
| 大地圖 16 色 4 季 | ✅ | capture | `guest-os-000.png`（季節 3） |
| 大地圖 256 色 4 季 | 🟡 | code | 色的順序、季節對應看圖 |
| 道具 32 件名稱（日、繁中） | ✅ | code+cross | DOS 版名表 |
| 道具加成 3 值 | 🟡 | code | 欄位意義推定 |
| 道具圖 48 張 | ✅ | code+cross | 0xb4c3a；32–47 的用途 🟡 |
| 持有者 12 劇本 223 筆 | ✅ | cross | kaodata 人名一致 |
| MESSAGE.S5 日 3578、繁中 3534 | 🟡 | code | 文字 ✅；部分控制碼意義未明 |
| 開場 13、結局 7 張 | 🟡 | code | 檔位置、色盤號 ✅；顏色沒和截圖比 |
| END1、OPV | ❌ | | 見「未解」 |
| UI、IKKI1/2、CANMA | 🟡 | | 只出 contact sheet（無名碎片） |

### 未解

- ESTL 第 n 張對應哪個事件：分派在 0x71c12，表 es:[0x44b8]，表的內容沒讀。
- 道具加成 +0–+2 的意義、+2 之後 0xFF 的意思、自訂道具的等級與圖號欄位。base 版截圖 `captures/screenshots/san5-pc98/main_000.raw1.png` 的曹操知力 97（本體 96）和孟徳新書的 +5 對不上，但那是本體不是 PK。
- IKKI1/2、CANMA 的分格；CANMD 的動畫腳本。
- IMODE 的色盤；256 色地圖的季節順序。
- MESSAGE.S5 `01 xx`、`04`、`06` 控制碼的意義；中文 88 則有不認得的碼。
- END1（40×48 格加遮罩，END.EXE 0:0x2db8、0:0x9c92 的 0x8000 旗標）、OPV（END.EXE／OPEN.EXE 0:0x0a0b 依 DS:0x1FC 的座標表剪貼）沒解。END3、END4 除了已匯出的部分，其他精靈沒拆。

### 下一輪候選

- 事件圖對應：前置無；做法：讀 0x71c12 與 es:[0x44b8] 的表，列出事件號→ESTL 號。
- 色盤的 capture：前置是在模擬器跑一騎討ち、武術大會、開場與結局；做法：截圖對 IMODE、IKKIHAI、op-01、op-13、ed-03、ed-07 的色號，順便確認 256 色地圖的季節。
- 道具加成：前置是 PK 版存檔；做法：截圖比對持有道具前後的能力。
- END1、OPV：讀 0:0x2db8、0:0x0a0b、0:0x9c92，拿到 atlas 的 pitch 後輸出格表。

### 負面結論

- 用「相鄰列相等」猜寬度：有網點的圖都失敗，改用程式的參數或看 4 bytes 一組的 hex。只有在圖沒有網點時才值得重試。
- MAP256 當作 64 寬逐列排：錯。它是 16 寬 × 592 列一欄，共 50 欄；要先讀 0x88540 才看得出來。
- MAINMAP 試了 rcp、cpr 等手猜的排法：都錯。它是每欄 4 個 plane 依序排；先對截圖的結構才定下來。
- END1 試了 640／480／320／240／160 寬與 6 種 plane 排法：都對不上。它是 40×48 的格加遮罩；要先讀懂畫法才值得重試。
