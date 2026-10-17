# ケルトの聖戦（魔眼邪神，Windows 日文版）

`dekoei.py export celt-win` 用 `build_celt_win`。

## 來源

`games/archives/win/CELT_CD.mdx`：Daemon Tools 的 MDX（`MEDIA DESCRIPTOR` 2.01）。檔頭 0x40 bytes 之後是沒壓縮的 2048-byte 磁區（ISO9660，第 16 磁區在 0x8040），一直到描述區 0x265E040；描述區加密了，但用不到。切出 `[0x40, 0x265E040)` 就是 ISO，可以用 `bsdtar` 解開。

- `SETUP.INF`：「ケルトの聖戦 セットアップ」，Win 3.1 的 MS Setup，用到 WinG。
- `CELTWIN/`：遊戲本體，除了 WAV、KOB 幾乎都是 MS COMPRESS（SZDD，`koei_games.szdd_expand`），副檔名最後一字是 `_`；EXE 裡寫的檔名是 `A:GDT\GRAPHIC.DAT`、`A:HERODAT0.DAT`、`A:GDT\CELT01.PAL` 等。
- `CELTCDDT/`：CD 才有的 OGRAPHIC／EGRAPHIC.DAT（開場、結局的 220×320 等大圖）與 AVI。

CD 上的檔案日期是 1995-07 到 1996-02。用到的 5 個檔解開後放 `games/celt-win/`。

## 圖

`GRAPHIC.DAT` 由 `GRAPHOFS.DAT`（u32 偏移，894 項）索引。每項的檔頭是 6 bytes：

- `B` 或 `N`、4（bpp）、u16 寬（byte 數，像素寬是兩倍）、u16 高。
- `B` 是未壓縮的 4 bit 像素；`N` 是 NPK，和 `utils.unpack_npk` 相同（每 2 bytes 展開成 4 點，旗標位元選複製）。

第 209–371 項是 163 張 64×80 頭像，209＋n 是英雄 n 的臉，最後 5 張（158–162）沒有英雄用到，歸「不明」。頭像只用色號 0–7（兩張有幾點 8）。其他尺寸：168×144 是 186 幀動畫、128×128 是物品圖、640×12 是畫面框線等。

## 色盤

`*.PAL` 是 16 色，每色 u16：bit 15–10 是 G（6 bit），9–5 是 R（5 bit），4–0 是 B（5 bit）。用中文 DOS 版的截圖（`~/works/cdosgame/raw/chiuinan/img/intro/ch/c32/celtic/game2.png` 左上的頭像）對過顏色。

`CELT01`–`CELT04.PAL` 是主畫面的四季，色號 0–7 只有 CELT03 的色號 4 不同，其他場景（`KAIGI`、`MC01` 等）的 0–7 也大多相同。資料集用 `CELT01.PAL`。

## 人物

- `HERODAT0.DAT`：158 筆 38 bytes 記錄，+0 是序號，+2 的 bit 6 是女性；+0x24 都是 158。
- 人名：`CELTWIN.EXE` 0xBDACB 起 158 個以 NUL 結尾的 Shift-JIS 字串（バラー … トリスタン），順序同記錄。之後是あだ名（邪眼、フォモール王…）與部族名，沒有收。
- 訊息檔（`MAIN_MSG.DAT` 等）是光榮自訂的 2 bytes 碼，沒有解。
