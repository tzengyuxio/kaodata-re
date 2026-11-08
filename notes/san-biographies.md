# 三國志 武將列傳

各代列傳的位置、編碼與人數。格式細節在各遊戲筆記的「列傳」段，這裡只做總表。

## 已匯出（繁中，給 koei-wiki）

`dekoei.py biography <dataset>`（`dekoei/biography.py`）寫到 `export/koei-wiki/<dataset>.jsonl`，一段一行：`{"dataset", "id", "name", "lang": "zh-Hant", "kind", "text"}`。`export/` 不進版控。

- `id` 是 kaodata 資料集的人物 id。5 份的 id 與姓名都和 `~/works/kaodata/data-local/<dataset>/dataset.json` 逐一對過，全部相同（✅ cross）。
- `kind`：簡介（列傳開頭一行）、演義、史實、單段（沒有分段的列傳）。
- 只寫「無記述」的段不輸出；「無記述。」後面還有說明的照留。
- 2026-11-02 匯出。

| 資料集 | 檔案 | 編碼 | 分段 | 有列傳的人數 | 段數 | 筆記 |
|---|---|---|---|--:|---|---|
| `san4pk-dos` | `MESSAGE.S4` 第 24–33 段（LS11） | 光榮台灣內碼 | 單段 | 454 | 單段 454 | `notes/san4.md` |
| `san5pk-dos` | `MESSAGE.S5` 第 1–10 段（LS11） | 光榮台灣內碼 | 單段 | 500 | 單段 500 | `notes/san5.md` |
| `san6pk-win` | `MESSAGE.S6` 第 1–6 段（LS11） | Big5 | 單段 | 520 | 單段 520 | `notes/san6.md` |
| `san13pk-win` | `pk/DATA1.S13` 第 1416 項（`zp1`、`XL` 字串表） | Big5＋外字 | 簡介／演義／史實（古武將單段） | 821 | 簡介 807、演義 708、史實 749、單段 14 | `notes/san13.md` |
| `san14pk-win` | `0001_TC/msgdata.bin`（`zp1`、`XL` 字串表） | UTF-16LE＋外字 | 簡介／演義／史實（英布單段） | 1001 | 簡介 1000、演義 775、史實 940、單段 1 | `notes/san14.md` |

- 沒有列傳的人：
  - `san4pk-dos`：南蠻王等 4 王、4 族、水滸傳 117 人。
  - `san6pk-win`：外族 12 人。
  - `san13pk-win`：kaodata 的 828 人中有 7 人沒有列傳。
- 光榮台灣內碼和名字同一套（`utils.to_unicode_name`）：
  - 漢字在 hi 0x92–0xD8。
  - 標點在 hi 0x81–0x91，對到 CNS 1-2121 起。
  - 三國志IV 的句號都寫成「．」，匯出成「。」。【推】
- 外字是照上下文判定的，沒有讀字型。🟡
  - 三國志13：坂、𩅦、伷、璝、儁。
  - 三國志14：伷、璝、儁、喁、崖、坂，以及衜／𩅦（兩字共用一碼）。

## 沒有匯出

| 代 | 版本 | 狀況 |
|---|---|---|
| 三國志X | Steam 日文 | `msg/S10M13PK.s10`（LS11），人物記錄 +20 是列傳號。🟡 沒輸出 |
| 三國志12 | Steam 日文 | `PK/Msg/S12MSG03.s12`，1089 則，順序同人物號。🟡 沒輸出 |
| 三國志13、14 | 日文 | 和繁中同一處（三國志13 的第 2 項；三國志14 的 `0001_JP`），沒輸出 |
| 三國志VII | Steam 日文 | `M_BFile.s7` part 1–11，520 人，第 k 筆是武將 k（`san7-extras` 的 `text/biographies.csv`）。✅ cross，還沒接 `biography.py` |
| 三國志VIII | Steam 日文 | `m_msg.s8` 51–54 項，654 則，編號＝頭像號（`san8-extras` 的 `text/biographies.csv`）。✅ cross，還沒接 `biography.py` |
| 三國志IX | Steam 日文 | `M_Rtdn.s9` 679 則（`san9-extras` 的 `text/biographies.csv`）；照頭像號對人，0–500 抽查都對，600 以後錯開（第 647 則是楊肇，頭像 647 是楊済）。🟡 沒匯出 |
| 三國志11 | Steam 日文 | `media/msg/S11MSG02.s11`，821 人 2195 段（簡介／演義／史實），`san11-extras` 的 `text/biographies.csv`。✅ cross，還沒接 `biography.py` |
| 三國志IV、V | PC-98 日文 | 遊戲有列伝畫面，沒找過檔案 |
| 三國志I–III | — | 筆記裡沒有列傳 |
