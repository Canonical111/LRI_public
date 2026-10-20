"""Exact difference between full and weight-zero endpoint fibration.
It restores positive-weight *constant* boundary values discarded in an archived
rational-stage calculation. Variable iterated integrals are not projected.
"""
from full_runner import *
@lru_cache(maxsize=4000)
def defect(w,idx):
 if not w:return {}
 X=GEN[idx]
 if all(a in (K.zero,X) for a in w):
  if all(a==K.zero for a in w) or all(a==X for a in w):return {}
  return scaled_phi(tuple(int(a==X) for a in w))
 # All possible nonzero base terms require both literal 0 and X letters.
 if not (K.zero in w and X in w):return {}
 out={};ext=(X,)+w+(K.zero,)
 for i,a in enumerate(w):
  lower=defect(w[:i]+w[i+1:],idx)
  if not lower:continue
  for side,sign,p in [('prev',1,ext[i]-a),('next',-1,ext[i+2]-a)]:
   if not p:
    if side=='prev' and i==0 and a==X:root=K.zero
    else:continue
   else:
    if not p.diff(X):continue
    if p.denom!=K.ring.one or degree(p.numer,idx)!=1:raise ValueError(('nonaffine',p))
    root=-sub(p,idx,K.zero)/p.diff(X)
   for ww,c in lower.items():addto(out,(root,)+ww,sign*c)
 return clean(out)

@lru_cache(maxsize=4000)
def projected_fibration(w,idx):
 if not w:return {():K.one}
 X=GEN[idx]
 if all(a in (K.zero,X) for a in w):return {w:K.one} if all(a==K.zero for a in w) else {}
 out={};ext=(X,)+w+(K.zero,)
 for i,a in enumerate(w):
  lower=projected_fibration(w[:i]+w[i+1:],idx)
  for side,sign,p in [('prev',1,ext[i]-a),('next',-1,ext[i+2]-a)]:
   if not p:
    if side=='prev' and i==0 and a==X:root=K.zero
    else:continue
   else:
    if not p.diff(X):continue
    root=-sub(p,idx,K.zero)/p.diff(X)
   for ww,c in lower.items():addto(out,(root,)+ww,sign*c)
 return clean(out)

def defect_stage(source,idx,N,mult=1):
 out={};n=0;candidate=0;st=time.time()
 for line in source.open():
  ww,ll,ct=json.loads(line);n+=1
  if isinstance(ll,int):assert ll==0;ll=[]
  if not ('0' in ww[idx-1] or str(GEN[idx+1]) in ww[idx-1]):continue
  words=tuple(tuple(rm.parseK(a) for a in w) for w in ww);active=words[idx-1]
  # A new letter in an elementary primitive is either an existing active
  # letter or a root of R. Both 0 and the next endpoint must be present
  # for a positive-weight coalescence constant.
  need = K.zero if K.zero not in active else (GEN[idx+1] if GEN[idx+1] not in active else None)
  if need is not None:
   if ')/' in ct:
    denominator=ct.rsplit(')/',1)[1]
   elif '/' in ct:
    denominator=ct.split('/',1)[1]
   else:continue
   invden=rm.parseK('1/('+denominator+')')
   possible=False
   for factor,factor_exponent in invden.denf.items():
    if degree(factor,idx)>0 and not psub(factor,idx,need):possible=True;break
   if not possible:continue
  R=rm.parseK(ct);candidate+=1
  pp,po=apart(R,idx)
  for kin,a,p,pref in [('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]:
   for wa,c in integrate_basis(kin,a,p,active,idx).items():
    if not (K.zero in wa and GEN[idx+1] in wa):continue
    for wb,cb in endpoint_value(c,wa,idx,GEN[idx+1]).items():
     for wf,mu in defect(wb,idx+1).items():
      for wn,mv in shuffle(wf,words[idx]).items():
       keys=list(words);keys[idx-1]=();keys[idx]=wn;addto(out,(tuple(keys),tuple(ll)),mult*pref*cb*mu*mv)
  if candidate%100==0:out=clean(out);print('DEFECT',source.parent.name,idx,'candidates',candidate,'output',len(out),time.time()-st,flush=True)
 return clean(out),{'source':str(source),'rows':n,'candidates':candidate,'output':len(clean(out)),'seconds':time.time()-st}

if __name__=='__main__':
 if sys.argv[1]=='check':
  import random
  random.seed(13);letters=[K.zero,GEN[5],K(-2),GEN[5]+1,GEN[6]+2]
  n=0
  for size in range(1,6):
   for j in range(35):
    w=tuple(random.choice(letters) for _ in range(size))
    a=endpoint_fibrate(w,5);b=projected_fibration(w,5);d=defect(w,5);test=a.copy()
    for ww,c in b.items():addto(test,ww,-c)
    for ww,c in d.items():addto(test,ww,-c)
    assert not clean(test),(w,test);n+=1
  print('EXACT_DEFECT_CHECK',n,flush=True)
 else:
  kind=sys.argv[1];n=int(sys.argv[2]);N=n if kind=='EA' else n-2
  base=Path('/mnt/data/P8_final_run/rational_stages/C8_rational_completion/workspace/R8_work')
  folder=(base/'endpoint_odd') if kind=='EA' else base/'tail_blocks'/f'{kind}_base'
  dest=ROOT/f'F4_defects_{kind}{n}';dest.mkdir(exist_ok=True)
  for idx in range(2,N-1):
   output={};records=[]
   for src in sorted(folder.glob(('EA'+str(n)+'_b*' if kind=='EA' else 'n'+str(n)+'_f*_b*')+'/stage'+str(idx-1)+'.jsonl')):
    if kind=='EA':mu=1
    else:
     face=int(src.parent.name.split('_')[1][1:]);mu=1 if (n-1)%2 and face==n//2 else 2
    ans,report=defect_stage(src,idx,N,mu);records.append(report)
    for key,c in ans.items():addto(output,key,c)
    output=clean(output);clear();defect.cache_clear()
   output=clean(output);dump(dest/f'defect_stage{idx}.jsonl',output)
   (dest/f'report{idx}.json').write_text(json.dumps({'rows':len(output),'inputs':records,'all_constant_periods_retained':True},indent=2))
   print('TOTAL_DEFECT_STAGE',kind,n,idx,len(output),flush=True)
