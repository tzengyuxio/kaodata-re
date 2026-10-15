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
- [魔眼邪神存檔分析 \- KPHEROS\# \- lechi的創作 \- 巴哈姆特](https://home.gamer.com.tw/artwork.php?sn=5227637)

## 水滸伝・天命の誓い（SUIKODEN, PC-98 日文版）

`dekoei.py export suikoden-pc98` 用到的格式。來源是 `games/pc98/SUIKODEN_PC98_水滸伝2.FDI`，只有第 2 片磁碟，解出放在 `games/suikoden-pc98/`。

- `KAO98.DAT`：260 張，64×80 全高、3bpp、每列 24 bytes，順序同 `utils.to_3bpp_indexes`，無壓縮、無組合臉。
- 色盤：沒有執行檔（在第 1 片）可查，用 8 色數位色盤（每分量 0 或 FF）。理由：舊的 `suikoden face` FDI 分支也用這組；膚色是紅黃抖色，沒有專用膚色色號；同期的三國志II PC-98 也是數位色。屬推論。
- 人物：`SUIDATA1–4.CIM` 從 7124 起 255 筆 × 20 bytes（`koei_games.load_suikoden_pc98_persons`）：
  - +0 姓名 7 bytes Shift-JIS，+7 讀音 9 bytes 半形片假名（不匯出），+16 恆為 0，+17 頭像碼（0 起算），+19 旗標。
  - 4 個劇本的姓名和頭像碼相同，匯出用劇本 1。順序、姓名和 `suikoden-fc` 完全相同。
  - 外字 SJIS 0xEBA0–0xEBAD 的字形在缺少的第 1 片上，字是用 FC 名字和讀音推出來的：鄧郝龔蔣玘鮑俅鄔烕燁褚貹龐戩。
- 沒有人物使用的頭像（對照 FC 的特殊頭像）：255 造船所、256 雑貨屋、257 武器屋（施設），258 徽宗皇帝、259 金国太宗（特殊人物）。
- 發行年份：ja.wikipedia 只寫 PC-9801 版 1991 年，沒有月日，待查。

## 水滸傳・天命之誓（SUIKODEN, DOS 中文版）

`dekoei.py export suikoden-dos` 用到的格式。來源是 `games/水滸傳_中文版_water.zip` 的 `water/`，解開放在 `games/suikoden-dos/`。

- 版本：英文 DOS 版 Bandit Kings of Ancient China（1989，[Wikipedia](https://en.wikipedia.org/wiki/Bandit_Kings_of_Ancient_China)）的中文化。`KAOIBM.DAT` 等和英文版逐 byte 相同，`SUIDATA?.CIM` 只有 7124–19899 的人名、綽號不同。中文版檔案日期都是 1993-05-06，執行檔只寫「(C)1989 KOEI」。
- `MAIN.EXE` 兩層壓縮（LZEXE 0.91 外層、MS EXEPACK 內層），解開後 DGROUP 段 0x28DE。下文是解開後的映像位址。
- 頭像 `KAOIBM.DAT`：260 張 × 960 bytes，64×40 半高、3bpp，格式同三國志II DOS（`san2_pixels`），沒有組合臉。0x71C3 seek `face × 0x3C0`，0x720E 畫臉，byte 0／1／2 寫到 plane 0／2／1。
- 色盤：EGA mode 0x0E（0x8C7B），int 10h AX=1002 載入 DS:0x665A `00 11 12 … 17`，結果是 `SAN2_PALETTE`。
- 人物 `SUIDATA1–4.CIM`：7124 起 255 筆 × 45 bytes，+0 姓名 7 bytes（光榮台灣內碼），+7 綽號，+42 頭像碼（`koei_games.load_suikoden_dos_persons`）。4 個劇本的姓名和頭像碼相同。`id` 從 0 起算，和 `suikoden-fc`、`suikoden-pc98` 逐筆對齊，頭像碼也和 PC-98 相同（PC-98 是全高重畫）。
- 沒有人物使用的頭像都由 MAIN.EXE 用常數頭像碼畫出：255 造船所（0x11BDB）、256 雜貨店（0x11874）、257 兵工廠（0x11946）、258 徽宗皇帝（0x194E7 等）、259 金國君主（0x19273，遊戲沒有名字，照 FC 寫金國太宗）。設施名用中文版 DS:0x7C9E–0x7CB3 的寫法。
- `nameHistorical`（依小說）：115 黃文譁→黃文燁、127 彭汜→彭玘、133 縻勝→縻貹、154 黨士英→党世英、185 黨士雄→党世雄、180 湯窿→湯隆、217 石遷→時遷、227 梁士傑→梁世傑。不填：65 方腊、66 李云（字形差異）。中文版對、日文版錯：35 盧俊義、128 馬麟、210 成貴、254 潘巧雲。待考：56 諸享（褚享？）、191 寇威（英文版 Kou Min，日文版寇烕）。

## 維新の嵐（ISHIN, PC-98 日文版）

`dekoei.py export ishin-pc98` 用到的格式。來源是 `games/pc98/[PC98] 維新の嵐.zip`（A、B 兩片 FDI），解到 `games/pc98/disks/ishin-pc98/A`、`B`，合併到 `games/ishin-pc98/`。A 片和之前的 `games/pc98/ISHIN_維新の嵐A.fdi`（沒有檔頭的原始映像）內容相同。ISIN.EXE 的 load image 從檔案 0x3800 起，DGROUP（段 0x3FE4）在 image 0x371C0；下文是 image 位址。

- `KAODAT.DAT`：105 張 48×40、3bpp，每 8 px 3 bytes，byte k＝bit k（0xA4B 依序寫 A800／B000／B800），720 bytes，無壓縮。
  - 匯出時逐列加倍成 48×80（200 線模式，看圖比例判斷，沒有找到設定模式的程式）。
  - 檔案 0x12750 是第 106 張代用頭像（持旗的浪士群）：0x2F2D 對 id 450–713 回傳真，0x4AB1 就改畫 0x2CA 號，也就是這張。匯出歸「一般人物」。
  - 檔案 0x12A20 是 48×40 1bpp 圓角遮罩：0x4BD0 把合成好的臉 AND 它（0x1521），四角變成色號 0。
- 讀臉函式 0x4AB1：讀 `DS:0x9346 + id × 6` 的 6 bytes 臉記錄；byte0＝0xFF 時讀 KAODAT 第 byte1 張，否則合成。
  - 這張表在 exe 裡全是 0，執行時從 `b:shinario.dat` 載入：SHINARIO.DAT 是 3 個劇本 × 0xA770 bytes，每個劇本載到 DS:0x930A，所以臉表在各劇本 +0x3C。
  - id 0–422：105 人用 KAODAT（0–104 各用一次），318 人是合成臉。
  - 31 人在不同劇本的臉不同（如松前崇広、戸田忠明），匯出時劇本 1 的臉當 `face`，其他放 `expressions`，標「劇本 N」。
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
- 人名：ISIN.EXE 檔案 0x42312 姓 7 bytes × 423、0x449F4 名 9 bytes × 423（`koei_games.load_ishin_pc98_persons`），Shift-JIS＋外字（字形在 USKCG.SYS）：EB9F 恂、EBA0 寛、EBA1 屏、EBA2 佶、EBA3 溥、EBA5 叟、EBA6 孚、EBA7 訥、EBA8 阮、EBA9 煕、EBAA 襄、EBAB 奎、EBAC 霖、EBAD 謨（用人名對過：星恂太郎、大久保忠寛、河合屏山、北添佶磨、黒田長溥、鍋島閑叟、元田永孚、大橋訥庵、箕作阮甫、近衛忠煕、新島襄、松本奎堂、黙霖、川路聖謨）。id 0–422 是史實人物（0x2F12）。
- PC-9801 版 1988 年 6 月（ja.wikipedia）。

## ロイヤルブラッド（ROYAL, PC-98 日文版）

`dekoei.py export royal-pc98` 用到的格式。來源是 `games/pc98/[PC98] [光栄] ロイヤルブラッド(FDI).zip`（A、B 片和使用者片），每片解到 `games/pc98/disks/royal-pc98/A`、`B`、`user`，A、B 合併到 `games/royal-pc98/`。使用者片的 KAODATA.DAT／SENFIEDA.DAT 和 B 片相同。

- `MAIN.EXE` 的 header 是 0x3200 bytes；DS 在檔案 0x27270（0x5B0 用 `index × 13 + 0xE52` 找名字）。下文程式位址是去掉 header 後的 image 位址。
- `KAODATA.DAT`：91 張 64×80，每 8 px 3 bytes，byte k＝plane k（`genpei.decode_planar`），1920 bytes，無壓縮（OPEN.EXE image 0x12D9 以 idx × 0x780 讀，0x29B0 依序寫 A800／B000／B800；MAIN.EXE 是 0x8D06）。順序和 `royal-fc` 的 91 張逐張相同：0–63 君主、64–67 相談役、68–90 部隊／魔獸／召喚。
  - 0x59C：君主的頭像號就是君主序號。相談役是 0x40＋n（0x6A4C、0x10890），部隊是 0x44＋種類（0x8460）。
- 名字是半形片假名：DS:0xE52 君主 64 筆 × 13 bytes（名字 10 bytes），DS:0x13CC 部隊 23 筆 × 16 bytes（`koei_games.load_royal_pc98_names`）。兩者都和 FC 版逐筆相同。
- 色盤：遊戲啟動時問是否用類比 RGB（旗標 DS:0x1942）。
  - 類比：0xE74 把 DS:0x189E 的 8 色淡入（0xDAA），每色 B、R、G 各 4 bit，由 0x2300 寫 port 0xAE／0xAC／0xAA。匯出時 ×17，當預設色盤。
  - 數位：標準 8 色，匯出成第二個色盤。
  - OPEN.EXE DS:0x8D6C 的色盤是開場用的染色，套到頭像會變綠。
- PC-9801 版 1991-12-21（ja.wikipedia）。

## 提督の決断（TK, PC-98 日文版）

`dekoei.py export tk-pc98` 用到的格式。來源是 `games/pc98/[PC98] 提督の決断.zip`（兩片 FDI），解到 `games/pc98/disks/tk-pc98/1`、`2`，合併到 `games/tk-pc98/`。

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

## 提督の決断II（TK2, PC-98 日文版）

`dekoei.py export tk2-pc98` 用到的格式。來源是 `games/pc98/[PC98] 提督の決断２.zip`（7 片 FDI：S 系統、A、B 資料、O 開場、E 結尾、U 使用者、K 硬碟起動；zip 裡的檔名是 Shift-JIS），每片解到 `games/pc98/disks/tk2-pc98/<片>`，S、A、B 合併到 `games/tk2-pc98/`，另加 U 片的 SCE.TK2。U 片的 MAIN.EXE 和 S 片相同。

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

- PK 只有一片（`games/pc98/disks/tk2pk-pc98/1`）：INSTALL.EXE 把 PACK.LZW 解到已安裝的本體上（LWEXT.EXE 是解壓工具）。`games/tk2pk-pc98/` 是本體的檔案加上 PK 片的檔案，匯出時直接從 PACK.LZW 取檔。
- PACK.LZW 是 LW11：檔頭「LW11」＋12 bytes、256 bytes 字典（同 LS11），接著每個檔 32 bytes 的目錄（16 bytes 檔名、big-endian 的壓縮大小、原始大小、位移、4 bytes 不明），檔名第一個 byte 是 0 結束。壓縮碼和 LS11 相同（`ls11.lw11_decode_files`）。共 27 個檔：main.exe、kaigi.exe、end.exe、ardata、newsce（新劇本）等，沒有頭像檔，KAO.TK2、GRDATA、SJDATA 沿用本體。
- 和本體的差別只有 ARDATA 兩個盟軍提督名：C.A.スプレング → スプレイグ、W.A.C.クラッチレー → V.A.C.クラッチレー。NEWSCE 裡的人物表和 PK 的 ARDATA、本體的 GRDATA／SJDATA 相同。
- 色盤：解開的 main.exe 0x3D860，值和本體相同。

## 提督の決断III（TK3, PC-98 日文版）

`dekoei.py export tk3-pc98`／`tk3pk-pc98` 用到的格式。來源是 `games/pc98/[PC98] 提督の決断３.zip`（7 片 FDI）與 `[PC98] 提督の決断３　パワーアップキット.zip`，磁片上只有 DPACK 安裝包，用 `dekoei/dpack.py` 解開（見 [dpack.md](dpack.md)）：本體解到 `games/tk3-pc98/`，`games/tk3pk-pc98/` 是本體再疊上 PK 的檔。

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
