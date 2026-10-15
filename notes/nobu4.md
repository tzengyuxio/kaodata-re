# 信長之野望・武將風雲錄（NOBU4, DOS 中文版）頭像相關格式

`dekoei.py export nobu4-dos` 用到的格式。來源是 `games/archives/dos/信長之野望．武將風雲錄_中文版_Nobu4.rar`，解開放在 `games/nobu4-dos/`。

## 版本

- 中文版 `MAIN.EXE` 1994-05-18，沒有壓縮（MZ 檔頭 0x7000 bytes），MSC 執行檔，DGROUP 段值 0x3DF4（檔案 0x44F40）。下文的位址是映像（檔案 − 0x7000）位址。
- `KAODATA.DAT`、`MONDATA.DAT`、`GAIJI.DAT` 是 1993-11-22，劇本 `SNDATA*.CIM` 是 1994-05-18。

## 色盤

- 0x2409 設 VGA mode 12h，int 10h AX=1000 把屬性 6 改成 0x36、7 改成 0x3F，其他用預設。
- 0x286A 把每 8 點的 byte 0／1／2 寫到 plane 0／2／1，所以 `to_3bpp_indexes` 的色號依序是 `#000000 #00AA00 #AA0000 #FFFF00 #0000AA #00AAAA #AA00AA #FFFFFF`（和舊 `nobu4` group 的 docstring 相同）。

## 頭像：KAODATA.DAT

- 311 張 × 1920 bytes，64×80 全高、3bpp（`to_3bpp_indexes`），沒有壓縮。0x7088 `seek(code × 0x780)`。

## 組合臉：MONDATA.DAT（0x6E9C）

- 頭像碼（記憶體人物 +0x17）bit 14–15 不為 0 時是組合臉，否則是頭像號。
- 4 種頭型，每型 0x5A90 bytes（`code & 3`）。每列 24 bytes，下列是型內 offset、筆數、碼的欄位、畫到的列：
  - 上：0x0000，8 × 0x3C0（40 列），bit 2–4，第 0–39 列
  - 下：0x1E00，8 × 0x3C0（40 列），bit 5–7，第 40–79 列
  - 眼：0x3C00，8 × 0x180（16 列），bit 8–10，第 22–37 列
  - 口：0x4800，8 × 0x1B0（18 列），bit 11–13，第 46–63 列
  - 鼻：0x5580，3 × 0x1B0（18 列），bit 14–15 減 1，第 32–49 列
- 上下直接複製；眼、口、鼻用 0x6E76 逐 byte XOR 疊上去。三者彼此也會重疊，但 XOR 的順序不影響結果，匯出用 `blend: "xor"`，code 是 bitfield（鼻 `base: 1`）。
- 頭型依畫面取名：0 甲冑、1 正面、2 側面、3 斜側。

## 人物：SNDATA1–3.CIM、SNDATA1T–3T.CIM

- 三個劇本。`SNDATAn.CIM` 0x1192 起是 33 bytes 的人物記錄（劇本 1、3 是 250 筆，劇本 2 是 255 筆）：姓 6 bytes、0、名 6 bytes、0，+0x15 是 u16 頭像碼，+0x1F 是指向下一筆的指標（載入後在 DGROUP 的位址，DGROUP＝檔案＋0x3E）。
- `SNDATAnT.CIM` 是之後登場的人物，28 bytes 一筆：+3 姓 6 bytes、0、名 6 bytes、0，+0x18 是 u16 頭像碼，姓為空的記錄結束。
- 姓名是光榮台灣內碼，外字 `EB xx` 的字形在 `GAIJI.DAT`（16×16，第 xx − 0x9F 個）。人名用到的（`koei_games.NOBU4_GAIJI`）：9F 長、A0＋A1 宗我部（三格擠四個字：長宗我部、香宗我部）、A3 蘆、A4 堯、A5 香、A8 瓊，B3 是擠成一格的「山內」、B4 是「深谷」（山內上杉憲政、深谷上杉憲賢、深谷上杉憲盛）。
- `id`：劇本 1、1T、2、2T、3、3T 的順序，同一頭像碼只收一次，共 507 人（223 組合臉、284 頭像）。0–249 和 `nobu4-fc` 相同。同名不同臉的是不同人（風魔小太郎兩代、河野通直兩人、島津家久與後來改名家久的忠恆）。
- 同一頭像碼在不同劇本寫法不同時，取正確的（`NOBU4_DOS_NAME_PICK`）：遠籐→遠藤基信、服部半臟→服部半藏、真田昌辛／昌信→真田昌幸、小早田→小早川秀包、大友親勝→大友親盛、柳生宗規→柳生宗矩。松平元康（劇本 1）和德川家康（劇本 2、3）同臉，取第一次出現的松平元康。
- `nameHistorical`：缺字代用 田山→畠山（義綱、義慶）、北田→北畠（具教、具房、政成）、神原→榊原康政；錯字 管沼定村→菅沼定村、肉戶隆家→宍戶隆家、四天王政孝→四王天政孝。齊藤（齋藤）、佐佐（佐々）、高阪（高坂）照錄不填。

## 沒有人物使用的頭像

畫臉的 0x714A 以常數頭像碼呼叫的地方，旁邊的訊息決定身分：

- 139 今井宗久（「堺商會」，原文誤作「界」，0x153DB、0x17DBF）
- 140 千利休（「茶道 %s」，名字在 DGROUP 0x8F42，0x30F2B）
- 273 澤彥（「政秀寺開山 澤彥」，安土城事件，0x2C78F）
- 274 朝廷使者（改名事件，0x2C4F2、0x2C635）
- 275 路易斯・弗羅伊斯（「耶穌會 傳教士 %s」，名字在 DGROUP 0x8F66 寫「路易斯. 弗羅伊斯」，0x2DE1B）
- 276–295 公主（「%s家 公主」，0x18566 `0x114 + rand(20)`；結束畫面 0x28D0F 用 `0x113 + rand(20)`，即 275–294）
- 296 義姬（伊達、最上的事件，0x2C00C、0x2C0A5）
- 297 田山義繼（畠山義繼，「二本松城主」，刺殺伊達輝宗的事件，0x2B81F、0x2BCD6）

## PC-98 版（`nobu4-pc98`）

來源是 `games/archives/pc98/[PC98] 信長の野望・風雲録.zip`（A、B 兩片），每片解在 `games/archives/pc98/disks/nobu4-pc98/`，合併放在 `games/nobu4-pc98/`。`VERSION`：For PC-9801 Series，Mar.07,1991 Ver 1.0 Rel 1.0 TYPE-A。`MAIN.EXE` 沒有壓縮（MZ 檔頭 0x6E00 bytes）。

- `KAODATA.DAT`、`MONDATA.DAT`、`GAIJI.DAT` 和 DOS 中文版逐 byte 相同，頭像碼、組合臉的排法也相同。但 PC-98 把每 8 點的 byte 0／1／2 寫到 B／R／G 平面（byte k＝bit k），所以用 `genpei.decode_planar`，不是 `to_3bpp_indexes`。
- 色盤：類比色盤由 0x1099 設定，淡入讀 DS:0x39DA（檔案 0x4216A）的 B、R、G 表。基本表是標準 8 色，主要的淡入（0x4646，11 處呼叫）和初始化（0x469E）把色號 1、3、7 的藍改成 0xC：`#000000 #0000cc #ff0000 #ff00cc #00ff00 #00ffff #ffff00 #ffffcc`。（0x467C 另一組把 1、3 設成 0xF，只有 2 處呼叫，不收。）
- 人物：劇本檔位置與記錄長度同 DOS 版，姓名是 Shift-JIS，姓、名各 7 bytes（DOS 是 6＋0）。外字 `EB xx` 照 `NOBU4_GAIJI` 對應，「山內」改寫成「山内」（`koei_games.load_nobu4_pc98_people`）。各劇本人數、頭像碼都和 DOS 相同，共 507 人。
  - 同碼不同名的只有松平元康（劇本 1）／徳川家康（劇本 2、3），比照 `nobu5-pc98`、`nobu6-pc98` 取徳川家康。
  - DOS 中文版的錯字在日文版只剩「四天王政孝」（四王天政孝），只填這一筆 `nameHistorical`。
- 沒有人物使用的頭像：`MAIN.EXE` 裡畫臉的常數相同（0x8B、0x8C、0x111–0x113、0x128、0x129，公主 0x114＋rand(20)）。名字用日文版的寫法：139 今井宗久、140 千利休、273 沢彦、274 朝廷使者、275 ルイス＝フロイス、296 義姫、297 畠山義継，歸「事件人物」；276–295 歸「姫」。

## X68000 版（`nobu4-x68`）

`dekoei.py export nobu4-x68` 用 `build_nobu4_dos(pc98=True, x68=True)`。來源是 Internet Archive `softwarelibrary-x68k` 的 `nobunaga_no_yabou_bushou_fuuun_x68k`（`games/archives/x68000/ia-softwarelibrary/`，3 片 DIM），Disk A 的 `MAIN.Z`、`VERSION`、`SNDATA*.CIM` 與 Disk C 的 `KAODATA.DAT`、`MONDATA.DAT`、`GAIJI.DAT` 放在 `games/nobu4-x68/`。Disk A 有三份傾印（無標記、`[a]`、`[a2]`），資料檔相同，`MAIN.Z` 只差 2 bytes，用無標記那份。`VERSION` 寫 `For X68000 Series july.12,1991 Ver 1.1`。

- `KAODATA.DAT`、`MONDATA.DAT` 和 PC-98 版逐 byte 相同，像素順序也同 PC-98（byte k＝plane k）。
- 人物：欄位同 PC-98，但有 68000 的補位。`SNDATA1–3.CIM` 從 0x17C8 起每筆 40 bytes，頭像碼是 +24 的大端序 u16；`SNDATA1T–3T.CIM` 每筆 30 bytes，頭像碼是 +26 的大端序 u16。三個劇本的姓名與頭像碼都和 PC-98 版相同。劇本 2 的人物表結尾和 PC-88 一樣是 0x01 開頭的記錄。
- 色盤：唯一的差異。`MAIN.Z`（檔頭 0x1C bytes，執行位址＝檔案 offset＋0x514DE）在 0x2584 把檔案 0x3FD4E 的 16 個 GRB 值寫進文字色盤 E82200；淡入的目標表在 0x3FC8E（B、R、G 各 5 bit）也是同一組顏色。色號 0–7 是 `0000 0037 07C1 06F3 F801 F83F FFC1 FFFF`，即色號 1 的藍是 27、色號 3 是紅 27 藍 25（滿值是 31），色號 7 是純白。換成 8 bit（v << 3 | v >> 2）是 `#000000 #0000de #ff0000 #de00ce #00ff00 #00ffff #ffff00 #ffffff`。PC-98 版則是把色號 1、3、7 的藍設成 0xC。

## PC-88 版（`nobu4-pc88`）

來源是 Neo Kobe 2016-02-25 的 `games/archives/pc88/neo-kobe-2016-02-25/Nobunaga no Yabou - Bushou Fuuunroku/`：Disk A 取 `[FD].7z` 主檔，Disk C 取 `[FD] [Set 1].7z` 的（FD 主檔 Disk C 在 0x5400 有一個壞磁區，是第 7 張頭像的底部；Set 1 和 C Alt 1 的才對）。用到的檔案解在 `games/nobu4-pc88/`。

- 版本：`風雲録.VER`「For PC-8801SR TYPE-B, Ver 1.0 Rel 1.0 03/12/1990」，Disk A 的檔案日期 1990-12-03，`KAODATA.DAT` 1990-11-19。ja.wikipedia：88SR 版 1990-12-12，比 PC-98 版（1991-03-15）早，是首發。
- 磁碟：80 軌，每軌 9 × 512 bytes。Disk A 是 YDOS 3.0（FAT 在 0x200、目錄 0xA00、資料 0x1800 起、1 KB 一叢），Disk C 是 FAT12 360 KB。Disk B 只用在 demo。
- 色盤：YSHELL.COM 0x153 清掉 port 0x32 bit 5，是數位 8 色（色號 bit 0 B、bit 1 R、bit 2 G）。

### 頭像：KAODATA.DAT（Disk C）

- 285 張 × 960 bytes：64×40，每 8 點 B、R、G 3 bytes（`pc88.brg_pixels`），200 線，匯出逐列加倍。
- 和 PC-98／DOS 比：同頭像號是同一個人。0–140 都是同一張畫在 200 線上重點的（19 武田信玄沒戴頭盔），141–272 多數修過，約三分之一明顯重畫（145 直江景綱、157 北条氏照、178 姉小路良頼等）；沒有任何一張是 400 線圖機械地抽列。273、274 和 PC-98 同（沢彦、朝廷使者）；275–284 是 10 位姫，是 PC-98 那 20 位裡的 10 位（PC-98 的 277、278、283、284、286、288、289、291、292、295）。沒有フロイス、義姫、畠山義継與 PC-98 的 298–310。
- 139、140、273、274 照 PC-98 命名歸「事件人物」，275–284 歸「姫」；其餘人物表沒用到的 60 張（PC-98 劇本 3 與之後登場者的臉）歸「未使用」。

### 組合臉

- 接在頭像之後（0x42CC0），4 種頭型 × 0x2D48 bytes，是 MONDATA 的半高版：上 8 × 0x1E0（+0）、下 8 × 0x1E0（+0xF00）、眼 8 × 0xC0（+0x1E00）、口 8 × 0xD8（+0x2400）、鼻 3 × 0xD8（+0x2AC0）。
- MAIN.COM 0x2EEB 在 960 bytes 的緩衝區組臉：上、下複製到第 0、20 列，眼、鼻、口 XOR 到第 11、16、23 列（DOS 列號的一半）。頭像碼欄位同 DOS。

### 人物：SNDATA1–2.CIM（Disk A）

- 記錄同 PC-98（33 bytes，姓、名各 7 bytes Shift-JIS，+0x15 頭像碼），從 0x1175 起（`koei_games.load_nobu4_pc88_people`）。劇本 2 的表後接一筆以 0x01 開頭的記錄，當結尾。
- 只有兩個劇本（250、255 人），沒有劇本 3 和之後登場的 T 檔。`id` 照劇本 1、2 的順序、同一頭像碼只收一次，共 362 人（151 組合臉、211 頭像），0–249 和 `nobu4-fc` 相同。
- 劇本 1 的頭像碼和 PC-98 完全相同。和 PC-98 同碼的名字只差上杉憲政、上杉憲賢、上杉憲盛沒有「山内／深谷」。松平元康（劇本 1）／徳川家康同碼，比照 PC-98 取徳川家康。沒有要填的 `nameHistorical`。

## Windows 版（`nobu4-win`）

`dekoei.py export nobu4-win` 用到的格式。來源是 Steam 版（appid 521740，見 `notes/steam.md`），是日文的 Windows 版，匯出用到的檔案複製到 `games/nobu4-win/`。

- 頭像全部重畫成 256 色。`.nb4` 圖檔是 BMP，只是 14 bytes 的檔頭寫成「`XEBM`、檔案大小、像素起點、2 bytes 0」（`nobu4_win_bitmap` 換回 `BM` 檔頭）。
  - `Facedata.nb4`：64×24880，311 張 64×80，和 `KAODATA.DAT` 同順序，事件人物、姫的編號相同。
  - `Mondata.nb4`：64×20480，256 張 64×80 的整張組合臉：頭型（甲冑、正面、側面、斜側）× 上 8 × 下 8，索引＝頭型 × 64＋上 × 8＋下。眼、鼻、口不再是零件。
  - 兩檔共用 BMP 的色盤，256 色全用到、沒有重複。色號 243（108 點）併進幾乎相同的 237（差 9、5、1），色號 255 換到 243，共 255 色。
- 人物：`sndata1–3.nb4`。檔頭 `D4BN`，0x14 起是本體人物，41 bytes 一筆：姓 9 bytes、名 7 bytes（Shift-JIS），+23 u16 頭像碼（同 PC-98），+25 u16 組合臉在 `Mondata.nb4` 的索引；0x3F38 起是後登場人物，32 bytes 一筆：姓在 +3（9 bytes）、名在 +12（7 bytes），+26 u16 頭像碼，+28 的索引都是 0（`koei_games.load_nobu4_win_people`）。筆數與 PC-98 相同。
- 組合臉的分配（`Nobunaga4.exe` 解開 SteamStub 後 0x44F400）：依頭像碼的頭型、上（bit 0–1、2–4），在同組 8 張裡挑一張還沒人用的；同組用完就隨機換頭型。人物死亡時釋放（0x46A8D0）。後登場的人在登場時才分配（0x43D49B）。所以同一頭像碼在不同劇本可能是不同張：本體表 201 個組合臉碼中有 81 個在三個劇本裡的索引不同；同劇本內不重複。
  - 匯出：本體表的人取劇本 1→2→3 第一次出現時存的那張；只在後登場表出現的 22 人取頭像碼的「下」欄位那張（遊戲可能挑中的 8 張之一），並加 `note` 說明。
- 姓名和 PC-98 相同，只有高橋紹雲改正為高橋紹運；四天王政孝照舊填 `nameHistorical`。依 PC-98 的規則每個頭像碼一人、松平元康併為徳川家康，共 507 人。
