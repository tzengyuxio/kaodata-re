#!/usr/bin/env python3
import argparse
from PIL import Image

parser = argparse.ArgumentParser(description="List all colors in an image")
parser.add_argument("filename", type=str, help="the path of the image")
parser.add_argument(
    "--x", type=int, default=0, help="x-coordinate of top-left corner of the block"
)
parser.add_argument(
    "--y", type=int, default=0, help="y-coordinate of top-left corner of the block"
)
parser.add_argument(
    "--w", type=int, help="width of the block (default: image width)", default=None
)
parser.add_argument(
    "--h", type=int, help="height of the block (default: image height)", default=None
)
parser.add_argument(
    "--hex", action="store_true", help="output colors in hexadecimal format"
)
args = parser.parse_args()


im = Image.open(args.filename)
if args.w is None or args.h is None:
    args.w, args.h = im.size
im = im.crop((args.x, args.y, args.x + args.w, args.y + args.h))
colors = im.convert('RGB').getcolors()

# palette = im.getpalette()
# im = im.convert("RGB")

# 以 RGB tuple 方式列出
if not args.hex:
    for count, color in sorted(colors, reverse=True):
        print(f"{color}: {count}")
# 以 #RRGGBB 方式列出
else:
    for count, color in sorted(colors, reverse=True):
        print(f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}: {count}")
print(f"Total {len(colors)} colors:")
# print(palette)
