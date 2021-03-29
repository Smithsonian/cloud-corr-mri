import sys

import vdif_utils

args = sys.argv
program = args.pop(0)
limit = int(args.pop(0))

for f in args:
    df = vdif_utils.index(f, limit=limit, only_seconds=True, verbose=True)

    print(df)
    print(df.dtypes)
