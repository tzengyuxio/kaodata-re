#!/usr/bin/env python3
import csv


def build_name_key():
    file = 'ROTK - Character Stats & Abilities.csv'
    with open(file, 'r', encoding='utf-8') as f:
        csv_reader = csv.reader(f)
        header = next(csv_reader)

        # name_key_fields: {game_id: [武力, 智力, 政治, 魅力]}
        name_key_fields = {}
        for i, field in enumerate(header):
            if '\n' not in field:
                continue
            game_id, ability_name = field.split('\n')
            if game_id not in name_key_fields:
                name_key_fields[game_id] = [None, None, None, None]
            if ability_name == '武力':
                name_key_fields[game_id][0] = i
            if ability_name == '知力':
                name_key_fields[game_id][1] = i
            if ability_name == '政治':
                name_key_fields[game_id][2] = i
            if ability_name == '魅力':
                name_key_fields[game_id][3] = i
            if ability_name == '身體' and game_id in ['S01']:  # 武知身魅
                name_key_fields[game_id][2] = i
            if ability_name == '統率' and game_id in ['S09', 'S12']:  # 武知政統
                name_key_fields[game_id][3] = i
        # for game_id, fields in name_key_fields.items():
        #     print(game_id, fields)

        # 調整順序
        s01 = name_key_fields['S01']
        name_key_fields['S01'] = [s01[2], s01[0], s01[1], s01[3]]  # 武知身魅 -> 身武知魅
        s09 = name_key_fields['S09']
        name_key_fields['S09'] = [s09[3], s09[0], s09[1], s09[2]]  # 武知政統 -> 統武知政
        s12 = name_key_fields['S12']
        name_key_fields['S12'] = [s12[3], s12[0], s12[1], s12[2]]  # 武知政統 -> 統武知政

        # name_key: f'{game_id}_{武力}{智力}{政治}{魅力}'
        name_keys = {}
        for row in csv_reader:
            name = row[0]
            for game_id, fields in name_key_fields.items():
                if row[fields[0]] == '':
                    continue
                abilities = [row[i] if i is not None else 'FF' for i in fields]
                a1, a2, a3, a4 = ['A0' if x == '100' else x for x in abilities]
                name_key = f'{game_id}_{a1:>02}{a2:>02}{a3:>02}{a4:>02}'
                if name_key in name_keys:
                    print("duplicated: ", name_key, name_keys[name_key], name)
                name_keys[name_key] = name

        for name_key, name in name_keys.items():
            if len(name_key) != 12:
                print(name_key, name)
        print(len(name_keys))

        # output to name_key.csv
        with open('namekey.csv', 'w') as fout:
            csv_writer = csv.writer(fout)
            csv_writer.writerow(['name_key', 'name'])
            for name_key, name in name_keys.items():
                csv_writer.writerow([name_key, name])


if __name__ == '__main__':
    build_name_key()
