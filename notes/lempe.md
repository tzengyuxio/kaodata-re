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
- 姓名照中文版。中文版有 7 人寫成了別人的譯名（例如 id 25 英文版是 Milhaud，中文版寫成 Moreau 的「莫羅」，和 id 41 重名），依英文版、日文版人名改正在 `kaodata_export.LEMPE_NAME_HISTORICAL`，譯名取自 koei-wiki 的人物對照表（`assets/data/lempereur/lempe-persons-mapping.csv`）。
- 還沒定論、沒有填 `nameHistorical` 的：
  - 14 儒爾當（英文版 La Mette）
  - 84 昂吉迪（Wade）
  - 101 布霍布登（Bagavout）
  - 161 路易斯（Luveck）
  - 175 貝利加德（Berg，與 155 重名）
  - 176 科魯華特（Cleves）

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
