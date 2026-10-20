"""Full-period last-inner integration, retaining exactly its polynomial growth.
Valid only for e*integral f(T)dT finite constant. This is NOT the weight-zero
projection: all zeta/log constants and GPL constants in the growth are retained.
"""
from endpoint_growth_finite import *

def pp_as_fraction(R,idx=6):
 pp=polynomial_part(R,idx);return sum((c*GEN[idx]**n for n,c in pp.items()),K.zero)

def project_stage5(items,N=6):
 idx=5;out={};st=time.time();terms=0;kept=0
 for j,((words,logs),R) in enumerate(items):
  pp,po=apart(R,idx)
  for kin,a,p,pref in [('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]:
   audit_basis(kin,a,p,words[idx-1],idx)
   for wa,c in integrate_basis(kin,a,p,words[idx-1],idx).items():
    for wb,cb in endpoint_value(c,wa,idx,GEN[N]).items():
     coef=pp_as_fraction(pref*cb,N);terms+=1
     if not coef:continue
     kept+=1
     for wf,mu in endpoint_fibrate(wb,N).items():
      assert not mu.diff(GEN[N])
      for wn,mv in shuffle(wf,words[N-1]).items():
       keys=[()]*N;keys[-1]=wn;addto(out,(tuple(keys),logs),coef*mu*mv)
    for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
     assert not wb;coef=pp_as_fraction(pref*cb,N)
     if coef:
      keys=list(words);keys[idx-1]=();addto(out,(tuple(keys),logs),-coef)
  items[j]=None
  if j%100==0:print('PROJECTED_STAGE',j+1,len(items),len(out),terms,kept,time.time()-st,flush=True)
 return clean(out)

def prepare(folder,force=False):
 folder=Path(folder);path=folder/'growth_stage5.jsonl'
 if path.exists() and not force:return
 if (folder/'stage5.jsonl').exists():
  rows=load(folder/'stage5.jsonl');out={}
  for key,c in rows:
   p=pp_as_fraction(c,6)
   if p:addto(out,key,p)
  out=clean(out);method='polynomial projection of complete saved stage five'
 else:
  rows=load(folder/'stage4.jsonl');out=project_stage5(rows);method='direct projected stage-five integration, all endpoint constants retained'
 dump(path,out)
 (folder/'growth_stage5_report.json').write_text(json.dumps({'complete':True,'method':method,'output_rows':len(out),'source':str(folder/'stage4.jsonl'),'source_sha256':hashlib.sha256((folder/'stage4.jsonl').read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(path.read_bytes()).hexdigest()},indent=2));print('PREPARED_GROWTH',folder.name,len(out),flush=True)

if __name__=='__main__':
 if sys.argv[1]=='check':
  folder=Path(sys.argv[2]);reference={}
  for key,c in load(folder/'stage5.jsonl'):
   p=pp_as_fraction(c,6)
   if p:addto(reference,key,p)
  reference=clean(reference);got=project_stage5(load(folder/'stage4.jsonl'));dif=got.copy()
  for k,v in reference.items():addto(dif,k,-v)
  assert not clean(dif),len(clean(dif))
  report={'folder':str(folder),'source_rows':sum(1 for _ in (folder/'stage4.jsonl').open()),'output_rows':len(got),'full_then_project_equal_to_projected_integration':True}
  (ROOT/'data/projected_stage_check.json').write_text(json.dumps(report,indent=2));print('PROJECTED_CHECK_PASS',report,flush=True)
 else:prepare(sys.argv[1])
