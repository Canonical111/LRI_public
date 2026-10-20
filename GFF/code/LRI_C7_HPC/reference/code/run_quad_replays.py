from pathlib import Path
import json,numpy as np,subprocess,time
W=Path(__file__).resolve().parents[1];ref=json.load(open(W/'verification/full_affine_assembly.json'));plans=[]
for L,N,ids in [(7,3,[3593,3970,3205,790]),(7,5,[3593,3933]),(6,5,[r['id']for r in json.load(open(W/'inputs/power_rows_L6.json'))['rows']if r['power']][:4])]:
 ng=len(json.load(open(W/f'inputs/power_rows_L{L}.json'))['rows']);counts=[2 if i in ids else 0 for i in range(ng)];fn=W/f'inputs/quad_replay_L{L}_N{N}.txt';fn.write_text(str(ng)+'\n'+''.join(f'{i} {k}\n'for i,k in enumerate(counts)));outs=[]
 for variant,exe in [('ld',W/'code/coordinate_tree_integrate_allocated'),('quad',W/'code/precision_quad/evaluate')]:
  out=W/f'verification/quad_replay_{variant}_L{L}_N{N}.json';cmd=[str(exe),str(W/'inputs'),str(L),str(N),'0','2',str(649151+37*L),str(out),'power','.8',str(fn)];t=time.time()
  with open(W/f'logs/quad_replay_{variant}_L{L}_N{N}.log','w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  outs.append(json.load(open(out)))
 a=np.array(outs[0]['graph_batches']);b=np.array(outs[1]['graph_batches']);j=np.array(ref['loops'][str(L)]['adjusted'])[7];plans.append({'L':L,'N':N,'ids':ids,'max_normalized_difference':float(np.max(abs(a-b)/np.maximum(1,abs(b)))),'max_controlled_C7_difference_per_replicate':float(np.max(abs((a-b).sum(1)@j))),'ld_seconds':outs[0]['seconds'],'quad_seconds':outs[1]['seconds'],'note':'Same 80-bit stored weights; integrand, tensor sums and Gamma products recalculated in binary128.'});print(plans[-1],flush=True)
 (W/'verification/quadrature_precision_replays.json').write_text(json.dumps(plans,indent=2))
