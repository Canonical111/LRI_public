#!/usr/bin/env python3
"""Fast direct full-range scan. Numerical roots are not continuum predictions."""
import argparse,json,os,sys,hashlib,time
from pathlib import Path
from fast_response import FastDressedZero
from dressed_zero import atomic_json
GRID=[.2499,.249,.2475,.245,.24,.235,.23,.225,.22,.21,.20,.19,.18,.175,.17,.16,.15,.14,.13,.125,.12,.11,.10,.09,.08,.075,.07,.06,.05,.04,.03,.025,.02,.015,.0125,.01,.0075,.005,.003,.002,.001,.0005,.0002,.0001]

def valid(row,N,z,o,d):
    return (row.get('bath_cut')==N and row.get('nz_per_parity')==z and row.get('auxiliary_oscillator_size')==o and abs(row.get('delta',-1)-d)<1e-14 and row.get('tuning_residual',1)<1e-8 and row.get('max_eigenvector_residual',1)<2e-7)

def main():
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bath-cut',type=int,default=8);p.add_argument('--nz',type=int,default=20);p.add_argument('--osc',type=int,default=160);p.add_argument('--deltas',type=float,nargs='+');p.add_argument('--out',type=Path,default=root/'results/dressed');p.add_argument('--seed-results',type=Path);p.add_argument('--resume',action='store_true');p.add_argument('--min-delta',type=float,default=.0001);args=p.parse_args()
    grid=sorted(set(args.deltas or GRID),reverse=True)
    if any(not 0<d<.25 for d in grid):p.error('Only 0<Delta_sigma<1/4 is diagonalized; plot.py supplies separate exact endpoint markers.')
    h=FastDressedZero(args.bath_cut,args.nz,args.osc);previous=None
    source_hash=hashlib.sha256((Path(__file__).read_bytes()+(Path(__file__).parent/'dressed_zero.py').read_bytes()+(Path(__file__).parent/'fast_response.py').read_bytes())).hexdigest()
    for d in grid:
        if d<args.min_delta:continue
        path=args.out/f'N{args.bath_cut}_z{args.nz}_o{args.osc}_d{d:.8f}.json'
        if args.resume and path.exists():
            row=json.loads(path.read_text())
            if not valid(row,args.bath_cut,args.nz,args.osc,d):raise RuntimeError(f'Existing output failed validation: {path}')
            previous=row;continue
        guess=None if previous is None else previous['theta']
        if args.seed_results:
            choices=[]
            for f in args.seed_results.glob(f'N*_z*_o*_d{d:.8f}.json'):
                x=json.loads(f.read_text())
                if x.get('tuning_residual',1)<1e-8:choices.append(x)
            if choices:
                choices.sort(key=lambda x:(abs(x['bath_cut']-args.bath_cut),-x['nz_per_parity']))
                guess=choices[0]['theta']
        bridges=[]
        if guess is None and d<.23:
            # Establish the branch from the weak-coupling region, rather than
            # guessing a strong-coupling root. No thermal target enters.
            for mid in [x for x in GRID if x>d][::2]:
                h.set_delta(mid);tmp=h.solve(guess);guess=tmp['theta'];bridges.append({'delta':mid,'theta':guess,'tuning_residual':tmp['tuning_residual']})
        h.set_delta(d)
        # g->0 makes the scale-free curvature coordinate ill-conditioned.
        # The weak-coupling initial guess is more reliable than transferring
        # that coordinate across an order-of-magnitude change in epsilon.
        if 1-4*d<.04:guess=h.initial(1-4*d)
        try:
            row=h.solve(guess);row['source_sha256']=source_hash;row['continuation_bridges']=bridges
            if not valid(row,args.bath_cut,args.nz,args.osc,d):raise RuntimeError('Publication gate')
            atomic_json(path,row);previous=row
            print(args.bath_cut,args.nz,d,row['Delta_thermal'],row['seconds'],row['spectral_evaluations'],flush=True)
        except Exception as ex:
            atomic_json(path.with_suffix('.failure.json'),{'delta':d,'error':str(ex),'source_sha256':source_hash});raise
if __name__=='__main__':main()
