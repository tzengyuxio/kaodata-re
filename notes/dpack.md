# DPACK（光榮 PC-98 硬碟安裝包）

PC-98 後期的光榮遊戲（提督の決断III、同 PK、三国志V 等）磁片上只有 `INSTALL.EXE`（KOEI Install Program Ver 2.1）、`INSTALL.SYS` 與 `DPACK1.xxx`、`DPACK2.xxx`…；`INSTALL.SYS` 以 `UNPACK DPACKn.xxx` 把包解到硬碟。`dekoei/dpack.py` 是 INSTALL.EXE UNPACK 的移植：

```sh
cd dekoei
../.venv/bin/python dpack.py <OUTDIR> DPACK1.TK3 DPACK2.TK3 ...   # 依序給全部的包，一個檔可能跨包
```

以下位址是提督の決断III 的 INSTALL.EXE（header 0xE00，DGROUP 0xD27）去掉 header 後的 image 位址；UNPACK 在 0x9B20。另有一套無關的 LW11（LS11）解碼在 0x76DC。

## 容器

- 整個包是 MSB 先的位元流（讀取 0x9F98，位元位置在 [0x8B6E]），由一連串「區塊」組成。
- 區塊開頭是 4 bit 的 opcode（跳躍表 0x8BC8），直到 15（接資料）或 14（包結束）：

| op | 內容 |
|----|------|
| 0  | 旗標 0x8000（不壓縮，原樣存放） |
| 1  | 旗標 = 0xB5 |
| 2  | 1 bit：0 → 旗標 \|= 0x14（距離用三棵 nibble 樹）；1 → 4 bit 距離寬度，≠ 12 時旗標 \|= 2 |
| 3  | 旗標 \|= 0x30，再 1 bit：1 → 0x80（字元樹用碼長傳），0 → 0x40（字元樹直接傳） |
| 4  | 多檔名（沒用到，未實作） |
| 5  | 1 bit「檔案在下一區塊繼續」＋17 bit 區塊大小；下一區塊在「本區塊起點＋大小 − 1」 |
| 7  | 檔名（8 bit 字元，最多 13 個，0 結束）＋屬性 8 bit＋日期 16 bit＋時間 16 bit |
| 14 | 包結束 |
| 15 | 後面是資料 |

## 資料區塊（0x8F62）

- 16 bit：位元組數 − 1。
- 旗標 0x8000 且沒有 0x20：對齊到 byte 後原樣存放。
- 旗標 0x80：字元樹（512 個符號）用碼長傳：
  - 先傳一棵 16 符號的樹（前序：bit 1 = 內部節點，先左 0 後右 1；bit 0 = 葉，接 `bitlen(n) − 1` bit 的符號，0x827A）。
  - 4 bit 跳過筆數，每筆 9 bit 位置＋9 bit 長度（這些符號碼長為 0）。
  - 其餘 512 個碼長用那棵樹解。
  - 由碼長建樹（0x8122／0x81E0）：從最深一層往上，同深度的節點依編號兩兩配對成父節點。
- 旗標 0x40：512 符號的樹直接以前序傳。
- 旗標 4：距離是三個 nibble，各有一棵 16 符號的樹（前序傳）。旗標 2：1 bit 選 12 bit 或指定寬度。否則距離固定 12 bit。
- 符號 < 0x100 是字元；否則長度 = 符號 − 0xFD，距離 + 1，視窗 4096。

## 驗證

- 提督の決断III：在 DOSBox-X 實際安裝（`games/archives/pc98/install/tk3-pc98/`），81 個檔中 80 個與 `dpack.py` 的結果逐 byte 相同。
  - 唯一不同的是 MAIN.EXE 檔案 0x15AC02 的 3 bytes：包裡是 `0F 85 8A 00`（jne），裝好的是 `E9 8B 00 00`（jmp），位置在一個 far call 之後的 `or ax,ax`。這是安裝後的修補，來源沒找到（INSTALL.SYS、INSTALL.EXE 的 UNPACK 路徑都沒有），檔案時間和包的日期相同。匯出不用 MAIN.EXE 的這一段。
  - 安裝後多出的檔是 INSTALL.SYS 的 MakeNewFile（全 0 的存檔等）與 README。
- 提督の決断III パワーアップキット（DPACK1–3.T3P）、三国志V（DPACK1–7.S5）都能解到 opcode 14，無錯誤。
  - 三国志V 解出的 64 個檔和 `san5pk-pc98` 的同名檔相同；KAODATA.S5（1,407,360 bytes）正好是 PK 版的前段。
- 解出的檔放在 `games/tk3-pc98/`（本體＋README.TXT）、`games/tk3pk-pc98/`（本體再疊上 PK，PK 的安裝程式也裝到同一個 `\TEKE3`）、`games/san5-pc98/`。
