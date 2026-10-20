"""Higher-precision control with changed acceleration and sampling parameters."""
import json,time
from pathlib import Path
import mpmath as mp
import check_two_dimensional as d2
from gamma_series import ratio_power_sum,alternating_linear_sum
from check_wheel_periodization import residue_weights
mp.mp.dps=70
d2.ratio_power_sum=lambda A,B,r:ratio_power_sum(A,B,r,N=144,K=58)
d2.alternating_linear_sum=lambda A,B,r,v:alternating_linear_sum(A,B,r,v,start=32,depth=340)

def dct_extract(r,q,fun):
    N=2*r-1;eta=1/(8*mp.pi*r)
    ts=[-q/2+mp.mpf(j)/N+mp.j*eta for j in range(r)]
    Y=[mp.re(fun(t)) for t in ts]
    c=[(Y[0]+2*sum(Y[1:]))/N]
    for k in range(1,r):
        c.append(2*(Y[0]+2*sum(Y[j]*mp.cos(2*mp.pi*k*j/N) for j in range(1,r)))/(N*mp.cosh(mp.mpf(k)/(4*r))))
    ans=-sum(w*v for w,v in zip(residue_weights(q,r),c))/(mp.pi*mp.sin(mp.pi*q))**r
    return ans

if __name__=='__main__':
    q=mp.mpf('.5');out={'working_digits':mp.mp.dps,'gamma_ratio_tail':{'N':144,'K':58},'Euler_tail':{'start':32,'depth':340},'sampling':'Stable fixed shifted cosine grid, different from first computation','scope':'Nonrigorous numerical control; no interval bound'}
    old=json.loads(Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/d2_factorization.json').read_text())
    for r in [3,4,7]:
        start=time.time()
        if r<7:v=dct_extract(r,q,lambda t:(-1)**r*d2.omega(q,r,t)**2)
        else:v=dct_extract(r,q,lambda t:d2.omega_alt(t)**2)/2
        key='P5' if r==7 else f'W{r}'
        # Original records use '(real + imagj)' string; compare real component.
        ov=mp.mpf(old[key]['value'].lstrip('(').split(' + ')[0].split(' - ')[0])
        row={'value':str(v),'difference_from_first_real_part':str(v-ov),'seconds':time.time()-start}
        if r==3:row['Gamma_difference']=str(v-mp.gamma(mp.mpf('.25'))**8/(8*mp.pi**4))
        out[key]=row;print(key,row,flush=True)
        Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/d2_control.json').write_text(json.dumps(out,indent=2))
