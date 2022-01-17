from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# invisible requirement: "pip install cryptography"
# invisible requirement: "pip install paramiko"

ComputeEngine = get_driver(Provider.GCE)

gce_project = 'eht-cloud'
datacenter='us-central1-c'

# https://libcloud.readthedocs.io/en/stable/compute/drivers/gce.html

# 3 auth methods

# service account -- good for limited perms
# https://console.cloud.google.com/ and pick a project or create a new one
# IAM & Admin -> Serice Accounts -> Create service account
# pick json for the private key, and download
# service account id looks like an email
# also need project id

#my_service_id = 'ray-autoscaler-sa-v1@eht-cloud.iam.gserviceaccount.com'
#my_pem_file = 'eht-cloud-b038a415dc0d.json'  # created Jan 16 2022, in home-desktop/Download
#
#driver = ComputeEngine(my_service_id, my_pem_file,
#                       project=gce_project,
#                       datacenter=datacenter)

# installed application -- good for code run by multiple users
# open G Cloud Console and select project
# click APIs & Auth on the left sidebar ** Actually APIs and Service -> Credentials
# +Create Credentials (at top)
# Installed Application -> Other -> Create Client ID
# save the Client ID and Client secret
# also need the Project ID 

#??? got an api key AIzaSyDdxLaq6NDTL_WA7r_5u2-emeKJnw8Odvo but there is no secret so that's not right

# oath key

# greg client test 1
# client_secret_1095685359415-to7ka253ii873kf8pfhgho6nhourbch9.apps.googleusercontent.com.json  # in home-desktop/Download

#import json
#
#with open('client_secret_1095685359415-to7ka253ii873kf8pfhgho6nhourbch9.apps.googleusercontent.com.json') as config_fd:
#    j = json.load(config_fd)
#    client_id = j['installed']['client_id']
#    client_secret = j['installed']['client_secret']

#driver = ComputeEngine(client_id, client_secret,
#                       datacenter=datacenter,
#                       project=gce_project)

# internal metadata service -- only if running inside of gce
# Only needs Project ID
# this works from eht-cloud, maybe it wouldn't from other instances?
driver = ComputeEngine('', '', project=gce_project,
                       datacenter=datacenter)


# retrieve available images and sizes
images = driver.list_images()
# [<NodeImage: id=3, name=Gentoo 2008.0, driver=Rackspace  ...>, ...]

sizes = driver.list_sizes()
# [<NodeSize: id=1, name=256 server, ram=256 ... driver=Rackspace ...>, ...]
    # id=, name=, ram=, disk=, bandwidth=, price=, driver=, ...

image = [i for i in images if i.name == 'ubuntu-1804-bionic-v20220111'][0]  # updated from example
size = [s for s in sizes if s.name == 'e2-micro'][0]  # same as example

print('image', str(image))
print('size', str(size))

# generic example
# https://libcloud.readthedocs.io/en/stable/compute/examples.html
node = driver.create_node(name='libcloud-test-greg2', image=image, size=size)
# <Node: uuid=..., name=test, state=3, public_ip=['1.1.1.1'],
#   provider=Rackspace ...>
print('Node:', str(node))

exit(0)

# gce example

#from libcloud.compute.deployment import ScriptDeployment
#step = ScriptDeployment("echo whoami ; date ; ls -la")

# XXX NotImplementedError: deploy_node not implemented for this driver
# deploy_node takes the same base keyword arguments as create_node.
#node = driver.deploy_node(name='libcloud-deploy-greg-1', image=image,
#                          size=size,  #ex_metadata=metadata,
#                          deploy=step)  #, ssh_key=PRIVATE_SSH_KEY_PATH)
#
#print('')
#print('Node: %s' % (node))
#print('')
#print('stdout: %s' % (step.stdout))
#print('stderr: %s' % (step.stderr))
#print('exit_code: %s' % (step.exit_status))



