import os.path
import stat

import mpi_helper_client


def test_pubkey(fs):  # pyfakefs
    pubfile = os.path.expanduser('~/.ssh/id_rsa.pub')
    fs.create_file(pubfile)

    fake = 'a fake public key\n'
    with open(pubfile, 'w') as f:
        f.write(fake)
    assert mpi_helper_client.get_pubkey() == fake

    keyfile = os.path.expanduser('~/.ssh/authorized_keys')
    mpi_helper_client.deploy_pubkey(fake)
    assert os.path.exists(keyfile)
    assert stat.filemode(os.stat(keyfile).st_mode) == '-rw-------'
    with open(keyfile) as f:
        assert f.read() == fake

    mpi_helper_client.deploy_pubkey(fake)
    assert stat.filemode(os.stat(keyfile).st_mode) == '-rw-------'
    with open(keyfile) as f:
        assert f.read() == fake  # make sure it doesn't write twice
