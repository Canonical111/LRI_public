import os,sys,subprocess,json,time
from pathlib import Path
W=Path(__file__).resolve().parents[1]
from sobol_net import make_net
L,N,B,seed=map(int,sys.argv[1:5]);tag=sys.argv[5];rate=sys.argv[6] if len(sys.argv)>6 else '.8';sel=sys.argv[7] if len(sys.argv)>7 else 'free'
net=W/f'inputs/{tag}_L{L}.net';rec=make_net(net,B,L+1,52,seed+7651*L)
cmd=[str(W/'code/coordinate_qmc'),str(W/'inputs'),str(L),str(N),str(B),str(seed),str(net),str(W/f'records/{tag}_L{L}.json'),rate,sel]
if len(sys.argv)>8:cmd.append(sys.argv[8])
with open(W/f'logs/{tag}_L{L}.log','w') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,OMP_NUM_THREADS='4'))
rec.update(pid=p.pid,command=cmd,started=time.time());(W/f'records/{tag}_L{L}_job.json').write_text(json.dumps(rec,indent=2));print(rec)
