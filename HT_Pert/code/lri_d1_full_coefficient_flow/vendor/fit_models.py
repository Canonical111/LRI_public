"""Target-excluded asymptotic fits, high-precision QR, explicit source roles.
Physical high-order targets are NEVER read by this module. Source amplitudes are
nuisance estimates from finite-cutoff data, not declared known exact kernels.
"""
from pathlib import Path
from functools import lru_cache
import json,math,time,os,argparse
import mpmath as mp
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def val(x):return mp.mpf(str(x))

def limits23():
 A=mp.pi+4*mp.log(2)
 return {2:A/9,3:(mp.pi**2+6*mp.pi*mp.log(2)+12*mp.log(2)**2-6*mp.gamma(mp.mpf('.25'))**4/mp.pi)/81}

@lru_cache(None)
def exactc2(L,dps):
 v=mp.mpf(1);total=mp.mpf(0)
 for n in range(L-1):
  if n:v*=mp.mpf(2*n-1)/(2*n)
  if n%2:continue
  nn=mp.mpf(n)
  total+=v*(mp.mpf(2)/81/(nn-mp.mpf('.5'))+mp.mpf(2)/9/(nn+mp.mpf('.5'))+mp.mpf(2)/81/(nn+1)+(mp.mpf(2)/9/nn if n else 0))
 return total

def expo(ell,w,d):
 e=[mp.mpf(1)]+[mp.mpf(0)]*d
 for k in range(1,d+1):e[k]=ell*sum(j*w.get(j,0)*e[k-j] for j in range(1,k+1))/k
 return e

def integral_expo(ell,w,d):
 # [epsilon^d] integral_0^ell exp(t Omega(epsilon)) dt
 power=[mp.mpf(1)]+[mp.mpf(0)]*d;answer=mp.mpf(0)
 for k in range(d+1):
  answer+=power[d]*ell**(k+1)/mp.factorial(k+1)
  power=[sum(power[j]*w.get(n-j,0) for j in range(n)) for n in range(d+1)]
 return answer

BASES={'S':[(1,0),(1.5,0)],'A':[(1,0),(1.5,0),(1.5,1),(2,0)],'B':[(1,0),(1.5,0),(1.5,1),(2,0),(2,1)],'C':[(1,0),(1,1),(1.5,0),(1.5,1)],'E':[(1,0),(1,1),(1.5,0),(1.5,1),(2,0),(2,1)],'E2':[(1,0),(1,1),(1,2),(1.5,0),(1.5,1),(2,0),(2,1)]}

def subcolumns(L,base):
 ell=mp.log(L)
 if base.startswith('lattice'):
  name=base.removeprefix('lattice');name=name or 'E'
  M=mp.mpf(L)/2
  u1=-6*((mp.digamma(M)+mp.euler)/18+mp.mpf(2)/9*(mp.digamma(M+mp.mpf('.25'))-mp.digamma(mp.mpf('.25')))+(mp.digamma(M+mp.mpf('.5'))-mp.digamma(mp.mpf('.5')))/18-(ell+mp.euler)/3-limits23()[2])
  t=exactc2(L,mp.mp.dps)-limits23()[2]
  u15=(t+mp.mpf(40)/(81*mp.sqrt(mp.pi*L)))/(-mp.mpf(5)/(27*mp.sqrt(mp.pi)))
  return [{1:u1,1.5:u15,2:u1*u1}[p]*ell**j for p,j in BASES[name]]
 return [mp.power(L,-val(p))*ell**j for p,j in BASES[base]]

def qr_fit(X,y):
 X=mp.matrix(X);y=mp.matrix(y);m,n=X.rows,X.cols
 if m<n+2:raise ValueError(f'Too few samples ({m} rows, {n} columns)')
 scales=[mp.sqrt(mp.fsum(X[i,j]**2 for i in range(m))) for j in range(n)]
 if any(v==0 for v in scales):raise ValueError('Zero design column')
 A=mp.matrix([[X[i,j]/scales[j] for j in range(n)] for i in range(m)])
 coeff,_=mp.qr_solve(A,y);coeff=mp.matrix([coeff[j]/scales[j] for j in range(n)])
 res=X*coeff-y
 # Input-noise sensitivity, not made small by large mp.dps.
 row=mp.lu_solve(A.T*A,mp.matrix([1]+[0]*(n-1)))
 influence=[sum(row[j]*A[i,j] for j in range(n))/scales[0] for i in range(m)]
 cond=float(np.linalg.cond(np.array(A.tolist(),dtype=float)))
 return list(coeff),dict(n=m,ncols=n,condition=cond,residual=float(max(abs(v) for v in res)),intercept_l1=float(sum(abs(v) for v in influence)))

def sequential(data,gaps,scheme,lo,hi,maxorder,base,mode,validation_hi=None,anchor='exactC2'):
 raw=data[scheme];D={int(L):{int(k):val(v) for k,v in row.items()} for L,row in raw.items()}
 for L in D:
  if 2 in D[L]:D[L][2]=exactc2(L,mp.mp.dps)
 known=limits23();w={int(k):val(v) for k,v in gaps.items()};w[6]=mp.mpf(0)
 source={};out={};coefs={};predicted={}
 # Independently fit the finite C3 tail with its exact continuum limit held fixed.
 # This enables genuine whole-cutoff withholding, not just conditioning on the
 # actual lower-order values at the withheld points.
 h3=hi if isinstance(hi,int) else hi.get(3,hi.get(4))
 t3=validation_hi if isinstance(validation_hi,int) else (validation_hi or {}).get(3,h3)
 ls3=sorted(L for L,row in D.items() if lo<=L<=h3 and 3 in row)
 def row3(L):return [exactc2(L,mp.mp.dps)-limits23()[2]]+subcolumns(L,base)
 def y3(L):return D[L][3]-known[3]+w[1]*mp.log(L)*(exactc2(L,mp.mp.dps)-known[2])
 beta3,info3=qr_fit([row3(L) for L in ls3],[y3(L) for L in ls3])
 for L in sorted(L for L,row in D.items() if h3<L<=t3 and 3 in row):
  predicted[L]={2:exactc2(L,mp.mp.dps),3:known[3]+sum(a*b for a,b in zip(row3(L),beta3))-w[1]*mp.log(L)*(exactc2(L,mp.mp.dps)-known[2])}
 for order in range(4,maxorder+1):
  end=hi if isinstance(hi,int) else hi.get(order)
  cutoff_hi=validation_hi if isinstance(validation_hi,int) else (validation_hi or {}).get(order,end)
  allL=sorted(L for L,row in D.items() if lo<=L<=end and order in row)
  if not allL:raise ValueError('No samples')
  tests=sorted(L for L,row in D.items() if end<L<=cutoff_hi and order in row)
  # Unknown omega6 in C8 cannot be fixed from the supplied independent gap data.
  free_omega=(order==8) or (mode=='free_omega' and order>=5)
  new_source=(mode=='source5' and order==5) or (mode=='sources567' and 5<=order<=7)
  if free_omega:w[order-2]=mp.mpf(0)
  def row(L):
   ell=mp.log(L);t=exactc2(L,mp.mp.dps)-limits23()[2]
   z=[mp.mpf(1),t]+subcolumns(L,base)
   if new_source:z.append(ell/mp.sqrt(L))
   if free_omega:z.append(-ell*t)
   return z
  def transported(L):
   return sum(a*integral_expo(mp.log(L),w,order-s)/mp.sqrt(L) for s,a in source.items() if s<=order)
  def y(L):
   ell=mp.log(L);e=expo(ell,w,order-2)
   return D[L][order]+sum(e[j]*(D[L][order-j]-known[order-j]) for j in range(1,order-1))-transported(L)
  beta,info=qr_fit([row(L) for L in allL],[y(L) for L in allL]);known[order]=beta[0]
  pred=[];fullpred=[]
  for L in tests:
   result=sum(a*b for a,b in zip(row(L),beta))+transported(L)
   e=expo(mp.log(L),w,order-2)
   result-=sum(e[j]*(D[L][order-j]-known[order-j]) for j in range(1,order-1))
   pred.append(dict(L=L,predicted=float(result),observed=float(D[L][order]),error=float(result-D[L][order]),conditional_on_measured_lower_orders=True))
   if L in predicted and all(order-j in predicted[L] for j in range(1,order-1)):
    uncond=sum(a*b for a,b in zip(row(L),beta))+transported(L)
    uncond-=sum(e[j]*(predicted[L][order-j]-known[order-j]) for j in range(1,order-1))
    predicted[L][order]=uncond
    fullpred.append(dict(L=L,predicted=float(uncond),observed=float(D[L][order]),error=float(uncond-D[L][order]),conditional_on_measured_lower_orders=False))
  if new_source:source[order]=beta[-1]
  if free_omega:w[order-2]=beta[-1]
  coefs[order]=beta
  out[order]=dict(intercept=mp.nstr(beta[0],40),coefficients=[mp.nstr(x,35) for x in beta],train_min=min(allL),train_max=max(allL),heldout=pred,heldout_whole_cutoff=fullpred,**info)
 return dict(scheme=scheme,lo=lo,hi=hi,maxorder=maxorder,base=base,model=mode,orders=out,third_order_control=dict(coefficients=[mp.nstr(z,35) for z in beta3],**info3),source_amplitudes={str(k):mp.nstr(v,35) for k,v in source.items()},omega_used={str(k):mp.nstr(v,35) for k,v in w.items()},scope='Exact sourced response algebra conditional on the leading-tail equation. Fitted source amplitudes are not exact asymptotic coefficients; individual fits are not confidence intervals.')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--dps',type=int,default=60);ap.add_argument('--scheme',nargs='+',default=['dconn']);ap.add_argument('--lo',nargs='+',type=int,default=[24,40]);ap.add_argument('--hi',type=int,default=92);ap.add_argument('--test-hi',type=int,default=118);ap.add_argument('--order',type=int,default=5);ap.add_argument('--bases',nargs='+',default=['A','E','latticeE']);ap.add_argument('--models',nargs='+',default=['homogeneous','source5','sources567','free_omega']);ap.add_argument('--output',type=Path,default=ROOT/'results/models');a=ap.parse_args();mp.mp.dps=a.dps
 data=json.loads((ROOT/'inputs/scheme_data.json').read_text());gaps=json.loads((ROOT/'inputs/independent_gap_inputs.json').read_text())['extended'];a.output.mkdir(exist_ok=True,parents=True)
 for scheme in a.scheme:
  for lo in a.lo:
   for base in a.bases:
    for mode in a.models:
     name=f'{scheme}_lo{lo}_hi{a.hi}_k{a.order}_{base}_{mode}';t=time.perf_counter()
     try:o=sequential(data,gaps,scheme,lo,a.hi,a.order,base,mode,a.test_hi);o.update(status='completed',dps=a.dps,seconds=time.perf_counter()-t)
     except Exception as e:o=dict(status='failed',error=repr(e),scheme=scheme,lo=lo,hi=a.hi,base=base,model=mode,maxorder=a.order)
     (a.output/(name+'.json')).write_text(json.dumps(o,indent=2,allow_nan=False)+'\n')
     if o['status']=='completed':print(name,{k:(float(v['intercept']),max([abs(r['error']) for r in v['heldout']],default=0),v['condition']) for k,v in o['orders'].items()},flush=True)
     else:print(name,o,flush=True)
if __name__=='__main__':main()
