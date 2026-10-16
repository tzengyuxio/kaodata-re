# 三國志 頭像 研究筆記

- [三國志 頭像 研究筆記](#三國志-頭像-研究筆記)
  - [系列共通](#系列共通)
    - [各代用語](#各代用語)
    - [尺寸代號](#尺寸代號)
    - [工具或參考頁面](#工具或參考頁面)
    - [頭像檔命名規範](#頭像檔命名規範)
      - [代號](#代號)
  - [SAN1, SAN2](#san1-san2)
    - [檔案](#檔案)
  - [SAN4, SAN5](#san4-san5)
  - [SAN6](#san6)
  - [SAN11](#san11)
    - [檔案格式](#檔案格式)
  - [SAN12](#san12)
    - [數據](#數據)
    - [相關檔案](#相關檔案)
  - [SAN13](#san13)
    - [RPGViewer 資料](#rpgviewer-資料)
    - [zp1 分析](#zp1-分析)
  - [SAN14](#san14)

## 系列共通

- 楊奉從七代開始就作為顏排名第一位，其次是張飛與關羽。一直到 12 代（13 之後未確認）
- 八代開始分大小圖
- 八代至 11 代的大圖多半還是頭像或胸像，12 代則是半身像（或及腰像）
- 13代開始有一個人多畫像（年輕壯年、文官武將、低位高位）

### 各代用語

- 臉譜: 4, 5
- 相貌: 7, 8
- 容貌: 9, 10, 11, 12, 13
- 臉孔: 14 (又稱, 臉部畫像)
- (缺6代)

### 尺寸代號

- XS: Extra Small
- S: Small
- M: Medium
- L: Large
- XL: Extra Large

### 工具或參考頁面

- [Van’s House](http://pigspy.ysepan.com/)
- 日本製編輯器 [Vector： トップ / ダウンロード / WindowsMe/98/95用ソフト / ゲーム / ユーティリティ / 市販ゲーム等の設定変更 / 光栄用](https://www.vector.co.jp/vpack/filearea/win95/game/tool/edit/koei/)
- ニコニコ動画 歴史戦略ゲー プレイ動画まとめwiki
  - LOS Face Editor [顔画像エディタ - 覚醒支援システム【カギヤマキナ】 総合まとめwiki - atwiki（アットウィキ）](https://w.atwiki.jp/losystem/pages/34.html), 支援 天下創世、革新、天道、三國志12
  - LOS MSG Editor [列伝エディタ - 覚醒支援システム【カギヤマキナ】 総合まとめwiki - atwiki（アットウィキ）](https://w.atwiki.jp/losystem/pages/29.html)
  - [顔グラ変更について - ニコニコ動画 歴史戦略ゲー プレイ動画まとめwiki - atwiki（アットウィキ）](https://w.atwiki.jp/nicosangokushi/pages/134.html)
  - [顔グラ変更について（三国志８以前） - ニコニコ動画 歴史戦略ゲー プレイ動画まとめwiki - atwiki（アットウィキ）](https://w.atwiki.jp/nicosangokushi/pages/794.html)
  - [顔グラ変更について（信長の野望） - ニコニコ動画 歴史戦略ゲー プレイ動画まとめwiki - atwiki（アットウィキ）](https://w.atwiki.jp/nicosangokushi/pages/777.html)
- LS11 格式
  - numdisp 的發問帖 [请问光荣系列的 LS11 格式 - 设计与修改 - 轩辕春秋文化论坛](http://www.xycq.online/forum/viewthread.php?tid=206168&page=1&showoldetails=yes)
  - 後來 numdisp 寫了篇 PDF 介紹 LS11, 我的主要實現均是參考自該篇 PDF

### 頭像檔命名規範

```sh
{作品代號}_{平台}_F{尺寸}{編號}_{附加資訊}.png

編號由 1 開始, 四碼 (0001~9999)

範例：
    SAN1_PC98_F0001.png
    SAN1_DOS_F0001.png
    SAN2_DOS_F0001_TW.png
```

#### 代號

- `F`: 顏 Face (不用 Kao, 遊戲後期命名都改 Face)
- `I`: Item 道具
- `E`: Event 事件
- `M`: Map 地圖
- `U`: Unit 單位

## SAN1, SAN2

- Steam 版 SAN1, SAN2 用的是 PC9801 的版本
- SAN1 DOS 版(Eng.) 與 Steam/PC98 版，除了顏色的差別外(4色 vs 8色), 顏良(No.41)頭盔也是一個差別
- 上面兩個版本在大眾臉武將處的空白也有差異
- SAN2 DOS 版 與 Steam/PC98 版，人物大致相同但有差異，前者感覺大小比較一致
- SAN2 DOS 版 與 Steam/PC98 版，關羽的帽子色不同，張飛的帽子則有明顯顏色不同（前藍後紅）

### 檔案

- SAN1: `PICDATA.DAT`, 檔案後面有其他圖
- SAN2: `KAODATA.DAT`

## SAN4, SAN5

## SAN6

- HLP 檔案裡面有黃氏，三張表情圖 https://i.imgur.com/oHTGphi.png (資訊提供 MikageSayo@ptt)

## SAN11

- [香港三國志 - \[教學\]三國志11頭像、暴擊圖導入/導出(連圖解)](http://hksan.net/main/article.php?/196)

### 檔案格式

解析資料到一半時，發現檔案內常出現 `WFTX0010`，
Google 了一下 `"wftx0010"`, 只找到 [การถอดรหัสไฟล์ (เช่น. Map, Data) - Programming Talk - ParadizeX Forum][progtalk] 這一個結果。
翻譯之後內容跟想像的差不多，雖沒有突破性的收穫，但自己的推測有人驗證也是感覺蠻不錯的。

[progtalk]: https://skjune.com/forum/topic/621-%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B8%96%E0%B8%AD%E0%B8%94%E0%B8%A3%E0%B8%AB%E0%B8%B1%E0%B8%AA%E0%B9%84%E0%B8%9F%E0%B8%A5%E0%B9%8C-%E0%B9%80%E0%B8%8A%E0%B9%88%E0%B8%99-map-data/

### Steam 版 `media/face/San11Face00.fce`（2026-10-16）

- 檔頭 `FACE@`，+12 u32 2200、u32 6600；之後 2200 個 u32（用途未查），再接 6600 項 (u32 位置, u32 大小)，大小 0 是空號。
- 每項是 `WFTX0010`、u32 大小、u32 1、u16 寬、高、u8 bpp、3 bytes 旗標，接像素（24 bit 是由上往下的 B、G、R；8 bit 是色號＋色盤）。
- 6600 項分三組各 2200 號：0–2199 是 240×240（964 張），2200–4399 是 64×80（1572 張），4400–6599 也是 64×80（356 張，1800–2147 等，和第二組同號的是另一個人）。偶數、奇數號是同一人的左右兩向。
- 64×80 有 6 張是 8 bit（444、1134、1468、1500、1508、1550），其餘都是 24 bit，每張 3000–5000 色，匯出成 kaodata/1 的全彩頭像（`rgbaBlobs`），見 [san11.md](san11.md)。

## SAN12

### 數據

- 遊戲中統計
  - 編輯武將容貌時有下拉式選單可選，每項最多10頁，從中可計算總頭像數
  - 新武將 139 張，包括古武將與日本戰國
  - 基本人物 611，包含傳令、童子等 NPC，以及異民族的首領、武將
  - 特別版 42，有關羽諸葛呂布等角色的特殊造型、武則天，以及無雙人物
  - **Total 792**

- 檔案中統計 (基於 steam 版)
  - `resfile` 674
  - `spkao` 35
  - `addkao00`, `addkao00pk` 4
  - `addkao20`, `addkao20pk` 180
  - **Total 893**

- [信長のWiki](https://www.nobuwiki.org/san/cg/12)
  - **收錄了 三國志12 人物頭像 933 張**，
  - 其中包含 40 張比較二次元風格（龍狼傳等）的頭像
    - 第二頁 21 張，第三頁 19 張
  - 從檔名推測圖檔可能源自 RPGViewer 的匯出
  - 與檔案中統計相差 40 張，剛好就是二次元風格的部分

- 其他補充
  - 遊戲中的武將名鑑列表有 588 位
  - 三國志武將大名鑑 書中刊載 12 代有武將 708 人
- 二次元風格 タイアップ (tie up)
  - 編號 1106-1126 為 三國志魂 (荒川弘) 連動
  - 關於 `addkao21` 19張的合作情報: [三國志12 タイアップ情報](http://www.gamecity.ne.jp/sangokushi/12wpk/netplay/tieup1.html)
    - 龍狼傳 13-16 四張
    - みんなの呉 18,19 兩張, 孫權 魯肅
    - 漢晉春秋司馬仲達伝三国志　しばちゅうさん 1-3 三張。看畫風後面也可能是
    - 還有10張...

### 相關檔案

Steam 版存檔位置：`Users\系統使用者名稱\Documents\KOEI\35th\San12WPK_TC\`
（跟網路上查到的資料不同，找好久）

- RPGViewer 可讀取下列檔案（與頭像有關）
  - `resfiles_01.bin`: 基本頭像。表定 2000 張，實際有 674 張。頭像不連續。檔案也包含物品圖。
  - `resfiles_addkao00.bin`: 4張頭像。
  - `resfiles_addkao00_pk.bin`: 同上。
  - `resfiles_addkao20.bin`: 180 張頭像。
  - `resfiles_addkao20_pk.bin`: 同上。
  - `resfiles_addkao21_pk.bin`: 無頭像。有 19 個空位，應該是信長のWiki第二頁的 19 張二次元頭像。
  - `resfiles_spkao0_pk.bin`: 35 張頭像。以無雙角色和主要角色壯年版為主。
  - 以上均包含所有尺寸在一個檔案中。

- 以下檔案是 RPGViewer 不讀取但也跟頭像有關的檔案
  - 下列檔案含 695 張個尺寸頭像，對應檔案 `resfiles_01.bin` 的 674 張與 21 張二次元頭像
    - `Data\KAO_F_M.S12` 推測是 48x60 頭像檔 (Medium)
    - `Data\KAO_F_S.S12` 推測是 32x32 頭像檔 (Small)
    - `Data\KAO_W_L.S12` 推測是 360x512 半身像 (Large)
    - `Data\KAO_W_S.S12` 推測是 90x128 半身像 (Small)
    - `Data\KAODATA.S12`: 作用不清，只有 266 bytes
  - 下列檔案含 4 張各尺寸頭像，對應檔案 `resfiles_addkao00`
    - `AddKao00\ADD00_KAO_F_M.S12`
    - `AddKao00\ADD00_KAO_F_S.S12`
    - `AddKao00\ADD00_KAO_W_L.S12`
    - `AddKao00\ADD00_KAO_W_S.S12`
    - `AddKao00\ADD00.dat` 頭像資料 與 頭像ID 的對應
  - 下列檔案含 180 張各尺寸頭像，對應檔案 `resfiles_addkao20`
    - `PK\AddKao20\ADD20_KAO_F_M.S12`
    - `PK\AddKao20\ADD20_KAO_F_S.S12`
    - `PK\AddKao20\ADD20_KAO_W_L.S12`
    - `PK\AddKao20\ADD20_KAO_W_S.S12`
    - `PK\AddKao20\ADD20.dat` 頭像資料 與 頭像ID 的對應
  - 下列檔案含 19 張各尺寸頭像，對應檔案 `resfiles_addkao21`，有龍狼傳等二次元三國角色
    - `PK\AddKao21\ADD21_KAO_F_M.S12`
    - `PK\AddKao21\ADD21_KAO_F_S.S12`
    - `PK\AddKao21\ADD21_KAO_W_L.S12`
    - `PK\AddKao21\ADD21_KAO_W_S.S12`
    - `PK\AddKao21\ADD21.dat` 頭像資料 與 頭像ID 的對應
  - 下列檔案含 35 張各尺寸頭像，對應檔案 `resfiles_spkao0`
    - `PK\AddKao21\SP0_KAO_F_M.S12`
    - `PK\AddKao21\SP0_KAO_F_S.S12`
    - `PK\AddKao21\SP0_KAO_W_L.S12`
    - `PK\AddKao21\SP0_KAO_W_S.S12`
    - `PK\AddKao21\SP0.dat` 頭像資料 與 頭像ID 的對應

## SAN13

推測數量：1467 -> 結果與推測相同

以下取自「『三國志13』武將ＣＧ追加工具」的 README file (英文取自英文版 README)

> 3.『三國志13』中所使用的武將ＣＧ，每個武將皆備有5張大小不同（特大、大、中、小、極小）的圖像。
> ‧特大(Extra-large) 　…　1024x1024像素：使用於戰法演出、絆成立等特定事件。
> ‧大(Large) 　　　　　…　 633x 900像素：使用於情報畫面、武將對話等。
> ‧中(Medium)　　　　　…　 186x  90像素：使用於出征畫面、都市情報畫面等。
> ‧小(Small) 　　　　　…　　96x　96像素：使用於武將畫面、內政對話方塊畫面等。
> ‧極小(Extra-small) 　…　　72x　72像素：使用於相關圖、標頭情報等。

| filename       |          size | memo       |
| -------------- | ------------: | ---------- |
| DATA0.S13      |        43,712 | =1366*32   |
| DATA1.S13      | 3,278,199,360 | 1366 group |
| pk/DATA0_2.S13 |         4,512 | =141*32    |
| pk/DATA0.S13   |        59,936 | =1873*32   |
| pk/DATA1_2.S13 |   302,463,616 | 141 group  |
| pk/DATA1.S13   | 3,880,394,688 | 1873 group |

- `pk/DATA1.S13`
  - 共有 1467 張, 32bpp
  - group 9, 1024x1024, bust 633x900, Large
  - group 14, 1024x1024, face 1024x1024, Extra Large
  - group 19, 256x128, face, 186x90, Medium
  - group 21, 128x128, face, 72x72, small
  - group 23, 2048x1024, 索引圖x8張, 數量 20x10 (200張)
    - 最後一張索引圖 10x10, 共 67
    - 總共數量 1467
  - group 27, 道具, 256x256, 256 張
- `DATA1.S13`
  - 1267 張
  - Group 7, 633x900
  - Group 8, Extra large
  - Group 9, Medium
  - Group 10, Extra small
  - Group 11, Small
  - Group 13, Items

----------------------------------------------------------------

`zp1`

0. no data
1. 0x00000000, 1, match
2. 0x00001100, 2, match; 分 3 段
3. 0x00040380, 3, 後面數字 match; 分 6 段
4. 0x000B2200, 4, match; 分 32 段
5. 0x002A5900, 沒對上
6. 0x01EA0A20, no data
7. 0x01EA0A20, no data
8. 0x01EA0A20, 後面 0x40C4655C

資料      表
0x2B5104  0x002A5900 (data 後接 0x4038, 16440) 前差
0x2B5984  0x002A5900 (data 後接 0x4038, 16440) 0x880
0x2B6304  0x002A5900 (data 後接 0x4038, 16440) 0x980 (2432)
0x2B6D04  0x002A5900 (data 後接 0x4038, 16440) 0xA00
0x2B7684  0x002A5900 (data 後接 0x4038, 16440) 0x980
0x2B8004  0x002A5900 (data 後接 0x4038, 16440) 0x980
0x2B8984  0x002A5900 (data 後接 0x4038, 16440) 0x980

### RPGViewer 資料

- zero: 零字節空白文件
- not: 非圖片或尚未支持的圖片格式

| no. | count | memo    | subs                              |
| --- | ----- | ------- | --------------------------------- |
| 1   |       | zero    |                                   |
| 2   |       | not     | zp1:1                             |
| 3   |       | not     | zp1:3                             |
| 4   |       | not     | zp1:6                             |
| 5   | 38    |         | zp1:32                            |
| 6   | 7936  |         | size:7936,(sizex8),zp1_block*size |
| 7   |       | zero    |                                   |
| 8   |       | zero    |                                   |
| 9   | 1467  | face L  | size:1467,(sizex8)                |
| 10  |       | zero    |                                   |
| 11  |       | zero    |                                   |
| 12  |       | zero    |                                   |
| 13  |       | zero    |                                   |
| 14  | 1467  | face XL |                                   |
| 15  |       | zero    |                                   |
| 16  |       | zero    |                                   |
| 17  |       | zero    |                                   |
| 18  |       | zero    |                                   |
| 19  | 1467  | face M  |                                   |
| 20  |       | zero    |                                   |
| 21  | 1467  | face XS |                                   |
| 22  |       | zero    |                                   |
| 23  | 8     | face S  |                                   |

### zp1 分析

| start_pos | size | 說明   | memo |
| --------- | ---- | ------ | ---- |
| 0         | 2048 | header |      |
| 2048      |      | body   |      |

- header:
  - 4: 固定 'zp1'
  - 4: 可能是資料原始長度
  - 4: unknown
  - 4: 分幾段
  - 4-: 第n段的長度(包含每段開始的資料長度，所以通常會比 `b_len` 多 4)
- body:
  - 4: 下段壓縮資料長度 k (`b_len`)
  - k: 壓縮資料

Another tree:

- root (`pk/DATA1.S13`)
  - [0] zero empty
  - ...
  - [8] raw data (pos:32115232) (BM1)
    - [0] zp1 (pos: 32126972) (BM2)
      - header: 16 bytes
      - zlib sizes: [71559, 74627, 59770, 29217, 71539, 74629, 59771, 29217, 71541, 74626, 59769, 29214, 19]
      - [0] size(71555) and zlib_data (pos: 32,129,020; 32126972+2048) (BM3)
      - [1] size(74623) and zlib data (pos: 32,200,700; 32126972+2048+ceil(71559/128)*128) (BM4)
      - [2] size(59766) and zlib data (pos: 32,275,452; 32126972+2048+ceil(71559/128)x128+ceil(74627/128)x128)
      - [3] size(29213) and zlib data (pos: 32,335,228; pos[2]+ceil(59766/128)*128)
      - ...
      - [12]
    - [1] zp1 (pos: 32,835,452)
    - ...
  - [13] raw data (pos:1118728064)
    - ...
    - [203] zp1 (pos: 1,212,295,132; 1118728064+93567068)
      - header: 16 bytes
      - zlib sizes: [84430, 115532, 118928, 155103, 56]
      - [0] size(84426) and zlib data
      - [1] size(115528) and zlib data
      - [2] size(118924) and zlib data
      - [3] size(155099) and zlib data
      - [4] size() and zlib data
    - [1466]

zp1 下的壓縮資料按 `0x40000` 的大小切割，分別各自壓縮。通常會切成四塊加上最後一塊 56 bytes (`0x38`) 大小。最後一塊有時有壓縮有時沒壓縮。

## SAN14

推測數量：1446, 全14代總計推測 10450
從圖片大小粗估 1466, 索引檔應該要有 17K 以上

- 主要的頭像放在 ScreenLayout
- 但順序不規則，中間也砸有其他圖片
- 從武將表可以拿到武將容貌編號，目前還不知道怎麼對應 ScreenLayout
- RDB 檔案或許可參考 KOEI Swiss Knife (還沒細看)
  - <https://forum.xentax.com/viewtopic.php?t=21679>
  - <https://github.com/yretenai/Cethleann>
- 三種圖檔大小
  - 大 1024x1024, 去背 32bit
  - 中 2048x1024, 有背景 三張連續（可能是呼吸效果）
  - 小 512x512, 有背景 32bit, 右邊有沒用到的黑邊
- nobuwiki 的編號與 RPGViewer 的不一致，看不出來源
- 夏侯惇
  - 大:4379 中:2800; 小:1129  0
- 袁紹
  - (5766,,)

以下取自「『三國志14』武將ＣＧ追加工具」的 README file (英文取自英文版 README)

> ‧大(Large) 　　…　1024x1024像素：使用於發動戰法時。
> ‧中(Medium)　　…　 633x 900像素：使用於事件、武將詳情畫面等。
> ‧小(Small) 　　…　 512x 512像素：使用於各種圖示以及獨特戰法演出等。

以下取自「武將 CG 追加工具」的使用說明書

```txt
A＝事件與武將詳細畫面等（636×900px）
B＝出陣時等表示的武將圖示（512×512px）
C＝戰法發動時的武將照片（1024×1024px）
```
