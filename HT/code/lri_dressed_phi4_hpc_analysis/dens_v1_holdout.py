"""Held-out-cutoff test of the dens_v1 extrapolations.

For each Δσ, the dens16 series is truncated at N <= Ncut and fitted with the extrapolate.py fit family
(F1/F2/F3 x Nmin 12..24) and the summarize() acceptance rules. Then:
  - each accepted fit predicts the held-out points N > Ncut; prediction error = actual - median prediction,
    compared with the half-spread of the accepted predictions;
  - D_inf(Ncut) shows how the extrapolated value moves as cutoffs are added.
Output: tables on stdout and dens_v1_holdout.json.
"""
import json,io,contextlib
from pathlib import Path
import numpy as np
from scipy.optimize import curve_fit
D=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    import extrapolate as E
rows=json.load(open(D/'dens_v1_rows.json'))
nrg={round(r['ds'],6):r for r in json.load(open(D/'nrg/ds13_final.json'))}

def ser(d):
    return dict(sorted((r['N'],r['Delta_thermal']) for r in rows if abs(r['delta']-d)<1e-12 and r['nz']==16))

def fits(s):
    # same as extrapolate.fits, but keeps the parameters
    N=np.array(list(s),float);y=np.array(list(s.values()));out=[]
    for name,(f,k) in E.F.items():
        for nmin in (12,14,16,18,20,22,24):
            m=N>=nmin
            if m.sum()<k+2:continue
            x,yy=N[m],y[m];slope=(yy[-1]-yy[-2])/(x[-1]-x[-2]);best=None
            for w0 in (0.3,0.6,1.0,1.5,2.5):
                a0=-slope*x[-1]**(w0+1)/w0 if slope!=0 else 0.
                p0=[yy[-1]+a0*x[-1]**-w0,a0,w0]+([0.] if k==4 else [])
                try:p,_=curve_fit(f,x,yy,p0=p0,maxfev=20000)
                except Exception:continue
                rms=float(np.sqrt(np.mean((yy-f(x,*p))**2)))
                if not (0.05<p[2]<6) or not np.isfinite(p).all():continue
                if best is None or rms<best[1]:best=(p,rms)
            if best:out.append({'form':name,'Nmin':nmin,'p':best[0],'D_inf':float(best[0][0]),'omega':float(best[0][2]),'rms':best[1],'f':f})
    return out

def accepted(fl,ymax):
    return [f for f in fl if f['rms']<E.RMS_TOL and 0.2<f['omega']<4 and abs(f['D_inf']-ymax)<0.05]

GRID=[0.2,0.175,0.15,0.125,0.1,0.075,0.05,0.025]
CUTS=[28,30,32,34,36,38,40]
res=[]
print('D_inf (median ± half-spread, n accepted, stable?) vs largest cutoff used')
print('| Δσ | '+' | '.join('N≤%d'%c for c in CUTS)+' | NRG |')
print('|---|'+'---|'*(len(CUTS)+1))
for d in GRID:
    s=ser(d);cells=[];rec={'delta':d,'by_cut':{}}
    for c in CUTS:
        t={n:v for n,v in s.items() if n<=c};ok=accepted(fits(t),list(t.values())[-1])
        if not ok:cells.append('—');continue
        v=np.array([f['D_inf'] for f in ok]);med=float(np.median(v));sp=float((v.max()-v.min())/2)
        st=len(ok)>=5 and np.median([f['omega'] for f in ok])>=0.45 and sp<=2e-3
        cells.append('%.5f(%d)%s'%(med,round(sp*1e5),'' if st else '*'))
        # held-out predictions
        held=[n for n in s if n>c];pred={}
        for n in held:
            pv=np.array([f['f'](float(n),*f['p']) for f in ok])
            pred[n]={'actual':s[n],'median':float(np.median(pv)),'half_spread':float((pv.max()-pv.min())/2)}
        rec['by_cut'][c]={'D_inf':med,'half_spread':sp,'n':len(ok),'stable':bool(st),
                         'omega_median':float(np.median([f['omega'] for f in ok])),'pred':pred}
    n=nrg.get(d);print('| %g | %s | %s |'%(d,' | '.join(cells),'%.5f(%d)'%(n['Delta_E'],round(n['total_uncertainty']*1e5)) if n else ''))
    res.append(rec)
print('(value(x): x = half-spread in 1e-5; * = fails the stability rule)')

print('\nFit N<=32, predict N=34..40: actual - median prediction (half-spread of predictions), in 1e-6')
print('| Δσ | N=34 | N=36 | N=38 | N=40 | D_inf(N≤32) − D_inf(N≤40) |')
print('|---|---|---|---|---|---|')
for r in res:
    b=r['by_cut'].get(32)
    if not b:continue
    cells=['%+.1f (%.1f)'%((p['actual']-p['median'])*1e6,p['half_spread']*1e6) for n,p in sorted(b['pred'].items())]
    full=r['by_cut'].get(40)
    print('| %g | %s | %s |'%(r['delta'],' | '.join(cells),('%+.2e'%(b['D_inf']-full['D_inf'])) if full else '—'))

print('\nFit N<=36, predict N=38,40 (same units)')
for r in res:
    b=r['by_cut'].get(36)
    if b:print('  Δσ=%-6g'%r['delta'],'  '.join('N%d %+.1f (%.1f)'%(n,(p['actual']-p['median'])*1e6,p['half_spread']*1e6) for n,p in sorted(b['pred'].items())))
json.dump(res,open(D/'dens_v1_holdout.json','w'),indent=1)
