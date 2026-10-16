# 太閤立志傳IV（TAIKOH4, Windows 中文版）頭像相關格式（未完成）

來源是 `games/archives/win/taiko4.rar`：裡面是 CloneCD 映像（`TAIKOU4.img`，2352 bytes 一個 Mode 1 磁區）。去掉磁區頭轉成 ISO 後，檔案解在 `games/archives/win/taikoh4-src/iso/`。

- 有 `00000404`（繁中）語系檔，訊息是 Big5，所以是繁中版。
- 光碟根目錄的 `TAIKOU4.EXE` 是 SafeDisc 外殼（有 `stxt` 區段）。`GAME/TAIKOU4.EXE` 是沒加殼的本體。
- 檔名以 `_` 結尾的檔案（`*.TR_`、`*.TG_`）是 SZDD（MS `COMPRESS.EXE`），安裝時才展開。

## 圖檔：*.TG4

- `TK4G` 檔頭：
  - +4 u16 旗標，+6 u16 種類。
  - +8 u32 張數。
  - +0x10 起是 256 bytes 的 LS11 字典。
- 0x110 起是每張 24 bytes 的索引：u32 寬、高、展開大小、壓縮大小、位置、0x32。
- 每張是 LS11 位元流（`ls11.get_codes`＋`ls11.recover`，用檔頭的字典）。展開後依序是：
  - 寬×高的色號。
  - 256 色 RGB555 色盤（512 bytes）。色號 0 是純綠，當透明色。
- 頭像檔：
  - `BUSTUP0.TG4`：677 張 304×300 半身像。`BUSTUP1.TG4`：62 張，第 0 張是 8×8 的空白，其餘 61 張接在後面。
  - `FACE0.TG4`／`FACE1.TG4`：同數量的 56×56 小臉，部分項目用上面的解法會失敗，沒有追。
  - 依「不小於 64×80、最接近」的規則應收 BUSTUP。
- `PLNAME.TG4` 是 312 張 132×26 的人名圖（點陣化的名字）。

## 人物：GAME/SNR/SNR1–3.TR_（卡住）

- SZDD 展開後是 `TR4SCENARIO0000n` 加上加密的資料。
- 用 `GAME/TAIKOU4.EXE` 檔案 0x1F8920 的 256 bytes 代換表反查，可以解出前 0x2A bytes（`TAI4SNR001`、`TAI4TAI4SCENARIO1`）。
- 後面看起來是「代換之後再 XOR 0x5A」，但解出來的內容仍然不成結構，也找不到人名。
- 讀劇本的程式碼（EXE 0x581500，經 0x581370 驗證檔頭）會呼叫物件 0x655B60 的函式。這組函式會讀登錄檔、磁碟序號，屬於安裝綁定的保護機制。
- 訊息檔 `MSG/TR4MSG??.TR_`（u16 筆數＋u32 位置表，Big5）裡有人名，但沒有人物表。
- 人名與「人物 → 頭像」的對照還沒找到，所以沒有做資料集。
