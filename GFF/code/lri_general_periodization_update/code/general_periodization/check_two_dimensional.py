"""Independent all-spin test of finite sampling, using exact d=2 factorization.
No retained period numbers are inputs to these evaluations.
"""
import mpmath as mp, json, time
from pathlib import Path
from check_wheel_periodization import residue_weights
mp.mp.dps=55
from gamma_series import ratio_power_sum, alternating_linear_sum

def omega(x,r,t):
    right=ratio_power_sum(x+t,1+t,r)
    reflected=ratio_power_sum(1-t,2-x-t,r)
    return mp.sin(mp.pi*(x+t))**r*right+(-mp.sin(mp.pi*t))**r*reflected

def extract(r,x,vals):
    V=mp.matrix([[mp.chebyt(k,j+2) for k in range(r)] for j in range(r)])
    coef=mp.lu_solve(V,mp.matrix(vals))
    result=-sum(coef[k]*residue_weights(x,r)[k] for k in range(r))/(mp.pi*mp.sin(mp.pi*x))**r
    return result,coef

def wheel2(r,x):
    ts=[-x/2+mp.j*mp.acosh(j+2)/(2*mp.pi) for j in range(r)]
    vals=[(-1)**r*omega(x,r,t)**2 for t in ts]
    ans,coefs=extract(r,x,vals)
    return (mp.gamma(1-x)/mp.gamma(x))**r*ans,coefs

def omega_alt(t):
    q=mp.mpf('.5');r=7;v=q+2*t
    right=alternating_linear_sum(q+t,1+t,r,v)
    reflected=alternating_linear_sum(1-t,2-q-t,r,2-v)
    pref=(-mp.sin(mp.pi*t)/mp.sin(mp.pi*(q+t)))**r
    return mp.sin(mp.pi*(q+t))**r*(right+pref*reflected)

def primitive2():
    x=mp.mpf('.5');r=7
    ts=[-x/2+mp.j*mp.acosh(j+2)/(2*mp.pi) for j in range(r)]
    vals=[omega_alt(t)**2 for t in ts]
    ans,coefs=extract(r,x,vals)
    return ans/2,coefs

if __name__=='__main__':
    out={'working_digits':mp.mp.dps}
    for r in [3,4]:
        start=time.time();v,c=wheel2(r,mp.mpf('.5'))
        out[f'W{r}']={'value':str(v),'coefficients':[str(a) for a in c],'seconds':time.time()-start}
        if r==3:out['W3']['Gamma_check_difference']=str(v-mp.gamma(mp.mpf('.25'))**8/(8*mp.pi**4))
        print(f'W{r}',out[f'W{r}'],flush=True)
        Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/d2_factorization.json').write_text(json.dumps(out,indent=2))
    start=time.time();v,c=primitive2();out['P5']={'value':str(v),'coefficients':[str(a) for a in c],'seconds':time.time()-start};print('P5',out['P5'],flush=True)
    Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/d2_factorization.json').write_text(json.dumps(out,indent=2))
