#!/usr/bin/env python

import sys
import os
import socket
import math


def estimate(base, cores=None):
    if base.endswith('.input'):
        base = base[:-len('.input')]

    if not os.path.exists(base + '.input'):
        raise ValueError(base + '.input does not exist')

    with open(base + '.input', 'r') as fd:
        for line in fd:
            if 'ACTIVE DATASTREAMS:' in line:
                datastreams = line.rsplit(None, 1)[1]  # py2.7
            if 'ACTIVE BASELINES:' in line:
                baselines = line.rsplit(None, 1)[1]  # py2.7

    mincores = 1 + int(datastreams) + int(baselines)

    #threads = int(math.ceil(cores / int(baselines)))
    #threads = max(threads, 1)
    #cores = 1 + int(datastreams) + threads * int(baselines)  # 1 for fxmanager

    return mincores


if __name__ == '__main__':
   for base in sys.argv[1:]:
       print(base, 'mincores=', estimate(base))
