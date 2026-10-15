# Backlog

想到但還沒要做的事。隨手記，不排優先序；要動工時再評估。
格式：`- [ ] 標題 — 一句說明（日期）`（完成就打勾或刪除）。

## 源平合戰舊程式

- [ ] 處理 `dekoei/genpei.py` 的舊色表 — `genpei_face_colors` 等是從截圖量的，和 `Mainpal.pld` 4-bit × 0x11 換算的色值不同；色 8–15 的幾張表也和 Mainpal 不符。新匯出以 `load_mainpal` 為準，舊表要修正或移除（2026-10-10）
- [ ] 修正 `genpei montage` 的位元順序 — 它走 `utils.to_3bpp_indexes`，把第一個 byte 當 bit 2，源平是 byte k = bit k，輸出的顏色會錯（藍綠、膚色黃對調）。新函式 `decode_planar` 是對的（2026-10-10）
- [ ] 修正或移除 `genpei face` — 從未解包的 Main.exe 0x4D51F 讀大小表，呼叫 `unpack_npk_3bits` 少一個參數，實際跑不起來；也沒處理 Kaodata 的 mask 與 trailer。新的 `load_kaodata` 已涵蓋（2026-10-10）

## 環境

- [ ] 更新 `requirements.txt` 的 bitarray — 鎖定的 2.7.3 沒有 Python 3.12 wheel，本機編譯失敗，目前 `.venv` 只能用 3.11（2026-10-10）

## 待分析遊戲（新增的 killpeople 壓縮檔，現在在 `games/archives/dos/`、`win/`）

- [x] 三國志IV 威力加強版 DOS 中文版（`6.10_三國志四加強版_killpeople.rar`）— 已解到 `games/san4pk-dos/`，有 KAODATAP／KAODATA2／NBDATA.SUI；比對 `san4pk-pc98` 後做 `san4pk-dos` 匯出（2026-10-14）
- [x] 三國志VI 威力加強版 Win 中文版（`5.31_三國志六加強版_killpeople.rar`）— 舊 `sango.san6_face` 有頭像解碼，尚未做 kaodata 匯出（2026-10-14）
- [x] 三國志孔明傳 Win 中文版（`5.31_三國志孔明傳_killpeople.rar`）— 附 `CRACK.TXT`，主程式 `EKD2.EXE`（2026-10-14）
- [x] 三國志曹操傳 Win 中文版（`6.3_三國志曹操傳_killpeople.rar`）— 安裝程式 `edk5.exe` 用 7z 解到 `games/eiketsu5-win/`，做 `eiketsu5-win` 匯出（2026-10-15）
- [x] 英傑傳 織田信長傳 Win 中文版（`6.7_英傑傳四織田信長傳_killpeople.rar`）— 解到 `games/eiketsu4-win/`，做 `eiketsu4-win` 匯出（2026-10-15）
- [x] 信長之野望 將星錄 Win 中文版（`5.31_信長之野望七_killpeople.rar`）— 解到 `games/nobu7-win/`（不含動畫），做 `nobu7-win` 匯出（2026-10-14）
- [ ] 成吉思汗 蒼狼與白鹿IV Win 中文版（`6.3_成吉思汗四_killpeople.rar`）— 無印版，頭像是 PK 版的前段（見 `notes/genghis4.md`），要不要另做 `genghis4-win` 再評估（2026-10-14）
- [x] 大航海時代外傳 Win 中文版（`5.31_大航海時代外傳_killpeople.rar`）— 解到 `games/koukaigd-win/`，做 `koukaigd-win` 匯出（2026-10-14）
- [x] 三國志英傑傳 DOS 中文版（`6.10_三國志英傑傳_killpeople.rar`）— 解到 `games/eiketsu-dos/`，做 `eiketsu-dos` 匯出（2026-10-14）

## 待分析遊戲（`games/archives/win/` 新增的檔案）

- [x] 大航海時代III Win 中文版（`大航海時代_III (中文).zip`）— 解到 `games/koukai3-win/`（不含 AVI），做 `koukai3-win` 匯出（2026-10-14）
- [x] 成吉思汗 蒼狼與白鹿IV 威力加強版（`成吉思汗 IV-威力加強版/`）— 複製到 `games/genghis4pk-win/`，做 `genghis4pk-win` 匯出（2026-10-15）
- [ ] 英傑傳系列（`[系列] 英傑傳/`）— 毛利元就傳中文版已做 `eiketsu3-win`（2026-10-15）；三國志英傑傳 威力加強版是 2012 年的同人改版（只改 MAIN.EXE／BAKDATA／SNR*D，FACEDAT 和 `eiketsu-dos` 相同），不另做；剩 Win31 版（`reko_win` 的 `R3WIN/`，FACEDAT.R3 和 DOS 版不同，可做 `eiketsu-win`），以及織田信長傳／毛利元就傳日文版（2026-10-14）
- [ ] 太閤立志傳系列（`[系列] 太閣立志傳 (pw 可能也是 Old-Games）/`）— 1 代 DOS 中文版已做 `taikoh-dos`、2 代 Win 中文版已做 `taikoh2-win`（2026-10-15）；剩 3–5 代、SEGA MD 版（2026-10-14）
- [ ] 維新之嵐 PC 版（`維新之嵐[PC版].rar`）（2026-10-14）
- [ ] 維新之嵐2（`ISHIN2.mdx`，538 MB 光碟映像）（2026-10-14）
- [ ] 太閤立志傳IV（`taiko4.rar`）（2026-10-14）

## 待分析遊戲（`games/archives/dos/` 的其他檔案）

- [ ] 信長之野望 英文版（`信長之野望_英文版_nobunagas-ambition.zip`）— 1988 年的 Nobunaga's Ambition（`1ODA_B/PICDATA.DAT` 等），應是全國版（NOBU2）的移植，目前沒有這一代的資料集（2026-10-15）

## 待分析遊戲（`games/archives/pc98/` 新增的 `[PC98]` 壓縮檔）

- [x] 源平合戦（`[PC98] 源平合戦.zip`，5 片 FDI）— 解到 `games/genpei-pc98/`，用 `build_genpei(pc98=True)` 做 `genpei-pc98` 匯出（2026-10-15）
- [x] 三国志・英傑伝（`[PC98] 三国志・英傑伝.zip`）— 解到 `games/eiketsu-pc98/`，用 `build_eiketsu_dos(pc98=True)` 做 `eiketsu-pc98` 匯出（2026-10-15）
- [x] 信長の野望・戦国群雄伝（`[PC98] 信長の野望・戦国群雄伝.zip`）— 解到 `games/nobu3-pc98/`，做 `nobu3-pc98` 匯出（2026-10-15）
- [x] 信長の野望・武将風雲録（`[PC98] 信長の野望・風雲録.zip`）— 解到 `games/nobu4-pc98/`，用 `build_nobu4_dos(pc98=True)` 做 `nobu4-pc98` 匯出（2026-10-15）
- [x] 信長の野望・覇王伝（`[PC98] 信長の野望・覇王伝o.zip`）— 解到 `games/nobu5-pc98/`，做 `nobu5-pc98` 匯出（2026-10-15）
- [x] 信長の野望・天翔記（`[PC98] 信長の野望・天翔記.zip`）— 解到 `games/nobu6-pc98/`，做 `nobu6-pc98` 匯出（2026-10-15）
- [x] 水滸伝～天命の誓い～（`[PC98] 水滸伝～天命の誓い～.ZIP`）— 第 2 片和既有 `suikoden-pc98` 相同，第 1 片的 MAIN.EXE 證實數位色盤，資料集不變（2026-10-15）
- [x] 独立戦争（`[PC98] 独立戦争.zip`，3 片 D88）— 解到 `games/liberty-pc98/`，用 `build_liberty_dos(pc98=True)` 做 `liberty-pc98` 匯出（2026-10-15）
- [x] 大航海時代（`[PC98] 大航海時代.zip`）— 解到 `games/koukai-pc98/`，用 `build_koukai_dos(pc98=True)` 做 `koukai-pc98` 匯出（2026-10-15）
- [ ] 大航海時代II（`[PC98] 大航海時代２.zip`）（2026-10-14）
- [x] 維新の嵐（`[PC98] 維新の嵐.zip`）— B 片補齊，做 `ishin-pc98` 匯出（2026-10-15）
- [x] ロイヤルブラッド（`[PC98] [光栄] ロイヤルブラッド(FDI).zip`）— A 片補齊，做 `royal-pc98` 匯出（2026-10-15）
- [x] プロジェネター（`[PC98] [光栄] プロジェネター（FDI).zip`）— 解到 `games/progen-pc98/`，做 `progen-pc98` 匯出（2026-10-15）
- [x] 太閤立志伝（`[PC98] 太閤立志伝.zip`）— 解到 `games/taikoh-pc98/`，用 `build_taikoh_dos(pc98=True)` 做 `taikoh-pc98` 匯出（2026-10-15）
- [x] 太閤立志伝II（`[PC98] 太閤立志伝２.zip`、`[PC98] 太閤立志伝2(hdi+fdi)(anex動確).zip`，兩份的遊戲檔相同）— `taikoh2-pc98`（2026-10-15）
- [x] 提督の決断（`[PC98] 提督の決断.zip`）— 解到 `games/tk-pc98/`，做 `tk-pc98` 匯出（2026-10-15）
- [x] 提督の決断II（`[PC98] 提督の決断２.zip`，7 片 FDI）— 解到 `games/tk2-pc98/`，做 `tk2-pc98` 匯出（2026-10-15）
- [x] 提督の決断III（`[PC98] 提督の決断３.zip`，7 片 FDI）— DPACK 用 `dekoei/dpack.py` 解到 `games/tk3-pc98/`，做 `tk3-pc98` 匯出（2026-10-15）
- [x] 提督の決断II パワーアップキット（`[PC98] 提督の決断２　ﾊﾟﾜｰｱｯﾌﾟｷｯﾄ.zip`）— PACK.LZW（LW11）解開，本體＋PACK.LZW 放 `games/tk2pk-pc98/`，做 `tk2pk-pc98` 匯出（2026-10-15）
- [x] 提督の決断III パワーアップキット（`[PC98] 提督の決断３　パワーアップキット.zip`）— DPACK1–3.T3P 解開疊在本體上放 `games/tk3pk-pc98/`，做 `tk3pk-pc98` 匯出（2026-10-15）
