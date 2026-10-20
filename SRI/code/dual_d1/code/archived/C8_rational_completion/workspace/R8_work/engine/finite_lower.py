"""Fresh finite, formal weight-zero lower responses used in the C8 subtraction.
Variable logarithms are retained; explicit scale logarithms cannot enter ell^0.
This integrates the absolute coordinates for endpoint sources, and otherwise
all consecutive gaps, independently of the cutoff-face residue method.
"""
import tail_boundary as tb
from hyperlog_core import *
from pathlib import Path
import json,hashlib,time,argparse
F=tb.F;ROOT=tb.ROOT;OUT=ROOT/'finite_lower';OUT.mkdir(exist_ok=True)

def setup(n,kind,deriv):
 absolute=kind.startswith('E');dipole=kind.endswith('Q');N=n if absolute else n-1
 coords=[K(i)+GEN[i+1] for i in range(n)] if absolute else [K.zero]+[K(i)+GEN[i] for i in range(1,n)]
 factors=[(coords[j]-coords[i],2*(-1)**(i+j)) for i in range(n) for j in range(i+1,n)]
 if dipole:factors.append((sum((coords[i+1]-coords[i] for i in range(0,n,2)),K.zero),1))
 # The two-kink dipole cancels one power of the very same kernel factor.
 # Combine identical factors before evaluating residues at their roots.
 merged=[]
 for factor,power in factors:
  for j,(other,exponent) in enumerate(merged):
   if factor==other:
    merged[j]=(other,exponent+power);break
  else:merged.append((factor,power))
 factors=[(factor,power) for factor,power in merged if power]
 # Original independently used insertion generator. The explicit log(eps*j)
 # constants project to powers of ell; none can enter this finite ell^0 target.
 old,N0=tb.tb.br.rr._old_initial(n,kind,deriv,kernel=False);assert N==N0;ins={}
 for (words,logs),c in old.items():
  if logs:continue
  ww=tuple(tuple(sub(a,0,K.one) for a in w) for w in words)
  addto(ins,(ww,()),sub(c,0,K.one))
 kap=(n%2)+(1 if dipole else 0)-(0 if absolute else 1)
 return factors,clean(ins),N,kap,absolute

def sources(n,kind,deriv):
 tag=f'{kind}{n}_{deriv}';folder=OUT/tag;folder.mkdir(exist_ok=True)
 fac,ins,N,kap,absolute=setup(n,kind,deriv)
 if n==2:
  rational=K.one
  for factor,power in fac:rational*=factor**power
  pp,po=apart(rational,1)
  blocks=[('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]
 else:blocks=tb.tb.pp_factored(fac)
 meta=[]
 for i,b in enumerate(blocks):
  subf=folder/f'b{i:02d}';subf.mkdir(exist_ok=True);dest=subf/'stage1.jsonl'
  if not dest.exists():ans=tb.tb.first_block(b,ins,N);tb.tb.br.rr.dump(dest,ans);del ans
  meta.append({'id':subf.name,'source_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'rows':sum(1 for _ in dest.open())})
  tb.tb.br.rr.clear();print('FINITE_SOURCE',tag,i,len(blocks),flush=True)
 manifest={'tag':tag,'n':n,'kind':kind,'deriv':deriv,'N':N,'kappa':kap,'absolute':absolute,'blocks':meta,'source_complete':True}
 (folder/'manifest.json').write_text(json.dumps(manifest,indent=2));return manifest

def worker(tag,name):
 folder=OUT/tag/name;meta=json.loads((folder.parent/'manifest.json').read_text());n=meta['n'];N=meta['N'];kap=meta['kappa'];absolute=meta['absolute'];st=time.time()
 if (folder/'result.json').exists():print('FINITE_REUSE',tag,name);return
 for idx in range(2,N-1):
  dest=folder/f'stage{idx}.jsonl'
  if not dest.exists():
   src=tb.tb.br.rr.load(folder/f'stage{idx-1}.jsonl');ans=tb.tb.one_stage(src,idx,N);tb.tb.br.rr.dump(dest,ans);del src,ans;tb.tb.br.rr.clear()
  print('FINITE_STAGE',tag,name,idx,time.time()-st,flush=True)
 items=tb.tb.br.rr.load(folder/f'stage{max(1,N-2)}.jsonl');value=F(0);idx=N-1;count=0
 def endpoint(co,w,other,sgn):
  nonlocal value,count
  scale,num,den=tb.parts(co,N)
  if not scale:return
  H=tb.mt.canon((tb.sb.aword_scaled(w,N),tb.sb.aword_scaled(other,N)))
  v=tb.functional(num,den,H,kap,n-1,0,0)
  if not absolute:
   v-=(n-1)*tb.functional(num,den,H,kap+1,n-1,0,0)
   v-=tb.functional((F(0),)+num,den,H,kap+1,n-1,0,0)
  value+=sgn*scale*v;count+=1
 if N==2:
  for (words,logs),R in items:
   assert not logs and not words[0];endpoint(R,words[-1],(),1)
 else:
  for j,((words,logs),R) in enumerate(items):
   assert not logs and not any(words[:idx-1]);pp,po=apart(R,idx)
   for kin,a,p,pref in [('poly',K.zero,p,c) for p,c in pp.items()]+[('pole',a,p,c) for (a,p),c in po.items()]:
    audit_basis(kin,a,p,words[idx-1],idx)
    for w,c in integrate_basis(kin,a,p,words[idx-1],idx).items():
     for ww,cc in endpoint_value(c,w,idx,GEN[N]).items():endpoint(pref*cc,ww,words[N-1],1)
     for ww,cc in endpoint_value(c,w,idx,K.zero,lower=True).items():
      assert not ww;endpoint(pref*cc,(),words[N-1],-1)
   items[j]=None
   if j%200==0:print('FINITE_TERM',tag,name,j,len(items),value,time.time()-st,flush=True)
 digest=hashlib.sha256((folder/'stage1.jsonl').read_bytes()).hexdigest();result={'tag':tag,'block':name,'status':'complete_block','finite':str(value),'source_sha256':digest,'seconds':time.time()-st,'endpoint_terms':count}
 (folder/'result.json').write_text(json.dumps(result,indent=2));print('FINITE_BLOCK_DONE',result,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--n',type=int);p.add_argument('--kind');p.add_argument('--deriv');p.add_argument('--sources',action='store_true');p.add_argument('--tag');p.add_argument('--block');a=p.parse_args()
 if a.sources:sources(a.n,a.kind,a.deriv)
 else:worker(a.tag,a.block)
