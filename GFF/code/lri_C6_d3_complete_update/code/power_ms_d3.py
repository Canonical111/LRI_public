"""Dimension-three MS pole audit using Gamma products and the established
A/B/T kite jets. Only closed raw graphs, subgraphs and cographs are accepted.
A supplied kite Taylor remainder is never silently set to zero where needed.
"""
from pathlib import Path
import sys,json,inspect,itertools,time
from fractions import Fraction as F
from collections import Counter
from functools import lru_cache
import mpmath as mp
W=Path(__file__).resolve().parents[1]
BASE=W/'vendor'
sys.path.insert(0,str(BASE))
import position_ms as pm
from position_ms import Unsolved,Singular,canon,normalized,uvsubs,forestsets,quotient,rootsafe,vertices,gcadd
mp.mp.dps=int(__import__('os').environ.get('POWER_DPS','75'));pm.K=10
D=F(__import__('os').environ.get('POWER_DIM','3'));NORM=D/2;ZERO=(F(0),F(0))
def pair(x,y=0):return F(x),F(y)
def plus(*ps):return tuple(sum(p[i] for p in ps)for i in (0,1))
def scale(p,a):return tuple(v*a for v in p)
def neg(p):return scale(p,-1)
def sub(a,b):return plus(a,neg(b))
def M(x):return mp.mpf(x.numerator)/x.denominator if isinstance(x,F)else mp.mpf(x)
INV=json.load(open(W/'inputs/classified_inventory.json'))
ROW={canon(g['edges']):g for row in INV['loops']for g in row['graphs']}
# Input master values are used only as common values in both sides of the audit.
Q=mp.mpf(__import__('os').environ.get('POWER_Q','5.01710256455385536959085484569018369956'))
P4=mp.mpf(__import__('os').environ.get('POWER_P4','62.05832794340667246646338858409673691827'))
P5=mp.mpf('240.34031775908354981636654638800359825615')
KAP=mp.mpf(__import__('os').environ.get('POWER_KAP','1.148594649527'));Z=mp.mpf(__import__('os').environ.get('POWER_Z','8.82092489306'))
q=M(D)/4
A=mp.digamma(2*q)+mp.digamma(1)-2*mp.digamma(q)
R=mp.polygamma(1,2*q)-mp.polygamma(1,1);U=mp.polygamma(2,q);V=mp.polygamma(2,1)+mp.polygamma(2,2*q)
origbf=pm.betafactors;origgs=pm.gammaseries

def betafactors(u,v):
 pref,g=origbf(u,v)
 gg=Counter({(r*NORM,s):n for (r,s),n in g.items()});gg[(NORM,F(0))]+=1
 return pref,gg,()

def complete(ps):return pm.complete(ps)
def mapped(ps,pp):
 lam=complete(ps)
 return tuple(lam[pp[i]]for i in [1,4,2,5,7])
TEMPLATES={(F(1,2),)*4+(F(1),):'A',(F(1,2),)*3+(F(1),F(1,2)):'B',(F(1,2),)*5:'T'}

CORE_PS=(pair(F(1,2),F(-1,2)),pair(1,-1),pair(1,-1),pair(F(1,2),F(-1,2)),pair(F(1,2),F(-1,2)))
CORE_ED=tuple(sorted([(0,1),(0,2),(0,3),(0,3),(1,2),(1,2),(1,3)]))
CORE_ROOTS=(2,3)
CORE_KEYS={mapped(CORE_PS,pp)for pp in pm.PERMS}
CORE_U0=mp.mpf(__import__('os').environ.get('CORE_U0','0'))
CORE_U1=mp.mpf(__import__('os').environ.get('CORE_U1','0'))
@lru_cache(None)
def choices(ps):
 opts=[];seen=set()
 if ps in CORE_KEYS:return (('CORE',ps),)
 for pp in pm.PERMS:
  xx=mapped(ps,pp)
  if xx in seen:continue
  seen.add(xx)
  tag=TEMPLATES.get(tuple(p[0]for p in xx))
  if tag:opts.append((tag,xx))
 return tuple(opts)

@lru_cache(None)
def masterfactors(ps):
 # Exact completion zero, not merely a zero at the expansion point.
 for pp in pm.PERMS:
  xx=mapped(ps,pp)
  if xx[-1]==ZERO:
   try:
    p,g,_=betafactors(xx[0],xx[1]);p1,g1,_=betafactors(xx[2],xx[3]);gg=gcadd(g,g1)
    if any(r.denominator==1 and r<=0 and s==0 for (r,s),n in gg.items()if n):continue
    return p*p1,gg,()
   except(Singular,ZeroDivisionError):pass
 if not choices(ps):raise Unsolved('unknown critical kite pattern '+str(tuple(p[0]for p in ps)))
 return F(1),Counter(),(ps,)

def combine(f,g):return f[0]*g[0],gcadd(f[1],g[1]),f[2]+g[2]
# Use the actual graph recursion of the preserved position-space engine.
s=inspect.getsource(pm.rawfactors.__wrapped__)
s=s.replace('return (F(1),Counter())','return (F(1),Counter(),())')
s=s.replace('if sg)))','if sg)),tuple(ff[2]))')
exec(s,globals())
oldraw=rawfactors
from scaleless_leaf import leaf
@lru_cache(None)
def rawfactors(ed,roots):
 if leaf(ed,roots):return F(0),(),()
 return oldraw(ed,roots)

def add(*ss):
 out={}
 for s in ss:
  for k,v in s.items():out[k]=out.get(k,mp.mpf(0))+v
 return out

def mul(s,t,hi=9):
 out={}
 for i,a in s.items():
  for j,b in t.items():
   if -8<=i+j<=hi:out[i+j]=out.get(i+j,mp.mpf(0))+a*b
 return out

def scal(s,c):return {k:c*v for k,v in s.items()}
def aff(p):return {0:M(p[0]),1:M(p[1])}
def invaff(p):
 if not p[0]:
  if not p[1]:raise Singular('identically zero affine denominator')
  return {-1:1/M(p[1])}
 return {k:(-M(p[1]))**k/M(p[0])**(k+1)for k in range(10)}

def bseries(a,b):
 # a,b are absolute-distance exponents, not half-exponents.
 u=scale(a,F(1,2));v=scale(b,F(1,2));g=Counter()
 for x in [pair(D/2),sub(pair(D/2),u),sub(pair(D/2),v),plus(u,v,pair(-D/2))]:g[x]+=1
 for x in [u,v,sub(pair(D),plus(u,v))]:g[x]-=1
 ga=tuple(sorted((r,s,n)for (r,s),n in g.items()if n))
 z=origgs((F(1),ga))
 return {k+1:v for k,v in z.items()}

@lru_cache(None)
def masterjet(ps):
 failures=[]
 for tag,xx in choices(ps):
  try:
   if tag=='CORE':return corejet(),tag,1
   a,b,c,f,e=[(D*p[0],p[1])for p in xx]
   if tag=='T':
    lam=complete(xx);norm=sum(M(p[1])**2 for p in lam)
    return {0:3*Q,1:mp.mpf(0),2:Z*norm/4},tag,2
   if tag=='A':
    t=sub(pair(D),e);p0=sub(pair(2*D),plus(a,c,e));p1=sub(pair(2*D),plus(b,f,e));u=scale(sub(a,c),F(1,2));v=scale(sub(b,f),F(1,2));sig=plus(p0,p1)
    pa=add(scal(mul(invaff(p0),bseries(sub(scale(plus(pair(D),t),F(1,2)),u),sub(pair(D),t))),2),
           scal(mul(invaff(p1),bseries(sub(scale(plus(pair(D),t),F(1,2)),v),sub(pair(D),t))),2),
           scal(mul(invaff(t),bseries(sub(pair(D),p0),sub(pair(D),p1))),2),
           scal(mul(invaff(t),add(invaff(p0),invaff(p1))),-4))
    rem=add(scal(aff(sig),A*R/2+U/8),scal(mul(aff(t),aff(sig)),A*A*R/8+A*U/16-R*R/8),scal(mul(aff(sig),aff(sig)),-A*V/8))
    out=add(pa,rem)
   else:
    p1=sub(pair(D),f);p2=sub(pair(2*D),plus(b,f,e));z1=sub(pair(3*D),plus(a,b,c,f,e));z2=sub(pair(2*D),plus(c,f,e))
    g2=mul(bseries(sub(plus(pair(D),p1),e),sub(pair(D),p1)),bseries(sub(plus(e,p2),z1),sub(pair(D),p2)))
    g1=mul(bseries(plus(e,neg(p1),p2,z2),plus(pair(D),p1,neg(e),neg(z2))),bseries(plus(pair(D),p1,neg(e),neg(p2)),sub(pair(D),p1)))
    g0=mul(bseries(sub(plus(pair(D),p1),e),sub(pair(D),p1)),bseries(plus(e,p2),sub(pair(D),p2)))
    db=add(bseries(plus(e,p2,z2,neg(z1)),sub(pair(D),p2)),scal(bseries(plus(e,p2,neg(z1)),sub(pair(D),p2)),-1),scal(bseries(plus(e,p2,z2),sub(pair(D),p2)),-1),bseries(plus(e,p2),sub(pair(D),p2)))
    out=add(g2,g1,scal(g0,-1),scal(mul(invaff(p1),db),2),scal(mul(aff(z1),aff(z2)),KAP))
   return {k:v for k,v in out.items()if k<=2},tag,2
  except(Singular,ZeroDivisionError,ValueError)as ex:failures.append(str(ex))
 raise Unsolved('no nonsingular A/B/T chart: '+str(failures[:2]))

class Series(dict):
 def __init__(self,x,known=99):super().__init__(x);self.known=known

def minpower(s):
 return min((k for k,v in s.items()if abs(v)>mp.mpf('1e-50')),default=0)
@lru_cache(None)
def gammaseries(ff):
 pref,ga,jj=ff
 if not pref:return Series({},99)
 gs=origgs((pref,ga));known=minpower(gs)+pm.K
 for ps in jj:
  js,tag,jmax=masterjet(ps);known=min(known+minpower(js),minpower(gs)+jmax);gs=mul(gs,js)
 return Series(gs,known)

C={};META={};FAIL={}
@lru_cache(None)
def ct(ed):
 ed=normalized(ed);key=canon(ed)
 if key in C:return C[key]
 if key in FAIL:raise Unsolved(FAIL[key])
 L=len(ed)//2;reason=[]
 gid=ROW.get(key,{}).get('id')
 if gid in ('L6G106','L6G117'):
  mm=mp.gamma(-q)*mp.gamma(2*q)**2/mp.gamma(3*q)
  C[key]={-1:-mm*P4/3};META[key]={'roots_tested':0,'root_error':'0','tags':['exact sunset contraction on primitive wheel']}
  return C[key]

 try:
  subc={ss:ct(ee)for ss,ee in uvsubs(ed)}
  vals=[]
  for rr in rootsafe(ed):
   try:
    ff=rawfactors(ed,rr);raw=gammaseries(ff)
    if raw.known < -1:raise Unsolved('raw jet known only through '+str(raw.known))
    out=raw;tags=[masterjet(x)[1]for x in ff[2]]
    for fs in forestsets(ed):
     qd,qr=quotient(ed,[ss for ss,ee in fs],rr)
     ffq=rawfactors(qd,qr);tmp=gammaseries(ffq);prod={0:mp.mpf(1)}
     for ss,ee in fs:prod=mul(prod,subc[ss])
     if tmp.known+minpower(prod)<-1:raise Unsolved('quotient insufficient jet order '+str(tmp.known)+' versus '+str(minpower(prod)))
     out=add(out,mul(tmp,prod))
    poles={k:-v for k,v in out.items()if k<0};vals.append((rr,poles,tags))
   except(Unsolved,Singular,ValueError,ZeroDivisionError)as ex:reason.append(str(ex))
  if not vals:raise Unsolved(';'.join(sorted(set(reason)))[:500]or'no admissible roots')
  res=vals[0][1];err=max((abs(v-res.get(k,0))for rr,z,tg in vals for k,v in z.items()),default=mp.mpf(0))
  if err>mp.mpf('1e-35'):raise RuntimeError(('root mismatch',ROW.get(key,{}).get('id'),mp.nstr(err,10),vals))
  C[key]=res;META[key]={'roots_tested':len(vals),'root_error':str(err),'tags':vals[0][2]}
  return res
 except Unsolved as ex:FAIL[key]=str(ex);raise

@lru_cache(None)
def corejet():
 # The poles of the unintegrated two-point core are fixed by its proper
 # logarithmic subtractions; its finite and linear jets remain arbitrary.
 out={}
 for fs in forestsets(CORE_ED):
  qd,qr=quotient(CORE_ED,[ss for ss,ee in fs],CORE_ROOTS)
  ff=rawfactors(qd,qr);rr=gammaseries(ff)
  nv=len(vertices(qd))
  rr={k+1:(nv-1)*v/2 for k,v in rr.items()}
  for ss,ee in fs:rr=mul(rr,ct(ee))
  out=add(out,rr)
 poles={k:-v for k,v in out.items()if k<0}
 poles[0]=CORE_U0;poles[1]=CORE_U1
 return poles

if __name__=='__main__':
 start=time.time();rows=[]
 for row in INV['loops'][:6]:
  L=row['loop'];done=[];failed=[]
  for g in row['graphs']:
   # All L<=4 provide independent RG checks; above, only needed power targets.
   if L>4 and not g['power_subgraphs']:continue
   if L==6 and 3*F(g['weight2'])==F(g['weight4']):continue
   try:
    p=ct(tuple(map(tuple,g['edges'])));r=-p.get(-1,mp.mpf(0));b=(-1)**(L+1)*L*M(F(g['weight4']))*r;c=(-1)**(L+1)*L*M(F(g['weight2']))*r
    done.append({'id':g['id'],'power':bool(g['power_subgraphs']),'ct':{str(k):str(v)for k,v in p.items()},'b':str(b),'c':str(c),**META[canon(g['edges'])]})
   except(Unsolved,Singular)as ex:failed.append({'id':g['id'],'power':bool(g['power_subgraphs']),'reason':str(ex)})
  rows.append({'L':L,'done':done,'failed':failed})
  print('L',L,'done',len(done),'failed',len(failed),'pwr_done',sum(r['power']for r in done),'seconds',time.time()-start,flush=True)
  print('FAILED',[(r['id'],r['reason'][:60])for r in failed],flush=True)
  (W/'records'/__import__('os').environ.get('POWER_OUTPUT','power_ms_d3_complete.json')).write_text(json.dumps({'dps':mp.mp.dps,'dimension':str(D),'core_U0':str(CORE_U0),'core_U1':str(CORE_U1),'loops':rows,'seconds':time.time()-start},indent=2))
