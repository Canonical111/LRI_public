from pathlib import Path
import json,subprocess,time,os,sys
W=Path(__file__).resolve().parents[1];tag=sys.argv[1]
plans={
'power_coarse':[(L,1,64,32,497162+L,'power',False) for L in [7,6,5]],
'power_refine':[(L,N,2,16,987137+L,'power',False) for L in [7,6,5] for N in [1,3]],
'low_exact':[(4,N,1,1,1,sel,True) for N in [8,12,16] for sel in ['free','power']],
}
rows=[]
for L,N,ns,B,seed,sel,exact in plans[tag]:
 out=W/f'records/{tag}_{sel}_L{L}_N{N}.json';cmd=[str(W/'code/coordinate_integrate'),str(W/'inputs'),str(L),str(N),str(ns),str(B),str(seed),str(out),sel]+(['exact']if exact else [])
 if out.exists():continue
 start=time.time()
 with open(W/f'logs/{tag}_{sel}_L{L}_N{N}.log','w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 rows.append(dict(command=cmd,seconds=time.time()-start));(W/f'records/{tag}_manifest.json').write_text(json.dumps(rows,indent=2))
