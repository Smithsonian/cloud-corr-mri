import requests
import json
import os
import os.path
import socket

url = "http://localhost:8889/jsonrpc"
pid = os.getpid()
ip = socket.gethostbyname('localhost')


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


def leader_checkin(cores, wanted_cores, pubkey):
    payload = {
        'method': 'leader_checkin',
        'params': [ip, cores, pid, wanted_cores, pubkey],
        'jsonrpc': '2.0',
        'id': 0,
    }
    response = requests.post(url, json=payload).json()
    return response


def follower_checkin(cores):
    payload = {
        'method': 'follower_checkin',
        'params': [ip, cores, pid],
        'jsonrpc': '2.0',
        'id': 0,
    }
    response = requests.post(url, json=payload).json()
    return response
