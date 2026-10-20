"""Extend conservative position-space MS closure by verified split-contour kite.
Unresolved higher cores remain excluded, never approximated by zero.
"""
import position_ms as pm
from position_ms import *
from kite_klt_fast import kite
import hashlib,multiprocessing as mproc
W=Path(__file__).parent
CACHE=W/'kite_cache';CACHE.mkdir(exist_ok=True)
NODES=int(__import__('os').environ.get('KNODES','32'))
DPS=int(__import__('os').environ.get('KDPS','45'))
RAD=__import__('os').environ.get('KRAD','.02')
POOL=None

def d4(ps):
 a,b,c,d,e=ps
 return min([(a,b,c,d,e),(b,a,d,c,e),(c,d,a,b,e),(d,c,b,a,e)])

def one_node(task):
 ss,j,n,dps,r=task;mp.mp.dps=dps
 ps=[tuple(F(x)for x in p)for p in ss]
 zz=mp.mpf(r)*mp.exp(2j*mp.pi*(mp.mpf(j)+mp.mpf('.5'))/n)
 pp=[2*mpf(a)+mpf(b)*zz for a,b in ps]
 v=zz**2*kite(pp)
 return str(mp.re(v)),str(mp.im(v))

@lru_cache(None)
def masterjet(ps):
 ss=[[str(x)for x in p]for p in ps]
 tag=hashlib.sha256(json.dumps([ss,NODES,DPS,RAD]).encode()).hexdigest()[:20];f=CACHE/(tag+'.json')
 if f.exists():data=json.load(open(f));return{int(k):mp.mpf(v)for k,v in data['coefficients'].items()}
 tasks=[(ss,j,NODES,DPS,RAD)for j in range(NODES//2)]
 vals=POOL.map(one_node,tasks)if POOL else list(map(one_node,tasks))
 # Half-offset Cauchy grid; lower-half conjugate nodes require no additional evaluations.
 hi=7;res={};imagmax=mp.mpf(0)
 for k in range(hi+1):
  total=mp.mpf(0)
  for j,(re,im)in enumerate(vals):
   v=mp.mpc(re,im);phase=mp.exp(-2j*mp.pi*(mp.mpf(j)+mp.mpf('.5'))*k/NODES)
   total+=2*mp.re(v*phase)
  res[k-2]=total/NODES/mp.mpf(RAD)**k
 # No exact zero is imposed except orders whose precision loss makes them below 1e-30.
 data={'arguments':ss,'nodes':NODES,'dps':DPS,'radius':RAD,'coefficients':{str(k):str(v)for k,v in res.items()},'samples':vals,'normalization':'distance powers 2*r+v*z, measure d2x/pi; z^2 regularized'}
 f.write_text(json.dumps(data,indent=2));print('KITE',len(list(CACHE.iterdir())),ss,'jet0',mp.nstr(res.get(0,0),15),flush=True)
 return res

oldmf=pm.masterfactors
@lru_cache(None)
def masterfactors(ps):
 try:
  a,g=oldmf(ps);return a,g,()
 except Unsolved:return F(1),Counter(),(d4(ps),)

oldbf=pm.betafactors
def betafactors(u,v):
 a,g=oldbf(u,v);return a,g,()

def combine(f,g):return f[0]*g[0],gcadd(f[1],g[1]),f[2]+g[2]

# Adapt bare symbolic factorization: Gamma multiplicities plus the short list of kite families.
import inspect
s=inspect.getsource(pm.rawfactors.__wrapped__)
s=s.replace('return (F(1),Counter())','return (F(1),Counter(),())')
s=s.replace('if sg)))','if sg)),tuple(ff[2]))')
exec(s,globals())
oldrf=rawfactors
from scaleless_leaf import leaf
@lru_cache(None)
def rawfactors(ed,roots):
 if leaf(ed,roots):return F(0),(),()
 return oldrf(ed,roots)

oldgs=pm.gammaseries
@lru_cache(None)
def gammaseries(ff):
 pref,ga,jj=ff;gs=oldgs((pref,ga))
 for ps in jj:gs=mul(gs,masterjet(ps))
 return gs

pm.rawfactors=rawfactors;pm.gammaseries=gammaseries
pm.K=8
exec(inspect.getsource(pm.ct).replace("mp.mpf('1e-40')", "mp.mpf('1e-20')"),pm.__dict__)

if __name__=='__main__':
 mp.mp.dps=max(60,DPS+10)
 pm.C={};pm.META={};pm.failcache={}
 st=time.time();records=[];old=json.load(open(W/'position_ms_results.json'));oldrows={g['id']:g for r in old['loops']for g in r['solved']}
 status=json.load(open(B/'verification/C6_d2_continuation_result.json'));targs={5:set(status['remaining_five_loop_mass_ids']),6:set(status['remaining_six_loop_ids'])}
 POOL=mproc.get_context('fork').Pool(4)
 try:
  for row in INV['loops']:
   L=row['loop'];solved=[];failed=[];delta=mp.mpf(0);errs=[]
   for g in row['graphs']:
    try:
     cp=pm.ct(tuple(map(tuple,g['edges'])));r=-cp.get(-1,0);b=(-1)**(L+1)*L*mpf(F(g['weight4']))*r;c=(-1)**(L+1)*L*mpf(F(g['weight2']))*r
     item={'id':g['id'],'ct':{str(k):str(v)for k,v in cp.items()},'b':str(b),'c':str(c),**pm.META[canon(g['edges'])]}
     if g['id']in oldrows:
      err=max(abs(v-mp.mpf(oldrows[g['id']]['ct'].get(str(k),'0')))for k,v in cp.items());errs.append(err);item['gamma_selberg_comparison']=str(err)
      if err>mp.mpf('1e-20'):print('MISMATCH',g['id'],mp.nstr(err),flush=True)
     if L in targs and g['id']in targs[L]:delta+=(3*c-b)/2187 if L==6 else -24*mp.log(2)*c/2187
     solved.append(item)
    except(Unsolved,Singular,ValueError,ZeroDivisionError)as e:failed.append({'id':g['id'],'reason':str(e)})
   rec={'loop':L,'solved':solved,'failed':failed,'new_target_contribution':str(delta),'new_target_count':sum(g['id']in targs.get(L,set())for g in solved),'max_Gamma_discrepancy':str(max(errs,default=0))};records.append(rec)
   print('L',L,'solved',len(solved),'new',rec['new_target_count'],'delta',mp.nstr(delta,22),'err',rec['max_Gamma_discrepancy'],'sec',time.time()-st,flush=True)
   (W/f'position_kite_leaf_ms_{NODES}_{DPS}_{RAD}.json').write_text(json.dumps({'dps':mp.mp.dps,'kite_dps':DPS,'nodes':NODES,'radius':RAD,'loops':records,'seconds':time.time()-st},indent=2))
 finally:POOL.close();POOL.join()
