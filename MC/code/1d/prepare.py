#!/usr/bin/env python3
"""Prepare immutable tasks and full periodic-image couplings, once on the login node."""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np
from scipy.special import zeta

# Seeds for temperature SEARCHES, not independently established critical temperatures.
# Values are the earlier campaign's baseline fit centers; s=.9 was unstable.
OLD_CENTERS = {0.6: .28178355, 0.654533: .31319468, 0.7: .34123074,
               0.8: .41105589, 0.875: .47489462, 0.9: .49948291, 0.95: .55915547}

def couplings(n: int, s: float) -> np.ndarray:
    if n < 2 or n & (n-1) or not (0 < s):
        raise ValueError('N must be a power of two >= 2 and s must be positive')
    r = np.arange(1, n//2+1, dtype=np.float64)
    half = (zeta(1+s, r/n)+zeta(1+s, 1-r/n)) / float(n)**(1+s)
    j = np.zeros(n, dtype='<f8')
    j[1:n//2+1] = half
    j[n//2+1:] = half[:-1][::-1]
    exact_sum = 2*zeta(1+s, 1)*(1-float(n)**(-1-s))
    if not np.all(np.isfinite(j)) or not np.all(j[1:] > 0):
        raise ArithmeticError('invalid couplings')
    if not np.isclose(j.sum(), exact_sum, rtol=4e-13, atol=0):
        raise ArithmeticError('periodic coupling sum-rule check failed')
    return j

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--s', type=float, nargs='+', default=[.8, .875, .9])
    p.add_argument('--sizes', type=int, nargs='+', default=[2**k for k in range(10,19)])
    p.add_argument('--replicas', type=int, default=8)
    p.add_argument('--measurements', type=int, default=1000000)
    p.add_argument('--warmup', type=int, default=50000)
    p.add_argument('--beta-points', type=int, default=3)
    p.add_argument('--beta-halfwidth', type=float, default=.002)
    p.add_argument('--window-exponent', type=float, default=.4,
                   help='search width ~ (N/1024)^(-p); a sampling heuristic, not a fitted prior')
    p.add_argument('--centers', type=Path, help='CSV columns s,N,beta; blank N applies to all sizes')
    p.add_argument('--seed-base', type=int, default=20260914)
    p.add_argument('--seed-namespace', default='', help='campaign identity mixed into every chain seed (FIT_MODEL_V3 §4.7; '
                   'required for every new campaign that may coincide with an existing one in (s, N, beta); empty = legacy key)')
    p.add_argument('--engine', choices=['v1', '1d'], default='v1', help="simulator: 'v1' = bin/lri_mc (coupling-table code of the scan), "
                   "'1d' = bin/lri_mc_1d (1D-specialised backbone sampler of lri_1d_precision, 2026-09-18; same Hamiltonian, same 4-column record)")
    args = p.parse_args()
    if args.out.exists():
        raise SystemExit('Output directory already exists; use a new campaign directory. Restarts use run_task.py.')
    if (not all(.5 < s < 1 for s in args.s) or not args.s or not args.sizes
            or any(n < 2 or n > 2**28 or n & (n-1) for n in args.sizes)):
        raise SystemExit('Require 1/2 < s < 1 and power-of-two sizes in [2,2^28]')
    if min(args.replicas,args.measurements,args.beta_points) < 1 or args.warmup < 0 or args.beta_halfwidth < 0:
        raise SystemExit('invalid counts or beta width')
    if args.beta_points > 1 and args.beta_halfwidth == 0:
        raise SystemExit('multiple beta points require a positive halfwidth')
    if not math.isfinite(args.beta_halfwidth) or not math.isfinite(args.window_exponent):
        raise SystemExit('width and exponent must be finite')
    overrides = {}
    if args.centers:
        for row in csv.DictReader(args.centers.open()):
            key=(float(row['s']), int(row['N']) if row.get('N','').strip() else None)
            if key in overrides: raise SystemExit(f'duplicate center: {key}')
            overrides[key]=float(row['beta'])
    plan=[]
    for n in sorted(set(args.sizes)):
        for s in sorted(set(args.s)):
            if args.centers and (s,n) not in overrides and (s,None) not in overrides:
                raise SystemExit(f'centers file has no entry for s={s}, N={n}; do not silently reuse an old center')
            b0=overrides.get((s,n), overrides.get((s,None), OLD_CENTERS.get(s)))
            if b0 is None or not math.isfinite(b0) or b0 <= 0:
                raise SystemExit(f'provide a valid beta center for s={s}, N={n}')
            width=args.beta_halfwidth*(n/1024)**(-args.window_exponent)
            offsets=np.linspace(-width,width,args.beta_points) if args.beta_points>1 else [0.]
            for ib,offset in enumerate(offsets):
                beta=float(b0+offset)
                if beta<=0: raise SystemExit('temperature grid contains beta <= 0')
                for rep in range(args.replicas):
                    # Deterministic distinct streams by full-precision coordinates, not job IDs.
                    key=f'{args.seed_base}|{s.hex()}|{n}|{beta.hex()}|{rep}' if not args.seed_namespace else f'{args.seed_base}|{args.seed_namespace}|{s.hex()}|{n}|{beta.hex()}|{rep}'
                    seed=int.from_bytes(hashlib.blake2b(key.encode(),digest_size=8).digest(),'little')
                    plan.append(dict(id=len(plan),s=s,Delta_sigma=(1-s)/2,N=n,beta=beta,
                        beta_center=b0,beta_index=ib,replica=rep,seed=seed,
                        initialization='hot' if rep%2==0 else 'cold',
                        measurements=args.measurements,warmup=args.warmup,engine=args.engine))
    if len({t['seed'] for t in plan}) != len(plan): raise RuntimeError('seed collision')
    args.out.mkdir(parents=True)
    (args.out/'couplings').mkdir(); (args.out/'chains').mkdir(); (args.out/'logs').mkdir()
    pairs={}
    for t in plan:
        pair=(t['s'],t['N'])
        if pair not in pairs:
            name=f'couplings/J_{len(pairs):04d}.bin'; j=couplings(t['N'],t['s']); j.tofile(args.out/name)
            pairs[pair]=(name,hashlib.sha256((args.out/name).read_bytes()).hexdigest())
        t['coupling_file'],t['coupling_sha256']=pairs[pair]
        t['directory']=f"chains/{t['id']:06d}"
        d=args.out/t['directory']; d.mkdir(); (d/'task.json').write_text(json.dumps(t,indent=2)+'\n')
    config={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()}
    manifest=dict(format_version=1,model='1D ferromagnetic Ising; full periodic-image couplings',engine=args.engine,
                  notes='Beta centers are exploratory, not critical-temperature constraints. Hot/cold starts alternate.',
                  config=config,tasks=plan)
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    fields=['id','s','Delta_sigma','N','beta','replica','seed','initialization','measurements','warmup']
    with (args.out/'tasks.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(plan)
    total=sum(t['measurements'] for t in plan); work=sum(t['N']*(t['measurements']+t['warmup']) for t in plan)
    report=dict(tasks=len(plan),measurement_sweeps=total,raw_output_GiB=32*total/2**30,
                spin_sweep_work=work,production_memory_bytes_approx=24*max(args.sizes),
                message='Storage is raw measurements only. Benchmark actual node throughput before full allocation.')
    (args.out/'plan.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
