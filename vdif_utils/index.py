import sys

import vdif_utils

for f in sys.argv[1:]:
    df = vdif_utils.index(f, limit=10)

    print(df.dtypes)
    print(df)
    for r in df.itertuples():
        print(r.seconds, r.frame_nr)
