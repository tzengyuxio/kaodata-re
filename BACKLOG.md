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
- [x] 三國志VI 威力加強版 Win 中文版（`5.31_三國志六加強版_killpeople.rar`）— 舊 `sango.san6_face` 有頭像解碼，尚未做 kaodata 匯出（2026-10-14）
- [x] 三國志孔明傳 Win 中文版（`5.31_三國志孔明傳_killpeople.rar`）— 附 `CRACK.TXT`，主程式 `EKD2.EXE`（2026-10-14）
- [x] 三國志曹操傳 Win 中文版（`6.3_三國志曹操傳_killpeople.rar`）— 安裝程式 `edk5.exe` 用 7z 解到 `games/eiketsu5-win/`，做 `eiketsu5-win` 匯出（2026-10-15）
- [x] 英傑傳 織田信長傳 Win 中文版（`6.7_英傑傳四織田信長傳_killpeople.rar`）— 解到 `games/eiketsu4-win/`，做 `eiketsu4-win` 匯出（2026-10-15）
- [x] 信長之野望 將星錄 Win 中文版（`5.31_信長之野望七_killpeople.rar`）— 解到 `games/nobu7-win/`（不含動畫），做 `nobu7-win` 匯出（2026-10-14）
- [ ] 成吉思汗 蒼狼與白鹿IV Win 中文版（`6.3_成吉思汗四_killpeople.rar`）— 無印版，頭像是 PK 版的前段（見 `notes/genghis4.md`），要不要另做 `genghis4-win` 再評估（2026-10-14）
- [x] 大航海時代外傳 Win 中文版（`5.31_大航海時代外傳_killpeople.rar`）— 解到 `games/koukaigd-win/`，做 `koukaigd-win` 匯出（2026-10-14）
- [x] 三國志英傑傳 DOS 中文版（`6.10_三國志英傑傳_killpeople.rar`）— 解到 `games/eiketsu-dos/`，做 `eiketsu-dos` 匯出（2026-10-14）

## 待分析遊戲（`games/win/` 新增的檔案）

- [x] 大航海時代III Win 中文版（`大航海時代_III (中文).zip`）— 解到 `games/koukai3-win/`（不含 AVI），做 `koukai3-win` 匯出（2026-10-14）
- [x] 成吉思汗 蒼狼與白鹿IV 威力加強版（`成吉思汗 IV-威力加強版/`）— 複製到 `games/genghis4pk-win/`，做 `genghis4pk-win` 匯出（2026-10-15）
- [ ] 英傑傳系列（`[系列] 英傑傳/`）（2026-10-14）
- [ ] 太閤立志傳系列（`[系列] 太閣立志傳 (pw 可能也是 Old-Games）/`）（2026-10-14）
- [ ] 維新之嵐 PC 版（`維新之嵐[PC版].rar`）（2026-10-14）
- [ ] 維新之嵐2（`ISHIN2.mdx`，538 MB 光碟映像）（2026-10-14）
- [ ] 太閤立志傳IV（`taiko4.rar`）（2026-10-14）

## 待分析遊戲（`games/pc98/` 新增的 `[PC98]` 壓縮檔）

- [ ] 三国志・英傑伝（`[PC98] 三国志・英傑伝.zip`）— 可和 `eiketsu-dos` 對照（2026-10-14）
- [ ] 信長の野望・戦国群雄伝（`[PC98] 信長の野望・戦国群雄伝.zip`）— 可和 `nobu3-dos` 對照（2026-10-14）
- [ ] 信長の野望・武将風雲録（`[PC98] 信長の野望・風雲録.zip`）— 可和 `nobu4-dos` 對照（2026-10-14）
- [ ] 信長の野望・覇王伝（`[PC98] 信長の野望・覇王伝o.zip`）（2026-10-14）
- [ ] 信長の野望・天翔記（`[PC98] 信長の野望・天翔記.zip`）（2026-10-14）
- [ ] 水滸伝～天命の誓い～（`[PC98] 水滸伝～天命の誓い～.ZIP`）— 和既有 `suikoden-pc98` 比對是否同版（2026-10-14）
- [ ] 独立戦争（`[PC98] 独立戦争.zip`）— 可和 `liberty-dos` 對照（2026-10-14）
- [ ] 大航海時代（`[PC98] 大航海時代.zip`）— 可和 `koukai-dos` 對照（2026-10-14）
- [ ] 大航海時代II（`[PC98] 大航海時代２.zip`）（2026-10-14）
- [ ] 維新の嵐（`[PC98] 維新の嵐.zip`）— 之前 `ishin-pc98` 卡住，看這份是否完整（2026-10-14）
- [ ] ロイヤルブラッド（`[PC98] [光栄] ロイヤルブラッド(FDI).zip`）— 之前 `royal-pc98` 卡住（2026-10-14）
- [ ] プロジェネター（`[PC98] [光栄] プロジェネター（FDI).zip`）（2026-10-14）
- [ ] 太閤立志伝（`[PC98] 太閤立志伝.zip`）（2026-10-14）
- [ ] 太閤立志伝II（`[PC98] 太閤立志伝２.zip`、`[PC98] 太閤立志伝2(hdi+fdi)(anex動確).zip`，兩份）（2026-10-14）
- [ ] 提督の決断（`[PC98] 提督の決断.zip`）（2026-10-14）
- [ ] 提督の決断II パワーアップキット（`[PC98] 提督の決断２　ﾊﾟﾜｰｱｯﾌﾟｷｯﾄ.zip`）（2026-10-14）
- [ ] 提督の決断III パワーアップキット（`[PC98] 提督の決断３　パワーアップキット.zip`）（2026-10-14）
