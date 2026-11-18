#!/usr/bin/env python3

from utils import *


def main():
    max_order_value = 13195
    orderToUnicodeTable = [""] * (max_order_value + 1)

    cns11643_unicode_table = load_cns11643_unicode_table()
    for k, v in cns11643_unicode_table.items():
        order = cns_to_order(k)
        kk = cns_from_order(order)
        print(k, v, order, kk)
    print(len(cns11643_unicode_table))
    with open("mytable.js", "w") as f:
        f.write("const cns11643ToUnicodeTable = {\n")
        for k, v in cns11643_unicode_table.items():
            if k == "":
                continue
            f.write(f'"{k}": "{v}",\n')
        f.write("};\n")
        f.write("\n")

        # f.write("const unicodeToCNS11643Table = {\n")
        # for k, v in cns11643_unicode_table.items():
        #     if k == "":
        #         continue
        #     f.write(f'"{v}": "{k}",\n')
        # f.write("};\n")
        # f.write("\n")

        # f.write("const unicodeToOrderTable = {\n")
        # for k, v in cns11643_unicode_table.items():
        #     if k == "":
        #         continue
        #     order = cns_to_order(k)
        #     if order < 0:
        #         continue
        #     orderToUnicodeTable[order] = v
        #     f.write(f'"{v}": {order},\n')
        # f.write("};\n")
        # f.write("\n")

        f.write("const unicodeToCNS11643OrderTable = {\n")
        for k, v in cns11643_unicode_table.items():
            if k == "":
                continue
            order = cns_to_order(k)
            if order < 0:
                continue
            orderToUnicodeTable[order] = v
            f.write(f'"{v}": ("{k}", {order}),\n')
        f.write("};\n")
        f.write("\n")

        f.write("const orderToUnicodeTable= [\n")
        for v in orderToUnicodeTable:
            f.write(f'"{v}",\n')
        f.write("];\n")
        f.write("\n")


if __name__ == "__main__":
    main()
