#!/usr/bin/env python

from __future__ import print_function

import sys
import os
import os.path

dataroot = sys.argv[1].rstrip('/')  # e.g. ../b2/b2-data
filelists = sys.argv[2:]

for f in filelists:
    if not f.endswith('.orig'):
        os.rename(f, f + '.orig')
        f = f + '.orig'

    new = f.replace('.orig', '', 1)
    with open(new, 'w') as ofd:
        with open(f, 'r') as ifd:
            for line in ifd:
                prefix = line.split('/mnt', 1)[0]
                line = line.replace(prefix, dataroot, 1).rstrip()
                file = line.split()[0]
                if not os.path.exists(file):
                    continue

                print(file, 'exists')
                print(line, file=ofd)
