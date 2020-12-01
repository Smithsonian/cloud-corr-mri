import sys

import baseband

for f in sys.argv[1:]:
    print(baseband.file_info(f))
