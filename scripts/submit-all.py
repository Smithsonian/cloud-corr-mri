#!/usr/bin/env python

import sys
import glob
import os.path
import math


def estimate(base, cores=None):
    if base.endswith('.input'):
        base = base[:-len('.input')]

    if not os.path.exists(base + '.input'):
        raise ValueError(base + '.input does not exist')

    datastreams = '0'
    baselines = '0'

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


cores_per_node = 48


for band in sys.argv[1:]:
    if band.endswith('.input'):
        files = [band]
        band, _ = os.path.split(band)
    else:
        files = glob.glob(band+'/*.input')

    for f in files:
        mincores = estimate(f)
        if mincores == 1:
            # this .input file has no work to do
            continue
        nodes_wanted = math.ceil(mincores / cores_per_node)
        print('band={} file={}'.format(band, os.path.basename(f)))
        export = '--export=DIFX_BAND={},DIFX_INPUT={}'.format(band, os.path.basename(f))

        job_name = '-J difx-'+band

        print('sbatch -N {} -n {} {} difx.batch'.format(nodes_wanted, nodes_wanted * cores_per_node, export))
        os.system('sbatch -N {} -n {} {} {} difx.batch'.format(nodes_wanted, nodes_wanted * cores_per_node, job_name, export))
