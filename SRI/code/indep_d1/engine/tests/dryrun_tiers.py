#!/usr/bin/env python3
"""Dry run of the C8 tier specs (no engine run, no cluster): plans every tier spec into a scratch directory with
campaign.py plan (hashed seeds, cost-balanced chunks) and runs seedcheck over the three tiers together with every
earlier campaign of this engine.  Korobov lattices that are not yet in py/korobov_db_g01.json are replaced by a
dummy generator in a SCRATCH copy of the database (the real search runs on a compute node at submission time,
slurm/submit_C8.sh), so the dry run checks seeds, chunking and cfg generation only.
usage: python3 tests/dryrun_tiers.py SCRATCHDIR [specs/production_C8_tierA.json ...]
"""
import glob, json, os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scr = os.path.abspath(sys.argv[1])
specs = sys.argv[2:] or sorted(glob.glob(os.path.join(ROOT, 'specs', 'production_C8_tier?.json')))
os.makedirs(scr, exist_ok=True)
db = json.load(open(os.path.join(ROOT, 'py', 'korobov_db_g01.json')))
sys.path.insert(0, os.path.join(ROOT, 'py'))
from make_spec_C8 import group_info          # noqa: E402
dummy = []
for sp in specs:
    for m in json.load(open(sp))['moments']:
        gi = group_info(m['name'])
        key = f"{m['N']}_{gi['dim']}"
        if key not in db and gi['dim'] >= 1:
            db[key] = 1
            dummy.append(key)
sdb = os.path.join(scr, 'korobov_db_dryrun.json')
json.dump(db, open(sdb, 'w'), indent=1, sort_keys=True)
env = dict(os.environ, LRI_LATTICE_DB=sdb)
dirs = []
for sp in specs:
    tier = json.load(open(sp))['tier']
    rd = os.path.join(scr, tier)
    shutil.rmtree(rd, ignore_errors=True)
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'py', 'campaign.py'), 'plan', sp, rd], env=env,
                       capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[0] if r.stdout else r.stderr[-2000:])
    if r.returncode:
        sys.exit(r.returncode)
    dirs.append(rd)
old = [os.path.join(ROOT, 'runs', d) for d in ('prod_6digit', 'prod_6digit_topup1', 'poles1', 'kplus1', 'conv1',
                                               'c8val', 'c8conv', 'c8kplus1')]
r = subprocess.run([sys.executable, os.path.join(ROOT, 'py', 'campaign.py'), 'seedcheck'] + dirs + old,
                   capture_output=True, text=True)
print(r.stdout.strip())
print(f'dummy lattices (searched at submission on a compute node): {sorted(set(dummy))}')
sys.exit(r.returncode)
