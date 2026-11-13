# 拿破崙（L'Empereur, DOS）頭像相關格式

`dekoei.py export lempe-dos` 用到的格式。

## 版本

- 匯出用中文版（`games/lempe-dos/`，原壓縮檔 `拿破崙_中文版_l-empereur-c.rar` 的 `lempereur/`）。英文版（`拿破崙_英文版_l-empereur.zip`）的 `KAODATA.DAT` 與中文版逐 byte 相同，五個劇本的人物順序和頭像碼也相同，只差人名文字。
- 英文版 `MAIN.EXE` 沒有壓縮，下面的位址都是它的檔案 offset 扣掉 MZ 檔頭後的映像位址，DGROUP 在檔案 0x3E6E0。

## 像素格式

- 和三國志II DOS 相同（見 [san2.md](san2.md)）：3bpp byte-interleaved planar、半高，每張 64×40 資料＝960 bytes，顯示成 64×80。
- `KAODATA.DAT` 共 260 張。
- 色盤：EGA `#000000 #55FF55 #FF5555 #FFFF55 #5555FF #55FFFF #FF55FF #FFFFFF`。

## 人物

- `NPDATA.CIM`，沿用 `lempe person` 的讀法（`koei_games.load_lempe_persons`）：五個劇本各 255 筆，每筆由兩段（17＋15 bytes）拼成 32 bytes，第 14 byte 是頭像碼。
- 五個劇本是同樣 255 人、同樣順序，頭像碼是 0–254 的排列，所以匯出只讀劇本 1，`id` 就是記錄順序。
- 姓名照中文版。網站的目標是用遊戲自己的名字顯示每張臉，人物身分的考證之後放在 koei.wiki。
- 中文版明顯寫成別人、或寫錯的 11 人，在 `kaodata_export.LEMPE_NAME_HISTORICAL` 填 `nameHistorical`。判斷依據是英文版和日文版的人名，日文名取自 koei-wiki 的人物對照表（`assets/data/lempereur/lempe-persons-mapping.csv`）。前 7 人是首次匯出時填的；138、150、165、175 是使用者對照 `lempe-fc` 後決定的。

| id | 中文版 | 英文版 | 日文版 | `nameHistorical` | 理由 |
|---|---|---|---|---|---|
| 25 | 莫羅 | Milhaud | ミロー | 米約 | 誤用 Moreau 的譯名，和 id 41 重名 |
| 52 | 格魯希 | Gourgaud | グールゴ | 古爾戈 | 誤用 Grouchy 的譯名，和 id 23 重名 |
| 77 | 塞納爾蒙 | Somerset | サマセット | 薩默塞特 | 誤用 Sénarmont 的譯名 |
| 104 | 洛巴諾夫 | Ubarov | ウバロフ | 烏瓦羅夫 | 誤用 Lobanov 的譯名 |
| 109 | 奇恰可夫 | Gortschakow | ゴルチャコフ | 戈爾恰科夫 | 誤用 Chichagov 的譯名 |
| 121 | 巴拉肖夫 | Woronsov | ヴォロンツォーフ | 沃龍佐夫 | 誤用 Balashov 的譯名 |
| 138 | 馬迪諾 | Oudinot | ウディノ | 烏迪諾 | 譯名錯字 |
| 150 | 歐圖一世 | Otto I | オット | 奧特 | 是奧地利將軍 Ott，不是君主 |
| 160 | 博利厄 | Gruber | プロヴェラ | 普羅韋拉 | 誤用 Beaulieu（id 230）的譯名；依日文版判定為 Provera |
| 165 | 儒瑾 | Rujean | ルジヒナン | 呂西尼昂 | 是 Lusignan |
| 175 | 貝利加德 | Berg | ベルク | 貝爾格 | 和 id 155 Bellegarde（ベレガルデ）重名，是筆誤 |

- 決定不填 `nameHistorical` 的：

| id | 中文版 | 英文版 | 日文版 | 理由 |
|---|---|---|---|---|
| 14 | 儒爾當 | La Mette | ラメット | 有爭議，維持原樣 |
| 97 | 霍夫頓 | Buxhowden | ビグソーデン | 有爭議，維持原樣 |
| 142 | 希爾曼 | Thielmann | ティーデマン | 有爭議，維持原樣 |
| 169 | 邦哈美 | BonHomme | ボーム | 有爭議，維持原樣 |
| 122 | 威廉三世 | Wilhelm III | ヴィルヘルム | 簡稱或後來的稱號，不算錯 |
| 147 | 法蘭一世 | Franz I | フランツ | 簡稱或後來的稱號，不算錯 |

- 身分仍待考、也沒填的：84 昂吉迪（Wade／アーチディーケ）、101 布霍布登（Bagavout／バゴブート）、161 路易斯（Luveck／ルイス）、176 科魯華特（Cleves／クレーヴェ）。

### 能力

- 狀態視窗（英文版 `MAIN.EXE` 0x166FA）：Politics Finance Supply Build／Leader Infantry Cavalry Artillry（各 D–A）、Loyal、Exper、Age、Men Mor Trng。中文版的用語（0x3FDC0）：忠誠 政治 財政 補給 建設 領導 步兵 騎兵 砲兵 經驗 兵力 士氣 訓練 年齡。日文版沒找到能力名稱的漢字字串。
- 人物記錄 R＝`NPDATA.CIM` 檔案 2＋15·i（每劇本 +13270）：+2 國、+3 所在（城市名在檔案 7370，46 個）、+4 政治 財政 補給 建設、+5 領導 步兵 騎兵 砲兵（各 2 bit、低位在前，0–3＝D C B A）、+6 經驗、+7 忠誠（拿破崙顯示「--」）、+8 年齡、+9 兵力、+0xC 訓練、+0xD 士氣、+0xE & 0xF 官階。讀取用 `koei_stats.load_lempe_stats`，`dekoei.py koei-person lempe-dos`。
- 各平台的位置：PC-88 從 1 起，每劇本 0x3100；X68000 `NPDATA1.DAT` 從 4 起、間距 18。
- ✅ code：英文版 `MAIN.EXE` 0x166FA、0x659C（等級表 DS:0x8FAE）。✅ cross：PC-88 五個劇本、X68000 劇本 1、英文版和 DOS 中文版相同；1795 年拿破崙 26 歲。
- 🟡 R+0xB 非 0 是砲兵、否則 R+0xA 非 0 是騎兵、否則步兵（0x6078）。名字 +15 是 bits 0–1（只有 0–5 號是 3，波拿巴家族？）加上 bits 2–7 的 6 個旗標；舊碼的冷靜、勇猛、魅力、幸運等名稱沒有根據。❌ +16（大多是 6）、R+0、R+1。
- 已修正（2026-10-22）：舊 `lempe_person` 忽略 `--scenario`（`PERSONS_TABLE/lempe-persons-s1…s4-*.csv` 完全相同），第二段錯開 2 bytes、漏了經驗、年齡、官階；ldr 標成「指揮」（遊戲用語是「領導」）；名字 +15 的四欄 冷靜 勇敢 魅力 幸運 沒有根據，改成一欄「隱藏」印出 8 個 bit；Bordeaux 原本譯成「布倫」，改成「波爾多」。`-s` 從 1 起算。s1–s4 的 en／zh 表已重新產生（en 用英文版 `NPDATA.CIM`，不在 `games/`）。

### koei-wiki 匯出

```sh
cd dekoei
../.venv/bin/python dekoei.py places-export lempe-dos --game-dir ../games/lempe-dos --out ../export/koei-wiki/places
../.venv/bin/python dekoei.py persons-export lempe-dos --game-dir ../games/lempe-dos --out ../export/koei-wiki/persons --places ../export/koei-wiki/places
```

`wiki_lempe.py`，koei-persons/1 與 koei-places/1。旁邊要有 `../lempe-pc88`（日文名）和 `../archives/dos/拿破崙_英文版_l-empereur.zip`（英文名，直接讀 zip 裡的 `empereur/NPDATA.CIM`；英文版的 `NPDATA.CIM` 除了名字，五個劇本的人物與城市記錄和中文版 byte 相同）。以下位移都是劇本內的位移（每劇本 13270 bytes）。

- 劇本：5628 是 u16 年份（1796、1798、1802、1806、1815），下一個 byte 都是 3，當成 `month`（標 `uncertain`）；5632 是劇本號 1–5。
- 國名：7220＋10·n，15 國（法蘭西 荷蘭 巴伐利亞 丹麥 土耳其 意大利 威尼斯 那普斯 葡萄牙 瑞典 西班牙 普魯士 俄羅斯 奧地利 英格蘭）；PC-88 在 `NPDATA.CIM` 0x1BA1＋9·n（半形片假名）。
- 城市：7370＋34·c，46 個，五個劇本相同。+0 名字（15 bytes），+16 x、+21 y（畫出來是歐洲的形狀【推】），+26–+32 相鄰（0xFF 是空，全部雙向），+33 旗標。PC-88 在 0x1C28＋31·c，名字 12 bytes，之後 19 bytes 和 DOS 的 +15–+33 相同。+15、+17–+20、+22–+25（像是另外幾組座標，0xFF 是沒有）沒解。
- 城市的領有國：4102＋28·c，255 是無主（羅馬在劇本 1、5）。

人物（255 人，`id` 同 kaodata，也就是記錄順序；和 koei-wiki `lempe-persons-mapping.csv` 的編號、遊戲中文名、日文名、英文名逐筆相同）：
- `name` 用中文版，`nameJa` 取 PC-88（NFKC 轉全形），`game.英文名` 取英文版。史書寫法（`LEMPE_NAME_HISTORICAL`）寫在 `notes`。
- `stats` 是 8 項等級 D–A（五個劇本都相同）；`more` 是劇本 1 的 國 經驗 忠誠 兵力 士氣 訓練 年齡，標籤是中文版狀態視窗的字。
- `born`＝劇本年－年齡。年齡 0 的是已死（官階 15），不算。7 人各劇本算出的生年不一致（26、56、75、83、138、216、229），取最早的劇本，`uncertain` 標 `born`。
- `scenarios`：
  - `status` 是官階（R+0xE & 0xF）在中文版 `MAIN.EXE` 的稱呼（0x3BE88 起，對應見上面英文版 0x60E8 的分析）：2 戰俘、3 預備軍官、4 現役軍官、5 司令官、6 督政官、7 國王；拿破崙 6 是第一執政、7 是皇帝。官階 0、1 沒有稱呼，不填 `status`（1 是王位繼承人）。15 是不在地圖上（已死或被取代），寫「不在」，不是遊戲用語，標 `uncertain`。年齡 ≥ 200（還沒出生，維多利亞）寫「未登場」。拿破崙官階 5 在某個條件下顯示「總司令官」，條件沒追，寫司令官。
  - `location` 是 R+3 的城市號；`lord` 是同國的國王（官階 7），沒有國王時是督政官（官階 6，1796、1798 年的法蘭西是巴羅斯、威尼斯是曼寧）。戰俘、官階 0–2 不填 `lord`；`loyalty` 是 R+7（拿破崙沒有）。
- 沒填：名字 +15 的隱藏旗標（名稱不明）、兵種、`relations`（遊戲沒有）。

城市（46 個）：
- `name` 用中文版的寫法（28 號是「布倫」，實際是波爾多），`nameJa` 取 PC-88，`game.英文名` 取英文版。`level` 一律「城市」，遊戲沒有地方區分，不填 `region`。
- `adjacent` 是 +26–+32（都柏林沒有相鄰）。`scenarios[].國` 是領有國，`lord` 是該國的國王或督政官。
- `game.座標` 放 +16、+21，`game.臨海` 是 +33 bit 0（和地理一致，【推】），都標 `uncertain`。大地圖（`HEXDATA.DAT`）沒解，所以沒有 `pos` 和 `world/`。
- 檢查：places-export 320 項、persons-export 2508 項、koei-wiki `verify_persons.py` 5569 項、`verify_sanguo_places.py` 575 項，0 不符。

## 頭像碼 0xFF–0x103

人物資料的頭像碼只有一個 byte，P255–P259 由程式直接把碼傳給畫頭像的函式（0xA17A，參數是頭像碼，0 起算）：

| 頭像 | 碼 | 出處 | 用途 |
|---|---|---|---|
| P255 | 0xFF | 0x6096：取人物頭像時，若是拿破崙且官階＝6 | 拿破崙：第一執政 |
| P256 | 0x100 | 同上，官階＝7 | 拿破崙：皇帝 |
| P257 | 0x101 | 0xE14A 事件 2「My love, please be careful!」；0x12EC4 字串「Josephine」 | 約瑟芬 |
| P258 | 0x102 | 0x12EC4 字串「Marie Louise」 | 瑪麗路易斯 |
| P259 | 0x103 | 0xE14A 事件 3、5（埃及遠征）；0x1D26D | 尼爾森 |

- 0x6096 與官銜函式 0x60E8 都用 0x5F82 取官階，拿破崙是參數 0x44。0x60E8 把官階換成官銜表（DGROUP 0x3984 起的指標，索引 2 起依序是 War prisoners、Reserves、Officers、Commander、Commander-in-Chief、Governor、First Consul、King、Emperor）的索引：
  - 官階 5：Commander；拿破崙在 `[0x1642]`＝2 時是 Commander-in-Chief
  - 官階 6：拿破崙是 First Consul，其他人是 Governor
  - 官階 7：0x6CFC 成立時是 Emperor，否則是 King（King 的人若是 Carolina／Victoria 改成 Queen）
- 所以 P255＝第一執政、P256＝皇帝。匯出時放在人物 0 的 `expressions`，`label` 用中文版 `MAIN.EXE` 的官銜：P000「司令官」（官階 ≤5，也用在「總司令官」）、P255「第一執政」、P256「皇帝」。中文版官銜表依序是 戰俘（未解碼）、預備軍官、現役軍官、司令官、總司令官、督政官、第一執政、國王、皇帝。
- P257–P259 的名稱用中文版 `MAIN.EXE` 的寫法：「約瑟芬」「瑪麗路易斯」「尼爾森」。

## PC-88 版（`lempe-pc88`）

`dekoei.py export lempe-pc88` 用到的差異（`build_lempe(pc88=True)`）。

- 來源：Neo Kobe 2016-02-25 的 `~/game-library/_original/pc88/neo-kobe-2016-02-25/L'Empereur/`，用 `[FD] [Set 1]`（REL.1C）。
  - 基本的 `[FD]` 是 REL.1A，Disk C 少了第 33 軌，`KAODATA.DAT` 從 0x12200 起錯位，不能用。
  - `[Set 2]` 的資料檔和 Set 1 相同。
- 磁碟：A、B、C 三片都是 YDOS 3.0，每軌 9 × 512 bytes。
- `games/lempe-pc88/` 放 Disk C 的 `KAODATA.DAT`、`NPDATA.CIM`，以及參考用的 Disk A `MAIN.COM`、`MAIN.OVL`。
- 版本：`NAPO.DIR` 寫 `REL.1C ****** L'EMPEREUR ******* KOEI`，遊戲檔日期 1990-05-17～06-28。
- `KAODATA.DAT` 和 DOS 版**逐 byte 相同**，DOS 版沿用了 PC-88 的 200 線圖。
- 色盤：數位 8 色（`SAN2_JP_PALETTE`，palette id `pc88`）。YSHELL 清掉 port 0x32 bit 5（數位模式）。
- 人物：`NPDATA.CIM` 每個劇本 0x3100 bytes，人物從 0x21BA 起，255 × 15 bytes：姓名 12 bytes（半形片假名，NFKC 轉全形），+12 是頭像（`koei_games.load_lempe_pc88_persons`）。
  - 5 個劇本相同。
  - 順序和頭像逐筆同 DOS，`id` 一致。
- `nameHistorical`：DOS 版的 11 筆是中文翻譯錯誤，日文版寫法是對的（ミロー、ウディノ等），不填。
- `nameZh`：和 `lempe-fc` 的 `nameZh` 相同（`LEMPE_PC88_NAME_ZH`），讓兩個假名版顯示同樣的中文名。內容是 DOS 中文版的人名，換上 `LEMPE_NAME_HISTORICAL` 的 11 筆，並在 7 位君主的名字加上世號（如 122 腓特烈·威廉三世、147 弗朗茨二世）。
- P255–P259：拿破崙的第一執政、皇帝臉沿用 DOS 的結論（PC-88 `MAIN.COM` 0x31A2 的官銜表有同樣的「第一執政」「皇帝」）。P257–P259 的名字照 PC-88 的字串：`MAIN.OVL` 0x4389 ジョゼフィーヌ、マリー・ルイーズ，`COMSUB.OVL` 0x1270 ネルソン。

## X68000 版（`lempe-x68`）

`dekoei.py export lempe-x68` 用 `build_lempe(x68=True)`。

- 來源：Internet Archive `lempereur_19xx_koei_disk_1_of_x68k`（`~/game-library/_original/x68/ia-softwarelibrary/`，A、B、C 3 片 DIM），沒有版本字串。`games/lempe-x68/` 放 C 片的 `KAODATA.DAT`、`NPDATA1.DAT` 與參考用的 A 片 `MAIN.Z`。
- `KAODATA.DAT`：260 張 64×80 全高、每 8 px 3 bytes，byte k＝plane k（1920 bytes）。順序同 DOS／PC-88，但是另外重畫的全高圖，不是把半高圖逐列加倍。
- 人物：`NPDATA1–5.DAT` 一個劇本一檔，從 0x2C92 起 255 筆 × 16 bytes（PC-88 的 15 bytes 記錄加 1 byte 補位），名字 12 bytes 半形片假名、頭像在 +12。5 個劇本和 PC-88 劇本 1 逐筆相同，所以 id、名字、`nameZh`、拿破崙的三張臉、257–259 的名字都照 `lempe-pc88`（`load_lempe_pc88_persons(..., x68=True)`）。
- 色盤：`MAIN.Z`（沒有壓縮，執行位址＝檔案＋0x514DE）由 0x81FD2 把 0x86C44 的 16 色設到文字色盤，0–7 是數位 8 色（palette id `x68`，同 `ISHIN_PC98_PALETTE`）。
