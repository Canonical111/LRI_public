#!/usr/bin/env python3
"""Independent d=3 normalizations, weights and fixed-point algebra checks (pure Python; no native binary).

Writes nothing into the package: an optional record goes to the path given as the first argument.
"""
from pathlib import Path
import ast,importlib.util,json,sys
import mpmath as mp
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import dump,load,checked
from assemble import REFERENCE_LOWER,coefficients,jacobians
BASE=ROOT/'reference/baseline_previous/baseline'

def literal(path:Path,name:str):
    """Value of the module-level assignment `name = <literal>` in an archived source file (never imported)."""
    for node in ast.parse(path.read_text()).body:
        if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in node.targets):
            return eval(compile(ast.Expression(node.value),str(path),'eval'),{'__builtins__':{}})
    raise KeyError(f'{name} not found in {path}')

def run():
    mp.mp.dps=80;d=mp.mpf(3);q=d/4;records=[]
    for L,line in zip(range(2,7),(ROOT/'inputs/gamma_d3.txt').read_text().splitlines()):
        vals=list(map(mp.mpf,line.split()));K=int(vals[0]);norm=vals[1];logs=vals[2:]
        assert K==6-L and len(logs)==5 and logs[0]==0
        def logG(z):
            return (mp.loggamma(1+L*z/2)+L*(mp.loggamma(d/2+z/2)-mp.loggamma(1+z/2))
                -2*L*mp.loggamma(q+z/4))
        err=max([abs(2*(-1)**(L+1)*mp.exp(logG(0))-norm)]+
            [abs(mp.diff(logG,0,k)/mp.factorial(k)-logs[k])for k in range(1,5)])
        assert err<mp.mpf('1e-47')
        records.append({'L':L,'max_absolute_error':mp.nstr(err,18),'working_digits':80})
    two=load(ROOT/'inputs/two_loop.json');A=2+4*mp.log(2)-mp.pi
    assert abs(mp.mpf(two['B2_decimal'][0])+6*A)<mp.mpf('1e-56')
    # All five B2 entries against the INDEPENDENT 85-digit two-loop record: B2[i] = -2 A2(d=3)[i-1] (same convention as d=2).
    ext=load(BASE/'lri_C6_d2_complete_update/reproduction/lri_C6_d2_two_forest_update/analytic/verification/two_loop_extended_reference.json')['dimensions']['3']['A2']
    b2_err=max(abs(mp.mpf(two['B2_decimal'][i])+2*mp.mpf(ext[str(i-1)]))for i in range(5))
    assert b2_err<mp.mpf('1e-50'),b2_err
    assert all(float(mp.mpf(v))==x for v,x in zip(two['B2_decimal'],two['B2']))
    # C0 = d/2 and C1 = 1/3 - 1/2 in closed form, C2 against the archived d=3 value; C3-C5 reference constants equal the
    # literals of the archived analyses (reference/code/analyze.py REF[3], reference_d3/code/final_analysis.py ref).
    final=literal(ROOT/'reference_d3/code/final_analysis.py','ref');archived=literal(ROOT/'reference/code/analyze.py','REF')[3]
    assert list(REFERENCE_LOWER)==list(archived)==list(final[3:6]),(REFERENCE_LOWER,archived,final)
    rng0=np.random.default_rng(3);low=coefficients({L:rng0.normal(size=2*(7-L))for L in range(3,7)})
    assert low[0]==float(d/2) and abs(low[1]-(mp.mpf(1)/3-mp.mpf(1)/2))<1e-15 and abs(low[2]-final[2])<1e-15,low[:3]
    # Independent finite Lagrange formula including regulator-dependent jets.
    def lagrange(vals):
        N=7;b={1:np.array([3.]),2:np.array(two['B2'])};c={1:np.array([1.]),2:b[2]/6}
        for L,a in vals.items():b[L]=a[:7-L];c[L]=a[7-L:]
        def mul(a,b):return np.convolve(a,b)[:N]
        def zero():return np.zeros(N)
        # B(g,z)=3*(1+h); organize powers of g and z independently.
        h={L-1:np.pad(b[L]/3,(0,N-len(b[L])))for L in range(2,7)}
        result=zero();result[0]=1.5;result[1]=-.5
        for n in range(1,7):
            series={0:np.array([1.])};power={0:np.array([1.])}
            for k in range(1,n):
                nxt={}
                for g1,a in power.items():
                    for g2,v in h.items():
                        if g1+g2<=n-1:
                            z=mul(a,v);nxt.setdefault(g1+g2,zero())[:len(z)]+=z
                power=nxt;coef=(-1)**k*int(mp.binomial(n+k-1,k))
                for gg,z in power.items():series.setdefault(gg,zero())[:len(z)]+=coef*z
            for L in range(1,n+1):
                gg=n-L
                if gg in series:
                    z=mul(L*c[L],series[gg])/(n*3**n)
                    z=z[:N-n];result[n:n+len(z)]+=z
        return result
    rng=np.random.default_rng(2026092803);error=0
    for i in range(96):
        jets={L:rng.normal(size=2*(7-L)) for L in range(3,7)}
        a=coefficients(jets);b=lagrange(jets)
        err=float(np.max(abs(a-b)/np.maximum(1,abs(b))));error=max(error,err)
        assert err<2e-12,(i,a,b)
    J=jacobians(jets);assert np.max(abs(J[6][6]-np.array([-1,3])/2187))<1e-18
    # Every frozen scientific input checks against its retained source.
    manifest=load(ROOT/'inputs/manifest.json')
    for name,digest in manifest['sources'].items():checked(ROOT/name,digest)
    return {'status':'passed','gamma_normalization':records,'two_loop_constant_matches_minus_6A':True,
        'B2_vs_independent_85_digit_A2_max_error':mp.nstr(b2_err,5),'C0_C1_closed_form_and_C2_archived':True,'lower_order_constants_match_archived_literals':True,
        'independent_regulator_dependent_lagrange_cases':96,'max_normalized_lagrange_difference':error,
        'six_loop_sensitivity_matches':[-1/2187,3/2187],
        'source_checksums_verified':len(manifest['sources']),
        'scope':'Exact conventions and floating-point independent assembly checks; not a new physics estimate.'}
if __name__=='__main__':
    x=run()
    if len(sys.argv)>1:dump(Path(sys.argv[1]),x)  # optional record; the shipped benchmarks/ evidence is never rewritten
    print(json.dumps(x,indent=2))
