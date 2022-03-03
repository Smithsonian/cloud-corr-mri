import argparse
import time
import os
import signal
import sys

import paramsurvey

import mpi_helper_client as client


# Google cloud HPC checklist https://cloud.google.com/architecture/best-practices-for-using-mpi-on-compute-engine#checklist
# Google storage: https://cloud.google.com/storage/docs/best-practices

def leader_start_mpi(pset, ret, wanted, user_kwargs):
    # XXX generate special difx hostfile
    # ret['followers'] is a list of fkeys and cores
    # get hostnames out of the fkeys

    cmd = pset['run_args'].format(int(wanted)).split()
    print('leader about to run', cmd)
    run_kwargs = pset.get('run_kwargs') or user_kwargs.get('run_kwargs') or {}
    mpi_proc = client.run_mpi(cmd, **run_kwargs)
    print('leader just ran MPI and mpi_proc is', mpi_proc)
    return mpi_proc


def leader(pset, system_kwargs, user_kwargs):
    print('I am leader and my pid is {}'.format(os.getpid()))
    pubkey = client.get_pubkey()
    mpi_proc = None
    ncores = pset['ncores']

    lseq = 0
    state = 'waiting'
    wanted = pset['wanted']

    print('I am leader before loop')
    while True:
        print('I am leader top of loop')
        sys.stdout.flush()
        ret = client.leader_checkin(ncores, wanted, pubkey, state, lseq)
        print('driver: leader checkin returned', ret)
        ret = ret['result']
        if ret is None:
            continue

        if ret['state'] == 'running':
            if state == 'running':
                assert mpi_proc is not None
                continue
            mpi_proc = leader_start_mpi(pset, ret, wanted, user_kwargs)
            state = 'running'
        elif ret['state'] == 'waiting' and mpi_proc is not None:
            # oh oh! mpi-helper thinks something bad happened. perhaps one of my followers timed out?
            mpi_proc.kill()
            completed = client.finish_mpi(mpi_proc)
            status = client.check_mpi(mpi_proc)
            return({'cli': completed})

        if mpi_proc:
            status = client.check_mpi(mpi_proc)
            if status is not None:
                # a normal exit
                completed = client.finish_mpi(mpi_proc)
                return({'cli': completed})

        time.sleep(0.1)
    return


def follower(pset, system_kwargs, user_kwargs):
    print('I am follower and my pid is {}'.format(os.getpid()))
    fseq = 0
    state = 'available'
    ncores = pset['ncores']

    while True:
        ret = client.follower_checkin(ncores, state, fseq)
        print('driver: follower checkin returned', ret)
        ret = ret['result']
        if ret is None:
            continue

        if ret['state'] == 'assigned':
            client.deploy_pubkey(ret['pubkey'])
        elif state == 'running':
            if ret['state'] == 'exit':
                return

        state = ret['state']
        time.sleep(1.0)


def run_mpi_multinode(pset, system_kwargs, user_kwargs):
    if pset['kind'] == 'leader':
        leader(pset, system_kwargs, user_kwargs)

    if pset['kind'] == 'follower':
        follower(pset, system_kwargs, user_kwargs)


def main():
    parser = argparse.ArgumentParser(description='difx_paramsurvey_driver, run inside ray')
    parser.add_argument('--resources', action='store', default='')
    args = parser.parse_args()

    helper_proc = client.run_mpi_helper()
    time.sleep(1)  # give the mpi helper time to get going

    #paramsurvey.init(backend='ray')
    paramsurvey.init(backend='multiprocessing', ncores=4)

    psets = [
        {'kind': 'leader', 'ncores': 1, 'run_args': 'mpirun -np {} ./a.out', 'wanted': 3},
        {'kind': 'follower', 'ncores': 1},
        {'kind': 'follower', 'ncores': 1},
    ]

    # this is how ray backend args are specified
    for p in psets:
        if 'ncores' in p:
            p['ray'] = {'ncores': p.get('ncores')}
            #p['ray'] = {'ncores': p.pop('ncores')}

    # example of how to return stdout from the cli process
    #user_kwargs = {'run_kwargs': {
    #    'stdout': subprocess.PIPE, 'encoding': 'utf-8',
    #    'stderr': subprocess.PIPE, 'encoding': 'utf-8',
    #}}
    user_kwargs = {}

    results = paramsurvey.map(run_mpi_multinode, psets, user_kwargs=user_kwargs)

    status = client.check_mpi_helper(helper_proc)
    if status is not None:
        print('driver: looked at mpi_helper and it had already existed with status', str(status))
    helper_proc.kill()

    for r in results.itertuples():
        # r.cli is a subprocess.CompletedProcess object
        #print(r.cli.returncode, r.cli.stdout.rstrip())
        pass


if __name__ == '__main__':
    main()
