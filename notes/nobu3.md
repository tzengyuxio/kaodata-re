# 信長之野望・戰國群雄傳（NOBU3, DOS 中文版）頭像相關格式

`dekoei.py export nobu3-dos` 用到的格式。來源是 `games/archives/dos/信長之野望２_中文版_nobu2-c.rar`（台灣稱「信長之野望II」），解開放在 `games/nobu3-dos/`。

## 版本

- 英文 DOS 版 Nobunaga's Ambition II 的移植：`KAODATA.DAT`、`KAO_OE.DAT`、`PACKDATA.DAT`、`HEXDATA.DAT` 和英文版（`games/archives/dos/信長之野望２_英文版_nobunagas-ambition-ii.zip`）逐 byte 相同；劇本換成中文名字（1993-08）。
  - 英文版本身（MAIN.EXE 1990-12-10）的 SNDATA1／2 記錄排法、人數（240／212）和頭像碼也逐筆和中文版相同，只有人名是羅馬字（Uesugi Kenshin……）。同平台、同頭像、只有人名語言不同的在地化版本不另收（kaodata `docs/collection.md`），所以沒有英文版資料集。
- 中文版 `MAIN.EXE`（1993-11-04）是 TINYPROG 壓縮，開頭會印「Cracked by C.C.F. 4th November, 1993」，是破解版。用 unicorn 跑完解壓 stub 後，程式碼和英文版 `MAIN.EXE`（沒壓縮，MZ 檔頭 0x3E00，DGROUP 0x1DBC）相同結構。下文位址是英文版映像位址。
- `SAVEDATA.DAT`（2001）是玩家存檔，`SAVEDATA.ORG` 是空白存檔範本，都不用。

## 色盤

- 預設走 EGA mode 0x0E（640×200，0x1356），屬性表 DGROUP 0x3BDC `00 11 12 … 17`（0x12E6 int 10h AX=1002）；200 線模式下 0x1x 是加亮色。
- 顯示模式由 `MAIN.EXE` 的第一個參數決定（存到 [0xA882]）：英文版 `KOEI.COM` 偵測到 EGA／VGA 彩色就傳 `0`（mode 0x0E），CGA、MCGA、單色 EGA 傳 `1`（mode 6，640×200 雙色，頭像在這個模式怎麼對色沒追）。中文版的 `KOEI.COM` 換成不偵測顯示卡、不帶參數的小程式，所以只跑 EGA。
- 0x2668 把每 8 點的 byte 0／1／2 寫到 plane 0／2／1，和三國志II、大航海時代相同，所以是 `SAN2_PALETTE`。
- 頭像是 64×40 半高（200 線），匯出時每列重複一次（`san2_pixels`）。

## 頭像：KAODATA.DAT

- 0x0000–0x297BF：177 張 × 960 bytes（0x5832 `seek(code × 0x3C0)`）。
- 0x297C0 起：組合臉零件，4 組 × 0x1680 bytes。
- `KAO_OE.DAT` 是 KAODATA 第 0–27 張的複本，給武將編輯程式 `OE.EXE` 用，不匯出。

## 組合臉（0x588C）

- 頭像碼 bit 15 為 1 時是組合臉。人物記憶體 +0x23（檔案記錄 +0x21）。
- 零件（相對 0x297C0 的 offset、每筆大小、碼的欄位、半高列）：
  - 上：0x0000，0x1B0（18 列），bit 2–3，第 0–17 列
  - 下：0x06C0，0x210（22 列），bit 4–5，第 18–39 列
  - 眼：0x0F00，0x78（5 列），bit 6–7，第 13–17 列
  - 鼻：0x10E0，0x90（6 列），bit 8–9，第 18–23 列
  - 口：0x1320，0xD8（9 列），bit 10–11，第 24–32 列
- 上下直接複製，眼鼻口用 0x5866 逐 byte XOR 疊上，匯出用 `blend: "xor"`。照遊戲組法逐 byte 重算過全部 228 張組合臉，結果一致。
- 檔案裡有 4 組零件（髮型、背景不同），劇本的頭像碼 bit 0–1 也用到 0–3，但英文版和中文版的 MAIN.EXE 都只讀第 0 組（0x297C0 寫死），bit 0–1 沒有作用。匯出照 DOS 的實際畫面只放第 0 組（一個 variant）。其他 3 組可能是 PC-98 原版用的，沒驗證。
- code 是 bitfield，`$variant` 放在 bit 15、`base: 1`，讓網站產生的碼帶上組合臉旗標；bit 0–1 不解。

## 人物：SNDATA1.CIM、SNDATA2.CIM

- 0xD38 起 44 bytes 一筆，首 byte 為 0 是空位：姓 11 bytes、名 11 bytes（光榮台灣內碼），+0x21 是 u16 頭像碼（`koei_games.load_nobu3_dos_people`）。劇本 1 240 人、劇本 2 212 人。
- 組合臉的碼會撞：不同人用同一個碼（如 0x8108 松田憲秀、繁澤元氏）。所以比照 `nobu3-fc`，以「姓名＋頭像碼」去重，劇本 1 再劇本 2，共 385 人（228 組合臉、157 頭像）。0–239 和 `nobu3-fc` 相同；FC 240–255 的後來登場武將（荒木村重等）DOS 版沒有。
- 同一人同一碼、只有其中一個劇本寫錯的，取正確寫法（`NOBU3_DOS_NAME_FIX`）：齊籐朝信→齊藤朝信、羽祡秀吉→羽柴秀吉。
- `nameHistorical`（18 筆）：
  - 缺字代用：田山→畠山（義綱、義慶）、北田→北畠（具教、具房、政成）、高田定吉→高畠定吉、神原康政→榊原康政、並和康忠→垪和康忠
  - 錯字：今川氏貞→今川氏真、北庄秀綱→本庄秀綱、溫井景龍→溫井景隆、森下通興→森下通與、溥生氏鄉→蒲生氏鄉、著尾高春→箸尾高春、肉戶隆家→宍戶隆家、九鬼嘉窿→九鬼嘉隆、小早川窿景→小早川隆景、羽祡秀長→羽柴秀長
  - 不填：齊藤（齋藤）、高阪／上阪（坂）、佐佐／野野村（々）、鈴木佐大夫。

## 沒有人物使用的頭像（157–176）

- 通婚（0x114A4）：`0x9D + rand(20)`，畫面是要嫁過去的女性，group「公主」。其他畫臉的呼叫都是用人物的頭像碼。

## PC-98 版（`nobu3-pc98`）

`dekoei.py export nobu3-pc98` 用到的差異（`build_nobu3_pc98`）。來源是 `games/archives/pc98/[PC98] 信長の野望・戦国群雄伝.zip`（A、B 兩片 FDI），解到 `games/archives/pc98/disks/nobu3-pc98/A`、`B`，合併到 `games/nobu3-pc98/`。MAIN.EXE 和劇本是 1989-05-08，頭像檔 1989-02-16。B 片的 `群雄伝.DIR` 是填滿 KOEI 版權字串的檔，不是目錄。

- `MAIN.EXE` 的 header 是 0x3C00 bytes，DGROUP 在檔案 0x23EF0。下文是去掉 header 後的位址。
- 頭像：`ORGKAO1–3.DAT` 接起來是 177 張 64×80 全高（400 線）頭像，每 8 px 3 bytes，byte k＝plane k（`genpei.decode_planar`），1920 bytes，順序和 DOS 版相同。0x1DE8 起的畫圖程式把 byte 0／1／2 寫到 A800／B000／B800。
- 色盤：預設的數位 8 色。DS:0x5618 存 port A8–AE 的值 `37 15 26 04`（標準排列），0x2236 改單色，只在 0x5F5A 的閃爍特效用到，結束後還原。
- 組合臉：`MONKAO.DAT` 是 4 組零件 × 0x2D00 bytes，每組是 DOS 版那一組的全高版（位置與列數加倍）：上 36 列、下 44 列（第 36 列起），眼 10 列（第 26 列）、鼻 12 列（第 36 列）、口 18 列（第 48 列），眼鼻口 XOR 疊上（0x4594）。
  - 和 DOS 版不同，0x45B8 用頭像碼 bit 0–1 選組（`(碼 & 3) × 0x2D00`），所以 4 組都匯出成 variant。第 3 組是僧侶（下間一族等）。
- 人物：`SNDATA1.CIM`、`SNDATA2.CIM` 0xD38 起 38 bytes 一筆：姓 9 bytes、名 7 bytes（Shift-JIS），+27 是 u16 頭像碼（`koei_games.load_nobu3_pc98_people`）。人數（240、212）和頭像碼都和 DOS 版相同，去重後同樣是 385 人（228 組合臉）。日文名沒有 DOS 版的錯字，不填 `nameHistorical`。
- 通婚的公主頭像同樣是 `0x9D + rand(20)`（0x10CBE），即 157–176，group「姫」。

## X68000 版（`nobu3-x68`）

`dekoei.py export nobu3-x68` 用 `build_nobu3_pc98(x68=True)`。來源是 Internet Archive `softwarelibrary-x68k` 的 `nobunaga_no_yabou_sengoku_guny_x68k`（`games/archives/x68000/ia-softwarelibrary/`，3 片 DIM），Disk A（`ORGKAO1–3.DAT`、`MONKAO.DAT`、`MAIN.Z`、`VERSION`）與 Disk C（`SNDATA1/2.CIM`）的檔案放在 `games/nobu3-x68/`。`MAIN.Z` 的版本字串是 `Rel.1A ***Feb.15, 1989***`。

- 頭像與組合臉檔和 PC-98 版逐 byte 相同。
- 色盤：`MAIN.Z`（未壓縮，檔頭 0x1C bytes）檔案 0x412D2 起的 GRB 文字色盤（每色 4 bytes）`0000 003E 07C0 07FE F800 F83E FFC0 FFFE`，各分量是 0 或最大，和 PC-98 的數位 8 色同序。
- 人物：`SNDATA1/2.CIM` 0x11F8 起 44 bytes 一筆，姓名欄同 PC-98，頭像碼是 +30 的大端序 u16（中間多了 68000 的補位）。兩個劇本的姓名與頭像碼和 PC-98 版完全相同，匯出結果除了 id、平台與色盤 id 之外一樣。kaodata 網站不另收這份資料集，只在 `nobu3-pc98` 標上 X68000 版（1989-12-08）。

## PC-88 原版（`nobu3-pc88`）

`dekoei.py export nobu3-pc88` 用到的差異（`build_nobu3_pc88`）。來源是 Neo Kobe 2016-02-25 的 `games/archives/pc88/neo-kobe-2016-02-25/Nobunaga no Yabou - Sengoku Gunyuuden/Nobunaga no Yabou - Sengoku Gunyuuden [FD].7z`。檔案放在 `games/nobu3-pc88/`：Disk C（FAT12）的 `KAODATA.DAT`，Disk A（YDOS 3.0）的 `SNDATA1/2.CIM`、`VERSION`，以及參考用的 `MAIN.COM`。

- `VERSION`：`NOBUNAGA NO YABOU -- SENGOKU GUNYUUDEN -- Rel.1C Dec.07, 1988`。這是系列的首發平台。
- `KAODATA.DAT` 和 DOS 版**逐 byte 相同**：177 張 64×40 半高頭像，加上 4 組組合臉零件。DOS 版直接沿用了 PC-88 的 200 線圖。匯出照 DOS 用 `san2_pixels`（每列重複一次）。
- 色盤：數位 8 色，色號意義同 `san2-pc88`（`SAN2_JP_PALETTE`），palette id `pc88`。
- 組合臉：`MAIN.COM` 0x2F8F 算 `(碼 & 3) × 0x1680 + 0x297C0`，用頭像碼 bit 0–1 選組（同 PC-98），所以 4 組都匯出成 variant。各區域的位置和 XOR 同 DOS（0x2F7D 是 XOR 迴圈）。
- 人物：`SNDATA1.CIM`、`SNDATA2.CIM` 0xC1E 起 36 bytes 一筆，欄位同 PC-98（姓 9、名 7，Shift-JIS，+27 頭像碼；`load_nobu3_pc98_people(..., pc88=True)`）。人數、順序、頭像碼都和 PC-98 相同，去重後 385 人。
- 姓名有 5 個 PC-88 才有的錯字，PC-98、DOS 版都已改正，填 `nameHistorical`（`NOBU3_PC88_NAME_HISTORICAL`）：
  - 河野道宣→河野通宣
  - 河野道直→河野通直
  - 萩野直正→荻野直正
  - 萩清誉→荻清誉
  - 山内隆道→山内隆通
- 公主頭像 157–176 的 group「姫」沿用 PC-98 的結論，沒有在 PC-88 程式裡另外追。

## Windows 日文版（Steam）

`dekoei.py export nobu3-win` 用到的格式（`build_nobu3_win`）。來源是 Steam 版（appid 521700，Readme 2017年2月，見 `notes/steam.md`），匯出用到的檔案複製到 `games/nobu3-win/`。

- `Nobunaga3.exe` 有 SteamStub，解法同三國志VIII（見 `notes/san8.md`）。匯出不讀 EXE。
- `Kao.nb3`、`Kao2.nb3`、`Kao3.nb3`、`palette.nb3` 都是 LS11 封裝（`ls11.ls11_decode_parts`）。頭像每段是 `2A 38`、u16 寬、u16 高，加 64×80 的 8 bit 色號，沒有壓縮。
  - `Kao.nb3`：157 張，PC-98 的頭像 0–156 重畫。
  - `Kao2.nb3`：22 張，前 20 張是 PC-98 157–176 的公主，最後 2 張是男性的臉。
  - `Kao3.nb3`：256 張，組合臉改成整張畫好的臉，沒有零件。
- 0x42A950 依頭像碼取圖：bit 15 → `Kao3[碼 & 0xFF]`，bit 11 → `Kao2[碼 & 0xFF]`，其他 → `Kao[碼]`。匯出的頭像依序是 Kao 0–156、Kao2 157–178、Kao3 179–434，`code` 就是遊戲的頭像碼。
- 婚姻（0x432DD0）的新娘臉是 `0x800 | rand(22)`，所以 Kao2 最後兩張男性的臉也會被抽到；22 張都歸 `姫`，那兩張加 `note`。
- 色盤：`palette.nb3` 第 1 段是頭像色盤（B、R、G）。頭像只用到 98 色，沒有用到色號 0 和 255，不用換色號。
- 人物：`sndata1.nb3`、`sndata2.nb3` 0x11B6 起 44 bytes 一筆（版面同 X68000 版），+30 是 little-endian 的頭像碼（`load_nobu3_pc98_people(..., win=True)`）。姓名、人數、順序都和 PC-98 相同。
  - 組合臉的碼重新編過，是 `0x8000 | Kao3 索引`，眼鼻口的位元不再使用；同一劇本裡每人一張，223 張有人用，33 張沒人用（都歸 `大眾臉`）。
  - 北条氏直在劇本 2 也改用劇本 1 的專用頭像 64（PC-98 版劇本 2 是組合臉），繁沢元氏和松田憲秀不再共用同一張臉。照 PC-98 以「姓名＋頭像碼」去重，共 384 人。
