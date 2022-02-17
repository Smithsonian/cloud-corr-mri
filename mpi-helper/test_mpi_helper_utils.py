from mpi_helper_utils import leader_checkin, follower_checkin


# mock time.time()
# @mock.patch('time.time', mock.MagicMock(return_value=12345))
# make jobnumber visible and check it

def test_onlyleader():
    leader_sequence = 0

    ret = leader_checkin('localhost', 1, 100, 1, '', 'waiting', leader_sequence)
    assert len(ret['followers']) == 0, 'leader has enough cores, schedules immediately'

    leader_sequence += 1
    for _ in range(10):
        ret = leader_checkin('localhost', 1, 100, 2, '', 'waiting', leader_sequence)
        assert not ret, 'leader has too few cores to schedule ever'


def test_leadfollow():


    pass
# too few: f, l, ... never succeeding
# f, l (success), f (success)
# l, f, l (success), f (success)
# l, f, l (success), f2 (fail), f2 (success?) or maybe l, f2
# f, l, f2, l (success), f2 (success)
# f, l (success), l2 (success), f (success)
# f1, f2, l, ...

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
