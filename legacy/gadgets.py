#!/usr/bin/env python3

import csv
import os
import struct
import requests
from bs4 import BeautifulSoup
from pytablewriter import MarkdownTableWriter, UnicodeTableWriter
from pytablewriter.style import Style
from dekoei.utils import to_unicode_name, to_koeitw
from dekoei.san_person import *


kohryuki_names = ['項羽', '劉邦', '英布', '韓信', '范增', '章邯', '項莊', '司馬欣', '董翳', '章平',
                  '趙歇', '陳餘', '張耳', '蕭公角', '田假', '鄭昌', '周殷', '鍾離昧', '夏說', '李左車',
                  '項聲', '曹咎', '張逸', '武涉', '張良', '陳嬰', '項伯', '夏侯嬰', '蕭何', '周勃',
                  '盧綰', '曹參', '審食其', '隨何', '周蘭', '陳平', '魏無知', '灌嬰', '紀信', '雍齒',
                  '周苛', '樅公', '袁生', '鄭忠', '劉賈', '柴武', '楊喜', '呂馬童', '王翳', '楊武',
                  '呂勝', '季布', '周昌', '叔孫通', '婁敬', '彭越', '孔聚', '陳賀', '楊', '申陽',
                  '共敖', '張敖', '田榮', '龍且', '王陵', '貫高', '田橫', '田廣', '王吸', '薛歐',
                  '任敖', '田既', '田光', '田吸', '侯公', '魏豹', '薛公', '丁公', '欒布', '臧荼',
                  '司馬卬', '樊噲', '靳彊', '吳芮', '酈商', '蒯徹', '酈食其', '呂澤', '陸賈', '樓煩',
                  '韓王信', '利幾']


def kohryuki_combine_persons():
    CSV_ZH = 'PERSONS_TABLE/kohryuki-persons-s1-zh.csv'
    CSV_JA = 'PERSONS_TABLE/kohryuki-persons-s1-ja.csv'
    with open(CSV_ZH, 'r', encoding='utf-8') as fzh, open(CSV_JA, 'r', encoding='utf-8') as fja:
        csv_zh = csv.reader(fzh)
        csv_ja = csv.reader(fja)

        header = next(csv_zh)
        header = header[0:2] + ['中文版', '日文版'] + header[2:]
        # header = header[0:2] + header[2:]
        next(csv_ja)

        persons = []
        for row_zh, row_ja in zip(csv_zh, csv_ja):
            id = row_zh[0]
            name = kohryuki_names[int(id)]
            name_value = f'[{name}](/人物/秦漢之際/{name})'
            person = [id, name_value] + [row_zh[1], row_ja[1]] + row_ja[2:]
            # person = [id, name] + row_ja[2:]
            persons.append(person)

    # header = [h.replace('力', '') if len(h) > 2 else h for h in header]
    # writer = UnicodeTableWriter(
    writer = MarkdownTableWriter(
        table_name='項劉記 人物資料',
        headers=header,
        value_matrix=persons,
        column_styles=[
            Style(),
            Style(),
            Style(),
            Style(),
            Style(),
            Style(),
            Style(),
            Style(),
            Style(),
            Style(),
            Style(),
        ]
    )
    writer.write_table()

# 18 位帝國元帥之一，但未出現在遊戲中
# https://zh.wikipedia.org/wiki/纪尧姆·布律纳


lempe_persons_wiki = [
    'https://zh.wikipedia.org/wiki/拿破仑一世',  # [0]
    'https://zh.wikipedia.org/wiki/约瑟夫·波拿巴',  # 拿破崙兄
    'https://zh.wikipedia.org/wiki/吕西安·波拿巴',  # 拿破崙弟
    'https://zh.wikipedia.org/wiki/拿破仑三世',  # 約瑟芬外孫
    'https://zh.wikipedia.org/wiki/热罗姆·波拿巴',  # 拿破崙幼弟
    'https://zh.wikipedia.org/wiki/拿破崙四世',  # 拿破崙三世獨生子
    'https://zh.wikipedia.org/wiki/讓-馬蒂厄-菲利貝爾·塞律里埃',  # 帝國元帥(榮譽)
    'https://zh.wikipedia.org/wiki/拉扎尔·卡诺',
    'https://zh.wikipedia.org/wiki/路易-亚历山大·贝尔蒂埃',  # 帝國元帥
    'https://zh.wikipedia.org/wiki/夏尔·莫里斯·德塔列朗-佩里戈尔',
    'https://zh.wikipedia.org/wiki/邦·阿德里安·让诺·德·蒙塞',  # [10] 帝國元帥
    'https://zh.wikipedia.org/wiki/保羅·巴拉斯',
    'https://zh.wikipedia.org/wiki/弗朗索瓦·约瑟夫·勒菲弗',  # 帝國元帥(榮譽)
    'https://zh.wikipedia.org/wiki/皮埃尔·奥热罗',  # 帝國元帥
    'https://zh.wikipedia.org/wiki/让-巴蒂斯特·儒尔当',  # 帝國元帥; 用中文名找, 英文 "La Mette" 找不到對應人物
    'https://zh.wikipedia.org/wiki/安德烈·马塞纳',  # 帝國元帥
    'https://zh.wikipedia.org/wiki/约瑟夫·富歇',  # [16]
    'https://zh.wikipedia.org/wiki/卡尔十四世·约翰',  # Bernadotte, 帝國元帥
    'https://zh.wikipedia.org/wiki/克洛德·维克托-佩兰',
    'https://zh.wikipedia.org/wiki/洛朗·古维翁-圣西尔',
    'https://en.wikipedia.org/wiki/Pierre_Dupont_de_l%27Étang',
    'https://en.wikipedia.org/wiki/Jean-Baptiste_Drouet,_Comte_d%27Erlon',
    'https://zh.wikipedia.org/wiki/艾蒂安·麦克唐纳',
    'https://zh.wikipedia.org/wiki/埃马纽埃尔·德·格鲁希',
    'https://zh.wikipedia.org/wiki/让-巴蒂斯特·贝西埃',  # 帝國元帥, 出生年 1768, 火間虫入道 記為 1766
    'https://en.wikipedia.org/wiki/Édouard_Jean_Baptiste_Milhaud',
    'https://zh.wikipedia.org/wiki/若阿尚·缪拉',  # 帝國元帥
    'https://zh.wikipedia.org/wiki/路易·德賽',
    'https://zh.wikipedia.org/wiki/爱德华·莫蒂埃',  # 帝國元帥
    '',  # 墨勃格, Mobrogue, モーブルグ (1768) 查無此人
    'https://zh.wikipedia.org/wiki/让·德迪厄·苏尔特',  # 帝國元帥
    'https://zh.wikipedia.org/wiki/米歇尔·内伊',  # 帝國元帥
    'https://en.wikipedia.org/wiki/Louis_Friant',  # [32]
    'https://zh.wikipedia.org/wiki/让·拉纳',  # 帝國元帥
    'https://en.wikipedia.org/wiki/Dominique_Vandamme',
    'https://en.wikipedia.org/wiki/Pierre_Cambronne',
    'https://en.wikipedia.org/wiki/François_Étienne_de_Kellermann',
    'https://zh.wikipedia.org/wiki/路易·加布里埃尔·絮歇',
    'https://zh.wikipedia.org/wiki/路易·尼古拉·达武',  # 帝國元帥
    'https://en.wikipedia.org/wiki/Louis_Antoine_Fauvelet_de_Bourrienne',  # 法國外交官
    'https://en.wikipedia.org/wiki/Louis-Pierre_Montbrun',  # 博羅金諾戰役
    'https://zh.wikipedia.org/wiki/让·维克托·马里·莫罗',
    'https://zh.wikipedia.org/wiki/讓-安多什·朱諾',
    'https://zh.wikipedia.org/wiki/讓·拉普',
    'https://en.wikipedia.org/wiki/Jean_Reynier',
    'https://zh.wikipedia.org/wiki/奥拉斯·塞巴斯蒂亚尼',
    '',  # 布代, Bruyes, プティ (1772)
    'https://zh.wikipedia.org/wiki/奧古斯特·德·馬爾蒙',
    'https://zh.wikipedia.org/wiki/艾蒂安·莫里斯·热拉尔',  # [48]
    'https://zh.wikipedia.org/wiki/安托萬·夏爾·路易·拉薩爾',
    '',  # 雷耶, Ledru, レイユ (1775)
    'https://zh.wikipedia.org/wiki/阿尔芒·德·科兰古',
    'https://en.wikipedia.org/wiki/Gaspard_Gourgaud',
    'https://en.wikipedia.org/wiki/Charles_Tristan,_marquis_de_Montholon',  # 穆頓, Montholon, モントロン (1783)
    'https://en.wikipedia.org/wiki/Charles_de_la_Bédoyère',  # [54]
    'https://zh.wikipedia.org/wiki/喬治三世',
    'https://zh.wikipedia.org/wiki/喬治四世',
    'https://zh.wikipedia.org/wiki/维多利亚女王',
    'https://zh.wikipedia.org/wiki/第一代西德默斯子爵亨利·阿丁頓',  # 英國首相 (1801-1804)
    'https://zh.wikipedia.org/wiki/理查德·布林斯利·谢立丹',  # 海軍財務官
    'https://en.wikipedia.org/wiki/Thomas_Picton',
    'https://zh.wikipedia.org/wiki/小威廉·皮特',
    '',  # 巴紹特, Basaust, バスアースト (1762)
    '',  # 比藍特, Bylandt, ビラント (1763)
    # [64] 戈登, Gordon, ゴードン (1764), Gordon 太多不知道是誰, https://en.wikipedia.org/wiki/George_Gordon,_5th_Duke_of_Gordon
    '',
    '',  # 奧蘭治, Orange, オレンジ (1766)
    'https://en.wikipedia.org/wiki/John_Moore_(Irish_politician)',
    'https://zh.wikipedia.org/wiki/第一代安格尔西侯爵亨利·佩吉特',  # Uxbridge
    '',  # 藍伯特, Lambert, ランバート (1768)
    'https://en.wikipedia.org/wiki/William_Beresford,_1st_Viscount_Beresford',
    'https://zh.wikipedia.org/wiki/第一代威靈頓公爵阿瑟·韋爾斯利',
    'https://en.wikipedia.org/wiki/Frederick_Maitland',
    '',  # 康瓦利斯, Cornwallis, コーンウォリス (1769), https://en.wikipedia.org/wiki/Charles_Cornwallis,_2nd_Marquess_Cornwallis
    '',  # 華亭, Alten, アルテン (1770)
    'https://en.wikipedia.org/wiki/Antoine_Le_Picard_de_Phélippeaux',  # フィリッポー (1770); 條目這個 (1767), 在埃及打敗拿破崙
    'https://en.wikipedia.org/wiki/Ormsby_Vandeleur',
    'https://en.wikipedia.org/wiki/Hussey_Vivian,_1st_Baron_Vivian',
    'https://en.wikipedia.org/wiki/FitzRoy_Somerset,_1st_Baron_Raglan',  # https://en.wikipedia.org/wiki/Lord_Robert_Somerset
    'https://en.wikipedia.org/wiki/Rowland_Hill,_1st_Viscount_Hill',
    '',  # 波謝, Pershey, パーシー (1772)
    'https://en.wikipedia.org/wiki/Frederick_Cavendish_Ponsonby',  # [80]
    '',  # 麥克唐納, McDonnel, マクドネル (1773)
    '',  # 科伯恩, Colburn, コルボーン (1774)
    'https://zh.wikipedia.org/wiki/卡蘇里子爵羅伯特·史都華',
    '',  # 昂吉迪, Wade, アーチディーケ (1777)
    'https://en.wikipedia.org/wiki/Cavalié_Mercer',
    'https://en.wikipedia.org/wiki/William_Howe_De_Lancey',
    '',  # 拉姆齊, Ramsay, ラムゼイ (1781)
    'https://en.wikipedia.org/wiki/John_Pitt,_2nd_Earl_of_Chatham',  # 與 小威廉彼特 (William Pitt the Younger) 是兄弟
    '',  # 諾莫爾	Nomire, ノーマイル (1782)
    'https://en.wikipedia.org/wiki/Georg_Baring',
    'https://en.wikipedia.org/wiki/John_Dawson,_2nd_Earl_of_Portarlington',  # [91]
]


def get_title(url):
    print(f'fetching title from {url}...', end=None)
    # 發送 GET 請求
    response = requests.get(url)
    # 使用 BeautifulSoup 解析回應的 HTML 內容
    soup = BeautifulSoup(response.content, 'html.parser')
    # 找到 HTML 中的 <title> 標籤的內容，並返回
    title = soup.title
    if title is not None:
        title = title.text.split(' - ')[0]
    # title = soup.find('span', {'class': 'mw-page-title-main'}).text
    print(title)
    return title


def fetch_name(id: int, default: str = ''):
    if id < len(lempe_persons_wiki) and lempe_persons_wiki[id] != '':
        url = lempe_persons_wiki[id]
        # name = url.split('/')[-1]
        if '/zh.' in url:
            url = url.replace('/wiki/', '/zh-tw/')
        return get_title(url)
    else:
        return f'({default})'


def lempe_combine_persons():
    CSV_TW = 'PERSONS_TABLE/lempe-persons-s1-zh.csv'
    CSV_EN = 'PERSONS_TABLE/lempe-persons-s1-en.csv'
    with open(CSV_TW, 'r', encoding='utf-8') as ftw, open(CSV_EN, 'r', encoding='utf-8') as fen:
        csv_tw = csv.reader(ftw)
        csv_en = csv.reader(fen)

        header = next(csv_tw)
        header = header[0:2] + ['中文版', '英文版', '國家'] + header[2:-2]
        next(csv_en)

        persons = []
        for row_tw, row_en in zip(csv_tw, csv_en):
            id = row_tw[0]
            name = fetch_name(int(id), row_tw[1])
            person = [id, name] + [row_tw[1], row_en[1], row_tw[-1]] + row_tw[2:-2]
            persons.append(person)
        # for person in persons:
            # person[1] = '[{}](/人物/拿破崙時代/{})'.format(person[1], person[1])

    writer = MarkdownTableWriter(
        table_name='拿破崙 人物資料',
        headers=header,
        value_matrix=persons,
        column_styles=[
            Style(),
            Style(),
            Style(),
            Style(),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
            Style(align='center'),
        ]
    )
    writer.write_table()


def lempe_list_cities_and_nations():
    HOME_DIR = os.path.expanduser('~')
    NPDATA_EN = HOME_DIR + '/DOSBox/empereur/NPDATA.CIM'
    NPDATA_TW = HOME_DIR + '/DOSBox/lempereur/NPDATA.CIM'
    with open(NPDATA_EN, 'rb') as fen, open(NPDATA_TW, 'rb') as ftw:
        cities = []
        nations = []

        # extract nations
        fen.seek(7220)
        ftw.seek(7220)
        for _ in range(15):
            nation_en = to_unicode_name(fen.read(10)[:9])
            nation_tw = to_unicode_name(ftw.read(10)[:8])
            nations.append((nation_en, nation_tw))

        # extract cities
        for _ in range(46):
            city_en = to_unicode_name(fen.read(34)[:15])
            city_tw = to_unicode_name(ftw.read(34)[:14])
            cities.append((city_en, city_tw))

    # print(nations)
    # print(cities)
    # print('nations:', len(nations))
    # print('cities:', len(cities))

    writer = MarkdownTableWriter(
        table_name='拿破崙 國家',
        headers=['ID', '中文', '英文'],
        value_matrix=[(i, nation[1], nation[0]) for i, nation in enumerate(nations)],
    )
    writer.write_table()

    writer = MarkdownTableWriter(
        table_name='拿破崙 城市',
        headers=['ID', '中文', '英文'],
        value_matrix=[(i, city[1], city[0]) for i, city in enumerate(cities)],
    )
    writer.write_table()


def encode_text(text: str):
    return to_koeitw(text)


def extract_sui_strings():
    HOME_DIR = os.path.expanduser('~')
    with open(HOME_DIR+'/DOSBox/SUI/output.000.exe', 'rb') as f:
        # f.seek(177612)
        f.seek(192605)
        for i in range(2):
            byte = f.read(1)
            result = b''
            while byte != b'' and byte != b'\x00':
                result += byte
                byte = f.read(1)
            print(i, to_unicode_name(result))


def get_name_list(filename: str, count: int):
    with open(filename, 'r', encoding='utf-8') as f:
        names = ['' for _ in range(count)]
        csv_reader = csv.reader(f)
        header = next(csv_reader)
        for row in csv_reader:
            name, kao = row[1], row[2]
            # test kao is a number or not
            if kao.isdigit() and len(kao) < 4:
                try:
                    names[int(kao)] = name
                except:
                    print(kao, name)
        # print(names)
        for x in names:
            print(x)


def get_san3_name_list(filename: str, count: int):
    def key(a1, a2, a3, a4) -> str:
        a1, a2, a3, a4 = ['A0' if x == '100' else x for x in [a1, a2, a3, a4]]
        return f'S03_{a1:>02}{a2:>02}{a3:>02}{a4:>02}'

    namekey = {}
    with open('MISC_TABLE/namekey.csv',  'r') as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            namekey[row[0]] = row[1]

    with open(filename, 'r', encoding='utf-8') as f:
        names = ['' for _ in range(count)]
        csv_reader = csv.reader(f)
        next(csv_reader)  # header
        for row in csv_reader:
            name, kao = row[1], row[2]
            namekey_index = key(row[9], row[10], row[11], row[12])
            correct_name = namekey[namekey_index]
            # test kao is a number or not
            if kao.isdigit() and len(kao) < 4:
                try:
                    names[int(kao)] = correct_name.split(' ')[0]  # 去掉後面括號內容
                    # names[int(kao)] = correct_name
                except:
                    print(kao, name)
        print('--------------------')
        for name in names:
            print(f"'{name}',")


def get_san3_scenario_name_list(game_dir: str):
    """
    列出三國志三每個劇本的武將名稱作為勘誤
    """
    namekey = {}
    with open('namekey.csv',  'r') as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            namekey[row[0]] = row[1]

    persons = {}  # {key: [name, s1, s2, s3, s4, s5, s6]}
    cities = {}  # {key: [name, s1, s2, s3, s4, s5, s6]}
    for i in range(6):
        filename = '{}/SNDATA{}B.CIM'.format(game_dir, i+1)
        read_count, read_size = 600, struct.calcsize(s3_format)
        with open(filename, 'rb') as f:
            for _ in range(read_count):
                pd = f.read(read_size)
                if pd[43:] == b'\x00\x00\x00\x00\x00\x00':
                    continue
                p = S3Person._make(struct.unpack(s3_format, pd))
                attrkey = p['attrkey']
                if attrkey not in namekey:
                    print(attrkey, p['name'], 'senario:', i+1)
                    continue
                if attrkey not in persons:
                    persons[attrkey] = [namekey[attrkey], '', '', '', '', '', '']
                    cities[attrkey] = [namekey[attrkey], '', '', '', '', '', '']
                persons[attrkey][i+1] = p['name']
                cities[attrkey][i+1] = int(p['city']) + 1
    # for key, value in persons.items():
    #     print(key, value)

    memo = {
        '辛毗': '毘：同「毗」',
        '蔡邕': '蔡陽為「過五關斬六將」時人物',
        '孔伷': '孔秀為「過五關斬六將」時人物',
        '桓階': '演義有時誤寫為「桓楷」',
        '范彊': '演義把「彊」誤寫為「疆」',
        '金環三結': '遊戲中姓名字數上限為三',
        '朵思大王': '遊戲中姓名字數上限為三',
        '張闓': '「張闓」為陶謙部將',
        '張顗': '「張顗」為袁尚部下',
        '橋瑁': '演義作「喬瑁」',
    }

    # output markdown table to s3_scenario_name_list.md
    headers = ['人物', '劇本一', '劇本二', '劇本三', '劇本四', '劇本五', '劇本六', 'Memo']
    name_matrix = []
    for key, value in persons.items():
        full_name = value[0]
        name = full_name.split(' ')[0]
        name = name.replace('脩', '修')
        row = [f'[{name}](/人物/三國/{full_name})']
        for i in range(1, 7):
            if value[i] == '':
                row.append('')
            elif value[i] == name:
                city = f'({cities[key][i]})' if cities[key][i] < 200 else ''
                row.append(f'{name} {city}')
            else:
                city = f'({cities[key][i]})' if cities[key][i] < 200 else ''
                row.append(f'*{value[i]}* {city}')
        row.append('')
        if name in memo:
            row[-1] = memo[name]
        else:
            row[-1] = ''
        name_matrix.append(row)
    writer = MarkdownTableWriter(
        table_name='三國志三 武將名稱勘誤',
        headers=headers,
        value_matrix=name_matrix,
    )
    writer.write_table()


def get_san4_name_list():
    kao_names = {}
    with open('/Users/tzengyuxio/DOSBox/SAN4/SNDATA.S4', 'rb') as f:
        offsets = [30892, 50637, 70672, 90527, 144632, 163447, 195512]
        for idx, offset in enumerate(offsets):
            f.seek(offset)
            for i in range(1024):
                b = f.read(30)
                if len(b) < 30:
                    print('scenario', idx+1, 'end in ', i, '(out of data)')
                    break
                name = to_unicode_name(b[:10])
                kao = int.from_bytes(b[20:22], 'little')
                if name == '':
                    print('scenario', idx+1, 'end in ', i)
                    break
                if kao not in kao_names:
                    kao_names[kao] = name

    with open('/Users/tzengyuxio/DOSBox/SAN4/TAIKI.S4', 'rb') as f:
        f.seek(62)
        for i in range(1024): # TODO: 1024 也許需要放大調整試試
            b = f.read(50)
            if len(b) < 50:
                print('out of data: ', i)
            name = to_unicode_name(b[20:40])
            kao = int.from_bytes(b[40:42], 'little')
            if kao not in kao_names:
                kao_names[kao] = name

    # ==== show persons with 專用 kao cg
    # for k in sorted(kao_names):
    #     if k > 1024:
    #         break
    #     print(k, kao_names[k])
    # ==== show total count
    # print('total size:', len(kao_names))
    for i in range(250):
        name = kao_names[i] if i in kao_names else ''
        comment = '' if i in kao_names else f' // {i}, 0x{i:02X}'
        print(f"'{name}',{comment}")

    # ==== NBC
    with open('/Users/tzengyuxio/DOSBox/SAN4/MAIN.EXE', 'rb') as f:
        f.seek(316527)
        kao = []
        name = []
        # read one byte and push to kao, until 0xff
        while True:
            b = f.read(1)
            if b == b'\xff':
                break
            kao.append(int.from_bytes(b, 'little'))
        kao.append(1)
        kao.append(2)
        for i in range(len(kao)):
            # read bytes until 0x00, and convert to unicode
            name_bytes = []
            while True:
                b = f.read(1)
                if b == b'\x00':
                    break
                name_bytes.append(b)
            name.append(to_unicode_name(b''.join(name_bytes)))
        for k, n in zip(kao, name):
            print(k, n)
        f.seek(328318)
        npc_names = []
        for i in range(15):
            # read bytes until 0x00, and convert to unicode
            name_bytes = []
            while True:
                b = f.read(1)
                if b == b'\x00':
                    break
                name_bytes.append(b)
            npc_names.append(to_unicode_name(b''.join(name_bytes)))
        for n in npc_names:
            print(n)

def get_san5_name_list():
    kao_names = {}
    with open('/Users/tzengyuxio/DOSBox/SAN5/SNDATA.S5', 'rb') as f:
        offsets = [10180, 28250, 49607, 72510, 95304, 118121,  192851, 215453]
        for idx, offset in enumerate(offsets):
            f.seek(offset)
            for i in range(1024):
                b = f.read(38)
                if len(b) < 38:
                    print('scenario', idx+1, 'end in ', i, '(out of data)')
                    break
                name = to_unicode_name(b[:10])
                kao = int.from_bytes(b[30:32], 'little')
                if name == '':
                    print('scenario', idx+1, 'end in ', i)
                    break
                if kao not in kao_names:
                    kao_names[kao] = name
    with open('/Users/tzengyuxio/DOSBox/SAN5/TAIKI.S5', 'rb') as f:
        f.seek(74)
        for i in range(2400):
            b = f.read(69)
            if len(b) < 69:
                print('out of data: ', i)
                break
            name = to_unicode_name(b[31:41])
            kao = int.from_bytes(b[61:63], 'little')
            if kao not in kao_names:
                kao_names[kao] = name
    # ==== show persons with 專用 kao cg
    # for k in sorted(kao_names):
    #     # if k > 1024:
    #     #     break
    #     print(k, kao_names[k])
    # ==== show total count
    # print('total size:', len(kao_names))
    for i in range(1024):
        name = kao_names[i] if i in kao_names else ''
        comment = '' if i in kao_names or i > 500 else f' // {i}, 0x{i:02X}'
        if comment == '' and i % 16 == 0:
            comment = f' // {i}, 0x{i:02X}'
        print(f"'{name}',{comment}")

def genpei_opendat_header():
    with open("/Users/tzengyuxio/DOSBox/genpei/opendat.gp", 'rb') as f:
        for i in range(41):
            for j in range(16):
                a = f.read(1).hex()[1:]
                b = f.read(1).hex()[1:]
                c = f.read(1).hex()[1:]
                print(f'{a}{b}{c} ', end='')
            print()



if __name__ == '__main__':
    # 將中文轉換成 KOEI-TW 編碼
    # ss = ['伊籍', '張飛', '關羽', '華雄']
    # kt = [encode_text(s) for s in ss]
    # for s, k in zip(ss, kt):
    #     print('{}: {} -> {}'.format(s, encode_text(s).hex().upper(), to_unicode_name(k)))

    # print(to_unicode_name(b'\x92\xbf\xa3\x77'))  # 于禁
    # print(to_unicode_name(b'\x9c\xaf\x9a\x47'))  # 袁胤
    # print(to_unicode_name(b'\x93\x7a\xc2\x9a'))  # 王粲
    # print(to_unicode_name(b'\x9c\xaf\x9f\x4a'))  # 袁術
    # print(to_unicode_name(b'\x9E\x39\x97\x9C'))  # 曹昂
    # print(to_unicode_name(b'\xAD\xB6\x9A\x9A'))  # 蘇飛
    # print(to_unicode_name(b'\x94\x44\xad\xa5'))  # 伊籍, kao: 1E
    # print(to_unicode_name(b'\x93\xb2\x9c\xea\xaa\x77'))  # 司馬徽
    # print(to_unicode_name(b'\x9b\x30\x9c\xf0'))  # 孫乾

    # extract_sui_strings()

    # kohryuki_combine_persons()  # 項劉記 合併中日文人名
    # lempe_combine_persons()  # 拿破崙 合併中英文人名
    # lempe_list_cities_and_nations()  # 拿破崙 列出所有城市與國家

    # get_name_list('PERSONS_TABLE/san2_persons.csv', 219) # 三國志II 人物名單
    # get_name_list('PERSONS_TABLE/san3_persons_s1.csv', 307)  # 三國志III 人物名單
    # get_san3_name_list('PERSONS_TABLE/san3_persons_s1.csv', 230)  # 三國志III 人物名單 (by namekey)
    # get_name_list('PERSONS_TABLE/suikoden_persons_s1.csv', 255)  # 水滸傳 人物名單

    # get_san3_scenario_name_list('/Users/tzengyuxio/DOSBox/SAN3')

    # get_san4_name_list()
    # get_san5_name_list()
    genpei_opendat_header()
