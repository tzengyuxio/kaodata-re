# 三國志II（SAN2, DOS 中文版）頭像相關格式

`dekoei.py export san2-dos` 用到的格式。組合臉的規則讀自 MAIN.EXE（PKLITE 壓縮，用 `deark -m pklite` 解開後反組譯）。

## 像素格式

- 3bpp byte-interleaved planar，`utils.to_3bpp_indexes` 的順序（第一個 byte 是色號 bit 2）。
- 半高：每列 64 px＝24 bytes，畫面上每列重複兩次，所以 64×40 的資料顯示成 64×80。
- 色盤：EGA `#000000 #55FF55 #FF5555 #FFFF55 #5555FF #55FFFF #FF55FF #FFFFFF`。匯出只放這一組。DOS 版的頭像沿用 PC-88 原版的 200 線圖（`san2-pc88`），PC-98 版是重畫成 400 線的，把 PC-98 色值套在 DOS 的像素上，會得到一張從來不存在的圖；PC-98 版另外從原檔匯出成 `san2-pc98`。

## 頭像碼

人物資料（SCENARIO.DAT／TAIKI.DAT）的 `face` 欄：

- 1–219：專屬頭像，`KAODATA.DAT` 第（碼 − 1）張，每張 960 bytes，共 219 張。
- bit 15＝1：組合臉。bit 0–2 頭型，bit 3–4、5–6、7–8、9–10、11–12 依序是五個區域的記錄號（0–3）。結構和 SFC 版相同（superfamicom-re `san2/docs/ROM_FORMAT.md` §6），但 DOS 版沒有 bit 13–14 的調色盤。

## MONTAGE.DAT：組合臉

- 8 頭型 × 0x18C0 bytes。每個頭型依序放五個區域，各 4 筆記錄。
- 組合函式在 MAIN.EXE 解包後的映像 0x7E08。三張表在 DGROUP（解包檔 0x3D916 起），各 5 個 u16：

| 區域 | 碼的 bit | 頭型內 offset | 每筆 bytes（列數） | 在臉上的 offset（列） | 匯出的 slot |
|---|---|---|---|---|---|
| 0 | 3–4 | 0 | 432（18） | 0（0） | 上 `top` |
| 1 | 5–6 | 1728 | 528（22） | 432（18） | 下 `bottom` |
| 2 | 7–8 | 3840 | 192（8） | 240（10） | 眼 `eyes` |
| 3 | 9–10 | 4608 | 240（10） | 528（22） | 口 `mouth` |
| 4 | 11–12 | 5568 | 192（8） | 384（16） | 鼻 `nose` |

- 遊戲先把 960 bytes 的緩衝清成 0，區域 0、1 直接複製，區域 2–4 逐 byte **OR** 上去。
- 區域 2–4 存成整列 64 px，挖空處以外都是 0。8192 個碼全部驗算過：OR 的結果等於「色 0 當透明，依序蓋上」，所以匯出時把這三區的色 0 換成 255，照 kaodata/1 §6.1 疊圖即可。
- 區域 3、4 的名稱依位置判斷：區域 4 緊接在眼睛下方（第 16 列），是鼻；區域 3 在第 22–31 列，是口和鬍子。SFC 版是 bit 9–10 鼻、bit 11–12 口（已在網站探索器確認零件內容），兩版的欄位順序不同，不是命名錯誤。

## 人物

- 沿用 `san2 person` 的讀法（`san2.load_san2_persons`）：依劇本 1–6、再到 TAIKI.DAT 的順序，以頭像碼去重，共 352 人。劇本裡的格位每個劇本都不一樣，遊戲沒有固定的人物編號，匯出的 `id` 就是這個順序。
- 姓名是遊戲內碼（KOEI-TW），用 `utils.to_unicode_name` 轉成繁體中文，錯字照錄在 `name`。和史書不同的 25 人在 `kaodata_export.SAN2_NAME_HISTORICAL` 填 `nameHistorical`，依據是主公欄位與 `san2-fc` 同位置的人。例如 id 157 寫成「樂進」，但它和 id 39 的樂進是不同人，FC 版同位置是于禁。南蠻的朵思王、金環結、董余奴照《三國演義》寫成朵思大王、金環三結、董荼那（FC 版寫董荼奴）。龐義（龐羲）是 2026-10-14 依新規則補的。295 劉延（劉度帳下，是劉賢）是 2026-11-02 依使用者的三國志能力表（Google 試算表，2015）的備註補的，日文版也一樣。181 陳嬉不是陳紀的錯字，而是吉川英治《三國志》的人物（曹仁的部將，望蜀の巻），能力和三國志I 的陳嬉（197）相同（武力 64、魅力 34，陳紀是 39、19，✅ cross），2026-11-10 從表裡拿掉，不填 `nameHistorical`。
- KAODATA 有 31 張沒有人物使用，用途見 koei-wiki〈遊戲/三國志II/人物顏〉：
  - P027 華佗、P177 司馬徽、P190 許子將：`特殊人物`，人名填在 `portraits[].name`
  - P191–P202：`新君主`。建立新諸侯時，依年齡（青、中、老）× 性別 × 文官或武官自動決定，共 12 張
  - P203–P218：`女兒`。勢力 0–15 外交聯姻時的女兒，例如曹操（勢力 0）是 P203

## PC-98／X68000 日文版（`san2-pc98`、`san2-x68`）

`dekoei.py export san2-pc98`／`san2-x68` 用到的格式（`kaodata_export.build_san2_jp`）。來源：
- PC-98：`games/archives/pc98/【PC98】三國志２.rar` 的 FDI（2026-11-08 移到 `games/archives/to-delete/`，2026-11-09 已刪除；兩片逐 sector 和 `~/game-library/_original/pc98/neo-kobe-2017-11-17/Koei/Sangokushi II/Sangokushi II [FD].zip` 的其中兩片相同），解出放在 `games/san2-pc98/`。
- X68000：`~/game-library/_original/x68/Sangokushi II [FD]/` 的 HDM（沒有檔頭的 2HD，Human68k），解出放在 `games/san2-x68/`。
  - 另一組 `[Set 1]` 的資料檔完全相同，只有 `MAIN.Z`（0x36E44）和 `OPEN.Z`（0x4716）各差 28 bytes：原版在那裡呼叫 IOCS 做磁片檢查，Set 1 改成寫死檢查結果，是破解版。匯出用原版。
- 位址：PC-98 `MAIN.EXE` 是檔案 offset（MZ 檔頭 0x5C00，DGROUP 從檔案 0x35F00 起）；X68000 `MAIN.Z` 沒有壓縮，檔頭 0x1C bytes，執行位址＝檔案 offset＋0x4FFDE。

### 頭像

- `KAODATA1/2/3.DAT`：64×80 全高、3bpp、每 8 px 3 bytes、不壓縮，每張 1920 bytes。95＋96＋KAODATA3 開頭 28 張（0xD200 bytes），共 219 張。
- 頭像碼 → 檔案（PC-98 0x8D9C／X68 `$6DEF4`）：碼 < 0x60 讀 KAODATA1 第 碼−1 張，< 0xC0 讀 KAODATA2 第 碼−0x60 張，其餘讀 KAODATA3 第 碼−0xC0 張。三段接起來就是「第 碼−1 張」，和 DOS 編號一致。
- 每組 3 bytes 的第 k 個 byte 是色號 bit k（PC-98 0x5F0A 依序寫 A800 藍、B000 紅、B800 綠平面；X68 `$85E3C` 寫文字 VRAM 平面 0/1/2）。匯出照 DOS 用 `to_3bpp_indexes`（第一個 byte 當 bit 2），色號意義就和 san2-dos 一樣，色盤也照這個順序排。
- 和 DOS 比：同一編號是同一人，但畫完全不同。PC-98 是把 PC-88 原版的 200 線半高圖重畫成全高，DOS 則直接沿用 PC-88 的半高圖（見下方 PC-88 一節）。X68000 和 PC-98 有 42 張重畫，其餘逐 byte 相同：2 13 20 28 29 38 42 56 63 64 70 73 75 76 77 78 108 110 114 115 116 119 121 127 133 137 155 156 159 160 162 163 165 166 188 191 192 193 194 208 213 216。
- 色盤：
  - PC-98 用預設的 8 色數位色盤（DGROUP 0x3420 的初值 `37 15 26 04`），改色盤的函式 0x6358 沒有呼叫者。
  - X68000 文字色盤表在 `$9F88E`（`$76F3C` 經 `$85F34` 寫進 E82200），0–7 是 `0000 003F 07C1 07FF F801 F83F FFC1 FFFF`，各分量是 0 或 31。
  - 兩者都是每分量 0 或最大：`#000000 #00FF00 #FF0000 #FFFF00 #0000FF #00FFFF #FF00FF #FFFFFF`（`to_3bpp_indexes` 順序）。

### 組合臉

- 零件在 KAODATA3 的 0xD200 起，8 頭型 × 0x37E0 bytes，到檔尾。兩平台這段相同。
- 組合（PC-98 0x8C84／X68 `$6DDAA`）：緩衝清成 0，區域 0、1 直接讀入，區域 2–4 逐 byte OR。8192 個碼都驗算過，等於「區域 2–4 的色 0 當透明、依序蓋上」。
- 頭像碼的位元和 DOS 相同；區域表（PC-98 DGROUP 0x3488/0x3492/0x349C；X68 `$9A164/$9A178/$9A18C`，數值相同）：

| 區域 | 每筆 bytes（列數） | 頭型內 offset | 在臉上的列 | slot |
|---|---|---|---|---|
| 0 | 792（33） | 0 | 0 | 上 |
| 1 | 1128（47） | 3168 | 33 | 下 |
| 2 | 552（23） | 7680 | 21 | 眼 |
| 3 | 552（23） | 9888 | 29 | 鼻 |
| 4 | 552（23） | 12096 | 41 | 口 |

- 區域 3、4 是鼻、口，和 DOS（口、鼻）相反，和 SFC 版相同。

### 人物

- PC-98：每個 `SNDATAn.CIM`（0x33AF bytes）就是 DOS `SCENARIO.DAT` 的一個劇本區塊（表頭 0x16，215 筆 × 43 bytes，`s2_format`）；`TAIKI.DAT` 同 DOS（`s2_format_taiki`）。
- X68000：大端序、有 68000 對齊補位。SNDATA 表頭 0x1A，每筆 54 bytes（`>IH12BIIIBxxBI14sxx`，頭像碼 u32 在 +34、姓名在 +38）；TAIKI 表頭 6 bytes，每筆 58 bytes（前面多 4 bytes）。
- 姓名欄 14 bytes：前 7 bytes Shift-JIS，後 7 bytes 半形片假名讀音。讀音不匯出（X68000 的張承讀音誤植為 ｼｮｳｼｮｳ，其他和 PC-98 相同）。
- 外字 SJIS 0xEB9F–0xEBC7，字形在 `FONT.DAT`，PC-98 對照表在 DGROUP 0x34B0（X68 `$9A854`），看字形判讀，見 `san2.JP_GAIJI`。兗、釭、幷沒有人名用到，判讀較沒把握。
- 依劇本 1–6、再 TAIKI 的順序以頭像碼去重（`san2.load_san2_jp_persons`），兩平台都是 352 人，順序和 DOS 完全相同，`id` 一致。
- 姓名：
  - DOS 版 `SAN2_NAME_HISTORICAL` 中，以下在日文版本來就正確，是中文移植造成的：31 張顗、61 蔡瑁、98 趙範、121 劉璝、157 于禁、164 夏侯楙、220 廖化、249 厳畯、308 阿会喃、332 毋丘倹。
  - 日文版本身有誤、照遊戲寫法的：67 張資（其實是吉川英治《三國志》的寫法，不是錯字，見下）、122 雷同、125 粱剛、167 韓楷、218 李湛、258 歩鷙、260 蔡仲、264 尚挙、284 尚寵、297 鮑龍、306 朶思王、315 金環結、319 董荼奴、322 沙摩可。
  - 這 14 筆都填 `nameHistorical`（`SAN2_JP_NAME_HISTORICAL`，用日文字形，如歩騭、向挙、朶思大王）。另外龐義（龐羲）、毋丘倹（毌丘倹）在日文版也寫錯，一起填；295 劉延→劉賢同 DOS，共 17 筆。181 陳嬉是吉川英治《三國志》的人物，不是錯字（見上）。67 張資也是吉川版（桃園の巻「赤兎馬」）的寫法，史書作張咨，`nameHistorical` 照填，koei-wiki 匯出標「吉川版名字」；203 楊平只在吉川版（圖南の巻「漢中併呑」），標「吉川版人物」（`kaodata_export.YOSHIKAWA_NAMES`，2026-11-14）。毋丘倹之前誤判為正確，「毋」和「毌」是不同的字。
- 沒有人物使用的頭像和 DOS 相同。特殊人物的名字在 PC-98 檔案 0x40A26（X68 0x5121A）：司馬徽、許子将、華陀（遊戲寫「華陀」）。對應 P177、P190、P027 是沿用 DOS 的結論加上看圖，沒在程式裡追到頭像碼。

### 戰場地圖

`dekoei.py san2 battlemap --game-dir ../games/san2-pc98 --out ../games/san2-pc98/extract/battlemap` 寫出 `01.png`–`41.png`（416×400）與 `terrain.png`（7 種地形）。

- `china.png`、`china_labeled.png`（3328×3472）：41 張依州的六角相鄰關係拼成的全中國戰場，拼法照 FC 版（`famicom-re:san2/docs/ROM_FORMAT.md`〈全中國戰場拼接測試〉）：州 (q, r) 放在第 -(q+r) 欄、第 -r 列，隔欄往下錯半張，奇數欄多出的半格剛好填進下一張的空位。
  - 六角座標抄自 FC 版相鄰表推出的 `hex_layout`（`san2.SAN2_PROVINCE_HEX`，famicom-re@bd59cff）。執行時會檢查每州在六角格上的鄰居和 PC-98 布陣層出現的州號相同，41 州都相同，✅ cross。
  - 從布陣層 5 格的位置推方向不可靠：和 FC 的邊方向比，有 9 組猜錯（多在地圖角落），所以只拿布陣層驗證鄰州集合。
  - 拼起來後河流和地形跨接縫連續（看圖確認，🟡），遊戲本身不會拼接。

- `HEXDATA.DAT`：
  - 0 起是地形層，41 張 × 156 bytes。每張 13 欄 × 12 列，逐列存放，每格 1 byte，值 0–6。
  - 6396 起是布陣層，格式相同。值是州號：本州 20 格，每個鄰州 5 格。推定是守方和從該州進攻的攻方的布陣區，🟡（只看了數值，沒在遊戲裡確認）。
  - 12792 起是 7 張 32×32 的地形圖塊，每張 384 bytes，3bpp，每 8 px 3 bytes（`to_3bpp_indexes`）。之後的 2592 bytes 是部隊等小圖，還沒解。
- 地形 id 照 FC 版的名稱：0 平地、1 森、2 林、3 山、4 河、5 村、6 城（舊的 `san2 map` 註解寫平原 森林 丘陵 高山 水域 營寨 城池）。每張圖剛好一個城。
- ✅ cross：地形層和 FC 版（`famicom-re:san2/docs/ROM_FORMAT.md`「戰場地圖」，ROM `0x26FE8` 的 nibble）41 張逐格相同。DOS、PC-98、X68000 的地形層和布陣層 byte 相同；PC-98 和 X68000 的地形圖塊 byte 相同，之後的小圖不同。
- DOS 版的圖塊是 32×16（200 線），一張 192 bytes，所以 `HEXDATA.DAT` 比較短；舊的 `san2 map` 切的就是 DOS 版。
- 排法：奇數欄往下半格（16 列），圖塊不重疊，13 × 32 = 416 寬、12 × 32 ＋ 16 = 400 高，剛好是全畫面高。色盤用頭像那一節的預設 8 色。排法和色盤都沒和遊戲畫面比過，🟡。

### 發行年份

ja.wikipedia〈三國志II〉：PC-9801 版 1990-03-23（1989-12 是 PC-8801 原版），X68000 版 1990-08-27（`VERSION` 寫 Jul.16, 1990）。

## PC-88 原版（`san2-pc88`）

`dekoei.py export san2-pc88` 用到的格式（`kaodata_export.build_san2_pc88`）。來源是 Neo Kobe 2016-02-25 的 `~/game-library/_original/pc88/neo-kobe-2016-02-25/Sangokushi II/Sangokushi II [FD].7z`（Disk A、B、C、D、U），解出的檔案放在 `games/san2-pc88/`：Disk C 的 `KAODATA.DAT`，Disk B 的 `SNDATA1–6.CIM`，Disk A 的 `TAIKI.DAT`，以及參考用的 `MAIN.COM`。

### 版本與磁碟

- `TAIKI.DAT`（以及 Disk A 開機區）的字串：`For PC-8801SR 1989.12.11 Ver1.0 Rel1.0 TYPE-A`。磁碟上的檔案日期是 1989-12-10。
- 發行年份：PC-8801 版 1989-12（ja.wikipedia〈三國志II〉），是系列首發。
- D88 每軌 9 個 512 bytes 磁區。Disk B、C 是 FAT12（`NEC 2.00` 開機區），Disk A、U 是 YDOS 3.0。

### 頭像與組合臉

- `KAODATA.DAT`（260928 bytes）＝219 張 960 bytes 的頭像（格式同 DOS：64×40 半高、`to_3bpp_indexes`），後面接 50688 bytes 的組合臉零件。
- **DOS 中文版沿用了這份圖**：219 張頭像中 218 張和 DOS `KAODATA.DAT` 逐 byte 相同，只有 P029（關羽）不同；組合臉零件和 DOS `MONTAGE.DAT` 相同，只有每個頭型裡最後兩個區域的順序對調。
- 零件表在 `MAIN.COM` 0x3665（每筆 bytes、在臉上的 offset、頭型內 offset 各 5 個 u16）：區域 3 是鼻（頭型內 4608，192 bytes，第 16 列），區域 4 是口（5376，240 bytes，第 22 列）。也就是說 PC-88 和 PC-98／SFC 一樣是 bit 9–10 鼻、bit 11–12 口，是 DOS 移植時把兩區對調（`san2.PC88_MONTAGE_AREAS`）。
- 色盤：數位 8 色，色號意義同 PC-98（`#000000 #00FF00 #FF0000 #FFFF00 #0000FF #00FFFF #FF00FF #FFFFFF`，`to_3bpp_indexes` 順序），palette id `pc88`。

### 人物

- `SNDATAn.CIM` 是 PC-98 的劇本記錄往前 1 byte（表頭 0x15），`TAIKI.DAT` 和 PC-98 相同的版面（`san2.load_san2_pc88_persons`）。
- 以頭像碼去重得 357 個碼，比 PC-98 多 5 個：有 5 人在某些劇本用了另一個組合臉碼（大多只差一個 bit，PC-98 已改成一致）。匯出把同名的合成一人，第一次出現的碼當 `face`，另一個放 `expressions`，標上用到它的劇本：
  - 30 審配：P077，劇本 2 是組合臉 9618
  - 103 陳蘭：88E5，劇本 3 是 98E5
  - 114 糜芳：9CED，劇本 3 是 8CED
  - 259 徐盛：9CA8，劇本 6 是 8CA8
  - 295 劉延：8AEB，待機是 8A2B
- 合併後 352 人，姓名、`id`、`face` 和 `san2-pc98` 完全相同，`nameHistorical` 沿用 `SAN2_JP_NAME_HISTORICAL`。沒有人物使用的頭像和名字也同 PC-98。

## koei-wiki 匯出（`san2-pc98` 人物）

```sh
cd dekoei
../.venv/bin/python dekoei.py persons-export san2-pc98 --game-dir ../games/san2-pc98 --out ../export/koei-wiki/persons --places ../export/koei-wiki/places
```

讀取在 `dekoei/wiki_san2.py`（koei-persons/1，2026-11-14）。352 人，`id` 同 kaodata `san2-pc98`。

- **名字**：`name` 取 DOS 中文版（`games/san2-dos`，`san2.load_san2_persons`），兩版的頭像碼順序逐筆相同（程式裡 assert）；PC-98 寫法不同時放 `nameJa`（75 人）。錯字照遊戲寫法，`kaodata_export.SAN2_NAME_HISTORICAL`／`SAN2_JP_NAME_HISTORICAL` 的史書寫法寫進 `notes`。`reading` 是姓名欄後 7 bytes 的半形片假名，轉成平假名。
- **欄位**：`stats` 知力 武力 魅力（+4–6，同 `stats-export`）；`born` 是 +25 生年（✅ capture：`captures/screenshots/san2-pc98/main_000.raw1.png`，189 年曹操年令 35＝189−155＋1）；`hidden` 義理 人徳 野望 相性（+7、+8、+9、+15）與親族（+16 u16 bitmask），整組 `uncertain`。頂層取這個人第一筆記錄（劇本 1–6 依序，再到 TAIKI）。
- **劇本檔 `SNDATAn.CIM` 的版面**（這次解出）：
  - 表頭 +2 u16 是年份，畫面顯示＋1（188 → 189 年 1 月，✅ capture 同上；六個劇本 189、194、201、208、215、220，和 koei-wiki〈遊戲/三國志II〉相同）。
  - 人物 255 格 × 43 bytes，從 0x16 起；+0 u16 是同一串的下一個人。指標是執行期位移：第 s 格在 88＋43s（檔案位移＋66）。
  - 0x2AEB 起 7 bytes 未解，0x2AF2 起 16 個勢力 × 41 bytes：+0 君主、+2 本拠國、+4 軍師（指標）。六個劇本的君主依序和 MAIN.EXE 0x3CB88 起的劇本君主名單相同，✅ cross；+6 起有 16 bytes 都是 50 的一段（推定是對各勢力的友好度，未確認）。
  - 0x2D82 起 41 國 × 35 bytes：+0 同勢力下一國、+2 現役武將串的頭、+6 在野武將串的頭、+16 所屬勢力（0xFF 無）。每個劇本的人物記錄都剛好出現在一串裡（程式裡 assert），+4 的串都是空的。
- **`scenarios`**：每劇本 `year`、`status`、`lord`、`location`、`loyalty`。
  - `status` 用遊戲的分類詞（MAIN.EXE 0x3DEF8「君主 太守 軍師 現役 在野」）：勢力記錄的君主是君主、軍師是軍師；現役串的第一個人是太守（✅ capture：189 年第 9 國「太守曹操、軍師陳宮」；其他國沒有對截圖，所以太守、軍師標 `uncertain`）；串裡其他人是現役；在野串是在野。軍師和串頭沒有重疊。
  - `lord` 是所屬勢力的君主；`location` 是國號，就是地點匯出的 `id`（1–41）；`loyalty` 是 +11 忠誠（君主、在野不填）。
  - 劇本裡沒有、但在 TAIKI.DAT（後登場武將）且登場年 ≥ 劇本年的，寫 `未登場`，附 `debut` 和 `location`（TAIKI +2 的國號，0 不填）。登場年比劇本年早、劇本裡又沒有的（史實已死的人等），遊戲會不會讓他登場沒追，不列。
  - TAIKI +0 的登場年直接當西元：遊戲開局時年份先＋1（表頭 188 顯示 189），推定 TAIKI 和執行中的年份比，沒追程式，所以 `debut` 標 `uncertain`。孫亮等 6 人登場年是 255，看來是不會自動登場。
  - TAIKI +1 是登場時投靠的人，存的是那個人的頭像碼低 byte（曹丕 103＝曹操、関平 30＝関羽、周瑜 109＝孫策），不是親屬，沒放進匯出。
- **檢查**：persons-export 2832 筆、koei-wiki `verify_persons.py` 6843 筆，0 不符。
- **沒填**：位、信用度、婚姻（畫面有，記錄裡沒找到）、兵士／訓練／武装（劇本起始值，沒匯出）、`died`（遊戲沒有）。
- **地點名**：地點匯出的 `name` 是 null、借用三国志ツクール的州名；但遊戲畫面會顯示州名（截圖上的「兗州-9」），名稱表還沒找，找到後可以補地點的 `name`。
