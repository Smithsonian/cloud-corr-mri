#!/usr/bin/env python

import fileinput

import sortedcontainers

fields = {
    'scandir': 8,  # band is the 9th+ chars, if present
    'daytime': 11,  # doyhhmmss
    'length': 5,
    'expno': 7,
    #$segtime[$i]   = substr($entry[11],4,6);
    'source': 13,
    'baseline': 14,  # 1c ref, 1c rem
    'pol': 17,
    'amp': 19,
    'snr': 20,
    'phase': 21,
    'sbd': 24,
    'mbd': 25,
    'drate': 27,
    'ambig': 26,
    'tphase': 37,
}


def read_v6():
    alist = {}
    scans = set()
    pols = set()
    for line in fileinput.input():
        if line.startswith('*'):
            continue  # comment
        parts = line.split()
        if len(parts) < 46:
            continue  # partial line

        element = dict((k, parts[v]) for (k, v) in fields.items())

        for k, v in element.items():
            if k in ('phase', 'tphase'):
                element[k] = float(v)

        first, second = element['baseline']  # 2 charactdrs
        if second < first:
            # backwards. rename and invert phases.
            element['baseline'] = second+first
            element['phase'] = - element['phase'] + 360.
            element['tphase'] = - element['tphase'] + 360.

        name = element['scandir'] + ' ' + element['baseline'] + ' ' + element['pol']
        alist[name] = element
        scans.add(element['scandir'])
        pols.add(element['pol'])

        print(name, element['phase'], element['tphase'])

    return alist, scans, pols


def find_triangles(alist):
    baselines = set()
    for k, v in alist.items():
        baselines.add(v['baseline'])

    stations = set()
    for b in baselines:
        stations.add(b[0])
        stations.add(b[1])

    stations = sortedcontainers.SortedSet(stations)
    triangles = []

    for s1 in stations:
        for s2 in stations:
            if s2 <= s1:
                continue
            for s3 in stations:
                if s3 <= s1 or s3 <= s2:
                    continue
                triangles.append((s1, s2, s3))
    return triangles


def compute_closure_phases(alist, triangles, scans, pols):
    for s in scans:
        for p in pols:
            for t in triangles:
                # all 3 baselines must be present in this scan and pol
                baselines = (t[0]+t[1], t[1]+t[2], t[0]+t[2])
                names = [s + ' ' + b + ' ' + p for b in baselines]
                if not all(name in alist for name in names):
                    #print('missing a baseline for scan {} pol {} baseline {}'.format(s, p, t))
                    # this is expected for all Alma baselines if polconvert is not run
                    continue
                cphase = (alist[names[0]]['phase'] +
                          alist[names[1]]['phase'] -
                          alist[names[2]]['phase'])  # 3rd baseline is inverted
                if cphase > 360.:
                    cphase -= 360.
                if cphase < 0.:
                    cphase += 360.
                print('scan {} pol {} triangle {} closure_phase {}'.format(
                    s, p, t, cphase)
                )

                ctphase = (alist[names[0]]['tphase'] +
                           alist[names[1]]['tphase'] -
                           alist[names[2]]['tphase'])  # 3rd baseline is inverted
                if ctphase > 360.:
                    ctphase -= 360.
                if ctphase < 0.:
                    ctphase += 360.
                print('scan {} pol {} triangle {} closure_tphase {}'.format(
                    s, p, t, ctphase)
                )


alist, scans, pols = read_v6()
triangles = find_triangles(alist)
closures = compute_closure_phases(alist, triangles, scans, pols)
