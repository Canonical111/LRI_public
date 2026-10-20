from full_runner import *
import sympy as s, random
import asymptotic_gpl as ag
from fractions import Fraction as F
sys.path.insert(0,'/mnt/data/P8_final_run');import linear_boundary as lb
from functools import lru_cache
from read_expression import parse
@lru_cache(None)
def formal_rseries(text,pmax):
 ex=s.cancel(parse(text));num,den=s.fraction(ex)
 pn=s.Poly(num,ag.E,domain='EX');pd=s.Poly(den,ag.E,domain='EX')
 aa={m[0]:c for m,c in pn.terms() if c};bb={m[0]:c for m,c in pd.terms() if c}
 if not aa:return {}
 v=min(aa)-min(bb);n0=min(aa);d0=min(bb);a={k-n0:c for k,c in aa.items()};b={k-d0:c for k,c in bb.items()};co=[]
 for k in range(max(0,pmax-v+1)):
  cc=(a.get(k,0)-sum(b.get(j,0)*co[k-j] for j in range(1,k+1)))/b[0];co.append(s.expand(cc))
 return {k+v:c for k,c in enumerate(co) if c}
ag.rseries=formal_rseries
random.seed(86291);st=time.time()
def complete(kin,a,p,w,N,kap,iv):
 W=tuple(K(x) for x in w);tmp={};fac=(1-N*e) if iv else K.one
 def append(ki,aa,pp,mult):
  for ww,c in integrate_basis(ki,K(aa),pp,W,6).items():
   cc=sub(c,6,1/e-N)*e**kap*mult
   key=tuple(int(x.as_expr()) for x in ww);addto(tmp,key,cc)
   low=endpoint_value(c,ww,6,K.zero,lower=True)
   for w0,c0 in low.items():
    assert not w0;addto(tmp,(),-e**kap*mult*c0)
 append(kin,a,p,fac)
 if iv:
  if kin=='poly':append('poly',0,p+1,-e)
  else:
   if p==1:append('poly',0,0,-e)
   else:append('pole',a,p-1,-e)
   append('pole',a,p,-e*a)
 rows=[(list(ww),[],str(c)) for ww,c in clean(tmp).items()]
 return ag.extract_rows(rows,N,0,0)
for i in range(180):
 w=tuple(random.choice([0,-1,-2,-4]) for _ in range(random.randint(0,5)));kin=random.choice(['poly','pole']);a=random.choice([0,-1,-2,-3]);p=random.randint(0,3) if kin=='poly' else random.randint(1,4);N=random.randint(2,8);kap=random.choice([-1,0,1]);iv=random.choice([True,False])
 x=s.expand(sum(s.Rational(c.numerator,c.denominator)*ag.Z(tuple(int(a) for a in ww)) for ww,c in lb.functional(kin,a,p,w,N,kap,iv)))
 y=complete(kin,a,p,w,N,kap,iv)
 assert s.expand(x-y)==0,(kin,a,p,w,N,kap,iv,x,y)
 if i%20==0:print('GENERAL_TERMINAL_CHECK',i,time.time()-st,flush=True)
(ROOT/'general_terminal_check.json').write_text(json.dumps({'exact_cases':180,'kappa_values':[-1,0,1],'interval_and_absolute':True,'all_equal':True,'seconds':time.time()-st},indent=2));print('GENERAL_TERMINAL_DONE',flush=True)
