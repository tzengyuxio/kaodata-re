# 三國志 人物資料 研究筆記

## SAN4

下面檔案包含伊籍 (0x9444ADA5)

- SNDATA.S4
  - 名字 offset: 30892, 50637, 70672, 90527, 144632, 163447, 195512
  - 能力 offset: 26455, 46200, 65965, 86360, 140675, 159240, 184465
- TAIKI.S4
- 張飛, 關羽 SNDATA.S4, offsets
  - 10770, 9210
  - 28935, 27035
- 從統帥起找能力的 offset -> **間隔 20 bytes**
  - 關羽(0x64625241) 9209 (kao: 1)
  - 華雄 9189
  - 夏侯惇(0x5E603E) 9169 (kao: 6)
- 從名字找起的 offset -> **間隔 30 bytes**, 第 21 bytes 為顏編號
  - 華雄 13067
  - 關羽 13097
- 顏ID (名字, byte20, 21, 22)
  - 關羽 ________ 00 01 00
  - 華雄 ________ 00 07 00
  - 呂凱 95649FB2 00 E7 00
  - 劉巴 A6AB9351 00 03 F8
  - 呂義 9564A399 00 47 F0

decode error: b'C0\x00\x00\x03\x01\x00\xff\xff\xff'
scenario 1 end in  222
decode error: b'C0\x00\x00\x03\x01\x00\xff\xff\xff'
scenario 2 end in  222
decode error: b'C0\x00\x00\x03\x01\x00\xff\xff\xff'
scenario 3 end in  234
decode error: b'C0\x00\x00\x03\x01\x00\xff\xff\xff'
scenario 4 end in  207
decode error: b'C0\x00\x00\x03\x01\x00\xff\xff\xff'
scenario 5 end in  198
decode error: b'C0\x00\x00\x03\x01\x00\xff\xff\xff'
scenario 6 end in  209
scenario 7 end in  95 (out of data)

新武將男可選擇的 70 個頭像中，前 30 個是專用，後 40 個是大眾臉

## SAN5

- SNDATA.S5
  - 伊籍 名字 offset: 49607, 72510, 95342, 118159, 192851, 215491
  - 伊籍 能力 offset: 42024, 65547, 87721, 111313, 185640, 208366
  - 張飛 13144
  - 關羽 10826
  - 華雄 10788 (差 38 bytes)
- offsets: 10180, 28250, 49607, 72510, 95304, 118121,  192851, 215453

名字後 30, 31 兩 bytes 為顏編號

decode error: b'F\x00\xff\x00\x00\x00\x00\x00\x00\x00'
scenario 1 end in  148
decode error: b'^\x00\xff\x00\x00\x00\x00\x00\x00\x00'
scenario 2 end in  188
decode error: b'q\x00\xff\x00\x00\x00\x00\x00\x00\x00'
scenario 3 end in  245
decode error: b'i\x00\xff\x00\x00\x00\x00\x00\x00\x00'
scenario 4 end in  225
decode error: b'k\x00\xff\x00\x00\x00\x00\x00\x00\x00'
scenario 5 end in  246
decode error: b'a\x00\xff\x00\x00\x00\x00\x00\x00\x00'
scenario 6 end in  221
decode error: b'G\x00\xff\x00\x00\x00\x00\x00\x00\x00'
scenario 7 end in  233
decode error: b'd\x00\xff\x00\x00\x00\x00\x00\x00\x00'
scenario 8 end in  230

## 參考來源

- 這邊有 1~11 代的能力一覽表：[楊奉とは (ヨウホウとは) \[単語記事\] - ニコニコ大百科](https://dic.nicovideo.jp/a/%E6%A5%8A%E5%A5%89)
- 三國志11 攻略 WIKI: [楊奉 - 三國志11攻略wiki - atwiki（アットウィキ）](https://w.atwiki.jp/sangokushi11/pages/795.html)
- 三國志13 攻略 WIKI: [楊奉 - 三国志13 攻略 WIKI](http://sangokushi13wiki.wiki.fc2.com/wiki/%E6%A5%8A%E5%A5%89)
- [火間虫入道-信長の野望 蒐集者の庭-](http://hima.que.ne.jp/)
  - 信長之野望系列
  - 太閤立志傳系列
  - 三國志 1~7, 12
  - 拿破崙
- 有天翔記~創造武將一覽 EXCEL [天翔記.jp](https://xn--rssu31gj1g.jp/)
- 有三國志10的改造資訊 [三国志Ⅹ改造スレ３](https://game13.5ch.net/test/read.cgi/gamehis/1098017701/)
- [NIKUO'S ROOM](https://www.lhexw.net/)
  - [三国志武将能力値比較](https://www.lhexw.net/san-bushou/index.html)
  - [SUPER三国志II モブ顔グラ分類](https://www.lhexw.net/san-2kao/index.html)
  - [三国志武将データ](https://www.lhexw.net/san/index.html)

## 其他註記

- 光榮美術館目前 39 作 (2023/3/1), koei-wiki 已整理 27 作，但尚未完整發布
- 光榮美術館目前 40 作 (2023/5/15), koei-wiki 已整理 30 作，發布 23 作。
- [光榮美術館](http://www.mitene.or.jp/~wintree/rent/keeekn/koeiface/koeiface_top.htm)

## 人物解析步驟

```py
    # 定義 'stack unpack fmt' for PersonRaw
    # 定義 PersonRaw 資料結構
    # 定義 Person 資料結構
    # func of PersonRaw -> Person
    #
    # 定義 headers
    # new table and add columns with header
    #
    # 宣告 persons
    # with open file:
    #     read data (maybe need to join with parts)
    #     pr = PersonRaw._make(unpack(fmt, data))
    #     p = convert(pr)
    #     persons.append(p)
    #
    # for p in persons:
    #     add row to table, or
    #     output as csv
    # print summary of persons
```
