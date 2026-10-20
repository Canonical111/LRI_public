"""Exact full-constant boundary functional, before cutoff substitution.
Computes [e^0 log(e)^0] integral_0^(1/e-N) (1-e(N+T)) R(T)G_w(T)dT.
Proper rational primitives vanish at the upper endpoint, but their GPL constants
are retained through integrate_basis. No weight projection is used.
"""
from endpoint_growth_finite import *

@lru_cache(None)
def eval_weight(r,k,kappa,N):
 if r<kappa:return s.S.Zero
 d=r-kappa
 if k>d:return s.S.Zero
 a=s.Symbol('a');pol=s.prod(a-j for j in range(d))/s.Integer(factorial(d))
 return s.expand(s.Integer(-N)**d*s.diff(pol,a,k).subs(a,r))

@lru_cache(maxsize=150000)
def upper_word(word,p,kappa,N):
 return s.expand(sum(eval_weight(p-n,k,kappa,N)*big_coefficient(word,n,k)
      for n in range(p-kappa+1) for k in range(min(len(word),p-n-kappa)+1)))

def upper_ant(ant,kappa,idx,N):
 out=0
 for w,c in ant.items():
  word=tuple(int(a) for a in w)
  for p,co in polynomial_part(c,idx).items():
   if p>=kappa:out+=scalar(str(co))*upper_word(word,p,kappa,N)
 return s.expand(out)

@lru_cache(maxsize=15000)
def basis(kin,a,p,ints,idx,N):
 root=K(a);w=tuple(K(v) for v in ints);audit_basis(kin,root,p,w,idx)
 ant=integrate_basis(kin,root,p,w,idx)
 out=upper_ant(ant,0,idx,N)-N*upper_ant(ant,1,idx,N)
 if kin=='poly':extra=integrate_basis('poly',K.zero,p+1,w,idx)
 else:
  extra={}
  if p==1:
   for ww,c in integrate_basis('poly',K.zero,0,w,idx).items():addto(extra,ww,c)
  else:
   for ww,c in integrate_basis('pole',root,p-1,w,idx).items():addto(extra,ww,c)
  for ww,c in ant.items():addto(extra,ww,root*c)
 out-=upper_ant(extra,1,idx,N)
 for w,c in ant.items():
  for ww,cc in endpoint_value(c,w,idx,K.zero,lower=True).items():
   assert not ww;out-=scalar(str(cc))
 return s.expand(out)

def evaluate_source(path,idx,N):
 out={};total=0;st=time.time()
 for line in Path(path).open():
  ww,ll,text=json.loads(line);total+=1;assert all(not w for w in ww[:-1]);word=tuple(int(rm.parseK(a)) for a in ww[-1]);R=rm.parseK(text)
  assert not R.diff(e)
  pol,po=apart(R,idx);val=0
  for p,c in pol.items():val+=scalar(str(c))*basis('poly',0,p,word,idx,N)
  for (a,p),c in po.items():val+=scalar(str(c))*basis('pole',int(a),p,word,idx,N)
  val=s.expand(val*s.prod(s.log(k) for k in ll))
  for term in s.Add.make_args(val):
   cf,mon=term.as_coeff_Mul(rational=True);out[mon]=out.get(mon,s.S.Zero)+cf
  if total%1000==0:print('BOUNDARY_FUNCTIONAL',total,len(out),time.time()-st,flush=True)
 ans=s.Add(*(m*c for m,c in out.items() if c));return ans,{'source_rows':total,'terms':len(s.Add.make_args(ans)),'seconds':time.time()-st,'full_constant_periods_retained':True}

def main(folder,n=8,idx=6):
 folder=Path(folder);value,report=evaluate_source(folder/f'stage{idx-1}.jsonl',idx,n-1)
 (folder/'functional_finite.expr').write_text(s.sstr(value,order='none'))
 if (folder/'finite.expr').exists():
  from read_expression import load as readfull
  difference=s.expand(value-readfull(folder/'finite.expr'));report['exact_difference_zero']=difference==0
  assert not difference,('terminal disagreement',len(s.Add.make_args(difference)))
 report['rational_projection']=str(value.as_coeff_Add()[0]);report['source_sha256']=hashlib.sha256((folder/f'stage{idx-1}.jsonl').read_bytes()).hexdigest()
 (folder/'functional_report.json').write_text(json.dumps(report,indent=2));print('FULL_BOUNDARY_FUNCTIONAL_DONE',report,flush=True)
if __name__=='__main__':main(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 8,int(sys.argv[3]) if len(sys.argv)>3 else 6)
