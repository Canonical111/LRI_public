from driver import *
import os
counts=np.array(json.load(open(W/'inputs/benchmark_counts.json')))*2
for d in [2,3]:
 for top in [0,3,11]:
  tag='validation_grid'+str(top)
  if (W/f'records/{tag}_d{d}_L6.json').exists():continue
  if top:os.environ['GRID_FILE']=str(W/f'inputs/grid_d{d}_top{top}.txt')
  else:os.environ.pop('GRID_FILE',None)
  run(tag,d,6,counts,32,98273105+61*d,0)
