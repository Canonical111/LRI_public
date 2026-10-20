#!/usr/bin/env python3
"""Create a campaign manifest. Does not submit jobs.

Legacy mode (default): independent continuation lanes for slurm/scan_array.slurm via
run_lane.py (schema lri-dressed-campaign-v1, raw prescription only; byte-compatible).

--pack mode: items for scripts/pack_node.py (schema lri-dressed-pack-v1). Each item is one
CLI invocation with every numerical option explicit, plus the per-item threads, memory
and time estimate the launcher packs by (from --calibration or explicit flags).
"""
import argparse,json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.planning import plan
from lri_dressed.io import atomic_json,source_fingerprint,release_fingerprint,digest
from lri_dressed.pack import item_id,check_item
p=argparse.ArgumentParser();p.add_argument('--bath-cuts',type=int,nargs='+',required=True);p.add_argument('--nz',type=int,default=24);p.add_argument('--osc',type=int,default=192);p.add_argument('--deltas',type=float,nargs='+',required=True);p.add_argument('--backend',choices=['auto','tensor','ladder'],default='auto');p.add_argument('--out',required=True)
g=p.add_argument_group('pack mode (rejected without --pack)')
g.add_argument('--pack',action='store_true',help='write an lri-dressed-pack-v1 manifest for pack_node.py')
PACK_DEFAULTS={'campaign':None,'windows':['none'],'split':'points','seed_dir':None,'calibration':None,'threads':1,'mem_gib':None,
    'est_seconds':None,'eig_tol':3e-11,'residual_tol':2e-7,'tuning_tol':5e-10,'maxiter':30,'max_eig_iter':10000,'ncv':28,
    'window_tol':1e-12,'window_maxiter':50,'allow_bridges':False,'basis_index':None}
g.add_argument('--campaign',help='campaign id (letters, digits, -, _); Slurm job names are lri-<id>')
g.add_argument('--windows',nargs='+',help="prescriptions: none, vacuum:consistent, vacuum:literal")
g.add_argument('--split',choices=['points','lanes'],help='one item per delta (needs seeds) or one lane per cutoff')
g.add_argument('--basis-index',help='checksummed per-delta frozen local-basis index; requires pack point mode')
g.add_argument('--seed-dir');g.add_argument('--calibration');g.add_argument('--threads',type=int)
g.add_argument('--mem-gib',type=float);g.add_argument('--est-seconds',type=float)
g.add_argument('--eig-tol',type=float);g.add_argument('--residual-tol',type=float);g.add_argument('--tuning-tol',type=float)
g.add_argument('--maxiter',type=int);g.add_argument('--max-eig-iter',type=int);g.add_argument('--ncv',type=int)
g.add_argument('--window-tol',type=float);g.add_argument('--window-maxiter',type=int)
g.add_argument('--allow-bridges',action='store_true',default=None,help='permit unseeded items (continuation bridges)')
a=p.parse_args()
given=[k for k in PACK_DEFAULTS if getattr(a,k) is not None]
if not a.pack and given:p.error(f'pack-only options {given} were given without --pack (legacy lanes are raw, default tolerances)')
for k,v in PACK_DEFAULTS.items():
    if getattr(a,k) is None:setattr(a,k,v)
if any(not 0<x<.25 for x in a.deltas):p.error('Only interior delta values are simulated')
deltas=sorted(set(a.deltas),reverse=True)
if not a.pack:
    lanes=[]
    for N in a.bath_cuts:
        pl=plan(N,a.nz,a.osc,a.backend)
        lanes.append({'bath_cut':N,'nz':a.nz,'osc':a.osc,'deltas':deltas,'backend':a.backend,'plan':pl})
    row={'schema':'lri-dressed-campaign-v1','source_sha256':source_fingerprint(),'lanes':lanes};row['sha256']=digest(row)
    atomic_json(a.out,row)
    print(f'{len(lanes)} lanes, array indices 0-{len(lanes)-1}. These are uncalibrated memory envelopes; validate resources on the target node.')
    raise SystemExit(0)

if not a.campaign or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',a.campaign):p.error('--pack needs --campaign ID')
if Path(a.out).exists():p.error(f'{a.out} exists; a pack manifest is never replaced in place (use a new campaign directory)')
seed_dir=str(Path(a.seed_dir).resolve()) if a.seed_dir else None
basis_entries={}
if a.basis_index:
    from lri_dressed.local_basis import read_basis_index,for_configuration,density_plan
    if a.split!='points' or a.windows!=['vacuum:consistent']:
        p.error('--basis-index requires --split points and --windows vacuum:consistent')
    basis_entries=read_basis_index(a.basis_index)
    if any(d not in basis_entries for d in deltas):p.error('Basis index does not cover every requested delta')
    for d in deltas:
        for_configuration(basis_entries[d][1],delta=d,nz=a.nz,osc=a.osc,window='vacuum',window_mode='consistent')

def seeded(delta):
    """An accepted seed for this delta, by the same rule the CLI uses (cli.execute --seed-dir)."""
    if delta in basis_entries:return True
    if not seed_dir:return False
    for pp in Path(seed_dir).glob('*.json'):
        try:raw=json.loads(pp.read_text());r=raw.get('payload',raw)
        except (OSError,ValueError):continue
        if abs(r.get('delta',-1)-delta)<1e-12 and r.get('tuning_residual',1)<1e-8:return True
    return False
need=deltas if a.split=='points' else deltas[:1]
unseeded=[d for d in need if not seeded(d)]
if unseeded and not a.allow_bridges:p.error(f'no accepted seed in --seed-dir for delta {unseeded}; give seeds or --allow-bridges')
prescriptions=[]
for w in a.windows:
    if w=='none':prescriptions.append(('none',None))
    elif w in ('vacuum:consistent','vacuum:literal'):prescriptions.append(('vacuum',w.split(':')[1]))
    else:p.error(f'Unknown prescription {w}')
cal=json.loads(Path(a.calibration).read_text())['records'] if a.calibration else []

def resources(N,backend,window,mode,basis_sha=None):
    rows=[r for r in cal if (r['bath_cut'],r['nz'],r['osc'],r['backend'],r['window'],r.get('window_mode'),r['threads'])==(N,a.nz,a.osc,backend,window,mode,a.threads) and r.get('local_basis_sha256')==basis_sha]
    if rows:
        per=max(r['seconds'] for r in rows);rss=max(r['peak_rss_gib'] for r in rows)
        return math.ceil(1.3*rss+.5),per,'calibration'
    if a.mem_gib is None or a.est_seconds is None:
        p.error(f'No calibration for cut={N} backend={backend} window={window}/{mode} threads={a.threads}; give --mem-gib and --est-seconds')
    return a.mem_gib,a.est_seconds,'explicit'

items=[]
for N in a.bath_cuts:
    for window,mode in prescriptions:
        pl=plan(N,a.nz,a.osc,a.backend,a.ncv,window);backend=pl['backend']
        groups=[[d] for d in deltas] if a.split=='points' else [deltas]
        for ds in groups:
            basis=basis_entries.get(ds[0])
            item_plan=density_plan(pl,basis[1]) if basis else pl
            mem,per,origin=resources(N,backend,window,mode,basis[1]['sha256'] if basis else None)
            mem=max(mem,math.ceil(item_plan['memory_envelope_gib']*100)/100)
            item={'bath_cut':N,'nz':a.nz,'osc':a.osc,'backend':backend,'window':window,'window_mode':mode,
                'window_tol':a.window_tol if window!='none' else None,'window_maxiter':a.window_maxiter if window!='none' else None,
                'deltas':ds,'seed_dir':seed_dir,'eig_tol':a.eig_tol,'residual_tol':a.residual_tol,'tuning_tol':a.tuning_tol,
                'maxiter':a.maxiter,'max_eig_iter':a.max_eig_iter,'ncv':a.ncv,'threads':a.threads,'mem_gib':mem,
                'est_seconds':per*len(ds),'resource_origin':origin,'plan_envelope_gib':item_plan['memory_envelope_gib']}
            if basis:
                item.update(local_basis_path=basis[0],local_basis_sha256=basis[1]['sha256'])
            item['id']=item_id(item);check_item(item);items.append(item)
if len({i['id'] for i in items})!=len(items):p.error('Duplicate item ids')
row={'schema':'lri-dressed-pack-v1','campaign':a.campaign,'release_sha256':release_fingerprint(),'source_sha256':source_fingerprint(),'items':items}
row['sha256']=digest(row);atomic_json(a.out,row)
print(f'{len(items)} pack items for campaign {a.campaign}; total estimate {sum(i["est_seconds"]*i["threads"] for i in items)/3600:.2f} core-hours (before 1.5x margin).')
