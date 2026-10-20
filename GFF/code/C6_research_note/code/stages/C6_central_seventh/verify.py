"""Exact algebra checks for the analytic transformation, not a numerical fit."""
from pathlib import Path
import json,hashlib
import sympy as s
from formula import build,symbols_for
ROOT=Path(__file__).resolve().parent

def main():
    old,new,env=build();checks=[]
    def check(label,expr):
        if s.simplify(s.expand(expr))!=0:raise AssertionError(label+': '+str(s.simplify(expr)))
        checks.append(label)
    p,e,g,A=s.symbols('pi ell gamma A');rt=s.sqrt(2)
    c7,s7=s.symbols('c7 s7')
    env2=dict(env,pi=p,ell=e,A=A,c7=c7,s7=s7,sqrt=s.sqrt)
    z={r:s.Symbol('Z'+str(r)) for r in [1,2,3,5,7]}
    l7=next(x for x in old['single_index_harmonic_series_terms'] if x['id']=='L7')
    w={r:s.sympify(l7['weights'][str(r)],locals=env2) for r in z}
    q={r:s.sympify(l7['ordinary_constant_coefficients'][str(r)],locals=env2) for r in z}
    aa={1:22*rt+13,2:-35,3:22*rt-13,5:22*rt-13,7:22*rt+13}
    bb={1:10+12*rt,2:-16,3:-10+12*rt,5:-10+12*rt,7:10+12*rt}
    trig={1:c7,2:1,3:c7,5:-s7,7:s7}
    cot={1:rt-1,2:0,3:1-rt,5:-1-rt,7:1+rt}
    psi_plus_gamma={1:p/2-3*e,2:0,3:-p/2-3*e+4,5:p/2-3*e+s.Rational(4,3),7:-p/2-3*e+s.Rational(24,5)}
    for r in z:
        check('input harmonic weight r='+str(r),w[r]+12*aa[r]*trig[r])
        check('input ordinary correction r='+str(r),q[r]-w[r]*(2*psi_plus_gamma[r]+p*cot[r]+2*e)-12*p*bb[r]*trig[r])
    # Prove the finite trigonometric interpolation on all three basis functions.
    t=s.symbols('t',real=True)
    for k in [1,2,3]:
        f=s.sin(2*s.pi*k*t)
        T=(22*rt+13)*f.subs(t,s.Rational(1,8))+(22*rt-13)*f.subs(t,s.Rational(3,8))-35*f.subs(t,s.Rational(1,4))
        U=(10+12*rt)*f.subs(t,s.Rational(1,8))+(-10+12*rt)*f.subs(t,s.Rational(3,8))-16*f.subs(t,s.Rational(1,4))
        D=(20*f-s.Rational(13,2)/s.pi*s.diff(f,t)+s.Rational(11,4)/s.pi**2*s.diff(f,t,2)).subs(t,s.Rational(1,4))
        E=(14*f-5/s.pi*s.diff(f,t)+s.Rational(3,2)/s.pi**2*s.diff(f,t,2)).subs(t,s.Rational(1,4))
        check('T interpolation mode '+str(k),T-D)
        check('U interpolation mode '+str(k),U-E)
    y,h,d,J,J2,J3,z3=s.symbols('y h delta J J2 J3 z3')
    u=1-14*y*h;v=196*y*h**2-28*h+7*y*(d-p**2)
    R=-7*(p**2/3+4*J2);S=-112*(z3-J3)
    logt=1/y-14*h;logtt=-1/y**2-7*p**2+7*d
    check('first t derivative',u-y*logt)
    check('second t derivative',v-y*(logt**2+logtt))
    fx=14*J*y;fxt=14*J*u+y*R;fxtt=14*J*v+2*u*R+y*S
    T=80*p**2*y-26*p*u+11*v;V=28*p**2*y-10*p*u+3*v
    D0=T/(4*p**2);E0=V/(2*p**2)
    Dx=20*fx-s.Rational(13,2)/p*fxt+s.Rational(11,4)/p**2*fxtt
    fn=(98*J+74*e-6*p)*T-98*p*V-98*(11*u-13*p*y)*(p**2/3+4*J2)-8624*y*(z3-J3)
    p5=16*p**5*D0
    mu=-48*p**5*Dx/7-6*e*p5+48*p**6*E0
    check('complete seventh-power weighted insertion',24*p**3*fn-(-36*(p+4*e)*p5-98*mu))
    fzero=fn.subs({y:s.Rational(1,4),h:e,d:p**2/3,J:0,J2:0,J3:0})
    specified=39886*e**3-10906*e**2*p-22792*e**2-2188*e*p**2+8156*e*p-s.Rational(1679,6)*p**3+s.Rational(2330,3)*p**2-2156*z3
    check('n=0 term retained without a polynomial shift',fzero-specified)
    op=s.sympify(old['known_polynomial'],locals=env2);np=s.sympify(new['known_polynomial'],locals=env2)
    CZ=sum(q[r]*z[r] for r in z)
    check('entire old known seventh-power block',op-np+36*A*s.Symbol('PZ5')+392*p**s.Rational(3,2)*CZ)
    # Independently check the compact Bminus/Bplus collection and full outer formula.
    ce=symbols_for(new['compact_known_polynomial']);ce.update(env2)
    compact=s.sympify(new['compact_known_polynomial'],locals=ce)
    bm,bp=s.symbols('Bminus Bplus')
    replacements={s.Symbol('Poct'):13*bm-3*bp,s.Symbol('Ell'):-(13*A-3*p)*bm/2+(3*A-p)*bp/2}
    check('compact and expanded new known part',np.subs(replacements)-compact)
    oldrhs=old['formula'].split(' = ',1)[1];newrhs=new['formula'].split(' = ',1)[1]
    re=symbols_for(oldrhs+' '+newrhs);re.update(env2)
    before=s.sympify(oldrhs,locals=re).subs(s.Symbol('known_polynomial'),op)
    after=s.sympify(newrhs,locals=re).subs(s.Symbol('known_polynomial'),np)
    after=after.subs(s.Symbol('M7central'),(-36*A*s.Symbol('PZ5')-392*p**s.Rational(3,2)*CZ-784*p**s.Rational(3,2)*s.Symbol('L7'))/(24*p**3))
    check('complete active formula including unchanged outer coefficients',after-before)
    forbidden={s.Symbol(n) for n in ['PZ5','Z1','Z2','Z3','Z5','Z7','L7','CZ','U','V']}
    assert not(np.free_symbols&forbidden);checks.append('no removed special values in active known polynomial')
    assert old['source_correction']==new['source_correction'];checks.append('source repair preserved exactly once')
    assert old['compact_elementary_polynomial']==new['compact_elementary_polynomial'];checks.append('elementary polynomial unchanged')
    assert old['polylogarithm_terms']==new['polylogarithm_terms'];checks.append('polylogarithm part unchanged')
    assert old['single_index_recurrence_series_terms']==new['single_index_recurrence_series_terms'];checks.append('primitive recurrence unchanged')
    assert old['classical_polylogarithm_replacement_terms']==new['classical_polylogarithm_replacement_terms'];checks.append('H3 and H5 unchanged')
    assert old['single_index_harmonic_series_terms'][0]==new['single_index_harmonic_series_terms'][0];checks.append('wheel unchanged')
    # Exact Euler-transform finite identity and its remainder, at symbolic q.
    qv,tv=s.symbols('q t')
    for N in range(1,9):
        approx=sum((-1)**n*(1-s.Rational(1,2**N)*sum(s.binomial(N,k) for k in range(n+1)))*(n+tv)*qv**n for n in range(N))
        exact=tv/(1+qv)-qv/(1+qv)**2
        remainder=2**(-s.Integer(N))*(tv*(1-qv)**N/(1+qv)-N*qv*(1-qv)**(N-1)/(1+qv)-qv*(1-qv)**N/(1+qv)**2)
        check('Euler kernel remainder N='+str(N),exact-approx-remainder)
    # Coefficient bounds in the Cauchy tail proof.
    crude=(2**19+2**21+2**25+2**20+2**22+2**26)
    assert crude<2**27;checks.append('mixed-derivative coefficient norm less than 2^27')
    out={'checks':checks,'count':len(checks),'all_passed':True,
         'input_sha256':hashlib.sha256((ROOT/'inputs/expression.json').read_bytes()).hexdigest(),
         'limitations':'Algebraic checks support the written analytic proof. They do not replace the growth/convergence arguments or rederive the upstream graph calculation.'}
    (ROOT/'results/exact_checks.json').write_text(json.dumps(out,indent=2)+'\n')
    print(len(checks),'exact checks passed')
    return out
if __name__=='__main__':main()
