"""Validate the saved production streams and count work (not raw points as independent observations)."""
from pathlib import Path
import json, hashlib, platform,sys
import numpy as np, scipy,mpmath
W=Path(__file__).resolve().parents[1]
rows=[]
paths=[]
for tag in ['tprodA','tprodB']:
 for L in [5,6,7]:paths.append((W/f'records/{tag}_L{L}.json','continuous','production',None))
for tag in ['power_coarseA','power_coarseB']:
 for L in [5,6,7]:paths.append((W/f'records/{tag}_L{L}_N1.json','quadrature','production',None))
for level,degrees in [('refine3',(1,3)),('refine5',(3,5)),('refine6',(5,6))]:
 for L in [5,6,7]:
  tag='power_refine3B' if level=='refine3' and L==7 else 'power_'+level
  for N in degrees:paths.append((W/f'records/{tag}_L{L}_N{N}.json','quadrature','production',str(W/f'inputs/power_refine3B_counts_L7.txt')if tag=='power_refine3B'else None))
worst=0;ntrees=0;npoints=0
for path,kind,use,allocation in paths:
 if not path.exists():raise FileNotFoundError(path)
 b=path.read_bytes();d=json.loads(b);a=np.asarray(d['batches']);g=np.asarray(d['graph_batches']);assert a.shape==(d['replicates'],14)
 assert g.shape[0]==len(a) and g.shape[-1]==14
 assert np.isfinite(a).all() and np.isfinite(g).all()
 diff=np.max(abs(a-g.sum(1))/(1+abs(a)+abs(g).sum(1)));worst=max(worst,float(diff));assert diff<2e-13
 L=d['L'];active=np.any(g!=0,axis=(0,2));B=d['replicates']
 if kind=='continuous':
  c=np.asarray(d['counts']);assert c.ndim==1
  pos=c[c>0];assert all((pos&(pos-1))==0)
  total=int(sum(pos))*B;npoints+=total
 else:
  if allocation:
   c=np.loadtxt(allocation,dtype=int,skiprows=1)[:,1];trees=int(sum(c))*B
  else:
   # Every algebraically nonzero power graph is sampled, even if its selected Taylor coefficient vanishes.
   nactive={5:24,6:132,7:694}[L];trees=d['samples_per_graph']*B*nactive
  ntrees+=trees;total=trees*(d['N']+1)**(L-1)
 row={k:d[k] for k in ['L','N','replicates','seed','rate','selection','method','seconds'] if k in d}
 row.update(file=str(path.relative_to(W)),sha256=hashlib.sha256(b).hexdigest(),kind=kind,replicate_count=len(a),finite_values=True,graph_sum_normalized_difference=float(diff),nominal_point_evaluations=int(total))
 if kind=='quadrature':row['sampled_trees']=trees
 rows.append(row)
result={'streams':rows,'continuous_evaluations':npoints,'quadrature_tree_evaluations':ntrees,'nominal_tensor_points':sum(r['nominal_point_evaluations']for r in rows if r['kind']=='quadrature'),'point_count_caveat':'Tensor grid points are highly structured and reused; only independent randomized replicate totals determine errors. Paired levels use the same trees. Counts exclude pilot, training and validation.','maximum_graph_sum_normalized_difference':worst,'runtime':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'mpmath':mpmath.__version__,'platform':platform.platform(),'longdouble':str(np.finfo(np.longdouble))},'excluded_training':['power_refine3_L7_N1.json','power_refine3_L7_N3.json'],'no_partial_output_included':True}
(W/'verification/production_audit.json').write_text(json.dumps(result,indent=2));print('production streams',len(rows),'continuous',npoints,'trees',ntrees,'max summation discrepancy',worst)
