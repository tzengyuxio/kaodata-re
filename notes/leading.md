# リーディングカンパニー（LEADING）頭像相關格式

`dekoei.py export leading-pc98`／`leading-x68` 用到的格式（`build_leading`）。

## 來源與版本

- PC-98：Neo Kobe 2017-11-17 的 `games/archives/pc98/neo-kobe-2017-11-17/Koei/Leading Company/Leading Company [FD].zip`（2 片 HDM，FAT12，可用 X68 的 2HD 版面解開；另有 `[Set 1]`、`[Set 2] [b]`）。`LC.VER` 寫 Version 1.00 Release 1，`LC.EXE` 有「Copyright (C) 1992 KOEI」，檔案日期 1992-03-09，`JUDGE.BIN` 檔頭是 1992/2/5。`games/leading-pc98/` 放 Disk B 的 11 個頭像 GDT 和 Disk A 的 `LC.EXE`。
- X68000：Internet Archive `games/archives/x68000/ia-softwarelibrary/leading_company_1992_koei_disk_x68k`（2 片 XDF）。`LC.Z` 1992-07-19，GDT 1992-06。`games/leading-x68/` 放 Disk B 的 11 個 GDT 和 Disk A 的 `LC.Z`（沒有壓縮，執行位址＝檔案位置＋0x514DE）。

## GDT（`koei_games.gdt_images`）

- 一個檔是多張圖串接，每張 16 bytes 檔頭：+2 壓縮旗標，+4 寬、+6 高、+8 每列的 8 點組數、+12 資料大小（PC-98 小端序，X68 大端序）。
- 像素是每 8 點 4 bytes（4 planes，byte k＝bit k）。
- 壓縮（X68 `LC.Z` 0xB06D2）以 4 bytes 為單位：`11kkkkcc` 從 k＋1 列前抄 cc＋1 單位；`10kkkkcc` 從 k＋1 單位前抄；`011cc`＋11 bit、`010`＋13 bit 是遠距離抄；`001nnnnn` 重複一個單位 n＋1 次；`000nnnnn` 是 n＋1 個字面單位。
- X68 的 GDT 大小與 PC-98 相同，像素是 PC-98 色號 XOR 8（plane 3 反相），44 張全部如此。

## 頭像

- 遊戲的圖片表（X68 0x51BF0，檔名前有 `B:`）第 20–30 號是 11 個頭像檔，各 4 張 64×80：`SYA_1–3` 社長、`HI_1–3` 秘書、`BU_KAI`／`BU_SEI`／`BU_EIG`／`BU_KEI` 開発／生産／営業／経理部長、`KAICYO` 会長，共 44 張，依此順序匯出、以職位分組。
- 另外 `LCGUIDE.GDT`（說明程式）有 4 張，和 `HI_1`#2、`BU_KAI`#1、`BU_SEI`#0、`BU_EIG`#3 完全相同，不收。
- 沒有人名：`LC.Z`、劇本 `LC1/2.SCN`、`EVENT.BIN`、`JUDGE.BIN` 都沒有人名，`ORGNAME.BIN` 只有 15 家公司名。`characters` 是空的，頭像沒有碼。

## 色盤

- 16 色兩組：X68 `LC.Z` 0x53F2A／0x53F4A（調色盤字，對應 X68 色號），PC-98 `LC.EXE` 檔案 0x45964／0x45994（G、R、B 各 4 bit，對應 PC-98 色號）。X68 的值是 PC-98 的兩倍、色號 XOR 8（只有 0x53F4A 的第 14 色 R 多 1）。
- 主迴圈開始時（X68 0x8D436）設的是 0x53F4A，之後大多數畫面都用它；0x53F2A 只在銷售統計（0x8B4A8）等少數地方用，兩組差在 PC-98 色號 1、2、9、10。頭像在哪個畫面顯示沒有逐一追，匯出用主畫面的 0x45994／0x53F4A。
- PC-98 換算 `v × 17`（palette id `analog`），X68 是 5 bit 擴成 8 bit（palette id `x68`），兩版只差量化。

## 發行年份

- PC-98 1992-03（檔案日期），X68000 1992-07（檔案日期）。
