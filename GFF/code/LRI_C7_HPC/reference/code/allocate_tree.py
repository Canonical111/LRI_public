from pathlib import Path
import json,numpy as np
from assemble_coordinate import coefficients
W=Path(__file__).resolve().parents[1];art=json.load(open(W/'inputs/articulation.json'))
v={2:np.array(json.load(open(W/'records/coord_L2_N24.json'))['batches'])[0],3:np.array(json.load(open(W/'records/coord_free_L3_N24.json'))['batches'])[0],4:np.array(json.load(open(W/'records/low_exact_free_L4_N16.json'))['batches'])[0]};G={};rows={};raw={}
for L in [5,6,7]:
 it=iter((W/f'inputs/L{L}_coord.txt').read_text().split());_,ng=int(next(it)),int(next(it));R=[]
 for i in range(ng):
  idx=int(next(it));wa,wb=float(next(it)),float(next(it));pw,pr,nt=[int(next(it))for _ in range(3)];R.append(dict(id=idx,wa=wa,wb=wb,power=pw,primitive=pr,terms=nt))
  for _ in range(nt):
   for _ in range(1+L*(L+1)//2):next(it)
 rows[L]=R;d=json.load(open(W/f'records/t_pilot_L{L}.json'));a=np.array(d['graph_batches']);raw[L]=d;valid=np.array([not r['power'] and i not in art[str(L)] and r['terms']>0 and not(L==7 and r['primitive']) for i,r in enumerate(R)]);a[:,~valid]=0;G[L]=a;v[L]=a.mean(0).sum(0)
v[7][6]+=-6561*(-696147.4459362661)
C=coefficients(v);print('pilot C',C);jacs={};out={}
for L,targetN in [(5,8192),(6,2048),(7,512)]:
 jac=np.zeros((8,14))
 for j in range(14):
  vv={k:a.astype(complex)for k,a in v.items()};vv[L][j]+=1e-20j;jac[:,j]=coefficients(vv).imag/1e-20
 jacs[L]=jac.tolist();y=G[L]@jac[7];sigma=y.std(0,ddof=1)*np.sqrt(raw[L]['N']);valid=np.any(G[L]!=0,axis=(0,2));cost=np.array([max(8,r['terms'])for r in rows[L]],float);floor=.03*np.median(sigma[valid]);sigma[valid]=np.maximum(sigma[valid],floor)
 k=targetN*cost[valid].sum()/np.sum(sigma[valid]*np.sqrt(cost[valid]));counts=np.zeros(len(valid),int);counts[valid]=np.clip(2**np.rint(np.log2(np.maximum(16,k*sigma[valid]/np.sqrt(cost[valid])))),16,131072).astype(int)
 if L==7:
  for i,r in enumerate(rows[L]):
   if abs(3*r['wb']-r['wa'])<1e-15:counts[i]=0
 path=W/f'inputs/tree_production_counts_L{L}.txt';path.write_text(str(len(counts))+'\n'+'\n'.join(f'{i} {n}'for i,n in enumerate(counts))+'\n')
 yy=y.sum(1);print(L,'pilot high contribution',yy.mean(),'SE',yy.std(ddof=1)/len(yy)**.5,'samples per rep',sum(counts),'max',max(counts),'forecast SE16',np.sqrt(sum(sigma[counts>0]**2/counts[counts>0])/16))
 out[L]=dict(pilot_N=raw[L]['N'],pilot_replicates=raw[L]['replicates'],active=int(sum(counts>0)),samples_per_replicate=int(sum(counts)),counts=counts.tolist(),cost_model='max(8,number of grouped coordinate forest terms)',target_uniform_N=targetN,jacobian=jac.tolist())
(W/'verification/tree_frozen_allocation.json').write_text(json.dumps(out,indent=2));(W/'verification/tree_pilot_coefficients.json').write_text(json.dumps(dict(values={k:x.tolist()for k,x in v.items()},C=C.tolist()),indent=2))
