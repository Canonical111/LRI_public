import json
from pathlib import Path
import numpy as np
from lri_dressed.identities import diagnose
from lri_dressed.solver import DressedSolver

ROOT=Path(__file__).resolve().parents[1]


def config(N,z,o,d,window='none',mode=None):
    return {'bath_cut':N,'nz':z,'osc':o,'delta':d,'eig_tol':3e-11,'zero_scale':1.,'resolved_backend':'tensor','ncv':28,
            'max_eig_iter':10000,'residual_tol':2e-7,'window':window,'window_mode':mode,'window_tol':1e-12 if mode else None,
            'window_maxiter':50 if mode else None}


def test_minimal_caps_report_unavailable_instead_of_failing():
    rep=diagnose({'theta':[0.,-3.]},config(2,2,12,.2),k=12)
    for name in ('sigma','shadow','epsilon'):
        e=rep['descendants'][name]
        assert e.get('status')=='unavailable' or e['level1']['status'] in ('ok','ambiguous','unavailable')
    json.dumps(rep)


def test_identities_at_weak_coupling():
    seed=json.loads((ROOT/'inputs/N16_z24_o192_d0.20000000.json').read_text())['theta']
    for window,mode in (('none',None),('vacuum','consistent')):
        s=DressedSolver(8,8,80,window=window,window_mode=mode or 'consistent');s.set_delta(.2);row=s.solve(seed)
        rep=diagnose(row,config(8,8,80,.2,window,mode),k=10)
        sig=rep['descendants']['sigma']['level1']
        assert sig['status']=='ok' and sig['overlap']>.5 and abs(sig['violation'])<.02
        assert abs(rep['descendants']['sigma']['gap']-.2)<1e-8
        if window=='none':raw=sig['violation']
        else:assert abs(sig['violation'])<abs(raw)          # the window reduces the level-1 sigma violation
