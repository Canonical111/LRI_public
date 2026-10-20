"""Full C7 reassembly from independent saved runs; no missing term is filled by zero.
The first L7 degree-1/3 stream trains a graph allocation and is NOT reused in the mean.
"""
from pathlib import Path
import json,numpy as np,sys
from assemble_coordinate import coefficients
W=Path(__file__).resolve().parents[1]
ref=json.load(open(W/'verification/full_affine_assembly.json'));K=np.array(ref['K']);J={int(L):np.array(v['J'])for L,v in ref['loops'].items()};Adj={int(L):np.array(v['adjusted'])for L,v in ref['loops'].items()}
prim=-696147.4459362661;primse=25.3678

def load(tag,L,N=None):
 f=W/f'records/{tag}_L{L}{"_N"+str(N)if N is not None else ""}.json'
 if not f.exists():raise FileNotFoundError(str(f))
 return json.load(open(f))

def stats(y):
 return y.mean(0),np.atleast_2d(np.cov(y,rowvar=False,ddof=1))/len(y)

def summary(m,c):return dict(mean=m.tolist(),sampling_se=np.sqrt(np.maximum(0,np.diag(c))).tolist(),covariance=c.tolist())

def free_lower():
 out={int(L):np.array(v)for L,v in ref['lower'].items()}
 out[3]=np.array(load('coord_free',3,24)['batches'])[0]
 d=load('trefexact',4,20);it=iter((W/'inputs/L4_coord.txt').read_text().split());L=int(next(it));ng=int(next(it));flags=[]
 for i in range(ng):
  idx=int(next(it));wa=next(it);wb=next(it);p=int(next(it));pr=int(next(it));nt=int(next(it));flags.append(p)
  for j in range(nt*(1+L*(L+1)//2)):next(it)
 out[4]=np.array(d['graph_batches'])[0,np.array(flags)==0].sum(0)
 return out

lowfree=free_lower();KF=coefficients(lowfree);JF={}
for L in [5,6,7]:
 mat=np.zeros((8,14))
 for k in range(14):
  v={i:a.astype(complex)for i,a in lowfree.items()};v[L]=np.zeros(14,complex);v[L][k]=1e-20j;mat[:,k]=coefficients(v).imag/1e-20
 JF[L]=mat
# Joint coordinates: C0...C7, power-free C7, actual full-minus-power-free C7.
mean=np.r_[K,KF[7],K[7]-KF[7]];cov=np.zeros((10,10));comp={};streams=[];runstats={};rawpower={L:np.zeros(14)for L in [5,6,7]};rawcov={L:np.zeros((14,14))for L in [5,6,7]}

def add_stream(label,raw,M,weight=1):
 global mean,cov
 y=raw@M.T*weight;m,c=stats(y);mean+=m;cov+=c;comp[label]=summary(m,c);streams.append((label,y));return m,c
for tag in ['tprodA','tprodB']:
 cm=K.copy();cv=np.zeros((8,8))
 for L in [5,6,7]:
  a=np.array(load(tag,L)['batches']);M=np.vstack([J[L],JF[L][7],J[L][7]-JF[L][7]]);add_stream(f'{tag}_L{L}',a,M,.5)
  m,c=stats(a@J[L].T);cm+=m;cv+=c
 cm[7]+=prim;cv[7,7]+=primse**2;runstats[tag]=summary(cm,cv)
mean[7]+=prim;mean[8]+=prim
pv=np.zeros(10);pv[7]=pv[8]=primse;cov+=np.outer(pv,pv);comp['retained_primitive']={'mean_C7':prim,'sampling_se':primse,'used_once':True}
levels={}
for level,lo,hi in [('coarse',None,1),('refine3',1,3),('refine5',3,5),('refine6',5,6)]:
 lm=np.zeros(10);lc=np.zeros((10,10))
 for L in [5,6,7]:
  M=np.vstack([Adj[L],np.zeros(14),Adj[L][7]])
  if level=='coarse':tags=[('power_coarseA',2/3),('power_coarseB',1/3)]
  elif level=='refine3':tags=[('power_refine3B'if L==7 else 'power_refine3',1)]
  else:tags=[('power_'+level,1)]
  for tag,w in tags:
   a=np.array(load(tag,L,hi)['batches'])
   if lo is not None:
    b=np.array(load(tag,L,lo)['batches']);assert a.shape==b.shape;a=a-b
   m,c=add_stream(f'{tag}_L{L}',a,M,w);lm+=m;lc+=c
   rm,rc=stats(a);rawpower[L]+=w*rm;rawcov[L]+=w*w*rc
 levels[level]=summary(lm,lc)
assert abs(mean[7]-mean[8]-mean[9])<2e-8
# Degrees are telescopic, NOT a fitted extrapolation.
prefix=K.copy();prefix[7]+=prim;prefixcov=np.zeros((8,8));prefixcov[7,7]=primse**2
for label,y in streams:
 if label.startswith('tprod'):
  m,c=stats(y);prefix+=m[:8];prefixcov+=c[:8,:8]
resolutions=[]
for lev,N in [('coarse',1),('refine3',3),('refine5',5),('refine6',6)]:
 x=levels[lev];prefix+=np.array(x['mean'])[:8];prefixcov+=np.array(x['covariance'])[:8,:8];resolutions.append({'degree':N,**summary(prefix,prefixcov)})
# Direct raw fixed-point reassembly, retaining the explicit finite-grid controls.
rawfull={int(L):np.array(a)for L,a in ref['lower'].items()}
for L in [5,6,7]:rawfull[L]=.5*(np.array(load('tprodA',L)['batches']).mean(0)+np.array(load('tprodB',L)['batches']).mean(0))+rawpower[L]
unc=coefficients(rawfull);unc[7]+=prim
control=sum((J[L]-Adj[L])@rawpower[L]for L in [5,6,7]);assert np.max(abs((unc-control)-mean[:8]))<5e-7
# Diagnostic spurious poles, not calibrated to physical reference coefficients.
poles=[]
for L in [5,6,7]:
 se=np.sqrt(np.maximum(0,np.diag(rawcov[L])))
 for k in list(range(L-1))+list(range(7,7+L-1)):
  if se[k]>1e-12:poles.append({'L':L,'column':k,'mean':float(rawpower[L][k]),'sampling_se':float(se[k]),'z_score':float(rawpower[L][k]/se[k])})
refs=[.5,-1/6,.657131263981,-3.719856322902,45.42488010356,-731.13947662454,14331.77074705]
checks=[]
for n in [3,4,5,6]:
 se=np.sqrt(cov[n,n]);checks.append({'n':n,'value':float(mean[n]),'sampling_se':float(se),'reference':refs[n],'difference_over_sampling_se':float((mean[n]-refs[n])/se)if se>0 else None})
# Conditional replicate bootstrap: fixed allocations and controls are not refitted.
rng=np.random.default_rng(715193271);R=4096;bt=np.repeat(mean[None,:],R,axis=0)
for label,y in streams:
 ind=rng.integers(0,len(y),size=(R,len(y)));bt+=y[ind].mean(1)-y.mean(0)
bt+=rng.normal(size=(R,1))*pv
bootstrap_se=bt.std(0,ddof=1)
# First/second halves, with original fixed stream weights unchanged.
halves=[]
for half in [0,1]:
 est=mean.copy()
 for label,y in streams:
  sl=y[:len(y)//2]if half==0 else y[len(y)//2:];est+=sl.mean(0)-y.mean(0)
 halves.append(est.tolist())
# Allowance is an empirical error policy, not a mathematical enclosure.
last=levels['refine6'];lastmean=last['mean'][7];lastse=last['sampling_se'][7]
policy=max(4*np.sqrt(cov[7,7]),2*abs(lastmean)+4*lastse,max(abs(h[7]-mean[7])for h in halves))+.01
allowance=float(np.ceil(policy/1000)*1000)
result={'status':'full graph combination numerically assembled; empirical quadrature and sampling checks required','convention':'epsilon=2s-1','C7_full':float(mean[7]),'sampling_se':float(np.sqrt(cov[7,7])),'empirical_allowance':allowance,'allowance_policy':'ceil_to_1000(max(4*SE,2*abs(last refinement)+4*SE_last,max half-split shift)+0.01)','joint_order':['C0','C1','C2','C3','C4','C5','C6','C7','C7_power_free','actual_power_correction'],**summary(mean,cov),'components':comp,'power_levels':levels,'resolution_sequence':resolutions,'power_free_campaigns_full_lower':runstats,'lower_order_checks':checks,'spurious_pole_checks':poles,'bootstrap_replicates':R,'bootstrap_sampling_se':bootstrap_se.tolist(),'half_splits':halves,'raw_uncontrolled_C7':float(unc[7]),'applied_zero_pole_control_C7':float(control[7]),'direct_reassembly_max_difference':float(np.max(abs(unc-control-mean[:8]))),'training_refine3_L7_excluded':True,'raw_power_jet_means':{L:v.tolist()for L,v in rawpower.items()},'raw_power_jet_covariances':{L:v.tolist()for L,v in rawcov.items()}}
result['joint_sampling_se']=result['sampling_se']; result['sampling_se']=float(np.sqrt(cov[7,7])); result['status']='accepted full-graph numerical estimate with empirical, non-rigorous error allowance'
(W/'verification/C7_assembled_result.json').write_text(json.dumps(result,indent=2));print('FULL C7',result['C7_full'],'SE',result['sampling_se'],'allowance',allowance);print('power correction',mean[9],np.sqrt(cov[9,9]));print('last resolution',lastmean,lastse);print('lower checks',checks);print('bootstrap',bootstrap_se[7]);print('halves',[h[7]for h in halves]);print('pole max z',max(abs(r['z_score'])for r in poles))
