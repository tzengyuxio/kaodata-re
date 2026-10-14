# kaodata

Early KOEI Games Data Research

早期光榮遊戲資料研究

這個專案的目的是研究早期光榮遊戲的資料格式，並提供一個簡單的工具來讀取這些遊戲的資料。

最初是以研究三國志系列的頭像為主，專案名稱 `kaodata` 即來自 三國志II 與 三國志III
的頭像資料檔。之後陸續加入對於其他遊戲資料的支援。遊戲資料的研究範圍主要包含
三國志系列、信長之野望系列，以及 2000 年之前的光榮歷史策略模擬遊戲。

## Game List 遊戲列表

|    ID     |            名稱             | 年份 |      顏ＣＧ      | 人物  | 大眾臉 |        Memo         |
| --------- | --------------------------- | ---: | :--------------: | :---: | ------ | ------------------- |
| SAN1      | 三國志                      | 1985 |     DOS,PC98     |   ○   |        |                     |
| SAN2      | 三國志II                    | 1989 | DOS,PC98,X68,WIN |   ○   |        |                     |
| SAN3      | 三國志III                   | 1992 |   DOS,PC98,WIN   |   ○   |        |                     |
| SAN4      | 三國志IV                    | 1994 |     DOS,PC98     |   ○   |        |                     |
| SAN5      | 三國志V                     | 1995 |     DOS,PC98     |   ○   |        |                     |
| SAN6      | 三國志VI                    | 1998 |       WIN        |       |        |                     |
| SAN7      | 三國志VII                   | 2000 |       WIN        |       |        |                     |
| SAN8      | 三國志VIII                  | 2001 |       WIN        |       |        |                     |
| SAN9      | 三國志IX                    | 2003 |       WIN        |       |        |                     |
| SAN10     | 三國志X                     | 2004 |       WIN        |       |        |                     |
| SAN11     | 三國志11                    | 2006 |       WIN        |       |        |                     |
| SAN12     | 三國志12                    | 2012 |       WIN        |       |        |                     |
| SAN13     | 三國志13                    | 2016 |       WIN        |       |        |                     |
| SAN14     | 三國志14                    | 2020 |                  |       |        |                     |
| NOBU1     | 信長之野望                  | 1983 |                  |       |        |                     |
| NOBU2     | 信長之野望 全國版           | 1986 |                  |       |        |                     |
| NOBU3     | 信長之野望 戰國群雄傳       | 1988 |       DOS        |       |        | 台灣稱 信長之野望II |
| NOBU4     | 信長之野望 武將風雲錄       | 1990 |       DOS        |       |        |                     |
| NOBU5     | 信長之野望 霸王傳           | 1992 |                  |       |        |                     |
| NOBU6     | 信長之野望 天翔記           | 1994 |                  |       |        |                     |
| NOBU7     | 信長之野望 將星錄           | 1997 |                  |       |        |                     |
| NOBU8     | 信長之野望 烈風傳           | 1999 |                  |       |        |                     |
| NOBU9     | 信長之野望 嵐世紀           | 2001 |                  |       |        |                     |
| NOBU10    | 信長之野望 蒼天錄           | 2002 |                  |       |        |                     |
| NOBU11    | 信長之野望 天下創世         | 2003 |                  |       |        |                     |
| NOBU12    | 信長之野望 革新             | 2005 |                  |       |        |                     |
| NOBU13    | 信長之野望 天道             | 2009 |                  |       |        |                     |
| NOBU14    | 信長之野望 創造             | 2013 |                  |       |        |                     |
| NOBU15    | 信長之野望 大志             | 2017 |                  |       |        |                     |
| NOBU16    | 信長之野望 新生             | 2022 |                  |       |        |                     |
|           | 蒼狼與白鹿                  | 1985 |                  |       |        |                     |
| GENGHIS   | 蒼狼與白鹿 成吉思汗         | 1987 |       DOS        |       |        |                     |
| (GENCHOH) | 蒼狼與白鹿 元朝秘史         | 1992 |                  |       |        |                     |
|           | 成吉思汗 蒼狼與白鹿IV       | 1998 |                  |       |        |                     |
| KOUKAI    | 大航海時代                  | 1990 |       DOS        |       |        |                     |
| KOUKAI2   | 大航海時代II                | 1993 |       DOS        |       |        |                     |
| KOUKAIGD  | 大航海時代外傳              | 1998 |       WIN        |       |        |                     |
| KOUKAI3   | 大航海時代III Costa del Sol | 1996 |       WIN        |       |        |                     |
| TAIKOH    | 太閤立志傳                  | 1992 |       DOS        |       |        |                     |
| (TAIKOH2) | 太閤立志傳II                | 1995 |                  |       |        |                     |
| (TAIKOH3) | 太閤立志傳III               | 1999 |                  |       |        |                     |
| EUROPE    | 歐陸戰線                    | 1991 |       DOS        |       |        |                     |
| ISHIN     | 維新之嵐                    | 1988 |       PC98       |       |        |                     |
| KOHRYUKI  | 項劉記                      | 1993 |       DOS        |   ○   |        |                     |
| LEMPE     | 拿破崙                      | 1990 |       DOS        |   ○   |        |                     |
| ROYAL     | 魔法皇冠                    | 1991 |     DOS,PC98     |       |        |                     |
| (ROYAL2)  | 王國興亡錄                  | 1999 |                  |       |        |                     |
| SUIKODEN  | 水滸傳・天命之誓            | 1989 |     DOS,PC98     |   ○   |        |                     |
| TK2       | 提督之決斷II                | 1993 |       DOS        |       |        |                     |
| WINNING   | 光榮賽馬／賽馬大亨          | 1993 |       DOS        |       |        |                     |
| AIR2      | 航空霸業II                  | 1993 |       DOS        |       |        |                     |
| EIKETSU   | 三國志英傑傳                | 1995 |     DOS,WIN      |       |        |                     |
| KOUMEI    | 三國志孔明傳                | 1996 |       WIN        |       |        |                     |
|           | 毛利元就 三矢之誓           | 1996 |                  |       |        |                     |
|           | 織田信長傳                  | 1998 |                  |       |        |                     |
|           | 三國志曹操傳                | 1998 |                  |       |        |                     |
| GENPEI    | 源平合戰                    | 1994 |                  |       |        |                     |
| LIBERTY   | 獨立戰爭                    | 1993 |       DOS        |       |        |                     |
|           | 魔眼邪神-賽爾特傳說         | 1996 |                  |       |        |                     |

* 目前支援 33 款作品的顏ＣＧ匯出，以及 8 款作品的人物資料匯出
* `ID` 一欄中，括號為暫定名稱
* `顏ＣＧ` 一欄中，列出支援輸出的對應平台遊戲版本

## Usage 使用方法

(WIP)

### 匯出 kaodata 統一格式資料集

```sh
cd dekoei
python dekoei.py export genpei-dos --game-dir <GENPEI 原版目錄> --out <kaodata>/data-local/genpei-dos
```

輸出 `dataset.json`、像素檔（`pixels.bin`、`portraits.bin`）與 `checksums.json`，格式見 kaodata 網站 repo 的 `docs/data-format.md`。目前支援的資料集：

| DATASET      | 遊戲                           | 來源版本   | 人物 | 頭像 | 組合臉 | 格式筆記                         |
| ------------ | ------------------------------ | ---------- | ---: | ---: | :----: | -------------------------------- |
| `genpei-dos` | 源平合戰                       | DOS        |  400 |   90 |   ○    | [notes/genpei.md](notes/genpei.md) |
| `san1-dos`   | 三國志                         | DOS 英文版 |  255 |   84 |   ○    | [notes/san1.md](notes/san1.md)     |
| `san1-pc98`  | 三國志                         | PC-98      |  255 |   84 |   ○    | [notes/san1.md](notes/san1.md)     |
| `san2-dos`   | 三國志II                       | DOS 中文版 |  352 |  219 |   ○    | [notes/san2.md](notes/san2.md)     |
| `san2-pc98`  | 三國志II                       | PC-98      |  352 |  219 |   ○    | [notes/san2.md](notes/san2.md)     |
| `san2-x68`   | 三國志II                       | X68000     |  352 |  219 |   ○    | [notes/san2.md](notes/san2.md)     |
| `san3-dos`   | 三國志III                      | DOS 中文版 |  531 |  307 |   ○    | [notes/san3.md](notes/san3.md)     |
| `san3-pc98`  | 三國志III                      | PC-98      |  531 |  307 |   ○    | [notes/san3.md](notes/san3.md)     |
| `san4pk-dos` | 三國志IV 威力加強版            | DOS 中文版 |  579 |  660 |   ○    | [notes/san4.md](notes/san4.md)     |
| `san4pk-pc98` | 三國志IV 威力加強版           | PC-98      |  579 |  660 |   ○    | [notes/san4.md](notes/san4.md)     |
| `san5pk-dos` | 三國志V 威力加強版             | DOS 中文版 |  500 | 1165 |        | [notes/san5.md](notes/san5.md)     |
| `san5pk-pc98` | 三國志V 威力加強版            | PC-98      |  500 | 1165 |        | [notes/san5.md](notes/san5.md)     |
| `eiketsu-dos` | 三國志英傑傳                 | DOS 中文版 |  264 |  240 |        | [notes/eiketsu.md](notes/eiketsu.md) |
| `koumei-win` | 三國志孔明傳                   | Win 中文版 |  240 |  288 |        | [notes/koumei.md](notes/koumei.md) |
| `san6pk-win` | 三國志VI 威力加強版            | Win 中文版 |  532 |  666 |        | [notes/san6.md](notes/san6.md)     |
| `suikoden-pc98` | 水滸伝・天命の誓い          | PC-98      |  255 |  260 |        | [notes/koei-games.md](notes/koei-games.md) |
| `suikoden-dos` | 水滸傳・天命之誓             | DOS 中文版 |  255 |  260 |        | [notes/koei-games.md](notes/koei-games.md) |
| `kouryuuki-dos` | 項劉記                      | DOS 中文版 |   92 |   97 |        | [notes/kouryuuki.md](notes/kouryuuki.md) |
| `europe-dos` | 歐陸戰線                       | DOS 中文版 |  106 |  120 |        | [notes/europe.md](notes/europe.md) |
| `liberty-dos` | 獨立戰爭                      | DOS 中文版 |  250 |  299 |        | [notes/liberty.md](notes/liberty.md) |
| `koukai-dos` | 大航海時代                     | DOS 中文版 |   62 |   34 |   ○    | [notes/koukai.md](notes/koukai.md) |
| `koukaigd-win` | 大航海時代外傳               | Win 中文版 |  169 |  157 |   ○    | [notes/koukaigd.md](notes/koukaigd.md) |
| `koukai3-win` | 大航海時代III                 | Win 中文版 |  246 |  558 |        | [notes/koukai3.md](notes/koukai3.md) |
| `genghis-dos` | 蒼狼與白鹿・成吉思汗          | DOS 中文版 |  152 |   83 |   ○    | [notes/genghis.md](notes/genghis.md) |
| `nobu3-dos`  | 信長之野望・戰國群雄傳         | DOS 中文版 |  385 |  177 |   ○    | [notes/nobu3.md](notes/nobu3.md)   |
| `nobu4-dos`  | 信長之野望・武將風雲錄         | DOS 中文版 |  507 |  311 |   ○    | [notes/nobu4.md](notes/nobu4.md)   |
| `air2-dos`   | 航空霸業II                     | DOS 中文版 |    0 |  114 |        | [notes/air2.md](notes/air2.md)     |
| `lempe-dos`  | 拿破崙                         | DOS 中文版 |  255 |  260 |        | [notes/lempe.md](notes/lempe.md)   |

原版遊戲檔放在 `games/<DATASET>/`（不進版控），`--game-dir` 指向該目錄即可。
