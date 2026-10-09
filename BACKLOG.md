# Backlog

想到但還沒要做的事。隨手記，不排優先序；要動工時再評估。
格式：`- [ ] 標題 — 一句說明（日期）`（完成就打勾或刪除）。

## 源平合戰舊程式

- [ ] 處理 `dekoei/genpei.py` 的舊色表 — `genpei_face_colors` 等是從截圖量的，和 `Mainpal.pld` 4-bit × 0x11 換算的色值不同；色 8–15 的幾張表也和 Mainpal 不符。新匯出以 `load_mainpal` 為準，舊表要修正或移除（2026-10-10）
- [ ] 修正 `genpei montage` 的位元順序 — 它走 `utils.to_3bpp_indexes`，把第一個 byte 當 bit 2，源平是 byte k = bit k，輸出的顏色會錯（藍綠、膚色黃對調）。新函式 `decode_planar` 是對的（2026-10-10）
- [ ] 修正或移除 `genpei face` — 從未解包的 Main.exe 0x4D51F 讀大小表，呼叫 `unpack_npk_3bits` 少一個參數，實際跑不起來；也沒處理 Kaodata 的 mask 與 trailer。新的 `load_kaodata` 已涵蓋（2026-10-10）

## 環境

- [ ] 更新 `requirements.txt` 的 bitarray — 鎖定的 2.7.3 沒有 Python 3.12 wheel，本機編譯失敗，目前 `.venv` 只能用 3.11（2026-10-10）
