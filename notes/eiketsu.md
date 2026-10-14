# 三國志英傑傳（EIKETSU, DOS 中文版）頭像相關格式

`dekoei.py export eiketsu-dos` 用到的格式。來源是 `games/6.10_三國志英傑傳_killpeople.rar`（killpeople 是上傳者標記），包內的 `rhero/` 解開放在 `games/eiketsu-dos/`。

- 是 DOS 版：`PLAY.BAT` 執行 `REKO3IBM.COM`，它依序載入 `SBOPL2.COM`、`GRPDRV.EXE`、`TFDED.COM`，再跑 `OPEN.EXE`、`MAIN.EXE`、`END.EXE`。
- `MAIN.EXE`：MS C 編譯，MZ 檔頭 0x6A00 bytes，DGROUP 在檔案 0x371D0（"MS Run-Time Library" 在 DGROUP 0x8）。下文的 DGROUP 位址都從這裡算。

## FACEDAT.R3：頭像

- 開頭是 240 組 (u32 offset, u16 size)，offset 從索引結尾（0x5A0）算起。
- 讀取在 MAIN.EXE 檔案 0x17F67（開檔字串 DGROUP 0x92A "B:FACEDAT.R3"），畫頭像在 0x1802E：先解到 VRAM，寬 0x40、高 0x50。
- 每張是 TF-DCE 5.11 壓縮圖。解碼程式不在 MAIN.EXE，而是常駐的 `TFDED.COM`（"TF-graphic Data Expand Driver Ver 1.54"，T.Fujinuma，掛在 int 62h，處理程式在 0x104）。MAIN.EXE 0xD52C 用 `int 62h` 呼叫它，參數區塊是 (x/8, y, 來源 segment, 來源 offset, 旗標 1, 模式 0)。
- 驅動程式直接寫 VGA planar VRAM（640 寬，每列 80 bytes，從 0xC80 起）。`koei_games.decode_tfdce` 是照它改寫的 Python 版，240 張都和 unicorn 模擬 `TFDED.COM` 的結果逐 byte 相同。

### TF-DCE 格式

- 檔頭：
  - +0 是檔頭長度 n，從 +n 起依序是：
    - 每列 bytes 數（8）
    - u16 列數（80）
    - u16 每個 plane 的編碼方式，每 plane 4 bit
    - 1 byte 的 plane 順序（每 2 bit 一個 plane 號碼）
    - 1 byte 旗標：0x40 表示接著 32 bytes 色盤，0x20 表示接著字典（1 byte 筆數，每筆 2 bytes）
  - 頭像都是 `08 50 00 33 03 D2 20`：
    - plane 順序依檔案而定（D2 是 2、0、1、3）
    - 前三個 plane 壓縮，plane 3 不編碼，所以只用色 0–7
- plane 編碼方式：
  - 0：不動
  - 1：整面填一個 byte
  - 2：複製第 k 個 plane
  - 3：壓縮串流
- 壓縮串流按 byte 欄排：第 0 欄由上往下，第 1 欄由下往上，依此類推。指令看高 4 bit：
  - 0x00–1F：查字典，換成 (指令, 參數) 兩個 byte；參數取代原本要讀的那個 byte
  - 0x2X：往回 d（下一個 byte）個位置複製 X+3 個
  - 0x3X：同位置複製另一個 plane（第 X>>2 個），再做 X&3 的轉換：不變、反相、右轉 1、左轉 1。長度是下一個 byte+2
  - 0x4X：從左邊第 X+1 欄的同一列複製，長度是下一個 byte+2
  - 0x5X／0x9X：同位置的另一個 plane AND 遮罩。
    - 遮罩從 4 筆最近用過的表裡取（初值 00、FF、55、AA，各 plane 共用）。
    - X&0xC＝0xC 時，下一個 byte 是新遮罩。
    - 0x9X 的遮罩每個 byte 旋轉：55／AA 轉 1 bit，其他轉 2 bit。
  - 0x6X：接著兩個 byte，重複 X+1 次
  - 0x7X：X+1 個原樣 byte
  - 0x8X：下一個 byte 的低、高 4 bit 各擴成一個 byte，這一對重複 X+1 次
  - 0xA0–FF：下一個 byte 重複 c−0x9E 次
- 每寫一個 byte 就檢查一次，plane 寫滿時，執行到一半的指令也直接結束。

## 色盤

- 驅動程式 `GRPDRV.EXE` 設色盤（0x2A7B）：輸入是 B、R、G 各 4 bit，寫進 DAC 前換成 `v << 2 | v >> 2`。
- MAIN.EXE DGROUP 0xB0A 起有好幾組 16 色，前 8 色都一樣，頭像用的就是這 8 色：
  - `#000000 #2041A2 #E36100 #C371A2 #00B271 #82C3F3 #F3C351 #F3F3F3`
  - 換算法和三國志IV 相同，是 `(v << 4) | (v >> 2)`
  - 舊 `eiketsu face` 的 Windows 版色碼和這組幾乎一樣

## BAKDATA.R3：人物

- 0x1100 起有 384 筆 21 bytes 的記錄（`koei_games.load_eiketsu_dos_persons`）：
  - +0：姓名，6 bytes Big5，後面補 NUL 或空白
  - +6：半形片假名讀音
  - +14：頭像碼
- 第 0–255 筆是武將，256–383 筆是兵種、一般人物，和最後的李明、祝融、蔣琬、費禕、諸葛均、司馬徽、獻帝、董承。
- 0x1100 之前是 13 bytes 一筆的城鎮人物和道具表。+8 那個數字不是頭像碼，不匯出。
- 匯出時：
  - 兵種和一般人物（`EIKETSU_DOS_TROOPS`／`EIKETSU_DOS_FOLK`）不算角色，共 264 人。
  - 只有這類人物用的頭像，以第一個名字命名，分到「部隊」或「一般人物」組。
- 遊戲本身有不少頭像重複使用，照原資料匯出：
  - 孫堅／羽則／曹真
  - 李雄等五人
  - 王鐵／蔣然用騎兵隊的臉
  - 蔡勳和獻帝同一張
- `nameHistorical`：沙摩可→沙摩柯、劉貴→劉璝。劉瞱是劉曄的異體字，不填。
- 0xE0（白鬚老人）、0xE3 沒有人物使用，標「未使用」。
