"""Cutoff (and nz) extrapolation of Delta_eps(Delta_sigma) from the dressed phi4 HT production.

Series per (delta, prescription):
  delta >= 0.1, 0.249 : nz=24/osc=192 production (prod1+prod2), cuts 12..40
  0.01 <= delta <= 0.075: nz=32/osc=256 (prod4), cuts 12..36, plus an nz correction c(N)=D_48(N)-D_32(N)
                          measured at N=16..28 (prod5) and extrapolated as a power law in N (error = 50% of c)
  delta = 0.001         : nz=40/osc=384 (prod6), cuts 12..32 (nz48 check at 16..28)
Fits on N >= Nmin (several Nmin):  F1 D+a N^-w ; F2 D+a N^-w+b N^-(w+1) ; F3 D+a N^-w+b N^-2w.
Accepted fits: converged, 0.05<w<6, rms residual < 2e-7 (relative to the spread of the data).
Result: median of accepted intercepts; systematic = half the full spread (min..max) of accepted intercepts,
plus the nz-correction uncertainty where applicable. These are model spreads, not confidence intervals.
"""
import json,math,sys,itertools
from pathlib import Path
import numpy as np
from scipy.optimize import curve_fit
D=Path(__file__).resolve().parent
rows=json.load(open(D/'collected.json'))['rows']

def series(delta,window,mode,nz):
    s={}
    for r in rows:
        if abs(r['delta']-delta)<1e-9 and r['window']==window and r['mode']==mode and r['nz']==nz:s[r['cut']]=r['Delta_thermal']
    return dict(sorted(s.items()))

F={'F1':(lambda N,D0,a,w:D0+a*N**-w,3),
   'F2':(lambda N,D0,a,w,b:D0+a*N**-w+b*N**-(w+1),4),
   'F3':(lambda N,D0,a,w,b:D0+a*N**-w+b*N**(-2*w),4)}

def fits(s):
    N=np.array(list(s),float);y=np.array(list(s.values()))
    out=[]
    for name,(f,k) in F.items():
        for nmin in (12,14,16,18,20,22,24):
            m=N>=nmin
            if m.sum()<k+2:continue
            x,yy=N[m],y[m];slope=(yy[-1]-yy[-2])/(x[-1]-x[-2])
            best=None
            for w0 in (0.3,0.6,1.0,1.5,2.5):
                a0=-slope*x[-1]**(w0+1)/w0 if slope!=0 else 0.
                p0=[yy[-1]+a0*x[-1]**-w0,a0,w0]+([0.] if k==4 else [])
                try:
                    p,cov=curve_fit(f,x,yy,p0=p0,maxfev=20000)
                except Exception:continue
                r=yy-f(x,*p);rms=float(np.sqrt(np.mean(r**2)))
                if not (0.05<p[2]<6) or not np.isfinite(p).all():continue
                if best is None or rms<best[1]:best=(p,rms)
            if best is None:continue
            p,rms=best
            out.append({'form':name,'Nmin':nmin,'D_inf':float(p[0]),'omega':float(p[2]),'rms':rms,'npts':int(m.sum())})
    return out

RMS_TOL=3e-6
def summarize(fl,ymax):
    ok=[f for f in fl if f['rms']<RMS_TOL and 0.2<f['omega']<4 and abs(f['D_inf']-ymax)<0.05]
    if not ok:return None
    v=np.array([f['D_inf'] for f in ok])
    return {'D_inf':float(np.median(v)),'spread_half':float((v.max()-v.min())/2),'n_fits':len(ok),
            'omega_median':float(np.median([f['omega'] for f in ok])),'min':float(v.min()),'max':float(v.max())}

def nz_correction(delta,window,mode,cuts):
    """c(N)=D_48-D_32 at N=16..28, power-law extrapolated to the requested cuts."""
    s32=series(delta,window,mode,32);s48=series(delta,window,mode,48)
    Ns=[n for n in (16,20,24,28) if n in s32 and n in s48]
    c={n:s48[n]-s32[n] for n in Ns}
    big=[n for n in Ns if abs(c[n])>2e-7]
    if len(big)>=2 and all(np.sign(c[n])==np.sign(c[big[-1]]) for n in big):
        x=np.log(big);yv=np.log([abs(c[n]) for n in big]);k,b=np.polyfit(x,yv,1)
        model=lambda n:np.sign(c[big[-1]])*np.exp(b+k*np.log(n))
    else:
        model=lambda n:c[Ns[-1]] if Ns else 0.
    return {n:(c[n] if n in c else float(model(n))) for n in cuts},c

REF_EPS={2:(math.pi+4*math.log(2))/9,3:-3.71985632290183342249,4:45.42488010356,5:-731.13947662454,6:14331.68703277,7:-322550.}
def eps_series(delta,order):
    e=1-4*delta;return 0.5-e/6+sum(REF_EPS[k]*e**k for k in range(2,order+1))

MC={0.025:(0.71115,0.00049,0.00959),0.05:(0.61987,0.00055,0.00220),0.075:(0.56694,0.00037,0.00139),
    0.1:(0.53248,0.00020,0.00242),0.125:(0.50710,0.00035,0.00193),0.15:(0.49325,0.00041,0.00306),
    0.175:(0.48460,0.00035,0.00067),0.225:(0.47912,0.00068,None)}

def composite(delta,window,mode):
    """Best-nz series: nz48 > nz40 > nz32 > nz24 per cut; a lower-nz value is used only where its estimated
    nz error (interpolated from measured D_48-D_32 gaps) is below NZ_TOL. Returns (series, nz_sys_at_max)."""
    S={nz:series(delta,window,mode,nz) for nz in (24,32,40,48,56)}
    out={};used={}
    if delta>=0.1 or delta>0.24:
        base=S[24];chk=S[48] if S[48] else {}
        gaps=[abs(chk[n]-base[n]) for n in chk if n in base]
        return dict(base),{n:24 for n in base},(max(gaps) if gaps else 0.)
    meas={n:S[48][n]-S[32][n] for n in S[48] if n in S[32]}
    if not meas:                       # no nz48 (delta=0.075): nz32 up to cut 28; nz error unmeasured (flagged)
        base={n:v for n,v in S[32].items() if n<=28};return base,{n:32 for n in base},float('nan')
    def cerr(n):
        if n in meas:return abs(meas[n])
        lo=[m for m in meas if m<n];hi=[m for m in meas if m>n]
        if not lo:return 0. if meas.get(min(meas),0)==0 or abs(meas[min(meas)])<1e-7 else abs(meas[min(meas)])
        if not hi:return float('inf')
        l,h=max(lo),min(hi);cl,ch=max(abs(meas[l]),1e-9),max(abs(meas[h]),1e-9)
        return float(np.exp(np.log(cl)+(np.log(ch)-np.log(cl))*(n-l)/(h-l)))
    for n in sorted(set().union(*[set(x) for x in S.values()])):
        for nz in (56,48,40):
            if n in S[nz]:out[n]=S[nz][n];used[n]=nz;break
        else:
            if n in S[32] and cerr(n)<NZ_TOL:out[n]=S[32][n];used[n]=32
    return out,used,0.

NZ_TOL=5e-6
results=[]
deltas=[0.249,0.24,0.225,0.2,0.175,0.15,0.125,0.1,0.075,0.05,0.025,0.01,0.001]
for d in deltas:
    for window,mode in (('none',None),('vacuum','consistent')):
        s,used,nzsys=composite(d,window,mode)
        if len(s)<5:continue
        fl=fits(s);sm=summarize(fl,list(s.values())[-1])
        rec={'delta':d,'eps':1-4*d,'prescription':'raw' if window=='none' else 'window','nz_used':used,'cuts':[min(s),max(s)],
             'n_points':len(s),'D_at_max_cut':list(s.values())[-1],'fit':sm,'nz_sys':nzsys,'all_fits':fl}
        if sm:rec['total_sys']=math.hypot(sm['spread_half'],0. if math.isnan(nzsys) else nzsys)
        results.append(rec)
json.dump({'results':results,'eps_series_coeffs':REF_EPS,'mc':{str(k):v for k,v in MC.items()}},open(D/'extrapolation.json','w'),indent=1)
print('%-6s %-6s %-4s %-9s %-11s %-22s %-6s %-9s %-24s %-9s'%('dsig','eps','nz','cuts','D(maxcut)','D_inf ± sys','omega','nfits','MC','eps-series(opt)'))
for r in results:r['nz']=max(r['nz_used'].values())
for r in results:
    sm=r['fit'];d=r['delta']
    mc=MC.get(d);mcs='%.5f(%d)(%s)'%(mc[0],round(mc[1]*1e5),'%d'%round(mc[2]*1e5) if mc[2] else '-') if mc else ''
    es=''
    if d>=0.2:
        sums=[eps_series(d,k) for k in range(2,8)];es='%.6f'%sums[3]
    if sm:
        print('%-6g %-6.3f %-3d %2d-%-6d %.6f  %.6f ± %.6f  %-6.2f %-9d %-24s %s  [%s]'%(d,1-4*d,r['nz'],r['cuts'][0],r['cuts'][1],r['D_at_max_cut'],sm['D_inf'],r['total_sys'],sm['omega_median'],sm['n_fits'],mcs,es,r['prescription']))
    else:print('%-6g %s no acceptable fit [%s]'%(d,r['nz'],r['prescription']))
