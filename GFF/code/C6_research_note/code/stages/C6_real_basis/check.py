"""Check two real-valued rewrites of the retained C6 polylog block.

The checks are floating point, not rigorous interval certificates.
No graph/RG claim or full-coefficient reevaluation is made.
"""
import argparse, json, math, time
from pathlib import Path
import mpmath as mp
import sympy as sp
from hpl_reference import at_i
ROOT=Path(__file__).resolve().parent

def cosine_c5(nterms):
    # Euler weighting of the real cosine-series coefficients at pi/2.
    # For k>=1, Li_{2,1,2} has coefficient H_{k-1}(1,2)/k^2.
    h2=mp.mpf(0); nested=mp.mpf(0); coeff=[]
    for j in range(1,2*nterms):
        nested += h2/j
        h2 += mp.mpf(1)/(j*j)
        if j%2: coeff.append(nested/(j+1)**2)
    den=mp.mpf(2)**nterms; accum=0; ans=[]
    for r,b in enumerate(coeff):
        accum+=math.comb(nterms,r)
        w=1-mp.mpf(accum)/den
        ans.append((-1)**(r+1)*w*b)
    return mp.fsum(ans)

def exact_checks():
    p,g,L,C,U,V=sp.symbols('p g L C U V',real=True)
    z3,z5=sp.symbols('z3 z5',real=True)
    D3=-L/2-7*p**3/192
    B=4352*((32*g+9*p*p)*D3-64*C)
    shift=-sp.Rational(476,3)*p**3*(32*g+9*p*p)
    real=-2176*((32*g+9*p*p)*L+128*C)
    checks={'two_value_weighted_replacement':sp.expand(B-real-shift)==0}
    # All-real, single-function-family optional form.
    Cexpr=-g*L+sp.Rational(3,2)*U+V/2-sp.Rational(13,192)*g*p**3+sp.Rational(451,3072)*p*p*z3+sp.Rational(7635,2048)*z5
    sh3=sp.Rational(41344,3)*g*p**3-1428*p**5-sp.Rational(122672,3)*p*p*z3-1038360*z5
    three=-6528*(3*p*p-32*g)*L-139264*(3*U+V)
    checks['three_value_weighted_replacement']=sp.expand(B.subs(C,Cexpr)-three-sh3)==0
    # Differentiate the general-angle C5 formula; this checks the integration by parts.
    x,theta=sp.symbols('x theta',real=True)
    checks['Ls3_polynomial_at_pi_over_2']=sp.integrate((x-p)**2/8,(x,0,p/2))==7*p**3/192
    checks['G_pi3_new_coefficient']= -sp.Rational(544,3)-sp.Rational(15232,3)==-sp.Rational(15776,3)
    checks['pi5_new_coefficient']=sp.Rational(37631,128)-1428==-sp.Rational(145153,128)
    # Complete general-angle weight-five identity: a derivative and boundary check.
    x=sp.symbols('x',real=True)
    lf,bf,ii,a3,b4,a5,uu,vv,jj=[sp.Function(n)(x) for n in ['lf','bf','ii','a3','b4','a5','uu','vv','jj']]
    q=(x-p)/2
    rhs=(2*bf*ii+sp.Rational(3,2)*uu+vv/2+bf*(q**3-p*p*q/12)
         +((x-p)**2/8-p*p/24)*a3
         +(5*p*x/4-x*x/4-p*p/12)*z3+sp.Rational(3,4)*(a5-z5))
    derivs={sp.diff(bf,x):-lf,sp.diff(ii,x):(lf**2-q**2)/2,
            sp.diff(a3,x):-bf,sp.diff(b4,x):a3,sp.diff(a5,x):-b4,
            sp.diff(uu,x):-bf*lf**2,sp.diff(vv,x):jj}
    rr=z3/2+a3/2+q*bf
    pim=-jj/6-q*q*bf/2-q*a3/2-p*z3/4+b4/4
    original_derivative=-(lf**2-q**2)*bf/2-lf*q*(q*q-p*p/12)-2*lf*ii-2*q*rr-3*pim
    checks['general_angle_D5_derivative']=sp.expand(sp.diff(rhs,x).subs(derivs)-original_derivative)==0
    checks['general_angle_D5_boundary']=sp.simplify(rhs.subs({x:0,bf:0,ii:0,a3:z3,b4:0,a5:z5,uu:0,vv:0,jj:0}))==0
    assert all(checks.values()),checks
    return checks

def run(digits):
    mp.mp.dps=digits+15
    t0=time.time();p=mp.pi;g=mp.catalan; al=p/2
    logsin=lambda x:mp.log(2*mp.sin(x/2))
    L=-mp.quad(lambda u:2*al*u*logsin(al*u*u)**2,[0,mp.mpf('0.25'),mp.mpf('0.5'),1])
    # Published iterated-log-sine convention: increasing inner-to-outer arguments.
    U=-mp.quad(lambda u:2*al*u*mp.clsin(2,al*u*u)*logsin(al*u*u)**2,[0,mp.mpf('0.5'),1])
    V=mp.quad(lambda u:2*al*u*(al-al*u*u)*logsin(al*u*u)**3,[0,mp.mpf('0.5'),1])
    cN=cosine_c5(5*digits+100)
    cN2=cosine_c5(7*digits+150)
    h=at_i([(0,1,1),(0,1,1,0,1)],6*digits+150)
    d3=mp.im(h[(0,1,1)]);d5=mp.re(h[(0,1,1,0,1)])
    D3=-L/2-7*p**3/192
    D5=-g*L+mp.mpf(3)*U/2+V/2-mp.mpf(13)*g*p**3/192+mp.mpf(451)*p*p*mp.zeta(3)/3072+mp.mpf(7635)*mp.zeta(5)/2048
    old=4352*((32*g+9*p*p)*d3-64*d5)
    shift=-mp.mpf(476)/3*p**3*(32*g+9*p*p)
    real=-2176*((32*g+9*p*p)*L+128*cN2)
    sh3=mp.mpf(41344)/3*g*p**3-1428*p**5-mp.mpf(122672)/3*p*p*mp.zeta(3)-1038360*mp.zeta(5)
    pure=-6528*(3*p*p-32*g)*L-139264*(3*U+V)
    errors={
      'D3_Ls3':abs(d3-D3),
      'C5_real_cosine_vs_reference':abs(cN2-d5),
      'C5_Euler_cutoff_change':abs(cN2-cN),
      'C5_pure_log_sine_identity':abs(D5-d5),
      'complete_two_value_replacement':abs(old-real-shift),
      'complete_three_log_sine_replacement':abs(old-pure-sh3),
    }
    tol=mp.mpf(10)**(-digits+5)
    assert all(e<tol for e in errors.values()),errors
    report={
       'requested_digits':digits,'working_digits':mp.mp.dps,
       'scope':'Floating-point implementation checks, not interval certificates; no full C6 reevaluation.',
       'old_HPL_reference':'Own series at i/2 then Taylor continuation to i; inherited code.',
       'new_methods':'Ls3, Ls23, Ls41 by real quadrature; C5 by real Euler-weighted cosine coefficients at two cutoffs.',
       'values':{k:mp.nstr(v,digits+5) for k,v in {'Ls3_pi2':L,'Cl212_pi2':cN2,'Ls23_pi2':U,'Ls41_pi2':V,'old_D3':d3,'old_D5':d5,'old_polylog_block_r6':old,'new_two_value_block_r6':real,'two_value_polynomial_shift':shift,'new_three_value_block_r6':pure,'three_value_polynomial_shift':sh3}.items()},
       'absolute_discrepancies':{k:mp.nstr(v,12) for k,v in errors.items()},
       'exact_checks':exact_checks(), 'seconds':time.time()-t0,
    }
    (ROOT/'results'/f'checks_{digits}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('digits',type=int,nargs='?',default=70)
    args=ap.parse_args();run(args.digits)
