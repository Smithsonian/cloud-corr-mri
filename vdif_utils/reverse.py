import sys
import os.path

import vdif_utils

for f in sys.argv[1:]:
    fnew = os.path.split(f)[1]+'.rev'
    if os.path.isfile(fnew):
        raise ValueError(fnew+' already exists')

    df = vdif_utils.index(f, limit=10)
    print('writing', fnew)
    vdif_utils.write_ordered(f, fnew, df[::-1])
