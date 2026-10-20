import os,sys,subprocess,json,time
from pathlib import Path
W=Path(__file__).resolve().parents[1]
L,N,ns,B,seed=map(int,sys.argv[1:6]);tag=sys.argv[6];sel=sys.argv[7] if len(sys.argv)>7 else 'power';rate=sys.argv[8]if len(sys.argv)>8 else '.8';exact=sys.argv[9]if len(sys.argv)>9 else ''
cmd=[str(W/'code/coordinate_tree_integrate'),str(W/'inputs'),str(L),str(N),str(ns),str(B),str(seed),str(W/f'records/{tag}_L{L}_N{N}.json'),sel,rate]+([exact]if exact else [])
with open(W/f'logs/{tag}_L{L}_N{N}.log','w')as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,OMP_NUM_THREADS='4'))
rec=dict(pid=p.pid,command=cmd,started=time.time());(W/f'records/{tag}_L{L}_N{N}_job.json').write_text(json.dumps(rec,indent=2));print(rec)
