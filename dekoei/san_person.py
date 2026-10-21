from collections import namedtuple
from utils import H, to_unicode_name, kao2str, grouper

##############################################################################
# Common data
# - `~format` for struct unpack
# - `~PersonRaw`
# - `~Person`
# - `~table_title`
# - `~headers`

##############################################################################
# 三國志
#
# SINADATA.DAT:4326
#
# 43616F20 43616F00 00000000 23585D5E 64616403 03001027 07010A0A 0A000000
# 53756E20 4A69616E 00000000 22255560 621A6403 08008813 29020A0A 0A000000
# 4C697520 42656900 00000000 1D555F3F 63476403 0200F401 0E030A0A 0A000000
# N                          A B I P  C L L ?  F   S    C N S S  S ? ? ?
# a                          g o n o  h u o U  a   o    i a . .  .
# m                          e d t w  a c y 1  c   l    t t L A  A
# e                            y e e  r k a    e   d    y i o b  r
#                                l r  i   l        i      o y i  m
#                                l    s   t        e      n a l  s
#                                .    m   y        r        l i
#                                     a            s        t t
#                                                           y y
#

s1_format = '<12sbBBBBBBBHHBBBBBxxx'  # 32 bytes

S1PersonRaw = namedtuple(
    'S1PersonRaw', 'name age body intell power charisma luck loyalty unknown1 face soldiers city nation s_loyalty s_ability s_arms')


class S1Person(S1PersonRaw):
    id: int

    def __getitem__(self, key):
        if key == 'name':
            return to_unicode_name(self.name)
        if key == 'face':
            return kao2str(self.face, 255)
        if key == 'master':
            return '◎' if self.unknown1 & 0b10 else ''
        if key == 'naval':
            return '○' if self.unknown1 & 0b01 else ''
        if hasattr(self, key):
            return str(getattr(self, key))
        else:
            raise KeyError(key)


s1_table_title = '三國志 人物表'
s1_headers = [H('id', 'ID', 'id'), H('name', '姓名', 'name'), H('face', '顏', 'face'),
              H('age', '年齡', 'base'),
              H('body', '身體', 'base'),
              H('intell', '知力', 'base'),
              H('power', '武力', 'base'),
              H('charisma', '信服力', 'base'),
              H('luck', '運勢', 'base'),
              H('loyalty', '忠誠度', 'state'),
              H('city', '城市', 'state'),
              H('nation', '勢力', 'state'),
              H('master', '君主', 'state'),
              H('naval', '水軍', ''),
              H('soldiers', '兵士數', 'state'),
              H('s_loyalty', '兵忠誠', 'state'),
              H('s_ability', '兵武力', 'state'),
              H('s_arms', '兵武裝', 'state'),
              #   H('unknown1', '未知1', ''),
              ]

##############################################################################
# 三國志II
#
# TAIKI.DAT:0x06
# SCENARIO.DAT:0x16 (以下範例為 SCENARIO.DAT)
#
# E305 0000 5F5B5F 3C4163 000001FF00010100 1027 E8030A00009B6700 9E39A8E600000000000000000000 00
# 1007 0000 554663 646455 016401FF00320200 1027 E8030A0000A1A100 A6AB9FAB00000000000000000000 00
# 6A09 0000 575A59 3C4B5A 026401FF00640400 1027 E8030A00009C6A00 9B309D6E00000000000000000000 00
#
# 0x00  BYTE    debut_year  登場年份 (0xBE = 190)
# 0x01  BYTE    debut_with  登場依附武將 (0xFF = 無登場條件, 其他值 = 對應武將顏CG編號)
# 0x02  BYTE    debut_city  登場城市
# 0x03  WORD    next        次席
# 0x05  WORD    status      狀態 (死亡, 移動, 內應, 生病 per 4 bits)
# 0x07  BYTE    intl        才智
# 0x08  BYTE    war         戰力
# 0x09  BYTE    chrm        號召
# 0x0A  BYTE    giri        義理
# 0x0B  BYTE    jintoku     人徳
# 0x0C  BYTE    ambition    野望
# 0x0D  BYTE    master      主公
# 0x0E  BYTE    loyalty     忠誠
# 0x0F  BYTE    service     侍衛 (仕官年數)
# 0x10  BYTE    in_nation   埋伏勢力
# 0x11  BYTE    in_city     埋伏城市
# 0x12  BYTE    aishou      相性
# 0x13  WORD    family      親族 (1=曹操, 2=劉備, 4=孫堅, 8=袁紹, 16=袁術, 32=馬騰, 64=劉焉, 128=劉表, 256=董卓, 512=公孫瓚, 1024=張魯, 2048=孟獲)
# 0x15  WORD    soldier     兵士數
# 0x17  WORD    weapon      武器?
# 0x19  BYTE    discipline  訓練
# 0x1A  WORD    unknown1    未知
# 0x1C  BYTE    birth_year  出生年份
# 0x1D  WORD    face        顏
# 0x1F  BYTEx14 name        姓名
# 0x2D  BYTE    unknown2    字串結束 (0x00)


s2_format = '<HHBBBBBBBBBBBBHHHBxxBH14sx'  # 43 bytes
s2_format_taiki = '<BBBHHBBBBBBBBBBBBHHHBxxBH14sx'  # 46 bytes

S2PersonRaw = namedtuple(
    'S2PersonRaw', 'next status intl war chrm giri jintoku ambition master loyalty service in_nation in_city aishou family soldier weapon discipline birth_year face name')
S2PersonRawTaiki = namedtuple('S2PersonRawTaiki', ('debut_year', 'debut_with', 'debut_city',)+S2PersonRaw._fields)


class S2Person(S2PersonRawTaiki):
    id: int

    def __getitem__(self, key):
        if key == 'name':
            return to_unicode_name(self.name)
        if key == 'name_code':
            name_code = self.name.hex().upper().replace('00', '')
            return ' '.join([name_code[i:i+4] for i in range(0, len(name_code), 4)])
        if key == 'face':
            return kao2str(self.face, 220, True)
        if hasattr(self, key):
            return str(getattr(self, key))
        else:
            raise KeyError(key)


s2_table_title = '三國志II 人物表'
s2_headers = [H('id', 'ID', 'id'), H('name', '姓名', 'name'), H('face', '顏', 'face'),
            #   H('name_code', '姓名編碼', 'name'),
              H('intl', '才智', 'base'),
              H('war', '戰力', 'base'),
              H('chrm', '號召', 'base'),
              H('giri', '義理', 'mask'),
              H('jintoku', '人德', 'mask'),
              H('ambition', '野望', 'mask'),
              H('aishou', '相性', 'mask'),
              H('family', '親族', 'mask'),
              H('debut_year', '登場年', 'state'),
              H('debut_with', '登場依附', 'state'),
              H('debut_city', '登場城市', 'state'),
              ]

##############################################################################
# 三國志III
#
# 0x0000 顏 次席 士兵 寶物 MASK STATUS ABILITY 相性 義理 忠誠 城市 勢力 仕官 裡所屬仕官 親族 訓練 士氣 無 生年 工作 餘月 無 姓名
# xx     H  H   H   H   H    BBBBB  BBBBBB   B   B   B   B   B   B    BB       B   B   B   xxx B   B   B   xxx 6s
#
# STATUS: 行動 疾病 壽命 埋伏 身份 (action disease lifespan undercover position)

s3_format = '<xxHHHHHBBBBBBBBBBBBBBBBBBBBBBxxxBBBxxx6s'  # 49 bytes

S3PersonRaw = namedtuple('S3PersonRaw', 'face next sldr items mask action disease lifespan undercover position army navy war intl pol chrm aishou giri loyalty city nation service in_nation in_service family discipline morale birth_year work left_month name')


class S3Person(S3PersonRaw):
    id: int

    def __getitem__(self, key):
        if key == 'name':
            return to_unicode_name(self.name)
        if key == 'face':
            return kao2str(self.face, 307, True)
        # mask is four 0-15 nibbles (most often 0x7777); which nibble is which is inferred from known
        # characters (張飛 0x4FBC: calm 4, brave 15; 司馬懿 0xC6FA: ambition 15), see notes/san-attributes.md
        if key == 'ambition':
            return str((self.mask >> 4) & 0xF)
        if key == 'luck':
            return str(self.mask & 0xF)
        if key == 'calmness':
            return str((self.mask >> 12) & 0xF)
        if key == 'bravery':
            return str((self.mask >> 8) & 0xF)
        if key == 'attrkey':
            war = self.war if self.war < 100 else 'A0'
            intl = self.intl if self.intl < 100 else 'A0'
            pol = self.pol if self.pol < 100 else 'A0'
            chrm = self.chrm if self.chrm < 100 else 'A0'
            return f'S03_{war:>02}{intl:>02}{pol:>02}{chrm:>02}'
        if hasattr(self, key):
            return str(getattr(self, key))
        else:
            raise KeyError(key)


s3_table_title = '三國志III 人物表'
s3_headers = [H('id', 'ID', 'id'), H('name', '姓名', 'name'), H('face', '顏', 'face'),
              H('ambition', '野心', 'mask'),
              H('luck', '運氣', 'mask'),
              H('calmness', '冷靜', 'mask'),
              H('bravery', '勇猛', 'mask'),
              H('army', '陸指', 'base'),
              H('navy', '水指', 'base'),
              H('war', '武力', 'base'),
              H('intl', '智力', 'base'),
              H('pol', '政治', 'base'),
              H('chrm', '魅力', 'base'),
              H('aishou', '相性', 'mask'),
              H('giri', '義理', 'mask'),
              ]
