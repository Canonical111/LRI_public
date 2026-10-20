#!/usr/bin/env python3
"""Freeze the zero-pole control variates of the sampled power sector (C7 recipe, reference/code/full_assembly.py).

The negative Laurent slots of the fully subtracted RG functions vanish, so fixed linear combinations of them are
control variates. For each sampled loop L (6,7,8) the training data are the per-replicate totals of the PILOT
coarse power campaigns (degree 1; never used in the estimate): X (replicates x 16). Pole columns are scaled, an SVD
ridge regression with ridge 0.015*s0 (the archived value) predicts each target row y_r = X J_L[r] (r = 5..8), and
C[r,cols] are the fitted coefficients. The production estimator uses adjusted = J - C for power sources only, at
every refinement level (a constant matrix, so telescoping is unchanged). Output: the frozen full affine map.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from c8lib import NW,NV,pole_columns
from campaign import verify_campaign,dump
RIDGE=.015

def training(camps:list[Path],L:int)->tuple[np.ndarray,list]:
    X=[];used=[]
    for c in camps:
        r=verify_campaign(c.resolve());m=r['manifest']
        if m['mode']!='power' or m['L']!=L or m['degrees']!=[1] or m.get('selection')!='power':raise ValueError(f'{c}: training must be a degree-1 power-selection campaign at L={L}')
        d=json.loads((c/'merged'/'N1.json').read_text());X.append(np.array(d['batches'],dtype=float))
        used.append({'campaign':str(c.resolve()),'manifest_sha256':r['manifest_sha256'],'replicates':m['replicates'],'seed':int(m['seed'])}) # assembly forbids these streams
    return np.vstack(X),used

def fit(X:np.ndarray,J:np.ndarray,L:int)->tuple[np.ndarray,dict]:
    cols=pole_columns(L);Z=X[:,cols];sc=np.sqrt((Z*Z).mean(0));keep=sc>1e-12*max(sc);cols=np.array(cols)[keep];sc=sc[keep]
    z=X[:,cols]/sc;zc=z-z.mean(0);u,s,vt=np.linalg.svd(zc,full_matrices=False);ridge=RIDGE*s[0];ss=s/(s*s+ridge*ridge);C=np.zeros_like(J);diag={}
    for r in range(5,NW+1):
        y=X@J[r]
        if not np.any(y):continue
        c=vt.T@(ss*(u.T@(y-y.mean())));C[r,cols]=c/sc;res=X@(J[r]-C[r])
        diag[str(r)]={'uncontrolled_sd':float(y.std(ddof=1)),'controlled_sd_in_training':float(res.std(ddof=1)),'variance_reduction_in_training':float((y.std(ddof=1)/res.std(ddof=1))**2) if res.std(ddof=1)>0 else None}
    return C,{'pole_columns':cols.tolist(),'ridge_relative':RIDGE,'training_replicates':len(X),'training_fit':diag}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--affine',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--train',nargs='+',required=True,metavar='L=CAMPAIGN',help='pilot coarse power campaigns, e.g. 6=pilot/power_coarseA_L6')
    a=p.parse_args();aff=json.loads(a.affine.read_text());by={}
    for t in a.train:L,c=t.split('=',1);by.setdefault(int(L),[]).append(Path(c))
    loops={}
    for L in range(5,9):
        J=np.array(aff['loops'][str(L)]['J'])
        if L in by:
            X,used=training(by[L],L);C,info=fit(X,J,L);info['training']=used
        else:
            C=np.zeros_like(J);info={'note':'no control (exact deterministic loop or no training given)'}
        loops[str(L)]={'J':J.tolist(),'control':C.tolist(),'adjusted':(J-C).tolist(),**info}
    if set(by)!={6,7,8}:raise ValueError('controls must be trained for exactly the sampled loops 6,7,8')
    out={**{k:v for k,v in aff.items() if k!='loops'},'schema':'c8-full-affine-1','loops':loops,'affine_sha256':hashlib.sha256(a.affine.read_bytes()).hexdigest()}
    dump(a.out,out);print(json.dumps({L:v.get('training_fit') for L,v in loops.items()},indent=1))
if __name__=='__main__':main()
