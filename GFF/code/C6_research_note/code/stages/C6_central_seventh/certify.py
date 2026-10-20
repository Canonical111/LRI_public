"""Fresh rational interval evaluation of the new central seventh-power sum.

Initial constants: pi, log(2), zeta(3), independently enclosed here.
New truncation theorem: Euler remainder <= 2**(100-N), DERIVATION.md.
All numerical enclosure arithmetic is integer/rational. The previous certificate
is read only after the new sum has been computed, for comparison and reassembly
of the unchanged parts of C6. It is not a fitting target.
"""
from pathlib import Path
from fractions import Fraction as F
import json,sys,time
import dyadic
from dyadic import I,log,machin_pi,evaluate
ROOT=Path(__file__).resolve().parent
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)

def weights(N):
    if N<1:raise ValueError('N >= 1 required')
    den=1<<N;c=1;partial=0
    for n in range(N):
        partial+=c
        yield F(den-partial,den)
        c=c*(N-n)//(n+1)

def constants():
    p=machin_pi();ell=log(I(2));eta=I(0);K=1400
    for n,w in enumerate(weights(K)):eta+=(-1)**n*w*I(F(1,(n+1)**3))
    z3=(eta+I.bounds(0,F(1,1<<K)))*F(4,3)
    return p,ell,z3

def compute(N,p,ell,z3):
    a=I(1);H=I(0);H2=I(0);J=I(0);J2=I(0);J3=I(0)
    total=I(0);p5=I(0);quad=I(0);dx=I(0)
    for n,w in enumerate(weights(N)):
        y=I(F(4*n+1,4));h=ell+H-J;delta=p**2/3-4*J2+2*H2
        u=1-14*y*h;v=196*y*h**2-28*h+7*y*(delta-p**2)
        T=80*p**2*y-26*p*u+11*v;V=28*p**2*y-10*p*u+3*v
        R=-7*(p**2/3+4*J2);S=-112*(z3-J3)
        fn=(98*J+74*ell-6*p)*T-98*p*V-98*(11*u-13*p*y)*(p**2/3+4*J2)-8624*y*(z3-J3)
        b=(-1)**n*w*a**7
        total+=b*fn
        p5+=b*T/(4*p**2)
        quad+=b*V/(2*p**2)
        dx+=b*(14*J*T/(4*p**2)-13*y*R/(2*p)+11*(2*u*R+y*S)/(4*p**2))
        H+=F(1,n+1);H2+=F(1,(n+1)**2)
        for k in [2*n+1,2*n+2]:
            J+=F(1,k);J2+=F(1,k*k);J3+=F(1,k*k*k)
        a*=F(2*n+1,2*n+2)
    error=F(2)**(100-N)
    value=total.inflate(error)
    # This same deliberately oversized error also bounds each of the following
    # derivative-linear combinations, by the coefficient bounds in the note.
    pp5=16*p**5*p5
    mu=-48*p**5*dx/7-96*p**5*ell*p5+48*p**6*quad
    info={'N':N,'finite_arithmetic_interval':total.package(260),
          'Euler_error_bound':str(error),'M7central':value.package(260),
          'P5_check_approximant':pp5.package(160),'mu_check_approximant':mu.package(160)}
    return value,info

def unpack(v):
    den=1<<v['denominator_power_of_two']
    return I.bounds(F(int(v['lower_numerator']),den),F(int(v['upper_numerator']),den))

def overlap(a,b):return a.lower()<=b.upper() and b.lower()<=a.upper()

def main():
    st=time.time();dyadic.set_precision(1280)
    p,ell,z3=constants();runs=[];vals=[]
    for N in [300,600,900]:
        v,info=compute(N,p,ell,z3);runs.append(info);vals.append(v)
        print('N',N,'M7 width',float(v.width()),flush=True)
    assert all(vals[i].lower()<=vals[i+1].lower()<=vals[i+1].upper()<=vals[i].upper() for i in range(2))
    previous=json.loads((ROOT/'inputs/previous_complete_interval.json').read_text())
    old=json.loads((ROOT/'inputs/expression.json').read_text())
    new=json.loads((ROOT/'results/reduced_expression.json').read_text())
    env={k:unpack(v) for k,v in previous['values'].items()}
    old_obj=next(x for x in old['single_index_harmonic_series_terms'] if x['id']=='L7')
    CZ=sum((evaluate(old_obj['ordinary_constant_coefficients'][str(r)],env)*env['Z'+str(r)] for r in [1,2,3,5,7]),I(0))
    oldblock=-36*env['A']*env['PZ5']-392*env['pi']**F(3,2)*(CZ+2*env['L7'])
    old_M=oldblock/(24*env['pi']**3)
    assert overlap(vals[-1],old_M)
    env.update(pi=p,ell=ell,z3=z3,A=p+4*ell,M7central=vals[-1])
    newblock=24*p**3*vals[-1]
    assert overlap(newblock,oldblock)
    rhs=new['formula'].split(' = ',1)[1].replace('known_polynomial','('+new['known_polynomial']+')')
    full=evaluate('('+rhs+')/2187',env)
    oldfull=unpack(previous['C6_representation'])
    assert overlap(full,oldfull)
    out={
      'scope':'Fresh enclosure of the new central seventh-power series, plus reassembly using the inherited intervals of the unchanged quantities. No new graph/RG verification.',
      'arithmetic':'Integer/rational outward dyadic interval arithmetic; 1280 bits. Timing and displayed width summaries are not used in interval construction.',
      'initial_constants':{'pi':p.package(260),'ell':ell.package(260),'z3':z3.package(260)},
      'Euler_remainder_theorem':'abs(M7-M7_Euler_N) <= 2**(100-N), N>=1',
      'runs':runs,'nested':True,
      'new_M7_overlaps_inherited_five_shift_value':True,
      'inherited_five_shift_M7_interval':old_M.package(260),
      'new_seventh_block_in_r6':newblock.package(200),
      'inherited_seventh_block_in_r6':oldblock.package(200),
      'updated_C6_representation':full.package(160),
      'full_interval_overlaps_inherited_certificate':True,
      'unchanged_source_correction':new['source_correction'],
      'seconds':time.time()-st
    }
    (ROOT/'results/intervals.json').write_text(json.dumps(out,indent=2)+'\n')
    print('M7:',vals[-1].package(100)['decimal_lower'])
    print('new C6:',full.package(100)['decimal_lower'])
    print('C6 width',float(full.width()),'seconds',time.time()-st)
    return out
if __name__=='__main__':main()
