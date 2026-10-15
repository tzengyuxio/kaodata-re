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

- 來源：Neo Kobe 2016-02-25 的 `games/archives/pc88/neo-kobe-2016-02-25/L'Empereur/`，用 `[FD] [Set 1]`（REL.1C）。
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
