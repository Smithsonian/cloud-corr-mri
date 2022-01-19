import os
import json

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

# GCE invisible requirements: "pip install cryptography paramiko"

ComputeEngine = get_driver(Provider.GCE)

datacenter='us-central1-c'

# https://libcloud.readthedocs.io/en/stable/compute/drivers/gce.html

# Cloud dashboard
# IAM & Admin -> Serice Accounts -> Create service account
# pick json for the private key, and download
# in this example the service account has Role Owner

def gce_service_account_driver():
    my_pem_file = 'eht-cloud-b038a415dc0d.json'  # created Jan 16 2022, in home-desktop/Download
    with open(my_pem_file) as config_fd:
        j = json.load(config_fd)
        service_id = j['client_email']    
        project_id = j['project_id']
        
    driver = ComputeEngine(service_id, my_pem_file,
                           project=project_id,
                           datacenter=datacenter)
    return driver

# installed application -- good for code run by multiple users
# open G Cloud Console and select project
# APIs and Service -> Credentials
# +Create Credentials (at top)
# Oauth Client ID

# greg client test 1
# client_secret_1095685359415-to7ka253ii873kf8pfhgho6nhourbch9.apps.googleusercontent.com.json  # in home-desktop/Download

def gce_installed_app_driver():
    with open('client_secret_1095685359415-to7ka253ii873kf8pfhgho6nhourbch9.apps.googleusercontent.com.json') as config_fd:
        j = json.load(config_fd)
        client_id = j['installed']['client_id']
        client_secret = j['installed']['client_secret']
        project_id = j['installed']['project_id']

    driver = ComputeEngine(client_id, client_secret,
                           datacenter=datacenter,
                           project=project_id)
    return driver


# internal metadata service -- only if running inside of gce
# this works from eht-cloud, maybe it wouldn't from other instances?
def gce_internal_metadata_driver():
    gce_project = 'eht-cloud'
    driver = ComputeEngine('', '', project=gce_project,
                           datacenter=datacenter)
    return driver


def do_it(driver, name):
    try:
        print('Name:', name)
        images = driver.list_images()
        # [<NodeImage: id=3, name=Gentoo 2008.0, driver=Rackspace  ...>, ...]

        sizes = driver.list_sizes()
        # [<NodeSize: id=1, name=256 server, ram=256 ... driver=Rackspace ...>, ...]

        image = [i for i in images if i.name == 'ubuntu-1804-bionic-v20220111'][0]  # updated from example
        size = [s for s in sizes if s.name == 'e2-micro'][0]  # same as example

        print('image', str(image))
        print('size', str(size))
        print('Creating...')

        # generic example
        # https://libcloud.readthedocs.io/en/stable/compute/examples.html
        node = driver.create_node(name='libcloud-test-greg-'+name, image=image, size=size)
        
        # <Node: uuid=..., name=test, state=3, public_ip=['1.1.1.1'],
        #   provider=Rackspace ...>
        print('Node:', str(node.name))

        print('Destroying...')
        node.destroy()
    except Exception as e:
        print('saw exception', str(e))


if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    print('Found a GOOGLE_APPLICATION_CREDENTIALS environment variable, ignoring it in this process.')
    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']


driver = gce_service_account_driver()
do_it(driver, 'service-account')

driver = gce_installed_app_driver()
do_it(driver, 'installed-app')

driver = gce_internal_metadata_driver()
do_it(driver, 'internal-metadata')
