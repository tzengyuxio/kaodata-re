---
status: in-progress
created: 2026-11-08
---

# PC-98／PC-88 磁片映像整理

目標：同一款有 FD 也有 HD 映像的只留 HD；只有磁片的試著安裝、把裝好的資料打包當研究來源；可以刪的磁片映像集中到一處，讓使用者確認後再刪。

## 現況

- **可刪清單**：61 項、約 2.2 GB 已用 `mv` 移到 `games/archives/to-delete/`（保留 `archives/` 底下的相對路徑），每項的理由寫在 `games/archives/to-delete/README.md`。分兩類：
  - 重複：CRC 相同或逐 sector 相同（neo-kobe 的 `Koei.zip` 1.9 GB、`pc98/x/`、`disks/tk*-zip`、`install/tk3-pc98/fdi`、`eiketsu-pc98-src`、5 個散放的 FDI）。
  - 有 HD：用 FAT 讀取器把 FD 與 HD 的檔案逐一比 SHA-1，FD 的檔案全部包含在 HD 裡（安裝程式、磁片 ID 檔除外）。
- 引用到被移走來源的筆記已加註「2026-11-08 移到 `games/archives/to-delete/`，2026-11-09 已刪除」與替代來源：`notes/genpei.md`、`san1.md`、`san2.md`、`nobu5.md`、`nobu6.md`、`koukai.md`、`progen.md`、`koei-games.md`、`eiketsu.md`、`kouryuuki.md`、`liberty.md`、`koei-platforms.md`。
- **安裝**：`~/game-library/_original/pc98/installed/` 有 `tk3-pc98.zip`、`nobu6-pc98.zip`、`tk2-pc98.zip`、`tk2pk-pc98.zip`，來源、做法與比對結果見同目錄的 `README.md`。
- **PC-88**：neo-kobe 各 Set 與 [Alt] 之間沒有完全相同的映像；`inindou-flux` 的 D88 B／C／D 和 neo Set 1 逐 sector 相同，但 A 片不同，而且包裡還有別處沒有的 SCP／MFI／HFE，所以保留。PC-88 沒有移動任何檔案。

### 要使用者決定的（沒有移動）

使用者的決定（2026-11-08）：照建議。
- 留：三國志IV FD、大航海時代II JP zip（資料集是另一版）；提督の決断II 本體 FD（安裝少了 SCE.TK2、QSAVE.TK2）；提督の決断II PK zip（KAIGI.EXE 和 PACK.LZW 解出的不同，原因沒查）；三國志IV PK 的 JP rar HDI。
- 移到 `to-delete/`：天翔記本體 neo FD、提督の決断III JP zip（都已安裝成 `installed/`）；英傑伝、三國志V 的 neo FD（和 HD 只差安裝修補）；太閤立志伝II 的兩個 JP zip（留 neo HD）；三國志IV neo with-PK HD（留 JP rar）。明細在 `to-delete/README.md` 末段。

- 之後再以「檔案層級」比對還留著的日本分享包（2026-11-08）：逐 sector 不同、但遊戲檔（扣掉 MS-DOS 系統檔）的 SHA-1 全部在還留著的 neo-kobe 映像裡的，也移到 `to-delete/`：`[PC98] 太閤立志伝.zip`、`【PC98】三國志３.rar`、`【PC98】三國志４.rar`、`【PC98】三國志５　パワーアップキット.rar`。其餘留著：群雄伝（`MAIN.EXE`、`OPENEND.EXE` 不同）、風雲録（`MAIN.EXE` 不同）、大航海時代II（14 檔不同）、提督の決断II（`TEK2.DIR` 不在 neo）、三國志IV PK（38 檔只在 JP rar）、維新の嵐（FAT 讀不出，逐 sector 不同）；提督の決断、提督の決断II PK、ロイヤルブラッド 的 neo FD 已因重複移走，JP 的是剩下的那份。

原本的表：

| 遊戲 | 保留的 FD | 為什麼要決定 |
|---|---|---|
| 三國志IV | neo `Sangokushi IV [FD] [Set 1]`（JP rar 後來改移到 `to-delete/`，見下） | 資料集的 MAIN.EXE 和 HD 的完全不同，是另一版 |
| 大航海時代II | `[PC98] 大航海時代２.zip` | 資料集那版的 MAIN.EXE、MESSAGE.DAT、END_PUT.DAT 和 HD 不同 |
| 天翔記本體 | neo `Tenshouki [FD]`（21 片） | HD 只有含 PK 的版本；本體已裝成 `nobu6-pc98.zip` |
| 提督の決断II 本體 | JP zip、neo `[FD]`、`[FD] [Set 1]` | 同上，已裝成 `tk2-pc98.zip` |
| 提督の決断II PK | JP PK zip | `tk2pk-pc98` 資料集讀它的 PACK.LZW；已裝成 `tk2pk-pc98.zip` |
| 提督の決断III 本體 | JP zip | 已裝成 `tk3-pc98.zip` |
| 英傑伝 | neo `Sangokushi Eiketsuden [FD]` | 和 HD 只差 MAIN.EXE 0x116BE 起 3 bytes（安裝時的修補），可視為同版 |
| 三國志V | neo `Sangokushi V [FD]` | 同上（MAIN.EXE 0x70BDF），另外是 DPACK 的來源 |
| 太閤立志伝II | 三份 HDI（兩個 JP zip、neo HD） | 三份是不同的安裝，資料集和三份都一致；要不要只留一份 |
| 三國志IV PK | JP rar 的 HDI、neo with-PK HDI | 兩份不同，資料集對得上 JP 的 |

刻意保留：天翔記的 Data Editor 與 Save Data Character Editor FD（沒有 HD 版）。只有磁片、也沒有安裝程式的（三國志 I–III、全国版、群雄伝、風雲録、維新の嵐、ロイヤルブラッド、水滸伝、太閤立志伝、提督の決断、大航海時代、ジンギスカン、元朝秘史、ヨーロッパ戦線、伊忍道、ランペルール、リーディングカンパニー等）照舊保留。

- **2026-11-09**：使用者刪掉 `games/archives/to-delete/pc98/`（上面列的全部 PC-98 項目）。留下的發行包搬到 `~/game-library/_original/`：`pc98/`（日本分享包 9 個、`neo-kobe-2017-11-17/Koei/`、`installed/`）、`pc88/`（`neo-kobe-2016-02-25/`、`inindou-flux/`）、`x68/`（原本的 `games/archives/x68000/`），各寫一份 `SHA1SUMS.txt`。`games/archives/pc98/disks/`、`install/`、`pc88/disks/` 是解開的工作檔，留在 repo。筆記裡的路徑已改成新位置，已刪的來源標「已刪除」。

## 下一步

- 三國志IV、大航海時代II、神々の大地 的安裝重試：改用 `imgmount` 掛真正的映像，用 lldb 呼叫 `_Z11swapInDisksi`／`_Z14swapInNextDiskb` 換片，看安裝程式要哪一片再換。

## 負面結論

- 合併資料夾當 A: 安裝：安裝程式會辨識磁片時（神々の大地每片有自己的 `光栄.DIR`）會一直說「ＤＩＳＫが違います」→ 合併資料夾沒有「哪一片」的概念 → 要真的換片才值得重試。
- 三國志IV、大航海時代II 用同樣做法：安裝中途回到 A:>，試兩次都一樣（三國志IV 停在第 1 片的 MKFILE 之後，大航海時代II 停在 LZW 包解開之前）→ 原因沒查 → 換片的做法成功後再重試。
- 讀 MemBase+0xA0000 看 PC-98 文字 VRAM：讀到全是 FF → DOSBox-X 的 PC-98 文字 VRAM 不在那裡 → 改用 lldb 呼叫 `_Z23CAPTURE_ScreenShotEventb(true)` 截圖（silent 模式也能用）。
- 提督の決断II PK 只放 PK 檔安裝：建好 `C:\TK2PUK` 後要本體磁片，一直說「ディスクが違います」→ 把本體檔案一起放進 A: 才裝得完。

## 未收尾

- 全部沒有 commit：12 份 notes 的加註與本檔。`games/` 不進版控。
- `games/archives/to-delete/` 只剩 `README.md`（刪除紀錄），可以一起刪。
- 掃描與比對腳本（FAT 讀取器、映像清單）還在 session scratch，沒有升級到 `research/` 或 `scripts/`；要重做比對時得重寫或先搬出來。
