# 寶物匯出（koei-wiki，koei-items/1）

`dekoei.py items-export <dataset> --extract ../games/<id>/extract --game-dir ../games/<id> --out ../export/koei-wiki/items`（`dekoei/items_export.py`）寫 `export/koei-wiki/items/<dataset>.jsonl`，一格寶物一行。規格在 koei-wiki `docs/items-format.mkdn`。大部分欄位讀各遊戲 `*-extras` 輸出的 `extract/items/*.csv`，所以要先跑該遊戲的 extras；信長6、11 的 CSV 只留持有者的名字，持有者 id 要重讀劇本檔。

- 三國志VIII–14 的遊戲檔 2026-11-11 移到 NAS（`notes/steam.md`「三國志8–14 的封存」），重跑時 `--extract` 指向素材庫 `~/game-library/koei/<dataset>`（同 `extract/` 的結構），`--game-dir` 指向 `/Volumes/Media/games/koei/Steam/<dataset>`；繁中版 depot 先找 `<game-dir>/../steam/<appid>-tchinese/depot`，沒有就找 `<game-dir>/../<appid>-tchinese/depot`（NAS 的排法）。
- `holders` 的 `person` 是 kaodata 資料集的人物 id。匯出時逐一檢查它在 kaodata `dataset.json` 的 characters 或 koei-wiki 人物匯出裡，不在就停止匯出。
- 持有者名字和人物名字不同的，都是同一人的別名（大友義鎮／大友宗麟、松平元康／徳川家康、木下秀吉／豊臣秀吉…），照 id 對 ✅ cross。
- 三國志的劇本號：有人物匯出的（`extract/tables/scenarios.csv`，由 `wiki_san<N>` 寫）照它的號碼，不在表裡的劇本檔不出；還沒有的照檔名排序。2026-11-11 起三國志IX、X 照人物匯出的號碼（X 原本把本體 7 個劇本也排進去，共 18 個，和人物匯出對不上）。
- 圖還沒出。效果（`effects`）2026-11-11 補上，見下面「效果」。
- 持有者只留劇本開局在場的人：三國志VIII、12、13、14 的寶物表常把寶物記在當年還沒登場或已死的人名下，照人物匯出（`export/koei-wiki/persons/<dataset>.jsonl`）的劇本狀態，未登場、未発見、死亡與沒有該劇本記錄的不出（`_present`）。
- 三國志VII–12 的 `nameZh`、`descriptionZh` 讀 Steam 繁中版（`games/steam/<appid>-tchinese/depot`，和遊戲目錄並排，`items_export.ZH`），各代的 `<game>_extras.zh_items` 回傳寶物號 → (名稱, 說明)；位置與比對方式見各遊戲筆記的寶物段。三國志11 繁中版也沒有寶物說明，只填 `nameZh`。三國志13、14 的繁中讀自己的檔。

## 第 1 批（2026-11-11）

| 資料集 | 件數 | 有持有者的件數（筆數） | 說明文 | 讀哪裡 | 標 `uncertain` |
|---|--:|--:|---|---|---|
| `san4pk-pc98` | 31 | 19（129） | 日文、中文（DOS 中文版） | `items.csv`、`holders.csv`（已有 kaodata id） | kind |
| `san7pk-win` | 72 | 46（428） | 日文、繁中 | 同上；持有者欄就是 kaodata id，12 個劇本照檔名排號 | kind、price |
| `san9pk-win` | 100 | 44（658） | 日文、繁中 | 只出人物持有者（狀態 2）；放在都市的只有都市號，沒有名字，沒出 | kind、price、holders |
| `san10pk-win` | 200 | 181（1950） | 日文、繁中 | 人物或所在都市（`other`）；只出 PK 的 11 個劇本（本體的 `Sce00?.s10` 不出）；人物槽 763 以後不在 kaodata，寫在 `notes` | — |
| `san11pk-win` | 43 | 43（592） | 沒有（繁中也沒有，只有 `nameZh`） | 人物或所在地（`other`）；7 個「アイテム」空槽不出 | kind、price、holders |
| `nobu6pk-pc98` | 120 | 57（152） | 日文 | 持有者是各劇本名字記錄的槽號（從 1 起），槽的頭像號換成 id（同 `wiki_nobu6`）；`effects` 是 CSV 的加成能力與數值 | — |
| `nobu7pk-win` | 200 | 78（387） | 日文 | 持有者 n（從 1 起）是 id n－1；種類只有數字，沒出 | grade |
| `nobu8pk-win` | 350 | 111（614） | 沒有 | 持有者 n 就是 id n；`price` 取劇本 10 的值 | grade、price |
| `nobu9pk-win` | 380 | 198（1885） | 沒有 | 人物用 id，都市用名字（`other`）；`pk` 是 PK 的 30 件 | grade |
| `nobu10pk-win` | 460 | 83（510） | 日文 | `holders.csv` 的持有者就是 id | — |
| `nobu11pk-win` | 430 | 145（664） | 日文 | 持有者連號：武將槽（`wiki_nobu11.OFFICERS`）是 id，勢力寫成「當主名勢力」（`other`）；劇本號是 DBSCEDA 的號碼 | kind（圖的種類） |
| `nobu12pk-win` | 355 | 109（596） | 日文 | `owners` 的名字對人物匯出的名字，每個名字都只對到一人 | grade |

| `nobu15pk-win` | 121 | 0 | 日文、繁中 | `kahou.csv`（`nobu15-extras`）；各劇本開局的持有欄全是 0xFFFF，家宝表的相關人物只寫在 `notes` | grade |
| `nobu14pk-win` | 160 | 52（240） | 繁中 | `wiki_nobu14.items` 直接讀劇本檔（不讀 CSV；`--extract` 不用）：持有人欄有值是人物槽，否則是持有的家（`other` 寫家名）；10 個劇本 | grade |

三國志VII、IX、X、11 的繁中名稱與說明在 2026-11-11 補上（第 2 批同一天），件數與持有者不變。

## 第 2 批（2026-11-11，三國志）

| 資料集 | 件數 | 有持有者的件數（筆數） | 說明文 | 讀哪裡 | 標 `uncertain` |
|---|--:|--:|---|---|---|
| `san8pk-win` | 255 | 43（1209） | 日文、繁中 | `items.csv`；持有者重讀 `D_Sce.s8` 0x129C5 的持有表，51 個劇本（184–234 年）照 `scenarios.csv` 的年份取值，不在場的 611 筆不出；放在都市的寫在 `notes` | kind、price |
| `san12pk-win` | 205 | 64（522） | 日文、繁中 | `items.csv`；持有者重讀 17 個劇本檔名品段的 bit 448，不在場的 324 筆不出；`pk` 是 184–204 | kind、price |
| `san13pk-win` | 234 | 234（2347） | 日文、繁中 | `items.csv`；持有者重讀 PK 第 942–952 項第 7 子項：人物 251 筆（不在場的 7 筆不出），放在地點的 2096 筆是 `other` | price、holders |
| `san14pk-win` | 131 | 46（591） | 日文、繁中 | `items.csv`（名稱、說明兩種語言都有）；持有者讀 27 個劇本檔 `scedaex*.s14` 的寶物段（劇本 1 在 0x69791，各檔逐件比對名稱確認位置），劇本號是檔號（同 `scenarios.csv`），未登場、未発見的不出 | price |

## 效果（`effects`，2026-11-11）

能力加成寫成 `{"target", "amount"}`，能力名照該代的寫法；特技、兵法、戦法和其他特殊效果寫成 `{"skill": "<遊戲寫法>"}`。看不懂的欄位不出；有推定的整件在 `uncertain` 加 `effects`。

| 資料集 | 有效果的件數（筆數） | 來源 | 標 `uncertain` |
|---|--:|---|---|
| `san4pk-pc98` | 24（28） | 說明文前兩列的效果文字（「知力＋５；政治力＋８」）；`＋` 的拆成能力加成，其餘（天変使用可、病気・怪我の治癒、退却確率の上昇、魅力・統率力が１００）照原文當 skill ✅ cross（和 +5、+6 一致）、✅ capture（曹操） | — |
| `san7pk-win` | 19（19） | 只出武器的加成（武力）；書的加成對象不知道，不出 | 全部 |
| `san8pk-win` | 84（88） | 武器的加成（武力）＋特技 +18（EXE 字表倒數，猛者、偵察、医術、人徳…；23–25 沒有名字的不出） | 全部 |
| `san9pk-win` | 50（60） | 武器的加成（武力，✅ capture 劉備 雌雄一対の剣 +3）＋兵法欄 | 全部 |
| `san10pk-win` | 41（41） | 武器的 `b2`（武力，✅ capture 孫堅 古錠刀 +3） | 全部 |
| `san11pk-win` | 0 | 寶物表的加成與數值欄沒解 | — |
| `san12pk-win` | 142（207） | 能力（效果種類 0 時的對象與數值）＋特技，兩者 ✅ cross | — |
| `san13pk-win` | 99（99） | 道具表欄 4 能力（0 統率、1 武力、2 知力、3 政治）、欄 5 數值；順序同三國志12，每類寶物都對到合理的能力 🟡；欄 6–7（特技號？）沒有名稱表，不出 | 全部 |
| `san14pk-win` | 110（114） | `stat`／`amount`（能力的順序 🟡）＋特殊效果（退却確実、寿命延長；寿命延長帶 `amount` 10，規格 2026-11-11 起 skill 可帶 `amount`；退却確実的數值是 0，不帶） | 全部 |
| `nobu6pk-pc98` | 120（120） | CSV 的加成能力與數值（第一輪就有） | — |
| `nobu7pk-win` | 0 | 效果欄（+0x1C）和 20 種效能說明的對照沒解 | — |
| `nobu8pk-win` | 155（155） | 種類的特殊效果（最大義理が上昇する、必ず戦場から退却できる…）；接在哪個種類是照字串位置推的 🟡；加成量與對象位元沒解，不出 | 全部 |
| `nobu9pk-win` | 380（380） | 種類的效果文字 ✅ code：「Xの特技を取得する」寫成特技 X，「Xの能力が%d上がる」寫成能力 X＋記錄 +92 的值（🟡，這 46 件標 uncertain），兵種的照原文 | 46 |
| `nobu10pk-win` | 0 | EXE 有欄位名（上昇能力、取得特技…），記錄 +54 以後怎麼對沒解 | — |
| `nobu11pk-win` | 0 | 種類與效果沒解 | — |
| `nobu14pk-win` | 0 | 效果欄沒解（`notes/nobu14.md`「家宝」） | — |
| `nobu12pk-win` | 74（74） | 戦法欄（🟡 cross：名馬、弓、火縄銃的戦法和種類吻合）；能力加成不在記錄裡 | 全部 |

三國志VII–X 的書（兵法書、經書、史書…）都有加成值，但對象看不出來：三國志12、13 的兵法書加統率，不是知力，所以不照種類猜。三國志VIII、X 的遊戲畫面還有知力、政治的加成（曹操 知力 +5、孫堅 政治 +2），之後可以拿來對。

