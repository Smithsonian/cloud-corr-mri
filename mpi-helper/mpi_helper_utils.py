import time
from collections import defaultdict


leaders = defaultdict(dict)
followers = defaultdict(dict)
cache_lifetime = 30  # should be several times as long as the follower checkin time

jobnumber = 0  # used to disambiguate states


def clear():
    print('clear')
    global leaders
    global followers
    leaders = defaultdict(dict)
    followers = defaultdict(dict)


def cache_timeout():
    now = time.time()
    kills = []
    for k, v in followers.items():
        if v['t'] < now - cache_lifetime:
            kills.append(k)
    if kills:
        print('cache: timing out {} followers entries'.format(len(kills)))
    for k in kills:
        # XXX if follower was 'assigned', not 'running' or 'available', set up for a reschedule
        # we expect running followers to never check in again
        del followers[k]

    kills = []
    for k, v in leaders.items():
        if v['t'] < now - cache_lifetime:
            kills.append(k)
    if kills:
        print('cache: timing out {} leaders entries'.format(len(kills)))
    for k in kills:
        # XXX maybe do something if waiting, scheduled, but not running?
        # we expect running leaders to never check in
        del leaders[k]


def find_followers(wanted_cores):
    print('  schedule: find followers, want {} cores'.format(wanted_cores))
    fkeys = []
    for k, v in followers.items():
        if v['state'] == 'available':
            wanted_cores -= v['cores']
            fkeys.append(k)
            if wanted_cores <= 0:
                break
    if wanted_cores <= 0:
        print('  ff: did find enough cores:', ','.join(fkeys))
        return fkeys
    print('  ff: did not find enough cores')


def schedule(lkey, l):
    global jobnumber
    cache_timeout()
    wanted_cores = l['wanted_cores'] - l['cores']
    print('  schedule: wanted {} minus leader cores {}'.format(l['wanted_cores'], l['cores']))
    is_reschedule = False
    if l.get('fkeys'):
        is_reschedule = True
        wanted_cores -= sum(followers[f]['cores'] for f in l['fkeys'])

    if wanted_cores > 0:
        fkeys = find_followers(wanted_cores)
    else:
        fkeys = []

    if wanted_cores <= 0 or fkeys is not None:
        if is_reschedule:
            print('  re-scheduled jobnumber', jobnumber)
        else:
            print('  scheduled jobnumber', jobnumber)
        for f in fkeys:
            followers[f]['state'] = 'assigned'
            followers[f]['leader'] = lkey
            followers[f]['pubkey'] = l['pubkey']
            followers[f]['jobnumber'] = jobnumber  # overwritten for is_reschedule
        if is_reschedule:
            l['fkeys'].extend(fkeys)
            for f in fkeys:
                f['jobnumber'] = l['jobnumber']
        else:
            l['jobnumber'] = jobnumber
            l['fkeys'] = fkeys
            jobnumber += 1

        l['state'] = 'scheduled'
        return True
    print('  failed to schedule')


def make_leader_return(l):
    # this is the return value for the leader
    ret = []
    for f in l['fkeys']:
        ret.append({'fkey': f, 'cores': followers[f]['cores']})
    return {'followers': ret}


def key(ip, pid):
    '''makes a string key for storing state information'''
    return '_'.join((ip, str(pid)))


def leader_checkin(ip, cores, pid, wanted_cores, pubkey, remotestate, remotesequence):
    print('leader checkin, wanted:', wanted_cores)
    # leader states: waiting -> scheduled -> running or nuked (all scheduled, or timeout)
    lkey = key(ip, pid)

    if lkey in followers:
        # well, this job might or might not have finished... so all we can do is:
        print('leader checkin used key of an existing follower')
        del followers[lkey]

    l = leaders[lkey]
    l['t'] = time.time()
    state = l.get('state')

    if l.get('remotesequence') != remotesequence:
        print('  leader sequence different, old: {}, new: {}, old-state: {}'.format(l.get('remotesequence'), remotesequence, state))
        # this leader is not the same one as in the table...
        if state == 'scheduled' or state == 'running':
            print('  setting state to None')
            # and so this job must have finished, one way or another
            # XXX what to do about followers? if 'scheduled'
            # if scheduled and if this jobnumber, then unschedule them
            state = None
        elif 'remotesequence' in l:
            # don't print this if the leader is brand new
            print('  new state is', state)

    try_to_schedule = False
    if state == 'scheduled':
        valid_fkeys = []
        for f in l['fkeys']:
            if f not in followers:
                pass
            elif followers[f]['state'] != 'assigned':
                # for example, follower timed out and then checked in
                pass
            elif followers[f]['jobnumber'] != l['jobnumber']:
                # for example, follower timed out, checked in, was assigned to some other job
                pass
            else:
                valid_fkeys.append(f)
        if len(valid_fkeys) != len(l['fkeys']):
            try_to_schedule = True
            l['fkeys'] = valid_fkeys
    elif state == 'waiting':
        try_to_schedule = True
    else:  # state is None, this is a new-to-us leader
        l['state'] = 'waiting'
        l['cores'] = cores
        l['wanted_cores'] = int(wanted_cores)
        l['remotesequence'] = remotesequence
        l['pubkey'] = pubkey
        l['jobnumber'] = None
        try_to_schedule = True

    if try_to_schedule:
        print('  before schedule:', l)
        schedule(lkey, l)
        print('  after schedule:', l)

    # return schedule or watever

    if l['state'] == 'scheduled':
        return make_leader_return(l)
    else:
        print('  did not schedule')


def follower_checkin(ip, cores, pid, remotestate, remotesequence):
    print('follower checkin')
    # follower states: available -> assigned -> nuked (timeout, etc)
    # remote follower states: sequence, available, assigned
    k = key(ip, pid)

    if k in leaders:
        # existing leader is now advertising it is a follower
        print('  existing leader {} is now advertising it is a follower'.format(k))
        fkeys = leaders[k].get('fkeys', [])
        for f in fkeys:
            if f in followers:
                # XXX need a leadersequence (jobseqeunce?) here
                # don't leave any of the fkeys in the assigned state
                print('  ... nuking follower', f)
                del followers[f]
        del leaders[k]

    f = followers[k]
    f['t'] = time.time()
    state = f.get('state')

    if f.get('remotesequence') != remotesequence:
        print('  sequence comaprison old: {} new: {}  old-state: {}'.format(f.get('remotesequence'), remotesequence, state))
        if state == 'assigned':
            print('  setting state to None')
            state = None
        elif 'remotesequence' in f:  # don't print this if the follower is brand new
            print('  keeping state', state)
            pass

    if state == 'assigned' and remotestate == 'available':
        f['state'] = 'working'
        print('  returning a schedule to the follower')
        return {'leader': f['leader'], 'pubkey': f['pubkey']}

    if f.get('state') == 'working':
        del f['leader']
        del f['pubkey']
    f['state'] = 'available'
    f['cores'] = cores
