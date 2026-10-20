import mpmath as mp, json, time
from pathlib import Path
mp.mp.dps=45
pi=mp.pi
points=[mp.mpf('0.25'),mp.mpf('0.25')+mp.mpf('.3')*1j,mp.mpf('0.2')-mp.mpf('.7')*1j]
results=[]
for s in points:
    def f(y):
        t=mp.mpf(1)/8+1j*y
        return 1j/(mp.expm1(2j*pi*t)*(1-t)*(1-2*s-t))
    start=time.time()
    integral=mp.quad(f,[-mp.inf,-16,-4,-1,0,1,4,16,mp.inf])
    exact=(mp.digamma(1-2*s)+mp.euler)/(-2*s)
    err=abs(integral-exact)
    print(s,integral,exact,err,'sec',time.time()-start,flush=True)
    results.append({'s':str(s),'direct_inner_Barnes':str(integral),'digamma_quotient':str(exact),'absolute_difference':str(err)})
(Path(__file__).resolve().parent/'results'/'inner_checks.json').write_text(json.dumps({'working_decimal_digits':mp.mp.dps,'contour_real_part':'1/8','log_minus_one':'i*pi','results':results,'rigorous_interval':False},indent=2))
