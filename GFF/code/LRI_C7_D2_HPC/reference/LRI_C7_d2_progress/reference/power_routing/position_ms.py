"""Conservative d=2 coordinate-space Gamma/Selberg MS closure.
Only declared IR-safe roots and recursively closed spinneys are accepted.
Actual distance exponent = 2*r+v*z for affine pair (r,v).
"""
from fractions import Fraction as F
from collections import Counter
from functools import lru_cache
from pathlib import Path
import itertools,json,time,sys
import mpmath as mp
W=Path(__file__).parent;B=W/'lri_C6_d2_two_forest_update'
sys.path.insert(0,str(B/'analytic/code'))
from sp_classify import canon
mp.mp.dps=70
INV=json.load(open(B/'classified_inventory.json'))
P5=list(itertools.combinations(range(5),2));I5={e:i for i,e in enumerate(P5)}
PERMS=[tuple(I5[tuple(sorted((p[a],p[b])))]for a,b in P5)for p in itertools.permutations(range(5))]
K=7
class Unsolved(Exception):pass
class Singular(Exception):pass
ZERO=(F(0),F(0))
def pair(a,b=0):return F(a),F(b)
def plus(*p):return tuple(sum(x[j]for x in p)for j in[0,1])
def neg(p):return tuple(-x for x in p)
def scale(p,c):return tuple(x*c for x in p)
def sub(a,b):return plus(a,neg(b))
def gf(g,arg,k=1):g[arg]+=k

def betafactors(u,v):
 if u==ZERO or v==ZERO:raise Singular('zero leg/scaleless beta')
 u=(u[0],u[1]/2);v=(v[0],v[1]/2);g=Counter()
 for a in [sub(pair(1),u),sub(pair(1),v),plus(u,v,pair(-1))]:gf(g,a)
 for a in [u,v,sub(pair(2),plus(u,v))]:gf(g,a,-1)
 return F(1),g

def complete(p):
 a,b,c,d,e=p
 return [plus(pair(3),*map(neg,p)),a,c,plus(b,d,e,pair(-1)),b,d,plus(a,c,e,pair(-1)),e,plus(pair(2),neg(a),neg(b),neg(e)),plus(pair(2),neg(c),neg(d),neg(e))]

def gcadd(g,h):
 out=Counter(g)
 for k,v in h.items():out[k]+=v
 return Counter({k:v for k,v in out.items()if v})

def combine(f,g):return f[0]*g[0],gcadd(f[1],g[1])

@lru_cache(None)
def masterfactors(ps):
 a,b,c,d,e=ps
 if e==ZERO:return combine(betafactors(a,b),betafactors(c,d))
 if a==ZERO:return combine(betafactors(b,e),betafactors(c,plus(d,b,e,pair(-1))))
 if b==ZERO:return combine(betafactors(a,e),betafactors(plus(c,a,e,pair(-1)),d))
 if c==ZERO:return combine(betafactors(d,e),betafactors(a,plus(b,d,e,pair(-1))))
 if d==ZERO:return combine(betafactors(c,e),betafactors(plus(a,c,e,pair(-1)),b))
 lam=complete(ps)
 for pp in PERMS:
  a,b,c,d,e=[lam[pp[i]]for i in[1,4,2,5,7]]
  if a!=c or b!=d:continue
  # Complex Selberg n=2 with sigma=1-p_a/2, tau=1-p_b/2, theta=-p_e/4.
  sig=pair(1-a[0],-a[1]/2);tau=pair(1-b[0],-b[1]/2);theta=pair(-e[0]/2,-e[1]/4)
  g=Counter()
  def cg(x,sign):gf(g,x,sign);gf(g,sub(pair(1),x),-sign)
  for x,sg in [(scale(theta,2),1),(theta,-1),(sig,1),(tau,1),(plus(sig,tau,theta),-1),(plus(sig,theta),1),(plus(tau,theta),1),(plus(sig,tau,scale(theta,2)),-1)]:cg(x,sg)
  if any(r.denominator==1 and r<=0 and v==0 for (r,v),sg in g.items()if sg):continue
  return F(2),g
 raise Unsolved('nonsymmetric kite')

def vertices(E):return sorted({v for e in E for v in e})

@lru_cache(None)
def rawfactors(ed,roots):
 E={e:(F(m,2),F(-m,2))for e,m in Counter(ed).items()};allvs=set(vertices(E))
 def rec(E,vs):
  if len(vs)==2:return (F(1),Counter())
  cand=[]
  for k in[1,2]:
   for inn in itertools.combinations(sorted(vs-set(roots)),k):
    ins=set(inn);touch={e:p for e,p in E.items()if set(e)&ins};bd={v for e in touch for v in e}-ins
    if len(bd)!=2:continue
    a,b=sorted(bd)
    try:
     if k==1:
      ff=betafactors(touch[tuple(sorted((a,inn[0])))],touch[tuple(sorted((b,inn[0])))])
     else:
      x,y=inn;ps=tuple(touch.get(tuple(sorted(e)),ZERO)for e in[(a,x),(b,x),(a,y),(b,y),(x,y)]);ff=masterfactors(ps)
     newp=plus(*touch.values(),pair(-k));nE={e:p for e,p in E.items()if e not in touch};nE[a,b]=plus(nE.get((a,b),ZERO),newp);nE={e:p for e,p in nE.items()if p!=ZERO}
     cand.append((k,ff,nE,vs-ins))
    except(Singular,Unsolved):continue
  for k,ff,nE,nvs in cand:
   try:return combine(ff,rec(nE,nvs))
   except(Unsolved,Singular):pass
  raise Unsolved('no safe Gamma-Selberg reduction')
 ff=rec(E,allvs);L=len(allvs)-1
 return (F(2,L)*ff[0],tuple(sorted((r,v,sg)for(r,v),sg in ff[1].items()if sg)))

def mpf(x):return mp.mpf(x.numerator)/x.denominator
@lru_cache(None)
def gammaseries(ff):
 pref,ga=ff;lead=mpf(pref);power=-1;logs=[mp.mpf(0)]*(K+1)
 for r,v,sg in ga:
  if sg==0:continue
  V=mpf(v)
  if r.denominator==1 and r<=0:
   if V==0:raise Singular('uncancelled identically singular Gamma')
   m=int(-r);power-=sg;lead*=((-1)**m/(V*mp.factorial(m)))**sg
   for k in range(1,K+1):logs[k]+=sg*V**k*(mp.polygamma(k-1,1)/mp.factorial(k)+sum(mp.mpf(j)**(-k)for j in range(1,m+1))/k)
  else:
   R=mpf(r);lead*=mp.gamma(R)**sg
   for k in range(1,K+1):logs[k]+=sg*V**k*mp.polygamma(k-1,R)/mp.factorial(k)
 cs=[lead]
 for k in range(1,K+1):cs.append(sum(j*logs[j]*cs[k-j]for j in range(1,k+1))/k)
 return{power+k:v for k,v in enumerate(cs)}

def add(*xs):
 out={}
 for x in xs:
  for k,v in x.items():out[k]=out.get(k,0)+v
 return out

def mul(x,y,hi=6):
 out={}
 for k,v in x.items():
  for j,w in y.items():
   if -6<=k+j<=hi:out[k+j]=out.get(k+j,0)+v*w
 return out

def normalized(ed,rr=None):
 vs=vertices(ed);n={v:i for i,v in enumerate(vs)}
 E=tuple(sorted(tuple(sorted((n[a],n[b])))for a,b in ed))
 return (E,tuple(n[v]for v in rr))if rr is not None else E

@lru_cache(None)
def uvsubs(ed):
 vs=vertices(ed);out=[]
 for k in range(2,len(vs)):
  for ss in itertools.combinations(vs,k):
   ss=frozenset(ss);ee=tuple(e for e in ed if set(e)<=ss)
   if len(ee)!=2*(k-1):continue
   connected=True
   vv=sorted(ss)
   for mask in range(1,1<<(k-1)):
    cut={vv[j]for j in range(k)if mask>>j&1}
    if sum((a in cut)!=(b in cut)for a,b in ee)<2:connected=False;break
   if connected:out.append((ss,ee))
 return tuple(out)

def rootsafe(ed):
 vs=vertices(ed);bad=[]
 for k in range(2,len(vs)):
  for ss in itertools.combinations(vs,k):
   ss=set(ss)
   if sum(set(e)<=ss for e in ed)>=2*(k-1):bad.append(ss)
 return [rr for rr in itertools.combinations(vs,2)if not any(set(rr)<=ss for ss in bad)]

def quotient(ed,subs,rr):
 pp={v:min(ss)for ss in subs for v in ss};out=[]
 for a,b in ed:
  a,b=pp.get(a,a),pp.get(b,b)
  if a!=b:out.append(tuple(sorted((a,b))))
 r=tuple(pp.get(v,v)for v in rr)
 if r[0]==r[1]:raise Unsolved('root collision')
 return normalized(out,r)

@lru_cache(None)
def forestsets(ed):
 subs=uvsubs(ed);ret=[]
 def rec(ch,poss):
  if ch:ret.append(tuple(subs[j]for j in ch))
  for k,j in enumerate(poss):rec(ch+[j],[i for i in poss[k+1:]if not subs[j][0]&subs[i][0]])
 rec([],list(range(len(subs))))
 return ret

C={};META={};failcache={}
def ct(ed):
 ed=normalized(ed);key=canon(ed)
 if key in C:return C[key]
 if key in failcache:raise Unsolved(failcache[key])
 L=len(ed)//2
 try:
  subc={ss:ct(ee)for ss,ee in uvsubs(ed)}
  vals=[]
  for rr in rootsafe(ed):
   try:
    raw=gammaseries(rawfactors(ed,rr));out=raw
    for fs in forestsets(ed):
     qd,qr=quotient(ed,[ss for ss,ee in fs],rr)
     tmp=gammaseries(rawfactors(qd,qr))
     for ss,ee in fs:tmp=mul(tmp,subc[ss])
     out=add(out,tmp)
    poles={k:-v for k,v in out.items()if k<0}
    vals.append((rr,poles))
    # A second safe-root result is optional, every existing one compared below.
   except(Unsolved,Singular):continue
  if not vals:raise Unsolved('nonclosed Gamma/Selberg raw graph or quotient')
  res=vals[0][1];err=max((abs(v-res.get(k,0))for rr,c in vals for k,v in c.items()),default=0)
  if err>mp.mpf('1e-40'):raise RuntimeError(('coordinate root mismatch',L,ed,mp.nstr(err),vals))
  C[key]=res;META[key]={'roots_tested':len(vals),'root_error':str(err),'root':vals[0][0]}
  return res
 except Unsolved as e:failcache[key]=str(e);raise

if __name__=='__main__':
 st=time.time();records=[];old=json.load(open(B/'analytic/verification/sp_ms_90.json'));oldrows={g['id']:g for r in old['loops']for g in r['graphs']}
 status=json.load(open(B/'verification/C6_d2_continuation_result.json'));targs={5:set(status['remaining_five_loop_mass_ids']),6:set(status['remaining_six_loop_ids'])}
 for row in INV['loops']:
  L=row['loop'];solved=[];failed=[];delta=mp.mpf(0);errs=[]
  for g in row['graphs']:
   try:
    cp=ct(tuple(map(tuple,g['edges'])));r=-cp.get(-1,0);b=(-1)**(L+1)*L*mpf(F(g['weight4']))*r;c=(-1)**(L+1)*L*mpf(F(g['weight2']))*r
    item={'id':g['id'],'ct':{str(k):str(v)for k,v in cp.items()},'b':str(b),'c':str(c),**META[canon(g['edges'])]}
    if g['id']in oldrows:
     err=max(abs(v-mp.mpf(oldrows[g['id']]['MS_counterterm'].get(str(k),'0')))for k,v in cp.items());errs.append(err);item['old_momentum_comparison']=str(err)
     if err>mp.mpf('1e-40'):print('MISMATCH',g['id'],mp.nstr(err),flush=True)
    if L in targs and g['id']in targs[L]:delta+=(3*c-b)/2187 if L==6 else -24*mp.log(2)*c/2187
    solved.append(item)
   except Unsolved as e:failed.append({'id':g['id'],'reason':str(e)})
  rec={'loop':L,'solved':solved,'failed':failed,'new_target_contribution':str(delta),'new_target_count':sum(g['id']in targs.get(L,set())for g in solved),'max_momentum_discrepancy':str(max(errs,default=0))};records.append(rec)
  print('L',L,'solved',len(solved),'new',rec['new_target_count'],'delta',mp.nstr(delta,22),'err',rec['max_momentum_discrepancy'],'sec',time.time()-st,flush=True)
  (W/'position_ms_results.json').write_text(json.dumps({'dps':mp.mp.dps,'loops':records,'seconds':time.time()-st},indent=2))
