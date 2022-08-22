import subprocess
import shlex
import sys

import ray

ray.init(address='auto')

# ray_bootstrap_key.pem is a private key that's in authorized_keys on all the workers
# the master node doesn't know that private key, so I need to use the key .ssh/id_rsa
# which was made by my ray setup

print('Configuring head authorized keys')
sys.stdout.flush()
subprocess.run(shlex.split('bash -c "cat .ssh/id_rsa.pub >> .ssh/authorized_keys"'))

print('Getting node ips')
sys.stdout.flush()
ips = [x['NodeManagerHostname'] for x in ray.nodes()]

print('Gathering host keys')
for ip in ips:
    print(' ', ip)
    sys.stdout.flush()
    cmd = 'ssh -i ~/.ssh/id_rsa -i ~/ray_bootstrap_key.pem -o StrictHostKeyChecking=no '+ip+' echo foo'
    subprocess.run(shlex.split(cmd))

# copy over head identity that I made
print('Copying over head keys to workers')
for ip in ips:
    print(' ', ip)
    sys.stdout.flush()
    cmd = 'scp -i ~/.ssh/id_rsa -i ~/ray_bootstrap_key.pem .ssh/id_rsa.pub '+ip+':.ssh'
    subprocess.run(shlex.split(cmd))
    cmd = 'ssh -i ~/.ssh/id_rsa -i ~/ray_bootstrap_key.pem '+ip+' "cat .ssh/id_rsa.pub .ssh/authorized_keys >> .ssh/new"'
    subprocess.run(shlex.split(cmd))
    cmd = 'ssh -i ~/.ssh/id_rsa -i ~/ray_bootstrap_key.pem '+ip+' mv .ssh/new .ssh/authorized_keys'
    subprocess.run(shlex.split(cmd))
    cmd = 'scp -i ~/.ssh/id_rsa -i ~/ray_bootstrap_key.pem .ssh/id_rsa '+ip+':.ssh'
    subprocess.run(shlex.split(cmd))
    cmd = 'scp -i ~/.ssh/id_rsa -i ~/ray_bootstrap_key.pem .ssh/known_hosts '+ip+':.ssh'
    subprocess.run(shlex.split(cmd))

# test it out                                                                                                                                                                
print('Testing ssh one final time')
for ip in ips:
    print(' ', ip)
    sys.stdout.flush()
    cmd = 'ssh '+ip+' echo foo'
    subprocess.run(shlex.split(cmd))
