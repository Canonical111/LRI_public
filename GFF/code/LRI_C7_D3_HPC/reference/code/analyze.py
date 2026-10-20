#!/usr/bin/env python3
"""Finite-scheme seventh-order assembly and replicate-level covariance."""
from pathlib import Path
import numpy as np,json,argparse,hashlib
W=Path(__file__).resolve().parents[1]
B2=np.array(json.load(open(W/'inputs/two_loop.json'))['B2'],float)
def coefficients(vals):
 dtype=np.result_type(*[np.asarray(v).dtype for v in vals.values()]);N=8
 b={1:np.array([3],dtype=dtype),2:B2.astype(dtype)};c={1:np.array([1],dtype=dtype),2:B2.astype(dtype)/6}
 for L,a in vals.items():
  a=np.asarray(a);k=8-L
  if L not in range(3,8)or a.shape!=(2*k,):raise ValueError('wrong loop jet shape')
  b[L]=a[:k];c[L]=a[k:]
 def mul(x,y):return np.convolve(x,y)[:N]
 g=np.zeros(N,dtype=dtype);e=g.copy();e[1]=1
 for _ in range(N):
  gp=g.copy();tmp=g.copy()*0
  for L in range(2,N):gp=mul(gp,g);tmp+=mul(b.get(L,np.zeros(1)),gp)
  g=(e-tmp)/3
 ga=np.zeros(N,dtype=dtype);gp=ga.copy();gp[0]=1
 for L in range(1,N):gp=mul(gp,g);ga+=mul(c.get(L,np.zeros(1)),gp)
 ga[0]+=1.5;ga[1]-=.5;return ga

def jacobians(means):
 out={}
 for L,a in means.items():
  columns=[]
  for j in range(len(a)):
   tmp={k:np.asarray(v,dtype=complex).copy()for k,v in means.items()};tmp[L][j]+=1e-20j;columns.append(coefficients(tmp).imag/1e-20)
  out[L]=np.array(columns).T
 return out

def load_campaign(tag,verify=True):
 m=json.load(open(W/'records'/tag/'manifest.json'));B=m['args']['replicates'];ar={s:{}for s in m['args']['sectors']};graphs={s:{}for s in ar};timing={s:{}for s in ar};evaluations=0
 inv=json.load(open(W/'inputs/inventory.json'));seen=set()
 for r in m['records']:
  p=W/r['file']
  if verify and hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('changed record '+str(p))
  d=json.load(open(p));s,L=r['sector'],r['L'];arr=ar[s].setdefault(L,np.zeros((B,2*(8-L)),dtype=np.longdouble));gr=graphs[s].setdefault(L,{});tm=timing[s].setdefault(L,{})
  for row in d['rows']:
   key=(s,L,row['rep'],row['graph'])
   if key in seen:raise ValueError('duplicate graph replicate')
   seen.add(key);assert row['begin']==0 and row['end']==row['total'];v=np.array(row['values'],dtype=np.longdouble);arr[row['rep']]+=v;gr.setdefault(row['graph'],np.zeros_like(arr))[row['rep']]=v
   rtm=tm.setdefault(row['graph'],dict(seconds=0.,points=0,quad=0,mp=0));rtm['seconds']+=row['seconds'];rtm['points']+=row['total'];rtm['quad']+=row['quad'];rtm['mp']+=row['mp'];evaluations+=row['total']
 for s,loops in ar.items():
  for L,x in loops.items():
   expected={r['id']for r in inv[s][str(L)]}if L!=2 else {0}
   assert set(graphs[s][L])==expected,(s,L,len(graphs[s][L]),len(expected))
   for g in expected:
    for r in range(B):assert (s,L,r,g)in seen
   ar[s][L]=np.asarray(x,dtype=float)
 return ar,graphs,timing,m

def analyze(tags,bootstrap=0,save=True):
 allarr={};gg={};tt={};mm=[]
 for tag in tags:
  allarr[tag],gg[tag],tt[tag],mf=load_campaign(tag);mm.append(mf)
  assert set(allarr[tag])=={'free','power'}
  for s in allarr[tag]:assert set(allarr[tag][s])==set(range(3,8))
 nc=len(tags);secs=['free','power'];loops=range(3,8)
 means={s:{L:sum(allarr[t][s][L].mean(0)for t in tags)/nc for L in loops}for s in secs}
 vc={s:{L:sum(np.cov(allarr[t][s][L],rowvar=False,ddof=1)/len(allarr[t][s][L])for t in tags)/nc**2 for L in loops}for s in secs}
 comb={L:means['free'][L]+means['power'][L]for L in loops};full=coefficients(comb);pf=coefficients(means['free']);delta=full-pf;J=jacobians(comb);Jf=jacobians(means['free']);Jd={L:J[L]-Jf[L]for L in loops}
 covs={s:{L:J[L]@vc[s][L]@J[L].T for L in loops}for s in secs};cov=sum(sum(v.values())for v in covs.values());covf=sum(Jf[L]@vc['free'][L]@Jf[L].T for L in loops);covd=sum(Jd[L]@vc['free'][L]@Jd[L].T+covs['power'][L]for L in loops);cross=sum(Jf[L]@vc['free'][L]@Jd[L].T for L in loops)
 assert np.allclose(cov,covf+covd+cross+cross.T,rtol=1e-8,atol=1e-8)
 refs={3:-.3535815204332,4:1.228063545327623,5:-5.85035142075,6:33.56819679857058};se=np.sqrt(np.maximum(0,np.diag(cov)))
 indiv={}
 for tag in tags:
  v={L:allarr[tag]['free'][L].mean(0)+allarr[tag]['power'][L].mean(0)for L in loops};jj=jacobians(v);cv=sum(jj[L]@(sum(np.cov(allarr[tag][s][L],rowvar=False)/len(allarr[tag][s][L])for s in secs))@jj[L].T for L in loops)
  indiv[tag]=dict(coefficients=coefficients(v).tolist(),sampling_se=np.sqrt(np.maximum(0,np.diag(cv))).tolist())
 halves=[]
 for h in [0,1]:
  v={L:sum(allarr[t][s][L][h*len(allarr[t][s][L])//2:(h+1)*len(allarr[t][s][L])//2].mean(0)for t in tags for s in secs)/nc for L in loops};halves.append(coefficients(v).tolist())
 boot=None
 if bootstrap:
  rng=np.random.default_rng(30930712);vals=[]
  for _ in range(bootstrap):
   v={L:sum(allarr[t][s][L][rng.integers(len(allarr[t][s][L]),size=len(allarr[t][s][L]))].mean(0)for t in tags for s in secs)/nc for L in loops};vals.append(coefficients(v))
  vals=np.array(vals);boot=dict(resamples=bootstrap,se=vals.std(0,ddof=1).tolist(),bias=(vals.mean(0)-full).tolist())
 output=dict(dimension=3,order=7,epsilon='2s-3',campaigns=tags,C7_full=float(full[7]),sampling_standard_error=float(se[7]),coefficients=full.tolist(),standard_errors=se.tolist(),covariance=cov.tolist(),power_free_C7=float(pf[7]),power_free_se=float(covf[7,7]**.5),power_correction=float(delta[7]),power_correction_se=float(max(0,covd[7,7])**.5),power_free_correction_covariance=float(cross[7,7]),power_differences=delta.tolist(),power_difference_errors=np.sqrt(np.maximum(0,np.diag(covd))).tolist(),means={s:{str(L):v.tolist()for L,v in means[s].items()}for s in secs},per_loop_errors={s:{str(L):float(max(0,v[7,7])**.5)for L,v in covs[s].items()}for s in secs},individual_campaigns=indiv,half_streams=halves,bootstrap=boot,production_evaluations=sum(m['evaluations']for m in mm),lower_order_checks=[dict(order=k,estimate=float(full[k]),reference=v,sampling_se=float(se[k]),discrepancy_se=float((full[k]-v)/se[k]))for k,v in refs.items()],status='Numerical calculation within the inherited graph/local-subtraction framework. Sampling SE is not a rigorous interval or independent field-theory validation.')
 if save:(W/'verification'/('analysis_'+'_'.join(tags)+'.json')).write_text(json.dumps(output,indent=2))
 # Per-graph projected replicate variance is diagnostic/allocation data only.
 growth={}
 for s in secs:
  growth[s]={}
  for L in loops:
   growth[s][str(L)]={}
   for g in gg[tags[0]][s][L]:
    samples=[np.asarray(gg[t][s][L][g],float)@J[L][7]for t in tags];rr=[tt[t][s][L][g]for t in tags]
    growth[s][str(L)][str(g)]=dict(projected_mean=float(sum(v.mean()for v in samples)/nc),projected_sd=float(sum(v.var(ddof=1)for v in samples)**.5/nc),cpu_seconds=sum(v['seconds']for v in rr),points=sum(v['points']for v in rr),replicates=sum(len(v)for v in samples),quad=sum(v['quad']for v in rr),mp=sum(v['mp']for v in rr))
 if save:(W/'verification'/('graphs_'+'_'.join(tags)+'.json')).write_text(json.dumps(growth,indent=2))
 return output
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('tags',nargs='+');ap.add_argument('--bootstrap',type=int,default=0);a=ap.parse_args();r=analyze(a.tags,a.bootstrap);print(json.dumps({k:r[k]for k in ['C7_full','sampling_standard_error','power_free_C7','power_correction','power_correction_se','production_evaluations','per_loop_errors','lower_order_checks']},indent=2))
