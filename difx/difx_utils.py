import re
import glob


def parse_difx_joblist(lines, dedup):
    # exper=E18C21  v2d=e18c21-1-b1.v2d  pass=e18c21-1-b1  mjd=58920.4578717  DiFX=DiFX-253  vex2difx=2.5.3  vex=.../corr_rev0/b1/e18c21-1-b1.vex.obs
    #pass_ = re.search(lines[0], r' pass=([^\ ]+) ').group(1)

    ret = []

    for line in lines[1:]:
        # e18c21-1-b1_1000 58229.2493056 58229.2520833 5 0 1 6.233e+04 0  # AA AX LM MG SZ
        jobname, stations = re.match(r'([^\ ]+) .* \#\ (.+)', line, flags=re.X).group(1, 2)
        if jobname in dedup:
            raise ValueError('Duplicate jobname: '+jobname)
        dedup.add(jobname)
        ret.append({'jobname': jobname, 'stations': stations.split(' ')})

    return ret


def get_difx_joblists():
    psets = []

    # Assume we are in a top level directory, with 1 or more bands
    bands = glob.glob('b[1-4]')
    if not bands:
        raise ValueError('Expected to find bands b[1-4] in the current directory, none found')
    for b in bands:
        joblists = glob.glob('{}/*.joblist'.format(b))
        dedup = set()
        for j in joblists:
            with open(j) as fd:
                new = parse_difx_joblist(fd.read().splitlines(), dedup)
                for n in new:
                    n['band'] = b
                psets.extend(new)
    return psets


def add_costs(psets):
    'The cost of a DiFX computation is linear with the station count (FFT) if there are few enough stations'
    for p in psets:
        p['cost'] = len(p['stations'])
