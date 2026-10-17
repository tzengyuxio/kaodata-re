# 各平台光榮遊戲與處理狀況

分平台列出光榮（KOEI）在 PC-88、PC-98、X68000、DOS、DOS/V 上的遊戲：手上有沒有原檔、掃過沒有、有沒有匯出成 kaodata 資料集。Windows／Steam 版不在這份表裡。整理日期：2026-10-17。

## 總覽

| 平台 | 款數 | 已匯出 | 不另收 | 略過 | 待處理 | 沒有檔案 |
| ---- | ---: | -----: | -----: | ---: | -----: | -------: |
| PC-88 | 21 | 14 | 2 | 1 | 1 | 3 |
| PC-98 | 57 | 36 | 4 | 3 | 11 | 3 |
| X68000 | 23 | 20 | 2 | 0 | 0 | 1 |
| DOS 中文版 | 23 | 18 | 1 | 0 | 0 | 4 |
| DOS 英文版 | 16 | 2 | 5 | 0 | 1 | 8 |
| DOS/V（日文版） | 7 | 0 | 0 | 0 | 0 | 7 |

「款數」是各平台表格的列數，也就是目前已知的作品數，不是該平台確定的發行總數：

- 手上有原檔的作品，來自 `games/archives/` 底下的收藏（neo-kobe 的 PC-88／PC-98 合集、IA 的 X68000 合集、DOS 中文版與英文版的壓縮檔）。
- 沒有原檔的作品，是和維基百科對照後補上的（2026-10-17）：日文維基各作品條目的「対応機種」與「発売日一覧」、英文維基的 List of Koei games 與各作品條目。年份也照這些條目改成各平台的發售年。
- 維基百科沒有列、但其他資料指得到的版本也保留，備註會說明出處或「未查證」；維基百科明確列出平台、裡面沒有這個平台的，就刪掉。
- 維基百科對中文 DOS 版、日文 DOS/V 版幾乎沒有記載，這兩張表的「沒有檔案」項目最可能不完整。
- 同一作品的多張磁片、Vol.1／Vol.3 等合在一列的，只算一款。

狀態的意思：

| 狀態 | 意思 |
| ---- | ---- |
| 已匯出 | 已經匯出成 kaodata 資料集，資料集欄是 id。 |
| 標為版本 | 頭像、色盤、人名都和另一個資料集相同，kaodata 在那個資料集旁標出這個版本（`src/ui/editions.ts`）。 |
| 不另收 | 和另一個資料集相同，或只差人名的語言（例如英文版），依收錄規則不另做資料集。 |
| 沒有頭像 | 掃過，確認沒有頭像。 |
| 不用掃 | 使用者決定不用掃。 |
| 未掃 | 手上有檔案，還沒看過。 |
| 未解 | 有頭像，格式還沒解開。 |
| 待匯出 | 掃過、決定要收，還沒匯出。 |
| 沒有檔案 | 手上沒有原檔。 |

總覽的「不另收」包含「標為版本」，「略過」是「沒有頭像」加「不用掃」，「待處理」是「未掃」、「未解」加「待匯出」。

## 待處理

| 平台 | 遊戲 | 狀態 | 備註 |
| ---- | ---- | ---- | ---- |
| PC-88 | 信長の野望 | 未掃 | Steam 版（544990）確認沒有頭像，PC-88 版應該也沒有 |
| PC-98 | ナイトライフ | 未掃 | 推測沒有頭像 |
| PC-98 | 団地妻の誘惑 | 未掃 | 推測沒有頭像 |
| PC-98 | オランダ妻は電気ウナギの夢を見るか? | 未掃 | 推測沒有頭像 |
| PC-98 | ウイニングポスト | 待匯出 | 由 winning-post-zh 匯出 `winning-pc98` |
| PC-98 | トップマネジメント 山王台編 | 未解 | 臉可能在 `.ANM`，格式沒解開（BACKLOG） |
| PC-98 | ウイニングポスト2 Plus | 未掃 | |
| PC-98 | デルフォイの神託 | 未掃 | 推測沒有頭像 |
| PC-98 | 魂の門 ダンテ「神曲」より | 未掃 | 推測沒有頭像 |
| PC-98 | バンドくん | 未掃 | 推測沒有頭像（音樂軟體） |
| PC-98 | Super Dog World | 未掃 | 推測沒有頭像 |
| PC-98 | Life is Music | 未掃 | 推測沒有頭像 |
| DOS 英文版 | Romance of the Three Kingdoms II | 未掃 | 沒有和 `san2-dos` 比對過 |

年份是該平台的發售年，不確定的加「?」，依年份排序。「原檔」是 `games/archives/` 底下的路徑，縮寫：`nk98/`＝`pc98/neo-kobe-2017-11-17/Koei/`、`nk88/`＝`pc88/neo-kobe-2016-02-25/`、`ia68/`＝`x68000/ia-softwarelibrary/`。

## PC-88

| 年 | 遊戲 | 狀態 | 資料集 | 備註 | 原檔 |
| -: | ---- | ---- | ------ | ---- | ---- |
| 1981–1982 | 川中島の合戦、投資ゲーム等早期作品 | 沒有檔案 |  | 推測沒有頭像 | — |
| 1982–1984 | ナイトライフ、団地妻の誘惑、オランダ妻は電気ウナギの夢を見るか? | 沒有檔案 |  | 推測沒有頭像 | — |
| 1983 | 信長の野望 | 未掃 |  | Steam 版（544990）確認沒有頭像，PC-88 版應該也沒有 | `nk88/Nobunaga no Yabou/` |
| 1984 | トップマネジメント | 沒有檔案 |  | 原版是 PC-88，1990 年移植 FC | — |
| 1985 | 蒼き狼と白き牝鹿 | 沒有頭像 |  | N88-BASIC，5 套映像都只有開場動畫、地圖、戰爭圖 | `nk88/Aoki Ookami to Shiroki Mejika/` |
| 1985 | 三國志（V1） | 已匯出 | `san1-pc88` | 男性頭像只有 30 張 | `nk88/Sangokushi/` |
| 1986? | 三國志（SR） | 標為版本 | → `san1-pc98` | 頭像和 PC-98 版逐 byte 相同 | `nk88/Sangokushi/` |
| 1986 | 信長の野望・全国版 | 已匯出 | `nobu2-pc88` | 全國版以 PC-88 為主，PC-98、Steam 版標為版本 | `nk88/Nobunaga no Yabou - Zenkoku-ban/` |
| 1988 | ジンギスカン | 標為版本 | → `genghis-pc98` | 舊 id `genghis-pc88`，首發是 1987 的 PC-98 版 | `nk88/Aoki Ookami to Shiroki Mejika - Genghis Khan/` |
| 1988 | 信長の野望・戦国群雄伝 | 已匯出 | `nobu3-pc88` |  | `nk88/Nobunaga no Yabou - Sengoku Gunyuuden/` |
| 1989 | 維新の嵐 | 已匯出 | `ishin-pc88` |  | `nk88/Ishin no Arashi/` |
| 1989 | 水滸伝・天命の誓い | 已匯出 | `suikoden-pc88` |  | `nk88/Suikoden/` |
| 1989 | 三國志II | 已匯出 | `san2-pc88` | DOS 版沿用這份 200 線圖 | `nk88/Sangokushi II/` |
| 1990 | 提督の決断 | 已匯出 | `tk-pc88` |  | `nk88/Teitoku no Ketsudan/` |
| 1990 | ランペルール | 已匯出 | `lempe-pc88` |  | `nk88/L'Empereur/` |
| 1990 | 大航海時代 | 已匯出 | `koukai-pc88` |  | `nk88/Daikoukai Jidai/` |
| 1990 | 信長の野望・武将風雲録 | 已匯出 | `nobu4-pc88` |  | `nk88/Nobunaga no Yabou - Bushou Fuuunroku/` |
| 1991 | ロイヤルブラッド | 已匯出 | `royal-pc88` |  | `nk88/Royal Blood/` |
| 1991 | 伊忍道 打倒信長 | 已匯出 | `inindou-pc88` | 同樣 14 張重畫成 64×40 | `nk88/Inindou - Datou Nobunaga/`、`pc88/inindou-flux/` |
| 1991 | ヨーロッパ戦線 | 已匯出 | `europe-pc88` |  | `nk88/Europe Sensen/` |
| 1992 | 蒼き狼と白き牝鹿・元朝秘史 | 已匯出 | `genchou-pc88` |  | `nk88/Aoki Ookami to Shiroki Mejika - Genchou Hishi/` |

## PC-98

| 年 | 遊戲 | 狀態 | 資料集 | 備註 | 原檔 |
| -: | ---- | ---- | ------ | ---- | ---- |
| 1982 | ナイトライフ | 未掃 |  | 推測沒有頭像 | `nk98/Nightlife/` |
| 1983 | 団地妻の誘惑 | 未掃 |  | 推測沒有頭像 | `nk98/Danchi-zuma no Yuuwaku/` |
| 1983? | 信長の野望 | 不用掃 |  | 使用者決定（2026-10-17）。Steam 版確認沒有頭像 | `nk98/Nobunaga no Yabou/` |
| 1984 | オランダ妻は電気ウナギの夢を見るか? | 未掃 |  | 推測沒有頭像 | `nk98/Do Dutchwives Dream of Electric Eel/` |
| 1985 | 蒼き狼と白き牝鹿 | 沒有檔案 |  | PC-88 版沒有頭像 | — |
| 1986 | 三國志 | 已匯出 | `san1-pc98` |  | `pc98/【PC98】三國志.rar`、`nk98/Sangokushi/` |
| 1987 | 信長の野望・全国版 | 標為版本 | → `nobu2-pc88` | 頭像與人名和 PC-88 版相同 | `nk98/Nobunaga no Yabou - Zenkoku-ban/` |
| 1987 | 蒼き狼と白き牝鹿・ジンギスカン | 已匯出 | `genghis-pc98` | 首發版 | `nk98/Aoki Ookami to Shiroki Mejika - Genghis Khan/` |
| 1987 | 麻雀大会 | 已匯出 | `mahjong-pc98` | 15 位對手各 7 種表情，48×48 | `nk98/Mahjong Taikai/` |
| 1988 | 維新の嵐 | 已匯出 | `ishin-pc98` |  | `pc98/[PC98] 維新の嵐.zip` |
| 1989 | 信長の野望・戦国群雄伝 | 已匯出 | `nobu3-pc98` |  | `pc98/[PC98] 信長の野望・戦国群雄伝.zip` |
| 1989 | 提督の決断 | 已匯出 | `tk-pc98` |  | `pc98/[PC98] 提督の決断.zip` |
| 1990 | 三國志II | 已匯出 | `san2-pc98` | 重畫成 400 線 | `pc98/【PC98】三國志２.rar` |
| 1990 | ランペルール | 標為版本 | → `lempe-x68` | 映像在頭像 92 以後損壞，前 92 張相同 | `nk98/L'Empereur/` |
| 1990 | 大航海時代 | 已匯出 | `koukai-pc98` |  | `pc98/[PC98] 大航海時代.zip` |
| 1991 | 水滸伝・天命の誓い | 已匯出 | `suikoden-pc98` |  | `pc98/[PC98] 水滸伝～天命の誓い～.ZIP` |
| 1991 | 信長の野望・武将風雲録 | 已匯出 | `nobu4-pc98` |  | `pc98/[PC98] 信長の野望・風雲録.zip` |
| 1991 | ロイヤルブラッド | 已匯出 | `royal-pc98` |  | `pc98/[PC98] [光栄] ロイヤルブラッド(FDI).zip` |
| 1991 | 伊忍道 打倒信長 | 已匯出 | `inindou-pc98` | 只有 7 位可以成家的女性 | `nk98/Inindou - Datou Nobunaga/` |
| 1992 | ヨーロッパ戦線 | 已匯出 | `europe-pc98` |  | `nk98/Europe Sensen/` |
| 1992 | 三國志III | 已匯出 | `san3-pc98` |  | `pc98/【PC98】三國志３.rar` |
| 1992 | 蒼き狼と白き牝鹿・元朝秘史 | 已匯出 | `genchou-pc98` |  | `nk98/Aoki Ookami to Shiroki Mejika - Genchou Hishi/` |
| 1992 | 太閤立志伝 | 已匯出 | `taikoh-pc98` |  | `pc98/[PC98] 太閤立志伝.zip` |
| 1992 | エアーマネージメント | 已匯出 | `air-pc98` | 只有頭像，沒有人名 | `nk98/Air Management - Oozora ni Kakeru/` |
| 1992 | リーディングカンパニー | 已匯出 | `leading-pc98` | 只有頭像，沒有人名 | `nk98/Leading Company/` |
| 1992 | トップマネジメントII | 已匯出 | `topman2-pc98` | 只有頭像 | `nk98/Top Management II/` |
| 1992 | 信長の野望・覇王伝 | 已匯出 | `nobu5-pc98` |  | `pc98/[PC98] 信長の野望・覇王伝o.zip` |
| 1993? | トップマネジメント 山王台編 | 未解 |  | 臉可能在 `.ANM`，格式沒解開（BACKLOG） | `nk98/Top Management Sannoudai Hen/` |
| 1993 | 大航海時代II | 已匯出 | `koukai2-pc98` |  | `pc98/[PC98] 大航海時代２.zip` |
| 1993 | 項劉記 | 已匯出 | `kouryuuki-pc98` |  | `nk98/Kouryuuki/` |
| 1993 | エアーマネージメントII | 已匯出 | `air2-pc98` | 頭像同 DOS 版，只差色盤換算 | `nk98/Air Management 2 - Koukuuou o Mezase/` |
| 1993 | 独立戦争 | 已匯出 | `liberty-pc98` |  | `pc98/[PC98] 独立戦争.zip` |
| 1993 | 提督の決断II | 已匯出 | `tk2-pc98`（只在 data-local） | kaodata 收 PK 版 | `pc98/[PC98] 提督の決断２.zip` |
| 1993 | ウイニングポスト | 待匯出 | `winning-pc98` | 和 DOS 版只差色盤換算（PC-98 是 v×17），使用者決定另收。由 winning-post-zh 匯出，檔案在 `games/winning-pc98/` | `nk98/Winning Post/` |
| 1993 | 神々の大地 古事記外伝 | 不用掃 |  | 使用者決定（2026-10-17） | `nk98/Kamigami no Daichi - Kojiki Gaiden/` |
| 1993 | デルフォイの神託 | 未掃 |  | 推測沒有頭像 | `nk98/Delphi no Shintaku/` |
| 1993 | 魂の門 ダンテ「神曲」より | 未掃 |  | 推測沒有頭像 | `nk98/Tamashii no Mon - Dante Shinkyoku yori/` |
| 1993? | バンドくん | 未掃 |  | 推測沒有頭像（音樂軟體） | `nk98/Band-kun/` |
| 1993? | Super Dog World | 未掃 |  | 推測沒有頭像 | `nk98/Super Dog World/` |
| 1993? | Life is Music | 未掃 |  | 推測沒有頭像 | `nk98/Life is Music/` |
| 1994 | 提督の決断II パワーアップキット | 已匯出 | `tk2pk-pc98` |  | `pc98/[PC98] 提督の決断２　ﾊﾟﾜｰｱｯﾌﾟｷｯﾄ.zip` |
| 1994 | 三國志IV | 不另收 |  | 本體完全包含在 PK 裡，kaodata 收 PK 版 | `pc98/【PC98】三國志４.rar` |
| 1994 | 三國志IV パワーアップキット | 已匯出 | `san4pk-pc98` |  | `pc98/【PC98】三國志４　パワーアップキット.rar` |
| 1994 | 源平合戦 | 已匯出 | `genpei-pc98` | DOS 版標為版本 | `pc98/[PC98] 源平合戦.zip` |
| 1994 | 信長の野望・天翔記 | 已匯出 | `nobu6-pc98` |  | `pc98/[PC98] 信長の野望・天翔記.zip` |
| 1994–1995 | Emit Vol.1／Vol.3 | 不用掃 |  | 使用者決定（2026-10-17）。手上沒有 Vol.2 | `nk98/Emit Vol. 1 - Toki no Maigo/`、`nk98/Emit Vol. 3 - Watashi ni Sayonara o/` |
| 1994? | 麻雀大会II | 沒有檔案 |  | 維基沒有寫 PC-98 版的發售日，只寫 1994 年移植 SFC | — |
| 1995 | 三國志 復刻版 | 標為版本 | → `san1-pc98` |  | `nk98/Sangokushi Fukkokuban/` |
| 1995 | ウイニングポスト2 Plus | 未掃 |  |  | `nk98/Winning Post 2 Plus/` |
| 1995 | 三國志英傑伝 | 已匯出 | `eiketsu-pc98` | Win3.1 版標為版本 | `pc98/[PC98] 三国志・英傑伝.zip` |
| 1995 | 太閤立志伝II | 已匯出 | `taikoh2-pc98` |  | `pc98/[PC98] 太閤立志伝２.zip` |
| 1995 | 三國志V | 已匯出 | `san5-pc98`（只在 data-local） | kaodata 收 PK 版 | `pc98/【PC98】三國志５.rar` |
| 1995 | プロジェネター | 已匯出 | `progen-pc98` |  | `pc98/[PC98] [光栄] プロジェネター（FDI).zip` |
| 1996 | 三國志V パワーアップキット | 已匯出 | `san5pk-pc98` |  | `pc98/【PC98】三國志５　パワーアップキット.rar` |
| 1996 | 提督の決断III | 已匯出 | `tk3-pc98`（只在 data-local） | kaodata 收 PK 版 | `pc98/[PC98] 提督の決断３.zip` |
| 1996 | 提督の決断III パワーアップキット | 已匯出 | `tk3pk-pc98` |  | `pc98/[PC98] 提督の決断３　パワーアップキット.zip` |
| 1996 | ウイニングポスト2 Plus with パワーアップキット | 沒有檔案 |  |  | — |

## X68000

已和日文維基各作品的「対応機種」對照過。日文維基寫項劉記（1993-11）是光榮在 X68000 上的最後一款，三國志IV、提督の決断II 沒有 X68000 版。

| 年 | 遊戲 | 狀態 | 資料集 | 備註 | 原檔 |
| -: | ---- | ---- | ------ | ---- | ---- |
| 1988 | 三國志 | 已匯出 | `san1-x68` | 256 色 48×80 | `ia68/sangokushi_1988_koei_disk_1_of_x68k/` |
| 1988 | 信長の野望・全国版 | 已匯出 | `nobu2-x68` | 重畫 64×80 | `ia68/nobunaga_no_yabou_zenkokuhan_1_x68k/` |
| 1989 | 蒼き狼と白き牝鹿・ジンギスカン | 已匯出 | `genghis-x68` | 重畫 48×80 | `ia68/aoki_ookami_to_shiroki_meshika_x68k/` |
| 1989 | 信長の野望・戦国群雄伝 | 標為版本 | → `nobu3-pc98` |  | `ia68/nobunaga_no_yabou_sengoku_guny_x68k/` |
| 1989 | 水滸伝・天命の誓い | 已匯出 | `suikoden-x68` |  | `ia68/suikoden_tenmei_no_chikai_1989_x68k/` |
| 1990 | 三國志II | 已匯出 | `san2-x68` |  | `x68000/Sangokushi II [FD]/` |
| 1990 | 維新の嵐 | 已匯出 | `ishin-x68` | 重畫 48×80 | `ia68/ishin_no_arashi_1990_koei_disk_x68k/` |
| 1990 | 提督の決断 | 已匯出 | `tk-x68` | 重畫 56×72 | `ia68/teitoku_no_ketsudan_1990_koei_x68k/` |
| 1990 | 大航海時代 | 標為版本 | → `koukai-pc98` |  | `ia68/daikoukai_jidai_19xx_koei_disk_x68k/` |
| 1991 | ランペルール | 已匯出 | `lempe-x68` | PC-98 版標為它的版本 | `ia68/lempereur_19xx_koei_disk_1_of_x68k/` |
| 1991 | 信長の野望・武将風雲録 | 已匯出 | `nobu4-x68` | 只有色盤不同 | `ia68/nobunaga_no_yabou_bushou_fuuun_x68k/` |
| 1991 | 伊忍道 打倒信長 | 已匯出 | `inindou-x68` |  | `ia68/inindou_datou_nobunaga_199x_ko_x68k/` |
| 1992 | ロイヤルブラッド | 已匯出 | `royal-x68` |  | `ia68/royal_blood_19xx_koei_disk_1_o_x68k/` |
| 1992 | ヨーロッパ戦線 | 已匯出 | `europe-x68` | 映像只讀得到劇本 0、5、6 | `ia68/europe_sensen_1992_koei_disk_1_x68k/` |
| 1992 | 三國志III | 已匯出 | `san3-x68` |  | `ia68/sangokushi_iii_1992_koei_disk_x68k/` |
| 1992 | 太閤立志伝 | 已匯出 | `taikoh-x68` |  | `ia68/taikou_risshiden_1992_koei_dis_x68k/` |
| 1992 | エアーマネージメント | 已匯出 | `air-x68` |  | `ia68/air_management_19xx_koei_disk_x68k/` |
| 1992 | リーディングカンパニー | 已匯出 | `leading-x68` |  | `ia68/leading_company_1992_koei_disk_x68k/` |
| 1993 | 信長の野望・覇王伝 | 已匯出 | `nobu5-x68` |  | `ia68/nobunaga_no_yabou_hanouden_199_x68k/` |
| 1993 | 蒼き狼と白き牝鹿・元朝秘史 | 已匯出 | `genchou-x68` |  | `ia68/aoki-ookami-to-shiroki-meshika-genchou-hishi-1993-koei-disk-1-of-3/` |
| 1993 | 項劉記 | 已匯出 | `kouryuuki-x68` |  | `ia68/kouryuuki_1993_koei_disk_1_of_x68k/` |
| 1993 | ウイニングポスト | 已匯出 | `winning-x68`（winning-post-zh 匯出） | 本 repo 只核對過色盤 | `ia68/winning_post_1993_koei_disk_1_x68k/` |
| 1993 | 大航海時代II | 沒有檔案 |  | IA 的 X68000 合集沒有 | — |

## DOS 中文版

| 年 | 遊戲 | 狀態 | 資料集 | 備註 | 原檔 |
| -: | ---- | ---- | ------ | ---- | ---- |
| 1990? | 三國志II | 已匯出 | `san2-dos` | 頭像沿用 PC-88 的 200 線圖 | `dos/san2.zip` |
| 1992 | 成吉思汗 | 已匯出 | `genghis-dos` | 英文版 Genghis Khan 的移植 | `dos/成吉思汗_中文版_khan-c.zip` |
| 1993 | 信長之野望II（戰國群雄傳） | 已匯出 | `nobu3-dos` | 英文版 Nobunaga's Ambition II 的移植 | `dos/信長之野望２_中文版_nobu2-c.rar` |
| 1993 | 水滸傳・天命之誓 | 已匯出 | `suikoden-dos` | 英文版 Bandit Kings 的移植 | `dos/水滸傳_中文版_water.zip` |
| 1993? | 拿破崙 | 已匯出 | `lempe-dos` |  | `dos/拿破崙_中文版_l-empereur-c.rar` |
| 1993 | 大航海時代 | 已匯出 | `koukai-dos` | 英文版 Uncharted Waters 的移植 | `dos/大航海時代_中文版_uwc.zip` |
| 1993? | 歐陸戰線 | 已匯出 | `europe-dos` |  | `dos/歐陸戰線_中文版_europe.rar` |
| 1993? | 三國志III | 已匯出 | `san3-dos` |  | `dos/三國志３_中文版_San3.rar` |
| 1993? | 魔法皇冠（ロイヤルブラッド） | 沒有檔案 |  | README 的舊 face 命令支援過 | — |
| 1993 | 伊忍道 打倒信長 | 沒有檔案 |  | 台灣發行（維基百科） | — |
| 1994 | 信長之野望・武將風雲錄 | 已匯出 | `nobu4-dos` |  | `dos/信長之野望．武將風雲錄_中文版_Nobu4.rar` |
| 1994 | 元朝秘史 | 已匯出 | `genchou-dos` |  | `dos/元朝秘史_killpeople.rar` |
| 1994 | 項劉記 | 已匯出 | `kouryuuki-dos` | 宏碁發行 | `dos/項劉記_中文版_hanlau.rar` |
| 1994 | 獨立戰爭 | 已匯出 | `liberty-dos` | 日文 DOS/V 版的移植 | `dos/獨立戰爭_中文版_liberty.rar` |
| 1994? | 航空霸業II | 已匯出 | `air2-dos` | 只有頭像 | `dos/航空霸業２_中文版_air2.rar` |
| 1994 | 三國志IV（含威力加強版） | 已匯出 | `san4pk-dos` | 本體不另收 | `dos/三國志４_中文版_San4.rar`、`dos/6.10_三國志四加強版_killpeople.rar` |
| 1994 | 源平合戰 | 標為版本 | → `genpei-pc98` | 舊 id `genpei-dos`，手上沒有原檔 | — |
| 1994? | 光榮賽馬（ウイニングポスト） | 已匯出 | `winning-dos`（winning-post-zh 匯出） |  | — |
| 1994? | 大航海時代II | 沒有檔案 |  | README 的舊 face 命令支援過 | — |
| 1994? | 提督之決斷II | 沒有檔案 |  | README 的舊 face 命令支援過 | — |
| 1995 | 太閤立志傳 | 已匯出 | `taikoh-dos` | DOSBox 包 | `win/[系列] 太閣立志傳 …/$太閤立志傳1.rar` |
| 1995 | 三國志英傑傳 | 已匯出 | `eiketsu-dos` |  | `dos/6.10_三國志英傑傳_killpeople.rar` |
| 1996 | 三國志V 威力加強版 | 已匯出 | `san5pk-dos` | MAIN.EXE 是破解版 | `dos/6.3_三國志五DOS加強版_killpeople.rar` |

## DOS 英文版

英文版只差人名語言時，依收錄規則不另收。

| 年 | 遊戲 | 狀態 | 資料集 | 備註 | 原檔 |
| -: | ---- | ---- | ------ | ---- | ---- |
| 1988 | Nobunaga's Ambition（全国版） | 已匯出 | `nobu2-dos` | 重畫的 4 色 EGA 頭像 | `dos/信長之野望_英文版_nobunagas-ambition.zip` |
| 1988 | Genghis Khan | 不另收 | → `genghis-dos` | 頭像檔逐 byte 相同 | `dos/成吉思汗_英文版_genghis-khan.zip` |
| 1989 | Romance of the Three Kingdoms | 已匯出 | `san1-dos` |  | `dos/三國志_英文版_romance-of-the-three-kingdoms.zip` |
| 1989 | Bandit Kings of Ancient China | 不另收 | → `suikoden-dos` | 頭像檔逐 byte 相同 | `dos/水滸傳_英文版_bandit-kings-of-ancient-china.zip` |
| 1989 | Nobunaga's Ambition II | 不另收 | → `nobu3-dos` | 頭像與頭像碼相同，只差人名 | `dos/信長之野望２_英文版_nobunagas-ambition-ii.zip` |
| 1991 | Romance of the Three Kingdoms II | 未掃 |  | 沒有和 `san2-dos` 比對過 | `dos/三國志２_英文版_romance-of-the-three-kingdoms-ii.zip` |
| 1991 | L'Empereur | 不另收 | → `lempe-dos` | `KAODATA.DAT` 相同 | `dos/拿破崙_英文版_l-empereur.zip` |
| 1991 | Uncharted Waters | 不另收 | → `koukai-dos` | 頭像檔逐 byte 相同 | `dos/大航海時代_英文版_uncharted-waters.zip` |
| 1992 | Gemfire（ロイヤルブラッド） | 沒有檔案 |  |  | — |
| 1993 | Romance of the Three Kingdoms III | 沒有檔案 |  |  | — |
| 1993 | Genghis Khan II（元朝秘史） | 沒有檔案 |  |  | — |
| 1993 | Liberty or Death | 沒有檔案 |  | 北美原版 | — |
| 1994 | Operation Europe（ヨーロッパ戦線） | 沒有檔案 |  |  | — |
| 1995 | Uncharted Waters: New Horizons | 沒有檔案 |  |  | — |
| 1995? | Romance of the Three Kingdoms IV | 沒有檔案 |  | 英文維基沒有列 DOS 版，未查證 | — |
| 1995 | Celtic Tales: Balor of the Evil Eye | 沒有檔案 |  |  | — |

## DOS/V（日文版）

日文 DOS/V 版目前都沒有原檔。維基百科只有天翔記明確列了 DOS/V 版，其他各列是憑記憶整理的，備註寫了對照結果。中文 `liberty-dos` 是日文 DOS/V 版的移植（`LIBERTY.VER` 寫著 DOS/V）。

| 年 | 遊戲 | 狀態 | 資料集 | 備註 | 原檔 |
| -: | ---- | ---- | ------ | ---- | ---- |
| 1993? | 独立戦争 Liberty or Death | 沒有檔案 |  | 中文版 `liberty-dos` 由它移植。英文維基寫日本首發是 1993-09-27 的 PC-98 版 | — |
| 1994? | 三國志IV | 沒有檔案 |  | 維基百科沒有列 DOS/V 版 | — |
| 1994? | 大航海時代II | 沒有檔案 |  | 維基百科沒有列 DOS/V 版（只有北美 MS-DOS 版 New Horizons） | — |
| 1994? | 提督の決断II | 沒有檔案 |  | 英文維基的 P.T.O. II 列了 1993 年日本的 MS-DOS 版 | — |
| 1995? | 信長の野望・天翔記 | 沒有檔案 |  | 日文維基列了 DOS/V 版 | — |
| 1995? | 三國志英傑伝 | 沒有檔案 |  | 維基百科沒有列 DOS/V 版；IA 有一筆 `sangokushi-eiketsuden-dosv`，沒有下載 | — |
| 1995? | 三國志V | 沒有檔案 |  | 維基百科沒有列 DOS/V 版 | — |
