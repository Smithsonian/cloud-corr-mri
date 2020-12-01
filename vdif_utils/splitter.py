import sys

import vdif_utils

delta_t = int(sys.argv.pop(1))
nfiles = None

for f in sys.argv[1:]:
    vdif_utils.split(f, delta_t=delta_t, nfiles=nfiles)
