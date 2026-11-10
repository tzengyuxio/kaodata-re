# 寶物匯出（koei-wiki，koei-items/1）

`dekoei.py items-export <dataset> --extract ../games/<id>/extract --game-dir ../games/<id> --out ../export/koei-wiki/items`（`dekoei/items_export.py`）寫 `export/koei-wiki/items/<dataset>.jsonl`，一格寶物一行。規格在 koei-wiki `docs/items-format.mkdn`。大部分欄位讀各遊戲 `*-extras` 輸出的 `extract/items/*.csv`，所以要先跑該遊戲的 extras；信長6、11 的 CSV 只留持有者的名字，持有者 id 要重讀劇本檔。

- `holders` 的 `person` 是 kaodata 資料集的人物 id。匯出時逐一檢查它在 kaodata `dataset.json` 的 characters 或 koei-wiki 人物匯出裡，不在就停止匯出。
- 持有者名字和人物名字不同的，都是同一人的別名（大友義鎮／大友宗麟、松平元康／徳川家康、木下秀吉／豊臣秀吉…），照 id 對 ✅ cross。
- 第一輪不出效果數值（信長6 的單一能力加成例外，CSV 裡就有）、圖、三國志VII–12 的繁中名稱。

## 第 1 批（2026-11-11）

| 資料集 | 件數 | 有持有者的件數（筆數） | 說明文 | 讀哪裡 | 標 `uncertain` |
|---|--:|--:|---|---|---|
| `san4pk-pc98` | 31 | 19（129） | 日文、中文（DOS 中文版） | `items.csv`、`holders.csv`（已有 kaodata id） | kind |
| `san7pk-win` | 72 | 46（428） | 日文 | 同上；持有者欄就是 kaodata id，12 個劇本照檔名排號 | kind、price |
| `san9pk-win` | 100 | 100（658） | 日文 | 只出人物持有者（狀態 2）；放在都市的只有都市號，沒有名字，沒出 | kind、price、holders |
| `san10pk-win` | 200 | 181（3188） | 日文 | 人物或所在都市（`other`）；人物槽 763 以後不在 kaodata，寫在 `notes` | — |
| `san11pk-win` | 43 | 43（592） | 沒有 | 人物或所在地（`other`）；7 個「アイテム」空槽不出 | kind、price、holders |
| `nobu6pk-pc98` | 120 | 57（152） | 日文 | 持有者是各劇本名字記錄的槽號（從 1 起），槽的頭像號換成 id（同 `wiki_nobu6`）；`effects` 是 CSV 的加成能力與數值 | — |
| `nobu7pk-win` | 200 | 78（387） | 日文 | 持有者 n（從 1 起）是 id n－1；種類只有數字，沒出 | grade |
| `nobu8pk-win` | 350 | 111（614） | 沒有 | 持有者 n 就是 id n；`price` 取劇本 10 的值 | grade、price |
| `nobu9pk-win` | 380 | 198（1885） | 沒有 | 人物用 id，都市用名字（`other`）；`pk` 是 PK 的 30 件 | grade |
| `nobu10pk-win` | 460 | 83（510） | 日文 | `holders.csv` 的持有者就是 id | — |
| `nobu11pk-win` | 430 | 145（664） | 日文 | 持有者連號：武將槽（`wiki_nobu11.OFFICERS`）是 id，勢力寫成「當主名勢力」（`other`）；劇本號是 DBSCEDA 的號碼 | kind（圖的種類） |
| `nobu12pk-win` | 355 | 109（596） | 日文 | `owners` 的名字對人物匯出的名字，每個名字都只對到一人 | grade |
