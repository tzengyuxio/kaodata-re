# エアーマネージメント 大空に賭ける（AIR）頭像相關格式

`dekoei.py export air-pc98`／`air-x68` 用到的格式（`build_air`）。

## 來源與版本

- PC-98：Neo Kobe 2017-11-17 的 `games/archives/pc98/neo-kobe-2017-11-17/Koei/Air Management - Oozora ni Kakeru/Air Management - Oozora ni Kakeru [FD].zip`（HDM，FAT12，可用 X68 的 2HD 版面解開），檔案日期 1992-07-15。`games/air-pc98/` 放 Disk B 的 `FACE_*.GDT`、`LADIES.GDT` 和 Disk A 的 `AM98.EXE`。
- X68000：Internet Archive `games/archives/x68000/ia-softwarelibrary/air_management_19xx_koei_disk_x68k`（2 片 XDF），檔案日期 1992-11-12，`AM.Z` 沒有版號字串。`games/air-x68/` 放 Disk B 的 `FACE_*.GDT` 和 Disk A 的 `AM.Z`（沒有壓縮，執行位址＝檔案位置＋0x514DE）。

## 頭像

- GDT 格式見 `notes/leading.md`（`koei_games.gdt_images`）；這幾個頭像檔沒有壓縮。X68 的 GDT 大小與 PC-98 相同，像素是 PC-98 色號 XOR 8。
- 圖片表（X68 `AM.Z` 檔案 0x16F28）依序是 `FACE_ASI`、`FACE_USA`、`FACE_EUR`、`FACE_AFR`、`FACE_ARA`、`FACE_MK`。前 5 個檔各 5–6 張 64×80（アジア 5、アメリカ 6、ヨーロッパ 6、アフリカ 5、中東 6），每張臉後面接 3 張眼（48×24，貼在 8,24）和 3 張口（32×24，貼在 16,48）的動畫幀，第 0 幀和原圖相同，所以只收 64×80 的臉，依地區分組。
- `FACE_MK`：5 位廠商代表（女性），只有口的動畫幀，後面另有 5 張 80×64 的圖（不收）。頭像名是廠商名，依遊戲順序（`AM.Z` 檔案 0x1C182、`AM98.EXE` 檔案 0x41744）：ブルーウィング、ダブルリンク、ミリャーコフ、エアライナー、ワールドリース；臉與廠商的對應沒有在程式裡追，照順序配。
- `LADIES.GDT`（只有 PC-98 版有）：`AM98.EXE` 沒有引用，內容是 5 位女性（畫法和 `FACE_MK` 不同的另一版）加口的動畫幀和 5 張 80×64，匯出 5 張臉、分組「未使用」。
- `air-sfc` 把同一批 33 人分成部下 8、交涉對象 20、廠商 5；這裡的地區臉哪些是部下沒有追，先依地區分組。
- 沒有人名：`characters` 是空的，頭像沒有碼。`CASTER.GDT`（壓縮，6 張 64×80）是新聞播報員的畫面動畫，不收。

## 色盤

- 9 組 16 色（G、R、B 各 4 bit）：X68 `AM.Z` 0x5253C 起每組 0x60 bytes（word），PC-98 `AM98.EXE` 檔案 0x40522 起每組 0x30 bytes（byte），PC-98 的每組是 X68 的前後半對調（對應色號 XOR 8）。
- 設色盤的函式（X68 0x9EA58）以 0x525FC 被呼叫 17 次，其他組各 1–2 次，所以匯出用 0x525FC（PC-98 0x40582）。0x9EA58 把每個 4 bit 值乘 2 成 5 bit 再寫進調色盤，所以 X68 和 PC-98 只差量化：PC-98 `v × 17`（palette id `analog`），X68 `v << 4 | v >> 1`（palette id `x68`）。

## 發行年份

- PC-98 1992-07（檔案日期），X68000 1992-11（檔案日期）。
