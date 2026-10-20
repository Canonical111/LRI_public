from read_expression import load as load_expr
"""Assemble all six new beta sectors from the exact regulated responses.
No ansatz for C6 or transcendental constants is used.
"""
from pathlib import Path
from functools import lru_cache
import sympy as s,json,time,sys
import moment_series as ms
ROOT=Path(__file__).resolve().parent
v,d=s.symbols('v d');ell=ms.ell
rawf={}
for n,ks in [(1,['A','EA']),(2,['Z','Q','EZ','EQ']),(3,['A','EA']),(4,['Z','Q','EZ','EQ']),(5,['A','EA']),(6,['Z','Q']),(7,['A'])]:
 for k in ks:rawf[f'{k}{n}']=s.Function(f'{k}{n}')(v,d)
A1=1;EA1=-2/(1+d)
A3=rawf['A3'];A5=rawf['A5'];A7=rawf['A7'];Z2=rawf['Z2'];Z4=rawf['Z4'];Z6=rawf['Z6'];Q2=rawf['Q2'];Q4=rawf['Q4'];Q6=rawf['Q6']
EA3=rawf['EA3'];EA5=rawf['EA5'];EZ2=rawf['EZ2'];EZ4=rawf['EZ4'];EQ2=rawf['EQ2'];EQ4=rawf['EQ4']
norms={
 'C3':A3-Z2,
 'C5':A5-A3*Z2+Z2**2-Z4,
 'C7':A7-A5*Z2+A3*(Z2**2-Z4)-Z2**3+2*Z2*Z4-Z6,
 'Q2':Q2,'K4':Q4-Q2*Z2,
 'K6':Q6-Q4*Z2+Q2*(Z2**2-Z4),
 'EC3':EA3-EA1*Z2-EZ2,
 'EC5':EA5-EA3*Z2-A3*EZ2+EA1*(Z2**2-Z4)+2*Z2*EZ2-EZ4,
 'EQ2':EQ2,'EK4':EQ4-EQ2*Z2-Q2*EZ2,
}
DERIV={(0,0):'base',(1,0):'v',(2,0):'vv',(3,0):'vvv',(0,1):'d',(1,1):'vd',(2,1):'vvd',(0,2):'dd'}

def cutadd(a,b):
 out=a.copy()
 for p,c in b.items():out[p]=out.get(p,0)+c
 return out

def cutmul(a,b):
 out={}
 for p,c in a.items():
  for q,h in b.items():
   if -6<=p+q<=4:out[p+q]=out.get(p+q,0)+c*h
 return out

@lru_cache(maxsize=None)
def rawcut(name,iv=0,idd=0):
 k=name.rstrip('0123456789');n=int(name[len(k):]);der=DERIV[iv,idd]
 # Cutoff powers needed by every normalization in this calculation.
 if n==7 or n==6:return {0:ms.pol(n,k,der,0)}
 if n==5:
  pmin=-2;pmax=1 if (iv,idd)==(0,0) and not k.startswith('E') else 0
 elif n==4:pmin=-2;pmax=1
 elif n==3:pmin=-1;pmax=2
 elif n==2:pmin=-1;pmax=2
 else:raise ValueError(name)
 return {p:ms.pol(n,k,der,p) for p in range(pmin,pmax+1)}

@lru_cache(maxsize=None)
def evalraw(ex):
 if ex.is_Add:
  out={}
  for term in ex.args:out=cutadd(out,evalraw(term))
  return out
 if ex.is_Mul:
  out={0:s.S.One}
  for term in ex.args:out=cutmul(out,evalraw(term))
  return out
 if ex.is_Pow and ex.exp.is_Integer and ex.exp>=0:
  out={0:s.S.One}
  for _ in range(int(ex.exp)):out=cutmul(out,evalraw(ex.base))
  return out
 if isinstance(ex,s.Derivative):
  f=ex.expr;co=dict(ex.variable_count)
  return rawcut(str(f.func),int(co.get(v,0)),int(co.get(d,0)))
 if ex.is_Function and str(ex.func) in rawf:return rawcut(str(ex.func))
 return {0:ex.subs({v:1,d:0})}

@lru_cache(maxsize=None)
def npol(name,iv=0,idd=0):
 fp=ROOT/'series'/f'norm_{name}_{iv}_{idd}.expr'
 if fp.exists():return load_expr(fp)
 ex=s.diff(norms[name],v,iv,d,idd)
 ans=s.expand(evalraw(ex).get(0,0))
 ans=s.expand_log(ans,force=True).expand()
 fp.write_text(s.sstr(ans, order="none"));print('NORM',name,iv,idd,'terms',len(s.Add.make_args(ans)),flush=True)
 return ans

# Formal finite/single-log moments, evaluated only when the demanded beta jet needs them.
f=lambda name,m: s.Function(name+('_f' if m==0 else '_l'))(v,d)
C30=f('C3',0);C31=f('C3',1);C50=f('C5',0);C51=f('C5',1);C71=f('C7',1)
Q20=f('Q2',0);K40=f('K4',0);K41=f('K4',1);K61=f('K6',1)
EC30=f('EC3',0);EC50=f('EC5',0);EQ20=f('EQ2',0);EK40=f('EK4',0)
j1=-2/(1+d)
j3=-2*s.diff(C30,v)+EC30;j5=-2*s.diff(C50,v)+EC50
l2=-2*Q20-4*v*s.diff(Q20,v)+2*v*EQ20
l4=-2*K40-4*v*s.diff(K40,v)+2*v*EK40
b3=C31+2*v*j1
h4=K41-2*Q20*b3+l2
b5=C51-3*C30*b3-2*v*j1*h4+2*v*j3
h6=K61-2*Q20*b5-4*K40*b3-l2*h4+l4
b7=C71-3*C30*b5-5*C50*b3-2*v*j1*h6-2*v*j3*h4+2*v*j5

@lru_cache(maxsize=None)
def evalnormf(ex):
 if isinstance(ex,s.Derivative):
  f0=ex.expr;co=dict(ex.variable_count);name=str(f0.func);iv=int(co.get(v,0));idd=int(co.get(d,0))
 else:name=str(ex.func);iv=idd=0
 stem,kind=name.rsplit('_',1);m=0 if kind=='f' else 1
 return npol(stem,iv,idd).coeff(ell,m)

def betaexpr(ex,label):
 fp=ROOT/(label+'_symbolic.expr')
 if fp.exists():return load_expr(fp)
 start=time.time();atoms=ex.atoms(s.Derivative)
 mapping={x:evalnormf(x) for x in atoms}
 ex=ex.xreplace(mapping)
 mapping={x:evalnormf(x) for x in ex.atoms(s.Function) if str(x.func).endswith(('_f','_l'))}
 ans=s.expand_log(ex.xreplace(mapping).subs({v:1,d:0}),force=True).expand()
 fp.write_text(s.sstr(ans, order="none"))
 print('BETA',label,'terms',len(s.Add.make_args(ans)),'seconds',time.time()-start,flush=True)
 return ans

needed={
 'a_check':s.diff(b3,v), 'p_check':s.diff(b3,d), 'A_check':s.diff(b3,v,2)/2,'E_check':s.diff(b3,v,d),
 'c_check':-4*h4, 'f_check':-4*s.diff(h4,v), 'q_check':-4*s.diff(h4,d),
 'b_check':b5,'G_check':s.diff(b5,v),'k_check':-4*h6,
 'L':-2*s.diff(h4,v,2),'M':-4*s.diff(h4,v,d),
 'R':s.diff(b5,d),'N':-4*s.diff(h6,v),'J':b7}

if __name__=='__main__':
 which=sys.argv[1:] or list(needed)
 for name in which:
  try:betaexpr(needed[name],name)
  except FileNotFoundError as e:print('MISSING for',name,str(e),flush=True)
 print('finished available assemblies',flush=True)
