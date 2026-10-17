# ウイニングポスト2 Plus（PC-98）

`dekoei.py export winning2pk-pc98` 用 `build_winning2pk_pc98`。

## 來源

neo-kobe PC-98 合集的 `Winning Post 2 Plus/`（`games/archives/pc98/neo-kobe-2017-11-17/Koei/Winning Post 2 Plus/`）：

- `Winning Post 2 Plus [FD].zip`：本體 7 片，每片是一個 `DISK_n.PAC`（KOEI Install Program Ver 2.1 的壓縮包，`INSTALL.SYS` 腳本用 `unpack disk_n.pac` 解開）。
- `Winning Post 2 Plus (Powerup Kit) [FD].zip`：PK 3 片（`PKDISK_n.PAC`，`PKDISK_1.VER` 是「Winning Post 2 Plus ﾊﾟﾜｰｱｯﾌﾟｷｯﾄ Version1.00」）。
- `Winning Post 2 Plus (with Powerup Kit) [HD].zip`：裝好 PK 的 HDI。PAC 的壓縮沒解，所以檔案都從這個 HDI 取（`games/archives/pc98/disks/winning2pk-pc98/hdi/`，用到的放 `games/winning2pk-pc98/`）。HDI 裡的 `SAVE/` 有 2017 年的存檔，遊戲玩過。

本體與 PK 的差別只能看 HDI 裡的 FAT 日期：`FACE.DAT`（1995-10-24）、`HUMAN.DAT`（1995-10-25）是本體的，PK 改的是 `HUMAN2.DAT`（1996-07-13）、`JOCKEY.BIN`、`MANNAME.BIN`、`OWNER.BIN`、`MAIN.EXE`（1996-08-06）等。分不出 PK 新增了哪些人，所以資料集沒有 `pk` 標記；kaodata 照 PK 規則只收這個 PK 版。

## 圖

`MAIN.EXE` 是 MS-LINK overlay 的 MZ（主程式到檔案 0x7309A，之後是 overlay），DGROUP 在檔案 0x6A200。畫人物的函式在檔案 0x16D7A（BX＝種類，參數＝編號）。

- 一張圖是 320×256：每 8 點 B、R、G 各 1 byte（`pc88.brg_pixels`），之後是 1 bpp 遮罩（1＝透明），共 0xA000 bytes。
- 一張臉是同樣格式的 104×112（0x16C0 bytes），遊戲把臉疊在身體圖的 (112, 0)（0x16CFA）。頭像就是這個 104×112 的視窗；只有整張圖的人也裁同一個位置。
- 色盤：`MAIN.EXE` 0x65850 起是 27 組 8 色（低半，色號 0–7），0x65AD8 起是 52 組 8 色（高半，色號 8–15），每色 B、R、G 各 1 byte（0–15）。0x1683C 用畫面結構的 +4、+5 選兩組。人物圖只用色號 0–7，取低半第 0 組（第 26 組是數位 8 色，可以確認 B、R、G 的順序）。

`HUMAN.DAT`（檔案控制代碼 DGROUP:0xD2A4）：

| 位置 | 內容 |
| ---- | ---- |
| 0–35 塊 | 6 位秘書各 6 個姿勢（第 s×6＋姿勢 塊，0x17232） |
| 36–51 塊 | 事件圖（秘書單獨、兩位秘書、記者、戴帽男子等） |
| 52–58 塊 | 騎手的身體（勝負服），騎手 n 用 DGROUP:0x87E[n]＋52 |
| 0x24E000 | 騎手 0–59 的臉，每人兩張：年齡 35 歲以下、36 歲以後（0x336C:0x9CA 取年齡） |
| 0x2F8A00 | 騎手 60–65 的整張圖（6 位女騎手） |
| 0x334A00 | 調教師的身體，DGROUP:0x8F6[n] |
| 0x352A00 | 調教師 0–42 的臉；3、14 是整張圖，佔 0xA000，後面的臉往後挪 |
| 0x3A0EC0 | 馬主的身體，DGROUP:0x94C[n]；身體 1 是 `HUMAN2.DAT` 第 42 塊 |
| 0x3D2EC0 | 馬主 0–27 的臉；0、8 是整張圖 |
| 0x40BE40 | 種類 5：5 張沒有記錄的馬主（第 6 張的位置超出檔尾） |

`HUMAN2.DAT`（DGROUP:0xD2A8）以 0xA000 為一塊：0–5 是派對上的 6 位秘書、6 是新娘、7–10 是騎手 66／67（年輕、年長）、11–24 是 7 對沒有臉的騎手（0x1713E 的 0x5A000 起 7 塊，和騎手 67 重疊一塊，照原樣）、25–41 是外國騎手（0x1713E 的 0xFA000、0x122000、0x154000 三段）、42 是馬主的身體、43–46 是情侶、47 是老人。

多人或側身的場景（`HUMAN.DAT` 40 的兩位秘書、45 宝塚讀報，`HUMAN2.DAT` 43–46 的情侶）臉不在頭像視窗裡，不收。

`FACE.DAT` 是 72 張 NPK016（檔頭 12 bytes：`NPK016`、寬、高、大小，沒有平面數；`utils.unpack_npk`）的 104×112 臉，用色號 0–7 加一個背景色（8 或 15，匯出成透明）。整個程式只有 overlay 裡 0x782CE 的「一頁 8 張」挑臉畫面讀它，和 `HUMAN.DAT` 的臉都不同，用途沒查到，歸「不明」。

## 人物

- 名字：`MANNAME.BIN` 是 2000 個 6 bytes 的 Shift-JIS 欄位（3 個全形字時沒有結尾 0），記錄的 +0、+2 是姓、名的欄位號。
- 騎手 `JOCKEY.BIN` 23 bytes × 371，+0x16 是臉號（0x336C:0xDF0），0xFF 是沒有臉。第 k 與 k＋180 筆共用同一個臉號（後一代接手）。
- 調教師 `TRAINER.BIN` 43 bytes × 178，+0x2A 是臉號（0x3467:0x8A4）。
- 馬主 `OWNER.BIN` 20 bytes × 50，+0x13 是臉號（0x3533:0x5DE）。
- 秘書：`MAIN.EXE` 0x6D45E 起 6 筆 28 bytes（姓 7、名 7、暱稱…），順序同 `HUMAN.DAT` 的圖。
- 同名合併：退休騎手當上調教師的 16 人，調教師的臉放 `expressions`（label「調教師」）。
