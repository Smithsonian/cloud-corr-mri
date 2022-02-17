import time

import mpi_helper_client


pubkey = mpi_helper_client.get_pubkey()


while True:
    ret = mpi_helper_client.leader_checkin(0, 5, pubkey)
    if ret.get('result') is not None:
        print('leader: got', ret['result'])
    time.sleep(1.0)
