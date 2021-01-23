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


cores = {}
fxmanager = None

with open(os.environ['DIFX_MACHINES']) as fd:
    # version = 1
    version = next(fd)
    if 'version' not in version:
        raise ValueError('expecting version line at start: '+version)
    for line in fd:
        parts = line.split(',')
        if len(parts) < 3:
            raise ValueError('confused by machines line: '+line)
        node, kind, ncores = parts[:3]
        if int(kind) == 0:
            continue
        if int(kind) == 1:
            cores[node.strip()] = int(ncores.strip())
        if int(kind) == 2:
            cores[node.strip()] = int(ncores.strip())
            fxmanager = node.strip()

for base in sys.argv[1:]:
    if base.startswith('-m'):
        print('set DIFX_MACHINES, so far this program does not support -m')
        exit(1)

    if base.endswith('.input'):
        base = base[:-len('.input')]

    if not os.path.exists(base + '.input'):
        raise ValueError(base + '.input does not exist')

    hostname = socket.gethostname()

    with open(base + '.input', 'r') as fd:
        for line in fd:
            if 'ACTIVE DATASTREAMS:' in line:
                datastreams = int(line.rsplit(None, 1)[1])
            if 'ACTIVE BASELINES:' in line:
                baselines = int(line.rsplit(None, 1)[1])

    names = list(cores.keys())
    names.remove(fxmanager)
    names.insert(0, fxmanager)

    total = 1 + datastreams + baselines
    #if len(names) > total:
    #    raise ValueError('sorry, you have too many nodes')

    # extend names so we can easily iterate over it
    if len(names) < total:
        extra = names.copy()
        while len(names) < total:
            names += extra

    with open(base + '.machines', 'w') as fd:
        for i in range(1 + datastreams):
            print(names[i], file=fd)
            # subtract off fxmanager and datastreams
            cores[names[i]] -= 1

        remaining = 0
        for k, v in cores.items():
            if v > 0:
                print(k, file=fd)
                remaining += 1
            elif v < 0:
                raise ValueError('too few cores')

    with open(base + '.threads', 'w') as fd:
        print('NUMBER OF CORES:    {}'.format(remaining), file=fd)
        for k, v in cores.items():
            if v > 0:
                print(k, v-1, file=fd)
