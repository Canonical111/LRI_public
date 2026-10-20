#!/usr/bin/env python3
"""Lossless integer-K block sufficient statistics for temperature reweighting.

Does not remove raw trajectories. Sparse arrays are compressed with np.savez.
Only completed extended-format chains are accepted by this production path.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from analyze import tau_int

def pack_chain(directory:Path,block:int,out:Path):
    status=json.loads((directory/'DONE.json').read_text());n=status['measurements_done']
    columns=status.get('record_columns',4)
    if columns!=8:raise ValueError('multihistogram U6/U8 analysis requires --record extended (8 columns)')
    raw=directory/'samples.bin'
    if raw.stat().st_size!=n*columns*8:raise ValueError('raw length differs from committed DONE count')
    a=np.memmap(raw,dtype='<f8',mode='r',shape=(n,columns));B=n//block
    if B<20:raise ValueError(f'{directory}: fewer than 20 complete blocks')
    ptr=[0];keys=[];counts=[];sums=[];bm=[]
    for i in range(B):
        x=np.asarray(a[i*block:(i+1)*block]);k=x[:,0]
        if np.any(k!=np.floor(k)) or np.any(k<0):raise ValueError('K is not a nonnegative integer')
        kk,inv,c=np.unique(k.astype(np.int64),return_inverse=True,return_counts=True)
        sums.append(np.stack([np.bincount(inv,weights=x[:,j],minlength=len(kk)) for j in (1,2,4,5)],axis=1))
        keys.append(kk);counts.append(c.astype(np.int32));ptr.append(ptr[-1]+len(kk));bm.append(x[:,1].mean())
    prefix=np.asarray(a[:min(n,262144)]);K=prefix[:,0];M=prefix[:,1];Q=K-K.mean()
    feats=np.column_stack([M,prefix[:,2],Q,M*Q,prefix[:,2]*Q]);mean=feats.mean(0)
    def slope(f):
        a2,a4,q,a2q,a4q=f;d2=a2q-a2*q;d4=a4q-a4*q
        return -(d4/a2**2-2*a4*d2/a2**3)/(3*status['beta'])
    grad=np.array([np.imag(slope(mean.astype(complex)+1j*1e-25*np.eye(5)[i]))/1e-25 for i in range(5)])
    score=(feats-mean)@grad
    taus={k:tau_int(v) for k,v in [('K',K),('m2',M),('dm2_score',(M-M.mean())*Q),('U4_slope_score',score)]}
    bm=np.array(bm);h=B//2;z=(bm[:h].mean()-bm[h:].mean())/np.sqrt(bm[:h].var(ddof=1)/h+bm[h:].var(ddof=1)/(B-h))
    h=hashlib.sha256()
    with raw.open('rb') as fr:
        for chunk in iter(lambda:fr.read(1<<24),b''):h.update(chunk)
    if not (directory/'binary.sha256').exists():raise ValueError(f'{directory}: binary.sha256 missing (chain not run through run_task.py): no binary identity')   # FIT2D-007
    bsig=(directory/'binary.sha256').read_text().strip()
    diag=dict(measurements=n,used=B*block,block=block,blocks=B,discarded=n-B*block,raw_sha256=h.hexdigest(),binary_sha256=bsig,initialization_status=status.get('init'),
              K_stdev=float(K.std(ddof=1)),rng=status.get('rng'),tau=taus,block_over_max_tau=block/max(taus.values()),half_drift_z=float(z),
              m2_mean=float(bm.mean()),m2_block_stderr=float(bm.std(ddof=1)/np.sqrt(B)),
              raw_bytes=raw.stat().st_size,seed=status['seed'],d=status['d'],L=status['L'],beta=status['beta'],
              sampler=status['sampler'],nn_extra=status.get('nn_extra',0),
              qualification='Stationarity/autocorrelation diagnostics are not a proof of equilibration.')
    out.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out,indptr=np.array(ptr,dtype=np.int64),K=np.concatenate(keys),counts=np.concatenate(counts),
                        sums=np.concatenate(sums),block_m2=bm,metadata=np.array(json.dumps(diag)))
    diag['packed_bytes']=out.stat().st_size;diag['packed_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()   # FIT2D-007: content hash of the packed file
    return diag

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('campaign',type=Path);p.add_argument('--block',type=int,default=2048)
    p.add_argument('--dim',type=int);p.add_argument('--s',type=float);p.add_argument('--nn-extra',type=float,default=0)
    p.add_argument('--out',type=Path);a=p.parse_args()
    if a.block<2:p.error('block >=2 required')
    mtext=(a.campaign/'manifest.json').read_bytes();mf=json.loads(mtext);out=a.out or a.campaign/f'hist_b{a.block}'
    try:out.mkdir(parents=True)   # FIT2D-008: atomic claim of a fresh output directory (no check-then-write race)
    except FileExistsError:raise SystemExit(f'{out} exists: packed histograms are immutable, use a new --out (FIT2D-008)')
    tasks=[];skipped=[]
    for t in mf['tasks']:
        if a.dim and t['d']!=a.dim:continue
        if a.s is not None and abs(t['s']-a.s)>1e-10:continue
        if abs(t.get('nn_extra',0)-a.nn_extra)>1e-12:continue
        dr=a.campaign/t['directory']
        if not (dr/'DONE.json').exists():skipped.append(t['id']);continue
        status=json.loads((dr/'DONE.json').read_text())
        for key in ('d','L','seed'):
            if status[key]!=t[key]:raise ValueError(f'{dr}: status / manifest mismatch: {key}')
        for key in ('beta','s','nn_extra'):
            if abs(status.get(key,0)-t.get(key,0))>1e-13*max(1,abs(t.get(key,0))):
                raise ValueError(f'{dr}: status / manifest mismatch: {key}')
        path=out/f'task_{t["id"]:06d}.npz';diag=pack_chain(dr,a.block,path)
        tasks.append(dict(t,histogram=path.name,diagnostics=diag));print(t['id'],json.dumps(diag),flush=True)
    index={'campaign_id':mf.get('campaign_id'),'manifest_sha256':hashlib.sha256(mtext).hexdigest(),'manifest_tasks':len(mf['tasks']),'block':a.block,'tasks':tasks,'skipped':skipped,
           'note':'Do not combine different s or nn_extra in a histogram solve. Each temperature remains a distinct state.'}
    (out/'index.json').write_text(json.dumps(index,indent=2)+'\n');print(out/'index.json')
if __name__=='__main__':main()
