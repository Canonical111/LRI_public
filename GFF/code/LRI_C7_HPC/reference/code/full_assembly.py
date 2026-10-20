from pathlib import Path
import json,numpy as np
from assemble_coordinate import coefficients
W=Path(__file__).resolve().parents[1]
def graph_rows(L):return json.load(open(W/f'inputs/power_rows_L{L}.json'))['rows']
def lower():
 v={2:np.array(json.load(open(W/'records/coord_L2_N24.json'))['batches'])[0],3:np.array(json.load(open(W/'records/coord_L3_N24.json'))['batches'])[0],4:np.array(json.load(open(W/'records/trefexact_L4_N20.json'))['batches'])[0]}
 return v

def affine():
 v=lower();K=coefficients(v);J={}
 for L in [5,6,7]:
  j=np.zeros((8,14))
  for k in range(14):
   vv={i:a.astype(complex)for i,a in v.items()};vv[L]=np.zeros(14,complex);vv[L][k]=1e-20j;j[:,k]=coefficients(vv).imag/1e-20
  J[L]=j
 return K,J
if __name__=='__main__':
 K,J=affine();zero=json.load(open(W/'verification/forest_polynomials.json.zero.json'));out={};print('lowconstant',K)
 for L in [5,6,7]:
  data=json.load(open(W/f'records/tqpilot_L{L}_N1.json'));g=np.array(data['graph_batches']);g[:,zero[str(L)]]=0;X=g.sum(1);cols=list(range(L-1))+list(range(7,7+L-1));Z=X[:,cols];sc=np.sqrt((Z*Z).mean(0));keep=sc>1e-12*max(sc);cols=np.array(cols)[keep];sc=sc[keep];z=X[:,cols]/sc;zc=z-z.mean(0);u,s,vt=np.linalg.svd(zc,full_matrices=False);ridge=.015*s[0];ss=s/(s*s+ridge*ridge);C=np.zeros_like(J[L]);target=X@J[L].T
  for r in range(5,8):
   y=target[:,r];c=vt.T@(ss*(u.T@(y-y.mean())));C[r,cols]=c/sc
   res=X@(J[L][r]-C[r]);print('L',L,'C',r,'unctrl',y.mean(),y.std(ddof=1)/len(y)**.5,'traincontrol',res.mean(),res.std(ddof=1)/len(res)**.5)
  out[L]=dict(J=J[L].tolist(),control=C.tolist(),adjusted=(J[L]-C).tolist(),pilot=f'tqpilot_L{L}_N1.json',ridge_relative=.015,pole_columns=cols.tolist(),excluded_exact_zeros=zero[str(L)])
 (W/'verification/full_affine_assembly.json').write_text(json.dumps(dict(K=K.tolist(),lower={L:a.tolist()for L,a in lower().items()},loops=out),indent=2))
