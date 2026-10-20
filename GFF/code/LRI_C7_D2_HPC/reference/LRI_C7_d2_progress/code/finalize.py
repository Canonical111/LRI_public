"""Strict reconstruction of the computed sectors. This never reports a full C7(2)."""
from pathlib import Path
import json,hashlib,math
import numpy as np
from analyze import read,coefficients,jacobians
W=Path(__file__).resolve().parents[1]
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def checked(tag):
 root=W/'records'/tag;meta=json.load(open(root/'manifest.json'));a=meta['args'];all_seen=set();expected=set();npoints=0;files=[]
 alloc=json.load(open(W/'inputs/allocation.json'))if a['allocation']else None
 for L in a['loops']:
  inv=json.load(open(W/f'inputs/L{L}/inventory.json'))
  for g in inv:
   if g['status']!='finite-kernel' or (a['primitive']and not g['primitive'])or(a['nonprimitive']and g['primitive'])or(L==7 and g['mass_numerator']==4):continue
   n=int(alloc[str(L)][str(g['id'])])if alloc else a['points']
   if n<=0:continue
   assert n&(n-1)==0
   expected.update((L,g['id'],rep,0,n,n)for rep in range(a['replicates']))
 for r in meta['records']:
  p=W/r;dat=json.load(open(p));assert dat['schema']=='c7-d2-native-1';L=dat['L'];assert dat['seed']==int(a['seed'])
  assert abs(float(dat['rate'])-float(a['rate']))<1e-16
  taskpath=p.with_suffix('.tasks');tokens=taskpath.read_text().split();assert tokens[0]=='C7D2TASKS1'and int(tokens[1])==L
  tasks=[list(map(int,tokens[i:i+6]))for i in range(3,len(tokens),6)];assert len(tasks)==int(tokens[2])==len(dat['rows'])
  byuid={t[0]:t for t in tasks};assert len(byuid)==len(tasks)
  for row in dat['rows']:
   assert byuid[row['uid']]==[row['uid'],row['rep'],row['graph'],row['begin'],row['end'],row['total']]
   key=(L,row['graph'],row['rep'],row['begin'],row['end'],row['total']);assert key not in all_seen;all_seen.add(key)
   assert len(row['values'])==2*(8-L)and np.isfinite(np.array(row['values'],float)).all();npoints+=row['end']-row['begin']
  files.append({'file':r,'sha256':h(p),'task_sha256':h(taskpath)})
 assert all_seen==expected,(tag,len(expected-all_seen),len(all_seen-expected))
 return dict(tag=tag,complete=True,rows=len(all_seen),samples=npoints,replicates=a['replicates'],rate=a['rate'],files=files)

def primitive(tag):
 ar,per=read(tag);ref=json.load(open(W/'verification/primitive_completion_checks.json'));mapping={int(g):j for g,j in ref['mapping'].items()}
 refs={6:-2*18*float(ref['P4_2'])**2/6561,7:-2*(27/4)*(3*float(ref['Q2']))**3/6561,12:-2*54*3*float(ref['Q2'])*float(ref['P5_2'])/6561}
 blocks={j:sum((per[7][g]@np.array([-1/6561,1/2187])for g,k in mapping.items()if k==j),np.zeros(len(ar[7])))for j in range(14)}
 vals=sum(v for j,v in blocks.items()if j not in refs)+sum(refs.values())
 checks=[]
 for j,r in refs.items():
  v=blocks[j];se=v.std(ddof=1)/len(v)**.5;checks.append(dict(period=j,estimate=float(v.mean()),reference=r,sampling_se=float(se),pull=float((v.mean()-r)/se)))
 return dict(tag=tag,mean=float(vals.mean()),sampling_se=float(vals.std(ddof=1)/len(vals)**.5),replicates=vals.tolist(),raw_mean=float((ar[7]@np.array([-1/6561,1/2187])).mean()),product_checks=checks)

if __name__=='__main__':
 coverage=[checked(t)for t in ['primitiveA','primitiveB','productionA','productionB']]
 pr=[primitive(t)for t in['primitiveA','primitiveB']];pm=sum(p['mean']for p in pr)/2;pv=sum(p['sampling_se']**2 for p in pr)/4
 campaign={t:read(t)[0]for t in['productionA','productionB']};means={L:sum(a[L].mean(0)for a in campaign.values())/2 for L in range(3,8)}
 J=jacobians(means);base=coefficients(means);base[7]+=pm
 covs={L:sum(J[L]@np.cov(a[L],rowvar=False)@J[L].T/len(a[L])for a in campaign.values())/4 for L in means}
 cov=sum(covs.values());cov[7,7]+=pv;errors=np.sqrt(np.maximum(0,np.diag(cov)))
 cdata=[]
 for t,a in campaign.items():
  m={L:v.mean(0)for L,v in a.items()};jt=jacobians(m);cs=coefficients(m);cs[7]+=pm
  cc=sum(jt[L]@np.cov(v,rowvar=False)@jt[L].T/len(v)for L,v in a.items());cc[7,7]+=pv
  cdata.append(dict(tag=t,coefficients=cs.tolist(),sampling_errors=np.sqrt(np.maximum(0,np.diag(cc))).tolist(),covariance=cc.tolist()))
 rng=np.random.default_rng(28496201);bootstrap=[]
 for _ in range(2048):
  mm={L:sum(a[L][rng.integers(0,len(a[L]),len(a[L]))].mean(0)for a in campaign.values())/2 for L in means};cc=coefficients(mm)
  pp=sum(np.mean(rng.choice(p['replicates'],len(p['replicates']),replace=True))for p in pr)/2;cc[7]+=pp;bootstrap.append(cc)
 bootstrap=np.array(bootstrap);bootse=bootstrap.std(0,ddof=1);bias=bootstrap.mean(0)-base
 # Independent half-stream diagnostics retain their common primitive input.
 halves=[]
 for s in range(2):
  mm={L:sum(a[L][s*8:(s+1)*8].mean(0)for a in campaign.values())/2 for L in means};cc=coefficients(mm);cc[7]+=pm;halves.append(cc.tolist())
 refs={3:-.8748500126526,4:5.048868431355,5:-38.83364589623,6:362.3489137997967};lower=[dict(order=k,estimate=float(base[k]),sampling_se=float(errors[k]),reference=r,pull=float((base[k]-r)/errors[k]),reference_sampling_se=.15264446036381157 if k==6 else 0)for k,r in refs.items()]
 out=dict(status='complete computed power-free sector; full C7(2) NOT evaluated',dimension=2,epsilon='2s-2',full_C7_2=None,power_correction=None,power_free_C7=float(base[7]),power_free_sampling_se=float(errors[7]),coefficients=base.tolist(),sampling_errors=errors.tolist(),covariance=cov.tolist(),error_by_loop={str(L):float(max(0,cc[7,7])**.5)for L,cc in covs.items()},common_primitive_se=pv**.5,primitive=dict(mean=pm,sampling_se=pv**.5,campaigns=pr),campaigns=cdata,lower_order_checks=lower,bootstrap_replicates=2048,bootstrap_se=bootse.tolist(),bootstrap_bias=bias.tolist(),half_streams=halves,total_samples=sum(x['samples']for x in coverage),coverage=coverage,jet_means={str(L):v.tolist()for L,v in means.items()},scope='Sampling uncertainties do not bound the omitted power correction or shared diagram/renormalization errors. Pilot data were excluded. The two production campaigns share the primitive result; its variance is counted once. Three primitive product periods are replaced by independently evaluated exact special-function formulas.')
 (W/'verification/C7_d2_progress_result.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({k:v for k,v in out.items()if k not in('coverage','covariance','jet_means','primitive','campaigns')},indent=2));print('primitive',pm,pv**.5)
