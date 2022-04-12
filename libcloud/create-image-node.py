import os
import json

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


ComputeEngine = get_driver(Provider.GCE)
datacenter='us-central1-c'


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


def do_it(driver, name):
    try:
        print('Name:', name)
        images = driver.list_images()
        print('found {} images'.format(len(images)))
        # [<NodeImage: id=3, name=Gentoo 2008.0, driver=Rackspace  ...>, ...]

        sizes = driver.list_sizes()
        print('found {} sizes'.format(len(sizes)))
        # [<NodeSize: id=1, name=256 server, ram=256 ... driver=Rackspace ...>, ...]

        for i in images:
            if i.name.startswith('ubuntu-1804'):
                print(i.name)
                # last matching image wins
                image = i
        #image = [i for i in images if i.name == 'ubuntu-1804-bionic-v20220111'][0]  # updated from example
        size = [s for s in sizes if s.name == 'e2-medium'][0]  # 2 vcpu, 4 gigs

        print('image', str(image))
        print('size', str(size))
        print('Creating...')

        # generic example
        # https://libcloud.readthedocs.io/en/stable/compute/examples.html
        node = driver.create_node(name='libcloud-test-greg-'+name, image=image, size=size)
        print('Created Node:', str(node.name))
    except:
        raise
        

if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    print('Found a GOOGLE_APPLICATION_CREDENTIALS environment variable, ignoring it in this process.')
    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']


driver = gce_service_account_driver()
do_it(driver, 'service-account')
