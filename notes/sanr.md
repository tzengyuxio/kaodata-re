# 三國志風雲再起（SANR, Win 中文版）圖片格式

`dekoei.py sanr-extras --game-dir ../games/sanr-win --out ../games/sanr-win/extract` 用到的格式。來源是 `~/game-library/_original/win/6.3_三國志風雲再起_killpeople.rar`（`_original/win/sanr-win.txt`），解開放在 `games/sanr-win/`。主程式 `SAN1.EXE`。2026-11-15 第一輪只解圖，人物、城、劇本還沒看。

## 圖檔（*.SA1）

- 一個檔是一串圖，每張是 `2a 38`、u16 寬、u16 高，接著寬×高 bytes 的 8bpp 色號，沒有其他檔頭。
- LS11 壓縮的檔（`KAO`、`MAINMAP`、`HEXMAP`、`HEXANI`、`ANIME`）每段最多 32768 bytes，大圖會跨段，要把各段接起來再切圖。未壓縮的檔（`MAP`、`TITLE`、`MAINGRP` 等）直接切。14 個圖檔切完都剛好用完，沒有剩餘 bytes。
- 色盤是 `MAINPAL.SA1`（768 bytes）：
  - 每色 3 bytes，順序是 B、R、G。
  - 圖的色號 i 對應 MAINPAL 第 i−10 色（Windows 把 0–9 留給系統色）。
  - 頭像用到的色號是 10–243。
- `ENDPAL.SA1` 是另一組 768 bytes 的色盤，推定給結尾用【推】；`TITLE.SA1` 7 張裡可能有用它的，目前全部用 MAINPAL 輸出。

## 輸出

| 資料夾 | 檔 | 張數 | 內容 |
|---|---|---:|---|
| `kao/` | `KAO.SA1` | 260 | 頭像 96×128，背景畫在圖裡（沒有透明色） |
| `map/` | `MAP.SA1` | 1 | 272×352 戰略地圖，標 1–58 城號 |
| `mainmap/` | `MAINMAP.SA1` | 178 | 0–57 是 72×84 小圖（內容沒看）；174 各城範圍、175 州（涼州、益州等）兩張 272×352 地圖；177 是 640×420 龍紋背景 |
| `hexmap/` | `HEXMAP.SA1` | 58 | 540×384 斜視角戰場圖，張數同城數，推定一城一張【推】 |
| 其他 | `HEXANI`、`ANIME`、`TITLE`、`MAINGRP`、`COM_HEX`、`HATA_HEX`、`SONOHEX`、`SONO2HEX`、`KOEILOGO`、`C1995` | | 戰場動畫、標題、介面零件等，沒有逐一辨認 |

## 進度

| 項目 | 狀態 | 證據 | 說明 |
|------|------|------|------|
| 圖檔格式 | ✅ | code | 14 個檔切完剛好用完 |
| 色盤 | 🟡 | | B、R、G 順序與 −10 位移是看頭像和標題圖試出來的，沒有讀程式、沒有截圖 |
| 頭像 260 張 | 🟡 | | 解出來的顏色自然，沒有和遊戲畫面比對 |
| 戰略地圖、戰場圖 | 🟡 | | 圖正確；戰場圖和城的對應未確認 |

## 未解

- 頭像對應的人物：人物資料推定在 `SANR*.KOS`／`SANR*.KOB` 或 `SAVEDATA.SA1`，還沒看。
- 戰場圖與城的對應、`MAINMAP` 0–57 的小圖是什麼。
- `ENDPAL.SA1` 用在哪些圖。

## 下一輪候選

- 人物、城、劇本 — 前置：無；做法：先看 `SAVEDATA.SA1`（有 Big5 名字）與 `SANR*.KOS` 的結構，再做 kaodata 資料集。

## 負面結論

- 用平滑度（相鄰像素色差）在所有檔裡掃描色盤：找不到，因為頭像是抖色（dither）的，正確色盤的分數不比隨機位置低；改成直接試 MAINPAL 的位移與通道順序才找到。
