# Backlog

想到但還沒要做的事。隨手記，不排優先序；要動工時再評估。
格式：`- [ ] 標題 — 一句說明（日期）`（完成就打勾或刪除）。

## 源平合戰舊程式

- [ ] 處理 `dekoei/genpei.py` 的舊色表 — `genpei_face_colors` 等是從截圖量的，和 `Mainpal.pld` 4-bit × 0x11 換算的色值不同；色 8–15 的幾張表也和 Mainpal 不符。新匯出以 `load_mainpal` 為準，舊表要修正或移除（2026-10-10）
- [ ] 修正 `genpei montage` 的位元順序 — 它走 `utils.to_3bpp_indexes`，把第一個 byte 當 bit 2，源平是 byte k = bit k，輸出的顏色會錯（藍綠、膚色黃對調）。新函式 `decode_planar` 是對的（2026-10-10）
- [ ] 修正或移除 `genpei face` — 從未解包的 Main.exe 0x4D51F 讀大小表，呼叫 `unpack_npk_3bits` 少一個參數，實際跑不起來；也沒處理 Kaodata 的 mask 與 trailer。新的 `load_kaodata` 已涵蓋（2026-10-10）

## 環境

- [ ] 更新 `requirements.txt` 的 bitarray — 鎖定的 2.7.3 沒有 Python 3.12 wheel，本機編譯失敗，目前 `.venv` 只能用 3.11（2026-10-10）

## 待分析遊戲（`games/` 新增的 killpeople 壓縮檔）

- [x] 三國志IV 威力加強版 DOS 中文版（`6.10_三國志四加強版_killpeople.rar`）— 已解到 `games/san4pk-dos/`，有 KAODATAP／KAODATA2／NBDATA.SUI；比對 `san4pk-pc98` 後做 `san4pk-dos` 匯出（2026-10-14）
- [ ] 三國志VI 威力加強版 Win 中文版（`5.31_三國志六加強版_killpeople.rar`）— 舊 `sango.san6_face` 有頭像解碼，尚未做 kaodata 匯出（2026-10-14）
- [ ] 三國志孔明傳 Win 中文版（`5.31_三國志孔明傳_killpeople.rar`）— 附 `CRACK.TXT`，主程式 `EKD2.EXE`（2026-10-14）
- [ ] 三國志曹操傳 Win 中文版（`6.3_三國志曹操傳_killpeople.rar`）— 包內是安裝程式 `edk5.exe`（2026-10-14）
- [ ] 英傑傳 織田信長傳 Win 中文版（`6.7_英傑傳四織田信長傳_killpeople.rar`）— 資料檔 `*.E4`（2026-10-14）
- [ ] 信長之野望 將星錄 Win 中文版（`5.31_信長之野望七_killpeople.rar`）（2026-10-14）
- [ ] 成吉思汗 蒼狼與白鹿IV Win 中文版（`6.3_成吉思汗四_killpeople.rar`）（2026-10-14）
- [ ] 大航海時代外傳 Win 中文版（`5.31_大航海時代外傳_killpeople.rar`）（2026-10-14）
- [ ] 取得三國志英傑傳（第一代）PC 原版 — 這批新檔裡仍然沒有，目前只有 SFC 版（2026-10-14）
