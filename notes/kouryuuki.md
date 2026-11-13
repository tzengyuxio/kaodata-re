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
- PC-98 的 `SNDT1–4.KR1` 取自 `~/game-library/_original/pc98/neo-kobe-2017-11-17/Koei/Kouryuuki/Kouryuuki [FD].zip`（2026-11-08 移到 `games/archives/to-delete/`，2026-11-09 已刪除；`games/kouryuuki-pc98/` 的檔案（`VERSION` 以外）都和同資料夾的 `Kouryuuki [HD].zip` 裡的 HDI 相同，留 HDI） 的 Disk A（headerless 2HD 的 HDM，FAT12），放進 `games/kouryuuki-pc98/`；同一片的 `MAIN.EXE`、`KAO.KR1` 和原本的檔 byte 相同。X68000 的 SNDT 還在磁碟映像裡。
- 已修正（2026-10-22）：舊 `KOHRYUKIPerson` 把 +15 原值當年齡（只有劇本 1 剛好對），欄名也和遊戲用語不同（skill＝戦闘、charm＝統率、intel＝用兵、stamina2＝上限、mask 是 +9 的串列），註解的「外交C/D/B」不對。現在照上面的欄位讀，另加 上限、經驗、外交；`PERSONS_TABLE/kohryuki-persons-s1-zh.csv` 已重新產生。`-ja.csv` 改讀 PC-98 `MAIN.EXE` 的人名表（`KOHRYUKI_PC98_NAMES`）與 PC-98 的 SNDT1，也已重新產生，能力值和中文版逐筆相同。
- 外字 EBE5 是「卬」（司馬卬，看字形判讀，同 `KOHRYUKI_X68_GAIJI`）；`KOHRYUKIPerson.extends` 原本寫成「卭」，已修正。
- ❌ 隱藏值的名稱、+1、外交「有」的作用。

### koei-wiki 匯出（人物）

```sh
cd dekoei
../.venv/bin/python dekoei.py persons-export kouryuuki-dos --game-dir ../games/kouryuuki-dos --out ../export/koei-wiki/persons --places ../export/koei-wiki/places
```

`wiki_kouryuuki.py`，koei-persons/1。PC-98 版要放在旁邊的 `../kouryuuki-pc98`。
- 92 人，`id` 同 kaodata（0–91；頭像 92–96 沒有人物）。`name` 用中文版，`nameJa`、`reading` 取 PC-98 `MAIN.EXE` 的人名表（同順序，讀音轉平假名）。史書寫法（`KOURYUUKI_DOS_NAME_HISTORICAL`）寫在 `notes`。
- `stats`：戰鬥、統御、用兵；`more`：年齡、體力、上限、經驗、外交（劇本 1 的值，標籤是中文版狀態視窗的字）。和 `koei_stats.load_kouryuuki_stats` 逐筆相同（✅ cross）。`born` 是名字表 +15 的西元前生年，寫成負數。
- `scenarios`：劇本 1–4，`year` 是檔頭 +3 的西元前年份（負數），`month` 是檔頭 +1。
  - `status`：人物 +0 bits 0–2，0 君主、1 配下、2 在野、7 不在，整組標 `uncertain`。每個勢力（bits 4–7）剛好一個 0，就是 `lord`；2 是在野（筆記上段）。「配下」借「の配下に」一詞，「不在」是自訂的：劇本 3 的審食其是 7，劇本 4 又回來，所以 7 不等於死亡（被俘等，沒追）。
  - `location`：配下與君主的 +2 是軍隊號。軍隊記錄在 `SNDT` 0x1684（格子圖之後）起每筆 27 bytes，+0 是同勢力下一支的 DS 位址，+8／+9 是所在格的 y／x，+25 是勢力號；格號對上地點表 +17 的就是那個地點（🟡：看值判斷，項羽在彭城、劉邦在南鄭、黥布在六、章邯在廢丘都對）。在野的 +2 直接是地點號（雍齒在沛、張良在彭城，🟡）。軍隊不在城、關的格上時不填 `location`（劇本 3、4 共 35 筆）。
- 沒填：隱藏值四項（名字表 +16，名稱不明）、軍隊的兵數等、`relations`（遊戲沒有）。
- 檢查：persons-export 638 項、koei-wiki `verify_persons.py` 1489 項，0 不符。

## 地點與地圖

大地圖是 55 × 44 格，地點 39 處（0–38），沒有州、郡這類區域。部隊在格子上移動，遊戲裡**沒有地點之間的相鄰表**。下文 DOS 位址是 `MAIN.EXE` 解壓後的映像位址。

**地點表**（靜態資料）：DOS 映像 0x3E9D8（DGROUP 0x4168），PC-98 `MAIN.EXE` 檔案 0x47628，每筆 19 bytes，共 39 筆。
- +0 名稱 6 bytes（DOS 是光榮台灣內碼，PC-98 是 Shift-JIS），+7 讀音 7 bytes（半形片假名；DOS 全是 0），+14–16 不明，+17 u16 格號（x＝值 % 55，y＝值 / 55）。
- 0x74A4 依地點號回傳 0x4168＋19 × 號（✅ code）。0x74E5 從 +0x11 取格號，再除以 55 分出 x、y（✅ code）。
- 結構和 SFC 版的地點表（`superfamicom-re:kouryuuki/docs/ROM_FORMAT.md` §6.1，ROM 0x16CA6）相同。三版的 +14–18 byte 相同，順序和名稱也一致（✅ cross）。
- PC-98 名稱的外字照 DOS 中文名對出來：EBE9 陘、EBD6 淄、EBE7 滎、EBEB 睢、EBC6 翟、EBEC 盱、EBDF 眙、EBEA 邾（🟡，字形沒看）。

**格子圖**（各劇本的初始值）：`SNDTn.KR1` 檔案 0x39C 起是 55 × 44 個 u16，逐列存放（檔案 offset＋0x42＝DS 位址，同上面「能力」段），載入到 DS:0x3DE。
- 0x751C、0x756D 用 DS:0x3DE＋2 ×（55y＋x）找格（✅ code）。
- 高位 byte 的低 4 bit 是地形碼，0x9B46 用 `& 0xF` 取出（✅ code）。地點格放的是「地點碼」0–8；其他格是 10–15。
- 照位置看圖判斷（🟡）：10 平地、11 黃河等河流（地圖中央的斜線）、12 山、13 海（東側）、14 零星的格、15 大河與西緣（長江一帶是一整列 15）。
- 10、11 可以通行，12–15 不行：PC-98 `SNDT1` 和 SFC 版的通行層（ROM entry 1）比，地點以外的 2381 格全部一致（✅ cross）。DOS `SNDT1` 只有 (6, 16) 一格不同：DOS 是 14，PC-98 是 10，SFC 是可以通行。
- 4 個劇本只有 2 格不同：広武劇本 3、4 是 2（劇本 1、2 是 1），垓下劇本 4 是 2（劇本 1–3 是 1）。
- 高位 byte 的高 4 bit 與低位 byte 沒查。

**種類**：遊戲用地點碼區分。碼 4 的 3 處（井陘口、函谷関、武関）就是關，SFC 劇本資料的人口也是 0。其他地點表裡沒有種類欄位。

**戰場**：0x2CEA7 取交戰格 (DS:0x87C0, 0x87C2) 的值，經 0x9B2B 寫到 DS:0x87E0。
- 那一格是地點，且地點狀態 +0x20 的 bit 4 有設，就是 9（0x7B94）；否則就是格子的地形碼（✅ code）。
- 0x2C903 用它讀 `HKMD.KR1` 的第 n 筆，碼大於 9 時改成 0（✅ code）。
- `HKMD.KR1` 是 16 筆 × 320 bytes。依自相關看是 32 × 10 格的圖塊號（🟡），程式只會讀到 0–9 筆。
- 所以攻城、關的戰場圖由地點碼決定（同碼的地點共用一張）；野外交戰時地形碼是 10–15，一律用第 0 筆（🟡，只讀了讀取這一段）。
- 0x2C5AF 另外在交戰格四周取 4 格的地形（碼 ≥ 0xE 改成 0xA），再整個讀入 `HYMD.KR1`（5120 bytes）。看起來是依周圍地形拼野戰的地形，沒有追下去（❌）。
- 0x2CD70 遇到碼 4（關）時走另一條路（❌）。

**鄰近地點【推】**：遊戲裡沒有相鄰表，下表是自己推出來的，給條目參考。
- 做法：從 39 個地點同時沿可通行格（地形碼 10、11）往上下左右擴展，每一格歸給最先到達的地點。兩個地點的範圍相接，就算相鄰。
- 遊戲實際的移動規則（四方向或六方向、走一格的天數）沒有查。

| 號 | 中文名 | 日文名 | 讀音 | 種類 | 格 (x, y) | 地點碼 | 鄰近地點【推】 |
|---:|---|---|---|---|---|---:|---|
| 0 | 薊 | 薊 | ケイ | 城 | (36, 0) | 6 | 代、平原 |
| 1 | 代 | 代 | ダイ | 城 | (29, 1) | 6 | 薊、井陘口、鉅鹿 |
| 2 | 井陘口 | 井陘口 | セイケイコウ | 関 | (27, 8) | 4 | 代、晉陽、襄國、鉅鹿 |
| 3 | 晉陽 | 晋陽 | シンヨウ | 城 | (20, 9) | 7 | 井陘口、平陽 |
| 4 | 平原 | 平原 | ヘイゲン | 城 | (36, 10) | 7 | 薊、鉅鹿、臨淄 |
| 5 | 襄國 | 襄国 | ジョウコク | 城 | (28, 12) | 7 | 井陘口、鉅鹿、朝歌 |
| 6 | 鉅鹿 | 鉅鹿 | キョロク | 城 | (32, 12) | 8 | 代、井陘口、平原、襄國、朝歌、昌邑、外黃 |
| 7 | 臨淄 | 臨淄 | リンシ | 城 | (44, 12) | 7 | 平原、高密 |
| 8 | 高奴 | 高奴 | コウド | 城 | (8, 13) | 7 | 櫟陽 |
| 9 | 高密 | 高密 | コウミツ | 城 | (48, 15) | 2 | 臨淄、彭城 |
| 10 | 平陽 | 平陽 | ヘイヨウ | 城 | (16, 16) | 7 | 晉陽、函谷關、櫟陽 |
| 11 | 朝歌 | 朝歌 | チョウカ | 城 | (27, 17) | 7 | 襄國、鉅鹿、廣武、滎陽、外黃 |
| 12 | 廣武 | 広武 | コウブ | 城 | (23, 20) | 1（劇本 3、4：2） | 朝歌、成皋、滎陽 |
| 13 | 昌邑 | 昌邑 | ショウユウ | 城 | (36, 20) | 6 | 鉅鹿、外黃、沛、睢陽 |
| 14 | 成皋 | 成皋 | セイコウ | 城 | (21, 21) | 3 | 廣武、函谷關、洛陽 |
| 15 | 函谷關 | 函谷関 | カンコクカン | 関 | (18, 22) | 4 | 平陽、成皋、櫟陽 |
| 16 | 滎陽 | 滎陽 | ケイヨウ | 城 | (25, 22) | 3 | 朝歌、廣武、外黃、陽翟 |
| 17 | 外黃 | 外黄 | ガイコウ | 城 | (31, 22) | 3 | 鉅鹿、朝歌、昌邑、滎陽、睢陽、陽翟、固陵 |
| 18 | 沛 | 沛 | ハイ | 城 | (39, 22) | 6 | 昌邑、睢陽、彭城、壽春 |
| 19 | 櫟陽 | 櫟陽 | レキヨウ | 城 | (9, 23) | 7 | 高奴、平陽、函谷關、咸陽、武關 |
| 20 | 陳倉 | 陳倉 | チンソウ | 城 | (1, 24) | 0 | 廢丘、南鄭 |
| 21 | 咸陽 | 咸陽 | カンヨウ | 城 | (6, 24) | 8 | 櫟陽、廢丘 |
| 22 | 洛陽 | 洛陽 | ラクヨウ | 城 | (20, 24) | 8 | 成皋 |
| 23 | 睢陽 | 睢陽 | スイヨウ | 城 | (35, 24) | 8 | 昌邑、外黃、沛、固陵、壽春 |
| 24 | 彭城 | 彭城 | ホウジョウ | 城 | (41, 24) | 7 | 高密、沛、垓下、壽春、盱眙 |
| 25 | 廢丘 | 廃丘 | ハイキュウ | 城 | (4, 25) | 6 | 陳倉、咸陽 |
| 26 | 陽翟 | 陽翟 | ヨウテキ | 城 | (25, 26) | 8 | 滎陽、外黃、固陵、宛 |
| 27 | 武關 | 武関 | ブカン | 関 | (15, 29) | 4 | 櫟陽、宛 |
| 28 | 固陵 | 固陵 | コリョウ | 城 | (32, 29) | 2 | 外黃、睢陽、陽翟、宛、壽春、六、邾 |
| 29 | 宛 | 宛 | エン | 城 | (21, 31) | 3 | 陽翟、武關、固陵、江陵、邾 |
| 30 | 垓下 | 垓下 | ガイカ | 城 | (44, 31) | 1 | 彭城、壽春、盱眙、六、烏江 |
| 31 | 南鄭 | 南鄭 | ナンテイ | 城 | (1, 32) | 7 | 陳倉 |
| 32 | 壽春 | 寿春 | ジュシュン | 城 | (39, 32) | 7 | 沛、睢陽、彭城、固陵、垓下、六 |
| 33 | 盱眙 | 盱眙 | クイ | 城 | (47, 32) | 7 | 彭城、垓下、會稽、烏江 |
| 34 | 六 | 六 | リク | 城 | (38, 37) | 6 | 固陵、垓下、壽春、烏江、邾 |
| 35 | 會稽 | 会稽 | カイケイ | 城 | (52, 38) | 7 | 盱眙、烏江 |
| 36 | 烏江 | 烏江 | ウコウ | 城 | (45, 39) | 5 | 垓下、盱眙、六、會稽、邾 |
| 37 | 江陵 | 江陵 | コウリョウ | 城 | (22, 43) | 7 | 宛、邾 |
| 38 | 邾 | 邾 | シュ | 城 | (31, 43) | 6 | 固陵、宛、六、烏江、江陵 |

**大地圖的圖**（`dekoei.py kouryuuki-extras --game-dir ../games/kouryuuki-dos --out ../games/kouryuuki-dos/extract`，寫 `places.csv` 和 `map/world.png`、`world_{spring,summer,autumn,winter}.png`、標「編號 名稱」的 `world_places.png`，2640 × 1408）：
- 0x80EB 把 `MAP.KR1`（14520 bytes）讀到 [0x63F8]:0，`GRP4.KR1`（0xC000 bytes）讀到同段 0x38B8（✅ code）。
- `MAP.KR1` 是 88 列 × 165 bytes，每 byte 一個 16 × 16 圖塊，一格是 3 × 2 塊（48 × 32 點）：0x5493 用 `0xA5 × 列 ＋ 欄` 取 byte（✅ code）。以前當成「每格 6 bytes」照格排，所以畫不出來。
- 0x54B3 畫一格（✅ code）：
  - 6 個圖塊：位址 0x56B8 ＋ 128 ×（byte − min(byte, 10)），即 `GRP4` 0x1E00 起的 246 塊；byte 小於 10 用第 0 塊。用 0x2CD8 不透明複製。
  - 格子值的高 4 bit 小於 13（0x77EF）時，疊上 `GRP4` 0x9900 ＋ 0x300 × 值的 48 × 32 圖（0x558E 的 `值 × 0x300 − 0x2E48`，16 bit 繞回）：13 種道路（直、橫、彎、T、十字），所以高 4 bit 是道路形狀，15 是沒有路（看圖判斷【推】）。
  - 地點碼（0x9B2B，同上「戰場」段）小於 10 時，疊上 `GRP4` 0 ＋ 0x300 × 碼 的 48 × 32 地點圖。碼 4 是關，5 是烏江的村落，9 是地點狀態 bit 4 有設的城。
  - 0x2D39 疊圖時色號 0 透明（遮罩 = 4 個 plane 都是 0）。
- 圖的格式：每 8 點 4 bytes（plane 0–3，bit 7 在左），一列由左到右（0x2CD8 一列複製 `寬 × 4` bytes）。
- 色盤：0x53FB 依 DS:0x43（月）選 0x5E5A ＋ 0x30 × min((月 − 1) // 3, 3)：1–3 月、4–6 月、7–9 月、10–12 月四組（✅ code）。0–7 色四季相同，地形用 8–15 色。
- 輸出照劇本 1 的 `SNDT1` 畫地點與道路；遊戲中地點碼 9 的城會隨狀態變（劇本間只差廣武、垓下兩格）。
- 地點全部落在地點圖上，道路連起相鄰地點，海、山、黃河的位置和地形碼一致（看輸出圖【推】，沒和截圖比對）。

**`places.csv`**：39 個地點，欄位是中文名、PC-98 日文名與讀音（`--pc98-dir`，預設 `games/kouryuuki-pc98`）、種類、格、四個劇本的地點碼、+14–16 原值、相鄰【推】（做法同上）。輸出和上表逐列相同。

**koei-wiki 匯出**：`dekoei.py places-export kouryuuki-dos --game-dir ../games/kouryuuki-dos --out ../export/koei-wiki/places`（`kouryuuki_extras.places`，koei-places/1）。PC-98 版要放在旁邊的 `../kouryuuki-pc98`。
- 39 筆，`name` 用中文版，`nameJa`、`reading` 取 PC-98 版（讀音轉全形）。`level` 是城或關，依地點碼分，遊戲資料沒有種類欄位，所以 `uncertain` 標 `level`。
- `adjacent` 是上面推出來的相鄰【推】，`uncertain` 標 `adjacent`。
- 大地圖 `world/world-{spring,summer,autumn,winter}.png`（2640 × 1408），`pos` 是地點格中心的像素（✅ code）。沒有戰場圖。
- 標籤版 `world/world-spring-labelled.png`：`dekoei.py places-label kouryuuki-dos --places ../export/koei-wiki/places`，放法同三國志IV（`notes/san-maps.md`），和 `kouryuuki-extras` 的 `world_places.png` 逐 pixel 相同。

**沒解開**：
- 地點表 +14–16（三版相同，值 0–24／0–10／0–8）❌。+15 大致隨 x、+16 大致隨 y 增加，像是粗略的座標【推】。
- 格子值低位 byte（四劇本全是 0）❌。
- `HKMD`／`HYMD` 的圖塊格式與渲染 ❌。
- `H2UD`、`H3UD`、`HKUD`、`HIUD`、`HDIR`、`HATK`、`HWAK`、`HSTL`、`H2GD`、`HYGD`、`HKGD` 沒看，從檔名看像是部隊圖、方向、攻擊動畫 ❌。
- 地形碼的名稱 🟡。
- 地點狀態 +0x20 bit 4 的意義（城？）❌。

## 沒有人物使用的頭像（92–96）

- 1ECD:2692 對 face 0x5C–0x60 查 DGROUP 0x7D6E 的指標表 `[(face − 0x5C) / 2]`：長老、士兵、虞姬。
- 92、93 長老；94、95 士兵（映像 0x2ECF2：部隊沒有將領時用 0x5E＋n，n 是楚／漢是推測）；96 虞姬（group「事件人物」）。

## X68000 版（`kouryuuki-x68`）

- 來源：Internet Archive `kouryuuki_1993_koei_disk_1_of_x68k`（`~/game-library/_original/x68/ia-softwarelibrary/`），Disk A 的 KAO.KR1、MAIN.Z、VERSION（「項劉記」 Ｘ６８０００ Ｖｅｒ． １．０）放在 `games/kouryuuki-x68/`。
- KAO.KR1 和 DOS 中文版逐 byte 相同。
- MAIN.Z 沒有壓縮（X 格式，base 0x514FA）。
- 人名表在檔案 0x50F1A，92 筆 × 18 bytes：+0 姓名 7 bytes（Shift-JIS），+7 讀音 8 bytes（半形片假名），+15 年齡、+16 旗標（同 DOS），+17 補位。
- 外字（`koei_games.KOHRYUKI_X68_GAIJI`）：EBB7 蒯、EBE1 酈、EBE2 噲、EBE3 芮、EBE5 卬、EBE6 靳。依 DOS 版同一人的名字對出來；KNJ1.KR1（512 bytes）沒有解讀。
- 日文版的寫法都對得上史書：臧荼、司馬卬、靳彊，所以不填 `nameHistorical`。
- 色盤：檔案 0x52552 是和 DOS DGROUP 0x5E5A 相同的 4 bit B、R、G 表；0x4AF92 的寫入程式把每色 `<< 2`、`<< 7`、`<< 12` 寫到 E82200，也就是 5 bit 的 2v，換算 `2v << 3 | 2v >> 2`。
- 92–96 的名字在 MAIN.Z 0x596B0：虞姫、兵卒、長老。group 用日文寫法（長老、兵卒、事件人物）。

## PC-98 版（`kouryuuki-pc98`）

`dekoei.py export kouryuuki-pc98` 用 `build_kouryuuki_dos(pc98=True)`。來源是 Internet Archive neo-kobe 的 `Kouryuuki [FD]`（`~/game-library/_original/pc98/neo-kobe-2017-11-17/Koei/`，4 片），Disk A 的 `KAO.KR1`、`MAIN.EXE`、`VERSION` 放在 `games/kouryuuki-pc98/`。`VERSION` 寫「項劉記 (PC-9801VM/UV) Ver 1.0」，檔案日期 1993-07-07。

- `KAO.KR1` 和 DOS、X68000 版逐 byte 相同。
- 人名表在 `MAIN.EXE` 檔案 0x45D24，92 筆 × 17 bytes（X68000 是 18 bytes，多一個補位），姓名與讀音和 X68000 版逐 byte 相同，外字碼也相同（`koei_games.load_kohryuki_x68_names(pc98=True)`）。
- 色盤：檔案 0x48116 是和 DOS、X68000 相同的 4 bit B、R、G 表，PC-98 類比色換成 8 bit 是 v × 17。
- 92–96 的名字在 `MAIN.EXE`（虞姫 0x4A856、兵卒 0x4A851、長老 0x48F15），group 同 X68000 版。

## 下一輪候選

- 戰場圖 `HKMD.KR1`／`HYMD.KR1` — 前置：大地圖的圖塊格式已知（每 8 點 4 bytes）；做法：從 0x2C903、0x2C5AF 追它們用哪一段 `GRP*` 當圖塊。
- 地點表 +14–16 — 做法：找讀 0x4168 ＋ 19 × 號 ＋ 14 的程式。
- 大地圖和遊戲截圖比對 — 前置：DOSBox-X 跑到大地圖畫面。

## 負面結論

- 把 `MAP.KR1` 當成「每格 6 bytes、照格排」、`GRP4` 當 16 × 24 的 planar 圖塊：畫不出來，因為檔案是 165 bytes 一列的 16 × 16 圖塊號，圖塊從 `GRP4` 0x1E00 起（見「大地圖的圖」）。
