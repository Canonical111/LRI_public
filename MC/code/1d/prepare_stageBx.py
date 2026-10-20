#!/usr/bin/env python3
"""Prepare the N2 campaigns of one scan point (FIT_MODEL_V3.md §5.1 with the §5.0 window rule x_max = 0.35; engine '1d').

Usage (Expanse login node, anaconda3 python): prepare_stageBx.py POINT_DIR PRE_JSON SEED_BASE [--x-max 0.35] [--sizes 65536 131072 262144 524288]
                                               [--replicas 8] [--measurements 2000000] [--warmup 50000] [--dry-run]
PRE_JSON is the frozen pre-fit of the point (fits_v3 pre.json: {s: {beta_c, Delta_epsilon, source, ...}}). For every size N one campaign
stageBx_<N> is prepared with 5 temperatures beta_c^pre + k h'(N)/2, k = -2..2, h'(N) = x_max / (100 (N/1024)^(1 - Delta_eps^pre)), i.e.
prepare.py --beta-halfwidth x_max/100 --window-exponent (1 - Delta_eps^pre) --beta-points 5, replicas hot/cold alternating, own seed
namespace 'stageBx_<N>@<point>' and seed base SEED_BASE + i. The campaigns are REGISTERED (status 'prepared', stage 'Bx', engine '1d',
pre-fit provenance) but NOT activated: activation into the active lists needs the §4.7 union schema (registry active lists).
"""
import argparse, csv, hashlib, json, os, subprocess, sys
from pathlib import Path
import registry
HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('point',type=Path);p.add_argument('pre',type=Path);p.add_argument('seed_base',type=int)
    p.add_argument('--x-max',type=float,default=0.35);p.add_argument('--sizes',type=int,nargs='+',default=[65536,131072,262144,524288])
    p.add_argument('--replicas',type=int,default=8);p.add_argument('--measurements',type=int,default=2000000);p.add_argument('--warmup',type=int,default=50000)
    p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    D=a.point.resolve();reg_path=D/'campaigns.json';reg=json.loads(reg_path.read_text());pre=json.loads(a.pre.read_text())
    if len(pre)!=1:raise SystemExit(f'pre.json must hold exactly one s: {list(pre)}')
    s=float(next(iter(pre)));v=pre[str(next(iter(pre)))] if str(next(iter(pre))) in pre else next(iter(pre.values()))
    beta_c=float(v['beta_c']);deps=float(v['Delta_epsilon']);expo=1.0-deps;half=a.x_max/100.0
    names={c['name'] for c in reg['campaigns']};pre_sha=hashlib.sha256(a.pre.read_bytes()).hexdigest();made=[]
    # AUDIT-006: validate the complete request before creating anything
    for N in a.sizes:
        pair=f'{s}:{N}'
        if pair not in reg['expected_pairs']:raise SystemExit(f'{pair} not in expected_pairs of {reg_path}; nothing prepared')
        if f'stageBx_{N}' not in names and (D/f'stageBx_{N}').exists():raise SystemExit(f'{D/f"stageBx_{N}"} exists but is not registered: remove it or register it by hand; nothing prepared')
    for i,N in enumerate(a.sizes):
        name=f'stageBx_{N}';pair=f'{s}:{N}'
        if name in names:print(f'{name}: already registered, skipped');continue
        h=half*(N/1024)**(-expo);betas=[beta_c+k*h/2 for k in (-2,-1,0,1,2)]
        print(f"{D.name} {name}: beta_c^pre={beta_c:.7f} Deps^pre={deps:.5f} h'={h:.3e} temps {[round(b,8) for b in betas]} x_pre={[round(100*(b-beta_c)*(N/1024)**expo,3) for b in betas]}")
        if a.dry_run:continue
        cfile=D/f'centers_{name}.csv';cfile.write_text(f's,N,beta\n{s!r},,{beta_c!r}\n')   # full precision: the grid must equal beta_c^pre + k h'/2 exactly
        cmd=[sys.executable,str(HERE/'prepare.py'),'--out',str(D/name),'--s',repr(s),'--sizes',str(N),'--replicas',str(a.replicas),'--measurements',str(a.measurements),
             '--warmup',str(a.warmup),'--beta-points','5','--beta-halfwidth',repr(half),'--window-exponent',repr(expo),'--centers',str(cfile),
             '--seed-base',str(a.seed_base+i),'--seed-namespace',f'{name}@{D.name}','--engine','1d']
        out=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
        if out.returncode:raise SystemExit(f'{name}: prepare FAILED: {out.stderr.strip()[-400:]}')
        man=json.loads((D/name/'manifest.json').read_text());bs=sorted({t['beta'] for t in man['tasks']})
        if not (len(man['tasks'])==5*a.replicas and len(bs)==5 and all(abs(x-y)<1e-13 for x,y in zip(bs,sorted(betas)))):
            raise SystemExit(f'{name}: grid mismatch: prepared {bs} vs intended {sorted(betas)}')
        reg['campaigns'].append(dict(name=name,dir=name,stage='Bx',engine='1d',seed_base=a.seed_base+i,seed_namespace=f'{name}@{D.name}',s=[s],sizes=[N],status='prepared',job_ids=[],
            grid=dict(beta_points=5,replicas=a.replicas,measurements=a.measurements),   # independently registered budget (IR9-001)
            x_max=a.x_max,window_exponent=expo,beta_halfwidth_1024=half,pre_fit=dict(path=str(a.pre.resolve()),sha256=pre_sha,beta_c=beta_c,Delta_epsilon=deps,source=v.get('source')),
            activation='pending: registry.py --activate after the union-schema inspection; never replaces the stage A/B campaign of the pair'))
        def register(rr,entry=reg['campaigns'][-1],name=name):   # IR18-002: reload under the registry lock, append, write atomically
            if any(c['name']==name for c in rr['campaigns']):raise SystemExit(f'{name} already registered in {reg_path} (concurrent preparation?)')
            rr['campaigns'].append(entry)
        registry.locked_update(reg_path,register,validate=False);made.append(name)   # registered immediately after its own preparation (AUDIT-006); atomic (R17-003)
    if not a.dry_run:print(f'{D.name}: registered {made} (not activated)')
if __name__=='__main__':main()
