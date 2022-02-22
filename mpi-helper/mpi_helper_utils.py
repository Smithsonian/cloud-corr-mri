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
    print('  schedule: wanted {} cores in addition to leader cores {}'.format(wanted_cores, l['cores']))
    is_reschedule = False
    if l.get('fkeys'):
        is_reschedule = True
        wanted_cores -= sum(followers[f]['cores'] for f in l['fkeys'])
        print('  reschedule, after existing follower cores we still want', wanted_cores)

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


def leader_checkin(ip, cores, pid, wanted_cores, pubkey, remotestate, lseq_new):
    lkey = key(ip, pid)
    print('leader checkin {}, wanted: {}, lseq_new: {}'.format(lkey, wanted_cores, lseq_new))
    # leader states: waiting -> scheduled -> running or nuked (all scheduled, or timeout)
    
    if lkey in followers:
        # well, this job might or might not have finished... so all we can do is:
        print('leader checkin used key of an existing follower')
        del followers[lkey]

    l = leaders[lkey]
    l['t'] = time.time()
    state = l.get('state')
    print('GREG old', l.get('lseq'), 'new', lseq_new)

    if l.get('lseq') != lseq_new:
        print('  leader sequence different, old: {}, new: {}, old-state: {}'.format(l.get('lseq'), lseq_new, state))
        # this leader is not the same one as in the table...
        if state == 'scheduled' or state == 'running':
            print('  changing state from {} to None'.format(state))
            state = None
            # this job must have finished, one way or another
            # just throw this info away, followers will check back in for new work anyway
            if 'fkeys' in l:
                del l['fkeys']
        elif 'lseq' in l:
            # don't print this if the leader is brand new
            print('  new state is', state)

    try_to_schedule = False
    if state == 'scheduled':
        print('  leader is already scheduled')
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
            print('  not all followers still exist, so triggering a new schedule')
            try_to_schedule = True
            l['fkeys'] = valid_fkeys
    else:
        # if state is None, this is a new-to-us leader
        # if it's waiting, we overwrite with identical information
        print('  overwriting leader state')
        l['state'] = 'waiting'
        l['cores'] = cores
        l['wanted_cores'] = int(wanted_cores)
        l['lseq'] = lseq_new
        l['pubkey'] = pubkey
        l['jobnumber'] = None
        try_to_schedule = True

    if try_to_schedule:
        print('  before schedule:', l)
        schedule(lkey, l)
        print('  after schedule:', l)
    else:
        print('  have an existing schedule with {} followers'.format(len(l['fkeys'])))

    # return schedule or watever

    if l['state'] == 'scheduled':
        print('  returning a schedule with {} followers'.format(len(l['fkeys'])))
        return make_leader_return(l)
    else:
        print('  did not schedule')


def follower_checkin(ip, cores, pid, remotestate, fseq_new):
    k = key(ip, pid)
    print('follower checkin', k)
    # follower states: available -> assigned -> working
    # remote follower states: available, assigned

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

    if f.get('fseq') != fseq_new:
        print('  follower sequence different old: {} new: {}  old-state: {}'.format(f.get('fseq'), fseq_new, state))
        if state == 'assigned':
            print('  setting state to None')
            state = None
        elif 'fseq' in f:  # don't print this if the follower is brand new
            print('  keeping state', state)
            pass

    f['fseq'] = fseq_new

    if state == 'assigned' and remotestate == 'available':
        f['state'] = 'working'
        print('  returning a schedule to the follower')
        return {'leader': f['leader'], 'pubkey': f['pubkey']}

    if f.get('state') == 'working':
        del f['leader']
        del f['pubkey']
    f['state'] = 'available'
    f['cores'] = cores
