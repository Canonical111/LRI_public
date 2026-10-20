#!/usr/bin/env python3
"""Invoke one legacy manifest lane (schema lri-dressed-campaign-v1, raw prescription only).

The solver itself owns all item locks and checkpoints. Pack manifests (lri-dressed-pack-v1,
which may carry the window prescription and tolerances) are run by scripts/pack_node.py.
"""
import argparse,json,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.io import digest,source_fingerprint,release_fingerprint,runtime,read_envelope
LANE_KEYS={'bath_cut','nz','osc','deltas','backend','plan'}
p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--index',type=int,required=True);p.add_argument('--output',required=True);p.add_argument('--threads',type=int,required=True);p.add_argument('--memory-limit-gib',type=float,required=True);p.add_argument('--receipt',required=True);p.add_argument('--seed-dir');a=p.parse_args()
r=json.loads(Path(a.manifest).read_text());s=r.pop('sha256',None)
if s!=digest(r):raise ValueError('Manifest checksum failed')
if r.get('schema')!='lri-dressed-campaign-v1':
    raise ValueError(f"run_lane.py runs only lri-dressed-campaign-v1 lanes, not {r.get('schema')!r}; use scripts/pack_node.py for pack manifests")
if r['source_sha256']!=source_fingerprint():raise ValueError('Manifest belongs to a different source revision')
receipt=read_envelope(a.receipt,'validation')['payload']
if receipt.get('passed') is not True or receipt.get('source_sha256')!=source_fingerprint() or receipt.get('runtime')!=runtime() \
   or receipt.get('release_sha256')!=release_fingerprint():
    raise ValueError('Missing or stale source/release/dependency validation receipt')
lane=r['lanes'][a.index]
extra=set(lane)-LANE_KEYS
if extra or lane['plan'].get('window','none')!='none':
    raise ValueError(f'Legacy lanes carry only the raw prescription; unsupported options {sorted(extra)}')
cmd=[sys.executable,'-m','lri_dressed','run','--bath-cut',str(lane['bath_cut']),'--nz',str(lane['nz']),'--osc',str(lane['osc']),'--backend',lane['backend'],'--deltas',*map(str,lane['deltas']),'--threads',str(a.threads),'--memory-limit-gib',str(a.memory_limit_gib),'--output-dir',a.output,'--resume']
if a.seed_dir:cmd+=['--seed-dir',a.seed_dir]
os.execv(sys.executable,cmd)
