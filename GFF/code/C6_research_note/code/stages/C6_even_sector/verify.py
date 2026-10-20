"""Exact algebra checks for the even-sector normal form."""
from pathlib import Path
import json
import sympy as sp
from formula import *
ROOT=Path(__file__).resolve().parent
def main():
    checks=[]
    def zero(name,ex):
        assert sp.simplify(sp.expand(ex))==0,name
        checks.append(name)
    t=sp.symbols('t',real=True)
    # Sixth-power cosine interpolation.
    for mode,f in [('constant',sp.S.One),('cos2',sp.cos(2*sp.pi*t)),('cos4',sp.cos(4*sp.pi*t))]:
        lhs=384*f.subs(t,0)-104*f.subs(t,sp.Rational(1,4))+32*f.subs(t,sp.Rational(1,2))
        rhs=(312*f-176/sp.pi*sp.diff(f,t)+52/sp.pi**2*sp.diff(f,t,2)).subs(t,sp.Rational(1,4))
        zero('sixth-power interpolation: '+mode,lhs-rhs)
    # Eighth-power sine interpolation.
    for k in [1,2,3]:
        f=sp.sin(2*sp.pi*k*t)
        rhs=(5*rt2*f/8-sp.diff(f,t)/(4*sp.pi)+rt2*sp.diff(f,t,2)/(32*sp.pi**2)).subs(t,sp.Rational(1,4))
        zero('eighth-power interpolation: sin'+str(2*k),f.subs(t,sp.Rational(1,8))-rhs)
    zero('cos(pi/8)^8 normalization',sp.cos(sp.pi/8)**8-(17+12*rt2)/64)
    zero('sin(pi/8)^8 normalization',sp.sin(sp.pi/8)**8-(17-12*rt2)/64)
    zero('Bsum coefficient',Cs-(-3*Cminus+9*Cplus)/8)
    zero('Bdiff coefficient',Cd-(-3*Cminus-9*Cplus)/8)
    ds6=[1,-12*h,144*h*h+6*de-6*pi*pi]
    zero('Pb derivative polynomial',pi**5*a**6*(312*ds6[0]-176/pi*ds6[1]+52/pi**2*ds6[2])-pb_summand)
    fg=40*rt2*pi**4*g8[0]-16*pi**3*g8[1]+2*rt2*pi**2*g8[2]
    zero('PZ6 weighted interpolation',pi**2*((816-828*rt2)*pi**4*g8[0]+23*fg)*a**8-z6_summand)
    zero('PK6 weighted interpolation',pi**2*(432*(1-rt2)*pi**4*g8[0]+12*fg)*a**8-k6_summand)
    zero('entire eighth-power block',24*z6_summand+k6_summand/3-pi**3*a**8*R8)
    bpart=8*pi**4*Cs*y*a**6+4*pi**3*Cd*a**4
    wpart=-393*pi**3*a**4*(8+20*pi*y*a*a)*de
    zero('complete pointwise even-sector substitution',bpart+24*pb_summand+24*z6_summand+k6_summand/3+wpart-pi**3*even_summand)
    zero('wheel zero-index correction',393*pi**3*(8+5*pi)*pi**2/3-n0_shift)
    inp=json.loads((ROOT/'inputs/expression.json').read_text());out=build()
    loc={str(v):v for v in [A,Q,G,pi,z3,z5,ell,Poct,Ell,PB6,PZ6,PK6]}
    known=sp.sympify(inp['known_polynomial'],locals=loc)
    new=sp.sympify(out['known_polynomial'],locals=loc)
    bm,bp=sp.symbols('Bminus Bplus')
    substitutions={Poct:13*bm-3*bp,Ell:-(13*A-3*pi)*bm/2+(3*A-pi)*bp/2}
    block=Cs*(bm+bp)+Cd*(bm-bp)+24*PB6+24*PZ6+PK6/3
    zero('complete known-part replacement',known.subs(substitutions)-block+n0_shift-new)
    zero('standalone pi-sixth cancellation',new.coeff(pi,6))
    zero('standalone pi-fifth coefficient',new.coeff(pi,5)+sp.Rational(279249,128))
    for field in ['source_correction','single_index_recurrence_series_terms',
                  'polylogarithm_terms','classical_polylogarithm_replacement_terms',
                  'central_seventh_periodization','legacy_L7_definition']:
        assert out[field]==inp[field],field
        checks.append('unchanged '+field)
    oldm=next(q for q in inp['single_index_harmonic_series_terms'] if q['id']=='M7central')
    newm=next(q for q in out['single_index_harmonic_series_terms'] if q['id']=='M7central')
    assert oldm==newm;checks.append('unchanged complete M7 definition')
    assert out['active_auxiliary_series']==['Ecentral','Pa','M7central']
    checks.append('three retained auxiliary quantities; no independence claim')
    # Direct tail estimates used in the note.
    u=sp.symbols('u',nonnegative=True)
    zero('quadratic lower bound for eighth derivative',256*u*u-32*u+1-(16*u-1)**2)
    zero('quadratic upper bound for eighth derivative',8-(256*u*u-32*u)-(sp.Rational(1,4)-u)*(256*u+32))
    assert all(str(v) not in str(new) for v in [Poct,Ell,PB6,PZ6,PK6])
    checks.append('all active unit-argument period symbols absent from known polynomial')
    res={'check_count':len(checks),'checks':checks,'passed':True,
         'input_monomials':len(sp.Add.make_args(known)),'output_monomials':len(sp.Add.make_args(new)),
         'scope':'Finite algebra and bookkeeping checks; Fourier growth/analytic arguments are in DERIVATION.md.'}
    (ROOT/'results/exact_checks.json').write_text(json.dumps(res,indent=2)+'\n')
    return res
if __name__=='__main__':print(json.dumps(main(),indent=2))
