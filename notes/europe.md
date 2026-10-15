# 歐陸戰線（EUROPE, DOS 中文版）頭像相關格式

`dekoei.py export europe-dos` 用到的格式。來源是 `games/archives/dos/歐陸戰線_中文版_europe.rar` 的 `olzx/`，解開放在 `games/europe-dos/`。

## 版本

- 檔案日期 1994-01-18，`MAIN.EXE` 沒有版權年（只有 MS C 1990）。
- 原作 ヨーロッパ戦線：SFC／MD 1993-01-16。英文 DOS 版 Operation Europe: Path to Victory 1939-45 只在北美發行，年份資料矛盾（[Wikipedia](https://en.wikipedia.org/wiki/Operation_Europe:_Path_to_Victory) 1994、[Playnite](https://playnite.gamescrobbler.com/games/operation-europe-path-to-victory-1939-45) 1991）。中文版是否由英文 DOS 版移植，未證實。
- `MAIN.EXE` 沒有壓縮，MZ 檔頭 0x5800，DGROUP 在檔案 0x46B00。「映像」＝扣掉檔頭的位址。

## 頭像：FACE.DAT

- 120 張 × 1920 bytes：64×80 全高，3bpp byte 交錯，byte k＝bit k（`genpei.decode_planar`），沒有壓縮。
- 映像 0xAA10 讀取：seek `face × 0x780`（0xAA8D）。
- 色盤：
  - 映像 0xAE48 `setpal(0, 8, DGROUP 0x56B6)`（檔案 0x4C1B6）；8–15 色是地圖用，依季節從 0x56CE／0x56E6／0x56FE／0x5716 選。
  - 映像 0x23D5 把每色 3 bytes 送到 DAC：R、G、B＝byte1、byte2、byte0，各 `<< 2`。
  - 換算 `(v6 << 2) | (v6 >> 4)`：`#000000 #104192 #D33030 #D371B2 #419241 #71B2B2 #F3C361 #F3F3F3`。
  - 舊 `europe face` 用 `to_3bpp_indexes`（第一個 byte 當 bit 2）配 G、B 對調的色盤，碰巧顏色正確；紅、青兩色和 MAIN.EXE 略有不同。
- 和 `europe-sfc` 的 120 張順序、內容一致。沒有組合臉。

## 人物

- 文字是光榮台灣內碼，不是 Big5。
- 記錄 22 bytes：+0 姓名 8 bytes，+9 國別（1 德、2 義、4 美、8 英、16 法、32 蘇；0xFF 是空位），+10–17 能力，+20 頭像碼＝人物編號，+21 雜項／領袖職位。映像 0xAAC0 以 `[bx+0x14]` 取頭像。
- 指揮官 0–93：`SCEDATA` 7 個劇本，起點 0x1772、間隔 0x1D95，各 40 筆（前 20 軸心、後 20 聯合軍），合起來 0–93 都有。
- 領袖 94–105：`MAIN.EXE` 檔案 0x49898（DGROUP 0x2D98）12 筆，+21 是職位（4 最高統帥、5 參謀總長、6 空軍司令、7 特種兵長官；依字串順序推得）。
- 劇本間寫法不同的 3 人，取出現最多的（同票取先出現）：14 克呂韋爾／克魯韋爾、34 蒂夫／提夫、36 巴特爾／海德（SFC 是ハイテ）。`koei_games.load_europe_dos_names`。
- `id` 從 0 起算，0–99 和 `europe-sfc` 一一對應；100–105（戈林、斯帕茨、諾比科夫、迪克茲、勒考克、梅爾赫夫）SFC 沒有。103–105 的史實人物沒查。
- `nameHistorical` 不填：多是音譯不同（如 60 弗萊舍＝Freyberg）。86 加里寧可能被誤認成 Kalinin，待考。

## 沒有人物使用的頭像

- 106–117 替補指揮官：映像 0xBD9E 建立新指揮官（名字「--------」），頭像範圍表在 DGROUP 0x57BA：軸心 106–111、聯合軍 112–117。
- 118 村姑、119 修女：映像 0x11834、0x114A0 直接 seek，旁邊是對應的字串。
