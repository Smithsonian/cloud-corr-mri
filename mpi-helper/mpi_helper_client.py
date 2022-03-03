import requests
import os
import os.path
import socket
import subprocess

url = "http://localhost:8889/jsonrpc"


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


exception_list = []


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
        response = requests.post(url, json=payload).json()
        exception_list.clear()
    except Exception as e:
        exception_list.append(str(e))
        if len(exception_list) > 100:
            raise ValueError('too many leader_checkin exceptions ({})'.format(len(exception_list))) from e
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
        response = requests.post(url, json=payload).json()
        exception_list.clear()
    except Exception as e:
        exception_list.append(str(e))
        if len(exception_list) > 100:
            raise ValueError('too many follower_checkin exceptions ({})'.format(len(exception_list))) from e
        response = {'result': None}  # clients expect this
    return response


def run_mpi_helper():
    # We can't really use capture_output/stdin/stdout here because we have no way to repeatedly call .communicate()
    # XXX add a timer() routine to paramsurvey.map()?
    return subprocess.Popen(['python', './mpi_helper_server.py'])


def check_mpi_helper(proc):
    # proc.communicate(timeout=1)
    # TimeoutExpired: -- continue
    # outs, errs = proc.communicate() *if* user specified kwargs, else None, None
    # finally the status is in .poll()
    # to imitate subprocess.run return a subprocess.CompletedProcess object
    # (args, returncode, stdout, stderr, check_returncode)
    return proc.poll()


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
    except subprocess.TimeoutExpired:
        return proc.poll()


def finish_mpi(proc):
    outs, errs = proc.communicate()
    returncode = proc.poll()
    return subprocess.CompletedProcess(args=None, returncode=returncode, stdout=outs, stderr=errs)
