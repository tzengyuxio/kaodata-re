# 伊忍道 打倒信長（ININDOU）頭像相關格式

`dekoei.py export inindou-pc98`／`inindou-x68` 用到的格式（`build_inindou`）。

## 來源與版本

- PC-98：Neo Kobe 2017-11-17 的 `games/archives/pc98/neo-kobe-2017-11-17/Koei/Inindou - Datou Nobunaga/Inindou - Datou Nobunaga [FD].zip`（HDM，FAT12，可用 X68 的 2HD 版面解開）。`VER` 是 `1991.9.2 rel1`，`MAIN.EXE` 1991-09-05。`games/inindou-pc98/` 放 Disk B 的 `KAOGRP.DAT`、Disk A 的 `SDATA.CIM`、`MAIN.EXE`（Disk A 的 `*.FFF` 是存檔用的副本，不用）。
- X68000：Internet Archive `games/archives/x68000/ia-softwarelibrary/inindou_datou_nobunaga_199x_ko_x68k`（3 片 XDF）。`VER` 是 `1991.12.3 rel1`，`IMAIN.Z` 1991-12-09。`games/inindou-x68/` 放 Disk B 的 `KAOGRP.DAT`、Disk A 的 `SDATA.DAT`、`IMAIN.Z`。`IMAIN.Z` 沒有壓縮，執行位址＝檔案位置＋0x514DE。
- PC-88 版（`games/archives/pc88/inindou-flux`，1991-07-19）沒有看。

## 頭像：KAOGRP.DAT

- 兩版逐 byte 相同。14 張 64×80 全高，每 8 點 B、R、G 各 1 byte（`pc88.brg_pixels(raw, 8, double=False)`），沒有壓縮、沒有索引。
- 只有 7 位女主角，每人兩張：第 2h 張平常，第 2h＋1 張閉眼、換白衣。匯出成 `face` 和 `expressions`（label「閉眼」）。
- 夥伴、敵人（`SDATA`、`RJDATA`）只有行走用的 32×32 小圖（`CHARAGRP.DAT`），沒有頭像。沒有組合臉。

## 人物

- X68 0x771D2 在 7 bytes 的表 0x9C02E（`42 10 11 0E 0F 3C 12`）裡找目前對話人物的編號 `[0x94973]`，位置 h 就是臉 2h（存到 `[0x9BFBA]`，0x7677E 畫第 `[0x9BFBA]`＋參數 張）。PC-98 的同一張表在 `MAIN.EXE` 檔案 0x47BDC。
- 人物編號是 `SDATA` 的記錄（0x575D8：記錄＝0x949FC＋編號 × 0x42）。名字（Shift-JIS）在 X68 `SDATA.DAT` 0xBD＋0x42 × 編號、PC-98 `SDATA.CIM` 0xAD＋51 × 編號，兩版 100 個名字相同。
- 7 人依頭像順序：レイ、陽炎、夜鬼姫、雪夜叉、梅夜叉、夕霞、鬼百合。虛構人物，沒有 `nameHistorical`。

## 色盤

- PC-98：`MAIN.EXE` 檔案 0x4385A 的 16 組（B、R、G 各 4 bit），頭像用色號 8–15（`v × 17`，palette id `analog`）。
- X68：`IMAIN.Z` 0x9A514 的 16 個 long，低 16 bit 是調色盤字，只設了 0–7；值是 PC-98 的 4 bit 乘 2 擴成 5 bit（palette id `x68`）。兩版只差量化。

## 發行年份

- PC-88 1991-07（flux 檔名 1991-07-19）、PC-98 1991-09（`VER` 1991.9.2）、X68000 1991-12（`VER` 1991.12.3）。
