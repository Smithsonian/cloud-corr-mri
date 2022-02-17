import time

import mpi_helper_client


while True:
    ret = mpi_helper_client.follower_checkin(5)
    if ret.get('result') is not None:
        print('follower: got', ret['result'])
    time.sleep(1.0)
