import subprocess
import shlex
import sys

import ray

ray.init(address='auto')

# copy my public key to my authorized keys, so I can ssh to myself
subprocess.run(shlex.split('cp .ssh/id_rsa.pub .ssh/authorized_keys'))

print('Getting node ips')
sys.stdio.flush()
ips = [x['NodeManagerHostname'] for x in ray.nodes()]

print('Gathering host keys')
for ip in ips:
    print(' ', ip)
    sys.stdio.flush()
    cmd = 'ssh -o StrictHostKeyChecking=no '+ip+' echo foo'
    subprocess.run(shlex.split(cmd))

# copy over my keys, whicih are already in everyone else's authorized keys (?)
print('Copying over head keys to workers')
for ip in ips:
    print(' ', ip)
    sys.stdio.flush()
    cmd = 'scp .ssh/id_rsa.pub '+ip+':.ssh'
    subprocess.run(shlex.split(cmd))
    cmd = 'scp .ssh/id_rsa '+ip+':.ssh'
    subprocess.run(shlex.split(cmd))
    cmd = 'scp .ssh/known_hosts '+ip+':.ssh'
    subprocess.run(shlex.split(cmd))

# test it out                                                                                                                                                                
print('Testing ssh one final time')
for ip in ips:
    print(' ', ip)
    sys.stdio.flush()
    cmd = 'ssh '+ip+' echo foo'
    subprocess.run(shlex.split(cmd))
