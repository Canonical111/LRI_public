"""Independent positive-gap coordinate reconstruction, decimal-650 reference."""
from pathlib import Path
import json,mpmath as mp
W=Path(__file__).resolve().parents[1];mp.mp.dps=650
samples=json.load(open(W/'verification/tree_point_samples.json'));graphs={}
for L in range(3,8):
 it=iter((W/f'inputs/L{L}_coord.txt').read_text().split());ll=int(next(it));ng=int(next(it));g=[];ne=L*(L+1)//2
 for i in range(ng):
  idx=int(next(it));wa=next(it);wb=next(it);power=int(next(it));primitive=int(next(it));nt=int(next(it));terms=[]
  for _ in range(nt):
   key=int(next(it));coef=[int(next(it))for _ in range(ne)];terms.append(([(key>>(2*k))&3 for k in range(ne)],coef))
  g.append(terms)
 graphs[L]=g
out=[]
for r in samples:
 L=r['L'];lt=list(map(mp.mpf,r['lt']));sc=[mp.mpf(1)]
 for j in range(1,L):sc.append(sc[r['parents'][j]]*mp.exp(lt[j]))
 gaps=[sc[k]for k in r['gapnodes']];pos={v:i for i,v in enumerate(r['order'])};dist=[]
 for i in range(L+1):
  for j in range(i+1,L+1):dist.append(mp.fsum(gaps[min(pos[i],pos[j]):max(pos[i],pos[j])]))
 weight=mp.exp(mp.fsum((r['sizes'][j]-1-mp.mpf(r['alpha'][j]))*lt[j]for j in range(1,L)));val=[mp.mpf(0)]*(8-L)
 for m,c in graphs[L][r['id']]:
  H=mp.fsum(a*x for a,x in zip(m,dist));R=mp.fsum(a*x for a,x in zip(c,dist))
  if not R:continue
  logD=mp.fsum(mp.mpf(a)*mp.log(x)for a,x in zip(m,dist))/2
  base=R/H*mp.exp(-logD)*weight;lv=logD-L*mp.log(H)
  for j in range(8-L):val[j]+=base*lv**j/mp.factorial(j)
 errors=[abs(mp.mpf(a)-b)/max(1,abs(b))for a,b in zip(r['values'],val)]
 out.append({'L':L,'id':r['id'],'method':r['method'],'max_normalized_error':str(max(errors)),'reference_values':[str(v)for v in val],'min_log_cluster_scale':str(min(lt))})
maxerr=max(mp.mpf(r['max_normalized_error'])for r in out);ordinary=[r for r in out if mp.mpf(r['min_log_cluster_scale'])>-80];extreme=[r for r in out if mp.mpf(r['min_log_cluster_scale'])<=-80]
res={'working_digits':mp.mp.dps,'checks':out,'maximum_normalized_error':str(maxerr),'ordinary_max_error':str(max(mp.mpf(r['max_normalized_error'])for r in ordinary)),'extreme_max_error':str(max(mp.mpf(r['max_normalized_error'])for r in extreme))}
(W/'verification/tree_point_checks.json').write_text(json.dumps(res,indent=2));print('POINT CHECK',res['ordinary_max_error'],res['extreme_max_error'])
