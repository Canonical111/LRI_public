"""Find critical NRG flow and estimate exponents without any CFT targets.

Finite iteration tuning convention: terminal odd gap = fraction of decoupled
bath fixed-point gap. This convention only finds a nearby trajectory; estimates
must use an interior, approximately scale-invariant plateau and vary settings.
"""
from nrg import Config, run, chain_coefficients
from dataclasses import asdict
import numpy as np
from pathlib import Path
import json, time

def atomic_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(path)

def find_critical(cfg,folder,bracket=(0.01,2.),fraction=.3,atol=5e-14,maxiter=48):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    statepath=folder/'tuning.json'
    if statepath.exists():
        old=json.loads(statepath.read_text())
        if old.get('config')==asdict(cfg) and old.get('fraction')==fraction and old.get('complete') and old.get('root_selection')=='final_bracket_midpoint':
            return json.loads((folder/'critical.json').read_text())
    free=run(0.,cfg);target=fraction*free['records'][-1]['odd_gap']
    lo,hi=bracket;history=[];best=None
    def ev(a):
        nonlocal best
        d=run(float(a),cfg);v=d['records'][-1]['odd_gap']-target
        history.append({'alpha':a,'terminal_gap':v+target,'f':v})
        if best is None or abs(v)<abs(best[0]):best=(v,d)
        print('tune',cfg.s,cfg.Lambda,cfg.keep,cfg.nb,len(history),format(a,'.16g'),format(v,'.6g'),flush=True)
        return v,d
    flo,_=ev(lo);fhi,_=ev(hi)
    while flo<0 and lo>1e-10:lo/=2;flo,_=ev(lo)
    while fhi>0 and hi<100:hi*=2;fhi,_=ev(hi)
    if not flo>0>fhi:raise RuntimeError('No valid phase bracket.')
    for it in range(maxiter):
        mid=(lo+hi)/2
        fm,dm=ev(mid)
        if fm>0:lo=mid
        else:hi=mid
        atomic_json(statepath,{'config':asdict(cfg),'fraction':fraction,'target':target,'bracket':[lo,hi],
            'history':history,'complete':False})
        if hi-lo < atol*max(1,abs(mid)):break
    # Do not pick a historical 'best terminal residual': in a saturated phase
    # numerical noise can make an early, noncritical trajectory appear best.
    midpoint=(lo+hi)/2
    d=run(float(midpoint),cfg)
    terminal_residual=d['records'][-1]['odd_gap']-target
    d['critical_tuning']={'target_gap':target,'terminal_residual':terminal_residual,'selection':'final_bracket_midpoint','historical_best_alpha':best[1]['alpha'],'bracket':[lo,hi],
        'fraction':fraction,'root_convention':'terminal fraction of free gap, interior critical plateau required'}
    atomic_json(folder/'critical.json',d)
    atomic_json(statepath,{'config':asdict(cfg),'fraction':fraction,'target':target,'bracket':[lo,hi],
            'history':history,'complete':True,'root_selection':'final_bracket_midpoint'})
    return d

def slope_diagnostics(d):
    r=d['records']; lnL=np.log(d['config']['Lambda']);n=len(r)
    g=np.array([x['odd_gap'] for x in r]);sp=np.array([x['log_spin_scale_correlation'] for x in r]);
    th=np.array([x['log_thermal_scale_correlation'] for x in r]);
    return {'n':np.arange(n),'gap':g,'x_eff':-np.gradient(sp)/(2*lnL),'dE_eff':-np.gradient(th)/(2*lnL)}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--s',type=float,default=.9);p.add_argument('--Lambda',type=float,default=2.)
    p.add_argument('--keep',type=int,default=32);p.add_argument('--nb',type=int,default=8);p.add_argument('--nsites',type=int,default=80)
    p.add_argument('--tunneling',type=float,default=.1);p.add_argument('--fraction',type=float,default=.3)
    p.add_argument('--folder',required=True);p.add_argument('--lo',type=float,default=.01);p.add_argument('--hi',type=float,default=2.)
    a=p.parse_args();cfg=Config(s=a.s,Lambda=a.Lambda,keep=a.keep,nb=a.nb,nsites=a.nsites,tunneling=a.tunneling)
    d=find_critical(cfg,a.folder,(a.lo,a.hi),a.fraction);z=slope_diagnostics(d)
    print('DIAG',d['alpha'])
    for n in range(5,cfg.nsites,5):print(n,z['gap'][n],z['x_eff'][n],z['dE_eff'][n])
