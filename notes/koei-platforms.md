# 各平台光榮遊戲與處理狀況

這份表格分平台列出光榮（KOEI）的遊戲，記錄手上有沒有原檔、掃過沒有、有沒有匯出成 kaodata 資料集。目前包含 PC-88、PC-98、X68000、DOS、DOS/V 五個平台。Windows／Steam 版不在這份表裡。整理日期：2026-10-17。

狀態的寫法：

- **已匯出 `<id>`**：已經匯出成 kaodata 資料集。
- **標為版本**：頭像、色盤、人名都和另一個資料集相同，不另收。kaodata 的 `src/ui/editions.ts` 把它標在那個資料集旁邊。
- **不另收**：和另一個資料集相同，或只差人名的語言（例如英文版）。依 kaodata 的收錄規則不另做資料集。
- **沒有頭像**：掃過，確認沒有頭像。
- **不用掃**：使用者決定不用掃。
- **未掃**：手上有檔案，但還沒看過。
- **掃描中**：正在看。
- **未解**：有頭像，但格式還沒解開。
- **檔案不在手上**：沒有原檔，沒辦法掃。

年份是該平台的發售年；不確定的加「?」。「位置」是 `games/archives/` 底下的路徑，Neo Kobe 合集簡寫成 `nk98/`（`pc98/neo-kobe-2017-11-17/Koei/`）、`nk88/`（`pc88/neo-kobe-2016-02-25/`）；IA 的 X68000 合集簡寫成 `ia68/`（`x68000/ia-softwarelibrary/`）。

## PC-88

| 遊戲 | 年 | 位置 | 狀態 | 備註 |
| ---- | -: | ---- | ---- | ---- |
| 川中島の合戦、投資ゲーム等早期作品 | 1981–1982 | 不在手上 | 檔案不在手上 | 推測沒有頭像 |
| ナイトライフ、団地妻の誘惑、オランダ妻は電気ウナギの夢を見るか? | 1982–1984 | 不在手上 | 檔案不在手上 | 推測沒有頭像 |
| 信長の野望 | 1983 | `nk88/Nobunaga no Yabou/` | 未掃 | Steam 版（544990）確認沒有頭像，PC-88 版應該也沒有 |
| 蒼き狼と白き牝鹿 | 1985 | `nk88/Aoki Ookami to Shiroki Mejika/` | 沒有頭像 | N88-BASIC，5 套映像都只有開場動畫、地圖、戰爭圖 |
| 三國志（V1） | 1985 | `nk88/Sangokushi/` | 已匯出 `san1-pc88` | 男性頭像只有 30 張 |
| 三國志（SR） | 1986? | `nk88/Sangokushi/` | 標為版本（`san1-pc98`） | 頭像和 PC-98 版逐 byte 相同 |
| 信長の野望・全国版 | 1986 | `nk88/Nobunaga no Yabou - Zenkoku-ban/` | 已匯出 `nobu2-pc88` | 全國版以 PC-88 為主，PC-98、Steam 版標為版本 |
| ジンギスカン | 1988 | `nk88/Aoki Ookami to Shiroki Mejika - Genghis Khan/` | 標為版本（`genghis-pc98`） | 舊 id `genghis-pc88`，首發是 1987 的 PC-98 版 |
| 信長の野望・戦国群雄伝 | 1988 | `nk88/Nobunaga no Yabou - Sengoku Gunyuuden/` | 已匯出 `nobu3-pc88` | |
| 維新の嵐 | 1988 | `nk88/Ishin no Arashi/` | 已匯出 `ishin-pc88` | |
| 水滸伝・天命の誓い | 1989 | `nk88/Suikoden/` | 已匯出 `suikoden-pc88` | |
| 三國志II | 1989 | `nk88/Sangokushi II/` | 已匯出 `san2-pc88` | DOS 版沿用這份 200 線圖 |
| 提督の決断 | 1989 | `nk88/Teitoku no Ketsudan/` | 已匯出 `tk-pc88` | |
| ランペルール | 1990 | `nk88/L'Empereur/` | 已匯出 `lempe-pc88` | |
| 大航海時代 | 1990 | `nk88/Daikoukai Jidai/` | 已匯出 `koukai-pc88` | |
| 信長の野望・武将風雲録 | 1991 | `nk88/Nobunaga no Yabou - Bushou Fuuunroku/` | 已匯出 `nobu4-pc88` | |
| ロイヤルブラッド | 1991 | `nk88/Royal Blood/` | 已匯出 `royal-pc88` | |
| 伊忍道 打倒信長 | 1991 | `nk88/Inindou - Datou Nobunaga/`、`pc88/inindou-flux/` | 已匯出 `inindou-pc88` | 同樣 14 張重畫成 64×40 |
| ヨーロッパ戦線 | 1991 | `nk88/Europe Sensen/` | 已匯出 `europe-pc88` | |
| 蒼き狼と白き牝鹿・元朝秘史 | 1992 | `nk88/Aoki Ookami to Shiroki Mejika - Genchou Hishi/` | 已匯出 `genchou-pc88` | |

## PC-98

| 遊戲 | 年 | 位置 | 狀態 | 備註 |
| ---- | -: | ---- | ---- | ---- |
| 川中島の合戦 | 1983? | 不在手上 | 檔案不在手上 | |
| ナイトライフ | 1983? | `nk98/Nightlife/` | 未掃 | 推測沒有頭像 |
| 団地妻の誘惑 | 1983? | `nk98/Danchi-zuma no Yuuwaku/` | 未掃 | 推測沒有頭像 |
| オランダ妻は電気ウナギの夢を見るか? | 1984? | `nk98/Do Dutchwives Dream of Electric Eel/` | 未掃 | 推測沒有頭像 |
| 信長の野望 | 1983? | `nk98/Nobunaga no Yabou/` | 不用掃 | 使用者決定（2026-10-17）。Steam 版確認沒有頭像 |
| 蒼き狼と白き牝鹿 | 1985 | 不在手上 | 檔案不在手上 | PC-88 版沒有頭像 |
| 三國志 | 1986? | `pc98/【PC98】三國志.rar`、`nk98/Sangokushi/` | 已匯出 `san1-pc98` | |
| 三國志 復刻版 | 1995 | `nk98/Sangokushi Fukkokuban/` | 標為版本（`san1-pc98`） | |
| 信長の野望・全国版 | 1987 | `nk98/Nobunaga no Yabou - Zenkoku-ban/` | 標為版本（`nobu2-pc88`） | 頭像與人名和 PC-88 版相同 |
| 蒼き狼と白き牝鹿・ジンギスカン | 1987 | `nk98/Aoki Ookami to Shiroki Mejika - Genghis Khan/` | 已匯出 `genghis-pc98` | 首發版 |
| トップマネジメント | 1988? | 不在手上 | 檔案不在手上 | |
| 信長の野望・戦国群雄伝 | 1988 | `pc98/[PC98] 信長の野望・戦国群雄伝.zip` | 已匯出 `nobu3-pc98` | |
| 維新の嵐 | 1988 | `pc98/[PC98] 維新の嵐.zip` | 已匯出 `ishin-pc98` | |
| 水滸伝・天命の誓い | 1989 | `pc98/[PC98] 水滸伝～天命の誓い～.ZIP` | 已匯出 `suikoden-pc98` | |
| 三國志II | 1989 | `pc98/【PC98】三國志２.rar` | 已匯出 `san2-pc98` | 重畫成 400 線 |
| 提督の決断 | 1989 | `pc98/[PC98] 提督の決断.zip` | 已匯出 `tk-pc98` | |
| ランペルール | 1990 | `nk98/L'Empereur/` | 標為版本（`lempe-x68`） | 映像在頭像 92 以後損壞，前 92 張相同 |
| 大航海時代 | 1990 | `pc98/[PC98] 大航海時代.zip` | 已匯出 `koukai-pc98` | |
| 信長の野望・武将風雲録 | 1991 | `pc98/[PC98] 信長の野望・風雲録.zip` | 已匯出 `nobu4-pc98` | |
| ロイヤルブラッド | 1991 | `pc98/[PC98] [光栄] ロイヤルブラッド(FDI).zip` | 已匯出 `royal-pc98` | |
| 伊忍道 打倒信長 | 1991 | `nk98/Inindou - Datou Nobunaga/` | 已匯出 `inindou-pc98` | 只有 7 位可以成家的女性 |
| ヨーロッパ戦線 | 1991 | `nk98/Europe Sensen/` | 已匯出 `europe-pc98` | |
| 三國志III | 1992 | `pc98/【PC98】三國志３.rar` | 已匯出 `san3-pc98` | |
| 蒼き狼と白き牝鹿・元朝秘史 | 1992 | `nk98/Aoki Ookami to Shiroki Mejika - Genchou Hishi/` | 已匯出 `genchou-pc98` | |
| 太閤立志伝 | 1992 | `pc98/[PC98] 太閤立志伝.zip` | 已匯出 `taikoh-pc98` | |
| エアーマネージメント | 1992 | `nk98/Air Management - Oozora ni Kakeru/` | 已匯出 `air-pc98` | 只有頭像，沒有人名 |
| リーディングカンパニー | 1992 | `nk98/Leading Company/` | 已匯出 `leading-pc98` | 只有頭像，沒有人名 |
| トップマネジメントII | 1992 | `nk98/Top Management II/` | 已匯出 `topman2-pc98` | 只有頭像 |
| トップマネジメント 山王台編 | 1993? | `nk98/Top Management Sannoudai Hen/` | 未解 | 臉可能在 `.ANM`，格式沒解開（BACKLOG） |
| 信長の野望・覇王伝 | 1992 | `pc98/[PC98] 信長の野望・覇王伝o.zip` | 已匯出 `nobu5-pc98` | |
| 大航海時代II | 1993 | `pc98/[PC98] 大航海時代２.zip` | 已匯出 `koukai2-pc98` | |
| 項劉記 | 1993 | `nk98/Kouryuuki/` | 已匯出 `kouryuuki-pc98` | |
| エアーマネージメントII | 1993 | `nk98/Air Management 2 - Koukuuou o Mezase/` | 已匯出 `air2-pc98` | 頭像同 DOS 版，只差色盤換算 |
| 独立戦争 | 1993 | `pc98/[PC98] 独立戦争.zip` | 已匯出 `liberty-pc98` | |
| 提督の決断II | 1993 | `pc98/[PC98] 提督の決断２.zip` | 已匯出 `tk2-pc98`（data-local） | kaodata 收 PK 版 |
| 提督の決断II パワーアップキット | 1994 | `pc98/[PC98] 提督の決断２　ﾊﾟﾜｰｱｯﾌﾟｷｯﾄ.zip` | 已匯出 `tk2pk-pc98` | |
| ウイニングポスト | 1993 | `nk98/Winning Post/` | 掃過，等 kaodata 決定 | 頭像、組合臉、馬頭檔和 DOS 版逐 byte 相同，人物頭像碼相同；只差色盤換算（同一張 4 bit 表，PC-98 是 v×17）。匯出程式在 winning-post-zh |
| ウイニングポスト2 Plus | 1995? | `nk98/Winning Post 2 Plus/` | 未掃 | |
| 麻雀大会 | 1987 | `nk98/Mahjong Taikai/` | 已匯出 `mahjong-pc98` | 15 位對手各 7 種表情，48×48 |
| 三國志IV | 1994 | `pc98/【PC98】三國志４.rar` | 不另收 | 本體完全包含在 PK 裡，kaodata 收 PK 版 |
| 三國志IV パワーアップキット | 1994 | `pc98/【PC98】三國志４　パワーアップキット.rar` | 已匯出 `san4pk-pc98` | |
| 源平合戦 | 1994 | `pc98/[PC98] 源平合戦.zip` | 已匯出 `genpei-pc98` | DOS 版標為版本 |
| 信長の野望・天翔記 | 1994 | `pc98/[PC98] 信長の野望・天翔記.zip` | 已匯出 `nobu6-pc98` | |
| 三國志英傑伝 | 1995 | `pc98/[PC98] 三国志・英傑伝.zip` | 已匯出 `eiketsu-pc98` | Win3.1 版標為版本 |
| 太閤立志伝II | 1995 | `pc98/[PC98] 太閤立志伝２.zip` | 已匯出 `taikoh2-pc98` | |
| 三國志V | 1995 | `pc98/【PC98】三國志５.rar` | 已匯出 `san5-pc98`（data-local） | kaodata 收 PK 版 |
| 三國志V パワーアップキット | 1996 | `pc98/【PC98】三國志５　パワーアップキット.rar` | 已匯出 `san5pk-pc98` | |
| プロジェネター | 1995 | `pc98/[PC98] [光栄] プロジェネター（FDI).zip` | 已匯出 `progen-pc98` | |
| 提督の決断III | 1996 | `pc98/[PC98] 提督の決断３.zip` | 已匯出 `tk3-pc98`（data-local） | kaodata 收 PK 版 |
| 提督の決断III パワーアップキット | 1996 | `pc98/[PC98] 提督の決断３　パワーアップキット.zip` | 已匯出 `tk3pk-pc98` | |
| 神々の大地 古事記外伝 | 1993 | `nk98/Kamigami no Daichi - Kojiki Gaiden/` | 不用掃 | 使用者決定（2026-10-17） |
| Emit Vol.1／Vol.3 | 1994–1995 | `nk98/Emit Vol. 1 - Toki no Maigo/`、`nk98/Emit Vol. 3 - Watashi ni Sayonara o/` | 不用掃 | 使用者決定（2026-10-17）。手上沒有 Vol.2 |
| デルフォイの神託 | 1993 | `nk98/Delphi no Shintaku/` | 未掃 | 推測沒有頭像 |
| 魂の門 ダンテ「神曲」より | 1993 | `nk98/Tamashii no Mon - Dante Shinkyoku yori/` | 未掃 | 推測沒有頭像 |
| バンドくん | 1993? | `nk98/Band-kun/` | 未掃 | 推測沒有頭像（音樂軟體） |
| Super Dog World | 1993? | `nk98/Super Dog World/` | 未掃 | 推測沒有頭像 |
| Life is Music | 1993? | `nk98/Life is Music/` | 未掃 | 推測沒有頭像 |

## X68000

| 遊戲 | 年 | 位置 | 狀態 | 備註 |
| ---- | -: | ---- | ---- | ---- |
| 三國志 | 1988 | `ia68/sangokushi_1988_koei_disk_1_of_x68k/` | 已匯出 `san1-x68` | 256 色 48×80 |
| 信長の野望・全国版 | 1988 | `ia68/nobunaga_no_yabou_zenkokuhan_1_x68k/` | 已匯出 `nobu2-x68` | 重畫 64×80 |
| 蒼き狼と白き牝鹿・ジンギスカン | 1989 | `ia68/aoki_ookami_to_shiroki_meshika_x68k/` | 已匯出 `genghis-x68` | 重畫 48×80 |
| 信長の野望・戦国群雄伝 | 1989 | `ia68/nobunaga_no_yabou_sengoku_guny_x68k/` | 標為版本（`nobu3-pc98`） | |
| 水滸伝・天命の誓い | 1989 | `ia68/suikoden_tenmei_no_chikai_1989_x68k/` | 已匯出 `suikoden-x68` | |
| 三國志II | 1990 | `x68000/Sangokushi II [FD]/` | 已匯出 `san2-x68` | |
| 維新の嵐 | 1990 | `ia68/ishin_no_arashi_1990_koei_disk_x68k/` | 已匯出 `ishin-x68` | 重畫 48×80 |
| 提督の決断 | 1990 | `ia68/teitoku_no_ketsudan_1990_koei_x68k/` | 已匯出 `tk-x68` | 重畫 56×72 |
| ランペルール | 1990 | `ia68/lempereur_19xx_koei_disk_1_of_x68k/` | 已匯出 `lempe-x68` | PC-98 版標為它的版本 |
| 大航海時代 | 1990 | `ia68/daikoukai_jidai_19xx_koei_disk_x68k/` | 標為版本（`koukai-pc98`） | |
| 信長の野望・武将風雲録 | 1991 | `ia68/nobunaga_no_yabou_bushou_fuuun_x68k/` | 已匯出 `nobu4-x68` | 只有色盤不同 |
| ロイヤルブラッド | 1991 | `ia68/royal_blood_19xx_koei_disk_1_o_x68k/` | 已匯出 `royal-x68` | |
| 伊忍道 打倒信長 | 1991 | `ia68/inindou_datou_nobunaga_199x_ko_x68k/` | 已匯出 `inindou-x68` | |
| ヨーロッパ戦線 | 1992 | `ia68/europe_sensen_1992_koei_disk_1_x68k/` | 已匯出 `europe-x68` | 映像只讀得到劇本 0、5、6 |
| 三國志III | 1992 | `ia68/sangokushi_iii_1992_koei_disk_x68k/` | 已匯出 `san3-x68` | |
| 太閤立志伝 | 1992 | `ia68/taikou_risshiden_1992_koei_dis_x68k/` | 已匯出 `taikoh-x68` | |
| エアーマネージメント | 1992 | `ia68/air_management_19xx_koei_disk_x68k/` | 已匯出 `air-x68` | |
| リーディングカンパニー | 1992 | `ia68/leading_company_1992_koei_disk_x68k/` | 已匯出 `leading-x68` | |
| 信長の野望・覇王伝 | 1993 | `ia68/nobunaga_no_yabou_hanouden_199_x68k/` | 已匯出 `nobu5-x68` | |
| 蒼き狼と白き牝鹿・元朝秘史 | 1993 | `ia68/aoki-ookami-to-shiroki-meshika-genchou-hishi-1993-koei-disk-1-of-3/` | 已匯出 `genchou-x68` | |
| 項劉記 | 1993 | `ia68/kouryuuki_1993_koei_disk_1_of_x68k/` | 已匯出 `kouryuuki-x68` | |
| ウイニングポスト | 1993 | `ia68/winning_post_1993_koei_disk_1_x68k/` | 已匯出 `winning-x68`（winning-post-zh） | 本 repo 只核對過色盤 |
| 大航海時代II | 1994? | 不在手上 | 檔案不在手上 | IA 的 X68000 合集沒有 |
| 三國志IV | 1994? | 不在手上 | 檔案不在手上 | IA 的 X68000 合集沒有 |
| 提督の決断II | 1994? | 不在手上 | 檔案不在手上 | IA 的 X68000 合集沒有 |

IA 的 X68000 合集不是完整的光榮清單，可能還有其他作品沒找到。

## DOS

### 中文版

| 遊戲 | 年 | 位置 | 狀態 | 備註 |
| ---- | -: | ---- | ---- | ---- |
| 三國志II | 1990? | `dos/san2.zip` | 已匯出 `san2-dos` | 頭像沿用 PC-88 的 200 線圖 |
| 信長之野望II（戰國群雄傳） | 1993 | `dos/信長之野望２_中文版_nobu2-c.rar` | 已匯出 `nobu3-dos` | 英文版 Nobunaga's Ambition II 的移植 |
| 水滸傳・天命之誓 | 1993 | `dos/水滸傳_中文版_water.zip` | 已匯出 `suikoden-dos` | 英文版 Bandit Kings 的移植 |
| 成吉思汗 | 1992 | `dos/成吉思汗_中文版_khan-c.zip` | 已匯出 `genghis-dos` | 英文版 Genghis Khan 的移植 |
| 拿破崙 | 1993? | `dos/拿破崙_中文版_l-empereur-c.rar` | 已匯出 `lempe-dos` | |
| 大航海時代 | 1993 | `dos/大航海時代_中文版_uwc.zip` | 已匯出 `koukai-dos` | 英文版 Uncharted Waters 的移植 |
| 信長之野望・武將風雲錄 | 1994 | `dos/信長之野望．武將風雲錄_中文版_Nobu4.rar` | 已匯出 `nobu4-dos` | |
| 歐陸戰線 | 1993? | `dos/歐陸戰線_中文版_europe.rar` | 已匯出 `europe-dos` | |
| 三國志III | 1993? | `dos/三國志３_中文版_San3.rar` | 已匯出 `san3-dos` | |
| 元朝秘史 | 1994 | `dos/元朝秘史_killpeople.rar` | 已匯出 `genchou-dos` | |
| 項劉記 | 1994 | `dos/項劉記_中文版_hanlau.rar` | 已匯出 `kouryuuki-dos` | 宏碁發行 |
| 獨立戰爭 | 1994 | `dos/獨立戰爭_中文版_liberty.rar` | 已匯出 `liberty-dos` | 日文 DOS/V 版的移植 |
| 航空霸業II | 1994? | `dos/航空霸業２_中文版_air2.rar` | 已匯出 `air2-dos` | 只有頭像 |
| 三國志IV（含威力加強版） | 1994 | `dos/三國志４_中文版_San4.rar`、`dos/6.10_三國志四加強版_killpeople.rar` | 已匯出 `san4pk-dos` | 本體不另收 |
| 太閤立志傳 | 1995 | `win/[系列] 太閣立志傳 …/$太閤立志傳1.rar` | 已匯出 `taikoh-dos` | DOSBox 包 |
| 源平合戰 | 1994 | 不在手上 | 標為版本（`genpei-pc98`） | 舊 id `genpei-dos`，手上沒有原檔 |
| 三國志英傑傳 | 1995 | `dos/6.10_三國志英傑傳_killpeople.rar` | 已匯出 `eiketsu-dos` | |
| 三國志V 威力加強版 | 1996 | `dos/6.3_三國志五DOS加強版_killpeople.rar` | 已匯出 `san5pk-dos` | MAIN.EXE 是破解版 |
| 光榮賽馬（ウイニングポスト） | 1994? | 不在 kaodata-re | 已匯出 `winning-dos`（winning-post-zh） | |
| 大航海時代II | 1994? | 不在手上 | 檔案不在手上 | README 的舊 face 命令支援過 |
| 提督之決斷II | 1994? | 不在手上 | 檔案不在手上 | README 的舊 face 命令支援過 |
| 魔法皇冠（ロイヤルブラッド） | 1993? | 不在手上 | 檔案不在手上 | README 的舊 face 命令支援過 |

### 英文版

英文版只差人名語言時，依收錄規則不另收。

| 遊戲 | 年 | 位置 | 狀態 | 備註 |
| ---- | -: | ---- | ---- | ---- |
| Nobunaga's Ambition（全国版） | 1988 | `dos/信長之野望_英文版_nobunagas-ambition.zip` | 已匯出 `nobu2-dos` | 重畫的 4 色 EGA 頭像 |
| Romance of the Three Kingdoms | 1988? | `dos/三國志_英文版_romance-of-the-three-kingdoms.zip` | 已匯出 `san1-dos` | |
| Genghis Khan | 1989 | `dos/成吉思汗_英文版_genghis-khan.zip` | 不另收（`genghis-dos`） | 頭像檔逐 byte 相同 |
| Bandit Kings of Ancient China | 1989 | `dos/水滸傳_英文版_bandit-kings-of-ancient-china.zip` | 不另收（`suikoden-dos`） | 頭像檔逐 byte 相同 |
| Romance of the Three Kingdoms II | 1990? | `dos/三國志２_英文版_romance-of-the-three-kingdoms-ii.zip` | 未掃 | 沒有和 `san2-dos` 比對過 |
| Nobunaga's Ambition II | 1990 | `dos/信長之野望２_英文版_nobunagas-ambition-ii.zip` | 不另收（`nobu3-dos`） | 頭像與頭像碼相同，只差人名 |
| L'Empereur | 1990? | `dos/拿破崙_英文版_l-empereur.zip` | 不另收（`lempe-dos`） | `KAODATA.DAT` 相同 |
| Uncharted Waters | 1991 | `dos/大航海時代_英文版_uncharted-waters.zip` | 不另收（`koukai-dos`） | 頭像檔逐 byte 相同 |
| Romance of the Three Kingdoms III | 1992? | 不在手上 | 檔案不在手上 | |
| Gemfire（ロイヤルブラッド） | 1992? | 不在手上 | 檔案不在手上 | |
| Genghis Khan II（元朝秘史） | 1993? | 不在手上 | 檔案不在手上 | |
| Operation Europe（ヨーロッパ戦線） | 1993? | 不在手上 | 檔案不在手上 | |
| Liberty or Death | 1993 | 不在手上 | 檔案不在手上 | 北美原版 |
| Aerobiz、Aerobiz Supersonic | 1993–1994? | 不在手上 | 檔案不在手上 | |
| P.T.O.（提督の決断） | 1993? | 不在手上 | 檔案不在手上 | |
| Rise of the Phoenix（項劉記） | 1993? | 不在手上 | 檔案不在手上 | |
| Uncharted Waters: New Horizons | 1994? | 不在手上 | 檔案不在手上 | |
| Romance of the Three Kingdoms IV | 1995? | 不在手上 | 檔案不在手上 | |
| Celtic Tales: Balor of the Evil Eye | 1995? | 不在手上 | 檔案不在手上 | |

## DOS/V（日文版）

日文 DOS/V 版目前都沒有原檔。中文 `liberty-dos` 是日文 DOS/V 版的移植（`LIBERTY.VER` 寫著 DOS/V）。

| 遊戲 | 年 | 位置 | 狀態 | 備註 |
| ---- | -: | ---- | ---- | ---- |
| 独立戦争 Liberty or Death | 1993? | 不在手上 | 檔案不在手上 | 中文版 `liberty-dos` 由它移植 |
| 三國志IV | 1994? | 不在手上 | 檔案不在手上 | |
| 信長の野望・天翔記 | 1995? | 不在手上 | 檔案不在手上 | |
| 大航海時代II | 1994? | 不在手上 | 檔案不在手上 | |
| 提督の決断II | 1994? | 不在手上 | 檔案不在手上 | |
| 三國志英傑伝 | 1995? | 不在手上 | 檔案不在手上 | IA 有一筆 `sangokushi-eiketsuden-dosv`，沒有下載 |
| 三國志V | 1995? | 不在手上 | 檔案不在手上 | |

DOS/V 的作品清單憑記憶整理，沒有逐款查證。
