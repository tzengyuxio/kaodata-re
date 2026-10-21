from collections import namedtuple
from utils import H, to_unicode_name, kao2str

##############################################################################
# Common data
# - `~format` for struct unpack
# - `~PersonRaw`
# - `~Person`
# - `~table_title`
# - `~headers`


##############################################################################
# 項劉紀
#
# MAIN.EXE:264260(日文版), 276180(中文版, depklite)
#
# 8D808948000000 BAB3B30000000000 1A 27  # 項羽
# 97AB964D000000 D8ADB3CEB3000000 29 DB  # 劉邦
# EA7C957A000000 B9DEB2CC00000000 27 0E  # 黥布
# ^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^ ^^ ^^
# name(7bytes)   kana(8bytes)     ^^ +15: 年齡 = (+15 - SNDT year BC - 50) & 0xFF (206 BC: +15 itself)
#                                    ^^ +16: four 2-bit hidden values
#
# SNDT1.KR1
#
# 000000 6464 64 54 50 0004  # 項羽 (外交 有)
# 100005 4343 38 63 43 001B  # 劉邦
# 20000B 5A5A 5B 4A 49 003A  # 黥布
# 190006 5151 51 5D 60 002B  # 韓信 (外交 有)
# 090000 2727 16 57 5C 0010  # 范增
#                            # 項莊 (外交D)
# ^^     ^^^^ ^^ ^^ ^^ ^^ ^^
# |      |    |  |  |  |  +9 next person in the same city (FF = end)
# |      |    |  |  |  +8 經驗
# |      |    |  |  +7 用兵
# |      |    |  +6 統御
# |      |    +5 戰鬥
# |      +3 體力, +4 上限
# +0 bits 0-2 状態 (2 在野), bit 3 外交, bits 4-7 勢力; +2 所在
# 外交 shows 有 when 用兵 >= 80 or +0 bit 3 (see notes/kouryuuki.md「能力」)

kohryuki_format = '<7s8sBxBxBBBBBBBBB'  # 17+10 bytes + SNDT year BC

KOHRYUKIPersonRaw = namedtuple(
    'KOHRYUKIPersonRaw', 'name kana birth state city stamina stamina_max battle command tactics exp next year')


class KOHRYUKIPerson(KOHRYUKIPersonRaw):
    id: int

    # 下列字超出了 Shift_JIS 的範圍，KOEI 有自行造字
    # 但解碼時需先使用 shift_jis_2004 以避免錯誤，解碼後再轉換為對應字
    extends = {'浘': '卭', '洱': '噲', '浥': '靳', '洹': '芮', '洮': '酈', '櫧': '蒯'}

    def __getitem__(self, key):
        if key == 'name-zh':
            return to_unicode_name(self.name[:6])
        if key == 'name':
            kanji = self.name.decode('shift_jis_2004').strip('\x00')
            for k, v in self.extends.items():
                kanji = kanji.replace(k, v)
            return kanji
        if key == 'face':
            return str(self.id)
        if key == 'kana':
            return self.kana.decode('shift_jis').strip('\x00')
        if key == 'age':
            return str((self.birth - self.year - 50) & 0xFF)
        if key == 'diplomacy':
            return '有' if self.tactics >= 80 or self.state & 8 else '無'
        if hasattr(self, key):
            return str(getattr(self, key))
        else:
            raise KeyError(key)


kohryuki_table_title = '項劉記 人物表'
kohryuki_headers = [H('id', 'ID', 'id'), H('name', '姓名', 'name'), H('face', '顏', 'face'),
                    H('kana', '假名', 'base'),
                    H('age', '年齡', 'base'),
                    H('stamina', '體力', 'base'),
                    H('stamina_max', '上限', 'base'),
                    H('battle', '戰鬥', 'base'),
                    H('command', '統御', 'base'),
                    H('tactics', '用兵', 'base'),
                    H('exp', '經驗', 'base'),
                    H('diplomacy', '外交', 'base'),
                    ]


##############################################################################
# 拿破崙
#
# NPDATA.CIM:8934
#
# 4E61706F 6C656F6E 00000000 0000005F 06  # BCBA AACA 1111
# 4E61706F 6C656F6E 00000000 0000005F 06  # start[22204]
# 4E61706F 6C656F6E 00000000 0000005F 06  # start[35474]
# 4E61706F 6C656F6E 00000000 0000005F 06  # start[48744]
# 4E61706F 6C656F6E 00000000 0000005F 06  # start[62014]
#  N a p o  l e o n
#
# 4A6F7365 70680000 00000000 00000103 06  # CCCB CCDD 0000, 2nd, Joseph
# 4C756369 656E0000 00000000 00000203 06  # BBCC CDDD 0000, 3rd, Lucien
# 42657274 68696572 00000000 00000842 06  # CCAB ACDC 1000, 9th, Berthier
# 57697474 67656E73 7465696E 00007201 06  # CDBC BBCB 0000, Wittgenstein
# 47656F72 67652049 49490000 00003A82 06  # George III
# 47656F72 67652049 56000000 00003B82 00  # George IV
# 56696374 6F726961 00000000 00003C5E 00  # Victoria
# 4B757475 736F7600 00000000 00006346 06  # Kutusov (single eye?)
# 42617272 61730000 00000000 00000B20 06  # Barras
# 4C656665 62767265 00000000 00000C12 06  # Lefebvre -o--
# 41756765 72656175 00000000 00000D81 06  # Augereau x---
# ^^^^^^^^ ^^^^^^^^ ^^^^^^^^     ^^
# 名字                            序號
#
# NPDATA.CIM:8934
#
# 00 1AE6DF00 411C0505 00525705 0000 # BCBA AACA 1111, 1769
# 00 1B950500 491E0500 00303904 0000 # CCCB CCDD 0000, 1768
# 00 1B5A0100 42170000 00000004 0000 # BBCC CDDD 0000, 1775
# 00 1E610500 31140000 00000000 0000 # CDBC CCDD 0000, 1778
# 00 1E515500 2D0E0000 00000000 0000 # CDCC CCCC -000, 1784
# 0E 04AF6A00 64E96464 00646401 0000 # AABB BBBC 1111, 1819
# ^^ ^ ^^^^ ^^ ^^ ^^ ^^     ^^^^^^
# 國 城 能   經 忠 年 兵     訓士官
#           驗 誠 齡 力     練氣階
#
# The 15-byte record starts 2 bytes before the 國 byte (file 2 + 15 * i per scenario, see notes/lempe.md「能力」).
# Name +15 (masks): bits 0-1 and six flags in bits 2-7, their meaning is unknown.

lempe_format = '<14sBBxxxBBBBBBBBxxBBB'  # 17+15 bytes

LEMPEPersonRaw = namedtuple(
    'LEMPEPersonRaw', 'name face masks nation city ability1 ability2 exp loyalty age soldiers discipline morale rank')


class LEMPEPerson(LEMPEPersonRaw):
    id: int
    lookups = {0: 'D', 1: 'C', 2: 'B', 3: 'A'}
    nations = [('France', '法蘭西'), ('Holland', '荷蘭'), ('Bavaria', '巴伐利亞'), ('Denmark', '丹麥'), ('Turkey', '土耳其'), ('Italy', '意大利'), ('Venice', '威尼斯'),
               ('Naples', '那普斯'), ('Portugal', '葡萄牙'), ('Sweden', '瑞典'), ('Spain', '西班牙'), ('Prussia', '普魯士'), ('Russia', '俄羅斯'), ('Austria', '奧地利'), ('England', '英格蘭')]
    cities = [('Dublin', '都柏林'), ('Edinburgh', '愛丁堡'), ('Liverpool', '利物浦'), ('Bristol', '布里斯托爾'),
              ('London', '倫敦'), ('Christiana', '奧斯陸'), ('Stockholm', '斯德哥爾摩'), ('Copenhagen', '哥本哈根'),
              ('Amsterdam', '阿姆斯特丹'), ('Lubeck', '魯貝克'), ('Berlin', '柏林'), ('Warsaw', '華沙'),
              ('Konigsberg', '柯尼斯堡'), ('St.Petersburg', '聖彼得堡'), ('Minsk', '明斯克'), ('Smolensk', '斯摩棱斯克'),
              ('Moscow', '莫斯科'), ('Kiev', '基輔'), ('Klausenburg', '克勞森堡'), ('Bucharest', '布加勒斯特'),
              ('Budapest', '布達佩斯'), ('Vienna', '維也納'), ('Prague', '布拉格'), ('Munich', '慕尼黑'),
              ('Frankfurt', '法蘭克福'), ('Lille', '里爾'), ('St.Malo', '聖美祿'), ('Paris', '巴黎'),
              ('Bordeaux', '波爾多'), ('Lyon', '里昂'), ('Marseilles', '馬賽'), ('Milano', '米蘭'),
              ('Florence', '佛羅倫斯'), ('Venice', '威尼斯'), ('Sarajevo', '薩拉耶沃'), ('Belgrade', '貝爾格萊德'),
              ('Rome', '羅馬'), ('Naples', '那不勒斯'), ('Istanbul', '伊斯坦堡'), ('Athens', '雅典'),
              ('Corunna', '克魯納'), ('Lisbon', '里斯本'), ('Gibraltar', '直布羅陀'), ('Madrid', '馬德里'),
              ('Saragossa', '薩拉戈薩'), ('Barcelona', '巴塞羅那')]

    def __getitem__(self, key):
        if key == 'name':
            return to_unicode_name(self.name)
        if key == 'face':
            return kao2str(self.face, 255)
        if key == 'pol':  # 政治 Politics
            v = (self.ability1 & 0b00000011)
            return self.lookups[v]
        if key == 'fin':  # 財政 Finance
            v = (self.ability1 & 0b00001100) >> 2
            return self.lookups[v]
        if key == 'sup':  # 補給 Supplyy
            v = (self.ability1 & 0b00110000) >> 4
            return self.lookups[v]
        if key == 'bui':  # 建設 Build
            v = (self.ability1 & 0b11000000) >> 6
            return self.lookups[v]
        if key == 'ldr':  # 領導 Leader
            v = (self.ability2 & 0b00000011)
            return self.lookups[v]
        if key == 'inf':  # 步兵 Infantry
            v = (self.ability2 & 0b00001100) >> 2
            return self.lookups[v]
        if key == 'cav':  # 騎兵 Cavalry
            v = (self.ability2 & 0b00110000) >> 4
            return self.lookups[v]
        if key == 'art':  # 砲兵 Artillry
            v = (self.ability2 & 0b11000000) >> 6
            return self.lookups[v]
        if key == 'masks':
            return f'{self.masks:08b}'
        if key == 'rank':
            return str(self.rank & 0xF)
        if key == 'city':
            return self.cities[self.city][1]
        if key == 'nation':
            return self.nations[self.nation][1]
        if hasattr(self, key):
            return str(getattr(self, key))
        else:
            raise KeyError(key)


lempe_table_title = '拿破崙 人物表'  # "L'Empereur Person Data Table"
lempe_headers = [H('id', 'ID', 'id'), H('name', '姓名', 'name'), H('face', '顏', 'face'),
                 H('pol', '政治', 'base'),
                 H('fin', '財政', 'base'),
                 H('sup', '補給', 'base'),
                 H('bui', '建設', 'base'),
                 H('ldr', '領導', 'base'),
                 H('inf', '步兵', 'base'),
                 H('cav', '騎兵', 'base'),
                 H('art', '砲兵', 'base'),
                 H('exp', '經驗', 'state'),
                 H('loyalty', '忠誠', 'state'),
                 H('age', '年齡', 'state'),
                 H('soldiers', '兵力', 'state'),
                 H('morale', '士氣', 'state'),
                 H('discipline', '訓練', 'state'),
                 H('rank', '官階', 'state'),
                 H('masks', '隱藏', 'mask'),
                 H('city', '城市', 'state'),
                 H('nation', '國籍', 'state'),
                 ]

##############################################################################
# 水滸傳
#
# SUIDATA1.CIM: 7124, 45 bytes each (前後邊緣未定)
#
# 9CECB3FD000000 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 590080 # 高俅
# A8A6A0829E8600 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 0C02C0 # 魯智深
# 93B7A1CF000000 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 160180 # 史進
# A0859C5A000000 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 BD04C1 # 曾索
# 968192D092A300 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 1E02C0 # 阮小七
# A034B0DA000000 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 8401C3
# A7759876A7D400 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 710300 # 潘金蓮
# 95D6A345AE3100 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 810300
# 93F4964A9A5700 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 700301
# A77593C8A1F700 000000000000000000 20 0000000000000000 0000000000000000 000000000000000000 720301
# NAME(7bytes)   (9bytes)           ?  (8bytes)         (8bytes)         (9bytes)               ^^性別舵
#                                                                                             ^^unknown1
#                                                                                           ^^kao
#
#
# SUIDATA1.CIM: 3, 22 bytes each (前後邊緣未定)
#
# 1D0016 5A5A4C454F313548 000000 00 000000 64800000 # 高俅   太尉 年:30 兵:100
# 240105 64643F4A585F4431 000000 00 0F0000 00C30000 # 魯智深 好漢 年:37 兵:  0 船x舵o
# 120218 62624A455F5B4F2D 000000 00 100F00 50830000 # 史進
# 1C0304 565651643E2F364C 000000 00 190000
# 150114 5C5C292435262C24 000000 00 080000 086B0000 # 曾索   若旦那 船舵 少爺 年:23(table:22)
# 170109 5757322A26492F27 000000 00 020000 00E30000 # 阮小七 漁師   船舵 漁夫 年:24
# 18002E 595922411D444234 000000 4E 090000 42420000 # 彭汜
# 140116 474708121D101126 000000 00 020000 00AC0000 # 潘金蓮 少女 年:21(table:21)
# 110109 48480A18120C0F25 000000 00 030000 00AD0000 # 李瑞蘭
# 120129 46460A170E1A1720 000000 00 030000 002D0000 # 白秀英
# 150104 45450A160A0B0920 000000 00 040000 002C4C04 # 潘巧雲 少女 年:23(table:22)
#                                ^^忠誠       ^^兵
#                         ^^^^^^ 經驗       ^^小者
#        ^^^^^^^^^^^^^^^^ 體力忠義仁愛勇氣能耐技能智慧
# ^^^^^^ 年齡勢力城市(0base)


# The 22 bytes from file 4 are P+2..P+0x15 of person record P (file 2 + 22 * i) plus the next record's P+0, P+1:
# P+0x11 ?, P+0x12 u16 人望; P+0x15 bit 6 船, bits 0-5 身分. Name record +43 is the 口調 (message set) and
# +44 bit 7 男, bit 6 舵 (see the 水滸伝「能力」section of notes/koei-games.md).

suikoden_format = '<7s35xBBB'+'3B8B4BxHBB2x'  # 45+22 bytes

SUIKODENPersonRaw = namedtuple(
    'SUIKODENPersonRaw', 'name face tone basic_info age nation city body body_max integrity mercy courage str dex wis str_exp dex_exp wis_exp loyalty popularity men status')


class SUIKODENPerson(SUIKODENPersonRaw):
    id: int
    # the order of the PC-98 MAIN.EXE DS:0x35BC list (6-9 and 30-33 not checked in the Chinese version)
    identities = ('太尉 太守 官吏 好漢 頭目 強盜 義兄 義弟 死亡 罪犯 僧侶 漁夫 苦力 醫者 生意人 客棧掌櫃 技工 學究 富人 少爺 '
                  '少女 藝妓 獵人 大力士 壯士 客商 江湖藝人 道士 失業武人 無業遊民 虎 狼 熊 豹').split()

    def __getitem__(self, key):
        if key == 'name':
            return to_unicode_name(self.name[:6])
        if key == 'gender':
            g = (self.basic_info & 0b10000000) >> 7
            return '男' if g == 1 else '女'
        if key == 'identity':
            # status bits 0-5 -> index (PC-98 MAIN.EXE 0x5B1A): bit 4 -> (b & 0xF) + 22, bit 5 -> (b & 0x1F) + 8
            b = self.status & 0x3F
            i = (b & 0xF) + 22 if b & 0x10 else (b & 0x1F) + 8 if b & 0x20 else b
            return self.identities[i] if i < len(self.identities) else f'不明({b:#x})'
        if key == 'ship':
            return '○' if self.status & 0b01000000 else ''
        if key == 'rudder':
            r = (self.basic_info & 0b01000000) >> 6
            return '○' if r == 1 else ''
        if hasattr(self, key):
            return str(getattr(self, key))
        else:
            raise KeyError(key)


suikoden_table_title = '水滸傳 人物表'
suikoden_headers = [H('id', 'ID', 'id'), H('name', '姓名', 'name'), H('face', '顏', 'face'),
                    H('age', '年齡', 'base'),
                    # H('nation', '勢力', 'base'),
                    # H('city', '城市', 'base'),
                    H('gender', '性別', 'base'),
                    H('identity', '身份', 'base'),
                    H('body', '體力', 'base'),
                    H('body_max', '體力上限', 'base'),
                    H('str', '能耐', 'base'),
                    H('dex', '技能', 'base'),
                    H('wis', '智慧', 'base'),
                    H('integrity', '忠義', 'base'),
                    H('mercy', '仁愛', 'base'),
                    H('courage', '勇氣', 'base'),
                    H('str_exp', '能耐經驗', 'base'),
                    H('dex_exp', '技能經驗', 'base'),
                    H('wis_exp', '智慧經驗', 'base'),
                    H('men', '士兵', 'base'),
                    H('loyalty', '忠誠度', 'base'),
                    H('popularity', '人望', 'base'),
                    H('ship', '船', 'base'),
                    H('rudder', '舵', 'base'),
                    H('tone', '口調', 'base'),
                    ]
