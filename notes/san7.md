# 三國志VII with パワーアップキット（SAN7PK, Windows 日文版）頭像相關格式

`dekoei.py export san7pk-win` 用到的格式。來源是 Steam 版（appid 628030，見 `notes/steam.md`），匯出用到的檔案複製到 `games/san7pk-win/`。

## 版本與 EXE

- Steam 版 `San7WPK.exe` 有 SteamStub 3.1 DRM：`.text`（檔案 0x1000–0x33B000）是 AES-256-CBC 加密的，金鑰在 SteamStub 標頭（入口點 − 0xF0，逐 dword XOR 串接解開；key +0x58、IV +0x78，IV 先用 key 做 ECB 解密）。看程式碼時要先解密，匯出只讀 `.data`，不受影響。
- image base 0x400000，`.rdata`、`.data` 的 VA＝檔案位置＋0x400000。

## Kaodata.s7：頭像

- 格式同三國志VI 的 KAODATA.S6：u32 張數（678），接著 678 × (offset, size, w, h) 各 u32，offset 從表尾（4 + 16 × 678）算起。每張 96×120、8 bit 色號，沒有壓縮。
- 頭像號就是索引。程式裡的資源號是 0xE23＋頭像號（檔案表 0x7FCF0C：`Kaodata.s7` 的資源 0xE23–0x10C8）。
- 新武將的選臉清單（EXE 0x408020／0x408050／0x408100）把頭像分成：
  - 0–519：武將（頭像號＝武將編號）
  - 520–589：新武將（男）70 張，590–619：新武將（女）30 張
  - 648–668：PK 的新武將（男）21 張，669–677：PK 的新武將（女）9 張。清單在本體的範圍後面另外接上，所以標 `pk`。
  - 620–647 不在清單裡：虎、戴冕的天子、女性、老人等 28 張，是事件用的臉。EXE 程式碼裡找不到這些頭像號，應該是在事件資料裡指定，還沒追到，只標 `事件人物`。
- 全部 678 張都有用到色號 255，只有色號 0（色盤的洋紅 `#ff00ff` 去背色）完全沒用到。匯出時把 255 換成 0，色盤第 0 色改成原本第 255 色，共 255 色。
- 頭像依頭像號切成約 1 MB 一包（`portraits.bin`–`portraits6.bin`），PK 追加的 648–677 放最後的 `extra.bin`。

## 色盤：P_Kao.s7

- 一個 Windows LOGPALETTE：版本 0x300、256 色，每色 R、G、B、flags。

## 人物：D_Sn???.s7

- 12 個劇本：D_Sn001–007（本體）、D_Sn101–105（PK），每檔 109060 bytes。
- 前 0x4C bytes 是明文標頭（`SAN7PVERSION10`，+0x1A u16 劇本號，+0x1C u16 開始年）。之後每個 byte 都經過替換表編碼：EXE 檔案 0x4E5500 起有 4 張 256 bytes 的表（第 k 張在 0x4E5500＋0x100 k），每個劇本用其中一張。檔案裡最常出現的 byte 是編碼後的 0，取 `表[0]` 等於它的那張，再用反查表解回（`sango.decode_san7_scenario`）。實際上是 001→1、002→2、003→3、004→0、005→1…、101→2、102→3、103→0、104→1、105→2。
- 人物表從 0x30A 起，620 筆 × 0x78 bytes：0–519 是武將，後 100 筆是新武將空位（「武将００」…，編號 0xFFFF）。
  - +0 u16 武將編號（＝頭像號），+0x24 再存一次
  - +0x2A 姓 6 bytes、+0x30 名 6、+0x36 字 6（Shift-JIS，NUL 結尾）
  - +0x3C 讀音 12 bytes（半形片假名，姓名之間沒有分隔）。匯出成平假名、不加空白，同 `san1-sfc` 等
- 12 個劇本的 520 位武將編號與姓名都相同，所以人物表依編號列一次，`id` 就是武將編號。
- 姓名裡有 38 個 `S7gaiji.tte`（EUDC 字型）的外字，Shift-JIS 解成 Unicode 私用區 U+E000 起。用字型畫出來對照，查表換成正字（`sango.SAN7_GAIJI`），例如 U+E00C 龐、U+E01D 褚、U+E000 瓚。
- 223 和 479 都叫馬忠（蜀的馬忠與吳的馬忠），是兩個人。

### 能力

- 人物記錄（解碼後）+0x4B 起依序是武力、知力、政治、魅力，各 u8（`sango.load_san7_stats`，`dekoei.py san7 person`）。七代沒有統率。
- 520 人裡有 13 人的值隨劇本不同，例如諸葛亮的武力 78（189 年）、83（217 年）、87（225 年以後），其他都一樣；全部在 1–100。
- 沒有遊戲畫面可以對照；和參考表 S07 欄的劇本 1 值一致（cross）。

## 事件、插圖、道具

`san7-extras`（`dekoei/san7_extras.py`）讀 `games/san7pk-win/`（Steam 安裝目錄裡用到的檔，見 `notes/steam.md`「安裝目錄的刪除」），輸出到 `games/san7pk-win/extract/`（約 71 MB、7947 個檔，跑一次約 10 秒）：

```sh
cd dekoei
../.venv/bin/python dekoei.py san7-extras --game-dir ../games/san7pk-win --out ../games/san7pk-win/extract
```

影片（`MOVIE/`）、BGM（`BGM/*.wav`）照規定不留。

### 圖檔 G_*.s7

- 220 個 `G_*.s7` 都是 `Kaodata.s7` 那種容器：u32 張數，張數 ×（offset、size、w、h）各 u32，offset 從表尾算，8 bit 色號、沒有壓縮。✅ code（每個檔的 size＝w×h、最後一張剛好到檔尾）
- 色盤是同名的 `P_*.s7`（LOGPALETTE），色號 0（純綠）是去背色。`G_KUNIT0–9` 共用 `P_Kunit.s7`；`G_YU_*` 有 8 組色盤 `P_YU_<名>1–8`，只用第 1 組 🟡。`G_YMap00–29` 是 BMP，由 `places-export` 輸出，這裡不重複。
- 分類（看縮圖決定，用途 🟡）：

| 輸出 | 檔案 | 張數 | 內容 |
|---|---|---|---|
| `eventcg/still/` | `G_StlEvD/H/J/O` | 25 | 事件靜止圖 300×200 |
| `eventcg/ending/` | `G_StlEd1–4`、`G_SSEnd1–4` | 30 | 結局圖 336×224 |
| `eventcg/scenery/` | `G_StlMe1–3` | 30 | 風景、建築（推定是名所） |
| `eventcg/pk/` | `G_PKRev1–6`、`G_Moji` | 52 | PK 圖 6 張；PK 歷史戰役標題用的書法字 46 個 |
| `eventcg/figures/` | `G_Ev00Ga–05Bu` | 722 | 事件場景的人物立繪與動作格 |
| `eventcg/banners/` | `G_Ev20Ek–26Ta` | 35 | 528×128 的橫幅背景 |
| `eventcg/sorcery/` | `G_WHouou`、`WKirin`、`WRyuu`、`WMajin`、`WThund`、`WTaiho`、`WJutsu`、`WJY`、`WBk*` | 173 | 仙術、召喚獸、戰鬥特效與其視窗框 |
| `eventcg/duel/` | `G_IK*` | 209 | 一騎討ち的背景、人物、虎（`G_IKTora`） |
| `eventcg/title/` | `G_M8Titl`、`G_Start`、`G_M9Logo` | 73 | 標題、開始畫面 |
| `pictures/<檔名>/` | 其餘 | 6504 | 介面、野戰與攻城的部隊和地圖零件（無名碎片） |

### 寶物

- 劇本 `D_Sn???.s7`（`decode_san7_scenario` 解開後）0x125BA 起 72 筆 × 40 bytes：
  - +0 u16 持有者＝人物表的格號（第 k 格的 +0 u16 才是武將編號），0xFFFF 沒人。✅ cross：189 年劇本的赤兎馬、方天画戟→呂布，絶影→曹操，青龍偃月刀→関羽，蛇矛→張飛，雌雄一対の剣→劉備，古錠刀→孫堅
  - +2 u16（1 或 0）❌
  - +4 名稱 18 bytes（Shift-JIS，外字同下面的訊息）✅ code
  - +0x16 u8 價值、+0x17 u8 加成（武器 3–10、書 2–10）🟡
  - +0x18 u8（0xFF 或 0x08–0x39，各劇本不同）❌
  - +0x24 u32 bitmask（名馬是 0x800，西蜀地形図、袖箭是 0x80…）❌：對成特技號（0 諜報…11 強行）時馬＝強行、地形図＝偵察說得通，但孫子の兵法書＝発明、青嚢書＝鬼謀說不通，沒採用。
- 圖：`G_Item1.s7` 0–33 接 `G_Item2.s7` 0–37，順序就是寶物號 ✅ cross（72 張都和名稱對得上：馬、武器、書、玉璽、銅雀、羽扇、長信宮燈、和氏の璧、黄龍、麒麟、鳳凰、大鵬）。
- 說明：`M_Msg.s7` part 30 的 0–71 ✅ cross；72–74 是三則效果說明（「戦闘時に必ず退却に成功します」「魅力が100になります」「戦闘中に召喚できます」），推定分別是的盧、玉璽、霊獸 🟡。
- 種類是照名稱分的（遊戲裡沒有種類名）🟡：0–4 名馬、5–23 武器、24–25 地図、26–29 方術書、30–33 兵法書、34–53 書物、54–55 玉璽・九錫、56–67 宝物、68–71 霊獸。
- 輸出：`items/items.csv`（號、名稱、種類、價值、加成、mask、圖、說明）、`items/pictures/NN.png`、`items/holders.csv`（12 劇本 × 72 筆，持有者的武將編號與姓名）。
- 兵装 14 種：`G_Soubi.s7` 160×160，名稱是 EXE 0x34E1F8 起的字串（倒序存放），照圖對上 ✅ cross：弓、藤甲、騎馬、馬鎧、鉄甲、弩、連弩、井闌、霹靂車、火炮、象、木獣、蒙衝、楼船（`items/equipment/`）。
- 特技 32 個的名稱：EXE 0x3FFFC0 的指標表是 武力、知力、政治、魅力，接著 諜報…富豪 ✅ code（`tables/tokugi.csv`）。人物記錄裡哪個 bit 是哪個特技還沒對。

### 訊息與列傳

- `M_Msg.s7`（53 part）、`M_BFile.s7`（13 part）都是 LS11。一個 part 是 u16 筆數＋筆數個 u16 offset（從 part 開頭算）。一筆可以有幾段文字，各以 05 05 05 結尾。✅ code
- 半形假名平常是平假名，ESC K 起是片假名、ESC H 回平假名（同三國志IX）；0A 換行；01＋3 bytes、02＋2 bytes 是變數，其他 0x20 以下的 byte 是指令，都照原樣寫成 `{..}`。
- 外字：姓名的 38 個用 `SAN7_GAIJI`；訊息另外有 15 個（彧、鄧、兗、畯、禕、琮、邳、琦、并、釭、涪、鄴、鄱、蒺、犍），用 `S7gaiji.tte` 畫出來、照上下文認的 🟡（`MSG_GAIJI`）。0xE0F1 以上的碼只出現在指令 byte 裡，不是字。
- `text/messages.csv`：`M_Msg.s7` 全文 7261 筆（part、entry、text）。各 part 的內容（看前幾筆判斷 🟡）：
  - 26 名所說明 86 筆（`text/sights.csv`）
  - 27、36、39、40、45、46、52 歷史事件與劇情的對白，共 1575 筆（`events/story.csv`；27 連環の計、39 孫策借兵、40 左慈、45 孫策平江東、46 銅雀台、52 政略結婚的樣板）
  - 41 年表 347 則（「曹操誕生」「桓帝、外戚の梁冀一族を誅殺する」…，`events/chronicle.csv`）
  - 47 人物經歷的樣板（「{..}の暗殺に失敗し、逃亡する」）
  - 31 指令的手引き、33 指令說明、34 兵装的說明、42 新武將編輯、43、44、48–50 目標與建言
- 列傳：`M_BFile.s7` part 1–11 共 521 筆，第 k 筆是武將 k 的列傳（0–519），最後一筆是「列伝はありません」✅ cross（0 楊奉、1 張飛、50 張松、500 左慈、519 王匡的內容都對得上）。輸出 `text/biographies.csv`（武將編號、姓名、全文），還沒接 `biography.py`。part 0 與 part 12 和 `M_Msg.s7` 的 part 0、52 byte 相同。

### 讀了安裝目錄的哪些檔

- `G_*.s7` 220 個（180 MB，其中 `G_YMap*` 43 MB）、`P_*.s7`、`M_Msg.s7`、`M_BFile.s7`、`D_Sn*.s7`、`San7WPK.exe`、`S7gaiji.tte`（核對外字），共約 188 MB。
- `games/san7pk-win/` 已有 `D_Sn*.s7`、`G_YMap*.s7`、`Kaodata.s7`、`P_Kao.s7`、`San7WPK.exe`。只缺 `G_YMap` 以外的 `G_*.s7`（約 137 MB）、其他 `P_*.s7`、`M_Msg.s7`、`M_BFile.s7`、`S7gaiji.tte`，共約 140 MB。安裝目錄 637 MB 裡 414 MB 是 BGM 與影片。

## 下一輪候選

- 事件觸發：事件對白在 `M_Msg.s7`，觸發條件應該在 EXE（`.text` 有 SteamStub，要先照「版本與 EXE」解密）；做法：從 part 27、39 的引用找事件表。
- 寶物的 +0x18、+0x24 與加成的對象：前置是解出人物記錄的特技 bit；做法：拿有特技的武將（諸葛亮、華佗）對 bit，再回頭對寶物。
- 列傳接 `biography.py` 交給 koei-wiki：`text/biographies.csv` 已經依武將編號排好。
- 事件靜止圖、名所圖對事件或名所說明：要從 EXE 找圖號表。

## 負面結論

- 把寶物 +0x24 的 bitmask 直接當特技號（bit 0＝諜報）：名馬＝強行、地形図＝偵察說得通，孫子の兵法書＝発明、青嚢書＝鬼謀說不通，所以不採用；要先確認人物記錄的特技 bit 順序再試。
- 寶物 +0x18 當成所在都市：189 年的赤兎馬是 8（城陽），但持有者呂布不在那裡，而且有 0x39（57）超過 54 都市，所以不是都市號。
