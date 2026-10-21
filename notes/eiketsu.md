# 三國志英傑傳（EIKETSU, DOS 中文版）頭像相關格式

`dekoei.py export eiketsu-dos` 用到的格式。來源是 `games/archives/dos/6.10_三國志英傑傳_killpeople.rar`（killpeople 是上傳者標記），包內的 `rhero/` 解開放在 `games/eiketsu-dos/`。

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

### 能力

- 人物記錄 +17 統率、+18 武力、+19 知力（u8，0–100）。0x3080 起 384 筆 18 bytes 的初始狀態和記錄一一對應：+0 bit 7 恆為 1、低位推定是勢力，+4 士氣，+5 u16 兵力，+7 兵種，+8 等級，+10–17 道具（BAKDATA 0xD00＋16×id，FF＝空）。讀取用 `koei_stats.load_eiketsu_dos_stats`，`dekoei.py koei-person eiketsu-dos`。
- ✅ code：`MAIN.EXE`（load image）0x13542 把兩張表寫進人物物件；攻擊力公式 0x12F6A 讀 +18（武力）、防禦力 0x13098 讀 +17；武將視窗 0x25DBC 依序顯示 武、知、統。標籤是圖示，EXE 裡沒有「知力」「統率」字串，這兩個名稱只依數值推定（諸葛亮 知 100、呂布 21；關羽 統 100）。
- ✅ cross：PC-98 的記錄 +14–20 與整張狀態表和 DOS 相同；關羽 青龍偃月刀、張飛 蛇矛、呂布 赤兔馬＋方天畫戟。兵種名稱照 `MAIN.EXE` 的字串順序（DOS 0x37BF8、PC-98 0x358B0，19 種）對應，🟡。
- 等級只有狀態表有值（曹操 18、諸葛亮 30），其他代的記錄都是 1。
- ❌ 記錄 +16、+20，狀態表 +1–3、+9；策略值公式（0x25F07）、策略的學習表沒有找到。PC-98 的道具名有 `EIKETSU_PC98_GAIJI` 沒收的外字（青〓の剣）。

## PC-98 版（`eiketsu-pc98`）

來源是 `games/archives/pc98/[PC98] 三国志・英傑伝.zip` 解出的 `eiketsu-pc98-src/SANEI_1–4.FDI`，每片解在 `games/archives/pc98/disks/eiketsu-pc98/`，合併放在 `games/eiketsu-pc98/`。`MAIN.EXE` 1995-01-25。

- `FACEDAT.R3` 和 DOS 中文版逐 byte 相同。PC-98 的 `TFDED.COM`（1959 bytes）把 plane 0–3 寫到 0xA800、0xB000、0xB800、0xE000（表在 0x6B6），也就是 B、R、G、E，色號和 DOS 相同。
- 色盤：`MAIN.EXE` 檔案 0x359AC 是 DOS DGROUP 0xB0A 的同一張 B、R、G 表，PC-98 類比色換算 v × 17：`#000000 #2244aa #ee6600 #cc77aa #00bb77 #88ccff #ffcc55 #ffffff`。
- `BAKDATA.R3` 記錄位置、格式同 DOS，384 筆的頭像碼完全相同；名字是 Shift-JIS，光榮外字 `EB xx` 的字形在 `FONT.R3`（87 字 × 16×16）。外字對照（`koei_games.EIKETSU_PC98_GAIJI`）是拿 DOS 中文版同一筆的名字對齊，再看字形確認的：
  - C4 是「璝」（中文版寫成劉貴，日文版是劉璝）。
  - AE 的字形是「鷙」（鳥字底），日文版寫成歩鷙，中文版是步騭。
  - E2 對齊是「邈」（張邈），但 `FONT.R3` 第 0xE2 − 0x9F 個字形不是邈（0xDF 那格才是），E0 之後的對應方式沒有查。
- 兵種、一般人物用日文名稱（`EIKETSU_PC98_TROOPS`／`EIKETSU_PC98_FOLK`），共 264 人，分組和 DOS 相同。
- `nameHistorical`：沙摩可→沙摩柯（日文版也是這樣寫）、歩鷙→歩騭；宋謙→宋憲（呂布的部將）、蔡仲→蔡中，這兩筆在 BAKDATA 是一般 Shift-JIS 碼（8CAA 謙、9287 仲），不是外字，是遊戲本身的寫法（DOS 中文版寫宋憲、蔡中）。

## 戰場地圖（PC-98）

`dekoei.py eiketsu battlemap --game-dir ../games/eiketsu-pc98 --out ../games/eiketsu-pc98/extract/battlemap`（`koei_games.render_eiketsu_battle_maps`），輸出 `00.png`–`57.png`，檔名是 HEXZMAP 的段號。下文位址是 PC-98 `MAIN.EXE` 的檔案位移（DGROUP 在 0x35370）。

- `HEXZMAP.R3`：LS11，59 段，前 58 段是戰場。每段是寬、高（以 16 px 的圖塊為單位）2 bytes，接著寬×高個圖塊號，最後是 (寬/2)×(高/2) 的地形格（一格 32 px，地形值的意義沒查）。✅ code：0x242F6 開檔，段號是參數結構的第 0 byte，寬、高右移 1 存到 DGROUP 0xD518／0xD519。
  - 第 58 段（388 bytes）不是戰場；DOS 版的 HEXZMAP 只有這一段和 PC-98 不同，其他段 byte 相同。
- `HEXZCHP.R3`：LS11，3 段，每塊 128 bytes＝16×16、4 個 plane 各 32 bytes（plane 0 是 bit 0）。✅ code：0x241DB 把第 0 段（80 塊）讀到開頭，再把第 1 或第 2 段接在 0x2800（80 塊）之後。
  - 用哪一段由 0x257AC 決定：地圖號在 DGROUP 0x32BC 的 19 個 u16（0 1 4 8 10 16 20 28 29 30 35 36 39 40 42 43 44 50 52）裡就用第 2 段（175 塊），否則第 1 段（174 塊）。✅ cross：圖塊號 254 只有第 2 段才有，用到 254 的只有地圖 0 和 52，兩張都在表裡。
- 色盤：0x359AC 起 9 組 16 色（B、R、G 各 4 bit，前 8 色是頭像色），0x159B8 依遊戲狀態結構 DGROUP 0x6DF0 的 +5 低 4 bit 選一組（呼叫者在 0x15A30）。
  - 套在地圖上看：0 偏藍、1 和 3 是綠地、2 和 5–8 是黃土、4 是 0／F 的閃光用。
  - 🟡 +5 在哪裡設定沒追到（沒有直接寫 DS:0x6DF5 的指令，推定是整塊載入）。`--palette` 預設 1，每張實際用哪組沒和遊戲畫面比過。
- 交戰畫面的背景：`dekoei.py eiketsu battlebg`（`koei_games.render_eiketsu_battle_backgrounds`），輸出 `0.png`–`8.png`。
  - ✅ code：0x2F856 是兩軍交戰的側面畫面（附近的訊息是「反撃しました！」「反撃された！」）。它讀 `HEXBCHP.R3`（1 段 224 塊，編碼同 HEXZCHP），再讀 `HEXBMAP.R3` 的兩段：段號查 DGROUP 0x428A 和 0x429E 的 20 筆表（索引是參數結構 +0xC，推定是地形種類），分別放到 +0x2110、+0x21F6。
  - 表一 `4 3 0 0 1 0 2 4 4 0 0 0 0 2 4 2 2 0 0 0` 選第 0–4 段（230 bytes），是遠景：23×10 塊，藍天、白雲、遠山。表二 `7 7 7 5 6 5 5 7 7 5 5 8 5 5 7 5 5 5 5 5` 選第 5–8 段（528 bytes），是地面：24×22 塊。
  - 🟡 寬 23、24 是看圖試出來的。第 6 段的地面只用 8、9、10 號色，用戰場色盤（8 號是黑色）畫出來每隔一列是黑線，交戰畫面可能另設色盤，沒追到。

## Win31 版（不另做資料集）

來源是 `games/archives/win/[系列] 英傑傳/三國志英傑傳 Win31 繁體化 (reko_win).zip`：DOSBox＋Windows 3.1 的整包，遊戲在 `reko_win/C_DRIVE/R3WIN/`，`R3WIN.EXE`（Win16）與同人繁體化修改的 `R3W_CHT.EXE`。沒有找到 Win31 版的發售日。

- `FACEDAT.R3` 是 LS11，240 段，每段是 NPK016（檔頭 0x10 的 16 色是通用色、不是遊戲用的；資料從 0x30 起，`utils.unpack_npk`，64×80 4 bpp）。
  - 和 DOS／PC-98 版是同一批圖、同樣順序，色號一對一：DOS 的 0 在 Win 是 8（都是黑），其他相同。
  - 只有 4 張共 137 點不同，DOS 的色 1／3 在 Win 是 9／11（多了 bit 3）：5 徐庶 68 點、164 劉璝 63 點、7 魏延 1 點（1→9），18 劉封 5 點（3→11）。都在帽緣，用 R3WIN 的色表是 9＝#aabbaa、11＝#3377aa，遊戲中看得到，可能是刻意加的亮點，也可能是轉檔的雜點，還沒確定。
- 色盤：`R3WIN.EXE` 檔案 0x3E8DC 起的 B、R、G 4 bit 色表和 PC-98 `MAIN.EXE` 0x359AC 相同，所以頭像色和 `eiketsu-pc98` 一樣。
- `BAKDATA.R3` 和 DOS 中文版逐 byte 相同（繁體化時換掉的），這份檔裡沒有日文 Win 版的人名。
- 結論：圖、色同 `eiketsu-pc98`，人名同 `eiketsu-dos`，不另做 `eiketsu-win`。kaodata 在 `src/ui/editions.ts` 把它列在 `eiketsu-pc98` 下（WIN 標籤＋說明），比較圖在 kaodata 的 `docs/images/eiketsu-win-vs-pc98.png`。
