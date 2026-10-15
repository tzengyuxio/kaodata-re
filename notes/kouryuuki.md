# 項劉記（KOURYUUKI, DOS 中文版）頭像相關格式

`dekoei.py export kouryuuki-dos` 用到的格式。來源是 `games/archives/dos/項劉記_中文版_hanlau.rar` 的 `hanlau/`，解開放在 `games/kouryuuki-dos/`。

## 版本

- 1994 年台灣宏碁（Acer TWP）發行的中文版（[MyAbandonware](https://www.myabandonware.com/game/rise-of-the-phoenix-axi)）。`MAIN.EXE` 檔案日期 1994-10-20，資料檔 1993-04～1994-09。
- 是日文版的移植：人物記錄保留日文版的讀音欄（中文版全是 0）。不是英文版 Rise of the Phoenix（1993）。
- `PASS.DAT` 是破解補丁（`74`→`EB`），由 `KANSO.COM` 套用；`MAIN.EXE` 本身沒改過。

## MAIN.EXE

- PKLITE 1.15 壓縮。`pklite.depklite` 是解壓 stub 的 Python 移植（不執行遊戲碼），解出 0x46761 bytes。
- DGROUP 段 0x3A87（映像 0x3A870）。下文是解壓後映像的 offset。
- 舊 `kohryuki person` 的 offset（日文版 264260、中文版 276180）是另一份外部解壓檔的位置，和這裡不同。

## 頭像：KAO.KR1

- 97 張 × 1920 bytes，沒有檔頭、沒有壓縮：64×80 全高，3 plane byte 交錯，byte k＝bit k（`genpei.decode_planar`）。
- 讀取在 0000:5C15：`lseek(face × 0x780)`；face ≥ 97 時改成 `random(0x5C)`，隨機借人物的臉。
- 色盤：
  - `GRPDRV.EXE` fn 15h 設 DAC，每色 3 bytes（B、R、G，4 bit），寫入時 `<< 2`。
  - MAIN.EXE 0000:53B9 開機時設 DGROUP 0x5E5A 的 16 色，0000:53FB 依季節換 0x5E5A＋0x30·n；0–7 色四季幾乎相同。
  - 換算 `(v6 << 2) | (v6 >> 4)`：`#000000 #0030A2 #C34100 #B27171 #418200 #82A2B2 #E3A251 #F3E3D3`。
  - 舊 `kohryuki face` 用 `to_3bpp_indexes` 加重排的色盤，畫出來相同，但 5 號色 `#71A2B2` 是冬季那組的。
- 沒有組合臉。

## 人物

- 92 人，人名表在 DGROUP 0x2864（映像 0x3D0D4），每筆 17 bytes：+0 姓名 7 bytes（光榮台灣內碼），+7 讀音 8 bytes，+15 年齡，+16 旗標（`koei_games.load_kohryuki_dos_names`）。能力在 `SNDT1–4.KR1`。
- 沒有頭像欄位，頭像碼就是人物編號：1ECD:2692（臉→名字）在 face < 0x5C 時回傳 DGROUP 0x2864 ＋ 0x11 × face。
- `id` 從 0 起算，和 `kouryuuki-sfc` 的 92 人、97 張頭像順序相同。
- `nameHistorical`：79 藏荼→臧荼、80 司馬邛→司馬卬（缺字代用）、82 靳疆→靳彊。不填：陳余（日文版也寫陳余）、歇、楊（單字，SFC 相同）。張逸（22）、孔熙（56）沒查證。

## 沒有人物使用的頭像（92–96）

- 1ECD:2692 對 face 0x5C–0x60 查 DGROUP 0x7D6E 的指標表 `[(face − 0x5C) / 2]`：長老、士兵、虞姬。
- 92、93 長老；94、95 士兵（映像 0x2ECF2：部隊沒有將領時用 0x5E＋n，n 是楚／漢是推測）；96 虞姬（group「事件人物」）。

## X68000 版（`kouryuuki-x68`）

- 來源：Internet Archive `kouryuuki_1993_koei_disk_1_of_x68k`（`games/archives/x68000/ia-softwarelibrary/`），Disk A 的 KAO.KR1、MAIN.Z、VERSION（「項劉記」 Ｘ６８０００ Ｖｅｒ． １．０）放在 `games/kouryuuki-x68/`。
- KAO.KR1 和 DOS 中文版逐 byte 相同。
- MAIN.Z 沒有壓縮（X 格式，base 0x514FA）。
- 人名表在檔案 0x50F1A，92 筆 × 18 bytes：+0 姓名 7 bytes（Shift-JIS），+7 讀音 8 bytes（半形片假名），+15 年齡、+16 旗標（同 DOS），+17 補位。
- 外字（`koei_games.KOHRYUKI_X68_GAIJI`）：EBB7 蒯、EBE1 酈、EBE2 噲、EBE3 芮、EBE5 卬、EBE6 靳。依 DOS 版同一人的名字對出來；KNJ1.KR1（512 bytes）沒有解讀。
- 日文版的寫法都對得上史書：臧荼、司馬卬、靳彊，所以不填 `nameHistorical`。
- 色盤：檔案 0x52552 是和 DOS DGROUP 0x5E5A 相同的 4 bit B、R、G 表；0x4AF92 的寫入程式把每色 `<< 2`、`<< 7`、`<< 12` 寫到 E82200，也就是 5 bit 的 2v，換算 `2v << 3 | 2v >> 2`。
- 92–96 的名字在 MAIN.Z 0x596B0：虞姫、兵卒、長老。group 用日文寫法（長老、兵卒、事件人物）。
