import subprocess
import shlex

import ray

ray.init(address='auto')

#ips = [x['NodeName'] for x in ray.nodes()]
ips = [x['NodeManagerHostname'] for x in ray.nodes()]

# copy my public key to my authorized keys                                                                                                                                   
subprocess.run(shlex.split('cp .ssh/id_rsa.pub .ssh/authorized_keys'))

# gather host keys                                                                                                                                                           
for ip in ips:
    cmd = 'ssh -o StrictHostKeyChecking=no '+ip+' echo foo'
    subprocess.run(shlex.split(cmd))

# copy over my keys, whicih are already in everyone else's authorized keys                                                                                                   
for ip in ips:
    cmd = 'scp .ssh/id_rsa.pub '+ip+':.ssh'
    subprocess.run(shlex.split(cmd))
    cmd = 'scp .ssh/id_rsa '+ip+':.ssh'
    subprocess.run(shlex.split(cmd))
    cmd = 'scp .ssh/known_hosts '+ip+':.ssh'
    subprocess.run(shlex.split(cmd))

# test it out                                                                                                                                                                
for ip in ips:
    cmd = 'ssh '+ip+' echo foo'
    subprocess.run(shlex.split(cmd))
