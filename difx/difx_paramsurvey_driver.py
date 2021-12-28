import argparse
import json
import os
import socket
import subprocess

import paramsurvey
from paramsurvey.utils import subprocess_run_worker

from difx_utils import get_difx_joblists, add_costs


'''
This code is a "driver" that runs correlation in the cloud or a compute cluster.

This code uses the paramusrvey module to orchestrate the computation.

Paramsurvey then uses the "ray" distributed system to run the computations.

Ray can run in many environments, such as slurm on a compute cluster,
cloud, and in k8s.
'''


def analyze_resources(argsr):
    'Find out how cores and nodes we have'
    resources = paramsurvey.current_resources()

    resources = list(reversed(sorted([r['num_cores'] for r in resources])))
    print('DEBUG: ray resources are', resources)

    if not argsr:
        return resources

    try:
        (nodes, cores) = argsr.split('x')
        if not nodes.endswith('n') or not cores.endswith('c'):
            raise ValueError()
        nodes = int(nodes[:-1])
        cores = int(cores[:-1])
    except Exception:
        raise ValueError('--resources should look like "18nx32c" for 18 nodes and 32 cores')
    resources = (cores,) * nodes
    print('DEBUG: CLI resources are', resources)

    return resources


def schedule_resources(resources, psets):
    sum_costs = sum(p['cost'] for p in psets)
    jobs = len(psets)
    sum_cores = sum(resources)
    nodes = len(resources)

    # We will frequently want to have sorted psets
    psets = sorted(psets, key=lambda p: -p['cost'])

    # some special cases
    if nodes == jobs:
        print('case: nodes == jobs')
        # give each job an entire node
        for p in psets:
            p['num_cores'] = resources.pop(0)
        return psets

    if nodes > jobs:
        raise ValueError('case: nodes > jobs, not yet implemented')
    
    if nodes < jobs:
        print('case: nodes < jobs')
        # let ray do the scheduling
        repeats = jobs // nodes + 1
        resources *= repeats
        for p in psets:
            p['num_cores'] = resources.pop(0)


def difx_genmachines(pset):
    streams = len(pset['stations'])
    #baselines = (streams * (streams-1)) // 2  # historically comes from .input but we fake it
    num_cores = pset['ray']['num_cores']
    compute_cores = num_cores - 1 - streams  # 1 for fxmanager, 1 per stream

    # here's the biggest difference to the standard genmachines algorithm -- single machine only
    #cores = 1  # difx "Core" processes
    threads = [compute_cores]

    # write it out
    # QUIRK: canot use localhost as the hostname or difx (?) will complain
    hostname = socket.gethostname()
    base = 'machines.' + pset['jobname']

    machines_file = base + '.input'
    with open(machines_file, 'w') as fd:
        for i in range(1 + streams + len(threads)):
            print(hostname, file=fd)

    threads_file = base + '.threads'
    with open(threads_file, 'w') as fd:
        print('NUMBER OF CORES:    {}'.format(len(threads)), file=fd)
        for i in len(threads):
            print(threads[i])


def difx_run_worker(pset, system_kwargs, user_kwargs):
    os.chdir(pset['band'])

    difx_input = pset['jobname'] + '.input'
    difx_genmachines(pset)
    
    # openmpi:
    # if oversubscription, must set --oversubscribe  # which also sets --mca mpi_yield_when_idle 1
    # --map-by node # means 1/line, no smart OpenMPI tricks when used with slurm etc
    # --mca rmaps seq  # means use machines file sequentially
    # --allow-run-as-root  # depending on your container, you might want to know about this
    os.environ['DIFX_MPIRUNOPTIONS'] = '--map-by node --mca rmaps seq'

    # YYY --force  # even if output file exists
    # btw -np is set by the length of the machines file
    run_args = 'startdifx --dont-calc -f --nomachines '+difx_input
    pset['run_args'] = run_args.split()

    # YYY allow helper nodes

    return subprocess_run_worker(pset, system_kwargs, user_kwargs)


def main():
    '''
    Tear down cluster when finished
    '''

    parser = argparse.ArgumentParser(description='difx_paramsurvey_driver, run inside ray')
    parser.add_argument('--resources', action='store', default='')
    args = parser.parse_args()

    paramsurvey.init()

    psets = get_difx_joblists()
    add_costs(psets)
    resources = analyze_resources(args.resources)
    schedule_resources(resources, psets)

    # this is how ray backend args are specified
    for p in psets:
        if 'num_cores' in p:
            p['ray'] = {'num_cores': p.pop('num_cores')}

    print('psets as json')
    print(json.dumps(psets, indent=2))

    # example of how to return stdout
    user_kwargs = {'run_kwargs': {'stdout': subprocess.PIPE, 'encoding': 'utf-8'}}

    print('psets')
    print(psets)
    exit()

    results = paramsurvey.map(difx_run_worker, psets, user_kwargs=user_kwargs)

    # YYY explicitly tear down the clsuter?

    for r in results.itertuples():
        # r.cli is a subprocess.CompletedProcess object
        print(r.cli.returncode, r.cli.stdout.rstrip())


if __name__ == '__main__':
    main()
