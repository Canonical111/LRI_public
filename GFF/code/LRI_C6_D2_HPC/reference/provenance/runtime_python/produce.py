import os
from driver import *
plan=json.load(open(W/'inputs/frozen_production_plan.json'))['plan']
# Run short lower-loop jobs first, then all sixth-loop streams. Outputs are checkpointed per loop.
plan=sorted(plan,key=lambda p:(p['L'],p['d'],p['tag']))
for p in plan:
 if (W/f'records/{p["tag"]}_d{p["d"]}_L{p["L"]}.json').exists():continue
 if p['grid']:os.environ['GRID_FILE']=p['grid']
 else:os.environ.pop('GRID_FILE',None)
 os.environ.pop('PREFIX_STRATA',None);os.environ.pop('TRAIN_HIST',None)
 counts=json.load(open(p['counts_file']))['counts']
 run(p['tag'],p['d'],p['L'],counts,p['replicates'],p['seed'],p['layout'],p['rate_factor'],p['antithetic'],'rqmc',False,p['bits'])
