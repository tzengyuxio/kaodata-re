# 項劉記（KOURYUUKI, DOS 中文版）頭像相關格式

`dekoei.py export kouryuuki-dos` 用到的格式。來源是 `games/archives/dos/項劉記_中文版_hanlau.rar` 的 `hanlau/`，解開放在 `games/kouryuuki-dos/`。

## 版本

- 1994 年台灣宏碁（Acer TWP）發行的中文版（[MyAbandonware](https://www.myabandonware.com/game/rise-of-the-phoenix-axi)）。`MAIN.EXE` 檔案日期 1994-10-20，資料檔 1993-04～1994-09。
- 是日文版的移植：人物記錄保留日文版的讀音欄（中文版全是 0）。不是英文版 Rise of the Phoenix（1993）。
- `PASS.DAT` 是破解補丁（`74`→`EB`），由 `KANSO.COM` 套用；`MAIN.EXE` 本身沒改過。

## MAIN.EXE

- PKLITE 1.15 壓縮。`pklite.depklite` 是解壓 stub 的 Python 移植（不執行遊戲碼），解出 0x46761 bytes。
- DGROUP 段 0x3A87（映像 0x3A870）。下文是解壓後映像的 offset。
- `kohryuki person` 遇到 PKLITE 壓縮的中文版 `MAIN.EXE` 時，解壓後從 `KOHRYUKI_DOS_NAMES` 讀名字；其他 `MAIN.EXE` 仍用舊的日文版 offset 264260（來源不明的外部解壓檔，`games/` 裡沒有對應的檔案）。

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

### 能力

- 狀態視窗（PC-98 `MAIN.EXE` 0x5091）：齢 戦闘／体力 統率／上限 用兵／外交 経験；DOS 中文版是 年齡 戰鬥 體力 統御 上限 用兵 外交 經驗。
- `SNDT?.KR1` 檔頭 +1 月、+3 西元前的年份；從 4 起每 10 bytes 一筆（DS:0x46＋10·i）：+0 bits 0–2 状態（2＝在野）、bit 3 外交、bits 4–7 勢力；+2 所在；+3 体力；+4 上限；+5 戦闘；+6 統率；+7 用兵；+8 経験（劇本都是 0）；+9 同地的下一個人（FF 結尾）。外交在 用兵 ≥80 或 bit 3 時顯示「有」（0x7767 → 0x5C21）。
- 名字表（DOS load image 0x3D0D4，17 bytes 一筆）+15：齢＝+15 − 檔頭 +3 − 50（mod 256，0x7EE8），生年是西元前 (+15＋206)；+16 是 4 個 2 bit 的隱藏值（讀取在 1EEA:0DD2、0DDE、0DEA、0DF6），名稱不明。讀取用 `koei_stats.load_kouryuuki_stats`，`dekoei.py koei-person kouryuuki-dos`。
- ✅ code：讀取函式在 1EEA:0C52–0E32。✅ cross：SNDT1–4 的人物段 DOS 和 PC-98 逐 byte 相同，X68000 只有檔頭不同；名字表 +15、+16 三版相同；項羽前 232、劉邦前 247 和史書一致。
- PC-98、X68000 的 SNDT 只在磁碟映像裡，`games/` 底下沒有，所以指令只支援 DOS 版。
- 已修正（2026-10-22）：舊 `KOHRYUKIPerson` 把 +15 原值當年齡（只有劇本 1 剛好對），欄名也和遊戲用語不同（skill＝戦闘、charm＝統率、intel＝用兵、stamina2＝上限、mask 是 +9 的串列），註解的「外交C/D/B」不對。現在照上面的欄位讀，另加 上限、經驗、外交；`PERSONS_TABLE/kohryuki-persons-s1-zh.csv` 已重新產生。`-ja.csv` 的來源檔不在 `games/`，沒有重跑。
- ❌ 隱藏值的名稱、+1、外交「有」的作用。

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

## PC-98 版（`kouryuuki-pc98`）

`dekoei.py export kouryuuki-pc98` 用 `build_kouryuuki_dos(pc98=True)`。來源是 Internet Archive neo-kobe 的 `Kouryuuki [FD]`（`games/archives/pc98/neo-kobe-2017-11-17/Koei/`，4 片），Disk A 的 `KAO.KR1`、`MAIN.EXE`、`VERSION` 放在 `games/kouryuuki-pc98/`。`VERSION` 寫「項劉記 (PC-9801VM/UV) Ver 1.0」，檔案日期 1993-07-07。

- `KAO.KR1` 和 DOS、X68000 版逐 byte 相同。
- 人名表在 `MAIN.EXE` 檔案 0x45D24，92 筆 × 17 bytes（X68000 是 18 bytes，多一個補位），姓名與讀音和 X68000 版逐 byte 相同，外字碼也相同（`koei_games.load_kohryuki_x68_names(pc98=True)`）。
- 色盤：檔案 0x48116 是和 DOS、X68000 相同的 4 bit B、R、G 表，PC-98 類比色換成 8 bit 是 v × 17。
- 92–96 的名字在 `MAIN.EXE`（虞姫 0x4A856、兵卒 0x4A851、長老 0x48F15），group 同 X68000 版。
