import argparse
import time
import os
import sys
import subprocess
import signal
import functools

import paramsurvey

import mpi_helper_client as client


sigint_count = 0


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
        if ret['state'] == 'exiting':
            print('driver leader: received exiting status')
            return

        if ret['state'] == 'running':
            if state == 'running':
                assert mpi_proc is not None
            else:
                mpi_proc = leader_start_mpi(pset, ret, wanted, user_kwargs)
                print('driver: leader just started mpi proc and poll returns', client.check_mpi(mpi_proc))
                state = 'running'
        elif ret['state'] == 'waiting' and mpi_proc is not None:
            # oh oh! mpi-helper thinks something bad happened. perhaps one of my followers timed out?
            # XXX did the mpi helper server send all my followers to exiting?
            mpi_proc.send_signal(signal.SIGINT)
            completed = client.finish_mpi(mpi_proc)
            status = client.check_mpi(mpi_proc)
            return {'cli': completed}

        if mpi_proc:
            status = client.check_mpi(mpi_proc)
            print('driver: leader checking mpirun: ', status)
            os.system('ps')
            if status is not None:
                print('driver: leader observes normal exit')
                state = 'exiting'
                completed = client.finish_mpi(mpi_proc)  # should complete immediately
                for _ in range(100):
                    ret = client.leader_checkin(ncores, wanted, pubkey, state, lseq)
                    print('driver: leader checkin returned', ret)
                    if ret['result'] and ret['result']['state'] == 'exiting':
                        break
                return {'cli': completed}

        time.sleep(0.1)
    return


def follower(pset, system_kwargs, user_kwargs):
    print('I am follower and my pid is {}'.format(os.getpid()))
    fseq = 0
    state = 'available'
    ncores = pset['ncores']

    while True:
        print('driver: follower checkin with state', state)
        ret = client.follower_checkin(ncores, state, fseq)
        print('driver: follower checkin returned', ret)
        ret = ret['result']
        if ret is None:
            continue

        if ret['state'] == 'assigned' and state != 'assigned':
            # do this only once
            client.deploy_pubkey(ret['pubkey'])
        elif ret['state'] == 'exiting':
            print('driver: follower told to exit')
            # for pandas type reasons, if cli is an object for the leader, it has to be an object for the follower
            # elsewise pandas will make the column a float
            return {'cli': 'hi pandas'}

        state = ret['state']
        time.sleep(1.0)


def run_mpi_multinode(pset, system_kwargs, user_kwargs):
    if pset['kind'] == 'leader':
        return leader(pset, system_kwargs, user_kwargs)

    if pset['kind'] == 'follower':
        return follower(pset, system_kwargs, user_kwargs)


def tear_down_helper(helper_proc):
    helper_proc.send_signal(signal.SIGHUP)
    for _ in range(10):
        status = client.check_mpi_helper(helper_proc)
        if status is not None:
            break
        time.sleep(1.0)
    if status is None:
        helper_proc.kill()


def mysignal(helper_proc, signum, frame):
    if signum == signal.SIGINT:
        global sigint_count
        sigint_count += 1
        if sigint_count == 1:
            print('driver: ^C seen, type it again to tear down', file=sys.stderr)
        else:
            print('driver: tearing down for ^C', file=sys.stderr)
            tear_down_helper(helper_proc)


def main():
    parser = argparse.ArgumentParser(description='difx_paramsurvey_driver, run inside ray')
    parser.add_argument('--resources', action='store', default='')
    args = parser.parse_args()

    helper_proc = client.run_mpi_helper()
    time.sleep(1)  # give the mpi helper time to get going
    mysignal_ = functools.partial(mysignal, helper_proc)
    signal.signal(signal.SIGINT, mysignal_)

    #paramsurvey.init(backend='ray')
    paramsurvey.init(backend='multiprocessing', ncores=4)

    psets = [
        {'kind': 'leader', 'ncores': 1, 'run_args': 'mpirun -np {} ./a.out', 'wanted': 3},
        {'kind': 'follower', 'ncores': 1},
        {'kind': 'follower', 'ncores': 1},
    ]

    # this is how ray backend args are specified
    # XXX shouldn't paramsurvey hide this?
    for p in psets:
        if 'ncores' in p:
            p['ray'] = {'ncores': p.get('ncores')}

    # example of how to return stdout from the cli process
    user_kwargs = {'run_kwargs': {
        'stdout': subprocess.PIPE, 'encoding': 'utf-8',
        'stderr': subprocess.PIPE, 'encoding': 'utf-8',
    }}

    results = paramsurvey.map(run_mpi_multinode, psets, user_kwargs=user_kwargs)

    status = client.check_mpi_helper(helper_proc)
    if status is not None:
        print('driver: looked at mpi_helper and it had already exited with status', str(status), file=sys.stderr)
    else:
        print('driver: mpi_helper has not exited already, tearing it down', file=sys.stderr)
        tear_down_helper(helper_proc)

    assert results.progress.failures == 0

    for r in results.iterdicts():
        print(r['cli'])

    for r in results.itertuples():
        if not isinstance(r.cli, str):
            print(r.cli.returncode, r.cli.stdout.rstrip())


if __name__ == '__main__':
    main()
