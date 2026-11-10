# 寶物匯出（koei-wiki，koei-items/1）

`dekoei.py items-export <dataset> --extract ../games/<id>/extract --game-dir ../games/<id> --out ../export/koei-wiki/items`（`dekoei/items_export.py`）寫 `export/koei-wiki/items/<dataset>.jsonl`，一格寶物一行。規格在 koei-wiki `docs/items-format.mkdn`。大部分欄位讀各遊戲 `*-extras` 輸出的 `extract/items/*.csv`，所以要先跑該遊戲的 extras；信長6、11 的 CSV 只留持有者的名字，持有者 id 要重讀劇本檔。

- `holders` 的 `person` 是 kaodata 資料集的人物 id。匯出時逐一檢查它在 kaodata `dataset.json` 的 characters 或 koei-wiki 人物匯出裡，不在就停止匯出。
- 持有者名字和人物名字不同的，都是同一人的別名（大友義鎮／大友宗麟、松平元康／徳川家康、木下秀吉／豊臣秀吉…），照 id 對 ✅ cross。
- 三國志的劇本號：有人物匯出的（`extract/tables/scenarios.csv`，由 `wiki_san<N>` 寫）照它的號碼，不在表裡的劇本檔不出；還沒有的照檔名排序。2026-11-11 起三國志IX、X 照人物匯出的號碼（X 原本把本體 7 個劇本也排進去，共 18 個，和人物匯出對不上）。
- 第一輪不出效果數值（信長6 的單一能力加成例外，CSV 裡就有）、圖。
- 持有者只留劇本開局在場的人：三國志VIII、12、13、14 的寶物表常把寶物記在當年還沒登場或已死的人名下，照人物匯出（`export/koei-wiki/persons/<dataset>.jsonl`）的劇本狀態，未登場、未発見、死亡與沒有該劇本記錄的不出（`_present`）。
- 三國志VII–12 的 `nameZh`、`descriptionZh` 讀 Steam 繁中版（`games/steam/<appid>-tchinese/depot`，和遊戲目錄並排，`items_export.ZH`），各代的 `<game>_extras.zh_items` 回傳寶物號 → (名稱, 說明)；位置與比對方式見各遊戲筆記的寶物段。三國志11 繁中版也沒有寶物說明，只填 `nameZh`。三國志13、14 的繁中讀自己的檔。

## 第 1 批（2026-11-11）

| 資料集 | 件數 | 有持有者的件數（筆數） | 說明文 | 讀哪裡 | 標 `uncertain` |
|---|--:|--:|---|---|---|
| `san4pk-pc98` | 31 | 19（129） | 日文、中文（DOS 中文版） | `items.csv`、`holders.csv`（已有 kaodata id） | kind |
| `san7pk-win` | 72 | 46（428） | 日文、繁中 | 同上；持有者欄就是 kaodata id，12 個劇本照檔名排號 | kind、price |
| `san9pk-win` | 100 | 44（658） | 日文、繁中 | 只出人物持有者（狀態 2）；放在都市的只有都市號，沒有名字，沒出 | kind、price、holders |
| `san10pk-win` | 200 | 181（1950） | 日文、繁中 | 人物或所在都市（`other`）；只出 PK 的 11 個劇本（本體的 `Sce00?.s10` 不出）；人物槽 763 以後不在 kaodata，寫在 `notes` | — |
| `san11pk-win` | 43 | 43（592） | 沒有（繁中也沒有，只有 `nameZh`） | 人物或所在地（`other`）；7 個「アイテム」空槽不出 | kind、price、holders |
| `nobu6pk-pc98` | 120 | 57（152） | 日文 | 持有者是各劇本名字記錄的槽號（從 1 起），槽的頭像號換成 id（同 `wiki_nobu6`）；`effects` 是 CSV 的加成能力與數值 | — |
| `nobu7pk-win` | 200 | 78（387） | 日文 | 持有者 n（從 1 起）是 id n－1；種類只有數字，沒出 | grade |
| `nobu8pk-win` | 350 | 111（614） | 沒有 | 持有者 n 就是 id n；`price` 取劇本 10 的值 | grade、price |
| `nobu9pk-win` | 380 | 198（1885） | 沒有 | 人物用 id，都市用名字（`other`）；`pk` 是 PK 的 30 件 | grade |
| `nobu10pk-win` | 460 | 83（510） | 日文 | `holders.csv` 的持有者就是 id | — |
| `nobu11pk-win` | 430 | 145（664） | 日文 | 持有者連號：武將槽（`wiki_nobu11.OFFICERS`）是 id，勢力寫成「當主名勢力」（`other`）；劇本號是 DBSCEDA 的號碼 | kind（圖的種類） |
| `nobu12pk-win` | 355 | 109（596） | 日文 | `owners` 的名字對人物匯出的名字，每個名字都只對到一人 | grade |

三國志VII、IX、X、11 的繁中名稱與說明在 2026-11-11 補上（第 2 批同一天），件數與持有者不變。

## 第 2 批（2026-11-11，三國志）

| 資料集 | 件數 | 有持有者的件數（筆數） | 說明文 | 讀哪裡 | 標 `uncertain` |
|---|--:|--:|---|---|---|
| `san8pk-win` | 255 | 43（1209） | 日文、繁中 | `items.csv`；持有者重讀 `D_Sce.s8` 0x129C5 的持有表，51 個劇本（184–234 年）照 `scenarios.csv` 的年份取值，不在場的 611 筆不出；放在都市的寫在 `notes` | kind、price |
| `san12pk-win` | 205 | 64（522） | 日文、繁中 | `items.csv`；持有者重讀 17 個劇本檔名品段的 bit 448，不在場的 324 筆不出；`pk` 是 184–204 | kind、price |
| `san13pk-win` | 234 | 234（2347） | 日文、繁中 | `items.csv`；持有者重讀 PK 第 942–952 項第 7 子項：人物 251 筆（不在場的 7 筆不出），放在地點的 2096 筆是 `other` | price、holders |
| `san14pk-win` | 131 | 46（591） | 日文、繁中 | `items.csv`（名稱、說明兩種語言都有）；持有者讀 27 個劇本檔 `scedaex*.s14` 的寶物段（劇本 1 在 0x69791，各檔逐件比對名稱確認位置），劇本號是檔號（同 `scenarios.csv`），未登場、未発見的不出 | price |
