#!/usr/bin/env python3
"""Regression test of tools/assemble.combine on archived fresh-campaign records (no native binary needed).

The arrays are built exactly as the archived reference/code/analyze.py load() builds them for fresh tags: loops 3-5
use 'batches'; loop 6 sums 'graph_batches' over graphs outside the ten primitives, whose counts must be zero. In
retained mode the new assembly must reproduce the archived fresh-only and per-campaign results.
"""
from __future__ import annotations
import json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from assemble import combine,verified_inputs
from prepare_inputs import PIDS
REL=1e-12

def arrays(tag):
    out={}
    for L in range(3,7):
        raw=json.load(open(ROOT/f'reference/records/{tag}_d2_L{L}.json'))
        if L<6:out[L]=np.array(raw['batches'],float);continue
        ids=raw['graph_ids'];counts=raw['counts_per_replicate']
        if any(n for g,n in zip(ids,counts)if g in PIDS):raise AssertionError(f'{tag}: primitive graphs were integrated')
        sel=np.array([g not in PIDS for g in ids]);out[L]=np.array(raw['graph_batches'],float)[:,sel,:].sum(1)
    return out

def close(a,b,what):
    if not math.isclose(a,b,rel_tol=REL,abs_tol=0):raise AssertionError(f'{what}: {a!r} vs archived {b!r}')
    return abs(a-b)/abs(b)if b else abs(a)

def run():
    vi=verified_inputs();expected=json.load(open(ROOT/'reference/verification/method_precision_results.json'))['2']
    ar={'a':arrays('new_a'),'b':arrays('new_b')}
    res=combine(ar,{'a':.5,'b':.5},'retained',vi['B2'],vi['primitive_reference'],bootstrap=0)
    fresh=expected['fresh_only'];worst=0
    worst=max(worst,close(res['C6'],fresh['C6'],'fresh_only C6'),close(res['sampling_standard_error'],fresh['sampling_standard_error'],'fresh_only SE'))
    for i,(x,y)in enumerate(zip(res['coefficients'],fresh['coefficients'])):
        if i>=2:worst=max(worst,close(x,y,f'fresh_only coefficient {i}'))
        elif x!=y:raise AssertionError(f'fresh_only coefficient {i}: {x!r} vs {y!r}')
    for t,tag in (('a','new_a'),('b','new_b')):
        arch=expected['fresh_campaigns'][tag];new=res['campaigns'][t]
        worst=max(worst,close(new['C6'],arch['C6'],f'{tag} C6'),close(new['sampling_se'],arch['sampling_standard_error'],f'{tag} SE'))
    return {'status':'passed','test':'archived_assembly','C6':res['C6'],'sampling_standard_error':res['sampling_standard_error'],'archived_fresh_only':[fresh['C6'],fresh['sampling_standard_error']],
            'max_relative_difference':worst,'relative_tolerance':REL}
if __name__=='__main__':print(json.dumps(run(),indent=2))
