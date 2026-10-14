# 航空霸業II（AIR2, DOS 中文版）頭像相關格式

`dekoei.py export air2-dos` 用到的格式。來源是 `games/航空霸業２_中文版_air2.rar`，是大陸網站的 DOSBox 打包版。遊戲檔在包內的 `air2/game/AM2/`，搬到 `games/air2-dos/`；包外的 `.url`、`.bat`、DOSBox 和 DLL 都沒有用。

## 版本

- 遊戲檔日期是 1996-03-23。字串是光榮台灣內碼（`koei_games.koei_tw_name` 可解）。
- 主程式 `AM2IBM.EXE` 有壓縮，執行時會印「Crack By (CB)」，是破解版。用 unicorn 跑完解壓 stub（要模擬 int 10h 和 int 21h AH=0Ah）得到映像，DS 在映像 0x3F100。匯出只讀頭像檔，不讀 EXE。

## 色盤

- DS 0x7FA0：16 色，每色 3 bytes，順序是 **G、R、B**，各 4 bit，色號是 PC-98 的編號。
- 載入 DAC 的函式（映像 0x31250）會對調色號的 bit 1、2，把 PC-98 色號轉成 VGA 的 DAC 號碼；頭像像素本身是 PC-98 色號，所以像素 v 直接取表中第 v 色。
- 換算：`(v << 4) | (v >> 2)`（DAC 寫 v << 2，同三國志V）。
- 結果：`#000000 #6182b2 #f3d300 #30a261 #d3a282 #c37151 #b2b2b2 #f3f330 #000000 #204182 #f35100 #107141 #f3c3a2 #82a2d3 #828282 #f3f3f3`。頭像沒用到第 7 色。

## 頭像：GDT 檔

- 每張頭像是一個未壓縮的 GDT：16 bytes 檔頭（`0200 0001 4000 5000 0800 0401 000a 0000`，寬 0x40、高 0x50），接著 64×80、4 planes byte-interleaved（每 8 點 4 bytes，byte k＝bit k，`genpei.decode_planar`），共 2576 bytes。檔案就是多張串接。
- 其他 GDT（地圖、背景等）檔頭第 3、4 byte 是 `01 00`，大小也對不上未壓縮的尺寸，應該是壓縮格式，沒有解；64×80 的只有下面 9 個檔。
- 匯出順序照 EXE 的資源表（DS 0x7C1A，資源編號從 0x1B6 起），group 用遊戲裡的字：
  - `SEC1.GDT`、`SEC2.GDT`：各 18 張，「秘書」。每 3 張是同一人的三種表情（普通、笑、困擾），共 12 人。
  - `STAFF1.GDT`–`STAFF5.GDT`：各 12 張，「幹部職員」（遊戲選單「幹部職員一覽」）。同樣每 3 張一人，共 20 人。
  - `MAKFACE.GDT`：10 張，「廠商」。依畫面推斷是飛機製造商的代表。
  - `CITYFACE.GDT`：8 張，「城市」。依畫面推斷是開設分公司、交涉時的城市代表。
- 共 114 張。頭像都按檔案載入，沒有頭像碼，所以不填 `code`。

## 人物

- 沒有人物資料：`AM2NAME.STR`、`AM2CITY.STR`、`AM2PLANE.STR` 等是航空公司、城市、機型的名字和說明，幹部、秘書、廠商代表都沒有名字。`characters` 是空的。
