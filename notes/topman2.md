# トップマネジメントII（TOPMAN2, PC-98）頭像相關格式

`dekoei.py export topman2-pc98` 用 `build_topman2_pc98`。來源是 Internet Archive neo-kobe 的 `Top Management II`（`games/archives/pc98/neo-kobe-2017-11-17/Koei/`，2 片 HDM），Disk B 的 4 個頭像 GDT 與 Disk A 的 `TOP2.EXE`、`VERSION` 放在 `games/topman2-pc98/`。`VERSION` 寫「トップマネジメントⅡ For PC-9801 Series Mar.22,1993 Ver. 1.1 Rel 1.0」，Copyright 1992。

## 頭像：GDT 檔

格式同リーディングカンパニー（`koei_games.gdt_images`，見 `notes/leading.md`），每張 64×64。

- `SYAHISYO.GDT`：12 張，每人 3 種表情，第一人是社長（玩家），其餘 3 人是秘書。社長的第 3 張長相和前兩張不太像，但照 3 張一組算。
- `BUTYO1.GDT`、`BUTYO2.GDT`：各 36 張，每人 3 種表情，共 24 位部長。
- `KAIHOLD.GDT`：48 張，每人 4 種表情，共 12 人。檔名是「会長、株主」（HOLDer），`TOP2.EXE` 的職稱表也有「会長」「株主」，但哪幾位是会長、哪幾位是株主沒有追，所以 group 寫「会長・株主」。
- 職稱表在 `TOP2.EXE` 檔案 0x5FB00 起：社長、社長室長、人事、経理、購買、広告、開発、営業、製造部長、秘書、会長、株主。沒有人名，所以 `characters` 是空的；同一人的表情排在一起，用 `name`（例：「部長 3」）標出是同一人。
- 128×64 的事件圖（`MEVENT.GDT` 等）不是頭像，不收。

## 色盤

- 這 4 個檔（以及 `KAIGI.GDT` 等場景圖）的 GDT 檔頭 +3 是 1，畫面上的顏色是色號 c XOR 8 後查 `TOP2.EXE` 檔案 0x62F5E 的 16 色表（每色 3 bytes，G、R、B，4 bit，類比色 v × 17）；+3 是 0 的圖（`MAIN.GDT` 等）直接查表。這是從畫出來的圖對出來的，寫入色盤與畫圖的程式沒有追。
- XOR 之後色號 8（表裡是純綠）是頭像的背景，匯出成透明；臉只用色號 0–7，另外 `BUTYO1.GDT` 有 1 點是色號 11。
