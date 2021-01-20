#!/usr/bin/env python


'''
Needs to run on python 2.7 because that's what's currently inside the
Singularity image

genmachines distributed with DiFX seems to do the wrong thing when you
have a single node, creating too few lines in .machines and then not
creating enough lines in .threads. As a result you can end up with extreme
oversubscription and high loads.

This genmachines works only on a single machine, and seems to mostly keep
the load down to something reasonable. You still may need to oversubscribe,
if there are too many baselines.

export DIFX_MPIRUNOPTIONS="--oversubscribe"  # OpenMPI
'''


from __future__ import print_function

import sys
import os
import os.path
import math
import socket

def _core_count():
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, NotImplementedError, OSError):
        try:
            return os.cpu_count()
        except AttributeError:
            # py2.7
            import multiprocessing
            return multiprocessing.cpu_count()


for base in sys.argv[1:]:
    if base.endswith('.input'):
        base = base[:-len('.input')]

    if not os.path.exists(base + '.input'):
        raise ValueError(base + '.input does not exist')

    hostname = socket.gethostname()

    with open(base + '.input', 'r') as fd:
        for line in fd:
            if 'ACTIVE DATASTREAMS:' in line:
                datastreams = line.rsplit(None, 1)[1]  # py2.7
            if 'ACTIVE BASELINES:' in line:
                baselines = line.rsplit(None, 1)[1]  # py2.7

    nodes = 1 + int(datastreams) + int(baselines)
    threads = int(math.ceil(_core_count() / int(baselines)))
    threads = max(threads, 1)
    cores = 1 + int(datastreams) + threads * int(baselines)  # 1 for fxmanager

    print(base,
          'datastreams='+datastreams,
          'baselines='+baselines, 'threads='+str(threads),
          'cores='+str(cores))

    with open(base + '.machines', 'w') as fd:
        for _ in range(nodes):
            print(hostname, file=fd)

    with open(base + '.threads', 'w') as fd:
        print('NUMBER OF CORES:    {}\n{}'.format(1, threads), file=fd)
