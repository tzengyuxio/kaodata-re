# 獨立戰爭 Liberty or Death（LIBERTY, DOS 中文版）頭像相關格式

`dekoei.py export liberty-dos` 用到的格式。來源是 `games/獨立戰爭_中文版_liberty.rar` 的 `LIBERTY/`，解開放在 `games/liberty-dos/`。資料集用英文名 liberty：這款原本在北美開發、發行，日文版是移植。

## 版本

- 原版是北美 DOS 版 Liberty or Death（1993，[Wikipedia](https://en.wikipedia.org/wiki/Liberty_or_Death_(video_game))），日文 PC-98 版 1993-09-27（[Giant Bomb](https://www.giantbomb.com/liberty-or-death/3030-20025/releases/)）。
- 這份中文版是日文 DOS/V 版的移植：`LIBERTY.VER` 是 Shift-JIS「独立戦争・Liberty or Death DOS/V」，`LORD_A/B/C.VOL` 也是日文磁碟標籤。資料檔 1993-07～08，`MAIN.EXE` 1994-07-13。
- `MAIN.EXE` 檔案＝映像＋0x5000，DGROUP 在映像 0x357F0。

## 頭像：FACE.IDX

- 檔頭 `IDX`，張數 byte 存 0x2B（實際 299＝0x12B，高位被截掉），接 299 個 dword offset。
- 每張 `u16 w, u16 h`（都是 64×80 全高），接 NPK 3-bit 資料（`utils.unpack_npk_3bits`），每張剛好 5120 px（`liberty.load_liberty_faces`）。
- 映像 0x62C6 讀取，先 `cmp ax, 0x12B`。沒有組合臉。
- 色盤：
  - DS:0x1E12 起 4 組 × 16 色 ×（B、R、G，4 bit），0–7 色四組相同。`lea bx,[0x1E12]; call 0x474A` 複製，0x46E6 逐色呼叫驅動。
  - 驅動 `GRP400.EXE` fn 14h（映像 0x28BF）寫 `b1 << 2, b2 << 2, b0 << 2` 到 3C9h。
  - 換算 `(v6 << 2) | (v6 >> 4)`：`#000000 #104192 #B25110 #A27171 #417100 #82A2B2 #E3B292 #F3E3D3`，和既有 `liberty_face_colors` 相同。

## 人物

- 人物表在 DS:0x3A0A，250 筆 × 58 bytes：+18 名、+35 姓，各 17 bytes，光榮台灣內碼。匯出寫成「名・姓」（同 SFC 的「・」）（`liberty.load_liberty_dos_names`）。
- 沒有頭像欄位，頭像＝人物編號：0x9101 的呼叫端用 0x78A9（`(ptr − 0x3A0A) / 58`）換出編號後直接傳入。
- `id` 從 0 起算，和 `dokuritsu-sfc` 逐筆一致（兩版的畫大多重畫過）。`SCENARIO.DAT` 只有城市狀態，`SAVEDATA.DAT` 全是 0。
- `nameHistorical`（只填寫成別人的）：82 托馬斯・蓋茨→托馬斯・蓋奇（Gage；Gates 是 87）、191 伊塞亞・加德納→伊斯雷爾・帕特南（Putnam）。音譯不準的不填，例如 35 卡特賴特（Cadwalader）、198／199 羅森堡（Rochambeau）。

## 沒有人物使用的頭像（250–298，都有用到）

- 250–293＝250＋陣營 × 22＋格位（0x9101），陣營 0 大陸會議、1 英國：
  - 格位 0–14：州代表／州總督；15–19：財政部長、國務卿、陸軍部長、海軍部長、大陸會議議長／財政大臣、外交大臣、陸軍大臣、海軍大臣、英國首相。名字取 DS:0x33D2 的初始任職者（44 × 34 bytes，+4 名、+17 姓），遊戲中會換人。
  - 格位 20、21（270／292、271／293）：彈藥補給官、糧食補給官（映像 0x14043）。
- 294、295 傳令（依陣營）；296、297 同盟國海軍軍官（映像 0x12301，國別參數 2 用 296、其他用 297；哪國未確認）；298 雇傭兵隊長。
