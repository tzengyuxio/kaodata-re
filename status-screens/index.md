# 武將個人資料畫面收集

三國志、信長の野望各代「一次顯示一位武將的頭像與能力」的畫面，以 PC-98 與 Windows 版為主。圖片不進版控（含遊戲美術），只有這份索引進版控。

## 檔名與來源標記

`<id>-<來源>-<NN>.<副檔名>`，id 照 dataset 命名（`san4pk-pc98`、`nobu6-win`）；平台不明時用 `-multi`。

| 來源標記 | 意思 | 這份索引記什麼 |
|---|---|---|
| `cap` | 截圖：遊戲跑起來時擷取 | 誰操作、誰截圖、模擬器與版本、劇本與時間點 |
| `web` | 網路下載 | 頁面網址、站名／作者、取得日期、平台怎麼判斷的 |
| `comp` | 組合：從遊戲素材拼出來的仿製畫面，不是遊戲畫面 | 用了哪些素材、怎麼拼（目前沒有） |

`web` 的平台可信度：**確定**（頁面寫明機種，或截圖帶 Windows 標題列）、**推定**（多平台同時發售、頁面沒寫截圖來自哪一版）、**不明**。網路圖的取得日期都是 2026-10-20。

截圖環境（`cap`）：DOSBox-X 2026.08.31，`machine=pc98`，從原版磁碟映像或取出的檔案執行；DOSBox-X 內建截圖，640×400 原生解析度。這裡只放挑過的；同一輪的全部截圖（選單、劇本選擇等）放在 `captures/screenshots/<id>/`，savestate 放在 `captures/saves/`。

## 三國志

| 檔名 | 平台 | 來源 | 內容 | 出處 |
|---|---|---|---|---|
| `san1-fc-web-01.jpg` | FC | web 確定 | 周瑜（蔡瑁配下）的武將狀態畫面 | [三國志シリーズ 〜レトロゲーム攻略記〜](https://sangokushiplay.seesaa.net/article/368314594.html)（芸美有） |
| `san1-fc-web-02.jpg` | FC | web 確定 | 魯粛（蔡瑁配下），同上 | [同站](https://sangokushiplay.seesaa.net/article/367951940.html) |
| `san1-pc98-cap-01.png` | PC-98 | cap | 開局選君主時的 8 位君主能力一覽（初代沒有單一武將的資料畫面，這是最接近的） | 使用者操作、Claude 截取視窗（2026-10-20）。NP2kai（2026-09-05 原始碼自行編譯）＋ Osaka 替代字型：沒有 PC-98 字型 ROM，半形數字下半被切掉，字形與實機不同。DOSBox-X 跑這款會殘留舊文字，所以改用 NP2kai |
| `san2-pc98-cap-01.png` | PC-98 | cap | 曹操（君主）的武將資訊欄，劇本 1、189 年 1 月 | 使用者操作、DOSBox-X 截圖（2026-10-20） |
| `san2-pc98-cap-02.png` | PC-98 | cap | 夏侯惇（曹操配下），同上 | 同上 |
| `san2-pc98-web-01.jpg` | PC-98 | web 確定 | 張飛（劉備配下）的武將資訊欄 | [コーエー レトロゲームの館](https://koeiretro.hatenablog.com/entry/blog-entry-5.html)（okaremon0701），「PC-98版」段 |
| `san2-x68-web-01.jpg` | X68000 | web 確定 | 張飛，同上 | 同一篇，「X68000版」段 |
| `san3-pc98-cap-01.png` | PC-98 | cap | 曹操（君主）的武將資訊視窗，劇本 1、189 年 1 月 | 使用者操作、DOSBox-X 截圖（2026-10-20）。各片磁碟的檔案合併在同一個資料夾，掛成 A、B 槽執行，不用換片 |
| `san3-pc98-cap-02.png` | PC-98 | cap | 夏侯惇（驃騎将軍），同上 | 同上 |
| `san3-pc98-cap-03.png` | PC-98 | cap | 曹操的資訊視窗加上道具「孟徳新書」的說明 | 同上 |
| `san3-pc98-web-01.jpg` | PC-98 | web 確定 | 趙雲的武將資訊視窗 | [コーエー レトロゲームの館](https://koeiretro.hatenablog.com/entry/blog-entry-2.html)，標題「PC-98版 三国志Ⅲ」 |
| `san3-pc98-web-02.jpg` | PC-98 | web 確定 | 向朗，同上 | 同上 |
| `san4-pc98-web-01.jpg` | PC-98 | web 確定 | 趙雲的「武将」視窗 | [コーエー レトロゲームの館](https://koeiretro.hatenablog.com/entry/blog-entry-22.html)，標題「PC-98版 三国志Ⅳ」 |
| `san4-pc98-web-02.jpg` | PC-98 | web 確定 | 程昱，同上 | 同上 |
| `san4pk-pc98-cap-01.png` | PC-98 | cap | 曹操（君主）的武將視窗，含特殊能力表與三國英雄列伝，189 年 12 月 | 使用者操作、Claude 截取視窗（2026-10-20）。NP2kai＋Osaka 替代字型（列伝等文字層的濁點位置與實機不同）。起動ディスク＋ゲームディスク（防拷鑰匙片）＋原版附的 HDI，不用換片；DOSBox-X 跑三國志IV 會卡在「動作環境」畫面、不吃輸入 |
| `san4pk-pc98-cap-02.png` | PC-98 | cap | 夏侯惇（将軍），同上 | 同上 |
| `san4pk-win-web-01.jpg` | Win | web 推定 | 周瑜的「武将」視窗（站方裁切） | [レトロゲームの塔](https://towerofclassicgame.com/sangoku4)：PK 版、640×480；FM TOWNS 也是 640×480，無法排除 |
| `san5-pc98-cap-01.png` | PC-98 | cap | 曹操（君主）的武將詳細，189 年 12 月 | 使用者操作、DOSBox-X 截圖（2026-10-20）。7 片磁碟的檔案合併成一個目錄掛成 A:／B:／C:，`san5 /b=16` 起動。防拷問答「D行7列目の顔を選んで下さい」的答案是頭像碼 238（MAIN.EXE 0x37B46 起的 71 筆排序頭像碼，A–F 行×1–12 列逐行排；實際 D7 是第 41 筆（從 0 起算），表在 D7 之前少一格，缺哪格未查） |
| `san5pk-pc98-cap-01.png` | PC-98 | cap | 曹操（君主）的武將詳細，189 年 12 月 | 使用者操作、DOSBox-X 截圖（2026-10-20）。起動ディスク＋原版附的 HDI，不用換片。防拷問答（「E行8列目の顔を選んで下さい」）照原版附的 `三国志5PK武将列伝.jpg` 頭像表回答；答錯會改寫 HDI，要換回乾淨的複本 |
| `san5pk-pc98-cap-02.png` | PC-98 | cap | 夏侯惇（昭文将軍），同上 | 同上 |
| `san5pk-pc98-cap-03.png` | PC-98 | cap | 夏侯惇的武將詳細上開著三國志武将列伝 | 同上 |
| `san5pk-pc98-cap-04.png` | PC-98 | cap | 夏侯惇的戦績視窗 | 同上 |
| `san5pk-win-web-01.jpg` | Win | web 推定 | 周瑜的武將詳細（站方裁切） | [レトロゲームの塔](https://towerofclassicgame.com/sangoku5)：PK 版、640×480 |
| `san8-win-web-01.jpg` | Win | web 確定 | 曹操的「武将情報」 | [4Gamer レビュー](https://www.4gamer.net/review/live/san8.html)（2001-06，PS2 版 2002 年才出） |
| `san9-win-web-01.jpg` | Win | web 確定 | 劉備的「武将情報」（狀態分頁） | [GAME Watch PCゲームレビュー](https://game.watch.impress.co.jp/docs/20030326/san9.htm)（2003-03-26） |
| `san9-win-web-02.jpg` | Win | web 確定 | 関羽的「武将情報」（兵法分頁） | 同上 |
| `san10-win-web-01.jpg` | Win | web 確定 | 孫堅的「主人公情報」 | [GAME Watch](https://game.watch.impress.co.jp/docs/20040702/sanx.htm)（2004-07-02） |
| `san10-win-web-02.jpg` | Win | web 確定 | 夏侯惇的「主人公情報」 | [4Gamer](http://www.4gamer.net/news/history/2004.05/20040524000005detail.html)（2004-05-24） |
| `san11-win-web-01.jpg` | Win | web 確定 | 鄧芝的「発見武将」視窗（探索時跳出，不是選單的武将情報） | [4Gamer レビュー](https://www.4gamer.net/review/san11/san11.shtml)（2006-03-17） |
| `san13pk-win-web-01.jpg` | Win | web 推定 | 班雪的「武将情報」 | [4Gamer](https://www.4gamer.net/games/354/G035404/20161104013/)（PC／PS4／PS3 同時發售） |
| `san13pk-win-web-02.jpg` | Win | web 推定 | 関良的「武将情報」 | 同上 |
| `san14-win-web-01.jpg` | Win | web 推定 | 劉備的「武将詳細」，只有資料區的局部（800×388） | [GAME Watch](https://game.watch.impress.co.jp/docs/news/1220225.html)（2019-11-22） |
| `san14-win-web-02.jpg` | Win | web 推定 | ミッターマイヤー的「武将詳細」（銀河英雄伝説合作 DLC，不是三國武將） | [4Gamer](https://www.4gamer.net/games/472/G047208/20200319055/)（2020-03-19） |
| `san14pk-win-web-01.jpg` | Win | web 推定 | 烏桓豪勇的「武将詳細」 | [4Gamer](https://www.4gamer.net/games/525/G052531/20201207040/)（2020-12-09） |
| `san14pk-win-web-02.jpg` | Win | web 推定 | 烏桓単于的「武将詳細」（能力分頁） | 同上 |

## 信長の野望

| 檔名 | 平台 | 來源 | 內容 | 出處 |
|---|---|---|---|---|
| `nobu1-win-web-01.jpg` | Win（Steam 復刻） | web 確定 | 主地圖右側織田信長的大名能力欄（初代只有大名、沒有頭像） | [Steam](https://store.steampowered.com/app/544990/) 官方截圖 |
| `nobu1-win-web-02.jpg` | Win（Steam 復刻） | web 確定 | 開局決定信長能力的畫面（純文字） | 同上 |
| `nobu2-pc88-web-01.png` | PC-88 | web 確定 | 決定斎藤義竜能力的畫面（純文字） | [MobyGames](https://www.mobygames.com/game/5825/nobunagas-ambition/screenshots/pc88/510564/)（Unicorn Lynx） |
| `nobu2-pc98-web-01.png` | PC-98 | web 確定 | 斎藤義竜的大名能力確認畫面，有頭像 | [MobyGames](https://www.mobygames.com/game/5825/nobunagas-ambition/screenshots/pc98/473194/) |
| `nobu2-pc98-web-02.png` | PC-98 | web 確定 | 決定斎藤義竜能力的畫面（純文字） | [MobyGames](https://www.mobygames.com/game/5825/nobunagas-ambition/screenshots/pc98/473193/) |
| `nobu2-win-web-01.jpg` | Win（Steam 復刻） | web 確定 | 織田信長的大名欄，有頭像 | [Steam](https://store.steampowered.com/app/521660/) 官方截圖 |
| `nobu2-win-web-02.jpg` | Win（Steam 復刻） | web 確定 | 同上，左邊是近畿放大地圖 | 同上 |
| `nobu3-pc98-web-01.png` | PC-98 | web 確定 | 決定上杉謙信能力的畫面，有頭像 | [MobyGames](https://www.mobygames.com/game/6167/nobunagas-ambition-ii/screenshots/pc98/473563/) |
| `nobu3-pc98-web-02.png` | PC-98 | web 確定 | 決定毛利輝元能力的畫面，有頭像 | [MobyGames](https://www.mobygames.com/game/6167/nobunagas-ambition-ii/screenshots/pc98/473574/) |
| `nobu4-pc98-cap-01.png` | PC-98 | cap | 織田信長（尾張大名）的「武将」視窗，1555 年 | 使用者操作、DOSBox-X 截圖（2026-10-20）。各片檔案合併在同一個資料夾，掛成 A、B 槽執行 |
| `nobu4-pc98-cap-02.png` | PC-98 | cap | 柴田勝家（尾張武将），同上 | 同上 |
| `nobu4-sfc-web-01.png` | SFC（北美英文版） | web 確定 | 林通勝的武將能力畫面（英文） | [MobyGames](https://www.mobygames.com/game/12611/nobunagas-ambition-lord-of-darkness/screenshots/snes/106882/)（Spencer Hart） |
| `nobu5-pc98-web-01.png` | PC-98 | web 確定 | 大友宗麟的大名資料窗 | [MobyGames](https://www.mobygames.com/game/44448/nobunaga-no-yabo-haoden/screenshots/pc98/457741/) |
| `nobu5pk-win-web-01.jpg` | Win（Steam） | web 確定 | PK 的「武将エディタ」：織田信長（編輯器，不是遊戲本身的武將情報） | [Steam](https://store.steampowered.com/app/628090/) 官方截圖 |
| `nobu6-pc98-web-01.png` | PC-98 | web 確定 | 朽木稙綱的武將資料窗 | [MobyGames](https://www.mobygames.com/game/171215/nobunaga-no-yabo-tenshoki/screenshots/pc98/1137155/)（Infernos） |
| `nobu6pk-pc98-cap-01.png` | PC-98 | cap | 織田信長（13 歲，織田信秀軍團部將）的武將視窗，含能力、兵科適性與列伝，劇本「信長元服（1546 年）」 | 使用者操作、DOSBox-X 截圖（2026-10-20）。neo-kobe 合集的 PK 硬碟版（HD 開機片＋HDI），不用換片；磁片版（6 片 FDI）在 DOSBox-X 會一直要求換片。防拷問答的答案表在 `MAINPK.EXE` 0x3DE54：72 筆 u16 頭像碼，A–F 列 × 1–12 行，同一列由上往下排（E列12行目＝第 59 筆＝頭像碼 239） |
| `nobu8-win-web-01.jpg` | Win | web 確定 | 服部友貞的捕虜處置視窗（完整資料，不是選單的武将情報） | [PC Watch](https://pc.watch.impress.co.jp/docs/article/990308/game.htm)（1999-03-08），截圖帶 Windows 標題列 |
| `nobu9pk-win-web-01.jpg` | Win | web 確定 | 柴田勝家的武將資料面板 | [4Gamer Preview](https://www.4gamer.net/previews/pre_nobu_puk.html)（朝倉哲也） |
| `nobu12-win-web-01.jpg` | Win | web 確定 | 佐竹義斯的「処遇選択」視窗（發售前版本） | [4Gamer](https://www.4gamer.net/games/020/G002045/20050513213023/)（2005-05-13，當時只有 Win 版） |
| `nobu14-win-web-01.jpg` | Win | web 推定 | 百地三太夫的「武将情報」 | [4Gamer](https://www.4gamer.net/games/215/G021583/20131023025/)（2013-10-23，同時列 PS3） |
| `nobu15-multi-web-01.jpg` | 不明 | web 不明 | 岡国高的「武将情報」 | [ファミ通.com](https://www.famitsu.com/news/201711/10145818.html) |
| `nobu15-multi-web-02.jpg` | 不明 | web 不明 | 明智光秀的「武将情報」（手冊加了紅框） | [官方 Web 手冊](http://www.gamecity.ne.jp/manual/O3U5IWuB/jp/6100.html) |
| `nobu16-multi-web-01.png` | 不明 | web 不明 | 柴田勝家的武將情報 | [官方 Web 手冊](https://www.gamecity.ne.jp/manual/shinsei/jp/4300.html) |
| `nobu16-multi-web-02.jpg` | 不明 | web 不明 | 宮部継潤的「武将情報」（有電撃浮水印） | [電撃オンライン](https://dengekionline.com/articles/139377/) |

## 還缺的

PC-98 截圖：可以自己截的（`games/` 裡有原版）優先補；網路上找不到的也列出來。

| 遊戲 | PC-98 | Win | 備註 |
|---|---|---|---|
| 三國志 | 一覽表（沒有個人畫面；替代字型） | 缺 | 另有 FC 版 |
| 三國志II | ✓ | 缺 | Steam 版和 PC-98 版畫面相同 |
| 三國志III | ✓（含截圖） | 缺 | |
| 三國志IV／PK | ✓／✓（截圖） | 缺／推定 | 無印可截：把檔案寫進 PK 的 HDI 複本，用 NP2kai |
| 三國志V／PK | ✓／✓（截圖） | 缺／推定 | |
| 三國志VI、VII | — | 缺 | 沒有 PC-98 版；`games/san6pk-win`、`san7pk-win` 有原版但本機不能跑 Windows |
| 三國志12、13 無印 | — | 缺 | 網路上沒有武將情報畫面 |
| 三國志 VIII–11 PK | — | 缺 | 網路上只有編輯畫面 |
| 信長 初代 | 缺 | ✓ | |
| 信長 戦国群雄伝 | ✓ | 缺 | |
| 信長 武将風雲録 | ✓（截圖） | 缺 | |
| 信長 覇王伝 | ✓ | 缺（PK 只有編輯器） | |
| 信長 天翔記／PK | ✓／✓（截圖） | 缺 | |
| 信長 将星録 | 缺 | 缺 | 所有平台都沒找到 |
| 信長 烈風伝 PK、嵐世記、蒼天録、天下創世、革新 PK、天道、創造 PK、大志 PK、新生 PK | — | 缺 | 網路上只有編輯、一覽或其他畫面 |
| 信長 大志、新生 | — | 不明 | 收了多平台共用的圖 |
