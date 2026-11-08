---
status: todo
created: 2026-11-08
from: koei-wiki
sources:
  - koei-wiki@4b5de63:docs/places-format.mkdn
  - koei-wiki@4b5de63:EDITORIAL.mkdn
  - kaodata-re@bd9515e:notes/san-maps.md
  - kaodata-re@bd9515e:notes/nobu3.md
  - kaodata-re@bd9515e:notes/nobu4.md
  - kaodata-re@bd9515e:notes/nobu5.md
  - kaodata-re@bd9515e:notes/nobu6.md
---

# 三國志 1–5 代、信長之野望 1–6 代的大地圖匯出給 koei-wiki

## 結論

koei-wiki 各代的地點一覽頁（三國的 `遊戲/<作品>/都市資料一覽`、信長的 `遊戲/<作品>/國資料一覽`）要放大地圖。請解出下列各代 PC 版的大地圖，渲染成 PNG，放在既有地點匯出的資料夾裡：`export/koei-wiki/places/<dataset>/world/<檔名>.png`（`docs/places-format.mkdn` 已預留 `world/`）。

| 作品 | dataset（和地點匯出相同） | 筆記裡的現況 |
| :--- | :--- | :--- |
| 三1 | `san1-pc98` | 地點沒有 `pos` |
| 三2 | `san2-pc98` | 41 州有 `pos`（`hex-axial`）；地圖圖檔沒有輸出 |
| 三3 | `san3-pc98` | 有 `pos`（`hex-offset`，15 × 16，相鄰表就是這張六角格表）；圖檔沒有輸出 |
| 三4 | `san4pk-pc98` | 沒有 `pos` |
| 三5 | `san5pk-pc98` | 沒有 `pos` |
| 信1 | （koei-wiki 沒有信1 的地點資料） | 見「未定」 |
| 信2 全國版 | `nobu2-pc88`（戰場圖用的是 `nobu2-dos`） | 沒有 `pos` |
| 信3 | `nobu3-pc98` | 大地圖是 `MAPDATA.DAT`，國號畫在圖上，各國位置沒找到 |
| 信4 | `nobu4-pc98` | `MAPDATA.DAT`（DOS 和 PC-98 內容不同）沒解 |
| 信5 | `nobu5pk-pc98` | 推定是 `M_CHIKEI.NB5`；城記錄裡沒有座標，筆記建議從地形格的城格（0x1A）反推 |
| 信6 | `nobu6pk-pc98` | `MAINMAP.NB6` 已解，214 座城的 `pos`（`square`，170 × 42）都對上；看筆記沒有輸出整張圖 |

- 每代至少一張「乾淨的」大地圖，就是遊戲畫面上看到的底圖。有季節、劇本或勢力上色的變化時，先給一張代表圖（例如春季、不上色），其他的有餘力再給。
- **同時補上或校正 `pos`**，讓座標能直接對到交付的圖：`pos.w`、`pos.h` 是這張圖在同一單位下的寬高。koei-wiki 會用 `pos` 自己在圖上標編號或地名，所以圖上不用另外加字。遊戲圖上原本就有的國號、州名照遊戲原樣保留。
- 可以分代交付，先交解得出來的（例如信6、三2、三3）。每代交付時附 commit，以及 `pos` 的驗證結果：所有座標都在圖的範圍內，且落在地點格上（N checked, 0 mismatched）。

## 為什麼由這裡做

大地圖的檔案格式、色盤和座標都要從遊戲檔解出來。讀檔程式、各代筆記和地點匯出都在 kaodata-re；koei-wiki 只讀匯出結果放上頁面，不碰遊戲檔。

## 已定與未定

- 已定（koei-wiki 的頁面規則，不用重新討論）：
  - 大地圖只放在各代的一覽頁，地點條目不放（凡例 §3.3）。
  - 圖放 koei-wiki 的 `assets/maps/<作品>/`，不上 R2（比照拿破崙、水滸的 FC 大地圖）。
  - 要用 PC 版的圖：koei-wiki 一覽頁的編號、國數、相鄰都來自這些 PC dataset，圖要和這些資料對得起來。
- 未定（開工時先決定，或問使用者）：
  - 信1（1983）：koei-wiki 目前沒有信1 的人物或地點資料。要做的話，連地點表一起匯出（`koei-places/1`，資料集 ID 依 kaodata 慣例），還是這次先跳過。
  - 色盤：PC-98 是數位或類比 16 色，沒有截圖驗證的，在交付說明裡標 🟡。
  - 信5：PC-98 解不出來時，能不能改用 Windows 版 `Map.dll` 101–104 已經輸出的四季大地圖（`map/world_1–4.png`，1920 × 376）。兩版的城數相同（173），但城的位置要對得起來才行。
  - 三2、三3 的六角格要怎麼渲染（格子大小、要不要畫道路），依遊戲畫面決定。

## 使用者的決定（2026-11-08）

- 信1：這次先跳過，之後連地點表一起做。
- 信5：先試 PC-98；解不出來時可以改用 Windows 版 `Map.dll` 的四季圖，但城的位置要對得上才交付，交付說明註明是 Windows 版。

## 進度

| 作品 | 狀態 | 證據 | 說明 |
| :--- | :--- | :--- | :--- |
| 信6 `nobu6pk-pc98` | ✅ | capture | `world/MAINMAP-spring.png` 2720×672（一格 16 點）；`pos` 照舊是 170×42 格、城 2×2 的左上角；214 城都落在城格上，places-export 2128 checked, 0 mismatched；春季色盤和截圖相符（地圖區 93.3% 的點相同，其餘是城上的勢力旗） |
| 三2 `san2-pc98` | ✅ | capture+cross | `world/MAPDATA.png` 296×400（主畫面左半的地圖面板原樣，州白色、有遊戲的州號、外框與日期框）；`pos` 改成圖上的像素（`pixel`，w 296、h 400），每州取白色區塊裡離州界最遠的點；places-export 536 checked, 0 mismatched（含 41 州各在自己的白州上、圖上相鄰 93 條和 `adjacent` 相同），koei-wiki `verify_sanguo_places.py` 556 checked, 0 mismatched；圖和截圖白州以外 99.9% 相同，數位 8 色 |
| 三3 `san3-pc98` | ✅ | code+emu+capture+cross | `world/MAPDATA-spring.png` 640×400（整個主畫面原樣：空視窗框、遊戲的地點號、州的黑色方塊）；`MAPDATA.DAT` 是三段壓縮，解壓照 `MAIN.EXE` 0x1E0F 移植，和 Unicorn 跑原函式逐點相同；`pos` 改成像素（`pixel`，w 640、h 400），州取黑色方塊中心、據點取藍色編號框中心，號碼從圖上讀出（1–68 各一次）；places-export 612 checked, 0 mismatched（含 68 個地點各在自己的方塊／藍框上），koei-wiki `verify_sanguo_places.py` 771 checked, 0 mismatched；春季色盤和截圖 `main_005` 地圖區 97.5% 相同；夏、秋、冬另有色盤（冬有截圖），未輸出 |
| 三4 `san4pk-pc98` | ✅ | code+capture | `world/MAINMAP.png` 1536×1280（`MAINMAP.S4` 96×80 格的第 0–7 層 × `MAINCG.S4` 16×16 圖塊，繪圖照 `MAIN.EXE` image 0x1E990；城的圖示在圖上，勢力旗與地名是程式另畫的，沒有）；`pos` 新增，`pixel`（w 1536、h 1280），取地圖第 8 層（都市號）上城 3×3 圖示正中那格的中心；places-export 1106 checked, 0 mismatched（含 43 城都在自己的城圖示正中、3×5 點擊區完整、沒有多出來的都市；故意移一格或對調會被抓到），koei-wiki `verify_sanguo_places.py` 1322 checked, 0 mismatched；色盤是程式設定的 DS:0x1136，和截圖 `np2kai-01`（12 月）地圖區 98.0% 一一對應，色號 0、8–15 相同（capture），1–7 截圖偏冬季色，季節改色沒找到（🟡） |
| 三5 `san5pk-pc98` | ✅ | code+capture | `world/MAINMAP.png` 800×592（`MAINMAP.S5` 原圖，城與地名畫在圖裡）；`pos` 新增，`pixel`（w 800、h 592），都市表 +24、+26 的 32×32 框左上角 ＋ (16, 12)；places-export 526 checked, 0 mismatched（含 47 框在圖內不重疊、框下有置中的地名、截圖 `guest-os-000` 裡 7 個有主都市的勢力旗都在框 ＋ (0, −13)；逐城移 8 點，188 次抓到 182 次），koei-wiki `verify_sanguo_places.py` 590 checked, 0 mismatched；預設色盤和截圖（12 月）地圖區 97.6% 一一對應，色號 0、5、6、8–15 相同（capture），1–4、7 偏冬季色（🟡） |
| 三1 `san1-pc98` | ✅ | code+emu+cross | `world/PACKDATA-000.png` 320×400（`PACKDATA.DAT` block 0 的 320×200 逐列加倍，國號畫在圖上）；block 0 在磁碟 A 加密的磁區上，解法從磁碟上破解過的 `COMMAND.COM` 讀出、用 Unicorn 跑它的假 int 1Bh 核對（`notes/san1.md`「磁碟 A 的加密」）；`pos` 新增，`pixel`（w 320、h 400），每國取白色區塊裡離國界最遠的點，國號讀圖上的數字、5 國改用相鄰決定；places-export 793 checked, 0 mismatched（含 58 國各在自己的白色區塊上、圖上相接和 `adjacent` 的 140 組相同，17–21 只在一點相接、除外；58 組對調都會被抓到），koei-wiki `verify_sanguo_places.py` 803 checked, 0 mismatched；色盤是數位 8 色，沒有大地圖畫面的截圖（🟡）。PC-88 V1 版的同一張圖資料 byte 相同，另外輸出在 `export/koei-wiki/places/san1-pc88/world/PACKDATA-000.png`（和 PC-98 的 PNG byte 相同），國號與 `pos` 照 `san1-pc98` |
| 信4 `nobu4-pc98` | ✅ | code+capture | `world/MAPDATA.png` 640×400（`MAPDATA.DAT` 前 96000 bytes 的 3 平面原圖，就是主畫面底圖，國名、標題字樣、視窗框都在圖上）；`pos` 新增，`pixel`（w 640、h 400），取遊戲替各國塗勢力色的填色起點（`MAIN.EXE` DS:0x3718、0x3778）；places-export 5811 checked, 0 mismatched（含 48 國各在陸地上、從各點填色不會碰到別國的點）；色盤和截圖 `guest os_003` 訊息視窗以外逐點相同 |
| 信3 `nobu3-pc98` | ✅ | code+capture | `world/MAPDATA-0.png`–`3.png` 各 416×304（4 張 416×152 逐列加倍）：0 是不寫國名的全國圖，1–3 是東、中、西分區圖（有國名）；`pos` 新增，是全國圖 `MAPDATA-0` 上的像素（`pixel`，w 416、h 304），取自 `MAIN.EXE` DS:0x3C5A 的點表；places-export 428 checked, 0 mismatched（含 38 國各在陸地上、互不相連）；分區圖 1–3 和截圖地圖區逐點相同，全國圖沒有截圖（同一色盤，🟡） |
| 信5 `nobu5pk-pc98` | 🟡 | code | PC-98 版解出：`world/M_CHIKEI-spring.png` 1920×376（`M_PARTS.NB5` 120×23 格 × `M_CHIKEI.NB5` 16×16 圖塊，奇數欄下移 8 點），沒用 Win 版；`pos` 新增，城格中心的像素（`pixel`，w 1920、h 376），城格表在 `MAIN.EXE` 映像 0x43984（173 × 欄、列）；places-export 346 checked, 0 mismatched（含 173 城都在自己的城格上）；色盤讀季節表第 0 組，沒有截圖比對，第 0 組是不是春【推】；國沒有 `pos` |
| 信2 `nobu2-pc88` | ❌ | | 沒交付：PC-88 只有 7 張地方地圖，圖的存放位置與格式沒找到（Disk A `PICDATA`、Disk B 頭像以外的 RLE 資料都試過），也沒有 PC-88 截圖；見 `notes/nobu2.md`「負面結論」 |

## 考慮過但放棄的做法

- 改用 FC／SFC 版的大地圖（famicom-re、superfamicom-re 已經有三國志 1–4、信長全國版、群雄傳、風雲錄、霸王傳、天翔記）：主機版的國數、編號和相鄰可能和 PC 版不同，對不上 koei-wiki 一覽頁的資料。只在 PC 版確定解不出來時，才當作個別代數的備案，由使用者決定。
- 由 koei-wiki 自己用 `pos` 畫示意地圖：沒有地形和海岸線，看不出地理位置，失去放大地圖的意義。
