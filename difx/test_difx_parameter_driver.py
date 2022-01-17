import pytest

import difx_utils

def test_joblist_reader():
    lines = (
        'exper=E18C21  v2d=e18c21-1-b1.v2d  pass=e18c21-1-b1  mjd=58920.4578717  DiFX=DiFX-253  vex2difx=2.5.3  vex=.../corr_rev0/b1/e18c21-1-b1.vex.obs',
        'e18c21-1-b1_1000 58229.2493056 58229.2520833 5 0 1 6.233e+04 0  # AA AX LM MG SZ'
    )

    psets = []
    dedup = set()

    psets = difx_utils.parse_difx_joblist(lines, dedup)
    assert len(psets) == 1
    assert len(psets[0]['stations']) == 5
    assert len(dedup) == 1

    with pytest.raises(ValueError):
        # since dedup starts with this job present, it will be a duplicate
        psets = difx_utils.parse_difx_joblist(lines, dedup)
