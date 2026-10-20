import json,sys,time,mpmath as mp
from single_sums import S
dps=int(sys.argv[1]) if len(sys.argv)>1 else 25
d=json.load(open('L2_factorized.json'));names=d['names']
mp.mp.dps=dps
const={'kappa2':2*(mp.psi(1,1)-mp.psi(1,mp.mpf(1)/2)),'psi1h':mp.psi(1,mp.mpf(1)/2),'psi3h':mp.psi(3,mp.mpf(1)/2)}
cache={};t0=time.time()
def SS(e):
    e=tuple(e)
    if e not in cache:cache[e]=S(e,names,dps=dps)
    return cache[e]
tot=mp.mpf(0)
for t in d['terms']:
    coef=mp.mpf(eval(t['coef'].replace('kappa2','const["kappa2"]').replace('psi1h','const["psi1h"]').replace('psi3h','const["psi3h"]'),{'const':const,'mp':mp}) if any(s in t['coef'] for s in const) else mp.mpf(mp.fraction(*map(int,(t['coef']+'/1').split('/')[:2])) if '/' in t['coef'] else int(t['coef'])))
    tot+=coef*SS(t['m'])*SS(t['n'])
mp.mp.dps=dps
print('L2 =',mp.nstr(-tot,dps-3),' (C63d: -347.2491531232)  time %.1fs'%(time.time()-t0))
json.dump({'dps':dps,'L2':str(-tot),'single_sums':{'|'.join(map(str,k)):str(v) for k,v in cache.items()}},open(f'L2_value_dps{dps}.json','w'),indent=1)
