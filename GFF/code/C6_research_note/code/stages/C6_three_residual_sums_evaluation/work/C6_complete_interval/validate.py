"""Finite validation checks. Numerical tests are explicitly supplementary."""
from pathlib import Path
from fractions import Fraction as F
from math import comb
import random,json,time
import mpmath as mp
import sympy as sp
import dyadic
from dyadic import I,exp,log
from elementary import Constants,euler_weights
ROOT=Path(__file__).resolve().parent

def unpack(v):
    d=1<<v['denominator_power_of_two']
    return F(int(v['lower_numerator']),d),F(int(v['upper_numerator']),d)

def upper_scientific(q,significant=5):
    q=F(q)
    if q==0:return '0'
    if q<0:raise ValueError('positive quantity required')
    e=len(str(q.numerator))-len(str(q.denominator))
    p=F(10)**e
    if q<p:e-=1
    scale=F(10)**(significant-1-e)
    v=q*scale;c=-((-v.numerator)//v.denominator)
    if c>=10**significant:c//=10;e+=1
    s=str(c).zfill(significant)
    result=s[0]+'.'+s[1:]+'e'+str(e)
    assert F(result)>=q
    return result

def main():
    st=time.time();dyadic.set_precision(1280);rng=random.Random(6006);count=0
    for _ in range(300):
        vals=[F(rng.randrange(-10000,10001),rng.randrange(1,500)) for _ in range(4)]
        a=I.bounds(*sorted(vals[:2]));b=I.bounds(*sorted(vals[2:]));av=[a.lower(),a.upper()];bv=[b.lower(),b.upper()]
        for result,fn in [(a+b,lambda x,y:x+y),(a-b,lambda x,y:x-y),(a*b,lambda x,y:x*y)]:
            assert all(result.contains(fn(x,y)) for x in av for y in bv);count+=1
        if not b.lo<=0<=b.hi:
            v=a/b;assert all(v.contains(x/y) for x in av for y in bv);count+=1
        aa=I.bounds(0,a.absolute_upper());rr=aa.sqrt()
        assert rr.lo*rr.lo<=aa.lo*dyadic.SCALE and rr.hi*rr.hi>=aa.hi*dyadic.SCALE;count+=1
    # Extreme-magnitude division catches reciprocal underflow in a naive fixed-point implementation.
    for k in [0,100,1000,2000,4000]:
        v=I(3*(1<<k))/(1<<k);assert v.lo==v.hi==3*dyadic.SCALE;count+=1
    ec=0
    for N in range(1,13):
        ws=list(euler_weights(N))
        for n,w in enumerate(ws):
            assert w==sum((F(comb(k,n),2**(k+1)) for k in range(n,N)),F(0));ec+=1
    rc=0
    for N in [1,2,3,7,16]:
        ws=list(euler_weights(N))
        for s in [F(0),F(1,8),F(1,2),F(7,8),F(1)]:
            for t in [F(1,8),F(1,4),F(3,8),F(5,8),F(7,8)]:
                finite=sum(((-1)**n*w*(n+t)*s**n for n,w in enumerate(ws)),F(0))
                full=t/(1+s)-s/(1+s)**2
                u=(1-s)/2
                remainder=t*u**N/(1+s)-s*u**N/(1+s)**2-F(N)*s*(1-s)**(N-1)/(2**N*(1+s))
                assert full-finite==remainder
                assert abs(remainder)<=(t+2)/2**N;rc+=1
    # The partial fraction identity underlying the Lambda evaluator.
    m,r=sp.symbols('m r',positive=True)
    apart=1/(r**2*(m+r)**3)+2/(r**3*(m+r)**2)+3/(r**4*(m+r))-3/(m*r**4)+1/(m**2*r**3)
    assert sp.factor(apart-1/(m**2*(m+r)**3))==0
    # The recurrence majorant at its worst admitted n=48.
    n=48
    assert F(8,n-6)+F(16*(n+5),25*(n-6))<=1
    assert F(44,9)+F(45,4)<17
    data=[json.loads((ROOT/'results'/f'complete_{name}.json').read_text()) for name in ['smoke','release','refined']]
    intervals=[unpack(d['C6_representation']) for d in data]
    assert all(a[0]<=b[0]<=b[1]<=a[1] for a,b in zip(intervals,intervals[1:]))
    assert len(set(d['input_sha256'] for d in data))==1
    expr=json.loads((ROOT/'inputs/expression.json').read_text())
    assert all(d['unchanged_source_correction']==expr['source_correction'] for d in data)
    assert all(d['active_auxiliary_series']==['Wcentral','Pa','L7'] for d in data)
    # High-precision special functions are NOT used to construct any certificate.
    mp.mp.dps=450;cs=Constants(1100,320,120);numeric=[]
    for a in map(F,['1/8','1/4','3/8','1/2','5/8','3/4','7/8','1','9/8','11/8','13/8']):
        v=cs.gamma(a);ref=mp.gamma(mp.mpf(a.numerator)/a.denominator)
        assert mp.mpf(v.lo)/mp.power(2,1280)<=ref<=mp.mpf(v.hi)/mp.power(2,1280)
        numeric.append('gamma('+str(a)+') contained at 450-digit reference precision')
    for label,v,ref in [('pi',cs.pi,mp.pi),('Catalan',cs.G,mp.catalan),('zeta3',cs.z3,mp.zeta(3)),('zeta5',cs.z5,mp.zeta(5)),('log2',cs.ell,mp.log(2))]:
        assert mp.mpf(v.lo)/mp.power(2,1280)<=ref<=mp.mpf(v.hi)/mp.power(2,1280)
        numeric.append(label+' contained at 450-digit reference precision')
    final=data[-1]
    widths={name:upper_scientific(unpack(d['C6_representation'])[1]-unpack(d['C6_representation'])[0],5) for name,d in zip(['smoke','release','refined'],data)}
    budget={k:upper_scientific(unpack(v)[1]-unpack(v)[0],5) for k,v in final['weighted_parts_in_C6_units'].items()}
    lo=final['C6_representation']['decimal_lower'];hi=final['C6_representation']['decimal_upper'];length=0
    for a,b in zip(lo,hi):
        if a!=b:break
        length+=1
    out={'exact_interval_arithmetic_endpoint_checks':count,'exact_Euler_weight_checks':ec,
         'exact_Euler_remainder_and_bound_checks':rc,'Lambda_partial_fraction_identity':True,
         'recurrence_majorant_at_n48':True,'beta_log_density_bound_less_than_17':True,
         'three_full_intervals_nested':True,'source_correction_unchanged':True,
         'interval_width_upper_bounds':widths,'weighted_width_upper_bounds':budget,
         'common_decimal_prefix':lo[:length],'common_places_after_decimal':length-lo.index('.')-1,
         'supplementary_numerical_tests':numeric,
         'supplementary_numerical_tests_used_for_certification':False,'seconds':time.time()-st}
    (ROOT/'results/validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
