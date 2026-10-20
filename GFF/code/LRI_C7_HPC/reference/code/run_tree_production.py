import os,sys,subprocess,json,time
from pathlib import Path
W=Path(__file__).resolve().parents[1]
from sobol_net import make_net
campaign=sys.argv[1];B=16;seedbase={'A':41927510,'B':84175213}[campaign];rate={'A':'.8','B':'.7'}[campaign];rows=[]
for L in [5,6,7]:
 tag=f'tprod{campaign}';out=W/f'records/{tag}_L{L}.json';net=W/f'inputs/{tag}_L{L}.net';seed=seedbase+2719*L
 if out.exists():raise RuntimeError('refuse overwrite '+str(out))
 check=make_net(net,B,2*L-1,52,seed+715831)
 cmd=[str(W/'code/coordinate_tree_qmc'),str(W/'inputs'),str(L),'1',str(B),str(seed),str(net),str(out),rate,'free',str(W/f'inputs/tree_production_counts_L{L}.txt')]
 start=time.time()
 with open(W/f'logs/{tag}_L{L}.log','w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OMP_NUM_THREADS='4'))
 rows.append(dict(L=L,command=cmd,seconds=time.time()-start,net_check=check));(W/f'records/{tag}_manifest.json').write_text(json.dumps(rows,indent=2))
