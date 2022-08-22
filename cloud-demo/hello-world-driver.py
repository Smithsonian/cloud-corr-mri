import argparse
import subprocess
import sys

import paramsurvey

import paramsurvey_multimpi.client as client


# Google cloud HPC checklist https://cloud.google.com/architecture/best-practices-for-using-mpi-on-compute-engine#checklist
# Google storage: https://cloud.google.com/storage/docs/best-practices

def out_func(user_ret, system_kwargs, user_kwargs):
    print('out_func: saw an exit of', user_ret)
    sys.stdout.flush()
    kind = user_ret.get('pset', {}).get('kind')
    if kind == 'leader':
        user_kwargs['leader_count'] -= 1
        if user_kwargs['leader_count'] == 0:
            pass


def main():
    parser = argparse.ArgumentParser(description='difx_paramsurvey_driver, run inside ray')
    parser.add_argument('--ray', action='store_true', default=True)
    args = parser.parse_args()

    user_kwargs = {}
    client.start_multimpi_server(hostport=':8889', user_kwargs=user_kwargs)

    if args.ray:
        kwargs = {
            'backend': 'ray',
            'ray': {'address': 'auto'},
        }
    else:
        kwargs = {
            'backend': 'multiprocessing', 'ncores': 7,
        }
    paramsurvey.init(**kwargs)

    leaders = 1
    user_kwargs['leader_count'] = leaders
    followers = 9
    user_kwargs['follower_count'] = followers
    ncores = 60
    wanted = 600
    repeats = 1

    # I don't know why OPAL_PREFIX isn't getting set on the workers
    run_args = 'mpirun -x OPAL_PREFIX=/usr --machinefile %MACHINEFILE% -np {} ./a.out'.format(wanted)
    psets = []
    psets.extend([{'kind': 'leader', 'ncores': ncores, 'run_args': run_args, 'wanted': wanted}] * leaders)
    psets.extend([{'kind': 'follower', 'ncores': ncores}] * followers)

    psets = psets * repeats

    # this is how ray backend args are specified
    # XXX shouldn't paramsurvey hide this?
    for p in psets:
        if 'ncores' in p:
            p['ray'] = {'num_cores': p.get('ncores')}

    # example of how to return stdout from the cli process
    run_kwargs = {
        'stdout': subprocess.PIPE, 'encoding': 'utf-8',
        'stderr': subprocess.PIPE, 'encoding': 'utf-8',
    }
    user_kwargs['run_kwargs'] = run_kwargs
    user_kwargs['mpi'] = 'openmpi'

    #user_kwargs['machinefile'] = 'DiFX'
    #user_kwargs['DiFX_datastreams'] = 1  # should come from joblist file
    #user_kwargs['DiFX_jobname'] = 'difx_jobname'  # should come from joblist file

    results = paramsurvey.map(client.multimpi_worker, psets, user_kwargs=user_kwargs, out_func=out_func)

    client.end_multimpi_server()

    #assert results.progress.failures == 0
    print('driver: after map, failures is', results.progress.failures)

    for r in results.iterdicts():
        print('result:', r['cli'])

    for r in results.itertuples():
        if not isinstance(r.cli, str):
            print('result:', r.cli.returncode)  # needs stdout capture: , r.cli.stdout.rstrip())


if __name__ == '__main__':
    main()
    print('exiting')
