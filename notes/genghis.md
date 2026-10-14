# 蒼狼與白鹿・成吉思汗（GENGHIS, DOS 中文版）頭像相關格式

`dekoei.py export genghis-dos` 用到的格式。來源是 `games/成吉思汗_中文版_khan-c.zip`，解開放在 `games/genghis-dos/`。

## 版本

- 英文 DOS 版 Genghis Khan（1989，部分資料寫 1990）的移植：`KAO.DAT`、`MONTER.DAT`、`PICDATA.DAT` 和英文版（`games/成吉思汗_英文版_genghis-khan.zip`）逐 byte 相同；`MDATA.CIM`／`SDATA.CIM` 換成中文名字（1992-11）。原作是 1987-12 的 PC-98 版。
- 中文版 `MAIN.EXE`（1993-04-26）是 EXEPACK，DGROUP 段值 0x1DED（MZ 檔頭 0x4290）。下文是解壓後的映像位址。

## 頭像：KAO.DAT

- 83 張 × 960 bytes，64×40 半高、3bpp，格式同三國志II DOS（`san2_pixels`），0x5CAA 讀取。頭像碼就是索引。
- 色盤：DGROUP 0x242F 以 int 10h AX=1002 載入，結果就是 `SAN2_PALETTE`（EGA）。

## 組合臉：MONTER.DAT（0x5B57／0x5C68）

- 頭像碼 bit 15 為 1 時是組合臉：`1 ccc vv TT BB EE NN MM`。
- `vv` 是頭型，每型 0x15C0 bytes，各 4 筆：上（19 列，offset 0）、下（21 列，0x720）、眼（7 列，0xF00）、鼻（6 列，0x11A0）、口（5 列，0x13E0）。都是半高、每列 24 bytes。
- 組法（臉緩衝區 DS:0x80B6）：
  1. 上（`TT`）放在第 0–18 列、下（`BB`）放在第 19–39 列。
  2. 0x955 把上下兩半中只有 plane 0 的像素（`to_3bpp_indexes` 的色號 4）換成 `ccc`（bit k → plane k）。
  3. 眼（`EE`）、鼻（`NN`）、口（`MM`）先拼進 432 bytes 的暫存區（第 12–18、19–24、25–29 列），0x5C94 再整塊以 XOR 疊到臉上。
- XOR 的三個部件彼此不重疊，但會和上下重疊，所以不能用一般覆蓋表示。匯出用規格的 `blend: "xor"`：眼鼻口是不透明的部件，色號 0＝不變。各 plane 分別 XOR 等於色號 XOR，換色又在 XOR 之前，所以把 `ccc` 烘進上下兩半就是精確的。
- 匯出成 32 個 variant（`ccc × 4 + vv`，id `vv-ccc`），code 用 bitfield，`$variant` 取 bit 15–10、base 32。用 game 的組法逐像素比對過 91 張組合臉，全部一致。

## 人物：MDATA.CIM／SDATA.CIM

- 蒙古篇（M）、世界篇（S）各一份，記錄首 byte 為 0 是空位，姓名 20 bytes 光榮台灣內碼（`koei_games.load_genghis_dos_people`）：
  - 君主 0x2E2，27 × 43 bytes，頭像碼 +0x27
  - 繼承人 0x76C，4 組 × 5 × 41 bytes（每組 205），+0x27
  - 部將 0xAEB，26 × 33 bytes，+0x1F
  - 子女 0xE46，4 組 × 5 × 32 bytes（每組 160），+0x1E
  - 女性 0x1E8A，40 × 34 bytes，+0x1C／+0x1E／+0x20 是平常／笑／哭三個表情（兩篇相同）
- `id` 依 `genghis-fc` 的順序：蒙古篇君主、繼承人、子女，世界篇君主、繼承人、子女，女性；接著是 FC 沒有的部將（蒙古篇再世界篇）。同名只收一次（兩篇的頭像碼一致）。0–114 和 FC 相同，115–151 是 DOS 才有的部將。共 152 人（91 組合臉、61 頭像），沒有未使用的頭像。
- `nameHistorical`：菲利浦一世→菲利浦二世（FC 是フィリップ2せい）、北鞗政子→北條政子、偪山重忠→畠山重忠（缺字）、斡鄰勒→脫斡鄰勒（少字）、摩柯末→摩訶末、江宗→襄宗（英文版 Chiang Tsung，推斷是西夏襄宗）。
- 未決定、沒填：高麗（英文版 Ghori）、合欽、岐國。

## 發行年份

- 英文 DOS 版 1989（部分資料 1990）；原版 PC-98 1987-12；中文版 MAIN.EXE 1993-04。
