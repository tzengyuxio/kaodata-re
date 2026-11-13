# Notes of Koei Games

雜七雜八的都記在這邊

## 拿破崙

- 有戰場 MAP [ランペルール](https://secky.org/arcade/lempe/index.html)
- handbook 介紹 [ランペルール](https://syumisya.com/koei/ex/LA.html)

## 項劉記

大地圖 (see [https://cafe.naver.com/koeimod/256])

- GRP3.KR1
- 分上下部份
- 變種 NPK/RLE
- 一個檔案中有多個不同格式

## 源平合戰

원평합전
원평합전 이미지 편집기 (源平合戰 影像 編輯器)

似乎有韓文編輯器 (source: https://k66google.tistory.com/766)

0x8000A000 在 kaodata.gp 出現位置
- 0
- 4403 0x1133 後面接 0x7FFF, 與前差 4403
- 5068 0x13cc 後面接 0x7000, 與前差 665
- 10068 0x2754, 0x7FFF, 5000
- 10760 0x2A08, 0x7000, 692
- 14932 0x3A54, 0x7FFF, 4172
- 15490 0x3C82, 0x7000, 558

mask 應該有 2560 bytes

## 英傑傳

有兩個版本的頭像檔案

### DOS

- 已解開，格式見 [eiketsu.md](eiketsu.md)（TFDED.COM 的 TF-DCE 壓縮）
- 人物似乎只有八色
- 檔案 342 KB
- 前面有 1440 bytes 為 offsets 資料, 6 bytes 一組, 240 組
- offset info 為 start(4 bytes) 與 size(2 bytes)
- 每個 block 開頭有 7 bytes 相同 `0254 0850 0033 03`
- 第 8 byte 都是 D2, C6, E1, C6, C9 這類的數值
- 第 9 byte 都是 `20`
- 第 10 byte 都是 `04` `05` `06` `07` `08`
- 後面的就比較沒規律

### WINDOS

- 檔案 461 KB
- 有 LS11 檔頭
- 每個 block 似乎都有 'NPK016' 字樣 (獨立戰爭也有)

## 水滸傳

0 太尉,寵臣
1 太守,高官
2 官吏,官吏
3 好漢
4 頭目
5 強盜,無頼漢
6 義兄
7 義弟
8 死亡
9 罪犯
10 僧侶,僧侶
11 漁夫,漁師
12 苦力,人夫
13 醫者,医者
14 生意人,商人
15 客棧掌櫃,居酒屋
16 技工,職人
17 學究,学者
18 富人,長者
19 少爺,若旦那
20 少女,小娘
21 藝妓,芸妓
22 獵人,猟師
23 大力士,力士
24 壯士,武芸者
25 客商,旅商人
26 江湖藝人
27 道士,道士
28 失業武人,浪人
29 無業遊民,無法者
30 虎
31 狼
32 熊
33 豹

## 獨立戰爭

- 前三個 byte 是 MagicWord, 固定 'IDX'
- 第四個 byte 各有差異
- FACE.IDX 每個 block 的前 8 個 bytes 應該是 width 與 height
- FACE.IDX 有 299 筆 offset 資料 (299 - 0x12B)
  - block size: min(1538), max(2023), avg1798.12
- COMMAND.IDX, EVENT.IDX 中有 'NPK016' 字樣，覺得眼熟
  - 另外檔案中也有個 'OPENNPK.NPK', 推測可能是片頭 OP
- 98版 129 頭像，SF版 174 頭像 (光榮美術館數據)
- GRAPHICS.IDX 中，每個 block 的頭四個 bytes 是 width 與 height,
  - 接下來的兩個 bytes (`first_byte`) 可能與色彩數或 block 長度有關
  - block size = width x height x (`first_byte` / 8)

| file         | pos(3)     | pos(4-7)     | first NBK016 | bytes before first | memo                   |
| ------------ | ---------- | ------------ | ------------ | ------------------ | ---------------------- |
| COMMAND.IDX  | 18 (0x12)  | 76 (0x4C)    | 76           | 72                 |                        |
| EVENT.IDX    | 22 (0x16)  | 92 (0x5C)    | 92           | 88                 |                        |
| FACE.IDX     | 43 (0x2B)  | 1200 (0x4B0) | --           | 1196               | 1200 處是 0x40005000LE |
| GRAPHICS.IDX | 142 (0x8E) | 572 (0x23C)  | --           | 568                | 572 處是 0x04001800LE  |

### NPK 壓縮

bitflag: 0xff1e, cursor=1, dest_len=0             #
bitflag: 0x7f8f, cursor=3, dest_len=4             #
    over_line=False, run_offset=0, run_count=128  #
bitflag: 0x3fc7, cursor=4, dest_len=132
    over_line=False, run_offset=8, run_count=108  # 第一行結束
bitflag: 0x1fe3, cursor=5, dest_len=240
    over_line=True, run_offset=0, run_count=128   #
bitflag: 0xff1, cursor=6, dest_len=368
    over_line=False, run_offset=8, run_count=112  # 第二行結束
bitflag: 0x7f8, cursor=7, dest_len=480            # 4px, 黑黑黑　藍
bitflag: 0x3fc, cursor=9, dest_len=484            # 4px, 藍 淺藍 淺藍 黑
bitflag: 0x1fe, cursor=11, dest_len=488           # 4px, 藍 藍 藍 藍 (共有 224 個藍)
bitflag: 0xff83, cursor=14, dest_len=492          #
    over_line=False, run_offset=0, run_count=128  # 128 藍, (累計132, 剩餘92)
bitflag: 0x7fc1, cursor=15, dest_len=620          #
    over_line=False, run_offset=8, run_count=92   # 92 藍, (累計224, 剩餘0)
bitflag: 0x3fe0, cursor=16, dest_len=712          # 黑 淺 淺 藍
bitflag: 0x1ff0, cursor=18, dest_len=716          # 藍 黑 黑 黑, 第三行結束
bitflag: 0xff8, cursor=20, dest_len=720           # 4px
bitflag: 0x7fc, cursor=22, dest_len=724           # 4px
bitflag: 0x3fe, cursor=24, dest_len=728           # 4px
bitflag: 0x1ff, cursor=26, dest_len=732
    over_line=False, run_offset=0, run_count=128  # 128px
bitflag: 0xffc1, cursor=28, dest_len=860
    over_line=False, run_offset=8, run_count=92   # 92px
bitflag: 0x7fe0, cursor=29, dest_len=952          # 4px
bitflag: 0x3ff0, cursor=31, dest_len=956          # 4px, 第四行結束
bitflag: 0x1ff8, cursor=33, dest_len=960          # 4px
bitflag: 0xffc, cursor=35, dest_len=964           # 4px
bitflag: 0x7fe, cursor=37, dest_len=968           # 4px
bitflag: 0x3ff, cursor=39, dest_len=972           #
    over_line=False, run_offset=0, run_count=128  # 128px
bitflag: 0x1ff, cursor=40, dest_len=1100
    over_line=False, run_offset=8, run_count=92   # 92px
bitflag: 0xff30, cursor=42, dest_len=1192         # 4px
bitflag: 0x7f98, cursor=44, dest_len=1196         # 4px, 第五行結束
bitflag: 0x3fcc, cursor=46, dest_len=1200         # 4px
bitflag: 0x1fe6, cursor=48, dest_len=1204         # 4px ! 最後變藍色？
bitflag: 0xff3, cursor=50, dest_len=1208
    over_line=True, run_offset=480, run_count=128 # 128px
bitflag: 0x7f9, cursor=51, dest_len=1336
    over_line=False, run_offset=8, run_count=96   # 96px
bitflag: 0x3fc, cursor=52, dest_len=1432          # 4px
bitflag: 0x1fe, cursor=54, dest_len=1436          # 4px, 第六行結束
bitflag: 0xff18, cursor=57, dest_len=1440         # 4px
bitflag: 0x7f8c, cursor=59, dest_len=1444         # 4px
bitflag: 0x3fc6, cursor=61, dest_len=1448         # 4px
bitflag: 0x1fe3, cursor=63, dest_len=1452
    over_line=False, run_offset=0, run_count=128  # 128px
bitflag: 0xff1, cursor=64, dest_len=1580
    over_line=False, run_offset=8, run_count=92   # 92px
bitflag: 0x7f8, cursor=65, dest_len=1672          # 4px
bitflag: 0x3fc, cursor=67, dest_len=1676          # 4px, 第七行結束
bitflag: 0x1fe, cursor=69, dest_len=1680          # 4px
bitflag: 0xff66, cursor=72, dest_len=1684         # 4px
bitflag: 0x7fb3, cursor=74, dest_len=1688         # 4px
    over_line=True, run_offset=0, run_count=128   # 128px
bitflag: 0x3fd9, cursor=75, dest_len=1816
    over_line=False, run_offset=8, run_count=96   # 96px
bitflag: 0x1fec, cursor=76, dest_len=1912
bitflag: 0xff6, cursor=78, dest_len=1916
bitflag: 0x7fb, cursor=80, dest_len=1920
    over_line=True, run_offset=1440, run_count=4
bitflag: 0x3fd, cursor=81, dest_len=1924
    over_line=True, run_offset=0, run_count=4
bitflag: 0x1fe, cursor=82, dest_len=1928
bitflag: 0xffd2, cursor=85, dest_len=1932
bitflag: 0x7fe9, cursor=87, dest_len=1936
    over_line=False, run_offset=0, run_count=44
bitflag: 0x3ff4, cursor=88, dest_len=1980
bitflag: 0x1ffa, cursor=90, dest_len=1984
bitflag: 0xffd, cursor=92, dest_len=1988
    over_line=False, run_offset=0, run_count=4
bitflag: 0x7fe, cursor=93, dest_len=1992
bitflag: 0x3ff, cursor=95, dest_len=1996
    over_line=False, run_offset=24, run_count=12
bitflag: 0x1ff, cursor=96, dest_len=2008
    over_line=False, run_offset=8, run_count=4
bitflag: 0xff66, cursor=98, dest_len=2012

## 魔眼邪神

- 日: ケルトの聖戦 (日文 wiki 好像找不到條目?)
- 英: Celtic Tales: Balor of the Evil Eye
- 日文 Windows 版的格式見 `notes/celt.md`（`celt-win`）
- [魔眼邪神存檔分析 \- KPHEROS\# \- lechi的創作 \- 巴哈姆特](https://home.gamer.com.tw/artwork.php?sn=5227637)

## 水滸伝・天命の誓い（SUIKODEN, PC-98 日文版）

`dekoei.py export suikoden-pc98` 用到的格式。來源原本是 `games/archives/pc98/SUIKODEN_PC98_水滸伝2.FDI`（只有第 2 片）；後來的 `[PC98] 水滸伝～天命の誓い～.ZIP` 有兩片（2026-11-08 移到 `games/archives/to-delete/`，2026-11-09 已刪除；兩片逐 sector 和 `~/game-library/_original/pc98/neo-kobe-2017-11-17/Koei/Suikoden - Tenmei no Chikai/Suikoden - Tenmei no Chikai [FD] [Set 1].zip` 的其中兩片相同；`SUIKODEN_PC98_水滸伝2.FDI` 也移過去了），第 2 片的檔案和它逐 byte 相同，是同一版（`REL.VER`：REL.1A，1989），第 1 片的 `MAIN.EXE` 等也補進 `games/suikoden-pc98/`，每片原樣在 `games/archives/pc98/disks/suikoden-pc98/`。

- `KAO98.DAT`：260 張，64×80 全高、3bpp、每列 24 bytes，順序同 `utils.to_3bpp_indexes`，無壓縮、無組合臉。
- 色盤：8 色數位色盤（每分量 0 或 FF）。第 1 片的 `MAIN.EXE`（MZ 檔頭 0x3000 bytes，DGROUP 段 0x299A）證實：數位色盤設定 0x8E4 用 DS:0xA30E 的標準 `37 15 26 04`；類比色盤 0xEEE 只用在把色 1–7 淡成藍色（0xF）的特效，沒有色表。
- 人物：`SUIDATA1–4.CIM` 從 7124 起 255 筆 × 20 bytes（`koei_games.load_suikoden_pc98_persons`）：
  - +0 姓名 7 bytes Shift-JIS，+7 讀音 9 bytes 半形片假名（不匯出），+16 恆為 0，+17 頭像碼（0 起算），+19 旗標。
  - 4 個劇本的姓名和頭像碼相同，匯出用劇本 1。順序、姓名和 `suikoden-fc` 完全相同。
  - 外字 SJIS 0xEBA0–0xEBAD 的字形在缺少的第 1 片上，字是用 FC 名字和讀音推出來的：鄧郝龔蔣玘鮑俅鄔烕燁褚貹龐戩。X68000 版的 `FONT68K.DAT`（0xEB9F 起 28 字，16×16）證實了這份對照。
- 沒有人物使用的頭像（對照 FC 的特殊頭像）：255 造船所、256 雑貨屋、257 武器屋（施設），258 徽宗皇帝、259 金国太宗（特殊人物）。
- 發行年份：ja.wikipedia 只寫 PC-9801 版 1991 年，沒有月日，待查。
- `nameHistorical`：盧俊儀→盧俊義、馬鱗→馬麟、成喜→成貴、潘功雲→潘巧雲（`SUIKODEN_PC98_NAME_HISTORICAL`，中文 DOS 版是對的）。

### 能力

- 狀態視窗（PC-98 `MAIN.EXE` 0x6190–0x6430）分三欄：体力 腕力 技量 知力／体力上限 腕力経験 技量経験 知力経験／小者 忠義 仁愛 勇気，另有 年齢、忠誠度、人気；一覽表（0x6D8C）另有 身分 性 船 舵。DOS 中文版的用語是 體力 能耐 技能 智慧 士兵 體力上限 能耐經驗… 忠義 仁愛 勇氣 人望。
- 人物記錄 P＝DS:0x44＋22·i（`SUIDATA?.CIM` 檔案 2＋22·i，P+0、P+1 恆為 0，檔案只存 P+2–P+0x15）：
  - +2 年齢、+3 勢力、+4 所在
  - +5 体力、+6 体力上限、+7–9 忠義 仁愛 勇気、+0xA–0xC 腕力 技量 知力
  - +0xD–0xF 経験（能力 100 時顯示「－」）、+0x10 忠誠度、+0x12 u16 人気、+0x14 小者
  - +0x15：bit 6 是船，bits 0–5 是身分（0x5B1A：bit 4 設時索引＝(b&0xF)+22，bit 5 設時＝(b&0x1F)+8，名稱表 DS:0x35BC 34 種）
- 名字記錄：PC-98 +18（DOS +43）是口調（0–4，選應答句組，0x3CF2），+19（DOS +44）的 bit 7 是男、bit 6 是舵。
- 各平台的位置：DOS 與 PC-98 從 4 起、間距 22；PC-88 從 1 起、間距 20，沒有口調；X68000 從 6 起、間距 26，人気是大端序，名字記錄的口調在 +38、旗標在 +39。讀取用 `koei_stats.load_suikoden_stats`，`dekoei.py koei-person suikoden-pc98`。
- ✅ code：視窗 0x6190–0x6430 的 printf 參數、一覽表 0x6D8C。數值和畫面沒有對過截圖。
- ✅ cross：四個平台的能力段相同；DOS 只有 4 人的年齢不同（上青、費保、穆弘、穆春兩兩對調），253 白秀英的身分 DOS 是芸妓、PC-98 是旅芸人。
- 🟡 年齢照原值顯示（0x6312）；人気只在某些身分顯示（0x62BF）。❌ P+0x11（1–15）、旗標 byte 的 bits 0–4。
- 已修正（2026-10-22）：舊 `SUIKODENPerson` 把年齢多加 1、`unknown1` 其實是口調（改名 `tone`），身分沒處理 bit 4 單獨設的情況（印成「不明英雄」），也沒輸出 上限、経験、小者、忠誠度、人気、船。現在都照上面讀；`PERSONS_TABLE/suikoden_persons_s1.csv` 已重新產生（DOS 中文版）。
- ✅ code：身分的中文名稱是 DOS 中文版 `MAIN.EXE` 的 34 個字串（LZEXE 0.91，用 `deark -m lzexe` 解開後在檔案 0x2B3EC，光榮台灣內碼、NUL 分隔，後面接指標表），順序和 `SUIKODENPerson.identities` 逐項相同，包括 6–9 義兄 義弟 死亡 罪犯、30–33 虎 狼 熊 豹。

### 州與戰場地圖（`dekoei.py suikoden battlemap`）

`dekoei.py suikoden battlemap --game-dir ../games/suikoden-pc98 --dos-dir ../games/suikoden-dos --out ../games/suikoden-pc98/extract/battlemap`（`koei_games.render_suikoden_battle_maps`）輸出 `春／夏／秋／冬/NN.png`（NN 是州號 1–49）和 `provinces.csv`（州號、中文名、日文名、城數、相鄰州）。

**州表**（`koei_games.load_suikoden_provinces`）：

- PC-98：`SUIDATA?.CIM` 0x2FC0 起 49 筆 × 21 bytes，和 FC 的州表（`famicom-re:suikoden/docs/ROM_FORMAT.md` §6.1）結構相同：+0 州名 4 bytes（Shift-JIS，不含「州」字），+5 城數，+12 相鄰州 8 bytes（0 起算，0xFF 結尾）。
  - 遊戲讀檔時把整個 `SUIDATA` 讀到 DS:0x42（`MAIN.EXE` 映像 0x513C），所以州表在 DS:0x3002。
  - 外字 0xEB9F 是「鄆」，X68000 版 `FONT68K.DAT` 的第 0 字；0xEBA0 鄧和人名共用。
- DOS 中文版：18600 起 49 筆 × 27 bytes，+0 州名 10 bytes（光榮台灣內碼），+11 城數，+18 相鄰州，排法和 PC-98 一樣，只是名字欄比較長。
- ✅ cross：4 個劇本的州表相同。三版（FC、PC-98、DOS）的相鄰州 49 州都相同。城數只有 13 延安不同：FC、PC-98 是 5，中文版是 4，和戰場圖上延安的城格數一致（FC 筆記已經指出表上 5、圖上 4），看起來是中文版改正了。
  - ✅ cross：中文版與 PC-98 的 `HEXMAP.DAT` 49 州的地形、州歸屬解碼後相同，延安在兩版的戰場圖上都是 4 個城格；其他 48 州的城格數和兩版的表都一致。
  - 城數的用途（PC-98 `MAIN.EXE` 映像位址）：取州表的函式是 0x3326（DS:0x3002＋21×州號），約 20 處讀 +5。多數算「城數 × 5」，和 0x33D2 數的一串鏈結資料比（像每城 5 人的上限，鏈結內容沒確認 🟡）；0x1C880、0x1D7F2 在戰鬥中拿城數和 0x3EF6 數的某方部隊數比，條件沒追（❌）。
- 州名寫法：
  - 中文版：12 太原、16 鳳祥、19 窿德、30 穎州。
  - 日文版與 FC：大原、風翔、隆徳、穎。
  - 《宋史》的寫法是太原、鳳翔、隆德、潁州【推】。
  - 中文版寫兩字州名時不加「州」（真定、大名、開封…），一字的才加。
- +6、+7（中文版 +12、+13）和 +8、+10 的 u16（中文版 +14、+16）是大地圖上的位置（PC-98 ✅ code，見下面「大地圖」）：+8、+10 是把州塗成勢力顏色的起點，+6、+7 是 16×16 標記的左上角。PC-98 的 +8、+10 和 FC 的值相同，中文版的有些不同（中文版的大地圖沒解，沒追中文版的程式）。+20（中文版 +26）是 0–7，三版相同，意義不明。
- 49 筆之後還有 42 bytes（PC-98 0x33C5 起），沒解。

**koei-wiki 匯出**：`dekoei.py places-export suikoden-dos --game-dir ../games/suikoden-dos --out ../export/koei-wiki/places`（`places_export.places_suikoden_dos`，koei-places/1，規格在 `koei-wiki:docs/places-format.mkdn`）。PC-98 版要放在旁邊的 `../suikoden-pc98`。

- 49 州，`level` 是「州」。`name` 用中文版的寫法；`nameJa` 只在 PC-98 的寫法去掉「州」字後仍然不同時才填（大原、風翔、晋、隆徳、済、寿、峡）。
- `cities` 是戰場圖上該州的城格數（兩版相同；13 延安是 4）。州表的城數在遊戲裡的作用還沒確認，所以日文版表上的 5 不匯出（使用者 2026-11-10 決定）。
- 每州 4 筆 `battlemaps`，依季節分（`season`），`role` 是「戰場」，圖檔是 `春／夏／秋／冬/NN.png`。圖是用 PC-98 的 `HEXMAP.DAT` 和圖塊畫的。
- 大地圖 `world/MAP98.png`（344×272）是 PC-98 版的（中文版 `MAPIBM.DAT` 沒解）。`pos` 取日文版州表的 +8、+10，換成這張圖上的像素（x 照原值，y＝2 × 值 − 16），`w`、`h` 是 344、272（✅ code，2026-11-10 起；之前取中文版 +14、+16、標 `uncertain`）。

| 州 | 中文版 | 日文版 | 城數 | 相鄰州 |
|---:|---|---|---:|---|
| 1 | 嵐州 | 嵐 | 2 | 2 代州、12 太原、13 延安 |
| 2 | 代州 | 代 | 3 | 1 嵐州、3 真定、12 太原 |
| 3 | 真定 | 真定 | 3 | 2 代州、4 河間、11 大名、12 太原 |
| 4 | 河間 | 河間 | 4 | 3 真定、5 滄州、6 青州、10 鄆州、11 大名 |
| 5 | 滄州 | 滄 | 3 | 4 河間、6 青州 |
| 6 | 青州 | 青 | 2 | 4 河間、5 滄州、7 登州、8 密州、9 沂州、10 鄆州 |
| 7 | 登州 | 登 | 2 | 6 青州、8 密州 |
| 8 | 密州 | 密 | 3 | 6 青州、7 登州、9 沂州、22 海州 |
| 9 | 沂州 | 沂 | 3 | 6 青州、8 密州、10 鄆州、21 徐州、22 海州 |
| 10 | 鄆州 | 鄆 | 6 | 4 河間、6 青州、9 沂州、11 大名、20 濟州、21 徐州 |
| 11 | 大名 | 大名 | 7 | 3 真定、4 河間、10 鄆州、12 太原、19 窿德、20 濟州、23 開封 |
| 12 | 太原 | 大原 | 3 | 1 嵐州、2 代州、3 真定、11 大名、13 延安、18 晉州、19 窿德 |
| 13 | 延安 | 延安 | 5（中文版 4） | 1 嵐州、12 太原、14 慶州、17 坊州、18 晉州 |
| 14 | 慶州 | 慶 | 2 | 13 延安、15 渭州、17 坊州 |
| 15 | 渭州 | 渭 | 2 | 14 慶州、16 鳳祥、17 坊州 |
| 16 | 鳳祥 | 風翔 | 3 | 15 渭州、17 坊州、26 京兆 |
| 17 | 坊州 | 坊 | 3 | 13 延安、14 慶州、15 渭州、16 鳳祥、18 晉州、25 河中、26 京兆 |
| 18 | 晉州 | 晋 | 2 | 12 太原、13 延安、17 坊州、19 窿德、24 河南、25 河中 |
| 19 | 窿德 | 隆徳 | 4 | 11 大名、12 太原、18 晉州、23 開封、24 河南 |
| 20 | 濟州 | 済 | 6 | 10 鄆州、11 大名、21 徐州、23 開封、30 穎州 |
| 21 | 徐州 | 徐 | 4 | 9 沂州、10 鄆州、20 濟州、22 海州、30 穎州、31 泗州、35 壽州 |
| 22 | 海州 | 海 | 2 | 8 密州、9 沂州、21 徐州、31 泗州、32 泰州 |
| 23 | 開封 | 開封 | 7 | 11 大名、19 窿德、20 濟州、24 河南、28 鄧州、29 蔡州、30 穎州 |
| 24 | 河南 | 河南 | 5 | 18 晉州、19 窿德、23 開封、25 河中、27 商州、28 鄧州 |
| 25 | 河中 | 河中 | 3 | 17 坊州、18 晉州、24 河南、26 京兆、27 商州 |
| 26 | 京兆 | 京兆 | 4 | 16 鳳祥、17 坊州、25 河中、27 商州、40 金州 |
| 27 | 商州 | 商 | 2 | 24 河南、25 河中、26 京兆、28 鄧州、39 房州、40 金州 |
| 28 | 鄧州 | 鄧 | 3 | 23 開封、24 河南、27 商州、29 蔡州、38 襄州、39 房州 |
| 29 | 蔡州 | 蔡 | 3 | 23 開封、30 穎州、28 鄧州、36 光州、37 安州、38 襄州 |
| 30 | 穎州 | 穎 | 2 | 20 濟州、21 徐州、23 開封、29 蔡州、35 壽州、36 光州 |
| 31 | 泗州 | 泗 | 3 | 21 徐州、22 海州、32 泰州、34 宣州、35 壽州、47 舒州、49 歙州 |
| 32 | 泰州 | 泰 | 3 | 22 海州、31 泗州、33 蘇州、34 宣州 |
| 33 | 蘇州 | 蘇 | 2 | 32 泰州、34 宣州 |
| 34 | 宣州 | 宣 | 4 | 31 泗州、32 泰州、33 蘇州、49 歙州 |
| 35 | 壽州 | 寿 | 3 | 21 徐州、30 穎州、31 泗州、36 光州、45 江州、47 舒州 |
| 36 | 光州 | 光 | 2 | 29 蔡州、30 穎州、35 壽州、37 安州、44 岳州、45 江州 |
| 37 | 安州 | 安 | 3 | 29 蔡州、36 光州、38 襄州、43 江陵、44 岳州 |
| 38 | 襄州 | 襄 | 3 | 28 鄧州、29 蔡州、37 安州、39 房州、41 峽州、43 江陵 |
| 39 | 房州 | 房 | 5 | 27 商州、28 鄧州、38 襄州、40 金州、41 峽州 |
| 40 | 金州 | 金 | 2 | 26 京兆、27 商州、39 房州 |
| 41 | 峽州 | 峡 | 3 | 38 襄州、39 房州、42 鼎州、43 江陵 |
| 42 | 鼎州 | 鼎 | 2 | 41 峽州、43 江陵 |
| 43 | 江陵 | 江陵 | 4 | 37 安州、38 襄州、41 峽州、42 鼎州、44 岳州 |
| 44 | 岳州 | 岳 | 2 | 36 光州、37 安州、43 江陵、45 江州、46 洪州 |
| 45 | 江州 | 江 | 5 | 35 壽州、36 光州、44 岳州、46 洪州、47 舒州、48 饒州 |
| 46 | 洪州 | 洪 | 3 | 44 岳州、45 江州、48 饒州 |
| 47 | 舒州 | 舒 | 4 | 31 泗州、35 壽州、45 江州、48 饒州、49 歙州 |
| 48 | 饒州 | 饒 | 3 | 45 江州、46 洪州、47 舒州、49 歙州 |
| 49 | 歙州 | 歙 | 2 | 31 泗州、34 宣州、47 舒州、48 饒州 |

**戰場**：打到哪一州就用那一州的圖。`MAIN.EXE` 0x18646 依序呼叫下面 4 個函式，州號都取自戰鬥記錄（DS:0xA6C2 指向的位置）的第 0 byte：

- 0x18608：讀地形。seek 州號 × 0xA8，讀 168 bytes 到 DS:0xA74A。
- 0x18540：依季節換圖塊。季節由 0x3844 傳回（0–3），平地、森林、山地、高山、湿地、川換成該季的圖塊，冬天的湿地、川都換成結冰（0xA）。結果和 DS:0x8452 的表相同（`SUIKODEN_SEASON_KINDS`），表的內容也和 FC 的 `$BA84` 相同。
- 0x183E6：讀州歸屬。seek 0x2028 ＋ 州號 × 0xA8，讀 168 bytes 到 DS:0xAB68。
- 0x1842A：讀圖塊。依「DS:0x8452［4 × 地形種類 ＋ 季節］」讀 8 種圖塊（各 0x1E0 bytes，從 0x4050 起），再從 0x63F0 起讀部隊等其他圖。

✅ code。

**`HEXMAP.DAT`（PC-98，29298 bytes）**：

| 位置 | 內容 |
|---|---|
| 0x0000 | 地形，49 州 × 168 bytes（14 × 12 格，逐列），值是春天的圖塊號：0 平地、4 森林、8 城、9 湿地、0xB 山地、0xF 川、0x10 海・湖、0x11 高山 |
| 0x2028 | 州歸屬，49 × 168 bytes，州號（0 起算），0xFF 是不屬任何州 |
| 0x4050 | 19 種圖塊 × 0x1E0 bytes：40 × 32 點，每 8 點 3 bytes（3 個 plane，依序是色號的 bit 0、1、2），8 色數位色盤 |
| 0x63F0 | 部隊與標記的圖（0x60、0xF0、0x50、0x80 等大小，0x1842A 讀進來），沒有解 |

- 格的位置（`MAIN.EXE` 0x1B49A）：第 x 欄 y 列畫在 byte 欄 4x＋0x16、第 (16y＋8)×2 行（x 為偶數）或 16y×2 行（x 為奇數）。也就是欄距 32 點、列距 32 點，奇數欄比偶數欄高半格，和 FC 一樣。整張圖 456 × 400。
- 移動到相鄰格的規則在 0x19226（方向 1–6），奇偶欄的處理和上面的排法一致。
- 圖塊四角黑色的部分：匯出時把 19 張都是 0 的點當成六角形外面，不蓋到鄰格。遊戲實際怎麼畫邊緣沒有追，🟡。
- ✅ cross：
  - 地形層和 FC（`famicom-re:suikoden/output/battle_maps.csv`）的 8232 格一一對應：PC-98 的圖塊號 0、4、8、9、0xB、0xF、0x10、0x11 依序就是 FC 的地形 0–7，也就是 FC 春天的圖塊種類。結構相同、參數不同（FC 每格 4 bit，PC-98 存春天的圖塊號）。
  - 州歸屬層 8232 格和 FC byte 相同。
  - 看圖比過嵐州、開封：城的位置與地形和 FC 的圖相同。
- DOS 中文版的 `HEXMAP.DAT`（19902 bytes）：地形每格 4 bit（高 nibble 在前），49 × 84 bytes，值是 0、3、6、7、9、0xC、0xD、0xE，依序對 PC-98 的 8 種地形（解碼後相同）。0x1014 起是州歸屬，8232 bytes，和 PC-98 byte 相同。其後是 EGA 的圖塊，沒有解。
- 地形名稱照 FC 筆記看圖取的，遊戲裡沒有文字。

### 大地圖（`dekoei.py suikoden worldmap`）

`dekoei.py suikoden worldmap --game-dir ../games/suikoden-pc98 --dos-dir ../games/suikoden-dos --out ../games/suikoden-pc98/extract/map`（`koei_games.render_suikoden_world_map`、`unpack_suikoden_picture`、`suikoden_world_points`）輸出：

- `world.png`：大地圖 344×272，和畫面相同。
- `world_provinces.png`：放大 3 倍，在塗色起點旁標「州號 州名」（中文版州名，放法同 `places-label`）。
- `world_provinces.csv`：每州的塗色起點與標記左上角（`world.png` 的像素）。
- `frame.png`、`panel.png`：`MAP98.DAT` 的另外兩張圖。

**`MAP98.DAT`（PC-98，19903 bytes）**：`MAIN.EXE` 0x5230 整個讀進 [0xAC7A] 段（下文位址是 `MAIN.EXE` 去掉 0x3000 bytes 檔頭後的映像位址，DS＝映像 0x299A0）。

| 位置 | 內容 | 誰畫 |
|---|---|---|
| 0x000 | 壓縮圖 80×110，畫在 (8, 16)，看起來是外框 | 0x1FAB4 呼叫 0x4456 |
| 0x3E3 | 壓縮圖 288×96，畫在 (0, 304)，幕簾狀的底圖 | 0x2F40 呼叫 0x4456 |
| 0x937 | 大地圖，不壓縮：0x2B bytes × 0x88 列，每 8 點依序是 B、R、G 三個 plane 的 byte | 0x16B70、0x31D0 呼叫 0x6E5 |

- 大地圖：0x6E5 的參數是 x＝0x24 byte（288 點）、y＝0x10 列、寬 0x2B byte、高 0x88 列，模式 0x8000＝每列畫兩次（0x528 的 `[bp+0xE] & 0x8000`），所以畫面上是 344×272，位置 (288, 16)。三段的長度剛好接滿整個檔（0x3E3、0x937、0x937＋0x2B × 3 × 0x88＝19903）（✅ code）。
- 壓縮圖（0x0F1C，用回呼逐 byte 讀）：u16 寬（點）、u16 高（列），之後逐列，以 4 點（VRAM 的半個 byte）為單位（✅ code）：
  - `0nnn cccc` 後接一個 byte c'：同一個 4 點重複 n＋1 次，B＝c' 低 4 bit、R＝c' 高 4 bit、G＝本 byte 低 4 bit。
  - `10dd nnnn`：從同一列 d＋1 個單位之前複製 n＋1 個單位。
  - `11dd nnnn`：從 d＋1 列之上複製 n＋1 個單位（一列是 160 個單位）。
  - 兩張圖都剛好在下一段的開頭解完。外框與底圖只是照程式解出來看，沒對過畫面【推】。
- 色盤：大地圖只用 3 個 plane，照數位 8 色輸出（色號 bit 0 B、bit 1 R、bit 2 G，和戰場圖相同）。`MAIN.EXE` 0x0EEE 會設類比色盤，但呼叫它的 0x2178E、0x267B8 只做淡入淡出，沒有找到另外的地圖色盤（🟡）。
- 州的位置（PC-98 州表）：
  - +8、+10：0x16B92 呼叫 0x0BDA，從畫面 (x＋0x120, 2y) 以黑色為邊界、用勢力的 3 byte 圖樣（DS:0x8030＋3 × 勢力）塗滿那一州，所以是塗色起點（✅ code）。49 個起點在大地圖上各自落在不同的黑線圍起的區塊（4 連通填色檢查，✅ code+cross）。
  - +6、+7：0x2450 對目前的州（[0xA966]）呼叫 0x6FA，在畫面 (8 × +6, 2 × +7) 畫 16 點寬、8 列（每列畫兩次）的標記（✅ code）。
  - 標上去的州名和圖上遊戲自己畫的州號逐一對得上，是看圖確認的【推】。
- DOS 中文版 `MAPIBM.DAT`（12679 bytes）：開頭是 u16 352、152，看起來是同一種壓縮圖的檔頭，但 EGA 是 4 個 plane，`MAP98.DAT` 的解法套上去色彩不對，沒有解（❌）。

沒解開：

- DOS `MAPIBM.DAT` 的大地圖（EGA 4 plane）。
- 沒有和遊戲畫面截圖比對大地圖、外框、底圖的顏色與位置。
- 州表 +6–11、+20，以及表後面的 42 bytes。
- `HEXMAP.DAT` 0x63F0 以後的部隊圖、DOS 版的圖塊。
- 沒有和遊戲畫面比對過截圖。

### koei-wiki 匯出（人物）

```sh
cd dekoei
../.venv/bin/python dekoei.py persons-export suikoden-dos --game-dir ../games/suikoden-dos --out ../export/koei-wiki/persons --places ../export/koei-wiki/places
```

`wiki_suikoden.py`，koei-persons/1。PC-98 版要放在旁邊的 `../suikoden-pc98`（同地點匯出）。

- 255 人，`id` 同 kaodata `suikoden-dos`。`name` 是中文版的寫法，`nameJa` 是 PC-98 寫法（不同時才填，兩版頭像碼逐筆相同，有 assert）。`reading` 是 PC-98 名字記錄 +7 的半形片假名轉平假名（中文版沒有讀音）。錯字的小說寫法寫在 `notes`（`SUIKODEN_DOS_NAME_HISTORICAL`、`SUIKODEN_PC98_NAME_HISTORICAL`）。
- 標籤用中文版 `MAIN.EXE`（LZEXE＋EXEPACK 解開後 0x359D4–0x35B18）狀態視窗的字：`stats` 是 體力 能耐 技能 智慧 忠義 仁愛 勇氣；`more` 是 年齡、體力上限、能耐／技能／智慧經驗、士兵、人望、身份、性別、船隻、掌舵（後兩項只在有時填 `true`）；`hidden.口調`。頂層取劇本 1。
- 四個劇本的年齡、能力都相同（只有 5 人的體力不同），遊戲不隨劇本加歲，所以不填 `born`。
- `scenarios`：劇本 1–4，年份取中文版劇本選單（0x397D8）：1101 林沖逃亡、1103 宋江殺閻婆惜、1104 宋江吟反詩被捕、1105 晁蓋戰死；沒有月份。
  - `status` 是該劇本的身份（P+0x15 的身分碼，名稱是中文版的 34 個字串）。
  - `location` 是 P+4＋1，就是地點匯出的州 id（高俅 23 開封、魯智深劇本 1 在 15 渭州、宋江劇本 3 在 45 江州）。死亡的不填。
  - `lord` 是 P+3：太尉、太守、官吏的是 0 高俅；好漢的是自己；頭目、強盜、義兄、義弟的是所屬好漢的 id（劇本 3、4 的武松、楊志、張青、孫二娘、曹正、施恩歸 1 魯智深，和小說的二龍山相合）。其他身份（在野的平民、罪犯、死亡）P+3 一律是 1，沒有意義，不填。四個劇本的每個好漢都是自己那一夥的 P+3，✅ cross（和小說對照）。
  - `loyalty` 是 P+0x10 忠誠度，只填有 `lord` 而不是自己的人。
- 沒填：綽號（名字記錄 +7–41 幾乎全是 0，中文版的綽號不在這裡，沒找）、P+0x11。
- 檢查：persons-export 1714 筆、koei-wiki `verify_persons.py suikoden-dos` 4066 筆，0 筆不符（2026-11-14）。

### 下一輪候選（水滸伝的地圖）

- 中文版 `MAPIBM.DAT` — 前置：中文版 `MAIN.EXE`（LZEXE 0.91，`deark -m lzexe` 解開）找到讀這個檔的函式；做法：照 PC-98 0x0F1C 的流程看 EGA 版每個單位存幾個 plane。
- 和截圖比對大地圖的顏色與州標記 — 前置：DOSBox-X／np2 跑 PC-98 版到大地圖畫面；做法：無頭擷取一張，和 `world.png` 逐點比對。

### 負面結論（水滸伝的地圖）

- 用 `MAP98.DAT` 的壓縮圖解法直接解 `MAPIBM.DAT`：能跑完（停在 0x2BF3），但顏色不對，因為 EGA 是 4 個 plane、literal 的格式不同；要先讀中文版的解壓程式才值得重試。

### PC-88 版（`suikoden-pc88`）

來源是 Neo Kobe 2016-02-25 的 `~/game-library/_original/pc88/neo-kobe-2016-02-25/Suikoden/`：Disk A、B 取 `[FD].7z` 主檔，Disk C 取同包 `alts/Suikoden (Disk C) [Alt 1].d88`（FD 主檔的 Disk C 在頭像 190 有 1 byte 和其他各組不同，Set 1 則在頭像 257 尾端被寫進 14 bytes ASCII）。用到的檔案解在 `games/suikoden-pc88/`，`build_suikoden_pc98(pc88=True)`。

- 版本：`REL.DIR`「SUIKODEN TENMEI NO CHIKAI REL.1C Copyright (C) 1988 by KOEI」，Disk A／C 檔案日期 1988-12-13，`KAODATA.DAT` 1988-12-01。ja.wikipedia：PC-8801（SR）1989 年 3 月，是首發。
- 磁碟：80 軌 × 9 × 512 bytes，YDOS 3.0 目錄（0xA00）。Disk A 程式、Disk B 開場與結局、Disk C 資料。
- 色盤：YSHELL.COM 清掉 port 0x32 bit 5，數位 8 色。
- `KAODATA.DAT`（Disk C）：258 張 × 960 bytes，64×40，每 8 點 B、R、G 3 bytes（`pc88.brg_pixels`），200 線，匯出逐列加倍。0–257 和 PC-98 同號同人，255–257 是設施，沒有 PC-98 的 258、259（徽宗皇帝、金国太宗）。
  - 全部是 200 線原生畫：和 PC-98 同一個設計，但沒有一張是 400 線圖抽列；約 13 張到 PC-98 時改過或換色，明顯不同的是 167、172、230、251，252 在 PC-98 是另一張畫（DOS 保留 PC-88 的畫）。DOS 版的 165↔173、201↔240、207↔225 對調，PC-88 和 PC-98 一致。
- 人物 `SUIDATA1–4.CIM`：0x1884 起 255 筆 × 19 bytes（PC-98 的記錄少了 +18 那個 byte，頭像碼同在 +17）。4 個劇本相同，姓名與頭像碼和 PC-98 逐筆相同，`nameHistorical` 也相同。
  - 外字 0xEBA0–0xEBAD 的碼和 PC-98 相同，名字和讀音對得上（鄧元覚 トウゲンカク、寇烕 コウケツ 等）。Disk A 的 `FONT.DAT`（45 字）、`FONT2.DAT`（15 字）是外字字形，但排列和碼不是一一對應（例如「俅」「烕」在 FONT2），沿用 PC-98 的對照。

### X68000 版（`suikoden-x68`）

來源是 Internet Archive `softwarelibrary-x68k` 的 `suikoden_tenmei_no_chikai_1989_x68k`（A、B、C 3 片 DIM），`build_suikoden_pc98(x68=True)`。`games/suikoden-x68/` 放 C 片的 `KAO98.DAT`、`SUIDATA1.CIM`，以及參考用的 A 片 `MAIN.Z`、`REL.VER`、`FONT68K.DAT`。`REL.VER` 寫「Ｘ６８０００版 水滸伝 ｖｅｒ． １．００」。

- 頭像：C 片的 `KAO98.DAT` 和 PC-98 逐 byte 相同，B 片的 `FACE.DAT` 也是同一個檔。
- 色盤：`MAIN.Z`（未壓縮）檔案 0x41102 起是數位文字色盤 `0000 003E 07C0 07FE F800 F83E FFC0 FFFE`（bit 0 藍、bit 1 紅、bit 2 綠），顯示結果和 PC-98 相同，沿用 `SAN2_JP_PALETTE`。
- 人物：`SUIDATA1–4.CIM` 從 0x232C 起 255 筆 × 40 bytes，姓名、讀音同 PC-98，頭像碼在 +37。4 個劇本相同。和 PC-98 只差 210：X68000 寫「成貴」（PC-98 是「成喜」），所以這筆不填 `nameHistorical`（`SUIKODEN_X68_NAME_HISTORICAL`）。
- 外字：`FONT68K.DAT` 是 0xEB9F 起 28 個 16×16 字形（鄆鄧郝龔蔣玘鮑俅鄔烕燁褚貹龐戩鵰矮攔…），人名用的 0xEBA0–0xEBAD 和 PC-98 的推測一致。

## 水滸傳・天命之誓（SUIKODEN, DOS 中文版）

`dekoei.py export suikoden-dos` 用到的格式。來源是 `games/archives/dos/水滸傳_中文版_water.zip` 的 `water/`，解開放在 `games/suikoden-dos/`。

- 版本：英文 DOS 版 Bandit Kings of Ancient China（1989，[Wikipedia](https://en.wikipedia.org/wiki/Bandit_Kings_of_Ancient_China)）的中文化。`KAOIBM.DAT` 等和英文版逐 byte 相同，`SUIDATA?.CIM` 只有 7124–19899 的人名、綽號不同。中文版檔案日期都是 1993-05-06，執行檔只寫「(C)1989 KOEI」。
- `MAIN.EXE` 兩層壓縮（LZEXE 0.91 外層、MS EXEPACK 內層），解開後 DGROUP 段 0x28DE。下文是解開後的映像位址。
- 頭像 `KAOIBM.DAT`：260 張 × 960 bytes，64×40 半高、3bpp，格式同三國志II DOS（`san2_pixels`），沒有組合臉。0x71C3 seek `face × 0x3C0`，0x720E 畫臉，byte 0／1／2 寫到 plane 0／2／1。
- 色盤：EGA mode 0x0E（0x8C7B），int 10h AX=1002 載入 DS:0x665A `00 11 12 … 17`，結果是 `SAN2_PALETTE`。
- 人物 `SUIDATA1–4.CIM`：7124 起 255 筆 × 45 bytes，+0 姓名 7 bytes（光榮台灣內碼），+7 綽號，+42 頭像碼（`koei_games.load_suikoden_dos_persons`）。4 個劇本的姓名和頭像碼相同。`id` 從 0 起算，和 `suikoden-fc`、`suikoden-pc98` 逐筆對齊，頭像碼也和 PC-98 相同（PC-98 是全高重畫）。
- 沒有人物使用的頭像都由 MAIN.EXE 用常數頭像碼畫出：255 造船所（0x11BDB）、256 雜貨店（0x11874）、257 兵工廠（0x11946）、258 徽宗皇帝（0x194E7 等）、259 金國君主（0x19273，遊戲沒有名字，照 FC 寫金國太宗）。設施名用中文版 DS:0x7C9E–0x7CB3 的寫法。
- `nameHistorical`（依小說）：115 黃文譁→黃文燁、127 彭汜→彭玘、133 縻勝→縻貹、154 黨士英→党世英、185 黨士雄→党世雄、180 湯窿→湯隆、217 石遷→時遷、227 梁士傑→梁世傑。2026-11-03 對照 koei.wiki 的人物頁名補上（使用者決定錯字要補）：47 朱同→朱仝、56 諸享→褚亨（日文版褚享）、159 鄭之端→鄭之瑞、191 寇威→寇烕（英文版 Kou Min，日文版寇烕）。不填：65 方腊、66 李云、117 家余慶（字形差異）；75 蔡得章（wiki 寫蔡德章，小說寫得章【推】）。中文版對、日文版錯：35 盧俊義、128 馬麟、210 成貴、254 潘巧雲；朱同、褚享、鄭之端、蔡得章是日文版就這樣寫，日文版沒有填 `nameHistorical`。

## 維新の嵐（ISHIN, PC-98 日文版）

`dekoei.py export ishin-pc98` 用到的格式。來源是 `~/game-library/_original/pc98/[PC98] 維新の嵐.zip`（A、B 兩片 FDI），解到 `games/archives/pc98/disks/ishin-pc98/A`、`B`，合併到 `games/ishin-pc98/`。A 片和之前的 `games/archives/pc98/ISHIN_維新の嵐A.fdi`（沒有檔頭的原始映像）內容相同。ISIN.EXE 的 load image 從檔案 0x3800 起，DGROUP（段 0x3FE4）在 image 0x371C0；下文是 image 位址。

- `KAODAT.DAT`：105 張 48×40、3bpp，每 8 px 3 bytes，byte k＝bit k（0xA4B 依序寫 A800／B000／B800），720 bytes，無壓縮。
  - 匯出時逐列加倍成 48×80（200 線模式，看圖比例判斷，沒有找到設定模式的程式）。
  - 檔案 0x12750 是第 106 張代用頭像（持旗的浪士群）：0x2F2D 對 id 450–713 回傳真，0x4AB1 就改畫 0x2CA 號，也就是這張。匯出歸「一般人物」。
  - 檔案 0x12A20 是 48×40 1bpp 圓角遮罩：0x4BD0 把合成好的臉 AND 它（0x1521），四角變成色號 0。
- 讀臉函式 0x4AB1：讀 `DS:0x9346 + id × 6` 的 6 bytes 臉記錄；byte0＝0xFF 時讀 KAODAT 第 byte1 張，否則合成。
  - 這張表在 exe 裡全是 0，執行時從 `b:shinario.dat` 載入：SHINARIO.DAT 是 3 個劇本 × 0xA770 bytes，每個劇本載到 DS:0x930A，所以臉表在各劇本 +0x3C。
  - id 0–422：105 人用 KAODAT（0–104 各用一次），318 人是合成臉。
  - 31 人在不同劇本的臉不同，其中 29 人是劇本 2、3 換成繼任者（如松前崇広→徳広、戸田忠明→忠恕），名字也跟著換，匯出成另外的人物；伊達慶邦、酒井忠義是同一人換臉，劇本 1 的臉當 `face`，其他放 `expressions`，標「劇本 N」。
- 劇本（ISIN.EXE 檔案 0x3E671 起）：1 新時代の幕開け（嘉永６年）、2 長州の攘夷実行（文久３年）、3 明治維新の戦乱（慶応３年）。
- `MONDAT.DAT` 合成：記錄解碼在 0x3BBC（b0–b3 的高、低 nibble → w0–w7，b4 高 nibble → w8，w9＝((b4 >> 2) & 3) − 2，w10＝(b4 & 3) − 2，w11–w13＝b5 bit 7-6／5-4／3-2 各減 2，w14＝b5 bit 1，w15＝b5 bit 0）。
  - 11 層依序畫（函式表 DS:0x43C、高度 DS:0x424、y DS:0x430）。每個部件是「1bpp 遮罩 h × 6 bytes」接「3 plane 圖 h × 18 bytes」，畫法是 AND 遮罩再 OR 圖。
  - 遮罩為 1 而圖有顏色的點只有兩個（髮型 4、鬍子），都是色號 7，OR 的結果和直接蓋上去一樣，所以匯出時把「遮罩 1、圖 0」當透明，其餘不透明。

| 圖層 | 欄位 | 檔案 offset | 項數 | 高 | y |
|---|---|---|---|---|---|
| 背景（無遮罩，720 bytes） | w0 | 0x0000 | 8 | 40 | 0 |
| 髷（腦後；10＝無） | w1 | 0x1680 | 4 | 40 | 0 |
| 頭／臉底 | w2 | 0x2580 | 10 | 40 | 0 |
| 衣服 | w3 | 0x4B00 | 10 | 40 | 0 |
| 眼 | w4 | 0x7080 | 10 | 6 | 14＋w9 |
| 口 | w5 | 0x7620 | 10 | 6 | 23＋w10 |
| 鼻 | w6 | 0x7BC0 | 10 | 9 | 15＋w11 |
| 眉 | w7 | 0x8430 | 10 | 5 | 10＋w12 |
| 髮型（10＝無） | w8 | 0x88E0 | 10 | 40 | 0 |
| 鬍子（w14 才畫） | — | 0xAE60 | 1 | 20 | 20＋w13 |
| 鉢卷（w15 才畫） | — | 0xB040 | 1 | 40 | 0 |

- 匯出的組合臉：canvas 48×80；有 y 位移的層，每個部件依位移 −2..1 各一項（項號＝部件 × 4＋位移＋2）；鬍子是「無＋4 種位移」，鉢卷是「無、有」，髷和髮型最後一項是「無」。圓角遮罩烘進部件：背景的四角填 0，其他層的四角透明。`face.code` 是 6 bytes 記錄的十六進位，KAODAT 頭像的 `code` 是 `FFnn00000000`。
- 色盤：ISINS.OVL 0x856 只寫數位色盤 port（`color & 7`），預設值 `37 15 26 04`，沒有切類比模式，所以是 8 色數位（每分量 0 或 FF）。
- 人名：ISIN.EXE 檔案 0x42312 姓 7 bytes × 423；名用 SHINARIO.DAT 各劇本 +0x983A 的 9 bytes × 423，ISIN.EXE 0x449F4 那份是載入前的預設值（見「能力」段，`koei_games.load_ishin_pc98_persons`），Shift-JIS＋外字（字形在 USKCG.SYS）：EB9F 恂、EBA0 寛、EBA1 屏、EBA2 佶、EBA3 溥、EBA5 叟、EBA6 孚、EBA7 訥、EBA8 阮、EBA9 煕、EBAA 襄、EBAB 奎、EBAC 霖、EBAD 謨（用人名對過：星恂太郎、大久保忠寛、河合屏山、北添佶磨、黒田長溥、鍋島閑叟、元田永孚、大橋訥庵、箕作阮甫、近衛忠煕、新島襄、松本奎堂、黙霖、川路聖謨）。id 0–422 是史實人物（0x2F12）。
  - `USKCG.SYS` 其實定義了 25 字（+0 是筆數，0x22 起每筆 34 bytes：JIS 碼 2 bytes（低位在前，從 0x7621 起）＋16×16 點陣），即 SJIS EB9F–EBB7；人名只用到上面 14 字，其餘是訊息用的耆、攘、誅、揆、忱、韶、咸、梟，EBB7 是開場當圖形用的實心方塊，EBA4、EBB4 未用（中文化專案 `~/works/ishin-zh` 查出）。
- 中文化：`~/works/ishin-zh`（另一個 repo）以本版做繁體中文化與網頁版，磁片版面、訊息位置與拼接方式記在該 repo 的 `docs/format-notes.md`。
- PC-9801 版 1988 年 6 月（ja.wikipedia）。

#### 能力（`dekoei.py koei-person ishin-pc98`）

- SHINARIO.DAT 每個劇本的 +0xAC8 是遊戲資料段（段 0x2690）的 offset 0。人物有兩張表，狀態視窗（ISINS.OVL 0xF1BF）兩張都讀：
  - 0x606:0xD3（image 0x6133）：0x3A35＋id × 28（id ≤ 450），也就是劇本 +0x44FD。
    - +1 u16 身分碼：高 4 bit 是大類，選 0x622:0x80A 的解碼函式（DS:0x57E 的函式表）。解出的序號查 DS:0x6790 的名稱表（40 種，`koei_stats.ISHIN_PC98_RANKS`）。
      - 1：低 byte 0 是朝廷（天皇、大臣、議奏、朝臣，次 4 bit 選），0x46 是幕府（将軍、老中、奉行、幕臣），1–0x56 是藩（藩主、家老、重臣、藩士，前面接藩名），0x5D–0x65 是諸隊（新撰組、奇兵隊…，DS:0x6578）。
      - 2：学者（低 byte 1–5 是 儒、国、蘭、兵、砲学者）。3：女性類（女性、女房、女官、将軍家御台所、勤王家、天理教々祖、おいらん）。4：仁侠親分／子分。5：商人。6：総領事、外交官、艦隊司令、外国商人。7：僧、神官、金光教々租。8：志士。9：町人。
      - 藩名在劇本 +0x95D9，每筆 7 bytes，66 藩之後接國名。藩 n 是第 n − 1 筆，對法是看人判斷的：坂本龍馬 0x1336＝土佐藩士、西郷隆盛 0x1342＝薩摩藩士、吉田松陰 0x1338＝長州藩士。程式是查藩記錄 +3 再查 DS:0x9DCB＋7 × n（0x622:0x21E），這中間差 1 的原因沒追（🟡）。
      - ✅ cross：坂本龍馬在劇本 2 是浪人（1862 年脫藩），勝海舟在劇本 2 是奉行。
    - +3 年齢（0x1627:0x34E）。
    - +0xC 剣道（上限 100），+0xD 学力、+0xE 魅力（上限 200），+0x12 戦闘経験（上限 100）。
    - +0x10 u16 レベル。
    - +0x16–0x19 照數值判斷是 尊王、公議、佐幕、攘夷：前三項加起來一律是 100，是国体思想的比重，第四項是国外思想（開国 0）。字串在 DS:0x15C6 起，依序是 尊王、公議、佐幕、攘夷、開国。沒有找到直接讀這四格的程式（🟡）。
  - 0x606:0xF（image 0x606F）：0x537＋id × 19，也就是劇本 +0xFFF。+0xF 武力，+0x10 體力、+0x11 原体力（上限 200）。
- ✅ code：ISINS.OVL 0xF2F0–0xF460 畫各項的條，上限分別是 200 與 100（0xC8、0x64）。✅ cross：
  - 剣道最高的是沖田総司、千葉周作（100）。
  - 学力最高的是佐久間象山、横井小楠（193）。
  - 孝明天皇是尊王 100、攘夷 95，徳川慶喜是佐幕 100。
- 年齢在劇本 1→2→3 依序加 5、加 4，比較像 1858→1863→1867，不像「嘉永６年」（1853）。劇本 1 的實際年代沒追。少數人物的年齢和史實差很多，例如徳川慶喜在劇本 1 是 29 歲。
- 名字：姓取 ISIN.EXE 的表，名取劇本 +0x983A（9 bytes × 423）。名字由 0x622:0x198 組成，讀的是 ISIN.EXE 的姓（DS:0x7952）和名（DS:0xA034），DS:0xA034 這張名表載入劇本時會被劇本的名表蓋掉（推論，沒追讀檔的程式，🟡）。
  - 劇本的名和 ISIN.EXE 的預設值不同的有：劇本 1 有 4 人（由利公正、大河内信古、藤堂平助、永倉新八），劇本 2 有 30 人、劇本 3 有 34 人，大多是藩主換成繼任者（松平定敬、細川韶邦、小笠原忠忱等），劇本 2、3 的 280 是「明冶天皇」（原文如此）。
  - `ishin-pc98` 的 kaodata 匯出也用劇本的名（2026-11-06 改，使用者決定）。劇本 2、3 換成繼任者的 33 人另成人物，接在 423 號之後，臉取他第一次出現的劇本；同一人換臉的只剩伊達慶邦、酒井忠義，放 `expressions`；「明冶天皇」併回明治天皇（`ISHIN_PC98_SAME_PERSON`）。
- 外字 EBAE 耆（伯耆）、EBB2 忱、EBB3 韶是照劇本裡的名字判斷的，和上面 USKCG.SYS 的順序（耆、攘、誅、揆、忱、韶）一致。
- 沒做：同志數（0x1627:0x30D）、id 423 以後的一般人物。所在見下段「koei-wiki 匯出」。

#### koei-wiki 匯出（`persons-export ishin-pc98`）

`dekoei.py persons-export ishin-pc98 --game-dir ../games/ishin-pc98 --out ../export/koei-wiki/persons`，讀取在 `wiki_ishin.py`。456 人，id 和 kaodata `ishin-pc98` 相同（0–422 史實人物，423 起是劇本 2、3 接手記錄的繼任者，順序照 `build_ishin_pc98`，逐筆對過名字）。

- `familyName`：ISIN.EXE 的姓表（姓、名分開存）；姓欄就是全名的（スネル等）不填。沒有讀音。
- `stats`：武力、剣道、学力、魅力、原体力（上段「能力」的兩張表）。`more`：年齢、戦闘経験、レベル、身分（遊戲寫法，如「土佐藩士」）、藩（身分所屬的藩，取劇本藩名表的寫法，如「土佐」；幕府、朝廷的人寫「幕府」「朝廷」，藩主、将軍、天皇本人也填；諸隊、浪人、學者等沒有；koei-wiki 2026-11-14 要求，一覽頁依它分組；363 人有值）、尊王、公議、佐幕、攘夷（思想四格是看數值判斷的，標 `uncertain`）。頂層取這個人第一次在地圖上的劇本，不是劇本 1 時寫在 `notes`。
- `scenarios`：三個劇本（1858.1、1863.5、1867.11，ISIN.EXE 0x3E672 的字串）。每人只列用他名字的劇本（繼任者只有劇本 2、3）。
  - `status` 是該劇本的身分原文（土佐藩士、幕臣、海援隊、浪人…），藩名就在裡面。
  - `lord`：藩主、家老、重臣、藩士取同藩在地圖上的藩主；幕府的取将軍，朝廷的取天皇。每個劇本每藩剛好一個藩主在地圖上（66 藩）。諸隊、浪人、學者等沒有 `lord`。
  - 28 bytes 記錄 +0x1B 的 bit 6 看起來是「劇本開始時在地圖上」（🟡，從值判斷：島津斉彬、吉田松陰在劇本 2 起是 0，高杉晋作只有劇本 2 是 1）。不在的劇本寫 `status`「未登場」（第一次登場前）或「不在」（登場過之後，推定已死，寫在 `notes`），都是使用者 2026-11-14 的規則（遊戲沒有稱呼；原本寫「不在」與「死亡」並標 `uncertain`，koei-wiki 要求拿掉）；何時登場沒追，所以沒有 `debut`。從不在地圖上的有 9 人（藤田東湖、阿部正弘、吉村寅太郎、榎本武揚等），之後是否由事件登場沒追，所以不用規格的「未登場」（要填 `debut`）。
  - 各劇本的能力放 `scenarios[].stats`。
  - `location`：19 bytes 記錄 +0 的 u16 是所在的地圖節點，查節點表得到場所（下段「地點」的 id）。在地圖上的 1051 筆全部有值。抽查：坂本龍馬 高知→江戸→京都、勝海舟 江戸→長崎→江戸、近藤勇 劇本 2、3 京都、大村益次郎劇本 1 在宇和島（1858 年仕宇和島藩）、グラバー 長崎，都和史實相合（✅ cross，史實）。28 bytes 記錄 +4 也是節點號，看值像是根據地（大村益次郎是萩），沒匯出。
- 沒填：同志數、讀音、生年。
- 檢查：`persons-export` 2786 筆、0 筆不符；koei-wiki `scripts/verify_persons.py ishin-pc98` 5880 筆、0 筆不符（2026-11-14，加上 location 後）。

#### koei-wiki 地點（`places-export ishin-pc98`）

`dekoei.py places-export ishin-pc98 --game-dir ../games/ishin-pc98 --out ../export/koei-wiki/places`，讀取在 `wiki_ishin.places`。96 個場所，id 是場所名表的序號。

- 場所名表：ISIN.EXE 檔案 0x42072（DGROUP 0x76B2），7 bytes × 96：87 個國（前 66 個和劇本藩名表的 66 藩同序，名字是國名，如陸奥＝弘前藩、防長＝長州藩），接 9 個町（江戸 京都 大坂 萩 高知 下関 鹿児島 長崎 横浜）。表頭寫「場所名」（ISIN.EXE 0x3E23D 等）。
- 地圖節點表：ISIN.EXE 檔案 0x29F9A，6 bytes × 402（節點 0 空）。+0 是場所號＋1，+1 是地區（DS 的「東北１ 東北２ 関東 信越 近畿 中四国 九州」，檔案 0x3AD9A，表頭寫「地区」），+3／+4 看值是六角格的列、行（國的節點行 0–28 由北往南；町的節點行從 101 起，是町內地圖），+2、+5 沒解。依據：用 56 個在地圖上的藩主所在節點搜出來的（節點 +0＝藩號＋1 全部相符），人物所在的抽查也都對（上段）。🟡 code（找到表，讀表的程式沒追）。
- 欄位：
  - `level`：國寫「国」（取檔名 KUNIMATI＝国町，遊戲畫面上的稱呼沒找到），町寫「町」（訊息「町に入りますか？」），都標 `uncertain`。
  - `region`：節點的地區。每個場所的節點都在同一個地區。町的地區和實際位置不合（江戸、横浜在東北２，京都、大坂在信越），原因沒追，町的 `region` 標 `uncertain`。
  - `game.藩`：前 66 國的藩名（劇本藩名表，三個劇本相同）。
  - `scenarios`：前 66 國每個劇本的 `lord`＝那個藩在地圖上的藩主（同人物的 `lord`）。沒有藩的國與町不填。
- 沒填：`adjacent`（節點的六角格怎麼相鄰沒追）、`pos`、大地圖（MAPPNT.DAT、HEXDAT.DAT、KUNIMATI.DAT、SMAP.PAC 沒解）、石高與兵數等藩的數值。
- 檢查：`places-export` 0 筆（沒有相鄰、位置可查）；koei-wiki `scripts/verify_sanguo_places.py ishin-pc98` 682 筆、0 筆不符（2026-11-14）。

### PC-88 版（`ishin-pc88`）

`dekoei.py export ishin-pc88` 用到的差異（`build_ishin_pc98(pc88=True)`）。PC-88 版 1989 年 4 月（ja.wikipedia，在 PC-98 之後）。

- 來源：Neo Kobe 2016-02-25 的 `~/game-library/_original/pc88/neo-kobe-2016-02-25/Ishin no Arashi/`，用「[FD]」的 Disk A–C。「[FD] [Set 1]」只有 A 片的 `EXT.DAT`、`MAIN.OVL` 不同。
- 磁碟：每軌 9 × 512 bytes，Disk A 是 YDOS 3.0，B、C 是 FAT12。檔案日期都是 1989-04-10，沒有版本字串。
- `games/ishin-pc88/` 放 Disk A 的 `KAODAT.DAT`、`MONDAT.DAT`、`YKAO.DAT`、`MAIN.COM`、`YCSUB.OVL`（參考用），Disk C 的 `SHINARIO.OVL`。
- `KAODAT.DAT`：98 張，格式同 PC-98（48×40，byte k＝bit k），檔尾沒有圓角遮罩，`MAIN.COM` 0x37C9 讀進來直接畫，所以不套遮罩。
  - 0–94 張和 PC-98 的逐 byte 相同但順序不同；94 是一般人物（id ≥ 0xD0 一律用 KAODAT 0x10860）；95–97 是 PC-98 沒有的臉。
- `YKAO.DAT`：4 張同格式的女性臉，`YCSUB.OVL` 的遊郭（「何番の娘にしますか」）用，匯出成 98–101，分類「遊郭の娘」。
- `MONDAT.DAT` 和 PC-98 逐 byte 相同。臉記錄是 5 bytes（`MAIN.COM` 0x3575）：w0–w7 是 b0–b3 的 nibble，w8＝b4 >> 4，鬍子＝b4 bit 3，鉢卷＝b4 bit 2，沒有 y 位移。匯出時換成 y 位移 0 的 PC-98 記錄（`ishin_pc88_record`）共用同一套部件，`face.code` 是 5 bytes 的十六進位，KAODAT 頭像的 `code` 是 `FFnn000000`。
- 人物：`SHINARIO.OVL` 有 2 個劇本，名 9 bytes 在 0xA90／0x3490，臉記錄 5 bytes 在 0x275F／0x515F（兩劇本相同）；姓 7 bytes 在 `MAIN.COM` 0x47AB（`koei_games.load_ishin_pc88_persons`）。id 0–200 是史實人物，外字同 PC-98。
  - 劇本 2 有兩筆換成繼任者：53 松平春猷 → 松平定敬、63 浅野斎粛 → 浅野長訓，用同一張臉，匯出成另外的人物 201、202。
  - id 順序和 PC-98 不同。201 人中 179 人的名字和 PC-98 相同；徳川慶勝、副島種臣、村田新八在 PC-98 寫成徳川義勝、福島種臣、村田信八（ishin-pc98 填 `nameHistorical`，`ISHIN_PC98_NAME_HISTORICAL`），其他 17 人（大島高任、山本覚馬等）PC-98 沒有。PC-88 劇本 2 的繼任者松平定敬、浅野長訓在 PC-98 也是另外的人物。
- 色盤：數位 8 色（同 `ISHIN_PC98_PALETTE`，palette id `pc88`）。

### X68000 版（`ishin-x68`）

`dekoei.py export ishin-x68` 用 `build_ishin_x68`。

- 來源：Internet Archive `ishin_no_arashi_1990_koei_disk_x68k`（`~/game-library/_original/x68/ia-softwarelibrary/`，A、B、C 3 片）。`games/ishin-x68/` 放 A 片的 `ISINMAIN.Z`，C 片的 `KAODAT.DAT`、`MONDAT.DAT`、`SDATA1.DAT`、`SDATA2.DAT`、`YKAO.DAT`。
- `ISINMAIN.Z` 沒有壓縮，執行位址＝檔案位址＋0x514DE，下文是執行位址。
- 人物是 PC-88 版的：姓在檔案 0x4548（和 PC-88 `MAIN.COM` 0x47AB 逐 byte 相同），名在 `SDATA1/2.DAT` 0x1DBE，臉記錄 5 bytes 在 0x2B18（兩個劇本相同）（`koei_games.load_ishin_x68_persons`）。id 和名字同 `ishin-pc88`，劇本 2 的繼任者也一樣匯出成 201、202。
- `KAODAT.DAT`：96 張重畫的 48×80 全高頭像（1440 bytes，byte k＝plane k），順序同 PC-88 的 0–93；94 是芹沢鴨（PC-88 用組合臉），95 是一般人物（0x7F9B6：id ≥ 0xD0）。PC-88 的 95–97（池内蔵太、新宮馬之助、近藤長次郎）在 X68000 改用組合臉。
- C 片也有 `YKAO.DAT`（和 PC-88 逐 byte 相同，4 張 48×40），但 `ISINMAIN.Z` 沒有開它（沒有這個檔名字串），X68000 上的顯示方式無從確定。照使用者決定仍匯出：格式同 `ishin-pc88`（byte k＝plane k，逐列加倍成 48×80），色盤用 X68000 的數位 8 色，成為頭像 96–99，分類「遊郭の娘」，不命名。
- 組合臉（0x7F5EE）：0x7F52C 把 5 bytes 拆成 w0–w9 十個 nibble，w9 &= 7，髷＝b4 bit 3。先把背景（`MONDAT.DAT` w0 × 0x5A0，48×80）放進 48×80 的緩衝，之後每層「AND 1bpp 遮罩（每列 6 bytes，作用在 3 個平面）、OR 圖（每列 18 bytes）」；只有遮罩的層畫出色號 0 的線。部件位置寫在 0x659C2 起的表：

| 圖層 | 欄位 | 遮罩 | 圖 | 項數 | 高 | y |
|---|---|---|---|---|---|---|
| 背景 | w0 | — | 0x0000 + w × 0x5A0 | 6 | 80 | 0 |
| 頭 | w1 | 0x21C0 + w × 0x780 | 遮罩後 0x1E0 | 6 | 80 | 0 |
| 衣 | w2 | 0x4EC0（共用） | 0x4F98 + w × 0x288 | 6 | 36 | 44 |
| 羽織（10＝無） | w3 | 0x5EC8 + w × 0x3C0 | 遮罩後 0xF0 | 10 | 40 | 40 |
| 髮型（6＝無） | w4 | 0x8448 + w × 0x4C8 | 遮罩後 0x132 | 6 | 51 | 0 |
| 眉 | w5 | 0xA0F8（共用） | 0xA116 + w × 0x5A | 6 | 5 | 24 |
| 鼻 | w6 | 0xA332（共用） | 0xA37A + w × 0xD8 | 6 | 12 | 31 |
| 眼 | w7 | 0xA88A + w × 30 | — | 6 | 5 | 29 |
| 口 | w8 | 0xA93E + w × 36 | — | 6 | 6 | 44 |
| 鬍（3＝無） | w9 | 0xAA16 + w × 0x96 | — | 3 | 25 | 33 |
| 髷（b4 bit 3） | — | 0xABD8 | 0xAC44 | 1 | 遮罩 18、圖 12 | 0 |

  - 髷的圖其實有 18 列（檔尾剛好用完），但程式只 OR 前 0xD8 bytes（12 列），匯出照程式。
  - 遮罩為 1 而圖有顏色的點只有羽織 9 的 4 點，都是色號 7，所以匯出時「遮罩 1、圖 0」透明，其餘不透明。匯出的 108 張組合臉和直接照程式合成的結果逐點相同。
- 畫到文字 VRAM 平面 0–2（0x9D6EE，byte k＝plane k），文字色盤（0x571D6）的 0–7 是數位 8 色（`ISHIN_PC98_PALETTE`，palette id `x68`）。

## ロイヤルブラッド（ROYAL, PC-98 日文版）

`dekoei.py export royal-pc98` 用到的格式。來源是 `~/game-library/_original/pc98/[PC98] [光栄] ロイヤルブラッド(FDI).zip`（A、B 片和使用者片），每片解到 `games/archives/pc98/disks/royal-pc98/A`、`B`、`user`，A、B 合併到 `games/royal-pc98/`。使用者片的 KAODATA.DAT／SENFIEDA.DAT 和 B 片相同。

- `MAIN.EXE` 的 header 是 0x3200 bytes；DS 在檔案 0x27270（0x5B0 用 `index × 13 + 0xE52` 找名字）。下文程式位址是去掉 header 後的 image 位址。
- `KAODATA.DAT`：91 張 64×80，每 8 px 3 bytes，byte k＝plane k（`genpei.decode_planar`），1920 bytes，無壓縮（OPEN.EXE image 0x12D9 以 idx × 0x780 讀，0x29B0 依序寫 A800／B000／B800；MAIN.EXE 是 0x8D06）。順序和 `royal-fc` 的 91 張逐張相同：0–63 君主、64–67 相談役、68–90 部隊／魔獸／召喚。
  - 0x59C：君主的頭像號就是君主序號。相談役是 0x40＋n（0x6A4C、0x10890），部隊是 0x44＋種類（0x8460）。
- 名字是半形片假名：DS:0xE52 君主 64 筆 × 13 bytes（名字 10 bytes），DS:0x13CC 部隊 23 筆 × 16 bytes（`koei_games.load_royal_pc98_names`）。兩者都和 FC 版逐筆相同。
- 色盤：遊戲啟動時問是否用類比 RGB（旗標 DS:0x1942）。
  - 類比：0xE74 把 DS:0x189E 的 8 色淡入（0xDAA），每色 B、R、G 各 4 bit，由 0x2300 寫 port 0xAE／0xAC／0xAA。匯出時 ×17，當預設色盤。
  - 數位：標準 8 色，匯出成第二個色盤。
  - OPEN.EXE DS:0x8D6C 的色盤是開場用的染色，套到頭像會變綠。
- PC-9801 版 1991-12-21（ja.wikipedia）。

### PC-88 版（`royal-pc88`）

`dekoei.py export royal-pc88` 用到的差異（`build_royal_pc98(pc88=True)`）。

- 來源：Neo Kobe 2016-02-25 的 `Royal Blood [FD].7z`（只有這一組）。Disk A 是 YDOS 3.0，B、C 是 FAT12。
- `games/royal-pc88/` 放 Disk C 的 `KAODATA.DAT`、Disk A 的 `SNDATA1.CIM`，以及參考用的 `MAIN.COM`、`ROYAL.VER`。
- 版本：`ROYAL.VER` 寫「ロイアル・ブラッド For PC-8801SR TYPE - B Ver 1.1 Rel 1.0 09/11/1991」（`ROYAL_B.VER` 是 Ver 1.0 Rel 1.0 09/09/1991）。
- 頭像：`KAODATA.DAT` 是 91 張 64×40、每 8 點 B、R、G 3 bytes，960 bytes，不壓縮。匯出用 `pc88.brg_pixels`，逐列加倍成 64×80。
  - 順序和 PC-98 相同，但沒有一張逐 byte 相同：0–67、83–88 是同一張圖改成 200 線，68–82（部隊）和 89、90 是另外畫的。
- 名字：`SNDATA1.CIM` 就是 PC-98 DS:0x6EB 起的資料，君主在檔案 0x767、部隊在 0xCE1（`koei_games.load_royal_pc98_names(..., pc88=True)`），和 PC-98 逐筆相同。
- 色盤：平時是數位 8 色（`ROYAL_PC98_DIGITAL`，palette id `pc88`）；`MAIN.COM` 只在畫面切換淡入時暫用類比色。

### X68000 版（`royal-x68`）

`dekoei.py export royal-x68` 用 `build_royal_pc98(x68=True)`。

- 來源：Internet Archive `softwarelibrary-x68k` 的 `royal_blood_19xx_koei_disk_1_o_x68k`（A、B、C 3 片 DIM）。`games/royal-x68/` 放 A 片的 `MAIN.Z`、`VERSION`，C 片的 `KAODATA.DAT`，以及參考用的 B 片 `WKAODATA.DAT`。`VERSION` 寫「ロイヤルブラッド 1992.3.4 ver1.1」。
- 頭像：`KAODATA.DAT` 和 PC-98 逐 byte 相同。`WKAODATA.DAT` 是 6 張 64×80，等於 KAODATA 的第 83–88 張（放在 B 片給片尾用），不另外匯出。
- 名字：`MAIN.Z` 沒有壓縮，是同一份資料加上 68000 的補位：君主從檔案 0x249C0 起每筆 16 bytes，部隊從 0x25018 起每筆 20 bytes（`koei_games.load_royal_x68_names`），和 PC-98 逐筆相同。
- 色盤：檔案 0x2DEBC 起是 8 組 B、R、G 各 5 bit 的類比色，是 PC-98 那組 4 bit 值 v 換成 2v＋1，換成 8 bit 用 v << 3 | v >> 2；後面接一組較暗的版本和數位 8 色。和 PC-98 一樣匯出類比與數位兩組。

## 提督の決断（TK, PC-98 日文版）

`dekoei.py export tk-pc98` 用到的格式。來源是 `~/game-library/_original/pc98/[PC98] 提督の決断.zip`（兩片 FDI），解到 `games/archives/pc98/disks/tk-pc98/1`、`2`，合併到 `games/tk-pc98/`。

- `RENMAIN.EXE` 的 header 是 0x4600 bytes，DGROUP 是段 0x3852（檔案 0x3CB20）。下文程式位址是去掉 header 後的 image 位址。
- `RENPIC.DAT`：42 張 40×48，每 8 px 3 bytes，byte k＝plane k（`genpei.decode_planar`），720 bytes，無壓縮。
  - 0xE644 讀一張：參數 ≤ 1 時讀 0x7080＋n × 720（第 40、41 張），否則參數是提督記錄的位址，讀 (參數 − DS:0xC6FC) / 19 × 720。0x14dd:0x115 以寬 5 bytes、48 列畫出。
  - 第 40、41 張：0x19F34 以陣營（[0x8360]，0 日本、1 盟軍）畫，旁邊印「陸軍参謀」（2F72:0009），是統合作戰會議的陸軍代表。
  - 第 42 張的位置（0x7620 起 288 bytes）是 0x12410 等讀的 32×24 小圖示，不是頭像。
- `SUGATA.DAT`（DS:0x2A3A 的 dword 位移表，0xE58A 讀）是艦影，`RENPACK.DAT` 是 640×400 的大圖，都沒有頭像。
- 名字：DS:0xC6FC 起 40 筆 × 19 bytes（`koei_games.load_tk_pc98_names`），0–19 日本、20–39 盟軍。順序和 `tk-sfc` 相同，但 16、19 是吉川　潔、友長丈一（SFC 是草鹿龍之介、木村昌福），31 是「ﾄﾞｰﾙﾏﾝ」（SFC 是 C.ドールマン）。
  - 盟軍是半形片假名，轉成全形。宇垣纒的「纒」是外字 EBA4（USKCG.SYS 的 JIS 0x7626），前面墊兩個半形空白，和「吉川　潔」一樣當一個全形空白。
- 色盤：程式裡沒有寫色盤 port 0xA8–0xAE 的指令（只有 GDC 的 0xA2、0xA6），用的是預設的 8 色數位色盤。
- PC-9801 版 1989-09-21（ja.wikipedia）。

### PC-88 版（`tk-pc88`）

`dekoei.py export tk-pc88` 用到的差異（`build_tk_pc98(pc88=True)`）。

- 來源：Neo Kobe 2016-02-25 的 `~/game-library/_original/pc88/neo-kobe-2016-02-25/Teitoku no Ketsudan/`，用 `[FD]` 的 Disk A–D 主組。
  - Alt 1 的 Disk A/B 只有 `SETTEI.CIM`、`RENMAIN.OVL` 不同（程式修正，沒看）。
- 磁碟：每軌 9 × 512 bytes。Disk A 是 YDOS 3.0，B、C 是 FAT12。
- `games/tk-pc88/` 放 Disk B 的 `KAO.DAT`、Disk A 的 `YSHELL.COM`，以及參考用的 `KOEI.C`、`HYOUSHI.CIM`。
- 版本：`KOEI.C` 寫 `Copyright KOEI 1990. / Ver. 1.00 rel. 1`，檔案日期 1990-08～10-22。
- 頭像：`KAO.DAT`（由 `HYOUSHI.CIM` 開啟）是 42 張 48×32、每 8 點 B、R、G 3 bytes，不壓縮。匯出用 `pc88.brg_pixels`，逐列加倍成 48×64。
  - 人物、順序和 PC-98 `RENPIC.DAT` 相同（40、41 也是陸軍参謀），但是另外以 200 線重畫的，不是同一份圖。
- 色盤：數位 8 色（同 PC-98 的 `TK_PC98_PALETTE`，palette id `pc88`）。沒有找到寫入類比色盤的程式。
  - 平面順序 B、R、G 是和 PC-98 比對色差最小的排法，和其他 PC-88 作品一致，沒有追畫圖程式。
- 名字：`YSHELL.COM` 0x7849 起 40 × 19 bytes，和 PC-98 `RENMAIN.EXE` DS:0xC6FC 逐 byte 相同（`load_tk_pc98_names(..., TK_PC88_ADMIRALS)`），`id` 一致。外字 EBA4 照 PC-98 當「纒」，PC-88 的字形沒有確認。

### X68000 版（`tk-x68`）

`dekoei.py export tk-x68` 用到的差異（`build_tk_pc98(x68=True)`）。

- 來源：Internet Archive `teitoku_no_ketsudan_1990_koei_x68k`（`~/game-library/_original/x68/ia-softwarelibrary/`）。Disk A 的 `RENMAIN.Z`、Disk C 的 `RENPIC.DAT` 放在 `games/tk-x68/`。
- `RENMAIN.Z` 沒有壓縮，映像起點是 0x54FDE（由 `jsr` 目標推得），下文是執行位址。
- 頭像：`RENPIC.DAT` 是 42 張 56×72、每 8 px 3 bytes，1512 bytes，後面接 288 bytes（同 PC-98 的小圖示）。人物、順序和 PC-98 相同（40、41 是陸軍参謀），但是另外重畫的大圖。
  - 0x645A0：(記錄 − 0xB41B6) / 20 × 0x5E8 讀一張，0x86A84 以 7 bytes × 72 列寫到文字 VRAM 平面 0–2（E00000／E20000／E40000），byte k＝plane k，平面 3 寫 0。
- 色盤：文字色盤 E82200 由 0x86BAA 從 0x96FB6／0x9750C 設定，色號 0–7 是數位 8 色，和 PC-98 的 `TK_PC98_PALETTE` 相同（palette id `x68`）。
- 名字：0x5F1D8（檔案位址）起 40 × 20 bytes，內容和 PC-98 的 19 bytes 記錄相同（`load_tk_pc98_names(..., TK_X68_ADMIRALS, 20)`），宇垣纒也是外字 EBA4，`GAIJI.DAT` 的字形沒有確認。

## 提督の決断II（TK2, PC-98 日文版）

`dekoei.py export tk2-pc98` 用到的格式。來源是 `~/game-library/_original/pc98/[PC98] 提督の決断２.zip`（7 片 FDI：S 系統、A、B 資料、O 開場、E 結尾、U 使用者、K 硬碟起動；zip 裡的檔名是 Shift-JIS），每片解到 `games/archives/pc98/disks/tk2-pc98/<片>`，S、A、B 合併到 `games/tk2-pc98/`，另加 U 片的 SCE.TK2。U 片的 MAIN.EXE 和 S 片相同。

- `MAIN.EXE` 的 header 是 0xD600 bytes，DGROUP 是段 0x5E15。下文程式位址是去掉 header 後的 image 位址。
- `KAO.TK2`：103 張 48×64，每 8 px 3 bytes，byte k＝plane k（`genpei.decode_planar`），1152 bytes，無壓縮。0x2A9D2（另一份在 0x3577C）以 `n × 0x480` 讀第 n 張；KAIGI.EXE（0x1C620）、END.EXE（0x3286）也讀這個檔。
- 頭像號：
  - 提督（`ARDATA`，每劇本 60 筆 × 17 bytes，0–29 日本、30–59 盟軍）：提督序號＋（盟軍 15）（0x2F30D 取 `序號 × 0x11` 的記錄，0x2F33D 加 15）。
  - 陸軍將領（`GRDATA`，每劇本 30 筆 × 18 bytes，0–14 日本、15–29 盟軍）：30＋序號＋（盟軍 15）（0x1F42D）。所以每邊都是「提督 30、將領 15」共 45 張連號，KAIGI.EXE 0x989B 也是「盟軍加 45」。
  - 元首（`SJDATA`，每劇本 9 筆 × 31 bytes，+13 是序號）：90＋序號（東条英機、ルーズベルト、チャーチル、ウィルヘルミナ、カーティン、スターリン、蒋介石、ピブン、ヒトラー，看圖對過）。
  - 99–102 沒有人物記錄，只在訊息框（0x31DAA，最後一個參數是頭像）出現：99 M.L.ケソン（0x331FA）、100 ホー・チ・ミン（0x3304C）、101 飛龍艦長 加来止男（0x32900）、102「英海軍　軍令部長」與「プリンス・オブ・ウェールズ艦長　J.C.リーチ」（0x32109、0x32235）。101、102 是背影。
- 名字：每筆記錄開頭是 Shift-JIS 名字（ARDATA／GRDATA 14 bytes、SJDATA 13 bytes），盟軍是半形片假名。10 個劇本的名字相同，匯出用第 1 劇本（`koei_games.load_tk2_pc98_names`）。日本人的姓名間是半形空白（`東条　英機` 是全形），匯出統一成一個全形空白。
  - `GRDATA` 前 5400 bytes 是 10 劇本 × 540；之後 3600 bytes 是 4 份 50 人的舊名單（多了小磯国昭、阿南惟幾、ルメイ等），程式沒有用到。
- 色盤：GRPDRV.EXE 0x1085 以每色 B、R、G 三個 4 bit 值寫 port 0xA8–0xAE。頭像的 8 色在 MAIN.EXE 檔案 0x657F0（後面還有幾份相同或變暗的表，KAIGI.EXE 也有），匯出時 ×17。
- PC-9801 版 1993 年。

### パワーアップキット（`tk2pk-pc98`）

- PK 只有一片（`games/archives/pc98/disks/tk2pk-pc98/1`）：INSTALL.EXE 把 PACK.LZW 解到已安裝的本體上（LWEXT.EXE 是解壓工具）。`games/tk2pk-pc98/` 是本體的檔案加上 PK 片的檔案，匯出時直接從 PACK.LZW 取檔。
- PACK.LZW 是 LW11：檔頭「LW11」＋12 bytes、256 bytes 字典（同 LS11），接著每個檔 32 bytes 的目錄（16 bytes 檔名、big-endian 的壓縮大小、原始大小、位移、4 bytes 不明），檔名第一個 byte 是 0 結束。壓縮碼和 LS11 相同（`ls11.lw11_decode_files`）。共 27 個檔：main.exe、kaigi.exe、end.exe、ardata、newsce（新劇本）等，沒有頭像檔，KAO.TK2、GRDATA、SJDATA 沿用本體。
- 和本體的差別只有 ARDATA 兩個盟軍提督名：C.A.スプレング → スプレイグ、W.A.C.クラッチレー → V.A.C.クラッチレー。NEWSCE 裡的人物表和 PK 的 ARDATA、本體的 GRDATA／SJDATA 相同。
- 色盤：解開的 main.exe 0x3D860，值和本體相同。

## 提督の決断III（TK3, PC-98 日文版）

`dekoei.py export tk3-pc98`／`tk3pk-pc98` 用到的格式。來源是 `games/archives/pc98/[PC98] 提督の決断３.zip`（7 片 FDI；2026-11-08 移到 `games/archives/to-delete/`，2026-11-09 已刪除，本體改由 DOSBox-X 安裝成 `~/game-library/_original/pc98/installed/tk3-pc98.zip`，81 個檔和 dpack 結果相同，`MAIN.EXE` 差 3 bytes 的安裝修補）與 `[PC98] 提督の決断３　パワーアップキット.zip`（2026-11-08 移到 `games/archives/to-delete/`，2026-11-09 已刪除；`games/tk3pk-pc98/` 全部 88 個檔和 neo-kobe 的 `Teitoku no Ketsudan III (with Powerup Kit) [HD].zip` 裡的 HDI 相同，留 HDI），磁片上只有 DPACK 安裝包，用 `dekoei/dpack.py` 解開（見 [dpack.md](dpack.md)）：本體解到 `games/tk3-pc98/`，`games/tk3pk-pc98/` 是本體再疊上 PK 的檔。

- `MAIN.EXE` 是 MS C 7 加 MOVE overlay：root 的 header 是 0x8000 bytes，load image 到 0x62563，之後是 114 個 overlay（各自是 MZ，從 0x62600 起 512 對齊）。DGROUP 是段 0x542B。下文程式位址是 root 去掉 header 後的 image 位址。
- `KAODATA.TK3`：LS11，197 段，每段一張 64×80、4 bpp，2560 bytes。每 8 px 4 bytes 交錯：byte (y × 8 + x / 8) × 4 + q 是 plane q（色號的 bit q），MSB 是最左邊（`kaodata_export.tk3_pc98_face`）。root 0x30D0C 讀（ov107 0x2C4 以 0x2453:0xC7DC 呼叫），本體的頭像號 ≥ 0xC5 會取 197 的餘數。
  - PK 的 `KAODATA2.TK3` 是另外 8 張（197–204）。
  - `PARTS.TK3`、`PARTS2.TK3` 是旗、徽章、階級章等介面圖，沒有組合臉。
- 色盤：root 0x2A6C4 從 0x36C5:0x0A0A（檔案 0x3F65A；PK 0x3E6BA，值相同）設定色號 0–15，每色 B、R、G 各一個 4 bit 值，匯出時 ×17。頭像主要用 0–6 和 15。`BRDGPAL.TK3`（LS11）是 12 個畫面的色盤，0–9 共用。
- 人物表：MAIN.EXE 檔案 0x538BE（PK 0x5291E）起 111 筆 × 26 bytes（`koei_games.load_tk3_pc98_persons`）：
  - [u8][0][名字 12 bytes，Shift-JIS，西洋人是半形片假名與「･」][0][國籍：1 日本、2 美國、3 英國、4 荷蘭、5 澳洲、7 德國][0]…，+25 是頭像號，本體裡都等於序號。
  - 0–78 是提督，79–94 是日本陸軍將領，95–110 是盟軍陸軍將領。看圖對過 46 H・M・スミス（眼鏡）、95 マッカーサー、107 スリム、110 ウィンゲート。
  - 劇本檔（`SNDATA.TK3`、PK 的 `SNDATA1–3.TK3`）有同格式的複本。PK `SNDATA2.TK3` 0x238FF 的表（ロンメル的劇本）106–110 換成 ロンメル 197、マンシュタイン 198、クルーゲ 199、クライスト 200、グーデリアン 201；0x3BBD9 的表 109、110 是 ジューコフ 202、ワシレフスキー 203。`SNDATA3.TK3` 的頭像欄是 0，格式不同。
- `MESSAGE.TK3`：LS11，每段是 [u16 筆數][u16 位移 × 筆數]，字串以 \x05\x05\x05 結束，\x1bk／\x1bH／\x1bK 是字型切換。訊息碼 = 1000 × 段＋序號（`koei_games.tk3_pc98_messages`）。
  - 第 0 段「索敵記録」之後的 24 筆（本體 170–193、PK 172–195）是各國元首：東條英機 … A.スカルノ，依序是頭像 141–164（`koei_games.load_tk3_pc98_leaders`，事件的名牌與看圖對過）。其中 152 K.デーニッツ和提督 78 是同一人，匯出時當 78 的表情。
- `EVENTSEQ.TK3`：u32 事件數（本體 59、PK 87）＋u32 位移，指令是 (u16 op, u16 參數)：2 顯示頭像、8 名牌、4 對話、5 旁白、6 結果、7 地點標題。頭像後面的名牌：
  - 165 軍令部総長 永野修身、168 海軍作戦部長 E・J・キング（只在 PK 的事件有名牌）、174 女優 マレーネ・ディートリッヒ、175 宣伝相 ヨセフ・ゲッペルス、176 アーニー・パイル（只有旁白）、177 大和艦長 有賀幸作、178 駆逐艦雪風艦長 寺内正道、179 日本的飛行員（沒有名牌）、180 第339戦闘飛行隊長 ジョン・W・ミッチェル、183 戦艦艦隊司令官 デイヨー、PK 204 伊19 艦長 木梨鷹一。
  - 參謀：181 日本軍参謀（副官、大本営海軍部参謀）、182 アメリカ軍参謀；185–190 日本的作戦、砲術、航空、航海、情報、補給参謀，191–196 美國同順序（194 沒有事件用到，依順序是航海参謀）。
- 111–140 的 30 張推定是「軍人登録」用的臉（`GUNJIN.TK3` 是 4＋30 × 78 bytes，MESSAGE 第 3 段有軍人登録的字串），沒有在程式裡追到。166、167、169–173、184 沒有在事件找到，用途不明。
- 本體 README 是 1996 年 3 月，PK 是 1996 年 8 月。
