import requests
import os
import os.path
import socket
import subprocess
import time
import signal
import sys
import functools

url = "http://localhost:8889/jsonrpc"
timeout = (4, 1)  # connect, read
sigint_count = 0
leader_exceptions = []
follower_exceptions = []
helper_server_proc = None


def get_pubkey():
    with open(os.path.expanduser('~/.ssh/id_rsa.pub')) as f:
        return f.read()


def deploy_pubkey(pubkey):
    keyfile = os.path.expanduser('~/.ssh/authorized_keys')
    if os.path.exists(keyfile):
        with open(keyfile) as f:
            existing = f.read()
        if pubkey in existing:
            return

    with open(keyfile, 'a') as f:
        f.write(pubkey)
    os.chmod(keyfile, 0o600)


def leader_checkin(cores, wanted_cores, pubkey, state, lseq):
    pid = os.getpid()
    ip = socket.gethostname()
    payload = {
        'method': 'leader_checkin',
        'params': [ip, cores, pid, wanted_cores, pubkey, state, lseq],
        'jsonrpc': '2.0',
        'id': 0,
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout).json()
        leader_exceptions.clear()
    except Exception as e:
        leader_exceptions.append(str(e))
        if len(leader_exceptions) > 100:
            raise ValueError('too many leader_checkin exceptions ({})'.format(len(leader_exceptions))) from e
        response = {'result': None}  # clients expect this
    return response


def follower_checkin(cores, state, fseq):
    pid = os.getpid()
    ip = socket.gethostname()
    payload = {
        'method': 'follower_checkin',
        'params': [ip, cores, pid, state, fseq],
        'jsonrpc': '2.0',
        'id': 0,
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout).json()
        follower_exceptions.clear()
    except Exception as e:
        follower_exceptions.append(str(e))
        if len(follower_exceptions) > 100:
            raise ValueError('too many follower_checkin exceptions ({})'.format(len(follower_exceptions))) from e
        response = {'result': None}  # clients expect this
    return response


def leader_start_mpi(pset, ret, wanted, user_kwargs):
    # XXX generate special difx hostfile
    # ret['followers'] is a list of fkeys and cores
    # get hostnames out of the fkeys

    cmd = pset['run_args'].format(int(wanted)).split()
    print('leader about to run', cmd)
    run_kwargs = pset.get('run_kwargs') or user_kwargs.get('run_kwargs') or {}
    mpi_proc = run_mpi(cmd, **run_kwargs)
    print('leader just ran MPI and mpi_proc is', mpi_proc)
    return mpi_proc


def leader(pset, system_kwargs, user_kwargs):
    print('I am leader and my pid is {}'.format(os.getpid()))
    pubkey = get_pubkey()
    mpi_proc = None
    ncores = pset['ncores']

    lseq = 0
    state = 'waiting'
    wanted = pset['wanted']

    print('I am leader before loop')
    while True:
        print('I am leader top of loop')
        sys.stdout.flush()
        ret = leader_checkin(ncores, wanted, pubkey, state, lseq)
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
                print('driver: leader just started mpi proc and poll returns', check_mpi(mpi_proc))
                state = 'running'
        elif ret['state'] == 'waiting' and mpi_proc is not None:
            # oh oh! mpi-helper thinks something bad happened. perhaps one of my followers timed out?
            # XXX did the mpi helper server send all my followers to state=exiting?
            mpi_proc.send_signal(signal.SIGINT)
            completed = finish_mpi(mpi_proc)
            status = check_mpi(mpi_proc)
            return {'cli': completed}

        if mpi_proc:
            status = check_mpi(mpi_proc)
            print('driver: leader checking mpirun: ', status)
            os.system('ps')
            if status is not None:
                print('driver: leader observes normal exit')
                state = 'exiting'
                completed = finish_mpi(mpi_proc)  # should complete immediately
                for _ in range(100):
                    ret = leader_checkin(ncores, wanted, pubkey, state, lseq)
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
        ret = follower_checkin(ncores, state, fseq)
        print('driver: follower checkin returned', ret)
        ret = ret['result']
        if ret is None:
            continue

        if ret['state'] == 'assigned' and state != 'assigned':
            # do this only once
            deploy_pubkey(ret['pubkey'])
        elif ret['state'] == 'exiting':
            print('driver: follower told to exit')
            break

        state = ret['state']
        time.sleep(1.0)

    # for pandas type reasons, if cli is an object for the leader, it has to be an object for the follower
    # elsewise pandas will make the column a float
    return {'cli': 'hi pandas'}


def mpi_multinode_worker(pset, system_kwargs, user_kwargs):
    if pset['kind'] == 'leader':
        return leader(pset, system_kwargs, user_kwargs)

    if pset['kind'] == 'follower':
        return follower(pset, system_kwargs, user_kwargs)


def tear_down_mpi_helper_server(helper_server_proc):
    helper_server_proc.send_signal(signal.SIGHUP)
    for _ in range(10):
        status = check_mpi_helper_server(helper_server_proc)
        if status is not None:
            break
        time.sleep(1.0)
    if status is None:
        helper_server_proc.kill()


def mysignal(helper_server_proc, signum, frame):
    if signum == signal.SIGINT:
        global sigint_count
        sigint_count += 1
        if sigint_count == 1:
            print('driver: ^C seen, type it again to tear down', file=sys.stderr)
        elif sigint_count == 2:
            print('driver: tearing down for ^C', file=sys.stderr)
            tear_down_mpi_helper_server(helper_server_proc)
        else:
            print('driver: additional sigint ignored', file=sys.stderr)


def start_mpi_helper_server():
    # We can't really use capture_output/stdin/stdout for the server because we have no way to repeatedly call .communicate()

    global helper_server_proc
    helper_server_proc = subprocess.Popen(['python', './mpi_helper_server.py'])

    time.sleep(1)  # give the mpi helper time to get going... might crash with port in use

    status = check_mpi_helper_server(helper_server_proc)
    if status is not None:
        print('driver: mpi helper server exited immediately with status', status, file=sys.stderr)
        raise ValueError('cannot continue without mpi_helper_server')

    # XXX add more checks, perahps in a paramsurvey.map() timer function?

    mysignal_ = functools.partial(mysignal, helper_server_proc)
    signal.signal(signal.SIGINT, mysignal_)


def end_mpi_helper_server():    
    status = check_mpi_helper_server(helper_server_proc)
    if status is not None:
        print('driver: looked at mpi_helper and it had already exited with status', str(status), file=sys.stderr)
    else:
        print('driver: mpi_helper has not exited already, tearing it down', file=sys.stderr)
        tear_down_mpi_helper_server(helper_server_proc)


def check_mpi_helper_server(helper_server_proc):
    # proc.communicate(timeout=1)
    # TimeoutExpired: -- continue
    # outs, errs = proc.communicate() *if* user specified kwargs, else None, None
    # finally the status is in .poll()
    # to imitate subprocess.run return a subprocess.CompletedProcess object
    # (args, returncode, stdout, stderr, check_returncode)
    return helper_server_proc.poll()


def run_mpi(cmd, **kwargs):
    if 'capture_output' in kwargs:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE
        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'
    return subprocess.Popen(cmd, **kwargs)


def check_mpi(proc):
    try:
        outs, errs = proc.communicate(timeout=0.01)
        print('outs', outs)
        print('errs', errs)
    except subprocess.TimeoutExpired:
        pass
    return proc.poll()


def finish_mpi(proc):
    '''We might be called right after sending a SIGINT to the mpi proc'''
    returncode = proc.poll()
    outs, errs = proc.communicate()

    count = 0
    while returncode is None:
        time.sleep(1.0)
        returncode = proc.poll()
        outs, errs = proc.communicate()
        count += 1
        if count > 10:
            proc.send_signal(signal.SIGKILL)
            break

    return subprocess.CompletedProcess(args=None, returncode=returncode, stdout=outs, stderr=errs)
