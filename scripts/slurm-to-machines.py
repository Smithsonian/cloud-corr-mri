#!/usr/bin/env python

# if running inside a Slurm batch job, generate a difx-compatible machines file

import os
import subprocess
import sys
import socket


def expand_slurm_nodelist(nodelist):
    args = 'scontrol show hostnames'.split() + [nodelist]

    # run with capture_output would be perfect here, but it's only available starting with 3.7
    # subprocess.run is 3.5+
    proc = subprocess.run(args, check=True, stdout=subprocess.PIPE)
    return proc.stdout.decode('utf8').splitlines()


def emit(nodelist, cpus_on_node):
    print('version = 1')

    first = 2
    for node in nodelist:
        print(node+',', str(first)+',', cpus_on_node.pop(0))
        if first == 2:
            first = 1


def do_slurm():
    if 'SLURM_JOB_ID' not in os.environ:
        return False

    cpus_on_node = os.environ['SLURM_CPUS_ON_NODE'].split(',')
    nodelist = expand_slurm_nodelist(os.environ['SLURM_JOB_NODELIST'])

    # the first node in nodelist is me,
    # make sure it matches `hostname` so genmachines doesn't have a cow
    hostname = socket.gethostname()
    nodelist.pop(0)
    nodelist.insert(0, hostname)

    length = len(cpus_on_node)
    if length != 1 and length != len(nodelist):
        print('cpus on node', cpus_on_node, file=sys.stderr)
        print('nodelist', nodelist, file=sys.stderr)
        raise ValueError('I expect cpus_on_node to be length 1 or length nodelist')

    if length == 1:
        cpus_on_node = cpus_on_node * len(nodelist)

    emit(nodelist, cpus_on_node)
    return True


def main():
    if not do_slurm():
        print('This is not slurm.')


if __name__ == '__main__':
    main()
