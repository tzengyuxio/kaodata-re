---
status: todo
created: 2026-11-10
---
# 三國志 VII–12 繁中列傳

## 現況

- Steam 的三國志 VII–12 with 威力加強版各有一個 `tchinese` depot，是完整的繁中版遊戲（2026-11-10 用 `app_info_print` 查到；`baselanguages` 是 `tchinese,japanese`）。目前只下載過日文 depot（`notes/steam.md`）。
- `notes/san-biographies.md` 與 `biography.py` 寫「三國志IX 沒有中文版」是錯的，`export/koei-wiki/san9pk-win.jsonl` 現在是日文。

| 遊戲 | appid | 繁中 depot | manifest | 安裝大小 | 下載量 |
|---|--:|--:|---|--:|--:|
| VII | 628030 | 628032 | 4248938368459573586 | 676 MB | 480 MB |
| VIII | 628040 | 628042 | 4089676707756992132 | 776 MB | 449 MB |
| IX | 628050 | 628052 | 4620203723096695661 | 1.36 GB | 946 MB |
| X | 628060 | 628062 | 2296353219613693479 | 1.02 GB | 683 MB |
| 11 | 628070 | 628072 | 3611590611992064954 | 2.09 GB | 1.38 GB |
| 12 | 628080 | 628082 | 1876821799476983415 | 11.5 GB | 3.84 GB |

## 下一步

1. 使用者在自己的終端機跑 `steamcmd +login yuxioz +quit` 更新登入快取（2026-11-10 快取已過期，`Cached credentials not found`）。
2. `steamcmd +@sSteamCmdForcePlatformType windows +login yuxioz +download_depot <appid> <depot> +quit`（沙箱外執行），記進 `notes/steam.md`。
3. 找各代繁中列傳的檔案（日文版的位置見 `notes/san-biographies.md`「沒有匯出」），接上 `biography.py`，`lang` 用 `zh-Hant`。
4. 三國志IX 改用繁中重新匯出，修正筆記、`biography.py` 註解與 CLAUDE.md 的「沒有繁中版的三國志IX」，通知 koei-wiki。

## 負面結論

目前沒有。

## 未收尾

- 等使用者登入 Steam。
