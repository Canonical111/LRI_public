from pathlib import Path
import argparse,json
import numpy as np
W=Path(__file__).resolve().parents[1]
B2=np.array(json.load(open(W/'inputs/two_loop.json'))['B2'],float)
def coefficients(vals):
 dtype=np.result_type(*[np.asarray(v).dtype for v in vals.values()]);N=8
 b={1:np.array([3],dtype=dtype),2:B2.astype(dtype)};c={1:np.array([1],dtype=dtype),2:B2.astype(dtype)/6}
 for L,a in vals.items():
  if L==2:continue
  a=np.asarray(a);k=8-L;b[L]=a[:k];c[L]=a[k:]
 def mul(x,y):return np.convolve(x,y)[:N]
 g=np.zeros(N,dtype=dtype);e=g.copy();e[1]=1
 for _ in range(8):
  gp=g.copy();tmp=g.copy()*0
  for L in range(2,8):gp=mul(gp,g);tmp+=mul(b.get(L,np.zeros(1)),gp)
  g=(e-tmp)/3
 ga=np.zeros(N,dtype=dtype);gp=ga.copy();gp[0]=1
 for L in range(1,8):gp=mul(gp,g);ga+=mul(c.get(L,np.zeros(1)),gp)
 ga[0]+=1;ga[1]-=.5
 return ga

def jacobians(means):
 J={}
 for L,a in means.items():
  out=[]
  for j in range(len(a)):
   tmp={k:np.asarray(v,dtype=complex).copy()for k,v in means.items()};tmp[L][j]+=1e-20j;out.append(coefficients(tmp).imag/1e-20)
  J[L]=np.array(out).T
 return J

def read(tag):
 ar={};per={};files=list((W/'records'/tag).glob('L*_block*.json'))
 for f in files:
  dat=json.load(open(f));L=dat['L']
  for r in dat['rows']:
   g,rep=r['graph'],r['rep'];v=np.array(r['values'],float)
   per.setdefault(L,{}).setdefault(g,{})[rep]=per.setdefault(L,{}).setdefault(g,{}).get(rep,np.zeros_like(v))+v
 for L,gs in per.items():
  reps=set.intersection(*(set(g)for g in gs.values()));ar[L]=sum(np.array([g[r]for r in sorted(reps)])for g in gs.values());per[L]={g:np.array([v[r]for r in sorted(reps)])for g,v in gs.items()}
 return ar,per

def analysis(tag):
 ar,per=read(tag);ar.pop(2,None);per.pop(2,None);means={L:a.mean(0)for L,a in ar.items()};J=jacobians(means);cs=coefficients(means)
 cov=sum(J[L]@np.cov(a,rowvar=False)/len(a)@J[L].T for L,a in ar.items());err=np.sqrt(np.maximum(0,np.diag(cov)))
 inf={str(L):{str(g):{'projected_c7_mean':float((a@J[L][7]).mean()),'projected_sd':float((a@J[L][7]).std(ddof=1))}for g,a in v.items()}for L,v in per.items()}
 return dict(status='power-free only; NOT full C7(2)',tag=tag,coefficients=cs.tolist(),sampling_errors=err.tolist(),covariance=cov.tolist(),jet_means={str(L):a.tolist()for L,a in means.items()},graph_counts={str(L):len(v)for L,v in per.items()},error_by_loop={str(L):float(max(0,(J[L]@np.cov(a,rowvar=False)/len(a)@J[L].T)[7,7])**.5)for L,a in ar.items()},graphs=inf)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('tag');a=ap.parse_args();r=analysis(a.tag);(W/'verification'/f'analysis_{a.tag}.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items()if k not in('graphs','covariance','jet_means')},indent=2))
