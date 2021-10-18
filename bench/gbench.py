#!/usr/bin/env python

import glob
import subprocess
import sys
import platform
import time


files = glob.glob('bench-*.deleteme')
if files:
    print('rm bench-*.deleteme first')
    exit(1)

size = int(sys.argv[1])
procs = int(sys.argv[2])

size_per_proc = size * 1000 // procs

s = 'seq {} | xargs -I XX -n 1 -P {} dd if=/dev/zero of=bench-XX.deleteme bs=1000000 count={}'.format(procs, procs, size_per_proc)

if platform.system() == 'Linux':
    s += ' conv=fdatasync'
else:
    s += '; sync; sync; sync'

subprocess.run('sync')
subprocess.run('sync')

start = time.time()
subprocess.run(s, shell=True)
elapsed = time.time() - start

rate = size / elapsed

print('procs {} size {} GB rate {:.2f} GB/s'.format(procs, size, rate))
