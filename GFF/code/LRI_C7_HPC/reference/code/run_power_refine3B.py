from pathlib import Path
import json,subprocess,time
W=Path(__file__).resolve().parents[1]
# Bound the number of memory-heavy integrators running concurrently.
while not (W/'records/power_refine5_L7_N5.json').exists():time.sleep(2)
rows=[]
for N in [1,3]:
 out=W/f'records/power_refine3B_L7_N{N}.json'
 if out.exists():continue
 cmd=[str(W/'code/coordinate_tree_integrate_allocated'),str(W/'inputs'),'7',str(N),'0','16','381957213',str(out),'power','.8',str(W/'inputs/power_refine3B_counts_L7.txt')]
 t=time.time()
 with open(W/f'logs/power_refine3B_L7_N{N}.log','w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 rows.append({'command':cmd,'seconds':time.time()-t})
 (W/'records/power_refine3B_manifest.json').write_text(json.dumps(rows,indent=2))
