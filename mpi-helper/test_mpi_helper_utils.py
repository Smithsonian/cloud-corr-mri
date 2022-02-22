from functools import partial

from mpi_helper_utils import leader_checkin, follower_checkin, clear


# mock time.time()
# @mock.patch('time.time', mock.MagicMock(return_value=12345))
# make jobnumber visible and check it

def test_onlyleader():
    seq = 0

    l = partial(leader_checkin, 'localhost', 1, 100, 1, '', 'waiting')
    ret = l(seq)
    assert len(ret['followers']) == 0, 'leader has enough cores, schedules immediately'

    seq += 1
    l = partial(leader_checkin, 'localhost', 1, 100, 2, '', 'waiting')
    for _ in range(10):
        ret = l(seq)
        assert not ret, 'leader has too few cores to schedule ever'


def test_leadfollow():
    lseq = 0
    fseq = 0

    l = partial(leader_checkin, 'localhost', 1, 100, 3, '', 'waiting')
    f = partial(follower_checkin, 'localhost', 1, 101, 'available')

    print('\nleadfollow too few to ever start')
    ret = l(lseq)
    assert not ret
    ret = f(fseq)
    assert not ret, 'leadfollow not enough cores to ever start'

    print('\nleadfollow enough cores to start f l f')
    fseq += 1
    f = partial(follower_checkin, 'localhost', 2, 101, 'available')
    ret = f(fseq)
    assert not ret, 'leadfollow leader must check in before scheduled'
    ret = l(lseq)
    assert len(ret['followers']) != 0, 'leadfollow leader should schedule'
    ret = f(fseq)
    assert ret, 'follower is scheduled'
    assert 'leader' in ret, 'leadfollow follower receives schedule'
    assert 'pubkey' in ret, 'leadfollow follower receives schedule'

    print('\nleadfollow enough cores to start l f l f')
    lseq += 1
    fseq += 1
    ret = l(lseq)
    assert not ret
    ret = f(fseq)
    assert not ret
    ret = l(lseq)
    assert ret['followers'], 'leader sees job has scheduled'
    ret = f(fseq)
    assert ret, 'follower sees job has scheduled'
    assert 'leader' in ret
    assert 'pubkey' in ret

# l, f, l (success), f (success)
# l, f, l (success), f2 (fail), f2 (success?) or maybe l, f2
# f, l, f2, l (success), f2 (success)
# f, l (success), l2 (success), f (success)
# f1, f2, l, ...

# could have scheduled but for a timeout
# scheduled and then timeout before follower checks in again
# shduled, timeout f, then f2 gets scheudled instead

# successful schedule but one follower never checks in again (cache timeout)
# f, l, timeout, f, l (success)

# successful schedule but one follower restarts before picking up
# successful schedule but leader reboots
# successful schedule but leader becomes follower
# successful schedule but follower becomes leader


# state table exploration
# create a couple of leaders, followers, both have a % chance of restarting
# do a couple of work units
# make sure it finishes
# count how many calls
# should rise as %restart increases
