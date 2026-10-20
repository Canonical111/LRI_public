"""Profile of the max fit residual vs an imposed C4 intercept, for corrected (raw + dC4_g2D + Dconn shift) campaign data.
Gives the interval of C4 values compatible with the data at <= 2x the free-fit residual for each tail variant."""
import sys, json, math, glob
sys.dont_write_bytecode = True
import numpy as np
exec(open('<TMP>/scratchpad/identity/reconcile/refit_corrected.py').read().split('rows=[]')[0])
print('raw residual floor check (free fits, lo=60):')
for lab in ('B','D','E','A+z^j/L','D+L^-0.75'):
    tk,w,free=variants[lab]; mm=L>=60
    for key in ('raw','g2D','Dconn'):
        lim,diag=thermal_fit(L[mm],data[key][mm],w,tk,maxorder=4)
        print(f'  {lab:12s} {key:6s} free res {diag[4]["max_residual"]:.2e}  C4 {lim[4]:.6f}')
grid=np.linspace(-0.03,0.03,601)
out={}
for lo in (40,50,60,70):
    mm=L>=lo
    for lab in ('A','B','C','D','E','F','A+z^j/L','A+L^-0.75','D+z^j/L^1.5','D+L^-0.75'):
        tk,w,free=variants[lab]
        for key in ('g2D','Dconn'):
            lim,diag=thermal_fit(L[mm],data[key][mm],w,tk,maxorder=4); r0=diag[4]['max_residual']
            res=[]
            for d in grid:
                _,dg=thermal_fit(L[mm],data[key][mm],w,tk,maxorder=4,fixed={4:EX4+d}); res.append(dg[4]['max_residual'])
            res=np.array(res); ok=grid[res<=2*max(r0,2.5e-12)]
            iv=(ok.min(),ok.max()) if len(ok) else (np.nan,np.nan)
            out[(lo,lab,key)]=dict(free=lim[4]-EX4,res0=r0,interval=iv,res_at_exact=float(res[np.argmin(abs(grid))]))
            print(f'lo={lo} {lab:12s} {key:6s} free miss {lim[4]-EX4:+.4f}  res0 {r0:.1e}  res@exact {res[np.argmin(abs(grid))]:.1e}  2x-res interval [{iv[0]:+.4f},{iv[1]:+.4f}]')
json.dump({str(k):v for k,v in out.items()},open(base+'reconcile/profile_c4.json','w'),indent=1,default=float)
