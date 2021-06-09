#!/usr/bin/env python

import sys
import re
import os

smap = {
    b'JCMT': 'J',
    b'LMT': 'L',
    b'SMAP': 'S',
    b'SPT': 'Y',
}

splitmap = dict(zip('123456', 'abcdef'))
print('splitmap', splitmap)

for f in sys.argv[1:]:
    if not f.startswith('fplot-'):
        continue
    split = splitmap[f[6]]
    newf = None
    with open(f, 'rb') as fd:
        text = fd.read()
        m = re.search(b'\\(([A-Z]{3,4}) - ([A-Z]{3,4}), fgroup ., pol (..)\\)', text)
        #m = re.match(b'\\(([A-Z]).*\\)', text)
        if m:
            tel1, tel2, pol = m.groups()
            if pol != b'RR':
                continue
            if tel1 not in smap or tel2 not in smap:
                continue
            newf = '{}{}-{}.ps'.format(smap[tel1], smap[tel2], split)
    if newf:
        print(f, newf)
        os.rename(f, newf)
