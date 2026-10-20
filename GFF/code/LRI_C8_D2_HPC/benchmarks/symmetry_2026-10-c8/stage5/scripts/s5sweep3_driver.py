#!/usr/bin/env python3
"""J-SWEEP-3 runner (symmetry, Intel debugq): run every index of an already-planned test-only campaign with the
package's own sweep runner (tools/sweep.py run_indices: heaviest first, one production.py run --index per process slot,
each pinned to its slot; C8_LANES=socket gives 2 x 20 socket-pinned slots on a 2 x 20-core Xeon Gold 6148), then the
package's merge. The plan (production.py plan) and the ledger registration (tools/ledger.py register --role sweep) are
done by the job script before this runs; tools/sweep.py itself plans with --test-graphs all only, which is why this
driver exists (the plan's J-SWEEP-3 row: the J-SWEEP-2 plan arguments and seed restricted to a stratified subset).
  s5sweep3_driver.py PACKAGE RUN --threads 20 --scratch DIR --merge-jobs 20 [--procs N]   (--procs: N equal slots, as sweep.py --procs)"""
import argparse,os,subprocess,sys,types
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('run',type=Path);p.add_argument('--threads',type=int,default=20)
p.add_argument('--scratch',required=True);p.add_argument('--merge-jobs',type=int,default=20);p.add_argument('--procs',type=int);a=p.parse_args()
sys.path.insert(0,str(a.package/'tools'))
import sweep
failed=sweep.run_indices(a.run.resolve(),types.SimpleNamespace(threads=a.threads,procs=a.procs,scratch=a.scratch),dict(os.environ))
if failed:sys.exit(f'{len(failed)} indices failed: {failed[:10]}')
for args in (['status',str(a.run),'--fast'],['merge',str(a.run),'--jobs',str(a.merge_jobs),'--scratch',a.scratch]):
    cp=subprocess.run([sys.executable,'-B',str(a.package/'tools/production.py'),*args],stdout=subprocess.DEVNULL if args[0]=='status' else None)
    if cp.returncode:sys.exit(f'production.py {args[0]} failed (exit {cp.returncode})')
print('driver: all indices ran and the campaign is merged',flush=True)
