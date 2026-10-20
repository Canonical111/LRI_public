#!/usr/bin/env python3
"""Regression test of tools/assemble.combine on archived d=3 campaign records (no native binary needed).

The arrays are built exactly as the archived reference/code/analyze.py load() builds them for d=3: 'batches' at every
loop, primitives included (d=3 has no retained primitive input and no offset). The new assembly must reproduce the
archived fresh-only result, both fresh campaigns, the previous production, and the four-campaign primary estimate.
"""
from __future__ import annotations
import json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from assemble import combine,verified_inputs
from prepare_inputs import PIDS
REL=1e-12
FRESH=ROOT/'reference/records';PREVIOUS=ROOT/'reference/baseline_previous/records'

def arrays(folder:Path,tag:str):
    out={}
    for L in range(3,7):
        raw=json.load(open(folder/f'{tag}_d3_L{L}.json'))
        if raw.get('dimension')!=3 or raw.get('L')!=L:raise AssertionError(f'{tag} L{L}: not a d=3 record')
        if L==6 and not all(n>0 for g,n in zip(raw['graph_ids'],raw['counts_per_replicate'])if g in PIDS):raise AssertionError(f'{tag}: primitive strata missing')
        out[L]=np.array(raw['batches'],float)
    return out

def close(a,b,what):
    if not math.isclose(a,b,rel_tol=REL,abs_tol=0):raise AssertionError(f'{what}: {a!r} vs archived {b!r}')
    return abs(a-b)/abs(b)if b else abs(a)

def check(res,arch,what,coefficients=True):
    worst=max(close(res['C6'],arch['C6'],what+' C6'),close(res['sampling_standard_error'],arch['sampling_standard_error'],what+' SE'))
    if coefficients:
        for i,(x,y)in enumerate(zip(res['coefficients'],arch['coefficients'])):
            if i>=2:worst=max(worst,close(x,y,f'{what} coefficient {i}'))
            elif x!=y:raise AssertionError(f'{what} coefficient {i}: {x!r} vs {y!r}')
    return worst

def run():
    vi=verified_inputs();expected=json.load(open(ROOT/'reference/verification/method_precision_results.json'))['3']
    ar={'new_a':arrays(FRESH,'new_a'),'new_b':arrays(FRESH,'new_b'),'prod_a':arrays(PREVIOUS,'prod_a'),'prod_b':arrays(PREVIOUS,'prod_b')}
    worst=0;out={}
    # Frozen production weighting of a new campaign: a/b = 1/2 each (this is what load_campaign enforces).
    res=combine({'a':ar['new_a'],'b':ar['new_b']},{'a':.5,'b':.5},vi['B2'],bootstrap=0)
    worst=max(worst,check(res,expected['fresh_only'],'fresh_only'));out['fresh_only']=[res['C6'],res['sampling_standard_error']]
    for t,tag in (('a','new_a'),('b','new_b')):
        arch=expected['fresh_campaigns'][tag];new=res['campaigns'][t]
        worst=max(worst,close(new['C6'],arch['C6'],f'{tag} C6'),close(new['sampling_se'],arch['sampling_standard_error'],f'{tag} SE'))
    res=combine({'a':ar['prod_a'],'b':ar['prod_b']},{'a':.5,'b':.5},vi['B2'],bootstrap=0)
    worst=max(worst,check(res,expected['previous'],'previous'));out['previous']=[res['C6'],res['sampling_standard_error']]
    # The archived four-campaign primary estimate (equal weights 1/4; explicit weights are a combine() argument only).
    res=combine(ar,{t:.25 for t in ar},vi['B2'],bootstrap=0)
    worst=max(worst,check(res,expected,'four-campaign primary'));out['four_campaign']=[res['C6'],res['sampling_standard_error']]
    return {'status':'passed','test':'archived_assembly_d3','results':out,'archived_primary':[expected['C6'],expected['sampling_standard_error']],
            'max_relative_difference':worst,'relative_tolerance':REL}
if __name__=='__main__':print(json.dumps(run(),indent=2))
