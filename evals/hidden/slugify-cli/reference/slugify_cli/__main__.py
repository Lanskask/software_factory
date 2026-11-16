import argparse
import sys

from slugify_cli import slugify

p = argparse.ArgumentParser(prog="slugify")
p.add_argument("--sep", default="-")
p.add_argument("--max-len", type=int)
p.add_argument("text", nargs="+")
args = p.parse_args()
slug = slugify(" ".join(args.text), args.sep, args.max_len)
if not slug:
    sys.exit("slugify: empty slug")
print(slug)
