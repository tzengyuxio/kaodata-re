# Backlog

想到但還沒要做的事。隨手記，不排優先序；要動工時再評估。
格式：`- [ ] 標題 — 一句說明（日期）`（完成就打勾或刪除）。

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
- [x] 英傑傳系列（`[系列] 英傑傳/`）— 毛利元就傳中文版已做 `eiketsu3-win`（2026-10-15）；三國志英傑傳 威力加強版是 2012 年的同人改版（只改 MAIN.EXE／BAKDATA／SNR*D，FACEDAT 和 `eiketsu-dos` 相同），不另做；Win31 版和 `eiketsu-pc98` 同圖同色，不另做資料集（2026-10-15，見 `notes/eiketsu.md`）；織田信長傳／毛利元就傳日文版的頭像與頭像色盤和中文版相同，只有人名語言不同，依規則不另收（2026-10-16，見 `notes/eiketsu3.md`、`notes/eiketsu4.md`）（2026-10-14）
- [ ] 太閤立志傳系列（`[系列] 太閣立志傳 (pw 可能也是 Old-Games）/`）— 1 代 DOS 中文版已做 `taikoh-dos`、2 代 Win 中文版已做 `taikoh2-win`（2026-10-15）；3 代 Win 中文版已做 `taikoh3-win`（2026-10-16）；5 代 DX（Steam）已做 `taikoh5dx-win`（2026-10-16）；4 代已做 `taikoh4-win`（2026-10-16）；剩 5 代原版、SEGA MD 版（2026-10-14）
- [x] 維新之嵐 PC 版（`維新之嵐[PC版].rar`）與維新之嵐2（`ISHIN2.mdx`）— 兩者都是日文版 維新の嵐 幕末志士伝，用光碟版做 `ishin2-win` 匯出（2026-10-16，見 `notes/ishin2.md`）
- [x] 太閤立志傳IV（`taiko4.rar`）— 劇本解密找到了（不是安裝綁定，是 EXE 的代換表），已匯出成 `taikoh4-win`，見 `notes/taikoh4.md`（2026-10-16）（2026-10-14）

## 待分析遊戲（`games/archives/dos/` 的其他檔案）


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
- [x] 大航海時代II（`[PC98] 大航海時代２.zip`）— `koukai2-pc98`（2026-10-15）
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

## 待分析遊戲（Internet Archive neo-kobe 的 PC-98 版，`~/game-library/_original/pc98/neo-kobe-2017-11-17/Koei/`）

和已收的其他平台版比對：一模一樣就只加版本標記，不同才做 `<game>-pc98`。

- [x] 蒼き狼と白き牝鹿・元朝秘史（`Genchou Hishi [FD]`）— 頭像、人物同 X68，色盤不同，做 `genchou-pc98`（2026-10-16）
- [x] 元朝秘史 DOS 中文版（`元朝秘史_killpeople.rar`）— 檔案同 PC-98、人名中文，做 `genchou-dos`；日文版元朝秘史、成吉思汗依 id 補 `nameZh`（2026-10-17）
- [x] ジンギスカン（`Genghis Khan [FD]`、`[FD][Set 1]`）— 和 `genghis-pc88` 相同；kaodata 改以首發的 PC-98 版為主，做 `genghis-pc98`，PC-88 改成標籤（2026-10-16）
- [x] ヨーロッパ戦線（`Europe Sensen [FD]`）— 色盤是類比色，做 `europe-pc98`（2026-10-16）
- [x] 項劉記（`Kouryuuki [FD]`／`[HD]`）— 頭像、人名同 X68，色盤不同，做 `kouryuuki-pc98`（2026-10-16）
- [x] ランペルール（`L'Empereur [FD]`、`[extras]`）— 和 `lempe-x68` 相同（映像後段損壞，只比對前 92 張），kaodata 加版本標記（2026-10-16）
- [x] エアーマネージメント2（`Air Management 2 [FD]`／`[HD]`）— 頭像同 DOS，色盤換算不同，做 `air2-pc98`（2026-10-16）
- [x] 三國志 復刻版（`Sangokushi Fukkokuban`，1995）— 和 `san1-pc98` 相同，kaodata 加版本標記（2026-10-16）
- [x] トップマネジメントII — 有 132 張 64×64 頭像，做 `topman2-pc98`（2026-10-16）
- [ ] トップマネジメント 産能大編 — 頭像可能在 `.ANM`（64×80、144×160 等），格式還沒解；代號等解開再定（2026-10-16）

## 待分析遊戲（Steam 版，`games/steam/<appid>/`，見 `notes/steam.md`）

- [x] 三國志12 with PK（628080）、三國志13（363150，PK 是 DLC）、三國志14（872410，PK 是 DLC）— 三國志12 PK 匯出成 `san12pk-win`、三國志13 PK 匯出成 `san13pk-win`（2026-10-16 使用者決定收）；三國志14 PK 只分析；頭像尺寸與張數已交 kaodata 記錄；人物與頭像的對應、日文／繁中名已追到（見 `notes/san12.md`–`san14.md`）（2026-10-16）
- [x] 大志（628890）、新生（1336980）— 只分析、先不交 kaodata；收 72×72，尺寸與張數已交 kaodata 記錄；人物、頭像號、日文／繁中名已追到（見 `notes/nobu15.md`、`nobu16.md`）（2026-10-16）
- [ ] 信長の野望・創造 with PK（本體 292990、PK 是 DLC 344120，暫定 `nobu14pk-win`）— 2026-10-17 用了錯的 appid 288390 才回 No subscription；Steam 商店資料兩個都只列繁中，2026-11-11 已下載到 `games/steam/292990-tchinese/depot/`，列伝格式已確認（見 `notes/nobu-attributes.md`「創造」），人物記錄與頭像待分析（2026-11-11）
- [x] 三国志ツクール（397720）— 96×120 全彩，本體 5101＋已裝 DLC 2722 張，匯出成 `santsukuru-win`（WebP），先留 data-local 不上線；之後頭像連同人名要放到 Forgejo 的 koei-images 備查（repo 已存在：https://hikari.tail81eb54.ts.net:8444/tzengyuxio/koei-images ，本地還沒 clone；使用者說先不用做（2026-10-17），圖檔格式與人名附法到時再問；push 前先問使用者）（見 `notes/santsukuru.md`）（天道 PK 已匯出成 `nobu13pk-win`，太閤立志伝V DX 已匯出成 `taikoh5dx-win`，大航海時代IV PK HD 已匯出成 `koukai4pk-win`）（2026-10-16）
- [x] 三國志11 with PK（628070）— 64×80 頭像是全彩，用 kaodata 的 `rgbaBlobs` 匯出成 `san11pk-win`，見 `notes/san11.md`（2026-10-16）

## 戰場地圖

- [x] 三國志 I–V 的戰場地圖 — 能力總覽（`notes/san-attributes.md`）完成後做；正傳每代只挑一個平台（PC-98 或 DOS），不每個平台都做。I 已完成（PC-98，`san1 battlemap`，圖案從截圖切）。II 已完成（PC-98，`san2 battlemap`，排法和色盤還沒和畫面比過）；III 已完成（PC-98，`san3 battlemap`，每張用哪組圖塊是看圖判斷的）；IV 已完成（PC-98，`san4 battlemap`，色盤種類執行時才決定）；V 已完成（PC-98，`san5 battlemap`，戰場色盤沒追到）。FC／SFC 版在別的 repo，已完成的拿來對照：FC 初代 58 張、FC II 41 張（famicom-re）、SFC 初代 58 張、SFC II 41 張、SFC IV 88 張（superfamicom-re）；SFC III 只有格子資料、沒渲染（那邊的事，不在本 repo 改）（2026-10-21）

## 遊戲資料（之後可以提供給 koei.wiki）

- [ ] 三國志各代的城市資料 — 以正傳為主（2026-11-04）
  - I–14 的地名、地點與戰場對照已整理到 `notes/san-maps.md`（2026-11-06）；還沒確認的：V 的讀取程式、VI–VIII 的攻守方向、VIII 戰場名與地點的對應、13 野戰地域碼的地名、11／14 的 EXE 沒解
- [ ] 信長之野望歷代的人物資料 — 基本數值與列傳（2026-11-04）
- [ ] 各個遊戲的大地圖 — 戰場地圖已做的是三國志 I–V，見上一段（2026-11-04）
- [ ] 維新の嵐的人物資料 — PC-98 的能力已能用 `koei-person ishin-pc98` 輸出（2026-11-06）；同志、所在還沒做；kaodata `ishin-pc98` 的人名已改用劇本的名表（2026-11-06）（2026-11-04）
- [ ] 大航海時代系列的人物資料與港口資料（2026-11-04）
- [ ] 各個遊戲的道具圖與道具資料（2026-11-04）
- [ ] 寶物匯出補 `effects`（koei-items/1）— koei-wiki 的寶物條目要加「遊戲中的效果」；已交付的 16 個資料集先做，extract 裡有效果欄的：三國志IV PK、VII、VIII、IX、12、14，信長8、9；排在三國志8–14 刪檔之後（2026-11-11）
- [ ] 三國志各代的大地圖已在 `<game>_extras` 的 `worldmap/`（VIII–14，2026-11-11）
- [ ] 成吉思汗系列的歷史人物資料與各個國家 — 三代的國、相鄰、人物欄位已解（`genghis-extras`、`genchou-extras`、`genghis4-extras`，2026-11-10）；地點已匯出給 koei-wiki（2026-11-10）；成吉思汗IV 的大地圖也已解（2026-11-10）；還沒做：人物匯出（2026-11-04）
- [ ] 遊戲歷史事件資料解析 — 以三國志、信長之野望為主（2026-11-06）

## 待確認（遊戲筆記的 🟡）

從 `notes/` 收集的 🟡（推論、沒驗證的項目）。確認後改筆記的符號，並把這裡打勾（2026-10-22）。

### 人物欄位：名稱或對位沒有截圖、沒追讀取程式

- [ ] 信長の野望・天道 — 欄位順序照革新推的，沒有截圖 — 見 `notes/nobu13.md`（2026-10-22）
- [ ] 信長の野望・蒼天録／天下創世 — 欄位名稱是從 EXE 的欄位名清單推的，沒有截圖 — 見 `notes/nobu10.md`、`notes/nobu11.md`（2026-10-22）
- [ ] 信長の野望・嵐世記 — 前三項顯示成一半，只有一張 web 試玩版截圖，發售版沒確認 — 見 `notes/nobu9.md`（2026-10-22）
- [ ] 信長の野望・天翔記 — 千分比超過 1000 的顯示上限、8 個技能格的位置 — 見 `notes/nobu6.md`（2026-10-22）
- [ ] 信長の野望・覇王伝 — 寿命只確認過 C，気合沒找到，PC-98 +20 不明 — 見 `notes/nobu5.md`（2026-10-22）
- [ ] 信長の野望・戦国群雄伝 — 截圖是重骰後的值，差幾點，要一張沒重骰的 — 見 `notes/nobu3.md`（2026-10-22）
- [ ] 三國志X — web 截圖的對照 — 見 `notes/san10.md`（2026-10-22）
- [ ] 三國志英傑傳 — 19 種兵種名稱照字串順序對應 — 見 `notes/eiketsu.md`（2026-10-22）
- [ ] 三國志孔明傳 — 全部欄位只靠數值對位，+2／+3 哪個是統御力最不確定 — 見 `notes/koumei.md`（2026-10-22）
- [ ] 毛利元就傳 — 技能值、命中率、敏捷只靠順序對位 — 見 `notes/eiketsu3.md`（2026-10-22）
- [ ] 織田信長傳 — 命中力、敏捷只靠順序；得意技／特性的區分只靠內容 — 見 `notes/eiketsu4.md`（2026-10-22）
- [ ] 三國志曹操傳 — 第 2、3 項的名稱（EXE 訊息順序和數值不符）；兵種成長、策略的位置 — 見 `notes/eiketsu5.md`（2026-10-22）
- [ ] ジンギスカン — 子女 +18、+28＝1／2 的名稱（寫入條件已知；升格公式 2026-11-10 已解）— 見 `notes/genghis.md`（2026-10-22）
- [ ] 元朝秘史 — 女性 +17–+19（男性 +17、+18、+23 2026-11-10 已解）— 見 `notes/genchou.md`（2026-10-22）
- [ ] 成吉思汗IV — 特技的 bit 順序只依字串表；+44 bit 3–9、國關係旗標（適性順序與關係欄位 2026-11-10 已解）— 見 `notes/genghis4.md`（2026-10-22）
- [ ] 大航海時代 — 忠誠度在 DS:0x125A（執行時才填） — 見 `notes/koukai.md`（2026-10-22）
- [ ] 大航海時代II — +46 職位、+35／+43 推定是運、忠誠 — 見 `notes/koukai2.md`（2026-10-22）
- [ ] 大航海時代III — 生日只在玩家顯示 — 見 `notes/koukai3.md`（2026-10-22）
- [ ] 大航海時代IV — 欄位順序只靠標籤表和數值；+0x27 出身地域 — 見 `notes/koukai4.md`（2026-10-22）
- [ ] 大航海時代外傳 — +0xB 運氣、+0x13 忠誠 — 見 `notes/koukaigd.md`（2026-10-22）
- [ ] 水滸伝 — 年齢照原值顯示、人気只在某些身分顯示 — 見 `notes/koei-games.md`「水滸伝」（2026-10-22）
- [ ] ランペルール — 兵種判定、名字 +15 的 bits — 見 `notes/lempe.md`（2026-10-22）

### 戰場地圖：沒和遊戲畫面比過

用模擬器（san1 用 NP2kai，其他用 DOSBox-X）各截一張戰場畫面就能確認。

- [ ] 三國志 — PC-98 `SAVEDATA` 各槽有幾格變成城，推定是遊玩中改寫的 — 見 `notes/san1.md`（2026-10-22）
- [ ] 三國志II — 布陣層的意義；排法和色盤 — 見 `notes/san2.md`（2026-10-22）
- [ ] 三國志III — 每張圖用哪組圖塊 — 見 `notes/san3.md`（2026-10-22）
- [ ] 三國志IV — 每張圖的色盤種類、季節 — 見 `notes/san4.md`（2026-10-22）
- [ ] 三國志V — 每張圖的色盤 — 見 `notes/san5.md`（2026-10-22）
- [ ] 三國志英傑傳 — 每張圖用 9 組色盤的哪一組（狀態結構 +5 在哪裡設定） — 見 `notes/eiketsu.md`（2026-10-22）
- [ ] 三國志孔明傳、曹操傳 — 地圖檔的對應只靠結構和渲染結果，讀取程式沒追 — 見 `notes/koumei.md`、`notes/eiketsu5.md`（2026-10-22）
- [ ] 三國志英傑傳 交戰背景 — 地面第 6 段每隔一列是黑線，交戰畫面的色盤沒找到 — 見 `notes/eiketsu.md`「戰場地圖」（2026-10-22）

### 屬性總覽

總表格子裡的 🟡 多半是 2026-10-21 調查時新列、各代筆記還沒有的位置，要逐代驗證後再搬進各代筆記。

- [ ] 三國志 I–XIV — 111 個 🟡 — 見 `notes/san-attributes.md`（2026-10-22）
- [ ] 信長の野望 — 82 個 🟡 — 見 `notes/nobu-attributes.md`（2026-10-22）
- [ ] 英傑傳系列 — 20 個 🟡 — 見 `notes/eiketsu-attributes.md`（2026-10-22）
- [ ] 大航海時代系列 — 11 個 🟡 — 見 `notes/koukai-attributes.md`（2026-10-22）
- [ ] 蒼き狼と白き牝鹿系列 — 11 個 🟡 — 見 `notes/genghis-attributes.md`（2026-10-22）
