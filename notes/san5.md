# 三國志V 威力加強版（SAN5PK, DOS 中文版）頭像相關格式

`dekoei.py export san5pk-dos` 用到的格式。來源是 `games/6.3_三國志五DOS加強版_killpeople.rar`（killpeople 是上傳者標記），解開放在 `games/san5pk-dos/`。

## 版本檢查

- 是威力加強版（PK）的資料：
  - `INSTALL.INI`（1997-01-15）是 PK 的安裝設定，標題「三國志加強版」，要先裝好本體（`DISK02VOL SAN5PUK`）。
  - `SNDATA.S5`、`TAIKI.S5`、`MESSAGE.S5` 的日期是 1997-01-14，和 PK 安裝程式同期。其他本體檔多是 1996-06／07。
  - `SNDATA.S5` 有 12 個劇本。ja.wikipedia〈三國志V〉說本體 7 個、PK 加 4 個。
  - `VERSION.S5`：「三國志V中文版／1996/06/27／光榮軟件有限公司」。
- 頭像和人物資料沒看到修改跡象：
  - `KAODATA.S5`（1996-06-17）和 `KAODATAP.S5` 逐 byte 相同，日期是原廠的。
  - `SNDATA.S5` 的劇本 offset 和 `gadgets.get_san5_name_list`（作者自己那份 SAN5）寫死的 offset 一致。
  - 不過手上沒有官方原檔，無法逐 byte 比對。
- `MAIN.EXE` 改過（日期 2000-03-11）：
  - 附有 `CRACK.TXT`（Martin Wu 的光碟檢查破解）：0x14533 75→EB、0x1A7BF 00→01、0x98DAA 75→EB。
  - 目前檔案只有 0x1A7BF 是 01，另外兩處仍是 75，所以實際改了什麼不確定。
  - 匯出不讀 `MAIN.EXE`，只拿它的程式碼當參考。

## MAIN.EXE

- MZ 檔頭 0x5600 bytes，有 47 個 MS-LINK overlay（各自有 MZ 檔頭，第一個在檔案 0x5E200）。
- DGROUP 在檔案 0x51F50（段值 0x4C95）。0xBDAD0 `push 0x5AB2` 指向字串 "KAODATA.S5"。下文的位址都是檔案 offset。

## KAODATA.S5：頭像

- 783 張，每張 64×80、3bpp planar、全高，1920 bytes，沒有壓縮。
- 每列 24 bytes，byte k＝色號 bit k（同 `genpei.decode_planar`）。
- 頭像碼就是索引（0 起算），人物用到 0–499，一碼一人。
- 色盤：
  - DGROUP 0x5C94 起 16 色（0xC2967 載入），每色 3 bytes（B、R、G，各 4 bit），頭像用 8–15 色。
  - 換算同三國志IV：`(v << 4) | (v >> 2)`。
  - 結果：`#202010 #104171 #B23000 #B27141 #206110 #618292 #E3A282 #E3D3C3`。
  - 和舊 `san5 face` 的 WIN 編輯器色碼相近，順序是 `to_3bpp_indexes` 的 bit 0、2 對調。

## 人物

- `SNDATA.S5`、`TAIKI.S5` 開頭都是 u16 劇本數（12），接著每劇本 (u32 offset, u16 size)，offset 從索引結尾算起（`sango.san5_parts`）。
- SNDATA：
  - 人物表在每個劇本的結尾前 1100 bytes 結束。
  - 每筆 38 bytes：姓名 10 bytes，+30 是 u16 頭像碼。
  - 往前找到第一筆不像姓名的記錄為止（`sango.load_san5_persons`）。
- TAIKI：每筆 69 bytes，+31 起是同樣的 38 bytes。
- 依劇本 1–12、每個劇本先 SNDATA 再 TAIKI 的順序，以頭像碼去重，共 500 人，`id` 就是這個順序。
- 頭像碼和姓名一一對應。同名只有馬忠（222、452），本來就是兩個人。
- `nameHistorical`（規則見 CLAUDE.md）：孔岫→孔伷、龐義→龐羲。不填的：異體字劉瞱（劉曄）、關彞（關彝），《三國演義》寫法范疆（范彊）。
- 華佗、司馬徽、許子將、于吉、左慈、管輅、南華老仙都是劇本人物（492–499），不算未使用頭像。

## 沒有人物使用的頭像（500–782）

- 新武將的挑臉函式在 overlay 16（0x8D420、0x8D21C、0x8D170、0x8D2B7）。
  - 記錄 +0x46 是性別旗標：參數為 0 時設成 1。
  - +0x4E 是起點：0x1FC（508），旗標為 0 時再加 0x75，得 625；翻頁時每頁加 32。
  - +0x50 是終點：0x270（624），旗標為 0 時再加 0x6C，得 732。
  - 超過終點後接到 0x2DD（733），旗標為 0 時再加 0x19，得 758。
  - 依畫面判斷旗標 1 是男、0 是女：
    - 新武將（男）：508–624、733–757
    - 新武將（女）：625–732、758–782
  - 733–782 的畫風和前面不同。
- 500–507 事件人物：
  - DGROUP 0x8E7A 起有 6 bytes 一格的名字表：獻帝、貂蟬、民眾、使者、士兵。
  - 兩人都不是劇本人物，依名字順序和畫面對應：
    - 500 獻帝
    - 501 貂蟬
    - 502–505 民眾（四張不同的平民）
    - 506 使者（官帽）
    - 507 士兵（頭盔）
  - DGROUP 0x5EFE 也有 [500…507] 的表。
  - 這兩張表都沒找到直接存取它們的程式碼，所以頭像和名字的對應是推斷的，之後在 koei.wiki 確認。

## KAOEX.S5：追加頭像（783–1164）

- 382 張，格式同 KAODATA（64×80、byte k＝bit k、1920 bytes、無壓縮）。DOS 和 PC-98 的檔案相同。
- PK 的挑臉對話框（PC-98 MAIN.EXE 0x6AC08）開啟 `KAOEX.S5`，選擇器 0x68744 的總數是 0x48D＝1165＝783＋382，每頁 32 張；碼 ≥ 783 讀 KAOEX 第（碼 − 783）張。劇本人物沒有用到，只在武將編輯、新武將換臉時可選。
- 第 0–95、97–159 張就是三國志IV `KAODATA.S4` 的第 0–95、97–217 張，連色號都相同（第 96 張不一樣）；其餘 222 張和三國志III、IV 都對不上，來源待考。
- 匯出時接在 KAODATA 後面，code 從 0x30F 起，group「追加頭像」。

## 發行年份

- ja.wikipedia〈三國志V〉：
  - 本體 PC-98 1995-12-15，PK PC-98 1996-07-19
  - Win3.1 1996-03、PK 1996-09
- Wikipedia 沒列 DOS 版。網站採用 PK 原版年份 1996。

## PC-98 日文版 PK（`san5pk-pc98`）

`dekoei.py export san5pk-pc98` 用到的差異。來源是 `games/pc98/【PC98】三國志５　パワーアップキット.rar` 的 HDI 硬碟映像（已安裝 PK），解出放在 `games/san5pk-pc98/`。

- `KAODATA.S5`、`KAODATAP.S5`、`KAOEX.S5` 和 DOS 中文版逐 byte 相同。`KAODATAP.S5` 是遊戲讀人物頭像用的工作副本（0x884E3 開檔，0x68704 讀取），原廠內容和 KAODATA 相同，匯出照舊用 KAODATA。
- `MAIN.EXE`：MZ 檔頭 0x5400，DGROUP 在檔案 0x51250（段值 0x4BE5）。
- 色盤：DGROUP 0x910 的 16 色和 DOS 逐 byte 相同。`GRP98W.EXE` 0x15F6 寫 port 的順序是 B→0xAE、R→0xAC、G→0xAA。PC-98 類比色盤每色 4 bit，所以用 v × 17：`#222211 #114477 #BB3300 #BB7744 #226611 #668899 #EEAA88 #EEDDCC`。256 色驅動（`GRP9821.EXE` 等）只用在地圖（`PAL256.S5`），頭像仍是 16 色。
- 人物：SNDATA／TAIKI 的結構、每筆的劇本和頭像碼都和 DOS 相同。38 bytes 記錄的姓名欄改成 8 bytes Shift-JIS＋NUL，+9 起是半形片假名讀音，所以往前找人物表起點的條件改成「首 byte ≥ 0x81、+8 為 0、+9 是半形假名」（`sango.load_san5_persons(..., pc98=True)`）。讀音不匯出。
  - 外字：SJIS 0xEB9F 起，字形在 `FONT.S5`（92 個 16×16 字），人名用到 42 個（`sango.SAN5_PC98_GAIJI`）。
  - 500 人，順序同 DOS。頭像碼 199 在劇本 1、2 寫蘆植（錯字），8、9、12 寫盧植，取盧植（`SAN5PK_PC98_NAME_PICK`）。
  - DOS 的錯字孔岫、劉瞱、關彞，日文版是正確的孔伷、劉曄、関彝；龐義兩版都錯，填 `nameHistorical`；范疆是《三國演義》的寫法，不填。
- 未使用頭像和 DOS 相同（新武將挑臉在 0x839F8 等處）。事件人物的名字表在 DGROUP 0x35BA：500 献帝、501 貂蝉、502–505 民衆、506 使者、507 兵士，對應同樣是推斷的。
- 發行年份：PK PC-9801 版 1996-07-19（ja.wikipedia〈三國志V〉）。

## PC-98 本體（`san5-pc98`）

- `games/san5-pc98/` 只有安裝片：`INSTALL.EXE`（KOEI Install Program Ver 2.1）照 `INSTALL.SYS` 的 `UNPACK DPACKn.S5` 解出 7 個包。
- DPACK 用 `dekoei/dpack.py` 解開（格式見 [dpack.md](dpack.md)），解出的檔放在 `games/san5-pc98/`：64 個檔和 `san5pk-pc98` 的同名檔相同，KAODATA.S5 是 PK 版的前段。
- `dekoei.py export san5-pc98` 用 `build_san5pk(pc98=True, pk=False)`：
  - KAODATA.S5 是 733 張（PK 的 0–732），沒有 KAOEX.S5。
  - 劇本只有 7 個；SNDATA.S5 每個劇本的人物表後面只接 64 bytes（PK 是 1100），`sango.load_san5_persons(tail=64)`。TAIKI.S5 的記錄格式相同。人物（500 人）、名字、頭像碼都和 PK 相同。
  - 新武將挑臉（MAIN.EXE 檔案 0x79830）：起點 0x1FC（508），旗標為 0 時加 0x75（625），每頁 32 張，第 4 頁男 21 張、女 12 張，所以是男 508–624、女 625–732，沒有 PK 的 733–782。
  - 頭像色盤在 MAIN.EXE 檔案 0x49E2A，值和 PK 相同。
- PC-98 本體 1995-12-15 發行。
