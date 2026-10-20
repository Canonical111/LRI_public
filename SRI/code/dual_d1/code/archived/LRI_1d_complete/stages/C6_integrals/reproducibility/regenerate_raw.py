"""Regenerate requested regulated integrals, including exact primitive checks.
Use --all to regenerate all raw jobs used in the assembled result. Each job
runs in a separate process, so caches and audit counters do not leak.
"""
from pathlib import Path
import argparse,subprocess,sys,re
ROOT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--all',action='store_true');ap.add_argument('tags',nargs='*');args=ap.parse_args()
if args.all:
 tags=[p.name.removesuffix('_negative.json') for p in ROOT.glob('*_negative.json') if re.fullmatch(r'(?:EA|EZ|EQ|A|Z|Q)\d+_(?:base|v|vv|vvv|d|vd|vvd|dd)_negative.json',p.name)]
else:tags=args.tags or ['A7_base','Q6_v']
for tag in sorted(tags,key=lambda t:(int(re.search(r'\d+',t).group()),t)):
 m=re.fullmatch(r'(EA|EZ|EQ|A|Z|Q)(\d+)_(base|v|vv|vvv|d|vd|vvd|dd)',tag)
 if not m:raise ValueError(f'Unsupported job tag: {tag}')
 kind,n,der=m.groups();print('GENERATE',tag,flush=True)
 subprocess.run([sys.executable,'run_moment.py',n,kind,der],cwd=ROOT,check=True)
print('Raw generation complete. Run recompute_from_raw.py next.',flush=True)
