# legacy

2023 年初期放在根目錄或 `dekoei/` 的小工具，現在的流程不再用到，留著備查。都沒有被 `dekoei/` 引用；`dekoei/` 來的兩支原本在 `dekoei/` 下用平面 import 跑（`from utils import *`），搬過來後不能直接執行。

| 檔案 | 用途 |
|---|---|
| `annotate.sh` | 在圖的右下角加一條標籤（`[key] 網址`），ImageMagick `convert` |
| `watermark.sh` | 在三國志V 頭像總表加署名，一次性指令 |
| `build_name_key.py` | 讀能力值 CSV（`ROTK - Character Stats & Abilities.csv`），找出各代的武力、智力、政治、魅力欄位 |
| `game_infos.py` | 早期的遊戲資訊表（頭像檔名、尺寸、色盤），已被 `dekoei/kaodata_export.py` 取代 |
| `get_colors.py` | 列出一張圖某個區塊用到的顏色 |
| `gadgets.py` | 一次性的雜項函式：合併項劉記、拿破崙的人物表，三國志III–V 的名單，源平合戦 OPENDAT 檔頭（原在 `dekoei/`） |
| `gen_font_table.py` | 把 CNS 11643 → Unicode 對照表寫成 JS（`mytable.js`）（原在 `dekoei/`） |
