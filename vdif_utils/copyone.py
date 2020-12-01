import sys

import baseband.vdif as vdif

fin = sys.argv[1]
fout = sys.argv[2]

with vdif.open(fin, 'rb') as fr:
    with vdif.open(fout, 'wb') as fw:
        for _ in range(17):
            frame = fr.read_frame()
            fw.write_frame(frame)
