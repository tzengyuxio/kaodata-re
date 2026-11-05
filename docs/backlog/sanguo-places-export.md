---
status: in-progress
created: 2026-11-06
from: koei-wiki
sources:
  - koei-wiki@048adb5:EDITORIAL.mkdn
  - koei-wiki@048adb5:assets/location_sanguo_template.mkdn
  - koei-wiki:docs/sanguo-places-format.mkdn（未 commit，格式草案）
  - kaodata-re@e7cfc3b:notes/san-maps.md
---

# 三國志各代地點資料匯出給 koei-wiki

## 結論

koei-wiki 要建三國地點與州條目。請把 `notes/san-maps.md` 整理好的各代地點匯出成 `export/koei-wiki/places/<dataset>.jsonl`，一個地點一行；戰場圖 PNG 放 `export/koei-wiki/places/<dataset>/`。欄位照 koei-wiki 的 `docs/sanguo-places-format.mkdn`（koei-places/1 草案）：`dataset`、`id`、`name`、`level`（遊戲中的等級）、`province`、`region`、`parentCity`、`adjacent`、`battlemaps`、`pos`、`uncertain`、`notes`。

- 三1 到三14 都要，資料集 ID 和能力值匯出相同（`san1-pc98` … `san14pk-win`）。
- 遊戲資料裡的地點**全部匯出**（野戰地點、三10 的拠点、三13 的縣級地點、三14 的府都要）；收不收條目由 koei-wiki 決定。
- 交付時附 commit 與驗證結果（N checked, 0 mismatched），驗證項目見格式檔。
- 可以分代交付，先交已經確認的代數，例如三3 到三5、三11 到三14 的都市與關。

## 為什麼由這裡做

地點表、相鄰關係與戰場對照都是從遊戲檔解出來的，讀取程式和筆記都在 kaodata-re；koei-wiki 只讀匯出結果產生條目，不碰遊戲檔。

## 已定與未定

- 已定（koei-wiki 的條目規則，不用重新討論）：
  - 條目以遊戲中的名稱為單位，同一個地方在不同代用不同名稱就各自成條，所以 `name` 照遊戲原樣，正體化與對照由 koei-wiki 做。
  - 每代要標「遊戲中的等級」，用遊戲裡的稱呼；遊戲裡沒有稱呼的（三13 的縣級地點）由這邊給分類並在 `notes` 說明。
  - 戰場圖放在地點條目裡；大地圖位置不放條目，日後放各代的大地圖頁面，所以 `pos` 是選填。
  - 三9、三11、三14 沒有獨立戰場圖，不用補。
- 未定（格式可以直接和 koei-wiki session 商量，使用者已同意由兩邊談定）：
  - 欄位名稱與型別：格式檔是草案，覺得哪裡不合遊戲資料就提出來。
  - 三6 之後的戰場圖要不要渲染成 PNG、尺寸多大；R2 由誰上傳。
  - 三8 戰場名和地點對不上、三13 野戰地域碼沒解等未確認的部分，先用 `uncertain` 或省略，不用等解完才交。

## 考慮過但放棄的做法

- 由 koei-wiki 直接讀 `notes/san-maps.md` 的 Markdown 表格：表格是給人讀的，各代欄位不同、混有說明文字，解析起來脆弱，而且筆記一改就壞。
- 只匯出都市與關：koei-wiki 已決定三13、三14 全收、三9 和三11 的港也收，篩選放在下游比較不會漏。

## 現況（2026-11-06）

- 三批都已輸出：`dekoei.py places-export <dataset>`（`dekoei/places_export.py`），14 個資料集（三1–三14）每個都印 0 mismatched；三9 原本漏在三批的計畫外，已補上。各代的取法與未確認的部分見 `notes/san-maps.md`「koei-wiki 匯出」。
- 有戰場圖 PNG 的：三1–三7（三5 是推定對應）。三8 缺色盤、三10 還沒寫渲染、三12／13 是 3D。
- 和 koei-wiki 談定的格式調整：`battlemaps[].from`、`nameBorrowed`、`pos.grid` 自由字串＋`w`／`h`、I–III 的 `role` 填「戰場」。

## 下一步

- 使用者同意 commit 後，把 commit 與驗證數字傳給 koei-wiki。
- 之後：三10 戰場圖、三8 色盤、三6 攻守方向。

